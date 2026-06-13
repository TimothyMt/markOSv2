"""
Telegram bot message and callback handlers.
All storage calls are async (asyncpg-backed).
"""
import asyncio
import functools
import logging
import re
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from telegram.error import TimedOut, NetworkError

from storage import get_session, save_session, reset_session
from storage.models import PipelineStage
from agents.pipeline import run_intake, run_targeted_pipeline, run_operational_skill, run_multi_agent_targeted
from agents.prompts import TASK_OPENING_QUESTIONS
from agents.task_registry import OPERATIONAL_TASKS, get_task, needs_intake
from frameworks.kpi_library import KPI_LIBRARY
from frameworks.industry_context import suggest_key_message_hint
from bot.keyboards import (
    MAIN_MENU_KEYBOARD,
    QUICK_MENU_KEYBOARD,
    TASK_SELECT_KEYBOARD,
    CONFIRM_KEYBOARD,
    BIZNAME_SKIP_KEYBOARD,
    stage_done_keyboard,
    get_action_keyboard,
    ASK_FOLLOWUP_KEYBOARD,
    ADS_COPY_TIER_KEYBOARD,
    VIDEO_CREATOR_KEYBOARD,
    LANG_LEVEL_KEYBOARD,
    RATING_KEYBOARD,
    REGEN_PROMPT_KEYBOARD,
    FEEDBACK_PROMPT_KEYBOARD,
    CALENDAR_TO_CONTENT_GEN_KEYBOARD,
    CONTENT_TYPE_SCOPE_KEYBOARD,
    FUNNEL_APPROVE_KEYBOARD,
    ADS_FORMAT_KEYBOARD,
    IMAGE_REFERENCE_KEYBOARD,
    IMAGE_GEN_PROMPT_KEYBOARD,
    IMAGE_SIZE_KEYBOARD,
    IMAGE_REVIEW_KEYBOARD,
    NEEDS_STRATEGY_KEYBOARD,
    MONITOR_PROMPT_KEYBOARD,
    MONITOR_INTERVAL_KEYBOARD,
    POST_AZ_CAMPAIGN_KEYBOARD,
    CONFIRM_STRATEGY_KEYBOARD,
    CONFIRM_STRATEGY_TO_CAMPAIGN_KEYBOARD,
    CONFIRM_BRIEF_KEYBOARD,
    CAMPAIGN_OPTION_KEYBOARD,
    CAMPAIGN_IDEA_CONFIRM_KEYBOARD,
    OFFER_LEVER_KEYBOARD,
    BRAND_VOICE_PROMPT_KEYBOARD,
    BV_DRAFT_APPROVE_KEYBOARD,
    XLSX_EDIT_KEYBOARD,
    USP_ANALYZE_KEYBOARD,
    LINH_BV_EXISTS_KEYBOARD,
    LINH_BV_NEW_KEYBOARD,
    NAM_MODE_KEYBOARD,
    TRANG_MODE_KEYBOARD,
    GROWTH_CHANNEL_KEYBOARD,
)


# Sprint 5: Creative ops skills cần Brand Voice — lazy trigger gate
BRAND_VOICE_GATED_SKILLS = {
    "post_write", "post_adapt", "post_batch", "post_hooks",
    "ads_generator", "ads_copy", "video_scripts",
    "sales_inbox_script", "email_zalo_sequence", "content_repurpose",
    "content_generator", "video_script_gen", "ugc_brief",
}

logger = logging.getLogger(__name__)

# Support contact — cập nhật khi có thông tin chính thức
SUPPORT_CONTACT = "Telegram: @Timothy0072 | Zalo: 0943188162"
SUPPORT_NOTE = f"📸 Nếu thấy lỗi, chụp màn hình và gửi cho support:\n{SUPPORT_CONTACT}"

STAGE_HEADERS = {
    "market_research": "📊 NGHIÊN CỨU THỊ TRƯỜNG (TAM/SAM/SOM)",
    "competitor":      "🕵️ PHÂN TÍCH ĐỐI THỦ CẠNH TRANH",
    "customer_insight":"👥 CUSTOMER INSIGHT & ICP",
    "psychology_pricing": "💡 MARKETING PSYCHOLOGY & PRICING STRATEGY",
    "social_listening":"📡 SOCIAL LISTENING SYSTEM",
    "synthesis":       "🚀 MARKETING STRATEGY TỔNG HỢP",
}

TASK_LABELS = {
    "full":       "Nghiên Cứu & Phân Tích Thị Trường",
    "market":     "Nghiên cứu thị trường",
    "competitor": "Phân tích đối thủ",
    "customer":   "Customer Insight & ICP",
    "pricing":    "Pricing Strategy",
    "social":     "Social Listening",
    "strategy":   "Kế Hoạch Đề Xuất",
    "swot":       "SWOT Analysis",
    "tactical_playbook": "Tactical Playbook",
}

TASK_PIPELINE_STEPS = {
    "full":       "1️⃣ Thị trường · 2️⃣ Đối thủ · 3️⃣ Customer · 4️⃣ Psychology & Pricing · 5️⃣ USP → Sếp chọn hướng → Kế hoạch chiến lược",
    "market":     "📊 Phân tích TAM/SAM/SOM + market dynamics",
    "competitor": "🕵️ Landscape đối thủ + market gap analysis",
    "customer":   "👥 ICP profile + Jobs-to-be-Done + Customer Journey",
    "pricing":    "💰 Pricing model + psychology tactics + revenue optimization",
    # "social":  "📡 Keyword clusters + monitoring routine + crisis thresholds",  # tạm tắt
    "strategy":   "🎯 SAVE Framework + SMART Goals + 90-day Roadmap",
    "swot":       "⚖️ SWOT 4 ô + chiến lược SO/WO/ST/WT",
    "tactical_playbook": "📕 Đào sâu kế hoạch chiến lược thành tactics thực thi từng kênh",
}

TASK_STAGE_COUNT = {
    # Research pipeline (phase=research): market + competitor + customer + usp_definition + psychology_pricing + SWOT
    # Synthesis + Tactical Playbook (phase=synthesis) chạy sau khi user trả lời 8 câu chiến lược — không đếm ở đây
    "full": 6,
    "market": 1,
    "competitor": 1,
    "customer": 1,
    "pricing": 1,
    # "social": 1,  # tạm tắt
    "strategy": 1,
    "swot": 1,
    "tactical_playbook": 1,
}

WELCOME_MESSAGE = """Em là *Max*, trợ lý marketing của sếp.

Em hỗ trợ sếp 3 mảng chính:

🎯 *Chiến Lược* — Phân tích thị trường, đối thủ, khách hàng, định giá, lập kế hoạch
⚙️ *Sản Xuất* — Brief campaign, lịch nội dung, viết quảng cáo, kịch bản video, website, kịch bản sales, chăm sóc khách
📊 *Theo Dõi & Báo Cáo* — Theo dõi đối thủ, báo cáo ads

─────────────────────────
*Hôm nay sếp muốn em xử lý phần nào ạ?*"""

# First-time language preference setup (Sprint 1)
LANG_SETUP_MESSAGE = """Em chào sếp! Trước khi vào việc, em hỏi nhanh 1 ý ạ:

*Khả năng tiếng Anh của sếp thế nào* để em biết cách trình bày output cho phù hợp?

🔴 *Không rành* — Em dùng thuần Việt toàn bộ, kể cả thuật ngữ
🟡 *Hiểu cơ bản* — Em dùng thuật ngữ EN nhưng kèm giải thích trong ngoặc
🟢 *Thông thạo* — Em dùng thuật ngữ EN tự nhiên, không cần giải thích

_(Sếp đổi lại bất kỳ lúc nào bằng /settings)_"""

HELP_MESSAGE = """*Marketing OS — Hướng dẫn sử dụng*

/start    — Mở menu chính (GIỮ data, không reset)
/reset    — Xoá toàn bộ data, bắt đầu phân tích mới
/settings — Đổi mức độ tiếng Anh trong output
/help     — Hiển thị hướng dẫn này

*Cách sử dụng*:
1. Chọn task sếp muốn em thực hiện
2. Trả lời các câu hỏi / paste form
3. Nhận card tóm tắt + file đầy đủ
4. Đánh giá output → em note lại để cải thiện

*Mẹo*: Chạy *Nghiên Cứu & Phân Tích Thị Trường* trước → các task sau (Brief Campaign, Content Calendar) sẽ tự động dùng Strategy đó làm base.

*Thời gian*: 30-60s task đơn, 3-5p phân tích toàn diện."""


def _strip_code_fences(text: str) -> str:
    """Remove ``` fences — Telegram renders them as ugly gray code blocks with copy button."""
    # Remove opening fence (optionally with language): ```python\n or ```\n
    text = re.sub(r"```[a-zA-Z]*\s*\n?", "", text)
    # Remove any remaining closing fences
    return text.replace("```", "")


# Per-user lock map — chống race khi user spam click với concurrent_updates=True.
# Lock được tạo lazy, giữ trong dict module-level. Memory ~1KB/user, không cần evict
# trong scope hiện tại (small user base). Nếu scale lớn → wrap bằng LRU cache.
_user_locks: dict[int, asyncio.Lock] = {}


def _get_user_lock(user_id: int) -> asyncio.Lock:
    lock = _user_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _user_locks[user_id] = lock
    return lock


def with_user_lock(handler):
    """Decorator: serialize đồng thời 2 update của cùng 1 user. Updates của user khác
    vẫn chạy song song (vì PTB concurrent_updates=True)."""
    @functools.wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None and update.callback_query:
            user = update.callback_query.from_user
        if user is None:
            return await handler(update, context)
        async with _get_user_lock(user.id):
            return await handler(update, context)
    return wrapped


async def _safe_reply(message: Message, text: str, **kwargs):
    """Reply with markdown; fallback to plain text if Telegram parser fails.
    Also strips ``` code fences which render ugly in Telegram."""
    text = _strip_code_fences(text)
    try:
        await message.reply_text(text, **kwargs)
    except Exception as e:
        # Markdown parse error (unbalanced *, _, [, etc.) — strip parse_mode and retry.
        # Note: in PTB 22+, BadRequest is a subclass of NetworkError, so check message first.
        if "parse" in str(e).lower() or "entities" in str(e).lower():
            logger.warning("Markdown parse failed (%s) — sending as plain text", e)
            kwargs_plain = {k: v for k, v in kwargs.items() if k != "parse_mode"}
            try:
                await message.reply_text(text, **kwargs_plain)
            except Exception as e2:
                logger.warning("Plain text fallback also failed (%s) — swallowing", e2)
        else:
            raise


async def send_long_message(message: Message, text: str, **kwargs):
    """Split messages exceeding Telegram's 4096-char limit. Safe markdown fallback."""
    MAX_LEN = 4000
    if len(text) <= MAX_LEN:
        await _safe_reply(message, text, **kwargs)
        return

    chunks, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > MAX_LEN:
            if current:
                chunks.append(current)
            current = line
        else:
            current = (current + "\n" + line) if current else line
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        kw = kwargs if i == len(chunks) - 1 else {k: v for k, v in kwargs.items() if k != "reply_markup"}
        await _safe_reply(message, chunk, **kw)
        await asyncio.sleep(0.3)


# ─── Commands ────────────────────────────────────────────────────

@with_user_lock
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu. GIỮ NGUYÊN session (profile, results, feedback, preferences).
    First-time user (no name) → hỏi tên TRƯỚC, sau đó ngôn ngữ.
    Dùng /reset nếu muốn xoá business data.
    """
    user_id = update.effective_user.id
    session = await get_session(user_id)

    # Clear any in-flight markers (awaiting feedback/rating/edit) — user vừa /start là muốn về menu
    transient_keys = [
        "_awaiting_feedback_for", "_awaiting_rating_for", "_awaiting_followup_for",
        "_awaiting_image_edit", "_awaiting_image_reference",
        "_pending_regen_skill", "_pending_feedback",
        "_monitor_pending_page_id", "_monitor_pending_page_name",
        "_last_image_b64", "_last_image_size", "_img_prompt", "_img_n",
        "_advisor_mode", "_awaiting_calendar_edit", "_awaiting_bp_edit", "_awaiting_week_selection",
        "_awaiting_calendar_cadence", "_awaiting_budget_team", "_budget_team_pending_confirm",
        "_content_gen_weekly_mode", "_content_gen_week",
        "_content_channels_remaining", "_content_gen_mode", "channel_focus",
        "_bv_draft", "_bv_resume_weekly",
        "_bv_edit_mode", "_growth_skill",
    ]
    for k in transient_keys:
        session.pending_intake.pop(k, None)

    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)

    # FIRST-TIME — hỏi tên trước
    if not session.preferences.get("user_name"):
        session.pending_intake["_awaiting_user_name"] = "1"
        await save_session(session)
        await update.message.reply_text(
            "👋 *Em là Max — AI CMO của sếp.*\n\n"
            "Trước khi vào việc, sếp gõ tên để em biết gọi sếp thế nào ạ?\n\n"
            "_Vd: \"Nhiên\" / \"Anh Minh\" / \"Founder Lily\"_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # FIRST-TIME (đã có tên) — hỏi ngôn ngữ
    if not session.preferences.get("en_level"):
        name = session.preferences.get("user_name", "")
        msg = LANG_SETUP_MESSAGE.replace("Em chào sếp!", f"Em chào sếp {name}!" if name else "Em chào sếp!")
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=LANG_LEVEL_KEYBOARD,
        )
        return

    # Returning user → vào menu chính, hiển thị status nếu có data
    welcome = WELCOME_MESSAGE
    status_lines = []
    if session.profile.business_name:
        status_lines.append(f"🏢 Business: *{session.profile.business_name}*")
    if session.has_result("synthesis") or session.has_result("strategy"):
        status_lines.append("✅ Đã có Marketing Strategy")
    elif session.has_result("market_research") or session.has_result("competitor"):
        status_lines.append("⚙️ Đã chạy 1 vài bước phân tích")
    if status_lines:
        welcome = "\n".join(status_lines) + "\n\n─────────────────────────\n\n" + welcome

    welcome = _personalize(welcome, session)
    await _safe_reply(
        update.message,
        welcome,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU_KEYBOARD,
    )
    # Persistent quick-menu (góc dưới khung chat) — gửi riêng vì 1 message chỉ
    # nhận 1 reply_markup, và inline keyboard ở trên đã chiếm slot đó.
    await update.message.reply_text(
        "💡 Menu nhanh luôn sẵn ở dưới khung chat 👇",
        reply_markup=QUICK_MENU_KEYBOARD,
    )


@with_user_lock
async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/settings — config cho Max: Tên / Token / Ngôn ngữ."""
    user_id = update.effective_user.id
    session = await get_session(user_id)
    current = session.preferences.get("en_level", "moderate")
    name = session.preferences.get("user_name", "")
    label_map = {"none": "🔴 Không rành", "moderate": "🟡 Hiểu cơ bản", "fluent": "🟢 Thông thạo"}

    # Token info (real tracking)
    from tools.token_tracker import usage_summary, is_low
    token_line = usage_summary(session)
    low_warning = "\n⚠️ _Token gần hết, sếp liên hệ admin để nạp thêm._" if is_low(session) else ""

    name_line = f"👤 *Tên em đang gọi:* {name}" if name else "👤 *Tên:* chưa đặt"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Đổi tên",            callback_data="settings_change_name")],
        [InlineKeyboardButton("🔤 Đổi mức tiếng Anh",   callback_data="settings_change_lang")],
        [InlineKeyboardButton("💎 Xem chi tiết token",  callback_data="settings_tokens")],
    ])
    await update.message.reply_text(
        f"⚙️ *Cài đặt Max của sếp*\n\n"
        f"{name_line}\n"
        f"🔤 *Ngôn ngữ:* {label_map.get(current, '🟡')}\n"
        f"💎 *Token usage:* {token_line}{low_warning}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )


@with_user_lock
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset business data. GIỮ tên + ngôn ngữ (preferences) gắn với User ID."""
    user_id = update.effective_user.id

    # Preserve preferences (name, en_level, future token balance)
    old_session = await get_session(user_id)
    preserved_prefs = dict(old_session.preferences) if old_session.preferences else {}

    await reset_session(user_id)
    # Build a fresh Session locally instead of re-reading. A re-read right after
    # reset could resurrect stale profile data (e.g. via a V2-read fallback to a
    # leftover V1 row), which save_session would then persist back as industry_cached.
    from storage.models import Session
    session = Session(user_id=user_id)
    session.preferences = preserved_prefs
    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)

    name = preserved_prefs.get("user_name", "")
    name_part = f" sếp {name}" if name else ""
    await update.message.reply_text(
        f"✅ *Đã xoá business data{name_part}!*\n\n"
        f"_Profile, kết quả, feedback đã clean. Tên + ngôn ngữ của sếp được giữ nguyên._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=MAIN_MENU_KEYBOARD,
    )


@with_user_lock
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.MARKDOWN)


@with_user_lock
async def cmd_dbg_funnel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """DEBUG: chạy lại Funnel Map trên session hiện tại, không cần đi lại
    flow brief. Gõ /dbgfunnel ở bất kỳ đâu."""
    session = await get_session(update.effective_user.id)
    campaign_name = (session.pending_intake.get("campaign_name")
                     or session.pending_intake.get("current_campaign") or "Campaign")
    campaign_goal = (session.pending_intake.get("campaign_goal")
                     or session.profile.primary_goal or "")
    await update.message.reply_text(
        f"🧪 *Debug: chạy lại Funnel Map cho \"{campaign_name}\"...*",
        parse_mode=ParseMode.MARKDOWN,
    )
    funnel_ok = await _gen_and_show_funnel_map(
        update.message, session, context, update, campaign_name, campaign_goal,
    )
    prompt = (
        "👆 *Funnel Map (debug re-run) — tóm tắt trên + file HTML + Excel.*\n\n"
        if funnel_ok else
        "_(Debug: chưa dựng được funnel map chi tiết.)_\n\n"
    )
    await _emit_funnel_approve_prompt(update.message, session, prompt)


# ─── Main message handler ─────────────────────────────────────────

@with_user_lock
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    session = await get_session(user_id)

    # Refine mode: user vừa gõ yêu cầu chỉnh sửa tự do cho 1 phân tích đã có sẵn
    # (xem nhánh "REFINABLE_STRATEGIC" trong handle_callback) — cập nhật trên bản
    # cũ qua injection riêng "_refine_request" (chỉ dẫn AI giữ nguyên phần không
    # liên quan, chỉ sửa đúng phần được yêu cầu — khác với regen toàn bộ).
    refine_target = session.pending_intake.get("_awaiting_refine_for")
    if refine_target:
        session.pending_intake.pop("_awaiting_refine_for", None)
        session.pending_intake["_refine_request"] = text
        session.selected_task = refine_target
        await save_session(session)

        await update.message.reply_text(
            "🔧 Em đang cập nhật bản phân tích theo đúng yêu cầu của sếp...",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            from agents.pipeline import run_strategic_single_skill
            from config import AGENT_TIMEOUT
            result = await asyncio.wait_for(
                run_strategic_single_skill(refine_target, session),
                timeout=AGENT_TIMEOUT,
            )
            session.pending_intake.pop("_refine_request", None)
            session.stage = PipelineStage.TASK_SELECT
            await save_session(session)
            await _send_ops_result(update.message, session, refine_target, result)
        except Exception as e:
            logger.exception("Refine run failed: %s", e)
            await update.message.reply_text(f"⚠️ Cập nhật gặp lỗi: {str(e)[:200]}")
        return

    # Quick-menu (persistent reply keyboard) — bấm nút gửi về plain text trùng label
    if text == "▶️ Tiếp tục":
        synthesis = (session.get_latest_result("synthesis") or "").strip()
        if synthesis and not session.pending_intake.get("_extracted_campaigns"):
            await _show_extracted_campaigns(update.message, session)
        else:
            await update.message.reply_text(
                "Sếp gõ /start để xem các lựa chọn tiếp theo nhé ạ 👇",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
        return
    if text == "🛍 Dịch vụ":
        await update.message.reply_text(
            "Đây là các dịch vụ Max có thể giúp sếp 👇",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return
    if text == "💬 Hỗ trợ":
        await update.message.reply_text(
            "Sếp cần hỗ trợ gì cứ nhắn trực tiếp ở đây — em chuyển admin xử lý sớm nhất ạ 🙏\n\n"
            "_Xem hướng dẫn nhanh qua /help_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    if text == "👛 Ví token":
        from tools.token_tracker import get_used, get_remaining, get_quota, fmt, is_low, is_exhausted
        used, remaining, quota = get_used(session), get_remaining(session), get_quota(session)
        pct_used = (used / quota * 100) if quota else 0
        status_emoji = "🔴" if is_exhausted(session) else "🟡" if is_low(session) else "🟢"
        await update.message.reply_text(
            f"👛 *Ví token của sếp*\n\n"
            f"{status_emoji} Quota: *{fmt(quota)}*\n"
            f"📉 Đã dùng: *{fmt(used)}* ({pct_used:.1f}%)\n"
            f"📊 Còn lại: *{fmt(remaining)}*\n\n"
            f"_Xem chi tiết & lịch sử qua /settings_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # NEW: First-time name capture
    if session.pending_intake.get("_awaiting_user_name"):
        raw = text.strip()
        # Strip common prefixes trước khi validate
        cleaned = raw
        for prefix in ("em là ", "tớ là ", "tôi là ", "mình là ", "anh ", "chị ", "tên ", "gọi "):
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break

        valid, error_msg = _validate_user_name(cleaned)
        if valid:
            session.preferences["user_name"] = cleaned
            session.pending_intake.pop("_awaiting_user_name", None)
            await save_session(session)

            # Nếu chưa có en_level → hỏi tiếp ngôn ngữ
            if not session.preferences.get("en_level"):
                await update.message.reply_text(
                    f"✨ *Em chào sếp {cleaned}!*\n\n"
                    f"Em hỏi nhanh thêm 1 ý nữa ạ:\n\n"
                    f"*Khả năng tiếng Anh của sếp thế nào* để em biết cách trình bày output cho phù hợp?\n\n"
                    f"🔴 *Không rành* — Em dùng thuần Việt toàn bộ\n"
                    f"🟡 *Hiểu cơ bản* — Em dùng thuật ngữ EN kèm giải thích\n"
                    f"🟢 *Thông thạo* — Em dùng EN tự nhiên",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=LANG_LEVEL_KEYBOARD,
                )
            else:
                # Đã có lang rồi → vào menu thẳng
                await update.message.reply_text(
                    f"✨ *Em chào sếp {cleaned}!*\n\n"
                    f"Em đã ghi nhớ tên — đổi bất kỳ lúc nào qua /settings.\n\n"
                    f"Giờ vào việc thôi sếp {cleaned}! 👇",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=MAIN_MENU_KEYBOARD,
                )
        else:
            await update.message.reply_text(
                f"⚠️ {error_msg}\n\n"
                f"_Sếp gõ lại 1 tên hợp lệ nhé. Vd: 'Nhiên' / 'Anh Minh' / 'Founder Lily'._",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    # ─── Secret Paste Detector ───────────────────────────────────────
    # User có thể paste FB token / API key vào chat (sau khi đọc gate
    # message). KHÔNG được route vào advisor (sẽ lộ secret trong log
    # và user confused). Detect → từ chối + hướng dẫn đúng cách.
    _stripped = text.strip()
    _looks_like_fb_token = (
        _stripped.startswith("EAA")
        and len(_stripped) > 100
        and " " not in _stripped
        and "\n" not in _stripped
    )
    _looks_like_long_key = (
        len(_stripped) > 80
        and " " not in _stripped
        and "\n" not in _stripped
        and sum(1 for c in _stripped if c.isalnum()) > len(_stripped) * 0.9
    )
    if _looks_like_fb_token or _looks_like_long_key:
        logger.warning(
            "User %d pasted what looks like a secret (len=%d, prefix=%s...) — refusing",
            session.user_id, len(_stripped), _stripped[:6],
        )
        try:
            # Best-effort: delete the message containing the secret
            await update.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "🛡️ *Em đã xoá tin nhắn vừa rồi — trông giống API token/secret.*\n\n"
                "⚠️ KHÔNG paste token vào chat:\n"
                "• Telegram lưu lại toàn bộ history\n"
                "• Token có thể bị log lại bên server\n"
                "• Bot không có cách dùng token gửi qua chat\n\n"
                "*Cách đúng:* Admin set env var trên Railway dashboard "
                "(Service → Variables → New Variable → `FB_ACCESS_TOKEN`).\n\n"
                "_Nếu token này đã lộ → vào https://developers.facebook.com/tools/debug/accesstoken/ để revoke + tạo mới._"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ─── Universal Greeting Intercept ────────────────────────────────
    # Returning user (đã có business_name) gõ greeting → show menu ngay,
    # KHÔNG rơi vào intake/followup/advisor để tránh bot hỏi lại info đã có.
    _GREETING_KEYWORDS = (
        "max ơi", "max", "ơi", "hello", "hi", "chào",
        "hey", "xin chào", "helo", "hii", "alo", "yo", "sup", "hola",
    )
    # iOS/macOS Telegram often sends Vietnamese diacritics in NFD form;
    # keywords above are NFC. Normalize so byte comparison matches.
    import unicodedata as _ud
    _t = _ud.normalize("NFC", text).lower().strip()
    _is_greeting = (
        len(_t) <= 25
        and (
            _t in _GREETING_KEYWORDS
            or any(
                _t == kw or _t.startswith(kw + " ") or _t.startswith(kw + ",")
                or _t.startswith(kw + "!") or _t.startswith(kw + "?")
                for kw in _GREETING_KEYWORDS
            )
        )
    )
    # Returning user heuristic: bất kỳ field profile nào có data → coi như đã có context
    _p = session.profile
    _has_any_profile = bool(
        _p.business_name or _p.product_service or _p.industry
        or _p.target_customer or _p.primary_goal or _p.main_challenge
    )
    _has_any_results = bool(session.results)
    _has_onboarded = bool(_get_user_name(session))
    _is_returning_user = _has_any_profile or _has_any_results or _has_onboarded

    # Special-flow flags: only block greeting for brand-new users mid-onboarding.
    # For returning users, greeting = intent to reset → always show menu and
    # clear any stale flags from abandoned flows.
    _STUCK_FLAGS = (
        "_post_editing", "_awaiting_image_edit", "_awaiting_campaign_idea",
        "_awaiting_campaign_finalize", "_awaiting_image_reference",
        "_workflow_awaiting_topic", "_workflow_task",
        OPS_INTAKE_AWAITING, "_awaiting_followup_for", "_advisor_mode",
        BIZ_CONTEXT_AWAITING, BIZ_CONTEXT_PENDING_SKILL,
        "_awaiting_feedback_for", "_awaiting_rating_for", "_pending_regen_skill",
        "_awaiting_campaign_setup",
        "_awaiting_campaign_needs",
        "_awaiting_offer_prefs",
        "_awaiting_usp_text",
        "_awaiting_strategy_q_custom",
        "_bv_edit_mode",
    )
    _stuck_now = [k for k in _STUCK_FLAGS if session.pending_intake.get(k)]
    _tone_stuck = session.tone_calibration.get("stage") in ("checking_tone", "waiting_feedback")
    _in_special_flow = bool(_stuck_now) or _tone_stuck

    if _is_greeting:
        logger.info(
            "Greeting detected (user=%d) | stage=%s | returning=%s | in_special=%s | stuck_flags=%s | tone_stuck=%s | results_keys=%s",
            session.user_id, session.stage.value, _is_returning_user,
            _in_special_flow, _stuck_now, _tone_stuck,
            list(session.results.keys())[:5],
        )

    # Returning user greeting → always intercept (clear stuck flags, show menu).
    # New user greeting → only intercept if not mid-onboarding.
    if _is_greeting and (_is_returning_user or not _in_special_flow):
        if not _is_returning_user:
            # Brand-new user greeted before /start → start onboarding
            if not session.pending_intake.get("_awaiting_user_name"):
                session.pending_intake["_awaiting_user_name"] = "1"
                session.stage = PipelineStage.TASK_SELECT
                await save_session(session)
                await update.message.reply_text(
                    "👋 *Em là Max — AI CMO của sếp.*\n\n"
                    "Sếp gõ tên để em biết gọi sếp thế nào ạ?\n\n"
                    "_Vd: \"Nhiên\" / \"Anh Minh\" / \"Founder Lily\"_",
                    parse_mode=ParseMode.MARKDOWN,
                )
            return

        # Returning user — clear ALL stuck flags + tone state, reset stage, show menu.
        if session.stage not in (PipelineStage.IDLE, PipelineStage.TASK_SELECT, PipelineStage.COMPLETE):
            session.stage = PipelineStage.IDLE
        for _k in _STUCK_FLAGS:
            session.pending_intake.pop(_k, None)
        if _tone_stuck:
            session.tone_calibration = {}
        await save_session(session)

        addr = _addr(session)
        if session.profile.is_intake_complete():
            msg = f"Em chào {addr}! Hôm nay tiếp tục phần nào ạ? 👇"
        else:
            msg = f"Em chào {addr}! Mình làm gì tiếp ạ? 👇"
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # Linh — chat-edit Brand Voice (chỉnh sửa tự do)
    if session.pending_intake.get("_bv_edit_mode"):
        session.pending_intake.pop("_bv_edit_mode", None)
        await save_session(session)
        await update.message.reply_text("✏️ _Linh đang cập nhật Brand Voice..._", parse_mode=ParseMode.MARKDOWN)
        updated = await _apply_bv_edit(session, text)
        if updated:
            await _send_bv_html(
                update.message, session, updated,
                "✅ *Đã cập nhật Brand Voice!* Dùng chung cho toàn business từ giờ.",
                keyboard=LINH_BV_EXISTS_KEYBOARD,
            )
        else:
            await update.message.reply_text(
                "⚠️ Em chưa cập nhật được (chưa có Brand Voice hoặc lỗi tạm thời). "
                "Sếp thử lại hoặc tạo Brand Voice mới nhé.",
                reply_markup=LINH_BV_NEW_KEYBOARD,
            )
        return

    # McKinsey Discovery Gate — user submitted basic business form
    if session.pending_intake.get(BIZ_CONTEXT_AWAITING):
        await _handle_basic_business_text(update, context, session, text)
        return

    # Task 1: Workflow topic intake — user gửi chủ đề viết content
    if session.pending_intake.get("_workflow_awaiting_topic"):
        workflow_task = session.pending_intake.get("_workflow_task", "write_content")
        topic_text = update.message.text.strip() if update.message else ""
        if workflow_task == "write_content":
            session.pending_intake.pop("_workflow_awaiting_topic", None)
            await save_session(session)
            await _run_write_content_workflow_handler(update.message, session, topic_text)
        return

    # Sprint 6: Tone calibration feedback
    if session.tone_calibration.get("stage") == "waiting_feedback":
        await _handle_tone_feedback(update, context, session, text)
        return

    # Sprint 7: Post edit instruction
    if session.pending_intake.get("_post_editing"):
        post_id = session.pending_intake.pop("_post_editing")
        post = session.content_outputs.get(post_id)
        if post:
            await update.message.reply_text("✏️ _Đang chỉnh sửa..._", parse_mode=ParseMode.MARKDOWN)
            from agents.post_actions import edit_post
            edited = await edit_post(post.get("content", ""), text, session)
            session.content_outputs[post_id]["content"] = edited
            session.content_outputs[post_id]["status"] = "draft"
            await save_session(session)
            from agents.post_actions import format_post_preview
            from bot.keyboards import post_action_keyboard
            await update.message.reply_text(
                f"✅ *`{post_id}` đã chỉnh:*\n\n" + format_post_preview(post_id, session.content_outputs[post_id]),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=post_action_keyboard(post_id),
            )
        return

    # Sprint 5 v2: Image edit text reply
    if session.pending_intake.get("_awaiting_image_edit"):
        await _handle_image_edit_text(update, context, session, text)
        return

    # Layer 2: User mô tả phần cần sửa trong strategy → surgical edit
    # Nhắc tên business trước khi chạy A→Z → user gõ tên (hoặc từ chối)
    if session.pending_intake.get("_awaiting_bizname"):
        await _handle_bizname_text(update, context, session, text)
        return

    if session.pending_intake.get("_awaiting_strategy_edit"):
        await _handle_strategy_edit_text(update, context, session, text)
        return

    if session.pending_intake.get("_awaiting_calendar_edit"):
        await _handle_calendar_edit_text(update, context, session, text)
        return

    if session.pending_intake.get("_awaiting_bp_edit"):
        await _handle_bp_edit_text(update, context, session, text)
        return

    if session.pending_intake.get("_awaiting_week_selection"):
        await _handle_week_selection_text(update, context, session, text)
        return

    if session.pending_intake.get("_awaiting_calendar_cadence"):
        await _handle_calendar_cadence_text(update, context, session, text)
        return

    if session.pending_intake.get("_awaiting_budget_team"):
        await _handle_budget_team_text(update, context, session, text)
        return

    # Layer 2b: User mô tả phần cần sửa trong campaign brief → surgical edit
    if session.pending_intake.get("_awaiting_brief_edit"):
        await _handle_brief_edit_text(update, context, session, text)
        return

    # Sau khi duyệt brief: sếp trả lời kênh + source mix → ghi nhận → dựng calendar
    if session.pending_intake.get("_awaiting_campaign_setup"):
        await _handle_campaign_setup_text(update, context, session, text)
        return

    # Ads Scheduler: user đang nhập ngưỡng alert
    if session.pending_intake.get("_awaiting_ads_thresholds"):
        await _handle_ads_threshold_text(update, session, text)
        return

    # Post A→Z: Bot hỏi nhu cầu (mục tiêu/dịp/ngân sách) → parse → đề xuất campaign options
    if session.pending_intake.get("_awaiting_campaign_needs"):
        await _handle_campaign_needs_text(update, context, session, text)
        return

    # Post A→Z: Bot hỏi triết lý + giới hạn offer → parse → đề xuất cách ưu đãi
    if session.pending_intake.get("_awaiting_offer_prefs"):
        await _handle_offer_prefs_text(update, context, session, text)
        return

    # Post A→Z: User mô tả idea campaign → refine với customer + market
    if session.pending_intake.get("_awaiting_campaign_idea"):
        await _handle_campaign_idea_text(update, context, session, text)
        return

    # Post A→Z: User fill 4 trường quyết định (budget, team, start_date, discount)
    if session.pending_intake.get("_awaiting_campaign_finalize"):
        await _handle_campaign_finalize_text(update, context, session, text)
        return

    # Strategic consultation: user gõ custom answer cho 1 câu hỏi chiến lược
    if session.pending_intake.get("_awaiting_strategy_q_custom"):
        import json as _json
        session.pending_intake.pop("_awaiting_strategy_q_custom", None)
        q_key   = session.pending_intake.pop("_current_q_key", "")
        answers = _json.loads(session.pending_intake.get("_strategy_answers", "{}"))
        if q_key:
            answers[q_key] = text.strip()
        session.pending_intake["_strategy_answers"] = _json.dumps(answers, ensure_ascii=False)
        await save_session(session)
        await _ask_next_strategy_question(update.message, session)
        return

    # USP Gate: user trả lời câu hỏi USP sau McKinsey Gate
    if session.pending_intake.get("_awaiting_usp_text"):
        await _handle_usp_text(update, context, session, text)
        return

    # Sprint 2: Q&A follow-up (stage COMPLETE + awaiting_followup_for OR stage COMPLETE)
    if session.pending_intake.get("_awaiting_followup_for") or session.stage == PipelineStage.COMPLETE:
        await _handle_followup(update, context, session, text)
        return

    # Advisor mode chain — sau khi user click "Hỏi tiếp"
    if session.pending_intake.get("_advisor_mode"):
        # FB URL intercept — recognize competitor intent before persona advisor
        if await _try_fb_url_intercept(update, context, session, text):
            return
        if await _try_persona_route(update, context, session, text):
            return
        await _claude_advisor_fallback(update, context, session, text)
        return

    if session.stage in (PipelineStage.IDLE, PipelineStage.TASK_SELECT):
        # FB URL intercept — recognize competitor intent before persona advisor
        if await _try_fb_url_intercept(update, context, session, text):
            return
        # User typed free-form text → try persona routing first, then generic advisor
        if await _try_persona_route(update, context, session, text):
            return
        await _claude_advisor_fallback(update, context, session, text)
        return

    elif session.stage == PipelineStage.INTAKE:
        # Sprint 2: Check feedback flow first (user typing feedback after rating ≤3)
        if session.pending_intake.get("_awaiting_feedback_for"):
            await _handle_feedback_text(update, context, session, text)
            return
        # Route to ops single-shot intake if marker present, else strategic multi-turn
        if session.pending_intake.get(OPS_INTAKE_AWAITING):
            await _handle_ops_intake_reply(update, context, session, text)
        else:
            await _handle_intake(update, context, session, text)

    elif session.pending_intake.get("_awaiting_feedback_for"):
        # User trong stage khác nhưng đang đợi feedback text → vẫn handle
        await _handle_feedback_text(update, context, session, text)

    elif session.stage == PipelineStage.CONFIRMED:
        await update.message.reply_text(
            "Nhấn *Đúng rồi, bắt đầu!* để tôi chạy phân tích nhé! Hoặc /reset để bắt đầu lại.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=CONFIRM_KEYBOARD,
        )

    else:
        await update.message.reply_text(
            "⏳ Đang phân tích... Vui lòng chờ tôi hoàn thành nhé."
        )


@with_user_lock
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sprint 5 v2: User upload ảnh mẫu để bot làm theo style."""
    user_id = update.effective_user.id
    session = await get_session(user_id)

    if not session.pending_intake.get("_awaiting_image_reference"):
        await update.message.reply_text(
            "📸 Em nhận ảnh nhưng chưa biết dùng làm gì ạ. "
            "Sếp vào *Sản Xuất Nội Dung Ads* để gửi ảnh mẫu nhé!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text(
        "🔍 Em đang phân tích style ảnh mẫu... (~10s)",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        # Download highest-res photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        import io as _io
        buf = _io.BytesIO()
        await file.download_to_memory(out=buf)
        image_bytes = buf.getvalue()

        # Analyze style
        from tools.image_gen import analyze_image_style
        style_desc = await analyze_image_style(image_bytes)

        # Build final prompt = original brief + style description
        original_prompt = session.pending_intake.get("_img_prompt", "")
        combined_prompt = f"{original_prompt}\n\nStyle reference (giữ style này): {style_desc}"
        session.pending_intake["_img_prompt"] = combined_prompt[:1500]
        session.pending_intake.pop("_awaiting_image_reference", None)
        await save_session(session)

        await update.message.reply_text(
            f"✅ *Em đã phân tích style:*\n\n_{style_desc[:300]}_\n\n"
            f"Sếp muốn em tạo mấy ảnh ạ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=IMAGE_GEN_PROMPT_KEYBOARD,
        )
    except Exception as e:
        logger.exception("Image reference analysis failed: %s", e)
        await update.message.reply_text(
            f"⚠️ Em không phân tích được ảnh: {str(e)[:200]}\n\nSếp thử ảnh khác hoặc skip ạ.",
            reply_markup=IMAGE_GEN_PROMPT_KEYBOARD,
        )


_XLSX_MIME = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Excel read-back: user uploads an edited .xlsx → detect skill từ tên file →
    parse nội dung → hỏi sếp muốn Max làm gì (lưu / xem lại / viết lại)."""
    doc = update.message.document
    if doc is None:
        return
    fname = doc.file_name or ""
    is_xlsx = (doc.mime_type in _XLSX_MIME) or fname.lower().endswith((".xlsx", ".xlsm"))
    if not is_xlsx:
        await update.message.reply_text(
            "📎 Em mới nhận file nhưng chỉ đọc được *file Excel (.xlsx)* thôi ạ.\n"
            "Sếp sửa trên file Excel em gửi rồi tải lên lại giúp em nhé.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    user_id = update.effective_user.id
    session = await get_session(user_id)

    from bot.excel_reader import detect_skill_from_filename, read_xlsx_to_markdown

    skill_name = detect_skill_from_filename(fname)
    if not skill_name:
        await update.message.reply_text(
            "🤔 Em chưa nhận ra file này thuộc nội dung nào ạ.\n\n"
            "👉 *Quan trọng:* khi sửa file Excel em gửi, sếp *giữ nguyên tên file* "
            "(vd: `content_calendar_ShopABC.xlsx`) rồi tải lên lại — em mới biết đây là "
            "output của skill nào để cập nhật đúng chỗ.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        import io as _io
        file = await context.bot.get_file(doc.file_id)
        buf = _io.BytesIO()
        await file.download_to_memory(out=buf)
        parsed_md = read_xlsx_to_markdown(buf.getvalue())
    except Exception as e:
        logger.exception("[xlsx] read failed: %s", e)
        await update.message.reply_text(
            f"⚠️ Em đọc file không được: `{str(e)[:200]}`\n"
            "Sếp thử lưu lại dạng .xlsx chuẩn rồi gửi lại nhé.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not parsed_md.strip():
        await update.message.reply_text(
            "📄 File Excel này em đọc ra rỗng (không có dữ liệu). Sếp kiểm tra lại nhé."
        )
        return

    task = get_task(skill_name)
    label = task.label if task else skill_name

    # Lưu tạm vào session — chờ user chọn hành động
    session.pending_intake["_xlsx_skill"] = skill_name
    session.pending_intake["_xlsx_content"] = parsed_md[:20000]
    await save_session(session)

    has_old = session.has_result(skill_name)
    note = "" if has_old else "\n_(Phiên này chưa có bản gốc — em sẽ lưu đây làm bản đầu.)_"
    await update.message.reply_text(
        f"📥 *Em nhận được file đã sửa của: {label}*{note}\n\n"
        f"Sếp muốn em làm gì với bản này ạ?\n"
        f"• 💾 *Lưu lại* — ghi đè, mọi skill sau sẽ bám theo bản sếp sửa\n"
        f"• 📋 *Xem em đọc đúng chưa* — em tóm tắt lại nội dung đọc được\n"
        f"• 🔄 *Max viết lại* — em hoàn thiện/mở rộng dựa trên chỉnh sửa của sếp",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=XLSX_EDIT_KEYBOARD,
    )


async def _refine_edited_excel(session, skill_name: str, edited_md: str) -> "str | None":
    """Option 'viết lại': Max hoàn thiện/mở rộng nội dung Excel user đã sửa.
    GIỮ NGUYÊN chỉnh sửa của user, chỉ bồi đắp thêm. Returns markdown hoặc None."""
    try:
        from agents.pipeline import client as _client
        from config import CLAUDE_SONNET_MODEL

        task = get_task(skill_name)
        label = task.label if task else skill_name
        sys = (
            f"Bạn là chuyên gia marketing. User vừa chỉnh sửa thủ công file '{label}' "
            f"(dạng bảng markdown). Nhiệm vụ: GIỮ NGUYÊN mọi chỉnh sửa của user, "
            f"hoàn thiện các ô còn trống, mở rộng/đánh bóng nội dung cho nhất quán & "
            f"dùng được ngay. KHÔNG đổi những gì user đã viết. KHÔNG giải thích — "
            f"chỉ xuất lại nội dung dạng bảng markdown hoàn chỉnh."
        )
        resp = await _client.messages.create(
            model=CLAUDE_SONNET_MODEL,
            max_tokens=8000,
            system=sys,
            messages=[{"role": "user", "content": f"Nội dung user đã sửa:\n\n{edited_md[:15000]}"}],
        )
        out = resp.content[0].text.strip()
        return out or None
    except Exception as e:
        logger.exception("[xlsx] refine failed skill=%s: %s", skill_name, e)
        return None


async def _handle_image_edit_text(update, context, session, text):
    """User gõ description sửa ảnh → call image edit API."""
    if not session.pending_intake.get("_last_image_b64"):
        await update.message.reply_text(
            "⚠️ Em không tìm thấy ảnh cũ. Sếp gen ảnh mới nhé.",
            reply_markup=IMAGE_GEN_PROMPT_KEYBOARD,
        )
        session.pending_intake.pop("_awaiting_image_edit", None)
        await save_session(session)
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await update.message.reply_text(
        "🎨 Em đang sửa ảnh theo yêu cầu... (~30s)",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        import base64 as _b64
        from tools.image_gen import edit_image
        base_b64 = session.pending_intake["_last_image_b64"]
        base_bytes = _b64.b64decode(base_b64)
        img_size = session.pending_intake.get("_last_image_size", "1024x1024")

        new_images = await edit_image(
            base_image_bytes=base_bytes,
            edit_prompt=text,
            size=img_size,
            quality="medium",
            n=1,
        )

        import io as _io
        new_bytes = new_images[0] if new_images else None
        if not new_bytes:
            raise RuntimeError("Không nhận được ảnh sau edit")

        buf = _io.BytesIO(new_bytes)
        buf.name = "ads_image_edited.png"
        await update.message.reply_photo(photo=buf, caption="✨ Ảnh đã sửa")

        # Update last image for chained edits
        session.pending_intake["_last_image_b64"] = _b64.b64encode(new_bytes).decode("ascii")
        session.pending_intake.pop("_awaiting_image_edit", None)
        await save_session(session)

        await update.message.reply_text(
            "Sếp muốn sửa tiếp hay chốt ạ?",
            reply_markup=IMAGE_REVIEW_KEYBOARD,
        )
    except Exception as e:
        logger.exception("Image edit failed: %s", e)
        session.pending_intake.pop("_awaiting_image_edit", None)
        await save_session(session)
        await update.message.reply_text(
            f"⚠️ Sửa ảnh thất bại: {str(e)[:200]}\n\nSếp thử lại hoặc gen ảnh mới?",
            reply_markup=IMAGE_REVIEW_KEYBOARD,
        )


# ─── Intake ───────────────────────────────────────────────────────

async def _handle_intake(update, context, session, text):
    # Guard: profile already complete — skip multi-turn, go straight to confirm
    if session.profile.is_intake_complete():
        logger.warning(
            "_handle_intake called with complete profile (stage=%s) — redirecting to CONFIRMED",
            session.stage,
        )
        task = session.selected_task or "full"
        session.stage = PipelineStage.CONFIRMED
        await save_session(session)
        await _show_profile_reuse_confirm(update.message, session, task)
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    response, is_complete = await run_intake(session, text)
    await save_session(session)

    if is_complete:
        clean_response = re.sub(r"```json.*?```", "", response, flags=re.DOTALL).strip()

        fw = KPI_LIBRARY.get(session.profile.industry or "")
        industry_name = fw.display_name if fw else (session.profile.industry or "Chưa xác định")

        task = session.selected_task or "full"
        task_label = TASK_LABELS.get(task, "Phân tích")
        steps_desc = TASK_PIPELINE_STEPS.get(task, "")

        confirm_msg = (
            f"Tôi đã nắm được thông tin cần thiết!\n\n"
            f"🏢 *Business*: {_escape_md(session.profile.business_name or 'Business của bạn')}\n"
            f"📦 *Sản phẩm/DV*: {_escape_md(session.profile.product_service or 'Chưa xác định')}\n"
            f"👥 *Khách hàng*: {_escape_md(session.profile.target_customer or 'Chưa xác định')}\n"
            f"📊 *Ngành*: {_escape_md(industry_name)}\n"
            f"🚀 *Stage*: {_escape_md(session.profile.stage or 'Chưa xác định')}\n"
            f"💰 *Doanh thu*: {_escape_md(session.profile.monthly_revenue or 'Chưa rõ')}\n"
            f"🎯 *Mục tiêu*: {_escape_md(session.profile.primary_goal or 'Chưa xác định')}\n"
            f"⚡ *Thách thức*: {_escape_md(session.profile.main_challenge or 'Chưa xác định')}\n\n"
            f"─────────────────────────\n"
            f"*Task*: {task_label}\n"
            f"{steps_desc}\n\n"
            f"Bắt đầu nhé? 🚀"
        )

        session.stage = PipelineStage.CONFIRMED
        # Profile đã extract xong → intake_history không còn giá trị, xóa để tiết kiệm storage
        session.intake_history = []
        await save_session(session)

        await _safe_reply(
            update.message,
            confirm_msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=CONFIRM_KEYBOARD,
        )
    else:
        # Smart Intake v2: LLM có thể vô tình output JSON sớm dù chưa đủ 8
        # fields. Strip JSON block để user không thấy block thô trong chat.
        clean_response = re.sub(r"```json.*?```", "", response, flags=re.DOTALL).strip()
        if not clean_response:
            clean_response = "Em note rồi sếp. Cho em hỏi thêm 1 câu nữa nhé..."
        await _safe_reply(update.message, clean_response, parse_mode=ParseMode.MARKDOWN)


# ─── Follow-up Q&A after analysis complete ───────────────────────

async def _handle_followup(update, context, session, text):
    """Multi-turn Q&A về output skill vừa xong.
    Ưu tiên context = latest result của skill được follow-up.
    Fallback = full pipeline context.
    """
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    import anthropic
    from config import CLAUDE_MODEL, ANTHROPIC_API_KEY

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Chọn context: ưu tiên latest output của skill đang follow-up
    skill_name = session.pending_intake.get("_awaiting_followup_for") or session.selected_task or ""
    latest_output = session.get_latest_result(skill_name) if skill_name else None

    if latest_output:
        context_str = (
            f"## Output em vừa đưa ra cho sếp ({skill_name}):\n\n"
            f"{latest_output}\n\n"
            f"## Profile business:\n{session.profile.to_context_string()}"
        )
    else:
        context_str = session.build_pipeline_context()

    user_name = _get_user_name(session)
    name_hint = (
        f"User tên là '{user_name}' — khi xưng hô gọi 'sếp {user_name}', không chỉ 'sếp'."
    ) if user_name else ""

    system_text = (
        "Bạn là Max, AI CMO của founder Việt Nam. "
        "Sếp vừa hỏi follow-up về output em đưa ra. "
        "Trả lời BÁM SÁT output đã có. Nếu sếp hỏi ngoài scope, "
        "gợi ý chạy skill khác phù hợp.\n\n"
        f"Tone: em/sếp, professional nhưng thân thiện. {name_hint}\n"
        "Trả lời ngắn gọn (1-3 đoạn), tập trung. Không lặp lại nguyên output."
    )

    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=[{
            "type": "text",
            "text": system_text,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"{context_str}\n\n---\n\nCâu hỏi follow-up: {text}",
        }],
    )

    # Token tracking
    try:
        from tools.token_tracker import track_usage
        track_usage(session, response, label="followup_qa")
        await save_session(session)
    except Exception as e:
        logger.warning("Token tracking failed (followup): %s", e)

    await send_long_message(
        update.message,
        response.content[0].text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ASK_FOLLOWUP_KEYBOARD,
    )


# ─── Callback (inline keyboard) ──────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # ACK Telegram BEFORE acquiring the user lock.
    # If we answer inside the lock and another handler holds it for >5s,
    # Telegram retries the callback, delivering it twice.  Both deliveries
    # then queue behind the lock; the second one fails with
    # "Message is not modified" and the user sees a spurious error card.
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    async with _get_user_lock(user_id):
        session = await get_session(user_id)
        try:
            return await _handle_callback_inner(update, context, query, session, data, user_id)
        except Exception as e:
            err_str = str(e).lower()
            # "Message is not modified" = duplicate delivery — ACKed already, safe to ignore
            if "not modified" in err_str or "message is not modified" in err_str:
                logger.debug("Duplicate callback ignored (data=%s): %s", data, e)
                return
            # Fallback for genuine unhandled callback errors
            logger.exception("Callback handler error (data=%s): %s", data, e)
            try:
                await query.message.reply_text(
                    "⚠️ Có lỗi xảy ra. Gõ /start để bắt đầu lại nhé."
                )
            except Exception:
                pass


async def _handle_callback_inner(update, context, query, session, data, user_id):

    # ── Ads Scheduler callbacks ───────────────────────────────────
    if data == "noop":
        return

    if data.startswith("fb_acct:"):
        account_id = data.split(":", 1)[1]
        from services.fb_oauth import _pending_connections, _norm_id, _notify_connected
        from storage.fb_connections import save_connection

        pending = _pending_connections.pop(user_id, None)
        if not pending:
            await query.answer("Link đã hết hạn. Vui lòng /connect_ads lại.", show_alert=True)
            return

        accounts = pending["accounts"]
        chosen = next((a for a in accounts if _norm_id(a) == account_id), None)
        if not chosen:
            await query.answer("Tài khoản không hợp lệ.", show_alert=True)
            return

        account_name = chosen.get("name") or account_id
        await save_connection(user_id, pending["encrypted_token"], account_id, account_name,
                              pending["expires_at"], available_accounts=accounts)
        await query.edit_message_text(f"⏳ Đang lưu kết nối với *{account_name}*...", parse_mode=ParseMode.MARKDOWN)
        await _notify_connected(context.bot, user_id, account_name, account_id, accounts)
        return

    if data.startswith("aud_pick:"):
        _, account_id, picked_task = data.split(":", 2)
        from storage.fb_connections import get_available_accounts, update_active_account
        accounts = await get_available_accounts(user_id)
        chosen = next((a for a in accounts if a.get("id") == account_id or
                       (not a["id"].startswith("act_") and f"act_{a['id']}" == account_id)), None)
        if not chosen:
            await query.answer("Tài khoản không tìm thấy.", show_alert=True)
            return
        acc_id = chosen["id"] if chosen["id"].startswith("act_") else f"act_{chosen['id']}"
        acc_name = (chosen.get("name") or acc_id).replace("*", "").replace("_", "-")
        await update_active_account(user_id, acc_id, acc_name)
        await query.edit_message_text(f"✅ Đang phân tích *{acc_name}*...", parse_mode=ParseMode.MARKDOWN)
        await _send_single_shot_form(query.message, session, picked_task, _skip_account_pick=True)
        return

    if data.startswith("sw_acct:"):
        account_id = data.split(":", 1)[1]
        from storage.fb_connections import get_available_accounts, update_active_account
        accounts = await get_available_accounts(user_id)
        chosen = next((a for a in accounts if a.get("id") == account_id or
                       (not a["id"].startswith("act_") and f"act_{a['id']}" == account_id)), None)
        if not chosen:
            await query.answer("Tài khoản không tìm thấy.", show_alert=True)
            return
        acc_id = chosen["id"] if chosen["id"].startswith("act_") else f"act_{chosen['id']}"
        acc_name = chosen.get("name") or acc_id
        await update_active_account(user_id, acc_id, acc_name)
        safe = acc_name.replace("*", "").replace("_", "-")
        await query.edit_message_text(
            f"✅ Đã chuyển sang *{safe}*\n`{acc_id}`\n\nChạy lại skill để pull data từ account này.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "ads_report_menu":
        await query.edit_message_reply_markup(reply_markup=None)
        from storage.fb_connections import get_connection
        conn = await get_connection(user_id)
        if not conn:
            await query.message.reply_text(
                "📈 Sếp chưa kết nối Facebook Ads. Gõ `/connect_ads` để kết nối nhé.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 Live — hôm nay",  callback_data="ads_report:live")],
            [InlineKeyboardButton("📅 Hôm qua",          callback_data="ads_report:yesterday")],
            [InlineKeyboardButton("📊 7 ngày qua",       callback_data="ads_report:7d")],
        ])
        await query.message.reply_text(
            "📈 *Báo Cáo Nhanh — Ads*\n\nSếp muốn xem chỉ số khung thời gian nào?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
        return

    if data.startswith("ads_report:"):
        period = data.split(":", 1)[1]
        await query.edit_message_reply_markup(reply_markup=None)
        from storage.fb_connections import get_connection
        from services.ads_notifier import fetch_quick_report, format_quick_report, send_message_safe
        conn = await get_connection(user_id)
        if not conn:
            await query.message.reply_text(
                "📈 Sếp chưa kết nối Facebook Ads. Gõ `/connect_ads` để kết nối nhé.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        account_name = (conn.get("account_name") or "Ads Account").replace("*", "").replace("_", "-").replace("`", "'").replace("[", "(").replace("]", ")")
        await query.message.reply_text("📊 Em đang pull số liệu...", parse_mode=ParseMode.MARKDOWN)
        try:
            current_rows, compare_rows = await fetch_quick_report(conn, period)
            text = format_quick_report(period, current_rows, compare_rows, conn, account_name)
            await send_message_safe(context.bot, user_id, text)
        except Exception as e:
            logger.warning("[AdsReport] quick report failed user=%d period=%s: %s", user_id, period, e)
            await query.message.reply_text(f"🛑 Không pull được số liệu: {str(e)[:200]}")
        return

    if data.startswith("opt_pick:"):
        choice = data.split(":", 1)[1]
        await query.edit_message_reply_markup(reply_markup=None)
        choices = session.pending_intake.pop("_optimizer_choices", {})
        if choice == "_custom":
            session.pending_intake["_optimizer_skip_pick"] = True
        else:
            name = choices.get(choice)
            if name:
                session.pending_intake["target"] = name
                await query.message.reply_text(f"✅ Đã chọn: *{_escape_md(name)}*", parse_mode=ParseMode.MARKDOWN)
        await save_session(session)
        await _send_single_shot_form(query.message, session, "ads_optimizer")
        return

    if data == "ads_toggle_notify":
        from storage.fb_connections import get_connection, update_notification_settings
        conn = await get_connection(user_id)
        if conn:
            new_state = not conn.get("notification_enabled", True)
            await update_notification_settings(user_id, notification_enabled=new_state)
            state_text = "🟢 Đã bật" if new_state else "🔴 Đã tắt"
            await query.edit_message_text(
                f"{state_text} báo cáo ads hàng ngày.\n\nDùng `/ads_settings` để chỉnh thêm.",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if data.startswith("ads_toggle_metric:"):
        metric = data.split(":", 1)[1]
        from storage.fb_connections import get_connection, update_notification_settings
        from services.ads_notifier import AVAILABLE_METRICS
        conn = await get_connection(user_id)
        if conn and metric in AVAILABLE_METRICS:
            tracked = list(conn.get("tracked_metrics") or ["spend", "roas", "cpl", "frequency"])
            if metric in tracked:
                tracked.remove(metric)
            else:
                tracked.append(metric)
            await update_notification_settings(user_id, tracked_metrics=tracked)
            # Re-render keyboard để tick cập nhật ngay
            try:
                await query.edit_message_reply_markup(reply_markup=_build_metric_keyboard(tracked))
            except Exception:
                pass
        return

    if data == "ads_set_thresholds":
        from storage.fb_connections import get_connection
        conn = await get_connection(user_id)
        freq = conn.get("alert_frequency_max")  if conn else None
        roas = conn.get("alert_roas_drop_pct")  if conn else None
        cpm  = conn.get("alert_cpm_spike_pct")  if conn else None
        has_current = any(v is not None for v in (freq, roas, cpm))

        # Nhắc lại giá trị đang dùng (nếu có) làm mẫu sẵn để khách dễ chỉnh,
        # không thì mới show ví dụ/benchmark mặc định.
        ex_freq = freq if freq is not None else 5.0
        ex_roas = int(roas) if roas is not None else 20
        ex_cpm  = int(cpm)  if cpm  is not None else 30
        intro = "Sếp đang để mức này — gửi lại 3 dòng nếu muốn đổi:" if has_current \
            else "Gửi cho em 3 dòng theo format:"

        await query.edit_message_text(
            "⚠️ *Đặt ngưỡng cảnh báo*\n\n"
            f"{intro}\n"
            f"`frequency: {ex_freq}`\n"
            f"`roas_drop: {ex_roas}`\n"
            f"`cpm_spike: {ex_cpm}`\n\n"
            "Bỏ trống dòng nào = Max tự dùng benchmark ngành.",
            parse_mode=ParseMode.MARKDOWN,
        )
        session.pending_intake["_awaiting_ads_thresholds"] = True
        from storage import save_session as _sv
        await _sv(session)
        return

    if data == "ads_setup_metrics":
        from services.ads_notifier import RECOMMENDED_METRICS
        from storage.fb_connections import get_connection
        conn = await get_connection(user_id)
        tracked = (conn or {}).get("tracked_metrics") or RECOMMENDED_METRICS
        await query.edit_message_text(
            "📊 *Chọn chỉ số theo dõi hàng ngày:*\n\n"
            "Nhấn để bật/tắt. ⭐ Recommended = 4 chỉ số thiết yếu nhất.\n\n"
            "_Ngưỡng alert: bỏ trống = Max tự theo benchmark ngành._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_build_metric_keyboard(tracked, with_done=True),
        )
        return

    if data == "ads_setup_default":
        await query.edit_message_text(
            "✅ *Cài đặt mặc định đã áp dụng.*\n\n"
            "📊 Theo dõi: Spend · ROAS · CPL · Frequency\n"
            "⚠️ Ngưỡng alert: Max tự theo benchmark ngành\n"
            "🕗 Báo cáo: 8:00 sáng mỗi ngày, Thứ Hai = weekly report\n\n"
            "Dùng `/ads_settings` bất kỳ lúc nào để chỉnh.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Sprint 6: Tone Calibration ────────────────────────────────
    if data.startswith("tone_"):
        await _handle_tone_callback(query, session)
        return

    # ── Sprint 7: Per-post Actions ────────────────────────────────
    if data.startswith("post_"):
        await _handle_post_action_callback(query, session)
        return

    if data.startswith("adapt_"):
        await _handle_adapt_channel_callback(query, session)
        return


    # ── BACKLOG #10g: chọn loại nội dung trước khi sản xuất ───────
    if data.startswith("ctype_"):
        await query.edit_message_reply_markup(reply_markup=None)
        choice = data[len("ctype_"):]
        if choice == "all":
            from agents.operational_skills_config import ContentGeneratorPipeline
            session.pending_intake["_content_gen_types"] = list(ContentGeneratorPipeline.SUB_SKILLS)
        else:
            session.pending_intake["_content_gen_types"] = [choice]
        weekly = session.pending_intake.get("_content_gen_mode") == "weekly"
        if not weekly:
            session.pending_intake.pop("_content_gen_week", None)
            session.pending_intake.pop("_content_gen_weekly_mode", None)
            session.pending_intake.pop("scope", None)
        session.pending_intake.pop("_bv_pending_skill", None)
        await save_session(session)
        await _start_content_generation(query.message, session, weekly=weekly)
        return

    # ── Calendar → Content Gen chain ─────────────────────────────
    if data == "run_content_gen_weekly_after_cal":
        await query.edit_message_reply_markup(reply_markup=None)
        # Brand Voice gate (đồng bộ với full-month) — hỏi BV trước nếu chưa có
        skipped_flag = session.pending_intake.get("_bv_skipped_session")
        if not skipped_flag:
            try:
                from storage import has_brand_voice
                has_bv = await has_brand_voice(user_id)
            except Exception:
                has_bv = True  # fail-safe
            if not has_bv:
                session.pending_intake["_bv_pending_skill"] = "content_generator"
                session.pending_intake["_bv_resume_weekly"] = "1"
                await save_session(session)
                await query.message.reply_text(
                    "🎙 *Sếp chưa setup Brand Voice cho brand.*\n\n"
                    "Em recommend setup Brand Voice 1 lần để nội dung sau này "
                    "(*posts, ads, video...*) đều đúng tone & từ ngữ brand — "
                    "nhất quán hơn nhiều.\n\n"
                    "_Sếp có thể bỏ qua giờ và setup sau, em vẫn chạy được._",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=BRAND_VOICE_PROMPT_KEYBOARD,
                )
                return
        await _start_content_generation(query.message, session, weekly=True)
        return

    if data == "run_content_gen_after_cal":
        await query.edit_message_reply_markup(reply_markup=None)
        # Brand Voice gate: hỏi BV trước, rồi mới sản xuất content
        skipped_flag = session.pending_intake.get("_bv_skipped_session")
        if not skipped_flag:
            try:
                from storage import has_brand_voice
                has_bv = await has_brand_voice(user_id)
            except Exception:
                has_bv = True  # fail-safe
            if not has_bv:
                session.pending_intake["_bv_pending_skill"] = "content_generator"
                await save_session(session)
                await query.message.reply_text(
                    "🎙 *Sếp chưa setup Brand Voice cho brand.*\n\n"
                    "Em recommend setup Brand Voice 1 lần để nội dung sau này "
                    "(*content calendar, social posts, ads, video...*) "
                    "đều đúng tone & từ ngữ brand — nhất quán hơn nhiều.\n\n"
                    "_Sếp có thể bỏ qua giờ và setup sau, em vẫn chạy được._",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=BRAND_VOICE_PROMPT_KEYBOARD,
                )
                return
        session.selected_task = "content_generator"
        session.pending_intake.pop("_bv_pending_skill", None)
        # Full-month mode: xoá scope tuần lẻ (nếu trước đó user từng chọn weekly)
        session.pending_intake.pop("_content_gen_week", None)
        session.pending_intake.pop("_content_gen_weekly_mode", None)
        session.pending_intake.pop("scope", None)
        await save_session(session)
        await _start_content_generation(query.message, session, weekly=False)
        return

    # ── Layer 3: chọn kênh sản xuất content (từng kênh 1) ─────────
    if data.startswith("cgch_"):
        await query.edit_message_reply_markup(reply_markup=None)
        choice = data[len("cgch_"):]
        weekly = session.pending_intake.get("_content_gen_mode") == "weekly"

        if choice == "done":
            session.pending_intake["_content_channels_remaining"] = []
            await save_session(session)
            session.pending_intake["_awaiting_rating_for"] = "content_calendar"
            await save_session(session)
            await query.message.reply_text(
                "OK ạ! Sếp đánh giá nội dung em vừa làm thế nào ạ?",
                reply_markup=RATING_KEYBOARD,
            )
            return

        remaining = _content_remaining_channels(session)
        try:
            idx = int(choice)
            channel = remaining.pop(idx)
        except (ValueError, IndexError):
            channel = remaining.pop(0) if remaining else ""

        session.pending_intake["channel_focus"] = channel
        session.pending_intake["_content_channels_remaining"] = remaining
        await save_session(session)

        if channel:
            await query.message.reply_text(
                f"✅ *Kênh: {channel}* — em tập trung sản xuất nội dung cho kênh này trước.",
                parse_mode=ParseMode.MARKDOWN,
            )
        await _run_content_generation_for_channel(query.message, session, weekly)
        return

    if data == "skip_content_gen_after_cal":
        await query.edit_message_reply_markup(reply_markup=None)
        # Tiếp tục flow rating cho calendar
        session.pending_intake["_awaiting_rating_for"] = "content_calendar"
        await save_session(session)
        await query.message.reply_text(
            "OK ạ! Sếp đánh giá Lịch Nội Dung em vừa làm thế nào ạ?",
            reply_markup=RATING_KEYBOARD,
        )
        return

    # ── Calendar → Tách loại nội dung: Video / UGC ──
    if data == "run_video_scripts_after_cal":
        await query.edit_message_reply_markup(reply_markup=None)
        duration = session.pending_intake.get("duration") or "Theo Lịch Nội Dung"
        session.pending_intake.setdefault("scope", duration)
        session.pending_intake["_after_cal_vid"] = "1"
        session.selected_task = "video_script_gen"
        await save_session(session)
        await query.message.reply_text(
            "🎬 *Viết Kịch Bản Video từ Lịch Nội Dung* — Brief cho loại creator nào ạ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=VIDEO_CREATOR_KEYBOARD,
        )
        return

    if data == "run_ugc_brief_after_cal":
        await query.edit_message_reply_markup(reply_markup=None)
        session.selected_task = "ugc_brief"
        await save_session(session)
        await query.message.reply_text(
            "🤝 *Brief Creator UGC từ Lịch Nội Dung...*",
            parse_mode=ParseMode.MARKDOWN,
        )
        await _send_single_shot_form(query.message, session, "ugc_brief")
        return

    # ── Backlog #1: competitor_comparison — so sánh luôn không cần landscape ──
    if data == "force_comp_compare":
        await query.edit_message_reply_markup(reply_markup=None)
        session.selected_task = "competitor_comparison"
        await save_session(session)
        await _send_single_shot_form(query.message, session, "competitor_comparison")
        return

    # ── Backlog 2.2: brand_positioning revise loop ──────────────
    if data == "bp_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_awaiting_bp_edit", None)
        session.pending_intake.pop("_bp_feedback", None)
        await save_session(session)
        await query.message.reply_text(
            "✅ *Đã chốt Messaging House!*\n\n"
            "Em lưu vào session rồi — từ giờ content Nam/Trang viết, ads copy, "
            "voice check đều bám thông điệp chuẩn này thay vì positioning gốc.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "bp_edit_request":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_bp_edit"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "✏️ *Sếp muốn sửa gì trong Messaging House?* Gõ tự do nhé:\n\n"
            "_Vd: 'tagline 2 hay hơn, bỏ tagline 4' / 'key message tệp mới phải nhấn giá' "
            "/ 'tone đang trang trọng quá'_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "calendar_edit_request":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_calendar_edit"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "✏️ *Sếp muốn sửa gì trong lịch?* Gõ tự do nhé:\n\n"
            "_Vd: 'tăng thêm 2 video TikTok/tuần' / 'đổi focus sang awareness' / 'bớt bài Convert'_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Layer 2: Xác nhận / Surgical edit strategy ──────────────
    if data == "strategy_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_awaiting_strategy_edit", None)
        session.pending_intake.pop("_awaiting_rating_for", None)
        session.pending_intake.pop("_awaiting_campaign_idea", None)
        await save_session(session)
        await _ask_budget_team_before_campaigns(query.message, session)
        return

    if data == "budget_team_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        profile = session.profile
        session.pending_intake["_budget_team_context"] = (
            f"Ngân sách marketing/tháng: {profile.monthly_marketing_budget}\n"
            f"Team: {profile.team_size}"
        )
        session.pending_intake.pop("_budget_team_pending_confirm", None)
        await save_session(session)
        await _show_extracted_campaigns(query.message, session)
        return

    if data == "budget_team_edit":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_budget_team_pending_confirm", None)
        session.pending_intake["_awaiting_budget_team"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "✏️ OK, gõ lại giúp em:\n"
            "• Ngân sách marketing/tháng (cho campaign này)\n"
            "• Team: số người + vai trò",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "extracted_campaign_show_more":
        await query.edit_message_reply_markup(reply_markup=None)
        await _show_extracted_campaigns(query.message, session, show_all=True)
        return

    if data == "strategy_ok_run_calendar":
        # Kế hoạch ổn → chạy Lịch Nội Dung ngay với default từ profile
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_awaiting_strategy_edit", None)
        session.pending_intake.pop("_awaiting_rating_for", None)
        profile = session.profile
        session.pending_intake.setdefault(
            "channels", profile.current_channels or "Facebook + TikTok + Zalo OA"
        )
        session.pending_intake.setdefault("duration", "Tháng tới (30 ngày)")
        session.pending_intake["_strategy_aware"] = "1"
        session.selected_task = "content_calendar"
        session.stage = PipelineStage.TASK_SELECT
        await save_session(session)
        addr = _addr(session)
        await query.message.reply_text(
            f"📅 *Vậy em lên Lịch Nội Dung cho {addr} luôn nhé!*\n"
            f"_Dựa trên Kế Hoạch Đề Xuất + ICP có sẵn · khoảng 30-60 giây ạ._",
            parse_mode=ParseMode.MARKDOWN,
        )
        from config import AGENT_TIMEOUT
        try:
            result = await asyncio.wait_for(
                run_operational_skill("content_calendar", session),
                timeout=AGENT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            await query.message.reply_text(
                "⚠️ Lịch Nội Dung timeout. Sếp thử lại từ menu Sản Xuất nhé.",
            )
            return
        except Exception as e:
            logger.exception("content_calendar from strategy_ok failed: %s", e)
            await query.message.reply_text(
                "⚠️ Em gặp lỗi khi dựng lịch. Sếp thử lại từ menu nhé.",
            )
            return
        session.stage = PipelineStage.TASK_SELECT
        await save_session(session)
        await _send_ops_result(query.message, session, "content_calendar", result)
        await _start_tone_calibration(query.message, session, result)
        return

    if data == "strategy_edit":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_strategy_edit"] = "1"
        session.pending_intake.pop("_awaiting_rating_for", None)
        await save_session(session)
        addr = _addr(session)
        await query.message.reply_text(
            f"✏️ OK {addr}! Sếp nói rõ giúp em cần *điều chỉnh hướng nào* ạ.\n\n"
            f"_Vd: \"Nặng về awareness thay vì conversion\", "
            f"\"Tập trung retention và upsell khách cũ\", "
            f"\"Roadmap tháng 1 thêm bước chạy thử ads ngân sách nhỏ\", "
            f"\"Budget allocation cho TikTok nên cao hơn\"..._\n\n"
            f"Em chỉnh lại kế hoạch theo hướng đó và build lại cho sếp.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Layer 2b: Xác nhận / Surgical edit Campaign Brief ───────
    if data == "brief_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        # Kênh + source mix đã hỏi TRƯỚC khi viết brief → dựng funnel/calendar luôn
        await _confirm_brief_and_gen_calendar(query.message, session, context, update)
        return

    # User duyệt Funnel Map + Execution Plan → mới dựng Content Calendar
    if data == "funnel_approve":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_awaiting_rating_for", None)
        await save_session(session)
        await _gen_content_calendar_after_approval(query.message, session, context, update)
        return

    # BACKLOG #9 — "Vớt khách chưa convert": chạy email_zalo_sequence prefill
    # từ campaign vừa chốt (key_offer + BOFU chưa convert + channels).
    if data == "rescue_nonconvert":
        await query.edit_message_reply_markup(reply_markup=None)
        await _rescue_nonconvert_action(update, context, session)
        return

    # DEBUG: re-run funnel_map với session hiện tại, không tạo session mới
    if data == "dbg_funnel":
        campaign_name = (session.pending_intake.get("campaign_name")
                         or session.pending_intake.get("current_campaign") or "Campaign")
        campaign_goal = (session.pending_intake.get("campaign_goal")
                         or session.profile.primary_goal or "")
        await query.message.reply_text(
            f"🧪 *Debug: chạy lại Funnel Map cho \"{campaign_name}\"...*",
            parse_mode=ParseMode.MARKDOWN,
        )
        funnel_ok = await _gen_and_show_funnel_map(
            query.message, session, context, update, campaign_name, campaign_goal,
        )
        prompt = (
            "👆 *Funnel Map (debug re-run) — tóm tắt trên + file HTML + Excel.*\n\n"
            if funnel_ok else
            "_(Debug: chưa dựng được funnel map chi tiết.)_\n\n"
        )
        await _emit_funnel_approve_prompt(query.message, session, prompt)
        return

    if data == "brief_edit":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_brief_edit"] = "1"
        session.pending_intake.pop("_brief_edit_orig_comment", None)
        session.pending_intake.pop("_awaiting_rating_for", None)
        await save_session(session)
        addr = _addr(session)
        await query.message.reply_text(
            f"✏️ OK {addr}! Sếp nói rõ giúp em cần *thêm/bớt/sửa phần nào* trong brief ạ.\n\n"
            f"_Vd: \"Thêm phần phân bổ ngân sách theo kênh\", "
            f"\"Bỏ phần KPI, tập trung vào nội dung\", "
            f"\"Mục tiêu nên là thu lead chứ không phải doanh thu\"..._\n\n"
            f"Em chỉ chỉnh đúng phần đó thôi.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Post A→Z: Campaign Ideation flow ─────────────────────────
    # Branch A: User đã có idea → ask user gõ idea → refine
    if data == "az_have_idea":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_campaign_idea"] = "1"
        session.pending_intake.pop("_awaiting_rating_for", None)
        await save_session(session)
        await query.message.reply_text(
            "💡 *OK!* Sếp mô tả ý tưởng + mục tiêu campaign ạ.\n\n"
            "_Vd: \"Tết này muốn tặng combo cho khách cũ để tăng repeat, target phụ nữ 28-40\", "
            "\"Launch SP mới cho gen Z, muốn viral trước, chưa có budget lớn\"..._\n\n"
            "Em đối chiếu với Customer Insight + Market Research → validate + refine cho sếp luôn.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Bridge: user picks one of the roadmap-extracted campaigns
    if data.startswith("extracted_campaign_pick_"):
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            pick_idx = int(data.split("_")[-1]) - 1
        except ValueError:
            await query.message.reply_text("⚠️ Pick không hợp lệ.")
            return

        import json as _json
        raw = session.pending_intake.get("_extracted_campaigns", "[]")
        try:
            ex_campaigns = _json.loads(raw)
        except _json.JSONDecodeError:
            ex_campaigns = []

        if pick_idx < 0 or pick_idx >= len(ex_campaigns):
            await query.message.reply_text("⚠️ Option đã hết hạn. Sếp thử lại nhé.")
            return

        chosen = ex_campaigns[pick_idx]
        await _ask_offer_preferences(query.message, session, chosen)
        return

    if data == "extracted_campaign_own_idea":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_campaign_idea"] = "1"
        session.pending_intake.pop("_awaiting_rating_for", None)
        await save_session(session)
        await query.message.reply_text(
            "💡 *OK!* Sếp mô tả ý tưởng + mục tiêu campaign ạ.\n\n"
            "_Vd: \"Tết này muốn tặng combo cho khách cũ để tăng repeat\", "
            "\"Launch SP mới cho gen Z, muốn viral trước\"..._\n\n"
            "Em đối chiếu với Customer Insight + Market Research → validate + refine cho sếp luôn.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "extracted_campaign_more":
        await query.edit_message_reply_markup(reply_markup=None)
        await _show_extracted_campaigns(query.message, session)
        return

    # Branch B: User chưa biết → hỏi nhu cầu (flex theo ngành) trước, rồi propose
    if data == "az_propose_campaign" or data == "campaign_propose_again":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_awaiting_rating_for", None)
        session.pending_intake.pop("_awaiting_campaign_idea", None)
        session.pending_intake["_awaiting_campaign_needs"] = "1"
        await save_session(session)
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING,
        )
        from agents.campaign_ideation import generate_campaign_needs_question
        needs_q = await generate_campaign_needs_question(session)
        await query.message.reply_text(needs_q, parse_mode=ParseMode.MARKDOWN)
        return

    # User picks 1/2/3 từ proposed options → show finalize form
    if data.startswith("campaign_pick_"):
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            pick_idx = int(data.split("_")[-1]) - 1  # 1 → 0, 2 → 1, 3 → 2
        except ValueError:
            await query.message.reply_text("⚠️ Pick không hợp lệ.")
            return

        import json as _json
        raw = session.pending_intake.get("_proposed_campaigns", "[]")
        try:
            options = _json.loads(raw)
        except _json.JSONDecodeError:
            options = []

        if pick_idx < 0 or pick_idx >= len(options):
            await query.message.reply_text("⚠️ Option đã hết hạn. Sếp đề xuất lại nhé.")
            return

        chosen = options[pick_idx]
        await _ask_offer_preferences(query.message, session, chosen)
        return

    # User confirm refined idea → show finalize form
    if data == "campaign_idea_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        import json as _json
        raw = session.pending_intake.get("_refined_campaign", "{}")
        try:
            refined_data = _json.loads(raw)
            chosen = refined_data.get("refined", {})
        except _json.JSONDecodeError:
            chosen = {}

        if not chosen:
            await query.message.reply_text("⚠️ Idea đã hết hạn. Sếp gõ lại idea nhé.")
            return

        await _ask_offer_preferences(query.message, session, chosen)
        return

    # User muốn sửa lại idea
    if data == "campaign_idea_redo":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_campaign_idea"] = "1"
        session.pending_intake.pop("_refined_campaign", None)
        await save_session(session)
        await query.message.reply_text(
            "✏️ OK, sếp mô tả lại idea campaign mới ạ.",
        )
        return

    # User pick 1 trong 3 gói ưu đãi (BACKLOG #6) → đề xuất 4 lever cụ thể
    # TRONG khuôn khổ gói đã chọn (đi thẳng vào _show_offer_lever_selection,
    # không hỏi lại 3 câu cũ).
    if data.startswith("offer_package_pick_"):
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            pkg_idx = int(data.split("_")[-1])
        except ValueError:
            await query.message.reply_text("⚠️ Gói không hợp lệ.")
            return

        import json as _json
        raw_packages = session.pending_intake.get("_offer_packages", "[]")
        raw_campaign = session.pending_intake.get("_chosen_campaign", "{}")
        try:
            packages = _json.loads(raw_packages)
            campaign = _json.loads(raw_campaign)
        except _json.JSONDecodeError:
            packages, campaign = [], {}

        if pkg_idx < 0 or pkg_idx >= len(packages) or not campaign:
            await query.message.reply_text("⚠️ Gói đã hết hạn. Sếp /start lại nhé.")
            return

        chosen = packages[pkg_idx]
        session.pending_intake["_offer_prefs_raw"] = (
            f"Gói \"{chosen.get('name', '?')}\": {chosen.get('mechanism', '?')}. "
            f"Mức cho đi: {chosen.get('give_away', '?')}. "
            f"Ràng buộc: {chosen.get('constraint', '?')}."
        )
        await save_session(session)
        await _show_offer_lever_selection(query.message, session, campaign)
        return

    if data == "offer_package_custom":
        await query.edit_message_reply_markup(reply_markup=None)
        import json as _json
        raw_campaign = session.pending_intake.get("_chosen_campaign", "{}")
        try:
            campaign = _json.loads(raw_campaign)
        except _json.JSONDecodeError:
            campaign = {}
        if not campaign:
            await query.message.reply_text("⚠️ Campaign đã hết hạn. Sếp /start lại nhé.")
            return
        await _ask_offer_preferences_custom(query.message, session, campaign)
        return

    # User pick offer lever 1/2/3/4 → show dynamic finalize form
    if data.startswith("lever_pick_"):
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            lever_idx = int(data.split("_")[-1])
        except ValueError:
            await query.message.reply_text("⚠️ Lever pick không hợp lệ.")
            return

        import json as _json
        raw_levers = session.pending_intake.get("_offer_levers", "[]")
        raw_campaign = session.pending_intake.get("_chosen_campaign", "{}")
        try:
            levers = _json.loads(raw_levers)
            campaign = _json.loads(raw_campaign)
        except _json.JSONDecodeError:
            levers, campaign = [], {}

        if lever_idx < 0 or lever_idx >= len(levers) or not campaign:
            await query.message.reply_text("⚠️ Lever đã hết hạn. Sếp đề xuất lại nhé.")
            return

        chosen_lever = levers[lever_idx]
        await _show_dynamic_finalize_form(query.message, session, campaign, chosen_lever)
        return

    # User muốn AI đề xuất 4 levers khác
    if data == "lever_propose_again":
        await query.edit_message_reply_markup(reply_markup=None)
        import json as _json
        raw_campaign = session.pending_intake.get("_chosen_campaign", "{}")
        try:
            campaign = _json.loads(raw_campaign)
        except _json.JSONDecodeError:
            campaign = {}

        if not campaign:
            await query.message.reply_text("⚠️ Campaign đã hết hạn. Sếp /start lại nhé.")
            return

        await _show_offer_lever_selection(query.message, session, campaign)
        return

    # ── Sprint 5: Brand Voice lazy trigger callbacks ─────────────
    if data == "bv_setup_now":
        await query.edit_message_reply_markup(reply_markup=None)
        # Pivot session sang brand_voice skill — _bv_pending_skill đã lưu task gốc
        session.selected_task = "brand_voice"
        # KHÔNG xóa _bv_pending_skill — sẽ chain sau khi BV xong
        await save_session(session)
        await query.message.reply_text(
            "🎙 *Setup Brand Voice* — em hỏi vài câu để build bộ quy tắc.\n",
            parse_mode=ParseMode.MARKDOWN,
        )
        await _send_single_shot_form(query.message, session, "brand_voice")
        return

    if data == "bv_skip_for_now":
        await query.edit_message_reply_markup(reply_markup=None)
        # Mark skip cho session này — không hỏi lại
        session.pending_intake["_bv_skipped_session"] = "1"
        pending_skill = session.pending_intake.pop("_bv_pending_skill", None)
        await save_session(session)

        if pending_skill:
            # Special: resume tone calibration
            if pending_skill == "tone_calibration":
                pending_cal = session.tone_calibration.pop("pending_calendar", "")
                await save_session(session)
                await query.message.reply_text(
                    "OK ạ! Em chạy tone check luôn nhé.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                await _start_tone_calibration(query.message, session, pending_cal)
                return

            # Special: resume weekly content-gen flow (hỏi tuần thay vì chạy full-month)
            if pending_skill == "content_generator" and session.pending_intake.pop("_bv_resume_weekly", None):
                await _prompt_week_selection(query.message, session)
                return

            # Resume skill gốc user định chạy
            from bot.keyboards import ADS_COPY_TIER_KEYBOARD as _ADS_KB, VIDEO_CREATOR_KEYBOARD as _VID_KB
            session.selected_task = (
                "ads_generator" if pending_skill in ("ads_copy", "ads_generator") else pending_skill
            )
            await save_session(session)

            if pending_skill in ("ads_copy", "ads_generator"):
                await query.message.reply_text(
                    "OK ạ. *Sản Xuất Nội Dung Ads* — Sếp muốn gen tier nào trước?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=_ADS_KB,
                )
                return
            if pending_skill == "video_scripts":
                await query.message.reply_text(
                    "OK ạ. *Viết Kịch Bản Video* — Brief cho loại creator nào?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=_VID_KB,
                )
                return
            await _send_single_shot_form(query.message, session, pending_skill)
        else:
            await query.message.reply_text("OK, sếp /start để chọn skill khác nhé.")
        return

    # ── Brand Voice draft approval callbacks ──────────────────────
    if data == "bv_draft_approve":
        await query.edit_message_reply_markup(reply_markup=None)
        draft = session.pending_intake.pop("_bv_draft", None)
        await save_session(session)
        if draft:
            try:
                await _persist_brand_voice_from_session(session, draft)
                await _continue_after_brand_voice(query.message, session)
            except (TimedOut, NetworkError) as e:
                logger.warning("[BV] draft approve transient error: %s", e)
            except Exception as e:
                logger.exception("[BV] draft approve failed: %s", e)
                await query.message.reply_text("⚠️ Lỗi lưu Brand Voice. Thử lại nhé.")
        else:
            await query.message.reply_text("⚠️ Không tìm thấy draft. Sếp chạy lại Brand Voice nhé.")
        return

    if data == "bv_draft_regen":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_bv_draft", None)
        await save_session(session)
        await query.message.reply_text(
            "🔄 _Viết lại Brand Voice từ đầu..._",
            parse_mode=ParseMode.MARKDOWN,
        )
        session.selected_task = "brand_voice"
        await save_session(session)
        await _send_single_shot_form(query.message, session, "brand_voice")
        return

    # ── Excel read-back callbacks (user uploaded edited .xlsx) ──────
    if data in ("xlsx_save", "xlsx_review", "xlsx_refine", "xlsx_cancel"):
        await query.edit_message_reply_markup(reply_markup=None)
        skill_name = session.pending_intake.get("_xlsx_skill")
        content = session.pending_intake.get("_xlsx_content")

        if data == "xlsx_cancel":
            session.pending_intake.pop("_xlsx_skill", None)
            session.pending_intake.pop("_xlsx_content", None)
            await save_session(session)
            await query.message.reply_text("👌 Đã bỏ qua file vừa gửi ạ.")
            return

        if not skill_name or not content:
            await query.message.reply_text(
                "⚠️ Em không còn giữ nội dung file (phiên đã hết). Sếp gửi lại file nhé."
            )
            return

        task = get_task(skill_name)
        label = task.label if task else skill_name

        if data == "xlsx_review":
            preview = content[:3000]
            ell = "\n\n_..._" if len(content) > 3000 else ""
            await query.message.reply_text(
                f"📋 *Em đọc được từ file ({label}):*\n\n{preview}{ell}\n\n"
                f"Đúng thì bấm *Lưu lại* nhé sếp 👇",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=XLSX_EDIT_KEYBOARD,
            )
            return

        if data == "xlsx_save":
            session.add_result(skill_name, content)
            session.pending_intake.pop("_xlsx_skill", None)
            session.pending_intake.pop("_xlsx_content", None)
            await save_session(session)
            await query.message.reply_text(
                f"✅ *Đã lưu bản sếp sửa cho: {label}!*\n\n"
                f"Từ giờ các skill liên quan (vd: viết content/video) sẽ bám theo bản này ạ.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        if data == "xlsx_refine":
            await query.message.reply_text(
                "🔄 _Max đang hoàn thiện theo bản sếp sửa..._", parse_mode=ParseMode.MARKDOWN
            )
            refined = await _refine_edited_excel(session, skill_name, content)
            final = refined or content
            session.add_result(skill_name, final)
            session.pending_intake.pop("_xlsx_skill", None)
            session.pending_intake.pop("_xlsx_content", None)
            await save_session(session)
            if refined:
                await _send_ops_result(query.message, session, skill_name, final)
                await query.message.reply_text(
                    f"✅ *Đã viết lại & lưu cho: {label}!* (giữ nguyên chỉnh sửa của sếp)",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await query.message.reply_text(
                    f"⚠️ Em chưa viết lại được (lỗi tạm thời) — nhưng đã *lưu nguyên bản sếp sửa* cho {label}.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            return

    if data == "az_skip_campaign":
        await query.edit_message_reply_markup(reply_markup=None)
        # Cleanup full ideation + lever + finalize state
        for k in (
            "_awaiting_campaign_idea", "_proposed_campaigns", "_refined_campaign",
            "_chosen_campaign", "_offer_levers", "_chosen_lever",
            "_awaiting_campaign_finalize", "_finalize_campaign",
        ):
            session.pending_intake.pop(k, None)
        await save_session(session)
        await query.message.reply_text(
            "Sếp đánh giá output Nghiên Cứu & Phân Tích Thị Trường em vừa làm thế nào ạ?",
            reply_markup=RATING_KEYBOARD,
        )
        return

    if data == "research_analyze":
        await query.edit_message_reply_markup(reply_markup=None)
        await _send_single_shot_form(query.message, session, "full")
        return

    if data == "run_strategy_standalone":
        # Redo strategy synthesis — reuse saved strategic direction if available
        await query.edit_message_reply_markup(reply_markup=None)
        import json as _jstrat3
        try:
            _strat_answers3 = _jstrat3.loads(session.pending_intake.get("_strategy_answers", "{}"))
        except Exception:
            _strat_answers3 = {}
        _strat_dir3 = _format_strategy_answers(_strat_answers3)
        if _strat_dir3.strip():
            await _run_strategy_plan(query.message, session, direction=_strat_dir3)
        else:
            await query.message.reply_text(
                "🎯 *Em đang lập lại kế hoạch chiến lược...*",
                parse_mode=ParseMode.MARKDOWN,
            )
            session.selected_task = "strategy"
            await save_session(session)
            await _proceed_after_confirm(query.message, session)
        return

    if data == "resume_strategy_synthesis":
        # User had all 7 answers but synthesis was interrupted → re-run synthesis
        await query.edit_message_reply_markup(reply_markup=None)
        import json as _jresume2
        try:
            _answers = _jresume2.loads(session.pending_intake.get("_strategy_answers", "{}"))
        except Exception:
            _answers = {}
        _direction_block = _format_strategy_answers(_answers)
        if not _direction_block.strip():
            await query.message.reply_text(
                "⚠️ Không tìm thấy câu trả lời chiến lược đã lưu. Sếp cần chạy lại 8 câu hỏi nhé.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Chạy lại từ đầu", callback_data="research_analyze")],
                ]),
            )
            return
        await _run_strategy_plan(query.message, session, direction=_direction_block)
        return

    if data == "resume_strategy_questions":
        # User has research results — luôn hỏi lại đủ 8 câu từ đầu (đơn giản,
        # tránh resume giữa chừng từ state cũ/lỗi gây crash lặp lại).
        await query.edit_message_reply_markup(reply_markup=None)
        await _start_strategic_consultation(query.message, session)
        return

    if data == "usp_use_as_is":
        await query.edit_message_reply_markup(reply_markup=None)
        stated_usp = session.pending_intake.pop("_user_stated_usp", "")
        pending_skill = session.pending_intake.pop("_usp_pending_skill", "")
        if stated_usp:
            session.add_result("usp_definition", stated_usp)
        await save_session(session)
        await query.message.reply_text(
            f"✅ *Em đã lưu USP của sếp!*\n\n_{stated_usp}_",
            parse_mode=ParseMode.MARKDOWN,
        )
        if pending_skill:
            await _send_single_shot_form(query.message, session, pending_skill)
        return

    if data == "usp_analyze_more":
        await query.edit_message_reply_markup(reply_markup=None)
        # Giữ USP sếp gõ làm bản nháp → agent chạy chế độ REFINE:
        # đối chiếu/so sánh với thị trường & đối thủ, giữ ý gốc, đề xuất bản mạnh hơn.
        stated_usp = session.pending_intake.pop("_user_stated_usp", "")
        if stated_usp:
            session.profile.usp = stated_usp
            session.profile.usp_confidence = "draft"
        pending_skill = session.pending_intake.pop("_usp_pending_skill", "")
        await save_session(session)
        if stated_usp:
            await query.message.reply_text(
                f"🔬 *Em giữ USP của sếp làm gốc:*\n_{stated_usp}_\n\n"
                f"Em sẽ đối chiếu với thị trường & đối thủ, so sánh USP của sếp với góc em phân tích ra — "
                f"chỗ nào mài sắc được thì em mài, còn lại để sếp tự chọn dùng USP nào ạ.",
                parse_mode=ParseMode.MARKDOWN,
            )
        if pending_skill:
            await _send_single_shot_form(query.message, session, pending_skill)
        return

    if data == "strategy_q_custom":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_strategy_q_custom"] = "1"
        await save_session(session)
        q_key  = session.pending_intake.get("_current_q_key", "")
        label  = _STRATEGY_Q_LABELS.get(q_key, "hướng")
        await query.message.reply_text(
            f"✏️ *Sếp gõ {label} muốn chọn vào đây ạ:*\n\n"
            f"_Nếu muốn kết hợp nhiều hướng, gõ tất cả vào (vd: \"Hướng A + Hướng B + Hướng C\"). "
            f"Em vẫn khuyên tập trung 1 hướng, nhưng tôn trọng quyết định của sếp._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data.startswith("strategy_q_"):
        import json as _json
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            idx     = int(data.split("_", 2)[2])
            options = _json.loads(session.pending_intake.get("_current_q_options", "[]"))
            answer  = options[idx]
        except Exception:
            answer = data
        q_key   = session.pending_intake.pop("_current_q_key", "")
        session.pending_intake.pop("_current_q_options", None)
        answers = _json.loads(session.pending_intake.get("_strategy_answers", "{}"))
        if q_key:
            answers[q_key] = answer
        session.pending_intake["_strategy_answers"] = _json.dumps(answers, ensure_ascii=False)
        await save_session(session)
        await _ask_next_strategy_question(query.message, session)
        return

    # ── Rating callback (Sprint 2) ───────────────────────────────
    if data.startswith("rate_"):
        skill_name = session.pending_intake.get("_awaiting_rating_for")

        # Skip rating → đi thẳng action keyboard
        if data == "rate_skip":
            session.pending_intake.pop("_awaiting_rating_for", None)
            await save_session(session)
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                "OK ạ! Sếp muốn làm gì tiếp?",
                reply_markup=get_action_keyboard(skill_name or ""),
            )
            return

        try:
            rating = int(data.replace("rate_", ""))
        except ValueError:
            return
        if rating < 1 or rating > 5:
            return

        if not skill_name:
            await query.message.reply_text("Cảm ơn sếp! 🙏")
            return

        # Lưu rating vào session.feedback
        from datetime import datetime
        versions = session.results.get(skill_name, [])
        latest_version = versions[-1].version if versions else 0
        session.feedback.setdefault(skill_name, []).append({
            "version": latest_version,
            "rating": rating,
            "feedback": "",
            "created_at": datetime.utcnow().isoformat(),
        })

        # Log to feedback_log table (Task #12)
        try:
            await _log_feedback_to_db(session, skill_name, rating, "")
        except Exception as e:
            logger.warning("Feedback DB log failed (non-blocking): %s", e)

        await query.edit_message_reply_markup(reply_markup=None)

        if rating >= 4:
            # Rating cao → cảm ơn, hiện action keyboard theo category
            session.pending_intake.pop("_awaiting_rating_for", None)
            await save_session(session)
            await query.message.reply_text(
                "Cảm ơn sếp đã feedback! 🙏\n\nSếp muốn làm gì tiếp?",
                reply_markup=get_action_keyboard(skill_name),
            )
        else:
            # Rating ≤ 3 → hỏi feedback chi tiết
            session.pending_intake["_awaiting_feedback_for"] = skill_name
            session.pending_intake.pop("_awaiting_rating_for", None)
            await save_session(session)
            await query.message.reply_text(
                "Cảm ơn sếp! Sếp note giúp em chỗ nào chưa OK để em note lại nhé ạ?\n\n"
                "_Sếp gõ thoải mái — càng cụ thể em càng sửa được chính xác._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=FEEDBACK_PROMPT_KEYBOARD,
            )
        return

    # Sprint 2 v2: User skip feedback text → action keyboard
    if data == "feedback_skip":
        skill_name = session.pending_intake.get("_awaiting_feedback_for", "")
        session.pending_intake.pop("_awaiting_feedback_for", None)
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "OK ạ, cảm ơn sếp! 🙏",
            reply_markup=get_action_keyboard(skill_name),
        )
        return

    # ── Regen decision (Sprint 2) ────────────────────────────────
    if data == "regen_yes":
        skill_name = session.pending_intake.get("_pending_regen_skill")
        feedback = session.pending_intake.get("_pending_feedback", "")
        if not skill_name:
            await query.edit_message_text("Có lỗi, sếp gõ /start lại nhé.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Em đang chạy lại theo feedback của sếp...",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Inject user correction vào pending_intake để build_user_msg đọc
        session.pending_intake["_user_correction"] = feedback
        session.pending_intake.pop("_pending_regen_skill", None)
        session.pending_intake.pop("_pending_feedback", None)
        await save_session(session)

        try:
            # Dispatch lại theo loại skill
            SINGLE_SHOT_STRATEGIC = {"market", "competitor", "customer", "pricing"}
            from config import AGENT_TIMEOUT

            if skill_name in SINGLE_SHOT_STRATEGIC:
                from agents.pipeline import run_strategic_single_skill
                result = await asyncio.wait_for(
                    run_strategic_single_skill(skill_name, session),
                    timeout=AGENT_TIMEOUT,
                )
            elif skill_name in OPERATIONAL_TASKS:
                result = await asyncio.wait_for(
                    run_operational_skill(skill_name, session),
                    timeout=AGENT_TIMEOUT,
                )
            else:
                await query.message.reply_text("⚠️ Em không re-run được skill này.")
                return

            # Clear correction marker sau khi dùng
            session.pending_intake.pop("_user_correction", None)
            session.stage = PipelineStage.TASK_SELECT
            await save_session(session)
            await _send_ops_result(query.message, session, skill_name, result)
        except Exception as e:
            logger.exception("Regen failed: %s", e)
            await query.message.reply_text(f"⚠️ Re-run gặp lỗi: {str(e)[:200]}")
        return

    if data == "regen_no":
        # User skip regen — feedback đã lưu DB rồi qua _handle_feedback_text
        skill_name = session.pending_intake.get("_pending_regen_skill")
        feedback = session.pending_intake.get("_pending_feedback", "")
        session.pending_intake.pop("_pending_regen_skill", None)
        session.pending_intake.pop("_pending_feedback", None)
        await save_session(session)

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "OK ạ, cảm ơn sếp! 🙏",
            reply_markup=get_action_keyboard(skill_name or ""),
        )
        logger.info("FEEDBACK [%s] rating_low (regen_skip): %s", skill_name, feedback[:200])
        return

    # ── Language preference setup (Sprint 1.III) ─────────────────
    if data == "settings_change_name":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_user_name"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "✏️ *Sếp gõ tên mới em sẽ gọi nhé:*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "settings_change_lang":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "🔤 Chọn mức tiếng Anh em dùng trong output:",
            reply_markup=LANG_LEVEL_KEYBOARD,
        )
        return

    if data == "settings_tokens":
        await query.edit_message_reply_markup(reply_markup=None)
        from tools.token_tracker import (
            get_used, get_remaining, get_quota, fmt, is_low, is_exhausted, get_token_log,
        )
        used = get_used(session)
        remaining = get_remaining(session)
        quota = get_quota(session)
        pct_used = (used / quota * 100) if quota else 0

        name = _get_user_name(session)
        addr = f"sếp {name}" if name else "sếp"

        status_emoji = "🟢"
        if is_exhausted(session): status_emoji = "🔴"
        elif is_low(session):     status_emoji = "🟡"

        msg = (
            f"💎 *Chi tiết token của {addr}*\n\n"
            f"{status_emoji} *Quota:* {fmt(quota)}\n"
            f"📉 *Đã dùng:* {fmt(used)} ({pct_used:.1f}%)\n"
            f"📊 *Còn lại:* {fmt(remaining)}\n"
        )
        if is_exhausted(session):
            msg += "\n🔴 *Hết quota!* Sếp liên hệ admin để nạp thêm hoặc chờ reset hàng tháng."
        elif is_low(session):
            msg += "\n⚠️ Sếp còn dưới 10% quota — cân nhắc dùng tiết kiệm."

        # Per-skill breakdown — 15 lần chạy gần nhất
        log = get_token_log(session)
        skill_entries = [e for e in log if e.get("skill") and e.get("total", 0) > 0]
        if skill_entries:
            rows = skill_entries[-15:]
            msg += "\n\n📋 *Lịch sử gần nhất:*\n"
            for e in reversed(rows):
                skill    = e.get("skill", "?")
                provider = e.get("provider", "?")
                inp      = e.get("input_tok", 0)
                out      = e.get("output_tok", 0)
                total_e  = e.get("total", inp + out)
                lat      = e.get("latency_sec", 0.0)
                cache_r  = e.get("cache_read", 0)
                cache_s  = f" cache:{fmt(cache_r)}" if cache_r else ""
                ts       = e.get("ts", "")[:16].replace("T", " ")
                msg += (
                    f"• `{skill}` — {fmt(inp)}↑ {fmt(out)}↓{cache_s}"
                    f" = *{fmt(total_e)}* · `{provider}` · {lat:.0f}s"
                    f" _{ts}_\n"
                )

        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("lang_"):
        level = data.replace("lang_", "")  # "none" / "moderate" / "fluent"
        if level not in ("none", "moderate", "fluent"):
            return
        session.preferences["en_level"] = level
        await save_session(session)

        level_label = {
            "none": "🔴 Không rành — Em sẽ dùng thuần Việt",
            "moderate": "🟡 Hiểu cơ bản — Em dùng EN có giải thích",
            "fluent": "🟢 Thông thạo — Em dùng EN tự nhiên",
        }[level]

        try:
            await query.edit_message_text(
                f"✅ Em ghi nhận ạ: *{level_label}*",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass

        # Đã có name (first-time flow đã hỏi trước) → welcome menu
        name = session.preferences.get("user_name", "")
        greeting = f"Em chào sếp {name}! Vào việc thôi 👇" if name else "Vào việc thôi sếp 👇"
        await query.message.reply_text(
            f"{greeting}\n\n" + _personalize(WELCOME_MESSAGE, session),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # ── Menu navigation (tier 1 → tier 2) ─────────────────────────
    if data == "menu_main":
        # Clear advisor + persona markers khi về menu
        session.pending_intake.pop("_advisor_mode", None)
        session.pending_intake.pop("_active_persona", None)
        await save_session(session)
        try:
            await query.edit_message_text(
                WELCOME_MESSAGE,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=MAIN_MENU_KEYBOARD,
            )
        except Exception:
            # Nếu edit fail (message quá cũ), send new message
            await query.message.reply_text(
                WELCOME_MESSAGE,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=MAIN_MENU_KEYBOARD,
            )
        return

    if data in ("menu_strategic", "menu_operational", "menu_content_suite", "menu_analysis"):
        await query.edit_message_text(
            "📋 *Chọn chuyên gia bạn muốn làm việc cùng:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # ── Task 1: Viết Content — full workflow ─────────────────────
    if data == "task_write_content":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_workflow_task"] = "write_content"
        session.pending_intake["_workflow_awaiting_topic"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "✍️ *Max nhận yêu cầu viết content.*\n\n"
            "Sếp muốn viết về chủ đề gì? Gõ ngắn gọn ạ.\n"
            "_Vd: 'Hướng dẫn chọn serum Vitamin C cho da nhạy cảm' hoặc 'Giới thiệu sản phẩm mới tháng 6'_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Persona skill picker — user chọn skill từ domain expert ──
    if data.startswith("persona_menu_"):
        persona_key = data[len("persona_menu_"):]
        from agents.manager_personas import get_persona as _get_persona
        persona = _get_persona(persona_key)
        if not persona:
            await query.answer("Persona không tồn tại.")
            return
        await query.edit_message_reply_markup(reply_markup=None)

        # ── Linh (Brand Voice) — custom flow: check có/chưa có BV ──
        if persona_key == "brand":
            try:
                from storage import has_brand_voice
                _has_bv = await has_brand_voice(user_id)
            except Exception as e:
                logger.warning("[Linh] has_brand_voice check failed: %s", e)
                _has_bv = False
            if _has_bv:
                await query.message.reply_text(
                    "🎨 *Linh đây sếp!* Brand Voice của brand đã có sẵn rồi ạ.\n\n"
                    "Sếp muốn làm gì?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=LINH_BV_EXISTS_KEYBOARD,
                )
            else:
                await query.message.reply_text(
                    "🎨 *Linh đây sếp!* Brand chưa có Brand Voice.\n\n"
                    "Em tạo 1 lần thôi — dùng chung cho *toàn bộ business*, "
                    "tất cả skill creative (content, ads, video, email...) sẽ tự "
                    "tuân thủ đúng tone & từ ngữ brand. Output nhất quán hơn nhiều ạ.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=LINH_BV_NEW_KEYBOARD,
                )
            return

        # ── Nam (Content) — 2 mode: theo Calendar / viết bài mới ──
        if persona_key == "content":
            await query.message.reply_text(
                "✍️ *Nam đây sếp!* Sếp muốn viết content kiểu nào?\n\n"
                "📅 *Theo Lịch Nội Dung* — bám sát calendar đã duyệt, sản xuất hàng loạt.\n"
                "✍️ *Bài mới theo yêu cầu* — viết 1 bài lẻ, em hỏi sếp vài câu rồi viết.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=NAM_MODE_KEYBOARD,
            )
            return

        # ── Trang (TikTok) — 2 mode: theo Calendar / kịch bản mới ──
        if persona_key == "tiktok":
            await query.message.reply_text(
                "🎬 *Trang đây sếp!* Sếp muốn làm video kiểu nào?\n\n"
                "🎬 *Theo Lịch Nội Dung* — kịch bản cho các slot video trong calendar.\n"
                "📝 *Kịch bản mới* — 1 kịch bản lẻ theo yêu cầu, em hỏi creator type rồi viết.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=TRANG_MODE_KEYBOARD,
            )
            return

        from agents.task_registry import get_task as _get_task
        skill_list = persona.owns_skills
        intro = f"{persona.emoji} *{persona.name} — Chọn skill muốn chạy:*"

        # Max (CMO): khoá các phân tích lẻ cho tới khi đã chạy xong "full" A→Z —
        # tránh sếp chọn nhầm 1 mảnh nhỏ rồi thiếu context tổng thể. Sau khi có
        # "synthesis" (kết quả cuối của full), các skill lẻ mới mở ra để đào sâu/tinh chỉnh.
        if persona_key == "cmo" and not session.has_result("synthesis"):
            skill_list = ["full"]
            intro = (
                f"{persona.emoji} *{persona.name} đây sếp!*\n\n"
                "Để có context đầy đủ, mình bắt đầu với phân tích tổng thể trước nhé — "
                "sau khi xong, các công cụ đào sâu từng mảng (Đối thủ / Khách hàng / Giá...) "
                "sẽ tự mở khoá để sếp tinh chỉnh dựa trên kết quả này."
            )

        buttons = []
        for skill_name in skill_list:
            task_cfg = _get_task(skill_name)
            if task_cfg:
                label = f"{task_cfg.button_emoji} {task_cfg.label}"
            else:
                label = skill_name
            buttons.append([InlineKeyboardButton(label, callback_data=f"task_{skill_name}")])

        # Minh — thêm nút Báo Cáo Nhanh: xem chỉ số theo khung giờ (live/hôm qua/7 ngày),
        # pull trực tiếp + so sánh, không qua AI audit (nhanh hơn ads_analytics)
        if persona_key == "digital_marketing":
            buttons.append([InlineKeyboardButton("📈 Báo Cáo Nhanh — Ads", callback_data="ads_report_menu")])

        buttons.append([InlineKeyboardButton("↩ Hỏi thêm", callback_data="continue_advisor")])

        await query.message.reply_text(
            intro,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    # ── Linh (Brand Voice) custom callbacks ───────────────────────
    if data == "bv_view":
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            from storage import get_brand_voice as _get_bv
            bv = await _get_bv(user_id)
        except Exception as e:
            logger.warning("[Linh] get_brand_voice failed: %s", e)
            bv = None
        if bv and not bv.is_empty():
            body = (bv.rules_markdown or "").strip() or bv.to_prompt_block(max_chars=3000)
            await _send_bv_html(
                query.message, session, body,
                f"📋 *Brand Voice hiện tại (v{getattr(bv, 'version', 1)}):*",
                keyboard=LINH_BV_EXISTS_KEYBOARD,
            )
        else:
            await query.message.reply_text(
                "Chưa có Brand Voice ạ. Sếp tạo nhé?",
                reply_markup=LINH_BV_NEW_KEYBOARD,
            )
        return

    if data == "bv_create":
        await query.edit_message_reply_markup(reply_markup=None)
        session.selected_task = "brand_voice"
        session.pending_intake = {}
        await save_session(session)
        await _send_single_shot_form(query.message, session, "brand_voice")
        return

    if data == "bv_edit_chat":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_bv_edit_mode"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "✏️ *Sếp muốn chỉnh gì trong Brand Voice?*\n\n"
            "Cứ gõ tự nhiên cho em, ví dụ:\n"
            "• _\"Thêm tone hài hước nhẹ\"_\n"
            "• _\"Bỏ từ 'tuyệt vời nhất', nghe sáo\"_\n"
            "• _\"Xưng 'mình' với khách thay vì 'em'\"_\n"
            "• _\"Thêm rule: luôn có 1 câu hỏi cuối bài\"_\n\n"
            "Em sẽ cập nhật Brand Voice dùng chung cho toàn business.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── Nam (Content) mode callbacks ──────────────────────────────
    if data == "nam_mode_calendar":
        await query.edit_message_reply_markup(reply_markup=None)
        if not session.get_latest_result("content_calendar"):
            session.pending_followup_skill = "content_generator"
            await save_session(session)
            await query.message.reply_text(
                "✍️ *Viết theo Lịch Nội Dung cần có Calendar trước ạ.*\n\n"
                "Em chạy *Lịch Nội Dung* trước nhé — sau đó tự động sản xuất content theo lịch.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Chạy Lịch Nội Dung trước", callback_data="task_content_calendar")],
                    [InlineKeyboardButton("⏭️ Quay lại menu",              callback_data="menu_main")],
                ]),
            )
            return
        session.selected_task = "content_generator"
        session.pending_intake = {}
        await save_session(session)
        await _start_content_generation(query.message, session, weekly=False)
        return

    if data == "nam_mode_fresh":
        await query.edit_message_reply_markup(reply_markup=None)
        session.selected_task = "post_write"
        session.pending_intake = {}
        await save_session(session)
        await _send_single_shot_form(query.message, session, "post_write")
        return

    # ── Trang (TikTok) mode callbacks ─────────────────────────────
    if data == "trang_mode_calendar":
        await query.edit_message_reply_markup(reply_markup=None)
        if not session.get_latest_result("content_calendar"):
            session.pending_followup_skill = "video_script_gen"
            await save_session(session)
            await query.message.reply_text(
                "🎬 *Video theo Lịch cần có Calendar trước ạ.*\n\n"
                "Em chạy *Lịch Nội Dung* trước nhé — sau đó viết kịch bản cho các slot video.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Chạy Lịch Nội Dung trước", callback_data="task_content_calendar")],
                    [InlineKeyboardButton("⏭️ Quay lại menu",              callback_data="menu_main")],
                ]),
            )
            return
        session.selected_task = "video_script_gen"
        session.pending_intake = {}
        await save_session(session)
        await _send_single_shot_form(query.message, session, "video_script_gen")
        return

    if data == "trang_mode_fresh":
        await query.edit_message_reply_markup(reply_markup=None)
        session.selected_task = "video_scripts"
        session.pending_intake = {}  # content-first: KHÔNG ép chọn creator type
        await save_session(session)
        await _send_single_shot_form(query.message, session, "video_scripts")
        return

    # ── Khoa (Growth) channel focus picker ────────────────────────
    if data.startswith("growth_ch_"):
        ch_key = data[len("growth_ch_"):]  # all / zalo / email / sms
        ch_label = {
            "all":   "Full đa kênh",
            "zalo":  "Zalo OA",
            "email": "Email",
            "sms":   "SMS",
        }.get(ch_key, "Full đa kênh")
        skill_name = session.pending_intake.get("_growth_skill") or "retention_strategy"
        await query.edit_message_reply_markup(reply_markup=None)
        session.selected_task = skill_name
        session.pending_intake = {}  # fresh intake; channel_focus prefilled below
        session.pending_intake["channel_focus"] = ch_label
        await save_session(session)
        await _send_single_shot_form(query.message, session, skill_name)
        return

    # ── Variant choosers for special ops skills ───────────────────
    if data.startswith("ads_tier_"):
        tier = data.replace("ads_tier_", "")  # tofu / mofu / bofu / all
        session.pending_intake["selected_tiers"] = tier
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        # Sprint 5: Sau tier chọn → ask format (Video / Ảnh)
        tier_label = {"tofu": "TOFU (Tệp lạnh)", "mofu": "MOFU (Tệp ấm)",
                      "bofu": "BOFU (Tệp nóng)", "all": "All 3 tầng"}.get(tier, tier)
        await query.message.reply_text(
            f"✅ Tier: *{tier_label}*\n\nSếp muốn format Video hay Ảnh ạ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ADS_FORMAT_KEYBOARD,
        )
        return

    if data.startswith("ads_format_"):
        ads_format = data.replace("ads_format_", "")  # "video" or "image"
        session.pending_intake["ads_format"] = ads_format
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        skill_name = session.selected_task or "ads_generator"
        await _send_single_shot_form(query.message, session, skill_name)
        return

    # Sprint 5: Image generation flow ──────────────────────────────
    if data.startswith("img_gen_"):
        choice = data.replace("img_gen_", "")  # "1", "3", or "skip"
        if choice == "skip":
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                "OK ạ, em chỉ gửi brief thôi. Team design của sếp tự làm tiếp nhé.",
                reply_markup=stage_done_keyboard(is_last=True),
            )
            return

        n_images = int(choice) if choice.isdigit() else 1
        session.pending_intake["_img_n"] = str(n_images)
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"OK ạ, em sẽ tạo *{n_images} ảnh*. Sếp pick kích thước:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=IMAGE_SIZE_KEYBOARD,
        )
        return

    if data.startswith("img_size_"):
        size_choice = data.replace("img_size_", "")
        size_map = {"vertical": "1024x1536", "square": "1024x1024", "horizontal": "1536x1024"}
        img_size = size_map.get(size_choice, "1024x1024")
        n_images = int(session.pending_intake.get("_img_n", "1"))
        img_prompt = session.pending_intake.get("_img_prompt", "")

        if not img_prompt:
            await query.edit_message_text("⚠️ Chưa có brief ảnh để gen. Sếp /start lại.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"🎨 Em đang tạo {n_images} ảnh ({img_size})... (~30-60s)",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            from tools.image_gen import generate_image
            images = await generate_image(img_prompt, size=img_size, quality="medium", n=n_images)
            import io as _io
            last_image_bytes = None
            for i, img_bytes in enumerate(images, start=1):
                buf = _io.BytesIO(img_bytes)
                buf.name = f"ads_image_{i}.png"
                await query.message.reply_photo(
                    photo=buf,
                    caption=f"🖼️ Ảnh {i}/{n_images}",
                )
                last_image_bytes = img_bytes
            # Lưu ảnh cuối cùng (để edit nếu user muốn sửa)
            if last_image_bytes:
                import base64 as _b64
                session.pending_intake["_last_image_b64"] = _b64.b64encode(last_image_bytes).decode("ascii")
                session.pending_intake["_last_image_size"] = img_size
            await save_session(session)
            await query.message.reply_text(
                f"✅ *Em tạo xong {n_images} ảnh!*\n\nSếp muốn sửa hay chốt ảnh này ạ?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=IMAGE_REVIEW_KEYBOARD,
            )
        except Exception as e:
            logger.exception("Image gen failed: %s", e)
            await query.message.reply_text(
                f"⚠️ Gen ảnh thất bại: {str(e)[:200]}\n\nSếp check OPENAI_API_KEY trong Railway env vars."
            )
        return

    # ── Auto monitor flow ────────────────────────────────────────
    if data == "monitor_yes":
        # User chấp nhận → hỏi interval
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "⏰ *Em check mỗi bao lâu 1 lần ạ?*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MONITOR_INTERVAL_KEYBOARD,
        )
        return

    if data == "monitor_no":
        # Skip monitor → tiếp tục flow rating bình thường
        session.pending_intake.pop("_monitor_pending_page_id", None)
        session.pending_intake.pop("_monitor_pending_page_name", None)
        task_name = session.selected_task or "competitor_spy"
        session.pending_intake["_awaiting_rating_for"] = task_name
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "OK ạ! Sếp đánh giá output em vừa làm thế nào ạ?",
            reply_markup=RATING_KEYBOARD,
        )
        return

    if data.startswith("monitor_iv_"):
        # User chọn interval → lưu DB
        try:
            interval_hours = int(data.replace("monitor_iv_", ""))
        except ValueError:
            return

        page_id = session.pending_intake.get("_monitor_pending_page_id")
        page_name = session.pending_intake.get("_monitor_pending_page_name") or ""
        ad_ids_str = session.pending_intake.get("_fb_ad_ids", "")
        ad_ids = [aid for aid in ad_ids_str.split(",") if aid]

        if not page_id:
            await query.edit_message_text("⚠️ Có lỗi, sếp /start lại nhé.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        try:
            from storage.tracked_competitors import add_tracked
            ok = await add_tracked(
                user_id=user_id,
                page_id=page_id,
                page_name=page_name,
                interval_hours=interval_hours,
                ad_ids=ad_ids,
            )
            interval_label = {3: "3 giờ", 6: "6 giờ", 12: "12 giờ", 24: "1 ngày", 168: "1 tuần"}.get(interval_hours, f"{interval_hours}h")
            if ok:
                await query.message.reply_text(
                    f"✅ *Em sẽ theo dõi {page_name}!*\n\n"
                    f"_Mỗi {interval_label}, em check 1 lần và báo sếp ngay khi có ads mới._",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await query.message.reply_text(
                    "⚠️ Có lỗi khi lưu tracking. Em báo admin để fix ạ.",
                )
        except Exception as e:
            logger.exception("Add tracked failed: %s", e)
            await query.message.reply_text(
                f"⚠️ Lưu tracking thất bại: {str(e)[:200]}",
            )

        # Cleanup markers
        session.pending_intake.pop("_monitor_pending_page_id", None)
        session.pending_intake.pop("_monitor_pending_page_name", None)
        await save_session(session)

        # Tiếp tục rating
        task_name = session.selected_task or "competitor_spy"
        session.pending_intake["_awaiting_rating_for"] = task_name
        await save_session(session)
        await query.message.reply_text(
            "Tiện thể — sếp đánh giá output em vừa làm thế nào ạ?",
            reply_markup=RATING_KEYBOARD,
        )
        return

    if data.startswith("monitor_diff_"):
        # User click "Phân tích ads mới" từ notification
        page_id = data.replace("monitor_diff_", "")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "🔍 Em đang phân tích ads mới của đối thủ này...",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            from tools.fb_ads_library import search_by_page_id, format_ads_for_analysis
            ads = await search_by_page_id(page_id, country="VN", limit=10)
            # Chỉ phân tích N ads mới nhất (sort by start_time desc)
            ads_sorted = sorted(ads, key=lambda a: a.get("ad_delivery_start_time", ""), reverse=True)[:5]
            fb_data = format_ads_for_analysis(ads_sorted, "đối thủ")

            # Inject diff-mode data + run competitor_spy
            session.pending_intake["_fb_data"] = (
                "**[DIFF MODE — phân tích ads MỚI nhất]**\n\n" + fb_data +
                "\n\nFocus: đối thủ vừa thay đổi gì? Hint angle/strategy mới? Mình react thế nào (3 action cụ thể)?"
            )
            session.selected_task = "competitor_spy"
            await save_session(session)

            result = await run_operational_skill("competitor_spy", session)
            await save_session(session)
            await _send_ops_result(query.message, session, "competitor_spy", result)
        except Exception as e:
            logger.exception("Monitor diff analysis failed: %s", e)
            await query.message.reply_text(f"⚠️ Phân tích thất bại: {str(e)[:200]}")
        return

    if data == "monitor_skip_diff":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("OK ạ! Em tiếp tục theo dõi và báo sếp lần sau nhé.")
        return

    # Sprint 5 v2: Image reference upload flow
    if data == "img_ref_upload":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_image_reference"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "📤 *Sếp gửi ảnh mẫu vào đây nhé!*\n\n"
            "_Em sẽ phân tích style ảnh đó và làm theo._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "img_ref_skip":
        # Tự gen theo brief, không có ảnh mẫu
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_awaiting_image_reference", None)
        await save_session(session)
        await query.message.reply_text(
            "🎨 OK, em tự gen theo brief. Sếp muốn em tạo mấy ảnh ạ?",
            reply_markup=IMAGE_GEN_PROMPT_KEYBOARD,
        )
        return

    if data == "img_ref_no_gen":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake.pop("_awaiting_image_reference", None)
        # Set rating marker TRƯỚC khi reply
        session.pending_intake["_awaiting_rating_for"] = session.selected_task or ""
        await save_session(session)
        await query.message.reply_text(
            "OK ạ, em chỉ gửi copy thôi. Sếp đánh giá output em vừa làm thế nào ạ?",
            reply_markup=RATING_KEYBOARD,
        )
        return

    # Sprint 5 v2: Image review (Sửa / Chốt / Regen)
    if data == "img_edit":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_awaiting_image_edit"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "✏️ *Sếp muốn sửa gì ạ?*\n\n"
            "_Vd:_\n"
            "_• 'đổi nền sang biển'_\n"
            "_• 'thêm text \"Giảm 50%\" góc phải'_\n"
            "_• 'sáng hơn, ấm hơn'_\n"
            "_• 'bỏ logo bên góc trái'_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "img_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        # Clean image buffers + set rating marker BEFORE reply
        session.pending_intake.pop("_last_image_b64", None)
        session.pending_intake.pop("_last_image_size", None)
        session.pending_intake.pop("_img_n", None)
        session.pending_intake.pop("_img_prompt", None)
        session.pending_intake["_awaiting_rating_for"] = session.selected_task or ""
        await save_session(session)
        await query.message.reply_text(
            "✅ Chốt! Sếp đánh giá output em vừa làm thế nào ạ?",
            reply_markup=RATING_KEYBOARD,
        )
        return

    if data == "img_regen":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "🔁 OK, em gen ảnh khác. Mấy ảnh ạ?",
            reply_markup=IMAGE_GEN_PROMPT_KEYBOARD,
        )
        return

    if data.startswith("video_creator_"):
        creator = data.replace("video_creator_", "")  # ugc / egc / fgc / kol
        session.pending_intake["creator_type"] = creator
        # post-calendar flow uses video_script_gen (calendar-aware); standalone uses video_scripts
        vid_task = "video_script_gen" if session.pending_intake.pop("_after_cal_vid", None) else "video_scripts"
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        await _send_single_shot_form(query.message, session, vid_task)
        return

    # ── Coming Soon placeholder ───────────────────────────────────
    if data.startswith("coming_soon_"):
        skill_key = data.replace("coming_soon_", "")
        labels = {
            "campaign_brief":      "📋 Viết Brief Campaign",
            "ads_generator":       "📢 Sản Xuất Nội Dung Ads",
            "video_scripts":       "🎬 Viết Kịch Bản Video",
            "sales_inbox_script":  "💬 Kịch Bản Sales",
        }
        label = labels.get(skill_key, skill_key)
        await query.answer("Skill này sắp ra mắt", show_alert=False)
        await query.message.reply_text(
            f"🚧 *{label}* — sắp ra mắt!\n\n"
            f"_Skill này đang được hoàn thiện. Em sẽ thông báo sếp ngay khi ready._\n\n"
            f"Trong lúc chờ, sếp có thể chạy các skill khác từ menu nhé:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # ── Task selection ────────────────────────────────────────────
    if data.startswith("task_"):
        task_type = data[5:]

        # Pre-check token quota
        try:
            from tools.token_tracker import is_exhausted, get_used, get_quota, fmt
            if is_exhausted(session):
                await query.answer("Đã hết quota token", show_alert=True)
                await query.message.reply_text(
                    f"🔴 *Đã hết quota token!*\n\n"
                    f"Đã dùng: {fmt(get_used(session))} / {fmt(get_quota(session))}\n\n"
                    f"_Sếp liên hệ admin để nạp thêm hoặc chờ reset hàng tháng._",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
        except Exception as e:
            logger.warning("Token quota pre-check failed: %s", e)

        session.selected_task = task_type
        session.pending_intake = {}  # reset for fresh single-shot intake
        await save_session(session)

        # ── Khoa (Growth) — chọn kênh tập trung trước khi chạy ────
        # Nếu user vào lại qua growth_ch_* thì channel_focus đã prefill,
        # callback đó gọi thẳng _send_single_shot_form (không qua đây).
        if task_type in ("retention_strategy", "winback_campaign"):
            await query.edit_message_reply_markup(reply_markup=None)
            session.pending_intake["_growth_skill"] = task_type
            await save_session(session)
            task_label = get_task(task_type).label if get_task(task_type) else task_type
            await query.message.reply_text(
                f"🚀 *{task_label}* — sếp muốn tập trung kênh nào ạ?\n\n"
                "_Chọn 1 kênh để em viết sâu cho kênh đó, hoặc Full đa kênh "
                "để có hệ thống tổng thể (recommend)._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=GROWTH_CHANNEL_KEYBOARD,
            )
            return

        # ── competitor_comparison: soft-gate — có landscape thì so sánh sắc hơn ──
        if (task_type == "competitor_comparison"
                and not session.get_latest_result("competitor")):
            await query.edit_message_reply_markup(reply_markup=None)
            await save_session(session)
            await query.message.reply_text(
                "🆚 *So Sánh 1-1 Với Đối Thủ* — em chưa có phân tích competitor landscape ạ.\n\n"
                "Có landscape trước thì so sánh sẽ sắc hơn (em đối chiếu được vị trí đối thủ "
                "trong toàn cảnh). Không có em vẫn search Google được.\n\n"
                "Sếp muốn chạy *Phân Tích Đối Thủ* trước hay so sánh luôn?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Phân Tích Đối Thủ trước", callback_data="task_competitor")],
                    [InlineKeyboardButton("▶️ Vẫn so sánh luôn",         callback_data="force_comp_compare")],
                ]),
            )
            return

        # ── brand_positioning (Linh): cần T2 USP / T4 synthesis làm input ──
        if task_type == "brand_positioning" and not (
            session.get_latest_result("usp_definition")
            or session.get_latest_result("synthesis")
        ):
            await query.edit_message_reply_markup(reply_markup=None)
            session.pending_followup_skill = task_type
            await save_session(session)
            await query.message.reply_text(
                "🏛️ *Messaging House cần có USP + Strategy nền (T2/T4) làm input.*\n\n"
                "Em chưa có data của sếp — em refine từ phân tích, không làm lại từ đầu.\n\n"
                "Em chạy *Nghiên Cứu & Phân Tích Thị Trường* trước nhé. "
                "_Xong em tự động tiếp tục Messaging House cho sếp._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=NEEDS_STRATEGY_KEYBOARD,
            )
            return

        # ── Smart gating: skill cần Strategy base ─────────────────
        STRATEGY_GATED_SKILLS = {"campaign_brief", "content_calendar"}
        if task_type in STRATEGY_GATED_SKILLS:
            await query.edit_message_reply_markup(reply_markup=None)
            # Check session có synthesis result chưa
            has_strategy = bool(
                session.get_latest_result("synthesis")
                or session.get_latest_result("strategy")
            )
            if has_strategy:
                # campaign_brief → full A→Z flow: LLM-extracted campaigns
                # (extract_campaigns_from_synthesis) → offer lever → channel/budget
                # setup → brief. Same path as strategy_confirm, so the direct test
                # button produces the SAME complete brief (not the lean 3-question
                # shortcut). content_calendar keeps its lightweight strategy-aware form.
                if task_type == "campaign_brief":
                    await _ask_budget_team_before_campaigns(query.message, session)
                    return
                await _send_strategy_aware_form(query.message, session, task_type)
                return
            # NO branch — suggest A→Z
            task_label = (get_task(task_type).label if get_task(task_type) else task_type)
            session.pending_followup_skill = task_type  # store for chain
            await save_session(session)
            await query.message.reply_text(
                f"📋 *{task_label} chuyên sâu cần có Marketing Strategy nền.*\n\n"
                f"Em chưa có data Strategy của sếp.\n\n"
                f"Để output chính xác (đúng audience, đúng goals, đúng channels), "
                f"em chạy *Nghiên Cứu & Phân Tích Thị Trường* trước nhé. (~5-8 phút, 6 bước)\n\n"
                f"_Sau khi phân tích xong, em tự động tiếp tục {task_label} cho sếp._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=NEEDS_STRATEGY_KEYBOARD,
            )
            return

        # ── Content skills: cần Calendar trước ────────────────────
        if task_type in ("content_generator", "post_batch", "video_script_gen"):
            has_calendar = bool(session.get_latest_result("content_calendar"))
            if not has_calendar:
                await query.edit_message_reply_markup(reply_markup=None)
                session.pending_followup_skill = task_type
                await save_session(session)
                await query.message.reply_text(
                    "✍️ *Sản Xuất Nội Dung cần có Lịch Nội Dung trước ạ.*\n\n"
                    "Em chưa có Calendar của sếp.\n\n"
                    "Em chạy *Lịch Nội Dung* trước nhé — sau đó em tự động "
                    "tiếp tục sản xuất content theo lịch đó cho sếp.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📅 Chạy Lịch Nội Dung trước", callback_data="task_content_calendar")],
                        [InlineKeyboardButton("⏭️ Quay lại menu",              callback_data="menu_main")],
                    ]),
                )
                return

        # ── ugc_brief: soft-gate — gợi ý chạy Calendar trước, vẫn cho chạy luôn ─
        if task_type == "ugc_brief" and not session.get_latest_result("content_calendar"):
            await query.edit_message_reply_markup(reply_markup=None)
            await save_session(session)
            await query.message.reply_text(
                "🤝 *Brief Creator UGC* — em chưa thấy Lịch Nội Dung ạ.\n\n"
                "Có Calendar trước thì brief sẽ bám đúng kế hoạch (topic/pillar/kênh đã lên lịch). "
                "Sếp muốn chạy Calendar trước hay làm brief luôn?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Chạy Lịch Nội Dung trước", callback_data="task_content_calendar")],
                    [InlineKeyboardButton("▶️ Vẫn làm brief luôn",        callback_data="run_ugc_brief_after_cal")],
                ]),
            )
            return

        # ── Sprint 5: Brand Voice lazy gate cho creative ops skills ─
        if task_type in BRAND_VOICE_GATED_SKILLS:
            # Skip nếu user đã skip trong session này
            skipped_flag = session.pending_intake.get("_bv_skipped_session")
            if not skipped_flag:
                try:
                    from storage import has_brand_voice
                    has_bv = await has_brand_voice(user_id)
                except Exception as e:
                    logger.warning("[BV] has_brand_voice check failed: %s", e)
                    has_bv = True  # fail-safe: skip prompt nếu DB lỗi
                if not has_bv:
                    await query.edit_message_reply_markup(reply_markup=None)
                    # Lưu task gốc để resume sau khi BV setup xong
                    session.pending_intake["_bv_pending_skill"] = task_type
                    await save_session(session)
                    task_label = get_task(task_type).label if get_task(task_type) else task_type
                    await query.message.reply_text(
                        f"🎙 *Sếp chưa setup Brand Voice cho brand.*\n\n"
                        f"Em recommend setup 1 lần để các skill creative "
                        f"(*{task_label}*, post, ads, video, email...) tuân thủ đúng tone & "
                        f"từ ngữ brand — output nhất quán hơn 10x.\n\n"
                        f"_Sếp có thể bỏ qua giờ và setup sau, em vẫn chạy được skill này._",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=BRAND_VOICE_PROMPT_KEYBOARD,
                    )
                    return

        # Operational skills → single-shot form (or variant chooser first)
        if task_type in OPERATIONAL_TASKS:
            await query.edit_message_reply_markup(reply_markup=None)

            # Special skills with variant chooser
            if task_type in ("ads_copy", "ads_generator"):
                # Lưu real skill name (cùng AdsCopySkill class)
                session.selected_task = "ads_generator"
                await save_session(session)
                await query.message.reply_text(
                    "📢 *Sản Xuất Nội Dung Ads* — Sếp muốn gen tier nào trước ạ?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=ADS_COPY_TIER_KEYBOARD,
                )
                return
            if task_type == "video_scripts":
                await query.message.reply_text(
                    "🎬 *Viết Kịch Bản Video* — Brief cho loại creator nào ạ?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=VIDEO_CREATOR_KEYBOARD,
                )
                return

            # Standard ops: jump straight to single-shot form
            await _send_single_shot_form(query.message, session, task_type)
            return

        # ── Full pipeline: dedicated handler with resume detection ────
        if task_type == "full":
            await query.edit_message_reply_markup(reply_markup=None)
            import json as _jresume

            _has_synthesis = bool((session.get_latest_result("synthesis") or "").strip())
            _has_research  = any(session.has_result(k) for k in ("market_research", "competitor", "customer_insight"))
            try:
                _n_answers = len(_jresume.loads(session.pending_intake.get("_strategy_answers", "{}")))
            except Exception:
                _n_answers = 0

            # Pipeline bị kill giữa chừng (server restart/deploy) — stage đã set
            # nhưng chưa có kết quả nào được lưu
            if (
                session.stage == PipelineStage.MARKET_RESEARCH
                and not _has_research
                and not _has_synthesis
            ):
                await query.message.reply_text(
                    "⚡ *Bot vừa được cập nhật — pipeline trước bị gián đoạn.*\n\n"
                    "Em chưa kịp lưu kết quả nào. Sếp bấm để chạy lại từ đầu nhé!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Chạy lại ngay", callback_data="research_analyze")],
                    ]),
                )
                return

            if _has_synthesis:
                # Synthesis exists — interrupted before campaign selection
                await query.message.reply_text(
                    "📊 *Em thấy sếp đã có kế hoạch chiến lược từ lần trước!*\n\n"
                    "Hình như bị gián đoạn trước khi chọn campaign. "
                    "Sếp muốn tiếp tục hay chạy lại phân tích từ đầu?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Tiếp tục — chọn campaign", callback_data="strategy_confirm")],
                        [InlineKeyboardButton("🔄 Chạy lại từ đầu", callback_data="research_analyze")],
                    ]),
                )
                return

            if _has_research and _n_answers >= 8:
                # All 8 answers saved but synthesis not done → synthesis was interrupted
                await query.message.reply_text(
                    "📋 *Em thấy sếp đã trả lời đủ 8/8 câu chiến lược!*\n\n"
                    "Kế hoạch bị gián đoạn trước khi hoàn thành. Sếp bấm để em lập lại nhé.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Lập kế hoạch chiến lược", callback_data="resume_strategy_synthesis")],
                        [InlineKeyboardButton("🔄 Chạy lại toàn bộ từ đầu", callback_data="research_analyze")],
                    ]),
                )
                return

            if _has_research:
                # Research exists but questions not all answered
                _total_q = len(_STRATEGY_Q_KEYS)
                if _n_answers > 0:
                    _resume_text = (
                        f"📊 *Em thấy sếp đã có kết quả nghiên cứu "
                        f"+ trả lời {_n_answers}/{_total_q} câu chiến lược.*\n\n"
                        "Sếp muốn tiếp tục từ câu hỏi tiếp theo hay bắt đầu lại?"
                    )
                else:
                    _resume_text = (
                        "📊 *Em thấy sếp đã có kết quả nghiên cứu thị trường từ trước!*\n\n"
                        "Sếp muốn tiếp tục chọn hướng chiến lược hay chạy lại phân tích?"
                    )
                await query.message.reply_text(
                    _resume_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Tiếp tục — chọn hướng chiến lược", callback_data="resume_strategy_questions")],
                        [InlineKeyboardButton("🔄 Chạy lại toàn bộ từ đầu", callback_data="research_analyze")],
                    ]),
                )
                return

            # No research results → start pipeline intake directly
            await _send_single_shot_form(query.message, session, "full")
            return

        # ── Strategy-standalone: check existing synthesis / context ─
        if task_type == "strategy":
            await query.edit_message_reply_markup(reply_markup=None)
            _has_synthesis_s = bool((session.get_latest_result("synthesis") or "").strip())
            _has_research_s  = any(session.has_result(k) for k in (
                "market_research", "competitor", "customer_insight", "psychology_pricing"
            ))

            if _has_synthesis_s:
                # Already has a plan — ask if redo or menu
                await query.message.reply_text(
                    "🎯 *Em thấy sếp đã có kế hoạch chiến lược từ trước.*\n\n"
                    "Sếp muốn tạo lại kế hoạch hay quay về menu?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Tạo lại kế hoạch", callback_data="run_strategy_standalone")],
                        [InlineKeyboardButton("⬅️ Về menu chính",    callback_data="menu_main")],
                    ]),
                )
                return

            if _has_research_s or session.profile.is_basic_business_context_ready():
                # Has context → run strategy synthesis with direction from saved answers
                import json as _jstrat
                try:
                    _strat_answers = _jstrat.loads(session.pending_intake.get("_strategy_answers", "{}"))
                except Exception:
                    _strat_answers = {}
                _strat_direction = _format_strategy_answers(_strat_answers)

                if _strat_direction.strip():
                    # Have saved strategic direction → use it (full-quality synthesis)
                    await _run_strategy_plan(query.message, session, direction=_strat_direction)
                else:
                    # No answers saved → run synthesis with whatever context exists
                    await query.message.reply_text(
                        "🎯 *Em đang lập kế hoạch chiến lược dựa trên dữ liệu đã có...*",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    session.selected_task = "strategy"
                    await save_session(session)
                    await _proceed_after_confirm(query.message, session)
                return

            # No context at all → McKinsey Gate first
            await _send_basic_business_form(query.message, session, "strategy")
            return

        # ── Strategic skills ─────────────────────────────────────
        # Refine mode: nếu đã có bản phân tích mảng này VÀ đã chạy xong full A→Z,
        # cho sếp gõ yêu cầu chỉnh sửa tự do — cập nhật trên bản cũ thay vì làm lại từ đầu.
        # Tactical Playbook: chỉ chạy được khi có đủ SWOT + Synthesis
        if task_type == "tactical_playbook":
            if not session.has_result("synthesis"):
                await query.answer("⚠️ Cần chạy xong phân tích tổng thể (full A→Z) trước nhé sếp!", show_alert=True)
                return
            if not session.has_result("swot"):
                await query.answer("⚠️ Cần có SWOT trước — sếp chạy SWOT một lần rồi mình làm Playbook nhé!", show_alert=True)
                return

        # SWOT refine-mode: nếu đã có SWOT thì cho tinh chỉnh
        if task_type == "swot" and session.has_result("swot"):
            from agents.pipeline import STRATEGIC_RESULT_KEYS
            await query.edit_message_reply_markup(reply_markup=None)
            session.pending_intake = {"_awaiting_refine_for": "swot"}
            await save_session(session)
            await query.message.reply_text(
                "🔧 *SWOT — Tinh chỉnh trên bản đã có*\n\n"
                "Sếp gõ yêu cầu cụ thể, em sẽ cập nhật trên bản SWOT cũ:\n\n"
                "_Ví dụ: \"thêm mối đe dọa từ nền tảng X\", \"điểm yếu về distribution cần chi tiết hơn\"_",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        REFINABLE_STRATEGIC = {"market", "competitor", "customer", "pricing", "swot", "tactical_playbook"}
        if task_type in REFINABLE_STRATEGIC:
            from agents.pipeline import STRATEGIC_RESULT_KEYS
            result_key = STRATEGIC_RESULT_KEYS[task_type]
            if session.has_result(result_key) and session.has_result("synthesis"):
                await query.edit_message_reply_markup(reply_markup=None)
                session.pending_intake = {"_awaiting_refine_for": task_type}
                await save_session(session)
                task_label = get_task(task_type).label if get_task(task_type) else task_type
                await query.message.reply_text(
                    f"🔧 *{task_label} — Tinh chỉnh trên bản đã có*\n\n"
                    "Sếp gõ ngay yêu cầu cụ thể, em sẽ cập nhật trên bản phân tích cũ "
                    "(không chạy lại từ đầu):\n\n"
                    "_Ví dụ: \"thêm đối thủ ABC vào phân tích\", \"đào sâu hơn về pricing "
                    "của Cocoon\", \"audience đổi sang nhóm 35-45 tuổi rồi, cập nhật lại insight\"_",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

        # Phase 1.3: Profile reuse — nếu profile đã có required fields, skip intake
        if not needs_intake(session, task_type):
            await query.edit_message_reply_markup(reply_markup=None)
            await _show_profile_reuse_confirm(query.message, session, task_type)
            return

        # Strategic tasks dùng single-shot form với smart pre-fill:
        # - McKinsey Gate đã thu thập industry/product/target/goal → chỉ hỏi fields còn thiếu
        SINGLE_SHOT_STRATEGIC = {"market", "competitor", "customer", "pricing"}
        if task_type in SINGLE_SHOT_STRATEGIC:
            task = get_task(task_type)
            if task and task.intake_fields:
                await query.edit_message_reply_markup(reply_markup=None)
                await _send_single_shot_form(query.message, session, task_type)
                return

        # Fallback: multi-turn intake (task không có intake_fields khai báo)
        session.stage = PipelineStage.INTAKE
        await save_session(session)

        task_label = TASK_LABELS.get(task_type, "Phân tích")
        opening = TASK_OPENING_QUESTIONS.get(task_type, TASK_OPENING_QUESTIONS["full"])

        try:
            await query.edit_message_text(
                f"✅ *{task_label}*\n\n{opening}",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.warning("edit_message_text markdown failed: %s — retrying as plain text", e)
            await query.edit_message_text(f"✅ {task_label}\n\n{opening}")

    # ── Pipeline confirmation ─────────────────────────────────────
    elif data == "confirm_yes":
        await query.edit_message_reply_markup(reply_markup=None)
        # Nhắc nhẹ tên business 1 lần nếu còn thiếu (không bắt buộc)
        if await _maybe_nudge_bizname(query.message, session):
            return
        await _proceed_after_confirm(query.message, session)

    elif data == "bizname_skip":
        session.pending_intake.pop("_awaiting_bizname", None)
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        await _proceed_after_confirm(query.message, session)

    elif data == "confirm_no":
        # 1 user = 1 business: keep existing profile, let user correct specific fields only
        await query.edit_message_reply_markup(reply_markup=None)
        task = session.selected_task or "full"
        await _send_basic_business_form(query.message, session, task)

    # ── Ads Optimizer confirmation ────────────────────────────────
    elif data == "optimizer_confirm":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "⚡ *Đang thực thi...*",
            parse_mode=ParseMode.MARKDOWN,
        )
        summary = await _execute_optimizer_actions(session)
        await _safe_reply(
            query.message,
            f"✅ *Hoàn tất — Kết quả thực thi:*\n\n{summary}\n\n"
            f"_Kiểm tra lại trong Ads Manager để xác nhận thay đổi đã áp dụng._",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "optimizer_cancel":
        session.pending_intake.pop("_pending_actions", None)
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "❌ *Đã hủy.* Không có thay đổi nào được thực hiện.",
            parse_mode=ParseMode.MARKDOWN,
        )

    # ── Restart ───────────────────────────────────────────────────
    elif data == "restart":
        await reset_session(user_id)
        session = await get_session(user_id)
        session.stage = PipelineStage.TASK_SELECT
        await save_session(session)
        # Pattern an toàn: bỏ keyboard cũ, gửi tin mới (tránh edit failures với message cũ)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning("restart: edit_reply_markup failed: %s", e)
        await query.message.reply_text(
            "✅ Đã reset! Bạn muốn Max làm gì hôm nay?",
            reply_markup=TASK_SELECT_KEYBOARD,
        )

    elif data == "run_az_then_back":
        # User chấp nhận chạy A→Z, sau đó tự quay lại skill ban đầu
        # pending_followup_skill đã được set ở bước trước
        await query.edit_message_reply_markup(reply_markup=None)
        session.selected_task = "full"
        await save_session(session)

        # Nếu profile đã đủ → CONFIRMED, chạy luôn
        if session.profile.is_ready_for_analysis():
            session.stage = PipelineStage.CONFIRMED
            await save_session(session)
            await query.message.reply_text(
                "🔬 *Bắt đầu Nghiên Cứu & Phân Tích Thị Trường...*",
                parse_mode=ParseMode.MARKDOWN,
            )
            session.stage = PipelineStage.MARKET_RESEARCH
            await save_session(session)
            await _run_pipeline_sequentially(query.message, session)
        else:
            # Profile chưa đủ — collect basic context via single-shot form, then chain A→Z
            await _send_basic_business_form(query.message, session, "full")
        return

    elif data == "continue_pipeline":
        # Defensive: ngày trước button này show giữa intermediate stages,
        # giờ pipeline auto-run hết → button không nên reach. Fallback về menu.
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Pipeline đã chạy hết các bước rồi sếp. Sếp muốn làm gì tiếp?",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    elif data == "continue_advisor":
        await query.edit_message_reply_markup(reply_markup=None)
        session.pending_intake["_advisor_mode"] = "1"
        await save_session(session)
        await query.message.reply_text(
            "💬 Sếp gõ tiếp câu hỏi nhé!",
        )
        return

    elif data == "ask_followup":
        # Multi-turn Q&A về output skill vừa xong
        skill_name = session.selected_task
        session.pending_intake["_awaiting_followup_for"] = skill_name or ""
        session.stage = PipelineStage.COMPLETE
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "💬 *Sếp hỏi gì về output vừa rồi?*\n\n"
            "_Em trả lời bám sát kết quả em vừa đưa ra. "
            "Gõ thoải mái nhé._",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "rerun_current_task":
        # Chạy lại cùng task với input mới (fresh form, giữ profile)
        task_name = session.selected_task
        if not task_name:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                "⚠️ Em không nhớ task vừa chạy. Sếp chọn lại từ menu nhé.",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
            return

        # Clear intake cũ (giữ preferences, profile, results)
        session.pending_intake = {}
        await save_session(session)
        await query.edit_message_reply_markup(reply_markup=None)

        # Dispatch lại theo loại task
        SINGLE_SHOT_STRATEGIC = {"market", "competitor", "customer", "pricing"}

        if task_name in OPERATIONAL_TASKS:
            # Special skills cần variant chooser trước
            if task_name in ("ads_copy", "ads_generator"):
                await query.message.reply_text(
                    "📢 *Sản Xuất Nội Dung Ads* — Sếp muốn gen tier nào ạ?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=ADS_COPY_TIER_KEYBOARD,
                )
                return
            if task_name == "video_scripts":
                await query.message.reply_text(
                    "🎬 *Viết Kịch Bản Video* — Brief cho loại creator nào ạ?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=VIDEO_CREATOR_KEYBOARD,
                )
                return
            await _send_single_shot_form(query.message, session, task_name)
            return

        if task_name in SINGLE_SHOT_STRATEGIC:
            task = get_task(task_name)
            if task and task.intake_fields:
                await _send_single_shot_form(query.message, session, task_name)
                return

        # Full pipeline / strategy → confirm với profile cũ rồi chạy
        if not needs_intake(session, task_name):
            await _show_profile_reuse_confirm(query.message, session, task_name)
            return

        # Fallback: về menu
        await query.message.reply_text(
            "Sếp chọn task từ menu nhé:",
            reply_markup=MAIN_MENU_KEYBOARD,
        )


# ─── Pipeline runner ─────────────────────────────────────────────

def _format_card(stage_key: str, parsed: dict, token_entry: dict | None = None) -> str:
    """Build Format-B Telegram card from parsed agent output."""
    header = STAGE_HEADERS.get(stage_key, stage_key.upper())
    parts = [f"*{header}*", "━" * 25, ""]

    if parsed.get("insight"):
        insight = parsed["insight"].strip().strip('"').strip("'")
        parts.append("💡 *Insight quan trọng nhất:*")
        parts.append(f"_{_sanitize_telegram_md(insight)}_")
        parts.append("")

    if parsed.get("summary"):
        parts.append("📌 *Tóm tắt:*")
        parts.append(_sanitize_telegram_md(parsed["summary"].strip()))
        parts.append("")

    if parsed.get("benchmarks"):
        parts.append("📊 *Benchmarks:*")
        parts.append(_sanitize_telegram_md(parsed["benchmarks"].strip()))
        parts.append("")

    # If nothing parsed, fallback to raw detail (truncated)
    if not any(parsed.get(k) for k in ("insight", "summary", "benchmarks")):
        detail = parsed.get("detail", "")[:1500]
        parts.append(_sanitize_telegram_md(detail))

    parts.append("📎 _Xem full analysis trong file HTML cuối pipeline_")

    if token_entry:
        from tools.token_tracker import fmt as _fmt, _provider_label as _plabel
        provider  = _plabel(token_entry.get("provider", "?"))
        inp       = token_entry.get("input_tok", 0)
        out       = token_entry.get("output_tok", 0)
        total_tok = token_entry.get("total", inp + out)
        latency   = token_entry.get("latency_sec", 0.0)
        cache_r   = token_entry.get("cache_read", 0)
        cache_txt = f" · cache {_fmt(cache_r)}" if cache_r else ""
        parts.append(
            f"\n`⚡ {provider}` · {_fmt(inp)} vào + {_fmt(out)} ra"
            f"{cache_txt} = *{_fmt(total_tok)}* tokens · {latency:.1f}s"
        )

    return "\n".join(parts)


# ─── Operational skill flow ──────────────────────────────────────

OPS_INTAKE_AWAITING = "ops_intake_awaiting"  # marker stored in pending_intake

# McKinsey Discovery Gate — basic business context bắt buộc trước mọi skill
BIZ_CONTEXT_AWAITING       = "_awaiting_basic_biz_context"
BIZ_CONTEXT_PENDING_SKILL  = "_biz_pending_skill"

async def _show_profile_reuse_confirm(message: Message, session, task_name: str):
    """Phase 1.3: Strategic task có profile đầy đủ → show confirm card với data cũ,
    user pick confirm → chạy luôn pipeline, không multi-turn intake."""
    task = get_task(task_name)
    profile = session.profile
    label = task.label if task else task_name
    emoji = task.button_emoji if task else "🎯"

    fw = KPI_LIBRARY.get(profile.industry or "")
    industry_name = fw.display_name if fw else (profile.industry or "Chưa xác định")

    # Build profile recap — hiện tất cả fields đã thu thập
    profile_lines = []
    profile_lines.append(f"🏢 *Business*: {_escape_md(profile.business_name or 'Business của bạn')}")
    profile_lines.append(f"📦 *Sản phẩm/DV*: {_escape_md(profile.product_service or '—')}")
    profile_lines.append(f"👥 *Khách hàng*: {_escape_md(profile.target_customer or '—')}")
    profile_lines.append(f"📊 *Ngành*: {_escape_md(industry_name)}")
    if profile.stage:
        profile_lines.append(f"🚀 *Giai đoạn*: {_escape_md(profile.stage)}")
    if profile.location:
        profile_lines.append(f"📍 *Địa bàn*: {_escape_md(profile.location)}")
    if profile.monthly_revenue:
        profile_lines.append(f"💰 *Doanh thu*: {_escape_md(profile.monthly_revenue)}")
    if profile.monthly_marketing_budget:
        profile_lines.append(f"📣 *Ngân sách marketing*: {_escape_md(profile.monthly_marketing_budget)}")
    if profile.team_size:
        profile_lines.append(f"👤 *Quy mô team*: {_escape_md(profile.team_size)}")
    if profile.current_channels:
        profile_lines.append(f"📡 *Kênh hiện tại*: {_escape_md(profile.current_channels)}")
    if profile.primary_goal:
        profile_lines.append(f"🎯 *Mục tiêu*: {_escape_md(profile.primary_goal)}")
    if profile.main_challenge:
        profile_lines.append(f"⚡ *Thách thức*: {_escape_md(profile.main_challenge)}")
    if profile.competitors:
        profile_lines.append(f"🕵️ *Đối thủ*: {_escape_md(profile.competitors)}")
    if profile.usp:
        profile_lines.append(f"✨ *USP*: {_escape_md(profile.usp)}")

    confirm_msg = (
        f"{emoji} *{label}*\n\n"
        f"Tôi đã có thông tin business của bạn từ trước — không cần hỏi lại:\n\n"
        + "\n".join(profile_lines) + "\n\n"
        f"─────────────────────────\n"
        f"Bắt đầu *{label}* luôn nhé? 🚀\n"
        f"_(Nếu muốn cập nhật profile, bấm 'Sửa thông tin')_"
    )

    session.stage = PipelineStage.CONFIRMED
    await save_session(session)

    await _safe_reply(
        message,
        confirm_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=CONFIRM_KEYBOARD,
    )


async def _haiku_extract_intake(text: str, task_name: str, session) -> dict:
    """Dùng Haiku để extract free-form text → structured intake fields.
    Trả về dict {field_key: value}. Field nào không extract được thì bỏ qua.
    """
    import anthropic, json as _json
    from config import CLAUDE_HAIKU_MODEL, ANTHROPIC_API_KEY

    task = get_task(task_name)
    if not task:
        return {}

    fields_desc = "\n".join(
        f"- {f['key']} ({f['label']}): example = '{f.get('example', '')}'"
        for f in task.intake_fields
    )

    system = f"""Extract values từ user message thành JSON.

Task: {task.label}
Fields cần extract:
{fields_desc}

Output: JSON object với key = field name, value = string extracted từ user.
Nếu field không có trong message → bỏ qua, KHÔNG put null hay empty.
KHÔNG thêm field nào ngoài list trên.
Output CHỈ JSON object, không markdown, không giải thích."""

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        # Token tracking
        try:
            from tools.token_tracker import track_usage
            track_usage(session, response, label="intake_extract")
        except Exception:
            pass

        raw = response.content[0].text.strip()
        # Strip markdown code fence if present
        raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
        data = _json.loads(raw)
        # Validate: only keep declared field keys
        valid_keys = {f["key"] for f in task.intake_fields}
        return {k: str(v) for k, v in data.items() if k in valid_keys and v}
    except Exception as e:
        logger.warning("Haiku extract intake failed for %s: %s — text was: %s", task_name, e, text[:100])
        return {}


async def _send_strategy_aware_form(message: Message, session, task_name: str):
    """Khi user đã có Strategy (synthesis) — show form rút gọn.
    Form khác nhau theo skill:
    - campaign_brief: cần chọn campaign cụ thể (3 câu)
    - content_calendar: KHÔNG cần chọn campaign — chỉ hỏi duration/channel (2 câu)
    """
    task = get_task(task_name)
    if not task:
        await _send_single_shot_form(message, session, task_name)
        return

    # McKinsey discovery gate — fallback nếu strategy chưa có business context cơ bản
    if not session.profile.is_basic_business_context_ready():
        await _send_basic_business_form(message, session, task_name)
        return

    # ── Content Calendar — form siêu gọn, KHÔNG hỏi campaign ──
    if task_name == "content_calendar":
        profile = session.profile
        default_channels = profile.current_channels or "Facebook + TikTok + Zalo OA"
        lines = [
            f"✅ *{task.button_emoji} {task.label}*",
            "",
            "_Em đã có Marketing Strategy + ICP của sếp. Em sẽ build lịch tháng theo Story Arc 4 tuần + 4 nhóm khách._",
            "",
            "─────────────────────────",
            "*Sếp trả lời 2 ý nhanh (hoặc gõ 'mặc định' để em chạy luôn):*",
            "",
            "**1️⃣ Lên lịch cho tháng/tuần nào?**",
            "  _Vd: 'Tháng 1/2026' / 'Tuần này' / 'Tháng tới'_",
            "  _Mặc định: tháng tới_",
            "",
            "**2️⃣ Kênh nào sếp đang chạy?**",
            f"  _Em đoán: {default_channels}_",
            "  _Sếp confirm hoặc đổi (vd: 'chỉ TikTok + Zalo')_",
            "",
            "─────────────────────────",
            "💬 *Gõ 'mặc định' để chạy ngay với data có sẵn, hoặc trả lời theo format trên.*",
        ]

        session.pending_intake[OPS_INTAKE_AWAITING] = task_name
        session.pending_intake["_strategy_aware"] = "1"
        # Pre-fill defaults
        session.pending_intake.setdefault("duration", "Tháng tới (30 ngày)")
        session.pending_intake.setdefault("channels", default_channels)
        session.selected_task = task_name
        session.stage = PipelineStage.INTAKE
        await save_session(session)

        await message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
        return

    # Mọi task strategy-aware khác (vd campaign_brief) đã được route riêng ở handler
    # (campaign_brief → _show_extracted_campaigns / full A→Z). Fallback an toàn:
    await _send_single_shot_form(message, session, task_name)


async def _run_write_content_workflow_handler(message: Message, session, topic_text: str):
    """Task 1: Execute the write_content workflow and send results.

    Flow: Linh (brand_direction) → Nam (post_write) → Linh (post_voice_check).
    """
    from agents.workflow_runner import run_write_content_workflow

    await message.reply_text("🔄 *Max đang điều phối team...*", parse_mode=ParseMode.MARKDOWN)
    await message.chat.send_action(ChatAction.TYPING)

    async def on_progress(text: str):
        try:
            await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass

    result = await run_write_content_workflow(
        session,
        topic=topic_text,
        on_progress=on_progress,
    )

    if result["success"]:
        await save_session(session)
        output = result["final_output"]
        if len(output) > 4000:
            for i in range(0, len(output), 4000):
                chunk = output[i:i + 4000]
                if i + 4000 >= len(output):
                    await message.reply_text(chunk, reply_markup=get_action_keyboard("post_write"))
                else:
                    await message.reply_text(chunk)
        else:
            await message.reply_text(output, reply_markup=get_action_keyboard("post_write"))
    else:
        await message.reply_text(
            f"⚠️ Workflow gặp lỗi ở bước {result.get('error', 'unknown')}. Sếp thử lại sau ạ.",
            reply_markup=get_action_keyboard("post_write"),
        )


async def _send_single_shot_form(message: Message, session, task_name: str, _skip_account_pick: bool = False):
    """Send a paste-template form for ops skill intake.
    User fills in template, replies once with all fields.

    Sprint UX: Basic Business Context Gate + Smart Pre-fill.
    1. Trước khi ANY skill chạy, đảm bảo có 5 fields cơ bản
       (industry, product, target_customer, stage, primary_goal).
    2. Pre-fill các fields đã có trong profile vào pending_intake →
       form chỉ hiện những câu CHƯA biết (loại bỏ duplicate question).
    3. Nếu profile đã đủ → SKIP form, chạy skill luôn.
    """
    task = get_task(task_name)
    if not task:
        await message.reply_text(f"⚠️ Skill {task_name} không tồn tại.")
        return

    intake_fields = task.intake_fields
    if task_name == "content_generator" and session.pending_intake.get("scope"):
        # Weekly mode (scope đã chốt = "Tuần N" ở _handle_week_selection_text)
        # — field "weeks" (Lên plan mấy tuần?) không còn ý nghĩa, scope đã
        # quyết định phạm vi chạy. Bỏ khỏi form, không prefill, không hỏi.
        intake_fields = [f for f in intake_fields if f["key"] != "weeks"]

    # Ads tasks pull data từ 1 Ad Account cụ thể — nếu user có nhiều account,
    # cho chọn account trước khi vào form (tránh audit/phân tích nhầm account).
    if task_name == "ads_analytics" and not _skip_account_pick:
        from storage.fb_connections import get_connection, get_available_accounts
        conn = await get_connection(session.user_id)
        if conn:
            accounts = await get_available_accounts(session.user_id)
            if len(accounts) > 1:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                active_id = conn.get("ad_account_id", "")
                buttons = []
                for a in accounts[:10]:
                    aid = a.get("id", "")
                    norm = aid if aid.startswith("act_") else f"act_{aid}"
                    is_active = (norm == active_id or aid == active_id)
                    label = ("✅ " if is_active else "○ ") + (a.get("name") or aid)
                    buttons.append([InlineKeyboardButton(label, callback_data=f"aud_pick:{aid}:{task_name}")])
                await message.reply_text(
                    "🔄 *Sếp có nhiều Ad Account — chọn account muốn phân tích trước nhé:*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return

    # Ads Optimizer — hiện list campaign trong account dạng nút bấm để user
    # chọn thẳng (đỡ phải gõ đúng tên), thay vì bắt nhập tay ngay từ đầu.
    # Bỏ qua nếu đã có target (user chọn rồi, hoặc bấm "nhập tay").
    if (task_name == "ads_optimizer"
            and not session.pending_intake.get("target")
            and not session.pending_intake.get("_optimizer_skip_pick")):
        from storage.fb_connections import get_connection
        conn = await get_connection(session.user_id)
        if conn:
            try:
                from tools.crypto import decrypt_token
                from tools.fb_marketing import get_active_campaigns
                token = decrypt_token(conn["encrypted_token"])
                campaigns = await get_active_campaigns(ad_account_id=conn["ad_account_id"], access_token=token)
            except Exception as e:
                logger.warning("[AdsOptimizer] load campaigns for picker failed: %s", e)
                campaigns = []

            if campaigns:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                _STATUS_ICON = {"ACTIVE": "🟢", "PAUSED": "⏸"}
                choices: dict[str, str] = {}
                buttons = []
                for i, c in enumerate(campaigns[:15]):
                    cid  = c.get("id") or str(i)
                    name = (c.get("name") or "Campaign").replace("*", "").replace("_", "-")
                    icon = _STATUS_ICON.get(c.get("status"), "⚪")
                    choices[cid] = name
                    buttons.append([InlineKeyboardButton(f"{icon} {name[:40]}", callback_data=f"opt_pick:{cid}")])
                buttons.append([InlineKeyboardButton("✍️ Khác — Ad Set / Ad / nhập tay", callback_data="opt_pick:_custom")])

                session.pending_intake["_optimizer_choices"] = choices
                await save_session(session)
                await message.reply_text(
                    "⚡ *Sếp muốn thao tác campaign nào?*\n\n"
                    "_Chọn 1 campaign trong list, hoặc nhập tay nếu muốn nhắm Ad Set / Ad cụ thể._",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return

    # ── McKinsey discovery gate — basic context required ──────
    if not session.profile.is_basic_business_context_ready():
        await _send_basic_business_form(message, session, task_name)
        return

    # ── Self-heal: tách location khỏi target_customer nếu profile cũ có lẫn ──
    p = session.profile
    if p.target_customer and not p.location:
        _VN_CITIES = [
            r"\bHà Nội\b", r"\bHCM\b", r"\bTP\.?\s*HCM\b", r"\bSài Gòn\b",
            r"\bĐà Nẵng\b", r"\bHải Phòng\b", r"\bCần Thơ\b", r"\bNha Trang\b",
            r"\bVũng Tàu\b", r"\bBiên Hòa\b", r"\bHuế\b",
        ]
        for pat in _VN_CITIES:
            m = re.search(pat, p.target_customer, re.IGNORECASE)
            if m:
                p.location = m.group(0).strip()
                cleaned = re.sub(pat, "", p.target_customer, flags=re.IGNORECASE).strip(" ,;.-")
                if cleaned:
                    p.target_customer = cleaned
                await save_session(session)
                break

    # ── Smart Pre-fill: map task field keys → profile attributes
    _PROFILE_KEY_MAP = {
        "industry":          "industry",
        "product_service":   "product_service",
        "product":           "product_service",       # ads_generator alias
        "target_customer":   "target_customer",
        "primary_goal":      "primary_goal",
        "campaign_goal":     "primary_goal",          # heuristic fallback
        "location":          "location",
        "monthly_revenue":   "monthly_revenue",
        "main_challenge":    "main_challenge",
        "competitors":       "competitors",
        "current_channels":  "current_channels",
        "team_size":         "team_size",
    }

    prefilled: dict[str, str] = {}
    for f in intake_fields:
        key = f["key"]
        profile_attr = _PROFILE_KEY_MAP.get(key)
        if not profile_attr:
            continue
        val = getattr(session.profile, profile_attr, None)
        if val and isinstance(val, str) and val.strip():
            prefilled[key] = val.strip()

    # Inject vào pending_intake để skill dùng được
    for k, v in prefilled.items():
        session.pending_intake[k] = v

    # ── content_calendar "channels": đã chốt ở câu 7/8 chiến lược
    # (_strategy_answers["channels"]) hoặc trong campaign đã chọn — không hỏi lại.
    if task_name == "content_calendar" and "channels" not in prefilled:
        import json as _json

        channels_val = ""
        try:
            _strat = _json.loads(session.pending_intake.get("_strategy_answers", "{}"))
            channels_val = (_strat.get("channels") or "").strip()
        except (_json.JSONDecodeError, AttributeError):
            pass
        if not channels_val:
            try:
                _camp = _json.loads(session.pending_intake.get("_chosen_campaign", "{}"))
                channels_val = (_camp.get("channels") or "").strip()
            except (_json.JSONDecodeError, AttributeError):
                pass
        if channels_val:
            prefilled["channels"] = channels_val
            session.pending_intake["channels"] = channels_val

    # ── Campaign Brief pre-fill: nếu đã có brief thì dùng làm base ──
    if task_name == "content_generator":
        brief_result = session.get_latest_result("campaign_brief")
        if brief_result:
            intake = session.pending_intake
            _brief_map = {
                # field key         ← pending_intake source
                "ads_usp":          intake.get("key_offer") or intake.get("campaign_goal"),
                "weeks":            intake.get("duration"),
                "highlight_angles": intake.get("campaign_goal") or intake.get("campaign_name"),
            }
            _intake_field_keys = {f["key"] for f in intake_fields}
            for key, val in _brief_map.items():
                if key not in _intake_field_keys:
                    continue
                if val and key not in prefilled:
                    prefilled[key] = str(val).strip()
                    session.pending_intake[key] = str(val).strip()
            # Thông báo source cho user
            _brief_name = intake.get("campaign_name") or intake.get("current_campaign") or "Campaign Brief"
            prefilled["_brief_source"] = _brief_name  # dùng để hiển thị, không phải field thật

    # Fields còn lại cần hỏi user.
    # Bỏ qua field đã prefill từ profile HOẶC đã set sẵn trong pending_intake
    # (vd channel_focus do nút chooser của Khoa set) → không hỏi lại.
    remaining_fields = [
        f for f in intake_fields
        if f["key"] not in prefilled and not session.pending_intake.get(f["key"])
    ]

    # ── Build form ────────────────────────────────────────────
    lines = [
        f"✅ *{task.button_emoji} {task.label}*",
        "",
        f"_{task.description}_",
        "",
    ]

    if prefilled:
        _brief_source = prefilled.pop("_brief_source", None)
        _display_prefilled = {k: v for k, v in prefilled.items()}
        if _brief_source:
            lines.append(f"*Em dùng Campaign Brief _{_escape_md(_brief_source)}_ làm base:*")
        else:
            lines.append("*Em đã có sẵn từ business profile của sếp:*")
        for k, v in _display_prefilled.items():
            label = next((f["label"] for f in intake_fields if f["key"] == k), k)
            lines.append(f"• *{label}:* {_escape_md(v[:120])}")
        lines.append("")
        if remaining_fields:
            lines.append("─────────────────────────")
            lines.append(f"*Em chỉ cần thêm {len(remaining_fields)} ý nữa — gõ tự do, em parse:*")
        else:
            lines.append("─────────────────────────")
            lines.append("*Em không cần hỏi thêm gì — gõ `ok` để em chạy luôn.*")
    else:
        lines.append("─────────────────────────")
        lines.append("*Copy template dưới, điền vào (hoặc thay example), gửi lại 1 lần:*")

    lines.append("")
    for f in remaining_fields:
        required_mark = "" if f.get("required", True) else " _(không bắt buộc)_"
        lines.append(f"*{f['label']}*{required_mark}:")
        lines.append(f"_Vd: {f.get('example', '...')}_")
        # Gợi ý 'thông điệp chính' video dựa trên Business + tâm lý mua của ngành
        if task_name == "video_scripts" and f["key"] == "key_message":
            hint = suggest_key_message_hint(
                session.profile.industry or "",
                session.profile.product_service or "",
                session.profile.target_customer or "",
            )
            if hint:
                lines.append(hint)
        lines.append("")

    if remaining_fields:
        lines.append("─────────────────────────")
        lines.append("💬 *Gửi tin trả lời theo format trên — Max sẽ tự parse và chạy.*")

    # Mark session as waiting for ops intake
    session.pending_intake[OPS_INTAKE_AWAITING] = task_name
    session.selected_task = task_name
    session.stage = PipelineStage.INTAKE
    await save_session(session)

    await _safe_reply(message, "\n".join(lines), parse_mode=ParseMode.MARKDOWN)


def _parse_single_shot_intake(text: str, task_name: str) -> dict:
    """Parse user's pasted template response.
    Strategy: extract value after each field label (case-insensitive match).
    Falls back to splitting by newlines if pattern unclear."""
    task = get_task(task_name)
    if not task:
        return {}

    parsed = {}
    text_lines = text.split("\n")

    # Build label → key map (case-insensitive)
    label_to_key = {f["label"].lower().strip(): f["key"] for f in task.intake_fields}

    current_field_key = None
    current_value_parts: list[str] = []

    for line in text_lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Match "Label: value" or "*Label*: value" — extract label
        label_match = re.match(r"^[*_]*([^:*_]+?)[*_]*\s*:\s*(.*)$", line_stripped)
        if label_match:
            label_candidate = label_match.group(1).strip().lower()
            value_inline = label_match.group(2).strip()

            # Check if this label is one of our fields
            matched_key = None
            for label, key in label_to_key.items():
                if label_candidate == label or label_candidate.startswith(label[:15]):
                    matched_key = key
                    break

            if matched_key:
                # Save previous field
                if current_field_key and current_value_parts:
                    parsed[current_field_key] = " ".join(current_value_parts).strip()
                # Start new field
                current_field_key = matched_key
                current_value_parts = [value_inline] if value_inline else []
                continue

        # No label match — append to current field value
        if current_field_key:
            current_value_parts.append(line_stripped)

    # Save last field
    if current_field_key and current_value_parts:
        parsed[current_field_key] = " ".join(current_value_parts).strip()

    return parsed


async def _handle_feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE, session, text: str):
    """Sprint 2: User gửi feedback text sau khi rate ≤3.
    Save feedback, hỏi user có muốn regen không."""
    skill_name = session.pending_intake.get("_awaiting_feedback_for")
    if not skill_name:
        return

    # Update last feedback entry với text
    if session.feedback.get(skill_name):
        session.feedback[skill_name][-1]["feedback"] = text
        # Persist updated feedback to DB feedback_log
        last_rating = session.feedback[skill_name][-1].get("rating", 0)
        try:
            await _log_feedback_to_db(session, skill_name, last_rating, text)
        except Exception as e:
            logger.warning("Feedback DB log failed (non-blocking): %s", e)

    # Store pending feedback for regen decision
    session.pending_intake["_pending_feedback"] = text
    session.pending_intake["_pending_regen_skill"] = skill_name
    session.pending_intake.pop("_awaiting_feedback_for", None)
    await save_session(session)

    # Try detect source mention từ Max's previous output (Layer 3 simplified)
    versions = session.results.get(skill_name, [])
    last_output = versions[-1].content if versions else ""
    KNOWN_SOURCES = ["Statista", "GSO", "Tổng cục Thống kê", "WorldBank", "World Bank",
                     "Nielsen", "Q&Me", "Decision Lab", "Vietcetera", "CafeF",
                     "VnEconomy", "Brands Vietnam", "Adsota", "Kantar"]
    cited = [s for s in KNOWN_SOURCES if s in last_output]

    if cited:
        # Max output có cite source → bot hỏi user có nguồn không
        msg = (
            f"Em note rồi ạ.\n\n"
            f"Em hiểu sếp nói output em có chỗ chưa đúng. Em note rằng output trước em có dẫn nguồn từ "
            f"*{', '.join(cited[:2])}*.\n\n"
            f"Sếp có nguồn nào khác đáng tin hơn không ạ? Hoặc em chạy lại với feedback của sếp luôn?"
        )
    else:
        msg = (
            "Em note rồi ạ. Sếp có muốn em chạy lại ngay với feedback này không?\n\n"
            "_Em sẽ giữ nguyên context của sếp, chỉ điều chỉnh theo correction sếp đưa._"
        )

    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=REGEN_PROMPT_KEYBOARD,
    )

    # Log feedback
    logger.info("Feedback collected for %s: %s", skill_name, text[:200])


async def _handle_ops_intake_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, session, text: str):
    """Handle user's paste reply for single-shot form (ops + strategic single-skill).
    Phase 3: also handles strategic single-skill tasks (market/competitor/customer/pricing).
    """
    task_name = session.pending_intake.get(OPS_INTAKE_AWAITING)
    if not task_name:
        return

    # Shortcut: nếu user gõ "mặc định" / "default" / "chạy luôn" / "ok"
    # → bỏ qua parse, dùng defaults đã pre-fill trong _strategy_aware form
    text_lower = text.strip().lower()
    SKIP_KEYWORDS = ("mặc định", "mac dinh", "default", "chạy luôn", "chay luon",
                     "ok chạy", "ok chay", "ok luôn", "ok luon", "chạy đi", "chay di",
                     "ok", "yes", "có", "đồng ý", "dong y", "ừ", "uh", "okela")
    if text_lower in SKIP_KEYWORDS or any(text_lower.startswith(kw + " ") for kw in SKIP_KEYWORDS):
        # Defaults đã được pre-fill ở _send_strategy_aware_form, dùng nguyên
        parsed = {}
    else:
        # Strategy-aware form + A→Z (full): dùng Haiku extract free-form nếu structured parse fail.
        # "full" cũng cần fallback vì user hay gõ tự do, không kèm nhãn field → parser rigid miss.
        is_strategy_aware = session.pending_intake.get("_strategy_aware") == "1"
        parsed = _parse_single_shot_intake(text, task_name)
        # Số field structured parse bắt được; nếu thiếu so với field cần hỏi → text free-form
        _task_obj = get_task(task_name)
        _expected = len(_task_obj.intake_fields) if _task_obj else 2
        _need_fallback = len([v for v in parsed.values() if v]) < min(2, _expected)
        if (is_strategy_aware or task_name == "full") and _need_fallback:
            try:
                parsed_haiku = await _haiku_extract_intake(text, task_name, session)
                # Merge: parsed_haiku ưu tiên nếu structured parse rỗng
                for k, v in parsed_haiku.items():
                    if v and not parsed.get(k):
                        parsed[k] = v
            except Exception as e:
                logger.warning("Haiku intake extract failed: %s", e)

    # Strategic single-shot: also merge parsed values into session.profile
    # (so future skills can reuse via profile reuse logic)
    SINGLE_SHOT_STRATEGIC = {"market", "competitor", "customer", "pricing"}
    if task_name in SINGLE_SHOT_STRATEGIC or task_name == "full":
        profile = session.profile
        for k, v in parsed.items():
            if v and hasattr(profile, k):
                setattr(profile, k, v)
        if not profile.industry and parsed.get("product_service"):
            inferred = _infer_industry(parsed["product_service"], parsed.get("target_customer", ""))
            if inferred:
                profile.industry = inferred

    # Merge into pending_intake (preserves variant chooser values like selected_tiers)
    for k, v in parsed.items():
        session.pending_intake[k] = v

    session.pending_intake.pop(OPS_INTAKE_AWAITING, None)

    # "full" task: sau khi collect missing fields → show confirm card → pipeline
    if task_name == "full":
        session.selected_task = "full"
        session.stage = PipelineStage.CONFIRMED
        await save_session(session)
        await _show_profile_reuse_confirm(update.message, session, "full")
        return

    await save_session(session)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    task_label = get_task(task_name).label if get_task(task_name) else task_name
    await update.message.reply_text(
        f"⚡ *Đang chạy {task_label}...*\nThời gian dự kiến: 30-90 giây.",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        from config import AGENT_TIMEOUT
        # Pre-fetch live FB data cho các skills cần
        if task_name == "competitor_spy":
            fb_status = await _prefetch_competitor_ads(update.message, session)
            # Merge pasted_ads (manual fallback) vào _fb_data nếu user paste tay
            pasted = (session.pending_intake.get("pasted_ads") or "").strip()
            if pasted and len(pasted) > 30:
                existing = session.pending_intake.get("_fb_data", "")
                merged = (
                    (existing + "\n\n---\n\n" if existing else "")
                    + "**ADS USER PASTE TAY:**\n\n" + pasted
                )
                session.pending_intake["_fb_data"] = merged
            if not session.pending_intake.get("_fb_data"):
                await _abort_with_fb_error(update.message, session, "competitor_spy", fb_status)
                return
        elif task_name == "ads_analytics":
            fb_status = await _prefetch_performance_data(update.message, session)
            has_live = bool(session.pending_intake.get("_fb_data"))
            channels = (session.pending_intake.get("channels_data") or "").strip()
            import re as _re
            has_manual = bool(channels and len(channels) >= 20 and _re.search(r"\d", channels))
            if not has_live and not has_manual:
                # Không có live data và không có paste tay → abort, hướng dẫn cả 2 cách
                session.stage = PipelineStage.TASK_SELECT
                session.pending_intake.pop(OPS_INTAKE_AWAITING, None)
                await save_session(session)
                reason = fb_status.get("reason", "no_token")
                detail = fb_status.get("detail", "")
                if reason in ("no_token", "no_account"):
                    api_note = f"FB API chưa cấu hình ({_md_detail(detail)})."
                elif reason == "api_error":
                    api_note = f"FB API lỗi: {_md_detail(detail[:150])}."
                else:
                    api_note = "FB API không trả về data."
                await update.message.reply_text(
                    "🛑 *Không có data để phân tích.*\n\n"
                    f"{api_note}\n\n"
                    "*Cách 1 — Kết nối FB API:* Admin set `FB_ACCESS_TOKEN` + `FB_AD_ACCOUNT_ID` trên Railway.\n\n"
                    "*Cách 2 — Paste số tay:* Chạy lại skill, điền vào ô *Paste số liệu thủ công*.\n"
                    "Ví dụ: `Meta: 800 mess, CPMess 19K, CTR 1.2%, Frequency 3.8`",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
        elif task_name == "ads_intelligence":
            # 1. Prefetch competitor ads (FB Ads Library)
            spy_status = await _prefetch_competitor_ads(update.message, session)
            pasted = (session.pending_intake.get("pasted_ads") or "").strip()
            if pasted and len(pasted) > 30:
                existing = session.pending_intake.get("_fb_data", "")
                session.pending_intake["_fb_data"] = (
                    (existing + "\n\n---\n\n" if existing else "") + "**ADS USER PASTE TAY:**\n\n" + pasted
                )
            session.pending_intake["_fb_data_spy"] = session.pending_intake.pop("_fb_data", "") or ""
            # 2. Prefetch account analytics (FB Marketing API)
            await _prefetch_performance_data(update.message, session)
            session.pending_intake["_fb_data_analytics"] = session.pending_intake.pop("_fb_data", "") or ""
            # Gate: cần ít nhất 1 nguồn data
            if not session.pending_intake.get("_fb_data_spy") and not session.pending_intake.get("_fb_data_analytics"):
                await _abort_with_fb_error(update.message, session, "ads_intelligence", spy_status)
                return
        elif task_name == "ads_optimizer":
            fb_status = await _prefetch_optimizer_data(update.message, session)
            if not session.pending_intake.get("_optimizer_hierarchy"):
                await _abort_with_fb_error(update.message, session, "ads_optimizer", fb_status)
                return

        # Dispatch theo task type
        if task_name in SINGLE_SHOT_STRATEGIC:
            from agents.pipeline import run_strategic_single_skill
            result = await asyncio.wait_for(
                run_strategic_single_skill(task_name, session),
                timeout=AGENT_TIMEOUT,
            )
            session.stage = PipelineStage.TASK_SELECT
            await save_session(session)
            await _send_ops_result(update.message, session, task_name, result)
        else:
            result = await asyncio.wait_for(
                run_operational_skill(task_name, session),
                timeout=AGENT_TIMEOUT,
            )
            # Skill done — reset stage so next message goes to menu/advisor, not intake handler
            session.stage = PipelineStage.TASK_SELECT
            await save_session(session)

            # Ads Optimizer: clean display text (strip markers), then show confirmation separately
            if task_name == "ads_optimizer":
                clean_result = _ACTION_RE.sub("", result).strip()
                await _send_ops_result(update.message, session, task_name, clean_result)
                await _show_optimizer_confirm(update.message, session, result)
                return

            await _send_ops_result(update.message, session, task_name, result)

            # Backlog 2.2: brand_positioning — revise loop (sửa đến khi sếp chốt)
            if task_name == "brand_positioning":
                await update.message.reply_text(
                    "🏛️ *Messaging House nháp xong rồi sếp!*\n\n"
                    "Sếp xem qua — muốn sửa gì không ạ? Chốt rồi thì mọi content "
                    "Nam/Trang viết sau này đều bám messaging house này.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Chốt bản này", callback_data="bp_confirm")],
                        [InlineKeyboardButton("✏️ Sửa thêm",     callback_data="bp_edit_request")],
                    ]),
                )
                return

            # Sprint 6: Tone Calibration Loop cho content_calendar
            if task_name == "content_calendar":
                await _start_tone_calibration(update.message, session, result)
                return

            # Layer 3: sau khi xong 1 kênh — hỏi tiếp kênh khác (chạy từng kênh 1)
            if task_name == "content_generator":
                remaining = session.pending_intake.get("_content_channels_remaining") or []
                channel_done = session.pending_intake.get("channel_focus")
                if remaining:
                    done_label = f" cho kênh *{channel_done}*" if channel_done else ""
                    await update.message.reply_text(
                        f"✅ Xong nội dung{done_label}!\n\n"
                        "Sếp muốn tiếp tục kênh nào tiếp theo?",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=_channel_pick_keyboard(remaining, extra_done_button=True),
                    )
                    return

            # Sprint 5: Show Brand Voice draft for user approval before persisting.
            # Deliverable (card + files) đã gửi xong ở trên — now ask to approve.
            if task_name == "brand_voice":
                session.pending_intake["_bv_draft"] = result
                await save_session(session)
                await update.message.reply_text(
                    "👆 *Brand Voice draft xong rồi sếp!*\n\n"
                    "Sếp xem qua rồi bấm *Duyệt & Lưu* để em lưu lại — "
                    "từ đó tất cả nội dung em viết (posts, ads, video...) đều sẽ theo đúng tone này.\n\n"
                    "Hoặc bấm *Viết lại* nếu muốn thay đổi.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=BV_DRAFT_APPROVE_KEYBOARD,
                )
    except asyncio.TimeoutError:
        logger.error("Skill %s timeout sau %ds", task_name, 500)
        await update.message.reply_text(
            f"⚠️ Skill {task_name} timeout (API chậm hoặc treo). Sếp thử lại nhé.\n"
            f"Nếu lặp lại, có thể giảm scope intake để output ngắn hơn."
        )
    except (TimedOut, NetworkError) as e:
        # In PTB 22+, BadRequest (400) is a subclass of NetworkError.
        # Tách riêng: nếu là Markdown parse error → retry plain text; nếu là timeout thật → log như cũ.
        if "parse" in str(e).lower() or "entities" in str(e).lower():
            logger.warning("Skill %s: Markdown parse error — retrying as plain text: %s", task_name, e)
            try:
                await update.message.reply_text(
                    "⚠️ Lỗi format Markdown khi gửi kết quả — đây là bản text thuần:\n\n"
                    + (result[:3000] if isinstance(result, str) else str(result)[:3000])
                )
            except Exception:
                pass
        else:
            # Timeout thật — output thường ĐÃ gửi tới user.
            logger.warning("Skill %s: Telegram delivery timeout (output likely delivered): %s", task_name, e)
    except Exception as e:
        logger.exception("Skill %s failed: %s", task_name, e)
        await update.message.reply_text(
            f"⚠️ Skill {task_name} gặp lỗi: {str(e)[:200]}\n\nThử /start lại nhé."
        )


def _infer_industry(product: str, customer: str = "") -> str | None:
    """Phase 3 helper: infer industry from product description.
    Returns industry key or None if cannot infer."""
    text = f"{product} {customer}".lower()
    # Simple keyword matching for VN context
    if any(k in text for k in ["spa", "beauty", "skincare", "salon", "nails", "facial", "thẩm mỹ"]):
        return "health_beauty"
    if any(k in text for k in ["cafe", "quán", "nhà hàng", "f&b", "đồ ăn", "thức uống", "restaurant", "coffee"]):
        return "fnb"
    if any(k in text for k in ["saas", "phần mềm", "app", "platform", "tech"]):
        return "tech_saas"
    if any(k in text for k in ["khóa học", "course", "edu", "đào tạo", "training"]):
        return "education"
    if any(k in text for k in ["shop", "thời trang", "fashion", "ecommerce", "online store"]):
        return "ecommerce"
    if any(k in text for k in ["bđs", "bất động sản", "real estate", "căn hộ", "nhà"]):
        return "real_estate"
    return None


def _extract_image_prompt_from_brief(parsed: dict, session) -> str:
    """Sprint 5 v2: Build image gen prompt từ Ads output dùng prompt library.
    Match category dựa industry + product → template phù hợp → fill placeholders."""
    intake = session.pending_intake or {}
    product = intake.get("product", "") or session.profile.product_service or "sản phẩm"
    offer = intake.get("offer", "") or ""
    brand = session.profile.business_name or "Brand"
    industry = session.profile.industry or ""

    # Map size → aspect ratio
    aspect_map = {"vertical": "vertical", "square": "square", "horizontal": "horizontal"}
    aspect = aspect_map.get(intake.get("_last_image_size_hint", "square"), "square")

    try:
        from tools.image_prompt_library import build_prompt
        final_prompt, template_slug = build_prompt(
            product=product[:200],
            brand=brand[:100],
            offer=offer[:150],
            style_note="",
            category=None,  # auto-detect from context_text
            aspect_ratio=aspect,
        )
        intake["_template_slug"] = template_slug
        logger.info("Image prompt: template=%s for industry=%s", template_slug, industry)
        return final_prompt[:1500]
    except Exception as e:
        logger.warning("Prompt library failed, falling back: %s", e)

    # Fallback: legacy logic
    insight = intake.get("insight", "")
    offer = intake.get("offer", "")
    deliverable = parsed.get("deliverable", "") or parsed.get("raw", "")[:500]

    # Try extract "Visual" or "Style" lines from deliverable
    import re as _re
    visual_hints = _re.findall(
        r"(?:Visual|Concept|Mood|Style|Color)[:\s]+([^\n]+)",
        deliverable, flags=_re.IGNORECASE
    )
    visual_str = " ".join(visual_hints[:3]) if visual_hints else ""

    # Compose image prompt (English works best for gpt-image-1)
    prompt = (
        f"Marketing ad image for: {product}. "
        f"Key insight: {insight}. "
        f"Offer: {offer}. "
    )
    if visual_str:
        prompt += f"Visual style: {visual_str}. "
    prompt += (
        "Vietnamese market, modern professional style, "
        "high quality commercial photography, clean composition with space for text overlay."
    )
    return prompt[:1000]  # gpt-image-1 prompt limit


async def _send_ops_result(message: Message, session, task_name: str, result: str):
    """Render single-skill result (ops + strategic single-shot): Telegram card + files."""
    from bot.renderers import (
        parse_by_format,
        format_telegram_card,
        render_markdown_file,
        render_excel_file,
    )
    from bot.html_report import build_single_skill_report
    from agents.skills import PrimaryDeliverable
    import io

    # ContentGeneratorPipeline returns "MULTI_OUTPUT:skill1,skill2" — dispatch each sub-skill
    if result.startswith("MULTI_OUTPUT:"):
        sub_skills = result[len("MULTI_OUTPUT:"):].split(",")
        for sub_name in sub_skills:
            sub_result = session.get_latest_result(sub_name) or ""
            if sub_result:
                await _send_ops_result(message, session, sub_name, sub_result)
        return

    # Resolve skill instance: strategic single-shot uses STRATEGIC_SKILL_CLASSES,
    # operational uses get_operational_skill factory
    SINGLE_SHOT_STRATEGIC = {"market", "competitor", "customer", "pricing"}
    if task_name in SINGLE_SHOT_STRATEGIC:
        from agents.pipeline import STRATEGIC_SKILL_CLASSES
        skill = STRATEGIC_SKILL_CLASSES[task_name]()
    else:
        from agents.operational_skills_config import get_operational_skill
        skill = get_operational_skill(task_name)

    task = get_task(task_name)
    parsed = parse_by_format(result, skill.output_format)

    # Telegram bullet card
    primary_label = {
        PrimaryDeliverable.HTML:     "Xem chi tiết trong file HTML đính kèm",
        PrimaryDeliverable.EXCEL:    "Xem chi tiết trong file Excel đính kèm",
        PrimaryDeliverable.MARKDOWN: "Xem chi tiết trong file Markdown đính kèm",
    }.get(skill.primary_deliverable, "Xem file đính kèm")

    card_text = format_telegram_card(
        task_name, task.label, task.button_emoji,
        parsed, skill.output_format,
        file_attached_hint=primary_label,
    )

    # Footer: API nào làm job này + token sử dụng (breakdown nếu nhiều API)
    try:
        from tools.token_tracker import format_job_footer
        footer = format_job_footer(session)
        if footer:
            card_text = f"{card_text}\n{footer}"
    except Exception as e:
        logger.warning("Token footer failed for %s: %s", task_name, e)

    await _safe_reply(message, card_text, parse_mode=ParseMode.MARKDOWN)

    _bizname = (session.profile.business_name or "").strip()
    # business_name rỗng → KHÔNG fallback về task_name (tránh tên kiểu
    # "campaign_brief_campaign_brief.html"); để slug rỗng, xử lý ở filename.
    business_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", _bizname)[:30].strip("_") if _bizname else ""
    business_name = _bizname or "Business"
    # Stem chung cho mọi file (tránh trailing "_" khi slug rỗng)
    file_stem = f"{task_name}_{business_slug}" if business_slug else task_name

    # Skip HTML phụ: Excel-only skills + action skills (ads_optimizer)
    SKIP_HTML_SKILLS = {"content_generator", "post_batch", "video_script_gen", "ugc_brief", "ads_optimizer", "ads_intelligence"}

    # Action skills: output hiện inline (kèm nút action), KHÔNG gửi file deliverable.
    # Khác SKIP_HTML_SKILLS (chỉ bỏ HTML phụ) — post_batch vẫn phải gửi MD primary.
    NO_FILE_SKILLS = {"ads_optimizer", "ads_intelligence"}

    if task_name not in SKIP_HTML_SKILLS:
        # Send HTML always (universal viewable)
        try:
            html_str = build_single_skill_report(
                task_name, parsed, skill.output_format,
                business_name=business_name,
                industry=session.profile.industry or "",
                stage=session.profile.stage or "",
            )
            buf = io.BytesIO(html_str.encode("utf-8"))
            buf.name = f"{file_stem}.html"
            await message.reply_document(
                document=buf,
                filename=buf.name,
                caption=f"📄 *{task.label}* — bản HTML đầy đủ",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.warning("HTML render failed for %s: %s", task_name, e)

    # Content Suite v2: skills luôn output MD primary + Excel secondary (Haiku convert)
    CONTENT_SUITE_V2 = {"post_write", "post_adapt", "post_voice_check", "post_hooks", "post_batch"}

    # Send primary deliverable per skill config (skip for action skills like ads_optimizer).
    # Gate bằng NO_FILE_SKILLS (KHÔNG phải SKIP_HTML_SKILLS) — post_batch nằm trong
    # SKIP_HTML_SKILLS nhưng MD là deliverable chính của nó, vẫn phải gửi.
    if task_name not in NO_FILE_SKILLS and skill.primary_deliverable == PrimaryDeliverable.MARKDOWN:
        # post_batch: chỉ gửi Excel (như các skill EXCEL khác), bỏ file MD song song
        if task_name != "post_batch":
            md_bytes = render_markdown_file(task_name, task.label, parsed, skill.output_format, business_name)
            buf = io.BytesIO(md_bytes)
            buf.name = f"{file_stem}.md"
            await message.reply_document(
                document=buf,
                filename=buf.name,
                caption=f"📝 *{task.label}* — bản Markdown (gửi designer/dev/creator)",
                parse_mode=ParseMode.MARKDOWN,
            )

        # Content Suite v2: TRY gen Excel secondary qua Haiku auto-convert
        if task_name in CONTENT_SUITE_V2:
            try:
                xlsx_bytes = render_excel_file(task_name, task.label, parsed, skill.output_format, business_name)
                if xlsx_bytes:
                    buf2 = io.BytesIO(xlsx_bytes)
                    buf2.name = f"{file_stem}.xlsx"
                    await message.reply_document(
                        document=buf2,
                        filename=buf2.name,
                        caption=(
                            f"📊 *{task.label}* — bản Excel (overview/track status)\n"
                            f"✏️ _Sửa xong gửi lại file này (giữ nguyên tên) — em cập nhật theo._"
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    logger.info("Excel secondary skipped for %s (Haiku convert returned no table)", task_name)
            except Exception as e:
                logger.warning("Excel secondary gen failed for %s (non-blocking): %s", task_name, e)
    elif skill.primary_deliverable == PrimaryDeliverable.EXCEL:
        # Wrap toàn bộ Excel pipeline trong try/except để user luôn thấy lỗi
        try:
            logger.info("Rendering Excel for skill=%s (parsed keys: %s, raw len: %d)",
                        task_name, list(parsed.keys()),
                        len(parsed.get("raw", "")) if isinstance(parsed.get("raw"), str) else 0)
            post_ids = None
            if task_name == "content_calendar":
                from agents.post_actions import parse_calendar_to_posts
                campaign_id = session.pending_intake.get("campaign_name", "")
                posts = parse_calendar_to_posts(result, campaign_id=campaign_id)
                if posts:
                    post_ids = list(posts.keys())
            xlsx_bytes = render_excel_file(task_name, task.label, parsed, skill.output_format, business_name, post_ids=post_ids)
        except Exception as e:
            logger.exception("render_excel_file CRASHED for %s: %s", task_name, e)
            xlsx_bytes = None
            await message.reply_text(
                f"⚠️ Lỗi khi gen Excel: `{str(e)[:200]}`\n_Admin đã được notify qua logs._",
                parse_mode=ParseMode.MARKDOWN,
            )

        if xlsx_bytes:
            try:
                buf = io.BytesIO(xlsx_bytes)
                buf.name = f"{file_stem}.xlsx"
                await message.reply_document(
                    document=buf,
                    filename=buf.name,
                    caption=(
                        f"📊 *{task.label}* — bản Excel (paste vào Google Sheet)\n"
                        f"✏️ _Sửa xong gửi lại file này (giữ nguyên tên) — em sẽ cập nhật theo._"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                logger.info("Excel sent successfully for %s (%d bytes)", task_name, len(xlsx_bytes))
            except Exception as e:
                logger.exception("reply_document FAILED for %s: %s", task_name, e)
                await message.reply_text(
                    f"⚠️ Lỗi khi gửi file Excel: `{str(e)[:200]}`",
                    parse_mode=ParseMode.MARKDOWN,
                )
        elif xlsx_bytes is None and "Lỗi khi gen" not in (parsed.get("raw", "")[:50] or ""):
            # Chỉ show "không gen được" nếu chưa show error ở trên
            logger.warning("Excel render returned None for %s", task_name)
            await message.reply_text(
                "⚠️ Em không gen được Excel — output AI không có pipe table chuẩn. Sếp chạy lại nhé.",
            )

    if task_name == "competitor":
        session.pending_intake["_awaiting_rating_for"] = "competitor"
        await save_session(session)
        await message.reply_text(
            "Sếp đánh giá output Phân Tích Đối Thủ em vừa làm thế nào ạ?",
            reply_markup=RATING_KEYBOARD,
        )
        return

    # Sprint 5 v2: Sau ads_generator (format=image) → hỏi upload ảnh mẫu hoặc gen luôn
    if task_name in ("ads_generator", "ads_copy") and session.pending_intake.get("ads_format") == "image":
        from tools.image_gen import is_available
        if is_available():
            # Lưu copy output để build prompt sau
            img_prompt = _extract_image_prompt_from_brief(parsed, session)
            session.pending_intake["_img_prompt"] = img_prompt
            await save_session(session)
            await message.reply_text(
                "📸 *Sếp có ảnh mẫu muốn em làm theo style không ạ?*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=IMAGE_REFERENCE_KEYBOARD,
            )
            return
        else:
            await message.reply_text(
                "⚠️ _Image gen chưa setup (cần OPENAI_API_KEY). Em chỉ gửi copy thôi._",
                parse_mode=ParseMode.MARKDOWN,
            )

    # Sprint 4: Special follow-up sau monitor setup
    if task_name == "competitor_spy" and session.pending_intake.get("_fb_page_id"):
        page_id = session.pending_intake["_fb_page_id"]
        page_name = session.pending_intake.get("competitor_name", "đối thủ")
        session.pending_intake["_monitor_pending_page_id"] = page_id
        session.pending_intake["_monitor_pending_page_name"] = page_name
        await save_session(session)
        await message.reply_text(
            f"🔔 *Sếp muốn em theo dõi tự động ads mới của {page_name} không ạ?*\n\n"
            f"_Em sẽ check định kỳ và báo sếp ngay khi đối thủ tung ads mới._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MONITOR_PROMPT_KEYBOARD,
        )
        return

    # content_calendar: no upsell here — _start_tone_calibration fires in main flow,
    # and the content-gen upsell is shown AFTER tone is locked/skipped.
    if task_name == "content_calendar":
        return

    # campaign_brief: XÁC NHẬN brief trước khi gen calendar (Layer 2b).
    # User duyệt → lưu campaign + auto-gen calendar; user sửa → surgical edit.
    if task_name == "campaign_brief":
        session.pending_intake.pop("_awaiting_rating_for", None)
        await save_session(session)
        addr = _addr(session)
        await message.reply_text(
            f"📋 *Brief Campaign xong rồi ạ!* {addr.capitalize()} xem qua giúp em.\n\n"
            f"Bản kế hoạch này đã đủ chưa, có cần *thêm/bớt* phần nào không?\n"
            f"• *Duyệt* → em tạo luôn Lịch Nội Dung theo brief này.\n"
            f"• *Cần sửa* → {addr} chỉ rõ phần nào, em chỉnh đúng chỗ đó.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=CONFIRM_BRIEF_KEYBOARD,
        )
        return

    # Sprint 2: Default — send RATING_KEYBOARD
    session.pending_intake["_awaiting_rating_for"] = task_name
    await save_session(session)

    await message.reply_text(
        f"✅ *Hoàn thành {task.label}!*\n\nSếp đánh giá output em vừa làm thế nào ạ?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=RATING_KEYBOARD,
    )


async def _maybe_nudge_bizname(message: Message, session) -> bool:
    """Trước khi chạy pipeline: nếu chưa có tên business → hỏi nhẹ 1 lần.

    Return True nếu đã gửi câu hỏi (caller phải dừng, chờ user trả lời/bấm skip).
    Return False nếu không cần hỏi (đã có tên hoặc đã hỏi rồi) → caller chạy tiếp.
    """
    if session.profile.business_name:
        return False
    if session.pending_intake.get("_bizname_nudged"):
        return False
    session.pending_intake["_bizname_nudged"] = "1"
    session.pending_intake["_awaiting_bizname"] = "1"
    await save_session(session)
    await message.reply_text(
        "Ơ, em vẫn chưa biết *tên business* của sếp 😅\n\n"
        "Sếp cho em xin tên để em ghi vào báo cáo cho chuyên nghiệp nhé — "
        "_còn không thích thì thôi cũng được, em chạy luôn ạ._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=BIZNAME_SKIP_KEYBOARD,
    )
    return True


async def _proceed_after_confirm(message: Message, session):
    """Chốt confirm → vào pipeline."""
    session.stage = PipelineStage.MARKET_RESEARCH
    await save_session(session)
    await _run_pipeline_sequentially(message, session)


async def _handle_bizname_text(update, context, session, text: str):
    """User trả lời câu hỏi tên business (hoặc từ chối) → chạy pipeline."""
    name = (text or "").strip()
    session.pending_intake.pop("_awaiting_bizname", None)

    _REFUSE = {"thôi", "thoi", "ko", "không", "khong", "skip", "bỏ qua",
               "bo qua", "no", "khỏi", "khoi", "thôi khỏi"}
    if name and name.lower() not in _REFUSE and len(name) <= 80:
        session.profile.business_name = name
        await save_session(session)
        await update.message.reply_text(
            f"✅ Ghi nhận business *{_escape_md(name)}* — em chạy luôn nhé! 🚀",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await save_session(session)
        await update.message.reply_text("Ok sếp, em chạy luôn nha! 🚀")

    await _proceed_after_confirm(update.message, session)


# ─── Strategic Consultation — 7-question direction flow ──────────

_STRATEGY_Q_KEYS = [
    "market_gap",
    "target_segment",
    "competitor_gap",
    "positioning",
    "pricing_approach",
    "usp_angle",
    "channels",
    "timeline",
]

_STRATEGY_Q_LABELS = {
    "market_gap":       "Market Gap",
    "target_segment":   "Target Segment",
    "competitor_gap":   "Messaging Gap",
    "positioning":      "Định Vị",
    "pricing_approach": "Pricing",
    "usp_angle":        "USP Angle",
    "channels":         "Kênh Triển Khai",
    "timeline":         "Timeline Triển Khai",
}


async def _generate_strategy_questions(session) -> list[dict]:
    """LLM call — read 5 research results, generate 7 targeted questions with options."""
    import json as _json, re as _re
    from tools.llm_router import call as router_call, TaskType
    from frameworks.pricing_segment_library import format_pricing_segments_for_prompt

    industry = session.profile.industry

    g = session.get_latest_result
    parts = []
    for key, label in [
        ("market_research",    "Thị trường"),
        ("competitor",         "Đối thủ"),
        ("customer_insight",   "Khách hàng"),
        ("psychology_pricing", "Định giá & Psychology"),
        ("usp_definition",     "USP"),
    ]:
        val = g(key)
        if val:
            parts.append(f"## {label}\n{val[:2000]}")

    if not parts:
        return _default_strategy_questions_fallback(industry)

    parts.append(format_pricing_segments_for_prompt(industry))

    system = """Bạn là marketing strategist senior. Dựa vào kết quả nghiên cứu, tạo 8 câu hỏi chiến lược để hỏi business owner — mỗi câu về 1 chiều quyết định.

8 chiều BẮT BUỘC (đúng key, đúng thứ tự):
1. market_gap — khoảng trống thị trường nào muốn khai thác
2. target_segment — segment/ICP nào muốn focus
3. competitor_gap (Messaging Gap) — thông điệp/narrative/claim nào đối thủ ĐANG bỏ trống mà business này có thể chiếm — CHỈ về góc truyền thông (tone, claim, story angle), KHÔNG đề cập channel gap/segment gap/product gap
4. positioning — định vị trên positioning map — quadrant/góc nào
5. pricing_approach — định vị PHÂN KHÚC GIÁ (không hỏi giá từng sản phẩm)
6. usp_angle — USP angle muốn lead (emotional/practical/social proof)
7. channels — kênh triển khai chính
8. timeline — khung thời gian triển khai kế hoạch (sprint nhanh / vừa phải / dài hơi)

🔴 RIÊNG câu 5 (pricing_approach): KHÔNG hỏi pricing model generic (premium/competitive/value/bundle) và KHÔNG hỏi giá từng sản phẩm. Hỏi founder muốn ĐỊNH VỊ Ở PHÂN KHÚC GIÁ nào. "options" PHẢI lấy NGUYÊN VĂN từ block "## Phân khúc giá tham khảo — ngành ..." được cung cấp trong Nghiên cứu (mỗi option = 1 phân khúc, gồm tên phân khúc + khoảng giá + kênh bán điển hình) — KHÔNG tự bịa khoảng giá hay kênh khác. "context": nếu research có đề cập giá/kênh bán hiện tại của business → so sánh và gợi ý phân khúc gần nhất phù hợp; nếu không có thì tóm tắt ngắn vì sao phân khúc này hợp với positioning/customer insight đã research.

🔴 RIÊNG câu 3 (competitor_gap / Messaging Gap): CHỈ hỏi về khoảng trống THÔNG ĐIỆP — claim/narrative/tone of voice nào đối thủ chưa ai sở hữu mà business này có thể "own". "options" là các GÓC TRUYỀN THÔNG cụ thể bám research (vd: "Data-driven — minh bạch số liệu/kết quả thật", "Anti-hype — thẳng thắn, không thổi phồng", "Local-first — gắn bản địa, insight vùng miền", "Authority — chuyên môn, chứng nhận, kinh nghiệm"). KHÔNG liệt kê channel gap / segment gap / product gap làm options — đó là chiều khác, không thuộc câu này.

🔴 RIÊNG câu 7 (channels): user sẽ TỰ GÕ các kênh muốn làm — KHÔNG hiển thị lựa chọn sẵn. Để "options": []. Dồn giá trị vào "context": tóm tắt finding CỤ THỂ từ research về kênh nào tiềm năng nhất cho business này (vd "TikTok organic CAC gần 0 nếu content đúng") để user tham khảo trước khi tự quyết. "question" hỏi mở: kênh nào user muốn triển khai content chính. Chỉ nhắc tới các kênh nội dung Max trực tiếp sản xuất được (Facebook, TikTok, Instagram, YouTube/Shorts, Zalo OA, Threads, LinkedIn, Google/SEO content...) — không nhắc "hợp tác đối tác", "referral", "co-marketing".

🔴 RIÊNG câu 8 (timeline): options là các MỐC THỜI GIAN cụ thể, phù hợp với stage business + resource (vd: "Sprint 90 ngày — kết quả nhanh", "6 tháng — build foundation + scale", "12 tháng — long-game brand building"). Tối đa 3-4 options.

Với mỗi chiều:
- "question": câu hỏi ngắn (1 câu)
- "context": 1-2 câu tóm tắt finding CỤ THỂ từ data (số liệu, tên đối thủ, tên segment nếu có)
- "options": 2-4 lựa chọn CỤ THỂ từ data (không generic như "option A")

Output JSON array (chỉ JSON, không markdown):
[{"key":"market_gap","question":"...","context":"...","options":["...","...","..."]}, ...]"""

    user = "Nghiên cứu:\n\n" + "\n\n".join(parts)

    try:
        result = await router_call(
            task_type=TaskType.INTAKE_JSON,
            system=system,
            user=user,
            max_tokens=1800,
        )
        raw = result["output"]
        match = _re.search(r'\[.*\]', raw, _re.DOTALL)
        if match:
            questions = _json.loads(match.group())
            if isinstance(questions, list) and len(questions) >= 6:
                # Ensure all 8 keys present, fill missing with fallback
                fallback = {q["key"]: q for q in _default_strategy_questions_fallback(industry)}
                result_map = {q["key"]: q for q in questions if q.get("key") in _STRATEGY_Q_KEYS}
                return [result_map.get(k, fallback[k]) for k in _STRATEGY_Q_KEYS]
    except Exception:
        logger.warning("_generate_strategy_questions LLM failed, using fallback")

    return _default_strategy_questions_fallback(industry)


def _format_answers_for_prompt(answers: dict, keys: list[str]) -> str:
    """Render các câu trả lời (key → _STRATEGY_Q_LABELS) đã chốt thành block
    text để inject vào prompt sinh câu hỏi tiếp theo (BACKLOG #3)."""
    lines = []
    for k in keys:
        if answers.get(k):
            label = _STRATEGY_Q_LABELS.get(k, k)
            lines.append(f"- {label}: {answers[k]}")
    return "\n".join(lines)


async def _gen_q4_positioning(session, answers: dict) -> dict | None:
    """BACKLOG #3 — sinh lại câu 4 (positioning) SAU KHI user đã trả lời Q1-3
    (market_gap, target_segment, competitor_gap/Messaging Gap), để options bám
    đúng hướng đã chọn. Trả về None nếu LLM fail (giữ placeholder cũ)."""
    import json as _json, re as _re
    from tools.llm_router import call as router_call, TaskType

    g = session.get_latest_result
    parts = []
    for key, label in [
        ("market_research", "Thị trường"),
        ("competitor",      "Đối thủ"),
        ("customer_insight", "Khách hàng"),
    ]:
        val = g(key)
        if val:
            parts.append(f"## {label}\n{val[:1500]}")

    chosen_block = _format_answers_for_prompt(answers, ["market_gap", "target_segment", "competitor_gap"])

    system = """Bạn là marketing strategist senior. Founder đã chọn Market Gap, Target Segment, và Messaging Gap (3 hướng chiến lược). Sinh 1 câu hỏi về POSITIONING — định vị trên positioning map — với options bám SÁT 3 hướng founder đã chọn (không generic, không lặp lại các hướng khác).

Output JSON object (chỉ JSON, không markdown):
{"key":"positioning","question":"...","context":"1-2 câu nối market_gap/target_segment/messaging_gap đã chọn với góc định vị đề xuất","options":["...","...","...",...]}

- "options": 2-4 lựa chọn CỤ THỂ, mỗi lựa chọn phải khả thi với target_segment + messaging_gap đã chọn ở trên
- "context": phải nhắc cụ thể tới ít nhất 1 trong 3 hướng đã chọn"""

    user = (
        "## 3 hướng founder đã chọn:\n" + chosen_block + "\n\n"
        + "\n\n".join(parts)
    )

    try:
        result = await router_call(
            task_type=TaskType.INTAKE_JSON,
            system=system,
            user=user,
            max_tokens=600,
        )
        raw = result["output"]
        match = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if match:
            q = _json.loads(match.group())
            if q.get("key") == "positioning" and q.get("question") and q.get("options"):
                q = {**q, "options": [_strategy_opt_to_str(o) for o in q.get("options", [])]}
                return q
    except Exception:
        logger.warning("_gen_q4_positioning LLM failed, keeping baseline question")
    return None


async def _gen_q5_6_pricing_usp(session, answers: dict) -> list[dict] | None:
    """BACKLOG #3 — sinh lại câu 5 (pricing_approach) + câu 6 (usp_angle) SAU KHI
    user đã trả lời positioning (Q4), để pricing segment + USP angle nhất quán
    với định vị đã chọn. Trả về None nếu LLM fail (giữ placeholder cũ)."""
    import json as _json, re as _re
    from tools.llm_router import call as router_call, TaskType
    from frameworks.pricing_segment_library import format_pricing_segments_for_prompt

    industry = session.profile.industry
    g = session.get_latest_result
    parts = []
    for key, label in [
        ("psychology_pricing", "Định giá & Psychology"),
        ("usp_definition",     "USP"),
    ]:
        val = g(key)
        if val:
            parts.append(f"## {label}\n{val[:1500]}")
    parts.append(format_pricing_segments_for_prompt(industry))

    chosen_block = _format_answers_for_prompt(answers, ["market_gap", "target_segment", "competitor_gap", "positioning"])

    system = """Bạn là marketing strategist senior. Founder đã chọn Market Gap, Target Segment, Messaging Gap, và Positioning (định vị). Sinh 2 câu hỏi:

1. pricing_approach — định vị PHÂN KHÚC GIÁ, NHẤT QUÁN với positioning đã chọn (vd positioning "Premium" → phân khúc giá phải ở mức cao tương ứng, không đề phân khúc giá thấp). "options" PHẢI lấy NGUYÊN VĂN từ block "## Phân khúc giá tham khảo — ngành ..." được cung cấp — KHÔNG tự bịa khoảng giá/kênh. "context": giải thích vì sao phân khúc này nhất quán với positioning đã chọn.

2. usp_angle — USP angle (emotional/practical/social proof/authority) PHÙ HỢP với positioning + pricing_approach vừa định. "context": nối USP angle với positioning đã chọn.

Output JSON array đúng 2 object theo thứ tự trên (chỉ JSON, không markdown):
[{"key":"pricing_approach","question":"...","context":"...","options":[...]}, {"key":"usp_angle","question":"...","context":"...","options":["...","...","...","..."]}]"""

    user = (
        "## Các hướng founder đã chọn:\n" + chosen_block + "\n\n"
        + "\n\n".join(parts)
    )

    try:
        result = await router_call(
            task_type=TaskType.INTAKE_JSON,
            system=system,
            user=user,
            max_tokens=1200,
        )
        raw = result["output"]
        match = _re.search(r'\[.*\]', raw, _re.DOTALL)
        if match:
            qs = _json.loads(match.group())
            if isinstance(qs, list) and len(qs) >= 2:
                qmap = {q.get("key"): q for q in qs}
                if "pricing_approach" in qmap and "usp_angle" in qmap:
                    out = []
                    for k in ("pricing_approach", "usp_angle"):
                        q = qmap[k]
                        out.append({**q, "options": [_strategy_opt_to_str(o) for o in q.get("options", [])]})
                    return out
    except Exception:
        logger.warning("_gen_q5_6_pricing_usp LLM failed, keeping baseline questions")
    return None


def _default_strategy_questions_fallback(industry: str | None = None) -> list[dict]:
    from frameworks.pricing_segment_library import get_pricing_segments

    pricing_options = [
        f"{seg['segment']} ({seg['price_range']}) — kênh: {seg['channels']}"
        for seg in get_pricing_segments(industry)
    ]

    return [
        {"key": "market_gap",       "question": "Market gap nào sếp muốn khai thác?",           "context": "Dựa vào nghiên cứu thị trường.",       "options": ["Khoảng trống phân khúc cao cấp", "Khoảng trống digital/online", "Khoảng trống địa lý", "Khoảng trống sản phẩm mới"]},
        {"key": "target_segment",   "question": "Segment / ICP nào muốn tập trung?",             "context": "Dựa vào customer insight.",            "options": ["Khách hàng trẻ 18-30", "Khách hàng trung niên 30-45", "Doanh nghiệp nhỏ SME", "Phụ huynh / gia đình"]},
        {"key": "competitor_gap",   "question": "Messaging Gap nào sếp muốn khai thác — thông điệp/narrative nào đối thủ chưa ai sở hữu?", "context": "Dựa vào phân tích đối thủ — góc truyền thông đang bị bỏ trống.", "options": ["Data-driven — minh bạch số liệu, kết quả thật", "Anti-hype — thẳng thắn, không quảng cáo thổi phồng", "Local-first — gắn bản địa, insight vùng miền", "Authority — chuyên môn, chứng nhận, kinh nghiệm"]},
        {"key": "positioning",      "question": "Muốn định vị ở góc nào trên thị trường?",       "context": "Dựa vào positioning map.",            "options": ["Premium — chất lượng cao, giá cao", "Value — chất lượng tốt, giá hợp lý", "Niche specialist — chuyên sâu 1 phân khúc", "Challenger — thách thức market leader"]},
        {"key": "pricing_approach", "question": "Sếp muốn định vị ở phân khúc giá nào?",         "context": "Mỗi phân khúc đi kèm khoảng giá tham khảo + kênh bán điển hình theo ngành.", "options": pricing_options},
        {"key": "usp_angle",        "question": "USP angle nào muốn lead trong marketing?",       "context": "Dựa vào USP definition.",             "options": ["Emotional angle — cảm xúc, câu chuyện", "Practical angle — lợi ích cụ thể, số liệu", "Social proof angle — review, kết quả khách", "Authority angle — expertise, chứng chỉ"]},
        {"key": "channels",         "question": "Kênh mạng xã hội nào sếp muốn triển khai content chính?",          "context": "Kênh Max có thể trực tiếp sản xuất nội dung: Facebook, TikTok, Instagram, YouTube/Shorts, Zalo OA, Threads, LinkedIn...", "options": []},
        {"key": "timeline",         "question": "Timeline triển khai kế hoạch sếp muốn?",                            "context": "Quyết định pace của roadmap + KPI checkpoints.", "options": ["Sprint 90 ngày — kết quả nhanh", "6 tháng — foundation + scale", "12 tháng — long-game brand"]},
    ]


async def _start_strategic_consultation(message: Message, session) -> None:
    """After research pipeline — ask 8 strategic questions one by one."""
    import json as _json

    addr = _addr(session)
    await message.reply_text(
        "🔍 *Em đang phân tích kết quả nghiên cứu để hỏi sếp 8 câu chiến lược...*",
        parse_mode=ParseMode.MARKDOWN,
    )

    questions = await _generate_strategy_questions(session)
    session.pending_intake["_strategy_questions"] = _json.dumps(questions, ensure_ascii=False)
    session.pending_intake["_strategy_answers"]   = _json.dumps({}, ensure_ascii=False)
    # Clear leftover current-question state từ lần chạy trước (resume-safe logic
    # trong _ask_next_strategy_question sẽ đọc nhầm state cũ nếu không xóa).
    session.pending_intake.pop("_current_q_key", None)
    session.pending_intake.pop("_current_q_full", None)
    session.pending_intake.pop("_current_q_options", None)
    session.pending_intake.pop("_awaiting_strategy_q_custom", None)
    await save_session(session)

    await message.reply_text(
        f"✅ *Nghiên cứu hoàn tất!*\n\n"
        f"Để kế hoạch chiến lược thực sự fit với sếp, Max cần hỏi {addr} *8 câu* về hướng đi.\n\n"
        f"💡 _Mỗi câu nên chọn **1 hướng** thôi — chiến lược càng tập trung, "
        f"dồn lực 1 mũi thì ra kết quả nhanh và rõ hơn là dàn trải. "
        f"Nếu sếp thật sự muốn kết hợp nhiều, bấm \"✏️ Tôi có ý khác\" và gõ tất cả vào ạ._\n\n"
        f"Xong ngay thôi 👇",
        parse_mode=ParseMode.MARKDOWN,
    )
    await _ask_next_strategy_question(message, session)


def _strategy_opt_to_str(opt) -> str:
    """LLM đôi khi trả 'options' dạng object (vd pricing segment
    {"segment","price_range","channels"}) thay vì string thuần — chuẩn hóa
    về string để tránh crash khi slice/format/lưu answer."""
    if isinstance(opt, dict):
        seg = opt.get("segment") or opt.get("name") or ""
        price = opt.get("price_range") or ""
        channels = opt.get("channels") or ""
        s = " ".join(p for p in [seg, f"({price})" if price else ""] if p)
        if channels:
            s += f" — kênh: {channels}"
        return s or str(opt)
    return str(opt)


async def _ask_next_strategy_question(message: Message, session) -> None:
    """Pop and show next strategy question, or run synthesis if all answered.

    Resume-safe: nếu câu hỏi hiện tại (`_current_q_key`) chưa có answer (vd
    bot crash giữa lúc render câu đó), render lại đúng câu đó từ
    `_current_q_full` thay vì pop câu tiếp theo (tránh mất câu hỏi)."""
    import json as _json
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    questions_raw = session.pending_intake.get("_strategy_questions", "[]")
    answers_raw   = session.pending_intake.get("_strategy_answers",   "{}")
    questions = _json.loads(questions_raw)
    answers   = _json.loads(answers_raw)
    total     = len(_STRATEGY_Q_KEYS)

    current_key  = session.pending_intake.get("_current_q_key")
    current_full = session.pending_intake.get("_current_q_full")
    if current_key and current_key not in answers and current_full:
        q = _json.loads(current_full)
        current = total - len(questions)
    elif current_key and current_key not in answers and not current_full:
        # Session cũ trước khi có _current_q_full (vd crash giữa câu pricing_approach
        # do bug dict-options) — không còn lưu full question, reconstruct từ fallback
        # theo industry để hỏi lại đúng câu này.
        fallback = {fq["key"]: fq for fq in _default_strategy_questions_fallback(session.profile.industry)}
        q = fallback.get(current_key, {
            "key": current_key,
            "question": _STRATEGY_Q_LABELS.get(current_key, current_key),
            "context": "",
            "options": [],
        })
        q = {**q, "options": [_strategy_opt_to_str(o) for o in q.get("options", [])]}
        session.pending_intake["_current_q_full"] = _json.dumps(q, ensure_ascii=False)
        await save_session(session)
        current = total - len(questions)
    elif not questions:
        # All answered → run synthesis
        session.pending_intake.pop("_strategy_questions", None)
        direction_block = _format_strategy_answers(answers)
        await save_session(session)
        await _run_strategy_plan(message, session, direction=direction_block)
        return
    else:
        # BACKLOG #3: Q4 (positioning) và Q5-6 (pricing_approach/usp_angle) phụ
        # thuộc các câu trước — regenerate ngay trước khi hiển thị để options
        # bám đúng hướng user đã chọn.
        if questions[0]["key"] == "positioning":
            new_q4 = await _gen_q4_positioning(session, answers)
            if new_q4:
                questions[0] = new_q4
        elif questions[0]["key"] == "pricing_approach":
            new_q56 = await _gen_q5_6_pricing_usp(session, answers)
            if new_q56:
                questions[0] = new_q56[0]
                if len(questions) > 1 and questions[1]["key"] == "usp_angle":
                    questions[1] = new_q56[1]

        q = questions[0]
        remaining = questions[1:]
        current   = total - len(remaining)  # 1-based index

        norm_options = [_strategy_opt_to_str(o) for o in q["options"]]
        q = {**q, "options": norm_options}

        session.pending_intake["_strategy_questions"]  = _json.dumps(remaining, ensure_ascii=False)
        session.pending_intake["_current_q_key"]       = q["key"]
        session.pending_intake["_current_q_full"]      = _json.dumps(q, ensure_ascii=False)
        session.pending_intake["_current_q_options"]   = _json.dumps(norm_options, ensure_ascii=False)
        await save_session(session)

    norm_options = q["options"]
    label = _STRATEGY_Q_LABELS.get(q["key"], q["key"])

    # Câu channels: KHÔNG đưa option sẵn — user tự gõ các kênh muốn làm.
    if q["key"] == "channels":
        session.pending_intake["_awaiting_strategy_q_custom"] = "1"
        await save_session(session)
        await message.reply_text(
            f"*{current}/{total} — {label}*\n\n"
            f"_{q['context']}_\n\n"
            f"{q['question']}\n\n"
            f"✏️ _Sếp gõ thẳng các kênh muốn triển khai vào đây "
            f"(vd: \"TikTok + Zalo OA\" hay \"Facebook, Instagram\"). "
            f"Bao nhiêu kênh cũng được — nhưng càng tập trung càng dễ làm sâu ạ._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    _letters = ["A", "B", "C", "D", "E"]
    options_text = "\n".join(
        f"*{_letters[i]}.* *{opt}*" for i, opt in enumerate(norm_options)
    )
    buttons = [
        [InlineKeyboardButton(f"{_letters[i]}. {opt[:55]}", callback_data=f"strategy_q_{i}")]
        for i, opt in enumerate(norm_options)
    ]
    buttons.append([InlineKeyboardButton("✏️ Tôi có ý khác", callback_data="strategy_q_custom")])
    kb = InlineKeyboardMarkup(buttons)

    hint = "_👉 Nên chọn 1 để tập trung. Muốn kết hợp nhiều → bấm \"✏️ Tôi có ý khác\"._"
    await message.reply_text(
        f"*{current}/{total} — {label}*\n\n"
        f"_{q['context']}_\n\n"
        f"{options_text}\n\n"
        f"{q['question']}\n\n"
        f"{hint}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )


def _format_strategy_answers(answers: dict) -> str:
    labels = {
        "market_gap":       "Market gap muốn khai thác",
        "target_segment":   "Target segment",
        "competitor_gap":   "Messaging gap muốn khai thác",
        "positioning":      "Định vị",
        "pricing_approach": "Pricing approach",
        "usp_angle":        "USP angle",
        "channels":         "Kênh triển khai chính",
    }
    lines = []
    for key, label in labels.items():
        if key in answers:
            lines.append(f"**{label}:** {answers[key]}")
    return "\n".join(lines)


async def _run_strategy_plan(message: Message, session, direction: str) -> None:
    """Run phase=synthesis (T4 Synthesis + T5 Tactical Playbook) với direction từ 8 câu chiến lược.

    User đã trả lời 8 câu → direction text → inject vào synthesis context →
    T4 Synthesis dựng kế hoạch → T5 Tactical Playbook đào sâu thành tactics.
    Cả 2 stage stream về user dưới dạng card riêng.
    """
    from agents.pipeline import run_multi_agent_targeted
    from bot.html_report import parse_agent_output
    from tools.token_tracker import get_latest_skill_entry

    addr = _addr(session)
    await message.reply_text(
        f"🚀 *Max đang xây kế hoạch chiến lược + tactical playbook theo hướng:*\n_{direction}_\n\n_~3-5 phút (2 bước)..._",
        parse_mode=ParseMode.MARKDOWN,
    )
    await context_bot_typing(message)

    session.pending_intake["_strategy_direction"] = direction
    await save_session(session)

    async def _synth_progress(msg: str):
        try:
            await message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await message.reply_text(msg, parse_mode=None)

    pipeline_aborted = False
    try:
        async for stage_key, result in run_multi_agent_targeted(
            session, progress_callback=_synth_progress, phase="synthesis"
        ):
            if stage_key == "pipeline_abort":
                pipeline_aborted = True
                await message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
                continue

            parsed = parse_agent_output(result)
            token_entry = get_latest_skill_entry(session, stage_key)
            card_text = _format_card(stage_key, parsed, token_entry=token_entry)
            await send_long_message(message, card_text, parse_mode=ParseMode.MARKDOWN, reply_markup=None)
            await save_session(session)
    except Exception as e:
        session.pending_intake.pop("_strategy_direction", None)
        await save_session(session)
        await message.reply_text(f"⚠️ Lỗi khi xây kế hoạch: {str(e)[:200]}")
        return
    finally:
        session.pending_intake.pop("_strategy_direction", None)
        await save_session(session)

    if pipeline_aborted:
        return

    # Build báo cáo HTML chỉ phase synthesis (2 tab: T4 Synthesis + T5 Tactical
    # Playbook) — research T1-T3 đã gửi report riêng ở cuối phase research,
    # không cần gửi lại.
    try:
        from bot.html_report import build_report, generate_archetype_banner_html
        from agents.pipeline import PIPELINE_DEF

        synthesis_stages: list[tuple[str, dict]] = []
        for stage_def in PIPELINE_DEF:
            if stage_def.phase != "synthesis":
                continue
            content = session.get_latest_result(stage_def.result_key)
            if content and not content.strip().startswith("⚠️"):
                synthesis_stages.append((stage_def.result_key, parse_agent_output(content)))

        if synthesis_stages:
            signal_text = " ".join(filter(None, [
                session.profile.product_service or "",
                session.profile.target_customer or "",
            ]))
            archetype_banner_html = await generate_archetype_banner_html(
                business_name=session.profile.business_name or "Business",
                industry=session.profile.industry or "",
                signal_text=signal_text,
                parsed_stages=synthesis_stages,
            )
            html_str = build_report(
                business_name=session.profile.business_name or "Business",
                industry=session.profile.industry or "",
                stage=session.profile.stage or "",
                parsed_stages=synthesis_stages,
                archetype_signal_text=signal_text,
                archetype_banner_html=archetype_banner_html,
            )
            await _send_html_report(
                message, html_str, session,
                caption="📊 *Kế hoạch chiến lược + Tactical Playbook* (T4-T5).",
            )
    except Exception as e:
        logger.warning("Full HTML report after synthesis failed (cards đã gửi đủ): %s", e)

    session.pending_intake["_awaiting_rating_for"] = "full"
    await save_session(session)

    await message.reply_text(
        f"✅ *Kế hoạch + Tactical Playbook đã xong!*\n\n"
        f"─────────────────────\n"
        f"📋 *{addr.capitalize()} xem qua giúp em:* kế hoạch trên ổn chưa, "
        f"hay cần điều chỉnh gì không ạ?\n\n"
        f"• *Ổn rồi* → em trích Campaign từ Roadmap để {addr} chốt, rồi mới lên Lịch Nội Dung theo Campaign Brief\n"
        f"• *Cần điều chỉnh* → {addr} nói rõ đổi hướng nào, em chỉnh và chạy lại",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=CONFIRM_STRATEGY_TO_CAMPAIGN_KEYBOARD,
    )


async def _ask_budget_team_before_campaigns(message: Message, session) -> None:
    """Trước khi trích campaign từ roadmap, chốt lại Budget/Team để campaign
    đề xuất sát quy mô thật (BACKLOG #5). Nếu profile đã có sẵn 2 field này
    thì cho user confirm/sửa nhanh; nếu chưa có thì hỏi 1 lượt."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    addr = _addr(session)
    profile = session.profile

    # Đã hỏi trong session này rồi → đi thẳng vào trích campaign.
    if session.pending_intake.get("_budget_team_context"):
        await _show_extracted_campaigns(message, session)
        return

    budget = (profile.monthly_marketing_budget or "").strip()
    team = (profile.team_size or "").strip()

    if budget and team:
        session.pending_intake["_budget_team_pending_confirm"] = "1"
        await save_session(session)
        await message.reply_text(
            f"💰 *Trước khi em trích campaign — chốt lại quy mô để đề xuất sát thực tế:*\n\n"
            f"💰 *Ngân sách marketing/tháng:* {_escape_md(budget)}\n"
            f"👥 *Team:* {_escape_md(team)}\n\n"
            f"Thông tin này còn đúng không {addr}?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Đúng rồi, tiếp tục", callback_data="budget_team_confirm")],
                [InlineKeyboardButton("✏️ Cập nhật", callback_data="budget_team_edit")],
            ]),
        )
        return

    session.pending_intake["_awaiting_budget_team"] = "1"
    await save_session(session)
    await message.reply_text(
        "💰 *Trước khi em trích campaign — cho em biết quy mô để đề xuất sát thực tế:*\n\n"
        "• Ngân sách marketing/tháng (cho campaign này, ước tính cũng được)\n"
        "• Team: số người + vai trò (vd \"1 content + thuê ngoài video\")\n\n"
        "_Vd: \"15-20tr/tháng · 1 mình làm content, outsource video lúc cần\"_",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _handle_budget_team_text(update, context, session, text: str) -> None:
    """User gõ Budget/Team (free text) → lưu context → trích campaign."""
    session.pending_intake.pop("_awaiting_budget_team", None)
    session.pending_intake["_budget_team_context"] = (text or "").strip()
    await save_session(session)
    await _show_extracted_campaigns(update.message, session)


async def _show_extracted_campaigns(message: Message, session, show_all: bool = False):
    """After strategy_confirm: extract 2-3 campaigns from synthesis roadmap + 8 strategy answers.
    Present as direct-pick buttons — no redundant needs re-questioning.

    show_all=True: re-render từ `_extracted_campaigns` đã cache (không gọi LLM lại),
    hiện cả campaign `scale: "stretch"` bị ẩn ban đầu (BACKLOG #5)."""
    from agents.campaign_ideation import extract_campaigns_from_synthesis
    import json as _json
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    addr = _addr(session)

    campaigns = None
    if show_all:
        try:
            campaigns = _json.loads(session.pending_intake.get("_extracted_campaigns") or "[]")
        except _json.JSONDecodeError:
            campaigns = None
        if not campaigns:
            show_all = False

    if not show_all:
        # Bridge yêu cầu output synthesis — nếu chưa có thì KHÔNG fallback, báo lỗi rõ.
        synthesis = (session.get_latest_result("synthesis") or "").strip()
        if not synthesis:
            await message.reply_text(
                f"⚠️ *Chưa có kế hoạch chiến lược (synthesis) để trích campaign.*\n\n"
                f"Sếp thử chạy lại bước lập kế hoạch, hoặc báo cho support nhé.\n\n{SUPPORT_NOTE}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        await message.reply_text(
            "✅ *Strategy đã chốt! Em đang trích campaign từ Roadmap...*",
            parse_mode=ParseMode.MARKDOWN,
        )

        campaigns = await extract_campaigns_from_synthesis(session)

        if not campaigns:
            from telegram import InlineKeyboardButton as _Btn, InlineKeyboardMarkup as _Kb
            retry_kb = _Kb([[_Btn("🔄 Thử lại", callback_data="extracted_campaign_more")]])
            await message.reply_text(
                f"⚠️ *Em chưa trích được campaign từ Roadmap.*\n\n"
                f"Sếp bấm thử lại giúp em. Nếu vẫn lỗi, chụp màn hình gửi support nhé.\n\n{SUPPORT_NOTE}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=retry_kb,
            )
            return

        session.pending_intake["_extracted_campaigns"] = _json.dumps(campaigns, ensure_ascii=False)
        await save_session(session)

    # Ẩn ban đầu các campaign "stretch" (tham vọng hơn quy mô hiện tại) — chỉ
    # hiện khi user bấm "🔍 Xem thêm phương án khác" (show_all=True).
    if show_all:
        visible = campaigns
        stretch_hidden = False
    else:
        visible = [c for c in campaigns if c.get("scale") != "stretch"]
        if not visible:
            visible = campaigns
        stretch_hidden = len(visible) < len(campaigns)

    num_emojis = ["1️⃣", "2️⃣", "3️⃣"]
    lines = [f"🗺️ *Em trích từ Roadmap {len(visible)} campaign cho {addr} chọn ngay:*\n"]
    for i, c in enumerate(visible):
        num = num_emojis[i] if i < 3 else f"{i+1}."
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"*{num} {c.get('name', '?')}*\n")
        lines.append(f"🎯 *Mục tiêu:* {c.get('goal', '?')}")
        lines.append(f"👥 *Target:* {c.get('target_segment', '?')}")
        lines.append(f"📱 *Kênh:* {c.get('channels', '?')}")
        lines.append(f"📅 *Độ dài gợi ý:* {c.get('duration_suggestion', '?')}")
        lines.append(f"💭 *Vì sao hợp:* {c.get('why_fit', '?')}\n")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if stretch_hidden:
        lines.append(
            "\n_Đây là campaign Max thấy phù hợp với quy mô hiện tại của sếp. "
            "Nếu muốn xem thêm hướng tham vọng hơn (cần thêm resource), bấm nút bên dưới._\n"
        )
    lines.append("\n_📅 Thời lượng / 🎟 % giảm — sếp quyết ở bước sau._\n")
    lines.append("👇 *Sếp chọn campaign nào để em làm Brief Campaign?*")

    rows = []
    for c in visible:
        idx = campaigns.index(c)
        num = num_emojis[idx] if idx < 3 else f"{idx+1}."
        label = f"{num} {c.get('name', '?')[:45]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"extracted_campaign_pick_{idx+1}")])
    if stretch_hidden:
        rows.append([InlineKeyboardButton("🔍 Xem thêm phương án khác (tham vọng hơn)", callback_data="extracted_campaign_show_more")])
    rows.append([InlineKeyboardButton("💡 Tôi có ý tưởng khác", callback_data="extracted_campaign_own_idea")])
    rows.append([InlineKeyboardButton("🔄 Đề xuất thêm options", callback_data="extracted_campaign_more")])
    keyboard = InlineKeyboardMarkup(rows)

    await send_long_message(message, "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def context_bot_typing(message: Message) -> None:
    """Send typing action — best-effort, ignore failures."""
    try:
        from telegram.constants import ChatAction
        await message.get_bot().send_chat_action(
            chat_id=message.chat_id, action=ChatAction.TYPING,
        )
    except Exception:
        pass


async def _run_pipeline_sequentially(message: Message, session):
    from bot.html_report import parse_agent_output, build_report

    task = session.selected_task or "full"
    task_label = TASK_LABELS.get(task, "Phân tích")
    total_stages = TASK_STAGE_COUNT.get(task, 1)

    if total_stages > 1:
        await message.reply_text(
            f"🔬 *Bắt đầu {task_label}!*\n\n"
            f"Em chạy {total_stages} bước phân tích, gửi card tóm tắt từng bước.\n"
            f"Xong xuôi em hỏi sếp muốn đánh theo hướng nào → mới lập kế hoạch.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await message.reply_text(
            f"🚀 *Bắt đầu {task_label}...*",
            parse_mode=ParseMode.MARKDOWN,
        )

    stage_count = 0
    parsed_stages: list[tuple[str, dict]] = []  # for HTML report

    async def progress_cb(msg: str):
        # Resilient: fallback to plain text if Markdown parse fails
        # (vd tier name có underscore không nằm trong */_ entity)
        try:
            await message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.warning("Progress message Markdown failed (%s) — falling back to plain", e)
            try:
                await message.reply_text(msg, parse_mode=None)
            except Exception as e2:
                logger.warning("Progress message plain fallback also failed: %s", e2)

    # Sprint 8.5 — dispatch: task=full + flag on → Multi-Agent Orchestrator,
    # các task khác → existing single-skill path (backward compat)
    from config import USE_MULTI_AGENT_PIPELINE
    if task == "full" and USE_MULTI_AGENT_PIPELINE:
        pipeline_runner = run_multi_agent_targeted
        logger.info("Using Multi-Agent Orchestrator (Sprint 8) for task=full")
    else:
        pipeline_runner = run_targeted_pipeline
        if task == "full":
            logger.info("Multi-Agent disabled (USE_MULTI_AGENT=false) — using legacy path")

    # Task "full" với multi-agent → chỉ chạy phase research (T1-T3)
    # Phase synthesis (T4-T5) chạy sau khi user trả lời 8 câu chiến lược
    runner_kwargs = {"progress_callback": progress_cb}
    if task == "full" and pipeline_runner is run_multi_agent_targeted:
        runner_kwargs["phase"] = "research"

    pipeline_aborted = False
    async for stage_key, result in pipeline_runner(session, **runner_kwargs):
        if stage_key == "pipeline_abort":
            pipeline_aborted = True
            parsed_stages.append((stage_key, parse_agent_output(result)))
            continue

        stage_count += 1

        parsed = parse_agent_output(result)
        parsed_stages.append((stage_key, parsed))

        from tools.token_tracker import get_latest_skill_entry
        token_entry = get_latest_skill_entry(session, stage_key)
        card_text = _format_card(stage_key, parsed, token_entry=token_entry)
        await send_long_message(
            message,
            card_text,
            parse_mode=ParseMode.MARKDOWN,
            # Intermediate stages: no keyboard (auto continue)
            # Last stage: handled below (Rating + chained followup)
            reply_markup=None,
        )
        await save_session(session)
        await asyncio.sleep(0.5)

    # After all stages complete: build + send HTML report
    # Hotfix: filter out stages bị timeout/error (result chứa "⚠️")
    # để HTML builder không cố parse skip message làm crash toàn report.
    valid_stages = [
        (k, p) for (k, p) in parsed_stages
        if p and not (p.get("summary", "") + p.get("deliverable", "")).startswith("⚠️")
        and not (p.get("raw", "") or "").startswith("⚠️")
    ]
    skipped_count = len(parsed_stages) - len(valid_stages)
    if skipped_count > 0:
        logger.warning(
            "HTML report: filtered %d skipped/error stages out of %d total",
            skipped_count, len(parsed_stages),
        )

    if valid_stages:
        # Tách BUILD (generate) khỏi SEND — lỗi mạng khi gửi file lớn (Telegram
        # đã nhận file nhưng response timeout) KHÔNG được báo nhầm "không generate được".
        html_str = None
        try:
            from bot.html_report import generate_archetype_banner_html
            signal_text = " ".join(filter(None, [
                session.profile.product_service or "",
                session.profile.target_customer or "",
            ]))
            # LLM-personalize banner (fallback template nếu LLM fail)
            archetype_banner_html = await generate_archetype_banner_html(
                business_name=session.profile.business_name or "Business",
                industry=session.profile.industry or "",
                signal_text=signal_text,
                parsed_stages=valid_stages,
            )
            html_str = build_report(
                business_name=session.profile.business_name or "Business",
                industry=session.profile.industry or "",
                stage=session.profile.stage or "",
                parsed_stages=valid_stages,
                archetype_signal_text=signal_text,
                archetype_banner_html=archetype_banner_html,
            )
        except Exception as e:
            logger.exception("Failed to BUILD HTML report: %s", e)
            await message.reply_text(
                "⚠️ Không dựng được file HTML — phần tóm tắt ở trên đã đủ. Sếp có thể hỏi thêm tự do."
            )

        if html_str:
            try:
                await _send_html_report(
                    message, html_str, session,
                    caption=(
                        f"📄 *Kết quả một phần* — một số bước bị timeout, đây là phần đã hoàn thành.\n\n{SUPPORT_NOTE}"
                        if pipeline_aborted else None
                    ),
                )
                if not pipeline_aborted and skipped_count > 0:
                    await message.reply_text(
                        f"ℹ️ Report HTML đã gửi, nhưng có {skipped_count} bước bị timeout/lỗi — "
                        "không xuất hiện trong report. Sếp có thể chạy lại các bước đó riêng lẻ."
                    )
            except Exception as e:
                # File có thể ĐÃ tới user dù await raise (timeout response). Không
                # báo "không generate được" — chỉ log + nhắc nhẹ.
                logger.warning("HTML report send raised (file may still have arrived): %s", e)
    elif stage_count > 0:
        # All stages failed/skipped → no valid content for HTML
        await message.reply_text(
            "⚠️ Tất cả bước phân tích đều timeout/lỗi — không có gì để render HTML. "
            "Sếp thử chạy lại từng bước riêng lẻ (từ menu Chiến Lược) để xem bước nào fail.\n\n"
            + SUPPORT_NOTE
        )

    if stage_count > 0 and stage_count == total_stages:
        # Chained followup — Brief Campaign hoặc skill khác đang chờ Strategy
        followup_skill = session.pending_followup_skill
        if followup_skill:
            session.pending_followup_skill = None
            await save_session(session)
            from agents.task_registry import get_task as _get_task
            followup_label = (_get_task(followup_skill).label if _get_task(followup_skill) else followup_skill)
            await message.reply_text(
                f"✅ *Nghiên Cứu & Phân Tích xong rồi ạ!* Em tiếp tục *{followup_label}* cho sếp luôn nhé...",
                parse_mode=ParseMode.MARKDOWN,
            )
            session.selected_task = followup_skill
            await save_session(session)
            await _send_single_shot_form(message, session, followup_skill)
            return

        # Sprint 2: Rating loop sau khi xong pipeline
        session.pending_intake["_awaiting_rating_for"] = task
        await save_session(session)

        if total_stages > 1 and task == "full":
            # Research done — 7-question strategic consultation
            await _start_strategic_consultation(message, session)
        elif total_stages > 1:
            addr = _addr(session)
            await message.reply_text(
                f"✅ *Hoàn thành {task_label}!* Mở file HTML để xem báo cáo đầy đủ.\n\n"
                f"─────────────────────\n"
                f"🔎 *{addr.capitalize()} xem qua giúp em:* phân tích trên đã chính xác chưa ạ?\n\n"
                f"• *Chuẩn rồi* → em chuyển sang lên kế hoạch campaign cụ thể.\n"
                f"• *Cần sửa* → {addr} chỉ rõ phần nào.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=CONFIRM_STRATEGY_KEYBOARD,
            )
        elif task == "strategy":
            # Strategy done → ask if plan is OK or needs adjustment
            addr = _addr(session)
            await message.reply_text(
                f"✅ *Kế hoạch đề xuất đã xong!* Mở file HTML để xem đầy đủ.\n\n"
                f"─────────────────────\n"
                f"📋 *{addr.capitalize()} xem qua giúp em:* kế hoạch trên ổn chưa, "
                f"hay cần điều chỉnh gì không ạ?\n\n"
                f"• *Ổn rồi* → em lên Lịch Nội Dung theo kế hoạch luôn\n"
                f"• *Cần điều chỉnh* → {addr} nói rõ đổi hướng nào (vd: \"nặng về awareness\", "
                f"\"tập trung retention\"), em chỉnh và chạy lại",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=CONFIRM_STRATEGY_KEYBOARD,
            )
        else:
            await message.reply_text(
                f"✅ *Hoàn thành {task_label}!*\n\nSếp đánh giá output em vừa làm thế nào ạ?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=RATING_KEYBOARD,
            )


# ─── Name personalization helpers ───────────────────────────────

def _validate_user_name(name: str) -> tuple[bool, str]:
    """Validate user_name: dưới 20 ký tự, có chữ cái. Returns (is_valid, error_msg)."""
    import re as _re

    if not name or not name.strip():
        return False, "Em chưa nhận được tên."

    name = name.strip()

    if len(name) > 20:
        return False, "Tên dài quá (>20 ký tự). Sếp đặt nickname ngắn gọn nhé."

    # Phải có ít nhất 1 chữ cái
    if not _re.search(r"[a-zA-ZÀ-ỹ]", name):
        return False, "Tên cần có ít nhất 1 chữ cái."

    return True, ""


def _get_user_name(session) -> str:
    """Lấy user_name từ preferences, fallback empty string."""
    return (session.preferences.get("user_name", "") or "").strip()


def _addr(session) -> str:
    """Cách xưng hô: 'sếp Nhiên' hoặc 'sếp' nếu chưa có tên."""
    name = _get_user_name(session)
    return f"sếp {name}" if name else "sếp"


def _personalize(text: str, session) -> str:
    """Replace 'sếp' với 'sếp {name}' trong text nếu có user_name."""
    name = _get_user_name(session)
    if not name:
        return text
    import re as _re
    # Match standalone 'sếp' (case-insensitive) NOT already followed by a name
    def repl(m):
        head = m.group(1)  # 'S' or 's'
        rest = m.group(2)  # 'ếp'
        return f"{head}{rest} {name}"
    # 'sếp' at word boundary, not followed by ' <Name>' already
    return _re.sub(r"\b(s|S)(ếp)\b(?!\s+[A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ])", repl, text)


# ─── Claude advisor fallback ────────────────────────────────────

def _escape_md(val) -> str:
    """Loại bỏ ký tự đặc biệt Markdown khỏi giá trị động.

    Telegram legacy Markdown (ParseMode.MARKDOWN) KHÔNG hỗ trợ backslash-escape —
    `\\_` vẫn bị parse thành entity dở dang → lỗi "Can't parse entities". Cách an
    toàn duy nhất là loại bỏ/thay thế các ký tự _ * ` [ ] khỏi nội dung động.
    """
    if not val:
        return str(val) if val is not None else ""
    return (str(val).replace("*", "").replace("_", "-")
            .replace("`", "'").replace("[", "(").replace("]", ")"))


def _sanitize_telegram_md(text: str) -> str:
    """Lớp an toàn: chuyển markdown nặng (heading/blockquote) về dạng Telegram
    legacy render được. LLM đôi khi vẫn xuất `#`, `>` dù prompt đã cấm.

    - `### Heading` / `## H` / `# H`  → `*Heading*`
    - leading `> blockquote`          → bỏ dấu `>`
    - dòng phân cách `---` / `***`     → bỏ (Telegram không render thành line)
    """
    import re as _re
    if not text:
        return text
    out_lines = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        # Heading → bold
        m = _re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            heading = m.group(2).strip().rstrip("#").strip()
            out_lines.append(f"*{heading}*" if heading else "")
            continue
        # Blockquote → bỏ dấu >
        if stripped.startswith(">"):
            out_lines.append(stripped.lstrip(">").lstrip())
            continue
        # Horizontal rule → bỏ
        if _re.match(r"^([-*_])\1{2,}\s*$", stripped):
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip()


# Regex: matches facebook.com / fb.com / m.facebook.com URLs
_FB_URL_RE = re.compile(
    r"(?i)\b(?:https?://)?(?:www\.|m\.)?(?:facebook|fb)\.com/(\S+)"
)


async def _try_fb_url_intercept(update, context, session, text: str) -> bool:
    """Detect FB URL in user message → pre-fill fanpage_url and route to
    competitor_spy. KHÔNG pre-judge URL pattern — chỉ extract, để Graph API
    quyết định xem URL có truy cập được không (qua resolve_fb_url ở prefetch).

    Returns True nếu đã handle.
    """
    m = _FB_URL_RE.search(text)
    if not m:
        return False

    full_url = m.group(0)
    if not full_url.startswith("http"):
        full_url = "https://" + full_url

    # Save URL — competitor_name placeholder; prefetch sẽ override bằng tên
    # thật từ Graph API nếu resolve OK.
    session.pending_intake["fanpage_url"] = full_url
    if "competitor_name" not in session.pending_intake:
        session.pending_intake["competitor_name"] = "(em sẽ pull tên thật từ Graph API)"
    session.pending_intake[OPS_INTAKE_AWAITING] = "competitor_spy"
    session.selected_task = "competitor_spy"
    session.stage = PipelineStage.INTAKE
    session.pending_intake.pop("_advisor_mode", None)
    session.pending_intake.pop("_active_persona", None)
    await save_session(session)

    await update.message.reply_text(
        f"🔍 *Em nhận link:* `{full_url}`\n\n"
        f"Gõ *ok* để em verify qua Graph API và pull ads từ Facebook Ads Library.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return True


async def _try_persona_route(update, context, session, text: str) -> bool:
    """Thử route free-form message đến đúng domain expert persona.

    Priority: @tag direct > keyword score >= 1 > fall through.
    Returns True nếu đã handle → caller nên return ngay.
    """
    import re as _re
    from agents.manager_personas import (
        route_to_persona, run_persona_turn,
        render_persona_intro, get_persona, TAG_MAP,
    )

    # ── @tag direct invocation (@minh, @trang, ...) ──────────────
    persona = None
    first_time = True
    actual_text = text

    tag_match = _re.match(r"^@([a-zA-ZÀ-ỹ]+)\s*(.*)?$", text.strip(), _re.IGNORECASE | _re.UNICODE)
    if tag_match:
        raw_tag = tag_match.group(1).lower()
        # Normalize diacritics: đức→duc, hương→huong
        _norm = str.maketrans("àáảãạăắặẳẵằâấậẩẫắèéẻẹêếềệểễìíỉịòóỏọôốồổỗộơớờởỡợùúủụưứừửữựỳýỷỵỹđ",
                              "aaaaaaaaaaaaaaaeeeeeeeeeeiiiioooooooooooooooooouuuuuuuuuuuyyyyyd")
        tag_norm = raw_tag.translate(_norm)
        persona_key = TAG_MAP.get(tag_norm) or TAG_MAP.get(raw_tag)
        if persona_key:
            persona = get_persona(persona_key)
            actual_text = (tag_match.group(2) or "").strip() or text

    # ── Keyword routing if no @tag ────────────────────────────────
    if persona is None:
        persona = route_to_persona(text, session)

    if persona is None:
        return False

    # ── If re-entering same persona conversation, skip full intro ─
    active_key = session.pending_intake.get("_active_persona")
    first_time = active_key != persona.key

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    if first_time:
        await update.message.reply_text(
            render_persona_intro(persona, first_time=True),
            parse_mode=ParseMode.MARKDOWN,
        )

    # ── Run persona LLM turn ──────────────────────────────────────
    persona_response = await run_persona_turn(session, actual_text, persona)

    # ── Parse markers (strip both before display) ────────────────
    dispatch_match = _re.search(r"\[SKILL_DISPATCH:(\w+)\]", persona_response)
    persona_dispatch_match = _re.search(r"\[PERSONA_DISPATCH:(\w+)\]", persona_response)
    clean = _re.sub(r"\[(?:SKILL|PERSONA)_DISPATCH:\w+\]", "", persona_response).strip()
    clean = _sanitize_telegram_md(clean)

    # ── [PERSONA_DISPATCH:key] — Max giao việc xuống manager Layer 3 ─
    if persona_dispatch_match and getattr(persona, "is_orchestrator", False):
        target_key = persona_dispatch_match.group(1)
        target = get_persona(target_key)
        if target and not getattr(target, "is_orchestrator", False):
            if clean:
                await update.message.reply_text(clean, parse_mode=ParseMode.MARKDOWN)
            # Chuyển ngữ cảnh sang manager được giao + mở menu skill của họ
            session.pending_intake["_active_persona"] = target.key
            session.pending_intake["_advisor_mode"] = "1"
            await save_session(session)
            from agents.task_registry import get_task as _get_task
            buttons = []
            for skill_name in target.owns_skills:
                tcfg = _get_task(skill_name)
                label = f"{tcfg.button_emoji} {tcfg.label}" if tcfg else skill_name
                buttons.append([InlineKeyboardButton(label, callback_data=f"task_{skill_name}")])
            buttons.append([InlineKeyboardButton("💬 Hỏi tiếp", callback_data="continue_advisor")])
            await update.message.reply_text(
                f"{target.emoji} *{target.name}* ({target.role}) nhận việc từ Max — chọn skill:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return True

    if dispatch_match:
        skill_name = dispatch_match.group(1)
        from agents.task_registry import TASK_REGISTRY
        if skill_name in TASK_REGISTRY and skill_name in persona.owns_skills:
            if clean:
                await update.message.reply_text(clean, parse_mode=ParseMode.MARKDOWN)
            session.selected_task = skill_name
            session.pending_intake.pop("_advisor_mode", None)
            session.pending_intake.pop("_active_persona", None)
            await save_session(session)
            await _launch_task_from_advisor(update, context, session, skill_name)
            return True

    # ── Advisory response — no skill dispatched yet ───────────────
    session.pending_intake["_active_persona"] = persona.key
    session.pending_intake["_advisor_mode"] = "1"
    await save_session(session)

    await send_long_message(
        update.message,
        clean or _sanitize_telegram_md(persona_response),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"⚡ Chọn skill ({persona.emoji} {persona.name})",
                callback_data=f"persona_menu_{persona.key}",
            )],
            [InlineKeyboardButton("💬 Hỏi tiếp",       callback_data="continue_advisor")],
            [InlineKeyboardButton("⚙️ Mở menu task",   callback_data="menu_main")],
        ]),
    )
    return True


async def _claude_advisor_fallback(update, context, session, text: str):
    """User nhắn free-form ngoài skill flow → Sonnet trả lời với full context.

    Context bao gồm: profile + tất cả results đã chạy + Strategy synthesis.
    Sau khi reply, kèm gợi ý các task có sẵn.
    """
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    import anthropic
    from config import CLAUDE_SONNET_MODEL, ANTHROPIC_API_KEY

    # Build context: profile + key results
    parts = []
    if session.profile and session.profile.business_name:
        parts.append(session.profile.to_context_string())

    synthesis = session.get_latest_result("synthesis") or session.get_latest_result("strategy")
    if synthesis:
        parts.append(f"## Marketing Strategy đã có:\n{synthesis[:3500]}")

    # Inject summaries của các skill đã chạy
    for skill_key in ("market_research", "competitor", "customer_insight", "psychology_pricing",
                       "campaign_brief", "content_calendar"):
        r = session.get_latest_result(skill_key)
        if r:
            parts.append(f"## Kết quả {skill_key}:\n{r[:1500]}")

    context_str = "\n\n---\n\n".join(parts) if parts else "_(User chưa chạy task nào, chưa có profile)_"

    en_level = session.preferences.get("en_level", "moderate")
    en_note = {
        "none":     "Dùng THUẦN VIỆT 100% — kể cả thuật ngữ marketing dịch sang VN.",
        "moderate": "Có thể dùng thuật ngữ EN nhưng kèm giải thích VN trong ngoặc.",
        "fluent":   "Dùng thuật ngữ EN tự nhiên, không cần giải thích.",
    }.get(en_level, "Moderate EN level.")

    user_name = _get_user_name(session)
    name_directive = (
        f"User name: '{user_name}'. Khi xưng hô gọi 'sếp {user_name}' (vd: 'Em chào sếp {user_name}', "
        f"'Sếp {user_name} ơi'), KHÔNG gọi chỉ 'sếp' nếu có tên này."
    ) if user_name else "User chưa cho biết tên, gọi 'sếp' thôi."

    system_text = f"""Bạn là Max — AI CMO cho founder Việt Nam.

Tone: xưng "em" gọi user "sếp", professional + thân thiện.
{name_directive}
Language: {en_note}

🎛️ **INTENT ROUTING — khi user yêu cầu mở menu / xem task / xem skill / hỏi em làm được gì:**
- Reply ngắn 1-2 câu giới thiệu rồi kết thúc bằng marker `[OPEN_MENU]` ở dòng cuối cùng
- Vd: "OK ạ, đây là menu task em hỗ trợ:\n[OPEN_MENU]"
- KHÔNG dùng marker này nếu user chỉ hỏi advisor bình thường

🎯 **INTENT ROUTING — khi user chỉ định rõ 1 skill cụ thể:**
- Nếu user nói rõ tên 1 task (vd: "chạy phân tích đối thủ", "lên lịch nội dung") → kết thúc bằng marker `[RUN_TASK:<task_name>]`
- Vd: "OK em chạy ngay ạ.\n[RUN_TASK:competitor]"
- task_name AVAILABLE: market / competitor / customer / pricing / strategy / full /
  content_calendar / content_generator / email_zalo_sequence / competitor_spy
- task_name COMING SOON (KHÔNG được dùng RUN_TASK, chỉ thông báo "sắp ra mắt"):
  campaign_brief / ads_generator / video_scripts / sales_inbox_script

NHIỆM VỤ: User nhắn câu hỏi/yêu cầu free-form ngoài flow skill chuẩn.
Trả lời như 1 marketing advisor có context business của sếp.

QUY TẮC:
- BÁM SÁT business profile + results đã có (đừng generic)
- Trả lời NGẮN GỌN (2-4 đoạn, max ~400 từ)
- Nếu câu hỏi liên quan task có sẵn → GỢI Ý chạy task đó cuối câu trả lời
  (vd: "Để có data đầy đủ về đối thủ, sếp chạy task *Phân Tích Đối Thủ* nhé")
- Nếu user hỏi vu vơ / chào / cảm ơn → reply ngắn, gợi ý mở menu
- KHÔNG bịa số liệu cụ thể, chỉ đưa khuyến nghị dựa trên framework

Skills có sẵn (gợi ý nếu phù hợp):
🎯 Chiến lược: Tìm Hiểu Thị Trường, Phân Tích Đối Thủ, Insight Khách Hàng,
   Chiến Lược Giá, Kế Hoạch Đề Xuất, Phân Tích Tổng Hợp A→Z
⚙️ Sản xuất: Lịch Nội Dung, Sản Xuất Nội Dung, Chăm Sóc Khách Hàng
📊 Theo dõi: Theo Dõi Đối Thủ, Báo Cáo Ads

🚧 Sắp ra mắt (chưa dùng được, nếu user hỏi → thông báo coming soon):
   Viết Brief Campaign, Sản Xuất Nội Dung Ads, Viết Kịch Bản Video,
   Thiết Kế Website, Kịch Bản Sales"""

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = await client.messages.create(
            model=CLAUDE_SONNET_MODEL,
            max_tokens=1200,
            system=[{
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": f"{context_str}\n\n---\n\nUser nhắn: {text}",
            }],
        )
        # Token tracking
        try:
            from tools.token_tracker import track_usage
            track_usage(session, response, label="advisor")
        except Exception as e:
            logger.warning("Token tracking failed (advisor): %s", e)
        reply = response.content[0].text
    except Exception as e:
        logger.exception("Claude advisor fallback failed: %s", e)
        await update.message.reply_text(
            "⚠️ Em đang gặp lỗi kết nối. Sếp thử chọn task từ menu nhé:",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # Detect intent markers từ Sonnet response
    open_menu = "[OPEN_MENU]" in reply
    run_task_match = re.search(r"\[RUN_TASK:(\w+)\]", reply)

    # Strip markers khỏi text hiển thị
    clean_reply = re.sub(r"\[OPEN_MENU\]|\[RUN_TASK:\w+\]", "", reply).strip()

    # CASE 1: User yêu cầu mở menu
    if open_menu:
        session.pending_intake.pop("_advisor_mode", None)
        await save_session(session)
        await send_long_message(
            update.message,
            clean_reply or "OK ạ, đây là menu task em hỗ trợ:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # CASE 2: User yêu cầu chạy task cụ thể
    if run_task_match:
        task_name = run_task_match.group(1)
        from agents.task_registry import TASK_REGISTRY
        if task_name in TASK_REGISTRY:
            session.pending_intake.pop("_advisor_mode", None)
            session.selected_task = task_name
            await save_session(session)
            if clean_reply:
                await update.message.reply_text(clean_reply, parse_mode=ParseMode.MARKDOWN)
            # Launch skill flow — same path as task_X callback
            await _launch_task_from_advisor(update, context, session, task_name)
            return
        # Invalid task name → fall through to default advisor reply

    # CASE 3: Default — advisor reply với "Hỏi tiếp" / "Mở menu"
    session.pending_intake["_advisor_mode"] = "1"
    await save_session(session)

    await send_long_message(
        update.message,
        clean_reply or reply,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Hỏi tiếp",      callback_data="continue_advisor")],
            [InlineKeyboardButton("⚙️ Mở menu task", callback_data="menu_main")],
        ]),
    )


async def _launch_task_from_advisor(update, context, session, task_name: str):
    """Khi advisor detect [RUN_TASK:X] → launch skill flow tương đương click button."""
    from agents.task_registry import OPERATIONAL_TASKS, get_task
    SINGLE_SHOT_STRATEGIC = {"market", "competitor", "customer", "pricing"}
    STRATEGY_GATED = {"campaign_brief", "content_calendar"}

    msg = update.message

    # brand_positioning (Linh): cần T2 USP / T4 synthesis làm input
    if task_name == "brand_positioning" and not (
        session.get_latest_result("usp_definition")
        or session.get_latest_result("synthesis")
    ):
        session.pending_followup_skill = task_name
        await save_session(session)
        await msg.reply_text(
            "🏛️ *Messaging House cần USP + Strategy nền (T2/T4).* "
            "Em chạy *Nghiên Cứu & Phân Tích Thị Trường* trước nhé sếp?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=NEEDS_STRATEGY_KEYBOARD,
        )
        return

    # Strategy gating
    if task_name in STRATEGY_GATED:
        has_strategy = bool(
            session.get_latest_result("synthesis") or session.get_latest_result("strategy")
        )
        if has_strategy:
            # campaign_brief → full A→Z flow (giống nút Brief Campaign / strategy_confirm)
            if task_name == "campaign_brief":
                await _ask_budget_team_before_campaigns(msg, session)
            else:
                await _send_strategy_aware_form(msg, session, task_name)
        else:
            session.pending_followup_skill = task_name
            await save_session(session)
            task_label = (get_task(task_name).label if get_task(task_name) else task_name)
            await msg.reply_text(
                f"📋 *{task_label} cần Strategy nền.* Em chạy *Nghiên Cứu & Phân Tích Thị Trường* trước nhé sếp?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=NEEDS_STRATEGY_KEYBOARD,
            )
        return

    # Content skills cần Calendar trước
    if task_name in ("content_generator", "post_batch", "video_script_gen"):
        if not session.get_latest_result("content_calendar"):
            session.pending_followup_skill = task_name
            await save_session(session)
            await msg.reply_text(
                "✍️ Sản Xuất Nội Dung cần *Lịch Nội Dung* trước. Em chạy Calendar trước nhé?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📅 Chạy Lịch Nội Dung trước", callback_data="task_content_calendar")],
                    [InlineKeyboardButton("⏭️ Quay lại menu",              callback_data="menu_main")],
                ]),
            )
            return

    # Special skills with variant chooser
    if task_name in ("ads_copy", "ads_generator"):
        session.selected_task = "ads_generator"
        await save_session(session)
        await msg.reply_text(
            "📢 *Sản Xuất Nội Dung Ads* — Sếp muốn gen tier nào trước ạ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ADS_COPY_TIER_KEYBOARD,
        )
        return
    if task_name == "video_scripts":
        await msg.reply_text(
            "🎬 *Viết Kịch Bản Video* — Brief cho loại creator nào ạ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=VIDEO_CREATOR_KEYBOARD,
        )
        return

    # Operational + strategic single-shot → form
    if task_name in OPERATIONAL_TASKS or task_name in SINGLE_SHOT_STRATEGIC:
        await _send_single_shot_form(msg, session, task_name)
        return

    # Strategy multi-turn / full → intake
    session.stage = PipelineStage.INTAKE
    await save_session(session)
    opening = TASK_OPENING_QUESTIONS.get(task_name, TASK_OPENING_QUESTIONS["full"])
    task_label = (get_task(task_name).label if get_task(task_name) else task_name)
    await msg.reply_text(
        f"✅ *{task_label}*\n\n{opening}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── Feedback log DB helper ──────────────────────────────────────

async def _log_feedback_to_db(session, skill_name: str, rating: int, feedback_text: str = ""):
    """Persist feedback vào table feedback_log (Task #12). Non-blocking."""
    try:
        from storage.feedback_log import log_feedback
        output = session.get_latest_result(skill_name) or ""
        user_correction = session.pending_intake.get("_pending_feedback", "")
        await log_feedback(
            user_id=session.user_id,
            skill_name=skill_name,
            rating=rating,
            feedback_text=feedback_text,
            industry=session.profile.industry or "",
            stage=session.profile.stage or "",
            business_name=session.profile.business_name or "",
            output_excerpt=output[:500],
            user_correction=user_correction,
        )
    except Exception as e:
        logger.warning("Feedback DB log failed (non-blocking): %s", e)


# ─── Facebook API pre-fetch helpers ─────────────────────────────

def _md_detail(s: str) -> str:
    """Strip Markdown v1 special characters from a dynamic detail string.
    Telegram Markdown v1 has no backslash escaping, so _ * ` [ must be removed."""
    return s.replace("_", "-").replace("*", "").replace("`", "'").replace("[", "(").replace("]", ")")


async def _abort_with_fb_error(message: Message, session, task_name: str, fb_status: dict):
    """Send reason-specific error message + reset session, so user knows
    why the skill refused to run. No menu keyboard inline (per user feedback)."""
    session.stage = PipelineStage.TASK_SELECT
    session.pending_intake.pop(OPS_INTAKE_AWAITING, None)
    await save_session(session)

    reason = fb_status.get("reason", "no_token")
    detail = fb_status.get("detail", "")

    # Skill-specific suffix (what user can do as workaround)
    workaround = {
        "competitor_spy": (
            "*Workaround:* Paste ads tay — chạy lại task và điền vào ô *Paste ads tay* "
            "(text 3-10 ads copy từ https://facebook.com/ads/library)."
        ),
        "ads_analytics": (
            "*Workaround:* Chạy lại skill và điền số liệu vào ô *Paste số liệu thủ công* — "
            "em sẽ phân tích từ số sếp paste thay vì pull API."
        ),
        "ads_optimizer": (
            "*Workaround:* Task này BẮT BUỘC live FB API (cần campaign ID thật để "
            "thao tác). Không thể paste tay. Phải fix env var trước."
        ),
    }.get(task_name, "")

    # Reason-specific message
    if reason == "no_token":
        body = (
            "🛑 *FB API chưa hoạt động.*\n\n"
            "Server chưa có `FB_ACCESS_TOKEN`. ⚠️ *KHÔNG paste token vào chat* — "
            "admin set trên Railway dashboard → Variables."
        )
    elif reason == "no_account":
        body = (
            "🛑 *FB Ad Account chưa cấu hình.*\n\n"
            "Server chưa có `FB_AD_ACCOUNT_ID` env var. Admin set trên Railway "
            "(dạng `act_1234567890`)."
        )
    elif reason == "page_not_found":
        body = (
            f"🛑 *Không tìm được Page trên FB.*\n\n"
            f"{_md_detail(detail)}\n\n"
            "Sếp check lại link fanpage (URL công khai dạng `https://facebook.com/tenpage`)."
        )
    elif reason == "is_user":
        body = (
            f"🛑 *Link này là user profile cá nhân, không phải Page.*\n\n"
            f"{_md_detail(detail)}\n\n"
            "FB Ads Library *chỉ phân tích Pages* (Page có `category`, user thì không). "
            "Nếu đối thủ chạy quảng cáo từ user profile thì sẽ không có data Ads Library."
        )
    elif reason == "private":
        body = (
            f"🛑 *FB API không có quyền truy cập link này.*\n\n"
            f"```\n{detail}\n```\n"
            "Page có thể private/restricted, hoặc token thiếu permission. "
            "Admin check token có `pages_read_engagement` + `ads_read` không."
        )
    elif reason == "invalid_url":
        body = (
            f"🛑 *URL không hợp lệ.*\n\n"
            f"{_md_detail(detail)}\n\n"
            "Sếp gửi URL Facebook đầy đủ (vd `https://facebook.com/cocoonvn`)."
        )
    elif reason == "no_ads_in_country":
        body = (
            f"🛑 *Page không có ads đang chạy ở VN.*\n\n"
            f"{_md_detail(detail)}\n\n"
            "Có thể đối thủ không chạy quảng cáo Meta hiện tại, hoặc chạy ở thị trường khác."
        )
    elif reason == "no_insights":
        body = (
            f"🛑 *Ad Account không có data trong khoảng thời gian này.*\n\n"
            f"{_md_detail(detail)}\n\n"
            "Sếp check: account ID có đúng không, period có campaign chạy không, "
            "hoặc đổi `date_range` sang khoảng dài hơn."
        )
    elif reason == "no_campaigns":
        body = (
            f"🛑 *Ad Account chưa có campaign nào.*\n\n"
            f"{_md_detail(detail)}\n\n"
            "Task tối ưu cần campaign tồn tại trên FB. Tạo campaign trước trong Ads Manager."
        )
    elif reason == "api_error":
        body = (
            f"🛑 *FB API trả lỗi.*\n\n"
            f"```\n{detail}\n```\n"
            "Thường do: token hết hạn (user token 60 ngày), thiếu permission "
            "(`ads_read` / `ads_management`), hoặc ad account ID sai."
        )
    elif reason == "no_input":
        body = (
            "🛑 *Em chưa có tên đối thủ hoặc link Page.*\n\n"
            "Chạy lại task và điền *Tên đối thủ* (bắt buộc) hoặc *Link Facebook Page*."
        )
    else:
        body = f"🛑 *FB API fail — {reason}*\n\n{_md_detail(detail)}"

    full = body + (f"\n\n{workaround}" if workaround else "") + "\n\n_Gõ /menu để chọn task khác._"
    await message.reply_text(full, parse_mode=ParseMode.MARKDOWN)


async def _prefetch_competitor_ads(message: Message, session) -> dict:
    """Pre-fetch FB Ads Library data cho competitor_spy skill.
    Ưu tiên link fanpage (search_by_page_id) → chính xác hơn search_terms.
    Inject _fb_data + _fb_page_id (để dùng cho auto-monitor sau).

    Returns dict: {"ok": bool, "reason": str, "detail": str}
      reason ∈ {"ok", "no_token", "no_input", "page_not_found",
                "no_ads_in_country", "api_error"}
    """
    from tools.fb_ads_library import (
        search_competitor_ads, search_by_page_id,
        format_ads_for_analysis, resolve_fb_url, is_available,
    )
    if not is_available():
        logger.info("FB Ads Library not configured — skipping pre-fetch")
        return {"ok": False, "reason": "no_token", "detail": "FB_ACCESS_TOKEN chưa set trên server"}

    competitor_name = (
        session.pending_intake.get("competitor_name")
        or session.pending_intake.get("competitor")
        or session.profile.competitors
        or ""
    )
    fanpage_url = session.pending_intake.get("fanpage_url", "").strip()

    if not competitor_name and not fanpage_url:
        return {"ok": False, "reason": "no_input", "detail": "Không có tên đối thủ hoặc URL fanpage"}

    # Resolve URL → ask Graph API what it actually is (Page / User / 404 / private)
    page_id = None
    if fanpage_url:
        await message.reply_text(
            f"🔗 Em đang verify link {fanpage_url} qua Graph API...",
            parse_mode=ParseMode.MARKDOWN,
        )
        resolution = await resolve_fb_url(fanpage_url)
        logger.info(
            "resolve_fb_url(%s) → ok=%s reason=%s detail=%s",
            fanpage_url, resolution["ok"], resolution["reason"], resolution["detail"],
        )
        if resolution["ok"]:
            page_id = resolution["page_id"]
            session.pending_intake["_fb_page_id"] = page_id
            # Override placeholder competitor_name with real page name
            if resolution.get("page_name"):
                session.pending_intake["competitor_name"] = resolution["page_name"]
                competitor_name = resolution["page_name"]
        else:
            # Link không phải Page khả dụng — surface real reason
            return {
                "ok": False,
                "reason": resolution["reason"],
                "detail": resolution["detail"],
            }

    # Notify user
    await message.reply_text(
        f"🔍 Em đang tìm ads của *{competitor_name or fanpage_url}* trên Facebook Ads Library...",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        if page_id:
            ads = await search_by_page_id(page_id, country="VN", limit=20)
        else:
            ads = await search_competitor_ads(
                search_terms=competitor_name or fanpage_url,
                country="VN",
                limit=20,
            )
    except Exception as e:
        err = str(e)[:300]
        logger.warning("FB Ads Library API call failed: %s", err)
        return {"ok": False, "reason": "api_error", "detail": err}

    if not ads:
        if fanpage_url and not page_id:
            return {
                "ok": False,
                "reason": "page_not_found",
                "detail": f"Không resolve được Page ID từ {fanpage_url}",
            }
        return {
            "ok": False,
            "reason": "no_ads_in_country",
            "detail": "Page tồn tại nhưng không có ads đang chạy ở VN (country=VN, limit=20)",
        }

    fb_data = format_ads_for_analysis(ads, competitor_name or "đối thủ")
    session.pending_intake["_fb_data"] = fb_data
    # Lưu ad IDs cho monitor diff sau
    session.pending_intake["_fb_ad_ids"] = ",".join(a.get("id", "") for a in ads if a.get("id"))
    logger.info("FB Ads Library: fetched %d ads (page_id=%s)", len(ads), page_id)
    return {"ok": True, "reason": "ok", "detail": f"{len(ads)} ads fetched"}


async def _prefetch_performance_data(message: Message, session) -> dict:
    """Pre-fetch FB Marketing API data cho ads_analytics / ads_intelligence skill.
    Ưu tiên token per-user (OAuth), fallback về global env var.

    Returns dict: {"ok": bool, "reason": str, "detail": str}
      reason ∈ {"ok", "no_token", "no_account", "no_insights", "api_error"}
    """
    from tools.fb_marketing import (
        get_account_insights, format_insights_for_analysis, format_ad_level_for_analysis, is_available,
    )
    from tools.crypto import decrypt_token
    from storage.fb_connections import get_connection
    from config import FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID

    # ── Ưu tiên per-user OAuth token ────────────────────────────
    user_token = None
    user_account_id = None
    user_account_name = None

    user_conn = await get_connection(session.user_id)
    if user_conn and user_conn.get("encrypted_token"):
        try:
            user_token = decrypt_token(user_conn["encrypted_token"])
            user_account_id = user_conn.get("ad_account_id")
            user_account_name = user_conn.get("account_name") or user_account_id
        except Exception as e:
            logger.warning("Decrypt user token failed for user=%d: %s", session.user_id, e)
            user_token = None

    # ── Fallback về global env var ───────────────────────────────
    access_token = user_token or FB_ACCESS_TOKEN
    account_id   = user_account_id or FB_AD_ACCOUNT_ID

    if not access_token:
        return {"ok": False, "reason": "no_token", "detail": "FB_ACCESS_TOKEN chưa set trên server"}
    if not account_id:
        return {"ok": False, "reason": "no_account", "detail": "FB_AD_ACCOUNT_ID chưa set trên server"}
    if not user_token and not is_available():
        return {"ok": False, "reason": "no_token", "detail": "FB Marketing API không khả dụng"}

    # Map date label → FB date_preset
    period_raw = (
        session.pending_intake.get("date_range")
        or session.pending_intake.get("period")
        or "30 ngày"
    ).lower()

    date_preset_map = {
        "hôm nay": "today", "today": "today", "live": "today", "real-time": "today", "realtime": "today",
        "hôm qua": "yesterday", "yesterday": "yesterday",
        "7":  "last_7d",  "7 ngày":  "last_7d",
        "14": "last_14d", "14 ngày": "last_14d",
        "30": "last_30d", "30 ngày": "last_30d",
        "90": "last_90d", "90 ngày": "last_90d",
        "tháng này": "this_month",
        "tháng trước": "last_month",
    }
    date_preset = "last_30d"
    for keyword, preset in date_preset_map.items():
        if keyword in period_raw:
            date_preset = preset
            break

    # Hiện account đang dùng để pull (chọn account đã làm ở bước trước —
    # gate aud_pick: trong _send_single_shot_form — không hiện lại bộ đổi
    # tài khoản ở đây nữa, kẻo user tưởng phải chọn lại giữa lúc đang chạy).
    safe_name = (user_account_name or "").replace("*", "").replace("_", "-")
    pull_text = f"📊 Em đang pull data *{safe_name}*..." if safe_name else "📊 Em đang pull data Facebook Ads của sếp..."
    await message.reply_text(pull_text, parse_mode=ParseMode.MARKDOWN)

    level_raw = session.pending_intake.get("level", "campaign").lower()
    level = level_raw if level_raw in ("campaign", "adset", "ad") else "campaign"

    try:
        insights = await get_account_insights(
            date_preset=date_preset,
            level=level,
            ad_account_id=account_id,
            access_token=access_token,
        )
    except Exception as e:
        err = str(e)[:300]
        logger.warning("FB Marketing API call failed: %s", err)
        return {"ok": False, "reason": "api_error", "detail": err}

    if not insights:
        return {
            "ok": False,
            "reason": "no_insights",
            "detail": f"Account {FB_AD_ACCOUNT_ID} không có data trong period={period_raw} (level={level})",
        }

    fb_data = format_insights_for_analysis(insights, period_raw)

    # Đào thêm 1 lớp xuống cấp AD — campaign-level chỉ biết "kênh nào thắng/thua",
    # không biết CREATIVE nào trong kênh đó đang kéo/ghì kết quả ("Content Win").
    # Pull riêng ở level="ad" (giữ nguyên level chính cho Frequency Radar/Budget
    # Reallocation vốn thiết kế theo campaign — tránh vỡ cấu trúc phân tích cũ).
    try:
        ad_insights = insights if level == "ad" else await get_account_insights(
            date_preset=date_preset, level="ad",
            ad_account_id=account_id, access_token=access_token,
        )
        ad_breakdown = format_ad_level_for_analysis(ad_insights, period_raw)
        if ad_breakdown:
            fb_data = f"{fb_data}\n\n{ad_breakdown}"
    except Exception as e:
        logger.warning("Ad-level pull for Content Win skipped: %s", e)

    session.pending_intake["_fb_data"] = fb_data
    logger.info("FB Marketing API: fetched %d rows | preset=%s | level=%s", len(insights), date_preset, level)
    return {"ok": True, "reason": "ok", "detail": f"{len(insights)} rows"}


async def _prefetch_optimizer_data(message: Message, session) -> dict:
    """Pre-fetch campaign hierarchy cho ads_optimizer skill.
    Load toàn bộ Campaign → AdSet tree, inject vào _optimizer_hierarchy.

    Returns dict: {"ok": bool, "reason": str, "detail": str}
      reason ∈ {"ok", "no_token", "no_account", "no_campaigns", "api_error"}
    """
    from tools.fb_marketing import (
        get_campaigns_with_adsets, format_hierarchy_for_optimizer, is_available
    )
    from config import FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID

    if not FB_ACCESS_TOKEN:
        return {"ok": False, "reason": "no_token", "detail": "FB_ACCESS_TOKEN chưa set trên server"}
    if not FB_AD_ACCOUNT_ID:
        return {"ok": False, "reason": "no_account", "detail": "FB_AD_ACCOUNT_ID chưa set trên server"}
    if not is_available():
        return {"ok": False, "reason": "no_token", "detail": "FB Marketing API không khả dụng"}

    await message.reply_text(
        "⚡ Em đang load hierarchy Campaign → Ad Set từ tài khoản Ads...",
        parse_mode=ParseMode.MARKDOWN,
    )

    account_id = FB_AD_ACCOUNT_ID or ""
    try:
        campaigns = await get_campaigns_with_adsets(ad_account_id=account_id)
    except Exception as e:
        err = str(e)[:300]
        logger.warning("Optimizer API call failed: %s", err)
        return {"ok": False, "reason": "api_error", "detail": err}

    if not campaigns:
        return {
            "ok": False,
            "reason": "no_campaigns",
            "detail": f"Account {account_id} không có campaign nào (cần campaign tồn tại để thao tác)",
        }

    hierarchy_text = format_hierarchy_for_optimizer(campaigns, account_id)
    session.pending_intake["_optimizer_hierarchy"] = hierarchy_text
    session.pending_intake["_optimizer_account_id"] = (
        account_id if account_id.startswith("act_") else f"act_{account_id}"
    )
    logger.info("Optimizer pre-fetch: %d campaigns loaded", len(campaigns))
    return {"ok": True, "reason": "ok", "detail": f"{len(campaigns)} campaigns"}


_ACTION_RE = re.compile(
    r'\[ACTION:(PAUSE|ACTIVATE|BUDGET_DAILY|BUDGET_LIFETIME):([^:\]]+):([^:\]]+):([^:\]]+?)(?::(\d+))?\]'
)

_ACTION_LABEL = {
    "PAUSE": "⏸ PAUSE",
    "ACTIVATE": "▶️ ACTIVATE",
    "BUDGET_DAILY": "💰 DAILY BUDGET",
    "BUDGET_LIFETIME": "💰 LIFETIME BUDGET",
}

_LEVEL_ICON = {
    "campaign": "📊",
    "adset": "📦",
    "ad": "🎯",
}


def _parse_optimizer_actions(result: str) -> list[dict]:
    """Extract [ACTION:...] markers from optimizer skill output."""
    actions = []
    for m in _ACTION_RE.finditer(result):
        action_type, obj_id, level, name = m.group(1), m.group(2), m.group(3), m.group(4)
        amount = int(m.group(5)) if m.group(5) else None
        actions.append({
            "type": action_type,
            "id": obj_id.strip(),
            "level": level.strip().lower(),
            "name": name.strip(),
            "amount": amount,
        })
    return actions


async def _show_optimizer_confirm(message: Message, session, result: str):
    """Parse action markers from optimizer output and show confirmation keyboard."""
    actions = _parse_optimizer_actions(result)
    if not actions:
        return  # No actions found — just advisory output, no confirmation needed

    # Store in session for callback to execute
    session.pending_intake["_pending_actions"] = actions
    await save_session(session)

    # Build summary of proposed actions
    lines = ["", "─────────────────────────────", "⚡ **Minh đề xuất thực thi:**", ""]
    for i, a in enumerate(actions, 1):
        icon = _LEVEL_ICON.get(a["level"], "🔷")
        label = _ACTION_LABEL.get(a["type"], a["type"])
        name_str = f"{icon} **{a['name']}** (`{a['id']}`)"
        if a["type"] in ("BUDGET_DAILY", "BUDGET_LIFETIME") and a["amount"]:
            budget_k = f"{a['amount']:,} VND"
            lines.append(f"`{i}.` {label}: {name_str} → {budget_k}")
        else:
            lines.append(f"`{i}.` {label}: {name_str}")
    lines.append("")
    lines.append(f"**Tổng: {len(actions)} actions** — Xác nhận để thực hiện ngay trên FB.")

    confirm_text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            f"✅ Thực hiện {len(actions)} actions",
            callback_data="optimizer_confirm",
        ),
        InlineKeyboardButton("❌ Hủy", callback_data="optimizer_cancel"),
    ]])

    await _safe_reply(message, confirm_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def _execute_optimizer_actions(session) -> str:
    """Execute all pending actions from _pending_actions list. Returns summary text."""
    from tools.fb_marketing import set_object_status, update_budget

    actions = session.pending_intake.pop("_pending_actions", [])
    if not actions:
        return "Không có action nào để thực hiện."

    results = []
    for a in actions:
        atype = a["type"]
        obj_id = a["id"]
        name = a["name"]
        level = a["level"]
        icon = _LEVEL_ICON.get(level, "🔷")

        try:
            if atype == "PAUSE":
                await set_object_status(obj_id, "PAUSED")
                results.append(f"✅ ⏸ PAUSE: {icon} **{name}** (`{obj_id}`)")
            elif atype == "ACTIVATE":
                await set_object_status(obj_id, "ACTIVE")
                results.append(f"✅ ▶️ ACTIVATE: {icon} **{name}** (`{obj_id}`)")
            elif atype in ("BUDGET_DAILY", "BUDGET_LIFETIME"):
                budget_type = "daily_budget" if atype == "BUDGET_DAILY" else "lifetime_budget"
                amount = a.get("amount") or 0
                await update_budget(obj_id, budget_type, amount)
                results.append(f"✅ 💰 BUDGET: {icon} **{name}** (`{obj_id}`) → {amount:,} VND")
            else:
                results.append(f"⚠️ Unknown action type: {atype}")
        except Exception as e:
            results.append(f"❌ FAILED — {icon} **{name}** (`{obj_id}`): {e}")

    await save_session(session)
    return "\n".join(results)


def _calendar_max_week(session) -> int:
    """Số tuần thực tế của calendar — đọc highest 'Tuần N' trong text, fallback 4."""
    calendar = session.get_latest_result("content_calendar") or ""
    weeks = [int(n) for n in re.findall(r"(?:Tuần|Week)\s*(\d+)", calendar, re.IGNORECASE)]
    return max(weeks) if weeks else 4


def _content_remaining_channels(session) -> list[str]:
    """List kênh CHƯA sản xuất content trong lượt này — init từ field `channels`."""
    pi = session.pending_intake
    remaining = pi.get("_content_channels_remaining")
    if remaining is None:
        remaining = _parse_channels_list(
            pi.get("channels") or session.profile.current_channels or ""
        )
        pi["_content_channels_remaining"] = remaining
    return remaining


def _channel_pick_keyboard(channels: list[str], extra_done_button: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"📌 {ch}", callback_data=f"cgch_{i}")]
        for i, ch in enumerate(channels)
    ]
    if extra_done_button:
        buttons.append([InlineKeyboardButton("⏭️ Dừng ở đây", callback_data="cgch_done")])
    return InlineKeyboardMarkup(buttons)


async def _start_content_generation(message, session, weekly: bool) -> None:
    """Layer 3 entry point — KHÔNG chạy hết các kênh 1 lượt.
    Hỏi user muốn sản xuất content cho kênh nào trước (trong các kênh đã chốt
    lúc setup campaign), rồi chạy TỪNG KÊNH 1.

    BACKLOG #10g: trước tiên hỏi LOẠI nội dung (bài đăng/video/UGC/ads/tất cả)
    — không tự cascade hết 4 loại như ContentGeneratorPipeline cũ.
    """
    if not session.pending_intake.get("_content_gen_types"):
        session.pending_intake["_content_gen_mode"] = "weekly" if weekly else "full"
        await save_session(session)
        await message.reply_text(
            "✍️ *Sếp cần sản xuất loại nội dung nào trước?*\n\n"
            "_Em chỉ chạy đúng loại sếp chọn — không tự kèm thêm loại khác._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=CONTENT_TYPE_SCOPE_KEYBOARD,
        )
        return

    remaining = _content_remaining_channels(session)
    session.pending_intake["_content_gen_mode"] = "weekly" if weekly else "full"

    if len(remaining) <= 1:
        # 0 hoặc 1 kênh — không cần hỏi, chạy thẳng
        if remaining:
            session.pending_intake["channel_focus"] = remaining[0]
            session.pending_intake["_content_channels_remaining"] = []
        await save_session(session)
        await _run_content_generation_for_channel(message, session, weekly)
        return

    await save_session(session)
    await message.reply_text(
        "✍️ *Sản xuất nội dung — em làm từng kênh 1 cho chất lượng tốt nhất.*\n\n"
        "Sếp muốn làm kênh nào trước?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_channel_pick_keyboard(remaining),
    )


async def _run_content_generation_for_channel(message, session, weekly: bool) -> None:
    """Chạy content_generator cho channel_focus đã chọn."""
    if weekly:
        await _prompt_week_selection(message, session)
        return

    session.selected_task = "content_generator"
    session.pending_intake.pop("_content_gen_week", None)
    session.pending_intake.pop("_content_gen_weekly_mode", None)
    session.pending_intake.pop("scope", None)
    await save_session(session)
    channel_focus = session.pending_intake.get("channel_focus")
    intro = (
        f"✍️ *Tiếp tục Sản Xuất Nội Dung — kênh {channel_focus}...*"
        if channel_focus
        else "✍️ *Tiếp tục Sản Xuất Nội Dung từ Calendar...*"
    )
    await message.reply_text(intro, parse_mode=ParseMode.MARKDOWN)
    await _send_single_shot_form(message, session, "content_generator")


async def _prompt_week_selection(message, session) -> None:
    """Hiện prompt 'chạy tuần mấy?' cho chế độ content-gen từng tuần.
    Dùng chung cho cả đường vào trực tiếp lẫn đường resume sau Brand Voice."""
    session.pending_intake["_content_gen_weekly_mode"] = "1"
    session.selected_task = "content_generator"
    await save_session(session)
    max_week = _calendar_max_week(session)
    await message.reply_text(
        "⭐ *Chạy từng tuần — chất lượng tốt nhất!*\n\n"
        "Sếp muốn viết nội dung cho *tuần mấy* trước?\n\n"
        f"_Lịch có {max_week} tuần — gõ số tuần (vd: `1`) hoặc `Tuần 1`. "
        "Em sẽ tập trung toàn bộ vào tuần đó._",
        parse_mode=ParseMode.MARKDOWN,
    )
    session.pending_intake["_awaiting_week_selection"] = "content_generator"
    await save_session(session)


async def _handle_week_selection_text(update, context, session, text: str):
    """User gõ tuần muốn chạy content gen (vd: '1', 'Tuần 2')."""
    import re as _re
    raw = (text or "").strip()
    m = _re.search(r"\d+", raw)
    if not m:
        await update.message.reply_text(
            "⚠️ Em chưa hiểu tuần mấy ạ — sếp gõ số thôi nhé, vd: `1` hoặc `Tuần 2`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    max_week = _calendar_max_week(session)
    week_num = int(m.group())
    if week_num < 1 or week_num > max_week:
        await update.message.reply_text(
            f"⚠️ Lịch nội dung này có {max_week} tuần — sếp chọn tuần từ 1 đến {max_week} nhé.",
        )
        return

    session.pending_intake.pop("_awaiting_week_selection", None)
    session.pending_intake["scope"] = f"Tuần {week_num}"
    session.pending_intake["_content_gen_week"] = str(week_num)
    session.selected_task = "content_generator"
    await save_session(session)

    next_hint = (
        f"_Sau khi xong sếp có thể tiếp tục Tuần {week_num + 1} để giữ chất lượng cao._"
        if week_num < max_week
        else "_Đây là tuần cuối của lịch — xong tuần này là đủ bộ nội dung._"
    )
    await update.message.reply_text(
        f"⭐ *Chạy nội dung Tuần {week_num}* — em tập trung toàn bộ vào tuần này!\n\n"
        + next_hint,
        parse_mode=ParseMode.MARKDOWN,
    )
    await _send_single_shot_form(update.message, session, "content_generator")


async def _handle_bp_edit_text(update, context, session, text: str):
    """Backlog 2.2: User sửa Messaging House — re-run brand_positioning với feedback,
    bản mới ghi đè session result (vòng lặp đến khi sếp bấm Chốt)."""
    comment = (text or "").strip()
    if len(comment) < 4:
        await update.message.reply_text("⚠️ Sếp nói rõ hơn chút giúp em: cần sửa phần nào ạ?")
        return

    session.pending_intake.pop("_awaiting_bp_edit", None)
    old_feedback = session.pending_intake.get("_bp_feedback", "")
    session.pending_intake["_bp_feedback"] = (
        (old_feedback + "\n" + comment).strip() if old_feedback else comment
    )
    await save_session(session)

    from config import AGENT_TIMEOUT
    await update.message.reply_text(
        f"🔄 _Đang sửa Messaging House theo feedback: \"{comment[:80]}\"..._",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        result = await asyncio.wait_for(
            run_operational_skill("brand_positioning", session),
            timeout=AGENT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        await update.message.reply_text("⏱ Timeout khi sửa Messaging House. Sếp thử lại nhé.")
        return
    except Exception as e:
        logger.exception("brand_positioning re-edit failed: %s", e)
        await update.message.reply_text("⚠️ Lỗi khi sửa Messaging House. Sếp thử lại nhé.")
        return

    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)
    await _send_ops_result(update.message, session, "brand_positioning", result)
    await update.message.reply_text(
        "🏛️ *Bản sửa xong rồi sếp!* Ổn chưa ạ?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Chốt bản này", callback_data="bp_confirm")],
            [InlineKeyboardButton("✏️ Sửa tiếp",     callback_data="bp_edit_request")],
        ]),
    )


async def _handle_calendar_edit_text(update, context, session, text: str):
    """User muốn sửa calendar — re-run content_calendar với feedback injected."""
    comment = (text or "").strip()
    if len(comment) < 4:
        await update.message.reply_text(
            "⚠️ Sếp nói rõ hơn chút giúp em: cần sửa phần nào ạ?",
        )
        return

    session.pending_intake.pop("_awaiting_calendar_edit", None)
    # Inject feedback vào intake để calendar prompt nhận
    old_feedback = session.pending_intake.get("_calendar_feedback", "")
    session.pending_intake["_calendar_feedback"] = (
        (old_feedback + "\n" + comment).strip() if old_feedback else comment
    )
    session.selected_task = "content_calendar"
    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)

    from config import AGENT_TIMEOUT
    await update.message.reply_text(
        f"🔄 _Đang chỉnh lịch theo feedback: \"{comment[:80]}\"..._",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        result = await asyncio.wait_for(
            run_operational_skill("content_calendar", session),
            timeout=AGENT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        await update.message.reply_text("⏱ Timeout khi gen lịch. Sếp thử lại nhé.")
        return
    except Exception as e:
        logger.exception("calendar re-edit failed: %s", e)
        await update.message.reply_text("⚠️ Lỗi khi sửa lịch. Sếp thử lại nhé.")
        return

    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)
    await _send_ops_result(update.message, session, "content_calendar", result)
    await _start_tone_calibration(update.message, session, result)


async def _handle_strategy_edit_text(update, context, session, text: str):
    """Surgical edit: sửa đúng section/sub-point trong synthesis theo comment user.

    Hybrid: comment rõ → patch luôn (b); comment mơ hồ → hỏi lại (a).
    Re-render HTML chỉ phần strategy đã cập nhật, giữ flag để lặp tới khi user chốt.
    """
    comment = (text or "").strip()
    if len(comment) < 4:
        await update.message.reply_text(
            "⚠️ Sếp nói rõ hơn chút giúp em: cần sửa phần nào, đổi thành hướng nào ạ?",
        )
        return

    synthesis = session.get_latest_result("synthesis")
    if not synthesis:
        # Không còn synthesis (edge) → thoát flow edit
        session.pending_intake.pop("_awaiting_strategy_edit", None)
        await save_session(session)
        await update.message.reply_text(
            "⚠️ Em không tìm thấy bản strategy để sửa. Sếp chạy lại Nghiên Cứu & Phân Tích Thị Trường giúp em nhé.",
        )
        return

    await update.message.reply_text(
        "✏️ *Em đang chỉnh đúng phần sếp nói...*", parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING,
    )

    from agents.surgical_edit import patch_document, summarize_changes, PATCH_ASK, PATCH_NOOP

    try:
        status, payload, detect = await patch_document(synthesis, comment)
    except Exception as e:
        logger.exception("strategy surgical edit failed: %s", e)
        await update.message.reply_text(
            "⚠️ Em gặp lỗi khi chỉnh. Sếp thử mô tả lại yêu cầu giúp em ạ.",
        )
        return

    if status == PATCH_ASK:
        # Comment mơ hồ — hỏi lại, giữ flag
        await update.message.reply_text(
            f"🤔 {payload}",
        )
        return

    if status == PATCH_NOOP:
        await update.message.reply_text(
            "🤔 Em chưa khoanh được đúng phần cần sửa. Sếp chỉ rõ giúp em là *section/đề mục nào* "
            "và đổi thành *hướng nào* cụ thể ạ?",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # PATCH_OK — lưu version mới + re-render HTML strategy
    session.add_result("synthesis", payload)
    await save_session(session)

    from bot.html_report import parse_agent_output, build_single_skill_report
    from agents.skills import OutputFormat

    try:
        parsed = parse_agent_output(payload)
        html_str = build_single_skill_report(
            "synthesis", parsed, OutputFormat.STRATEGIC_4_SECTION,
            business_name=session.profile.business_name or "Business",
            industry=session.profile.industry or "",
            stage=session.profile.stage or "",
        )
        await _send_html_report(update.message, html_str, session)
    except Exception as e:
        logger.warning("re-render strategy HTML failed: %s", e)

    change_summary = summarize_changes(detect)
    await update.message.reply_text(
        f"✅ {change_summary}\n\n"
        f"Sếp xem lại bản cập nhật giúp em. Đã ổn chưa, hay cần chỉnh thêm phần nào nữa ạ?",
        reply_markup=CONFIRM_STRATEGY_KEYBOARD,
    )


async def _handle_brief_edit_text(update, context, session, text: str):
    """Surgical edit campaign_brief theo comment user + log intelligence ngầm."""
    comment = (text or "").strip()
    if len(comment) < 4:
        await update.message.reply_text(
            "⚠️ Sếp nói rõ hơn chút: cần thêm/bớt/sửa phần nào trong brief ạ?",
        )
        return

    brief = session.get_latest_result("campaign_brief")
    if not brief:
        session.pending_intake.pop("_awaiting_brief_edit", None)
        session.pending_intake.pop("_brief_edit_orig_comment", None)
        await save_session(session)
        await update.message.reply_text(
            "⚠️ Em không tìm thấy brief để sửa. Sếp chạy lại Brief Campaign giúp em nhé.",
        )
        return

    # Nếu lượt trước Max đã hỏi lại (PATCH_ASK), gộp câu trả lời này với
    # yêu cầu gốc để patch_document có đủ ngữ cảnh — tránh hỏi lặp vòng.
    prior_comment = session.pending_intake.get("_brief_edit_orig_comment")
    if prior_comment:
        comment = f"{prior_comment}\n\nLàm rõ thêm: {comment}"

    await update.message.reply_text(
        "✏️ *Em đang chỉnh đúng phần sếp nói trong brief...*", parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING,
    )

    from agents.surgical_edit import patch_document, summarize_changes, PATCH_ASK, PATCH_NOOP

    try:
        status, payload, detect = await patch_document(brief, comment)
    except Exception as e:
        logger.exception("brief surgical edit failed: %s", e)
        await update.message.reply_text(
            "⚠️ Em gặp lỗi khi chỉnh brief. Sếp thử mô tả lại yêu cầu giúp em ạ.",
        )
        return

    if status == PATCH_ASK:
        session.pending_intake["_brief_edit_orig_comment"] = comment
        await save_session(session)
        await update.message.reply_text(f"🤔 {payload}")
        return

    if status == PATCH_NOOP:
        session.pending_intake.pop("_brief_edit_orig_comment", None)
        await save_session(session)
        await update.message.reply_text(
            "🤔 Em chưa khoanh được đúng phần cần sửa. Sếp chỉ rõ giúp em *phần nào* và "
            "*thêm/bớt/đổi* thế nào ạ?",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # PATCH_OK — lưu version mới + re-render HTML brief
    session.pending_intake.pop("_brief_edit_orig_comment", None)
    session.add_result("campaign_brief", payload)
    await save_session(session)

    # NGẦM: log intelligence — user yêu cầu sửa brief → học field nào cần
    try:
        from storage.campaign_intelligence import log_campaign_intelligence
        _added = [t.get("sub_point") or t.get("instruction", "")[:60]
                  for t in detect.get("targets", [])]
        asyncio.create_task(log_campaign_intelligence(
            user_id=session.user_id,
            event_type="brief_edited",
            industry=session.profile.industry,
            target_customer=session.profile.target_customer,
            campaign_goal=session.pending_intake.get("campaign_goal") or session.profile.primary_goal,
            stage=session.profile.stage,
            fields_added=[x for x in _added if x],
            edit_comment=comment,
            brief_excerpt=payload[:500],
        ))
    except Exception as e:
        logger.debug("brief_edited intelligence log skipped: %s", e)

    from bot.html_report import build_single_skill_report
    from bot.renderers import parse_by_format
    from agents.skills import OutputFormat

    try:
        # Dùng parse_by_format (giống _send_ops_result) — trả key 'deliverable'
        # đúng với build_single_skill_report(OPERATIONAL_DELIVERABLE). parse_agent_output
        # trả 'detail' → renderer không tìm thấy → mất sạch nội dung brief.
        parsed = parse_by_format(payload, OutputFormat.OPERATIONAL_DELIVERABLE)
        html_str = build_single_skill_report(
            "campaign_brief", parsed, OutputFormat.OPERATIONAL_DELIVERABLE,
            business_name=session.profile.business_name or "Business",
            industry=session.profile.industry or "",
            stage=session.profile.stage or "",
        )
        await _send_html_report(update.message, html_str, session)
    except Exception as e:
        logger.warning("re-render brief HTML failed: %s", e)

    change_summary = summarize_changes(detect)
    await update.message.reply_text(
        f"✅ {change_summary}\n\n"
        f"Sếp xem lại brief giúp em. Đã đủ chưa, hay cần chỉnh thêm gì nữa ạ?",
        reply_markup=CONFIRM_BRIEF_KEYBOARD,
    )


def _duration_to_days(duration: str | None) -> int:
    """Suy số ngày từ field duration tự do ('1 tuần', '6 tuần', '40 ngày', '2 tháng').
    Fallback 30. Dùng cho funnel map duration_days."""
    if not duration:
        return 30
    s = str(duration).lower()
    # Tìm "<số> <đơn vị>" — đơn vị match lỏng bằng substring để né Unicode tổ hợp
    for m in re.finditer(r"(\d+)\s*([^\d\s]+)", s):
        n = int(m.group(1))
        unit = m.group(2)
        if "tu" in unit or "week" in unit:        # tuần / tuan / week
            return max(7, n * 7)
        if unit.startswith("ng") or "day" in unit:  # ngày / ngay / day
            return max(1, n)
        if "th" in unit or "month" in unit:        # tháng / thang / month
            return max(30, n * 30)
    return 30


async def _ask_campaign_setup(update, context, session):
    """KHÔNG hỏi lại kênh + ngân sách nữa (2026-06-12) — 2 ý này sếp đã trả lời ở
    câu 7 chiến lược (channels) + budget gate (_budget_team_context). Organic/ads +
    kênh chủ lực: KHÔNG hỏi, để AI tự suy từ data. Prefill xong viết Brief thẳng."""
    import json as _json
    pi = session.pending_intake

    # Reset answer cũ để campaign mới không kế thừa
    for k in ("media_mix", "hero_channel", "total_budget"):
        pi.pop(k, None)

    # 1) Kênh — lấy từ câu 7 chiến lược đã chốt; fallback profile.current_channels
    channels = ""
    try:
        answers = _json.loads(pi.get("_strategy_answers") or "{}")
        channels = (answers.get("channels") or "").strip()
    except Exception:
        channels = ""
    if not channels:
        channels = (session.profile.current_channels or "").strip()
    if channels:
        pi["channels"] = channels

    # 2) Ngân sách — lấy từ budget gate đã chốt (_budget_team_context); fallback profile.
    #    Chuỗi này gồm cả budget + team → đủ cho brief phân bổ Section 5 (AI tự bóc số).
    budget_ctx = (pi.get("_budget_team_context") or "").strip()
    if not budget_ctx and session.profile.monthly_marketing_budget:
        budget_ctx = str(session.profile.monthly_marketing_budget).strip()
    if budget_ctx:
        pi["total_budget"] = budget_ctx

    await save_session(session)

    # KHÔNG hỏi organic/ads + kênh chủ lực — viết Brief thẳng, AI tự suy từ data
    await _run_campaign_brief_after_setup(update.message, session, context, update)


async def _handle_campaign_setup_text(update, context, session, text):
    """Parse câu trả lời kênh + organic/ads + kênh chủ lực của sếp →
    lưu vào pending_intake → viết Campaign Brief (channel-aware)."""
    session.pending_intake.pop("_awaiting_campaign_setup", None)

    # Parse 3 ý bằng LLM (CRITIC_REVIEW) — robust với free-form tiếng Việt
    channels = ""
    total_budget = ""
    media_mix = ""
    hero_channel = ""
    try:
        from tools.llm_router import call as _router_call, TaskType as _TT
        import json as _json
        _prompt = (
            "Trích xuất từ câu trả lời của founder VN về kênh + ngân sách campaign:\n"
            f"\"{text}\"\n\n"
            "Trả về DUY NHẤT 1 JSON:\n"
            "{"
            '"channels": "<danh sách kênh, cách nhau dấu +; vd \'Facebook + TikTok\'; rỗng nếu không nêu>", '
            '"total_budget": "<tổng ngân sách campaign nếu nêu; vd \'30 triệu\'; rỗng nếu không nêu>", '
            '"media_mix": "<phân bổ organic/ads + ngân sách ads theo từng kênh nếu có; '
            'vd \'Facebook ads 15tr, TikTok organic\'; rỗng nếu không nêu>", '
            '"hero_channel": "<kênh chủ lực + kênh hỗ trợ; vd \'TikTok chủ lực, Facebook+Zalo hỗ trợ\'; rỗng nếu không nêu>"'
            "}\n"
            "Chỉ JSON, không giải thích."
        )
        _res = await _router_call(
            task_type=_TT.CRITIC_REVIEW,
            system="Bạn là parser. Chỉ xuất JSON hợp lệ.",
            user=_prompt,
            max_tokens=350,
        )
        _raw = (_res.get("output") or "").strip()
        _m = re.search(r"\{.*\}", _raw, re.DOTALL)
        if _m:
            _d = _json.loads(_m.group(0))
            channels = (_d.get("channels") or "").strip()
            total_budget = (_d.get("total_budget") or "").strip()
            media_mix = (_d.get("media_mix") or "").strip()
            hero_channel = (_d.get("hero_channel") or "").strip()
    except Exception as e:
        logger.warning("campaign_setup parse failed: %s", e)

    if channels:
        session.pending_intake["channels"] = channels
    elif not session.pending_intake.get("channels"):
        session.pending_intake["channels"] = (
            session.profile.current_channels or "Facebook + TikTok + Zalo OA"
        )
    if total_budget:
        session.pending_intake["total_budget"] = total_budget
    if media_mix:
        session.pending_intake["media_mix"] = media_mix
    if hero_channel:
        session.pending_intake["hero_channel"] = hero_channel
    await save_session(session)

    addr = _addr(session)
    ack = f"📝 Ghi nhận:\n*Kênh* = {session.pending_intake.get('channels')}"
    if total_budget:
        ack += f"\n*Ngân sách* = {total_budget}"
    if media_mix:
        ack += f"\n*Organic/Ads* = {media_mix}"
    if hero_channel:
        ack += f"\n*Chủ lực* = {hero_channel}"
    await update.message.reply_text(
        ack + f"\n\nEm viết Brief theo đúng ý {addr} nhé 👇",
        parse_mode=ParseMode.MARKDOWN,
    )
    await _run_campaign_brief_after_setup(update.message, session, context, update)


async def _run_campaign_brief_after_setup(message, session, context, update):
    """Viết Campaign Brief (đã có channels trong intake) → hiển thị.
    Brief output kèm nút duyệt → brief_confirm → _confirm_brief_and_gen_calendar."""
    campaign_name = session.pending_intake.get("campaign_name", "Campaign")
    session.selected_task = "campaign_brief"
    await save_session(session)

    await message.reply_text(
        f"📋 Em viết Brief Campaign cho \"{campaign_name}\" "
        f"(kênh: {session.pending_intake.get('channels', '?')})...\n"
        f"_Khoảng 60-90 giây ạ._",
        parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING,
    )

    try:
        from config import AGENT_TIMEOUT
        result = await asyncio.wait_for(
            run_operational_skill("campaign_brief", session),
            timeout=AGENT_TIMEOUT,
        )
        await save_session(session)
        await _send_ops_result(message, session, "campaign_brief", result)
    except asyncio.TimeoutError:
        await message.reply_text("⚠️ Brief Campaign timeout. Sếp thử lại nhé.")
    except Exception as e:
        logger.exception("Campaign brief auto-run failed: %s", e)
        await message.reply_text(f"⚠️ Lỗi khi chạy Brief: {str(e)[:200]}")


async def _confirm_brief_and_gen_calendar(message, session, context, update):
    """User duyệt brief → lưu campaign DB + log intelligence ngầm →
    gen Funnel Map + Execution Plan (tóm tắt Telegram + file HTML) →
    DỪNG chờ user duyệt (nút). Duyệt mới dựng Content Calendar
    (trong _gen_content_calendar_after_approval).
    """
    session.pending_intake.pop("_awaiting_brief_edit", None)
    session.pending_intake.pop("_brief_edit_orig_comment", None)
    session.pending_intake.pop("_awaiting_rating_for", None)

    brief = session.get_latest_result("campaign_brief") or ""
    campaign_name = (session.pending_intake.get("campaign_name")
                     or session.pending_intake.get("current_campaign") or "Campaign")
    campaign_goal = session.pending_intake.get("campaign_goal") or session.profile.primary_goal

    # NGẦM: lưu campaign vào DB (fire-and-forget)
    try:
        from storage.v2.campaigns_v2 import create_campaign
        asyncio.create_task(create_campaign(
            user_id=session.user_id,
            name=campaign_name,
            industry=session.profile.industry,
            primary_goal=campaign_goal,
            offer_lever=session.pending_intake.get("key_offer"),
            start_date=session.pending_intake.get("start_date"),
            end_date=session.pending_intake.get("end_date"),
            summary=brief[:2000],
        ))
    except Exception as e:
        logger.debug("create_campaign skipped: %s", e)

    # NGẦM: log intelligence — brief được duyệt nguyên trạng
    try:
        from storage.campaign_intelligence import log_campaign_intelligence
        asyncio.create_task(log_campaign_intelligence(
            user_id=session.user_id,
            event_type="brief_approved",
            industry=session.profile.industry,
            target_customer=session.profile.target_customer,
            campaign_goal=campaign_goal,
            stage=session.profile.stage,
            brief_excerpt=brief[:500],
        ))
    except Exception as e:
        logger.debug("brief_approved intelligence log skipped: %s", e)

    # Auto-gen Content Calendar từ brief — channels/source_mix sếp đã chốt ở
    # bước _ask_campaign_setup (text). Chỉ fallback nếu vì lý do gì đó trống.
    profile = session.profile
    session.pending_intake["channels"] = (
        session.pending_intake.get("channels")
        or profile.current_channels or "Facebook + TikTok + Zalo OA"
    )
    # Thời lượng: GIỮ ĐÚNG giá trị từ brief (field "Thời gian chạy") — KHÔNG ép
    # "30 ngày". Calendar prompt nay đã duration-aware (1 tuần → 1 tuần).
    if not session.pending_intake.get("duration"):
        session.pending_intake["duration"] = "4 tuần"
    if profile.team_size:
        session.pending_intake.setdefault("team_size", str(profile.team_size))
    session.pending_intake["current_campaign"] = campaign_name
    session.selected_task = "content_calendar"
    await save_session(session)

    await message.reply_text(
        f"✅ Brief đã duyệt! Em lưu lại campaign *{campaign_name}* rồi.",
        parse_mode=ParseMode.MARKDOWN,
    )

    # ── Funnel Map + Execution Plan → tóm tắt Telegram + file HTML ─────
    funnel_ok = await _gen_and_show_funnel_map(
        message, session, context, update, campaign_name, campaign_goal,
    )

    # ── DỪNG chờ user duyệt — KHÔNG auto dựng calendar ────────────────
    session.pending_intake["_awaiting_funnel_approve"] = "1"
    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)

    prompt = (
        "👆 *Sếp xem kế hoạch triển khai (tóm tắt trên + file HTML + file Excel đầy đủ).*\n\n"
        if funnel_ok else
        "_(Em chưa dựng được funnel map chi tiết, nhưng vẫn có thể đi tiếp.)_\n\n"
    )
    await _emit_funnel_approve_prompt(message, session, prompt)


async def _gen_and_show_funnel_map(
    message, session, context, update, campaign_name, campaign_goal,
) -> bool:
    """Gen Funnel Map + Execution Plan → tóm tắt Telegram + HTML + Excel.
    Trả funnel_ok (True nếu có map — thật hoặc fallback). Tách riêng để
    flow chính VÀ nút debug (re-run funnel_map) cùng dùng, không cần tạo
    lại session từ đầu.
    """
    funnel_ok = False
    _funnel_map = None
    try:
        from agents.funnel_mapper import (
            generate_funnel_map, render_funnel_map_summary, build_funnel_map_markdown,
            _fallback_funnel_map,
        )
        from agents.campaign_execution import (
            generate_execution_plan, classify_goal_type, funnel_map_objective,
        )
        import json as _json_fm

        _goal_slug = classify_goal_type(campaign_goal or "")
        _channels_str = session.pending_intake.get("channels", "Facebook + TikTok")
        # Tách chuỗi kênh thành list (cho fallback dùng đúng từng kênh)
        _channels_list = [c.strip() for c in re.split(r"[+,/]| và ", _channels_str) if c.strip()]
        _campaign_dict = {
            "name":             campaign_name,
            "objective":        funnel_map_objective(_goal_slug),
            "objective_detail": campaign_goal or "",
            "channels":         _channels_str,
            "channels_list":    _channels_list,
            "audience":         session.profile.target_customer or "",
            "duration_days":    _duration_to_days(session.pending_intake.get("duration")),
            "extra_notes":      session.pending_intake.get("key_offer", ""),
        }

        await message.reply_text(
            "🗺 *Em đang map ToFu/MoFu/BoFu cho từng kênh...*\n_Khoảng 15-25 giây ạ._",
            parse_mode=ParseMode.MARKDOWN,
        )
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING,
        )

        # Funnel map: nếu timeout/lỗi → DÙNG FALLBACK (không bỏ cuộc).
        try:
            _funnel_map = await asyncio.wait_for(
                generate_funnel_map(session, _campaign_dict), timeout=180,
            )
        except (asyncio.TimeoutError, Exception) as _fme:
            logger.warning("funnel_map gen failed/timeout → fallback: %s", _fme)
            _funnel_map = _fallback_funnel_map(
                channels=_channels_list or ["Facebook", "TikTok"],
                objective=_campaign_dict["objective"],
            )

        session.pending_intake["_funnel_map_json"] = _json_fm.dumps(_funnel_map, ensure_ascii=False)
        session.add_result("funnel_map", _json_fm.dumps(_funnel_map, ensure_ascii=False))
        await save_session(session)
        funnel_ok = True  # đã có map (thật hoặc fallback) → coi như OK

        # Execution plan: optional — lỗi thì bỏ qua, vẫn show funnel.
        _exec_plan = ""
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.TYPING,
            )
            _exec_plan = await asyncio.wait_for(
                generate_execution_plan(session, _funnel_map, campaign_name, campaign_goal or ""),
                timeout=45,
            )
        except (asyncio.TimeoutError, Exception) as _epe:
            logger.warning("execution_plan failed/timeout → skip: %s", _epe)

        # 1) Telegram: TÓM TẮT funnel + execution roadmap
        await message.reply_text(render_funnel_map_summary(_funnel_map), parse_mode=ParseMode.MARKDOWN)
        if _exec_plan:
            await message.reply_text(_exec_plan, parse_mode=ParseMode.MARKDOWN)

        # 2) HTML: chi tiết đầy đủ funnel (+ execution plan nếu có)
        try:
            from bot.html_report import build_single_skill_report
            from agents.skills import OutputFormat
            plan_md = (
                "## 🗺 Funnel Map — Chiến lược từng kênh\n\n"
                + build_funnel_map_markdown(_funnel_map)
            )
            if _exec_plan:
                plan_md += "\n\n---\n\n## 🚀 Kế hoạch thực thi\n\n" + _exec_plan
            html_str = build_single_skill_report(
                "campaign_plan",
                {"summary": f"Kế hoạch triển khai campaign *{campaign_name}* — funnel ToFu/MoFu/BoFu theo kênh + roadmap thực thi.",
                 "deliverable": plan_md},
                OutputFormat.OPERATIONAL_DELIVERABLE,
                business_name=session.profile.business_name or "",
                industry=session.profile.industry or "",
                stage=session.profile.stage or "",
            )
            await _send_html_report(message, html_str, session)
        except Exception as _he:
            logger.warning("campaign_plan HTML build skipped: %s", _he)

        # 3) Excel: funnel map chi tiết → file .xlsx
        try:
            await _send_excel_funnel_map(message, _funnel_map, campaign_name, session)
        except Exception as _xe:
            logger.warning("funnel_map Excel export skipped: %s", _xe)

    except Exception as _fe:
        logger.warning("funnel_map/execution_plan block skipped: %s", _fe)

    return funnel_ok


async def _rescue_nonconvert_action(update, context, session):
    """BACKLOG #9 — 'Vớt khách chưa convert' cho campaign vừa chốt: chạy thẳng
    email_zalo_sequence với intake prefill từ campaign (key_offer, segment
    BOFU chưa convert lấy từ Funnel Map, channels của campaign) — 1 chuỗi
    nurture tập trung vào nhóm "warm nhưng chưa chốt" của riêng campaign này."""
    import json as _json

    try:
        campaign = _json.loads(session.pending_intake.get("_chosen_campaign", "{}"))
    except _json.JSONDecodeError:
        campaign = {}

    campaign_name = (
        campaign.get("name")
        or session.pending_intake.get("campaign_name")
        or session.pending_intake.get("current_campaign")
        or "Campaign"
    )
    key_offer = (campaign.get("key_offer") or session.pending_intake.get("key_offer") or "").strip()
    channels  = (campaign.get("channels") or session.pending_intake.get("channels") or "").strip()

    # Lấy mô tả stage BOFU (Convert) từ Funnel Map đã gen — đúng nhóm "đã vào
    # BOFU nhưng chưa mua" để chuỗi nurture bám sát.
    bofu_desc = ""
    try:
        funnel_map = _json.loads(session.pending_intake.get("_funnel_map_json") or "[]")
        if funnel_map:
            bofu = funnel_map[0].get("bofu") or {}
            stage_label = (funnel_map[0].get("stage_labels") or {}).get("bofu", "Convert")
            if bofu.get("goal"):
                bofu_desc = f"Đã ở giai đoạn {stage_label} (BOFU) — {bofu['goal']}, nhưng chưa {bofu.get('cta', 'chốt')}"
    except Exception:
        pass

    audience_segment = (
        bofu_desc
        or f"Khách đã quan tâm/inbox campaign \"{campaign_name}\" nhưng chưa chuyển đổi"
    )
    sequence_goal = f"Vớt khách chưa convert từ campaign \"{campaign_name}\""
    if key_offer:
        sequence_goal += f" — nurture quay lại với offer: {key_offer}"

    session.pending_intake["audience_segment"]  = audience_segment
    session.pending_intake["sequence_goal"]     = sequence_goal
    session.pending_intake["channel_preference"] = channels or "Zalo OA + Email"
    session.pending_intake[OPS_INTAKE_AWAITING] = "email_zalo_sequence"
    session.selected_task = "email_zalo_sequence"
    session.stage = PipelineStage.INTAKE
    await save_session(session)

    await update.message.reply_text(
        f"🎯 *Em dựng chuỗi nurture \"vớt khách chưa convert\" cho campaign \"{campaign_name}\"...*",
        parse_mode=ParseMode.MARKDOWN,
    )
    await _handle_ops_intake_reply(update, context, session, "ok")


async def _emit_funnel_approve_prompt(message, session, prompt: str):
    """Gửi prompt + nút duyệt funnel → calendar. Tách riêng để dùng lại."""
    addr = _addr(session)
    await message.reply_text(
        prompt + f"Duyệt để em dựng *Lịch Nội Dung* theo kế hoạch này cho {addr} nhé?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=FUNNEL_APPROVE_KEYBOARD,
    )


def _parse_channels_list(channels_str: str) -> list[str]:
    """Tách field `channels` (vd 'Facebook + TikTok + Zalo OA') thành list tên kênh."""
    if not channels_str:
        return []
    parts = re.split(r"\s*[+,/]\s*|\s+và\s+", channels_str.strip())
    return [p.strip() for p in parts if p.strip()]


async def _gen_content_calendar_after_approval(message, session, context, update):
    """User đã duyệt funnel/execution plan → hỏi cadence/kênh trước khi dựng Content Calendar."""
    session.pending_intake.pop("_awaiting_funnel_approve", None)
    await _prompt_calendar_cadence(message, session)


async def _prompt_calendar_cadence(message, session):
    """Hỏi user muốn bao nhiêu bài/tuần cho mỗi kênh — mỗi kênh là 1 tuyến nội dung
    riêng, bổ trợ lẫn nhau (không phân biệt kênh chính/phụ)."""
    channels = _parse_channels_list(
        session.pending_intake.get("channels") or session.profile.current_channels or ""
    )
    if not channels:
        channels = ["Facebook", "TikTok"]

    lines = [
        "📅 *Trước khi dựng Lịch Nội Dung — mỗi kênh sếp muốn bao nhiêu bài/tuần?*",
        "",
        "_Mỗi kênh sẽ có tuyến nội dung riêng theo campaign brief, bổ trợ lẫn nhau "
        "(không phân biệt kênh chính/phụ)._",
        "",
        "Gõ mỗi kênh 1 dòng, theo format:",
    ]
    for ch in channels:
        lines.append(f"`{ch}: <số bài/tuần>`")
    lines.append("")
    example = " · ".join(f"{ch}: 3" for ch in channels)

    # TikTok có trong kênh → hỏi gộp thêm "tuyến content" + "thuê UGC ngoài?"
    # trong CÙNG bước này (không tách thêm round-trip) — BACKLOG #10(b).
    has_tiktok = any("tiktok" in ch.lower() for ch in channels)
    if has_tiktok:
        from agents.social_industry_profiles import get_tiktok_content_lines
        suggested_lines = get_tiktok_content_lines(session.profile.industry or "")
        lines.append(
            "_Vd: " + example + " · Tuyến: Behind-the-scenes + Review khách · UGC: Có, 2 video/tháng_"
        )
        lines.append("")
        lines.append("📱 *Riêng TikTok — trả lời thêm 2 ý dưới đây (trong cùng tin nhắn):*")
        lines.append("")
        lines.append(f"1️⃣ *Tuyến content TikTok* muốn tập trung? Gợi ý theo ngành:\n_{suggested_lines}_")
        lines.append("2️⃣ *Có thuê UGC ngoài không?* (Có/Không + số lượng nếu có)")
        lines.append("")
        lines.append("Gõ theo format: `Tuyến: <tuyến muốn chọn>` và `UGC: <Có/Không, số lượng>`")
    else:
        lines.append("_Vd: " + example + "_")

    session.pending_intake["_awaiting_calendar_cadence"] = "1"
    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)

    await message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def _handle_calendar_cadence_text(update, context, session, text: str):
    """User trả lời 'Kênh: X bài/tuần' từng dòng → lưu cadence → dựng Content Calendar."""
    session.pending_intake.pop("_awaiting_calendar_cadence", None)

    raw = (text or "").strip()
    cadence_lines = []
    # Tìm MỌI cặp "Kênh: N" trong toàn bộ text — user có thể gõ mỗi kênh 1 dòng
    # HOẶC tất cả trên 1 dòng nối bằng " · "/"," (giống ví dụ bot đưa ra).
    for m in re.finditer(r"([^\s:：·,]+(?:\s+[^\s:：·,]+)*)\s*[:：]\s*(\d+)", raw):
        ch_name = m.group(1).strip().strip("`-•").strip()
        if ch_name:
            cadence_lines.append(f"{ch_name}: {m.group(2).strip()} bài/tuần")

    # Không match được format → lưu nguyên text, để LLM tự suy
    session.pending_intake["channel_cadence"] = "; ".join(cadence_lines) if cadence_lines else raw

    # TikTok: trích "Tuyến: ..." và "UGC: ..." nếu có (BACKLOG #10b) — gộp
    # cùng bước cadence, không tách round-trip riêng.
    m_tuyen = re.search(r"Tuyến[^:：]*[:：]\s*(.+?)(?:\n|·\s*UGC|UGC[^:：]*[:：]|$)", raw, re.IGNORECASE)
    if m_tuyen:
        tuyen_val = m_tuyen.group(1).strip(" ·-")
        if tuyen_val:
            session.pending_intake["tiktok_content_lines"] = tuyen_val
    m_ugc = re.search(r"UGC[^:：]*[:：]\s*(.+?)(?:\n|$)", raw, re.IGNORECASE)
    if m_ugc:
        ugc_val = m_ugc.group(1).strip(" ·-")
        if ugc_val:
            session.pending_intake["ugc_outsource"] = ugc_val

    await save_session(session)

    await _run_content_calendar(update.message, session, context, update)


async def _run_content_calendar(message, session, context, update):
    """Dựng Content Calendar theo channel_cadence đã chốt."""
    addr = _addr(session)
    await message.reply_text(
        f"📅 *Em dựng Lịch Nội Dung theo kế hoạch cho {addr}...*\n"
        f"_Kênh: {session.pending_intake.get('channels', 'Facebook + TikTok')} · Khoảng 30-60 giây ạ._",
        parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING,
    )

    session.selected_task = "content_calendar"
    await save_session(session)

    from config import AGENT_TIMEOUT
    try:
        result = await asyncio.wait_for(
            run_operational_skill("content_calendar", session),
            timeout=AGENT_TIMEOUT,
        )
    except Exception as e:
        logger.exception("content_calendar after funnel approval failed: %s", e)
        await message.reply_text(
            "⚠️ Em gặp lỗi khi dựng lịch. Sếp thử lại từ menu Lịch Nội Dung nhé.",
        )
        return

    session.stage = PipelineStage.TASK_SELECT
    await save_session(session)

    await _send_ops_result(message, session, "content_calendar", result)
    # Dừng cho user duyệt calendar trước (tone calibration → nút sản xuất content)
    await _start_tone_calibration(message, session, result)


async def _send_html_report(message: Message, html_str: str, session, caption: str = None):
    """Send HTML report as document attachment."""
    import io
    bizname = (session.profile.business_name or "").strip()
    if bizname:
        business_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", bizname)[:30].strip("_")
        filename = f"marketing_report_{business_slug}.html"
    else:
        filename = "marketing_report.html"

    buf = io.BytesIO(html_str.encode("utf-8"))
    buf.name = filename

    await message.reply_document(
        document=buf,
        filename=filename,
        caption=caption or "📄 *Báo cáo đầy đủ* — mở để xem full analysis với layout đẹp.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _send_excel_funnel_map(message: Message, funnel_map: list, campaign_name: str, session):
    """Export funnel map → .xlsx và gửi qua Telegram."""
    import io as _io
    from agents.funnel_mapper import build_funnel_map_excel

    xlsx_bytes = build_funnel_map_excel(funnel_map, campaign_name)
    business_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", (session.profile.business_name or "campaign"))[:30]
    filename = f"funnel_map_{business_slug}.xlsx"

    buf = _io.BytesIO(xlsx_bytes)
    buf.name = filename

    await message.reply_document(
        document=buf,
        filename=filename,
        caption=(
            "📊 *Funnel Map — Excel*\n"
            "Format · Content Angles · CTA · Volume từng tầng từng kênh.\n"
            "_Mở bằng Excel / Google Sheets để chỉnh sửa trực tiếp._"
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── Campaign Ideation Helpers ────────────────────────────────────

async def _handle_campaign_needs_text(update, context, session, text: str):
    """Parse câu trả lời nhu cầu (mục tiêu/dịp/ngân sách) → lưu vào pending_intake
    → chạy propose_campaigns với context đầy đủ."""
    session.pending_intake.pop("_awaiting_campaign_needs", None)

    # Lưu vào pending_intake để propose_campaigns dùng làm context
    session.pending_intake["_campaign_needs_raw"] = text.strip()

    # Parse nhanh bằng LLM để lưu structured
    try:
        from tools.llm_router import call as _rc, TaskType as _TT
        import json as _json
        _res = await _rc(
            task_type=_TT.CRITIC_REVIEW,
            system="Bạn là parser. Chỉ xuất JSON hợp lệ.",
            user=(
                "Trích xuất từ câu trả lời của founder VN về nhu cầu campaign:\n"
                f"\"{text}\"\n\n"
                "Trả về JSON:\n"
                '{"campaign_objective": "<thu khách mới | bán thêm cho khách cũ | ra sản phẩm mới | kéo khách cũ quay lại | khác>", '
                '"upcoming_occasion": "<dịp/mùa vụ hoặc rỗng>", '
                '"budget_range": "<nhỏ | vừa | lớn | cụ thể hoặc rỗng>"}'
            ),
            max_tokens=200,
        )
        _raw = (_res.get("output") or "").strip()
        _m = re.search(r"\{.*\}", _raw, re.DOTALL)
        if _m:
            _d = _json.loads(_m.group(0))
            if _d.get("campaign_objective"):
                session.pending_intake["campaign_objective"] = _d["campaign_objective"]
            if _d.get("upcoming_occasion"):
                session.pending_intake["upcoming_occasion"] = _d["upcoming_occasion"]
            if _d.get("budget_range"):
                session.pending_intake["budget_range"] = _d["budget_range"]
    except Exception as e:
        logger.warning("campaign_needs parse failed: %s", e)

    await save_session(session)

    await update.message.reply_text(
        "🔍 *Em đang đề xuất campaign phù hợp...*\n_Khoảng 20-40 giây ạ._",
        parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING,
    )

    try:
        from agents.campaign_ideation import propose_campaigns, format_options_card
        options = await propose_campaigns(session)
        if not options:
            await update.message.reply_text(
                "⚠️ Em đề xuất bị lỗi. Sếp thử lại hoặc gõ idea trực tiếp nhé.",
                reply_markup=POST_AZ_CAMPAIGN_KEYBOARD,
            )
            return
        import json as _json
        session.pending_intake["_proposed_campaigns"] = _json.dumps(options, ensure_ascii=False)
        await save_session(session)
        card = format_options_card(options)
        await send_long_message(
            update.message, card,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=CAMPAIGN_OPTION_KEYBOARD,
        )
    except Exception as e:
        logger.exception("Campaign propose after needs failed: %s", e)
        await update.message.reply_text(
            f"⚠️ Lỗi khi đề xuất: {str(e)[:200]}",
            reply_markup=POST_AZ_CAMPAIGN_KEYBOARD,
        )


async def _handle_campaign_idea_text(update, context, session, text: str):
    """Refine user's campaign idea với customer_insight + market_research, rồi show confirm card."""
    text = (text or "").strip()
    if len(text) < 5:
        await update.message.reply_text(
            "⚠️ Idea hơi ngắn. Sếp mô tả thêm 1-2 câu để em refine chính xác ạ.",
        )
        return

    # Clear flag
    session.pending_intake.pop("_awaiting_campaign_idea", None)
    await save_session(session)

    await update.message.reply_text(
        "✨ *Em đang đối chiếu idea với Customer Insight + Market Research...*\n"
        "_Khoảng 20-40 giây ạ._",
        parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING,
    )

    try:
        from agents.campaign_ideation import refine_user_idea, format_refined_card
        refined_data = await refine_user_idea(session, text)
        if not refined_data:
            await update.message.reply_text(
                "⚠️ Em refine bị lỗi. Sếp thử lại nhé.",
                reply_markup=POST_AZ_CAMPAIGN_KEYBOARD,
            )
            return

        # Save refined data để confirm_callback dùng lại
        import json as _json
        session.pending_intake["_refined_campaign"] = _json.dumps(refined_data, ensure_ascii=False)
        await save_session(session)

        card = format_refined_card(refined_data)
        await send_long_message(
            update.message, card,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=CAMPAIGN_IDEA_CONFIRM_KEYBOARD,
        )
    except Exception as e:
        logger.exception("Campaign refine failed: %s", e)
        await update.message.reply_text(
            f"⚠️ Lỗi khi refine: {str(e)[:200]}",
            reply_markup=POST_AZ_CAMPAIGN_KEYBOARD,
        )


async def _ask_offer_preferences(message: Message, session, campaign: dict):
    """Sau khi chốt campaign → đề xuất 3 GÓI ƯU ĐÃI để sếp chọn nhanh (BACKLOG #6),
    thay flow 3-câu-hỏi cũ. "✏️ Tự định nghĩa" → fallback flow 3 câu cũ
    (`_ask_offer_preferences_custom` → `_handle_offer_prefs_text`)."""
    import json as _json
    from agents.campaign_ideation import propose_offer_packages, format_packages_card
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    session.pending_intake["_chosen_campaign"] = _json.dumps(campaign, ensure_ascii=False)
    await save_session(session)

    await message.reply_text(
        f"✅ *Đã chốt campaign \"{campaign.get('name', '?')}\"!*\n\n"
        f"Em đang đề xuất các gói ưu đãi phù hợp...",
        parse_mode=ParseMode.MARKDOWN,
    )

    packages = await propose_offer_packages(session, campaign)
    if not packages:
        await _ask_offer_preferences_custom(message, session, campaign)
        return

    session.pending_intake["_offer_packages"] = _json.dumps(packages, ensure_ascii=False)
    await save_session(session)

    card = format_packages_card(campaign, packages)
    num_emojis = ["1️⃣", "2️⃣", "3️⃣"]
    rows = [
        [InlineKeyboardButton(num_emojis[i] if i < 3 else f"{i+1}.", callback_data=f"offer_package_pick_{i}")]
        for i in range(len(packages))
    ]
    rows.append([InlineKeyboardButton("✏️ Tự định nghĩa", callback_data="offer_package_custom")])
    await send_long_message(
        message, card, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def _ask_offer_preferences_custom(message: Message, session, campaign: dict):
    """Fallback flow cũ: HỎI triết lý + giới hạn offer (3 câu) khi sếp bấm
    "✏️ Tự định nghĩa" hoặc khi propose_offer_packages lỗi."""
    import json as _json
    from agents.campaign_ideation import generate_bait_hint
    session.pending_intake["_chosen_campaign"] = _json.dumps(campaign, ensure_ascii=False)
    session.pending_intake["_awaiting_offer_prefs"] = "1"
    await save_session(session)
    bait_hint = await generate_bait_hint(session)
    await message.reply_text(
        f"✏️ *OK, sếp tự định nghĩa ưu đãi.*\n\n"
        f"Em chỉ đề xuất trong khuôn khổ sếp đặt ra. Cho em hỏi 3 ý ạ:\n\n"
        f"1️⃣ *Sếp muốn \"mồi\" khách bằng cách nào?*\n"
        f"_({bait_hint} — chọn 1-2 hướng)_\n\n"
        f"2️⃣ *Sếp sẵn sàng \"cho đi\" tới đâu mà vẫn lời?*\n"
        f"_(Vd: \"giảm tối đa 20%\", \"tặng được món < 15k\", \"miễn phí 1 buổi trải nghiệm\")_\n\n"
        f"3️⃣ *Có gì BẮT BUỘC phải giữ không?*\n"
        f"_(Vd: \"giá gốc vẫn hiển thị trên menu\", \"không phá giá thị trường\", \"không tặng tiền mặt\" — hoặc \"không có ràng buộc\")_\n\n"
        f"Sếp trả lời cả 3 trong 1 tin, hoặc gõ \"để em tự đề xuất\" nếu muốn em chủ động 🙏",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _handle_offer_prefs_text(update, context, session, text: str):
    """Parse triết lý + giới hạn offer của sếp → lưu → đề xuất 4 cách ưu đãi trong khuôn khổ đó."""
    session.pending_intake.pop("_awaiting_offer_prefs", None)
    session.pending_intake["_offer_prefs_raw"] = (text or "").strip()
    await save_session(session)

    import json as _json
    raw_campaign = session.pending_intake.get("_chosen_campaign", "{}")
    try:
        campaign = _json.loads(raw_campaign)
    except _json.JSONDecodeError:
        campaign = {}
    if not campaign:
        await update.message.reply_text("⚠️ Campaign đã hết hạn. Sếp /start lại nhé.")
        return

    await _show_offer_lever_selection(update.message, session, campaign)


async def _show_offer_lever_selection(message: Message, session, campaign: dict):
    """Sau khi chốt campaign + biết triết lý/giới hạn, AI propose 4 cách ưu đãi
    SPECIFIC trong khuôn khổ sếp đặt. Save campaign + levers vào pending_intake.
    """
    from agents.campaign_ideation import propose_offer_levers, format_levers_card
    import json as _json

    # Cleanup ideation state, prepare for lever selection
    for k in ("_awaiting_campaign_idea", "_proposed_campaigns", "_refined_campaign",
              "_awaiting_campaign_finalize", "_finalize_campaign", "_chosen_lever"):
        session.pending_intake.pop(k, None)
    session.pending_intake.pop(OPS_INTAKE_AWAITING, None)

    session.pending_intake["_chosen_campaign"] = _json.dumps(campaign, ensure_ascii=False)
    await save_session(session)

    await message.reply_text(
        "🎯 *Em đang đề xuất cách ưu đãi phù hợp với campaign vừa chốt...*\n"
        "_Khoảng 15-25 giây ạ._",
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        levers = await propose_offer_levers(session, campaign)
        if not levers:
            await message.reply_text(
                "⚠️ Em đề xuất lever bị lỗi. Sếp thử lại hoặc /start lại nhé.",
                reply_markup=POST_AZ_CAMPAIGN_KEYBOARD,
            )
            return

        # Save levers vào pending_intake
        session.pending_intake["_offer_levers"] = _json.dumps(levers, ensure_ascii=False)
        await save_session(session)

        # Build keyboard động — chỉ show số nút tương ứng số levers
        if len(levers) == 4:
            kb = OFFER_LEVER_KEYBOARD
        else:
            # Fallback: build keyboard với đúng số levers thực tế
            from telegram import InlineKeyboardButton as _Btn, InlineKeyboardMarkup as _Mkup
            emoji_num = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
            row = [
                _Btn(emoji_num[i], callback_data=f"lever_pick_{i}")
                for i in range(len(levers))
            ]
            kb = _Mkup([
                row,
                [_Btn("🔄 Đề xuất 4 levers khác", callback_data="lever_propose_again")],
                [_Btn("⏭️ Hủy, quay lại đánh giá", callback_data="az_skip_campaign")],
            ])

        card = format_levers_card(campaign, levers)
        await send_long_message(
            message, card,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
    except Exception as e:
        logger.exception("Show offer levers failed: %s", e)
        await message.reply_text(
            f"⚠️ Lỗi khi đề xuất lever: {str(e)[:200]}",
            reply_markup=POST_AZ_CAMPAIGN_KEYBOARD,
        )


async def _show_dynamic_finalize_form(message: Message, session, campaign: dict, lever: dict):
    """Show form động: lever params + Thời lượng campaign (cho Content Calendar)."""
    from agents.campaign_ideation import format_dynamic_finalize_form
    import json as _json

    session.pending_intake["_chosen_lever"] = _json.dumps(lever, ensure_ascii=False)
    session.pending_intake["_awaiting_campaign_finalize"] = "1"
    session.pending_intake.pop("_finalize_partial", None)  # fresh form → reset tích lũy
    session.stage = PipelineStage.INTAKE
    await save_session(session)

    form_text = format_dynamic_finalize_form(campaign, lever)
    await send_long_message(message, form_text, parse_mode=ParseMode.MARKDOWN)


async def _haiku_extract_finalize(text: str, fields: list, session) -> dict:
    """Fallback khi user trả lời finalize form free-form / positional (không kèm nhãn).
    Dùng router CRITIC_REVIEW (Haiku → GPT-5-mini → GPT-5) extract → dict keyed by label."""
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
    import json as _json

    fields_desc = "\n".join(
        f'- "{f["label"]}"'
        + ("" if f.get("required", True) else " (không bắt buộc)")
        + f' — vd: {f.get("example", "")}'
        for f in fields
    )
    system = (
        "Bạn trích thông tin từ tin nhắn user thành JSON.\n\n"
        "Các field cần điền (key = label CHÍNH XÁC như dưới, kèm ví dụ giá trị mong đợi):\n"
        f"{fields_desc}\n\n"
        "🔑 QUY TẮC MAP — QUAN TRỌNG NHẤT:\n"
        "- Map theo NGHĨA / NỘI DUNG, TUYỆT ĐỐI KHÔNG theo thứ tự/vị trí.\n"
        "- User có thể trả lời LỘN XỘN, thiếu field, hoặc gộp nhiều field trong 1 câu.\n"
        "- So khớp mỗi mẩu thông tin với field có 'ví dụ' GIỐNG NHẤT về kiểu dữ liệu:\n"
        "  · Tên món ăn / sản phẩm (vd 'sốt phô mai', 'bánh taco') → field hỏi TÊN món/quà tặng\n"
        "  · Số tiền VND ('8k', '50.000đ', '8 nghìn') → field hỏi GIÁ TRỊ / mức tiền (KHÔNG phải số lượng)\n"
        "  · Số kèm 'suất/slot/phần' → field SỐ LƯỢNG\n"
        "  · Số có '%' → field mức DISCOUNT\n"
        "  · Điều kiện/cách nhận biết (vd 'khách tự khai', 'nhân viên hỏi') → field ĐIỀU KIỆN\n"
        "  · '4 tuần', '6 tuần', '2 tháng', '30 ngày' → field THỜI LƯỢNG CAMPAIGN\n"
        "- Nếu 1 câu chứa NHIỀU field (vd 'tặng sốt phô mai 8k') → tách ra đúng từng field.\n"
        "- Field nào user KHÔNG nhắc → bỏ qua, TUYỆT ĐỐI không bịa.\n"
        "Output CHỈ JSON object, key = label CHÍNH XÁC, value = string. Không markdown, không giải thích."
    )
    try:
        result = await router_call(
            task_type=TaskType.CRITIC_REVIEW, system=system, user=text, max_tokens=400,
        )
        raw = (result.get("output") or "").strip()
        raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
        data = _json.loads(raw)
        valid_labels = {f["label"] for f in fields}
        return {k: str(v).strip() for k, v in data.items() if k in valid_labels and v}
    except (AllProvidersFailedError, _json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("finalize free-form extract failed: %s", e)
        return {}


async def _handle_campaign_finalize_text(update, context, session, text: str):
    """Parse user reply (dynamic theo lever) → merge với campaign + lever → run campaign_brief."""
    from agents.campaign_ideation import (
        parse_dynamic_finalize_form, merge_to_brief_fields, get_finalize_fields,
    )
    import json as _json

    raw_campaign = session.pending_intake.get("_chosen_campaign", "{}")
    raw_lever = session.pending_intake.get("_chosen_lever", "{}")
    try:
        campaign = _json.loads(raw_campaign)
        lever = _json.loads(raw_lever)
    except _json.JSONDecodeError:
        campaign, lever = {}, {}

    if not campaign or not lever:
        await update.message.reply_text(
            "⚠️ Campaign hoặc lever đã hết hạn. Sếp /start lại nhé.",
        )
        return

    fields = get_finalize_fields(lever)

    # Tích lũy đáp án qua NHIỀU tin nhắn — sếp có thể trả lời từng phần.
    # _finalize_partial giữ các field đã thu được ở các lần trước.
    parsed = {}
    raw_partial = session.pending_intake.get("_finalize_partial", "{}")
    try:
        parsed = {k: v for k, v in _json.loads(raw_partial).items() if v}
    except (_json.JSONDecodeError, AttributeError):
        parsed = {}

    new_parsed, _ = parse_dynamic_finalize_form(text, fields)
    for k, v in new_parsed.items():
        if v:
            parsed[k] = v

    # Field nào còn thiếu sau khi merge → thử LLM extract từ tin hiện tại
    missing = [f["label"] for f in fields
               if f.get("required", True) and not parsed.get(f["label"])]
    if missing:
        extra = await _haiku_extract_finalize(text, fields, session)
        for k, v in extra.items():
            if v and not parsed.get(k):
                parsed[k] = v
        missing = [f["label"] for f in fields
                   if f.get("required", True) and not parsed.get(f["label"])]

    if missing:
        # Lưu phần đã thu để lần sau không hỏi lại → tránh loop vô hạn
        session.pending_intake["_finalize_partial"] = _json.dumps(parsed, ensure_ascii=False)
        await save_session(session)
        got = [f["label"] for f in fields if parsed.get(f["label"])]
        got_line = ("✅ Đã nhận: " + ", ".join(got) + "\n\n") if got else ""
        await update.message.reply_text(
            got_line
            + "⚠️ *Còn thiếu thông tin:*\n"
            + "\n".join(f"• {lbl}" for lbl in missing)
            + "\n\nSếp gửi nốt các mục còn thiếu giúp em ạ (không cần gửi lại phần đã có).",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Cleanup ideation states
    for k in ("_awaiting_campaign_finalize", "_chosen_campaign", "_chosen_lever",
              "_offer_levers", "_offer_prefs_raw", "_campaign_needs_raw",
              "_finalize_partial"):
        session.pending_intake.pop(k, None)

    # Merge campaign + lever + user inputs → 4 fields cho campaign_brief
    brief_fields = merge_to_brief_fields(campaign, lever, parsed)
    for key, val in brief_fields.items():
        session.pending_intake[key] = val or "(chưa rõ)"

    session.pending_intake["campaign_name"] = campaign.get("name", "Campaign")
    session.selected_task = "campaign_brief"
    await save_session(session)

    # Prefill kênh (từ câu 7 chiến lược) + ngân sách (từ budget gate) đã chốt →
    # viết brief thẳng, KHÔNG hỏi lại. Organic/ads + kênh chủ lực để AI tự suy.
    await _ask_campaign_setup(update, context, session)


# ─── Brand Voice Persistence (Sprint 5) ──────────────────────────

def _split_rule_lines(text: str) -> list[str]:
    """Parse multiline rules from user input (numbered list, bullets, plain lines)."""
    if not text:
        return []
    items = []
    for line in text.split("\n"):
        line = line.strip()
        cleaned = re.sub(r"^[\d\.\-\*\+\)\s]+", "", line).strip()
        if cleaned:
            items.append(cleaned)
    return items[:10]  # cap


def _extract_banned_words_from_md(markdown: str) -> list[str]:
    """Best-effort parse banned-words table từ BrandVoiceSkill markdown output."""
    words = []
    # Section "NÊN TRÁNH" followed by markdown table
    m = re.search(r"(?i)NÊN TRÁNH.*?\n((?:\|.*\n){2,})", markdown, re.DOTALL)
    if not m:
        return words
    for line in m.group(1).split("\n"):
        if "|" not in line or "---" in line or "Lý do" in line:
            continue
        cells = [c.strip().strip("`*\"'") for c in line.split("|") if c.strip()]
        if len(cells) >= 2:
            w = cells[1] if cells[0].isdigit() else cells[0]
            if w and w not in ("...", "Từ/cụm tránh"):
                words.append(w)
    return words[:10]


def _extract_tone_from_md(markdown: str) -> list[str]:
    """Heuristic — extract tone descriptors from markdown."""
    m = re.search(r"(?i)tone[^:\n]*:\s*([^\n]+)", markdown)
    if not m:
        return []
    tones = re.split(r"[,;]|\s+và\s+", m.group(1))
    return [t.strip().strip("*_.`") for t in tones if t.strip()][:5]


def _extract_do_rules_from_md(markdown: str) -> list[str]:
    """Parse Section 1 ('10 quy tắc giọng văn') numbered list → do_rules.
    Keeps discrete do_rules synced với rules_markdown sau chat-edit."""
    # Lấy block từ heading chứa "quy tắc giọng văn" → heading kế tiếp
    m = re.search(
        r"(?im)^#{1,4}.*?quy\s*tắc\s*giọng\s*văn.*?\n(.*?)(?=^#{1,4}\s|\Z)",
        markdown, re.DOTALL,
    )
    if not m:
        return []
    rules = []
    for line in m.group(1).split("\n"):
        line = line.strip()
        if not line or line.startswith("|") or "---" in line:
            continue
        # Chỉ lấy dòng list: "1. ...", "- ...", "* ..."
        if not re.match(r"^[\d]+[\.\)]\s|^[-*+]\s", line):
            continue
        cleaned = re.sub(r"^[\d]+[\.\)]\s*|^[-*+]\s*", "", line).strip().strip("*_`")
        if cleaned and len(cleaned) > 3:
            rules.append(cleaned)
    return rules[:10]


def _extract_dont_rules_from_md(markdown: str) -> list[str]:
    """Parse 'NÊN TRÁNH' table → dont_rules dạng 'Tránh "x" — lý do'.
    Giữ discrete dont_rules synced với rules_markdown sau chat-edit."""
    m = re.search(r"(?i)NÊN TRÁNH.*?\n((?:\|.*\n){2,})", markdown, re.DOTALL)
    if not m:
        return []
    out = []
    for line in m.group(1).split("\n"):
        if "|" not in line or "---" in line or "Lý do" in line:
            continue
        cells = [c.strip().strip("`*\"'") for c in line.split("|") if c.strip()]
        if len(cells) >= 2:
            # bỏ cột số thứ tự nếu có
            cells = cells[1:] if cells[0].isdigit() else cells
            word = cells[0] if cells else ""
            reason = cells[1] if len(cells) >= 2 else ""
            if word and word not in ("...", "Từ/cụm tránh"):
                out.append(f'Tránh "{word}"' + (f" — {reason}" if reason and reason != "..." else ""))
    return out[:10]


async def _continue_after_brand_voice(message: Message, session) -> None:
    """Sau khi brand_voice gen + persist xong: chain sang skill gốc (nếu vào BV
    qua lazy trigger), hoặc kết thúc bằng rating prompt (standalone)."""
    pending_skill = session.pending_intake.pop("_bv_pending_skill", None)
    session.pending_intake.pop("_bv_skipped_session", None)
    # Capture TRƯỚC khi nhánh generic wipe sạch pending_intake
    resume_weekly = session.pending_intake.pop("_bv_resume_weekly", None)

    # Standalone — không có skill gốc chờ → kết thúc bằng rating prompt
    if not pending_skill or pending_skill == "brand_voice":
        session.pending_intake["_awaiting_rating_for"] = "brand_voice"
        await save_session(session)
        await message.reply_text(
            "✅ *Brand Voice đã lưu!* Từ giờ mọi nội dung em làm sẽ tuân theo bộ quy tắc này.\n\n"
            "Sếp đánh giá output em vừa làm thế nào ạ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=RATING_KEYBOARD,
        )
        return

    # Lazy trigger — chain sang skill gốc với BV vừa setup
    await save_session(session)

    # Special: resume tone calibration (không dispatch qua task form)
    if pending_skill == "tone_calibration":
        pending_cal = session.tone_calibration.pop("pending_calendar", "")
        await save_session(session)
        await message.reply_text(
            "✅ *Brand Voice đã lưu!* Em kiểm tra tone cho Lịch Nội Dung luôn nhé...",
            parse_mode=ParseMode.MARKDOWN,
        )
        await _start_tone_calibration(message, session, pending_cal)
        return

    # Special: resume weekly content-gen flow (hỏi tuần thay vì chạy full-month)
    if pending_skill == "content_generator" and resume_weekly:
        await message.reply_text(
            "✅ *Brand Voice đã lưu!* Giờ mình chạy nội dung từng tuần nhé.",
            parse_mode=ParseMode.MARKDOWN,
        )
        await _start_content_generation(message, session, weekly=True)
        return

    pending_label = (
        get_task(pending_skill).label if get_task(pending_skill) else pending_skill
    )
    await message.reply_text(
        f"✅ *Brand Voice đã lưu!* Em tiếp tục *{pending_label}* "
        f"với BV vừa setup luôn nhé...",
        parse_mode=ParseMode.MARKDOWN,
    )
    session.selected_task = pending_skill
    session.pending_intake = {}  # reset for fresh intake
    await save_session(session)
    if pending_skill in ("ads_copy", "ads_generator"):
        from bot.keyboards import ADS_COPY_TIER_KEYBOARD as _ADS_KB
        await message.reply_text(
            "📢 *Sản Xuất Nội Dung Ads* — chọn tier:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_ADS_KB,
        )
    elif pending_skill == "video_scripts":
        from bot.keyboards import VIDEO_CREATOR_KEYBOARD as _VID_KB
        await message.reply_text(
            "🎬 *Viết Kịch Bản Video* — chọn loại creator:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_VID_KB,
        )
    else:
        await _send_single_shot_form(message, session, pending_skill)


async def _persist_brand_voice_from_session(session, raw_markdown: str):
    """Sau khi brand_voice skill xong, save BV vào user_brand_voice DB.
    Parse what we can từ pending_intake + markdown output. Graceful on error.
    """
    try:
        from storage import save_brand_voice, BrandVoice

        intake = session.pending_intake or {}
        do_rules = _split_rule_lines(intake.get("do_list", ""))
        dont_rules = _split_rule_lines(intake.get("dont_list", ""))
        sample_content = intake.get("sample_content") or None

        bv = BrandVoice(
            user_id=session.user_id,
            do_rules=do_rules,
            dont_rules=dont_rules,
            tone_descriptors=_extract_tone_from_md(raw_markdown),
            banned_words=_extract_banned_words_from_md(raw_markdown),
            sample_content=sample_content,
            rules_markdown=raw_markdown[:10000],  # cap 10K
            industry_context=session.profile.industry,
        )

        saved = await save_brand_voice(bv)
        if saved:
            logger.info(
                "[BV] Persisted user=%d version=%d do=%d dont=%d banned=%d",
                session.user_id, saved.version,
                len(saved.do_rules), len(saved.dont_rules), len(saved.banned_words),
            )
        else:
            logger.warning("[BV] save_brand_voice returned None for user=%d", session.user_id)
    except Exception as e:
        # Non-fatal — flow vẫn tiếp tục
        logger.exception("[BV] persist failed for user=%d: %s", session.user_id, e)


_BV_EDIT_SYSTEM = """Bạn là chuyên gia Brand Voice. User đưa Brand Voice hiện tại (markdown) \
và 1 yêu cầu chỉnh sửa. Nhiệm vụ: trả về BẢN BRAND VOICE ĐÃ CẬP NHẬT, GIỮ NGUYÊN cấu trúc \
markdown gốc, chỉ thay đổi đúng phần user yêu cầu. KHÔNG giải thích, KHÔNG thêm lời dẫn — \
chỉ xuất markdown Brand Voice mới."""


async def _apply_bv_edit(session, instruction: str) -> "str | None":
    """Linh chat-edit: cập nhật Brand Voice theo yêu cầu tự do của user.
    Returns updated markdown nếu thành công, None nếu fail. Non-fatal."""
    try:
        from storage import get_brand_voice, save_brand_voice, BrandVoice
        from agents.pipeline import client as _anthropic_client
        from config import CLAUDE_SONNET_MODEL

        bv = await get_brand_voice(session.user_id)
        current_md = ((bv.rules_markdown if bv else "") or
                      (bv.to_prompt_block(max_chars=4000) if bv and not bv.is_empty() else ""))
        if not current_md.strip():
            return None

        user_msg = (
            f"**Brand Voice hiện tại:**\n\n{current_md[:8000]}\n\n"
            f"---\n\n**Yêu cầu chỉnh sửa của sếp:**\n{instruction}\n\n"
            f"Trả về Brand Voice đã cập nhật (markdown)."
        )
        resp = await _anthropic_client.messages.create(
            model=CLAUDE_SONNET_MODEL,
            max_tokens=4000,
            system=_BV_EDIT_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        updated_md = resp.content[0].text.strip()
        if not updated_md:
            return None

        # Sync discrete fields từ markdown mới (giữ DB nhất quán sau chat-edit).
        # Nếu parse được thì dùng bản mới; parse fail → giữ giá trị cũ.
        new_do = _extract_do_rules_from_md(updated_md) or (bv.do_rules if bv else [])
        new_dont = _extract_dont_rules_from_md(updated_md) or (bv.dont_rules if bv else [])

        new_bv = BrandVoice(
            user_id=session.user_id,
            do_rules=new_do,
            dont_rules=new_dont,
            tone_descriptors=_extract_tone_from_md(updated_md) or (bv.tone_descriptors if bv else []),
            banned_words=_extract_banned_words_from_md(updated_md) or (bv.banned_words if bv else []),
            preferred_words=(bv.preferred_words if bv else []),
            sample_content=(bv.sample_content if bv else None),
            rules_markdown=updated_md[:10000],
            industry_context=(bv.industry_context if bv else session.profile.industry),
        )
        saved = await save_brand_voice(new_bv)
        if saved:
            logger.info("[BV] Edited via chat user=%d version=%d", session.user_id, saved.version)
        return updated_md
    except Exception as e:
        logger.exception("[BV] chat-edit failed user=%d: %s", session.user_id, e)
        return None


async def _send_bv_html(message: Message, session, bv_markdown: str, intro: str, keyboard=None):
    """Send Brand Voice: short inline preview card + full HTML file attachment."""
    import io as _io

    # Preview: first ~400 chars from leading non-empty lines
    preview_lines = [line.strip() for line in bv_markdown.split('\n') if line.strip()][:8]
    preview = '\n'.join(preview_lines)
    if len(preview) > 400:
        preview = preview[:400].rsplit('\n', 1)[0]
    ellipsis = '...' if len(bv_markdown) > len(preview) else ''

    card = f"{intro}\n\n{preview}{ellipsis}\n\n📎 _Xem đầy đủ trong file HTML bên dưới_"
    await _safe_reply(message, card, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    _biz = (session.profile.business_name or "Business").strip()
    _slug = re.sub(r'[^a-zA-Z0-9_-]', '_', _biz)[:20].strip('_') or 'bv'
    try:
        from bot.html_report import build_single_skill_report
        from agents.skills import OutputFormat
        from bot.renderers import parse_operational_deliverable
        parsed = parse_operational_deliverable(bv_markdown)
        if not parsed.get("summary") and not parsed.get("deliverable"):
            parsed["deliverable"] = bv_markdown
        html_str = build_single_skill_report(
            "brand_voice", parsed, OutputFormat.OPERATIONAL_DELIVERABLE,
            business_name=_biz,
            industry=session.profile.industry or "",
            stage=session.profile.stage or "",
        )
        buf = _io.BytesIO(html_str.encode("utf-8"))
        fname = f"brand_voice_{_slug}.html"
        buf.name = fname
        await message.reply_document(
            document=buf, filename=fname,
            caption="📄 *Brand Voice* — bản đầy đủ (HTML)",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning("[BV] HTML send failed: %s", e)


# ─── Admin Commands ───────────────────────────────────────────────

def _admin_only(handler):
    """Decorator: block non-admin users khỏi admin commands."""
    @functools.wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from config import ADMIN_IDS
        user_id = update.effective_user.id if update.effective_user else None
        if not user_id or user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Lệnh này chỉ dành cho admin.")
            return
        return await handler(update, context)
    return wrapped


@_admin_only
async def cmd_admin_addquota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/addquota <user_id> <amount> — Cộng thêm N token vào quota của user."""
    args = context.args
    if len(args) != 2 or not args[0].lstrip("-").isdigit() or not args[1].lstrip("-").isdigit():
        await update.message.reply_text(
            "⚠️ *Cú pháp:* `/addquota <user_id> <amount>`\n"
            "Ví dụ: `/addquota 123456789 500000`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    target_id = int(args[0])
    amount = int(args[1])
    if amount <= 0:
        await update.message.reply_text("⚠️ Amount phải là số dương.")
        return

    session = await get_session(target_id)
    from tools.token_tracker import get_quota, get_used, fmt

    old_quota = get_quota(session)
    new_quota = old_quota + amount
    session.preferences["token_quota"] = str(new_quota)
    await save_session(session)

    used = get_used(session)
    await update.message.reply_text(
        f"✅ *Nạp token thành công*\n\n"
        f"👤 User ID: `{target_id}`\n"
        f"➕ Nạp thêm: *{fmt(amount)}*\n"
        f"📊 Quota mới: *{fmt(new_quota)}* (trước: {fmt(old_quota)})\n"
        f"📉 Đã dùng: *{fmt(used)}*\n"
        f"💚 Còn lại: *{fmt(max(0, new_quota - used))}*",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("[admin] addquota user=%d amount=%d new_quota=%d by admin=%d",
                target_id, amount, new_quota, update.effective_user.id)


@_admin_only
async def cmd_admin_setquota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setquota <user_id> <amount> — Set quota tuyệt đối cho user (ghi đè)."""
    args = context.args
    if len(args) != 2 or not args[0].lstrip("-").isdigit() or not args[1].lstrip("-").isdigit():
        await update.message.reply_text(
            "⚠️ *Cú pháp:* `/setquota <user_id> <amount>`\n"
            "Ví dụ: `/setquota 123456789 2000000`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    target_id = int(args[0])
    new_quota = int(args[1])
    if new_quota < 0:
        await update.message.reply_text("⚠️ Quota phải >= 0.")
        return

    session = await get_session(target_id)
    from tools.token_tracker import get_quota, get_used, fmt

    old_quota = get_quota(session)
    session.preferences["token_quota"] = str(new_quota)
    await save_session(session)

    used = get_used(session)
    await update.message.reply_text(
        f"✅ *Set quota thành công*\n\n"
        f"👤 User ID: `{target_id}`\n"
        f"📊 Quota mới: *{fmt(new_quota)}* (trước: {fmt(old_quota)})\n"
        f"📉 Đã dùng: *{fmt(used)}*\n"
        f"💚 Còn lại: *{fmt(max(0, new_quota - used))}*",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("[admin] setquota user=%d new_quota=%d old_quota=%d by admin=%d",
                target_id, new_quota, old_quota, update.effective_user.id)


@_admin_only
async def cmd_admin_resetusage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/resetusage <user_id> — Reset token_used về 0, giữ nguyên quota."""
    args = context.args
    if len(args) != 1 or not args[0].lstrip("-").isdigit():
        await update.message.reply_text(
            "⚠️ *Cú pháp:* `/resetusage <user_id>`\n"
            "Ví dụ: `/resetusage 123456789`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    target_id = int(args[0])
    session = await get_session(target_id)
    from tools.token_tracker import get_quota, get_used, fmt

    old_used = get_used(session)
    quota = get_quota(session)
    session.preferences["token_used"] = "0"
    await save_session(session)

    await update.message.reply_text(
        f"✅ *Reset usage thành công*\n\n"
        f"👤 User ID: `{target_id}`\n"
        f"🗑️ Đã xóa: *{fmt(old_used)}* tokens đã dùng\n"
        f"📊 Quota hiện tại: *{fmt(quota)}*\n"
        f"💚 Còn lại sau reset: *{fmt(quota)}*",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("[admin] resetusage user=%d old_used=%d by admin=%d",
                target_id, old_used, update.effective_user.id)


@_admin_only
async def cmd_admin_userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/userinfo <user_id> — Xem thông tin token + profile của user."""
    args = context.args
    if len(args) != 1 or not args[0].lstrip("-").isdigit():
        await update.message.reply_text(
            "⚠️ *Cú pháp:* `/userinfo <user_id>`\n"
            "Ví dụ: `/userinfo 123456789`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    target_id = int(args[0])
    session = await get_session(target_id)
    from tools.token_tracker import get_quota, get_used, get_remaining, fmt, is_low, is_exhausted

    used = get_used(session)
    quota = get_quota(session)
    remaining = get_remaining(session)
    pct = (used / quota * 100) if quota else 0

    if is_exhausted(session):
        status = "🔴 Hết quota"
    elif is_low(session):
        status = "⚠️ Sắp hết (< 10%)"
    else:
        status = "✅ Bình thường"

    name = session.preferences.get("user_name", "_(chưa đặt)_")
    business = session.profile.business_name or "_(chưa có)_"
    stage = session.stage.value

    await update.message.reply_text(
        f"👤 *Thông tin user `{target_id}`*\n\n"
        f"🏷️ Tên: {name}\n"
        f"🏢 Business: {business}\n"
        f"📍 Stage hiện tại: `{stage}`\n\n"
        f"─────────────────────\n"
        f"💎 *Token*\n"
        f"📊 Quota: *{fmt(quota)}*\n"
        f"📉 Đã dùng: *{fmt(used)}* ({pct:.1f}%)\n"
        f"💚 Còn lại: *{fmt(remaining)}*\n"
        f"📌 Trạng thái: {status}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─────────────────────────────────────────────────────────────────
# /history — Campaign History + Semantic Search  (Sprint 8)
# ─────────────────────────────────────────────────────────────────

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /history [query] — Xem hoặc tìm kiếm lịch sử campaigns.

    - /history          → Liệt kê 10 campaigns gần nhất
    - /history <query>  → Semantic search (tìm campaign tương tự)

    Mỗi entry hiển thị: business, ngành, mục tiêu, ngày chạy.
    """
    user_id = update.effective_user.id
    query = " ".join(context.args).strip() if context.args else ""

    from storage.campaign_history import list_campaigns, search_similar_campaigns

    await update.message.reply_text("🔍 Đang tìm...", parse_mode=ParseMode.MARKDOWN)

    if query:
        campaigns = await search_similar_campaigns(user_id, query, top_k=5)
        header = f"🔍 *Kết quả tìm kiếm:* _{query}_\n\n"
    else:
        campaigns = await list_campaigns(user_id, limit=10)
        header = "📚 *Lịch sử Campaigns của bạn*\n\n"

    if not campaigns:
        msg = (
            header +
            "_(Chưa có campaign nào được lưu)_\n\n"
            "💡 Chạy Nghiên Cứu & Phân Tích Thị Trường để bắt đầu tích lũy lịch sử."
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    lines = [header]
    for i, c in enumerate(campaigns, start=1):
        biz  = c.get("business_name") or "_(chưa đặt tên)_"
        ind  = c.get("industry") or "—"
        goal = c.get("primary_goal") or "—"
        date = (c.get("created_at") or "")[:10]  # YYYY-MM-DD
        sim  = c.get("similarity")

        sim_tag = f" · {sim*100:.0f}% match" if sim is not None else ""
        lines.append(
            f"*{i}.* {biz}\n"
            f"   📌 {ind} · {goal}\n"
            f"   🗓 {date}{sim_tag}\n"
        )

    lines.append("\n💡 _Dùng `/history <từ khoá>` để tìm campaign tương tự_")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


# ═════════════════════════════════════════════════════════════════
# Sprint 6 — Tone Calibration Loop
# ═════════════════════════════════════════════════════════════════

async def _start_tone_calibration(message, session, calendar_result: str) -> None:
    """
    Sau khi content_calendar gen xong: hỏi Brand Voice trước nếu chưa setup
    (gate giữ nguyên thứ tự), rồi đi THẲNG vào menu sản xuất content với BV
    đã có — KHÔNG còn bước "Bài mẫu đầu tiên" / tone calibration loop
    (BACKLOG #10d).
    """
    from agents.post_actions import parse_calendar_to_posts

    # Brand Voice gate: hỏi BV trước khi sản xuất content
    skipped_bv = session.pending_intake.get("_bv_skipped_session")
    if not skipped_bv:
        try:
            from storage import has_brand_voice
            has_bv = await has_brand_voice(session.user_id)
        except Exception:
            has_bv = True  # fail-safe: không block nếu storage lỗi
        if not has_bv:
            # Lưu calendar để resume sau khi BV xong/skip
            session.tone_calibration = {"pending_calendar": calendar_result}
            session.pending_intake["_bv_pending_skill"] = "tone_calibration"
            await save_session(session)
            await message.reply_text(
                "🎙 *Trước khi sản xuất content — sếp có muốn setup Brand Voice không?*\n\n"
                "Brand Voice giúp em viết đúng *tone & từ ngữ* của brand — "
                "bài viết sẽ nhất quán hơn nhiều khi sản xuất content sau này.\n\n"
                "_Chỉ cần setup 1 lần, áp dụng cho mọi nội dung. "
                "Sếp có thể bỏ qua giờ và setup sau._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=BRAND_VOICE_PROMPT_KEYBOARD,
            )
            return

    # Parse calendar → gán POST-XXX IDs ngay, dùng BV đã có (không cần sample post)
    campaign_id = session.pending_intake.get("campaign_name", "")
    posts = parse_calendar_to_posts(calendar_result, campaign_id=campaign_id)
    if posts:
        session.content_outputs.update(posts)
    session.tone_calibration = {"stage": "done"}
    await save_session(session)

    if posts:
        post_count = len(posts)
        await message.reply_text(
            f"📋 *{post_count} bài đã được gán ID*\n\n"
            + "\n".join([f"`{pid}` — {p.get('channel','').capitalize()} · Tuần {p.get('week',1)}"
                        for pid, p in list(posts.items())[:10]])
            + ("\n..." if post_count > 10 else "")
            + "\n\n💡 _Dùng /post \\<ID\\> để xem + quản lý từng bài_",
            parse_mode=ParseMode.MARKDOWN,
        )

    await message.reply_text(
        "✅ *Lịch Nội Dung xong rồi sếp!*\n\n"
        "💡 *Gợi ý để có chất lượng tốt nhất:* Chạy từng tuần một — "
        "mỗi lần em tập trung sâu hơn vào từng bài thay vì chia token cho cả tháng.\n\n"
        "Sếp chọn cách nào ạ?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=CALENDAR_TO_CONTENT_GEN_KEYBOARD,
    )


async def _handle_tone_feedback(update, context, session, text: str) -> None:
    """
    Xử lý feedback text sau khi user bấm 'Chỉnh tone'.
    Extract signals → regen Post 1 → show với TONE_REGEN_KEYBOARD.
    """
    from agents.tone_calibration import (
        extract_tone_signals, regen_post_with_signals, format_signals_card
    )
    from bot.keyboards import TONE_REGEN_KEYBOARD

    cal = session.tone_calibration
    rejection_count = cal.get("rejection_count", 0) + 1

    await update.message.reply_text("🔄 _Đang chỉnh tone..._", parse_mode=ParseMode.MARKDOWN)

    post1 = cal.get("post1_content", "")
    signals = await extract_tone_signals(session, text, post1)
    new_post = await regen_post_with_signals(session, post1, signals)

    # Update state
    session.tone_calibration.update({
        "stage":           "checking_tone",
        "rejection_count": rejection_count,
        "post1_content":   new_post,
        "locked_signals":  signals,
    })
    await save_session(session)

    signals_card = format_signals_card(signals)
    max_attempts = 3
    remaining = max_attempts - rejection_count

    kb = TONE_REGEN_KEYBOARD
    suffix = ""
    if rejection_count >= max_attempts:
        suffix = "\n\n⚠️ _Đã chỉnh tối đa 3 lần — lần này sẽ tự lock tone._"
        # Auto-approve after 3 rejections
        await _tone_lock_and_apply(update.message, session)
        return

    await send_long_message(
        update.message,
        f"{signals_card}\n\n"
        f"*Bài viết lại:*\n\n"
        f"{new_post}\n\n"
        f"─────────────────────\n"
        f"_(Còn {remaining} lần chỉnh){suffix}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )


async def _tone_lock_and_apply(message, session) -> None:
    """
    Lock tone signals → apply lên full calendar → update session.
    """
    from agents.tone_calibration import apply_tone_to_calendar
    from agents.post_actions import parse_calendar_to_posts

    cal = session.tone_calibration
    signals = cal.get("locked_signals", {})
    post1 = cal.get("post1_content", "")
    calendar_full = cal.get("calendar_full", "")

    await message.reply_text(
        "🔒 *Tone đã lock!* Em đang apply cho toàn bộ calendar...",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Apply tone lên full calendar
    if signals:
        updated_calendar = await apply_tone_to_calendar(session, calendar_full, signals, post1)
    else:
        updated_calendar = calendar_full

    # Sprint 7: Parse posts → assign POST-XXX IDs
    campaign_id = session.pending_intake.get("campaign_name", "")
    posts = parse_calendar_to_posts(updated_calendar, campaign_id=campaign_id)
    if posts:
        session.content_outputs.update(posts)

    # Update results + clear tone state
    session.add_result("content_calendar", updated_calendar)
    session.tone_calibration = {"stage": "done", "locked_signals": signals}
    await save_session(session)

    # Show updated calendar
    preview = updated_calendar[:2000] + ("..." if len(updated_calendar) > 2000 else "")
    await message.reply_text(
        f"✅ *Content Calendar (Tone Applied)*\n\n{preview}",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Sprint 7: Show post IDs summary
    if posts:
        post_count = len(posts)
        await message.reply_text(
            f"📋 *{post_count} bài đã được gán ID*\n\n"
            + "\n".join([f"`{pid}` — {p.get('channel','').capitalize()} · Tuần {p.get('week',1)}"
                        for pid, p in list(posts.items())[:10]])
            + ("\n..." if post_count > 10 else "")
            + "\n\n💡 _Dùng /post \\<ID\\> để xem + quản lý từng bài_",
            parse_mode=ParseMode.MARKDOWN,
        )

    # Show content-gen upsell AFTER tone is locked
    await message.reply_text(
        "✅ *Lịch Nội Dung xong rồi sếp!*\n\n"
        "💡 *Gợi ý để có chất lượng tốt nhất:* Chạy từng tuần một — "
        "mỗi lần em tập trung sâu hơn vào từng bài thay vì chia token cho cả tháng.\n\n"
        "Sếp chọn cách nào ạ?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=CALENDAR_TO_CONTENT_GEN_KEYBOARD,
    )


# ─── Tone calibration callbacks ───────────────────────────────────────────────

async def _handle_tone_callback(query, session) -> None:
    """Dispatch tone_* callback queries."""
    data = query.data

    if data == "tone_approve":
        await query.edit_message_reply_markup(reply_markup=None)
        # Lock với signals hiện tại (có thể rỗng nếu approve ngay lần đầu)
        await _tone_lock_and_apply(query.message, session)

    elif data == "tone_reject":
        await query.edit_message_reply_markup(reply_markup=None)
        session.tone_calibration["stage"] = "waiting_feedback"
        await save_session(session)
        await query.message.reply_text(
            "✏️ *Gõ feedback về tone để em chỉnh:*\n\n"
            "_Ví dụ: 'Viết thân mật hơn, bớt formal' / 'Thêm emoji' / 'Ngắn hơn, mạnh hơn'_",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "tone_skip":
        await query.edit_message_reply_markup(reply_markup=None)
        # Skip: parse calendar gốc sang POST-XXX luôn không apply tone
        cal = session.tone_calibration
        from agents.post_actions import parse_calendar_to_posts
        posts = parse_calendar_to_posts(cal.get("calendar_full", ""))
        if posts:
            session.content_outputs.update(posts)
        session.tone_calibration = {"stage": "done"}
        await save_session(session)
        await query.message.reply_text(
            f"⏭ _Bỏ qua tone calibration. Calendar đã lưu với {len(posts)} bài._",
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.message.reply_text(
            "✅ *Lịch Nội Dung xong rồi sếp!*\n\n"
            "💡 *Gợi ý để có chất lượng tốt nhất:* Chạy từng tuần một — "
            "mỗi lần em tập trung sâu hơn vào từng bài thay vì chia token cho cả tháng.\n\n"
            "Sếp chọn cách nào ạ?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=CALENDAR_TO_CONTENT_GEN_KEYBOARD,
        )


# ═════════════════════════════════════════════════════════════════
# Sprint 7 — Per-post Actions (/post command + callbacks)
# ═════════════════════════════════════════════════════════════════

async def cmd_post(update, context) -> None:
    """
    /post <POST-ID> — Xem chi tiết + action menu cho 1 bài.
    Ví dụ: /post POST-001  hoặc  /post 001
    """
    user_id = update.effective_user.id
    from storage import get_session
    session = await get_session(user_id)

    arg = " ".join(context.args).strip().upper()
    if not arg.startswith("POST-"):
        arg = f"POST-{arg.zfill(3)}"

    post = session.content_outputs.get(arg)
    if not post:
        await update.message.reply_text(
            f"❌ Không tìm thấy `{arg}`.\n"
            "Dùng `/history` để xem danh sách posts.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    from agents.post_actions import format_post_preview
    from bot.keyboards import post_action_keyboard

    preview = format_post_preview(arg, post)
    await update.message.reply_text(
        preview,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=post_action_keyboard(arg),
    )


async def _handle_post_action_callback(query, session) -> None:
    """Dispatch post_edit/adapt/variant/delete callbacks."""
    data = query.data  # e.g. "post_edit_001"
    parts = data.split("_", 2)  # ["post", "edit", "001"]
    if len(parts) < 3:
        return

    action = parts[1]  # edit | adapt | variant | delete
    pid_short = parts[2]  # "001"
    post_id = f"POST-{pid_short}"
    post = session.content_outputs.get(post_id)

    if not post:
        await query.answer("Không tìm thấy bài này.", show_alert=True)
        return

    await query.edit_message_reply_markup(reply_markup=None)

    if action == "delete":
        session.content_outputs[post_id]["status"] = "deleted"
        await save_session(session)
        await query.message.reply_text(
            f"🗑 `{post_id}` đã xoá khỏi calendar.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if action == "adapt":
        # Show channel selection
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 TikTok",    callback_data=f"adapt_{pid_short}_tiktok")],
            [InlineKeyboardButton("💬 Zalo OA",   callback_data=f"adapt_{pid_short}_zalo")],
            [InlineKeyboardButton("📸 Instagram", callback_data=f"adapt_{pid_short}_instagram")],
            [InlineKeyboardButton("📧 Email",     callback_data=f"adapt_{pid_short}_email")],
        ])
        await query.message.reply_text(
            f"🔄 Adapt `{post_id}` sang kênh nào?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
        return

    if action == "variant":
        await query.message.reply_text("✨ _Đang tạo A/B variant..._", parse_mode=ParseMode.MARKDOWN)
        from agents.post_actions import gen_variant
        variant_content = await gen_variant(post.get("content", ""), session)
        # Assign new ID
        existing = [k for k in session.content_outputs if k.startswith(f"{post_id}-V")]
        variant_id = f"{post_id}-V{len(existing)+1}"
        session.content_outputs[variant_id] = {
            **post,
            "content":   variant_content,
            "parent_id": post_id,
            "status":    "draft",
        }
        await save_session(session)
        from agents.post_actions import format_post_preview
        from bot.keyboards import post_action_keyboard
        await query.message.reply_text(
            f"✨ *Variant tạo thành công:* `{variant_id}`\n\n"
            + format_post_preview(variant_id, session.content_outputs[variant_id]),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=post_action_keyboard(variant_id),
        )
        return

    if action == "edit":
        # Set state chờ edit instruction
        session.pending_intake["_post_editing"] = post_id
        await save_session(session)
        await query.message.reply_text(
            f"✏️ *Edit `{post_id}`* — gõ yêu cầu chỉnh sửa:\n\n"
            "_Ví dụ: 'Viết hook mạnh hơn' / 'Thêm social proof' / 'Ngắn hơn 30%'_",
            parse_mode=ParseMode.MARKDOWN,
        )


async def _handle_adapt_channel_callback(query, session) -> None:
    """Xử lý adapt_<pid>_<channel> callback."""
    parts = query.data.split("_", 2)  # ["adapt", "001", "tiktok"]
    if len(parts) < 3:
        return
    pid_short = parts[1]
    channel   = parts[2]
    post_id   = f"POST-{pid_short}"
    post = session.content_outputs.get(post_id)
    if not post:
        await query.answer("Không tìm thấy bài.", show_alert=True)
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"🔄 _Đang adapt `{post_id}` sang {channel.capitalize()}..._",
        parse_mode=ParseMode.MARKDOWN,
    )

    from agents.post_actions import adapt_post
    adapted = await adapt_post(post.get("content", ""), channel, session)

    adapted_id = f"{post_id}-{channel[:2].upper()}"
    session.content_outputs[adapted_id] = {
        **post,
        "content":   adapted,
        "channel":   channel,
        "parent_id": post_id,
        "status":    "draft",
    }
    # Track adapted versions on parent
    session.content_outputs[post_id].setdefault("adapted_versions", []).append(adapted_id)
    await save_session(session)

    from agents.post_actions import format_post_preview
    from bot.keyboards import post_action_keyboard
    await query.message.reply_text(
        f"✅ *Adapted: `{adapted_id}`* ({channel.capitalize()})\n\n"
        + format_post_preview(adapted_id, session.content_outputs[adapted_id]),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=post_action_keyboard(adapted_id),
    )


# ═════════════════════════════════════════════════════════════════
# McKinsey Discovery Gate — Basic Business Context (universal)
# Trước khi ANY skill chạy → bắt buộc có 5 fields:
#   industry, product_service, target_customer, stage, primary_goal
# ═════════════════════════════════════════════════════════════════

async def _send_basic_business_form(message: Message, session, pending_skill: str):
    """
    Show McKinsey discovery form khi user thiếu context cơ bản.
    Sau khi user trả lời → extract + save profile + chain lại pending_skill.
    """
    task = get_task(pending_skill)
    skill_label = task.label if task else pending_skill

    session.pending_intake[BIZ_CONTEXT_AWAITING]      = "1"
    session.pending_intake[BIZ_CONTEXT_PENDING_SKILL] = pending_skill
    session.stage = PipelineStage.INTAKE
    await save_session(session)

    # Pre-fill placeholders nếu profile có sẵn vài field
    p = session.profile
    pre = {
        "biz_name":         _escape_md(p.business_name)    if p.business_name    else "_(chưa có)_",
        "industry":         _escape_md(p.industry)         if p.industry         else "_(chưa có)_",
        "product":          _escape_md(p.product_service)  if p.product_service  else "_(chưa có)_",
        "target":           _escape_md(p.target_customer)  if p.target_customer  else "_(chưa có)_",
        "stage":            _escape_md(p.stage)            if p.stage            else "_(chưa có)_",
        "goal":             _escape_md(p.primary_goal)     if p.primary_goal     else "_(chưa có)_",
    }

    msg = (
        f"🎯 *Trước khi chạy {skill_label}, em cần nắm 6 ý cơ bản về business của sếp*\n\n"
        f"_Output sẽ generic nếu em không biết ngành/khách/giai đoạn của sếp. "
        f"Em hỏi 1 lần — lưu vĩnh viễn, lần sau không cần khai lại._\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*Sếp trả lời 6 câu (gõ tự do, em parse được):*\n\n"
        f"*1️⃣ Tên business:*\n"
        f"   _Vd: 'Spa Hoa Lan' / 'Công ty ABC' / 'Shop thời trang X'_\n"
        f"   _Hiện tại: {pre['biz_name']}_\n\n"
        f"*2️⃣ Ngành kinh doanh:*\n"
        f"   _Vd: F&B / SaaS / Spa-Beauty / Bán lẻ online / Đào tạo / BĐS / B2B service_\n"
        f"   _Hiện tại: {pre['industry']}_\n\n"
        f"*3️⃣ Sản phẩm/Dịch vụ chính:*\n"
        f"   _Vd: 'Combo skincare 5 sản phẩm' / 'App quản lý đơn online' / 'Khoá học marketing'_\n"
        f"   _Hiện tại: {pre['product']}_\n\n"
        f"*4️⃣ Khách hàng mục tiêu (ai mua):*\n"
        f"   _Vd: 'Phụ nữ 25-35t TP HCM' / 'SME 10-50 nhân viên' / 'Mẹ bỉm có con < 3t'_\n"
        f"   _Hiện tại: {pre['target']}_\n\n"
        f"*5️⃣ Stage hiện tại:*\n"
        f"   _Mới mở (<6 tháng) / Đang tăng trưởng / Ổn định scale / Maturity_\n"
        f"   _Hiện tại: {pre['stage']}_\n\n"
        f"*6️⃣ Mục tiêu chính 3 tháng tới:*\n"
        f"   _Vd: 'Tăng doanh thu 30%' / 'Mở thêm kênh TikTok' / 'Giữ chân khách cũ' / 'Tăng AOV'_\n"
        f"   _Hiện tại: {pre['goal']}_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 *Gửi 1 tin theo format trên — em parse và hỏi thêm 1 câu nữa rồi chạy {skill_label} ngay.*"
    )
    await message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def _haiku_extract_basic_business(text: str, session) -> dict:
    """Extract basic business fields từ free-form text via Haiku.
    Returns dict — 5 must-have + location bonus nếu user có nhắc.
    """
    import anthropic, json as _json
    from config import CLAUDE_HAIKU_MODEL, ANTHROPIC_API_KEY

    system = """Extract business fields từ user message thành JSON.

Fields cần extract (nếu user có nhắc):
- business_name    : tên business/thương hiệu/công ty (giữ nguyên như user gõ)
- industry         : ngành kinh doanh, NORMALIZE thành 1 trong 15 nhãn sau — chọn gần nhất:
  fnb (nhà hàng/cà phê/quán ăn/food), tech_saas (app/phần mềm/saas/digital product),
  ecommerce (shop online/tmđt/dropship), education (khóa học/coaching/đào tạo/gia sư),
  health_beauty (spa/làm đẹp/thẩm mỹ/nail/tóc/gym/yoga), retail (cửa hàng bán lẻ/siêu thị mini/tạp hóa),
  b2b_service (tư vấn/outsourcing/dịch vụ cho doanh nghiệp), real_estate (bất động sản/môi giới nhà đất),
  health_clinic (phòng khám/nha khoa/da liễu/bác sĩ), agency (marketing agency/pr/creative/quảng cáo),
  fashion_retail (thời trang/quần áo/phụ kiện/túi xách), travel_hospitality (khách sạn/resort/homestay/tour/du lịch),
  interior_design (nội thất/kiến trúc/home decor/thiết kế), pet_care (thú cưng/thú y/grooming/pet hotel/pet shop),
  events_wedding (tổ chức sự kiện/tiệc cưới/venue/event).
- product_service  : sản phẩm/dịch vụ chính (1 câu ngắn)
- target_customer  : khách hàng mục tiêu — CHỈ demographic/psychographic, KHÔNG kèm địa danh (vd "Gen Z 18-25", "phụ nữ 25-35", "SME 10-50 NV")
- location         : địa bàn — TÁCH RIÊNG nếu user nhắc thành phố/khu vực (vd "Hà Nội", "HCM", "Đà Nẵng", "TP HCM Q1-Q3", "miền Bắc"). Nếu user gộp "Gen Z Hà Nội" → tách thành target_customer="Gen Z" và location="Hà Nội".
- stage            : NORMALIZE thành 1 trong: idea, mvp, growth, scale. Mapping: "mới mở/dưới 6 tháng"→idea/mvp, "tăng trưởng"→growth, "ổn định/scale/maturity"→scale.
- primary_goal     : mục tiêu chính (1 câu ngắn)

QUY TẮC:
- Field nào không có trong message → bỏ qua, KHÔNG put null/empty.
- KHÔNG thêm field nào ngoài list trên.
- Output CHỈ JSON object, không markdown, không giải thích.

Ví dụ:
Input: "1: Spa Hoa Lan\\n2: thời trang\\n3: cho thuê quần áo\\n4: Gen Z Hà Nội\\n5: mới mở\\nTăng doanh thu 50%"
Output: {"business_name":"Spa Hoa Lan","industry":"retail","product_service":"cho thuê quần áo","target_customer":"Gen Z","location":"Hà Nội","stage":"mvp","primary_goal":"Tăng doanh thu 50%"}"""

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        resp = await client.messages.create(
            model=CLAUDE_HAIKU_MODEL,
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        try:
            from tools.token_tracker import track_usage
            track_usage(session, resp, label="biz_context_extract")
        except Exception:
            pass

        raw = resp.content[0].text.strip()
        raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
        data = _json.loads(raw)

        valid = {"business_name", "industry", "product_service", "target_customer",
                 "location", "stage", "primary_goal"}
        extracted = {k: str(v).strip() for k, v in data.items() if k in valid and v}

        # Fallback regex: nếu Haiku miss location, detect VN cities trong target_customer
        if not extracted.get("location") and extracted.get("target_customer"):
            target = extracted["target_customer"]
            _VN_CITIES = [
                r"\bHà Nội\b", r"\bHCM\b", r"\bTP\.?\s*HCM\b", r"\bSài Gòn\b",
                r"\bĐà Nẵng\b", r"\bHải Phòng\b", r"\bCần Thơ\b", r"\bNha Trang\b",
                r"\bVũng Tàu\b", r"\bBiên Hòa\b", r"\bHuế\b",
            ]
            for pat in _VN_CITIES:
                m = re.search(pat, target, re.IGNORECASE)
                if m:
                    city = m.group(0)
                    extracted["location"] = city.strip()
                    # Strip city khỏi target_customer
                    cleaned = re.sub(pat, "", target, flags=re.IGNORECASE).strip(" ,;.-")
                    if cleaned:
                        extracted["target_customer"] = cleaned
                    break

        return extracted
    except Exception as e:
        logger.warning("Haiku extract basic business failed: %s — text=%s", e, text[:100])
        return {}


async def _send_usp_gate(message: Message, session, pending_skill: str):
    """Ask user about USP after McKinsey Gate — single question, branching by response."""
    session.pending_intake["_awaiting_usp_text"] = "1"
    session.pending_intake["_usp_pending_skill"] = pending_skill
    await save_session(session)
    await message.reply_text(
        "💎 *Một câu cuối — USP của sếp là gì?*\n\n"
        "_Điểm khác biệt / lợi thế cạnh tranh chính so với đối thủ_\n\n"
        "Vd: 'Giao hàng trong 2h' / 'Giá rẻ hơn 30% so với spa cùng chất lượng' / "
        "'Công nghệ X duy nhất ở VN'\n\n"
        "_Nếu chưa có → gõ *'chưa có'* để Max phân tích giúp_",
        parse_mode=ParseMode.MARKDOWN,
    )


_NO_USP_SIGNALS = {"chưa có", "chua co", "không có", "khong co", "không", "chưa", "ko", "k có",
                   "không biết", "chưa rõ", "chưa xác định", "skip", "bỏ qua"}


async def _handle_usp_text(update, context, session, text: str):
    """Process user's USP answer → branch based on whether they have one."""
    session.pending_intake.pop("_awaiting_usp_text", None)
    pending_skill = session.pending_intake.get("_usp_pending_skill", "")

    if text.strip().lower() in _NO_USP_SIGNALS or len(text.strip()) < 5:
        # No USP → proceed, usp_definition will run in pipeline normally
        session.pending_intake.pop("_usp_pending_skill", None)
        await save_session(session)
        await update.message.reply_text(
            "OK ạ — Max sẽ phân tích và đề xuất USP trong quá trình nghiên cứu.",
            parse_mode=ParseMode.MARKDOWN,
        )
        if pending_skill:
            await _send_single_shot_form(update.message, session, pending_skill)
        return

    # Has USP → save it, ask if want more analysis
    session.pending_intake["_user_stated_usp"] = text.strip()
    await save_session(session)
    await update.message.reply_text(
        f"✅ Ghi nhận: _{text.strip()}_\n\n"
        f"Sếp có muốn Max phân tích thêm để tìm ra USP mạnh nhất không?\n\n"
        f"• *Phân tích thêm* → Max đối chiếu với thị trường & đối thủ, đề xuất nhiều góc USP để lựa\n"
        f"• *Dùng luôn* → Max dùng USP này làm nền luôn, không phân tích thêm",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=USP_ANALYZE_KEYBOARD,
    )


async def _handle_basic_business_text(update, context, session, text: str):
    """User submitted basic business form → extract, save, chain to pending skill."""
    pending_skill = session.pending_intake.get(BIZ_CONTEXT_PENDING_SKILL)
    if not pending_skill:
        # Edge case: marker present nhưng pending skill missing → clear + show menu
        session.pending_intake.pop(BIZ_CONTEXT_AWAITING, None)
        await save_session(session)
        await update.message.reply_text(
            "⚠️ Em mất context skill đang chạy. Sếp chọn lại từ menu nhé:",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    await update.message.reply_text("🔍 _Em đang ghi nhớ business của sếp..._", parse_mode=ParseMode.MARKDOWN)

    extracted = await _haiku_extract_basic_business(text, session)

    # Save to profile
    p = session.profile
    if extracted.get("business_name"):    p.business_name    = extracted["business_name"]
    if extracted.get("industry"):         p.industry         = extracted["industry"]
    if extracted.get("product_service"):  p.product_service  = extracted["product_service"]
    if extracted.get("target_customer"):  p.target_customer  = extracted["target_customer"]
    if extracted.get("location"):         p.location         = extracted["location"]
    if extracted.get("stage"):            p.stage            = extracted["stage"]
    if extracted.get("primary_goal"):     p.primary_goal     = extracted["primary_goal"]

    # Clear gate markers
    session.pending_intake.pop(BIZ_CONTEXT_AWAITING, None)
    session.pending_intake.pop(BIZ_CONTEXT_PENDING_SKILL, None)
    await save_session(session)

    # Check: extract đủ 5 fields chưa?
    if not p.is_basic_business_context_ready():
        # Vẫn thiếu — re-show form với fields đã có
        await update.message.reply_text(
            "⚠️ *Em chưa parse được đủ 5 ý.* Sếp gửi lại theo format trên giúp em nhé.\n\n"
            "_Em cần đủ 5 ý mới chạy chuẩn được, không bị output chung chung._",
            parse_mode=ParseMode.MARKDOWN,
        )
        # Re-trigger form với pending_skill cũ
        session.pending_intake[BIZ_CONTEXT_AWAITING] = "1"
        session.pending_intake[BIZ_CONTEXT_PENDING_SKILL] = pending_skill
        await save_session(session)
        return

    # Confirm
    summary_lines = []
    if p.business_name:
        summary_lines.append(f"• *Business:* {_escape_md(p.business_name)}")
    summary_lines.extend([
        f"• *Ngành:* {_escape_md(p.industry)}",
        f"• *Sản phẩm:* {_escape_md(p.product_service)}",
        f"• *Khách hàng:* {_escape_md(p.target_customer)}",
    ])
    if p.location:
        summary_lines.append(f"• *Địa bàn:* {_escape_md(p.location)}")
    summary_lines.extend([
        f"• *Stage:* {_escape_md(p.stage)}",
        f"• *Mục tiêu:* {_escape_md(p.primary_goal)}",
    ])

    await update.message.reply_text(
        "✅ *Em đã ghi nhớ:*\n\n"
        + "\n".join(summary_lines)
        + "\n\n_Lần sau dùng skill khác em không cần hỏi lại nữa._",
        parse_mode=ParseMode.MARKDOWN,
    )

    # USP gate — ask once; skip if already have usp result
    if not session.get_latest_result("usp_definition"):
        await _send_usp_gate(update.message, session, pending_skill)
    else:
        await _send_single_shot_form(update.message, session, pending_skill)


# ─────────────────────────────────────────────────────────────────
# FB ADS SCHEDULER — /connect_ads · /disconnect_ads · /ads_settings
# ─────────────────────────────────────────────────────────────────

def _build_metric_keyboard(tracked: list, with_done: bool = False, extra_rows: list = None):
    """Build inline keyboard chọn metric — dùng chung cho settings + setup + toggle re-render."""
    from services.ads_notifier import METRIC_LABELS
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    recommended = ["spend", "roas", "cpl", "frequency"]
    advanced    = ["cpm", "ctr", "vtr_3s", "reach"]
    deep        = ["purchases", "cpa", "cpc", "leads"]

    def _btn(key):
        icon, label, _ = METRIC_LABELS[key]
        tick = "✅" if key in tracked else "☐"
        return InlineKeyboardButton(f"{tick} {icon} {label}", callback_data=f"ads_toggle_metric:{key}")

    rows = [
        [InlineKeyboardButton("── ⭐ Khuyến nghị ──", callback_data="noop")],
        [_btn(k) for k in recommended],
        [InlineKeyboardButton("── 📊 Hiệu quả ads ──", callback_data="noop")],
        [_btn(k) for k in advanced],
        [InlineKeyboardButton("── 💡 Chuyên sâu ──", callback_data="noop")],
        [_btn(k) for k in deep],
    ]
    if with_done:
        rows.append([InlineKeyboardButton("✅ Xong — ngưỡng alert dùng mặc định", callback_data="ads_setup_default")])
    else:
        rows.append([InlineKeyboardButton("⚠️ Đặt ngưỡng alert", callback_data="ads_set_thresholds")])
    if extra_rows:
        rows.extend(extra_rows)
    return InlineKeyboardMarkup(rows)


async def cmd_connect_ads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/connect_ads — bắt đầu OAuth flow để kết nối FB Ad Account."""
    user_id = update.effective_user.id
    from config import FB_APP_ID, FB_APP_SECRET

    if not FB_APP_ID or not FB_APP_SECRET:
        await update.message.reply_text(
            "⚠️ *FB App chưa được cấu hình.*\n\n"
            "Admin cần set các env vars:\n"
            "`FB_APP_ID`, `FB_APP_SECRET`, `ENCRYPTION_KEY`\n\n"
            "Sau khi admin setup xong, sếp dùng lại lệnh này nhé.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    from config import ENCRYPTION_KEY
    if not ENCRYPTION_KEY:
        await update.message.reply_text(
            "⚠️ *ENCRYPTION_KEY chưa set.*\n\n"
            "Admin tạo key:\n"
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`\n"
            "rồi set vào env var `ENCRYPTION_KEY`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Kiểm tra đã kết nối chưa
    from storage.fb_connections import get_connection
    existing = await get_connection(user_id)
    if existing and existing.get("notification_enabled"):
        name = (existing.get("account_name") or existing.get("ad_account_id") or "?").replace("*", "").replace("_", "-")
        await update.message.reply_text(
            f"✅ *Đã kết nối:* {name}\n\n"
            "Có nhiều Ad Account muốn xem? Dùng `/switch_account` để đổi — không cần kết nối lại.\n"
            "Muốn đổi sang tài khoản FB khác hẳn? Dùng `/disconnect_ads` trước.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.reply_text(
        "🔗 *Kết nối Facebook Ads*\n\n"
        "Em đang tạo link OAuth... (hết hạn sau 15 phút)",
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        from services.fb_oauth import build_oauth_url
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        url = await build_oauth_url(user_id)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔗 Kết nối Facebook Ads", url=url)
        ]])
        await update.message.reply_text(
            "Bấm nút bên dưới để authorize FB Ads của sếp.\n\n"
            "Bot sẽ yêu cầu quyền `ads_read` + `read_insights` + `ads_management`.",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error("cmd_connect_ads failed user=%d: %s", user_id, e)
        await update.message.reply_text("❌ Lỗi tạo link OAuth. Admin kiểm tra log.")


async def cmd_switch_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/switch_account — chọn Ad Account khác (không cần re-OAuth)."""
    user_id = update.effective_user.id
    from storage.fb_connections import get_connection, get_available_accounts
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    conn = await get_connection(user_id)
    if not conn:
        await update.message.reply_text(
            "⚠️ Sếp chưa kết nối Facebook. Dùng `/connect_ads` trước.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    accounts = await get_available_accounts(user_id)
    if len(accounts) <= 1:
        current = conn.get("account_name") or conn.get("ad_account_id") or "?"
        await update.message.reply_text(
            f"ℹ️ Sếp chỉ có 1 Ad Account: *{current.replace('*','').replace('_','-')}*\n\n"
            "Để thêm account khác, dùng `/disconnect_ads` rồi connect lại bằng FB có nhiều accounts.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    active_id = conn.get("ad_account_id", "")
    buttons = []
    for a in accounts[:10]:
        aid = a.get("id", "")
        norm = aid if aid.startswith("act_") else f"act_{aid}"
        is_active = (norm == active_id or aid == active_id)
        label = f"{'✅' if is_active else '○'} {a.get('name') or aid}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"sw_acct:{aid}")])

    await update.message.reply_text(
        "🔄 *Chọn Ad Account muốn dùng:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_disconnect_ads(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/disconnect_ads — ngắt kết nối, xóa token."""
    user_id = update.effective_user.id
    from storage.fb_connections import get_connection, delete_connection

    conn = await get_connection(user_id)
    if not conn:
        await update.message.reply_text("Chưa kết nối FB Ads nào cả sếp ơi.")
        return

    name = (conn.get("account_name") or conn.get("ad_account_id") or "?").replace("*", "").replace("_", "-")
    await delete_connection(user_id)
    await update.message.reply_text(
        f"✅ Đã ngắt kết nối *{name}*.\n\nToken đã được xóa khỏi hệ thống.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_ads_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ads_settings — xem + chỉnh cài đặt báo cáo ads.

    Cho phép user:
    - Bật/tắt notification
    - Chọn chỉ số theo dõi (multi-select inline keyboard)
    - Đặt ngưỡng alert (Frequency / ROAS drop / CPM spike)
    """
    user_id = update.effective_user.id
    from storage.fb_connections import get_connection
    from services.ads_notifier import METRIC_LABELS, RECOMMENDED_METRICS

    conn = await get_connection(user_id)
    if not conn:
        await update.message.reply_text(
            "Chưa kết nối FB Ads. Dùng `/connect_ads` trước nhé sếp.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    name      = conn.get("account_name") or conn.get("ad_account_id")
    enabled   = conn.get("notification_enabled", True)
    tracked   = conn.get("tracked_metrics") or RECOMMENDED_METRICS
    freq_max  = conn.get("alert_frequency_max")
    roas_drop = conn.get("alert_roas_drop_pct")
    cpm_spike = conn.get("alert_cpm_spike_pct")

    status_icon = "🟢" if enabled else "🔴"
    tracked_labels = " · ".join(METRIC_LABELS[m][1] for m in tracked if m in METRIC_LABELS)

    text = (
        f"⚙️ *Cài đặt Ads Scheduler — {name}*\n\n"
        f"{status_icon} Báo cáo: {'Đang bật' if enabled else 'Đang tắt'} (8:00 sáng hàng ngày)\n"
        f"📊 Theo dõi: {tracked_labels}\n\n"
        f"*Ngưỡng cảnh báo:*\n"
        f"• Frequency > {freq_max if freq_max else 'benchmark ngành (5.0)'}\n"
        f"• ROAS giảm > {f'{roas_drop:.0f}%' if roas_drop else 'benchmark ngành (20%)'}\n"
        f"• CPM tăng > {f'{cpm_spike:.0f}%' if cpm_spike else 'benchmark ngành (30%)'}\n\n"
        f"{'🔴 Bấm chỉ số để bật/tắt. /ads_settings lại để bật báo cáo.' if not enabled else '📊 Bấm chỉ số để bật/tắt theo dõi.'}"
    )

    from telegram import InlineKeyboardButton
    kb = _build_metric_keyboard(tracked, extra_rows=[[
        InlineKeyboardButton(
            "🔴 Tắt báo cáo" if enabled else "🟢 Bật báo cáo",
            callback_data="ads_toggle_notify",
        ),
    ]])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _start_ads_task_command(update: Update, task_name: str) -> None:
    """Khởi chạy 1 ads task (ads_analytics/ads_optimizer) qua slash command —
    cùng đường với khi bấm nút trong menu Minh (reset intake, pre-check quota,
    rồi mở form). Dùng chung vì các message digest/alert/report đều gợi ý
    `/ads_analytics` · `/ads_optimizer` như command — nếu không đăng ký, gõ vào
    Telegram chỉ im lặng (filters.COMMAND chặn handle_message, không route đi đâu).
    """
    user_id = update.effective_user.id
    session = await get_session(user_id)

    try:
        from tools.token_tracker import is_exhausted, get_used, get_quota, fmt
        if is_exhausted(session):
            await update.message.reply_text(
                f"🔴 *Đã hết quota token!*\n\n"
                f"Đã dùng: {fmt(get_used(session))} / {fmt(get_quota(session))}\n\n"
                f"_Sếp liên hệ admin để nạp thêm hoặc chờ reset hàng tháng._",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
    except Exception as e:
        logger.warning("Token quota pre-check failed: %s", e)

    session.selected_task = task_name
    session.pending_intake = {}
    await save_session(session)
    await _send_single_shot_form(update.message, session, task_name)


async def cmd_ads_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ads_analytics — mở form Phân Tích & Audit Ads (giống bấm nút trong menu Minh)."""
    await _start_ads_task_command(update, "ads_analytics")


async def cmd_ads_optimizer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ads_optimizer — mở form Điều Chỉnh Ads (giống bấm nút trong menu Minh)."""
    await _start_ads_task_command(update, "ads_optimizer")


async def _handle_ads_threshold_text(update: Update, session, text: str) -> None:
    """Parse ngưỡng alert user nhập theo format 'key: value' mỗi dòng."""
    import re
    from storage.fb_connections import update_notification_settings
    from storage import save_session as _sv

    session.pending_intake.pop("_awaiting_ads_thresholds", None)
    await _sv(session)

    user_id = update.effective_user.id
    updates = {}
    lines = text.strip().lower().splitlines()

    for line in lines:
        m = re.match(r"(frequency|roas_drop|cpm_spike)\s*[:=]\s*([\d.]+)", line)
        if m:
            key, val = m.group(1), float(m.group(2))
            if key == "frequency":
                updates["alert_frequency_max"] = val
            elif key == "roas_drop":
                updates["alert_roas_drop_pct"] = val
            elif key == "cpm_spike":
                updates["alert_cpm_spike_pct"] = val

    if updates:
        await update_notification_settings(user_id, **updates)
        summary = []
        if "alert_frequency_max"  in updates: summary.append(f"Frequency > {updates['alert_frequency_max']}")
        if "alert_roas_drop_pct" in updates: summary.append(f"ROAS giảm > {updates['alert_roas_drop_pct']:.0f}%")
        if "alert_cpm_spike_pct" in updates: summary.append(f"CPM tăng > {updates['alert_cpm_spike_pct']:.0f}%")
        await update.message.reply_text(
            "✅ *Ngưỡng alert đã lưu:*\n" + "\n".join(f"• {s}" for s in summary),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            "Không parse được ngưỡng. Format đúng:\n"
            "`frequency: 5.0`\n`roas_drop: 20`\n`cpm_spike: 30`",
            parse_mode=ParseMode.MARKDOWN,
        )
