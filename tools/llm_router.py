"""
Multi-Provider LLM Router (Sprint 8.3 stub).

Single entry point cho mọi LLM call. Routing decision based on `task_type`:
- Mỗi TaskType có routing chain (primary → fallback1 → fallback2)
- Auto failover khi provider raise RateLimitError / ProviderUnavailable
- Token tracking + provider monitoring built-in

S8.3 scope:
- ✅ Provider enum + TaskType enum
- ✅ ROUTING_TABLE config-driven
- ✅ Working Anthropic Sonnet + Haiku paths
- ⏳ Gemini Pro/Flash: stub (NotImplementedError) — wire khi có GEMINI_API_KEY (S8.7)
- ⏳ OpenAI GPT-4o/mini: stub — wire khi có OPENAI_API_KEY
- ⏳ Perplexity Sonar: stub — wire khi có PERPLEXITY_API_KEY

Backward compat: nếu router không gọi được (chưa wire), fallback xuống Anthropic
Sonnet — pipeline hiện tại vẫn chạy.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from enum import Enum
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_SONNET_MODEL, CLAUDE_HAIKU_MODEL

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Provider enum
# ─────────────────────────────────────────────────────────────────

class Provider(str, Enum):
    """Available LLM providers. Order matters: primary first, fallbacks after."""
    ANTHROPIC_SONNET     = "anthropic_sonnet"      # claude-sonnet-4-6
    ANTHROPIC_HAIKU      = "anthropic_haiku"       # claude-haiku-4-5
    GEMINI_PRO           = "gemini_pro"            # gemini-2.5-pro (1M context)
    GEMINI_PRO_GROUNDED  = "gemini_pro_grounded"   # gemini-2.5-pro + Google Search (replace Perplexity)
    GEMINI_FLASH         = "gemini_flash"          # gemini-2.5-flash (cheap)
    OPENAI_GPT5          = "openai_gpt5"           # gpt-5 (flagship structured + reasoning)
    OPENAI_GPT5_MINI     = "openai_gpt5_mini"      # gpt-5-mini (sweet spot quality+cost)
    OPENAI_GPT5_NANO     = "openai_gpt5_nano"      # gpt-5-nano (bulk cheap)
    OPENAI_GPT_4_1_MINI  = "openai_gpt_4_1_mini"   # gpt-4.1-mini (1M ctx fallback)
    OPENAI_GPT4O         = "openai_gpt4o"          # legacy gpt-4o (deprecated by GPT-5)
    OPENAI_GPT4O_MINI    = "openai_gpt4o_mini"     # legacy gpt-4o-mini
    PERPLEXITY_SONAR     = "perplexity_sonar"      # DEPRECATED — replaced bởi GEMINI_PRO_GROUNDED


# ─────────────────────────────────────────────────────────────────
# TaskType enum — semantic intent của call
# ─────────────────────────────────────────────────────────────────

class TaskType(str, Enum):
    # Strategic stages
    MARKET_RESEARCH_DATA      = "market_research_data"       # → Perplexity primary
    MARKET_RESEARCH_NARRATIVE = "market_research_narrative"  # → Haiku VN polish
    COMPETITOR_RESEARCH       = "competitor_research"
    COMPETITOR_MATRIX         = "competitor_matrix"
    CUSTOMER_INSIGHT          = "customer_insight"
    PSYCHOLOGY                = "psychology"
    PRICING_MATH              = "pricing_math"
    USP_CREATIVE              = "usp_creative"
    RETENTION_MATRIX          = "retention_matrix"
    WINBACK_STRATEGY          = "winback_strategy"
    SYNTHESIS_LONG_CONTEXT    = "synthesis_long_context"     # → Gemini Pro primary

    # Operational
    INTAKE_JSON               = "intake_json"
    CRITIC_REVIEW             = "critic_review"
    CONTENT_TABLE             = "content_table"
    CONTENT_HERO              = "content_hero"
    CONTENT_BULK              = "content_bulk"
    CHANNEL_ADAPT             = "channel_adapt"
    CLASSIFICATION            = "classification"
    VISION_ANALYSIS           = "vision_analysis"

    # Generic fallbacks
    GENERIC_CREATIVE          = "generic_creative"
    GENERIC_STRUCTURED        = "generic_structured"

    # ─── Operational skills ──────────────────────────────────────
    OPS_CRITICAL              = "ops_critical"          # High-stakes: ads_optimizer, brand_voice — Sonnet locked
    OPS_BRIEF                 = "ops_brief"             # Campaign Brief — GPT-5 primary
    OPS_ANALYSIS              = "ops_analysis"          # Audit, Analytics, Spy — GPT-5 primary
    OPS_CONTENT_CREATIVE      = "ops_content_creative"  # Ads copy, video scripts — GPT-5 primary
    OPS_CONTENT_BULK          = "ops_content_bulk"      # Email sequence, post batch — GPT-5-mini primary


# ─────────────────────────────────────────────────────────────────
# Routing table — task → ordered provider chain (primary → fallbacks)
# ─────────────────────────────────────────────────────────────────

ROUTING_TABLE: dict[TaskType, list[Provider]] = {
    # ─── Strategic pipeline — CEO-locked chains (Phase 1b) ────────────
    # Research — Gemini Grounded for citations (Google Search built-in)
    TaskType.MARKET_RESEARCH_DATA:       [Provider.GEMINI_PRO_GROUNDED, Provider.GEMINI_PRO, Provider.ANTHROPIC_SONNET],
    TaskType.MARKET_RESEARCH_NARRATIVE:  [Provider.ANTHROPIC_HAIKU, Provider.OPENAI_GPT5_MINI],
    TaskType.COMPETITOR_RESEARCH:        [Provider.GEMINI_PRO_GROUNDED, Provider.GEMINI_PRO, Provider.ANTHROPIC_SONNET],

    # Structured matrix — GPT-5 primary, Gemini Pro fallback (strong at tables)
    TaskType.COMPETITOR_MATRIX:          [Provider.OPENAI_GPT5, Provider.GEMINI_PRO, Provider.ANTHROPIC_SONNET],

    # VN-critical creative — Sonnet primary, GPT-5 fallback, Gemini Pro last
    TaskType.CUSTOMER_INSIGHT:           [Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5, Provider.GEMINI_PRO],
    # PSYCHOLOGY: GPT-5 primary — combined psychology+pricing output is 8-10K tokens;
    # Sonnet hits 180s timeout at that length. GPT-5 completes in ~30-40s.
    TaskType.PSYCHOLOGY:                 [Provider.OPENAI_GPT5, Provider.ANTHROPIC_SONNET, Provider.GEMINI_PRO],
    TaskType.USP_CREATIVE:               [Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5, Provider.GEMINI_PRO],
    TaskType.CONTENT_HERO:               [Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5_MINI],

    # Math/structured — GPT-5 mini primary, Gemini Flash before Sonnet (cost)
    TaskType.PRICING_MATH:               [Provider.OPENAI_GPT5, Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5_MINI],
    TaskType.RETENTION_MATRIX:           [Provider.OPENAI_GPT5_MINI, Provider.GEMINI_FLASH, Provider.ANTHROPIC_SONNET],
    TaskType.WINBACK_STRATEGY:           [Provider.OPENAI_GPT5_MINI, Provider.GEMINI_FLASH, Provider.ANTHROPIC_SONNET],
    TaskType.CONTENT_TABLE:              [Provider.OPENAI_GPT5_MINI, Provider.GEMINI_FLASH, Provider.ANTHROPIC_SONNET],

    # Synthesis — Gemini Pro 1M ctx primary (CEO-locked: avoid Sonnet rate-limit)
    TaskType.SYNTHESIS_LONG_CONTEXT:     [Provider.GEMINI_PRO, Provider.OPENAI_GPT5_MINI, Provider.ANTHROPIC_SONNET],

    # Intake — GPT-5 mini primary (CEO-locked: reduce Sonnet load)
    TaskType.INTAKE_JSON:                [Provider.OPENAI_GPT5_MINI, Provider.ANTHROPIC_HAIKU, Provider.ANTHROPIC_SONNET],

    # Polish/critic — Haiku primary, GPT-5 mini fallback (avoid Sonnet for polish)
    TaskType.CRITIC_REVIEW:              [Provider.ANTHROPIC_HAIKU, Provider.OPENAI_GPT5_MINI, Provider.OPENAI_GPT5],

    # Bulk content — GPT-5 mini cheap & fast
    TaskType.CONTENT_BULK:               [Provider.OPENAI_GPT5_MINI, Provider.ANTHROPIC_SONNET, Provider.GEMINI_FLASH],
    TaskType.CHANNEL_ADAPT:              [Provider.OPENAI_GPT5_MINI, Provider.ANTHROPIC_HAIKU, Provider.GEMINI_FLASH],
    TaskType.CLASSIFICATION:             [Provider.OPENAI_GPT5_NANO, Provider.GEMINI_FLASH, Provider.ANTHROPIC_HAIKU],

    # Vision — Anthropic vision strong
    TaskType.VISION_ANALYSIS:            [Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5],

    # Generic fallbacks
    TaskType.GENERIC_CREATIVE:           [Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5, Provider.GEMINI_PRO],
    TaskType.GENERIC_STRUCTURED:         [Provider.OPENAI_GPT5_MINI, Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT_4_1_MINI],

    # ─── Operational skills ──────────────────────────────────────
    # High-stakes actions (real money, brand foundation): Sonnet must be primary
    TaskType.OPS_CRITICAL:          [Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5, Provider.GEMINI_PRO],
    # Long briefs: GPT-5 handles structured long-form well
    TaskType.OPS_BRIEF:             [Provider.OPENAI_GPT5, Provider.ANTHROPIC_SONNET, Provider.GEMINI_PRO],
    # Data analysis: GPT-5 primary, Gemini Pro thinking for complex fallback, Sonnet last
    TaskType.OPS_ANALYSIS:          [Provider.OPENAI_GPT5, Provider.GEMINI_PRO, Provider.ANTHROPIC_SONNET],
    # Creative copy: GPT-5 capable, Sonnet fallback
    TaskType.OPS_CONTENT_CREATIVE:  [Provider.OPENAI_GPT5, Provider.ANTHROPIC_SONNET, Provider.OPENAI_GPT5_MINI],
    # Bulk/structured content: GPT-5-mini cost-efficient
    TaskType.OPS_CONTENT_BULK:      [Provider.OPENAI_GPT5_MINI, Provider.ANTHROPIC_SONNET, Provider.GEMINI_FLASH],
}


# ─────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────

class ProviderUnavailable(Exception):
    """Provider chưa setup (missing API key) hoặc temporarily down."""
    pass


class AllProvidersFailedError(Exception):
    """Cả primary + fallback chain đều fail."""
    pass


# ─────────────────────────────────────────────────────────────────
# Anthropic client (singleton — shared với pipeline.py)
# ─────────────────────────────────────────────────────────────────

_anthropic_client: Optional[anthropic.AsyncAnthropic] = None


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic(
            api_key=ANTHROPIC_API_KEY,
            timeout=300.0,  # 5 min — Sonnet fallback for long outputs (was 180s)
            max_retries=1,
        )
    return _anthropic_client


# ─────────────────────────────────────────────────────────────────
# Provider call functions
# ─────────────────────────────────────────────────────────────────

async def _call_anthropic_sonnet(
    system: str, user: str, max_tokens: int = 4000, **kwargs
) -> dict:
    """Call Anthropic Sonnet 4.6. Returns {output, tokens_in, tokens_out, provider}."""
    client = _get_anthropic_client()
    extra_headers = {}
    if max_tokens > 8192:
        extra_headers["anthropic-beta"] = "output-128k-2025-02-19"
    response = await client.messages.create(
        model=CLAUDE_SONNET_MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        extra_headers=extra_headers,
    )
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"Anthropic {CLAUDE_SONNET_MODEL} output bị cắt giữa câu (stop_reason=max_tokens, "
            f"max_tokens={max_tokens}) — failover sang provider khác."
        )
    return {
        "output": response.content[0].text,
        "tokens_in": getattr(response.usage, "input_tokens", 0),
        "tokens_out": getattr(response.usage, "output_tokens", 0),
        "provider": Provider.ANTHROPIC_SONNET.value,
    }


async def _call_anthropic_haiku(
    system: str, user: str, max_tokens: int = 2048, **kwargs
) -> dict:
    """Call Anthropic Haiku 4.5 — cheap classification + critic.

    Default max output = 8192. Khi max_tokens > 8192 (polish 40K case)
    cần extended output beta header `output-128k-2025-02-19`.
    """
    client = _get_anthropic_client()
    extra_headers = {}
    if max_tokens > 8192:
        extra_headers["anthropic-beta"] = "output-128k-2025-02-19"
    response = await client.messages.create(
        model=CLAUDE_HAIKU_MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        extra_headers=extra_headers,
    )
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"Anthropic {CLAUDE_HAIKU_MODEL} output bị cắt giữa câu (stop_reason=max_tokens, "
            f"max_tokens={max_tokens}) — failover sang provider khác."
        )
    return {
        "output": response.content[0].text,
        "tokens_in": getattr(response.usage, "input_tokens", 0),
        "tokens_out": getattr(response.usage, "output_tokens", 0),
        "provider": Provider.ANTHROPIC_HAIKU.value,
    }


# Lazy import google-genai — chỉ load khi cần
_gemini_client = None


def _get_gemini_client():
    """Lazy initialize Gemini client (singleton)."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ProviderUnavailable("GEMINI_API_KEY env var không có")
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client
    except ImportError as e:
        raise ProviderUnavailable(
            f"google-genai chưa cài. Run: pip install google-genai. Error: {e}"
        )


def _calc_thinking_budget(max_tokens: int) -> int:
    """Smart thinking budget — tránh ăn hết max_tokens.

    Gemini 2.5 Pro counts thinking tokens vào max_output_tokens.
    Nếu thinking_budget >= max_tokens → output empty (no room left).

    Rule:
    - max_tokens < 1500: thinking=0 (no thinking — short response)
    - max_tokens 1500-5000: thinking = 30% (mild reasoning)
    - max_tokens 5000-20000: thinking = min(8000, 40%) — medium reasoning
    - max_tokens >= 20000: thinking = min(12000, 25%) — deep reasoning for
      synthesis 30-40K. Giữ output ≥75% budget cho narrative dày.
    """
    if max_tokens < 1500:
        return 0
    if max_tokens < 5000:
        return int(max_tokens * 0.3)
    if max_tokens < 20000:
        # N-12: dải giữa (research 16K + content assets) — giảm cap 8000→4000 / 40%→25% để chừa
        # output (Gemini tính thinking VÀO max_output) → bớt cụt giữa câu. Không đụng ≥20K (synthesis/playbook).
        return min(4000, int(max_tokens * 0.25))
    return min(12000, int(max_tokens * 0.25))


async def _call_gemini_pro(
    system: str, user: str, max_tokens: int = 10000, **kwargs
) -> dict:
    """Call Gemini 2.5 Pro — long context champion (1M window).

    Wired ở Sprint 8.7 (post-CEO API key provided).

    Config:
    - temperature=0.7: balance creative + consistent
    - thinking_budget: AUTO-calculated theo max_tokens (tránh ăn hết budget)
    - max_output_tokens: configurable per call (default 10K cho synthesis)
    """
    client = _get_gemini_client()
    from google.genai import types

    thinking_budget = _calc_thinking_budget(max_tokens)

    config_kwargs = dict(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=0.7,
        top_p=0.95,
    )
    if thinking_budget > 0:
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=thinking_budget,
        )

    config = types.GenerateContentConfig(**config_kwargs)

    response = await client.aio.models.generate_content(
        model="gemini-2.5-pro",
        contents=user,
        config=config,
    )

    # Extract output — handle None safely (Gemini có thể return text=None
    # khi hit safety filter hoặc max_tokens chỉ đủ cho thinking)
    output_text = response.text or ""
    if not output_text:
        # Try fallback: extract từ candidates parts
        try:
            candidates = response.candidates or []
            if candidates and candidates[0].content and candidates[0].content.parts:
                output_text = "".join(
                    p.text or "" for p in candidates[0].content.parts if hasattr(p, "text")
                )
        except (AttributeError, IndexError):
            pass

        if not output_text:
            finish_reason = getattr(response.candidates[0], "finish_reason", "unknown") if response.candidates else "no_candidates"
            raise RuntimeError(
                f"Gemini Pro empty output (finish_reason={finish_reason}, "
                f"thinking_budget={thinking_budget}, max_tokens={max_tokens}). "
                "Có thể safety block, hoặc max_tokens không đủ cho output."
            )

    # Extract token usage
    usage = getattr(response, "usage_metadata", None)
    tokens_in = getattr(usage, "prompt_token_count", 0) if usage else 0
    tokens_out = getattr(usage, "candidates_token_count", 0) if usage else 0

    return {
        "output": output_text,
        "tokens_in": tokens_in or 0,
        "tokens_out": tokens_out or 0,
        "provider": Provider.GEMINI_PRO.value,
    }


def _patch_homepage_links(text: str, chunks: list) -> str:
    """Replace homepage-only markdown links with specific article URLs from grounding chunks.

    Gemini often writes [Statista](https://statista.com) (homepage) instead of
    the actual article URL. grounding_chunks has the real URLs — use them to
    patch any link where the path is empty or just "/".
    """
    import re
    from urllib.parse import urlparse

    # Build domain → most specific URL map from grounding chunks
    domain_to_url: dict[str, str] = {}
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        if not web:
            continue
        uri = getattr(web, "uri", "") or ""
        if not uri:
            continue
        try:
            netloc = urlparse(uri).netloc.lower().lstrip("www.")
            # Keep the longest (most specific) URL per domain
            if netloc not in domain_to_url or len(uri) > len(domain_to_url[netloc]):
                domain_to_url[netloc] = uri
        except Exception:
            pass

    if not domain_to_url:
        return text

    def _replace(m: re.Match) -> str:
        link_text, url = m.group(1), m.group(2)
        try:
            parsed = urlparse(url)
            if parsed.path in ("", "/"):
                netloc = parsed.netloc.lower().lstrip("www.")
                specific = domain_to_url.get(netloc)
                if specific:
                    return f"[{link_text}]({specific})"
        except Exception:
            pass
        return m.group(0)

    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _replace, text)


async def _call_gemini_pro_grounded(
    system: str, user: str, max_tokens: int = 6000, **kwargs
) -> dict:
    """Call Gemini 2.5 Pro VỚI Google Search Grounding — replace Perplexity.

    Thêm tool google_search() → Gemini tự search Google trước khi answer.
    Output includes inline citations với real URLs.

    Phù hợp cho:
    - Market Research (TAM/SAM/SOM real-time data)
    - Competitor Research (recent competitor moves)
    - Bất kỳ task nào cần fresh data + citations

    Cost: same as Gemini Pro ($1.25/$10) — Search Grounding FREE bundled.
    """
    client = _get_gemini_client()
    from google.genai import types

    thinking_budget = _calc_thinking_budget(max_tokens)

    config_kwargs = dict(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=0.7,
        top_p=0.95,
        # KEY: enable Google Search tool
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    if thinking_budget > 0:
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=thinking_budget,
        )

    config = types.GenerateContentConfig(**config_kwargs)

    response = await client.aio.models.generate_content(
        model="gemini-2.5-pro",
        contents=user,
        config=config,
    )

    # Extract output (same handling as non-grounded version)
    output_text = response.text or ""
    if not output_text:
        try:
            candidates = response.candidates or []
            if candidates and candidates[0].content and candidates[0].content.parts:
                output_text = "".join(
                    p.text or "" for p in candidates[0].content.parts if hasattr(p, "text")
                )
        except (AttributeError, IndexError):
            pass
        if not output_text:
            raise RuntimeError("Gemini Pro Grounded returned empty output")

    # Extract citations từ grounding_metadata (nếu có)
    citations_text = ""
    try:
        candidate = response.candidates[0] if response.candidates else None
        grounding_meta = getattr(candidate, "grounding_metadata", None) if candidate else None
        if grounding_meta:
            chunks = getattr(grounding_meta, "grounding_chunks", []) or []
            if chunks:
                # Patch homepage-only inline links before building citation list
                output_text = _patch_homepage_links(output_text, chunks)

                citations = []
                for i, chunk in enumerate(chunks[:10], 1):  # cap 10 sources
                    web = getattr(chunk, "web", None)
                    if web:
                        title = getattr(web, "title", "") or "Source"
                        uri = getattr(web, "uri", "") or ""
                        if uri:
                            citations.append(f"[{i}] [{title}]({uri})")
                if citations:
                    citations_text = "\n\n---\n\n**Nguồn tham khảo (Google Search):**\n" + "\n".join(citations)
    except (AttributeError, IndexError):
        pass

    final_output = output_text + citations_text

    usage = getattr(response, "usage_metadata", None)
    tokens_in = getattr(usage, "prompt_token_count", 0) if usage else 0
    tokens_out = getattr(usage, "candidates_token_count", 0) if usage else 0

    return {
        "output": final_output,
        "tokens_in": tokens_in or 0,
        "tokens_out": tokens_out or 0,
        "provider": Provider.GEMINI_PRO_GROUNDED.value,
    }


async def _call_gemini_flash(
    system: str, user: str, max_tokens: int = 10000, **kwargs
) -> dict:
    """Call Gemini 2.5 Flash — cheap fallback cho Pro (10x rẻ hơn).

    Flash KHÔNG có thinking mode mặc định nên không cần config thinking_budget.
    """
    client = _get_gemini_client()
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=0.7,
    )

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=user,
        config=config,
    )

    output_text = response.text or ""
    if not output_text:
        try:
            candidates = response.candidates or []
            if candidates and candidates[0].content and candidates[0].content.parts:
                output_text = "".join(
                    p.text or "" for p in candidates[0].content.parts if hasattr(p, "text")
                )
        except (AttributeError, IndexError):
            pass
        if not output_text:
            raise RuntimeError("Gemini Flash returned empty output")

    usage = getattr(response, "usage_metadata", None)
    tokens_in = getattr(usage, "prompt_token_count", 0) if usage else 0
    tokens_out = getattr(usage, "candidates_token_count", 0) if usage else 0

    return {
        "output": output_text,
        "tokens_in": tokens_in or 0,
        "tokens_out": tokens_out or 0,
        "provider": Provider.GEMINI_FLASH.value,
    }


# OpenAI client singleton (lazy init, AsyncOpenAI)
_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ProviderUnavailable("OPENAI_API_KEY env var không có")
    try:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=api_key, timeout=180.0, max_retries=1)
        return _openai_client
    except ImportError as e:
        raise ProviderUnavailable(f"openai SDK chưa cài: {e}")


async def _call_openai_generic(model: str, system: str, user: str, max_tokens: int, provider_enum: "Provider") -> dict:
    """Shared OpenAI Chat Completions caller — dùng cho mọi GPT model.

    GPT-5 series là reasoning models — tokens chia giữa reasoning + output.
    Auto-pick reasoning_effort theo max_tokens để tránh output bị cắt.
    """
    client = _get_openai_client()
    is_gpt5_reasoning = model.startswith("gpt-5")

    request_args = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": max_tokens,
    }

    if is_gpt5_reasoning:
        # Auto-pick reasoning effort: lower max_tokens → minimal reasoning để giữ output.
        # "low" áp dụng cho hầu hết task — "medium" (default khi omit) có thể ăn
        # hết budget reasoning trước khi sinh output, gây cắt giữa câu (finish_reason=length)
        # ngay cả khi max_tokens khá lớn (vd SWOT max_tokens=6000 vẫn bị cắt).
        if max_tokens < 500:
            request_args["reasoning_effort"] = "minimal"
        elif max_tokens < 12000:
            request_args["reasoning_effort"] = "low"
        # else: omit → OpenAI default = medium (task output rất dài, cần reasoning kỹ hơn)

        # reasoning tokens tính vào max_completion_tokens nhưng KHÔNG nằm trong output
        # trả về → cộng buffer để reasoning không ăn vào budget dành cho output.
        request_args["max_completion_tokens"] = max_tokens + 1500

    response = await client.chat.completions.create(**request_args)
    choice = response.choices[0]
    output = (choice.message.content or "").strip()
    if not output:
        raise RuntimeError(
            f"OpenAI {model} returned empty output (finish_reason={choice.finish_reason}, "
            f"max_tokens={max_tokens}). GPT-5 reasoning models cần max_tokens lớn hơn (~500+)."
        )
    if choice.finish_reason == "length":
        raise RuntimeError(
            f"OpenAI {model} output bị cắt giữa câu (finish_reason=length, max_tokens={max_tokens}) "
            f"— failover sang provider khác để có output đầy đủ."
        )
    usage = response.usage
    return {
        "output": output,
        "tokens_in": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "tokens_out": getattr(usage, "completion_tokens", 0) if usage else 0,
        "provider": provider_enum.value,
    }


async def _call_openai_gpt5(
    system: str, user: str, max_tokens: int = 4000, **kwargs
) -> dict:
    """Call OpenAI GPT-5 — flagship structured + reasoning."""
    from config import GPT5_MODEL
    return await _call_openai_generic(GPT5_MODEL, system, user, max_tokens, Provider.OPENAI_GPT5)


async def _call_openai_gpt5_mini(
    system: str, user: str, max_tokens: int = 4000, **kwargs
) -> dict:
    """Call OpenAI GPT-5 mini — sweet spot quality+cost."""
    from config import GPT5_MINI_MODEL
    return await _call_openai_generic(GPT5_MINI_MODEL, system, user, max_tokens, Provider.OPENAI_GPT5_MINI)


async def _call_openai_gpt5_nano(
    system: str, user: str, max_tokens: int = 2048, **kwargs
) -> dict:
    """Call OpenAI GPT-5 nano — bulk cheap."""
    from config import GPT5_NANO_MODEL
    return await _call_openai_generic(GPT5_NANO_MODEL, system, user, max_tokens, Provider.OPENAI_GPT5_NANO)


async def _call_openai_gpt_4_1_mini(
    system: str, user: str, max_tokens: int = 4000, **kwargs
) -> dict:
    """Call OpenAI GPT-4.1 mini — 1M context fallback."""
    from config import GPT_4_1_MINI_MODEL
    return await _call_openai_generic(GPT_4_1_MINI_MODEL, system, user, max_tokens, Provider.OPENAI_GPT_4_1_MINI)


async def _call_openai_gpt4o(
    system: str, user: str, max_tokens: int = 4000, **kwargs
) -> dict:
    """Call OpenAI GPT-4o (legacy)."""
    return await _call_openai_generic("gpt-4o", system, user, max_tokens, Provider.OPENAI_GPT4O)


async def _call_openai_gpt4o_mini(
    system: str, user: str, max_tokens: int = 2048, **kwargs
) -> dict:
    """Call OpenAI GPT-4o mini (legacy)."""
    return await _call_openai_generic("gpt-4o-mini", system, user, max_tokens, Provider.OPENAI_GPT4O_MINI)


async def _call_perplexity_sonar(
    system: str, user: str, max_tokens: int = 4000, **kwargs
) -> dict:
    """Call Perplexity Sonar Pro — research + citations. STUB."""
    if not os.getenv("PERPLEXITY_API_KEY"):
        raise ProviderUnavailable("Perplexity chưa setup")
    raise NotImplementedError("Perplexity Sonar deferred (post-S8)")


# Provider → call function mapping
PROVIDER_CALLERS = {
    Provider.ANTHROPIC_SONNET:    _call_anthropic_sonnet,
    Provider.ANTHROPIC_HAIKU:     _call_anthropic_haiku,
    Provider.GEMINI_PRO:          _call_gemini_pro,
    Provider.GEMINI_PRO_GROUNDED: _call_gemini_pro_grounded,
    Provider.GEMINI_FLASH:        _call_gemini_flash,
    Provider.OPENAI_GPT5:         _call_openai_gpt5,
    Provider.OPENAI_GPT5_MINI:    _call_openai_gpt5_mini,
    Provider.OPENAI_GPT5_NANO:    _call_openai_gpt5_nano,
    Provider.OPENAI_GPT_4_1_MINI: _call_openai_gpt_4_1_mini,
    Provider.OPENAI_GPT4O:        _call_openai_gpt4o,
    Provider.OPENAI_GPT4O_MINI:   _call_openai_gpt4o_mini,
    Provider.PERPLEXITY_SONAR:    _call_perplexity_sonar,
}


# Per-provider hard timeout (seconds).
# Prevents a slow/overloaded provider (e.g. Sonnet 529) from sitting
# for the full client-level timeout (300s) and consuming the outer
# asyncio.wait_for budget before failover can happen.
_PER_PROVIDER_TIMEOUT: dict[Provider, float] = {
    Provider.ANTHROPIC_SONNET:    300.0,  # content pipeline (post_batch 15K+ tokens) needs 2-3 min
    Provider.ANTHROPIC_HAIKU:     90.0,   # intake/classify — generous buffer for slow bursts
    Provider.OPENAI_GPT5:         300.0,  # reasoning model — can take 3-5 min on deep tasks
    Provider.OPENAI_GPT5_MINI:    180.0,  # sweet-spot model — content gen needs 2 min+
    Provider.OPENAI_GPT5_NANO:    90.0,   # bulk classify — short tasks but keep buffer
    Provider.OPENAI_GPT_4_1_MINI: 180.0,  # 1M ctx fallback — long context parsing
    Provider.OPENAI_GPT4O:        150.0,  # multi-modal capable — moderate buffer
    Provider.OPENAI_GPT4O_MINI:   90.0,
    Provider.GEMINI_PRO:          300.0,  # deep analysis tasks
    Provider.GEMINI_PRO_GROUNDED: 300.0,  # grounded search + analysis
    Provider.GEMINI_FLASH:        150.0,  # flash — fast but keep buffer for large outputs
    Provider.PERPLEXITY_SONAR:    90.0,
}


# ─────────────────────────────────────────────────────────────────
# Top-level router
# ─────────────────────────────────────────────────────────────────

async def call(
    task_type: TaskType,
    system: str,
    user: str,
    max_tokens: int = 4000,
    json_schema: Optional[dict] = None,
) -> dict:
    """Single entry point — router picks provider per task_type với failover chain.

    Returns: dict {output, tokens_in, tokens_out, provider, latency_sec}

    Raises:
        AllProvidersFailedError: nếu cả primary + fallback chain đều fail
    """
    providers = ROUTING_TABLE.get(task_type, [Provider.ANTHROPIC_SONNET])

    # Test mode — force toàn bộ task type chạy 1 provider rẻ trước (vẫn giữ
    # fallback chain gốc phía sau nếu forced provider fail). Bật bằng env var:
    #   LLM_FORCE_PROVIDER=anthropic_haiku
    forced = _forced_test_provider()
    if forced:
        providers = [forced] + [p for p in providers if p != forced]

    last_error: Optional[Exception] = None

    for provider in providers:
        caller = PROVIDER_CALLERS.get(provider)
        if not caller:
            logger.error(f"No caller registered for provider {provider}")
            continue

        per_timeout = _PER_PROVIDER_TIMEOUT.get(provider, 60.0)
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                caller(
                    system=system,
                    user=user,
                    max_tokens=max_tokens,
                    json_schema=json_schema,
                ),
                timeout=per_timeout,
            )
            result["latency_sec"] = time.monotonic() - start
            logger.info(
                f"[router] task={task_type.value} provider={provider.value} "
                f"in={result.get('tokens_in')} out={result.get('tokens_out')} "
                f"latency={result['latency_sec']:.1f}s"
            )
            return result

        except asyncio.TimeoutError as e:
            logger.warning(
                f"[router] provider={provider.value} exceeded per-provider timeout "
                f"({per_timeout}s) → failover to next"
            )
            last_error = e
            continue

        except ProviderUnavailable as e:
            # Provider chưa setup — silently failover
            logger.debug(f"Provider {provider} unavailable, failing over: {e}")
            last_error = e
            continue

        except NotImplementedError as e:
            # Stub provider — failover
            logger.debug(f"Provider {provider} not yet implemented, failing over: {e}")
            last_error = e
            continue

        except anthropic.RateLimitError as e:
            logger.warning(f"Provider {provider} rate limit, failing over: {e}")
            last_error = e
            continue

        except anthropic.APITimeoutError as e:
            logger.warning(f"Provider {provider} timeout, failing over: {e}")
            last_error = e
            continue

        except Exception as e:
            logger.warning(
                f"Provider {provider} unexpected error, failing over: "
                f"{type(e).__name__}: {str(e)[:200]}"
            )
            last_error = e
            continue

    raise AllProvidersFailedError(
        f"All providers failed for task={task_type.value}. "
        f"Tried: {[p.value for p in providers]}. "
        f"Last error: {last_error}"
    )


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _forced_test_provider() -> Optional[Provider]:
    """Đọc env var LLM_FORCE_PROVIDER — nếu set, mọi task_type ưu tiên chạy
    provider này trước (test mode, để giảm chi phí khi test). Unset env var
    để trở về routing table gốc."""
    val = os.getenv("LLM_FORCE_PROVIDER", "").strip().lower()
    if not val:
        return None
    try:
        return Provider(val)
    except ValueError:
        logger.warning(f"[router] LLM_FORCE_PROVIDER={val!r} không hợp lệ, bỏ qua")
        return None


def is_provider_available(provider: Provider) -> bool:
    """Check provider khả dụng (API key setup)."""
    if provider in (Provider.ANTHROPIC_SONNET, Provider.ANTHROPIC_HAIKU):
        return bool(ANTHROPIC_API_KEY)
    if provider in (Provider.GEMINI_PRO, Provider.GEMINI_PRO_GROUNDED, Provider.GEMINI_FLASH):
        return bool(os.getenv("GEMINI_API_KEY"))
    if provider in (
        Provider.OPENAI_GPT5,
        Provider.OPENAI_GPT5_MINI,
        Provider.OPENAI_GPT5_NANO,
        Provider.OPENAI_GPT_4_1_MINI,
        Provider.OPENAI_GPT4O,
        Provider.OPENAI_GPT4O_MINI,
    ):
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == Provider.PERPLEXITY_SONAR:
        return bool(os.getenv("PERPLEXITY_API_KEY"))
    return False


def availability_report() -> str:
    """Trạng thái providers — useful cho /settings hoặc debug."""
    lines = ["## LLM Router — Provider Availability"]
    for p in Provider:
        status = "✅" if is_provider_available(p) else "❌"
        lines.append(f"- {status} {p.value}")
    return "\n".join(lines)


# Alias so callers can `from tools.llm_router import route`
route = call


# ─────────────────────────────────────────────────────────────────
# Operational skill → TaskType mapping
# Single source of truth: thêm skill mới → thêm entry ở đây
# ─────────────────────────────────────────────────────────────────

OPS_SKILL_TASK_TYPES: dict[str, TaskType] = {
    # ── Sonnet-locked: real-money actions + brand foundation ──────
    "ads_optimizer":         TaskType.OPS_CRITICAL,   # Executes FB API actions — must be best model
    "brand_voice":           TaskType.OPS_CRITICAL,   # Defines brand tone for entire business

    # ── GPT-5 primary: long structured briefs ─────────────────────
    "campaign_brief":        TaskType.OPS_BRIEF,
    "brand_positioning":     TaskType.OPS_BRIEF,

    # ── GPT-5 primary: data analysis & diagnosis ──────────────────
    "ads_analytics":         TaskType.OPS_ANALYSIS,
    "competitor_spy":        TaskType.OPS_ANALYSIS,
    # Backlog #1: comparison 1-1 cần Google Search grounded → route research chain
    "competitor_comparison": TaskType.COMPETITOR_RESEARCH,

    # ── GPT-5 primary: creative writing ───────────────────────────
    "ads_generator":         TaskType.OPS_CONTENT_CREATIVE,
    "ads_copy":              TaskType.OPS_CONTENT_CREATIVE,
    "video_scripts":         TaskType.OPS_CONTENT_CREATIVE,
    "sales_inbox_script":    TaskType.OPS_CONTENT_CREATIVE,
    "content_repurpose":     TaskType.OPS_CONTENT_CREATIVE,
    "post_write":            TaskType.OPS_CONTENT_CREATIVE,
    "post_hooks":            TaskType.OPS_CONTENT_CREATIVE,

    # ── GPT-5-mini primary: bulk / structured content ─────────────
    "content_generator":     TaskType.OPS_CONTENT_BULK,
    "email_zalo_sequence":   TaskType.OPS_CONTENT_BULK,
    "post_batch":            TaskType.OPS_CONTENT_BULK,

    # ── Strategic A→Z pipeline stages ────────────────────────────
    # _run_skill() tra dict NÀY cho mọi skill. Thiếu entry → rơi về
    # GENERIC_CREATIVE (Sonnet primary) — dồn 100% tải A→Z lên Sonnet OTPM
    # + mất Google Search grounding ở research. Map đúng chuỗi thiết kế:
    "market_research":       TaskType.MARKET_RESEARCH_DATA,   # Gemini Grounded (citations) → Gemini Pro → Sonnet
    "competitor":            TaskType.COMPETITOR_MATRIX,      # GPT-5 (structured matrix) → Gemini Pro → Sonnet
    "customer_insight":      TaskType.CUSTOMER_INSIGHT,       # Sonnet (VN psychographics) → GPT-5 → Gemini Pro
    "psychology_pricing":    TaskType.PSYCHOLOGY,             # GPT-5 (tránh timeout 180s @ 8-10K) → Sonnet → Gemini Pro
    "usp_definition":        TaskType.USP_CREATIVE,           # Sonnet → GPT-5 → Gemini Pro
    # Synthesis (A→Z kế hoạch tổng, ~40K output): Gemini Pro 1M-ctx primary
    # → GPT-5-mini → Sonnet. Offload Sonnet cho output dài.
    "synthesis":             TaskType.SYNTHESIS_LONG_CONTEXT,
    "retention_strategy":    TaskType.RETENTION_MATRIX,   # GPT-5-mini → Sonnet
    "winback_campaign":      TaskType.WINBACK_STRATEGY,   # GPT-5-mini → Sonnet
    "content_calendar":      TaskType.CONTENT_TABLE,      # GPT-5-mini → Sonnet

    # ── Light tasks — cheap providers ─────────────────────────────
    "post_adapt":            TaskType.CHANNEL_ADAPT,      # GPT-5-mini → Haiku
    "post_voice_check":      TaskType.CRITIC_REVIEW,      # Haiku → GPT-5-mini
}
