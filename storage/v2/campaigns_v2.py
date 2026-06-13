"""
campaigns — proper entity (deprecate user_campaign_history JSONB).

Linked to skill_runs (brief, calendar) qua FK.
Embedding vector cho semantic search (Sprint 8).
"""
import logging
from typing import Optional

from storage.v2._client import get_client

logger = logging.getLogger(__name__)
TABLE = "campaigns"


async def create_campaign(
    user_id: int,
    name: Optional[str] = None,
    industry: Optional[str] = None,
    primary_goal: Optional[str] = None,
    offer_lever: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    summary: Optional[str] = None,
    embedding: Optional[list[float]] = None,
    brief_skill_run_id: Optional[str] = None,
    calendar_skill_run_id: Optional[str] = None,
) -> Optional[dict]:
    """Insert new campaign. Returns row with id."""
    client = get_client()
    if client is None:
        return None

    payload: dict = {"user_id": user_id, "status": "draft"}
    if name is not None:                  payload["name"] = name
    if industry is not None:              payload["industry"] = industry
    if primary_goal is not None:          payload["primary_goal"] = primary_goal
    if offer_lever is not None:           payload["offer_lever"] = offer_lever
    if start_date is not None:            payload["start_date"] = start_date
    if end_date is not None:              payload["end_date"] = end_date
    if summary is not None:               payload["summary"] = summary
    if embedding is not None:             payload["embedding"] = embedding
    if brief_skill_run_id is not None:    payload["brief_skill_run_id"] = brief_skill_run_id
    if calendar_skill_run_id is not None: payload["calendar_skill_run_id"] = calendar_skill_run_id

    try:
        resp = await client.table(TABLE).insert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("create_campaign(%d) failed: %s", user_id, e)
        return None


async def get_campaign(campaign_id: str) -> Optional[dict]:
    client = get_client()
    if client is None:
        return None
    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("id", campaign_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_campaign(%s) failed: %s", campaign_id, e)
        return None


async def list_campaigns_v2(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    client = get_client()
    if client is None:
        return []
    try:
        q = client.table(TABLE).select("*").eq("user_id", user_id)
        if status:
            q = q.eq("status", status)
        resp = await q.order("created_at", desc=True).limit(limit).execute()
        return resp.data or []
    except Exception as e:
        logger.warning("list_campaigns_v2(%d) failed: %s", user_id, e)
        return []


async def update_campaign_embedding(
    campaign_id: str,
    embedding: list[float],
    summary: Optional[str] = None,
) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        payload = {"embedding": embedding}
        if summary:
            payload["summary"] = summary
        await client.table(TABLE).update(payload).eq("id", campaign_id).execute()
        return True
    except Exception as e:
        logger.warning("update_campaign_embedding(%s) failed: %s", campaign_id, e)
        return False
