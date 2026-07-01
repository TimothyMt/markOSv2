"""
strategies — output CMO (Marketing Plan).

Xương sống: positioning (SAVE) + wedge + roadmap 90 ngày (SMART) +
budget + content pillars + KPI dashboard + kill criteria (falsifiable).
Version tự increment per engagement. Execution (skill_runs) trace về đây.
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "strategies"


async def insert_strategy(
    engagement_id: str,
    user_id: int,
    brief_id: Optional[str] = None,
    positioning: Optional[dict] = None,
    wedge: Optional[dict] = None,
    roadmap_90d: Optional[list] = None,
    budget_allocation: Optional[dict] = None,
    content_pillars: Optional[list] = None,
    kpi_dashboard: Optional[list] = None,
    kill_criteria: Optional[list] = None,
    content: Optional[str] = None,
    model_used: Optional[str] = None,
    tokens_used: Optional[int] = None,
) -> Optional[dict]:
    """Insert strategy. Tự tính version tiếp theo cho engagement.

    Caller nên update engagement.strategy_id + status='strategy' sau đó.
    """
    client = get_client()
    if client is None:
        return None

    try:
        last = (
            await client.table(TABLE)
            .select("version")
            .eq("engagement_id", engagement_id)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        next_version = (last.data[0]["version"] + 1) if last.data else 1
    except Exception:
        next_version = 1

    payload = {
        "engagement_id":     engagement_id,
        "user_id":           user_id,
        "brief_id":          brief_id,
        "version":           next_version,
        "positioning":       positioning or {},
        "wedge":             wedge or {},
        "roadmap_90d":       roadmap_90d or [],
        "budget_allocation": budget_allocation or {},
        "content_pillars":   content_pillars or [],
        "kpi_dashboard":     kpi_dashboard or [],
        "kill_criteria":     kill_criteria or [],
        "content":           content,
        "model_used":        model_used,
        "tokens_used":       tokens_used,
    }
    try:
        resp = await client.table(TABLE).insert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("insert_strategy(eng=%s) failed: %s", engagement_id, e)
        return None


async def get_strategy(strategy_id: str) -> Optional[dict]:
    """Fetch 1 strategy theo id."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("id", strategy_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_strategy(%s) failed: %s", strategy_id, e)
        return None


async def get_latest_strategy(engagement_id: str) -> Optional[dict]:
    """Strategy version mới nhất của 1 engagement."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("engagement_id", engagement_id)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_latest_strategy(%s) failed: %s", engagement_id, e)
        return None


async def update_rating(
    strategy_id: str,
    rating: int,
    feedback_text: Optional[str] = None,
) -> bool:
    """Set rating + feedback cho 1 strategy."""
    client = get_client()
    if client is None:
        return False
    try:
        payload: dict = {"rating": rating}
        if feedback_text:
            payload["feedback_text"] = feedback_text
        await client.table(TABLE).update(payload).eq("id", strategy_id).execute()
        return True
    except Exception as e:
        logger.warning("update_rating(%s) failed: %s", strategy_id, e)
        return False
