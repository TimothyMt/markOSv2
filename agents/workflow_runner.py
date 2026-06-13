"""
Workflow Runner — executes multi-step task workflows.

Main entry point: run_write_content_workflow()
  Step 1: Linh (brand) generates brand_direction
  Step 2: Nam (content) runs post_write with brand_direction as context
  Step 3: Linh (brand) runs post_voice_check on Nam's draft (optional)
"""
import logging
from typing import Callable, Optional

import anthropic

from config import CLAUDE_HAIKU_MODEL, ANTHROPIC_API_KEY
from storage.models import Session

logger = logging.getLogger(__name__)

# Lazy Haiku client (same pattern as pipeline.py)
_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            api_key=ANTHROPIC_API_KEY,
            timeout=120.0,
            max_retries=1,
        )
    return _client


_BRAND_DIRECTION_SYSTEM = (
    "Bạn là brand strategist. Dựa vào profile business, tạo brand direction note ngắn "
    "(5 bullets) cho content writer. Output tiếng Việt."
)


def _build_brand_direction_fallback(session: Session) -> str:
    """Build a hardcoded fallback brand_direction from session profile."""
    p = session.profile
    lines = ["**Brand Direction (mặc định từ profile):**"]
    if p.business_name:
        lines.append(f"- Brand: {p.business_name}")
    if p.product_service:
        lines.append(f"- Sản phẩm/DV: {p.product_service}")
    if p.target_customer:
        lines.append(f"- Audience: {p.target_customer}")
    if p.primary_goal:
        lines.append(f"- Mục tiêu: {p.primary_goal}")
    if p.main_challenge:
        lines.append(f"- Thách thức: {p.main_challenge}")
    if p.industry:
        lines.append(f"- Ngành: {p.industry}")
    if len(lines) == 1:
        lines.append("- Chưa có thông tin business đủ — viết content tổng quát")
    return "\n".join(lines)


async def _get_brand_direction(session: Session) -> str:
    """Step 1: Generate brand_direction.

    Priority:
    1. Reuse session cached brand_direction
    2. Use BrandVoice from DB if exists
    3. Call Haiku to generate from profile
    4. Fallback to hardcoded from profile fields
    """
    from storage.workflow_errors import log_workflow_error

    # 1. Check session cache
    cached = session.get_latest_result("brand_direction")
    if cached:
        logger.info("[workflow] Reusing cached brand_direction for user=%s", session.user_id)
        return cached

    # 2. Check stored Brand Voice
    try:
        from storage import get_brand_voice
        bv = await get_brand_voice(session.user_id)
        if bv and not bv.is_empty():
            result = bv.to_prompt_block(max_chars=2000)
            session.add_result("brand_direction", result)
            logger.info("[workflow] brand_direction from BrandVoice DB for user=%s", session.user_id)
            return result
    except Exception as e:
        logger.warning("[workflow] BrandVoice fetch failed (non-fatal): %s", e)

    # 3. Haiku call to generate brand direction
    p = session.profile
    strategy = session.get_latest_result("synthesis") or session.get_latest_result("strategy") or ""
    playbook = session.get_latest_result("tactical_playbook") or ""

    profile_block = p.to_context_string()
    user_content = profile_block
    if strategy:
        user_content += f"\n\n---\n\nMarketing Strategy (tóm tắt):\n{strategy[:2000]}"
    if playbook:
        user_content += f"\n\n---\n\nTactical Playbook (copy mẫu + tone tham chiếu):\n{playbook[:1500]}"

    try:
        client = _get_client()
        response = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=500,
            system=[{"type": "text", "text": _BRAND_DIRECTION_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_content}],
        )
        result = response.content[0].text.strip()
        session.add_result("brand_direction", result)
        logger.info("[workflow] brand_direction generated via Haiku for user=%s", session.user_id)
        return result

    except Exception as e:
        logger.error("[workflow] Haiku brand_direction failed for user=%s: %s", session.user_id, e)
        await log_workflow_error(
            user_id=session.user_id,
            task_type="write_content",
            step_index=0,
            skill_name="brand_direction",
            error_msg=e,
        )

    # 4. Hardcoded fallback
    result = _build_brand_direction_fallback(session)
    session.add_result("brand_direction", result)
    logger.info("[workflow] brand_direction using hardcoded fallback for user=%s", session.user_id)
    return result


async def run_write_content_workflow(
    session: Session,
    topic: str,
    date_channel: str = "",
    audience: str = "",
    on_progress: Optional[Callable] = None,
) -> dict:
    """Execute the write_content workflow: Linh → Nam → Linh.

    Returns:
        {
            "success": bool,
            "final_output": str,
            "steps": dict,
        }
    """
    from agents.pipeline import run_operational_skill
    from storage.workflow_errors import log_workflow_error

    steps_results: dict = {}

    # ── Step 1: Linh generates brand_direction ────────────────────
    if on_progress:
        try:
            await on_progress("🎨 *Linh đang phân tích brand direction...*")
        except Exception:
            pass

    brand_direction = await _get_brand_direction(session)
    steps_results["brand_direction"] = brand_direction

    # ── Step 2: Nam runs post_write ───────────────────────────────
    if on_progress:
        try:
            await on_progress("✍️ *Nam đang viết content...*")
        except Exception:
            pass

    # Inject intake fields for post_write
    session.pending_intake["topic"] = topic
    session.pending_intake["date_channel"] = date_channel or "Hôm nay — Facebook"
    session.pending_intake["pillar_funnel"] = "Educate / TOFU"
    session.pending_intake["audience"] = audience or (session.profile.target_customer or "")
    session.pending_intake["_workflow_context"] = brand_direction

    try:
        post_write_output = await run_operational_skill("post_write", session)
        steps_results["post_write"] = post_write_output
    except Exception as e:
        logger.error("[workflow] post_write failed for user=%s: %s", session.user_id, e)
        await log_workflow_error(
            user_id=session.user_id,
            task_type="write_content",
            step_index=1,
            skill_name="post_write",
            error_msg=e,
        )
        return {
            "success": False,
            "error": str(e)[:200],
            "final_output": "",
            "steps": steps_results,
        }

    # ── Step 3: Linh runs post_voice_check (optional) ────────────
    if on_progress:
        try:
            await on_progress("🔍 *Linh đang kiểm tra brand voice...*")
        except Exception:
            pass

    session.pending_intake["draft_post"] = post_write_output[:3000]
    session.pending_intake["brand_voice_rules"] = brand_direction[:1500]

    try:
        voice_check_output = await run_operational_skill("post_voice_check", session)
        steps_results["post_voice_check"] = voice_check_output
        final_output = voice_check_output
    except Exception as e:
        logger.warning(
            "[workflow] post_voice_check failed (optional, skipping) for user=%s: %s",
            session.user_id, e,
        )
        await log_workflow_error(
            user_id=session.user_id,
            task_type="write_content",
            step_index=2,
            skill_name="post_voice_check",
            error_msg=e,
        )
        # Step is optional — use post_write output as final
        final_output = post_write_output

    return {
        "success": True,
        "final_output": final_output,
        "steps": steps_results,
    }
