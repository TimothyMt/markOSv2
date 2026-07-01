"""
skill_runs — immutable versioned skill output history.

Replace FIFO list trong session.results với proper table.
Version tự increment per (user_id, skill_name).
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "skill_runs"


async def insert_skill_run(
    user_id: int,
    skill_name: str,
    content: str,
    tokens_used: Optional[int] = None,
    model_used: Optional[str] = None,
    campaign_id: Optional[str] = None,
    parent_run_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Insert new skill run. Tự tính version tiếp theo cho (user_id, skill_name).
    Returns full row dict or None.
    """
    client = get_client()
    if client is None:
        return None

    # Tính version mới
    try:
        last = (
            await client.table(TABLE)
            .select("version")
            .eq("user_id", user_id)
            .eq("skill_name", skill_name)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        next_version = (last.data[0]["version"] + 1) if last.data else 1
    except Exception:
        next_version = 1

    payload = {
        "user_id":       user_id,
        "skill_name":    skill_name,
        "version":       next_version,
        "content":       content,
        "tokens_used":   tokens_used,
        "model_used":    model_used,
        "campaign_id":   campaign_id,
        "parent_run_id": parent_run_id,
    }
    try:
        resp = await client.table(TABLE).insert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("insert_skill_run(%d, %s) failed: %s", user_id, skill_name, e)
        return None


async def get_latest_skill_run(user_id: int, skill_name: str) -> Optional[dict]:
    """Get latest version của 1 skill cho user."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("skill_name", skill_name)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_latest_skill_run(%d, %s) failed: %s", user_id, skill_name, e)
        return None


async def list_skill_runs(
    user_id: int,
    skill_name: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """List skill runs (newest first). Filter theo skill_name nếu có."""
    client = get_client()
    if client is None:
        return []
    try:
        q = client.table(TABLE).select("*").eq("user_id", user_id)
        if skill_name:
            q = q.eq("skill_name", skill_name)
        resp = await q.order("created_at", desc=True).limit(limit).execute()
        return resp.data or []
    except Exception as e:
        logger.warning("list_skill_runs(%d) failed: %s", user_id, e)
        return []


async def delete_skill_runs(user_id: int) -> bool:
    """Xoá toàn bộ skill_runs của user (dùng cho /reset — tương đương clear results)."""
    client = get_client()
    if client is None:
        return False
    try:
        await client.table(TABLE).delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("delete_skill_runs(%d) failed: %s", user_id, e)
        return False


async def update_rating(
    run_id: str,
    rating: int,
    feedback_text: Optional[str] = None,
) -> bool:
    """Set rating + feedback cho 1 skill_run (sau khi user rate)."""
    client = get_client()
    if client is None:
        return False
    try:
        payload: dict = {"rating": rating}
        if feedback_text:
            payload["feedback_text"] = feedback_text
        await client.table(TABLE).update(payload).eq("id", run_id).execute()
        return True
    except Exception as e:
        logger.warning("update_rating(%s) failed: %s", run_id, e)
        return False
