"""Ads Notifier — pull FB data → compute delta → format → send Telegram.

Hai loại output:
  - Daily digest (so với hôm qua)
  - Weekly digest (so với 7 ngày trước, gửi mỗi thứ Hai)

Industry benchmarks (dùng khi user không set ngưỡng):
  Frequency max: 5.0
  ROAS drop:     20%
  CPM spike:     30%
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Benchmark mặc định (dùng khi alert threshold = NULL) ────────
DEFAULT_FREQUENCY_MAX  = 5.0
DEFAULT_ROAS_DROP_PCT  = 20.0
DEFAULT_CPM_SPIKE_PCT  = 30.0

# ── Metric display config ────────────────────────────────────────
METRIC_LABELS = {
    "spend":      ("💰", "Spend",      lambda v: f"{v/1000:.1f}K VND" if v < 1_000_000 else f"{v/1_000_000:.1f}M VND"),
    "roas":       ("📈", "ROAS",       lambda v: f"{v:.1f}x"),
    "cpl":        ("🎯", "CPL",        lambda v: f"{v:,.0f} VND"),
    "frequency":  ("📡", "Frequency",  lambda v: f"{v:.1f}"),
    "cpm":        ("💵", "CPM",        lambda v: f"{v:,.0f} VND"),
    "ctr":        ("👆", "CTR",        lambda v: f"{v:.2f}%"),
    "vtr_3s":     ("🎬", "VTR 3s",     lambda v: f"{v:.1f}%"),
    "reach":      ("📣", "Reach",      lambda v: f"{v:,.0f}"),
    "purchases":  ("🛒", "Purchases",  lambda v: f"{v:.0f}"),
    "cpa":        ("💸", "CPA",        lambda v: f"{v:,.0f} VND"),
    "cpc":        ("🔗", "CPC",        lambda v: f"{v:,.0f} VND"),
    "leads":      ("👥", "Leads",      lambda v: f"{v:.0f}"),
}

AVAILABLE_METRICS = list(METRIC_LABELS.keys())
RECOMMENDED_METRICS = ["spend", "roas", "cpl", "frequency"]


# ── Pull & snapshot ──────────────────────────────────────────────

async def pull_and_snapshot(conn: dict) -> tuple[list[dict], datetime]:
    """Pull data của NGÀY HÔM QUA + lưu snapshot dưới đúng ngày đó.

    Returns (rows, report_date).

    Dùng 'yesterday' (ngày đã đóng, ổn định) — KHÔNG dùng:
    - 'today': digest chạy 8h sáng + alert monitor chạy mỗi 4h → mỗi lần pull
      data "hôm nay" lại khác nhau (ngày chưa hết), snapshot bị ghi đè liên tục
      → so sánh ngày-qua-ngày lệch pha, ra số vô nghĩa.
    - 'last_7d': cumulative rolling 7 ngày nhưng lại lưu/so sánh như 1 ngày →
      frequency/spend/CPL bị thổi phồng ~7 lần so với thực tế 1 ngày, false-trigger
      alert liên tục (frequency 7-ngày gần như luôn > ngưỡng 5.0 của 1-ngày).
    'yesterday' là data đã chốt — pull lúc nào cũng ra cùng kết quả, khớp với số
    user thấy trong FB Ads Manager khi xem "Hôm qua".
    """
    from tools.crypto import decrypt_token
    from tools.fb_marketing import get_account_insights
    from storage.fb_connections import save_snapshot, update_last_pull

    user_id   = conn["user_id"]
    token     = decrypt_token(conn["encrypted_token"])
    account   = conn["ad_account_id"]

    campaigns = await get_account_insights(
        date_preset="yesterday",
        level="campaign",
        ad_account_id=account,
        access_token=token,
        extra_fields=["campaign_id", "action_values"],
    )

    report_date = datetime.now(timezone.utc) - timedelta(days=1)
    # save_snapshot trả về rows đã compute (roas/cpl/vtr_3s/campaign_id) — dùng
    # shape này để delta nhất quán với snapshot đọc từ DB.
    computed_rows = await save_snapshot(user_id, report_date, campaigns)
    await update_last_pull(user_id)
    return computed_rows, report_date



# ── Backfill / repair snapshot lịch sử ───────────────────────────

async def backfill_snapshots(conn: dict, days: int = 9) -> int:
    """Pull lại N ngày gần nhất theo TỪNG NGÀY riêng (time_increment=1) và ghi đè
    snapshot cũ — sửa data bị nhiễm bởi bug pull_and_snapshot trước đây (pull
    date_preset="last_7d" — tổng cumulative 7 ngày — nhưng lưu/nhãn như 1 ngày).

    Snapshot cho mỗi ngày trong khoảng vì vậy chứa tổng 7-ngày-tính-đến-hôm-đó
    thay vì số liệu thực của riêng ngày đó → tổng tuần (sum nhiều snapshot nhiễm)
    bị thổi phồng gấp nhiều lần so với thực tế (vd 20M vs thực chi 9.5M).

    'yesterday' (closed day) tự sửa được do upsert ghi đè mỗi sáng, nhưng các
    ngày xa hơn không bao giờ được pull lại — cần backfill 1 lần để sửa dứt
    điểm. time_range + time_increment=1 trả về đúng số liệu RIÊNG của từng ngày
    (giống "Hôm qua" trong FB Ads Manager), khớp với số user thấy khi xem theo
    range trong Ads Manager.

    Returns: số ngày đã ghi đè (overwrite).
    """
    from tools.crypto import decrypt_token
    from tools.fb_marketing import get_account_insights_daily
    from storage.fb_connections import save_snapshot

    user_id = conn["user_id"]
    token   = decrypt_token(conn["encrypted_token"])
    account = conn["ad_account_id"]

    today = datetime.now(timezone.utc).date()
    since = today - timedelta(days=days)
    until = today - timedelta(days=1)

    rows = await get_account_insights_daily(
        since=since.strftime("%Y-%m-%d"),
        until=until.strftime("%Y-%m-%d"),
        level="campaign",
        ad_account_id=account,
        access_token=token,
        extra_fields=["campaign_id", "action_values"],
    )

    by_date: dict[str, list[dict]] = {}
    for r in rows:
        d = r.get("date_start")
        if d:
            by_date.setdefault(d, []).append(r)

    for date_str, campaigns in by_date.items():
        snap_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        await save_snapshot(user_id, snap_date, campaigns)

    return len(by_date)


# ── Delta computation ────────────────────────────────────────────

def _sum_metric(rows: list[dict], key: str) -> float:
    return sum(float(r.get(key) or 0) for r in rows)


def _avg_metric(rows: list[dict], key: str) -> float:
    vals = [float(r.get(key) or 0) for r in rows if r.get(key)]
    return sum(vals) / len(vals) if vals else 0.0


def compute_delta(today_rows: list[dict], prev_rows: list[dict]) -> dict:
    """Tính delta per metric giữa 2 snapshot sets. Returns dict metric → (today, prev, pct_change)."""
    result = {}
    for metric in AVAILABLE_METRICS:
        if metric in ("roas", "cpl", "cpm", "ctr", "vtr_3s", "frequency", "cpa", "cpc"):
            today_val = _avg_metric(today_rows, metric)
            prev_val  = _avg_metric(prev_rows, metric)
        else:
            today_val = _sum_metric(today_rows, metric)
            prev_val  = _sum_metric(prev_rows, metric)
        if prev_val and prev_val != 0:
            pct = (today_val - prev_val) / prev_val * 100
        else:
            pct = None
        result[metric] = (today_val, prev_val, pct)
    return result


# ── Health assessment ────────────────────────────────────────────

def _account_health(campaigns: list[dict], conn: dict) -> str:
    freq_max = conn.get("alert_frequency_max") or DEFAULT_FREQUENCY_MAX
    roas_avg = _avg_metric(campaigns, "roas")
    freq_max_actual = max((float(c.get("frequency") or 0) for c in campaigns), default=0)
    if freq_max_actual > freq_max or roas_avg < 1.5:
        return "🔴 Nguy hiểm"
    if freq_max_actual > freq_max * 0.7 or roas_avg < 3.0:
        return "🟡 Cần tối ưu"
    return "🟢 Healthy"


# ── Format daily digest ──────────────────────────────────────────

def format_daily_digest(
    campaigns: list[dict],
    delta: dict,
    conn: dict,
    account_name: str,
    report_date: Optional[datetime] = None,
) -> str:
    tracked = conn.get("tracked_metrics") or RECOMMENDED_METRICS
    health  = _account_health(campaigns, conn)
    rdate   = (report_date or (datetime.now(timezone.utc) - timedelta(days=1))).strftime("%d/%m/%Y")

    lines = [
        f"📊 *Báo cáo Ads — {account_name}*",
        f"📅 Hôm qua ({rdate})  |  Sức khỏe: {health}",
        "",
    ]

    # Tracked metrics với delta
    for key in tracked:
        if key not in METRIC_LABELS or key not in delta:
            continue
        icon, label, fmt = METRIC_LABELS[key]
        today_val, prev_val, pct = delta[key]
        val_str = fmt(today_val)
        if pct is not None:
            arrow = "↑" if pct > 0 else "↓"
            # Nhóm "thấp là tốt": CPL/CPM/CPA/CPC + Frequency (tăng = saturation)
            good_down = key in ("cpl", "cpm", "cpa", "cpc", "frequency")
            # Spend là trung tính — không gắn ✅/⚠️
            if key == "spend":
                delta_str = f" ({arrow}{abs(pct):.0f}%)"
            else:
                is_good = (pct < 0 if good_down else pct > 0)
                delta_str = f" ({arrow}{abs(pct):.0f}% {'✅' if is_good else '⚠️'})"
        else:
            delta_str = ""
        lines.append(f"{icon} *{label}:* {val_str}{delta_str}")

    # Cảnh báo top 2
    alerts = _find_alerts(campaigns, conn)
    if alerts:
        lines.append("")
        lines.append("⚠️ *Cần chú ý:*")
        for a in alerts[:2]:
            lines.append(f"  {a['icon']} [{a['campaign']}] {a['message']}")

    # Winner
    winner = _find_winner(campaigns)
    if winner:
        lines.append("")
        lines.append(f"🏆 *Winner:* [{winner['campaign_name']}] ROAS {winner.get('roas', 0):.1f}x — 🟢 tốt")

    lines.extend(["", "👉 `/ads_analytics` — full report  ·  `/ads_optimizer` — thực thi ngay"])
    return "\n".join(lines)


def format_weekly_digest(
    this_week_rows: list[dict],
    prev_week_rows: list[dict],
    conn: dict,
    account_name: str,
) -> str:
    tracked = conn.get("tracked_metrics") or RECOMMENDED_METRICS
    delta   = compute_delta(this_week_rows, prev_week_rows)

    from datetime import date, timedelta
    today = date.today()
    week_start = (today - timedelta(days=6)).strftime("%d/%m")
    week_end   = today.strftime("%d/%m")

    lines = [
        f"📊 *Báo cáo tuần — {account_name}*",
        f"📅 {week_start}–{week_end} so với 7 ngày trước",
        "",
    ]

    for key in tracked:
        if key not in METRIC_LABELS or key not in delta:
            continue
        icon, label, fmt = METRIC_LABELS[key]
        today_val, prev_val, pct = delta[key]
        val_str  = fmt(today_val)
        prev_str = fmt(prev_val)
        if pct is not None:
            arrow = "↑" if pct > 0 else "↓"
            lines.append(f"{icon} *{label}:* {val_str} (vs {prev_str}, {arrow}{abs(pct):.0f}%)")
        else:
            lines.append(f"{icon} *{label}:* {val_str} (tuần trước: {prev_str})")

    lines.extend(["", "👉 `/ads_analytics` — phân tích chi tiết"])
    return "\n".join(lines)


# ── Báo Cáo Nhanh (on-demand, theo khung thời gian) ──────────────

LIVE_REPORT_NOTE = (
    "⚠️ *Lưu ý:* Số liệu hôm nay chưa chốt — Facebook vẫn đang cập nhật "
    "(đặc biệt conversions/ROAS do attribution window chưa đủ 24-72h), "
    "số có thể đổi nếu sếp xem lại sau vài giờ. So với hôm qua chỉ mang tính "
    "tham khảo vì hôm nay chưa hết ngày."
)

QUICK_REPORT_PERIODS = {
    "live":      {"title": "🔴 Live — hôm nay (tính đến giờ)", "vs": "hôm qua"},
    "yesterday": {"title": "📅 Hôm qua",                       "vs": "hôm kia"},
    "7d":        {"title": "📊 7 ngày qua",                    "vs": "7 ngày trước đó"},
}


async def fetch_quick_report(conn: dict, period: str) -> tuple[list[dict], list[dict]]:
    """Pull data cho Báo Cáo Nhanh — period = 'live' | 'yesterday' | '7d'.

    Trả về (current_rows, compare_rows) đã compute metrics (roas/cpl/...) — CHỈ
    xem nhanh, KHÔNG lưu snapshot (tránh ghi đè data dùng cho digest/alert tracking).

    Mỗi cặp current/compare luôn cùng granularity (cùng số ngày, cùng cách pull)
    để compute_delta so sánh đúng nghĩa — không lệch pha kiểu cumulative-vs-daily.
    """
    from tools.crypto import decrypt_token
    from tools.fb_marketing import get_account_insights, get_account_insights_daily
    from storage.fb_connections import compute_campaign_metrics

    token   = decrypt_token(conn["encrypted_token"])
    account = conn["ad_account_id"]
    today   = datetime.now(timezone.utc).date()
    extra   = ["campaign_id", "action_values"]

    if period == "live":
        # 'today' (chưa chốt) so với 'yesterday' (đã chốt) — cùng là 1 tổng/account/campaign
        current = await get_account_insights(date_preset="today", level="campaign",
                                              ad_account_id=account, access_token=token, extra_fields=extra)
        compare = await get_account_insights(date_preset="yesterday", level="campaign",
                                              ad_account_id=account, access_token=token, extra_fields=extra)

    elif period == "yesterday":
        # Pull 2 ngày liền kề theo time_increment=1 rồi tách — cả 2 đều là "1 ngày đã chốt"
        since = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        until = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = await get_account_insights_daily(since, until, ad_account_id=account,
                                                 access_token=token, extra_fields=extra)
        d_yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        current = [r for r in rows if r.get("date_start") == d_yesterday]
        compare = [r for r in rows if r.get("date_start") != d_yesterday]

    else:  # "7d"
        # Pull 14 ngày theo từng ngày rồi chia đôi — tránh trộn cumulative (last_7d)
        # với daily (như bug đã sửa ở pull_and_snapshot — xem b62d7eb)
        since = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        until = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = await get_account_insights_daily(since, until, ad_account_id=account,
                                                 access_token=token, extra_fields=extra)
        cutoff = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        current = [r for r in rows if r.get("date_start") >= cutoff]
        compare = [r for r in rows if r.get("date_start") <  cutoff]

    return [compute_campaign_metrics(c) for c in current], [compute_campaign_metrics(c) for c in compare]


def format_quick_report(period: str, current_rows: list[dict], compare_rows: list[dict],
                        conn: dict, account_name: str) -> str:
    meta    = QUICK_REPORT_PERIODS[period]
    tracked = conn.get("tracked_metrics") or RECOMMENDED_METRICS
    delta   = compute_delta(current_rows, compare_rows)

    lines = [
        f"📈 *Báo Cáo Nhanh — {account_name}*",
        meta["title"],
        "",
    ]

    for key in tracked:
        if key not in METRIC_LABELS or key not in delta:
            continue
        icon, label, fmt = METRIC_LABELS[key]
        today_val, prev_val, pct = delta[key]
        val_str = fmt(today_val)
        if pct is not None:
            arrow = "↑" if pct > 0 else "↓"
            delta_str = f" ({arrow}{abs(pct):.0f}% so với {meta['vs']})"
        else:
            delta_str = ""
        lines.append(f"{icon} *{label}:* {val_str}{delta_str}")

    if not current_rows:
        lines.append("_Chưa có data cho khung giờ này._")

    if period == "live":
        lines.append("")
        lines.append(LIVE_REPORT_NOTE)

    lines.extend(["", "👉 `/ads_analytics` — phân tích sâu  ·  `/ads_optimizer` — thực thi ngay"])
    return "\n".join(lines)


def ads_table_from_metrics(
    ads: list[dict],
    tracked_metrics: list[str],
    name_key: str = "ad_name",
    campaign_key: str = "campaign_name",
) -> tuple[list[str], list[dict]]:
    """Dựng (columns, rows) cho render_ads_table/build_ads_dashboard_report (bot.html_report)
    từ list ad-level metric dict + tracked_metrics user đã chọn qua menu /ads_settings.

    Cột = "Ad name" + "Campaign" (cố định, để biết đang xem ad nào) + đúng những
    metric user đã bật trong tracked_metrics — dùng chung METRIC_LABELS làm nguồn
    label/format với phần notification/quick-report, nên user đổi lựa chọn ở
    /ads_settings sẽ tự phản ánh vào bảng dashboard, không cần sửa code/đợi release.
    """
    metric_keys = [k for k in tracked_metrics if k in METRIC_LABELS]
    columns = ["Ad name", "Campaign"] + [METRIC_LABELS[k][1] for k in metric_keys]

    rows = []
    for ad in ads:
        cells = [ad.get(name_key) or "—", ad.get(campaign_key) or "—"]
        for key in metric_keys:
            _, _, fmt = METRIC_LABELS[key]
            try:
                cells.append(fmt(ad.get(key) or 0))
            except Exception:
                cells.append(str(ad.get(key, "—")))
        row = {"cells": cells}
        if ad.get("badge"):
            row["badge"] = ad["badge"]
            row["badge_cls"] = ad.get("badge_cls", "pill-win")
        rows.append(row)
    return columns, rows


# ── Alert detection ──────────────────────────────────────────────

def _find_alerts(campaigns: list[dict], conn: dict) -> list[dict]:
    freq_max   = conn.get("alert_frequency_max") or DEFAULT_FREQUENCY_MAX
    alerts = []
    for c in campaigns:
        freq = float(c.get("frequency") or 0)
        name = c.get("campaign_name") or "Campaign"
        if freq > freq_max:
            alerts.append({
                "icon": "🔴", "campaign": name[:25],
                "message": f"Frequency {freq:.1f} — saturate, cần PAUSE hoặc rotate creative",
                "campaign_id": c.get("campaign_id") or "",
                "alert_type":  "frequency",
            })
        elif freq > freq_max * 0.7:
            alerts.append({
                "icon": "🟠", "campaign": name[:25],
                "message": f"Frequency {freq:.1f} — đang ấm, chuẩn bị creative mới",
                "campaign_id": c.get("campaign_id") or "",
                "alert_type":  "frequency_warn",
            })
    return alerts


async def check_alerts(campaigns: list[dict], prev_campaigns: list[dict], conn: dict) -> list[dict]:
    """Kiểm tra ngưỡng cảnh báo so với snapshot hôm qua. Áp cooldown."""
    from storage.fb_connections import check_and_set_cooldown
    user_id       = conn["user_id"]
    freq_max      = conn.get("alert_frequency_max") or DEFAULT_FREQUENCY_MAX
    roas_drop_pct = conn.get("alert_roas_drop_pct") or DEFAULT_ROAS_DROP_PCT
    cpm_spike_pct = conn.get("alert_cpm_spike_pct") or DEFAULT_CPM_SPIKE_PCT

    # Build lookup prev by campaign_id
    prev_map = {c.get("campaign_id") or c.get("id"): c for c in prev_campaigns}

    triggered = []
    for c in campaigns:
        cid  = c.get("campaign_id") or c.get("id") or ""
        name = (c.get("campaign_name") or "Campaign")[:25]
        prev = prev_map.get(cid) or {}

        freq = float(c.get("frequency") or 0)
        if freq > freq_max:
            if await check_and_set_cooldown(user_id, cid, "frequency"):
                days_left = max(0, round(7 / max(freq - 5, 0.1), 1)) if freq > 5 else "?"
                triggered.append({
                    "icon": "🔴", "campaign": name,
                    "message": (
                        f"Frequency = *{freq:.1f}* — vượt ngưỡng {freq_max}\n"
                        f"   Ước tính còn ~{days_left} ngày trước khi CPM tăng >30%\n"
                        f"   → PAUSE creative + reset audience"
                    ),
                })

        cpm_today = float(c.get("cpm") or 0)
        cpm_prev  = float(prev.get("cpm") or 0)
        if cpm_prev > 0 and cpm_today > 0:
            cpm_chg = (cpm_today - cpm_prev) / cpm_prev * 100
            if cpm_chg > cpm_spike_pct:
                if await check_and_set_cooldown(user_id, cid, "cpm_spike"):
                    triggered.append({
                        "icon": "🟠", "campaign": name,
                        "message": (
                            f"CPM tăng *{cpm_chg:.0f}%* "
                            f"({cpm_prev:,.0f} → {cpm_today:,.0f} VND)\n"
                            f"   → Kiểm tra audience overlap hoặc đổi creative"
                        ),
                    })

        roas_today = float(c.get("roas") or 0)
        roas_prev  = float(prev.get("roas") or 0)
        if roas_prev > 0 and roas_today > 0:
            roas_chg = (roas_prev - roas_today) / roas_prev * 100
            if roas_chg > roas_drop_pct:
                if await check_and_set_cooldown(user_id, cid, "roas_drop"):
                    triggered.append({
                        "icon": "🔴", "campaign": name,
                        "message": (
                            f"ROAS giảm *{roas_chg:.0f}%* "
                            f"({roas_prev:.1f}x → {roas_today:.1f}x)\n"
                            f"   → Xem lại offer + landing page"
                        ),
                    })
    return triggered


def format_alert(alert: dict, account_name: str) -> str:
    return (
        f"🚨 *Alert — {account_name}*\n\n"
        f"Campaign [{alert['campaign']}]\n"
        f"{alert['message']}\n\n"
        f"👉 `/ads_optimizer` để thực thi ngay"
    )


def _find_winner(campaigns: list[dict]) -> Optional[dict]:
    valid = [c for c in campaigns if float(c.get("roas") or 0) > 0]
    if not valid:
        return None
    return max(valid, key=lambda c: float(c.get("roas") or 0))


# ── Send helpers ─────────────────────────────────────────────────

async def send_message_safe(bot, user_id: int, text: str) -> None:
    from telegram.constants import ParseMode
    from telegram.error import BadRequest
    try:
        await bot.send_message(user_id, text, parse_mode=ParseMode.MARKDOWN)
    except BadRequest as e:
        if "parse entities" in str(e).lower():
            # Markdown entity lỗi (vd ký tự đặc biệt trong dynamic data) — gửi lại không format
            # còn hơn mất tin báo cáo/alert.
            logger.warning("send_message markdown parse failed user=%d, retry plain text: %s", user_id, e)
            try:
                await bot.send_message(user_id, text.replace("*", "").replace("_", "").replace("`", ""))
            except Exception as e2:
                logger.warning("send_message plain-text retry failed user=%d: %s", user_id, e2)
        else:
            logger.warning("send_message failed user=%d: %s", user_id, e)
    except Exception as e:
        logger.warning("send_message failed user=%d: %s", user_id, e)
