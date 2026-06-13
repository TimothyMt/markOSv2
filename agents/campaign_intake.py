"""
Campaign Intake engine — bước đầu Ops layer v0.1.

Flow:
  Strategy output (đã duyệt)
    → build_campaign_draft_from_strategy()  [no LLM — auto pre-fill]
    → generate_brand_voice()                [1 Haiku call]
    → render_campaign_draft_card()          [show user]
    → run_intake_turn() × N                 [user confirm/adjust]
    → campaign dict locked
    → render_campaign_confirmed_card()
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from storage.models import Session

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


# ─────────────────────────────────────────────────────────────────
# Parse
# ─────────────────────────────────────────────────────────────────

def parse_intake_completion(text: str) -> Optional[dict]:
    """Extract campaign JSON from intake agent response. Pure — unit-testable."""
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
        if isinstance(obj, dict) and obj.get("status") == "complete" and "campaign" in obj:
            c = obj["campaign"]
            # Normalize mandatory fields
            return {
                "name":              c.get("name", "Campaign Sprint 1"),
                "objective":         c.get("objective", "mix"),
                "objective_detail":  c.get("objective_detail", ""),
                "channels":          c.get("channels") or [],
                "audience":          c.get("audience", ""),
                "budget_total":      c.get("budget_total", ""),
                "budget_breakdown":  c.get("budget_breakdown") or [],
                "brand_voice":       c.get("brand_voice") or {},
                "duration_days":     int(c.get("duration_days") or 30),
                "location":          c.get("location", ""),
                "content_pillars":   c.get("content_pillars") or [],
                "kpi_targets":       c.get("kpi_targets") or [],
                "extra_notes":       c.get("extra_notes", ""),
            }
    return None


# ─────────────────────────────────────────────────────────────────
# Draft builder — no LLM
# ─────────────────────────────────────────────────────────────────

def build_campaign_draft_from_strategy(session: Session, strategy: dict) -> dict:
    """Auto-build campaign draft từ strategy output. Không cần LLM.

    Pre-fills: channels, audience, budget, pillars, KPIs, location.
    brand_voice=None → filled by generate_brand_voice() sau đó.
    """
    p = session.profile
    wedge    = strategy.get("wedge") or {}
    budget   = strategy.get("budget_allocation") or {}
    pillars  = strategy.get("content_pillars") or []
    roadmap  = strategy.get("roadmap_90d") or []
    pos      = strategy.get("positioning") or {}
    kpis     = strategy.get("kpi_dashboard") or []

    # Infer objective từ phase 1 goals
    phase1      = roadmap[0] if roadmap else {}
    phase1_goals = phase1.get("smart_goals") or []
    goal_text   = " ".join(phase1_goals).lower()

    if any(w in goal_text for w in ["awareness", "nhận diện", "reach"]):
        objective = "awareness"
    elif any(w in goal_text for w in ["chuyển đổi", "conversion", "mua", "booking", "enroll"]):
        objective = "conversion"
    elif any(w in goal_text for w in ["branding", "định vị", "brand"]):
        objective = "branding"
    else:
        objective = "mix"

    return {
        "name":             "",
        "objective":        objective,
        "objective_detail": phase1_goals[0] if phase1_goals else "",
        "channels":         list(wedge.get("channels") or []),
        "audience":         wedge.get("audience") or p.target_customer or "",
        "budget_total":     budget.get("total") or p.monthly_marketing_budget or "",
        "budget_breakdown": list(budget.get("breakdown") or []),
        "brand_voice":      None,   # filled by generate_brand_voice
        "duration_days":    30,
        "location":         p.location or "",
        "content_pillars":  [
            {"name": pl.get("name", ""), "angle": pl.get("angle", "")}
            for pl in pillars
        ],
        "kpi_targets":      [
            {"metric": k.get("metric", ""), "target": k.get("target", "")}
            for k in kpis[:3]
        ],
        "_positioning":     pos.get("statement", ""),   # internal — for context only
        "extra_notes":      "",
    }


# ─────────────────────────────────────────────────────────────────
# Brand voice generator — 1 LLM call
# ─────────────────────────────────────────────────────────────────

async def generate_brand_voice(session: Session, strategy: dict) -> dict:
    """Draft brand voice từ positioning + content pillars. 1 Haiku call."""
    from tools.llm_router import call as router_call, TaskType
    from agents.campaign_intake_prompts import BRAND_VOICE_SYSTEM

    pos     = strategy.get("positioning") or {}
    pillars = strategy.get("content_pillars") or []

    pillar_text = "\n".join(
        f"- {p.get('name', '')}: {p.get('angle', '')} (ladder: {p.get('ladder', '')})"
        for p in pillars
    )
    user_msg = "\n".join([
        "# Positioning Statement",
        pos.get("statement", "(chưa có)"),
        "",
        "# SAVE — Solution / Value / Education",
        f"Solution: {pos.get('solution', '')}",
        f"Value: {pos.get('value', '')}",
        f"Education: {pos.get('education', '')}",
        "",
        "# Content Pillars",
        pillar_text or "(chưa có)",
        "",
        "Draft brand voice JSON theo format ở system prompt.",
    ])

    try:
        result = await router_call(
            task_type=TaskType.GENERIC_CREATIVE,
            system=BRAND_VOICE_SYSTEM,
            user=user_msg,
            max_tokens=800,
        )
        raw = result.get("output", "")
        candidates = _JSON_BLOCK_RE.findall(raw)
        if not candidates and raw.strip().startswith("{"):
            candidates = [raw.strip()]
        for c in candidates:
            try:
                obj = json.loads(c)
                if isinstance(obj, dict) and "tone" in obj:
                    return obj
            except (json.JSONDecodeError, ValueError):
                continue
    except Exception as e:
        logger.warning("generate_brand_voice failed: %s", e)

    # Generic fallback
    return {
        "tone":       ["chuyên nghiệp", "thân thiện", "thực tế"],
        "style":      "warm",
        "always_do":  ["Dùng ngôn ngữ đơn giản, dễ hiểu", "Kể câu chuyện thật từ thực tế"],
        "never_do":   ["Dùng jargon kỹ thuật không cần thiết", "Phóng đại hoặc hứa hẹn vô căn cứ"],
        "sample":     "Sản phẩm của em giúp sếp giải quyết [vấn đề] nhanh hơn — không cần phức tạp.",
    }


# ─────────────────────────────────────────────────────────────────
# Intake conversation turn
# ─────────────────────────────────────────────────────────────────

async def run_intake_turn(
    session: Session,
    user_msg: str,
    draft: dict,
    strategy: dict,
) -> tuple[str, Optional[dict]]:
    """Xử lý 1 lượt hội thoại intake.

    Returns:
        ("adjusting", None)       — model đang điều chỉnh, chờ user confirm
        ("complete", campaign)    — user đã confirm, campaign locked
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
    from agents.campaign_intake_prompts import CAMPAIGN_INTAKE_SYSTEM, build_intake_user
    from agents.campaign_scope_library import format_scope_for_prompt

    p        = session.profile
    industry = p.industry or ""

    draft_json     = json.dumps(draft, ensure_ascii=False, indent=2)
    industry_scope = format_scope_for_prompt(industry) if industry else ""

    user_prompt = build_intake_user(
        strategy_ctx   = _strategy_to_ctx(strategy),
        profile_ctx    = p.to_context_string(),
        draft_json     = draft_json,
        brand_voice_draft = draft.get("brand_voice") or {},
        industry_scope = industry_scope,
    )

    full_user = f"{user_prompt}\n\n# USER:\n{user_msg}"

    try:
        result = await router_call(
            task_type  = TaskType.GENERIC_CREATIVE,
            system     = CAMPAIGN_INTAKE_SYSTEM,
            user       = full_user,
            max_tokens = 3000,
        )
        raw = result.get("output", "")
    except AllProvidersFailedError as e:
        logger.error("intake turn failed: %s", e)
        return "adjusting", None

    campaign = parse_intake_completion(raw)
    if campaign:
        return "complete", campaign
    return "adjusting", None


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _strategy_to_ctx(strategy: dict) -> str:
    """Format strategy dict → compact text block cho intake agent."""
    pos     = strategy.get("positioning") or {}
    wedge   = strategy.get("wedge") or {}
    budget  = strategy.get("budget_allocation") or {}
    pillars = strategy.get("content_pillars") or []
    roadmap = strategy.get("roadmap_90d") or []
    kpis    = strategy.get("kpi_dashboard") or []

    lines = []
    if pos.get("statement"):
        lines.append(f"Positioning: {pos['statement']}")
    if wedge.get("audience"):
        lines.append(f"Tệp đề xuất: {wedge['audience']}")
    if wedge.get("channels"):
        lines.append(f"Kênh đề xuất: {', '.join(wedge['channels'])}")
    if wedge.get("not_doing"):
        lines.append(f"Tạm gác: {'; '.join(wedge['not_doing'][:2])}")
    if budget.get("total"):
        lines.append(f"Budget: {budget['total']}/tháng")
    if roadmap:
        ph1   = roadmap[0]
        goals = "; ".join((ph1.get("smart_goals") or [])[:2])
        lines.append(f"Phase 1 ({ph1.get('window', '30d')}): {goals}")
    if pillars:
        lines.append(f"Content pillars: {', '.join(p.get('name', '') for p in pillars)}")
    if kpis:
        kpi_str = ", ".join(f"{k.get('metric')}→{k.get('target')}" for k in kpis[:3])
        lines.append(f"KPIs: {kpi_str}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
# Card renderers
# ─────────────────────────────────────────────────────────────────

def render_campaign_draft_card(draft: dict) -> str:
    """Format campaign draft → Telegram card để user review. Pure."""
    bv = draft.get("brand_voice") or {}
    lines = ["📋 *Campaign Draft — sếp xem qua nhé*", ""]

    obj = draft.get("objective", "")
    obj_detail = draft.get("objective_detail", "")
    lines.append(f"🎯 *Objective:* {obj}" + (f" — {obj_detail}" if obj_detail else ""))

    channels = draft.get("channels") or []
    lines.append(f"📡 *Channels:* {', '.join(channels) if channels else '(chưa chọn)'}")
    lines.append(f"👥 *Tệp:* {draft.get('audience', '')}")
    lines.append(f"💰 *Budget:* {draft.get('budget_total', '')} / {draft.get('duration_days', 30)} ngày")
    lines.append(f"📍 *Khu vực:* {draft.get('location', '')}")
    lines.append("")

    if bv:
        tone = ", ".join(bv.get("tone") or [])
        lines += [
            "🎨 *Brand Voice:*",
            f"• Tone: {tone} ({bv.get('style', '')})",
            f"• Luôn: {' | '.join(bv.get('always_do') or [])}",
            f"• Không: {' | '.join(bv.get('never_do') or [])}",
            f"• Mẫu: _{bv.get('sample', '')}_",
            "",
        ]

    pillars = draft.get("content_pillars") or []
    if pillars:
        lines.append("📌 *Content Pillars:*")
        for pl in pillars:
            lines.append(f"• *{pl.get('name', '')}* — {pl.get('angle', '')}")
        lines.append("")

    kpis = draft.get("kpi_targets") or []
    if kpis:
        lines.append("📊 *KPI Targets:*")
        for k in kpis:
            lines.append(f"• {k.get('metric', '')} → {k.get('target', '')}")
        lines.append("")

    if draft.get("extra_notes"):
        lines += [f"📝 *Lưu ý:* {draft['extra_notes']}", ""]

    lines.append("_Sếp muốn điều chỉnh gì không, hay em chốt bản này?_")
    return "\n".join(lines).strip()


def render_campaign_confirmed_card(campaign: dict) -> str:
    """Card sau khi campaign đã confirm — brief trước khi gen funnel map. Pure."""
    lines = [
        f"✅ *Campaign '{campaign.get('name', 'Sprint 1')}' đã chốt*",
        "",
        f"🎯 {campaign.get('objective_detail') or campaign.get('objective', '')}",
        f"📡 Channels: {', '.join(campaign.get('channels') or [])}",
        f"💰 {campaign.get('budget_total', '')} / {campaign.get('duration_days', 30)} ngày",
        "",
        "_Em đang map ToFu/MoFu/BoFu cho từng kênh..._",
    ]
    return "\n".join(lines).strip()
