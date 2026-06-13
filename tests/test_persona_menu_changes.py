"""
Regression tests cho việc chỉnh menu persona:
- Bỏ Mai khỏi main menu, bỏ performance_audit khỏi Khoa
- Nam mode "viết bài mới" → post_write với 4 field (topic/channel/post_goal/tone_angle), KHÔNG có TikTok
- Khoa skills có field channel_focus (prefill từ nút chooser)
- Các keyboard mới tồn tại + callback_data đúng

Chạy offline, không gọi API.
"""
from bot import keyboards as kb
from agents.task_registry import get_task
from agents.manager_personas import get_persona


def _all_callbacks(markup):
    return [btn.callback_data for row in markup.inline_keyboard for btn in row]


# ── Main menu ─────────────────────────────────────────────────────
def test_main_menu_no_mai():
    cbs = _all_callbacks(kb.MAIN_MENU_KEYBOARD)
    assert "persona_menu_crm" not in cbs, "Mai (CRM) vẫn còn trong main menu"
    # Các persona còn lại vẫn có
    for expected in ("persona_menu_cmo", "persona_menu_brand",
                     "persona_menu_content", "persona_menu_tiktok",
                     "persona_menu_growth"):
        assert expected in cbs, f"Thiếu {expected} trong main menu"


# ── Khoa (growth) ─────────────────────────────────────────────────
def test_growth_drops_performance_audit():
    skills = get_persona("growth").owns_skills
    assert "performance_audit" not in skills
    assert skills == ["retention_strategy", "winback_campaign"]


def test_growth_skills_have_channel_focus():
    for name in ("retention_strategy", "winback_campaign"):
        keys = [f["key"] for f in get_task(name).intake_fields]
        assert "channel_focus" in keys, f"{name} thiếu channel_focus"


def test_growth_channel_keyboard():
    cbs = _all_callbacks(kb.GROWTH_CHANNEL_KEYBOARD)
    assert set(cbs) == {"growth_ch_all", "growth_ch_zalo",
                        "growth_ch_email", "growth_ch_sms"}


# ── Nam (content) ─────────────────────────────────────────────────
def test_post_write_fresh_fields_no_tiktok():
    pw = get_task("post_write")
    keys = [f["key"] for f in pw.intake_fields]
    assert keys == ["topic", "channel", "post_goal", "tone_angle"]
    # Channel example không được gợi ý TikTok (đó là domain của Trang)
    channel_field = next(f for f in pw.intake_fields if f["key"] == "channel")
    assert "TikTok" not in channel_field["example"]
    assert "tone_angle" == pw.intake_fields[-1]["key"]
    assert pw.intake_fields[-1]["required"] is False  # tone optional


def test_nam_mode_keyboard():
    cbs = _all_callbacks(kb.NAM_MODE_KEYBOARD)
    assert "nam_mode_calendar" in cbs
    assert "nam_mode_fresh" in cbs


# ── Trang (tiktok) ────────────────────────────────────────────────
def test_trang_mode_keyboard():
    cbs = _all_callbacks(kb.TRANG_MODE_KEYBOARD)
    assert "trang_mode_calendar" in cbs
    assert "trang_mode_fresh" in cbs


def test_video_scripts_content_first():
    """Trang 'kịch bản mới' tập trung nội dung/type, KHÔNG ép creator type."""
    vs = get_task("video_scripts")
    keys = [f["key"] for f in vs.intake_fields]
    assert keys == ["topic", "key_message", "content_type", "highlight"]
    # content_type (loại nội dung) là trục chính, bắt buộc
    ct = next(f for f in vs.intake_fields if f["key"] == "content_type")
    assert ct["required"] is True
    # KHÔNG còn hỏi creator type / funnel / duration trong form
    assert "creator_type" not in keys
    assert "funnel" not in keys


def test_video_scripts_msg_type_drives_format():
    """build_user_msg: loại nội dung quyết định format; creator type optional."""
    from agents.operational_skills_config import VideoScriptsSkill

    class _P:
        industry = "Mỹ phẩm"
        target_customer = "Nữ 25-35"
        def to_context_string(self): return ""

    class _S:
        profile = _P()
        pending_intake = {
            "topic": "Kem chống nắng",
            "key_message": "Da dầu vẫn phải chống nắng",
            "content_type": "Educate",
        }
        def get_latest_result(self, k): return None

    msg = VideoScriptsSkill().build_user_msg(_S())
    assert "Da dầu vẫn phải chống nắng" in msg     # thông điệp là gốc
    assert "EDUCATE" in msg                          # type → format guidance
    assert "tự chọn người xuất hiện" in msg          # creator không ép


# ── Gợi ý thông điệp chính (Business + KPI ngành) ─────────────────
def test_key_message_hint_uses_business_and_industry():
    """suggest_key_message_hint neo vào product của user + tâm lý ngành."""
    from frameworks.industry_context import suggest_key_message_hint

    hint = suggest_key_message_hint(
        "health_beauty",
        product_service="Combo trị mụn 30 ngày",
        target_customer="Nữ 18-25 da dầu mụn",
    )
    assert hint, "Ngành đã định nghĩa phải có gợi ý"
    # Gắn sản phẩm cụ thể của business
    assert "Combo trị mụn 30 ngày" in hint
    # Neo vào tâm lý ngành: lý do mua + nỗi lo (buyer trigger/barrier)
    assert "khách muốn nhất" in hint
    assert "Nỗi lo cần gỡ" in hint
    # Viết cho đúng tệp khách
    assert "Nữ 18-25 da dầu mụn" in hint


def test_key_message_hint_unknown_industry_empty():
    """Ngành chưa định nghĩa → rỗng để form fallback về example tĩnh."""
    from frameworks.industry_context import suggest_key_message_hint

    assert suggest_key_message_hint("ngành_không_tồn_tại", "X", "Y") == ""


# ── Linh (brand voice) ────────────────────────────────────────────
def test_linh_keyboards():
    exists = _all_callbacks(kb.LINH_BV_EXISTS_KEYBOARD)
    assert "bv_edit_chat" in exists
    assert "bv_view" in exists
    new = _all_callbacks(kb.LINH_BV_NEW_KEYBOARD)
    assert "bv_create" in new


# ── Excel read-back ───────────────────────────────────────────────
def test_xlsx_filename_detection():
    from bot.excel_reader import detect_skill_from_filename
    assert detect_skill_from_filename("content_calendar_ShopABC.xlsx") == "content_calendar"
    # Longest-prefix match: không nhầm video_script_gen với 'video'
    assert detect_skill_from_filename("video_script_gen_X.xlsx") == "video_script_gen"
    # Tên file không khớp skill nào → None
    assert detect_skill_from_filename("my_random_export.xlsx") is None
    assert detect_skill_from_filename("") is None


def test_xlsx_reader_roundtrip():
    from openpyxl import Workbook
    import io
    from bot.excel_reader import read_xlsx_to_markdown

    wb = Workbook()
    ws = wb.active
    ws.append(["Tuần", "Topic", "Kênh"])
    ws.append([1, "Trị mụn", "FB"])
    buf = io.BytesIO()
    wb.save(buf)
    md = read_xlsx_to_markdown(buf.getvalue())
    assert "Topic" in md
    assert "Trị mụn" in md
    assert md.count("|") >= 6  # có pipe table


def test_xlsx_edit_keyboard():
    cbs = _all_callbacks(kb.XLSX_EDIT_KEYBOARD)
    assert "xlsx_save" in cbs
    assert "xlsx_review" in cbs
    assert "xlsx_refine" in cbs
    assert "xlsx_cancel" in cbs


# ── Brand Voice markdown sync (chat-edit) ─────────────────────────
def test_bv_do_dont_parsers():
    from bot.handlers import _extract_do_rules_from_md, _extract_dont_rules_from_md
    md = (
        "### 1. 10 quy tắc giọng văn\n"
        "1. Luôn xưng \"em\" với khách\n"
        "2. Câu max 18 từ\n\n"
        "### 2. 10 từ NÊN TRÁNH\n"
        "| # | Từ/cụm tránh | Lý do | Vd |\n"
        "|---|---|---|---|\n"
        "| 1 | Sản phẩm chúng tôi | Generic | Bộ Glow |\n"
    )
    do = _extract_do_rules_from_md(md)
    dont = _extract_dont_rules_from_md(md)
    assert len(do) == 2 and "xưng" in do[0]
    assert len(dont) == 1 and "Sản phẩm chúng tôi" in dont[0]
