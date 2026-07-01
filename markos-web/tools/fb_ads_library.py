"""
Facebook Ads Library API wrapper.
Dùng cho skill "Theo Dõi Đối Thủ" (competitor_spy) — tìm ads đang chạy của đối thủ.

Docs: https://developers.facebook.com/docs/marketing-api/reference/ads_archive
Endpoint: GET /v20.0/ads_archive

Lưu ý:
- Public API — không cần user phải là admin của đối thủ
- Chỉ cần access_token hợp lệ (bất kỳ user token nào)
- Rate limit: ~200 req/hour với user token
"""
import logging
from typing import Optional
import httpx

from config import FB_ACCESS_TOKEN

logger = logging.getLogger(__name__)

FB_GRAPH_VERSION = "v20.0"
FB_BASE_URL = f"https://graph.facebook.com/{FB_GRAPH_VERSION}"


# ─────────────────────────────────────────────────────────────────
# Core search
# ─────────────────────────────────────────────────────────────────

async def search_competitor_ads(
    search_terms: str,
    country: str = "VN",
    ad_type: str = "ALL",
    limit: int = 20,
    access_token: Optional[str] = None,
) -> list[dict]:
    """Tìm ads đang chạy của đối thủ theo tên brand/keyword.

    Args:
        search_terms: Tên brand hoặc keyword, ví dụ: "Bitis Hunter"
        country: Mã quốc gia ISO2, mặc định "VN"
        ad_type: "ALL" | "POLITICAL_AND_ISSUE_ADS" | "HOUSING_ADS" | "EMPLOYMENT_ADS" | "CREDIT_ADS"
        limit: Số ads trả về (max 50 per request)
        access_token: Override token (mặc định dùng FB_ACCESS_TOKEN từ env)

    Returns:
        List of ad dicts với các fields: id, page_name, ad_creative_body,
        ad_creative_link_caption, ad_delivery_start_time, ad_delivery_stop_time,
        spend, impressions, currency, ad_snapshot_url
    """
    token = access_token or FB_ACCESS_TOKEN
    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN chưa setup trong env vars")

    params = {
        "search_terms": search_terms,
        "ad_reached_countries": country,
        "ad_type": ad_type,
        "fields": ",".join([
            "id",
            "page_name",
            "page_id",
            "ad_creative_bodies",
            "ad_creative_link_captions",
            "ad_creative_link_titles",
            "ad_delivery_start_time",
            "ad_delivery_stop_time",
            "ad_snapshot_url",
            "spend",
            "impressions",
            "currency",
            "publisher_platforms",
            "languages",
        ]),
        "limit": min(limit, 50),
        "access_token": token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{FB_BASE_URL}/ads_archive", params=params)

    if response.status_code != 200:
        error_data = response.json()
        error_msg = error_data.get("error", {}).get("message", response.text)
        logger.error(f"FB Ads Library API error: {error_msg}")
        raise RuntimeError(f"FB Ads Library lỗi: {error_msg}")

    data = response.json()
    ads = data.get("data", [])
    logger.info(f"Ads Library: tìm '{search_terms}' @ {country} → {len(ads)} ads")
    return ads


async def search_by_page_id(
    page_id: str,
    country: str = "VN",
    limit: int = 20,
    access_token: Optional[str] = None,
) -> list[dict]:
    """Tìm ads theo Page ID (chính xác hơn search_terms).

    Dùng khi đã biết Page ID của đối thủ (lấy từ URL Facebook Page của họ).
    """
    token = access_token or FB_ACCESS_TOKEN
    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN chưa setup trong env vars")

    params = {
        "search_page_ids": page_id,
        "ad_reached_countries": country,
        "ad_type": "ALL",
        "fields": ",".join([
            "id",
            "page_name",
            "page_id",
            "ad_creative_bodies",
            "ad_creative_link_captions",
            "ad_creative_link_titles",
            "ad_delivery_start_time",
            "ad_delivery_stop_time",
            "ad_snapshot_url",
            "spend",
            "impressions",
            "currency",
            "publisher_platforms",
        ]),
        "limit": min(limit, 50),
        "access_token": token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{FB_BASE_URL}/ads_archive", params=params)

    if response.status_code != 200:
        error_data = response.json()
        error_msg = error_data.get("error", {}).get("message", response.text)
        raise RuntimeError(f"FB Ads Library lỗi: {error_msg}")

    data = response.json()
    return data.get("data", [])


# ─────────────────────────────────────────────────────────────────
# Format helpers — chuẩn bị data cho Claude phân tích
# ─────────────────────────────────────────────────────────────────

def format_ads_for_analysis(ads: list[dict], competitor_name: str) -> str:
    """Convert raw FB API response → structured text cho Claude phân tích.

    Returns markdown-formatted string ready to inject vào system/user prompt.
    """
    if not ads:
        return f"**{competitor_name}**: Không tìm thấy ads đang chạy trong Ads Library."

    lines = [
        f"## Facebook Ads Library Data — {competitor_name}",
        f"**Tổng ads tìm được:** {len(ads)}",
        "",
    ]

    for i, ad in enumerate(ads[:15], 1):  # Cap ở 15 để không quá dài
        page_name = ad.get("page_name", "Unknown")
        bodies = ad.get("ad_creative_bodies") or []
        captions = ad.get("ad_creative_link_captions") or []
        titles = ad.get("ad_creative_link_titles") or []
        start = ad.get("ad_delivery_start_time", "")[:10] if ad.get("ad_delivery_start_time") else "?"
        stop = ad.get("ad_delivery_stop_time", "")
        status = "🟢 Đang chạy" if not stop else f"🔴 Đã dừng ({stop[:10]})"
        platforms = ", ".join(ad.get("publisher_platforms") or [])
        spend = ad.get("spend", {})
        spend_str = ""
        if spend:
            lower = spend.get("lower_bound", "?")
            upper = spend.get("upper_bound", "?")
            currency = ad.get("currency", "VND")
            spend_str = f" | Chi phí: {lower}–{upper} {currency}"

        lines.append(f"### Ad #{i} — {page_name}")
        lines.append(f"- **Status:** {status} (bắt đầu {start})")
        lines.append(f"- **Platform:** {platforms or 'Facebook/Instagram'}{spend_str}")

        if bodies:
            body_preview = bodies[0][:300] + ("..." if len(bodies[0]) > 300 else "")
            lines.append(f"- **Copy:**\n  > {body_preview}")

        if titles:
            lines.append(f"- **Headline:** {titles[0]}")

        if captions:
            lines.append(f"- **Caption/CTA:** {captions[0]}")

        lines.append("")

    return "\n".join(lines)


def is_available() -> bool:
    """Check nếu FB Ads Library đã được config."""
    return bool(FB_ACCESS_TOKEN)


# ─────────────────────────────────────────────────────────────────
# URL → page_id extraction
# ─────────────────────────────────────────────────────────────────

def _extract_fb_candidate(url: str) -> Optional[str]:
    """Extract the candidate identifier (slug or numeric id) from a FB URL.
    Does NOT pre-judge what it is — that's done by Graph API in resolve_fb_url.

    Examples:
      facebook.com/cocoonvn                  → "cocoonvn"
      facebook.com/profile.php?id=123        → "123"
      facebook.com/pages/Name/123            → "123"
      facebook.com/123456789                 → "123456789"
      facebook.com/groups/xyz                → "groups"  (caller checks via API)
    """
    import re as _re
    if not url:
        return None
    url = url.strip().rstrip("/")

    # profile.php?id=NUMERIC — used by New Pages Experience (FB ≥2022)
    # and also by user profiles. Both resolve via Graph API; numeric id is
    # the candidate.
    m = _re.search(r"profile\.php\?id=(\d+)", url)
    if m:
        return m.group(1)

    # /pages/Name/NUMERIC
    m = _re.search(r"/pages/[^/]+/(\d+)", url)
    if m:
        return m.group(1)

    # /{slug}  (first path segment after facebook.com/ or fb.com/)
    m = _re.search(r"(?:facebook|fb)\.com/([^/?#]+)", url)
    if not m:
        return None
    return m.group(1)


async def resolve_fb_url(url: str, access_token: Optional[str] = None) -> dict:
    """Resolve a Facebook URL via Graph API — distinguishes Page vs User vs
    missing. NEVER pre-judges based on URL pattern alone.

    Returns dict:
      {"ok": bool, "page_id": str|None, "page_name": str|None,
       "category": str|None, "reason": str, "detail": str}

    reason ∈ {"ok", "is_user", "not_found", "private", "no_token",
              "api_error", "invalid_url"}
    """
    if not url:
        return {"ok": False, "reason": "invalid_url", "detail": "URL rỗng",
                "page_id": None, "page_name": None, "category": None}

    candidate = _extract_fb_candidate(url)
    if not candidate:
        return {"ok": False, "reason": "invalid_url",
                "detail": f"Không extract được ID/slug từ {url}",
                "page_id": None, "page_name": None, "category": None}

    token = access_token or FB_ACCESS_TOKEN
    if not token:
        return {"ok": False, "reason": "no_token",
                "detail": "FB_ACCESS_TOKEN chưa set",
                "page_id": None, "page_name": None, "category": None}

    # Ask Graph API what this thing is. `category` is the discriminator:
    # Pages have it, users don't.
    params = {
        "fields": "id,name,category,link,fan_count,verification_status",
        "access_token": token,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{FB_BASE_URL}/{candidate}", params=params)
    except Exception as e:
        return {"ok": False, "reason": "api_error",
                "detail": f"Network/timeout khi gọi Graph API: {e}",
                "page_id": None, "page_name": None, "category": None}

    try:
        data = response.json()
    except Exception:
        data = {}

    if response.status_code == 200 and data.get("id"):
        category = data.get("category")
        page_name = data.get("name")
        page_id = data.get("id")
        if category:
            return {"ok": True, "reason": "ok",
                    "detail": f"Page '{page_name}' — {category}",
                    "page_id": page_id, "page_name": page_name,
                    "category": category}
        # 200 nhưng không có category → đây là user profile, không phải Page
        return {"ok": False, "reason": "is_user",
                "detail": f"`{page_name}` là user profile, không phải Page. "
                          "FB Ads Library chỉ phân tích Page (Page có category, "
                          "user không có).",
                "page_id": page_id, "page_name": page_name, "category": None}

    # Error path — surface real FB error
    error = (data or {}).get("error", {})
    err_msg = error.get("message") or response.text[:300]
    err_code = error.get("code")
    err_subcode = error.get("error_subcode")
    detail = f"FB Graph API: {err_msg} (code={err_code}, subcode={err_subcode})"

    if response.status_code == 404 or err_code == 803:
        return {"ok": False, "reason": "not_found", "detail": detail,
                "page_id": None, "page_name": None, "category": None}
    if response.status_code in (401, 403) or err_code in (10, 200, 190):
        return {"ok": False, "reason": "private", "detail": detail,
                "page_id": None, "page_name": None, "category": None}
    return {"ok": False, "reason": "api_error", "detail": detail,
            "page_id": None, "page_name": None, "category": None}


async def resolve_page_id_from_url(url: str, access_token: Optional[str] = None) -> Optional[str]:
    """Backwards-compat wrapper — returns page_id only, or None on any failure.
    New callers should use resolve_fb_url for structured errors."""
    result = await resolve_fb_url(url, access_token=access_token)
    return result["page_id"] if result.get("ok") else None
