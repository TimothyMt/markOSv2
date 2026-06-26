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
import uuid

logger = logging.getLogger(__name__)


def _short_uuid() -> str:
    """M-E: id ổn định ngắn cho pillar (giữ liên kết bài-đã-duyệt khi đổi tên trụ)."""
    return uuid.uuid4().hex[:8]


# M-E2 (B): bộ góc khai thác (value lens) — KHỚP nhãn FE để slot pre-select đúng option.
_VALUE_LENSES = ["Nỗi đau/Vấn đề", "Kết quả/Lợi ích", "Bằng chứng xã hội", "Khát vọng/Định vị",
                 "Xử lý phản đối", "Cơ chế/USP", "Khẩn cấp", "Uy tín chuyên môn"]

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
    # M-F (F1): meta loại campaign + checklist task (lưu intake_extra.campaign_meta) → FE bảng task.
    try:
        _ie = (out.get("bizProfile") or {}).get("intake_extra") or {}
        out["bizCampaignMeta"] = (_ie.get("campaign_meta") if isinstance(_ie, dict) else {}) or {}
    except Exception:
        out["bizCampaignMeta"] = {}
    out["bizCampaignTypes"] = campaign_types_list()
    try:
        _ie2 = (out.get("bizProfile") or {}).get("intake_extra") or {}
        out["bizCampaignPortfolio"] = (_ie2.get("campaign_portfolio") if isinstance(_ie2, dict) else []) or []
    except Exception:
        out["bizCampaignPortfolio"] = []
    # M-G (campaign-first): các gap đã bóc (sau research) → FE màn "Tạo campaign tổng" chọn gap.
    try:
        _ie3 = (out.get("bizProfile") or {}).get("intake_extra") or {}
        out["bizGaps"] = (_ie3.get("gaps") if isinstance(_ie3, dict) else []) or []
    except Exception:
        out["bizGaps"] = []
    # Vision A: option đặt cược (5 nhóm) + lựa chọn founder đã chốt → FE màn "Đặt cược".
    try:
        _ie4 = (out.get("bizProfile") or {}).get("intake_extra") or {}
        out["bizBetOptions"] = (_ie4.get("bet_options") if isinstance(_ie4, dict) else {}) or {}
        out["bizBetChoices"] = (_ie4.get("bet_choices") if isinstance(_ie4, dict) else {}) or {}
    except Exception:
        out["bizBetOptions"] = {}; out["bizBetChoices"] = {}
    out["bizBetCategories"] = [{"key": k, "icon": v[0], "label": v[1], "hint": v[2]}
                               for k, v in BET_CATEGORIES.items()]
    # M-D Pha2b: archetype mua hàng của ngành → FE lọc "mục đích đợt" hợp ngành (nguồn duy nhất ở frameworks/).
    try:
        from frameworks.industry_context import get_purchase_archetype
        prof = out.get("bizProfile") or {}
        out["bizArchetype"] = get_purchase_archetype((prof.get("industry") or "")) or ""
    except Exception:
        out["bizArchetype"] = ""
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
                    # M-E: id ổn định — giữ nếu FE gửi lại (re-lock), cấp mới nếu chưa có.
                    "id": str(p.get("id") or "")[:16] or _short_uuid(),
                    "name": str(p.get("name") or "")[:120],
                    "role": str(p.get("role") or "")[:240],
                    "funnel": str(p.get("funnel") or "")[:40],
                    "cadence": str(p.get("cadence") or "")[:120],
                    "posts_per_week": _ppw(p.get("posts_per_week")),
                    "framework": str(p.get("framework") or "")[:40],
                    "value_lens": str(p.get("value_lens") or "")[:80],
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


def _post_key(track: str, pillar_id: str, campaign_id: str, phase: str,
              week, day) -> str:
    """M-E: key thẻ ỔN ĐỊNH — always theo pillarId (đổi tên trụ không mất), occasion theo
    campaignId+phase. Vị trí (week/day) là phần founder tự đặt (kéo-thả ở pha C)."""
    if (track or "") == "camp":
        return f"oc|{campaign_id}|{phase}"
    return f"aw|{pillar_id}|{week}|{day}"


async def save_calendar_post(user_id=None, slot_key: str = "", content: str = "",
                             delete: bool = False, track: str = "", pillar_id: str = "",
                             campaign_id: str = "", phase: str = "",
                             week=None, day=None) -> dict:
    """M-E (nâng từ M-C): lưu/duyệt bài tại ô lịch dưới dạng THẺ HẠNG NHẤT.

    value = {content, approved, track, ref:{pillarId|campaignId,phase}, place:{week,day,phase}}.
    key ổn định (_post_key) → đổi tên trụ / đổi cadence / đổi thứ tự KHÔNG mất bài (render
    inject theo ref+place). delete=True → gỡ thẻ. slot_key = key cũ (back-compat / migration)."""
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
        posts = extra.get("calendar_posts") or {}
        if not isinstance(posts, dict):
            posts = {}
        tr = (track or "").strip() or "always"
        # key ổn định từ field cấu trúc; fallback slot_key (gọi cũ / migration)
        has_struct = bool((pillar_id or campaign_id))
        key = _post_key(tr, pillar_id, campaign_id, phase, week, day) if has_struct else (slot_key or "").strip()
        if not key:
            return {"error": "Thiếu thông tin ô (key)."}
        if delete:
            posts.pop(key, None)
            if slot_key and slot_key != key:
                posts.pop(slot_key, None)   # dọn cả key cũ nếu khác
        else:
            if not (content or "").strip():
                return {"error": "Bài trống — không lưu."}
            def _int(v):
                try: return int(v)
                except Exception: return None
            ref = ({"campaignId": str(campaign_id), "phase": str(phase or "")} if tr == "camp"
                   else {"pillarId": str(pillar_id)})
            posts[key] = {"content": content[:6000], "approved": True, "track": tr,
                          "ref": ref, "place": {"week": _int(week), "day": _int(day),
                                                "phase": str(phase or "")}}
            if slot_key and slot_key != key:
                posts.pop(slot_key, None)   # migration: bỏ bản key cũ trùng ô
        extra["calendar_posts"] = posts
        row = await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "saved": len(posts), "profile": row}
    except Exception as e:
        logger.warning("biz.save_calendar_post failed: %s", e)
        return {"error": str(e)}


async def gen_calendar_topics(user_id=None) -> dict:
    """M-E Pha 2: Max sinh LOẠT chủ đề cụ thể cho always-on (mỗi pillar 1 danh sách phủ horizon),
    bám USP/ngành/wedge + tiến triển TOFU→BOFU, KHÔNG lặp. Lưu intake_extra.calendar_topics
    (dict pillarId → [topic...]). calendar_plan gán topic thứ k cho lần xuất hiện thứ k của pillar.
    Tham khảo bot content_calendar (topic cụ thể theo theme tuần × pillar × phễu)."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        plan = await campaign_plan(uid)
        pillars = (plan or {}).get("pillars") or []
        if not pillars:
            return {"error": "Chưa có tuyến nền — chốt chiến lược (và chốt pillars) trước."}
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        industry = prof.get("industry") or ""
        usp = prof.get("usp") or ""
        wedge = (extra.get("wedge") if isinstance(extra, dict) else "") or ""
        hz = (extra.get("horizon") if isinstance(extra, dict) else "") or ""
        weeks = _HORIZON_WEEKS.get(str(hz or ""), 4)
        synth = await _latest_content(uid, "synthesis")
        # số chủ đề cần/pillar = ppw × tuần, trần 12 (đủ đa dạng, không phình token)
        specs = []
        for i, p in enumerate(pillars):
            n = min(_ppw(p.get("posts_per_week")) * weeks, 12)
            specs.append((i, _pillar_id(p), p, max(n, 3)))
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        plist = "\n".join(
            f"{i+1}. Trụ «{p.get('name','')}» (vai: {p.get('role','')[:80]}; phễu: {p.get('funnel','')}; "
            f"góc: {p.get('value_lens','')}) → cần {n} chủ đề"
            for (i, _pid, p, n) in specs)
        lens_opts = " · ".join(_VALUE_LENSES)
        system = (
            "Bạn là Content Strategist. Với mỗi content pillar (always-on), sinh DANH SÁCH chủ đề "
            "bài viết CỤ THỂ (không phải góc khai thác chung chung) cho founder Việt Nam.\n"
            "🔴 Mỗi chủ đề = 1 ý bài rõ ràng, viết được ngay (6-14 từ), KHÁC NHAU hoàn toàn (không lặp ý).\n"
            "🔴 Mỗi chủ đề kèm 1 'lens' = GÓC KHAI THÁC phù hợp NHẤT với chủ đề đó (mỗi bài 1 góc riêng, "
            f"KHÔNG dùng chung 1 góc của trụ), CHỌN ĐÚNG 1 trong: {lens_opts}.\n"
            "🔴 Tiến triển theo phễu trong danh sách: đầu list nghiêng nhận biết/giá trị (TOFU), "
            "giữa list bằng chứng/so sánh (MOFU), cuối list gần chuyển đổi (BOFU) — hợp VAI của trụ.\n"
            "🔴 Bám USP + ngành + tệp ưu tiên (wedge). BẮT BUỘC TIẾNG VIỆT tự nhiên — kể cả khi chiến lược "
            "tham chiếu bằng tiếng Anh thì vẫn DỊCH/viết chủ đề bằng tiếng Việt, KHÔNG để nguyên tiếng Anh. "
            "Cụ thể (nêu được tình huống/đối tượng), KHÔNG generic kiểu 'Mẹo hay mỗi ngày'. KHÔNG markdown.\n"
            'Output JSON DUY NHẤT: {"pillars":[{"topics":[{"topic":"...","lens":"..."}]}]} — mảng "pillars" '
            "ĐÚNG THỨ TỰ và ĐÚNG SỐ chủ đề yêu cầu cho từng trụ ở trên."
        )
        user = (f"# Ngành\n{industry}\n# USP\n{usp or '(chưa rõ)'}\n# Wedge\n{wedge or '(chưa chọn)'}\n"
                f"# Horizon\n{weeks} tuần\n\n# CÁC TRỤ + SỐ CHỦ ĐỀ CẦN\n{plist}\n\n"
                f"# Chiến lược (tham chiếu)\n{synth[:1800]}")
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=user, max_tokens=2200)
        raw = (res or {}).get("output", "").strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```\s*$', '', raw).strip()
        data = _json.loads(raw)
        arr = data.get("pillars") or []
        topics_map, total = {}, 0
        for (i, pid, p, n) in specs:
            tlist = []
            if i < len(arr) and isinstance(arr[i], dict):
                for t in (arr[i].get("topics") or []):
                    # hỗ trợ cả {topic,lens} lẫn chuỗi thuần
                    if isinstance(t, dict):
                        tp = str(t.get("topic") or "").strip()
                        ln = str(t.get("lens") or "").strip()
                    else:
                        tp, ln = str(t).strip(), ""
                    if tp:
                        tlist.append({"t": tp[:160], "lens": ln if ln in _VALUE_LENSES else ""})
            if tlist:
                topics_map[pid] = tlist[:12]
                total += len(topics_map[pid])
        if not topics_map:
            return {"error": "Max chưa sinh được chủ đề — thử lại."}
        if not isinstance(extra, dict):
            extra = {}
        extra["calendar_topics"] = topics_map
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "pillars": len(topics_map), "topics": total}
    except Exception as e:
        logger.warning("biz.gen_calendar_topics failed: %s", e)
        return {"error": str(e)}


async def archive_calendar_post(user_id=None, slot_key: str = "") -> dict:
    """M-E (Q4): chuyển 1 bài orphan sang Tài liệu (skill_runs 'calendar_post') rồi gỡ khỏi lịch.
    Để bài đã duyệt không kẹt ở khay khi trụ/đợt liên quan bị bỏ."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if not (slot_key or "").strip():
        return {"error": "Thiếu slot_key."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, skill_runs
        cur = await profiles.get_profile(uid) or {}
        extra = cur.get("intake_extra") or {}
        if not isinstance(extra, dict):
            extra = {}
        posts = extra.get("calendar_posts") or {}
        entry = posts.get(slot_key) if isinstance(posts, dict) else None
        content = (entry or {}).get("content") if isinstance(entry, dict) else None
        if not (content or "").strip():
            return {"error": "Không tìm thấy bài để chuyển."}
        await skill_runs.insert_skill_run(uid, "calendar_post", content, model_used="web-calendar-archive")
        posts.pop(slot_key, None)
        extra["calendar_posts"] = posts
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "archived": True}
    except Exception as e:
        logger.warning("biz.archive_calendar_post failed: %s", e)
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


async def set_current_run(user_id=None, run_id: str = "") -> dict:
    """N-01: ĐẶT 1 version cũ làm HIỆN HÀNH mà KHÔNG đẻ bản copy. Re-stamp version của run đã chọn
    lên cao nhất (mô hình newest-wins) → mọi nơi đọc 'mới nhất' tự trỏ vào nó. Không tạo row mới."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if not run_id:
        return {"error": "Thiếu version."}
    try:
        c = await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        row = (await c.table("skill_runs").select("id,skill_name,version")
               .eq("id", run_id).eq("user_id", uid).limit(1).execute())
        if not row.data:
            return {"error": "Không tìm thấy version."}
        sk = row.data[0].get("skill_name")
        cur_ver = row.data[0].get("version") or 0
        top = (await c.table("skill_runs").select("version")
               .eq("user_id", uid).eq("skill_name", sk)
               .order("version", desc=True).limit(1).execute())
        cur_top = (top.data[0].get("version") if top.data else 0) or 0
        if cur_ver < cur_top:
            await c.table("skill_runs").update({"version": cur_top + 1}).eq("id", run_id).execute()
        return {"ok": True, "run_id": run_id}
    except Exception as e:
        logger.warning("biz.set_current_run failed: %s", e)
        return {"error": str(e)}


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
            "archetype/wedge; mỗi pillar có vai + tầng phễu + nhịp đăng + SỐ bài/tuần + vài góc bài.\n"
            "(2) 3-5 gợi ý OCCASION (đợt theo dịp) hợp MÙA VỤ của ngành (đọc kỹ động lực/mùa vụ).\n"
            'Output JSON đúng schema: {"pillars":[{"name":"","role":"","funnel":"TOFU|MOFU|BOFU",'
            '"cadence":"","posts_per_week":1,"framework":"PAS|AIDA|BAB|FAB|Star-Story",'
            '"value_lens":"","angles":["",""]}],"occasions":[{"name":"","when":"","why":""}]}.\n'
            "🔴 posts_per_week = SỐ NGUYÊN bài/tuần hợp lý cho trụ đó (thường 1-3); cadence là mô tả chữ tương ứng.\n"
            "🔴 framework = khung copywriting ẩn hợp VAI trụ (PAS/AIDA/BAB/FAB/Star-Story). value_lens = "
            "GÓC KHAI THÁC chính của trụ, chọn 1 trong: Nỗi đau/Vấn đề · Kết quả/Lợi ích · Bằng chứng xã hội · "
            "Khát vọng/Định vị · Xử lý phản đối · Cơ chế/USP · Khẩn cấp · Uy tín chuyên môn.\n"
            "🔴 BẮT BUỘC TIẾNG VIỆT cho MỌI giá trị chữ (name/role/cadence/value_lens/angles/occasion "
            "name/when/why) — KỂ CẢ khi Synthesis/Tactical tham chiếu bằng TIẾNG ANH thì vẫn phải DỊCH/đặt "
            "tên trụ + chủ đề bằng tiếng Việt tự nhiên, TUYỆT ĐỐI KHÔNG để nguyên cụm tiếng Anh (vd KHÔNG "
            "'Supply Chain Insights' mà là 'Góc nhìn chuỗi cung ứng'). angles = gợi ý CHỦ ĐỀ bài, không phải "
            "brief ảnh. Giữ NGUYÊN khoá JSON tiếng Anh.\n"
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
    "leadgen":     "THU LEAD / ĐẶT TƯ VẤN (high-consideration): mục tiêu là form/booking/lịch hẹn/demo, KPI = số lead, cost-per-lead, tỉ lệ đặt lịch — KHÔNG ép chốt đơn ngay; nuôi để sales theo sau.",
    "brand":       "RA MẮT / PHỦ NHẬN BIẾT: launch sản phẩm hoặc phủ tệp mới; KPI = reach/tần suất/nhớ thương hiệu, KHÔNG ép chốt; ưu tiên thông điệp định vị.",
    "engagement":  "TƯƠNG TÁC & LAN TOẢ (earned/viral): UGC, minigame/giveaway, share/tag bạn, livestream; KPI = reach earned, lượt tương tác/chia sẻ, người tham gia — KHÔNG lấy đơn hàng làm thước đo chính.",
    "retention":   "GIỮ & KÉO LẠI khách CŨ: nhắm tệp đã mua (giữ active: repeat/AOV/CLV) và kéo lại khách đã rời (winback); ưu đãi loyalty, KHÔNG đốt ngân sách acquisition.",
}


# M-F (Pha F1): LOẠI chiến dịch = playbook gắn mục tiêu. 2 nhóm + tự-mô-tả (không trần cứng).
# tuple: (group, icon, label, objective, window_weeks, [task_kind...]). task kind 'action:*' = việc người làm.
CAMPAIGN_TYPES = {
    # Nhóm Nền — XUYÊN SUỐT (M-G): không window/deadline, là campaign nền chạy liên tục
    "branding":    ("nền", "🟢", "Branding nền (xuyên suốt)", "brand", 0, ["calendar_post", "video_script", "ugc_brief"]),
    # Nhóm A — theo mục tiêu
    "awareness":   ("A", "📣", "Nhận biết",        "brand",      5, ["calendar_post", "video_script", "ugc_brief"]),
    "launch":      ("A", "🚀", "Ra mắt sản phẩm",  "brand",      4, ["calendar_post", "video_script", "ads_copy", "ugc_brief", "email_zalo_sequence", "landing_copy"]),
    "promo":       ("A", "💰", "Sale/Khuyến mãi",  "conversion", 2, ["calendar_post", "ads_copy", "email_zalo_sequence", "sales_inbox_script", "action:setup_ads"]),
    "leadgen":     ("A", "📞", "Thu lead/Tư vấn",  "leadgen",    4, ["calendar_post", "ads_copy", "landing_copy", "email_zalo_sequence", "sales_inbox_script"]),
    "engagement":  ("A", "✨", "Tương tác/Viral",  "engagement", 2, ["calendar_post", "ugc_brief"]),
    "retention":   ("A", "🔁", "Giữ & Winback",    "retention",  0, ["email_zalo_sequence", "sales_inbox_script", "calendar_post", "referral_plan"]),
    # Nhóm B — theo hình thức đặc thù
    "rebrand":     ("B", "🔄", "Tái định vị",       "brand",      6, ["calendar_post", "video_script", "ugc_brief", "pr_pitch"]),
    "influencer":  ("B", "🤝", "Influencer/KOL",    "engagement", 4, ["ugc_brief", "calendar_post", "action:contact_kol"]),
    "event":       ("B", "🎪", "Event/Trải nghiệm", "engagement", 3, ["event_plan", "calendar_post", "video_script", "email_zalo_sequence", "action:run_event"]),
    "csr":         ("B", "❤️", "CSR/Vì cộng đồng",  "brand",      4, ["calendar_post", "video_script", "pr_pitch"]),
    "content_seo": ("B", "📚", "Content/SEO dài hơi", "leadgen",  8, ["seo_outline", "calendar_post", "email_zalo_sequence"]),
    "ugc":         ("B", "👥", "UGC/Cộng đồng",      "engagement", 3, ["ugc_brief", "calendar_post", "action:contact_kol"]),
}

# Nhãn task (kind → label tiếng Việt). content task móc generator sẵn; 'action:*' = người làm + Max ra brief.
CAMPAIGN_TASK_LABELS = {
    "calendar_post":       "Bài đăng cho đợt (posts)",
    "post_channels":       "Biến thể đa kênh",
    "video_script":        "Kịch bản video",
    "ugc_brief":           "Brief UGC / KOL",
    "ads_copy":            "Quảng cáo (ads copy theo phễu)",
    "email_zalo_sequence": "Chuỗi Email / Zalo",
    "sales_inbox_script":  "Kịch bản chốt inbox",
    "landing_copy":        "Nội dung Landing page",
    "seo_outline":         "Dàn bài SEO (cụm từ khoá + outline)",
    "pr_pitch":            "Bài PR / pitch báo chí",
    "event_plan":          "Kế hoạch event (kịch bản chương trình)",
    "referral_plan":       "Cơ chế giới thiệu (referral)",
    "action:setup_ads":    "Set-up & chạy tài khoản ads (việc người làm)",
    "action:contact_kol":  "Liên hệ & chốt KOL/Influencer (việc người làm)",
    "action:run_event":    "Tổ chức event (việc người làm)",
}


def campaign_types_list() -> list:
    """Cho FE: list loại campaign (2 nhóm) + objective/window/task (kèm label) để pre-fill wizard."""
    out = []
    for k, (grp, ic, label, obj, wk, tasks) in CAMPAIGN_TYPES.items():
        out.append({"key": k, "group": grp, "icon": ic, "label": label,
                    "objective": obj, "window_weeks": wk,
                    "tasks": [{"kind": t, "label": CAMPAIGN_TASK_LABELS.get(t, t),
                               "is_action": t.startswith("action:")} for t in tasks]})
    return out


def _build_campaign_tasks(type_key: str) -> list:
    """Dựng checklist task mặc định từ template loại campaign."""
    spec = CAMPAIGN_TYPES.get(type_key)
    kinds = list(spec[5]) if spec else ["calendar_post", "ads_copy", "email_zalo_sequence"]
    tasks = []
    for kind in kinds:
        tasks.append({"id": kind.replace(":", "_"), "kind": kind,
                      "label": CAMPAIGN_TASK_LABELS.get(kind, kind),
                      "is_action": kind.startswith("action:"),
                      "status": "todo", "run_id": None})
    return tasks


async def occasion_draft(user_id=None, occasion: str = "", window_start: str = "",
                         window_end: str = "", budget: str = "", baseline: str = "",
                         goal: str = "", objective: str = "", objective_custom: str = "",
                         campaign_type: str = "", audience: str = "") -> dict:
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
        # M-F: loại campaign → mặc định objective nếu founder chưa chọn + playbook vào prompt.
        ct = CAMPAIGN_TYPES.get((campaign_type or "").strip().lower())
        ct_hint = ""
        if ct:
            if not (objective or "").strip() and not (objective_custom or "").strip():
                objective = ct[3]   # objective gốc của loại
            ct_hint = (f"LOẠI chiến dịch: {ct[2]} (playbook đặc thù — bám đúng hình thức này: arc, "
                       f"trọng tâm phễu, loại deliverable phù hợp loại {ct[2]}).")
        obj_key = (objective or "").strip().lower()
        obj_custom = (objective_custom or "").strip()
        # Pha2b: mục đích tự điền ưu tiên > nút chọn. KHÔNG ép phân loại — đưa nguyên văn cho LLM diễn giải.
        if obj_custom:
            obj_hint = (f"FOUNDER TỰ MÔ TẢ mục đích đợt: «{obj_custom}». Đây là mục đích chính — "
                        "tự suy loại KPI/tầng phễu/offer phù hợp với mô tả này + archetype ngành; "
                        "nếu mô tả mơ hồ thì chọn cách hiểu hợp dịp + giai đoạn roadmap.")
        else:
            obj_hint = OCCASION_OBJECTIVES.get(obj_key, "")
        # Pha2b: archetype ngành → brief bám đúng bản chất mua hàng (vd trust-building KHÔNG flash-chốt-đơn).
        from frameworks.industry_context import get_purchase_archetype, ARCHETYPE_LABEL
        arche = get_purchase_archetype(industry) or ""
        arche_label = ARCHETYPE_LABEL.get(arche, arche)
        horizon = (extra.get("horizon") if isinstance(extra, dict) else "") or ""
        posture = (extra.get("posture") if isinstance(extra, dict) else "") or ""
        # M5-B1: trước đây key KHÔNG băm synthesis → đổi chiến lược, brief đợt vẫn cũ.
        # Thêm chữ ký nguồn (synth+tact+wedge+usp+ngành+horizon+posture) vào key.
        src_fp = _strategy_fp(synth, tact, wedge, usp, industry, horizon, posture)
        cache_key = f"{uid}:{src_fp}:{hash((occasion, window_start, window_end, budget, baseline, goal, obj_key, obj_custom))}"
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
            "Brief tốt = team không cần hỏi lại 1 câu để bắt đầu. Xuất MARKDOWN gồm:\n"
            "## 1. Big idea & Key message\n"
            "1 BIG IDEA xuyên suốt đợt (concept, KHÔNG phải tagline) + Key message (điều khách phải nhớ sau đợt).\n"
            "## 2. Tệp nhắm + insight ngầm\n"
            "Demographic + psychographic + pain cốt lõi + 1 insight ngầm dẫn dắt creative.\n"
            "## 3. Mục tiêu SMART (đợt này)\n"
            "## 4. Arc 5 pha theo timeline (bảng: Pha | Thời gian | Mục tiêu pha | Kênh | Góc copy)\n"
            "## 5. Creative direction\n"
            "Tone & visual mood (bối cảnh VN) + Do's/Don'ts cụ thể + 3 HOOK ANGLE để A/B test.\n"
            "## 6. Offer & cơ chế urgency\n"
            "Offer chính (từ lever, KHÔNG bịa) + cách tạo urgency THẬT (không fake — khách VN nhận ra ngay).\n"
            "## 7. KPI cần theo dõi (đúng loại theo mục đích; có target nếu có baseline)\n"
            "## 8. Phân bổ ngân sách đợt (theo pha)\n"
            "## 9. Rủi ro & dự phòng + Lưu ý nhất quán (2-3 rủi ro + plan B; đợt có lệch wedge/định vị chính không?)\n\n"
            f"🔴 SMART: {base_rule}\n"
            "🔴 MỤC ĐÍCH đợt (nếu founder chọn/tự mô tả) định hình TRỌNG TÂM phễu + KPI + loại offer "
            "của cả arc — bám đúng, đừng lệch sang mục đích khác. KPI (mục 7) phải ĐÚNG LOẠI với mục "
            "đích (vd thu lead → số lead/CPL/lịch hẹn; tương tác → reach/share/người tham gia; chốt "
            "đơn → doanh số/ROAS), KHÔNG mặc định lấy đơn hàng.\n"
            "🔴 ARCHETYPE ngành quyết bản chất mua: trust_building (ticket lớn, cân nhắc cao) thì đợt "
            "KHÔNG ép 'flash chốt đơn' — hướng thu lead/đặt tư vấn/nuôi; impulse thì đẩy chốt nhanh "
            "được; demand_gen thì khơi desire + tương tác. Nếu mục đích founder chọn nghịch archetype "
            "→ vẫn theo founder nhưng NHẮC ở mục 9.\n"
            "🔴 Bám đúng dịp + mùa vụ + văn hoá ngành. Tôn trọng wedge/USP founder đã chọn "
            "(nếu lever cho thấy đợt nhắm tệp khác → vẫn làm theo founder, chỉ NHẮC ở mục 9). "
            "KHÔNG bịa số ngoài lever/baseline."
        )
        user = (
            f"# Ngành\n{industry} — Archetype mua: {arche_label or '(chưa rõ)'}\n{ictx}\n\n"
            f"# Wedge (tệp ưu tiên — la bàn)\n{wedge or '(chưa chọn)'}\n"
            f"# USP\n{usp or '(chưa rõ)'}\n\n"
            f"# Lever ĐỢT NÀY\n- Dịp: {occasion}\n- Window: {window_start or '?'} → {window_end or '?'}\n"
            f"- Ngân sách đợt: {budget or '(chưa nhập)'}\n- Baseline hiện tại: {baseline or '(chưa rõ)'}\n"
            f"- Mục tiêu chính founder muốn: {goal or '(theo giai đoạn roadmap)'}\n"
            f"- MỤC ĐÍCH đợt: {obj_hint or '(founder chưa chọn — tự suy mục đích hợp dịp + giai đoạn)'}\n"
            f"{('- ' + ct_hint + chr(10)) if ct_hint else ''}"
            f"{('- TỆP NHẮM chính: ' + audience + ' — bám đúng nhóm khách này (thông điệp/offer/kênh).' + chr(10)) if (audience or '').strip() else ''}\n"
            f"# Chiến lược (Synthesis — la bàn)\n{synth[:3000]}\n\n"
            f"# Tactical Playbook (cách đánh)\n{(tact or '(chưa có)')[:2000]}"
        )
        res = await router_call(task_type=TaskType.OPS_BRIEF, system=system,
                                user=user, max_tokens=3200)
        brief = (res or {}).get("output", "").strip()
        if not brief:
            return {}
        out = {"brief": brief, "occasion": occasion,
               "window_start": window_start, "window_end": window_end,
               "budget": budget, "baseline": baseline, "has_baseline": has_base,
               "objective": obj_key, "objective_custom": obj_custom}
        _occasion_cache[cache_key] = out
        return out
    except Exception as e:
        logger.warning("biz.occasion_draft failed (non-fatal): %s", e)
        return {}


async def save_occasion(user_id=None, occasion: str = "", window_start: str = "",
                        window_end: str = "", budget: str = "", goal: str = "",
                        brief: str = "", objective: str = "", objective_custom: str = "",
                        campaign_type: str = "", audience: str = "") -> dict:
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
        obj_custom = (objective_custom or "").strip()
        # primary_goal: ưu tiên mục đích tự điền > WHY tag (nút) > goal cụ thể
        primary_goal = (obj_custom[:120] or (obj if obj in OCCASION_OBJECTIVES else "")
                        or (goal or "").strip() or None)
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
        # M-F (F1): lưu loại campaign + checklist task vào intake_extra.campaign_meta[cid] (không cần migration).
        ctk = (campaign_type or "").strip().lower()
        cid = (camp or {}).get("id")
        if ctk in CAMPAIGN_TYPES and cid is not None:
            extra = prof.get("intake_extra") or {}
            if not isinstance(extra, dict):
                extra = {}
            meta = extra.get("campaign_meta") or {}
            if not isinstance(meta, dict):
                meta = {}
            spec = CAMPAIGN_TYPES[ctk]
            meta[str(cid)] = {"type": ctk, "type_label": spec[2], "type_icon": spec[1],
                              "group": spec[0], "audience": (audience or "").strip(),
                              "tasks": _build_campaign_tasks(ctk)}
            extra["campaign_meta"] = meta
            await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "campaign": camp, "run_id": run_id}
    except Exception as e:
        logger.warning("biz.save_occasion failed: %s", e)
        return {"error": str(e)}


# M-F (F2): nhóm khách (Pha 4 bản nhẹ — gắn ở lớp campaign). always-on KHÔNG dùng.
AUDIENCE_SEGMENTS = ["Mới", "Active", "Nguy cơ", "VIP", "Tất cả"]
# default tệp nhắm theo loại (founder đổi được)
_TYPE_AUDIENCE = {
    "awareness": "Mới", "launch": "Mới", "promo": "Tất cả", "leadgen": "Mới",
    "engagement": "Tất cả", "retention": "Active", "rebrand": "Tất cả", "influencer": "Mới",
    "event": "Tất cả", "csr": "Mới", "content_seo": "Mới", "ugc": "Active",
}


async def gen_campaign_portfolio(user_id=None) -> dict:
    """M-F (F2): Max suy DANH MỤC chiến dịch từ roadmap (synthesis) — chuỗi chiến dịch CÓ LOẠI
    theo từng giai đoạn, kèm tệp nhắm (Pha 4 nhẹ) + lý do. CODE lo NGÀY (map start_week→date),
    LLM lo Ý. Lưu intake_extra.campaign_portfolio; founder duyệt → commit thành occasion."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        synth = await _latest_content(uid, "synthesis")
        if not synth.strip():
            return {"error": "Cần Chiến lược (Synthesis) trước khi đề xuất danh mục."}
        tact = await _latest_content(uid, "tactical_playbook")
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        industry = prof.get("industry") or ""
        usp = prof.get("usp") or ""
        wedge = (extra.get("wedge") if isinstance(extra, dict) else "") or ""
        hz = (extra.get("horizon") if isinstance(extra, dict) else "") or ""
        weeks = _HORIZON_WEEKS.get(str(hz or ""), 4)
        from frameworks.industry_context import get_purchase_archetype, ARCHETYPE_LABEL
        arche = ARCHETYPE_LABEL.get(get_purchase_archetype(industry) or "", "")
        # mô tả loại cho LLM chọn đúng key
        type_menu = "\n".join(f"- {k} ({CAMPAIGN_TYPES[k][2]})" for k in CAMPAIGN_TYPES)
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        system = (
            "Bạn là CMO lập DANH MỤC CHIẾN DỊCH cho 1 doanh nghiệp Việt theo roadmap chiến lược.\n"
            f"Đề xuất 3-6 chiến dịch trải đều trong {weeks} TUẦN tới, mỗi cái bám 1 GIAI ĐOẠN của roadmap "
            "(từ nhận biết → cân nhắc → chuyển đổi/giữ chân theo đúng mạch chiến lược + mùa vụ ngành).\n"
            "Mỗi chiến dịch chọn 1 LOẠI từ menu (trả đúng KEY tiếng Anh):\n" + type_menu + "\n"
            "🔴 KHÔNG bịa NGÀY tháng — chỉ ghi start_week (tuần bắt đầu, số nguyên 1.." + str(weeks) + ") và "
            "window_weeks (độ dài, số nguyên). Hệ thống tự tính ngày.\n"
            "🔴 audience = tệp nhắm chính, chọn 1 trong: Mới · Active · Nguy cơ · VIP · Tất cả (hợp loại + giai đoạn).\n"
            "🔴 why = 1-2 câu vì sao chiến dịch này ở giai đoạn này (bám roadmap + USP + ngành). TIẾNG VIỆT.\n"
            "🔴 Trải hợp lý, KHÔNG chồng chéo dày; tôn trọng wedge/định vị; KHÔNG bịa số/ngân sách.\n"
            'Output JSON DUY NHẤT: {"campaigns":[{"name":"","type":"","objective":"","audience":"",'
            '"why":"","start_week":1,"window_weeks":2}]} — name tiếng Việt, ngắn gọn hook-y.'
        )
        user = (f"# Ngành\n{industry} — {arche}\n# USP\n{usp or '(chưa rõ)'}\n# Wedge\n{wedge or '(chưa chọn)'}\n"
                f"# Horizon\n{weeks} tuần\n\n# Chiến lược (Synthesis — roadmap)\n{synth[:3200]}\n\n"
                f"# Tactical Playbook\n{(tact or '(chưa có)')[:1500]}")
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=user, max_tokens=1800)
        raw = (res or {}).get("output", "").strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```\s*$', '', raw).strip()
        data = _json.loads(raw)
        from datetime import date, timedelta
        today = date.today()
        anchor = today - timedelta(days=today.weekday())   # thứ Hai tuần này
        items = []
        for c in (data.get("campaigns") or [])[:8]:
            if not isinstance(c, dict):
                continue
            tkey = str(c.get("type") or "").strip().lower()
            spec = CAMPAIGN_TYPES.get(tkey)
            if not spec:
                continue   # bỏ loại không hợp lệ
            try:
                sw = max(1, min(int(c.get("start_week") or 1), weeks))
            except Exception:
                sw = 1
            try:
                ww = max(1, int(c.get("window_weeks") or spec[4] or 2))
            except Exception:
                ww = spec[4] or 2
            ww = ww if ww > 0 else 2
            ws = anchor + timedelta(weeks=sw - 1)
            we = ws + timedelta(weeks=ww) - timedelta(days=1)
            aud = str(c.get("audience") or "").strip()
            if aud not in AUDIENCE_SEGMENTS:
                aud = _TYPE_AUDIENCE.get(tkey, "Tất cả")
            items.append({"name": str(c.get("name") or spec[2])[:120], "type": tkey,
                          "type_label": spec[2], "type_icon": spec[1],
                          "objective": (str(c.get("objective") or "").strip() or spec[3]),
                          "audience": aud, "why": str(c.get("why") or "")[:280],
                          "start_week": sw, "window_weeks": ww,
                          "ws": ws.isoformat(), "we": we.isoformat()})
        if not items:
            return {"error": "Max chưa đề xuất được danh mục — thử lại."}
        if not isinstance(extra, dict):
            extra = {}
        extra["campaign_portfolio"] = items
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "campaigns": items}
    except Exception as e:
        logger.warning("biz.gen_campaign_portfolio failed: %s", e)
        return {"error": str(e)}


# Reset để test: các key SINH RA trong intake_extra (xoá khi reset 'mềm', giữ hồ sơ + intake answers).
_RESET_EXTRA_KEYS = ["wedge", "usp_stance", "usp_text", "horizon", "posture", "pillars_locked",
                     "calendar_posts", "calendar_topics", "campaign_meta", "campaign_portfolio"]


async def reset_business(user_id=None, full: bool = False) -> dict:
    """Reset dữ liệu để TEST lại từ đầu.
    full=False (mềm): giữ hồ sơ + câu trả lời intake, xoá kết quả phân tích (skill_runs) + campaigns
                      + các key sinh ra (gate/pillars/lịch/chiến dịch) trong intake_extra.
    full=True: xoá HẲN hồ sơ + skill_runs + campaigns (về trắng, làm lại từ intake)."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, skill_runs, campaigns_v2
        await skill_runs.delete_skill_runs(uid)
        await campaigns_v2.delete_campaigns_by_user(uid)
        # dọn cache in-memory để không trả output cũ
        for _c in (_campaign_plan_cache, _occasion_cache, _retention_cache, _market_kpi_cache):
            try: _c.clear()
            except Exception: pass
        if full:
            await profiles.delete_profile(uid)
            return {"ok": True, "full": True}
        cur = await profiles.get_profile(uid) or {}
        extra = cur.get("intake_extra") if isinstance(cur.get("intake_extra"), dict) else {}
        for k in _RESET_EXTRA_KEYS:
            extra.pop(k, None)
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "full": False}
    except Exception as e:
        logger.warning("biz.reset_business failed: %s", e)
        return {"error": str(e)}


# S-10: tuyến bài (content tracks theo vai trò phễu) + mặc định theo mục tiêu sub-campaign
CONTENT_TRACKS = {
    "khai_sang":  ("🎓", "Khai sáng", "TOFU — làm khách NHẬN RA gap/vấn đề"),
    "tin_cay":    ("🤝", "Tin cậy", "MOFU — bằng chứng · case · so sánh"),
    "chuyen_hoa": ("🎯", "Chuyển hoá", "BOFU — chốt · CTA mềm"),
    "lan_toa":    ("✨", "Lan toả", "Engage — tương tác · UGC · cộng đồng"),
}
# objective của sub → bộ tuyến mặc định (mix phễu theo mục tiêu)
_OBJ_TRACKS = {
    "brand":      ["khai_sang", "tin_cay", "lan_toa"],
    "acquisition":["khai_sang", "chuyen_hoa"],
    "leadgen":    ["khai_sang", "tin_cay", "chuyen_hoa"],
    "conversion": ["chuyen_hoa"],
    "engagement": ["lan_toa", "khai_sang"],
    "retention":  ["tin_cay", "lan_toa"],
}


def _tracks_for(objective: str) -> list:
    keys = _OBJ_TRACKS.get(objective or "", ["khai_sang", "tin_cay", "chuyen_hoa"])
    return [{"key": k, "icon": CONTENT_TRACKS[k][0], "label": CONTENT_TRACKS[k][1],
             "role": CONTENT_TRACKS[k][2]} for k in keys]


# S-05: 6 loại GAP bóc từ research (key ổn định để FE map icon/màu)
GAP_KINDS = {
    "market":      ("🕳️", "Khoảng trống thị trường", "nhu cầu chưa ai đáp ứng tốt"),
    "segment":     ("👥", "Tệp bị bỏ ngỏ", "phân khúc chưa ai phục vụ đúng"),
    "positioning": ("🎯", "Góc định vị trống", "chỗ trống trong tâm trí khách chưa ai chiếm"),
    "trust":       ("🤝", "Khoảng tin cậy / bằng chứng", "khách thiếu niềm tin, chưa ai giải"),
    "channel":     ("📡", "Kênh đối thủ bỏ trống", "kênh đối thủ yếu/bỏ"),
    "price":       ("💰", "Phân khúc giá-trị", "mức giá/giá trị chưa ai phục vụ"),
}


async def gen_gaps(user_id=None) -> dict:
    """S-05: bóc GAP/cơ hội từ research (market/competitor/customer/swot) → trình user chọn khi
    tạo CAMPAIGN TỔNG. 1 LLM call → list gap {kind, title, desc, why, segment}. Lưu intake_extra.gaps."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        research = {}
        for sk in _RESEARCH_SKILLS:
            research[sk] = await _latest_content(uid, sk)
        if not any((research.get(k) or "").strip() for k in _RESEARCH_SKILLS):
            return {"error": "Chưa có nghiên cứu (T1-T3) — hãy chạy nghiên cứu trước."}
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        if not isinstance(extra, dict):
            extra = {}
        industry = prof.get("industry") or ""
        synth = await _latest_content(uid, "synthesis")
        kinds_menu = "\n".join(f"- {k}: {v[1]} ({v[2]})" for k, v in GAP_KINDS.items())
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        system = (
            "Bạn là Chief Strategist. Từ RESEARCH (thị trường/đối thủ/khách/SWOT), BÓC ra các GAP/CƠ HỘI "
            "ĐÁNG ĐÁNH — chỗ trống thật mà đối thủ bỏ ngỏ / khách chưa được phục vụ tốt. 4-7 gap.\n"
            "Mỗi gap chọn 1 'kind' (trả đúng KEY tiếng Anh) trong:\n" + kinds_menu + "\n"
            "Mỗi gap: title (ngắn, cụ thể) · desc (1-2 câu) · why (vì sao đáng đánh — bám phát hiện research "
            "THẬT, KHÔNG bịa) · segment (tệp khách liên quan, nếu có). KHÔNG bịa số. TIẾNG VIỆT.\n"
            'Output JSON DUY NHẤT: {"gaps":[{"kind":"","title":"","desc":"","why":"","segment":""}]}.'
        )
        user = (f"# Ngành\n{industry}\n\n# Thị trường\n{(research.get('market_research') or '(chưa có)')[:2200]}\n\n"
                f"# Đối thủ (chú ý Market Gap)\n{(research.get('competitor') or '(chưa có)')[:2200]}\n\n"
                f"# Khách\n{(research.get('customer_insight') or '(chưa có)')[:1800]}\n\n"
                f"# SWOT (Cơ hội)\n{(research.get('swot') or '(chưa có)')[:1600]}\n\n"
                f"# Chiến lược (nếu có)\n{synth[:1200]}")
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=user, max_tokens=1600)
        raw = (res or {}).get("output", "").strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```\s*$', '', raw).strip()
        data = _json.loads(raw)
        gaps = []
        for g in (data.get("gaps") or [])[:8]:
            if not isinstance(g, dict):
                continue
            kind = str(g.get("kind") or "").strip().lower()
            if kind not in GAP_KINDS:
                kind = "market"
            gaps.append({"kind": kind, "icon": GAP_KINDS[kind][0], "kind_label": GAP_KINDS[kind][1],
                         "title": str(g.get("title") or "")[:120], "desc": str(g.get("desc") or "")[:280],
                         "why": str(g.get("why") or "")[:280], "segment": str(g.get("segment") or "")[:120]})
        if not gaps:
            return {"error": "Chưa bóc được gap — thử lại."}
        extra["gaps"] = gaps
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "gaps": gaps}
    except Exception as e:
        logger.warning("biz.gen_gaps failed: %s", e)
        return {"error": str(e)}


# ════ Vision A: ĐẶT CƯỢC THEO NHÓM → T4-T5 → tuyến → lịch ════
# 5 nhóm đặt cược (trust XUỐNG tầng tuyến nội dung = CONTENT_TRACKS['tin_cay'], không ở đây).
BET_CATEGORIES = {
    "market":      ("🕳️", "Khoảng trống thị trường", "nhu cầu/giải pháp chưa ai làm tốt"),
    "segment":     ("👥", "Tệp khách nhắm tới", "phân khúc muốn phục vụ trước (wedge)"),
    "positioning": ("🎯", "Góc định vị", "chỗ muốn chiếm trong tâm trí khách"),
    "price":       ("💰", "Phân khúc giá-trị", "mô hình giá / mức giá-trị"),
    "channel":     ("📡", "Kênh triển khai", "kênh chính muốn đánh"),
}


async def gen_bet_options(user_id=None) -> dict:
    """Vision A: từ research T1-T3, Max rút OPTION cho 5 NHÓM đặt cược (market/segment/positioning/
    price/channel) để founder CHỌN (hoặc tự ghi) trước khi chạy T4-T5. 1 LLM call → options theo nhóm.
    Lưu intake_extra.bet_options. (Tái dùng mạch gen_gaps, gom theo nhóm.)"""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        research = {}
        for sk in _RESEARCH_SKILLS:
            research[sk] = await _latest_content(uid, sk)
        if not any((research.get(k) or "").strip() for k in _RESEARCH_SKILLS):
            return {"error": "Chưa có nghiên cứu (T1-T3) — hãy chạy nghiên cứu trước."}
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        if not isinstance(extra, dict):
            extra = {}
        industry = prof.get("industry") or ""
        cats_menu = "\n".join(f"- {k}: {v[1]} ({v[2]})" for k, v in BET_CATEGORIES.items())
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        system = (
            "Bạn là Chief Strategist. Từ RESEARCH (thị trường/đối thủ/khách/SWOT), với MỖI NHÓM dưới đây "
            "rút 2-4 OPTION (lựa chọn) ĐÁNG ĐÁNH — bám phát hiện research THẬT, KHÔNG bịa. Đây là các hướng "
            "để founder CHỌN khi đặt cược chiến lược.\n" + cats_menu + "\n"
            "Mỗi option: title (ngắn, cụ thể) · desc (1 câu) · why (vì sao đáng — bám research). TIẾNG VIỆT.\n"
            'Output JSON DUY NHẤT: {"market":[{"title":"","desc":"","why":""}],"segment":[...],'
            '"positioning":[...],"price":[...],"channel":[...]}.'
        )
        user = (f"# Ngành\n{industry}\n\n# Thị trường\n{(research.get('market_research') or '(chưa có)')[:2200]}\n\n"
                f"# Đối thủ (chú ý Market Gap)\n{(research.get('competitor') or '(chưa có)')[:2200]}\n\n"
                f"# Khách\n{(research.get('customer_insight') or '(chưa có)')[:1800]}\n\n"
                f"# SWOT\n{(research.get('swot') or '(chưa có)')[:1600]}")
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=user, max_tokens=2200)
        raw = re.sub(r'\s*```\s*$', '', re.sub(r'^```(?:json)?\s*', '', (res or {}).get("output", "").strip())).strip()
        data = _json.loads(raw)
        options = {}
        for k in BET_CATEGORIES:
            opts = []
            for o in (data.get(k) or [])[:4]:
                if isinstance(o, dict) and str(o.get("title") or "").strip():
                    opts.append({"title": str(o.get("title"))[:120], "desc": str(o.get("desc") or "")[:200],
                                 "why": str(o.get("why") or "")[:200]})
            options[k] = opts
        if not any(options.values()):
            return {"error": "Chưa rút được lựa chọn — thử lại."}
        extra["bet_options"] = options
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "options": options}
    except Exception as e:
        logger.warning("biz.gen_bet_options failed: %s", e)
        return {"error": str(e)}


async def save_bet(user_id=None, choices=None) -> dict:
    """Vision A: lưu lựa chọn ĐẶT CƯỢC theo 5 nhóm (choices = {market:[...],segment:[...],...} mỗi nhóm
    list chuỗi — title option đã chọn HOẶC tự ghi). Lưu intake_extra.bet_choices + map wedge (tệp) / usp
    (định vị) để strategize + hiển thị tương thích. Nằm trong _strategy_fp → đổi là cache vô hiệu."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        if not isinstance(extra, dict):
            extra = {}
        norm = {}
        for k in BET_CATEGORIES:
            vals = (choices or {}).get(k) or []
            if isinstance(vals, str):
                vals = [vals]
            norm[k] = [str(v).strip()[:160] for v in vals if str(v).strip()][:5]
        # Bỏ trống hết = "🤖 để Max tự quyết toàn bộ" (giống bot) — KHÔNG báo lỗi, Max tự rút.
        extra["bet_choices"] = norm
        fields = {"intake_extra": extra}
        if norm.get("segment"):
            extra["wedge"] = " · ".join(norm["segment"])
        if norm.get("positioning"):
            extra["usp_stance"] = "clear"
            fields["usp"] = " · ".join(norm["positioning"])[:400]
            fields["usp_confidence"] = "clear"
        await profiles.upsert_profile(uid, **fields)
        return {"ok": True, "bet_choices": norm}
    except Exception as e:
        logger.warning("biz.save_bet failed: %s", e)
        return {"error": str(e)}


async def gen_master_plan(user_id=None, gap_kind: str = "", gap_title: str = "",
                          wedge: str = "", usp: str = "", name: str = "", gaps=None) -> dict:
    """S-10a: tạo CAMPAIGN TỔNG (đặt cược: GAP(s)+wedge+USP) — lưu campaigns_v2 row + meta(role=master).
    Campaign tổng CẤU THÀNH từ NHIỀU gap ngang hàng (không gap chính) — neo định vị = wedge+USP.
    1 LLM call ĐỀ XUẤT sub-campaign (theo mục tiêu) hợp các gap/wedge → lưu proposed_subs. Nhiều tổng OK."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    # chuẩn hoá danh sách gap (đa gap, ngang hàng); fallback gap đơn (tương thích ngược)
    norm_gaps = []
    for g in (gaps if isinstance(gaps, list) else []):
        if not isinstance(g, dict):
            continue
        k = str(g.get("kind") or "").strip().lower()
        if k not in GAP_KINDS:
            k = "market"
        t = str(g.get("title") or "").strip()
        if not t:
            continue
        norm_gaps.append({"kind": k, "icon": GAP_KINDS[k][0], "kind_label": GAP_KINDS[k][1], "title": t[:140]})
    if not norm_gaps and (gap_title or "").strip():
        gk0 = (gap_kind or "").strip().lower()
        if gk0 not in GAP_KINDS:
            gk0 = "market"
        norm_gaps = [{"kind": gk0, "icon": GAP_KINDS[gk0][0], "kind_label": GAP_KINDS[gk0][1],
                      "title": (gap_title or "").strip()[:140]}]
    if not norm_gaps:
        return {"error": "Thiếu gap — chọn ít nhất 1 gap."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, campaigns_v2
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        if not isinstance(extra, dict):
            extra = {}
        industry = prof.get("industry") or ""
        synth = await _latest_content(uid, "synthesis")
        # đề xuất sub-campaign cho master này
        sub_menu = "\n".join(f"- {k}: {CAMPAIGN_TYPES[k][2]}" for k in CAMPAIGN_TYPES if k != "branding")
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        system = (
            "Bạn là CMO. Cho 1 ĐẶT CƯỢC chiến lược (đánh ĐỒNG THỜI nhiều GAP bổ trợ + tệp wedge + USP), "
            "đề xuất 2-4 SUB-CAMPAIGN theo MỤC TIÊU để thực thi đặt cược đó (vd kéo khách mới, chuyển đổi, "
            "giữ chân, đợt theo dịp). Mỗi sub có thể nghiêng về 1 gap phù hợp. "
            "LUÔN ngầm hiểu có 1 sub Branding nền — KHÔNG đề xuất lại branding. Chọn type từ:\n" + sub_menu + "\n"
            "Mỗi sub: type (KEY tiếng Anh) · name (tiếng Việt ngắn) · why (1 câu vì sao cần cho đặt cược này).\n"
            'Output JSON: {"subs":[{"type":"","name":"","why":""}]}.'
        )
        gaps_txt = "\n".join(f"  • {g['kind_label']} — {g['title']}" for g in norm_gaps)
        user = (f"# Ngành\n{industry}\n# ĐẶT CƯỢC (các GAP cấu thành 1 chiến lược, ngang hàng)\n{gaps_txt}\n"
                f"- Tệp ưu tiên (wedge): {wedge or '(theo synthesis)'}\n- USP: {usp or '(theo synthesis)'}\n\n"
                f"# Chiến lược\n{synth[:1800]}")
        res = await router_call(task_type=TaskType.INTAKE_JSON, system=system, user=user, max_tokens=1000)
        raw = re.sub(r'\s*```\s*$', '', re.sub(r'^```(?:json)?\s*', '', (res or {}).get("output", "").strip())).strip()
        subs = []
        try:
            for sb in (_json.loads(raw).get("subs") or [])[:4]:
                t = str(sb.get("type") or "").strip().lower()
                if t in CAMPAIGN_TYPES and t != "branding":
                    subs.append({"type": t, "type_label": CAMPAIGN_TYPES[t][2], "type_icon": CAMPAIGN_TYPES[t][1],
                                 "name": str(sb.get("name") or CAMPAIGN_TYPES[t][2])[:80], "why": str(sb.get("why") or "")[:160]})
        except Exception:
            pass
        # tạo master row + meta
        gap_titles = ", ".join(g["title"] for g in norm_gaps)
        mname = (name or "").strip() or f"Tổng: {norm_gaps[0]['title']}"[:120]
        camp = await campaigns_v2.create_campaign(uid, name=mname, industry=prof.get("industry"),
                                                  primary_goal="master", summary=gap_titles[:400])
        mid = str((camp or {}).get("id") or "")
        if not mid:
            return {"error": "Không tạo được campaign tổng."}
        meta = extra.get("campaign_meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        meta[mid] = {"role": "master", "type": "master", "type_label": "Campaign tổng", "type_icon": "📦",
                     "name": mname, "gaps": norm_gaps, "gap": norm_gaps[0],
                     "wedge": wedge, "usp": usp, "proposed_subs": subs, "sub_ids": []}
        extra["campaign_meta"] = meta
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "master_id": mid, "proposed_subs": subs}
    except Exception as e:
        logger.warning("biz.gen_master_plan failed: %s", e)
        return {"error": str(e)}


async def commit_subcampaign(user_id=None, master_id: str = "", type: str = "", name: str = "") -> dict:
    """S-10b: chốt 1 sub-campaign vào master — campaigns_v2 row + meta(role=sub, parent, tuyến, task)."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    tk = (type or "").strip().lower()
    if tk not in CAMPAIGN_TYPES:
        return {"error": "Loại sub không hợp lệ."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, campaigns_v2
        prof, extra, meta = await _campaign_meta(uid)
        m = meta.get(str(master_id))
        if not m or m.get("role") != "master":
            return {"error": "Không tìm thấy campaign tổng."}
        spec = CAMPAIGN_TYPES[tk]
        sname = (name or "").strip() or spec[2]
        camp = await campaigns_v2.create_campaign(uid, name=sname, industry=prof.get("industry"),
                                                  primary_goal=tk, summary=(m.get("name") or "")[:400])
        sid = str((camp or {}).get("id") or "")
        if not sid:
            return {"error": "Không tạo được sub."}
        meta[sid] = {"role": "sub", "parent": str(master_id), "type": tk, "type_label": spec[2],
                     "type_icon": spec[1], "group": spec[0], "audience": _TYPE_AUDIENCE.get(tk, "Tất cả"),
                     "persistent": (spec[4] == 0), "tracks": _tracks_for(spec[3]),
                     "tasks": _build_campaign_tasks(tk)}
        m.setdefault("sub_ids", []).append(sid)
        extra["campaign_meta"] = meta
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "sub_id": sid}
    except Exception as e:
        logger.warning("biz.commit_subcampaign failed: %s", e)
        return {"error": str(e)}


async def gen_sub_content(user_id=None, sub_id: str = "") -> dict:
    """S-10c: sinh BRIEF + TOPICS theo tuyến cho 1 sub-campaign. Bám đặt-cược master (gap/wedge/USP)
    + mục tiêu sub + vai-trò-tuyến. 2 LLM call (brief + topics). Lưu meta[sub].brief_run_id + tracks[].topics."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, skill_runs
        prof, extra, meta = await _campaign_meta(uid)
        sub = meta.get(str(sub_id))
        if not sub or sub.get("role") != "sub":
            return {"error": "Không tìm thấy sub-campaign."}
        master = meta.get(str(sub.get("parent"))) or {}
        _mgaps = master.get("gaps") or ([master.get("gap")] if master.get("gap") else [])
        gap = " + ".join((g or {}).get("title", "") for g in _mgaps if g) or (master.get("gap") or {}).get("title") or ""
        wedge = master.get("wedge") or (extra.get("wedge") or "")
        usp = master.get("usp") or prof.get("usp") or ""
        industry = prof.get("industry") or ""
        synth = await _latest_content(uid, "synthesis")
        objective = CAMPAIGN_TYPES.get(sub.get("type"), ("", "", "", "brand"))[3]
        tracks = sub.get("tracks") or _tracks_for(objective)
        is_persist = bool(sub.get("persistent"))
        tracks_desc = " · ".join(f"{t['label']} ({t['role']})" for t in tracks)
        from tools.llm_router import call as router_call, TaskType
        import json as _json
        # (1) brief sub — bám đặt cược + mục tiêu sub
        smart_rule = ("KHÔNG SMART số/deadline (nền liên tục)." if is_persist
                      else "Mục tiêu định hướng theo mục tiêu sub; số cụ thể chốt khi lập đợt — KHÔNG bịa.")
        b_sys = (f"Bạn là CMO viết BRIEF cho SUB-CAMPAIGN '{sub.get('type_label')}' (mục tiêu: {objective}) "
                 f"trong campaign tổng (đặt cược: đánh GAP + tệp wedge + USP). Bám đặt-cược + synthesis.\n"
                 "MARKDOWN gọn: ## Mục tiêu sub · ## Tệp nhắm + insight · ## Thông điệp chính · "
                 f"## Các tuyến bài & vai trò ({tracks_desc}) · ## KPI định hướng (đo gì).\n"
                 f"🔴 {smart_rule} Bám archetype ngành. TIẾNG VIỆT, không bịa số.")
        b_user = (f"# Ngành\n{industry}\n# Đặt cược (master)\n- Gap: {gap}\n- Wedge: {wedge or '(synthesis)'}\n"
                  f"- USP: {usp or '(synthesis)'}\n\n# Chiến lược\n{synth[:2200]}")
        b_res = await router_call(task_type=TaskType.OPS_BRIEF, system=b_sys, user=b_user, max_tokens=1800)
        brief = (b_res or {}).get("output", "").strip()
        brun = await skill_runs.insert_skill_run(uid, "subcampaign_brief", brief or "(trống)", model_used="web-sub") if brief else None
        # (2) topics theo tuyến — mỗi tuyến vài chủ đề + lens
        lens_opts = " · ".join(_VALUE_LENSES)
        tlist = "\n".join(f"{i+1}. {t['label']} — {t['role']}" for i, t in enumerate(tracks))
        t_sys = ("Bạn là Content Strategist. Với MỖI tuyến bài dưới, sinh 4-6 CHỦ ĐỀ bài CỤ THỂ (viết được ngay, "
                 "khác nhau) đúng VAI TRÒ tuyến (Khai sáng=giáo dục/nhận biết; Tin cậy=bằng chứng; Chuyển hoá=chốt; "
                 "Lan toả=tương tác). Mỗi chủ đề kèm 'lens' (góc khai thác) ∈ " + lens_opts + ".\n"
                 "Bám gap/wedge/USP + ngành. TIẾNG VIỆT, cụ thể, không generic.\n"
                 'Output JSON: {"tracks":[{"topics":[{"topic":"","lens":""}]}]} — ĐÚNG THỨ TỰ & SỐ tuyến.')
        t_user = (f"# Đặt cược\n- Gap: {gap}\n- Wedge: {wedge}\n- USP: {usp}\n# Ngành\n{industry}\n\n# CÁC TUYẾN\n{tlist}")
        t_res = await router_call(task_type=TaskType.INTAKE_JSON, system=t_sys, user=t_user, max_tokens=1800)
        traw = re.sub(r'\s*```\s*$', '', re.sub(r'^```(?:json)?\s*', '', (t_res or {}).get("output", "").strip())).strip()
        try:
            arr = _json.loads(traw).get("tracks") or []
        except Exception:
            arr = []
        for i, t in enumerate(tracks):
            tps = []
            if i < len(arr) and isinstance(arr[i], dict):
                for tp in (arr[i].get("topics") or []):
                    if isinstance(tp, dict) and str(tp.get("topic") or "").strip():
                        ln = str(tp.get("lens") or "").strip()
                        tps.append({"t": str(tp.get("topic"))[:160], "lens": ln if ln in _VALUE_LENSES else ""})
            t["topics"] = tps[:8]
        sub["tracks"] = tracks
        if brun:
            sub["brief_run_id"] = (brun or {}).get("id")
        extra["campaign_meta"] = meta
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "brief_run_id": sub.get("brief_run_id"),
                "tracks": [{"label": t["label"], "topics": len(t.get("topics") or [])} for t in tracks]}
    except Exception as e:
        logger.warning("biz.gen_sub_content failed: %s", e)
        return {"error": str(e)}


async def gen_branding_brief(user_id=None) -> dict:
    """M-G (G1): tạo/cập nhật campaign BRANDING NỀN (xuyên suốt). 1 LLM call sinh brand brief
    (big idea + key message + định vị nền + KPI định hướng) bám synthesis/playbook — KHÔNG SMART/
    deadline/offer (tham khảo bot CAMPAIGN_BRIEF, bỏ phần số/deadline). Lưu campaigns_v2 row
    (type=branding, không ngày) + meta + task. 1 user 1 branding (có thì cập nhật brief)."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        synth = await _latest_content(uid, "synthesis")
        if not synth.strip():
            return {"error": "Cần Chiến lược (Synthesis) trước khi tạo campaign Branding."}
        tact = await _latest_content(uid, "tactical_playbook")
        from storage.v2 import profiles, skill_runs, campaigns_v2
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        if not isinstance(extra, dict):
            extra = {}
        industry = prof.get("industry") or ""
        usp = prof.get("usp") or ""
        wedge = (extra.get("wedge") or "")
        _ans = (extra.get("answers") if isinstance(extra.get("answers"), dict) else {}) or {}
        team_size = _ans.get("team_size") or ""
        cur_channels = prof.get("current_channels") or _ans.get("current_channels") or ""
        from frameworks.industry_context import get_purchase_archetype, ARCHETYPE_LABEL
        arche = ARCHETYPE_LABEL.get(get_purchase_archetype(industry) or "", "")
        from tools.llm_router import call as router_call, TaskType
        system = (
            "Bạn là Campaign Strategist viết BRIEF cho 1 CAMPAIGN THƯƠNG HIỆU NỀN (branding) — chạy "
            "LIÊN TỤC, xuyên suốt (Byron Sharp: hiện diện đều để được nhớ). 🔴 Đây KHÔNG phải đợt: "
            "TUYỆT ĐỐI KHÔNG có offer/deadline/SMART số/urgency — chỉ định hướng được-nhớ.\n"
            "Bám Chiến lược (Synthesis) + Tactical Playbook đã có. Xuất MARKDOWN gồm:\n"
            "## 1. Big idea & Key message (concept xuyên suốt + điều khách phải nhớ về thương hiệu)\n"
            "## 2. Định vị nền (kế thừa synthesis — câu định vị + vì sao khác biệt)\n"
            "## 3. Tệp nhắm + insight ngầm (rộng theo Byron Sharp — chạm cả khách chưa mua)\n"
            "## 4. Trục nội dung (content pillars) — vai trò mỗi trụ trong xây nhận biết/niềm tin\n"
            "## 5. Kênh + vai trò mỗi kênh (kênh nào xây nhận biết, kênh nào nuôi niềm tin)\n"
            "## 6. Creative direction (tone & visual mood VN + 3 hook angle thương hiệu)\n"
            "## 7. KPI định hướng (reach/tần suất/nhớ thương hiệu — ĐO GÌ, KHÔNG target/deadline)\n\n"
            "🔴 Bám archetype ngành + nguồn lực (đề xuất khả thi, không vẽ quá sức). KHÔNG bịa số. "
            "Diễn đạt tự nhiên, TIẾNG VIỆT."
        )
        user = (f"# Ngành\n{industry} — {arche}\n# USP\n{usp or '(chưa rõ)'}\n# Wedge\n{wedge or '(chưa chọn)'}\n"
                f"# Nguồn lực\n- Đội: {team_size or '(nhỏ)'}\n- Kênh: {cur_channels or '(chưa rõ)'}\n\n"
                f"# Chiến lược (Synthesis)\n{synth[:3200]}\n\n# Tactical Playbook\n{(tact or '(chưa có)')[:1800]}")
        res = await router_call(task_type=TaskType.OPS_BRIEF, system=system, user=user, max_tokens=2600)
        brief = (res or {}).get("output", "").strip()
        if not brief:
            return {"error": "Chưa sinh được brief — thử lại."}
        run = await skill_runs.insert_skill_run(uid, "branding_brief", brief, model_used="web-branding")
        run_id = (run or {}).get("id")
        spec = CAMPAIGN_TYPES["branding"]
        meta = extra.get("campaign_meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        # 1 user 1 branding: tìm cái có sẵn → cập nhật; chưa có → tạo campaigns_v2 row
        cid = next((k for k, v in meta.items() if isinstance(v, dict) and v.get("type") == "branding"), None)
        if cid is None:
            camp = await campaigns_v2.create_campaign(
                uid, name="Branding nền", industry=prof.get("industry"),
                primary_goal="brand", summary=brief[:500], brief_skill_run_id=run_id)
            cid = str((camp or {}).get("id") or "")
            if not cid:
                return {"error": "Không tạo được campaign."}
            meta[cid] = {"type": "branding", "type_label": spec[2], "type_icon": spec[1],
                         "group": spec[0], "audience": "Tất cả", "persistent": True,
                         "brief_run_id": run_id, "tasks": _build_campaign_tasks("branding")}
        else:
            meta[cid]["brief_run_id"] = run_id   # cập nhật brief, giữ task
        extra["campaign_meta"] = meta
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "campaign_id": cid, "brief_run_id": run_id}
    except Exception as e:
        logger.warning("biz.gen_branding_brief failed: %s", e)
        return {"error": str(e)}


async def clear_campaign_portfolio(user_id=None, index: int = -1) -> dict:
    """M-F (F2): bỏ 1 mục (index) hoặc cả danh mục (index<0) khỏi proposal đã lưu."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles
        prof = await profiles.get_profile(uid) or {}
        extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
        if not isinstance(extra, dict):
            extra = {}
        lst = extra.get("campaign_portfolio") or []
        if index is not None and index >= 0 and index < len(lst):
            lst.pop(index)
            extra["campaign_portfolio"] = lst
        else:
            extra.pop("campaign_portfolio", None)
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "remaining": len(extra.get("campaign_portfolio") or [])}
    except Exception as e:
        logger.warning("biz.clear_campaign_portfolio failed: %s", e)
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
            "→ PHỦ ĐỦ 4 trạng thái vòng đời (diễn đời thường, KHÔNG thuật ngữ RFM): khách MỚI (vừa mua "
            "lần đầu) · đang ĐỀU (mua nhiều lần) · có dấu hiệu NGUỘI (đều rồi tự nhiên thưa) · đã RỜI lâu "
            "(mất hút) — hợp mode đang chọn. Dấu hiệu CỤ THỂ (vd 'mua đều rồi ~3 tuần không quay lại').\n"
            "## 2. Nhịp liên hệ theo chu kỳ ngành (lần 1 → 2 → 3)\n"
            "Gợi ý mốc chạm sau mỗi lần mua theo CHU KỲ NGÀNH (vd spa 4-6 tuần: ngày 3 hỏi thăm → ngày 25 "
            "nhắc lịch → ngày 35 ưu đãi; F&B 1-2 tuần; clinic/giáo dục dài hơn). Mỗi mốc: làm gì + kênh.\n"
            "## 3. Loyalty/tier mộc (đếm tay được, không cần phần mềm)\n"
            "2-4 bậc đơn giản (vd Mua-lần-đầu → Khách-quen → VIP) + điều kiện đếm tay + quyền lợi gợi ý "
            "hợp ngành. Chỉ làm nếu hợp mode (winback có thể bỏ).\n"
            "## 4. KPI tự theo dõi thủ công (repeat/AOV/tỉ lệ quay lại — cách đếm mộc, không cần phần mềm)\n"
            "## 5. Mẹo nhịp & ưu tiên (làm gì trước với nguồn lực nhỏ)\n\n"
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
        res = await router_call(task_type=TaskType.OPS_BRIEF, system=system, user=user, max_tokens=3000)
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


def _ppw(v) -> int:
    """Chuẩn hoá posts_per_week → số nguyên 1..7 (mặc định 1)."""
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return 1
    return max(1, min(n, 7))


def _assign_days(k: int) -> list:
    """Rải k bài/tuần ra 7 thứ (0=T2..6=CN) đều nhau, deterministic."""
    if k <= 0:
        return []
    return [min(6, round(i * 7 / k)) for i in range(k)]


# 30/60/90 ngày → số tuần hiển thị (auto/khác → 4 tuần, nhịp tháng).
_HORIZON_WEEKS = {"30": 4, "60": 9, "90": 13}

# M-D Pha 3: Story Arc của 1 ĐỢT occasion — 5 pha + vị trí (fraction trong window) + hint.
# Đợt ≤1 tuần dùng bản gộp 3 pha (_OCC_PHASES_SHORT).
_OCC_PHASES = [
    ("Teaser",    "🌱", 0.00, 0.18, "hé lộ, gây tò mò — CHƯA lộ offer"),
    ("Build-up",  "🔥", 0.18, 0.55, "nuôi giá trị, social proof, xử lý phản đối"),
    ("Peak",      "🚀", 0.55, 0.72, "đẩy mạnh nhất — ngày trọng tâm của đợt"),
    ("Last-call", "⏰", 0.72, 0.90, "urgency + deadline, chốt gấp"),
    ("After",     "💌", 0.90, 1.00, "hậu mãi/cảm ơn/upsell + kéo người lỡ"),
]
_OCC_PHASES_SHORT = [
    ("Teaser",    "🌱", 0.00, 0.33, "hé lộ + nuôi nhanh"),
    ("Peak",      "🚀", 0.33, 0.70, "đẩy mạnh nhất"),
    ("Last-call", "⏰", 0.70, 1.00, "urgency + deadline + cảm ơn"),
]
_OCC_PHASE_HINT = {p[0]: p[4] for p in _OCC_PHASES}


def _occasion_beats(sd: str, ed: str, anchor) -> list:
    """Suy beat theo 5 pha (đợt ≤1 tuần → 3 pha) đặt vào (tuần,ngày) trong window.
    Mỗi beat: {week, day, phase, icon, hint}. Deterministic — không LLM."""
    from datetime import date, timedelta
    try:
        sy, sm, sdd = (int(x) for x in str(sd)[:10].split("-"))
        ey, em, edd = (int(x) for x in str(ed)[:10].split("-"))
        d0, d1 = date(sy, sm, sdd), date(ey, em, edd)
    except Exception:
        return []
    total = max(0, (d1 - d0).days)
    phases = _OCC_PHASES_SHORT if total <= 7 else _OCC_PHASES
    beats = []
    seen = set()
    for name, icon, a, b, hint in phases:
        f = (a + b) / 2
        pt = d0 + timedelta(days=round(f * total))
        wk = _week_of(pt.strftime("%Y-%m-%d"), anchor)
        if wk is None:
            continue
        wk = max(1, wk)
        dy = pt.weekday()                 # 0=T2 .. 6=CN
        if (wk, dy) in seen:              # tránh trùng ô khi window ngắn
            dy = (dy + 1) % 7
        seen.add((wk, dy))
        beats.append({"week": wk, "day": dy, "phase": name, "icon": icon, "hint": hint})
    return beats


def _pillar_id(p: dict) -> str:
    """M-E: id dùng cho key/ref. Locked pillar có uuid; bản sinh (chưa chốt) → slug từ tên."""
    pid = str((p or {}).get("id") or "").strip()
    if pid:
        return pid
    return "n_" + (re.sub(r'[^a-z0-9]+', '', str((p or {}).get("name") or "pillar").lower())[:12] or "pillar")


def _normalize_saved(key: str, val, pillars_by_name: dict) -> dict | None:
    """M-E: chuẩn hoá 1 entry calendar_posts về thẻ {track,pillarId,campaignId,phase,week,day,content}.
    Đọc cả schema MỚI (có ref/place) lẫn key CŨ (aw|w|d|name, oc|cid|phase, value phẳng) → migration mềm."""
    if not isinstance(val, dict):
        return None
    content = (val.get("content") or "").strip()
    if not content:
        return None
    # schema mới
    if isinstance(val.get("ref"), dict):
        ref = val["ref"]; place = val.get("place") or {}
        tr = val.get("track") or ("camp" if ref.get("campaignId") else "always")
        return {"track": tr, "pillarId": str(ref.get("pillarId") or ""),
                "campaignId": str(ref.get("campaignId") or ""), "phase": str(ref.get("phase") or place.get("phase") or ""),
                "week": place.get("week"), "day": place.get("day"), "content": content, "key": key}
    # key cũ
    parts = (key or "").split("|")
    if parts and parts[0] == "oc" and len(parts) >= 3:
        return {"track": "camp", "pillarId": "", "campaignId": parts[1], "phase": parts[2],
                "week": None, "day": None, "content": content, "key": key}
    if parts and parts[0] == "aw" and len(parts) >= 4:
        # aw|week|day|name → match name → pillarId hiện tại
        try: wk, dy = int(parts[1]), int(parts[2])
        except Exception: wk, dy = None, None
        name = "|".join(parts[3:])
        pid = _pillar_id(pillars_by_name[name]) if name in pillars_by_name else ""
        return {"track": "always", "pillarId": pid, "campaignId": "", "phase": "",
                "week": wk, "day": dy, "content": content, "key": key}
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

        # M-A: span lịch = horizon đã chọn ở gate (30/60/90 ngày → tuần); auto/khác = 4.
        from storage.v2 import profiles as _profiles
        _prof = await _profiles.get_profile(uid) or {}
        _extra = _prof.get("intake_extra") if isinstance(_prof.get("intake_extra"), dict) else {}
        _hz = (_extra or {}).get("horizon")
        horizon_weeks = _HORIZON_WEEKS.get(str(_hz or ""), 4)
        saved_raw = (_extra or {}).get("calendar_posts") or {}
        if not isinstance(saved_raw, dict):
            saved_raw = {}

        # M-E: pillars trước (cần để chuẩn hoá bài đã lưu + phát hiện orphan).
        plan = await campaign_plan(uid)
        pillars = (plan or {}).get("pillars") or []
        for p in pillars:
            if isinstance(p, dict):
                p["_pid"] = _pillar_id(p)
        pillars_by_name = {str(p.get("name") or ""): p for p in pillars if isinstance(p, dict)}
        pillars_by_id = {p["_pid"]: p for p in pillars if isinstance(p, dict)}

        # M-E: chuẩn hoá bài đã lưu thành thẻ (migration mềm key cũ) + index theo ref+place.
        cards = [c for c in (_normalize_saved(k, v, pillars_by_name) for k, v in saved_raw.items()) if c]
        idx_always, idx_camp = {}, {}
        for c in cards:
            if c["track"] == "camp":
                idx_camp[(c["campaignId"], c["phase"])] = c
            else:
                idx_always[(c["pillarId"], c["week"], c["day"])] = c
        consumed = set()   # storage-key của thẻ ĐÃ đặt lên lịch (phần còn lại = orphan)

        from storage.v2 import campaigns_v2
        camps_raw = await campaigns_v2.list_campaigns_v2(uid, limit=30)
        bands, bands_by_cid, camp_ids = [], {}, set()
        max_week = horizon_weeks
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
            cid = str(c.get("id"))
            camp_ids.add(cid)
            # M-D Pha 3: beat theo Story Arc 5 pha (đợt ≤1 tuần → 3 pha) thay vì 3 bài generic.
            beats = _occasion_beats(sd, ed, anchor)
            if not beats:                       # fallback an toàn nếu parse lỗi
                beats = [{"week": fw, "day": 2, "phase": "Peak", "icon": "🚀", "hint": "đẩy mạnh đợt"}]
            posts = []
            for bt in beats:
                key = f"oc|{cid}|{bt['phase']}"
                post = {"week": bt["week"], "day": bt["day"], "phase": bt["phase"],
                        "icon": bt["icon"], "hint": bt["hint"],
                        "title": f"{bt['icon']} {bt['phase']} — {name}", "key": key}
                card = idx_camp.get((cid, bt["phase"]))
                if card:
                    post["saved"] = True; post["post"] = card["content"]
                    consumed.add(card["key"])
                posts.append(post)
            band = {"name": name, "occasion": c.get("primary_goal") or "đợt",
                    "offer": offer or "ưu đãi đợt", "color": color,
                    "fromWeek": fw, "toWeek": tw, "posts": posts,
                    "campaignId": c.get("id"), "briefRunId": c.get("brief_skill_run_id")}
            bands.append(band); bands_by_cid[cid] = band

        # Always-on từ pillars đã chốt (M4(2)) — rải theo NHỊP (posts_per_week) suốt HORIZON.
        # Mỗi trụ xuất hiện posts_per_week lần/tuần; angles xoay theo tuần cho đa dạng.
        # Pha 2: nếu có calendar_topics (Max sinh sẵn) → gán chủ đề CỤ THỂ theo lần xuất hiện.
        topics_map = (_extra or {}).get("calendar_topics") or {}
        if not isinstance(topics_map, dict):
            topics_map = {}
        occ = {}   # đếm lần xuất hiện mỗi pillar (để lấy topic thứ k)
        always = []
        if pillars:
            weekly = []                      # 1 phần tử = 1 slot/tuần (lặp theo nhịp trụ)
            for p in pillars:
                for _ in range(_ppw(p.get("posts_per_week"))):
                    weekly.append(p)
            weekly = weekly[:14]             # trần an toàn ~2 bài/ngày
            day_of = _assign_days(len(weekly))
            def _topic_lens(item):   # hỗ trợ {t,lens} (mới) lẫn chuỗi thuần (cũ)
                if isinstance(item, dict):
                    return (item.get("t") or ""), (item.get("lens") or "")
                return str(item), ""
            for w in range(1, max_week + 1):
                for idx, p in enumerate(weekly):
                    pid = p["_pid"]
                    angles = p.get("angles") or []
                    k = occ.get(pid, 0); occ[pid] = k + 1
                    tlist = topics_map.get(pid) or []
                    # M-E2: chip gợi ý = các CHỦ ĐỀ Việt Pha 2 (nếu có) thay vì angle gốc (có thể tiếng Anh);
                    # mỗi chip mang kèm góc khai thác (lens) riêng → bấm chip đổi cả topic lẫn góc.
                    pairs = [_topic_lens(it) for it in tlist]
                    pairs = [(t, l) for (t, l) in pairs if t]
                    if pairs:
                        topic, lens = pairs[k % len(pairs)]
                        chips = [t for (t, _l) in pairs[:8]]
                        chip_lens = [l for (_t, l) in pairs[:8]]
                    else:
                        topic = (angles[(idx + w) % len(angles)] if angles
                                 else (p.get("role") or p.get("name") or "Bài brand"))
                        lens = ""
                        chips = [str(a) for a in (p.get("angles") or [])][:6]
                        chip_lens = []
                    pname = p.get("name") or "Pillar"
                    key = f"aw|{pid}|{w}|{day_of[idx]}"
                    slot = {"week": w, "day": day_of[idx], "pillar": pname, "pillarId": pid,
                            "title": topic, "topic": topic, "angles": chips, "angleLens": chip_lens,
                            "funnel": p.get("funnel") or "", "framework": p.get("framework") or "",
                            "value_lens": lens or p.get("value_lens") or "",
                            "track": "always", "key": key}
                    card = idx_always.get((pid, w, day_of[idx]))
                    if card:
                        slot["saved"] = True; slot["post"] = card["content"]
                        consumed.add(card["key"])
                    always.append(slot)

        # M-E: INJECT thẻ đã duyệt chưa khớp ô gợi ý (đổi cadence/thứ tự) — trụ còn tồn tại,
        # vị trí trong horizon → hiện đúng chỗ, KHÔNG mất. Ngoài horizon / trụ mất → orphan.
        for c in cards:
            if c["key"] in consumed:
                continue
            if c["track"] == "always":
                p = pillars_by_id.get(c["pillarId"])
                w, d = c["week"], (c["day"] if c["day"] is not None else 0)
                if p and isinstance(w, int) and 1 <= w <= max_week:
                    always.append({"week": w, "day": d, "pillar": p.get("name") or "Pillar",
                                   "pillarId": c["pillarId"], "title": (p.get("role") or p.get("name") or "Bài brand"),
                                   "angles": [str(a) for a in (p.get("angles") or [])][:6],
                                   "funnel": p.get("funnel") or "", "framework": p.get("framework") or "",
                                   "value_lens": p.get("value_lens") or "", "track": "always",
                                   "key": c["key"], "saved": True, "post": c["content"]})
                    consumed.add(c["key"])
            else:
                band = bands_by_cid.get(c["campaignId"])
                if band and isinstance(c["week"], int):
                    band["posts"].append({"week": c["week"], "day": (c["day"] if c["day"] is not None else 0),
                                          "phase": c["phase"] or "Đợt", "icon": "📌", "hint": "bài đã duyệt",
                                          "title": f"📌 {c['phase'] or 'Đợt'} — {band['name']}",
                                          "key": c["key"], "saved": True, "post": c["content"]})
                    consumed.add(c["key"])

        # M-E: phần còn lại = orphan (trụ/đợt đã bị bỏ, hoặc ngoài horizon) → khay, KHÔNG mất.
        orphans = []
        for c in cards:
            if c["key"] in consumed:
                continue
            orphans.append({"key": c["key"], "track": c["track"],
                            "content": c["content"], "excerpt": c["content"][:160],
                            "label": ("Always-on" if c["track"] == "always" else "Đợt"),
                            "reason": "Trụ/đợt liên quan đã đổi hoặc bị bỏ — xếp lại hoặc lưu vào Tài liệu."})

        if not bands and not always and not orphans:
            return {}   # chưa có gì thật → FE giữ mock
        return {"days": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
                "weeks": max_week, "alwaysOn": always, "campaigns": bands, "orphans": orphans,
                "horizon": str(_hz or "auto")}
    except Exception as e:
        logger.warning("biz.calendar_plan failed (non-fatal): %s", e)
        return {}


async def gen_calendar_post(user_id=None, track: str = "always", pillar: str = "",
                            campaign_id: str = "", week: str = "", day: str = "",
                            angle: str = "", value_lens: str = "", hook_style: str = "",
                            framework: str = "", phase: str = "",
                            campaign_gap: str = "", objective: str = "", track_role: str = "") -> dict:
    """M1.2b + M-D: sinh 1 BÀI cho slot lịch — bám pillar (always-on) hoặc brief occasion.
    angle = CHỦ ĐỀ founder chọn; value_lens = GÓC KHAI THÁC; hook_style = CÁCH MỞ (1/5 nhóm);
    framework = khung copywriting ẩn. Lưu skill_run `calendar_post`. Degrade {error}."""
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
        target = prof.get("target_customer") or ""
        product = prof.get("product_service") or ""
        # Brand voice (nếu có) → giọng nhất quán
        voice_ctx = ""
        try:
            from storage import brand_voice as _bv
            bv = await _bv.get_brand_voice(uid)
            if bv:
                tone = (bv.get("tone") or bv.get("voice") or "") if isinstance(bv, dict) else ""
                if tone:
                    voice_ctx = f"\n# Brand voice\n{str(tone)[:300]}"
        except Exception:
            pass
        ctx, kind, lines = "", "", []
        if track == "camp" and campaign_id:
            from storage.v2 import campaigns_v2
            c = await campaigns_v2.get_campaign(campaign_id) or {}
            brief = ""
            if c.get("brief_skill_run_id"):
                run = await skill_run_content(c["brief_skill_run_id"])
                brief = (run or {}).get("content") or c.get("summary") or ""
            lines.append(f"Đợt: {c.get('name','')}. Brief:\n{brief[:1800]}")
            if (phase or "").strip():
                lines.append(f"Bài thuộc PHA: {phase} — mục tiêu pha: {_OCC_PHASE_HINT.get(phase, '')}")
            kind = "1 bài cho ĐỢT theo dịp, bám đúng PHA của Story Arc (CTA hợp pha)"
        else:
            lines.append(f"Content pillar (always-on, nền brand): {pillar or '(brand)'}")
            kind = "1 bài NỀN brand bám pillar (xây nhận biết/niềm tin — KHÔNG ép bán)"
        # M-G (post-wiring): context chuỗi campaign tổng → bài bám đúng đặt-cược + VAI TRÒ TUYẾN.
        if (campaign_gap or "").strip():
            lines.append(f"Đặt cược campaign tổng (gap đang đánh): {campaign_gap}")
        if (track_role or "").strip():
            lines.append(f"VAI TRÒ TUYẾN của bài này: {track_role} — viết ĐÚNG vai trò này "
                         "(Khai sáng=giáo dục/nhận biết, KHÔNG bán; Tin cậy=bằng chứng/case; "
                         "Chuyển hoá=chốt/CTA mạnh; Lan toả=tương tác/share).")
        elif (objective or "").strip():
            lines.append(f"Mục tiêu sub-campaign: {objective}")
        # Trục chung cho cả 2 track (M-D Pha 2): chủ đề + góc khai thác + khung ẩn.
        if (angle or "").strip():
            lines.append(f"Chủ đề cụ thể (founder chọn — bám SÁT): {angle}")
        if (value_lens or "").strip():
            lines.append(f"Góc khai thác (value lens) BẮT BUỘC bám: {value_lens}")
        if (framework or "").strip():
            lines.append(f"Khung copywriting ẩn gợi ý: {framework}")
        ctx = "\n".join(lines)
        # Cách mở: founder chọn 1 hook style cụ thể → ép dùng; nếu không → để LLM tự chọn trong 5 nhóm.
        hook_rule = (f"\n🔴 CÁCH MỞ bài DÙNG ĐÚNG nhóm hook: {hook_style}." if (hook_style or "").strip()
                     and hook_style.lower() not in ("auto", "tự động") else "")
        from tools.llm_router import call as router_call, TaskType
        system = (
            "Bạn là content writer social media giỏi cho founder Việt. Viết " + kind + ".\n\n"
            "🪝 HOOK (câu đầu) — chọn 1 trong 5 góc, hợp tệp khách + tầng phễu, viết cho SẮC:\n"
            "  • Tò mò (paradox/câu hỏi tiết lộ) • Trái ngược (đảo niềm tin) • Cảm xúc (chạm pain thật)\n"
            "  • Góc nhìn chuyên gia (POV người trong nghề) • Đồng cảm (kể đúng trải nghiệm khách).\n"
            "📝 THÂN: 1 ý chính, có chi tiết/ví dụ ĐỜI THỰC; dùng PAS/AIDA làm khung XƯƠNG ẨN; lồng USP qua "
            "bằng chứng/câu chuyện, KHÔNG hô khẩu hiệu.\n"
            "📣 CTA: 1 dòng CỤ THỂ (vd \"Inbox 'tư vấn' để em check giúp\"); bài nền thì CTA mềm "
            "(lưu/chia sẻ/comment), đừng ép mua.\n"
            "#️⃣ 3-5 hashtag tiếng Việt, trộn 3 loại: thương hiệu + ngách + xu hướng.\n"
            "💡 Kết bằng đúng 1 dòng \"Gợi ý ảnh: …\" (concept hình minh hoạ ngắn — để founder tự chụp/đặt).\n\n"
            "🔴 NGHIÊM CẤM: mở bài generic ('Bạn có biết…?', 'Hôm nay mình chia sẻ…'), CTA 'Tìm hiểu thêm', "
            "bịa số/khuyến mãi không có thật; TUYỆT ĐỐI không in nhãn khung ('Hook:', 'Thân:', 'CTA:', "
            "'Problem:', 'Mở:'…) ra bài — bài đọc tự nhiên, copy-paste đăng được ngay.\n"
            "🔴 Trong NỘI DUNG gọi người đọc là 'bạn' hoặc 'anh/chị' (KHÔNG 'sếp'). Nếu có 'Chủ đề cụ thể' "
            "→ bám ĐÚNG. Bám USP + đúng tệp khách + ngành. Viết TIẾNG VIỆT tự nhiên. Trả MARKDOWN gọn."
            + hook_rule
        )
        user = (f"# Ngành\n{industry}\n# Sản phẩm/dịch vụ\n{product or '(chưa rõ)'}\n"
                f"# Khách mục tiêu\n{target or '(chưa rõ)'}\n# USP\n{usp or '(chưa rõ)'}{voice_ctx}\n\n"
                f"# Bối cảnh slot\n{ctx}")
        res = await router_call(task_type=TaskType.OPS_CONTENT_CREATIVE, system=system, user=user, max_tokens=900)
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


# M-F (F1b): mỗi task của campaign → 1 generator bám CONTEXT ĐỢT (brief). Content task = deliverable;
# action:* = hướng dẫn thực thi + mẫu cho người làm (Max KHÔNG thực thi ngoài đời).
_CAMPAIGN_TASK_GEN = {
    "calendar_post":       ("OPS_CONTENT_CREATIVE", 900,  "Viết 1 BÀI ĐĂNG mẫu organic cho đợt (hook + body + CTA), bám brief đợt + USP."),
    "post_channels":       ("CHANNEL_ADAPT",        1100, "Biến thông điệp đợt thành biến thể cho 3-4 kênh (FB/Zalo/TikTok/IG) — mỗi kênh đúng đặc tính."),
    "video_script":        ("OPS_CONTENT_CREATIVE", 1500,
        "Viết KỊCH BẢN VIDEO quay-được-ngay (TikTok/Reels/Shorts) cho đợt. Chọn FRAMEWORK theo pillar/funnel "
        "(PAS=TOFU/educate · BAB=MOFU/before-after · AIDA=narrative · FAB=BOFU/chốt · Star-Story/Storytime=viral). "
        "Viết LỜI THOẠI THẬT từng beat kèm timing (Xs) — TUYỆT ĐỐI không placeholder kiểu '[giới thiệu SP]'. "
        "Hook ở đầu (1 trong 5 nhóm: tò mò/trái ngược/cảm xúc/chuyên gia/đồng cảm). Kèm: Visual direction (shot "
        "list từng beat) + Music/SFX + Caption hook ≤125 ký tự + 8-12 hashtag VN (branded+niche+trending). "
        "Proof chưa có data thật → ghi '[chèn review khách thật]', KHÔNG bịa số."),
    "ugc_brief":           ("OPS_BRIEF",            1400,
        "Viết CREATOR BRIEF giao UGC/KOL cho đợt — chi tiết tới mức creator không hỏi lại. Mỗi brief đủ 9 phần: "
        "Creator Type (UGC micro 1K-50K / KOL 100K+ / EGC nhân viên / FGC khách cũ) · Platform · Objective · "
        "Brand Voice (tone + từ nên/tránh) · Key Message (1-2 câu) · Content Requirements (cảnh quay/lời thoại "
        "gợi ý/thời lượng/góc máy/ánh sáng/background) · Don'ts (claim sai, cách mention brand) · Hashtags 5-8 "
        "(branded+niche+trending) · Disclosure (#ad). Specific quay-được-ngay (KHÔNG generic 'thể hiện tự nhiên'); "
        "KPI realistic theo size (micro 3-5% ER, mid 2-3%, KOL 1-2%). KHÔNG budget/payment/deadline."),
    "ads_copy":            ("OPS_CONTENT_CREATIVE", 1500,
        "Viết bộ ADS COPY dùng-được-ngay cho đợt, theo phễu TOFU/MOFU/BOFU — mỗi tầng vài variant. Chọn framework "
        "hợp tầng (AIDA/PAS=TOFU · BAB/4P=MOFU · FAB=BOFU · Star-Story=viral). Luật VN: 125 ký tự đầu là vàng; "
        "MỞ bằng câu hỏi/statement chạm pain, KHÔNG mở bằng tên brand; tránh từ trigger spam ('miễn phí/khuyến "
        "mãi/giảm giá') ở headline; 1-2 emoji; CTA cụ thể ('Inbox ngay' > 'Tìm hiểu thêm'); BOFU có deadline THẬT. "
        "Mỗi variant dùng ≥1 emotion trigger (sợ mất/tự hào/cộng đồng/tò mò/kết quả cụ thể/đau ngầm). CẤM generic "
        "kiểu 'sản phẩm chất lượng cao giá tốt'. Mỗi variant ghi rõ tầng phễu + framework + kênh."),
    "email_zalo_sequence": ("OPS_CONTENT_BULK",     1600,
        "Build CHUỖI nurture Email + Zalo OA cho đợt (3-5 chặng), mỗi chặng 1 mục tiêu rõ. Phân kênh: Email cho "
        "long-form/B2B/khách >30t; Zalo OA cho short reminder/B2C. Tối đa 2-3 message/tuần (quá = spam). Mỗi chặng: "
        "thời điểm gửi (ngày T+x) · kênh · mục tiêu · tiêu đề/dòng mở (Zalo) · nội dung đầy đủ · CTA · cá nhân hoá "
        "(first_name + 1 field segment). Ghi rõ loại chuỗi (onboarding/re-engage/reactivation/upsell). Nội dung "
        "viết thật, dùng được ngay; KHÔNG bịa số/ưu đãi không có thật."),
    "sales_inbox_script":  ("OPS_CONTENT_CREATIVE", 1500,
        "Viết KỊCH BẢN chat sales/inbox cho đợt — nhân viên ca mới đọc 1 lần là chốt được. Tone match đợt "
        "(luxury formal / mass thân thiện-urgency / B2B value). 4 phần: (1) Opening (auto-reply 5 phút đầu + reply "
        "manual: chào + 1 câu hỏi mở dẫn dắt) · (2) Discovery (3-5 câu hỏi flow, mỗi câu kèm vì sao hỏi + cách "
        "handle) · (3) Recommendation (match offer theo câu trả lời + cách present nối lại pain) · (4) Handle "
        "Objections — 3 cái phổ biến (giá đắt / để suy nghĩ / so sánh đối thủ): Acknowledge → Reframe value → "
        "Alternative, kèm script cụ thể 3 dòng. Nguyên tắc: hỏi dẫn dắt (không liệt kê features), urgency THẬT, "
        "soft close (VN dị ứng pressure mạnh). LỜI THOẠI cụ thể, có placeholder tên khách."),
    "landing_copy":        ("OPS_CONTENT_CREATIVE", 1400, "Viết NỘI DUNG LANDING PAGE cho đợt: headline + sub + 3-5 khối (vấn đề/giá trị/bằng chứng/ưu đãi/FAQ) + CTA rõ. Ghi gợi ý bố cục."),
    "seo_outline":         ("OPS_BRIEF",            1300, "Lập DÀN BÀI SEO cho đợt: 5-10 từ khoá (intent) + cụm chủ đề + outline H1/H2/H3 cho 1-2 bài trụ + meta title/description gợi ý."),
    "pr_pitch":            ("OPS_CONTENT_CREATIVE", 1200, "Viết BÀI PR / pitch báo chí cho đợt: góc tin (news angle) + tiêu đề + thân bài ~300-400 chữ + boilerplate + mẫu email gửi báo."),
    "event_plan":          ("OPS_BRIEF",            1400, "Lập KẾ HOẠCH EVENT cho đợt: mục tiêu, định dạng, kịch bản chương trình theo mốc thời gian (pre/ngày/post), phân vai, checklist hậu cần, KPI."),
    "referral_plan":       ("OPS_BRIEF",            1200, "Thiết kế CƠ CHẾ GIỚI THIỆU (referral): cấu trúc thưởng cho người giới thiệu + người được giới thiệu, điều kiện, kênh chia sẻ, mẫu lời mời, chống gian lận."),
}
_ACTION_TASK_GEN = ("OPS_BRIEF", 1000,
    "Viết HƯỚNG DẪN THỰC THI + MẪU cho đầu việc này (các bước cụ thể + mẫu tin nhắn/checklist/yêu cầu) "
    "để người của founder dùng ngay. KHÔNG hứa tự động làm hộ.")


async def _campaign_meta(uid):
    """Đọc intake_extra.campaign_meta (+ profile) — dùng chung cho gen/update task."""
    from storage.v2 import profiles
    prof = await profiles.get_profile(uid) or {}
    extra = prof.get("intake_extra") if isinstance(prof.get("intake_extra"), dict) else {}
    meta = (extra or {}).get("campaign_meta") or {}
    return prof, (extra or {}), (meta if isinstance(meta, dict) else {})


async def gen_campaign_task(user_id=None, campaign_id: str = "", task_id: str = "") -> dict:
    """M-F (F1b): sinh deliverable cho 1 task của campaign (bám brief đợt). Lưu skill_run +
    cập nhật status='draft'+run_id trong campaign_meta. action task → hướng dẫn + mẫu."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if not (campaign_id or "").strip() or not (task_id or "").strip():
        return {"error": "Thiếu campaign_id/task_id."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles, skill_runs, campaigns_v2
        prof, extra, meta = await _campaign_meta(uid)
        cm = meta.get(str(campaign_id))
        if not cm:
            return {"error": "Không tìm thấy campaign."}
        task = next((t for t in (cm.get("tasks") or []) if t.get("id") == task_id), None)
        if not task:
            return {"error": "Không tìm thấy task."}
        kind = task.get("kind") or ""
        # context đợt: tên + brief
        camp = await campaigns_v2.get_campaign(str(campaign_id)) or {}
        brief = ""
        bid = camp.get("brief_skill_run_id")
        if bid:
            brief = (await skill_run_content(bid)).get("content") or ""
        if not brief:
            brief = camp.get("summary") or ""
        strat = await skill_runs.get_latest_skill_run(uid, "synthesis") or {}
        if kind.startswith("action:"):
            task_name, max_tok, instruction = _ACTION_TASK_GEN
        else:
            task_name, max_tok, instruction = _CAMPAIGN_TASK_GEN.get(
                kind, ("OPS_CONTENT_CREATIVE", 1000, "Viết deliverable bám brief đợt + USP."))
        from tools.llm_router import call as router_call, TaskType
        task_type = getattr(TaskType, task_name, TaskType.OPS_CONTENT_CREATIVE)
        system = ("Bạn là chuyên gia content/marketing người Việt. " + instruction + "\n"
                  "🔴 Bám BRIEF ĐỢT + USP + ngành; TIẾNG VIỆT tự nhiên; KHÔNG bịa số/khuyến mãi không có thật. "
                  "Trả MARKDOWN gọn, dùng được ngay.")
        user = (f"# Loại deliverable\n{task.get('label') or kind}\n"
                f"# Ngành\n{prof.get('industry') or ''}\n# USP\n{prof.get('usp') or '(chưa rõ)'}\n"
                f"# Khách mục tiêu\n{prof.get('target_customer') or '(chưa rõ)'}\n\n"
                f"# BRIEF ĐỢT: {camp.get('name') or ''}\n{brief[:2200] or '(chưa có brief — bám chiến lược)'}\n\n"
                f"# Chiến lược (tham chiếu)\n{(strat.get('content') or '')[:1200]}")
        res = await router_call(task_type=task_type, system=system, user=user, max_tokens=max_tok)
        content = (res or {}).get("output", "").strip()
        if not content:
            return {"error": "Chưa sinh được — thử lại."}
        run = await skill_runs.insert_skill_run(uid, kind.replace(":", "_"), content, model_used="web-camptask")
        rid = (run or {}).get("id")
        task["run_id"] = rid
        task["status"] = "draft"
        extra["campaign_meta"] = meta
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "content": content, "run_id": rid, "kind": kind}
    except Exception as e:
        logger.warning("biz.gen_campaign_task failed: %s", e)
        return {"error": str(e)}


async def update_campaign_task(user_id=None, campaign_id: str = "", task_id: str = "",
                               status: str = "") -> dict:
    """M-F (F1b): đổi status task (todo/draft/approved). approve = founder chốt deliverable/việc."""
    if not available():
        return {"error": "Chưa cấu hình Supabase."}
    if status not in ("todo", "draft", "approved"):
        return {"error": "status không hợp lệ."}
    try:
        await ensure_client()
        uid = await pick_user_id(user_id)
        if uid is None:
            return {"error": "Chưa có user."}
        from storage.v2 import profiles
        prof, extra, meta = await _campaign_meta(uid)
        cm = meta.get(str(campaign_id))
        if not cm:
            return {"error": "Không tìm thấy campaign."}
        task = next((t for t in (cm.get("tasks") or []) if t.get("id") == task_id), None)
        if not task:
            return {"error": "Không tìm thấy task."}
        task["status"] = status
        extra["campaign_meta"] = meta
        await profiles.upsert_profile(uid, intake_extra=extra)
        return {"ok": True, "status": status}
    except Exception as e:
        logger.warning("biz.update_campaign_task failed: %s", e)
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
        # Nguồn lực (đề xuất KHẢ THI, không vẽ quá sức): team_size (intake answers) + kênh đang dùng.
        _ans = (extra.get("answers") if isinstance(extra.get("answers"), dict) else {}) or {}
        team_size = _ans.get("team_size") or ""
        cur_channels = prof.get("current_channels") or _ans.get("current_channels") or ""
        resource_block = (f"# Nguồn lực (đề xuất phải KHẢ THI với cái này)\n"
                          f"- Đội làm marketing: {team_size or '(chưa rõ — giả định nhỏ)'}\n"
                          f"- Kênh đang dùng: {cur_channels or '(chưa rõ)'}\n\n")

        # Vision A: ĐẶT CƯỢC theo 5 nhóm founder đã chọn → T4-T5 bám CHẶT lựa chọn này.
        bet_block = ""
        _bc = extra.get("bet_choices") if isinstance(extra.get("bet_choices"), dict) else {}
        if _bc and any(_bc.values()):
            _lines = []
            for _k, _spec in BET_CATEGORIES.items():
                _vals = _bc.get(_k) or []
                if _vals:
                    _lines.append(f"- {_spec[1]}: {' · '.join(_vals)}")
            if _lines:
                bet_block = ("# ĐẶT CƯỢC FOUNDER ĐÃ CHỌN (bám CHẶT — đây là kim chỉ nam, KHÔNG đi lệch)\n"
                             + "\n".join(_lines) + "\n\n")

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
            "trình bày khuyến nghị + lý do + đánh đổi để sếp quyết.\n\n"
            "🔴 VIẾT NHƯ MỘT MẠCH LẬP LUẬN TÍCH HỢP, không phải danh sách framework rời. 'SÂU' = logic "
            "NỐI research→lựa chọn (vì sao chọn nước này), không phải nhiều section song song. Ngắn mà sắc.\n"
            "🔴 GẮN NHÃN SỐ — chống bịa: mọi con số (benchmark/%/KPI) phải lấy từ số THẬT của user, có nguồn, "
            "HOẶC gắn '(ước tính)' ngay sau. TUYỆT ĐỐI không nêu số tự nhớ như fact.\n"
            "🔴 TÁCH RÕ 2 TẦNG THỜI GIAN: Định vị (BỀN, mục 3) vs Roadmap (theo NHỊP, mục 5) — đây là điểm "
            "cốt lõi, đừng trộn.\n\n"
            "Chiến lược MARKDOWN gồm:\n"
            "## 1. Luận điểm trung tâm (nước cờ chính)\n"
            "1 đoạn sắc (3-5 câu): tình thế + cơ hội lớn nhất + ĐẶT CƯỢC (thắng bằng gì). Trích mã TOWS từ "
            "SWOT làm trục (vd 'lấy SO1 làm mũi nhọn, kèm WT2 dựng moat') — KHÔNG in lại bảng 4 ô TOWS.\n"
            "## 2. Mạch lập luận — vì sao đánh ở đây, thắng bằng cách nào (SÂU NHẤT)\n"
            "Nối thẳng research→lựa chọn theo mạch 'vì X + vì Y + vì Z → nên W': 'Thị trường cho thấy [phát "
            "hiện] + Đối thủ để hở [khoảng trống] + Khách đau ở [cốt lõi] → nên đánh [hướng], thắng bằng "
            "[đòn bẩy]'. Mỗi mệnh đề bám 1 phát hiện research THẬT (DÙNG research làm lý do, đừng liệt kê lại).\n"
            "## 3. Định vị (BỀN — ít đổi theo thời gian)\n"
            "Là KẾT TINH của mạch lập luận (suy ra, không áp đặt):\n"
            "#### USP chính: 1 câu — '[Tính từ] [sản phẩm] cho [audience cụ thể] mà [khác biệt vs đối thủ]'. "
            "Kèm lý do work + 3 variants A/B (góc khác nhau: cảm xúc / thực dụng / bằng chứng xã hội).\n"
            "#### SAVE: Solution (giải vấn đề gì) · Access (cách khách tiếp cận) · Value (tổng giá trị) · "
            "Educate (dạy gì để khách tin). #### JTBD: khách 'thuê' sản phẩm để làm gì. (LA BÀN, KHÔNG gắn mốc.)\n"
            "## 4. Mũi nhọn (Wedge) — đánh ở đâu TRƯỚC\n"
            "Tệp/đầu cầu ưu tiên #1 + vì sao (dễ thắng nhất / đòn bẩy mạnh nhất) + tối đa 2 kênh + ≥2 thứ NÊN "
            "TẠM GÁC (kèm vì sao). Founder đã chọn phân khúc → TÔN TRỌNG làm wedge.\n"
            "## 5. Roadmap (theo NHỊP đã chọn — cuốn chiếu, làm lại mỗi kỳ)\n"
            "Chia pha theo nhịp; mỗi pha: trọng tâm 1 câu + chỉ số ĐỊNH HƯỚNG cần nhìn (đo gì, KHÔNG target số "
            "cứng/deadline khi chưa có baseline — số thật chốt khi lập chiến dịch). Tách hẳn khỏi mục 3.\n"
            "## 6. KPI cần theo dõi (3-5, tên KPI hợp ngành, đo gì + vì sao — KHÔNG chốt target)\n"
            "## 7. Rủi ro lớn nhất + Cờ đỏ (bám SWOT Threats: rủi ro chính + cách giảm; 🚩 dấu hiệu phải dừng/đổi hướng)\n"
            "## 8. Tóm tắt khuyến nghị (4-6 câu, giọng em-sếp, đóng khung 'đề xuất — sếp quyết')\n\n"
            f"🧭 NHỊP ROADMAP: {_horizon_guide(horizon)}\n"
            f"⚖️ {_posture_guide(posture)}\n"
            f"🎯 ĐỊNH VỊ: {usp_rule}\n"
            "🔴 Cụ thể > chung chung; actionable > lý thuyết; ngắn gọn > dài dòng. Bám archetype + mùa vụ "
            "ngành. Đừng đề xuất thứ không khả thi với team/ngân sách của họ. Diễn đạt tự nhiên, đừng quăng "
            "thuật ngữ trần (archetype/SAVE) mà không giải thích. Roadmap = đề xuất ('có thể/nên cân nhắc').\n"
            "🔴 Viết TOÀN BỘ bằng TIẾNG VIỆT."
        )
        syn_user = (
            f"# Ngành\n{industry}\n{ictx}\n\n"
            f"{bet_block}"
            f"{resource_block}"
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
            "Bạn là CMO senior viết TACTICAL PLAYBOOK — cách đánh CHI TIẾT, xuống tới level thực thi, "
            "bám Chiến lược (Synthesis) + SWOT đã có. Nói thẳng với founder, sắc, không vòng vo.\n\n"
            "XƯƠNG SỐNG bắt buộc: **Segment (tệp khách) → Phễu TOFU/MOFU/BOFU**. KHÔNG tổ chức theo "
            "SO/WO/WT (đó là việc của SWOT).\n\n"
            "NGUYÊN TẮC:\n"
            "1. Tôn trọng WEDGE: tệp ƯU TIÊN viết ĐẦU TIÊN + ĐẦY ĐỦ nhất (đủ 3 tầng, mỗi tầng vài mũi); "
            "tệp phụ viết GỌN (mỗi tầng 1 mũi, bỏ đoạn 'lợi thế bền vững').\n"
            "2. Mỗi tệp MỞ ĐẦU bằng **🧠 Insight cốt lõi** (2-3 đoạn SẮC, dám contrarian nếu thị trường đang "
            "làm sai) — viết bằng NGÔN NGỮ FOUNDER, không quăng thuật ngữ trần.\n"
            "3. Mỗi mũi tactic phải xuống thực thi: tên chiến thuật + góc/insight + **COPY MẪU** (câu quote "
            "dùng được ngay) + **kênh cụ thể** + **khung thử nghiệm** (cấu trúc test + ngưỡng cut theo chỉ số "
            "TƯƠNG ĐỐI CTR/ROAS/CVR + thời lượng) + **KPI cần theo dõi**.\n"
            "4. Mỗi mũi gắn 1 tag NGẮN dẫn về nước cờ TOWS nó phục vụ, trích mã từ SWOT — vd '(phục vụ SO1)'. "
            "Tag là PHỤ, bỏ vẫn đọc hiểu; TUYỆT ĐỐI KHÔNG dựng lại khối SO/WO/WT làm cấu trúc.\n"
            "5. Tệp ƯU TIÊN có 1 đoạn **📊 Vì sao đối thủ không copy được ngay** (lợi thế bền vững, bám đối thủ thật).\n"
            "6. BÁM ARCHETYPE mua hàng của ngành (xem block context) — kênh + copy + tactic phải khớp:\n"
            "   • trust_building: long-form/chuyên môn (LinkedIn, blog, podcast, YouTube/FB dài), nuôi authority "
            "trước, đừng push-sale sớm; copy góc người trong nghề + quan điểm cá nhân.\n"
            "   • impulse: paid ads + retarget + livestream (Meta/TikTok Ads, TikTok Shop, Shopee); copy ngắn, "
            "hook scroll-stop, social proof định lượng, CTA + urgency.\n"
            "   • demand_gen: video-first organic (TikTok/Reels/Shorts); khơi desire/lifestyle trước, UGC/KOC, "
            "rồi mới pitch.\n"
            "   Diễn đạt archetype theo cách founder hiểu (vd 'khách của sếp không tự nghĩ tới chuyện mua — phải "
            "khơi nhu cầu trước khi pitch'), KHÔNG nói trần 'archetype demand_gen là…'.\n"
            "7. PHỦ HẾT mọi tệp — TUYỆT ĐỐI KHÔNG cụt. Số tệp lấy đúng từ Synthesis; nếu sắp dài thì RÚT GỌN tệp "
            "ưu tiên (vẫn giữ copy mẫu + khung test + KPI) để chừa đủ chỗ cho mọi tệp — thà mỗi tệp ngắn còn hơn cụt.\n"
            "8. 🔴 KHÔNG ghi số tiền tuyệt đối (ngân sách thật chốt khi lập chiến dịch). KPI nêu ĐO GÌ, KHÔNG chốt target.\n"
            "9. 🔴 Viết TOÀN BỘ bằng TIẾNG VIỆT. MARKDOWN.\n\n"
            "FORMAT mỗi tệp:\n"
            "# [TÊN TỆP — mô tả ngắn] (cách mua: <archetype diễn đạt tự nhiên>)\n"
            "### 🧠 Insight cốt lõi\n"
            "## TOFU — Khơi/bắt nhu cầu\n### 🎯 Hướng 1 — [Tên] _(phục vụ SOx)_ …\n"
            "## MOFU — Nuôi & thuyết phục\n### 🎯 Hướng 1 — [Tên] _(phục vụ WOx)_ …\n"
            "## BOFU — Chốt\n### 🎯 Hướng 1 — [Tên] …\n"
            "### 📊 Vì sao đối thủ không copy được _(chỉ tệp ưu tiên)_\n\n"
            "Kết bằng **# BẢNG TỔNG HỢP**: cột Tệp | Tầng | Mũi chính | Phục vụ (TOWS) | Mức đầu tư (Thấp/Trung/Cao — "
            "định tính, ghi chú số tiền cụ thể chốt khi lập chiến dịch)."
        )
        tac_user = (
            f"# Ngành\n{industry}\n{ictx}\n\n"
            f"{bet_block}"
            f"{resource_block}"
            f"# Tệp ƯU TIÊN (wedge founder chọn)\n{wedge or '(chưa chọn — lấy tệp ưu tiên từ Synthesis)'}\n\n"
            f"# Chiến lược (Synthesis — vừa lập)\n{synthesis[:3500]}\n\n"
            f"# SWOT (dùng mã TOWS SO/WO/ST/WT để gắn tag mũi)\n{(research.get('swot') or '(chưa có)')[:2200]}\n\n"
            f"# Customer Insight (hiểu tệp + insight)\n{(research.get('customer_insight') or '(chưa có)')[:1800]}\n\n"
            f"# Đối thủ (cho đoạn 'không copy được')\n{(research.get('competitor') or '(chưa có)')[:1500]}"
        )
        tac_res = await router_call(task_type=TaskType.OPS_BRIEF,
                                    system=tac_system, user=tac_user, max_tokens=4000)
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
            warns: list[str] = []
            stop_reason = None
            async for stage_key, result in agen:
                # M-fix: BẮT lý do dừng (trước đây nuốt _result → không truy nguyên được).
                if stage_key in ("pipeline_abort", "quota_stop"):
                    stop_reason = str(result or stage_key)
                    job["progress"] = f"Dừng: {stage_key}"
                    logger.warning("research stopped (user=%s task=%s): %s — %s",
                                   uid, task, stage_key, stop_reason[:300])
                    break
                # bước lỗi/timeout: pipeline vẫn yield stage_key nhưng result là chuỗi '⚠️ …'
                if isinstance(result, str) and result.lstrip().startswith("⚠️"):
                    warns.append(f"{stage_key}: {result.strip()[:160]}")
                    job["progress"] = f"⚠️ {stage_key}"
                    logger.warning("research stage warn (user=%s): %s — %s",
                                   uid, stage_key, result[:300])
                else:
                    done.append(stage_key)
                    job["progress"] = f"Hoàn tất bước: {stage_key}"
            await save_session(session)

            if task == "full" and not stop_reason:
                res = await strategize_web(uid, progress)
                if res.get("error"):
                    raise RuntimeError(res["error"])
                done.append("strategy_web")

            if stop_reason:
                job["status"] = "error"
                job["error"] = stop_reason[:300]
                job["summary"] = f"Dừng sớm sau {len(done)} bước ({', '.join(done) or '—'})."
            else:
                parts = [f"Hoàn tất {len(done)} bước: {', '.join(done)}" if done else "Hoàn tất."]
                if warns:
                    parts.append(f"⚠️ {len(warns)} bước cảnh báo — {' | '.join(warns)}")
                job["status"] = "done"
                job["summary"] = " ".join(parts)
                if warns:
                    job["error"] = "; ".join(warns)[:300]   # để hiện cảnh báo dù status done
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
