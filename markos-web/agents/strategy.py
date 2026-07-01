"""
Strategy engine — phần CMO của pipeline v0.1.

Nhận Diagnostic Brief (từ Discovery) → Marketing Plan có cấu trúc → persist v2.
Cũng cấp Hybrid shortcut: get_existing_strategy() để nhảy thẳng vào Execution.

Tái dùng: llm_router, frameworks (SAVE/SMART/industry_context), storage.v2 spine.
KHÔNG wire handlers ở đây.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from storage.models import Session

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_strategy_json(text: str) -> Optional[dict]:
    """Trích Marketing Plan JSON từ output. Pure — unit-testable."""
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
        if isinstance(obj, dict) and ("positioning" in obj or "wedge" in obj):
            return {
                "positioning":       obj.get("positioning", {}) or {},
                "wedge":             obj.get("wedge", {}) or {},
                "roadmap_90d":       obj.get("roadmap_90d", []) or [],
                "budget_allocation": obj.get("budget_allocation", {}) or {},
                "content_pillars":   obj.get("content_pillars", []) or [],
                "kpi_dashboard":     obj.get("kpi_dashboard", []) or [],
                "kill_criteria":     obj.get("kill_criteria", []) or [],
                "summary":           obj.get("summary", "") or "",
            }
    return None


async def generate_strategy(session: Session, brief: dict) -> dict:
    """Gọi CMO generator → parse Marketing Plan.

    Returns dict các field strategy + content/model_used/tokens_used.
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
    from frameworks.industry_context import get_full_industry_brief, format_archetype_block
    from frameworks.save_framework import generate_save_analysis
    from frameworks.smart_framework import format_smart_prompt
    from agents.strategy_prompts import CMO_STRATEGY_SYSTEM, build_strategy_user, brief_to_block

    p = session.profile
    industry = p.industry or ""
    stage = p.stage or "growth"

    industry_brief = get_full_industry_brief(industry) if industry else ""
    save_text = generate_save_analysis(
        industry=industry,
        business_description=p.product_service or "",
        target_customer=p.target_customer or "",
        product_service=p.product_service or "",
    )
    goals = [p.primary_goal] if p.primary_goal else []
    smart_text = format_smart_prompt(industry, stage, goals)

    # Brief text dùng để match override signals — gộp các field free-text
    archetype_brief_text = " ".join(filter(None, [
        p.product_service or "",
        p.target_customer or "",
    ]))
    archetype_block = format_archetype_block(industry, archetype_brief_text) if industry else ""

    user_msg = build_strategy_user(
        profile_ctx=p.to_context_string(),
        brief_block=brief_to_block(brief),
        industry_brief=industry_brief,
        save_text=save_text,
        smart_text=smart_text,
        archetype_block=archetype_block,
    )

    raw = ""
    model_used = "unknown"
    tokens_used = 0
    try:
        result = await router_call(
            task_type=TaskType.GENERIC_CREATIVE,  # Sonnet primary — VN strategic reasoning
            system=CMO_STRATEGY_SYSTEM,
            user=user_msg,
            max_tokens=10000,
        )
        raw = result.get("output", "")
        model_used = result.get("provider", "unknown")
        tokens_used = (result.get("tokens_in", 0) or 0) + (result.get("tokens_out", 0) or 0)
        try:
            from tools.token_tracker import track_skill
            track_skill(
                session, skill_name="cmo_strategy", provider=model_used,
                input_tok=result.get("tokens_in", 0), output_tok=result.get("tokens_out", 0),
                latency_sec=result.get("latency_sec", 0.0),
            )
        except Exception:
            pass
    except AllProvidersFailedError as e:
        logger.error("strategy generation failed: %s", e)

    parsed = parse_strategy_json(raw) or {
        "positioning": {}, "wedge": {}, "roadmap_90d": [], "budget_allocation": {},
        "content_pillars": [], "kpi_dashboard": [], "kill_criteria": [],
        "summary": raw[:1000] if raw else "Chưa dựng được kế hoạch — vui lòng thử lại.",
    }
    parsed.update({"content": raw, "model_used": model_used, "tokens_used": tokens_used})
    return parsed


async def persist_strategy(
    session: Session,
    engagement_id: str,
    brief_id: Optional[str],
    strategy: dict,
) -> Optional[dict]:
    """Ghi strategy vào v2 + link engagement.strategy_id + status='strategy'.

    Returns {strategy_id} hoặc None nếu v2 chưa khả dụng.
    """
    try:
        from storage import v2
    except Exception as e:
        logger.warning("v2 storage unavailable: %s", e)
        return None

    row = await v2.insert_strategy(
        engagement_id=engagement_id,
        user_id=session.user_id,
        brief_id=brief_id,
        positioning=strategy.get("positioning"),
        wedge=strategy.get("wedge"),
        roadmap_90d=strategy.get("roadmap_90d"),
        budget_allocation=strategy.get("budget_allocation"),
        content_pillars=strategy.get("content_pillars"),
        kpi_dashboard=strategy.get("kpi_dashboard"),
        kill_criteria=strategy.get("kill_criteria"),
        content=strategy.get("content"),
        model_used=strategy.get("model_used"),
        tokens_used=strategy.get("tokens_used"),
    )
    if not row:
        logger.warning("insert_strategy returned None (v2 write failed)")
        return None
    strategy_id = row["id"]

    await v2.update_engagement(engagement_id, strategy_id=strategy_id, status="strategy")
    logger.info("Strategy persisted: engagement=%s strategy=%s", engagement_id, strategy_id)
    return {"strategy_id": strategy_id}


async def get_existing_strategy(user_id: int) -> Optional[dict]:
    """Hybrid shortcut: lấy strategy gần nhất của user (nếu có).

    Returns row strategy hoặc None. Cho phép nhảy thẳng vào EXECUTION_MENU.
    """
    try:
        from storage import v2
    except Exception:
        return None
    eng = await v2.get_latest_with_strategy(user_id)
    if not eng or not eng.get("strategy_id"):
        return None
    return await v2.get_strategy(eng["strategy_id"])


def render_strategy_card(strategy: dict) -> str:
    """Format khuyến nghị thành Telegram card (Markdown). Pure.

    Đóng khung TƯ VẤN: lời khuyên dựa trên nghiên cứu, sếp giữ quyền quyết.
    """
    lines = ["💡 *Khuyến nghị của Max* — dựa trên nghiên cứu, sếp cân nhắc & quyết", ""]

    pos = strategy.get("positioning") or {}
    if pos.get("statement"):
        lines += [f"🎯 *Định vị đề xuất:* {pos['statement']}", ""]

    wedge = strategy.get("wedge") or {}
    if wedge:
        chans = ", ".join(wedge.get("channels", []) or [])
        lines.append("⚔️ *Mũi nhọn nên đánh trước:*")
        if wedge.get("audience"):
            lines.append(f"• Tệp khách: {wedge['audience']}")
        if chans:
            lines.append(f"• Kênh: {chans}")
        nots = wedge.get("not_doing", []) or []
        if nots:
            lines.append(f"• Nên tạm gác: {'; '.join(nots)}")
        if wedge.get("rationale"):
            lines.append(f"• _Lý do: {wedge['rationale']}_")
        lines.append("")

    roadmap = strategy.get("roadmap_90d") or []
    if roadmap:
        lines.append("🗺 *Lộ trình gợi ý 90 ngày:*")
        for ph in roadmap[:3]:
            goals = "; ".join(ph.get("smart_goals", []) or [])
            lines.append(f"• *{ph.get('phase', '')}* ({ph.get('window', '')}): {goals}")
        lines.append("")

    kpis = strategy.get("kpi_dashboard") or []
    if kpis:
        lines.append("📊 *KPI nên theo dõi:*")
        for k in kpis[:5]:
            lines.append(f"• {k.get('metric', '')} → {k.get('target', '')}")
        lines.append("")

    kills = strategy.get("kill_criteria") or []
    if kills:
        lines.append("🚦 *Dấu hiệu nên đổi hướng:*")
        for kc in kills[:3]:
            lines.append(f"• {kc.get('condition', '')} → {kc.get('action', '')}")
        lines.append("")

    if strategy.get("summary"):
        lines += ["—", strategy["summary"]]

    lines += ["", "_Đây là góc nhìn tư vấn của em dựa trên dữ liệu nghiên cứu — quyết định cuối vẫn là của sếp ạ._"]
    return "\n".join(lines).strip()


async def run_advisor(session: Session, engagement_id: Optional[str] = None) -> dict:
    """Bước kết luận (thay synthesis cũ): deep-dive → brief xếp hạng → CMO advisory.

    Giả định các deep-dive đã chạy xong và nằm trong session.results.
    Returns {brief, advisory, card} — handler render card + ghép vào HTML report.
    Nếu có engagement_id → persist brief + strategy vào v2.
    """
    from agents.discovery import (
        assemble_research_from_deepdives, generate_diagnostic_brief,
        render_brief_card,
    )

    # 1. Gom deep-dive → research → brief xếp hạng giả thuyết
    research = assemble_research_from_deepdives(session)
    brief = await generate_diagnostic_brief(session, research)

    # 2. CMO advisory (tấn công rank 1, ≤2 kênh, not_doing, kill_criteria)
    advisory = await generate_strategy(session, brief)

    # 3. Persist (nếu có engagement)
    brief_id = None
    if engagement_id:
        try:
            from storage import v2
            brief_row = await v2.insert_brief(
                engagement_id=engagement_id, user_id=session.user_id,
                facts=brief.get("facts"), hypotheses=brief.get("hypotheses"),
                gaps=brief.get("gaps"), sources=brief.get("sources"),
                grounded=brief.get("grounded", False), confidence_note=brief.get("confidence_note"),
                content=brief.get("content"), model_used=brief.get("model_used"),
                tokens_used=brief.get("tokens_used"),
            )
            brief_id = brief_row["id"] if brief_row else None
            await v2.update_engagement(engagement_id, brief_id=brief_id)
            await persist_strategy(session, engagement_id, brief_id, advisory)
        except Exception as e:
            logger.warning("run_advisor persist failed: %s", e)

    return {
        "brief":         brief,
        "advisory":      advisory,
        "brief_card":    render_brief_card(brief),
        "advisory_card": render_strategy_card(advisory),
    }
