"""
Async Supabase session storage via supabase-py (HTTPS/REST).
Communicates over port 443 — works on any cloud platform.
"""
import json
import logging
from typing import Optional

from supabase import AsyncClient, acreate_client

from config import SUPABASE_URL, SUPABASE_KEY
from storage.models import Session, BusinessProfile, PipelineStage, VersionedResult

logger = logging.getLogger(__name__)

_client: Optional[AsyncClient] = None
TABLE = "sessions"


async def init_pool():
    """Initialize Supabase async client. Called once at bot startup."""
    global _client
    _client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized.")


async def init_db():
    """Verify connection by pinging the sessions table."""
    try:
        await _client.table(TABLE).select("user_id").limit(1).execute()
        logger.info("Supabase sessions table reachable.")
    except Exception as e:
        logger.error(f"sessions table not found — run the setup SQL in Supabase: {e}")
        raise


def _normalize_results(raw_results: dict) -> dict[str, list[VersionedResult]]:
    """Convert stored results into VersionedResult list per skill.
    Backward-compat: if a value is a string (old schema), wrap into a single v1.
    If a value is already list[dict], convert each dict → VersionedResult.
    """
    normalized: dict[str, list[VersionedResult]] = {}
    for skill_key, value in raw_results.items():
        if isinstance(value, str):
            # Old schema: single string → wrap as v1
            normalized[skill_key] = [VersionedResult.new(value, version=1)]
        elif isinstance(value, list):
            # New schema: list of dicts
            normalized[skill_key] = [VersionedResult.from_dict(v) for v in value if isinstance(v, dict)]
        # else: skip unknown types
    return normalized


def _row_to_session(row: dict) -> Session:
    profile_data = row.get("profile") or {}
    if isinstance(profile_data, str):
        profile_data = json.loads(profile_data)

    profile = BusinessProfile(**{
        k: v for k, v in profile_data.items()
        if k in BusinessProfile.__dataclass_fields__
    })

    intake_history = row.get("intake_history") or []
    raw_results = row.get("results") or {}
    if isinstance(raw_results, str):
        raw_results = json.loads(raw_results)

    # Extract meta fields stored inside results (NOT versioned skill results)
    selected_task = raw_results.pop("_selected_task", None) or None
    pending_intake = raw_results.pop("_pending_intake", {}) or {}
    preferences = raw_results.pop("_preferences", {}) or {}
    feedback = raw_results.pop("_feedback", {}) or {}
    pending_followup_skill = raw_results.pop("_pending_followup_skill", None) or None
    # Sprint 1 — NEW meta fields
    tone_calibration = raw_results.pop("_tone_calibration", {}) or {}
    content_outputs = raw_results.pop("_content_outputs", {}) or {}
    raw_results.pop("_brand_candidates", None)  # backward-compat: drop old field

    results = _normalize_results(raw_results)

    return Session(
        user_id=row["user_id"],
        stage=PipelineStage(row.get("stage", "idle")),
        selected_task=selected_task,
        profile=profile,
        intake_history=intake_history if isinstance(intake_history, list) else json.loads(intake_history),
        results=results,
        pending_intake=pending_intake if isinstance(pending_intake, dict) else {},
        preferences=preferences if isinstance(preferences, dict) else {},
        feedback=feedback if isinstance(feedback, dict) else {},
        pending_followup_skill=pending_followup_skill,
        tone_calibration=tone_calibration if isinstance(tone_calibration, dict) else {},
        content_outputs=content_outputs if isinstance(content_outputs, dict) else {},
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )


async def get_session(user_id: int) -> Session:
    """Fetch existing session or return a fresh one.

    Dual-Write strategy:
      DB_V2_READ=True  → đọc từ v2 normalized (production hit v2)
      DB_V2_READ=False → đọc từ v1 sessions (default, an toàn)

    Nếu v2 read fail → tự động fallback v1.
    """
    try:
        from config import DB_V2_READ
    except ImportError:
        DB_V2_READ = False

    if DB_V2_READ:
        try:
            from storage.session_v2_adapter import get_session_v2
            return await get_session_v2(user_id)
        except Exception as e:
            try:
                from config import DB_V2_WRITE as _v2w
            except ImportError:
                _v2w = False
            if not _v2w:
                # Phase D (V2-only): never resurrect stale V1 data on V2 failure
                logger.error("V2-only get_session failed, returning fresh session (no V1 fallback): %s", e)
                return Session(user_id=user_id)
            logger.exception("V2 get_session failed, fallback to v1: %s", e)

    # v1 path (legacy / fallback — only reached when DB_V2_READ=False or dual-write V2 failed)
    resp = (
        await _client.table(TABLE)
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if resp.data:
        return _row_to_session(resp.data[0])
    return Session(user_id=user_id)


async def save_session(session: Session):
    """Upsert session via Supabase REST.

    Dual-Write strategy:
      DB_V2_WRITE=True → ghi cả v1 (legacy) + v2 (normalized) song song
      DB_V2_WRITE=False → chỉ ghi v1 (default, an toàn)

    V1 write LUÔN chạy (source of truth) trừ khi đã ở Phase D (WRITE=False + READ=True).
    V2 write là BEST-EFFORT — nếu fail, log warning nhưng không throw exception
    (tránh làm crash bot).
    """
    try:
        from config import DB_V2_WRITE, DB_V2_READ
    except ImportError:
        DB_V2_WRITE = False
        DB_V2_READ = False

    # Phase D logic: nếu chỉ READ=True và WRITE=False → đã cutover sang v2 only
    _v2_only = DB_V2_READ and not DB_V2_WRITE

    if _v2_only:
        # Phase D: skip v1 write hoàn toàn
        try:
            from storage.session_v2_adapter import save_session_v2
            await save_session_v2(session)
            return
        except Exception as e:
            logger.exception("V2-only save failed, NO FALLBACK in Phase D: %s", e)
            raise

    # Phase A/B/C: write to v1 (always) + maybe v2
    if DB_V2_WRITE:
        # Best-effort v2 write (don't fail v1)
        try:
            from storage.session_v2_adapter import save_session_v2
            await save_session_v2(session)
        except Exception as e:
            logger.warning("Dual-write v2 failed (v1 will still save): %s", e)

    # v1 path (always — primary source of truth during dual-write phase)
    from dataclasses import asdict
    profile_dict = asdict(session.profile)

    # Serialize results: skill_key → list[dict] per version
    results_serialized: dict = {
        skill_key: [v.to_dict() for v in versions]
        for skill_key, versions in session.results.items()
    }

    # Pack meta fields inside results dict
    results_serialized["_selected_task"] = session.selected_task or ""
    if session.pending_intake:
        results_serialized["_pending_intake"] = session.pending_intake
    if session.preferences:
        results_serialized["_preferences"] = session.preferences
    if session.feedback:
        results_serialized["_feedback"] = session.feedback
    if session.pending_followup_skill:
        results_serialized["_pending_followup_skill"] = session.pending_followup_skill
    # Sprint 1 — persist tone_calibration + content_outputs
    if session.tone_calibration:
        results_serialized["_tone_calibration"] = session.tone_calibration
    if session.content_outputs:
        results_serialized["_content_outputs"] = session.content_outputs

    payload = {
        "user_id":          session.user_id,
        "stage":            session.stage.value,
        "profile":          profile_dict,
        "intake_history":   session.intake_history,
        "results":          results_serialized,
    }

    await _client.table(TABLE).upsert(payload).execute()


async def _clear_v1_row(user_id: int) -> None:
    """Best-effort delete of the legacy V1 sessions row.

    The V1 sessions table is no longer written in V2-only mode, but old rows
    persist. The get_session V1 fallback path reads them on any V2 read error,
    which can resurrect stale profile data. Deleting on reset removes that risk.
    """
    try:
        await _client.table(TABLE).delete().eq("user_id", user_id).execute()
    except Exception as e:
        logger.warning("V1 row cleanup failed for user %d (non-fatal): %s", user_id, e)


async def reset_session(user_id: int):
    """Reset session to initial state.

    Dual-Write strategy (mirror save_session):
      Phase D (READ=True, WRITE=False) → reset V2 only.
      Dual-write (WRITE=True)          → reset V2 best-effort + V1.
      Default (cả 2 False)             → reset V1 only.
    """
    try:
        from config import DB_V2_WRITE, DB_V2_READ
    except ImportError:
        DB_V2_WRITE = False
        DB_V2_READ = False

    _v2_only = DB_V2_READ and not DB_V2_WRITE

    if _v2_only:
        # Phase D: reset V2 (source of truth)
        from storage.session_v2_adapter import reset_session_v2
        await reset_session_v2(user_id)
        # Also wipe the stale V1 sessions row so the get_session V1 fallback
        # (session.py get_session, line ~118) can never resurrect old profile
        # data — e.g. industry → industry_cached — after a reset.
        await _clear_v1_row(user_id)
        return

    # Dual-write: reset V2 best-effort (không làm fail V1)
    if DB_V2_WRITE:
        try:
            from storage.session_v2_adapter import reset_session_v2
            await reset_session_v2(user_id)
        except Exception as e:
            logger.warning("V2 reset failed (V1 will still reset): %s", e)

    # V1 path (default / dual-write source of truth)
    payload = {
        "user_id":         user_id,
        "stage":           "idle",
        "profile":         {},
        "intake_history":  [],
        "results":         {},
    }
    await _client.table(TABLE).upsert(payload).execute()
