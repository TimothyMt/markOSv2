"""
Campaign History — per-user persistent storage với vector semantic search.
Sprint 8 — Semantic Search.

Auto-saved sau khi pipeline A→Z hoàn thành (synthesis present).
User có thể dùng /history để xem + search campaigns cũ.

Graceful degradation: mọi DB error đều return None/[] — không block bot.
"""
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from storage.models import Session

logger = logging.getLogger(__name__)
TABLE = "user_campaign_history"

# Giới hạn text dài để tránh bloat storage
_MAX_SKILL_CHARS = 3000


def _get_client():
    """Lazy import Supabase client từ session module."""
    from storage import session as _session_mod
    return _session_mod._client


def _truncate(text: Optional[str], max_chars: int = _MAX_SKILL_CHARS) -> Optional[str]:
    if not text:
        return None
    return text[:max_chars] if len(text) > max_chars else text


def _build_summary(session: "Session") -> str:
    """
    Build searchable summary text từ session để embed + hiển thị /history.
    Kết hợp business context + synthesis excerpt.
    """
    p = session.profile
    parts = []

    if p.business_name:
        parts.append(f"Business: {p.business_name}")
    if p.industry:
        parts.append(f"Ngành: {p.industry}")
    if p.stage:
        parts.append(f"Stage: {p.stage}")
    if p.primary_goal:
        parts.append(f"Mục tiêu: {p.primary_goal}")
    if p.product_service:
        parts.append(f"Sản phẩm: {p.product_service}")
    if p.target_customer:
        parts.append(f"Khách hàng: {p.target_customer}")
    if p.usp:
        parts.append(f"USP: {p.usp}")
    if p.main_challenge:
        parts.append(f"Thách thức: {p.main_challenge}")

    # Thêm synthesis excerpt vào summary để embedding phong phú hơn
    synthesis = session.get_latest_result("synthesis")
    if synthesis:
        parts.append(synthesis[:600])

    return ". ".join(parts)


async def save_campaign_history(session: "Session") -> Optional[dict]:
    """
    Persist pipeline run vào campaign history.
    Chỉ save khi có synthesis result (đã chạy A→Z hoặc strategy).
    Gọi non-blocking sau khi pipeline COMPLETE.
    Returns saved row dict hoặc None nếu skip/fail.
    """
    if not session.has_result("synthesis"):
        return None  # Skip nếu chưa chạy synthesis

    client = _get_client()
    if client is None:
        return None

    summary = _build_summary(session)
    if not summary.strip():
        return None

    # Generate embedding (non-blocking, graceful if OpenAI unavailable)
    from storage.embeddings import embed_text
    embedding = await embed_text(summary)

    p = session.profile
    payload: dict = {
        "user_id":          session.user_id,
        "business_name":    p.business_name,
        "industry":         p.industry,
        "stage":            p.stage,
        "primary_goal":     p.primary_goal,
        "usp":              p.usp,
        "summary":          summary,
        "market_research":  _truncate(session.get_latest_result("market_research")),
        "competitor":       _truncate(session.get_latest_result("competitor")),
        "customer_insight": _truncate(session.get_latest_result("customer_insight")),
        "synthesis":        _truncate(session.get_latest_result("synthesis")),
        "campaign_brief":   _truncate(session.get_latest_result("campaign_brief")),
    }

    # Supabase pgvector nhận list[float] trực tiếp
    if embedding:
        payload["embedding"] = embedding

    try:
        ins = await client.table(TABLE).insert(payload).execute()
        if ins.data:
            logger.info(
                "campaign_history saved (user=%d, id=%s)",
                session.user_id, ins.data[0].get("id")
            )
            return ins.data[0]
        return None
    except Exception as e:
        logger.warning("save_campaign_history failed (user=%d): %s", session.user_id, e)
        return None


async def search_similar_campaigns(
    user_id: int,
    query_text: str,
    top_k: int = 3,
) -> list[dict]:
    """
    Semantic search — top_k campaigns gần nhất với query_text.
    Fallback về recency sort nếu OpenAI embedding không available.
    """
    client = _get_client()
    if client is None:
        return []

    from storage.embeddings import embed_text
    embedding = await embed_text(query_text)

    try:
        if embedding:
            # Gọi Postgres function match_campaign_history (migration 005)
            resp = await client.rpc(
                "match_campaign_history",
                {
                    "query_embedding": embedding,
                    "match_user_id":   user_id,
                    "match_count":     top_k,
                },
            ).execute()
        else:
            # Fallback: recency sort
            resp = (
                await client.table(TABLE)
                .select("id,business_name,industry,primary_goal,summary,created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(top_k)
                .execute()
            )
        return resp.data or []
    except Exception as e:
        logger.warning("search_similar_campaigns failed (user=%d): %s", user_id, e)
        return []


async def list_campaigns(user_id: int, limit: int = 10) -> list[dict]:
    """
    Liệt kê campaigns gần đây của user theo thứ tự created_at DESC.
    Dùng cho /history command.
    """
    client = _get_client()
    if client is None:
        return []

    try:
        resp = (
            await client.table(TABLE)
            .select("id,business_name,industry,primary_goal,summary,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_campaigns failed (user=%d): %s", user_id, e)
        return []
