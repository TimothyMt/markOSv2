"""
engagements — trục xương sống Discovery → Strategy → Execution.

Mỗi engagement giữ snapshot discovery_input + con trỏ tới brief/strategy
mới nhất. Hybrid shortcut: get_latest_with_strategy() để nhảy thẳng vào
Execution nếu user đã có Strategy.
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "engagements"

# Vòng đời hợp lệ
VALID_STATUS = {"discovery", "brief", "strategy", "execution", "complete", "archived"}


async def create_engagement(
    user_id: int,
    discovery_input: Optional[dict] = None,
    title: Optional[str] = None,
) -> Optional[dict]:
    """Tạo engagement mới ở stage 'discovery'. Returns row dict hoặc None."""
    client = get_client()
    if client is None:
        return None

    payload = {
        "user_id":         user_id,
        "status":          "discovery",
        "discovery_input": discovery_input or {},
        "title":           title,
    }
    try:
        resp = await client.table(TABLE).insert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("create_engagement(%d) failed: %s", user_id, e)
        return None


async def get_engagement(engagement_id: str) -> Optional[dict]:
    """Fetch 1 engagement theo id."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("id", engagement_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_engagement(%s) failed: %s", engagement_id, e)
        return None


async def get_active_engagement(user_id: int) -> Optional[dict]:
    """Engagement đang chạy gần nhất (chưa complete/archived) của user."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .not_.in_("status", ["complete", "archived"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_active_engagement(%d) failed: %s", user_id, e)
        return None


async def get_latest_with_strategy(user_id: int) -> Optional[dict]:
    """Engagement gần nhất CÓ strategy — dùng cho Hybrid shortcut.

    Nếu trả về row → cho phép user nhảy thẳng vào EXECUTION_MENU.
    """
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .not_.is_("strategy_id", "null")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_latest_with_strategy(%d) failed: %s", user_id, e)
        return None


async def update_engagement(engagement_id: str, **fields) -> Optional[dict]:
    """Update fields cho engagement (status / brief_id / strategy_id / title / discovery_input)."""
    client = get_client()
    if client is None:
        return None

    allowed = {"status", "title", "discovery_input", "brief_id", "strategy_id"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        return None
    if "status" in clean and clean["status"] not in VALID_STATUS:
        logger.warning("update_engagement(%s) invalid status: %s", engagement_id, clean["status"])
        return None

    try:
        resp = await client.table(TABLE).update(clean).eq("id", engagement_id).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("update_engagement(%s) failed: %s", engagement_id, e)
        return None


async def list_engagements(user_id: int, limit: int = 20) -> list[dict]:
    """List engagements của user (mới nhất trước)."""
    client = get_client()
    if client is None:
        return []
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_engagements(%d) failed: %s", user_id, e)
        return []
