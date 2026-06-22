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
    "research":   "Nghiên cứu (T1-T3)",
    "strategize": "Lập chiến lược (T4-T5)",
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
    "occasion_brief":     "occasion",
    "retention_playbook": "occasion",
    "winback_playbook":   "occasion",
    "calendar_post":      "calendar",
    "post_channels":      "calendar",
    "video_script":       "calendar",
    "ugc_brief":          "calendar",
    "ads_copy":           "adscopy",
    "email_zalo_sequence":"sequence",
    "sales_inbox_script": "inbox",
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


async def save_gate(user_id=None, wedge: str = "", usp_stance: str = "", usp_text: str = "",
                    horizon: str = "", posture: str = "") -> dict:
    """D-041 + M5-B2: lưu lựa chọn GATE trước khi lập chiến lược.

    Gồm: phân khúc (wedge) + định vị (USP) + horizon (nhịp roadmap) + posture
    (nghiêng brand/activation). horizon/posture optional — bỏ trống = 'auto'
    (để Max tự cân theo bối cảnh khi sinh synthesis). Lưu vào intake_extra để
    strategize_web đọc; cũng nằm trong _strategy_fp nên đổi là cache vô hiệu.
    """
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles
        cur = await profiles.get_profile(uid) or {}
        extra = cur.get("intake_extra") or {}
        if not isinstance(extra, dict):
            extra = {}
        if (wedge or "").strip():
            extra["wedge"] = wedge.strip()
        # horizon: '30' | '60' | '90' | 'auto'(mặc định). posture: 'brand' | 'balanced'
        # | 'activation' | 'auto'(mặc định). Giá trị lạ → 'auto' (không hardcode hành vi).
        hz = (horizon or "").strip().lower()
        extra["horizon"] = hz if hz in ("30", "60", "90") else "auto"
        ps = (posture or "").strip().lower()
        extra["posture"] = ps if ps in ("brand", "balanced", "activation") else "auto"
        fields = {"intake_extra": extra}
        if usp_stance in ("clear", "draft", "missing"):
            extra["usp_stance"] = usp_stance
            fields["usp_confidence"] = usp_stance
            if usp_stance == "clear" and (usp_text or "").strip():
                fields["usp"] = usp_text.strip()
        row = await profiles.upsert_profile(uid, **fields)
        return {"ok": True, "profile": row}
    except Exception as e:
        logger.warning("biz.save_gate failed: %s", e)
        return {"error": str(e)}


async def approve_synthesis(user_id=None) -> dict:
    """M4(1): founder CHỐT bản Chiến lược hiện tại. Lưu version đã duyệt vào
    intake_extra.synthesis_approved_version. Tạo lại synthesis → version đổi → tự bỏ
    chốt (FE so version để biết). Là checkpoint chiến lược trước khi xuống chiến dịch."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, skill_runs
        run = await skill_runs.get_latest_skill_run(uid, "synthesis")
        if not run or not (run.get("content") or "").strip():
            return {"error": "Chưa có Chiến lược để chốt."}
        cur = await profiles.get_profile(uid) or {}
        extra = cur.get("intake_extra") or {}
        if not isinstance(extra, dict):
            extra = {}
        extra["synthesis_approved_version"] = run.get("version")
        row = await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "version": run.get("version"), "profile": row}
    except Exception as e:
        logger.warning("biz.approve_synthesis failed: %s", e)
        return {"error": str(e)}


async def save_pillars(user_id=None, pillars=None) -> dict:
    """M4(2): founder CHỐT tuyến nền (curate). Lưu danh sách pillar đã GIỮ vào
    intake_extra.pillars_locked → campaign_plan/calendar dùng bản này. Gửi list rỗng
    hoặc None = BỎ chốt (quay lại để Max tự sinh)."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles
        cur = await profiles.get_profile(uid) or {}
        extra = cur.get("intake_extra") or {}
        if not isinstance(extra, dict):
            extra = {}
        if pillars and isinstance(pillars, list):
            # chỉ giữ field cần thiết, chặn payload rác
            clean = []
            for p in pillars[:12]:
                if not isinstance(p, dict):
                    continue
                clean.append({
                    "name": str(p.get("name") or "")[:120],
                    "role": str(p.get("role") or "")[:240],
                    "funnel": str(p.get("funnel") or "")[:40],
                    "cadence": str(p.get("cadence") or "")[:120],
                    "angles": [str(a)[:200] for a in (p.get("angles") or [])][:6],
                })
            extra["pillars_locked"] = clean
        else:
            extra.pop("pillars_locked", None)   # bỏ chốt
        row = await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "locked": len(extra.get("pillars_locked") or []), "profile": row}
    except Exception as e:
        logger.warning("biz.save_pillars failed: %s", e)
        return {"error": str(e)}


_market_kpi_cache: dict = {}


async def _latest_content(uid: int, skill_name: str) -> str:
    """Content của skill_run mới nhất theo skill_name (cho campaign_plan)."""
    try:
        c = await ensure_client()
        resp = (await c.table("skill_runs").select("content")
                .eq("user_id", uid).eq("skill_name", skill_name)
                .order("version", desc=True).limit(1).execute())
        if resp.data:
            return resp.data[0].get("content") or ""
    except Exception as e:
        logger.warning("_latest_content(%s) failed: %s", skill_name, e)
    return ""


def _strategy_fp(*parts) -> int:
    """M5-B1 — chữ ký NGUỒN chiến lược + input, dùng làm khoá cache.

    Mọi downstream (campaign_plan / occasion / retention) đọc Synthesis + Tactical
    + wedge/USP/ngành (+ horizon/posture sau này). Trước đây các cache chỉ băm 1
    phần synthesis (hoặc bỏ hẳn) → đổi NGUỒN mà cache giữ output CŨ → lệch. Gộp tất
    cả nguồn vào 1 chữ ký để đổi bất kỳ nguồn nào là cache tự vô hiệu.
    """
    return hash(tuple((p if p is not None else "") for p in parts))


_campaign_plan_cache: dict = {}


def _apply_pillar_lock(out: dict, locked) -> dict:
    """M4(2): nếu founder đã CHỐT tuyến nền → trả pillars đã chốt (overlay lên bản
    sinh), giữ occasions từ bản sinh. Lock đổi KHÔNG cần bust cache generation."""
    if locked and isinstance(locked, list):
        return {**out, "pillars": locked, "pillars_locked": True}
    return out


async def campaign_plan(user_id=None, steer: str = "") -> dict:
    """D-040: sinh content PILLARS (Always-on) + gợi ý OCCASION theo ngành — từ
    Synthesis + Tactical + industry context (Byron Sharp + Binet&Field). Cache; degrade {}.

    M4(2): nếu founder đã chốt tuyến nền (intake_extra.pillars_locked) và KHÔNG có
    steer → trả pillars đã chốt. steer = định hướng thêm khi 'sinh lại có định hướng'
    (bỏ qua lock, sinh mới để founder curate rồi chốt lại)."""
    if not available():
        return {}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {}
        synth = await _latest_content(uid, "synthesis")
        if not synth.strip():
            return {}   # cần Chiến lược (T4) trước
        tact = await _latest_content(uid, "tactical_playbook")
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        industry = prof.get("industry") or ""
        _extra = prof.get("intake_extra") or {}
        wedge = (_extra.get("wedge") if isinstance(_extra, dict) else "") or ""
        horizon = (_extra.get("horizon") if isinstance(_extra, dict) else "") or ""
        posture = (_extra.get("posture") if isinstance(_extra, dict) else "") or ""
        locked = (_extra.get("pillars_locked") if isinstance(_extra, dict) else None)
        steer = (steer or "").strip()
        # M5-B1: khoá theo TRỌN nguồn (synth+tact+wedge+industry+horizon+posture+steer),
        # không chỉ synth[:300] — đổi wedge/định vị/horizon là pillars sinh lại.
        cache_key = f"{uid}:{_strategy_fp(synth, tact, wedge, industry, horizon, posture, steer)}"
        if cache_key in _campaign_plan_cache:
            out = _campaign_plan_cache[cache_key]
            return out if steer else _apply_pillar_lock(out, locked)
        ictx = ""
        try:
            from frameworks.industry_context import INDUSTRY_CONTEXT
            ic = INDUSTRY_CONTEXT.get((industry or "").lower())
            if ic:
                ictx = f"Archetype mua hàng: {ic.purchase_archetype}. Động lực/mùa vụ ngành: {ic.market_dynamics[:450]}"
        except Exception:
            pass
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        system = (
            "Bạn là CMO lập kế hoạch 2 TUYẾN marketing theo marketing hiện đại (Byron Sharp = "
            "hiện diện liên tục để được nhớ; Binet&Field 60/40 brand/activation). Từ Chiến lược + "
            "Tactical + bối cảnh NGÀNH, sinh:\n"
            "(1) 4-6 content PILLARS cho ALWAYS-ON (nền chạy đều, KHÔNG gắn dịp) — bám USP/JTBD/"
            "archetype/wedge; mỗi pillar có vai + tầng phễu + nhịp đăng + vài góc bài.\n"
            "(2) 3-5 gợi ý OCCASION (đợt theo dịp) hợp MÙA VỤ của ngành (đọc kỹ động lực/mùa vụ).\n"
            'Output JSON đúng schema: {"pillars":[{"name":"","role":"","funnel":"TOFU|MOFU|BOFU",'
            '"cadence":"","angles":["",""]}],"occasions":[{"name":"","when":"","why":""}]}.\n'
            "🔴 Bám đúng NGÀNH + wedge; KHÔNG bịa số/ngân sách (always-on KHÔNG chốt SMART). KHÔNG markdown."
        )
        steer_block = (f"\n\n# ĐỊNH HƯỚNG THÊM TỪ FOUNDER (ưu tiên bám)\n{steer}" if steer else "")
        user = (f"# Ngành\n{industry}\n{ictx}\n\n# Wedge (tệp ưu tiên đã chọn)\n{wedge or '(chưa chọn — tự suy)'}\n\n"
                f"# Chiến lược (Synthesis)\n{synth[:3500]}\n\n# Tactical Playbook\n{(tact or '(chưa có)')[:2500]}"
                f"{steer_block}")
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=user, max_tokens=1600)
        raw = (res or {}).get("output", "").strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```\s*$', '', raw).strip()
        data = _json.loads(raw)
        out = {"pillars": data.get("pillars") or [], "occasions": data.get("occasions") or []}
        if out["pillars"] or out["occasions"]:
            _campaign_plan_cache[cache_key] = out
        return out if steer else _apply_pillar_lock(out, locked)
    except Exception as e:
        logger.warning("biz.campaign_plan failed (non-fatal): %s", e)
        return {}


_occasion_cache: dict = {}

# M1.1+ (D-044): "mục đích đợt" = trục WHY (khác trục WHEN always-on/occasion).
# Định hình brief — KHÔNG phải loại campaign mới. Founder chọn; mặc định auto (Max suy).
OCCASION_OBJECTIVES = {
    "acquisition": "Kéo KHÁCH MỚI (demand-gen): nặng TOFU/MOFU, mở rộng reach, lead/CPL là KPI chính; offer hút thử.",
    "conversion":  "CHỐT ĐƠN (activation spike): nặng BOFU, ROAS/CPA/doanh số là KPI chính; offer mạnh, deadline gấp.",
    "brand":       "ĐẨY NHẬN BIẾT (the long): reach/tần suất/nhớ thương hiệu, KHÔNG ép chốt; ưu tiên thông điệp định vị.",
    "retention":   "GIỮ & TĂNG TẦN SUẤT khách CŨ: nhắm tệp đã mua, tăng repeat/AOV/CLV; ưu đãi loyalty, KHÔNG đốt ngân sách acquisition.",
}


async def occasion_draft(user_id=None, occasion: str = "", window_start: str = "",
                         window_end: str = "", budget: str = "", baseline: str = "",
                         goal: str = "", objective: str = "") -> dict:
    """M1.1 (D-043/044): sinh Campaign Brief cho 1 ĐỢT theo dịp — web-side 1 LLM call.

    Kế thừa Synthesis (la bàn) + Tactical (cách đánh) + industry (mùa vụ/archetype)
    + wedge/USP đã chọn ở gate, GHÉP lever đợt (dịp/window/ngân sách/baseline/MỤC ĐÍCH)
    → chốt SMART THẬT (D-029). Baseline 'chưa rõ' → SMART để KHOẢNG + nhãn (ước tính),
    KHÔNG chặn (Founder 2026-06-21). objective = trục WHY (D-044) định hình brief.
    Trả Markdown brief; degrade {}.
    """
    if not available() or not (occasion or "").strip():
        return {}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {}
        synth = await _latest_content(uid, "synthesis")
        if not synth.strip():
            return {}   # cần Chiến lược (T4) trước
        tact = await _latest_content(uid, "tactical_playbook")
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        industry = prof.get("industry") or ""
        extra = prof.get("intake_extra") or {}
        wedge = (extra.get("wedge") if isinstance(extra, dict) else "") or ""
        usp = prof.get("usp") or ""
        has_base = bool((baseline or "").strip())
        obj_key = (objective or "").strip().lower()
        obj_hint = OCCASION_OBJECTIVES.get(obj_key, "")
        horizon = (extra.get("horizon") if isinstance(extra, dict) else "") or ""
        posture = (extra.get("posture") if isinstance(extra, dict) else "") or ""
        # M5-B1: trước đây key KHÔNG băm synthesis → đổi chiến lược, brief đợt vẫn cũ.
        # Thêm chữ ký nguồn (synth+tact+wedge+usp+ngành+horizon+posture) vào key.
        src_fp = _strategy_fp(synth, tact, wedge, usp, industry, horizon, posture)
        cache_key = f"{uid}:{src_fp}:{hash((occasion, window_start, window_end, budget, baseline, goal, obj_key))}"
        if cache_key in _occasion_cache:
            return _occasion_cache[cache_key]
        ictx = ""
        try:
            from frameworks.industry_context import INDUSTRY_CONTEXT
            ic = INDUSTRY_CONTEXT.get((industry or "").lower())
            if ic:
                ictx = (f"Archetype mua hàng: {ic.purchase_archetype}. "
                        f"Động lực/mùa vụ ngành: {ic.market_dynamics[:450]}")
        except Exception:
            pass
        from tools.llm_router import call as router_call, TaskType
        base_rule = (
            "Founder ĐÃ cung cấp baseline → SMART phải có CON SỐ MỤC TIÊU cụ thể, suy từ baseline."
            if has_base else
            "Founder CHƯA có baseline → SMART để dạng KHOẢNG (vd '+15-25%') và gắn nhãn "
            "'(ước tính — chưa có baseline)'. TUYỆT ĐỐI không bịa con số tuyệt đối chắc nịch."
        )
        system = (
            "Bạn là CMO lập Campaign Brief cho 1 ĐỢT theo dịp (occasion = activation spike "
            "ngắn hạn, Binet&Field 'the short'), CHỒNG lên always-on (không thay nền). Brief "
            "kế thừa la bàn (Synthesis) + cách đánh (Tactical) + mùa vụ NGÀNH, GHÉP lever đợt → "
            "chốt SMART THẬT. Cấu trúc đợt = arc theo thời gian:\n"
            "Teaser (hé lộ) → Build-up (nuôi) → Peak (ngày dịp, đẩy mạnh) → Last-call (chốt gấp) "
            "→ After (hậu mãi/winback). Mỗi pha bám archetype ngành + tầng phễu (TOFU hút mới → "
            "BOFU chốt).\n\n"
            "Xuất MARKDOWN gồm các mục:\n"
            "## 1. Mục tiêu SMART (đợt này)\n"
            "## 2. Arc 5 pha theo timeline (bảng: Pha | Thời gian | Mục tiêu pha | Kênh | Góc copy)\n"
            "## 3. KPI cần theo dõi (có target nếu có baseline)\n"
            "## 4. Phân bổ ngân sách đợt (theo pha)\n"
            "## 5. Lưu ý nhất quán (đợt này có lệch wedge/định vị chính không? — nhắc nhẹ nếu có)\n\n"
            f"🔴 SMART: {base_rule}\n"
            "🔴 MỤC ĐÍCH đợt (nếu founder chọn) định hình TRỌNG TÂM phễu + KPI + loại offer của "
            "cả arc — bám đúng, đừng lệch sang mục đích khác.\n"
            "🔴 Bám đúng dịp + mùa vụ + văn hoá ngành. Tôn trọng wedge/USP founder đã chọn "
            "(nếu lever cho thấy đợt nhắm tệp khác → vẫn làm theo founder, chỉ NHẮC ở mục 5). "
            "KHÔNG bịa số ngoài lever/baseline."
        )
        user = (
            f"# Ngành\n{industry}\n{ictx}\n\n"
            f"# Wedge (tệp ưu tiên — la bàn)\n{wedge or '(chưa chọn)'}\n"
            f"# USP\n{usp or '(chưa rõ)'}\n\n"
            f"# Lever ĐỢT NÀY\n- Dịp: {occasion}\n- Window: {window_start or '?'} → {window_end or '?'}\n"
            f"- Ngân sách đợt: {budget or '(chưa nhập)'}\n- Baseline hiện tại: {baseline or '(chưa rõ)'}\n"
            f"- Mục tiêu chính founder muốn: {goal or '(theo giai đoạn roadmap)'}\n"
            f"- MỤC ĐÍCH đợt: {obj_hint or '(founder chưa chọn — tự suy mục đích hợp dịp + giai đoạn)'}\n\n"
            f"# Chiến lược (Synthesis — la bàn)\n{synth[:3000]}\n\n"
            f"# Tactical Playbook (cách đánh)\n{(tact or '(chưa có)')[:2000]}"
        )
        res = await router_call(task_type=TaskType.OPS_BRIEF, system=system,
                                user=user, max_tokens=2600)
        brief = (res or {}).get("output", "").strip()
        if not brief:
            return {}
        out = {"brief": brief, "occasion": occasion,
               "window_start": window_start, "window_end": window_end,
               "budget": budget, "baseline": baseline, "has_baseline": has_base,
               "objective": obj_key}
        _occasion_cache[cache_key] = out
        return out
    except Exception as e:
        logger.warning("biz.occasion_draft failed (non-fatal): %s", e)
        return {}


async def save_occasion(user_id=None, occasion: str = "", window_start: str = "",
                        window_end: str = "", budget: str = "", goal: str = "",
                        brief: str = "", objective: str = "") -> dict:
    """M1.1 (D-044): lưu Campaign Brief đợt → skill_runs (occasion_brief) + campaigns.

    Tái dùng hạ tầng có sẵn (skill_runs cho doc-reader/patch; campaigns cho record),
    KHÔNG cần migration. primary_goal = mục đích (WHY tag) → goal cụ thể (fallback).
    Trả {ok, campaign, run_id} | {error}.
    """
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if not (occasion or "").strip() or not (brief or "").strip():
        return {"error": "Thiếu dịp hoặc brief để lưu."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import skill_runs, profiles, campaigns_v2
        run = await skill_runs.insert_skill_run(uid, "occasion_brief", brief, model_used="web-occasion")
        run_id = (run or {}).get("id")
        prof = await profiles.get_profile(uid) or {}
        obj = (objective or "").strip().lower()
        # primary_goal = WHY tag (mục đích) nếu founder chọn, fallback goal cụ thể
        primary_goal = (obj if obj in OCCASION_OBJECTIVES else "") or (goal or "").strip() or None
        camp = await campaigns_v2.create_campaign(
            uid,
            name=occasion.strip(),
            industry=prof.get("industry"),
            primary_goal=primary_goal,
            offer_lever=(budget or "").strip() or None,
            start_date=(window_start or "").strip() or None,
            end_date=(window_end or "").strip() or None,
            summary=brief[:500],
            brief_skill_run_id=run_id,
        )
        return {"ok": True, "campaign": camp, "run_id": run_id}
    except Exception as e:
        logger.warning("biz.save_occasion failed: %s", e)
        return {"error": str(e)}


# ── M2.1 (D-045): Retention/Lifecycle — cẩm nang if-then, KHÔNG cần order data ──
_retention_cache: dict = {}

# 2 chế độ cùng 1 module (D-045 mục 8). retention = full lifecycle giữ chân;
# winback = chuyên kéo khách đã rời bỏ quay lại.
RETENTION_MODES = {
    "retention": ("Giữ chân & tăng tần suất",
                  "Cẩm nang theo VÒNG ĐỜI khách (mới → active/repeat → at-risk chậm lại). "
                  "Mục tiêu tăng repeat rate / AOV / CLV. Ưu tiên owned media (rẻ), KHÔNG đốt ads acquisition."),
    "winback":   ("Kéo khách cũ quay lại",
                  "Cẩm nang WIN-BACK khách đã rời bỏ (lapsed/churned). Sequence chạm tăng dần "
                  "(nhắc nhẹ → lý do quay lại → ưu đãi mạnh có hạn). Mục tiêu reactivation rate."),
}


async def retention_draft(user_id=None, mode: str = "retention", cycle: str = "",
                          channels: str = "", offer: str = "") -> dict:
    """M2.1 (D-045): sinh CẨM NANG if-then giữ chân/winback — web-side 1 LLM call.

    KHÔNG cần order data: Max đưa bảng 'dấu hiệu nhận biết → hành động → kênh → tin mẫu',
    founder tự đối chiếu khách rồi áp tay. Ngưỡng thời gian = ước tính theo chu kỳ NGÀNH
    + nhãn (founder chỉnh). Kế thừa Synthesis + industry archetype. Degrade {}.
    """
    if not available():
        return {}
    m = (mode or "retention").strip().lower()
    if m not in RETENTION_MODES:
        m = "retention"
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {}
        synth = await _latest_content(uid, "synthesis")
        if not synth.strip():
            return {}   # cần Chiến lược (T4) trước
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        industry = prof.get("industry") or ""
        extra = prof.get("intake_extra") or {}
        wedge = (extra.get("wedge") if isinstance(extra, dict) else "") or ""
        usp = prof.get("usp") or ""
        horizon = (extra.get("horizon") if isinstance(extra, dict) else "") or ""
        posture = (extra.get("posture") if isinstance(extra, dict) else "") or ""
        # M5-B1: băm TRỌN synthesis (+ wedge/usp/ngành) thay vì synth[:200].
        src_fp = _strategy_fp(synth, wedge, usp, industry, horizon, posture)
        cache_key = f"{uid}:{m}:{src_fp}:{hash((cycle, channels, offer))}"
        if cache_key in _retention_cache:
            return _retention_cache[cache_key]
        ictx = ""
        try:
            from frameworks.industry_context import INDUSTRY_CONTEXT
            ic = INDUSTRY_CONTEXT.get((industry or "").lower())
            if ic:
                ictx = (f"Archetype mua hàng: {ic.purchase_archetype}. "
                        f"Động lực/chu kỳ ngành: {ic.market_dynamics[:400]}")
        except Exception:
            pass
        label, mode_hint = RETENTION_MODES[m]
        from tools.llm_router import call as router_call, TaskType
        system = (
            f"Bạn là CMO lập CẨM NANG {label.upper()} cho founder Việt Nam — "
            "tuyến RETENTION (behavior-triggered, KHÁC occasion theo lịch). "
            f"{mode_hint}\n\n"
            "🔴 RÀNG BUỘC CỐT LÕI: founder KHÔNG có dữ liệu đơn hàng. Đừng yêu cầu data, đừng "
            "giả định có hệ thống. Thay vào đó đưa cẩm nang FOUNDER TỰ NHÌN RA & ÁP TAY:\n"
            "Xuất MARKDOWN:\n"
            "## 1. Bảng cẩm nang theo tình huống\n"
            "Bảng cột: Tình huống khách (DẤU HIỆU founder tự nhận biết bằng mắt) | Nên làm gì | "
            "Kênh (owned: Zalo/SMS/gọi/email) | Tin nhắn mẫu (copy sẵn dùng được, đúng giọng ngành)\n"
            "→ phủ các giai đoạn vòng đời hợp mode. Dấu hiệu phải CỤ THỂ, đời thường "
            "(vd 'mua đều rồi ~3 tuần không quay lại'), KHÔNG phải thuật ngữ RFM.\n"
            "## 2. KPI tự theo dõi thủ công (repeat/AOV/tỉ lệ quay lại — cách đếm mộc, không cần phần mềm)\n"
            "## 3. Mẹo nhịp & ưu tiên (làm gì trước với nguồn lực nhỏ)\n\n"
            "🔴 Ngưỡng thời gian (vd '3 tuần', '2 tháng') để dạng '≈ X× chu kỳ mua TB của ngành' "
            "+ nhãn '(ước tính — chỉnh theo thực tế)'. TUYỆT ĐỐI không bịa số đo lường chắc nịch.\n"
            "🔴 Bám USP/wedge + archetype ngành. Tin mẫu đúng văn hoá VN, ngắn, gửi được ngay."
        )
        user = (
            f"# Ngành\n{industry}\n{ictx}\n\n"
            f"# Wedge (tệp ưu tiên)\n{wedge or '(chưa chọn)'}\n# USP\n{usp or '(chưa rõ)'}\n\n"
            f"# Lever (founder cung cấp — đều optional)\n"
            f"- Chu kỳ mua điển hình: {cycle or '(chưa rõ — tự suy theo ngành)'}\n"
            f"- Kênh owned đang có: {channels or '(chưa rõ — gợi ý kênh phổ biến VN)'}\n"
            f"- Ưu đãi loyalty sẵn có: {offer or '(chưa có — gợi ý loại phù hợp)'}\n\n"
            f"# Chiến lược (Synthesis — la bàn)\n{synth[:2800]}"
        )
        res = await router_call(task_type=TaskType.OPS_BRIEF, system=system, user=user, max_tokens=2600)
        brief = (res or {}).get("output", "").strip()
        if not brief:
            return {}
        out = {"brief": brief, "mode": m, "label": label,
               "cycle": cycle, "channels": channels, "offer": offer}
        _retention_cache[cache_key] = out
        return out
    except Exception as e:
        logger.warning("biz.retention_draft failed (non-fatal): %s", e)
        return {}


async def save_retention(user_id=None, mode: str = "retention", cycle: str = "",
                         channels: str = "", offer: str = "", brief: str = "") -> dict:
    """M2.1: lưu cẩm nang → skill_runs (retention_playbook/winback_playbook) + campaigns."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if not (brief or "").strip():
        return {"error": "Thiếu cẩm nang để lưu."}
    m = (mode or "retention").strip().lower()
    if m not in RETENTION_MODES:
        m = "retention"
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import skill_runs, profiles, campaigns_v2
        skill_name = "winback_playbook" if m == "winback" else "retention_playbook"
        run = await skill_runs.insert_skill_run(uid, skill_name, brief, model_used="web-retention")
        run_id = (run or {}).get("id")
        prof = await profiles.get_profile(uid) or {}
        camp = await campaigns_v2.create_campaign(
            uid,
            name=RETENTION_MODES[m][0],
            industry=prof.get("industry"),
            primary_goal=m,                      # WHY tag: retention / winback
            offer_lever=(offer or "").strip() or None,
            summary=brief[:500],
            brief_skill_run_id=run_id,
        )
        return {"ok": True, "campaign": camp, "run_id": run_id}
    except Exception as e:
        logger.warning("biz.save_retention failed: %s", e)
        return {"error": str(e)}


# ── M1.2 (D-017/018/019): Lịch nội dung 2-track — nối campaign thật ──
_CAL_COLORS = ["#f59e0b", "#ef4444", "#ec4899", "#8b5cf6", "#0ea5e9", "#10b981"]


def _week_of(date_str: str, anchor):
    """Tuần (1-based) của 1 ngày so với anchor (đầu tuần hiện tại). None nếu parse lỗi."""
    from datetime import date
    try:
        y, m, d = (int(x) for x in str(date_str)[:10].split("-"))
        delta = (date(y, m, d) - anchor).days
        return delta // 7 + 1
    except Exception:
        return None


async def calendar_plan(user_id=None) -> dict:
    """M1.2: ghép lịch 2-track THẬT = always-on pillars (D-040) + occasion bands (window thật).

    Anchor = thứ Hai tuần hiện tại; map start/end_date của campaign → tuần. Campaign không
    window (retention) KHÔNG lên lịch. Degrade {} (FE giữ mock). Tái dùng campaign_plan +
    list_campaigns_v2 (KHÔNG nhân bản)."""
    if not available():
        return {}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {}
        from datetime import date, timedelta
        today = date.today()
        anchor = today - timedelta(days=today.weekday())   # thứ Hai tuần này

        from storage.v2 import campaigns_v2
        camps_raw = await campaigns_v2.list_campaigns_v2(uid, limit=30)
        bands = []
        max_week = 4
        for i, c in enumerate(camps_raw or []):
            sd, ed = c.get("start_date"), c.get("end_date")
            if not sd or not ed:
                continue   # retention/winback (không window) → không lên lịch tuần
            fw, tw = _week_of(sd, anchor), _week_of(ed, anchor)
            if fw is None or tw is None or tw < 1:
                continue   # parse lỗi hoặc đã qua hoàn toàn
            fw = max(1, fw); tw = max(fw, tw)
            max_week = max(max_week, tw)
            color = _CAL_COLORS[i % len(_CAL_COLORS)]
            name = c.get("name") or "Đợt"
            offer = c.get("offer_lever") or ""
            mid = (fw + tw) // 2
            posts = [{"week": fw, "day": 2, "title": f"Khởi động {name}"}]
            if mid != fw:
                posts.append({"week": mid, "day": 3, "title": f"Đẩy mạnh {name}"})
            posts.append({"week": tw, "day": 4, "title": f"Chốt — ngày cuối {name}"})
            bands.append({"name": name, "occasion": c.get("primary_goal") or "đợt",
                          "offer": offer or "ưu đãi đợt", "color": color,
                          "fromWeek": fw, "toWeek": tw, "posts": posts,
                          "campaignId": c.get("id"), "briefRunId": c.get("brief_skill_run_id")})

        # Always-on từ pillars thật (D-040) — lặp mỗi tuần, phủ 7 slot ngày
        plan = await campaign_plan(uid)
        pillars = (plan or {}).get("pillars") or []
        always = []
        if pillars:
            for d in range(7):
                p = pillars[d % len(pillars)]
                angles = p.get("angles") or []
                title = (angles[d % len(angles)] if angles else p.get("role")) or p.get("name") or "Bài brand"
                always.append({"pillar": p.get("name") or "Pillar", "title": title})

        if not bands and not always:
            return {}   # chưa có gì thật → FE giữ mock
        return {"days": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
                "weeks": max_week, "alwaysOn": always, "campaigns": bands}
    except Exception as e:
        logger.warning("biz.calendar_plan failed (non-fatal): %s", e)
        return {}


async def gen_calendar_post(user_id=None, track: str = "always", pillar: str = "",
                            campaign_id: str = "", week: str = "", day: str = "") -> dict:
    """M1.2b: sinh 1 BÀI cho slot lịch — bám pillar (always-on) hoặc brief occasion (campaign).
    Lưu skill_run `calendar_post`. Degrade {error}."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        industry = prof.get("industry") or ""
        usp = prof.get("usp") or ""
        ctx, kind = "", ""
        if track == "camp" and campaign_id:
            from storage.v2 import campaigns_v2
            c = await campaigns_v2.get_campaign(campaign_id) or {}
            brief = ""
            if c.get("brief_skill_run_id"):
                run = await skill_run_content(c["brief_skill_run_id"])
                brief = (run or {}).get("content") or c.get("summary") or ""
            ctx = f"Đợt: {c.get('name','')}. Brief:\n{brief[:1800]}"
            kind = "1 bài ĐẨY OFFER cho đợt (có CTA, tạo hành động)"
        else:
            ctx = f"Content pillar (always-on, nền brand): {pillar or '(brand)'}"
            kind = "1 bài NỀN brand bám pillar (KHÔNG ép bán, xây nhận biết/niềm tin)"
        from tools.llm_router import call as router_call, TaskType
        system = (
            "Bạn là copywriter mạng xã hội Việt Nam. Viết " + kind + " — đăng được NGAY:\n"
            "- Hook 1 dòng đầu bắt mắt.\n- Thân bài ngắn (2-4 câu), giọng đời thường, hợp ngành.\n"
            "- CTA cuối phù hợp.\n- 3-5 hashtag.\n"
            "🔴 Bám USP + ngành. KHÔNG bịa số/khuyến mãi không có trong brief. Trả MARKDOWN gọn."
        )
        user = f"# Ngành\n{industry}\n# USP\n{usp or '(chưa rõ)'}\n\n# Bối cảnh slot\n{ctx}"
        res = await router_call(task_type=TaskType.OPS_CONTENT_CREATIVE, system=system, user=user, max_tokens=700)
        content = (res or {}).get("output", "").strip()
        if not content:
            return {"error": "Chưa sinh được bài — thử lại."}
        from storage.v2 import skill_runs
        run = await skill_runs.insert_skill_run(uid, "calendar_post", content, model_used="web-calendar")
        return {"ok": True, "content": content, "run_id": (run or {}).get("id")}
    except Exception as e:
        logger.warning("biz.gen_calendar_post failed: %s", e)
        return {"error": str(e)}


# M3.1 (hybrid): biến thể PHÁI SINH từ 1 bài — đa kênh / video / UGC (gộp vào Lịch)
_DERIVATIVES = {
    "channels": ("post_channels", "CHANNEL_ADAPT",
                 "Chuyển thể 1 BÀI gốc sang 3 kênh: Facebook, TikTok (script ngắn), Zalo OA. Giữ "
                 "thông điệp lõi, đổi giọng/định dạng/độ dài hợp từng kênh + gợi ý hashtag/CTA mỗi kênh."),
    "video":    ("video_script", "OPS_CONTENT_CREATIVE",
                 "Biến 1 BÀI/ý thành KỊCH BẢN VIDEO ngắn (Reel/TikTok 15-30s): chia cảnh theo timeline "
                 "(Hook 0-3s → Body → Proof → CTA), gợi ý hình ảnh + text overlay + nhạc trend."),
    "ugc":      ("ugc_brief", "OPS_BRIEF",
                 "Biến 1 BÀI/ý thành UGC BRIEF cho creator: concept, thông điệp bắt buộc, do/don't, "
                 "phân tầng Micro/Mid/KOL (góc quay + CTA), khung nội dung gợi ý."),
}


async def gen_derivative(user_id=None, kind: str = "channels", source: str = "") -> dict:
    """M3.1: sinh biến thể từ 1 bài gốc (kind: channels/video/ugc). Lưu skill_run. Degrade {error}."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if not (source or "").strip():
        return {"error": "Chưa có bài gốc để chuyển thể."}
    if kind not in _DERIVATIVES:
        return {"error": f"Loại biến thể không hợp lệ: {kind}"}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        skill_name, task_name, instruction = _DERIVATIVES[kind]
        from tools.llm_router import call as router_call, TaskType
        task = getattr(TaskType, task_name, TaskType.OPS_CONTENT_CREATIVE)
        system = (
            "Bạn là copywriter/đạo diễn nội dung Việt Nam. " + instruction + "\n"
            "🔴 Bám đúng bài gốc + ngành; KHÔNG bịa số/khuyến mãi mới ngoài bài gốc. Trả MARKDOWN gọn, dùng được ngay."
        )
        user = f"# Ngành\n{prof.get('industry') or ''}\n# USP\n{prof.get('usp') or '(chưa rõ)'}\n\n# BÀI GỐC\n{source[:2500]}"
        res = await router_call(task_type=task, system=system, user=user, max_tokens=1200)
        content = (res or {}).get("output", "").strip()
        if not content:
            return {"error": "Chưa sinh được biến thể — thử lại."}
        from storage.v2 import skill_runs
        run = await skill_runs.insert_skill_run(uid, skill_name, content, model_used="web-derive")
        return {"ok": True, "content": content, "run_id": (run or {}).get("id"), "kind": kind}
    except Exception as e:
        logger.warning("biz.gen_derivative(%s) failed: %s", kind, e)
        return {"error": str(e)}


# M3.2 (hybrid): trang đặc thù — sinh THẬT bám strategy/USP (KHÔNG phái sinh từ 1 bài)
_ASSETS = {
    "ads_copy": ("ads_copy", "OPS_CONTENT_CREATIVE", 1300,
                 "Viết BỘ ADS COPY theo phễu cho chạy quảng cáo. Chia 3 nhóm: "
                 "TOFU (nhận biết — hook gây chú ý, đánh nỗi đau/khao khát), "
                 "MOFU (cân nhắc — chứng minh giá trị/khác biệt USP, social proof), "
                 "BOFU (chốt đơn — offer rõ, CTA mạnh, khử rủi ro). Mỗi nhóm 2-3 mẫu: "
                 "primary text + headline ngắn. Gợi ý đối tượng nhắm cho mỗi tầng."),
    "sequence": ("email_zalo_sequence", "OPS_CONTENT_BULK", 1400,
                 "Viết CHUỖI NURTURE Email/Zalo (4-6 bước) cho lead/khách mới. Mỗi bước: "
                 "thời điểm gửi (D0/D2/D5…), mục tiêu, tiêu đề/dòng mở, nội dung ngắn, CTA. "
                 "Đi từ welcome → trao giá trị → social proof → offer → winback. Giọng hợp ngành."),
    "inbox": ("sales_inbox_script", "OPS_CONTENT_CREATIVE", 1200,
              "Viết KỊCH BẢN CHAT bán hàng (Messenger/Zalo/IG) xử lý các tình huống: hỏi giá, "
              "chê đắt, để suy nghĩ, so sánh đối thủ, ở xa/giao hàng. Mỗi tình huống: câu khách "
              "thường nói → cách phản hồi (công nhận → giá trị/USP → chốt nhẹ). Giọng thân thiện, chuyên nghiệp."),
}


async def gen_content_asset(user_id=None, kind: str = "ads_copy") -> dict:
    """M3.2: sinh tài sản content đặc thù (ads_copy/sequence/inbox) bám strategy+USP. Lưu skill_run."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if kind not in _ASSETS:
        return {"error": f"Loại nội dung không hợp lệ: {kind}"}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, skill_runs
        prof = await profiles.get_profile(uid) or {}
        if not (prof.get("industry") or prof.get("product_service")):
            return {"error": "Chưa có hồ sơ (ngành/sản phẩm) — hoàn tất Hồ sơ doanh nghiệp trước."}
        skill_name, task_name, max_tok, instruction = _ASSETS[kind]
        # bám chiến lược tổng hợp nếu đã chạy (giúp copy đúng định vị/đối tượng)
        strat = await skill_runs.get_latest_skill_run(uid, "synthesis") or \
            await skill_runs.get_latest_skill_run(uid, "tactical_playbook") or {}
        strat_ctx = (strat.get("content") or "")[:1800]
        from tools.llm_router import call as router_call, TaskType
        task = getattr(TaskType, task_name, TaskType.OPS_CONTENT_CREATIVE)
        system = (
            "Bạn là copywriter/sales trưởng người Việt. " + instruction + "\n"
            "🔴 Bám USP + ngành + định vị; KHÔNG bịa số/khuyến mãi không có thật. Trả MARKDOWN gọn, dùng được ngay."
        )
        user = (f"# Ngành\n{prof.get('industry') or ''}\n# Sản phẩm/Dịch vụ\n{prof.get('product_service') or ''}\n"
                f"# USP\n{prof.get('usp') or '(chưa rõ)'}\n# Khách mục tiêu\n{prof.get('target_customer') or '(chưa rõ)'}"
                + (f"\n\n# Chiến lược (tham chiếu)\n{strat_ctx}" if strat_ctx else ""))
        res = await router_call(task_type=task, system=system, user=user, max_tokens=max_tok)
        content = (res or {}).get("output", "").strip()
        if not content:
            return {"error": "Chưa sinh được nội dung — thử lại."}
        run = await skill_runs.insert_skill_run(uid, skill_name, content, model_used="web-asset")
        return {"ok": True, "content": content, "run_id": (run or {}).get("id"), "kind": kind}
    except Exception as e:
        logger.warning("biz.gen_content_asset(%s) failed: %s", kind, e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# M5: WEB-OWNED strategy generation (Synthesis + Tactical Playbook)
# Thay cho synthesis của pipeline bot — bot là tham khảo, sẽ rebuild để hỗ trợ web
# (không sửa agents/). Điểm khác cốt lõi: horizon LINH HOẠT + tách ĐỊNH VỊ (bền)
# khỏi ROADMAP (theo kỳ) + nghiêng theo POSTURE; ưu tiên để LLM tự cân, hạn chế hardcode.
# ─────────────────────────────────────────────────────────────────────────────
_RESEARCH_SKILLS = ["market_research", "competitor", "customer_insight", "swot"]


def _horizon_guide(hz: str) -> str:
    """Dịch lựa chọn horizon của founder → chỉ dẫn cho LLM (KHÔNG bảng cứng stage→ngày).
    'auto' = giao LLM tự chọn nhịp hợp bối cảnh."""
    if hz in ("30", "60", "90"):
        return (f"Founder CHỌN nhịp roadmap = {hz} NGÀY. Chia pha vừa khít {hz} ngày "
                f"(số pha hợp lý theo độ dài), không co kéo sang mốc khác.")
    return ("Founder để 'tự động' → BẠN tự chọn nhịp roadmap hợp giai đoạn doanh nghiệp "
            "dựa trên research (gợi ý vùng 30/60/90 ngày, hoặc dài hơn nếu thực sự hợp). "
            "Ghi RÕ ở đầu mục Roadmap: chọn bao nhiêu ngày + 1 câu vì sao (bám stage/dòng tiền/chu kỳ mua).")


def _posture_guide(ps: str) -> str:
    """Dịch posture (cán cân the-long/the-short) → chỉ dẫn nghiêng trọng tâm."""
    if ps == "brand":
        return ("Posture: NGHIÊNG XÂY NHẬN BIẾT (the long). Roadmap & trục nội dung ưu tiên "
                "phủ/được nhớ/định vị; activation (đẩy đơn) là phụ. Nói rõ đánh đổi: chậm thấy đơn hơn.")
    if ps == "activation":
        return ("Posture: NGHIÊNG RA ĐƠN NGAY (the short). Roadmap & trục nội dung dồn về chuyển đổi "
                "/offer/BOFU; xây nhận biết giữ mức tối thiểu. Nói rõ đánh đổi: nền thương hiệu mỏng hơn.")
    if ps == "balanced":
        return "Posture: CÂN BẰNG ~60/40 brand/activation (Binet&Field) — vừa xây nhớ vừa có đơn."
    return ("Posture để 'tự động' → BẠN tự cân the-long/the-short hợp giai đoạn + bối cảnh dòng tiền "
            "(DN mới/cạn vốn có thể cần đơn sớm; DN có nền nên đầu tư nhận biết). Nêu 1 câu lý do.")


async def strategize_web(user_id=None, progress=None) -> dict:
    """M5 — Web-OWNED: sinh Chiến lược (Synthesis) + Tactical Playbook.

    Đọc research đã có (T1-T3 + SWOT) + gate (wedge/USP/horizon/posture) → 2 LLM call
    bằng prompt RIÊNG của web:
      (1) Synthesis (markdown): TÁCH 'Định vị (bền)' khỏi 'Roadmap (theo horizon)',
          nghiêng theo posture, horizon 'auto' để LLM tự chọn nhịp.
      (2) Tactical Playbook (markdown): cách đánh per-segment theo phễu, bám synthesis.
    Lưu skill_run 'synthesis' + 'tactical_playbook'. Degrade {error}.
    """
    async def _say(msg):
        if progress:
            try:
                r = progress(msg)
                if hasattr(r, "__await__"):
                    await r
            except Exception:
                pass

    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, skill_runs
        prof = await profiles.get_profile(uid) or {}
        # Research là ĐẦU VÀO bắt buộc (web không tự chạy research — pipeline lo phần đó)
        research = {}
        for sk in _RESEARCH_SKILLS:
            research[sk] = await _latest_content(uid, sk)
        if not (research.get("market_research") or research.get("competitor")
                or research.get("customer_insight") or research.get("swot")):
            return {"error": "Chưa có nghiên cứu (T1-T3) — hãy chạy nghiên cứu trước khi lập chiến lược."}

        extra = prof.get("intake_extra") or {}
        if not isinstance(extra, dict):
            extra = {}
        wedge = extra.get("wedge") or ""
        horizon = (extra.get("horizon") or "auto")
        posture = (extra.get("posture") or "auto")
        usp_stance = extra.get("usp_stance") or "draft"
        usp = prof.get("usp") or ""
        industry = prof.get("industry") or ""

        ictx = ""
        try:
            from frameworks.industry_context import INDUSTRY_CONTEXT
            ic = INDUSTRY_CONTEXT.get((industry or "").lower())
            if ic:
                ictx = (f"Archetype mua hàng: {ic.purchase_archetype}. "
                        f"Động lực/mùa vụ ngành: {ic.market_dynamics[:500]}")
        except Exception:
            pass

        from tools.llm_router import call as router_call, TaskType

        # USP stance: 'clear'=giữ USP founder · 'draft'=Max làm sắc · 'missing'=tự đề xuất
        usp_rule = {
            "clear": f"Founder GIỮ USP của họ: \"{usp}\". Bám sát, chỉ tinh chỉnh câu chữ, KHÔNG đổi ý.",
            "draft": (f"Founder muốn Max LÀM SẮC định vị" + (f" (USP gốc: \"{usp}\")" if usp else "")
                      + ". Đề xuất câu định vị sắc hơn nhưng trung thành tinh thần gốc."),
        }.get(usp_stance, "Founder chưa có USP rõ → BẠN đề xuất định vị dựa trên research + khác biệt tìm được.")

        # ───────── (1) SYNTHESIS ─────────
        await _say("Đang lập Chiến lược (định vị + roadmap)…")
        syn_system = (
            "Bạn là CỐ VẤN chiến lược marketing 10 năm cho founder Việt ('sếp') — KHÔNG ra lệnh, "
            "trình bày khuyến nghị + lý do + đánh đổi để sếp quyết. Từ research (thị trường/đối thủ/"
            "khách/SWOT) + định hướng founder, viết Chiến lược MARKDOWN, TÁCH RÕ 2 tầng thời gian:\n\n"
            "## 1. Định vị (BỀN — ít đổi theo thời gian)\n"
            "Câu định vị 1 dòng (cho ai · là gì · khác vì sao) + SAVE (Solution/Access/Value/Education) "
            "+ JTBD (khách 'thuê' sản phẩm để làm gì). Đây là LA BÀN sống lâu, KHÔNG gắn mốc thời gian.\n"
            "## 2. Mũi nhọn (Wedge)\n"
            "Tệp khách đánh TRƯỚC + tối đa 2 kênh + ≥2 thứ NÊN TẠM GÁC (kèm vì sao) + lý do (bám giả thuyết research).\n"
            "## 3. Roadmap (theo NHỊP đã chọn — cuốn chiếu, sẽ làm lại mỗi kỳ)\n"
            "Chia pha theo nhịp; mỗi pha: trọng tâm 1 câu + chỉ số ĐỊNH HƯỚNG cần nhìn (đo gì, KHÔNG target "
            "số cứng nếu chưa có baseline). Đây là phần NGẮN HẠN, tách khỏi định vị ở mục 1.\n"
            "## 4. KPI cần theo dõi (3-5, tên KPI hợp ngành, vì sao)\n"
            "## 5. Tiêu chí đổi hướng (nếu [chỉ số] < [ngưỡng] sau [thời gian] → cân nhắc pivot)\n"
            "## 6. Tóm tắt khuyến nghị (4-6 câu, giọng em-sếp, đóng khung 'đề xuất — sếp quyết')\n\n"
            f"🧭 NHỊP ROADMAP: {_horizon_guide(horizon)}\n"
            f"⚖️ {_posture_guide(posture)}\n"
            f"🎯 ĐỊNH VỊ: {usp_rule}\n"
            "🔴 Bám archetype + mùa vụ ngành nếu có. KHÔNG bịa số tuyệt đối. Tệp ưu tiên = wedge founder chọn "
            "(nếu có). Diễn đạt tự nhiên, đừng quăng thuật ngữ trần (archetype/SAVE) mà không giải thích."
        )
        syn_user = (
            f"# Ngành\n{industry}\n{ictx}\n\n"
            f"# Định hướng founder\n- Wedge (tệp ưu tiên): {wedge or '(chưa chọn — tự đề xuất theo research)'}\n"
            f"- Nhịp roadmap: {horizon}\n- Posture: {posture}\n\n"
            f"# Nghiên cứu thị trường\n{(research.get('market_research') or '(chưa có)')[:3000]}\n\n"
            f"# Phân tích đối thủ\n{(research.get('competitor') or '(chưa có)')[:2500]}\n\n"
            f"# Customer Insight\n{(research.get('customer_insight') or '(chưa có)')[:2500]}\n\n"
            f"# SWOT\n{(research.get('swot') or '(chưa có)')[:2000]}"
        )
        syn_res = await router_call(task_type=TaskType.SYNTHESIS_LONG_CONTEXT,
                                    system=syn_system, user=syn_user, max_tokens=3200)
        synthesis = (syn_res or {}).get("output", "").strip()
        if not synthesis:
            return {"error": "Chưa lập được chiến lược — thử lại."}
        syn_run = await skill_runs.insert_skill_run(uid, "synthesis", synthesis, model_used="web-strategize")

        # ───────── (2) TACTICAL PLAYBOOK ─────────
        await _say("Đang viết Tactical Playbook (cách đánh chi tiết)…")
        tac_system = (
            "Bạn là CMO senior viết TACTICAL PLAYBOOK — cách đánh CHI TIẾT theo từng tệp khách, bám "
            "Chiến lược (synthesis) + SWOT đã có. Xương sống: mỗi tệp = phễu TOFU/MOFU/BOFU, mỗi tầng "
            "vài mũi tactic. Tệp ƯU TIÊN (wedge) viết đầy đủ nhất (đủ 3 tầng); tệp phụ gọn (mỗi tầng 1 mũi). "
            "Mỗi mũi có: góc/insight, COPY MẪU (quote dùng được), kênh cụ thể, khung THỬ NGHIỆM (cấu trúc test "
            "+ ngưỡng theo chỉ số TƯƠNG ĐỐI: CTR/ROAS/CVR + thời lượng), KPI cần theo dõi.\n"
            "🔴 KHÔNG ghi số tiền tuyệt đối (ngân sách thật chốt khi lập chiến dịch). KPI nêu ĐO GÌ, không chốt target.\n"
            "🔴 Bám archetype ngành; PHỦ HẾT các tệp (đừng cụt). Kết bằng bảng tổng hợp (Tệp|Tầng|Mũi chính|Mức đầu tư định tính).\n"
            "Xuất MARKDOWN, giọng CMO thẳng thắn."
        )
        tac_user = (
            f"# Ngành\n{industry}\n{ictx}\n\n"
            f"# Chiến lược (Synthesis — vừa lập)\n{synthesis[:3500]}\n\n"
            f"# SWOT\n{(research.get('swot') or '(chưa có)')[:2200]}\n\n"
            f"# Customer Insight (để hiểu tệp)\n{(research.get('customer_insight') or '(chưa có)')[:1800]}"
        )
        tac_res = await router_call(task_type=TaskType.OPS_BRIEF,
                                    system=tac_system, user=tac_user, max_tokens=3600)
        tactical = (tac_res or {}).get("output", "").strip()
        tac_run = None
        if tactical:
            tac_run = await skill_runs.insert_skill_run(uid, "tactical_playbook", tactical, model_used="web-strategize")
        else:
            logger.warning("strategize_web: tactical rỗng (uid=%s) — synthesis vẫn lưu", uid)

        return {"ok": True,
                "synthesis_run_id": (syn_run or {}).get("id"),
                "tactical_run_id": (tac_run or {}).get("id"),
                "horizon": horizon, "posture": posture}
    except Exception as e:
        logger.exception("biz.strategize_web failed (uid=%s)", user_id)
        return {"error": str(e)}


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

        async def progress(msg):
            job["progress"] = str(msg)[:160]

        # M5: Synthesis + Tactical do WEB sở hữu (strategize_web) — horizon linh hoạt,
        # tách định vị bền/roadmap, posture-aware. KHÔNG qua pipeline bot (bot = tham
        # khảo, sẽ rebuild). Research (T1-T3) vẫn để pipeline lo.
        #   • 'strategize'/'strategy' → chỉ lập chiến lược (research phải có sẵn).
        #   • 'full'                  → research (pipeline) → rồi strategize_web.
        #   • còn lại (research/market/competitor/swot…) → pipeline như cũ.
        if task in ("strategize", "strategy"):
            res = await strategize_web(uid, progress)
            if res.get("error"):
                raise RuntimeError(res["error"])
            job["status"] = "done"
            job["summary"] = (f"Đã lập Chiến lược + Playbook "
                              f"(nhịp {res.get('horizon')}, posture {res.get('posture')}).")
        else:
            from storage.session import get_session, save_session
            from agents.pipeline import run_targeted_pipeline

            session = await get_session(uid)
            # 'full' = research trước rồi web-strategize → pipeline chỉ chạy phần research.
            session.selected_task = "research" if task == "full" else task

            try:
                from tools.token_tracker import begin_job
                begin_job(session)
            except Exception:
                pass

            agen = run_targeted_pipeline(session, progress_callback=progress)
            done: list[str] = []
            async for stage_key, _result in agen:
                if stage_key in ("pipeline_abort", "quota_stop"):
                    job["progress"] = f"Dừng: {stage_key}"
                    break
                done.append(stage_key)
                job["progress"] = f"Hoàn tất bước: {stage_key}"
            await save_session(session)

            if task == "full":
                res = await strategize_web(uid, progress)
                if res.get("error"):
                    raise RuntimeError(res["error"])
                done.append("strategy_web")

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
