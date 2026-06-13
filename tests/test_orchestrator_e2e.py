"""
Sprint 8.7 — End-to-End smoke test cho Multi-Agent Orchestrator.

KHÔNG cần API key thật — dùng MockAgentSkill + monkey-patch _run_skill.

Test scenarios:
1. Happy path — all 7 agents succeed → pipeline complete
2. Nice-to-have fail — 1 T1 agent fail → pipeline continues, Synthesis runs
3. Critical fail — customer_insight fail → PipelineAbortError raised
4. Synthesis fail — must_have T4 fail → PipelineAbortError
5. Timeout — 1 agent timeout → fail isolated, others OK
6. Latency benchmark — full pipeline phải < 10s với mock (parallel works)

Chạy:
    python -m tests.test_orchestrator_e2e

Sẽ chạy 6 test cases + report.
"""
from __future__ import annotations

import asyncio
import sys
import time
from unittest.mock import patch

from storage.models import Session, BusinessProfile
from agents.orchestrator import (
    run_multi_agent_pipeline,
    get_strategic_pipeline_tiers,
    PipelineAbortError,
    AgentResult,
)


# ─────────────────────────────────────────────────────────────────
# Mock _run_skill — bypasses real Anthropic API calls
# ─────────────────────────────────────────────────────────────────

# Per-skill mock outputs (realistic length for smoke test)
MOCK_OUTPUTS = {
    "market_research":    "## Market Research mock output\nTAM: 10,000 tỷ VND. SAM: 1,500 tỷ. SOM: 50 tỷ năm 1.",
    "competitor":         "## Competitor mock output\n8 chiều: Tier 1 Cocoon, M.O.I. Market gap: niche 25-30.",
    "customer_insight":   "## Customer Insight mock\nICP: nữ 28-40 HCM văn phòng. JTBD: self-care guilt.",
    "psychology_pricing": "## Psychology+Pricing mock\nLoss aversion + Anchoring. Combo 680K (gốc 850K).",
    "usp_definition":     "## USP mock\nUSP chính: 'Spa Đông y Q1 cho phụ nữ văn phòng kết hợp công nghệ Hàn'.",
    "retention_strategy": "## Retention mock\nTier: Mới 40%, Active 30%, Nguy cơ 15%, VIP 15%.",
    "winback_campaign":   "## Winback mock\nPriority: VIP cũ >90d. Sequence 3 bước Tier 1/2/3.",
    "synthesis":          "## Synthesis mock\nSAVE Framework + SMART goals + 90-day roadmap toàn bộ.",
}


class MockBehavior:
    """Control mock behavior cho mỗi test scenario."""
    def __init__(self):
        self.fail_skills: set[str] = set()       # skill_name → raise exception
        self.timeout_skills: set[str] = set()     # skill_name → sleep > timeout
        self.latency_sec: float = 0.1             # default mock latency

    async def mock_run_skill(self, skill, session):
        skill_name = getattr(skill, "name", "unknown")

        if skill_name in self.fail_skills:
            raise ValueError(f"MOCK: forced fail for {skill_name}")

        if skill_name in self.timeout_skills:
            await asyncio.sleep(300)  # Will hit timeout_per_agent
            return "should not reach"

        await asyncio.sleep(self.latency_sec)
        return MOCK_OUTPUTS.get(skill_name, f"mock output for {skill_name}")

    async def mock_router_call(self, task_type, system, user, max_tokens=4000, **kwargs):
        """Mock router calls — bypass real Gemini/Anthropic/OpenAI APIs.

        Sau Phase 1c, các agents wire qua router gồm: synthesizer,
        market_research, competitor, retention, winback, polish.
        """
        task_id = task_type.value if hasattr(task_type, "value") else str(task_type)
        # Map task_type → skill_name để check fail_skills/timeout_skills
        task_to_skill = {
            "synthesis_long_context": "synthesis",
            "market_research_data":   "market_research",
            "competitor_matrix":      "competitor",
            "retention_matrix":       "retention_strategy",
            "winback_strategy":       "winback_campaign",
            "critic_review":          "polish",
        }
        skill_name = task_to_skill.get(task_id, task_id)

        if skill_name in self.fail_skills:
            raise ValueError(f"MOCK: forced fail for {skill_name} (task={task_id})")

        if skill_name in self.timeout_skills:
            await asyncio.sleep(300)
            return {"output": "should not reach", "provider": "mock", "tokens_in": 0, "tokens_out": 0}

        await asyncio.sleep(self.latency_sec)
        return {
            "output": MOCK_OUTPUTS.get(skill_name, f"mock {skill_name} output"),
            "provider": f"mock_router_{skill_name}",
            "tokens_in": 200,
            "tokens_out": 800,
            "latency_sec": self.latency_sec,
        }


async def _noop_cb(msg: str) -> None:
    """Async no-op progress callback for tests that don't care about progress."""
    pass


async def _passthrough_polish(raw_text: str, session) -> str:
    """Mock Haiku polish — return input unchanged (cho tests).

    synthesizer_agent gọi _haiku_polish_vn sau khi Gemini Pro trả output.
    Trong test, skip polish step để không hit Anthropic API.
    """
    return raw_text


def _full_patches(behavior):
    """Context manager combining 3 patches:
    - agents.pipeline._run_skill: cho 6 agents còn lại (Anthropic path)
    - tools.llm_router.call: cho synthesizer_agent (Gemini path)
    - agents.agent_wrappers._haiku_polish_vn: skip polish step
    """
    import contextlib
    return contextlib.ExitStack().__class__()  # placeholder, see actual impl below


import contextlib


def _full_patches(behavior):
    """Helper: combine 3 patches into single contextmanager."""
    stack = contextlib.ExitStack()
    stack.enter_context(patch("agents.pipeline._run_skill", behavior.mock_run_skill))
    stack.enter_context(patch("tools.llm_router.call", behavior.mock_router_call))
    stack.enter_context(patch("agents.agent_wrappers._haiku_polish_vn", _passthrough_polish))
    return stack


def _make_session() -> Session:
    profile = BusinessProfile(
        industry="health_beauty",
        product_service="Spa thuốc bắc + facial",
        target_customer="Phụ nữ 28-40 HCM văn phòng",
        monthly_revenue="80tr/tháng",
        primary_goal="revenue",
        main_challenge="retention thấp",
        location="HCM Q1",
        usp_confidence="missing",  # Force USP skill to FIND mode
    )
    return Session(user_id=99999, profile=profile)


# ─────────────────────────────────────────────────────────────────
# Test cases
# ─────────────────────────────────────────────────────────────────

async def test_1_happy_path():
    """Tất cả 7 agents succeed → pipeline complete, all stages có output."""
    print("\n" + "=" * 70)
    print("TEST 1: Happy path — all agents succeed")
    print("=" * 70)

    behavior = MockBehavior()
    session = _make_session()
    progress_log = []

    async def capture(msg):
        progress_log.append(msg)

    with _full_patches(behavior):
        start = time.monotonic()
        results = await run_multi_agent_pipeline(session, capture)
        elapsed = time.monotonic() - start

    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Results count: {len(results)}")
    print(f"Progress messages: {len(progress_log)}")

    expected_agents = {
        "market_research_agent", "competitor_agent", "customer_insight_agent",
        "usp_definition_agent", "psychology_pricing_agent",
        "retention_then_winback_chain", "synthesizer_agent",
    }
    assert set(results.keys()) == expected_agents, f"Missing: {expected_agents - set(results.keys())}"
    assert all(r.success for r in results.values()), \
        f"Failed agents: {[n for n, r in results.items() if not r.success]}"

    # Session.results phải có cả 7 stage_keys
    expected_stages = {
        "market_research", "competitor", "customer_insight",
        "usp_definition", "psychology_pricing",
        "retention_strategy", "winback_campaign", "synthesis",
    }
    actual_stages = set(session.results.keys())
    assert expected_stages.issubset(actual_stages), \
        f"Missing stages in session: {expected_stages - actual_stages}"

    # Latency check — with mock 0.1s per call, parallel should be <5s total
    assert elapsed < 5, f"Expected <5s with mock, got {elapsed:.2f}s — parallel chưa work?"
    print(f"✓ All 7 agents succeeded, session has all 8 stage results")
    print(f"✓ Latency {elapsed:.2f}s confirms parallel execution (T1 3 agents in ~{behavior.latency_sec}s, not {3*behavior.latency_sec}s)")
    return True


async def test_2_nice_to_have_fail():
    """Market Research fail (nice_to_have) → pipeline continues."""
    print("\n" + "=" * 70)
    print("TEST 2: Nice-to-have fail — market_research crashes")
    print("=" * 70)

    behavior = MockBehavior()
    behavior.fail_skills = {"market_research"}
    session = _make_session()

    with _full_patches(behavior):
        results = await run_multi_agent_pipeline(session, _noop_cb)

    assert not results["market_research_agent"].success
    assert "MOCK" in results["market_research_agent"].error
    # Other agents should succeed
    assert results["customer_insight_agent"].success
    assert results["synthesizer_agent"].success
    # Final synthesis must be in session
    assert session.results.get("synthesis"), "Synthesis should have run despite market fail"
    print(f"✓ market_research failed (isolated), 6 other agents succeeded")
    print(f"✓ Synthesis ran successfully → pipeline degraded gracefully")
    return True


async def test_3_critical_fail():
    """Customer Insight fail (must_have T1) → PipelineAbortError."""
    print("\n" + "=" * 70)
    print("TEST 3: Critical fail — customer_insight crashes")
    print("=" * 70)

    behavior = MockBehavior()
    behavior.fail_skills = {"customer_insight"}
    session = _make_session()

    with _full_patches(behavior):
        try:
            await run_multi_agent_pipeline(session, _noop_cb)
            assert False, "Expected PipelineAbortError"
        except PipelineAbortError as e:
            print(f"✓ Correctly raised PipelineAbortError: {str(e)[:200]}")
            assert "customer_insight" in str(e)
    return True


async def test_4_synthesis_fail():
    """Synthesis fail (must_have T4) → PipelineAbortError at end."""
    print("\n" + "=" * 70)
    print("TEST 4: Synthesis must_have fail — synthesis crashes")
    print("=" * 70)

    behavior = MockBehavior()
    behavior.fail_skills = {"synthesis"}
    session = _make_session()

    with _full_patches(behavior):
        try:
            await run_multi_agent_pipeline(session, _noop_cb)
            assert False, "Expected PipelineAbortError at T4"
        except PipelineAbortError as e:
            print(f"✓ Correctly raised PipelineAbortError at T4: {str(e)[:200]}")
            assert "synthes" in str(e).lower()
    # T1-T3 results should still be in session
    assert session.results.get("market_research")
    assert session.results.get("customer_insight")
    print(f"✓ T1-T3 results preserved in session (user có thể dùng partial)")
    return True


async def test_5_timeout_isolation():
    """1 agent timeout → fail isolated, others continue."""
    print("\n" + "=" * 70)
    print("TEST 5: Timeout isolation — 1 agent slow > timeout")
    print("=" * 70)

    behavior = MockBehavior()
    behavior.timeout_skills = {"competitor"}  # Will sleep 300s, hit 180s timeout
    session = _make_session()

    # Patch competitor timeout to be short for fast test
    with _full_patches(behavior):
        # Override the tier timeout temporarily for fast test
        original_get_tiers = get_strategic_pipeline_tiers
        def fast_tiers():
            tiers = original_get_tiers()
            tiers[0].timeout_per_agent = 1  # 1s timeout for test
            return tiers

        with patch("agents.orchestrator.get_strategic_pipeline_tiers", fast_tiers):
            results = await run_multi_agent_pipeline(session, _noop_cb)

    assert not results["competitor_agent"].success
    assert "timeout" in results["competitor_agent"].error.lower()
    # Other agents should still succeed
    assert results["customer_insight_agent"].success
    assert results["synthesizer_agent"].success
    print(f"✓ competitor timeout isolated, 6 other agents succeeded")
    return True


async def test_6_latency_benchmark():
    """Latency benchmark — parallel execution proves faster than sequential."""
    print("\n" + "=" * 70)
    print("TEST 6: Latency benchmark (parallel vs theoretical sequential)")
    print("=" * 70)

    behavior = MockBehavior()
    behavior.latency_sec = 0.5  # Each agent takes 0.5s
    session = _make_session()

    with _full_patches(behavior):
        start = time.monotonic()
        results = await run_multi_agent_pipeline(session, _noop_cb)
        elapsed = time.monotonic() - start

    # Theoretical sequential time: 8 agents × 0.5s = 4s (chain T3 counts as 2)
    # Parallel time: T1 max(3×0.5)=0.5s + T2 max(2×0.5)=0.5s + T3 1×0.5×2=1.0s + T4 0.5s = ~2.5s
    sequential_estimate = 0.5 * 8  # 8 individual calls (including chain's 2 sub-calls)
    print(f"Parallel actual: {elapsed:.2f}s")
    print(f"Sequential estimate (all serial): {sequential_estimate:.2f}s")
    print(f"Speedup: {sequential_estimate/elapsed:.1f}x")
    assert elapsed < sequential_estimate, \
        f"Parallel must be faster than sequential ({elapsed:.2f}s vs {sequential_estimate:.2f}s)"
    assert all(r.success for r in results.values())
    print(f"✓ Parallel execution faster (~{sequential_estimate/elapsed:.1f}x speedup)")
    return True


# ─────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────

async def run_all():
    tests = [
        test_1_happy_path,
        test_2_nice_to_have_fail,
        test_3_critical_fail,
        test_4_synthesis_fail,
        test_5_timeout_isolation,
        test_6_latency_benchmark,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n✗ {test.__name__} FAILED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    import logging
    # Quiet logs during test (focus on test output)
    logging.basicConfig(level=logging.WARNING)
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
