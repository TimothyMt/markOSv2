"""
Post Actions — Sprint 7.

Xử lý per-post actions sau khi Content Calendar gen xong:
- parse_calendar_to_posts(): extract posts từ calendar text → assign POST-XXX IDs
- edit_post(): AI rewrite theo user instruction
- adapt_post(): adapt sang kênh khác (TikTok ↔ Facebook ↔ Zalo)
- gen_variant(): gen A/B variant giữ nguyên chủ đề
- delete_post(): soft delete (mark status='deleted')

Tất cả output lưu vào session.content_outputs[POST-XXX].
"""
import logging
import re
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_HAIKU_MODEL

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


# ─── Parse calendar → POST-XXX ────────────────────────────────────────────────

def parse_calendar_to_posts(calendar_text: str, campaign_id: str = "") -> dict:
    """
    Parse content calendar text → dict {POST-001: {...}, POST-002: {...}, ...}

    Nhận dạng các block post bằng pattern tuần/ngày/kênh.
    Mỗi post được gán ID tuần tự POST-001, POST-002...
    """
    posts = {}

    # Split theo các header phổ biến của content calendar
    split_patterns = [
        r"(?=\*\*(?:Tuần|Week)\s*\d)",          # **Tuần 1**, **Week 2**
        r"(?=#{1,3}\s*(?:Tuần|Week|Day|Ngày))",  # ## Tuần 1
        r"(?=\n📅|\n🗓)",                          # Emoji date marker
        r"(?=---\n)",                              # HR separator
    ]

    # Try splitting by common patterns
    blocks = None
    for pat in split_patterns:
        parts = re.split(pat, calendar_text, flags=re.IGNORECASE)
        if len(parts) > 2:
            blocks = [p.strip() for p in parts if len(p.strip()) > 80]
            break

    # Fallback: split by double newline, filter substantial blocks
    if not blocks:
        blocks = [b.strip() for b in calendar_text.split("\n\n") if len(b.strip()) > 100]

    counter = 1
    for block in blocks[:28]:  # Max 4 tuần × 7 ngày
        if not block.strip():
            continue

        post_id = f"POST-{counter:03d}"

        # Extract metadata from block
        channel = _detect_channel(block)
        week, day = _detect_week_day(block)
        pillar = _detect_pillar(block)

        posts[post_id] = {
            "campaign_id":    campaign_id,
            "week":           week,
            "day":            day,
            "channel":        channel,
            "pillar":         pillar,
            "content":        block,
            "status":         "draft",
            "adapted_versions": [],
        }
        counter += 1

    return posts


def _detect_channel(text: str) -> str:
    text_lower = text.lower()
    if "tiktok" in text_lower:
        return "tiktok"
    if "zalo" in text_lower:
        return "zalo"
    if "instagram" in text_lower or "ig" in text_lower:
        return "instagram"
    if "email" in text_lower:
        return "email"
    return "facebook"  # default


def _detect_week_day(text: str) -> tuple[int, str]:
    week_m = re.search(r"(?:Tuần|Week)\s*(\d)", text, re.IGNORECASE)
    week = int(week_m.group(1)) if week_m else 1

    day_map = {
        "thứ 2": "Mon", "monday": "Mon",
        "thứ 3": "Tue", "tuesday": "Tue",
        "thứ 4": "Wed", "wednesday": "Wed",
        "thứ 5": "Thu", "thursday": "Thu",
        "thứ 6": "Fri", "friday": "Fri",
        "thứ 7": "Sat", "saturday": "Sat",
        "chủ nhật": "Sun", "sunday": "Sun",
    }
    text_lower = text.lower()
    for key, val in day_map.items():
        if key in text_lower:
            return week, val
    return week, "Mon"


def _detect_pillar(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["educate", "giáo dục", "tips", "how to", "hướng dẫn"]):
        return "Educate"
    if any(w in text_lower for w in ["entertain", "giải trí", "hài", "viral"]):
        return "Entertain"
    if any(w in text_lower for w in ["social proof", "review", "testimonial", "khách hàng nói"]):
        return "Social Proof"
    if any(w in text_lower for w in ["cta", "offer", "khuyến mãi", "mua ngay", "đặt hàng"]):
        return "Convert"
    return "Inspire"


# ─── Edit post ────────────────────────────────────────────────────────────────

_EDIT_SYSTEM = """Bạn là Content Editor. Chỉnh sửa bài content theo đúng yêu cầu user.
Giữ nguyên: cấu trúc, chủ đề core, CTA.
Chỉ thay đổi những gì user yêu cầu.
Trả về bài đã chỉnh, không giải thích."""


async def edit_post(post_content: str, instruction: str, session) -> str:
    """Rewrite post theo instruction. Returns new content."""
    client = _get_client()
    try:
        resp = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=1000,
            system=_EDIT_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"**Bài gốc:**\n{post_content}\n\n**Yêu cầu chỉnh:**\n{instruction}"
            }],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("edit_post failed: %s", e)
        return post_content


# ─── Adapt post to another channel ────────────────────────────────────────────

_ADAPT_SYSTEM = """Bạn là Content Strategist. Adapt bài content sang kênh khác.

Rules per channel:
- TikTok: hook 3s đầu siêu mạnh, ngắn, trending sound gợi ý, CTA "Follow"
- Facebook: storytelling, 150-300 chữ, emoji vừa phải, CTA rõ ràng
- Zalo OA: thân mật, ngắn gọn, không quá 200 chữ, link đặt hàng rõ
- Instagram: visual-first, caption ngắn, hashtag 5-10 cái, IG Reels hook
- Email: subject line + body, personalization, 1 CTA button

Giữ nguyên: thông điệp core, offer, USP.
Trả về bài adapted, không giải thích."""


async def adapt_post(post_content: str, target_channel: str, session) -> str:
    """Adapt post sang target_channel. Returns adapted content."""
    client = _get_client()
    try:
        resp = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=1000,
            system=_ADAPT_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"**Bài gốc:**\n{post_content}\n\n"
                    f"**Adapt sang:** {target_channel}\n"
                    f"**Business:** {session.profile.to_context_string()[:300]}"
                )
            }],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("adapt_post failed: %s", e)
        return post_content


# ─── Gen variant (A/B test) ───────────────────────────────────────────────────

_VARIANT_SYSTEM = """Bạn là Creative Copywriter.
Viết 1 variant A/B cho bài content — giữ nguyên chủ đề + offer nhưng khác về:
- Góc tiếp cận (angle)
- Hook đầu tiên
- Tone (nếu gốc formal → variant casual, hoặc ngược lại)

Trả về chỉ bài variant, không giải thích."""


async def gen_variant(post_content: str, session) -> str:
    """Gen A/B variant. Returns variant content."""
    client = _get_client()
    try:
        resp = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=800,
            system=_VARIANT_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"**Bài gốc:**\n{post_content}\n\n**Business:**\n{session.profile.to_context_string()[:300]}"
            }],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("gen_variant failed: %s", e)
        return post_content


# ─── Format single post for display ───────────────────────────────────────────

def format_post_preview(post_id: str, post: dict, max_chars: int = 600) -> str:
    """Format 1 post để show trong Telegram với ID tag."""
    content = post.get("content", "")
    preview = content[:max_chars] + ("..." if len(content) > max_chars else "")

    meta = []
    if post.get("week"):
        meta.append(f"Tuần {post['week']}")
    if post.get("day"):
        meta.append(post["day"])
    if post.get("channel"):
        meta.append(post["channel"].capitalize())
    if post.get("pillar"):
        meta.append(post["pillar"])

    meta_str = " · ".join(meta)
    return f"📌 `{post_id}` — {meta_str}\n\n{preview}"
