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
