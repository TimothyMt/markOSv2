"""
campaign_intelligence — học ngầm để bồi đắp KPI library.

Ghi lại: ngành nào / tệp khách hàng nào thì user CẦN và KHÔNG CẦN thông tin gì
trong campaign brief. Chạy ngầm (fire-and-forget), KHÔNG thông báo cho user.

Dùng để phân tích offline → note thêm field vào frameworks/kpi_library.py.
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "campaign_intelligence"


async def log_campaign_intelligence(
    user_id: int,
    event_type: str,                       # 'brief_approved' | 'brief_edited'
    industry: Optional[str] = None,
    target_customer: Optional[str] = None,
    campaign_goal: Optional[str] = None,
    stage: Optional[str] = None,
    fields_added: Optional[list[str]] = None,
    fields_removed: Optional[list[str]] = None,
    edit_comment: Optional[str] = None,
    brief_excerpt: Optional[str] = None,
) -> bool:
    """Insert 1 dòng intelligence. Fire-and-forget — nuốt mọi lỗi, không raise.

    Trả True nếu ghi thành công, False nếu skip/lỗi (vd chưa có DB client).
    """
    client = get_client()
    if client is None:
        return False

    payload: dict = {"user_id": user_id, "event_type": event_type}
    if industry:         payload["industry"] = industry
    if target_customer:  payload["target_customer"] = target_customer
    if campaign_goal:    payload["campaign_goal"] = campaign_goal
    if stage:            payload["stage"] = stage
    if fields_added:     payload["fields_added"] = fields_added
    if fields_removed:   payload["fields_removed"] = fields_removed
    if edit_comment:     payload["edit_comment"] = edit_comment[:2000]
    if brief_excerpt:    payload["brief_excerpt"] = brief_excerpt[:500]

    try:
        await client.table(TABLE).insert(payload).execute()
        return True
    except Exception as e:
        # Ngầm — chỉ log debug, không ảnh hưởng UX
        logger.debug("log_campaign_intelligence(%d, %s) skipped: %s", user_id, event_type, e)
        return False
