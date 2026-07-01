"""
Brand Voice persistent CRUD — Sprint 5.

Stores per-user BrandVoice in `user_brand_voice` table (Supabase REST/HTTPS).
Graceful degradation: nếu table không tồn tại / DB lỗi → return None,
KHÔNG block flow. Ops skills sẽ skip BV injection.
"""
import logging
from typing import Optional

from storage.models import BrandVoice

logger = logging.getLogger(__name__)

TABLE = "user_brand_voice"


def _get_client():
    """Lazy import client từ session module (đã init pool tại startup)."""
    from storage import session as _session_mod
    return _session_mod._client


def _row_to_bv(row: dict) -> BrandVoice:
    """Map Supabase row → BrandVoice dataclass."""
    return BrandVoice(
        user_id=int(row["user_id"]),
        id=row.get("id"),
        version=int(row.get("version", 1)),
        do_rules=row.get("do_rules") or [],
        dont_rules=row.get("dont_rules") or [],
        tone_descriptors=row.get("tone_descriptors") or [],
        banned_words=row.get("banned_words") or [],
        preferred_words=row.get("preferred_words") or [],
        sample_content=row.get("sample_content"),
        rules_markdown=row.get("rules_markdown"),
        industry_context=row.get("industry_context"),
        is_active=bool(row.get("is_active", True)),
        created_at=str(row.get("created_at") or "") or None,
        updated_at=str(row.get("updated_at") or "") or None,
    )


async def get_brand_voice(user_id: int) -> Optional[BrandVoice]:
    """Lấy BV active của user. Returns None nếu chưa setup hoặc DB lỗi."""
    client = _get_client()
    if client is None:
        logger.warning("get_brand_voice: client not init")
        return None

    try:
        resp = (
            await client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning("get_brand_voice DB error (user=%d): %s", user_id, e)
        return None

    if not resp.data:
        return None
    return _row_to_bv(resp.data[0])


async def save_brand_voice(bv: BrandVoice) -> Optional[BrandVoice]:
    """Upsert BV. Nếu user đã có BV active → deactivate, insert version mới.
    Returns BV sau khi save (có id + timestamps), hoặc None nếu fail.
    """
    client = _get_client()
    if client is None:
        logger.warning("save_brand_voice: client not init")
        return None

    try:
        # Bước 1: deactivate BV cũ active
        await (
            client.table(TABLE)
            .update({"is_active": False})
            .eq("user_id", bv.user_id)
            .eq("is_active", True)
            .execute()
        )

        # Bước 2: tính version mới
        try:
            last = (
                await client.table(TABLE)
                .select("version")
                .eq("user_id", bv.user_id)
                .order("version", desc=True)
                .limit(1)
                .execute()
            )
            next_version = (last.data[0]["version"] + 1) if last.data else 1
        except Exception:
            next_version = bv.version or 1

        # Bước 3: insert row mới
        payload = {
            "user_id":          bv.user_id,
            "version":          next_version,
            "do_rules":         bv.do_rules,
            "dont_rules":       bv.dont_rules,
            "tone_descriptors": bv.tone_descriptors,
            "banned_words":     bv.banned_words,
            "preferred_words":  bv.preferred_words,
            "sample_content":   bv.sample_content,
            "rules_markdown":   bv.rules_markdown,
            "industry_context": bv.industry_context,
            "is_active":        True,
        }
        ins = await client.table(TABLE).insert(payload).execute()
        if ins.data:
            return _row_to_bv(ins.data[0])
        return None
    except Exception as e:
        logger.exception("save_brand_voice failed (user=%d): %s", bv.user_id, e)
        return None


async def has_brand_voice(user_id: int) -> bool:
    """Quick check — TRUE nếu user có BV active. Dùng trong lazy trigger."""
    bv = await get_brand_voice(user_id)
    return bv is not None and not bv.is_empty()


async def deactivate_brand_voice(user_id: int) -> bool:
    """Soft delete tất cả BV của user. Returns True nếu thành công."""
    client = _get_client()
    if client is None:
        return False
    try:
        await (
            client.table(TABLE)
            .update({"is_active": False})
            .eq("user_id", user_id)
            .execute()
        )
        return True
    except Exception as e:
        logger.warning("deactivate_brand_voice DB error (user=%d): %s", user_id, e)
        return False
