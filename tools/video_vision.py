"""
Video vision analyzer — extract keyframes + Claude vision API → visual descriptions.

Bổ sung cho viral_video_analyzer skill: transcript cho biết "nói gì",
vision cho biết "trên màn hình có gì" → Section 9.1 (shot list) chính xác hơn.

Flow:
1. ffmpeg extract N keyframes ở timestamp chiến lược (mid-point của segments)
2. Batch frames vào 1 Claude vision call (cost-efficient hơn N calls)
3. Parse response → dict {timestamp: visual_description}

Requirements: ffmpeg binary (apt-get install ffmpeg trên Railway/Docker)
Fallback: nếu ffmpeg thiếu → return empty, skill vẫn chạy với chỉ transcript.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_SONNET_MODEL

logger = logging.getLogger(__name__)

FFMPEG_BINARY = shutil.which("ffmpeg") or os.getenv("FFMPEG_BINARY", "")
DEFAULT_FRAME_COUNT = 6  # 6 frames đủ cover hook + 2 build + climax + CTA + 1 buffer
DEFAULT_FRAME_QUALITY = 3  # ffmpeg -q:v scale 2-5, 3 = balance size/quality
MAX_FRAME_BYTES = 400 * 1024  # ~400KB per frame — vision API edge


def is_available() -> bool:
    return bool(FFMPEG_BINARY and ANTHROPIC_API_KEY)


def availability_report() -> str:
    lines = [f"- ffmpeg: {'✅ ' + FFMPEG_BINARY if FFMPEG_BINARY else '❌ chưa cài (apt-get install ffmpeg)'}",
             f"- Anthropic API: {'✅' if ANTHROPIC_API_KEY else '❌'}"]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Frame extraction (ffmpeg)
# ─────────────────────────────────────────────────────────────────

async def extract_keyframes(
    video_path: str,
    segments: Optional[list[dict]] = None,
    max_frames: int = DEFAULT_FRAME_COUNT,
) -> list[dict]:
    """Extract N keyframes từ video. Trả về list[{timestamp_sec, path}].

    Strategy chọn timestamp:
    - Nếu có segments (từ transcript) → chọn mid-point của N segment đầu/giữa/cuối phân bố đều
    - Nếu không → chia đều theo duration
    """
    if not FFMPEG_BINARY:
        return []

    duration = await _probe_duration(video_path)
    if duration <= 0:
        return []

    timestamps = _choose_timestamps(duration, segments, max_frames)
    if not timestamps:
        return []

    out_dir = tempfile.mkdtemp(prefix="frames_")
    frames: list[dict] = []
    for i, ts in enumerate(timestamps):
        out_path = os.path.join(out_dir, f"frame_{i:02d}_{ts:.1f}s.jpg")
        ok = await _extract_one_frame(video_path, ts, out_path)
        if ok and os.path.getsize(out_path) <= MAX_FRAME_BYTES * 2:
            frames.append({"timestamp_sec": ts, "path": out_path})

    logger.info(f"extracted {len(frames)}/{len(timestamps)} frames from {video_path}")
    return frames


def _choose_timestamps(duration: float, segments: Optional[list[dict]], max_frames: int) -> list[float]:
    """Chọn timestamp đại diện cho video. Ưu tiên segment mid-points."""
    if not segments:
        # Phân bố đều, tránh 0s và duration cuối
        step = duration / (max_frames + 1)
        return [round(step * (i + 1), 2) for i in range(max_frames)]

    # Chọn N segment phân bố đều, lấy mid-point
    n = min(max_frames, len(segments))
    if n <= 0:
        return []
    indices = [int(i * (len(segments) - 1) / max(n - 1, 1)) for i in range(n)] if n > 1 else [0]
    timestamps = []
    for idx in indices:
        seg = segments[idx]
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 1))
        mid = (start + end) / 2
        timestamps.append(round(mid, 2))
    # Bảo đảm timestamp đầu < 3s (cover hook)
    if timestamps and timestamps[0] > 3.0:
        timestamps[0] = min(2.0, duration / 2)
    return sorted(set(timestamps))


async def _probe_duration(video_path: str) -> float:
    """Dùng ffprobe (đi kèm ffmpeg) lấy duration."""
    ffprobe = shutil.which("ffprobe") or FFMPEG_BINARY.replace("ffmpeg", "ffprobe")
    if not ffprobe or not os.path.exists(ffprobe):
        return 0.0
    proc = await asyncio.create_subprocess_exec(
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
        return float(stdout.decode().strip() or 0)
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")
        return 0.0


async def _extract_one_frame(video_path: str, timestamp_sec: float, out_path: str) -> bool:
    """ffmpeg seek + 1 frame extract. -ss trước -i = fast seek."""
    proc = await asyncio.create_subprocess_exec(
        FFMPEG_BINARY, "-y", "-ss", f"{timestamp_sec:.2f}", "-i", video_path,
        "-frames:v", "1", "-q:v", str(DEFAULT_FRAME_QUALITY), out_path,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return proc.returncode == 0 and os.path.exists(out_path)
    except asyncio.TimeoutError:
        proc.kill()
        return False


# ─────────────────────────────────────────────────────────────────
# Claude vision batch analysis
# ─────────────────────────────────────────────────────────────────

VISION_SYSTEM = """Bạn là Video Visual Analyst. Mô tả CHÍNH XÁC những gì thấy trên màn hình ở MỖI frame được cung cấp — KHÔNG suy diễn cảm xúc, KHÔNG bịa.

Cho mỗi frame, output đúng format này:

**Frame @ {timestamp}s:**
- Subject: <ai/cái gì là main subject — 1 dòng>
- Shot type: <close-up / medium / wide / extreme close-up / split / POV>
- Camera angle: <eye-level / low / high / overhead / Dutch tilt>
- Background: <chỗ quay — 1 dòng>
- Lighting: <natural / ring light / golden hour / studio / overhead — mô tả thấy được>
- Composition: <subject ở vị trí nào của frame — center / rule of thirds / edge>
- On-screen text (nếu có): <text + style + vị trí>
- Visual effects (nếu có): <transition, zoom, freeze, overlay graphics>
- Notable detail: <1 chi tiết đáng chú ý cho creator replicate>

Tone: như DP (director of photography) brief team — kỹ thuật, ngắn gọn, không khen."""


async def analyze_frames_with_vision(
    frames: list[dict],
    model: str = CLAUDE_SONNET_MODEL,
) -> str:
    """Gửi frames cho Claude vision, parse text block trả về.

    Batched single call → tiết kiệm cost (1 call x N images thay vì N calls).
    """
    if not frames or not ANTHROPIC_API_KEY:
        return ""

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    content_blocks: list[dict] = []
    for f in frames:
        try:
            with open(f["path"], "rb") as fh:
                img_b64 = base64.standard_b64encode(fh.read()).decode("ascii")
        except Exception as e:
            logger.warning(f"read frame failed: {e}")
            continue
        content_blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64},
        })
        content_blocks.append({
            "type": "text",
            "text": f"^ Frame @ {f['timestamp_sec']:.1f}s — mô tả frame này.",
        })

    if not content_blocks:
        return ""

    content_blocks.append({
        "type": "text",
        "text": "Output mô tả cho TẤT CẢ frames theo đúng format trong system. Mỗi frame 1 block.",
    })

    try:
        resp = await client.messages.create(
            model=model,
            max_tokens=4000,
            system=VISION_SYSTEM,
            messages=[{"role": "user", "content": content_blocks}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        return text.strip()
    except Exception as e:
        logger.warning(f"vision API failed: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────
# Top-level orchestration
# ─────────────────────────────────────────────────────────────────

async def extract_visual_analysis(
    video_path: str,
    segments: Optional[list[dict]] = None,
    max_frames: int = DEFAULT_FRAME_COUNT,
) -> str:
    """Top-level: ffmpeg extract + Claude vision batch → text block để inject prompt.

    Trả về string rỗng nếu engine không sẵn sàng (graceful degrade — skill vẫn chạy
    với chỉ transcript).
    """
    if not is_available():
        return ""
    try:
        frames = await extract_keyframes(video_path, segments, max_frames)
        if not frames:
            return ""
        analysis = await analyze_frames_with_vision(frames)
        # Cleanup temp frames sau khi gửi xong
        for f in frames:
            try:
                os.unlink(f["path"])
            except OSError:
                pass
        if not analysis:
            return ""
        return f"### VISUAL ANALYSIS (Claude vision đã phân tích {len(frames)} keyframes)\n\n{analysis}"
    except Exception as e:
        logger.warning(f"visual analysis pipeline failed: {e}")
        return ""
