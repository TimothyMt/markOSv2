"""
CRUD helpers cho table tracked_competitors.
Lưu trữ các đối thủ user đang theo dõi tự động qua FB Ads Library.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from storage.session import _client, TABLE as _SESSIONS_TABLE  # reuse client

logger = logging.getLogger(__name__)

TRACKED_TABLE = "tracked_competitors"


async def add_tracked(
    user_id: int,
    page_id: str,
    page_name: str,
    interval_hours: int,
    ad_ids: list[str],
) -> bool:
    """Insert hoặc update tracking entry. Returns True nếu thành công."""
    if not _client:
        logger.error("Supabase client chưa init")
        return False
    payload = {
        "user_id": user_id,
        "page_id": page_id,
        "page_name": page_name or "",
        "interval_hours": interval_hours,
        "last_check_at": datetime.utcnow().isoformat(),
        "last_ad_ids": ad_ids or [],
        "is_active": True,
    }
    try:
        await _client.table(TRACKED_TABLE).upsert(payload, on_conflict="user_id,page_id").execute()
        return True
    except Exception as e:
        logger.exception("add_tracked failed: %s", e)
        return False


async def remove_tracked(user_id: int, page_id: str) -> bool:
    """Soft-disable tracking (giữ history)."""
    if not _client:
        return False
    try:
        await _client.table(TRACKED_TABLE).update(
            {"is_active": False}
        ).eq("user_id", user_id).eq("page_id", page_id).execute()
        return True
    except Exception as e:
        logger.exception("remove_tracked failed: %s", e)
        return False


async def list_tracked_by_user(user_id: int) -> list[dict]:
    """Lấy danh sách competitors đang track của 1 user."""
    if not _client:
        return []
    try:
        resp = (
            await _client.table(TRACKED_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.exception("list_tracked_by_user failed: %s", e)
        return []


async def get_due_tracked() -> list[dict]:
    """Lấy danh sách entries cần check (theo interval_hours).
    Cron job dùng hàm này mỗi giờ để biết entry nào tới hạn.
    """
    if not _client:
        return []
    try:
        resp = (
            await _client.table(TRACKED_TABLE)
            .select("*")
            .eq("is_active", True)
            .execute()
        )
        all_active = resp.data or []
        now = datetime.utcnow()
        due = []
        for entry in all_active:
            last_check_str = entry.get("last_check_at", "")
            interval = entry.get("interval_hours", 24)
            try:
                last_check = datetime.fromisoformat(last_check_str.replace("Z", "+00:00"))
                last_check = last_check.replace(tzinfo=None)
            except Exception:
                last_check = now
            hours_elapsed = (now - last_check).total_seconds() / 3600
            if hours_elapsed >= interval:
                due.append(entry)
        return due
    except Exception as e:
        logger.exception("get_due_tracked failed: %s", e)
        return []


async def update_after_check(
    tracked_id: int,
    new_ad_ids: list[str],
) -> bool:
    """Sau khi check xong, update last_check_at + last_ad_ids."""
    if not _client:
        return False
    try:
        await _client.table(TRACKED_TABLE).update({
            "last_check_at": datetime.utcnow().isoformat(),
            "last_ad_ids": new_ad_ids,
        }).eq("id", tracked_id).execute()
        return True
    except Exception as e:
        logger.exception("update_after_check failed: %s", e)
        return False
