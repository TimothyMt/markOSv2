"""
KrillinAI / KlicStudio client — extract transcript + metadata từ video.

Repo gốc: https://github.com/krillinai/KlicStudio
KrillinAI là tool video localization/transcription dùng Whisper + LLM segmentation.

Pattern em chọn:
1. Nếu KRILLIN_BINARY env var trỏ tới binary → subprocess CLI mode (best quality, có VAD + segmentation)
2. Nếu không có → fallback Whisper API qua openai SDK (đã có sẵn trong requirements)
3. Nếu cả 2 fail → cho user paste transcript trực tiếp (skill vẫn chạy được)

Trả về dict:
  {
    "transcript": "full text concat",
    "segments": [{"start": float, "end": float, "text": str}, ...],
    "duration_seconds": float,
    "language": "vi" | "en" | ...,
    "source": "krillin" | "whisper_api" | "user_paste",
    "video_url": str (original input nếu là URL),
  }
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

KRILLIN_BINARY = os.getenv("KRILLIN_BINARY", "")  # vd: /usr/local/bin/krillin
KRILLIN_TIMEOUT_SECONDS = int(os.getenv("KRILLIN_TIMEOUT", "300"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Max file size cho Whisper API: 25MB
WHISPER_MAX_BYTES = 25 * 1024 * 1024

URL_REGEX = re.compile(r"^https?://", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────

async def extract_transcript(
    source: str,
    language_hint: Optional[str] = None,
) -> dict:
    """Extract transcript từ video URL hoặc local file path.

    Args:
        source: URL (YouTube/TikTok/...) hoặc local file path
        language_hint: "vi" / "en" — Whisper sẽ dùng làm prior

    Returns:
        dict với keys: transcript, segments, duration_seconds, language, source, video_url
    """
    is_url = bool(URL_REGEX.match(source))

    # Path 1: KrillinAI CLI (preferred — handles YouTube/TikTok download + transcript)
    if KRILLIN_BINARY and shutil.which(KRILLIN_BINARY):
        try:
            result = await _run_krillin(source, language_hint)
            result["video_url"] = source if is_url else ""
            result.setdefault("local_video_path", "" if is_url else source)
            return result
        except Exception as e:
            logger.warning(f"krillin CLI failed, falling back to whisper: {e}")

    # Path 2: Whisper API fallback
    if OPENAI_API_KEY:
        try:
            local_path = await _ensure_local_file(source) if is_url else source
            result = await _run_whisper_api(local_path, language_hint)
            result["video_url"] = source if is_url else ""
            result["local_video_path"] = local_path
            return result
        except Exception as e:
            logger.warning(f"whisper API failed: {e}")
            raise

    raise RuntimeError(
        "Không có engine transcript khả dụng. Setup 1 trong 2:\n"
        "- KRILLIN_BINARY env var trỏ tới binary KrillinAI (https://github.com/krillinai/KlicStudio)\n"
        "- OPENAI_API_KEY env var (Whisper API fallback)"
    )


def is_available() -> bool:
    """Skill chỉ chạy được nếu có ít nhất 1 engine."""
    return bool(
        (KRILLIN_BINARY and shutil.which(KRILLIN_BINARY))
        or OPENAI_API_KEY
    )


def availability_report() -> str:
    """Trả về thông tin debug để user biết engine nào đang active."""
    krillin_ok = bool(KRILLIN_BINARY and shutil.which(KRILLIN_BINARY))
    whisper_ok = bool(OPENAI_API_KEY)
    lines = []
    lines.append(f"- KrillinAI binary: {'✅ ' + KRILLIN_BINARY if krillin_ok else '❌ chưa setup'}")
    lines.append(f"- Whisper API fallback: {'✅' if whisper_ok else '❌ thiếu OPENAI_API_KEY'}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# KrillinAI CLI
# ─────────────────────────────────────────────────────────────────

async def _run_krillin(source: str, language_hint: Optional[str]) -> dict:
    """Chạy KrillinAI binary, parse stdout JSON.

    Giả định convention KrillinAI có flag --transcript-only --json --input <src>.
    Nếu binary thật khác CLI shape, cần adapt hàm này (tham khảo docs upstream).
    """
    cmd = [
        KRILLIN_BINARY,
        "--transcript-only",
        "--json",
        "--input", source,
    ]
    if language_hint:
        cmd.extend(["--language", language_hint])

    logger.info(f"krillin cmd: {' '.join(cmd)}")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=KRILLIN_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"krillin timeout sau {KRILLIN_TIMEOUT_SECONDS}s")

    if proc.returncode != 0:
        raise RuntimeError(f"krillin exit {proc.returncode}: {stderr.decode()[:500]}")

    data = json.loads(stdout.decode())
    segments = data.get("segments", [])
    return {
        "transcript": data.get("transcript") or " ".join(s.get("text", "") for s in segments),
        "segments": segments,
        "duration_seconds": float(data.get("duration", 0)),
        "language": data.get("language") or language_hint or "vi",
        "source": "krillin",
    }


# ─────────────────────────────────────────────────────────────────
# Whisper API fallback (OpenAI SDK)
# ─────────────────────────────────────────────────────────────────

async def _run_whisper_api(local_path: str, language_hint: Optional[str]) -> dict:
    """Whisper-1 API qua openai SDK. Trả về segments có timestamps."""
    from openai import AsyncOpenAI

    file_size = os.path.getsize(local_path)
    if file_size > WHISPER_MAX_BYTES:
        raise RuntimeError(
            f"File {file_size / 1024 / 1024:.1f}MB vượt giới hạn Whisper API (25MB). "
            "Cần compress audio hoặc dùng KrillinAI binary cho file lớn."
        )

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    with open(local_path, "rb") as f:
        resp = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language=language_hint or "vi",
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    segments = [
        {"start": float(s.start), "end": float(s.end), "text": s.text}
        for s in (resp.segments or [])
    ]
    return {
        "transcript": resp.text,
        "segments": segments,
        "duration_seconds": float(resp.duration or 0),
        "language": resp.language or language_hint or "vi",
        "source": "whisper_api",
    }


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

async def _ensure_local_file(url: str) -> str:
    """Download remote audio/video về /tmp. Whisper accept mp3/mp4/m4a/wav/webm."""
    suffix = Path(url.split("?")[0]).suffix or ".mp4"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="krillin_")
    os.close(fd)

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(tmp_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)

    logger.info(f"downloaded {url} → {tmp_path} ({os.path.getsize(tmp_path)} bytes)")
    return tmp_path


def format_transcript_for_prompt(extract: dict, max_chars: int = 8000) -> str:
    """Format extract dict thành text block đẹp inject vào prompt Claude."""
    src = extract.get("source", "unknown")
    dur = extract.get("duration_seconds", 0)
    lang = extract.get("language", "?")
    segments = extract.get("segments") or []

    header = (
        f"**Transcript engine:** {src} | "
        f"**Độ dài video:** {dur:.1f}s | "
        f"**Ngôn ngữ:** {lang}"
    )

    # Prefer timestamped segments — giúp Claude reason về pacing/hook timing
    if segments:
        lines = []
        for s in segments:
            ts = f"[{s.get('start', 0):.1f}s → {s.get('end', 0):.1f}s]"
            lines.append(f"{ts} {s.get('text', '').strip()}")
        body = "\n".join(lines)
    else:
        body = extract.get("transcript", "")

    if len(body) > max_chars:
        body = body[:max_chars] + f"\n\n... (truncated, tổng {len(body)} chars)"

    return f"{header}\n\n```\n{body}\n```"
