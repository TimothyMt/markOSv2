"""
user_sessions_slim — HOT state only.

Chỉ giữ: stage, selected_task, pending_intake (small), intake_history, tone_calibration.
KHÔNG còn: profile (→ profiles), results (→ skill_runs), preferences (→ users).

Đọc/ghi liên tục mỗi message → phải nhỏ và nhanh.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "user_sessions_slim"

# Sentinel — phân biệt "không truyền vào" vs "truyền None để xoá"
_UNSET = object()


async def get_session_slim(user_id: int) -> dict:
    """
    Fetch slim session. Returns default empty session dict nếu chưa có.
    """
    client = get_client()
    if client is None:
        return _default_session(user_id)
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return _default_session(user_id)
    except Exception as e:
        logger.warning("get_session_slim(%d) failed: %s", user_id, e)
        return _default_session(user_id)


def _default_session(user_id: int) -> dict:
    return {
        "user_id":                user_id,
        "stage":                  "idle",
        "selected_task":          None,
        "pending_followup_skill": None,
        "pending_intake":         {},
        "intake_history":         [],
        "tone_calibration":       {},
        "token_log":              [],
        "content_outputs":        {},
    }


async def upsert_session_slim(
    user_id: int,
    stage: Optional[str] = None,
    selected_task=_UNSET,           # None = clear, _UNSET = don't touch
    pending_followup_skill=_UNSET,  # None = clear, _UNSET = don't touch
    pending_intake: Optional[dict] = None,
    intake_history: Optional[list] = None,
    tone_calibration: Optional[dict] = None,
    token_log: Optional[list] = None,
    content_outputs: Optional[dict] = None,
    touch_last_msg: bool = True,
) -> bool:
    """Upsert session fields. Only non-_UNSET / non-None fields written."""
    client = get_client()
    if client is None:
        return False

    payload: dict = {"user_id": user_id}
    if stage is not None:                            payload["stage"] = stage
    if selected_task is not _UNSET:                  payload["selected_task"] = selected_task
    if pending_followup_skill is not _UNSET:         payload["pending_followup_skill"] = pending_followup_skill
    if pending_intake is not None:                   payload["pending_intake"] = pending_intake
    if intake_history is not None:                   payload["intake_history"] = intake_history
    if tone_calibration is not None:                 payload["tone_calibration"] = tone_calibration
    if token_log is not None:                        payload["token_log"] = token_log
    if content_outputs is not None:                  payload["content_outputs"] = content_outputs
    if touch_last_msg:
        payload["last_message_at"] = datetime.now(timezone.utc).isoformat()

    try:
        await client.table(TABLE).upsert(payload).execute()
        return True
    except Exception as e:
        logger.warning("upsert_session_slim(%d) failed: %s", user_id, e)
        return False


async def delete_session_slim(user_id: int) -> bool:
    """Xoá hẳn slim session của user (dùng cho /reset)."""
    client = get_client()
    if client is None:
        return False
    try:
        await client.table(TABLE).delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("delete_session_slim(%d) failed: %s", user_id, e)
        return False


async def touch_last_message(user_id: int) -> bool:
    """Lightweight update — chỉ cập nhật last_message_at để tránh stale-reset."""
    client = get_client()
    if client is None:
        return False
    try:
        await (
            client.table(TABLE)
            .update({"last_message_at": datetime.now(timezone.utc).isoformat()})
            .eq("user_id", user_id)
            .execute()
        )
        return True
    except Exception:
        return False
