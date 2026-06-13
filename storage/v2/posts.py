"""
posts — POST-XXX as proper table.

PK = post_id ('POST-001', 'POST-001-TT', 'POST-001-V1').
parent_post_id linkage cho adapt/variant tracking.
Soft delete via status='deleted'.
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "posts"


async def insert_post(
    post_id: str,
    user_id: int,
    content: str,
    campaign_id: Optional[str] = None,
    week: Optional[int] = None,
    day: Optional[str] = None,
    channel: Optional[str] = None,
    pillar: Optional[str] = None,
    funnel: Optional[str] = None,
    status: str = "draft",
    parent_post_id: Optional[str] = None,
    adapt_type: Optional[str] = None,
) -> Optional[dict]:
    """Insert new post. Returns row or None on conflict/error."""
    client = get_client()
    if client is None:
        return None

    payload = {
        "post_id":        post_id,
        "user_id":        user_id,
        "content":        content,
        "campaign_id":    campaign_id,
        "week":           week,
        "day":            day,
        "channel":        channel,
        "pillar":         pillar,
        "funnel":         funnel,
        "status":         status,
        "parent_post_id": parent_post_id,
        "adapt_type":     adapt_type,
    }
    try:
        resp = await client.table(TABLE).upsert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("insert_post(%s) failed: %s", post_id, e)
        return None


async def get_post(post_id: str) -> Optional[dict]:
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("post_id", post_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_post(%s) failed: %s", post_id, e)
        return None


async def update_post(
    post_id: str,
    content: Optional[str] = None,
    status: Optional[str] = None,
) -> bool:
    client = get_client()
    if client is None:
        return False
    payload: dict = {}
    if content is not None: payload["content"] = content
    if status is not None:  payload["status"] = status
    if not payload:
        return False
    try:
        await client.table(TABLE).update(payload).eq("post_id", post_id).execute()
        return True
    except Exception as e:
        logger.warning("update_post(%s) failed: %s", post_id, e)
        return False


async def list_posts_by_campaign(campaign_id: str) -> list[dict]:
    """Sorted by week, day."""
    client = get_client()
    if client is None:
        return []
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("campaign_id", campaign_id)
            .neq("status", "deleted")
            .order("week")
            .order("day")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_posts_by_campaign(%s) failed: %s", campaign_id, e)
        return []


async def list_posts_by_user(
    user_id: int,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List user's posts, optionally filtered by channel/status."""
    client = get_client()
    if client is None:
        return []
    try:
        q = client.table(TABLE).select("*").eq("user_id", user_id)
        if channel:
            q = q.eq("channel", channel)
        if status:
            q = q.eq("status", status)
        else:
            q = q.neq("status", "deleted")
        resp = await q.order("created_at", desc=True).limit(limit).execute()
        return resp.data or []
    except Exception as e:
        logger.warning("list_posts_by_user(%d) failed: %s", user_id, e)
        return []


async def soft_delete_post(post_id: str) -> bool:
    return await update_post(post_id, status="deleted")
