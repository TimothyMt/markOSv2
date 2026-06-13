"""
Tone Calibration Loop — Sprint 6.

Flow:
  1. Content Calendar gen xong → extract Post 1 → show user để check tone
  2. User approve → lock tone signals → gen N-1 bài còn lại với signals
  3. User reject + feedback → AI regen Post 1 theo feedback (max 3 lần)
  4. Sau 3 lần reject → auto-lock (dùng sample_content nếu có)

Graceful: mọi lỗi AI đều degrade về "show calendar gốc".
"""
import logging
import json
import re
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_HAIKU_MODEL, CLAUDE_SONNET_MODEL, AGENT_TIMEOUT

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


# ─── Parse first post from calendar text ──────────────────────────────────────

def parse_first_post(calendar_text: str) -> Optional[dict]:
    """
    Extract bài đăng đầu tiên từ content calendar text.
    Trả về dict {preview, full_block} hoặc None nếu không parse được.

    Hỗ trợ cả 2 format:
    1. Markdown table: tìm đúng weekly grid (có cột Ngày/Kênh/Pillar/Topic)
       — bỏ qua các bảng phụ (Pillar Breakdown, Repurpose Matrix, Team, Story Arc)
    2. Block format: "Tuần 1 — ... Hook: ..."
    """
    # ── Format 1: Find weekly grid table specifically ─────────────────
    # Weekly grid signature: có ít nhất 3 trong các cột đặc trưng
    WEEKLY_GRID_KEYS = {"ngày", "kênh", "channel", "nền tảng", "pillar", "funnel", "topic", "chủ đề"}

    table_pattern = re.compile(
        r"\|([^\n]+)\|\s*\n\|[-| ]+\|\s*\n((?:\|[^\n]+\|[ \t]*\n?)+)",
        re.MULTILINE,
    )

    for m in table_pattern.finditer(calendar_text):
        header_raw = m.group(1)
        header_cells_lower = [c.strip().lower() for c in header_raw.split("|") if c.strip()]

        # Must match ≥3 weekly-grid column keywords — skips Pillar/Repurpose/Team tables
        matched = sum(1 for h in header_cells_lower if any(k in h for k in WEEKLY_GRID_KEYS))
        if matched < 3:
            continue

        # Extract first data row
        data_block = m.group(2)
        first_row_raw = data_block.split("\n")[0].strip()
        first_data_row = [c.strip() for c in first_row_raw.split("|") if c.strip()]
        header_cells_orig = [c.strip() for c in header_raw.split("|") if c.strip()]

        if not first_data_row or len(first_data_row) < 4:
            continue

        # Find important column indices
        topic_idx = next(
            (i for i, h in enumerate(header_cells_orig)
             if any(k in h.lower() for k in ["topic", "chủ đề", "nội dung", "content"])),
            min(7, len(first_data_row) - 1),
        )
        hook_idx = next(
            (i for i, h in enumerate(header_cells_orig)
             if any(k in h.lower() for k in ["hook", "angle"])),
            min(6, len(first_data_row) - 1),
        )
        day_idx = 0
        channel_idx = next(
            (i for i, h in enumerate(header_cells_orig)
             if any(k in h.lower() for k in ["kênh", "channel", "nền tảng"])),
            1,
        )
        pillar_idx = next(
            (i for i, h in enumerate(header_cells_orig) if "pillar" in h.lower()),
            None,
        )
        funnel_idx = next(
            (i for i, h in enumerate(header_cells_orig) if "funnel" in h.lower()),
            None,
        )

        topic   = first_data_row[topic_idx]   if topic_idx   < len(first_data_row) else ""
        hook    = first_data_row[hook_idx]    if hook_idx    < len(first_data_row) else ""
        day     = first_data_row[day_idx]     if day_idx     < len(first_data_row) else ""
        channel = first_data_row[channel_idx] if channel_idx < len(first_data_row) else ""
        pillar_val = (first_data_row[pillar_idx] if pillar_idx is not None and pillar_idx < len(first_data_row) else "Educate")
        funnel_val = (first_data_row[funnel_idx] if funnel_idx is not None and funnel_idx < len(first_data_row) else "TOFU")

        if topic and len(topic) > 10:
            preview = f"📅 {day} | {channel}\n🎯 Hook angle: {hook}\n📝 Topic: {topic}"
            return {
                "preview":   preview,
                "full_block": first_row_raw,
                "row_meta":  {
                    "day": day, "channel": channel, "topic": topic,
                    "hook_angle": hook, "pillar": pillar_val, "funnel": funnel_val,
                },
            }

    # ── Format 2: Block / labelled sections ──────────────────────────
    patterns = [
        r"(?:Tuần\s*1|Week\s*1).*?(?:Hook|Caption|Nội dung|Content)[:\s]+(.{50,500}?)(?=\n\n|\nTuần|\nWeek|\Z)",
        r"(?:POST-001|Bài\s*1|Day\s*1|Ngày\s*1).*?(?:Hook|Caption|Nội dung)[:\s]+(.{50,500}?)(?=\n\n|\nBài|\nPost|\Z)",
    ]
    for pat in patterns:
        m = re.search(pat, calendar_text, re.DOTALL | re.IGNORECASE)
        if m:
            content = m.group(1).strip()[:800]
            return {"preview": content, "full_block": m.group(0)[:1000]}

    # ── Fallback: first paragraph that looks like content, not metadata ──
    # Skip paragraphs that are metadata/instructions (contain "Lưu ý", "Owner", "Giờ đăng" etc.)
    skip_keywords = ["lưu ý", "owner", "giờ đăng", "hook angle", "tổng kế hoạch", "tổng số bài"]
    paragraphs = [
        p.strip() for p in calendar_text.split("\n\n")
        if len(p.strip()) > 100
        and not any(kw in p.strip().lower() for kw in skip_keywords)
    ]
    if paragraphs:
        first = paragraphs[0][:800]
        return {"preview": first, "full_block": first}

    return None


# ─── Generate sample post from calendar row ───────────────────────────────────

_SAMPLE_POST_SYSTEM = """Bạn là Content Writer viết bài mẫu để kiểm tra tone cho founder Việt Nam.

Nhiệm vụ: Viết 1 bài social post hoàn chỉnh dựa trên metadata từ Content Calendar.

Yêu cầu:
- Body ~150-200 chữ, dùng framework phù hợp với Pillar/Funnel
- Hook đầu 12-15 từ, match angle đã chọn
- CTA cuối 1 dòng cụ thể
- 3-5 hashtags
- Tone match với business profile được inject
- Bài phải viết THẬT — đủ để founder judge tone ngay

KHÔNG viết placeholder kiểu "[tên sản phẩm]" — dùng thông tin từ profile.
Chỉ trả về bài viết, không giải thích thêm."""


async def generate_sample_post(
    session,
    row_meta: dict,
    calendar_context: str = "",
) -> str:
    """
    Dùng Haiku gen 1 bài post mẫu từ calendar row metadata.
    row_meta: {day, channel, topic, hook_angle, pillar, funnel}
    Returns written post text, hoặc fallback string nếu fail.
    """
    client = _get_client()
    profile = session.profile

    pillar  = row_meta.get("pillar", "Educate")
    funnel  = row_meta.get("funnel", "TOFU")
    channel = row_meta.get("channel", "Facebook")
    topic   = row_meta.get("topic", "")
    hook_angle = row_meta.get("hook_angle", "Tò mò")

    framework_hint = {
        "educate": "PAS hoặc Star-Story",
        "trust":   "BAB hoặc AIDA",
        "engage":  "Star-Story hoặc AIDA",
        "convert": "FAB hoặc PAS",
    }.get(pillar.lower().strip(), "PAS")

    # Fetch Brand Voice if available — inject so the sample reflects approved tone
    bv_block = ""
    try:
        from storage import get_brand_voice as _get_bv
        bv = await _get_bv(session.user_id)
        if bv and not bv.is_empty():
            bv_block = bv.to_prompt_block(max_chars=600)
    except Exception:
        pass

    user_msg = f"""**Thông tin bài cần viết (từ Content Calendar):**
- Kênh: {channel}
- Pillar: {pillar} | Funnel: {funnel}
- Topic: {topic}
- Hook angle: {hook_angle}
- Framework gợi ý: {framework_hint}

**Business Profile:**
- Ngành: {profile.industry or 'chưa rõ'}
- Sản phẩm/dịch vụ: {profile.product_service or 'chưa rõ'}
- Khách hàng: {profile.target_customer or 'chưa rõ'}
- Địa bàn: {profile.location or 'Việt Nam'}
{f"{chr(10)}**Brand Voice (TUÂN THỦ TUYỆT ĐỐI):**{chr(10)}{bv_block}" if bv_block else ""}
Viết bài {channel} hoàn chỉnh theo thông tin trên."""

    try:
        resp = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=800,
            system=_SAMPLE_POST_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("generate_sample_post failed: %s", e)
        return f"[Topic: {topic}]\n[Hook angle: {hook_angle}]\n\n_(Em không gen được bài mẫu — sếp check tone dựa trên kế hoạch trên nhé.)_"




_EXTRACT_TONE_SYSTEM = """Bạn là chuyên gia phân tích Brand Voice.
User vừa đọc bài content và cho feedback về tone.

NHIỆM VỤ: Extract "tone signals" từ feedback để dùng làm style guide cho toàn bộ calendar.

Trả về JSON:
{
  "tone_words": ["list 3-5 từ mô tả tone mong muốn, vd: thân thiện, chuyên nghiệp, hài hước"],
  "do_adjust": ["điều chỉnh CẦN làm, vd: viết câu ngắn hơn, dùng emoji vừa phải"],
  "dont_repeat": ["lỗi cần tránh lặp lại từ bài cũ"],
  "sample_phrase": "1 câu mẫu thể hiện đúng tone mong muốn (nếu user có gợi ý)"
}

Chỉ trả về JSON, không giải thích thêm."""


async def extract_tone_signals(
    session,
    user_feedback: str,
    post_content: str,
) -> dict:
    """
    Dùng AI extract tone signals từ user feedback + post content.
    Returns dict signals, hoặc minimal fallback nếu fail.
    """
    client = _get_client()

    user_msg = f"""**Bài content vừa gen:**
{post_content[:600]}

**Feedback của user:**
{user_feedback}

**Business context:**
Ngành: {getattr(session.profile, 'industry', 'chưa rõ')}
Tone hiện tại: {getattr(session.profile, 'usp', '')}
"""

    try:
        resp = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=500,
            system=_EXTRACT_TONE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        # Parse JSON
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        logger.warning("extract_tone_signals failed: %s", e)

    # Fallback: minimal signals from feedback text
    return {
        "tone_words": [],
        "do_adjust": [user_feedback[:200]],
        "dont_repeat": [],
        "sample_phrase": "",
    }


# ─── Regen post 1 with tone signals ───────────────────────────────────────────

_REGEN_POST_SYSTEM = """Bạn là Content Writer chuyên nghiệp.
Viết lại bài content theo đúng tone signals được cung cấp.
Giữ nguyên chủ đề, thông điệp core. Chỉ thay đổi phong cách.
Trả về bài content đã viết lại, không cần giải thích."""


async def regen_post_with_signals(
    session,
    original_post: str,
    signals: dict,
) -> str:
    """Viết lại Post 1 theo tone signals. Returns new post text."""
    client = _get_client()

    tone_guide = []
    if signals.get("tone_words"):
        tone_guide.append(f"Tone: {', '.join(signals['tone_words'])}")
    if signals.get("do_adjust"):
        tone_guide.append("Cần làm: " + "; ".join(signals["do_adjust"]))
    if signals.get("dont_repeat"):
        tone_guide.append("Tránh: " + "; ".join(signals["dont_repeat"]))
    if signals.get("sample_phrase"):
        tone_guide.append(f"Câu mẫu: {signals['sample_phrase']}")

    user_msg = f"""**Bài gốc cần viết lại:**
{original_post}

**Tone signals (TUÂN THỦ TUYỆT ĐỐI):**
{chr(10).join(tone_guide)}

**Business:**
{session.profile.to_context_string()[:400]}

Viết lại bài theo đúng tone signals trên."""

    try:
        resp = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=1000,
            system=_REGEN_POST_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("regen_post_with_signals failed: %s", e)
        return original_post  # Fallback: return original


# ─── Apply tone signals to full calendar ──────────────────────────────────────

_APPLY_TONE_SYSTEM = """Bạn là Content Director review toàn bộ content calendar.

Đã lock tone signals từ Post 1. Áp dụng đồng nhất cho TẤT CẢ bài còn lại.

KHÔNG thay đổi:
- Chủ đề từng bài
- Ngày đăng / kênh
- CTA core
- Số lượng bài

CHỈ điều chỉnh:
- Phong cách viết (tone, từ ngữ, cấu trúc câu)
- Mức độ emoji
- Voice consistency

Giữ nguyên format structure của calendar gốc."""


async def apply_tone_to_calendar(
    session,
    calendar_text: str,
    signals: dict,
    approved_post1: str,
) -> str:
    """
    Áp dụng locked tone signals lên full calendar.
    Returns updated calendar text.
    """
    client = _get_client()

    tone_guide = []
    if signals.get("tone_words"):
        tone_guide.append(f"Tone đã lock: {', '.join(signals['tone_words'])}")
    if signals.get("do_adjust"):
        tone_guide.append("Style rules: " + "; ".join(signals["do_adjust"]))
    if signals.get("dont_repeat"):
        tone_guide.append("Tránh: " + "; ".join(signals["dont_repeat"]))

    user_msg = f"""**Post 1 (đã approved — dùng làm mẫu tone):**
{approved_post1[:600]}

**Tone signals đã lock:**
{chr(10).join(tone_guide)}

**Full Content Calendar cần update:**
{calendar_text}

Áp dụng tone đồng nhất cho toàn bộ calendar theo mẫu Post 1."""

    try:
        resp = await client.messages.create(
            model=CLAUDE_SONNET_MODEL,
            max_tokens=8000,
            system=_APPLY_TONE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("apply_tone_to_calendar failed: %s", e)
        return calendar_text  # Fallback: return original calendar


# ─── Format signals for display ───────────────────────────────────────────────

def format_signals_card(signals: dict) -> str:
    """Format tone signals thành text card để show user."""
    lines = ["🎯 *Tone đã extract:*"]
    if signals.get("tone_words"):
        lines.append(f"• Phong cách: {', '.join(signals['tone_words'])}")
    if signals.get("do_adjust"):
        for d in signals["do_adjust"][:3]:
            lines.append(f"• ✅ {d}")
    if signals.get("dont_repeat"):
        for d in signals["dont_repeat"][:2]:
            lines.append(f"• ❌ Tránh: {d}")
    return "\n".join(lines)
