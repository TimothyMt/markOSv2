"""
Backfill script — migrate existing `sessions` rows → v2 normalized tables.

Run ONCE sau khi apply migration 006_normalize_schema.sql.
Idempotent — chạy lại được không hỏng data.

Usage:
    cd marketing-os-bot
    python -m scripts.backfill_v2
"""
import asyncio
import json
import logging
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("backfill")


async def main():
    # Init Supabase client
    from storage import init_pool
    await init_pool()

    from storage import session as _session_mod
    client = _session_mod._client

    # Fetch all sessions
    logger.info("Fetching all sessions...")
    resp = await client.table("sessions").select("*").execute()
    rows = resp.data or []
    logger.info("Found %d sessions to migrate.", len(rows))

    stats = {
        "users":      0,
        "profiles":   0,
        "sessions":   0,
        "skill_runs": 0,
        "errors":     0,
    }

    for i, row in enumerate(rows, 1):
        try:
            user_id = row.get("user_id")
            if not user_id:
                continue

            # Parse results dict
            raw_results = row.get("results") or {}
            if isinstance(raw_results, str):
                raw_results = json.loads(raw_results)

            preferences      = raw_results.pop("_preferences", {}) or {}
            pending_intake   = raw_results.pop("_pending_intake", {}) or {}
            feedback         = raw_results.pop("_feedback", {}) or {}
            tone_calibration = raw_results.pop("_tone_calibration", {}) or {}
            content_outputs  = raw_results.pop("_content_outputs", {}) or {}
            selected_task    = raw_results.pop("_selected_task", None) or None
            raw_results.pop("_pending_followup_skill", None)
            raw_results.pop("_brand_candidates", None)

            profile_data = row.get("profile") or {}
            if isinstance(profile_data, str):
                profile_data = json.loads(profile_data)

            # ── 1. users table ──────────────────────────────────────
            await client.table("users").upsert({
                "user_id":         user_id,
                "name":            preferences.get("user_name"),
                "en_level":        preferences.get("en_level", "moderate"),
                "token_quota":     int(preferences.get("token_quota", 500000)),
                "token_used":      int(preferences.get("token_used", 0)),
                "plan":            preferences.get("plan", "free"),
                "industry_cached": profile_data.get("industry"),
            }).execute()
            stats["users"] += 1

            # ── 2. user_business_profile ────────────────────────────
            profile_clean = {
                k: v for k, v in profile_data.items()
                if k in {
                    "business_name", "industry", "stage", "product_service",
                    "target_customer", "monthly_revenue", "team_size",
                    "monthly_marketing_budget", "primary_goal",
                    "current_channels", "main_challenge", "competitors",
                    "location", "usp", "usp_confidence",
                } and v is not None
            }
            if profile_clean:
                profile_clean["user_id"] = user_id
                await client.table("user_business_profile").upsert(profile_clean).execute()
                stats["profiles"] += 1

            # ── 3. user_sessions_slim ───────────────────────────────
            intake_history = row.get("intake_history") or []
            if isinstance(intake_history, str):
                intake_history = json.loads(intake_history)

            await client.table("user_sessions_slim").upsert({
                "user_id":          user_id,
                "stage":            row.get("stage", "idle"),
                "selected_task":    selected_task,
                "pending_intake":   pending_intake,
                "intake_history":   intake_history[-20:],  # cap 20
                "tone_calibration": tone_calibration,
            }).execute()
            stats["sessions"] += 1

            # ── 4. skill_runs — migrate versioned outputs ───────────
            for skill_name, value in raw_results.items():
                if skill_name.startswith("_"):
                    continue

                # value can be string (old schema) or list[dict] (new)
                if isinstance(value, str):
                    versions = [{"content": value, "version": 1}]
                elif isinstance(value, list):
                    versions = value
                else:
                    continue

                for v in versions:
                    if not isinstance(v, dict):
                        continue
                    content = v.get("content")
                    if not content:
                        continue
                    try:
                        await client.table("skill_runs").insert({
                            "user_id":    user_id,
                            "skill_name": skill_name,
                            "version":    int(v.get("version", 1)),
                            "content":    content,
                        }).execute()
                        stats["skill_runs"] += 1
                    except Exception as e:
                        # Likely duplicate or FK error — log + skip
                        logger.debug("skill_run insert skipped (%s v%s): %s",
                                     skill_name, v.get("version"), e)

            # ── 5. posts (content_outputs) ──────────────────────────
            # Note: cần campaign_id, mà data cũ không có → skip để Phase 2 wire
            # Posts sẽ được populate khi user chạy content_calendar mới
            if content_outputs:
                logger.info("User %d has %d content_outputs — sẽ migrate Phase 2 (cần campaign_id)",
                            user_id, len(content_outputs))

            if i % 20 == 0:
                logger.info("Migrated %d/%d users...", i, len(rows))

        except Exception as e:
            logger.exception("Failed migrating user %s: %s", row.get("user_id"), e)
            stats["errors"] += 1

    logger.info("=" * 60)
    logger.info("BACKFILL COMPLETE")
    logger.info("  Users created:      %d", stats["users"])
    logger.info("  Profiles created:   %d", stats["profiles"])
    logger.info("  Sessions migrated:  %d", stats["sessions"])
    logger.info("  Skill runs migrated:%d", stats["skill_runs"])
    logger.info("  Errors:             %d", stats["errors"])
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
