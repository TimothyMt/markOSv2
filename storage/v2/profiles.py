"""
user_business_profile — 1:1 với users.
Queryable profile fields, replace JSONB profile trong sessions.
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "user_business_profile"

# Whitelist của fields được phép upsert (security + schema enforce)
_VALID_FIELDS = {
    "business_name", "industry", "stage", "product_service", "target_customer",
    "monthly_revenue", "team_size", "monthly_marketing_budget", "primary_goal",
    "current_channels", "main_challenge", "competitors", "location",
    "usp", "usp_confidence",
}


async def get_profile(user_id: int) -> Optional[dict]:
    """Fetch business profile. Returns None nếu chưa có."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_profile(%d) failed: %s", user_id, e)
        return None


async def delete_profile(user_id: int) -> bool:
    """Xoá hẳn business profile của user (dùng cho /reset)."""
    client = get_client()
    if client is None:
        return False
    try:
        await client.table(TABLE).delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("delete_profile(%d) failed: %s", user_id, e)
        return False


async def upsert_profile(user_id: int, **fields) -> Optional[dict]:
    """
    Upsert profile fields. Chỉ accept whitelist fields.

    Note: cần users record tồn tại trước (FK constraint).
    """
    client = get_client()
    if client is None:
        return None

    # Filter chỉ valid fields
    clean = {k: v for k, v in fields.items() if k in _VALID_FIELDS}
    if not clean:
        return None

    clean["user_id"] = user_id

    try:
        resp = await client.table(TABLE).upsert(clean).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("upsert_profile(%d) failed: %s", user_id, e)
        return None
