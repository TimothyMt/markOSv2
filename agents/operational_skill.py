"""
OperationalSkill — generic class for standard operational skills.

Standard ops skills follow same pattern: single-shot intake → fill template → output deliverable.
This generic class handles 6 of 8 ops skills via config.

Special ops skills (AdsCopySkill, VideoScriptsSkill) have custom logic — keep as subclass.
"""
from dataclasses import dataclass, field

from agents.skills import (
    AgentSkill,
    OutputFormat,
    IntakePattern,
    ContextStrategy,
    PrimaryDeliverable,
)
from storage.models import Session


@dataclass
class OperationalSkillConfig:
    """Config for one standard operational skill — drives OperationalSkill behavior."""
    name: str
    label: str

    # Prompt
    system_prompt: str
    user_msg_template: str           # Template with {placeholder} for intake fields + session data
    max_tokens: int = 4000

    # Behavior
    output_format: OutputFormat = OutputFormat.OPERATIONAL_DELIVERABLE
    context_strategy: ContextStrategy = ContextStrategy.PROFILE_PLUS_STRATEGY
    primary_deliverable: PrimaryDeliverable = PrimaryDeliverable.HTML
    enable_critic: bool = False       # Most ops skills don't need critic

    # Intake (declared in task_registry, but cached here too for skill self-containment)
    intake_fields: list[dict] = field(default_factory=list)


class OperationalSkill(AgentSkill):
    """Generic operational skill — behavior driven by OperationalSkillConfig.

    Reads context from session.profile + (optionally) session.results based on context_strategy.
    Builds user message by filling template with session.pending_intake answers.

    Used for standard ops skills:
      campaign_brief, content_calendar, sales_inbox_script,
      email_zalo_sequence

    AdsCopySkill + VideoScriptsSkill are custom subclasses (separate file) due to:
      - AdsCopy: tier batching (TOFU/MOFU/BOFU selection)
      - VideoScripts: 4 creator type variants
    """

    intake_pattern = IntakePattern.SINGLE_SHOT_FORM
    accumulate_to_report = False  # Each ops deliverable is standalone

    def __init__(self, config: OperationalSkillConfig):
        self._config = config
        # Copy config values to instance attrs (AgentSkill API)
        self.name = config.name
        self.system_prompt = config.system_prompt
        self.max_tokens = config.max_tokens
        self.output_format = config.output_format
        self.context_strategy = config.context_strategy
        self.primary_deliverable = config.primary_deliverable
        self.enable_critic = config.enable_critic

    # ─── Context builder — resolves based on context_strategy ─────

    def build_context(self, session: Session) -> str:
        """Build context string based on configured strategy."""
        from frameworks.kpi_library import get_framework_as_text

        if self.context_strategy == ContextStrategy.PROFILE_ONLY:
            return session.profile.to_context_string()

        elif self.context_strategy == ContextStrategy.FULL_PIPELINE:
            return session.build_pipeline_context()

        elif self.context_strategy == ContextStrategy.PROFILE_PLUS_STRATEGY:
            parts = [session.profile.to_context_string()]
            advisory = session.get_latest_result("advisory") or session.get_latest_result("synthesis")
            if advisory:
                parts.append(f"## Marketing Strategy (đã duyệt)\n{advisory}")
                playbook = session.get_latest_result("tactical_playbook")
                if playbook:
                    parts.append(f"## Tactical Playbook (SO/WO/WT tactics đã duyệt)\n{playbook[:5000]}")
            else:
                # Synthesis chưa có — include available sub-strategic results so ops
                # skills aren't flying blind (enriches context without re-asking user)
                for key, label in [
                    ("market_research",  "Market Research"),
                    ("competitor",       "Competitor Analysis"),
                    ("customer_insight", "Customer Insights"),
                    ("psychology_pricing", "Psychology & Pricing"),
                ]:
                    result = session.get_latest_result(key)
                    if result:
                        parts.append(f"## {label}\n{result[:3000]}")
            return "\n\n---\n\n".join(parts)

        elif self.context_strategy == ContextStrategy.PROFILE_PLUS_CAMPAIGN:
            parts = [session.profile.to_context_string()]
            advisory = session.get_latest_result("advisory") or session.get_latest_result("synthesis")
            if advisory:
                parts.append(f"## Marketing Strategy nền\n{advisory}")
            playbook = session.get_latest_result("tactical_playbook")
            if playbook:
                parts.append(f"## Tactical Playbook (SO/WO/WT tactics)\n{playbook[:5000]}")
            campaign_brief = session.get_latest_result("campaign_brief")
            if campaign_brief:
                parts.append(f"## Campaign Brief hiện tại\n{campaign_brief}")
            return "\n\n---\n\n".join(parts)

        elif self.context_strategy == ContextStrategy.PROFILE_PLUS_KPI:
            parts = [session.profile.to_context_string()]
            if session.profile.industry:
                kpi_text = get_framework_as_text(session.profile.industry)
                parts.append(kpi_text)
            return "\n\n---\n\n".join(parts)

        # Fallback
        return session.profile.to_context_string()

    # ─── User message builder — fills template ────────────────────

    def build_user_msg(self, session: Session) -> str:
        """Fill user_msg_template with intake answers + safe defaults."""
        # Pending intake answers (from single-shot form)
        intake = dict(session.pending_intake or {})

        # Sprint 2: nếu có user_correction từ regen flow → append vào msg
        user_correction = intake.pop("_user_correction", None)
        # FB live data (competitor spy / performance audit) — injected by handlers
        fb_data = intake.pop("_fb_data", None)
        # Workflow context — injected by workflow_runner (brand_direction from Linh)
        workflow_context = intake.pop("_workflow_context", None)
        # Remove all internal markers (start with _) before formatting
        intake = {k: v for k, v in intake.items() if not k.startswith("_")}

        # Common profile fallbacks accessible in template
        profile = session.profile
        intake.setdefault("industry",         profile.industry or "chưa xác định")
        intake.setdefault("business_name",    profile.business_name or "business của bạn")
        intake.setdefault("product_service",  profile.product_service or "chưa xác định")
        intake.setdefault("target_customer",  profile.target_customer or "chưa xác định")
        intake.setdefault("location",         profile.location or "Việt Nam")
        intake.setdefault("monthly_revenue",  profile.monthly_revenue or "chưa rõ")
        intake.setdefault("primary_goal",     profile.primary_goal or "tăng doanh thu")
        intake.setdefault("main_challenge",   profile.main_challenge or "chưa xác định")

        # Use SafeDict — return "(không có thông tin)" for any missing placeholder
        # instead of raising KeyError. Handles both strategy_aware form (subset of fields)
        # and template missing fields gracefully.
        class _SafeIntake(dict):
            def __missing__(self, key):
                return "(không có thông tin)"

        try:
            msg = self._config.user_msg_template.format_map(_SafeIntake(intake))
        except Exception:
            # Last-resort fallback — strip all placeholders
            import re as _re
            msg = _re.sub(r"\{[^{}]+\}", "(không có thông tin)", self._config.user_msg_template)

        # Append FB live data nếu có (competitor spy / performance audit)
        if fb_data:
            msg += (
                "\n\n---\n\n"
                "**LIVE DATA TỪ FACEBOOK API (đã tự động fetch — ưu tiên phân tích data thực này):**\n\n"
                f"{fb_data}"
            )

        # Inject Brand Direction từ workflow (Linh → Nam pipeline)
        if workflow_context:
            msg += (
                "\n\n---\n\n"
                "**BRAND DIRECTION ĐÃ XÁC NHẬN (từ bước phân tích brand trước):**\n"
                f"{workflow_context}"
            )

        # Inject Strategy context nếu có (Brief Campaign / Content Calendar / Landing Page reuse)
        synthesis = session.get_latest_result("synthesis") or session.get_latest_result("strategy")
        if synthesis:
            msg += (
                "\n\n---\n\n"
                "**MARKETING STRATEGY ĐÃ CÓ TỪ TRƯỚC (dùng làm base, đừng yêu cầu user cung cấp lại):**\n\n"
                f"{synthesis[:6000]}"
            )

        # Inject Tactical Playbook (T5) — kênh/copy/tham số deliverable phải bám tactics này
        playbook = session.get_latest_result("tactical_playbook")
        if playbook:
            msg += (
                "\n\n---\n\n"
                "**TACTICAL PLAYBOOK ĐÃ CÓ (SO/WO/WT tactics per-segment — kênh, copy mẫu, "
                "tham số trong deliverable phải nhất quán với playbook này):**\n\n"
                f"{playbook[:5000]}"
            )

        # Sprint 4: Inject Campaign Scope Library cho campaign_brief
        if self._config.name == "campaign_brief" and session.profile.industry:
            try:
                from agents.campaign_scope_library import format_scope_for_prompt
                scope_block = format_scope_for_prompt(session.profile.industry)
                msg += f"\n\n---\n\n{scope_block}"
            except Exception:
                pass  # Graceful — scope library optional

        # Inject Calendar context nếu skill cần (Content Generator)
        calendar = session.get_latest_result("content_calendar")
        if calendar and self._config.name in ("content_generator",):
            msg += (
                "\n\n---\n\n"
                "**CONTENT CALENDAR ĐÃ CÓ (dựa vào lịch này để gen content, đừng hỏi user):**\n\n"
                f"{calendar[:6000]}"
            )

        # Layer 3: chạy từng kênh 1 — chỉ sản xuất cho kênh đang chọn
        channel_focus = (session.pending_intake.get("channel_focus") or "").strip()
        if channel_focus and self._config.name in ("post_batch", "video_script_gen", "ugc_brief"):
            msg += (
                "\n\n---\n\n"
                f"**🔴 KÊNH ĐANG SẢN XUẤT: {channel_focus}**\n"
                f"CHỈ sản xuất content cho kênh **{channel_focus}** trong scope đã chọn — "
                "BỎ QUA slot của các kênh khác trong Calendar. "
                f"Nếu Calendar không có slot nào cho kênh **{channel_focus}** trong scope này, "
                "nói rõ điều đó (KHÔNG tự bịa thêm slot)."
            )

        # Universal directive — bot KHÔNG được hỏi user trong output
        msg += (
            "\n\n---\n\n"
            "**QUY TẮC TUYỆT ĐỐI VỀ OUTPUT:**\n"
            "- KHÔNG được hỏi user 'em cần thêm thông tin' / 'sếp cho em biết...'\n"
            "- KHÔNG được output bảng 'thiếu input' hay '5 câu hỏi trả lời nhanh'\n"
            "- Nếu thiếu chi tiết → DÙNG DEFAULT hợp lý dựa trên context business profile / strategy\n"
            "- Output PHẢI là deliverable thực sự dùng được, không phải báo cáo về việc thiếu input\n"
        )

        # Append user correction nếu đang regen (Sprint 2)
        if user_correction:
            msg += (
                "\n\n---\n\n"
                "**USER CORRECTION (sếp đã feedback ở lần chạy trước, hãy fix theo):**\n"
                f"{user_correction}\n\n"
                "Apply correction này vào output mới. Giữ nguyên các phần khác."
            )
        return msg

    # ─── Intake helpers ───────────────────────────────────────────

    def get_intake_fields(self) -> list[dict]:
        """Return declared intake fields (for single-shot form template)."""
        return list(self._config.intake_fields)

    def missing_intake_fields(self, session: Session) -> list[dict]:
        """Return only fields that need to be asked (not in session.pending_intake)."""
        provided = set((session.pending_intake or {}).keys())
        return [f for f in self._config.intake_fields if f.get("key") not in provided]
