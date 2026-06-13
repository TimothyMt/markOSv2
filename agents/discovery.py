"""
Discovery engine — phần McKinsey của pipeline v0.1.

Luồng:
  1. run_discovery_turn()       — hội thoại adaptive thu 6-7 trường (1 câu/lượt)
  2. run_discovery_research()   — 3 research agent SONG SONG (run_tier), grounded
  3. generate_diagnostic_brief()— dựng brief có cấu trúc (facts/hypotheses/gaps)
  4. persist_discovery()        — ghi v2: users/profile → engagement → brief

Tái dùng: tools.llm_router (grounded + failover), agents.orchestrator (run_tier),
frameworks.industry_context (Phase 1), storage.v2 (Phase 1 spine).

KHÔNG wire vào handlers ở đây — đó là bước 2b (tích hợp UI cẩn thận).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional, Awaitable, Callable

from storage.models import Session

logger = logging.getLogger(__name__)

# 7 trường bắt buộc để hoàn tất discovery (industry/stage tự suy, competitors tùy)
REQUIRED_FIELDS = [
    "product_service", "target_customer", "monthly_revenue",
    "primary_goal", "main_challenge", "monthly_marketing_budget", "current_channels",
]
# Trường được phép ghi vào profile từ discovery_input
_PROFILE_FIELDS = REQUIRED_FIELDS + ["competitors", "stage", "industry"]


# ═════════════════════════════════════════════════════════════════
# 1. CONVERSATIONAL INTAKE
# ═════════════════════════════════════════════════════════════════

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_completion(text: str) -> Optional[dict]:
    """Trích discovery_input nếu LLM xuất block completion JSON.

    Returns dict discovery_input nếu status='complete', else None (vẫn đang hỏi).
    Pure function — unit-testable.
    """
    if not text:
        return None
    # Thử block ```json ... ``` trước, fallback bare JSON object
    candidates = _JSON_BLOCK_RE.findall(text)
    if not candidates:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            candidates = [stripped]
    for raw in candidates:
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict) and obj.get("status") == "complete":
            di = obj.get("discovery_input")
            if isinstance(di, dict):
                return di
    return None


async def run_discovery_turn(
    session: Session,
    user_msg: str,
) -> tuple[str, Optional[dict]]:
    """Một lượt phỏng vấn. Returns (mode, payload):

      ("question", None)         — payload là câu hỏi tiếp theo (trả về qua text)
      ("complete", discovery_input) — đã đủ, payload là dict trường thu được

    Lưu ý: caller chịu trách nhiệm append vào session.intake_history + gửi câu hỏi.
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
    from agents.discovery_prompts import MCKINSEY_INTERVIEW_SYSTEM

    if user_msg and user_msg.strip():
        session.add_to_history("user", user_msg)

    # Dựng hội thoại từ history
    convo = "\n".join(
        f"{'Sếp' if h['role'] == 'user' else 'Minh'}: {h['content']}"
        for h in session.intake_history
    ) or "(chưa có — đây là câu mở đầu)"

    user_block = (
        f"# HỘI THOẠI ĐẾN GIỜ\n{convo}\n\n"
        "Dựa trên hội thoại, hoặc hỏi câu TIẾP THEO (1 câu), "
        "hoặc nếu đã đủ 7 trường bắt buộc thì xuất block JSON completion."
    )

    try:
        result = await router_call(
            task_type=TaskType.GENERIC_CREATIVE,  # Sonnet primary — chất lượng VN hội thoại
            system=MCKINSEY_INTERVIEW_SYSTEM,
            user=user_block,
            max_tokens=1200,
        )
    except AllProvidersFailedError as e:
        logger.error("discovery_turn: all providers failed: %s", e)
        return ("question", None)

    text = result.get("output", "")
    _track(session, "discovery_intake", result)

    discovery_input = parse_completion(text)
    if discovery_input is not None:
        return ("complete", discovery_input)

    session.add_to_history("assistant", text)
    return ("question", text)


def apply_discovery_to_profile(session: Session, discovery_input: dict) -> None:
    """Ghi discovery_input vào session.profile (chỉ field whitelist, bỏ rỗng)."""
    for key in _PROFILE_FIELDS:
        val = discovery_input.get(key)
        if val and isinstance(val, str) and val.strip():
            setattr(session.profile, key, val.strip())


# ═════════════════════════════════════════════════════════════════
# 2. RESEARCH (parallel via orchestrator)
# ═════════════════════════════════════════════════════════════════

def _fill_seeds(seeds: list[str], session: Session) -> str:
    """Fill placeholder {sản phẩm}/{khu vực}/{thành phố} từ profile."""
    p = session.profile
    repl = {
        "{sản phẩm}": p.product_service or "",
        "{khu vực}": p.location or "",
        "{thành phố}": p.location or "",
        "{category}": p.product_service or "",
        "{dịch vụ}": p.product_service or "",
        "{chức năng}": p.product_service or "",
        "{chủ đề}": p.product_service or "",
        "{lĩnh vực}": p.industry or "",
        "{ngành}": p.industry or "",
        "{phân khúc}": p.product_service or "",
        "{đối thủ}": p.competitors or "",
    }
    out = []
    for s in seeds:
        for k, v in repl.items():
            s = s.replace(k, v)
        out.append(re.sub(r"\s+", " ", s).strip())
    return " · ".join([s for s in out if s])


def _track(session: Session, label: str, result: dict) -> None:
    """Track tokens + provider qua token_tracker (cho caveat detection sau)."""
    try:
        from tools.token_tracker import track_skill
        track_skill(
            session,
            skill_name=label,
            provider=result.get("provider", "unknown"),
            input_tok=result.get("tokens_in", 0),
            output_tok=result.get("tokens_out", 0),
            latency_sec=result.get("latency_sec", 0.0),
        )
    except Exception as e:
        logger.warning("track(%s) failed: %s", label, e)


async def _run_one_research(session: Session, system: str, task_type, seed_key: str, label: str) -> str:
    """Chạy 1 research call → router (grounded nếu task type cho phép)."""
    from tools.llm_router import call as router_call, AllProvidersFailedError
    from frameworks.industry_context import get_full_industry_brief, get_search_seeds
    from agents.discovery_prompts import build_research_user

    industry = session.profile.industry or ""
    industry_brief = get_full_industry_brief(industry) if industry else ""
    seeds = get_search_seeds(industry).get(seed_key, []) if industry else []
    search_hint = _fill_seeds(seeds, session)

    user_msg = build_research_user(
        session.profile.to_context_string(), industry_brief, search_hint,
    )
    try:
        result = await router_call(task_type=task_type, system=system, user=user_msg, max_tokens=10000)
    except AllProvidersFailedError as e:
        logger.error("research %s failed: %s", label, e)
        return ""
    _track(session, label, result)
    return result.get("output", "")


async def run_discovery_research(
    session: Session,
    progress_cb: Optional[Callable[[str], Awaitable[None]]] = None,
) -> dict:
    """Chạy 3 research agent SONG SONG qua orchestrator run_tier.

    Returns {market, competitor, customer, grounded, confidence_note}.
    grounded=True nếu market HOẶC competitor thực sự chạy qua Gemini grounded.
    """
    from agents.orchestrator import run_tier, TierConfig
    from tools.llm_router import TaskType
    from agents.discovery_prompts import (
        DISCOVERY_MARKET_SYSTEM, DISCOVERY_COMPETITOR_SYSTEM, DISCOVERY_CUSTOMER_SYSTEM,
    )

    async def research_market(s: Session) -> str:
        return await _run_one_research(s, DISCOVERY_MARKET_SYSTEM, TaskType.MARKET_RESEARCH_DATA, "tam", "dc_market")

    async def research_competitor(s: Session) -> str:
        return await _run_one_research(s, DISCOVERY_COMPETITOR_SYSTEM, TaskType.COMPETITOR_RESEARCH, "competitor", "dc_competitor")

    async def research_customer(s: Session) -> str:
        return await _run_one_research(s, DISCOVERY_CUSTOMER_SYSTEM, TaskType.CUSTOMER_INSIGHT, "trend", "dc_customer")

    tier = TierConfig(
        name="Discovery Research",
        agents=[research_market, research_competitor, research_customer],
        must_have={"research_customer"},  # customer là nền — phải có
        nice_to_have={"research_market", "research_competitor"},
        timeout_per_agent=180,
        max_concurrent=3,
    )

    results = await run_tier(tier, session, progress_cb)

    def _out(name: str) -> str:
        r = results.get(name)
        return r.output if (r and r.success) else ""

    # Caveat detection: grounded thật chạy khi provider là gemini_pro_grounded
    from tools.token_tracker import get_latest_skill_entry
    grounded = False
    for label in ("dc_market", "dc_competitor"):
        entry = get_latest_skill_entry(session, label)
        if entry and entry.get("provider") == "gemini_pro_grounded":
            grounded = True
            break

    confidence_note = None if grounded else (
        "⚠️ Số liệu thị trường/đối thủ là ƯỚC LƯỢNG từ kiến thức mô hình "
        "(không có web realtime). Cần kiểm chứng trước khi quyết định lớn."
    )

    return {
        "market":          _out("research_market"),
        "competitor":      _out("research_competitor"),
        "customer":        _out("research_customer"),
        "grounded":        grounded,
        "confidence_note": confidence_note,
    }


def assemble_research_from_deepdives(session: Session) -> dict:
    """Gom kết quả DEEP-DIVE đã chạy (session.results) thành research dict cho brief.

    Dùng khi flow chạy full deep-dive (tái dùng strategic skills cũ) thay vì
    research concise. Map các domain → market/competitor/customer + extra.
    """
    g = session.get_latest_result
    market = g("market_research") or ""
    competitor = g("competitor") or ""
    customer = g("customer_insight") or ""

    extra_parts = []
    for key, label in [
        ("psychology_pricing", "Psychology & Pricing"),
        ("usp_definition", "USP"),
        ("retention_strategy", "Retention Strategy"),
        ("winback_campaign", "Winback"),
    ]:
        val = g(key)
        if val:
            extra_parts.append(f"## {label}\n{val}")

    # Grounded detection — market deep-dive chạy qua Gemini grounded?
    from tools.token_tracker import get_latest_skill_entry
    grounded = False
    for label in ("market_research", "dc_market"):
        entry = get_latest_skill_entry(session, label)
        if entry and entry.get("provider") == "gemini_pro_grounded":
            grounded = True
            break

    confidence_note = None if grounded else (
        "⚠️ Số liệu thị trường là ƯỚC LƯỢNG (không có web realtime). "
        "Cần kiểm chứng trước khi quyết định lớn."
    )

    return {
        "market":          market,
        "competitor":      competitor,
        "customer":        customer,
        "extra":           "\n\n".join(extra_parts),
        "grounded":        grounded,
        "confidence_note": confidence_note,
    }


# ═════════════════════════════════════════════════════════════════
# 3. DIAGNOSTIC BRIEF
# ═════════════════════════════════════════════════════════════════

def parse_brief_json(text: str) -> Optional[dict]:
    """Trích brief JSON từ output. Pure — unit-testable.

    Returns dict {facts, hypotheses, gaps, sources, summary} hoặc None nếu fail.
    """
    if not text:
        return None
    candidates = _JSON_BLOCK_RE.findall(text)
    if not candidates:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            candidates = [stripped]
    for raw in candidates:
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict) and ("facts" in obj or "hypotheses" in obj):
            return {
                "facts":      obj.get("facts", []) or [],
                "hypotheses": obj.get("hypotheses", []) or [],
                "gaps":       obj.get("gaps", []) or [],
                "sources":    obj.get("sources", []) or [],
                "summary":    obj.get("summary", "") or "",
            }
    return None


async def generate_diagnostic_brief(session: Session, research: dict) -> dict:
    """Gọi brief generator → parse structured brief.

    Returns {facts, hypotheses, gaps, sources, summary, grounded,
             confidence_note, content, model_used, tokens_used}.
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
    from frameworks.industry_context import get_full_industry_brief
    from agents.discovery_prompts import DIAGNOSTIC_BRIEF_SYSTEM, build_brief_user

    industry = session.profile.industry or ""
    industry_brief = get_full_industry_brief(industry) if industry else ""
    grounded = bool(research.get("grounded"))

    user_msg = build_brief_user(
        profile_ctx=session.profile.to_context_string(),
        industry_brief=industry_brief,
        market_note=research.get("market", ""),
        competitor_note=research.get("competitor", ""),
        customer_note=research.get("customer", ""),
        grounded=grounded,
        extra_notes=research.get("extra", ""),
    )

    tokens_used = 0
    model_used = "unknown"
    raw = ""
    try:
        result = await router_call(
            task_type=TaskType.GENERIC_CREATIVE,
            system=DIAGNOSTIC_BRIEF_SYSTEM,
            user=user_msg,
            max_tokens=10000,
        )
        raw = result.get("output", "")
        model_used = result.get("provider", "unknown")
        tokens_used = (result.get("tokens_in", 0) or 0) + (result.get("tokens_out", 0) or 0)
        _track(session, "diagnostic_brief", result)
    except AllProvidersFailedError as e:
        logger.error("brief generation failed: %s", e)

    parsed = parse_brief_json(raw) or {
        "facts": [], "hypotheses": [], "gaps": [], "sources": [],
        "summary": raw[:1000] if raw else "Chưa dựng được brief — vui lòng thử lại.",
    }
    parsed.update({
        "grounded":        grounded,
        "confidence_note": research.get("confidence_note"),
        "content":         raw,
        "model_used":      model_used,
        "tokens_used":     tokens_used,
    })
    return parsed


# ═════════════════════════════════════════════════════════════════
# 4. PERSISTENCE (v2-native — không dual-write)
# ═════════════════════════════════════════════════════════════════

async def persist_discovery(session: Session, discovery_input: dict, brief: dict) -> Optional[dict]:
    """Ghi v2: đảm bảo users/profile tồn tại → engagement → brief.

    Returns {engagement_id, brief_id} hoặc None nếu v2 chưa khả dụng.
    """
    try:
        from storage import v2
    except Exception as e:
        logger.warning("v2 storage unavailable: %s", e)
        return None

    user_id = session.user_id
    prefs = session.preferences or {}

    # 1. Đảm bảo users + profile tồn tại (FK của engagement)
    await v2.upsert_user(
        user_id=user_id,
        name=prefs.get("user_name"),
        en_level=prefs.get("en_level"),
        industry_cached=session.profile.industry,
    )
    profile_fields = {
        k: getattr(session.profile, k)
        for k in _PROFILE_FIELDS
        if getattr(session.profile, k, None)
    }
    if profile_fields:
        await v2.upsert_profile(user_id, **profile_fields)

    # 2. Tạo engagement
    title = (session.profile.product_service or "Engagement")[:60]
    eng = await v2.create_engagement(user_id, discovery_input=discovery_input, title=title)
    if not eng:
        logger.warning("create_engagement returned None (v2 write failed)")
        return None
    engagement_id = eng["id"]

    # 3. Ghi brief
    brief_row = await v2.insert_brief(
        engagement_id=engagement_id,
        user_id=user_id,
        facts=brief.get("facts"),
        hypotheses=brief.get("hypotheses"),
        gaps=brief.get("gaps"),
        sources=brief.get("sources"),
        grounded=brief.get("grounded", False),
        confidence_note=brief.get("confidence_note"),
        content=brief.get("content"),
        model_used=brief.get("model_used"),
        tokens_used=brief.get("tokens_used"),
    )
    brief_id = brief_row["id"] if brief_row else None

    # 4. Link + chuyển status
    await v2.update_engagement(engagement_id, brief_id=brief_id, status="brief")

    logger.info("Discovery persisted: engagement=%s brief=%s", engagement_id, brief_id)
    return {"engagement_id": engagement_id, "brief_id": brief_id}


def render_brief_card(brief: dict) -> str:
    """Format brief thành Telegram card (Markdown). Pure."""
    lines = ["🔍 *Diagnostic Brief* — Chẩn đoán ban đầu", ""]
    if brief.get("summary"):
        lines += [brief["summary"], ""]

    facts = brief.get("facts") or []
    if facts:
        lines.append("📊 *Facts:*")
        for f in facts[:6]:
            conf = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(f.get("confidence", ""), "")
            src = f" _({f['source']})_" if f.get("source") else ""
            lines.append(f"• {f.get('claim', '')} {conf}{src}")
        lines.append("")

    hyps = brief.get("hypotheses") or []
    if hyps:
        lines.append("💡 *Giả thuyết (xếp hạng):*")
        for h in sorted(hyps, key=lambda x: x.get("rank", 99))[:4]:
            lines.append(f"{h.get('rank', '•')}. {h.get('statement', '')}")
        lines.append("")

    gaps = brief.get("gaps") or []
    if gaps:
        lines.append("❓ *Cần sếp bổ sung:*")
        for g in gaps[:3]:
            lines.append(f"• {g.get('question', '')}")
        lines.append("")

    if brief.get("confidence_note"):
        lines.append(f"_{brief['confidence_note']}_")

    return "\n".join(lines).strip()
