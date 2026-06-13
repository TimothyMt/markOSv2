"""Ads Scheduler — chạy 2 jobs nền:

Job A — Daily Digest:  8:00 AM Asia/Ho_Chi_Minh mỗi ngày
Job B — Alert Monitor: mỗi 4 tiếng, check thresholds
Job C — Weekly Report: mỗi thứ Hai 8:00 AM (gửi thay vì Daily Digest)
Job D — Token Refresh: mỗi ngày, refresh token gần hết hạn
Job E — Snapshot Cleanup: mỗi tuần, xóa snapshots > 90 ngày
Job F — Snapshot Backfill: chạy 1 lần lúc khởi động, sửa snapshot lịch sử
        bị nhiễm bởi bug pull last_7d-lưu-thành-1-ngày (xem _run_snapshot_backfill)

Tích hợp: gọi start_ads_scheduler(bot) từ post_init trong main.py.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta, date

logger = logging.getLogger(__name__)


# Dedup guard — đảm bảo mỗi job fire đúng 1 lần/khung giờ (sleep 60s có thể drift).
# Key = job name, value = chuỗi định danh khung đã chạy (vd "2026-06-01" hoặc "2026-06-01-08").
_last_fired: dict[str, str] = {}


def _should_fire(job: str, slot_key: str) -> bool:
    """True nếu job chưa chạy ở slot này. Đánh dấu đã chạy."""
    if _last_fired.get(job) == slot_key:
        return False
    _last_fired[job] = slot_key
    return True


async def start_ads_scheduler(bot) -> None:
    """Entry point — chạy vô tận dưới dạng asyncio task."""
    logger.info("[AdsScheduler] Starting background scheduler")
    asyncio.create_task(_run_snapshot_backfill())
    while True:
        try:
            await _tick(bot)
        except Exception as e:
            logger.error("[AdsScheduler] tick error: %s", e)
        await asyncio.sleep(30)  # check mỗi 30s — bắt khung giờ chính xác hơn


async def _tick(bot) -> None:
    """Gọi định kỳ — quyết định job nào cần chạy. Dùng _should_fire để chống double-fire."""
    now_vn = datetime.now(timezone.utc) + timedelta(hours=7)  # Asia/Ho_Chi_Minh (UTC+7)
    hour, weekday = now_vn.hour, now_vn.weekday()  # 0=Mon
    day_key  = now_vn.strftime("%Y-%m-%d")
    hour_key = now_vn.strftime("%Y-%m-%d-%H")

    # Job A/C: Daily/Weekly digest — 8:00 (1 lần/ngày)
    if hour == 8 and _should_fire("digest", day_key):
        if weekday == 0:  # Thứ Hai → weekly report
            asyncio.create_task(_run_weekly_report(bot))
        else:
            asyncio.create_task(_run_daily_digest(bot))

    # Job B: Alert monitor — mỗi 4 tiếng (0,4,8,12,16,20h), 1 lần/khung giờ
    if hour % 4 == 0 and _should_fire("alert", hour_key):
        asyncio.create_task(_run_alert_monitor(bot))

    # Job D: Token refresh — 2:00 (1 lần/ngày)
    if hour == 2 and _should_fire("refresh", day_key):
        asyncio.create_task(_run_token_refresh(bot))

    # Job E: Snapshot cleanup — Chủ Nhật 3:00 (1 lần/ngày)
    if weekday == 6 and hour == 3 and _should_fire("cleanup", day_key):
        asyncio.create_task(_run_cleanup())


# ── Job A: Daily Digest ──────────────────────────────────────────

async def _run_daily_digest(bot) -> None:
    from storage.fb_connections import get_all_active_connections, get_snapshot
    from services.ads_notifier import pull_and_snapshot, compute_delta, format_daily_digest, send_message_safe

    logger.info("[AdsScheduler] Running daily digest")
    connections = await get_all_active_connections()

    for conn in connections:
        user_id      = conn["user_id"]
        account_name = (conn.get("account_name") or "Ads Account").replace("*", "").replace("_", "-").replace("`", "'").replace("[", "(").replace("]", ")")
        try:
            yesterday_campaigns, report_date = await pull_and_snapshot(conn)

            # Lấy snapshot 2 ngày trước để so sánh ngày-qua-ngày với "hôm qua"
            day_before = report_date - timedelta(days=1)
            prev_rows = await get_snapshot(user_id, day_before)

            delta = compute_delta(yesterday_campaigns, prev_rows)
            text  = format_daily_digest(yesterday_campaigns, delta, conn, account_name, report_date=report_date)
            await send_message_safe(bot, user_id, text)

        except Exception as e:
            logger.warning("[AdsScheduler] daily digest failed user=%d: %s", user_id, e)
            if "401" in str(e) or "190" in str(e) or "Invalid OAuth" in str(e):
                await _handle_token_revoked(bot, conn)


# ── Job C: Weekly Report ─────────────────────────────────────────

async def _run_weekly_report(bot) -> None:
    from storage.fb_connections import get_all_active_connections, get_snapshots_range
    from services.ads_notifier import pull_and_snapshot, format_weekly_digest, send_message_safe

    logger.info("[AdsScheduler] Running weekly report (Monday)")
    connections = await get_all_active_connections()
    today = date.today()

    for conn in connections:
        user_id      = conn["user_id"]
        account_name = (conn.get("account_name") or "Ads Account").replace("*", "").replace("_", "-").replace("`", "'").replace("[", "(").replace("]", ")")
        try:
            await pull_and_snapshot(conn)  # đảm bảo snapshot hôm qua đã có trước khi query range

            # Snapshot 7 ngày vừa rồi vs 7 ngày trước đó
            this_week_start = datetime.combine(today - timedelta(days=6), datetime.min.time()).replace(tzinfo=timezone.utc)
            this_week_end   = datetime.now(timezone.utc)
            prev_week_start = this_week_start - timedelta(days=7)
            prev_week_end   = this_week_start - timedelta(seconds=1)

            this_rows = await get_snapshots_range(user_id, this_week_start, this_week_end)
            prev_rows = await get_snapshots_range(user_id, prev_week_start, prev_week_end)

            text = format_weekly_digest(this_rows, prev_rows, conn, account_name)
            await send_message_safe(bot, user_id, text)

        except Exception as e:
            logger.warning("[AdsScheduler] weekly report failed user=%d: %s", user_id, e)
            if "401" in str(e) or "190" in str(e):
                await _handle_token_revoked(bot, conn)


# ── Job B: Alert Monitor ─────────────────────────────────────────

async def _run_alert_monitor(bot) -> None:
    from storage.fb_connections import get_all_active_connections, get_snapshot
    from services.ads_notifier import pull_and_snapshot, check_alerts, format_alert, send_message_safe

    logger.info("[AdsScheduler] Running alert monitor")
    connections = await get_all_active_connections()

    for conn in connections:
        user_id      = conn["user_id"]
        account_name = (conn.get("account_name") or "Ads Account").replace("*", "").replace("_", "-").replace("`", "'").replace("[", "(").replace("]", ")")
        try:
            yesterday_campaigns, report_date = await pull_and_snapshot(conn)
            day_before = report_date - timedelta(days=1)
            prev_rows = await get_snapshot(user_id, day_before)

            alerts = await check_alerts(yesterday_campaigns, prev_rows, conn)
            for alert in alerts:
                text = format_alert(alert, account_name)
                await send_message_safe(bot, user_id, text)

        except Exception as e:
            logger.warning("[AdsScheduler] alert monitor failed user=%d: %s", user_id, e)


# ── Job D: Token Refresh ─────────────────────────────────────────

async def _run_token_refresh(bot) -> None:
    from storage.fb_connections import get_all_active_connections
    from services.fb_oauth import refresh_token_if_needed

    logger.info("[AdsScheduler] Running token refresh check")
    connections = await get_all_active_connections()
    for conn in connections:
        user_id = conn["user_id"]
        try:
            still_valid = await refresh_token_if_needed(user_id)
            if not still_valid:
                await _handle_token_revoked(bot, conn)
        except Exception as e:
            logger.warning("[AdsScheduler] token refresh failed user=%d: %s", user_id, e)


# ── One-time: Snapshot Backfill/Repair ───────────────────────────

async def _run_snapshot_backfill() -> None:
    """Chạy 1 lần khi scheduler khởi động — sửa snapshot lịch sử bị nhiễm bởi
    bug cũ (pull date_preset="last_7d" nhưng lưu/nhãn như 1 ngày → mỗi snapshot
    chứa tổng cumulative 7-ngày thay vì số liệu thực của ngày đó, khiến tổng
    tuần bị thổi phồng ~2x — vd báo 20M trong khi Ads Manager chỉ ghi nhận 9.5M).

    Pull lại 9 ngày gần nhất theo TỪNG NGÀY riêng (time_increment=1) rồi ghi đè
    (upsert) snapshot cũ bằng số liệu đúng — tự sửa dứt điểm, không cần thao tác
    thủ công trên DB. Idempotent: chạy lại (vd bot restart) chỉ ghi đè bằng đúng
    số liệu closed-day giống hệt, không gây sai lệch thêm.
    """
    from storage.fb_connections import get_all_active_connections
    from services.ads_notifier import backfill_snapshots

    logger.info("[AdsScheduler] Running one-time snapshot backfill/repair (fix contaminated last_7d snapshots)")
    connections = await get_all_active_connections()
    for conn in connections:
        user_id = conn["user_id"]
        try:
            n = await backfill_snapshots(conn, days=9)
            logger.info("[AdsScheduler] Snapshot backfill: repaired %d days for user=%d", n, user_id)
        except Exception as e:
            logger.warning("[AdsScheduler] snapshot backfill failed user=%d: %s", user_id, e)


# ── Job E: Snapshot Cleanup ──────────────────────────────────────

async def _run_cleanup() -> None:
    from storage.fb_connections import cleanup_old_snapshots
    deleted = await cleanup_old_snapshots()
    logger.info("[AdsScheduler] Snapshot cleanup: deleted %d rows > 90 days", deleted)


# ── Token revoked handler ────────────────────────────────────────

async def _handle_token_revoked(bot, conn: dict) -> None:
    from storage.fb_connections import disable_connection
    from services.ads_notifier import send_message_safe

    user_id = conn["user_id"]
    await disable_connection(user_id)
    await send_message_safe(
        bot, user_id,
        "⚠️ *Kết nối Facebook Ads đã ngắt*\n\n"
        "Token hết hạn hoặc quyền bị thu hồi.\n"
        "Gõ `/connect_ads` để kết nối lại — settings cũ vẫn giữ nguyên."
    )
    logger.info("[AdsScheduler] Token revoked, disabled connection for user=%d", user_id)
