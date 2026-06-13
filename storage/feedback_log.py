"""
CRUD helpers cho table feedback_log.
Lưu mọi rating + feedback của user theo skill + industry → admin review.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from storage.session import _client

logger = logging.getLogger(__name__)

FEEDBACK_TABLE = "feedback_log"


async def log_feedback(
    user_id: int,
    skill_name: str,
    rating: int,
    feedback_text: str = "",
    industry: str = "",
    stage: str = "",
    business_name: str = "",
    output_excerpt: str = "",
    user_correction: str = "",
) -> bool:
    """Insert 1 feedback entry. Non-blocking — log warning nếu fail."""
    if not _client:
        logger.warning("Supabase client chưa init, skip feedback log")
        return False
    if rating < 1 or rating > 5:
        return False
    try:
        payload = {
            "user_id": user_id,
            "skill_name": skill_name,
            "rating": rating,
            "feedback_text": (feedback_text or "")[:2000],
            "industry": (industry or "")[:50],
            "stage": (stage or "")[:50],
            "business_name": (business_name or "")[:200],
            "output_excerpt": (output_excerpt or "")[:500],
            "user_correction": (user_correction or "")[:2000],
        }
        await _client.table(FEEDBACK_TABLE).insert(payload).execute()
        return True
    except Exception as e:
        logger.warning("log_feedback failed (non-blocking): %s", e)
        return False


async def get_recent_feedback(
    since_days: int = 2,
    rating_max: Optional[int] = None,
) -> list[dict]:
    """Lấy feedback trong N ngày gần nhất. Dùng cho digest.

    Args:
        since_days: số ngày từ hiện tại
        rating_max: chỉ lấy rating ≤ N (vd: rating_max=3 → chỉ feedback xấu)
    """
    if not _client:
        return []
    try:
        since = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
        query = _client.table(FEEDBACK_TABLE).select("*").gte("created_at", since)
        if rating_max is not None:
            query = query.lte("rating", rating_max)
        resp = await query.order("created_at", desc=True).execute()
        return resp.data or []
    except Exception as e:
        logger.warning("get_recent_feedback failed: %s", e)
        return []


async def get_digest_summary(since_days: int = 2) -> dict:
    """Build summary dict cho digest:
    - total_count, avg_rating
    - by_skill: {skill_name: {count, avg_rating, low_rating_count}}
    - by_industry: {industry: {count, avg_rating}}
    - top_complaints: top 5 feedback_text với rating ≤ 3
    """
    rows = await get_recent_feedback(since_days=since_days)
    if not rows:
        return {"total_count": 0, "summary": "Không có feedback nào trong period."}

    by_skill: dict[str, dict] = {}
    by_industry: dict[str, dict] = {}
    low_rating_examples = []

    for r in rows:
        skill = r.get("skill_name", "unknown")
        rating = r.get("rating", 0)
        industry = r.get("industry") or "unknown"
        feedback_text = r.get("feedback_text") or r.get("user_correction", "")

        # By skill
        s = by_skill.setdefault(skill, {"count": 0, "sum_rating": 0, "low_count": 0})
        s["count"] += 1
        s["sum_rating"] += rating
        if rating <= 3:
            s["low_count"] += 1

        # By industry
        ind = by_industry.setdefault(industry, {"count": 0, "sum_rating": 0})
        ind["count"] += 1
        ind["sum_rating"] += rating

        # Top complaints
        if rating <= 3 and feedback_text:
            low_rating_examples.append({
                "skill": skill,
                "industry": industry,
                "rating": rating,
                "feedback": feedback_text[:200],
            })

    # Calculate averages
    for s in by_skill.values():
        s["avg_rating"] = round(s["sum_rating"] / s["count"], 2) if s["count"] else 0
        s.pop("sum_rating", None)
    for ind in by_industry.values():
        ind["avg_rating"] = round(ind["sum_rating"] / ind["count"], 2) if ind["count"] else 0
        ind.pop("sum_rating", None)

    total = len(rows)
    avg = round(sum(r.get("rating", 0) for r in rows) / total, 2)

    return {
        "total_count": total,
        "avg_rating": avg,
        "period_days": since_days,
        "by_skill": dict(sorted(by_skill.items(), key=lambda x: -x[1]["count"])),
        "by_industry": dict(sorted(by_industry.items(), key=lambda x: -x[1]["count"])),
        "top_complaints": low_rating_examples[:10],
    }
