"""
Users table — top-level identity + token quota.
Soft delete pattern (deleted_at). Never hard delete.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "users"


async def get_user(user_id: int) -> Optional[dict]:
    """Fetch user record. Returns None if not exist or soft-deleted."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_user(%d) failed: %s", user_id, e)
        return None


async def upsert_user(
    user_id: int,
    name: Optional[str] = None,
    en_level: Optional[str] = None,
    token_quota: Optional[int] = None,
    plan: Optional[str] = None,
    industry_cached: Optional[str] = None,
    cost_used_usd: Optional[float] = None,
) -> Optional[dict]:
    """Upsert user. Only non-None fields are written."""
    client = get_client()
    if client is None:
        return None

    payload: dict = {
        "user_id": user_id,
        "last_active_at": datetime.now(timezone.utc).isoformat(),
    }
    if name is not None:            payload["name"] = name
    if en_level is not None:        payload["en_level"] = en_level
    if token_quota is not None:     payload["token_quota"] = token_quota
    if plan is not None:            payload["plan"] = plan
    if industry_cached is not None: payload["industry_cached"] = industry_cached
    if cost_used_usd is not None:   payload["cost_used_usd"] = cost_used_usd

    try:
        resp = await client.table(TABLE).upsert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("upsert_user(%d) failed: %s", user_id, e)
        return None


async def soft_delete_user(user_id: int) -> bool:
    """Soft delete — set deleted_at. Top-level users không hard delete."""
    client = get_client()
    if client is None:
        return False
    try:
        await (
            client.table(TABLE)
            .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
            .eq("user_id", user_id)
            .execute()
        )
        return True
    except Exception as e:
        logger.warning("soft_delete_user(%d) failed: %s", user_id, e)
        return False


async def clear_industry_cached(user_id: int) -> bool:
    """Reset industry_cached về NULL (dùng cho /reset — giữ row users + quota)."""
    client = get_client()
    if client is None:
        return False
    try:
        await (
            client.table(TABLE)
            .update({"industry_cached": None})
            .eq("user_id", user_id)
            .execute()
        )
        return True
    except Exception as e:
        logger.warning("clear_industry_cached(%d) failed: %s", user_id, e)
        return False


async def add_token_usage(user_id: int, tokens: int) -> Optional[int]:
    """Increment token_used atomically via PostgREST RPC or read-modify-write.

    Returns new token_used count, or None on failure.
    """
    client = get_client()
    if client is None:
        return None
    try:
        # Read current
        user = await get_user(user_id)
        if not user:
            return None
        new_used = (user.get("token_used") or 0) + tokens
        await (
            client.table(TABLE)
            .update({"token_used": new_used})
            .eq("user_id", user_id)
            .execute()
        )
        return new_used
    except Exception as e:
        logger.warning("add_token_usage(%d, %d) failed: %s", user_id, tokens, e)
        return None


async def set_token_quota(user_id: int, quota: int) -> bool:
    """Admin command: set quota cố định."""
    client = get_client()
    if client is None:
        return False
    try:
        # Đảm bảo user tồn tại trước
        await upsert_user(user_id=user_id)
        await (
            client.table(TABLE)
            .update({"token_quota": quota})
            .eq("user_id", user_id)
            .execute()
        )
        return True
    except Exception as e:
        logger.warning("set_token_quota(%d, %d) failed: %s", user_id, quota, e)
        return False


async def reset_token_usage(user_id: int) -> bool:
    """Admin command: reset token_used về 0."""
    client = get_client()
    if client is None:
        return False
    try:
        await (
            client.table(TABLE)
            .update({"token_used": 0})
            .eq("user_id", user_id)
            .execute()
        )
        return True
    except Exception as e:
        logger.warning("reset_token_usage(%d) failed: %s", user_id, e)
        return False
