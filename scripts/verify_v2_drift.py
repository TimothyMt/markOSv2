"""
Drift Detection — so sánh v1 (sessions) vs v2 (normalized) cho mỗi user.

Chạy định kỳ trong dual-write phase để verify v2 đang đồng bộ với v1.
Nếu phát hiện drift → log chi tiết để debug trước khi cutover.

Usage:
    cd marketing-os-bot
    python -m scripts.verify_v2_drift            # check all users
    python -m scripts.verify_v2_drift 7011450357 # check 1 user
"""
import asyncio
import json
import logging
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("drift")


def _norm(value):
    """Normalize value để compare (handle None, empty string, etc.)."""
    if value is None or value == "":
        return None
    return value


async def check_user(user_id: int, v1_client) -> dict:
    """
    So sánh v1 vs v2 cho 1 user.
    Returns dict {user_id, drifts: [...]}
    """
    drifts = []

    # ── Load v1 ──────────────────────────────────────────────
    v1_resp = (
        await v1_client.table("sessions")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not v1_resp.data:
        return {"user_id": user_id, "drifts": ["v1: no row"]}

    v1 = v1_resp.data[0]
    v1_profile = v1.get("profile") or {}
    if isinstance(v1_profile, str):
        v1_profile = json.loads(v1_profile)
    v1_results = v1.get("results") or {}
    if isinstance(v1_results, str):
        v1_results = json.loads(v1_results)
    v1_prefs = v1_results.get("_preferences", {}) or {}

    # ── Load v2 ──────────────────────────────────────────────
    from storage.v2 import get_user, get_profile, get_session_slim, list_skill_runs
    v2_user    = await get_user(user_id)
    v2_profile = await get_profile(user_id)
    v2_slim    = await get_session_slim(user_id)
    v2_runs    = await list_skill_runs(user_id, limit=100)

    if not v2_user:
        drifts.append("v2: user row missing")
        return {"user_id": user_id, "drifts": drifts}

    # ── Compare users table ──────────────────────────────────
    checks = [
        ("name",        _norm(v1_prefs.get("user_name")),  _norm(v2_user.get("name"))),
        ("en_level",    _norm(v1_prefs.get("en_level")),    _norm(v2_user.get("en_level"))),
        ("token_used",  int(v1_prefs.get("token_used", 0)), int(v2_user.get("token_used", 0))),
        ("token_quota", int(v1_prefs.get("token_quota", 500000)),
                        int(v2_user.get("token_quota", 500000))),
    ]
    for field, v1_val, v2_val in checks:
        if v1_val != v2_val:
            drifts.append(f"users.{field}: v1={v1_val!r} ≠ v2={v2_val!r}")

    # ── Compare profile ──────────────────────────────────────
    if v2_profile:
        for field in ("business_name", "industry", "stage", "product_service",
                      "target_customer", "primary_goal", "main_challenge", "usp"):
            v1_val = _norm(v1_profile.get(field))
            v2_val = _norm(v2_profile.get(field))
            if v1_val != v2_val:
                drifts.append(f"profile.{field}: v1={v1_val!r} ≠ v2={v2_val!r}")
    elif any(v1_profile.values()):
        drifts.append("profile: v1 has data, v2 row missing")

    # ── Compare slim session ─────────────────────────────────
    v1_stage = v1.get("stage", "idle")
    v2_stage = v2_slim.get("stage", "idle")
    if v1_stage != v2_stage:
        drifts.append(f"session.stage: v1={v1_stage!r} ≠ v2={v2_stage!r}")

    # ── Compare skill_runs count ─────────────────────────────
    v1_skill_count = sum(
        len(v) if isinstance(v, list) else 1
        for k, v in v1_results.items()
        if not k.startswith("_")
    )
    v2_skill_count = len(v2_runs)
    if abs(v1_skill_count - v2_skill_count) > 0:
        drifts.append(f"skill_runs: v1 count={v1_skill_count}, v2 count={v2_skill_count}")

    return {"user_id": user_id, "drifts": drifts}


async def main():
    target_user = int(sys.argv[1]) if len(sys.argv) > 1 else None

    from storage import init_pool
    await init_pool()
    from storage import session as _session_mod
    client = _session_mod._client

    # Fetch list of user_ids
    if target_user:
        user_ids = [target_user]
    else:
        resp = await client.table("sessions").select("user_id").execute()
        user_ids = [r["user_id"] for r in (resp.data or [])]
        logger.info("Checking %d users...", len(user_ids))

    total = len(user_ids)
    clean = 0
    dirty = 0
    drift_summary: dict[str, int] = {}

    for i, uid in enumerate(user_ids, 1):
        result = await check_user(uid, client)
        if not result["drifts"]:
            clean += 1
        else:
            dirty += 1
            logger.warning("DRIFT user=%d:", uid)
            for d in result["drifts"]:
                logger.warning("    - %s", d)
                key = d.split(":")[0]
                drift_summary[key] = drift_summary.get(key, 0) + 1

        if i % 20 == 0:
            logger.info("Progress %d/%d (clean=%d, drift=%d)", i, total, clean, dirty)

    logger.info("=" * 60)
    logger.info("DRIFT REPORT")
    logger.info("  Total users checked: %d", total)
    logger.info("  Clean (no drift):    %d", clean)
    logger.info("  Drifted:             %d (%.1f%%)", dirty, 100*dirty/max(total,1))
    if drift_summary:
        logger.info("  Top drift fields:")
        for k, v in sorted(drift_summary.items(), key=lambda x: -x[1])[:10]:
            logger.info("    %-40s %d", k, v)
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
