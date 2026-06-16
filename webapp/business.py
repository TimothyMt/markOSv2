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

        from agents.pipeline import run_targeted_pipeline, run_multi_agent_targeted
        try:
            from config import USE_MULTI_AGENT_PIPELINE
        except ImportError:
            USE_MULTI_AGENT_PIPELINE = False

        async def progress(msg):
            job["progress"] = str(msg)[:160]

        if task == "full" and USE_MULTI_AGENT_PIPELINE:
            agen = run_multi_agent_targeted(session, progress_callback=progress, phase="research")
        else:
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
