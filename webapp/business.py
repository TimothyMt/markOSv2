"""
Lớp dữ liệu nghiệp vụ THẬT + trigger AI agent cho web dashboard.

Khác với store_* (bảng web_* mock-first), module này đọc trực tiếp các bảng
THẬT của bot trong cùng project Supabase (sessions/v2: users, profile,
campaigns, tracked_competitors, brand_voice, skill_runs) và gọi pipeline /
skill THẬT trong agents/.

Chỉ hoạt động khi có Supabase (cùng project với bot). Không có credentials
→ trả {"bizEnabled": False} và frontend tự ẩn phần dữ liệu thật.

Không phụ thuộc store backend — tái dùng client của storage.session (init lazy)
để mọi module storage/* và agents/* dùng chung 1 AsyncClient.
"""
import asyncio
import logging
import os
import re
import time

logger = logging.getLogger(__name__)

# AI agent jobs (in-memory — đủ nhẹ để nhét vào full_state cho SSE đẩy live)
_jobs: dict[str, dict] = {}
_JOB_LIMIT = 30

# task → nhãn hiển thị + skill key tương ứng trong skill_runs/results
TASK_LABELS = {
    "full":       "Phân tích toàn diện",
    "market":     "Nghiên cứu thị trường",
    "competitor": "Phân tích đối thủ",
    "customer":   "Customer Insight",
    "pricing":    "Định giá & Tâm lý",
    "swot":       "SWOT",
    "strategy":   "Chiến lược tổng hợp",
}

# skill_name (bot) → page id (web) để frontend map output thật vào đúng trang
SKILL_TO_PAGE = {
    "market_research":    "market",
    "competitor":         "competitor",
    "customer_insight":   "customer",
    "psychology_pricing": "pricing",
    "swot":               "swot",
    "synthesis":          "strategy",
    "tactical_playbook":  "strategy",
}

_EXCERPT = 600


def available() -> bool:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")
    return bool(url and key)


async def ensure_client():
    """Đảm bảo storage.session._client đã init (dùng chung cho storage/* + agents/*)."""
    from storage import session as s
    if s._client is None:
        await s.init_pool()
    return s._client


# ── Jobs ────────────────────────────────────────────────────────────
def jobs_public() -> list:
    return sorted(_jobs.values(), key=lambda j: j.get("started", 0), reverse=True)[:_JOB_LIMIT]


def _trim_jobs():
    if len(_jobs) > _JOB_LIMIT * 2:
        for k in sorted(_jobs, key=lambda k: _jobs[k].get("started", 0))[:_JOB_LIMIT]:
            _jobs.pop(k, None)


# ── Reads (real tables) ─────────────────────────────────────────────
async def list_users(limit: int = 50) -> list:
    try:
        c = await ensure_client()
        resp = (
            await c.table("users")
            .select("user_id,name,plan,token_quota,token_used,industry_cached,last_active_at")
            .is_("deleted_at", "null")
            .order("last_active_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("biz.list_users failed: %s", e)
        return []


async def pick_user_id(requested=None):
    """Chọn user đang xem: query param → env WEB_DEFAULT_USER_ID → user active gần nhất."""
    if requested not in (None, "", "null"):
        try:
            return int(requested)
        except (TypeError, ValueError):
            pass
    env = os.getenv("WEB_DEFAULT_USER_ID")
    if env:
        try:
            return int(env)
        except ValueError:
            pass
    users = await list_users(1)
    return users[0]["user_id"] if users else None


def _slim_run(r: dict) -> dict:
    content = r.get("content") or ""
    return {
        "id":          r.get("id"),
        "skill_name":  r.get("skill_name"),
        "page":        SKILL_TO_PAGE.get(r.get("skill_name")),
        "version":     r.get("version"),
        "rating":      r.get("rating"),
        "model_used":  r.get("model_used"),
        "tokens_used": r.get("tokens_used"),
        "created_at":  r.get("created_at"),
        "excerpt":     content[:_EXCERPT],
        "length":      len(content),
    }


def _bv_dict(bv) -> dict:
    if bv is None:
        return None
    return {
        "version":          getattr(bv, "version", 1),
        "do_rules":         getattr(bv, "do_rules", []) or [],
        "dont_rules":       getattr(bv, "dont_rules", []) or [],
        "tone_descriptors": getattr(bv, "tone_descriptors", []) or [],
        "banned_words":     getattr(bv, "banned_words", []) or [],
        "preferred_words":  getattr(bv, "preferred_words", []) or [],
        "industry_context": getattr(bv, "industry_context", None),
    }


async def biz_data(user_id=None) -> dict:
    """Dữ liệu nghiệp vụ thật cho frontend (gọi on-demand, KHÔNG để watcher poll)."""
    if not available():
        return {"bizEnabled": False}
    try:
        await ensure_client()
    except Exception as e:
        logger.warning("biz ensure_client failed: %s", e)
        return {"bizEnabled": False, "bizError": str(e)}

    users = await list_users()
    uid = await pick_user_id(user_id)
    out = {
        "bizEnabled": True,
        "bizUserId":  uid,
        "bizUsers":   users,
        "agentJobs":  jobs_public(),
    }
    if uid is None:
        return out

    from storage.v2 import profiles, campaigns_v2, skill_runs, users as users_mod
    from storage import tracked_competitors, brand_voice

    async def _safe(coro, default, label):
        try:
            return await coro
        except Exception as e:
            logger.warning("biz.%s failed: %s", label, e)
            return default

    out["bizProfile"]     = await _safe(profiles.get_profile(uid), None, "profile")
    out["bizUser"]        = await _safe(users_mod.get_user(uid), None, "user")
    out["bizCampaigns"]   = await _safe(campaigns_v2.list_campaigns_v2(uid, limit=20), [], "campaigns")
    out["bizCompetitors"] = await _safe(tracked_competitors.list_tracked_by_user(uid), [], "competitors")
    runs                  = await _safe(skill_runs.list_skill_runs(uid, limit=30), [], "skill_runs")
    bv                    = await _safe(brand_voice.get_brand_voice(uid), None, "brand_voice")

    slim = [_slim_run(r) for r in runs]
    out["bizSkillRuns"] = slim
    # latest run per skill_name (newest-first → first wins)
    latest: dict[str, dict] = {}
    for r in slim:
        latest.setdefault(r["skill_name"], r)
    out["bizLatest"]     = latest
    out["bizBrandVoice"] = _bv_dict(bv)
    return out


_market_kpi_cache: dict = {}


async def market_kpis(run_id: str = "") -> dict:
    """D-034 #2: trích TAM/SAM/SOM số THẬT từ output market_research (web-side, cache theo run).
    Thiếu/lỗi → {} (UI ẩn card, không bao giờ hiện số bịa)."""
    if not run_id:
        return {}
    if run_id in _market_kpi_cache:
        return _market_kpi_cache[run_id]
    run = await skill_run_content(run_id)
    content = (run or {}).get("content") or ""
    if not content.strip():
        return {}
    try:
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        system = (
            "Trích TAM/SAM/SOM từ báo cáo nghiên cứu thị trường dưới đây. "
            'Output JSON: {"tam":{"value":"","unit":"","note":""},"sam":{...},"som":{...}}. '
            "value = con số/khoảng ĐÚNG như báo cáo (vd '20-30' hoặc '5.700'); unit = đơn vị "
            "(vd 'tỷ USD/năm', 'tỷ VND'); note = cụm ngắn nếu có (vd 'ước tính'). "
            "🔴 CHỐNG BỊA: nếu báo cáo KHÔNG nêu số rõ cho mục nào → để value RỖNG. "
            "TUYỆT ĐỐI không tự tính/bịa số ngoài báo cáo. KHÔNG markdown wrapper."
        )
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=content[:6000], max_tokens=400)
        raw = (res or {}).get("output", "").strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```\s*$', '', raw).strip()
        data = _json.loads(raw)
        out = {}
        for k in ("tam", "sam", "som"):
            v = data.get(k) or {}
            if isinstance(v, dict) and str(v.get("value", "")).strip():
                out[k] = {"value": str(v.get("value", "")).strip(),
                          "unit": str(v.get("unit", "")).strip(),
                          "note": str(v.get("note", "")).strip()}
        if out:
            _market_kpi_cache[run_id] = out
        return out
    except Exception as e:
        logger.warning("biz.market_kpis failed (non-fatal): %s", e)
        return {}


async def skill_run_content(run_id: str) -> dict:
    """Lấy full content 1 skill_run (cho modal xem chi tiết)."""
    try:
        c = await ensure_client()
        resp = await c.table("skill_runs").select("*").eq("id", run_id).limit(1).execute()
        if resp.data:
            return resp.data[0]
    except Exception as e:
        logger.warning("biz.skill_run_content(%s) failed: %s", run_id, e)
    return {}


async def save_profile(user_id=None, fields: dict = None) -> dict:
    """Lưu hồ sơ doanh nghiệp (form-first entry). Tạo user nếu chưa có rồi upsert profile.

    No-auth (v1 demo): nếu chưa chọn được user → dùng WEB_DEFAULT_USER_ID, mặc định 1.
    """
    if not available():
        return {"error": "Chưa cấu hình Supabase — không lưu được hồ sơ."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            try:
                uid = int(os.getenv("WEB_DEFAULT_USER_ID") or 1)
            except ValueError:
                uid = 1
        clean = {k: v for k, v in (fields or {}).items() if v}
        from storage.v2 import users as users_mod, profiles
        await users_mod.upsert_user(user_id=uid, name=clean.get("business_name") or None)
        row = await profiles.upsert_profile(uid, **clean)
        return {"ok": True, "userId": uid, "profile": row}
    except Exception as e:
        logger.warning("biz.save_profile failed: %s", e)
        return {"error": str(e)}


_STRATEGIC_QS = {
    "jtbd": 'Khách "thuê" sản phẩm để hoàn thành việc gì (mua lúc/dịp nào, giải quyết chuyện gì)',
    "competitive_alternative": "Nếu không có brand này, khách dùng giải pháp thay thế nào / so sánh với ai",
    "differentiation": "Điểm khác biệt bền vững + bằng chứng (khách hay khen gì, vì sao quay lại)",
    "objection": "Rào cản / nỗi sợ lớn nhất khiến khách chần chừ (hay lo/hỏi/từ chối vì gì)",
    "competitors": "Tên đối thủ điển hình cùng ngách/địa bàn",
}


async def intake_suggestions(fields: dict = None) -> dict:
    """D-032 step 2 — sinh chip gợi ý cho câu chiến lược tầng CMO, bám
    ngành/sản phẩm/khách user đã nhập. Degrade an toàn: lỗi → {} (UI không chip).

    Returns: {jtbd:[...], competitive_alternative:[...], differentiation:[...],
              objection:[...], competitors:[...]}
    """
    f = fields or {}
    biz_ctx = "\n".join(filter(None, [
        f.get("business_name") and f"Tên: {f['business_name']}",
        f.get("industry") and f"Ngành: {f['industry']}",
        f.get("location") and f"Địa bàn: {f['location']}",
        f.get("product_service") and f"Sản phẩm/dịch vụ: {f['product_service']}",
        f.get("target_customer") and f"Khách mục tiêu: {f['target_customer']}",
    ]))
    if not biz_ctx.strip():
        return {}
    try:
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        qlist = "\n".join(f'- "{k}": {desc}' for k, desc in _STRATEGIC_QS.items())
        system = (
            "Bạn giúp founder Việt Nam điền hồ sơ marketing. Với MỖI câu chiến lược, "
            "đưa 3-4 GỢI Ý câu trả lời NGẮN (≤14 từ), cụ thể & đời thường theo đúng "
            "ngành/sản phẩm/khách của họ — để họ NHẬN RA và chọn (không phải tự nghĩ). "
            "🔴 CHỐNG BỊA: chỉ dùng tên đối thủ / nhân khẩu có cơ sở từ ngành; KHÔNG bịa "
            "số liệu, KHÔNG bịa brand không tồn tại. Gợi ý là 'phổ biến trong ngành' — "
            "founder chọn nếu đúng. Output JSON object: key = mã câu, value = mảng string. "
            "KHÔNG markdown wrapper."
        )
        user = f"# Business\n{biz_ctx}\n\n# Các câu cần gợi ý\n{qlist}\n\n# Output\nJSON: {{\"jtbd\":[...], ...}}"
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=user, max_tokens=900)
        raw = (res or {}).get("output", "").strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```\s*$', '', raw).strip()
        data = _json.loads(raw)
        # Chỉ giữ key hợp lệ + value là list string ngắn
        out = {}
        for k in _STRATEGIC_QS:
            v = data.get(k)
            if isinstance(v, list):
                out[k] = [str(x).strip() for x in v if str(x).strip()][:4]
        return out
    except Exception as e:
        logger.warning("biz.intake_suggestions failed (non-fatal): %s", e)
        return {}


async def intake_turn(user_id=None, message: str = "") -> dict:
    """Một lượt phỏng vấn AI-adaptive (Max hỏi thông minh) → dựng hồ sơ.

    Tái dùng agents.discovery.run_discovery_turn. Trả:
      {mode:'question', question}  — câu hỏi tiếp theo
      {mode:'complete'}            — đã đủ, đã lưu profile (v1 session + v2 profiles)
    """
    if not available():
        return {"error": "Chưa cấu hình Supabase — Max chưa phỏng vấn được."}
    try:
        await ensure_client()
    except Exception as e:
        return {"error": f"Không kết nối được Supabase: {e}"}
    uid = await pick_user_id(user_id)
    if uid is None:
        try:
            uid = int(os.getenv("WEB_DEFAULT_USER_ID") or 1)
        except ValueError:
            uid = 1
    from storage.session import get_session, save_session
    from agents.discovery import run_discovery_turn, apply_discovery_to_profile
    session = await get_session(uid)
    try:
        mode, payload = await run_discovery_turn(session, message or "")
    except Exception as e:
        logger.exception("intake_turn discovery failed")
        return {"error": f"Max chưa kết nối được mô hình AI: {e}"}

    if mode == "complete":
        apply_discovery_to_profile(session, payload or {})
        await save_session(session)
        try:
            from dataclasses import asdict
            from storage.v2 import users as users_mod, profiles
            clean = {k: v for k, v in asdict(session.profile).items() if v}
            await users_mod.upsert_user(user_id=uid, name=clean.get("business_name") or None)
            await profiles.upsert_profile(uid, **clean)
        except Exception as e:
            logger.warning("intake_turn profile upsert failed: %s", e)
        return {"mode": "complete", "userId": uid}

    await save_session(session)
    return {"mode": "question",
            "question": payload or "Kể cho Max nghe về doanh nghiệp của bạn nhé — bán gì, cho ai?",
            "userId": uid}


async def rate_skill_run(run_id: str, rating: int, feedback: str = None) -> dict:
    """Chấm điểm 1 output research (1–5) — feed vòng học của bot (skill_runs.rating)."""
    try:
        await ensure_client()
        from storage.v2 import skill_runs
        ok = await skill_runs.update_rating(run_id, int(rating), feedback)
        return {"ok": bool(ok)}
    except Exception as e:
        logger.warning("biz.rate_skill_run(%s) failed: %s", run_id, e)
        return {"error": str(e)}


async def save_skill_edit(user_id, skill_name: str, content: str) -> dict:
    """Lưu chỉnh sửa thành VERSION MỚI (không ghi đè bản cũ). Dùng cho sửa tay +
    'đặt làm hiện hành'. Tái dùng insert_skill_run (tự tăng version)."""
    if not (skill_name and content):
        return {"error": "Thiếu skill_name hoặc content."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import skill_runs
        row = await skill_runs.insert_skill_run(uid, skill_name, content, model_used="web-edit")
        return row or {"error": "Lưu thất bại."}
    except Exception as e:
        logger.warning("biz.save_skill_edit failed: %s", e)
        return {"error": str(e)}


async def list_skill_versions(user_id, skill_name: str) -> list:
    """Danh sách các version của 1 skill (mới→cũ) cho user."""
    if not skill_name:
        return []
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return []
        from storage.v2 import skill_runs
        runs = await skill_runs.list_skill_runs(uid, skill_name=skill_name, limit=50)
        return [{
            "id": r.get("id"), "version": r.get("version"), "rating": r.get("rating"),
            "model_used": r.get("model_used"), "created_at": r.get("created_at"),
            "length": len(r.get("content") or ""),
        } for r in runs]
    except Exception as e:
        logger.warning("biz.list_skill_versions failed: %s", e)
        return []


async def patch_skill_run(run_id: str, comment: str) -> dict:
    """Nhờ Max chỉnh 1 đoạn (surgical_edit.patch_document) → lưu version mới.

    Trả: {status:'ok', summary, run} | {status:'ask', question} | {status:'noop'} | {error}
    """
    if not comment:
        return {"error": "Thiếu yêu cầu chỉnh sửa."}
    try:
        await ensure_client()
        run = await skill_run_content(run_id)
        if not run:
            return {"error": "Không tìm thấy output."}
        from agents.surgical_edit import patch_document, summarize_changes, PATCH_OK, PATCH_ASK
        status, payload, meta = await patch_document(run.get("content") or "", comment)
        if status == PATCH_ASK:
            return {"status": "ask", "question": payload}
        if status != PATCH_OK:
            return {"status": "noop"}
        from storage.v2 import skill_runs
        row = await skill_runs.insert_skill_run(
            run["user_id"], run["skill_name"], payload, model_used="web-patch")
        return {"status": "ok", "summary": summarize_changes(meta), "run": row}
    except Exception as e:
        logger.warning("biz.patch_skill_run(%s) failed: %s", run_id, e)
        return {"error": str(e)}


# ── Ads data (đọc ads_snapshots + user_fb_connections) ──────────
async def ads_data(user_id=None, days: int = 7) -> dict:
    """Dữ liệu Ads thật: snapshots gần nhất + thông tin kết nối FB account.

    - Đọc ads_snapshots trong `days` ngày gần đây.
    - KHÔNG giải mã token / gọi FB API (chỉ đọc snapshot đã lưu).
    """
    if not available():
        return {"adsEnabled": False}
    try:
        c = await ensure_client()
    except Exception as e:
        return {"adsEnabled": False, "adsError": str(e)}

    uid = await pick_user_id(user_id)
    if uid is None:
        return {"adsEnabled": True, "adsUserId": None, "adsSnapshots": [], "adsFbConn": None}

    from datetime import datetime, timezone, timedelta

    async def _safe(coro, default, label):
        try:
            return await coro
        except Exception as e:
            logger.warning("biz.ads.%s failed: %s", label, e)
            return default

    # Kết nối FB (sanitize: bỏ token mã hóa, chỉ giữ meta)
    conn_raw = await _safe(
        c.table("user_fb_connections")
         .select("user_id,ad_account_id,account_name,expires_at,connected_at,notification_enabled,available_accounts,last_pull_at")
         .eq("user_id", uid).limit(1).execute(),
        None, "fb_conn"
    )
    fb_conn = conn_raw.data[0] if (conn_raw and conn_raw.data) else None

    # Snapshots trong `days` ngày gần đây
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    snap_raw = await _safe(
        c.table("ads_snapshots")
         .select("*")
         .eq("user_id", uid)
         .gte("snapshot_date", cutoff)
         .order("snapshot_date", desc=True)
         .limit(200)
         .execute(),
        None, "snapshots"
    )
    snaps = snap_raw.data if (snap_raw and snap_raw.data) else []

    # Tổng hợp KPI: gộp tất cả snapshot trong khoảng
    total_spend  = sum(s.get("spend",  0) or 0 for s in snaps)
    total_clicks = sum(s.get("clicks", 0) or 0 for s in snaps)
    total_impr   = sum(s.get("impressions", 0) or 0 for s in snaps)
    total_leads  = sum(s.get("leads",  0) or 0 for s in snaps)
    total_purch_val = sum(s.get("purchase_value", 0) or 0 for s in snaps)
    agg_roas = round(total_purch_val / total_spend, 2) if total_spend > 0 else 0
    agg_cpl  = round(total_spend / total_leads, 0) if total_leads > 0 else 0
    agg_cpm  = round(total_spend / total_impr * 1000, 0) if total_impr > 0 else 0
    agg_ctr  = round(total_clicks / total_impr * 100, 2) if total_impr > 0 else 0

    # Per-campaign summary (gộp theo campaign_id)
    camp_map: dict[str, dict] = {}
    for s in snaps:
        cid = s.get("campaign_id") or "unknown"
        if cid not in camp_map:
            camp_map[cid] = {
                "campaign_id":   cid,
                "campaign_name": s.get("campaign_name", cid),
                "spend": 0, "roas_sum": 0, "roas_count": 0,
                "impressions": 0, "clicks": 0, "leads": 0, "purchase_value": 0,
                "frequency": 0, "freq_count": 0,
            }
        m = camp_map[cid]
        m["spend"]         += s.get("spend", 0) or 0
        m["impressions"]   += s.get("impressions", 0) or 0
        m["clicks"]        += s.get("clicks", 0) or 0
        m["leads"]         += s.get("leads", 0) or 0
        m["purchase_value"] += s.get("purchase_value", 0) or 0
        if s.get("roas"):
            m["roas_sum"]   += s["roas"]; m["roas_count"] += 1
        if s.get("frequency"):
            m["frequency"]  += s["frequency"]; m["freq_count"] += 1

    campaigns_agg = []
    for m in camp_map.values():
        sp = m["spend"]
        pv = m["purchase_value"]
        roas = round(pv / sp, 2) if sp > 0 else (round(m["roas_sum"] / m["roas_count"], 2) if m["roas_count"] else 0)
        cpl  = round(sp / m["leads"], 0) if m["leads"] > 0 else 0
        freq = round(m["frequency"] / m["freq_count"], 1) if m["freq_count"] else 0
        campaigns_agg.append({
            "campaign_id":   m["campaign_id"],
            "campaign_name": m["campaign_name"],
            "spend":  sp,
            "roas":   roas,
            "cpl":    cpl,
            "impressions": m["impressions"],
            "clicks": m["clicks"],
            "leads":  m["leads"],
            "frequency": freq,
        })

    # Sort: winners (ROAS ≥ median) + losers (ROAS < median, có spend)
    spenders = [c for c in campaigns_agg if c["spend"] > 0]
    spenders.sort(key=lambda c: c["roas"], reverse=True)
    half = max(1, len(spenders) // 2)
    winners = spenders[:half]
    losers  = sorted(spenders[half:], key=lambda c: c["roas"])

    # Tổng hợp theo ngày cho biểu đồ (date → spend)
    daily: dict[str, dict] = {}
    for s in snaps:
        d = s.get("snapshot_date") or ""
        if d not in daily:
            daily[d] = {"date": d, "spend": 0, "roas": 0, "roas_count": 0}
        daily[d]["spend"] += s.get("spend", 0) or 0
        if s.get("roas"):
            daily[d]["roas"] += s["roas"]; daily[d]["roas_count"] += 1
    daily_chart = []
    for dd in sorted(daily.values(), key=lambda x: x["date"]):
        daily_chart.append({
            "date":  dd["date"],
            "spend": round(dd["spend"], 0),
            "roas":  round(dd["roas"] / dd["roas_count"], 2) if dd["roas_count"] else 0,
        })

    return {
        "adsEnabled":   True,
        "adsUserId":    uid,
        "adsDays":      days,
        "adsFbConn":    fb_conn,
        "adsKpi": {
            "spend":  round(total_spend,  0),
            "roas":   agg_roas,
            "cpl":    agg_cpl,
            "cpm":    agg_cpm,
            "ctr":    agg_ctr,
            "clicks": int(total_clicks),
            "leads":  int(total_leads),
        },
        "adsWinners":    winners[:5],
        "adsLosers":     losers[:5],
        "adsCampaigns":  spenders,
        "adsDaily":      daily_chart,
        "adsSnapshots":  snaps[:50],
    }


# ── Facebook OAuth (kết nối Ads từ web) ─────────────────────────────
async def fb_connect_url(user_id=None) -> dict:
    """Tạo link FB OAuth cho user. User bấm → approve → /oauth/fb/callback lưu token.

    Cần server đã cấu hình FB_APP_ID + WEBHOOK_BASE_URL (redirect URI đã đăng ký
    với Facebook App). Khi web mount chung server với bot, callback có sẵn; web
    standalone cần mount /oauth/fb/callback (run_web.py đã làm).
    """
    if not available():
        return {"error": "Supabase chưa cấu hình."}
    try:
        from config import FB_APP_ID, WEBHOOK_BASE_URL
    except Exception:
        FB_APP_ID = WEBHOOK_BASE_URL = ""
    if not FB_APP_ID or not WEBHOOK_BASE_URL:
        return {"error": "Server chưa cấu hình Facebook App (FB_APP_ID + WEBHOOK_BASE_URL)."}
    uid = await pick_user_id(user_id)
    if uid is None:
        return {"error": "Chưa có user nào để kết nối."}
    try:
        await ensure_client()
        from services.fb_oauth import build_oauth_url
        url = await build_oauth_url(uid)
        return {"url": url, "userId": uid}
    except Exception as e:
        logger.warning("fb_connect_url failed: %s", e)
        return {"error": f"Không tạo được link kết nối: {e}"}


# ── Agent trigger ───────────────────────────────────────────────────
async def run_agent(user_id=None, task: str = "full") -> dict:
    """Khởi chạy pipeline/skill THẬT cho 1 user trong background. Trả jobId ngay."""
    if not available():
        return {"error": "Supabase chưa cấu hình — không thể chạy AI agent."}
    if task not in TASK_LABELS:
        return {"error": f"Tác vụ không hợp lệ: {task}"}
    try:
        await ensure_client()
    except Exception as e:
        return {"error": f"Không kết nối được Supabase: {e}"}
    uid = await pick_user_id(user_id)
    if uid is None:
        return {"error": "Chưa có user nào trong hệ thống để chạy phân tích."}

    job_id = f"job-{int(time.time() * 1000)}"
    job = {
        "id":       job_id,
        "userId":   uid,
        "task":     task,
        "label":    TASK_LABELS.get(task, task),
        "status":   "running",
        "progress": "Đang khởi tạo…",
        "started":  time.time(),
        "finished": None,
        "summary":  None,
        "error":    None,
    }
    _jobs[job_id] = job
    _trim_jobs()
    asyncio.create_task(_execute(job))
    return {"jobId": job_id, "job": job}


async def _execute(job: dict):
    uid = job["userId"]
    task = job["task"]
    try:
        await ensure_client()
        from storage.session import get_session, save_session

        session = await get_session(uid)
        session.selected_task = task

        try:
            from tools.token_tracker import begin_job
            begin_job(session)
        except Exception:
            pass

        from agents.pipeline import run_targeted_pipeline

        async def progress(msg):
            job["progress"] = str(msg)[:160]

        # Web chạy NON-INTERACTIVE: dùng run_targeted_pipeline cho mọi task.
        # task="full" → cả 8 bước (gồm SYNTHESIS) → ra chiến lược, lưu skill_runs.
        # Multi-agent (research-only + 8 câu hỏi) chỉ hợp luồng chat của bot,
        # không hợp 1 cú bấm trên web. (DECISIONS D-015)
        agen = run_targeted_pipeline(session, progress_callback=progress)

        done: list[str] = []
        async for stage_key, _result in agen:
            if stage_key in ("pipeline_abort", "quota_stop"):
                job["progress"] = f"Dừng: {stage_key}"
                break
            done.append(stage_key)
            job["progress"] = f"Hoàn tất bước: {stage_key}"

        await save_session(session)
        job["status"] = "done"
        job["summary"] = (
            f"Hoàn tất {len(done)} bước: {', '.join(done)}" if done else "Hoàn tất."
        )
    except Exception as e:
        logger.exception("AI agent job failed (user=%s task=%s)", uid, task)
        job["status"] = "error"
        job["error"] = str(e)[:300]
    finally:
        job["finished"] = time.time()
        try:
            from webapp import notify as tg
            if job["status"] == "done":
                await tg.notify(
                    f"🤖 <b>AI Agent</b> hoàn tất: {job['label']} (user <code>{uid}</code>).\n{job.get('summary') or ''}"
                )
            else:
                await tg.notify(
                    f"⚠️ <b>AI Agent</b> lỗi: {job['label']} (user <code>{uid}</code>) — {job.get('error')}"
                )
        except Exception:
            pass
