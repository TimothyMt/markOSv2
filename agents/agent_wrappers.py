"""
Agent wrappers — wrap existing AgentSkill classes thành async functions
cho orchestrator dùng.

Mỗi wrapper:
- Signature: `async def NAME(session: Session) -> str`
- Có `_provider` attribute: dùng cho monitoring + LLM Router routing
- Reuse logic của _run_skill từ pipeline.py (giữ Critic, format injection, token tracking)

S8.2 scope: 8 Digital Twin wrappers — Anna/Bình/Chi/David/Linh/Minh/Phương/Tâm
mapping với 8 strategic skill classes hiện có + 1 conditional logic cho USP.
"""
from __future__ import annotations

import logging
from typing import Optional

from storage.models import Session
from agents.skills import (
    MarketResearchSkill,
    CompetitorSkill,
    CustomerInsightSkill,
    PsychologyPricingSkill,
    UspDefinitionSkill,
    StrategySynthesisSkill,
    AgentSkill,
    ContextStrategy,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Helper — run skill via LLM Router (multi-provider failover)
# ─────────────────────────────────────────────────────────────────

async def _run_skill_via_router(skill: AgentSkill, session: Session, task_type) -> str:
    """Execute skill qua llm_router (multi-provider chain).

    Khác với _run_skill (hardcode Anthropic): build context giống nhau nhưng
    output route qua ROUTING_TABLE → primary + fallbacks tự động.

    Use case: agents có primary provider NON-Anthropic (competitor=GPT-5,
    retention=GPT-5 mini, winback=GPT-5 mini, market=Gemini Grounded).
    """
    from tools.llm_router import call as router_call, AllProvidersFailedError
    from agents.output_formats import get_format_instruction, get_lang_instruction
    from tools.token_tracker import track_usage_raw

    context = skill.build_context(session)
    user_msg = skill.build_user_msg(session)

    # Inject user correction (regen flow)
    user_correction = (session.pending_intake or {}).get("_user_correction")
    if user_correction and "USER CORRECTION" not in user_msg:
        user_msg += (
            "\n\n---\n\n"
            "**USER CORRECTION (sếp đã feedback ở lần chạy trước):**\n"
            f"{user_correction}\n\nApply correction vào output mới."
        )

    format_instruction = get_format_instruction(skill.output_format)
    en_level = (session.preferences or {}).get("en_level", "moderate")
    lang_instruction = get_lang_instruction(en_level)

    user_name = ((session.preferences or {}).get("user_name", "") or "").strip()
    name_directive = (
        f"\n\n---\n\n**Tên user:** {user_name}. Khi xưng hô gọi 'sếp {user_name}'."
    ) if user_name else ""

    augmented_system = (
        skill.system_prompt + format_instruction + "\n\n---\n\n"
        + lang_instruction + name_directive
    )
    full_user = f"{context}\n\n---\n\n{user_msg}"

    logger.info(
        "Skill %s via router: task=%s max_tokens=%d ctx_chars=%d",
        skill.name, task_type.value, skill.max_tokens, len(context) + len(user_msg),
    )

    try:
        result = await router_call(
            task_type=task_type,
            system=augmented_system,
            user=full_user,
            max_tokens=skill.max_tokens,
        )
    except AllProvidersFailedError as e:
        # Last-resort: fallback xuống legacy _run_skill (Anthropic SDK với retry)
        logger.error("Skill %s: all router providers failed, fallback _run_skill: %s", skill.name, e)
        from agents.pipeline import _run_skill
        return await _run_skill(skill, session)

    raw_output = result["output"]
    provider = result.get("provider", "unknown")
    logger.info(
        "Skill %s: provider=%s in=%d out=%d latency=%.1fs",
        skill.name, provider,
        result.get("tokens_in", 0), result.get("tokens_out", 0),
        result.get("latency_sec", 0),
    )

    # Token tracking — per-skill với actual provider + latency
    try:
        from tools.token_tracker import track_skill
        track_skill(
            session,
            skill_name=skill.name,
            provider=provider,
            input_tok=result.get("tokens_in", 0),
            output_tok=result.get("tokens_out", 0),
            latency_sec=result.get("latency_sec", 0.0),
        )
    except Exception as e:
        logger.warning("Token tracking failed (%s via router): %s", skill.name, e)

    return raw_output


# Helper marker — dùng để track provider per agent (S8.3 LLM Router sẽ override)
def _with_provider(provider_name: str):
    """Decorator gắn _provider attribute cho wrapper function."""
    def deco(fn):
        fn._provider = provider_name
        return fn
    return deco


# ─────────────────────────────────────────────────────────────────
# TIER 1 — Foundation agents (parallel, no deps)
# ─────────────────────────────────────────────────────────────────

@_with_provider("gemini_grounded_router")
async def market_research_agent(session: Session) -> str:
    """🌍 Anna — Sr Market Research Analyst.

    Routes via llm_router → MARKET_RESEARCH_DATA chain:
    Gemini Pro Grounded (citations) → Gemini Pro → Sonnet (fallback)
    """
    from tools.llm_router import TaskType
    result = await _run_skill_via_router(
        MarketResearchSkill(), session, TaskType.MARKET_RESEARCH_DATA,
    )
    session.add_result("market_research", result)
    return result


@_with_provider("openai_gpt5_router")
async def competitor_agent(session: Session) -> str:
    """🕵️ Bình — Competitor Intelligence Analyst.

    Routes via llm_router → COMPETITOR_MATRIX chain:
    GPT-5 (structured matrix) → Sonnet → GPT-5 mini (fallback)
    """
    from tools.llm_router import TaskType
    result = await _run_skill_via_router(
        CompetitorSkill(), session, TaskType.COMPETITOR_MATRIX,
    )
    session.add_result("competitor", result)
    return result


@_with_provider("anthropic_sonnet")
async def customer_insight_agent(session: Session) -> str:
    """👥 Chi — Consumer Psychologist VN.

    Foundation tier — ICP + JTBD + Pain-gain map với VN cultural depth.
    Sonnet giữ nguyên (em strong nhất cho VN psychographics).
    """
    from agents.pipeline import _run_skill
    result = await _run_skill(CustomerInsightSkill(), session)
    session.add_result("customer_insight", result)
    return result


# ─────────────────────────────────────────────────────────────────
# TIER 2 — Strategy synthesis (parallel after T1)
# ─────────────────────────────────────────────────────────────────

@_with_provider("anthropic_sonnet")
async def usp_definition_agent(session: Session) -> str:
    """🎯 Linh — USP Strategist.

    Tier 2 — depends on T1 outputs (market + competitor + customer).
    Conditional skip nếu profile.usp_confidence='clear'.
    """
    confidence = (session.profile.usp_confidence or "").lower()
    if confidence == "clear":
        # Skip — already have USP from intake
        skipped_msg = (
            "## USP — Skipped (đã có từ intake)\n\n"
            f'USP user đã định nghĩa: "{session.profile.usp or "N/A"}"\n\n'
            "Synthesis sẽ dùng USP này trực tiếp."
        )
        session.add_result("usp_definition", skipped_msg)
        return skipped_msg

    from agents.pipeline import _run_skill
    result = await _run_skill(UspDefinitionSkill(), session)
    session.add_result("usp_definition", result)
    return result


@_with_provider("anthropic_sonnet")
async def psychology_pricing_agent(session: Session) -> str:
    """🧠 David — Marketing Psychologist + Pricing Strategist.

    Tier 2 — combined psychology + pricing trong 1 call (giữ design hiện tại).
    S8.3 có thể split: psychology=Sonnet ∥ pricing=GPT-4o parallel sub-tasks.
    """
    from agents.pipeline import _run_skill
    result = await _run_skill(PsychologyPricingSkill(), session)
    session.add_result("psychology_pricing", result)
    return result


# ─────────────────────────────────────────────────────────────────
# TIER 3 — SWOT Analysis (sequential: cần đủ T1+T2 results)
# ─────────────────────────────────────────────────────────────────

async def swot_agent(session: Session) -> str:
    """🔀 Max — SWOT Analysis.

    Tier 3 — tổng hợp S/W/O/T từ toàn bộ T1+T2 research pipeline.
    Sequential (không parallel): cần đủ Market+Competitor+Customer+USP+Pricing.
    """
    from agents.pipeline import _run_skill
    from agents.skills import SwotSkill
    result = await _run_skill(SwotSkill(), session)
    session.add_result("swot", result)
    return result

@_with_provider("openai_gpt5_mini_router")
async def retention_strategy_agent(session: Session) -> str:
    """🔄 Minh — Customer Retention Strategist.

    Routes via llm_router → RETENTION_MATRIX chain:
    GPT-5 mini (tier matrix structured) → Sonnet → GPT-4.1 mini
    """
    from agents.operational_skills_config import get_operational_skill
    from tools.llm_router import TaskType

    skill = get_operational_skill("retention_strategy")
    skill.context_strategy = ContextStrategy.FULL_PIPELINE
    if hasattr(skill, "_config"):
        skill._config.context_strategy = ContextStrategy.FULL_PIPELINE

    result = await _run_skill_via_router(skill, session, TaskType.RETENTION_MATRIX)
    session.add_result("retention_strategy", result)
    return result


@_with_provider("openai_gpt5_mini_router")
async def winback_vision_agent(session: Session) -> str:
    """🔁 Phương — Winback Campaign Specialist.

    Routes via llm_router → WINBACK_STRATEGY chain:
    GPT-5 mini (sequence structured) → Sonnet → Gemini Flash
    """
    from agents.operational_skills_config import get_operational_skill
    from tools.llm_router import TaskType

    skill = get_operational_skill("winback_campaign")
    skill.context_strategy = ContextStrategy.FULL_PIPELINE
    if hasattr(skill, "_config"):
        skill._config.context_strategy = ContextStrategy.FULL_PIPELINE

    result = await _run_skill_via_router(skill, session, TaskType.WINBACK_STRATEGY)
    session.add_result("winback_campaign", result)
    return result


@_with_provider("anthropic_sonnet")
async def retention_then_winback_chain(session: Session) -> str:
    """🔄→🔁 Minh + Phương — Sequential chain.

    Tier 3 SEQUENTIAL chain — Winback đọc Retention output từ session.results.
    Wrap thành 1 function vì orchestrator T3 chỉ cần 1 "agent" trong sequential mode.

    Output: concatenated text của cả 2 stage cho Synthesis đọc.
    """
    retention_result = await retention_strategy_agent(session)
    winback_result = await winback_vision_agent(session)

    combined = (
        f"## Retention Strategy (Tier 3.1)\n\n{retention_result}\n\n"
        f"---\n\n"
        f"## Winback Vision (Tier 3.2)\n\n{winback_result}"
    )
    return combined


# ─────────────────────────────────────────────────────────────────
# TIER 4 — Synthesis (long context aggregation)
# ─────────────────────────────────────────────────────────────────

@_with_provider("gemini_pro_with_haiku_polish")
async def synthesizer_agent(session: Session) -> str:
    """📋 Tâm — Chief Marketing Strategist (Synthesizer).

    Tier 4 — aggregate all T1-T3 outputs thành Marketing Strategy hoàn chỉnh.

    Pattern: Gemini 2.5 Pro (long context primary) → Haiku polish (VN tone).
    Failover chain (trong llm_router): Gemini Pro → Gemini Flash → Anthropic Sonnet.

    Khi GEMINI_API_KEY chưa setup hoặc credit hết, failover xuống Sonnet —
    pipeline KHÔNG fail, chỉ chậm hơn + cost cao hơn.
    """
    from agents.pipeline import _run_skill
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
    from agents.output_formats import get_format_instruction, get_lang_instruction

    skill = StrategySynthesisSkill()

    # Build context + user_msg (same logic as _run_skill, but route output qua router)
    context = skill.build_context(session)
    user_msg = skill.build_user_msg(session)

    format_instruction = get_format_instruction(skill.output_format)
    en_level = (session.preferences or {}).get("en_level", "moderate")
    lang_instruction = get_lang_instruction(en_level)

    user_name = ((session.preferences or {}).get("user_name", "") or "").strip()
    name_directive = (
        f"\n\n---\n\n**Tên user:** {user_name}. Khi xưng hô gọi 'sếp {user_name}'."
    ) if user_name else ""

    augmented_system = (
        skill.system_prompt + format_instruction + "\n\n---\n\n"
        + lang_instruction + name_directive
    )
    full_user = f"{context}\n\n---\n\n{user_msg}"

    # Step 1: Primary call — Gemini Pro (auto failover trong router)
    try:
        result = await router_call(
            task_type=TaskType.SYNTHESIS_LONG_CONTEXT,
            system=augmented_system,
            user=full_user,
            max_tokens=skill.max_tokens,
        )
        raw_output = result["output"]
        provider = result.get("provider", "unknown")
        logger.info(
            f"Synthesizer: provider={provider} "
            f"in={result.get('tokens_in')} out={result.get('tokens_out')} "
            f"latency={result.get('latency_sec', 0):.1f}s"
        )

        # Track tokens — per-skill với actual provider + latency
        try:
            from tools.token_tracker import track_skill
            track_skill(
                session,
                skill_name="synthesis",
                provider=provider,
                input_tok=result.get("tokens_in", 0),
                output_tok=result.get("tokens_out", 0),
                latency_sec=result.get("latency_sec", 0.0),
            )
        except Exception:
            pass

    except AllProvidersFailedError as e:
        logger.error(f"Synthesizer: all providers failed, fallback _run_skill: {e}")
        # Last-resort: use legacy _run_skill path (calls Anthropic directly với retry SDK)
        raw_output = await _run_skill(skill, session)
        session.add_result("synthesis", raw_output)
        return raw_output

    # Step 2: Haiku polish VN tone — chỉ khi Gemini đã trả output
    # (nếu Sonnet đã chạy ở fallback path thì skip polish — Sonnet VN tone đã tốt)
    if provider in ("gemini_pro", "gemini_flash"):
        try:
            polished = await _haiku_polish_vn(raw_output, session)
            session.add_result("synthesis", polished)
            return polished
        except Exception as e:
            logger.warning(f"Haiku polish failed, returning raw Gemini output: {e}")
            session.add_result("synthesis", raw_output)
            return raw_output

    # Sonnet/Haiku path — no polish needed
    session.add_result("synthesis", raw_output)
    return raw_output


HAIKU_POLISH_SYSTEM = """Bạn là VN Editor — chuyên viên Việt hoá tone marketing.

Nhiệm vụ: Đọc output Marketing Strategy đã có sẵn, POLISH lại tone VN cho:
- Giọng "em-sếp" tự nhiên (KHÔNG dùng "mình/bạn/anh/chị")
- Việt hoá thuật ngữ EN không cần thiết (vd: "implement" → "triển khai")
- Câu cú flow hơn, bớt cứng nhắc
- GIỮ NGUYÊN: structure (sections, numbers, KPI, frameworks), số liệu, USP

QUY TẮC:
- KHÔNG đổi nội dung — chỉ polish tone
- KHÔNG xoá section, KHÔNG đổi số liệu
- KHÔNG thêm preamble như "Đây là bản polished..." — output trực tiếp"""


async def _haiku_polish_vn(raw_text: str, session: Session) -> str:
    """Polish step — Haiku 4.5 nhẹ refine VN tone.

    Match Synthesizer output 40K → polish max_tokens 40K (Haiku 4.5 extended
    output beta cần header `anthropic-beta: output-128k-2025-02-19` set sẵn
    trong Anthropic SDK 0.40+).
    """
    from tools.llm_router import call as router_call, TaskType
    result = await router_call(
        task_type=TaskType.CRITIC_REVIEW,  # Route → Haiku primary
        system=HAIKU_POLISH_SYSTEM,
        user=f"Polish VN tone cho text sau:\n\n{raw_text}",
        max_tokens=40000,  # Match Synthesizer 40K (was 12K — too small for full polish)
    )
    logger.info(
        f"Synthesizer polish: provider={result.get('provider')} "
        f"latency={result.get('latency_sec', 0):.1f}s"
    )
    return result["output"]


# ─────────────────────────────────────────────────────────────────
# TIER 5 — Tactical Playbook (sequential: cần SWOT + Synthesis)
# ─────────────────────────────────────────────────────────────────

async def tactical_playbook_agent(session: Session) -> str:
    """📋 Max — Tactical Playbook.

    Tier 5 — viết SO/WO/WT tactics per-segment dựa trên SWOT + Synthesis.
    Sequential: chạy sau synthesizer_agent.
    """
    from agents.pipeline import _run_skill
    from agents.skills import TacticalPlaybookSkill
    result = await _run_skill(TacticalPlaybookSkill(), session)
    session.add_result("tactical_playbook", result)
    return result


# ─────────────────────────────────────────────────────────────────
# Registry — agent_name → wrapper function (cho introspection)
# ─────────────────────────────────────────────────────────────────

ALL_AGENTS = {
    "market_research_agent":         market_research_agent,
    "competitor_agent":              competitor_agent,
    "customer_insight_agent":        customer_insight_agent,
    "usp_definition_agent":          usp_definition_agent,
    "psychology_pricing_agent":      psychology_pricing_agent,
    "swot_agent":                    swot_agent,
    "retention_strategy_agent":      retention_strategy_agent,
    "winback_vision_agent":          winback_vision_agent,
    "retention_then_winback_chain":  retention_then_winback_chain,
    "synthesizer_agent":             synthesizer_agent,
    "tactical_playbook_agent":       tactical_playbook_agent,
}


def get_agent_provider(agent_name: str) -> str:
    """Lookup provider của 1 agent (cho monitoring/debug)."""
    agent = ALL_AGENTS.get(agent_name)
    if not agent:
        return "unknown"
    return getattr(agent, "_provider", "unknown")
