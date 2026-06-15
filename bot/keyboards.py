"""
Telegram inline keyboards for the bot.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


# ─────────────────────────────────────────────────────────────────
# MAIN MENU — Max (CMO/Layer 2) + Persona-based entry (6 active managers)
# ─────────────────────────────────────────────────────────────────

MAIN_MENU_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🧠 Max — Chiến lược & Điều phối (CMO)", callback_data="persona_menu_cmo")],
    [InlineKeyboardButton("📋 Brief Campaign — kế hoạch chiến dịch", callback_data="task_campaign_brief")],
    [InlineKeyboardButton("📅 Lịch Nội Dung — kế hoạch đăng bài", callback_data="task_content_calendar")],
    [InlineKeyboardButton("✍️ Viết Content — full workflow", callback_data="task_write_content")],
    [InlineKeyboardButton("📊 Minh — Ads & Performance",   callback_data="persona_menu_digital_marketing")],
    [InlineKeyboardButton("🎨 Linh — Brand Voice",          callback_data="persona_menu_brand")],
    [InlineKeyboardButton("✍️ Nam — Content",               callback_data="persona_menu_content")],
    [InlineKeyboardButton("🎬 Trang — TikTok",              callback_data="persona_menu_tiktok")],
    [InlineKeyboardButton("🚀 Khoa — Growth & Retention",  callback_data="persona_menu_growth")],
])

TASK_SELECT_KEYBOARD = MAIN_MENU_KEYBOARD  # alias

# ─────────────────────────────────────────────────────────────────
# QUICK MENU — persistent reply keyboard (góc dưới khung chat, kiểu shop bot)
# ─────────────────────────────────────────────────────────────────

QUICK_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["▶️ Tiếp tục", "🛍 Dịch vụ"],
        ["💬 Hỗ trợ", "👛 Ví token"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Chọn menu nhanh bên dưới",
)

# ─────────────────────────────────────────────────────────────────
# Persona sub-menus (custom flows) — Linh / Nam / Trang / Khoa
# ─────────────────────────────────────────────────────────────────

# Linh — khi ĐÃ có Brand Voice
LINH_BV_EXISTS_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✏️ Cập nhật / chỉnh sửa (chat)", callback_data="bv_edit_chat")],
    [InlineKeyboardButton("📋 Xem Brand Voice hiện tại",     callback_data="bv_view")],
    [InlineKeyboardButton("↩ Hỏi Linh thêm",                callback_data="continue_advisor")],
])

# Linh — khi CHƯA có Brand Voice
LINH_BV_NEW_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Tạo Brand Voice ngay", callback_data="bv_create")],
    [InlineKeyboardButton("↩ Hỏi Linh thêm",         callback_data="continue_advisor")],
])

# Nam — chọn mode viết content
NAM_MODE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📅 Viết theo Lịch Nội Dung",       callback_data="nam_mode_calendar")],
    [InlineKeyboardButton("✍️ Viết bài mới theo yêu cầu",     callback_data="nam_mode_fresh")],
    [InlineKeyboardButton("↩ Hỏi Nam thêm",                   callback_data="continue_advisor")],
])

# Trang — chọn mode video
TRANG_MODE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎬 Video theo Lịch Nội Dung",      callback_data="trang_mode_calendar")],
    [InlineKeyboardButton("📝 Viết kịch bản video mới",       callback_data="trang_mode_fresh")],
    [InlineKeyboardButton("↩ Hỏi Trang thêm",                 callback_data="continue_advisor")],
])

# Khoa — chọn kênh tập trung trước khi chạy retention/winback skill
GROWTH_CHANNEL_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🌐 Full đa kênh (recommend)", callback_data="growth_ch_all")],
    [
        InlineKeyboardButton("💬 Zalo OA", callback_data="growth_ch_zalo"),
        InlineKeyboardButton("📧 Email",   callback_data="growth_ch_email"),
        InlineKeyboardButton("📱 SMS",     callback_data="growth_ch_sms"),
    ],
])

# Sprint 1: Language preference setup (first-time)
LANG_LEVEL_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔴 Không rành — Toàn Việt",         callback_data="lang_none")],
    [InlineKeyboardButton("🟡 Hiểu cơ bản — Có giải thích",     callback_data="lang_moderate")],
    [InlineKeyboardButton("🟢 Thông thạo — EN tự nhiên",        callback_data="lang_fluent")],
])

# Sprint 2: Rating after skill execution (5 stars + skip)
RATING_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⭐",         callback_data="rate_1"),
        InlineKeyboardButton("⭐⭐",        callback_data="rate_2"),
        InlineKeyboardButton("⭐⭐⭐",       callback_data="rate_3"),
        InlineKeyboardButton("⭐⭐⭐⭐",      callback_data="rate_4"),
        InlineKeyboardButton("⭐⭐⭐⭐⭐",     callback_data="rate_5"),
    ],
    [InlineKeyboardButton("⏭️ Bỏ qua đánh giá", callback_data="rate_skip")],
])

# Sprint 2: After rating ≤ 3 + user provided feedback — 2 buttons only
REGEN_PROMPT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Chạy lại theo feedback", callback_data="regen_yes")],
    [InlineKeyboardButton("⏭️ Bỏ qua",                  callback_data="regen_no")],
])

# Sprint 2 v2: After rating ≤ 3 — trước khi user gõ feedback, cho skip luôn
FEEDBACK_PROMPT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭️ Bỏ qua, không feedback", callback_data="feedback_skip")],
])

# Sau khi Lịch Nội Dung xong — hỏi chạy hết hay cần sửa
CALENDAR_TO_CONTENT_GEN_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("⭐ Chạy từng tuần (chất lượng tốt hơn)", callback_data="run_content_gen_weekly_after_cal")],
    [InlineKeyboardButton("⚡ Chạy hết cả tháng (nhanh hơn)",       callback_data="run_content_gen_after_cal")],
    [InlineKeyboardButton("✏️ Cần sửa lịch",                         callback_data="calendar_edit_request")],
    [InlineKeyboardButton("⏭️ Để sau",                               callback_data="skip_content_gen_after_cal")],
])

# BACKLOG #10g — hỏi loại nội dung cần sản xuất TRƯỚC khi chạy, KHÔNG tự
# cascade hết post + video + UGC + ads cùng lúc.
CONTENT_TYPE_SCOPE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📝 Bài đăng (post)",      callback_data="ctype_post_batch")],
    [InlineKeyboardButton("🎬 Video Script",          callback_data="ctype_video_script_gen")],
    [InlineKeyboardButton("🤝 UGC Brief",             callback_data="ctype_ugc_brief")],
    [InlineKeyboardButton("📢 Ads Copy",              callback_data="ctype_ads_generator")],
    [InlineKeyboardButton("📦 Tất cả (full package)", callback_data="ctype_all")],
])

# Sau khi gửi Funnel Map + Execution Plan (HTML) → chờ user duyệt mới dựng calendar
FUNNEL_APPROVE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Duyệt kế hoạch — dựng Lịch Nội Dung", callback_data="funnel_approve")],
    # Đã gỡ nút test: "🎯 Vớt khách chưa convert" (rescue_nonconvert) + "🧪 Chạy lại
    # Funnel Map (debug)" (dbg_funnel). Handler 2 callback vẫn còn để không vỡ nếu
    # có message cũ, nhưng không hiển thị nút nữa.
])

# Sprint 5: Ads Generator — sau tier chooser, hỏi format (Video hay Ảnh)
ADS_FORMAT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎥 Video",     callback_data="ads_format_video")],
    [InlineKeyboardButton("🖼️ Ảnh tĩnh",  callback_data="ads_format_image")],
])

# Sprint 5 v2: Sau copy xong (format=image) — hỏi có upload ảnh mẫu không
IMAGE_REFERENCE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📤 Upload ảnh mẫu",          callback_data="img_ref_upload")],
    [InlineKeyboardButton("🎨 Tự gen theo brief",       callback_data="img_ref_skip")],
    [InlineKeyboardButton("⏭️ Chỉ lấy copy, không gen", callback_data="img_ref_no_gen")],
])

# Sprint 5 v2: Hỏi số lượng ảnh (bỏ cost display)
IMAGE_GEN_PROMPT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎨 Tạo 1 ảnh",        callback_data="img_gen_1")],
    [InlineKeyboardButton("🎨 Tạo 3 variants",   callback_data="img_gen_3")],
    [InlineKeyboardButton("⏭️ Bỏ qua",           callback_data="img_gen_skip")],
])

# Sprint 5: Chọn size ảnh
IMAGE_SIZE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📱 Vertical (Story/Reels)",  callback_data="img_size_vertical")],
    [InlineKeyboardButton("🖼️ Square (Feed)",            callback_data="img_size_square")],
    [InlineKeyboardButton("🖥️ Horizontal (Landscape)",  callback_data="img_size_horizontal")],
])

# Sprint 5 v2: Sau khi gen ảnh xong — Sửa hoặc Chốt
IMAGE_REVIEW_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✏️ Sửa ảnh này",          callback_data="img_edit")],
    [InlineKeyboardButton("✅ Chốt ảnh này",          callback_data="img_confirm")],
    [InlineKeyboardButton("🔁 Gen ảnh khác",          callback_data="img_regen")],
])


# ─────────────────────────────────────────────────────────────────
# Confirmation + flow control
# ─────────────────────────────────────────────────────────────────

CONFIRM_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Đúng rồi, bắt đầu!", callback_data="confirm_yes"),
        InlineKeyboardButton("✏️ Sửa thông tin",       callback_data="confirm_no"),
    ]
])

RESTART_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔄 Bắt đầu phân tích mới", callback_data="restart")],
])

# Nhắc nhẹ tên business trước khi chạy pipeline — user có thể bỏ qua
BIZNAME_SKIP_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭️ Thôi, chạy luôn", callback_data="bizname_skip")],
])

# Research Gate — hỏi trước khi chạy Nghiên Cứu & Phân Tích Thị Trường
RESEARCH_GATE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 Có rồi — paste bản nghiên cứu vào đây", callback_data="research_paste")],
    [InlineKeyboardButton("🔬 Chưa có — em và sếp cùng phân tích",    callback_data="research_analyze")],
])


# ─────────────────────────────────────────────────────────────────
# ACTION KEYBOARD — sau khi bất kỳ skill nào xong
# ─────────────────────────────────────────────────────────────────

ACTION_AFTER_SKILL = InlineKeyboardMarkup([
    [InlineKeyboardButton("🏠 Về menu chính",            callback_data="menu_main")],
    [InlineKeyboardButton("❓ Hỏi thêm về output này",  callback_data="ask_followup")],
])

# Aliases for backward compat (old callback_data "menu_strategic" / "menu_operational" still route to menu_main)
ACTION_AFTER_STRATEGIC = ACTION_AFTER_SKILL
ACTION_AFTER_OPS       = ACTION_AFTER_SKILL
ACTION_AFTER_ANALYSIS  = ACTION_AFTER_SKILL

# Post-strategy next steps (after rating): lead into execution rather than dead-end.
# Mô hình 2-track: 🟢 Content Engine (always-on, không offer) vs 🔴 Campaign (offer theo đợt).
ACTION_AFTER_STRATEGY = InlineKeyboardMarkup([
    [InlineKeyboardButton("🟢 Content Engine — lịch brand (always-on)", callback_data="strategy_ok_run_calendar")],
    [InlineKeyboardButton("🔴 Tạo Campaign — đẩy offer theo đợt",        callback_data="strategy_confirm")],
    [InlineKeyboardButton("🏠 Về menu chính",                            callback_data="menu_main")],
])

# Q&A follow-up — sau khi user hỏi thêm 1 lần, có thể hỏi tiếp hoặc thoát
ASK_FOLLOWUP_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("💬 Hỏi tiếp",              callback_data="ask_followup")],
    [InlineKeyboardButton("✅ Đủ rồi, về menu",        callback_data="menu_main")],
])


def get_action_keyboard(task_name: str) -> InlineKeyboardMarkup:
    """Return post-skill action keyboard, context-aware by task."""
    if task_name in ("strategy", "synthesis", "full", "tactical_playbook"):
        return ACTION_AFTER_STRATEGY
    return ACTION_AFTER_SKILL


def stage_done_keyboard(is_last: bool = False, task_name: str | None = None) -> InlineKeyboardMarkup:
    """Keyboard sau mỗi stage. is_last=True → action keyboard, else continue button."""
    if is_last:
        return ACTION_AFTER_SKILL
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Chạy bước tiếp theo", callback_data="continue_pipeline")],
    ])


# ─────────────────────────────────────────────────────────────────
# Variant choosers — for special ops skills
# ─────────────────────────────────────────────────────────────────

# Ads Copy: user picks which tier(s) to generate
ADS_COPY_TIER_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🌐 TOFU (Tệp lạnh)",    callback_data="ads_tier_tofu"),
        InlineKeyboardButton("🌡️ MOFU (Tệp ấm)",      callback_data="ads_tier_mofu"),
    ],
    [
        InlineKeyboardButton("🔥 BOFU (Tệp nóng)",   callback_data="ads_tier_bofu"),
        InlineKeyboardButton("⚡ Full 3 tầng",        callback_data="ads_tier_all"),
    ],
])

# Video Scripts: user picks creator type
VIDEO_CREATOR_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("👥 UGC (Khách thật)",    callback_data="video_creator_ugc"),
        InlineKeyboardButton("👤 EGC (Nhân viên)",     callback_data="video_creator_egc"),
    ],
    [
        InlineKeyboardButton("🎤 FGC (Founder)",       callback_data="video_creator_fgc"),
        InlineKeyboardButton("⭐ KOL/KOC (Paid)",      callback_data="video_creator_kol"),
    ],
])


# ─────────────────────────────────────────────────────────────────
# Strategy gating — skill cần Strategy base nhưng chưa có
# ─────────────────────────────────────────────────────────────────

NEEDS_STRATEGY_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Chạy A→Z, rồi quay lại task này", callback_data="run_az_then_back")],
    [InlineKeyboardButton("⏭️ Quay lại menu",                  callback_data="menu_main")],
])

# Sprint 5: Lazy Brand Voice setup prompt (creative ops skills)
BRAND_VOICE_PROMPT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Setup Brand Voice ngay",          callback_data="bv_setup_now")],
    [InlineKeyboardButton("⏭️ Bỏ qua, chạy luôn skill này",     callback_data="bv_skip_for_now")],
    [InlineKeyboardButton("🔙 Quay lại menu",                   callback_data="menu_main")],
])

# Brand Voice draft approval — show draft before saving
BV_DRAFT_APPROVE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Duyệt & Lưu Brand Voice",  callback_data="bv_draft_approve")],
    [InlineKeyboardButton("🔄 Viết lại từ đầu",          callback_data="bv_draft_regen")],
])

# Excel read-back — user uploaded an edited .xlsx; choose what Max does with it
XLSX_EDIT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("💾 Lưu lại (ghi đè bản cũ)",        callback_data="xlsx_save")],
    [InlineKeyboardButton("📋 Xem em đọc đúng chưa",           callback_data="xlsx_review")],
    [InlineKeyboardButton("🔄 Để Max viết lại theo bản sửa",  callback_data="xlsx_refine")],
    [InlineKeyboardButton("❌ Bỏ qua",                         callback_data="xlsx_cancel")],
])

# Sau khi strategy xong — hỏi ổn chưa hay cần điều chỉnh
CONFIRM_STRATEGY_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🟢 Content Engine — lịch brand (always-on)", callback_data="strategy_ok_run_calendar")],
    [InlineKeyboardButton("🔴 Tạo Campaign — đẩy offer theo đợt",        callback_data="strategy_confirm")],
    [InlineKeyboardButton("✏️ Cần điều chỉnh kế hoạch",                  callback_data="strategy_edit")],
    [InlineKeyboardButton("🏠 Về menu chính",                            callback_data="menu_main")],
])

# Sau khi T4-T5 (Synthesis + Tactical Playbook) xong — mô hình 2-track:
# 🟢 Content Engine (always-on, không cần campaign) HOẶC 🔴 Tạo Campaign (offer theo đợt).
CONFIRM_STRATEGY_TO_CAMPAIGN_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🟢 Content Engine — lịch brand (always-on)", callback_data="strategy_ok_run_calendar")],
    [InlineKeyboardButton("🔴 Tạo Campaign — đẩy offer theo đợt",        callback_data="strategy_confirm")],
    [InlineKeyboardButton("✏️ Cần điều chỉnh kế hoạch",                  callback_data="strategy_edit")],
    [InlineKeyboardButton("🏠 Về menu chính",                            callback_data="menu_main")],
])

# Sau khi Campaign Brief xong — XÁC NHẬN brief trước khi gen calendar
CONFIRM_BRIEF_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Duyệt — tạo Lịch Nội Dung", callback_data="brief_confirm")],
    [InlineKeyboardButton("✏️ Cần thêm/bớt gì đó",         callback_data="brief_edit")],
])

# Sau khi A→Z xong — hỏi có muốn triển khai campaign ngay không
POST_AZ_CAMPAIGN_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("💡 Tôi có ý tưởng — kể Max nghe",  callback_data="az_have_idea")],
    [InlineKeyboardButton("🔍 Max đề xuất 3 campaign options", callback_data="az_propose_campaign")],
])

# Sau khi Max đề xuất 3 options — user chọn 1 trong 3
CAMPAIGN_OPTION_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("1️⃣", callback_data="campaign_pick_1"),
        InlineKeyboardButton("2️⃣", callback_data="campaign_pick_2"),
        InlineKeyboardButton("3️⃣", callback_data="campaign_pick_3"),
    ],
    [InlineKeyboardButton("🔄 Đề xuất 3 options khác", callback_data="campaign_propose_again")],
    [InlineKeyboardButton("⏭️ Quay lại, đánh giá A→Z", callback_data="az_skip_campaign")],
])

# Sau khi refine idea của user — confirm proceed hay sửa lại
CAMPAIGN_IDEA_CONFIRM_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ OK, chọn Offer Lever",        callback_data="campaign_idea_confirm")],
    [InlineKeyboardButton("✏️ Sửa lại idea",                callback_data="campaign_idea_redo")],
    [InlineKeyboardButton("⏭️ Hủy, quay lại đánh giá",     callback_data="az_skip_campaign")],
])

# Sau khi chốt campaign → AI gen 4 offer levers → user pick 1
OFFER_LEVER_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("1️⃣", callback_data="lever_pick_0"),
        InlineKeyboardButton("2️⃣", callback_data="lever_pick_1"),
        InlineKeyboardButton("3️⃣", callback_data="lever_pick_2"),
        InlineKeyboardButton("4️⃣", callback_data="lever_pick_3"),
    ],
    [InlineKeyboardButton("🔄 Đề xuất 4 levers khác", callback_data="lever_propose_again")],
    [InlineKeyboardButton("⏭️ Hủy, quay lại đánh giá", callback_data="az_skip_campaign")],
])


# ─────────────────────────────────────────────────────────────────
# Auto monitor — interval picker
# ─────────────────────────────────────────────────────────────────

MONITOR_PROMPT_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔔 Có, theo dõi tự động",  callback_data="monitor_yes")],
    [InlineKeyboardButton("⏭️ Không cần",              callback_data="monitor_no")],
])

MONITOR_INTERVAL_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⚡ 3 giờ",   callback_data="monitor_iv_3"),
        InlineKeyboardButton("🕐 6 giờ",   callback_data="monitor_iv_6"),
    ],
    [
        InlineKeyboardButton("🕔 12 giờ",  callback_data="monitor_iv_12"),
        InlineKeyboardButton("📅 1 ngày",  callback_data="monitor_iv_24"),
    ],
    [InlineKeyboardButton("📆 1 tuần",     callback_data="monitor_iv_168")],
])

# Note: New-ads notification keyboard được build động trong worker
# (workers/monitor_competitors.py:55-60) với callback_data="monitor_diff_{page_id}"
# vì cần inject page_id. Không define keyboard tĩnh ở đây.


# ─────────────────────────────────────────────────────────────────
# Sprint 6 — Tone Calibration Loop
# ─────────────────────────────────────────────────────────────────

TONE_CHECK_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Tone đúng rồi — Lock & gen tiếp", callback_data="tone_approve")],
    [InlineKeyboardButton("✏️ Chỉnh tone (gõ feedback)",       callback_data="tone_reject")],
    [InlineKeyboardButton("⏭ Bỏ qua kiểm tra tone",           callback_data="tone_skip")],
])

TONE_REGEN_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Ổn rồi — Lock tone này",  callback_data="tone_approve")],
    [InlineKeyboardButton("🔄 Chỉnh thêm",              callback_data="tone_reject")],
    [InlineKeyboardButton("⏭ Bỏ qua, dùng bản gốc",    callback_data="tone_skip")],
])


# ─────────────────────────────────────────────────────────────────
# Sprint 7 — Per-post Action Menu (built dynamically with post_id)
# ─────────────────────────────────────────────────────────────────

def post_action_keyboard(post_id: str) -> InlineKeyboardMarkup:
    """Build per-post action keyboard. post_id = 'POST-001' etc."""
    pid = post_id.replace("POST-", "")  # '001'
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit",     callback_data=f"post_edit_{pid}"),
            InlineKeyboardButton("🔄 Adapt",    callback_data=f"post_adapt_{pid}"),
        ],
        [
            InlineKeyboardButton("✨ Variant",  callback_data=f"post_variant_{pid}"),
            InlineKeyboardButton("🗑 Delete",   callback_data=f"post_delete_{pid}"),
        ],
    ])


# ─────────────────────────────────────────────────────────────────
# USP Gate — hỏi USP sau McKinsey Gate
# ─────────────────────────────────────────────────────────────────

USP_ANALYZE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔬 Phân tích thêm — tìm USP mạnh hơn", callback_data="usp_analyze_more")],
    [InlineKeyboardButton("⚡ Dùng luôn USP này, khỏi phân tích",  callback_data="usp_use_as_is")],
])
