"""
diagnostic_briefs — output McKinsey Discovery.

Lưu structured object (facts/hypotheses/gaps/sources) thay vì văn xuôi,
kèm provenance (grounded vs Claude-knowledge fallback) để minh bạch nguồn.
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "diagnostic_briefs"


async def insert_brief(
    engagement_id: str,
    user_id: int,
    facts: Optional[list] = None,
    hypotheses: Optional[list] = None,
    gaps: Optional[list] = None,
    sources: Optional[list] = None,
    grounded: bool = False,
    confidence_note: Optional[str] = None,
    content: Optional[str] = None,
    model_used: Optional[str] = None,
    tokens_used: Optional[int] = None,
) -> Optional[dict]:
    """Insert diagnostic brief. Caller nên update engagement.brief_id sau đó."""
    client = get_client()
    if client is None:
        return None

    payload = {
        "engagement_id":   engagement_id,
        "user_id":         user_id,
        "facts":           facts or [],
        "hypotheses":      hypotheses or [],
        "gaps":            gaps or [],
        "sources":         sources or [],
        "grounded":        grounded,
        "confidence_note": confidence_note,
        "content":         content,
        "model_used":      model_used,
        "tokens_used":     tokens_used,
    }
    try:
        resp = await client.table(TABLE).insert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("insert_brief(eng=%s) failed: %s", engagement_id, e)
        return None


async def get_brief(brief_id: str) -> Optional[dict]:
    """Fetch 1 brief theo id."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("id", brief_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_brief(%s) failed: %s", brief_id, e)
        return None


async def get_latest_brief(engagement_id: str) -> Optional[dict]:
    """Brief mới nhất của 1 engagement."""
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("engagement_id", engagement_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_latest_brief(%s) failed: %s", engagement_id, e)
        return None
