"""
Max Conductor — CMO-level intent router (Claude Haiku).

Routes user messages to task workflows. Currently supports:
  - write_content: Linh → Nam → Linh pipeline

Returns a routing dict with task, params, and clarification flags.
"""
import logging
import json
import re
from typing import Optional

import anthropic

from config import CLAUDE_HAIKU_MODEL, ANTHROPIC_API_KEY
from storage.models import Session

logger = logging.getLogger(__name__)

# Module-level lazy singleton (same pattern as pipeline.py line 60)
_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            api_key=ANTHROPIC_API_KEY,
            timeout=60.0,
            max_retries=1,
        )
    return _client


_ROUTER_SYSTEM = """Bạn là Max — CMO của một marketing agency. Nhiệm vụ của bạn là phân tích intent của user và route đến workflow phù hợp.

Hiện tại chỉ hỗ trợ 1 task: "write_content" (viết content/bài đăng).

Phân tích tin nhắn và trả về JSON:
{
  "task": "write_content" hoặc null,
  "params": {
    "topic": "chủ đề viết (trích từ tin nhắn hoặc null)",
    "date_channel": "ngày/kênh đăng (vd: 'Hôm nay — Facebook') hoặc null",
    "audience": "đối tượng cụ thể nếu user mention, hoặc null"
  },
  "needs_clarification": true/false,
  "clarification_question": "câu hỏi tiếng Việt nếu cần làm rõ, hoặc null"
}

Quy tắc:
- Nếu user rõ ràng muốn viết content/bài đăng → task = "write_content"
- Nếu topic đã rõ trong tin nhắn → điền vào params.topic
- Nếu không rõ intent hoặc không liên quan viết content → task = null, needs_clarification = true
- Chỉ trả về JSON thuần, không thêm text ngoài JSON"""


async def route_intent(user_msg: str, session: Session) -> dict:
    """Route user intent to a task workflow.

    Returns dict:
    {
        "task": "write_content" | null,
        "params": {"topic": str, "date_channel": str, "audience": str},
        "needs_clarification": bool,
        "clarification_question": str | null,
    }
    """
    _fallback = {
        "task": None,
        "params": {"topic": None, "date_channel": None, "audience": None},
        "needs_clarification": True,
        "clarification_question": "Sếp muốn em hỗ trợ gì ạ? Sếp có thể mô tả cụ thể hơn không?",
    }

    try:
        client = _get_client()
        response = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=300,
            system=[{"type": "text", "text": _ROUTER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()

        # Extract JSON (handle markdown code blocks if present)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

        data = json.loads(raw)

        # Normalize
        task = data.get("task")
        if task not in ("write_content",):
            task = None

        params = data.get("params") or {}
        return {
            "task": task,
            "params": {
                "topic": params.get("topic") or None,
                "date_channel": params.get("date_channel") or None,
                "audience": params.get("audience") or None,
            },
            "needs_clarification": bool(data.get("needs_clarification", task is None)),
            "clarification_question": data.get("clarification_question") or None,
        }

    except Exception as e:
        logger.warning("max_conductor.route_intent failed (user=%s): %s", session.user_id, e)
        return _fallback
