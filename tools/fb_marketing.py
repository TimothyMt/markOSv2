"""
Facebook Marketing API wrapper.
Dùng cho skill "Phân Tích & Audit Ads" (ads_analytics) — pull data ads của sếp.

Docs: https://developers.facebook.com/docs/marketing-api/insights
Endpoint: GET /v20.0/act_{ad_account_id}/insights

Requires:
- FB_ACCESS_TOKEN với permissions: ads_read, read_insights
- FB_AD_ACCOUNT_ID: dạng "act_XXXXXXXXXX"
"""
import json
import logging
from typing import Optional
import httpx

from config import FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID

logger = logging.getLogger(__name__)

FB_GRAPH_VERSION = "v20.0"
FB_BASE_URL = f"https://graph.facebook.com/{FB_GRAPH_VERSION}"

# Default insight fields để pull
DEFAULT_INSIGHT_FIELDS = [
    "campaign_name",
    "adset_name",
    "ad_name",
    "spend",
    "impressions",
    "reach",
    "clicks",
    "ctr",
    "cpc",
    "cpm",
    "cpp",
    "frequency",
    "actions",                          # conversions, link_clicks, etc.
    "cost_per_action_type",
    # Video metrics — dùng để tính Hook Rate (T1) + Hold Rate (T2) theo framework phân tích
    # Lưu ý: "video_3_sec_watched_actions" đã bị FB loại khỏi fields param (lỗi #100 trên v20.0+)
    # → 3-sec video view giờ lấy qua actions[action_type=video_view] (cùng field "actions" ở trên).
    "video_play_actions",               # tổng lượt play
    "video_thruplay_watched_actions",   # Hold Rate = ThruPlay / VTR3s (Tầng 2, 15s+)
    "video_p25_watched_actions",        # 25% watched — body strength signal
    "video_p75_watched_actions",        # 75% watched — story compelling signal
    "date_start",
    "date_stop",
]


# ─────────────────────────────────────────────────────────────────
# Ad Account Insights
# ─────────────────────────────────────────────────────────────────

async def get_account_insights(
    date_preset: str = "last_30d",
    level: str = "campaign",
    ad_account_id: Optional[str] = None,
    access_token: Optional[str] = None,
    extra_fields: Optional[list] = None,
) -> list[dict]:
    """Pull insights từ Ad Account của sếp.

    Args:
        date_preset: "today" | "yesterday" | "last_7d" | "last_30d" | "last_90d" | "this_month" | "last_month"
        level: "account" | "campaign" | "adset" | "ad"
        ad_account_id: Override account ID (dạng "act_XXXXXXXXXX")
        access_token: Override token
        extra_fields: Fields bổ sung ngoài DEFAULT_INSIGHT_FIELDS

    Returns:
        List of insight dicts, sorted by spend desc
    """
    token = access_token or FB_ACCESS_TOKEN
    account_id = ad_account_id or FB_AD_ACCOUNT_ID

    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN chưa setup trong env vars")
    if not account_id:
        raise RuntimeError(
            "FB_AD_ACCOUNT_ID chưa setup — sếp cần thêm env var này.\n"
            "Tìm trong Business Manager → Ad Accounts → copy số act_XXXXXXXX"
        )

    # Ensure format act_XXXXXXXX
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    fields = DEFAULT_INSIGHT_FIELDS + (extra_fields or [])

    params = {
        "fields": ",".join(fields),
        "date_preset": date_preset,
        "level": level,
        "sort": "spend_descending",
        "limit": 50,
        "access_token": token,
    }

    url = f"{FB_BASE_URL}/{account_id}/insights"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        error_data = response.json()
        error_msg = error_data.get("error", {}).get("message", response.text)
        logger.error(f"FB Marketing API error: {error_msg}")
        raise RuntimeError(f"FB Marketing API lỗi: {error_msg}")

    data = response.json()
    results = data.get("data", [])
    logger.info(f"Marketing API: account {account_id} | {date_preset} | {level} → {len(results)} rows")
    return results


async def get_account_insights_daily(
    since: str,
    until: str,
    level: str = "campaign",
    ad_account_id: Optional[str] = None,
    access_token: Optional[str] = None,
    extra_fields: Optional[list] = None,
) -> list[dict]:
    """Pull insights theo TỪNG NGÀY riêng biệt trong khoảng [since, until] (YYYY-MM-DD).

    Khác với get_account_insights (date_preset trả về 1 tổng cumulative cho cả
    khoảng), hàm này dùng time_range + time_increment=1 — FB trả về N rows/campaign
    (1 row/ngày), mỗi row có date_start riêng. Dùng để backfill/sửa snapshot lịch
    sử bị lưu sai (vd snapshot nhiễm tổng last_7d thay vì số liệu 1 ngày thực).
    """
    token = access_token or FB_ACCESS_TOKEN
    account_id = ad_account_id or FB_AD_ACCOUNT_ID

    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN chưa setup trong env vars")
    if not account_id:
        raise RuntimeError("FB_AD_ACCOUNT_ID chưa setup")

    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    fields = DEFAULT_INSIGHT_FIELDS + (extra_fields or [])

    params = {
        "fields": ",".join(fields),
        "time_range": json.dumps({"since": since, "until": until}),
        "time_increment": 1,
        "level": level,
        "limit": 200,
        "access_token": token,
    }

    url = f"{FB_BASE_URL}/{account_id}/insights"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        error_data = response.json()
        error_msg = error_data.get("error", {}).get("message", response.text)
        logger.error(f"FB Marketing API error (daily): {error_msg}")
        raise RuntimeError(f"FB Marketing API lỗi: {error_msg}")

    data = response.json()
    results = data.get("data", [])
    logger.info(f"Marketing API: account {account_id} | {since}..{until} (daily) | {level} → {len(results)} rows")
    return results


async def get_active_campaigns(
    ad_account_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> list[dict]:
    """Lấy danh sách campaigns đang active."""
    token = access_token or FB_ACCESS_TOKEN
    account_id = ad_account_id or FB_AD_ACCOUNT_ID

    if not token or not account_id:
        return []

    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    params = {
        "fields": "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time",
        "effective_status": '["ACTIVE","PAUSED"]',
        "limit": 30,
        "access_token": token,
    }

    url = f"{FB_BASE_URL}/{account_id}/campaigns"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        return []

    return response.json().get("data", [])


# ─────────────────────────────────────────────────────────────────
# Format helpers
# ─────────────────────────────────────────────────────────────────

def _extract_action_value(actions: list[dict], action_type: str) -> int:
    """Extract value của 1 action_type từ actions array."""
    if not actions:
        return 0
    for a in actions:
        if a.get("action_type") == action_type:
            return int(float(a.get("value", 0)))
    return 0


def _hook_hold_rates(r: dict, impressions: int) -> tuple[float | None, float | None]:
    """Tính Hook Rate (VTR 3s/imp) và Hold Rate (ThruPlay/VTR3s). None = không có data.

    3-sec video view lấy từ actions[action_type=video_view] — field dedicated
    "video_3_sec_watched_actions" đã bị FB từ chối trong fields param (lỗi #100).
    """
    vtr3 = _extract_action_value(r.get("actions") or [], "video_view")
    thruplay = _extract_action_value(r.get("video_thruplay_watched_actions") or [], "video_view")

    hook = (vtr3 / impressions * 100) if impressions and vtr3 else None
    hold = (thruplay / vtr3 * 100) if vtr3 and thruplay else None
    return hook, hold


def format_insights_for_analysis(insights: list[dict], period: str) -> str:
    """Convert raw FB Marketing API response → structured text cho Claude phân tích.

    Tính Hook Rate (VTR 3s / Imp) + Hold Rate (ThruPlay / VTR 3s) từ video metrics thật.
    Claude dùng framework phễu 6 tầng để suy luận điểm break — không phải data từ Andromeda.
    """
    if not insights:
        return f"**Không có data ads trong period: {period}**\n(Ad Account chưa có campaign nào chạy hoặc không có spend)"

    # Tính tổng account
    total_spend = sum(float(r.get("spend", 0)) for r in insights)
    total_impressions = sum(int(r.get("impressions", 0)) for r in insights)
    total_clicks = sum(int(r.get("clicks", 0)) for r in insights)
    total_vtr3 = sum(
        _extract_action_value(r.get("actions") or [], "video_view")
        for r in insights
    )
    total_thruplay = sum(
        _extract_action_value(r.get("video_thruplay_watched_actions") or [], "video_view")
        for r in insights
    )
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
    avg_cpm = (total_spend / total_impressions * 1000) if total_impressions else 0
    avg_hook = (total_vtr3 / total_impressions * 100) if total_impressions and total_vtr3 else None
    avg_hold = (total_thruplay / total_vtr3 * 100) if total_vtr3 and total_thruplay else None

    lines = [
        f"## Facebook Ads Data — {period}",
        "",
        "### TỔNG QUAN ACCOUNT",
        f"- **Tổng spend:** {total_spend:,.0f} VND",
        f"- **Tổng impressions:** {total_impressions:,}",
        f"- **Tổng clicks:** {total_clicks:,}",
        f"- **CTR trung bình:** {avg_ctr:.2f}%",
        f"- **CPM trung bình:** {avg_cpm:,.0f} VND",
    ]
    if avg_hook is not None:
        lines.append(f"- **Hook Rate (VTR 3s) trung bình:** {avg_hook:.1f}%")
    if avg_hold is not None:
        lines.append(f"- **Hold Rate (ThruPlay) trung bình:** {avg_hold:.1f}%")
    if avg_hook is None and avg_hold is None:
        lines.append("- **Video metrics:** Không có (campaign không phải video hoặc chưa đủ data)")

    lines += ["", f"### BREAKDOWN THEO CAMPAIGN ({len(insights)} campaigns)"]

    for r in insights[:20]:  # Cap ở 20
        name = r.get("campaign_name") or r.get("adset_name") or r.get("ad_name", "Unknown")
        spend = float(r.get("spend", 0))
        impressions = int(r.get("impressions", 0))
        clicks = int(r.get("clicks", 0))
        ctr = float(r.get("ctr", 0)) * 100
        cpm = float(r.get("cpm", 0))
        cpc = float(r.get("cpc", 0))
        frequency = float(r.get("frequency", 0))
        hook, hold = _hook_hold_rates(r, impressions)

        # Extract conversions from actions
        actions = r.get("actions") or []
        conversions = next(
            (int(float(a.get("value", 0))) for a in actions
             if a.get("action_type") in ("purchase", "lead", "complete_registration")),
            0,
        )

        lines.append(f"\n**{name}**")
        lines.append(f"  Spend: {spend:,.0f} VND | Imp: {impressions:,} | Clicks: {clicks:,}")
        lines.append(f"  CTR: {ctr:.2f}% | CPM: {cpm:,.0f} | CPC: {cpc:,.0f} | Frequency: {frequency:.1f}")

        # Video funnel metrics (từ FB API) — chỉ hiện nếu là video campaign
        if hook is not None or hold is not None:
            video_line = "  Video funnel:"
            if hook is not None:
                video_line += f" Hook Rate(VTR3s): {hook:.1f}%"
            if hold is not None:
                video_line += f" | Hold Rate(ThruPlay): {hold:.1f}%"
            lines.append(video_line)

        if conversions:
            cost_per_conv = spend / conversions if conversions else 0
            lines.append(f"  Conversions: {conversions} | Cost/Conv: {cost_per_conv:,.0f} VND")

    lines.append("")
    return "\n".join(lines)


def format_ad_level_for_analysis(insights: list[dict], period: str, top_n: int = 15) -> str:
    """Format breakdown ở CẤP AD (level='ad') thành bảng "Content Win" — xếp hạng
    theo leads để Claude đào sâu xuống TỪNG CREATIVE cụ thể.

    Khác với format_insights_for_analysis (cấp campaign — biết "kênh nào thắng"
    nhưng không biết "creative nào trong kênh đó đang kéo kết quả"), hàm này cho
    Claude thấy tên ad/post cụ thể + leads/CPL/CPM/Reach/Freq từng cái — đủ để trả
    lời "Post nào nên scale, Post nào đang ghì account xuống".
    """
    if not insights:
        return ""

    rows = []
    for r in insights:
        spend = float(r.get("spend") or 0)
        actions = r.get("actions") or []
        leads = next(
            (float(a.get("value") or 0) for a in actions if a.get("action_type") == "lead"),
            0.0,
        )
        rows.append({
            "ad_name":       r.get("ad_name") or "Unknown",
            "campaign_name": r.get("campaign_name") or "Unknown",
            "spend":         spend,
            "leads":         leads,
            "cpl":           round(spend / leads, 0) if leads > 0 else None,
            "cpm":           float(r.get("cpm") or 0),
            "reach":         float(r.get("reach") or 0),
            "frequency":     float(r.get("frequency") or 0),
        })

    ranked = sorted(rows, key=lambda a: a["leads"], reverse=True)[:top_n]
    with_leads = [a for a in ranked if a["leads"] > 0]
    cheapest = min(with_leads, key=lambda a: a["cpl"]) if with_leads else None

    lines = [
        f"### BREAKDOWN THEO AD — CONTENT WIN ({len(ranked)} ads, xếp hạng theo leads, period: {period})",
        "",
        "| Ad name | Campaign | Spend (VND) | Leads | CPL (VND) | CPM (VND) | Reach | Freq | Note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, a in enumerate(ranked):
        notes = []
        if a["leads"] > 0 and i == 0:
            notes.append("🏆 Win #1")
        elif a["leads"] > 0 and i == 1:
            notes.append("🏆 Win #2")
        if cheapest is a:
            notes.append("💰 CPL thấp nhất")
        cpl_str = f"{a['cpl']:,.0f}" if a["cpl"] is not None else "—"
        lines.append(
            f"| {a['ad_name']} | {a['campaign_name']} | {a['spend']:,.0f} | {a['leads']:.0f} "
            f"| {cpl_str} | {a['cpm']:,.0f} | {a['reach']:,.0f} | {a['frequency']:.2f} | {' · '.join(notes)} |"
        )
    return "\n".join(lines)


def is_available() -> bool:
    """Check nếu Marketing API đã được config."""
    return bool(FB_ACCESS_TOKEN and FB_AD_ACCOUNT_ID)


def has_token() -> bool:
    """Check chỉ cần token (cho Ads Library, không cần account ID)."""
    return bool(FB_ACCESS_TOKEN)


# ─────────────────────────────────────────────────────────────────
# Hierarchy getters — build 3-tier context for ads_optimizer
# ─────────────────────────────────────────────────────────────────

async def get_campaigns_with_adsets(
    ad_account_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> list[dict]:
    """Lấy campaigns + adsets nested theo hierarchy.

    Returns list of campaign dicts, each with "adsets" key chứa list adset dicts.
    """
    token = access_token or FB_ACCESS_TOKEN
    account_id = ad_account_id or FB_AD_ACCOUNT_ID
    if not token or not account_id:
        return []
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"

    params = {
        "fields": (
            "id,name,status,objective,daily_budget,lifetime_budget,"
            "adsets{id,name,status,daily_budget,lifetime_budget}"
        ),
        "effective_status": '["ACTIVE","PAUSED"]',
        "limit": 30,
        "access_token": token,
    }
    url = f"{FB_BASE_URL}/{account_id}/campaigns"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        logger.warning("get_campaigns_with_adsets: %s", response.text[:200])
        return []
    return response.json().get("data", [])


async def get_ads_by_adset(
    adset_id: str,
    access_token: Optional[str] = None,
) -> list[dict]:
    """Lấy ads trong một adset (ID + name + status)."""
    token = access_token or FB_ACCESS_TOKEN
    if not token:
        return []
    params = {
        "fields": "id,name,status,effective_status",
        "limit": 50,
        "access_token": token,
    }
    url = f"{FB_BASE_URL}/{adset_id}/ads"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        return []
    return response.json().get("data", [])


# ─────────────────────────────────────────────────────────────────
# Write operations — requires ads_management permission
# ─────────────────────────────────────────────────────────────────

# VND budget multiplier: FB API stores budgets as "smallest currency unit"
# For VND accounts: 100,000 VND → API value 10,000,000 (× 100)
_FB_BUDGET_MULTIPLIER = 100


async def set_object_status(
    object_id: str,
    status: str,   # "PAUSED" | "ACTIVE"
    access_token: Optional[str] = None,
) -> dict:
    """Pause hoặc activate campaign / adset / ad theo object_id.

    Cần permission: ads_management trên access token.
    """
    token = access_token or FB_ACCESS_TOKEN
    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN chưa setup")
    if status not in ("PAUSED", "ACTIVE"):
        raise ValueError(f"status phải là PAUSED hoặc ACTIVE, nhận: '{status}'")

    url = f"{FB_BASE_URL}/{object_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, data={"status": status, "access_token": token})

    data = response.json()
    if response.status_code != 200 or data.get("error"):
        err = data.get("error", {}).get("message", response.text)
        raise RuntimeError(f"FB set_status lỗi: {err}")

    logger.info("set_object_status: %s → %s | success=%s", object_id, status, data.get("success"))
    return data


async def update_budget(
    object_id: str,
    budget_type: str,   # "daily_budget" | "lifetime_budget"
    amount_vnd: int,    # user-facing VND (e.g. 500000 = 500k VND)
    access_token: Optional[str] = None,
) -> dict:
    """Cập nhật daily hoặc lifetime budget của campaign / adset.

    amount_vnd: số VND người dùng nhìn thấy (e.g. 500000 = 500,000 VND/ngày).
    API nhận: amount_vnd × _FB_BUDGET_MULTIPLIER.
    """
    token = access_token or FB_ACCESS_TOKEN
    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN chưa setup")
    if budget_type not in ("daily_budget", "lifetime_budget"):
        raise ValueError(f"budget_type phải là daily_budget hoặc lifetime_budget")

    api_amount = amount_vnd * _FB_BUDGET_MULTIPLIER

    url = f"{FB_BASE_URL}/{object_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, data={budget_type: api_amount, "access_token": token})

    data = response.json()
    if response.status_code != 200 or data.get("error"):
        err = data.get("error", {}).get("message", response.text)
        raise RuntimeError(f"FB update_budget lỗi: {err}")

    logger.info(
        "update_budget: %s | %s = %d VND (api=%d) | success=%s",
        object_id, budget_type, amount_vnd, api_amount, data.get("success"),
    )
    return data


def format_hierarchy_for_optimizer(
    campaigns: list[dict],
    account_id: str,
) -> str:
    """Convert campaigns+adsets hierarchy → structured text cho LLM phân tích."""
    if not campaigns:
        return "⚠️ Không có campaign nào đang ACTIVE hoặc PAUSED trong tài khoản."

    acc = account_id if account_id.startswith("act_") else f"act_{account_id}"
    lines = [f"## Hierarchy — {acc}", ""]

    for c in campaigns:
        cid = c.get("id", "?")
        cname = c.get("name", "Unknown Campaign")
        cstatus = c.get("status", "?")
        daily_b = c.get("daily_budget")
        life_b = c.get("lifetime_budget")
        budget_str = ""
        if daily_b:
            budget_str = f" | Daily: {int(daily_b) // _FB_BUDGET_MULTIPLIER:,} VND"
        elif life_b:
            budget_str = f" | Lifetime: {int(life_b) // _FB_BUDGET_MULTIPLIER:,} VND"

        lines.append(f"📊 **{cname}**")
        lines.append(f"   Campaign ID: `{cid}` | Status: {cstatus}{budget_str}")

        adsets = (c.get("adsets") or {}).get("data", [])
        for ads in adsets:
            aids = ads.get("id", "?")
            aname = ads.get("name", "Unknown AdSet")
            astatus = ads.get("status", "?")
            ads_daily = ads.get("daily_budget")
            ads_life = ads.get("lifetime_budget")
            ads_budget = ""
            if ads_daily:
                ads_budget = f" | Daily: {int(ads_daily) // _FB_BUDGET_MULTIPLIER:,} VND"
            elif ads_life:
                ads_budget = f" | Lifetime: {int(ads_life) // _FB_BUDGET_MULTIPLIER:,} VND"

            lines.append(f"   └── 📦 **{aname}**")
            lines.append(f"       AdSet ID: `{aids}` | Status: {astatus}{ads_budget}")

        lines.append("")

    return "\n".join(lines)
