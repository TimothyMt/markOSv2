"""
Max trên web — lõi hội thoại đặt cố vấn Max làm trung tâm.

Tái dùng đúng các primitive của bot:
  - agents.discovery.run_discovery_turn   → phỏng vấn dựng hồ sơ (intake)
  - tools.llm_router.call                 → Max trả lời cố vấn (đa nhà cung cấp)
  - webapp.business.run_agent             → Max kích hoạt phân tích/skill thật

Chỉ hoạt động khi có Supabase + 1 API key LLM (ANTHROPIC/OpenAI/Gemini). Không có
→ trả {"error": ...} và frontend hiển thị trạng thái chưa sẵn sàng.
"""
import logging

logger = logging.getLogger(__name__)

# Transcript hội thoại web (ephemeral, theo user). Intake dùng session.intake_history.
_chat_log: dict[int, list] = {}
_LOG_CAP = 24

MAX_SYSTEM = """Bạn là Max — Giám đốc Marketing (CMO) ảo của Marketing OS, cố vấn cho doanh nghiệp Việt.

Phong cách:
- Thẳng thắn, ấm áp, ngắn gọn, thực chiến (tư duy McKinsey nhưng nói đời thường).
- Trả lời tiếng Việt, 2–5 câu, không lan man, không markdown rườm rà.
- Luôn bám vào HỒ SƠ DOANH NGHIỆP được cung cấp; không bịa số liệu.
- Khi hợp lý, chủ động gợi ý ĐÚNG MỘT bước tiếp theo cụ thể (vd: chạy phân tích đối
  thủ, lập chiến lược, tạo nội dung) — diễn đạt tự nhiên, để hệ thống tự gắn nút.
- Nếu cần dữ liệu phân tích sâu, nói rõ "để em chạy phân tích" thay vì bịa kết quả.
"""


def _log(uid: int) -> list:
    return _chat_log.setdefault(uid, [])


def history(user_id) -> list:
    try:
        return _chat_log.get(int(user_id), [])
    except (TypeError, ValueError):
        return []


def _profile_complete(session) -> bool:
    from agents.discovery import REQUIRED_FIELDS
    p = session.profile
    filled = sum(1 for f in REQUIRED_FIELDS if getattr(p, f, None))
    # đủ "đủ dùng" khi có ngành/sản phẩm + ≥ 4/7 trường bắt buộc
    return bool(getattr(p, "product_service", None)) and filled >= 4


def _stage(session, skill_keys: set) -> str:
    if not _profile_complete(session):
        return "discovery"
    if not skill_keys:
        return "diagnosis"
    if "synthesis" not in skill_keys:
        return "strategy"
    return "execution"


def _suggestions(stage: str, skill_keys: set) -> list:
    """Next-best-action chips theo chặng hành trình."""
    if stage == "discovery":
        return []
    if stage == "diagnosis":
        return [
            {"label": "▶ Chạy phân tích toàn diện", "task": "full"},
            {"label": "🥊 Phân tích đối thủ", "task": "competitor"},
            {"label": "👤 Customer Insight", "task": "customer"},
        ]
    if stage == "strategy":
        return [
            {"label": "🎯 Lập chiến lược tổng hợp", "task": "strategy"},
            {"label": "⚖️ Chạy SWOT", "task": "swot"},
            {"label": "📄 Xem kết quả phân tích", "goto": "competitor"},
        ]
    # execution
    return [
        {"label": "✍️ Tạo nội dung", "goto": "content"},
        {"label": "🗓️ Lên lịch nội dung", "goto": "calendar"},
        {"label": "🎯 Xem chiến lược", "goto": "strategy"},
    ]


async def _skill_keys(uid: int) -> set:
    try:
        from storage.v2 import skill_runs
        runs = await skill_runs.list_skill_runs(uid, limit=30)
        return {r.get("skill_name") for r in runs if r.get("skill_name")}
    except Exception as e:
        logger.warning("chat._skill_keys failed: %s", e)
        return set()


async def _advisor_reply(session, uid: int) -> str:
    """Max trả lời cố vấn (profile đã đủ) — dùng llm_router với persona CMO."""
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError

    log = _log(uid)
    convo = "\n".join(
        f"{'Sếp' if m['role'] == 'user' else 'Max'}: {m['content']}" for m in log[-10:]
    ) or "(chưa có)"

    done = await _skill_keys(uid)
    done_str = ", ".join(sorted(done)) if done else "(chưa chạy phân tích nào)"

    user_block = (
        f"# HỒ SƠ DOANH NGHIỆP\n{session.profile.to_context_string()}\n\n"
        f"# PHÂN TÍCH ĐÃ CÓ\n{done_str}\n\n"
        f"# HỘI THOẠI GẦN ĐÂY\n{convo}\n\n"
        "Trả lời tin nhắn mới nhất của Sếp đúng vai Max (CMO), ngắn gọn 2–5 câu."
    )
    try:
        result = await router_call(
            task_type=TaskType.GENERIC_CREATIVE,
            system=MAX_SYSTEM,
            user=user_block,
            max_tokens=700,
        )
        return (result.get("output") or "").strip() or "Em chưa rõ ý Sếp, Sếp nói thêm giúp em nhé?"
    except AllProvidersFailedError as e:
        logger.error("advisor_reply: all providers failed: %s", e)
        return "Xin lỗi Sếp, hiện em chưa kết nối được tới mô hình AI. Sếp thử lại sau ít phút nhé."


async def chat_turn(user_id, message: str) -> dict:
    """Một lượt hội thoại với Max. Returns dict cho frontend."""
    from webapp import business as biz

    if not biz.available():
        return {"error": "Chưa cấu hình Supabase — Max chưa hoạt động trên web."}
    try:
        await biz.ensure_client()
    except Exception as e:
        return {"error": f"Không kết nối được Supabase: {e}"}

    uid = await biz.pick_user_id(user_id)
    if uid is None:
        return {"error": "Chưa có người dùng nào trong hệ thống."}

    from storage.session import get_session, save_session
    session = await get_session(uid)
    msg = (message or "").strip()
    log = _log(uid)
    if msg:
        log.append({"role": "user", "content": msg})

    if not _profile_complete(session):
        from agents.discovery import run_discovery_turn, apply_discovery_to_profile
        try:
            mode, payload = await run_discovery_turn(session, msg)
        except Exception as e:
            logger.exception("discovery turn failed")
            mode, payload = "question", None
        if mode == "complete":
            apply_discovery_to_profile(session, payload or {})
            await save_session(session)
            reply = ("Tuyệt vời! Em đã đủ thông tin về doanh nghiệp của Sếp. "
                     "Giờ em đề xuất chạy phân tích để chẩn đoán thị trường, đối thủ và khách hàng — "
                     "Sếp bấm nút bên dưới để em bắt đầu nhé.")
        else:
            await save_session(session)
            reply = payload or "Sếp kể em nghe về doanh nghiệp của mình nhé — bán gì, cho ai, mục tiêu sắp tới là gì?"
    else:
        reply = await _advisor_reply(session, uid)

    log.append({"role": "assistant", "content": reply})
    if len(log) > _LOG_CAP:
        del log[: len(log) - _LOG_CAP]

    skill_keys = await _skill_keys(uid)
    stage = _stage(session, skill_keys)
    return {
        "reply":           reply,
        "userId":          uid,
        "stage":           stage,
        "profileComplete": _profile_complete(session),
        "suggestions":     _suggestions(stage, skill_keys),
        "history":         log[-_LOG_CAP:],
    }
