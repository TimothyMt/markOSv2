"""
Token billing — tính chi phí thực tế theo provider và token count.

Pricing source (approximate, verify at provider dashboards):
  Anthropic  → https://www.anthropic.com/pricing
  Gemini     → https://ai.google.dev/pricing
  OpenAI     → https://openai.com/pricing

All prices in USD per 1M tokens (input, output).
"""
from __future__ import annotations

from typing import Optional

# ─────────────────────────────────────────────────────────────────
# Price table — (input_usd_per_1m, output_usd_per_1m)
# ─────────────────────────────────────────────────────────────────

PROVIDER_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "anthropic_sonnet":     (3.00,  15.00),   # claude-sonnet-4-6
    "anthropic_haiku":      (0.80,   4.00),   # claude-haiku-4-5

    # Google Gemini
    "gemini_pro":           (1.25,  10.00),   # gemini-2.5-pro (<=200K ctx)
    "gemini_pro_grounded":  (1.25,  10.00),   # gemini-2.5-pro + Search (Search free)
    "gemini_flash":         (0.15,   0.60),   # gemini-2.5-flash

    # OpenAI
    "openai_gpt5":          (10.00, 40.00),   # gpt-5 — estimate, confirm at dashboard
    "openai_gpt5_mini":     (0.40,   1.60),   # gpt-5-mini — estimate
    "openai_gpt5_nano":     (0.10,   0.40),   # gpt-5-nano — estimate
    "openai_gpt_4_1_mini":  (0.40,   1.60),   # gpt-4.1-mini
    "openai_gpt4o":         (2.50,  10.00),   # gpt-4o (legacy)
    "openai_gpt4o_mini":    (0.15,   0.60),   # gpt-4o-mini (legacy)
}

# VND/USD reference rate — update định kỳ
VND_PER_USD: float = 25_500.0

# Cost key stored in session.preferences
_COST_KEY = "cost_used_usd"


# ─────────────────────────────────────────────────────────────────
# Core calculation
# ─────────────────────────────────────────────────────────────────

def calc_cost_usd(
    provider: str,
    tokens_in: int,
    tokens_out: int,
    cache_read: int = 0,
    cache_create: int = 0,
) -> float:
    """Tính chi phí USD cho 1 call.

    Cache read = 10% input price (Anthropic prompt cache discount).
    Cache create = 125% input price (Anthropic cache write surcharge).
    Gemini/OpenAI: cache_read/create ignored (no cache pricing yet).
    """
    pricing = PROVIDER_PRICING.get(provider)
    if not pricing:
        return 0.0

    input_rate, output_rate = pricing
    cost = (tokens_in / 1_000_000) * input_rate
    cost += (tokens_out / 1_000_000) * output_rate

    if provider.startswith("anthropic"):
        cost += (cache_read / 1_000_000) * input_rate * 0.10
        cost += (cache_create / 1_000_000) * input_rate * 1.25

    return round(cost, 6)


def calc_cost_vnd(
    provider: str,
    tokens_in: int,
    tokens_out: int,
    cache_read: int = 0,
    cache_create: int = 0,
) -> float:
    """Tính chi phí VND."""
    return calc_cost_usd(provider, tokens_in, tokens_out, cache_read, cache_create) * VND_PER_USD


def fmt_usd(amount: float) -> str:
    """Format USD: 0.000345 → '$0.000345', 1.23 → '$1.23'"""
    if amount < 0.001:
        return f"${amount:.6f}"
    if amount < 1:
        return f"${amount:.4f}"
    return f"${amount:.2f}"


def fmt_vnd(amount: float) -> str:
    """Format VND: 8750 → '8,750đ'"""
    return f"{int(amount):,}đ"


# ─────────────────────────────────────────────────────────────────
# Session cost accumulation
# ─────────────────────────────────────────────────────────────────

def accumulate_cost(session, cost_usd: float) -> float:
    """Cộng thêm cost_usd vào session.preferences['cost_used_usd'].
    Returns total accumulated cost.
    """
    if session is None or cost_usd <= 0:
        return 0.0
    prefs = session.preferences or {}
    try:
        current = float(prefs.get(_COST_KEY, 0.0))
    except (ValueError, TypeError):
        current = 0.0
    total = current + cost_usd
    prefs[_COST_KEY] = round(total, 6)
    session.preferences = prefs
    return total


def get_total_cost_usd(session) -> float:
    """Tổng chi phí USD đã dùng trong session."""
    if session is None:
        return 0.0
    prefs = session.preferences or {}
    try:
        return float(prefs.get(_COST_KEY, 0.0))
    except (ValueError, TypeError):
        return 0.0


# ─────────────────────────────────────────────────────────────────
# Summary helpers
# ─────────────────────────────────────────────────────────────────

def cost_summary_from_log(token_log: list[dict]) -> dict:
    """Aggregate cost per provider từ token_log entries.

    Returns:
        {
          "total_usd": float,
          "total_vnd": float,
          "by_provider": {provider: {"usd": float, "calls": int}},
          "by_skill": {skill: {"usd": float, "calls": int}},
        }
    """
    total_usd = 0.0
    by_provider: dict[str, dict] = {}
    by_skill: dict[str, dict] = {}

    for entry in token_log:
        provider = entry.get("provider", "unknown")
        skill = entry.get("skill", "unknown")
        cost = calc_cost_usd(
            provider,
            entry.get("tokens_in", 0) or entry.get("input_tok", 0),
            entry.get("tokens_out", 0) or entry.get("output_tok", 0),
            entry.get("cache_read", 0),
            entry.get("cache_create", 0),
        )
        total_usd += cost

        bp = by_provider.setdefault(provider, {"usd": 0.0, "calls": 0})
        bp["usd"] += cost
        bp["calls"] += 1

        bs = by_skill.setdefault(skill, {"usd": 0.0, "calls": 0})
        bs["usd"] += cost
        bs["calls"] += 1

    # round for display
    for v in by_provider.values():
        v["usd"] = round(v["usd"], 6)
    for v in by_skill.values():
        v["usd"] = round(v["usd"], 6)

    return {
        "total_usd": round(total_usd, 6),
        "total_vnd": round(total_usd * VND_PER_USD, 0),
        "by_provider": by_provider,
        "by_skill": by_skill,
    }


def format_cost_report(session) -> str:
    """Render cost report string cho /settings command."""
    from tools.token_tracker import get_token_log
    log = get_token_log(session)
    if not log:
        return "Chưa có dữ liệu chi phí."

    summary = cost_summary_from_log(log)
    total_usd = summary["total_usd"]
    total_vnd = summary["total_vnd"]

    lines = [
        f"💰 *Chi phí API (session này)*",
        f"Tổng: {fmt_usd(total_usd)} ≈ {fmt_vnd(total_vnd)}",
        "",
        "*Theo provider:*",
    ]
    for prov, data in sorted(summary["by_provider"].items(), key=lambda x: -x[1]["usd"]):
        lines.append(f"  • `{prov}`: {fmt_usd(data['usd'])} ({data['calls']} calls)")

    top_skills = sorted(summary["by_skill"].items(), key=lambda x: -x[1]["usd"])[:5]
    if top_skills:
        lines.append("")
        lines.append("*Top skills (tốn nhất):*")
        for skill, data in top_skills:
            lines.append(f"  • `{skill}`: {fmt_usd(data['usd'])}")

    return "\n".join(lines)
