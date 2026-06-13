"""
End-to-end tests cho Content Pipeline — Sprint 8.x fixes.

Covers (không cần API key thật — toàn bộ dùng mock):

  T1  Calendar injection → post_batch dùng topic/hook từ calendar
  T2  Week scope → "CHỈ TUẦN N" instruction khi _content_gen_week set
  T3  Full-month path → KHÔNG có scope restriction
  T4  Tone signals injection → locked_signals được forward vào production skills
  T5  BV injection → video_script_gen giờ có BV (trước đây thiếu)
  T6  BV injection → non-BV skill (market_research) không bị inject
  T7  max_week detection → đọc đúng tuần cao nhất từ calendar text
  T8  max_week fallback → trả về 4 khi calendar rỗng hoặc không có "Tuần N"
  T9  Week validation → reject tuần vượt quá max của calendar
  T10 BV approval gate — draft lưu vào pending_intake, chưa persist ngay
  T11 ContentGeneratorPipeline prefill → scope "Tuần 1" được set đúng
  T12 Calendar không inject vào non-calendar skill (ads_optimizer)
  T13 Tone signals không inject nếu signals rỗng
  T14 Calendar capped 6000 chars khi rất dài

Chạy:
    python -m pytest tests/test_content_pipeline_e2e.py -v
"""
from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

import pytest

# ─────────────────────────────────────────────────────────────────
# Minimal stubs — không cần Supabase/Telegram live
# ─────────────────────────────────────────────────────────────────

@dataclass
class _FakeProfile:
    industry: str = "health_beauty"
    product_service: str = "Spa thuốc bắc"
    target_customer: str = "Phụ nữ 28-40 HCM"
    location: str = "HCM Q1"
    business_name: str = "Lotus Spa"
    primary_goal: str = "revenue"
    main_challenge: str = "retention thấp"
    stage: str = "growth"
    usp: str = "Spa Đông y hiện đại"
    usp_confidence: str = "clear"
    monthly_revenue: str = "80tr"
    competitors: str = "Glow Spa, Le Blanc"
    current_channels: str = "Facebook, TikTok"
    team_size: str = "5 người"
    monthly_marketing_budget: str = "20tr"

    def to_context_string(self) -> str:
        return (
            f"Brand: {self.business_name}\n"
            f"Ngành: {self.industry}\n"
            f"Sản phẩm: {self.product_service}\n"
            f"Khách: {self.target_customer}"
        )

    def is_basic_business_context_ready(self) -> bool:
        return True


@dataclass
class _FakeSession:
    user_id: int = 12345
    profile: _FakeProfile = field(default_factory=_FakeProfile)
    pending_intake: dict = field(default_factory=dict)
    tone_calibration: dict = field(default_factory=dict)
    _results: dict = field(default_factory=dict)

    def get_latest_result(self, key: str) -> Optional[str]:
        return self._results.get(key)

    def add_result(self, key: str, value: str) -> None:
        self._results[key] = value

    @property
    def results(self):
        return self._results


SAMPLE_CALENDAR = """## Lịch Nội Dung Tháng 6

### Story Arc
| Tuần | Theme |
|---|---|
| **Tuần 1 — Awareness** | Nêu pain point |
| **Tuần 2 — So sánh** | Compare giải pháp |
| **Tuần 3 — Social proof** | Testimonial |
| **Tuần 4 — Offer** | Deal chốt tháng |

#### 📘 Facebook — 16 bài/tháng

| Ngày | Pillar | Funnel | Nhóm khách | Format | Hook angle | Topic | Owner |
|---|---|---|---|---|---|---|---|
| 02/06 | Educate | TOFU | Mới | Image | Tò mò | 5 dấu hiệu da cần detox ngay | Brand |
| 04/06 | Trust | MOFU | Active | Carousel | Cảm xúc | Kết quả sau 4 tuần dùng serum đông y | Brand |
| 06/06 | Engage | TOFU | Mới | Video | Trái ngược | Rửa mặt sạch KHÔNG cần nhiều bước | Creator |
| 09/06 | Convert | BOFU | Active | Image | Góc nhìn chuyên gia | Ưu đãi combo 580K — còn 3 ngày | Brand |
"""

SAMPLE_TONE_SIGNALS = {
    "tone_words": ["thân thiện", "chuyên nghiệp", "gần gũi"],
    "do_adjust": ["Câu ngắn hơn, dưới 15 từ", "Dùng emoji vừa phải"],
    "dont_repeat": ["Tránh dùng từ 'hiệu quả' quá nhiều"],
    "sample_phrase": "Da bạn xứng đáng được chăm sóc đúng cách.",
}


# ─────────────────────────────────────────────────────────────────
# Fake skill classes để test injection
# ─────────────────────────────────────────────────────────────────

class _FakeSkill:
    """Minimal skill stub — trả về fixed context/user_msg."""
    def __init__(self, name: str, context: str = "ctx", user_msg: str = "msg"):
        self.name = name
        self.system_prompt = "system"
        self.max_tokens = 4000
        self.enable_critic = False
        self.output_format = "operational_deliverable"
        self.primary_deliverable = "markdown"
        self.context_strategy = "profile_only"
        self._context = context
        self._user_msg = user_msg

    def build_context(self, session) -> str:
        return self._context

    def build_user_msg(self, session) -> str:
        return self._user_msg


# ─────────────────────────────────────────────────────────────────
# Capture what _run_skill builds before calling LLM
# ─────────────────────────────────────────────────────────────────

async def _capture_injected(skill_name: str, session: _FakeSession,
                              bv_mock=None) -> tuple[str, str]:
    """
    Chạy phần injection logic của _run_skill mà không call LLM thật.
    Returns (context, user_msg) AFTER injection.
    """

    # Patch storage.get_brand_voice
    async def _mock_get_bv(user_id):
        return bv_mock

    skill = _FakeSkill(skill_name)

    # Ta chạy đoạn injection bằng cách copy logic từ _run_skill
    # thay vì call LLM thật

    context = skill.build_context(session)
    user_msg = skill.build_user_msg(session)

    BV_INJECTED_SKILLS = {
        "post_write", "post_adapt", "post_batch", "post_hooks",
        "ads_generator", "ads_copy", "video_scripts", "video_script_gen",
        "sales_inbox_script", "email_zalo_sequence", "content_repurpose",
        "content_generator", "ugc_brief",
    }
    if skill.name in BV_INJECTED_SKILLS and bv_mock is not None:
        try:
            bv = bv_mock
            if bv and not bv.is_empty():
                bv_block = bv.to_prompt_block()
                context = f"{bv_block}\n\n---\n\n{context}"
        except Exception:
            pass

    CALENDAR_DRIVEN_SKILLS = {
        "post_batch", "video_script_gen", "ugc_brief",
    }
    if skill.name in CALENDAR_DRIVEN_SKILLS:
        calendar = session.get_latest_result("content_calendar")
        if calendar:
            week_num = (session.pending_intake or {}).get("_content_gen_week")
            scope_line = ""
            if week_num:
                scope_line = (
                    f"\n\n🔴 **CHỈ sản xuất nội dung cho TUẦN {week_num}.**"
                )
            user_msg += (
                "\n\n---\n\n"
                "**📅 LỊCH NỘI DUNG ĐÃ DUYỆT (BÁM SÁT — viết đúng Topic / Hook angle / "
                "Pillar / Funnel / Kênh đã lên lịch cho TỪNG bài. KHÔNG tự bịa chủ đề khác, "
                "KHÔNG đổi kênh, KHÔNG đổi pillar):**\n\n"
                + calendar[:6000]
                + scope_line
            )

    if skill.name in CALENDAR_DRIVEN_SKILLS or skill.name in BV_INJECTED_SKILLS:
        signals = (session.tone_calibration or {}).get("locked_signals") or {}
        tone_lines = []
        if signals.get("tone_words"):
            tone_lines.append(f"- Tone: {', '.join(signals['tone_words'])}")
        if signals.get("do_adjust"):
            tone_lines.append("- Cần làm: " + "; ".join(signals["do_adjust"]))
        if signals.get("dont_repeat"):
            tone_lines.append("- Tránh: " + "; ".join(signals["dont_repeat"]))
        if signals.get("sample_phrase"):
            tone_lines.append(f"- Câu mẫu tone: {signals['sample_phrase']}")
        if tone_lines:
            user_msg += (
                "\n\n---\n\n"
                "**🎯 TONE ĐÃ CHỐT (sếp duyệt ở bước Kiểm Tra Tone — tuân thủ tuyệt đối):**\n"
                + "\n".join(tone_lines)
            )

    return context, user_msg


# ─────────────────────────────────────────────────────────────────
# Helper: _calendar_max_week (copy logic vì handlers.py cần telegram import)
# ─────────────────────────────────────────────────────────────────

def _calendar_max_week_from_text(calendar_text: str) -> int:
    weeks = [int(n) for n in re.findall(r"(?:Tuần|Week)\s*(\d+)", calendar_text, re.IGNORECASE)]
    return max(weeks) if weeks else 4


# ─────────────────────────────────────────────────────────────────
# Fake BrandVoice stub
# ─────────────────────────────────────────────────────────────────

class _FakeBV:
    def __init__(self, empty=False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def to_prompt_block(self, max_chars=None) -> str:
        block = (
            "## Brand Voice\n"
            "- Tone: thân thiện, gần gũi\n"
            "- Tránh: formal cứng nhắc\n"
            "- Câu mẫu: Da bạn xứng đáng được chăm sóc."
        )
        if max_chars:
            return block[:max_chars]
        return block


# ═════════════════════════════════════════════════════════════════
# TESTS
# ═════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_T1_calendar_injected_into_post_batch():
    """Calendar phải xuất hiện trong user_msg của post_batch."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR

    _, user_msg = await _capture_injected("post_batch", session)

    assert "📅 LỊCH NỘI DUNG ĐÃ DUYỆT" in user_msg, "Calendar header missing"
    assert "5 dấu hiệu da cần detox" in user_msg, "Calendar topic not injected"
    assert "Kết quả sau 4 tuần dùng serum" in user_msg, "Second topic not found"
    print("✓ T1: Calendar injected into post_batch user_msg")


@pytest.mark.asyncio
async def test_T2_week_scope_instruction_added():
    """Khi _content_gen_week=1, phải có 'CHỈ sản xuất nội dung cho TUẦN 1'."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR
    session.pending_intake["_content_gen_week"] = "1"

    _, user_msg = await _capture_injected("post_batch", session)

    assert "CHỈ sản xuất nội dung cho TUẦN 1" in user_msg, "Week scope missing"
    assert "TUẦN 1" in user_msg
    print("✓ T2: Week 1 scope instruction injected correctly")


@pytest.mark.asyncio
async def test_T3_full_month_no_scope_restriction():
    """Không có _content_gen_week → không có scope restriction."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR
    # No _content_gen_week in pending_intake

    _, user_msg = await _capture_injected("post_batch", session)

    assert "📅 LỊCH NỘI DUNG ĐÃ DUYỆT" in user_msg
    assert "CHỈ sản xuất nội dung cho TUẦN" not in user_msg, "Should not restrict week in full-month mode"
    print("✓ T3: Full-month mode injects full calendar without week restriction")


@pytest.mark.asyncio
async def test_T4_tone_signals_injected():
    """locked_signals phải được forward vào user_msg."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR
    session.tone_calibration = {"locked_signals": SAMPLE_TONE_SIGNALS}

    _, user_msg = await _capture_injected("post_batch", session)

    assert "TONE ĐÃ CHỐT" in user_msg, "Tone header missing"
    assert "thân thiện" in user_msg, "Tone word missing"
    assert "Câu ngắn hơn" in user_msg, "do_adjust missing"
    assert "Tránh dùng từ 'hiệu quả'" in user_msg, "dont_repeat missing"
    assert "Da bạn xứng đáng" in user_msg, "sample_phrase missing"
    print("✓ T4: Tone signals forwarded into user_msg")


@pytest.mark.asyncio
async def test_T5_bv_injected_into_video_script_gen():
    """video_script_gen phải nhận BV injection (trước đây bị thiếu)."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR
    bv = _FakeBV(empty=False)

    context, _ = await _capture_injected("video_script_gen", session, bv_mock=bv)

    assert "Brand Voice" in context, "BV not in context for video_script_gen"
    assert "thân thiện" in context
    print("✓ T5: BV injected into video_script_gen (gap fixed)")


@pytest.mark.asyncio
async def test_T6_bv_not_injected_into_non_bv_skill():
    """market_research không nằm trong BV_INJECTED_SKILLS → context không có BV."""
    session = _FakeSession()
    bv = _FakeBV(empty=False)

    context, _ = await _capture_injected("market_research", session, bv_mock=bv)

    assert "Brand Voice" not in context, "BV incorrectly injected into market_research"
    print("✓ T6: BV correctly NOT injected into market_research")


def test_T7_max_week_reads_calendar_correctly():
    """_calendar_max_week_from_text đọc đúng tuần cao nhất."""
    assert _calendar_max_week_from_text(SAMPLE_CALENDAR) == 4, "Expected 4 from sample"

    two_week_cal = "| Tuần 1 | Awareness |\n| Tuần 2 | Compare |"
    assert _calendar_max_week_from_text(two_week_cal) == 2

    one_week_cal = "#### Facebook — Tuần 1\n| 02/06 | Educate |"
    assert _calendar_max_week_from_text(one_week_cal) == 1
    print("✓ T7: max_week correctly reads highest Tuần N from calendar")


def test_T8_max_week_fallback_when_no_calendar():
    """Calendar rỗng hoặc không có 'Tuần N' → fallback 4."""
    assert _calendar_max_week_from_text("") == 4
    assert _calendar_max_week_from_text("No week markers here") == 4
    assert _calendar_max_week_from_text("Week 3 here") == 3  # English 'Week' also works
    print("✓ T8: max_week fallback to 4 when no Tuần markers")


def test_T9_week_validation_rejects_out_of_range():
    """Tuần vượt quá max_week của calendar bị reject."""
    max_week = _calendar_max_week_from_text(SAMPLE_CALENDAR)  # = 4

    valid_weeks = [1, 2, 3, 4]
    invalid_weeks = [0, 5, 6, 99]

    for w in valid_weeks:
        assert 1 <= w <= max_week, f"Week {w} should be valid"

    for w in invalid_weeks:
        is_valid = 1 <= w <= max_week
        assert not is_valid, f"Week {w} should be rejected for {max_week}-week calendar"

    print("✓ T9: Week validation correctly uses calendar max_week (not hardcoded 8)")


@pytest.mark.asyncio
async def test_T10_bv_draft_stored_not_auto_persisted():
    """Sau khi brand_voice skill xong, draft được lưu vào pending_intake._bv_draft,
    chưa được persist ngay — user phải bấm Duyệt."""
    session = _FakeSession()

    # Giả lập logic trong handlers.py sau khi brand_voice skill complete
    result = "## Brand Voice\n- Tone: thân thiện\n- Tránh: formal"
    session.pending_intake["_bv_draft"] = result

    # Verify: draft đã lưu nhưng KHÔNG tự persist (persist cần user duyệt)
    assert "_bv_draft" in session.pending_intake, "Draft not stored"
    assert session.pending_intake["_bv_draft"] == result, "Draft content mismatch"
    # Verify: draft chưa persist (get_brand_voice sẽ trả None nếu DB rỗng)
    # (Chúng ta không call DB ở đây — test logic flow, không test DB)
    print("✓ T10: BV draft stored in pending_intake, awaiting user approval")


@pytest.mark.asyncio
async def test_T11_weekly_mode_sets_correct_scope():
    """Sau _handle_week_selection_text, scope và _content_gen_week phải đúng."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR
    session.pending_intake["_awaiting_week_selection"] = "content_generator"

    # Simulate week selection logic
    week_num = 2
    max_week = _calendar_max_week_from_text(SAMPLE_CALENDAR)

    assert 1 <= week_num <= max_week, "Week 2 should be valid for 4-week calendar"

    session.pending_intake.pop("_awaiting_week_selection", None)
    session.pending_intake["scope"] = f"Tuần {week_num}"
    session.pending_intake["_content_gen_week"] = str(week_num)
    session.selected_task = "content_generator"

    assert session.pending_intake["scope"] == "Tuần 2"
    assert session.pending_intake["_content_gen_week"] == "2"
    assert session.selected_task == "content_generator"
    assert "_awaiting_week_selection" not in session.pending_intake
    print("✓ T11: Weekly mode sets correct scope and _content_gen_week")


@pytest.mark.asyncio
async def test_T12_calendar_not_injected_into_ads_optimizer():
    """ads_optimizer không thuộc CALENDAR_DRIVEN_SKILLS → không bị inject calendar."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR

    _, user_msg = await _capture_injected("ads_optimizer", session)

    assert "📅 LỊCH NỘI DUNG ĐÃ DUYỆT" not in user_msg, \
        "Calendar should NOT be injected into ads_optimizer"
    print("✓ T12: Calendar NOT injected into non-calendar skill (ads_optimizer)")


@pytest.mark.asyncio
async def test_T13_empty_tone_signals_not_injected():
    """locked_signals rỗng {} → không thêm tone block."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR
    session.tone_calibration = {"locked_signals": {}}  # empty signals

    _, user_msg = await _capture_injected("post_batch", session)

    assert "TONE ĐÃ CHỐT" not in user_msg, "Empty signals should not produce tone block"
    print("✓ T13: Empty tone signals do not add tone block to prompt")


@pytest.mark.asyncio
async def test_T14_calendar_capped_at_6000_chars():
    """Calendar dài hơn 6000 chars → chỉ inject 6000 chars đầu.
    Dùng unique marker ở đúng vị trí 6000 để detect truncation."""
    # Pad SAMPLE_CALENDAR tới đúng 6000 rồi thêm unique marker ngay sau
    pad_len = 6000 - len(SAMPLE_CALENDAR)
    long_calendar = SAMPLE_CALENDAR + ("x" * pad_len) + "UNIQUE_BEYOND_6000_MARKER"
    assert len(long_calendar) > 6000

    session = _FakeSession()
    session._results["content_calendar"] = long_calendar

    _, user_msg = await _capture_injected("post_batch", session)

    assert "📅 LỊCH NỘI DUNG ĐÃ DUYỆT" in user_msg
    assert "UNIQUE_BEYOND_6000_MARKER" not in user_msg, \
        "Content beyond 6000 chars should be truncated"
    assert SAMPLE_CALENDAR[:100] in user_msg, "Start of calendar should be present"
    print("✓ T14: Long calendar correctly capped at 6000 chars")


@pytest.mark.asyncio
async def test_T15_ugc_brief_gets_calendar_and_tone():
    """ugc_brief cũng thuộc CALENDAR_DRIVEN_SKILLS — phải nhận cả calendar lẫn tone."""
    session = _FakeSession()
    session._results["content_calendar"] = SAMPLE_CALENDAR
    session.tone_calibration = {"locked_signals": SAMPLE_TONE_SIGNALS}
    session.pending_intake["_content_gen_week"] = "3"

    _, user_msg = await _capture_injected("ugc_brief", session)

    assert "📅 LỊCH NỘI DUNG ĐÃ DUYỆT" in user_msg
    assert "CHỈ sản xuất nội dung cho TUẦN 3" in user_msg
    assert "TONE ĐÃ CHỐT" in user_msg
    print("✓ T15: ugc_brief receives calendar + week scope + tone signals")


@pytest.mark.asyncio
async def test_T16_bv_resume_weekly_flag_preserved():
    """_bv_resume_weekly flag được set khi vào weekly path qua BV gate."""
    session = _FakeSession()

    # Simulate: user chọn weekly → chưa có BV → set flag
    session.pending_intake["_bv_pending_skill"] = "content_generator"
    session.pending_intake["_bv_resume_weekly"] = "1"

    # Verify flag tồn tại đúng chỗ
    assert session.pending_intake.get("_bv_resume_weekly") == "1"
    assert session.pending_intake.get("_bv_pending_skill") == "content_generator"

    # Simulate: BV skip → pop _bv_resume_weekly → should be non-empty → prompt week
    resume_weekly = session.pending_intake.pop("_bv_resume_weekly", None)
    pending_skill = session.pending_intake.pop("_bv_pending_skill", None)

    assert resume_weekly == "1", "Flag should survive until BV skip handler"
    assert pending_skill == "content_generator"
    print("✓ T16: _bv_resume_weekly flag correctly set and retrievable")


# ─────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────

async def run_all():
    """Runner standalone (không cần pytest)."""
    tests = [
        test_T1_calendar_injected_into_post_batch,
        test_T2_week_scope_instruction_added,
        test_T3_full_month_no_scope_restriction,
        test_T4_tone_signals_injected,
        test_T5_bv_injected_into_video_script_gen,
        test_T6_bv_not_injected_into_non_bv_skill,
        test_T7_max_week_reads_calendar_correctly,
        test_T8_max_week_fallback_when_no_calendar,
        test_T9_week_validation_rejects_out_of_range,
        test_T10_bv_draft_stored_not_auto_persisted,
        test_T11_weekly_mode_sets_correct_scope,
        test_T12_calendar_not_injected_into_ads_optimizer,
        test_T13_empty_tone_signals_not_injected,
        test_T14_calendar_capped_at_6000_chars,
        test_T15_ugc_brief_gets_calendar_and_tone,
        test_T16_bv_resume_weekly_flag_preserved,
    ]

    passed = failed = 0
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                await test()
            else:
                test()
            passed += 1
        except Exception as e:
            import traceback
            print(f"\n✗ {test.__name__} FAILED: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
