"""
Skill modularity: AgentSkill base class + concrete subclasses for each pipeline agent.

LƯU Ý KHI THÊM/SỬA SKILL MỚI:
1. GIỮ NGUYÊN system_prompt từ prompts.py — không cleanup wording
2. GIỮ NGUYÊN context_builder per-agent (vd: synthesis cần SAVE+SMART injection riêng)
3. GIỮ NGUYÊN max_tokens custom — không 1-size-fits-all
4. Test before/after: chạy cùng input qua skill class và verify output ~ identical
"""
from abc import ABC, abstractmethod
from enum import Enum
from storage.models import Session
from agents.prompts import (
    MARKET_RESEARCH_SYSTEM,
    COMPETITOR_SYSTEM,
    CUSTOMER_INSIGHT_SYSTEM,
    MARKETING_PSYCHOLOGY_SYSTEM,
    PRICING_STRATEGY_SYSTEM,
    SOCIAL_LISTENING_SYSTEM,
    STRATEGY_SYNTHESIZER_SYSTEM,
    USP_DEFINITION_SYSTEM,
    SWOT_SYSTEM,
)
from agents.strategy_prompts import TACTICAL_PLAYBOOK_SYSTEM
from frameworks.kpi_library import get_framework_as_text
from frameworks.save_framework import generate_save_analysis
from frameworks.smart_framework import format_smart_prompt


# ─────────────────────────────────────────────────────────────────
# Enums for skill behavior — drives runtime per skill
# ─────────────────────────────────────────────────────────────────

class OutputFormat(str, Enum):
    """Skill output format — determines OUTPUT_FORMAT_INSTRUCTION injected + renderer used."""
    STRATEGIC_4_SECTION       = "strategic_4_section"        # Insight / Tóm tắt / Benchmarks / Detail
    OPERATIONAL_DELIVERABLE   = "operational_deliverable"    # Standalone file format (ad copy, brief...)
    OPERATIONAL_ANALYSIS      = "operational_analysis"       # Audit-style (verdict + KPI vs reality + actions)


class IntakePattern(str, Enum):
    """How skill collects info from user."""
    MULTI_TURN       = "multi_turn"        # Strategic — Claude conversation extracts JSON profile
    SINGLE_SHOT_FORM = "single_shot_form"  # Operational — user pastes filled template once
    NO_INTAKE        = "no_intake"         # All needed data already in session (e.g., follow-up)


class ContextStrategy(str, Enum):
    """What context data to inject into agent prompt."""
    PROFILE_ONLY              = "profile_only"               # Just BusinessProfile
    FULL_PIPELINE             = "full_pipeline"              # Profile + KPI library + previous results
    PROFILE_PLUS_STRATEGY     = "profile_plus_strategy"      # Profile + synthesis result (for ops post-strategic)
    PROFILE_PLUS_CAMPAIGN     = "profile_plus_campaign"      # Profile + synthesis + campaign_brief
    PROFILE_PLUS_KPI          = "profile_plus_kpi"           # Profile + KPI framework only


class PrimaryDeliverable(str, Enum):
    """Main output format user receives (in addition to Telegram bullets)."""
    HTML     = "html"      # All skills support; default
    EXCEL    = "excel"     # Table-heavy: content_calendar
    MARKDOWN = "markdown"  # Creative deliverables: ads_copy, video_scripts, briefs


# ─────────────────────────────────────────────────────────────────
# AgentSkill — base class
# ─────────────────────────────────────────────────────────────────

class AgentSkill(ABC):
    """Base class for a skill. Each concrete skill defines its prompt + behavior flags.

    Hierarchy:
      AgentSkill (abstract)
      ├── Strategic skills (current 6 subclasses — MarketResearchSkill, etc.)
      ├── OperationalSkill (generic, config-driven — for 6 standard ops skills)
      └── Special operational subclasses (AdsCopySkill, VideoScriptsSkill — custom logic)
    """

    # Identity
    name: str = ""

    # AI behavior
    system_prompt: str = ""
    max_tokens: int = 4000
    enable_critic: bool = True

    # Skill type flags (default = strategic; ops skills override)
    output_format: OutputFormat = OutputFormat.STRATEGIC_4_SECTION
    intake_pattern: IntakePattern = IntakePattern.MULTI_TURN
    context_strategy: ContextStrategy = ContextStrategy.FULL_PIPELINE
    primary_deliverable: PrimaryDeliverable = PrimaryDeliverable.HTML

    # Aggregation into final HTML report (Strategic full-pipeline only)
    accumulate_to_report: bool = True

    @abstractmethod
    def build_context(self, session: Session) -> str:
        """Build context string injected before user message."""
        ...

    @abstractmethod
    def build_user_msg(self, session: Session) -> str:
        """Build the user message — agent-specific framing of the task."""
        ...


class MarketResearchSkill(AgentSkill):
    name = "market_research"
    system_prompt = MARKET_RESEARCH_SYSTEM
    max_tokens = 16000  # bumped từ 8000 — TAM/SAM/SOM + citations dài, từng bị cắt
    output_format = OutputFormat.STRATEGIC_4_SECTION
    intake_pattern = IntakePattern.SINGLE_SHOT_FORM  # Phase 3: dùng template paste
    context_strategy = ContextStrategy.PROFILE_PLUS_KPI
    accumulate_to_report = True

    def build_context(self, session: Session) -> str:
        return session.profile.to_context_string()

    def build_user_msg(self, session: Session) -> str:
        kpi_text = get_framework_as_text(session.profile.industry or "")
        return f"""Hãy phân tích TAM/SAM/SOM cho business này.

{kpi_text}

Đặc biệt chú ý methodology ước tính TAM phù hợp với ngành {session.profile.industry}.
Location: {session.profile.location or 'Việt Nam'}
Target customer: {session.profile.target_customer}"""


class CompetitorSkill(AgentSkill):
    name = "competitor"
    system_prompt = COMPETITOR_SYSTEM
    max_tokens = 16000  # bumped từ 8000 — landscape nhiều đối thủ + matrix dài
    intake_pattern = IntakePattern.SINGLE_SHOT_FORM  # Phase 3
    context_strategy = ContextStrategy.FULL_PIPELINE

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        competitors_known = session.profile.competitors or "chưa xác định"
        grounded = (session.pending_intake or {}).get("_competitor_grounded", "")
        grounded_block = ""
        if grounded:
            grounded_block = (
                "\n\n---\n\n**📡 DỮ LIỆU GROUNDED (đã search web thật — DÙNG LÀM NGUỒN "
                "CHÍNH, GIỮ NGUYÊN link nguồn, KHÔNG bịa số ngoài data này):**\n\n"
                + grounded[:5000]
            )
        return f"""Phân tích landscape cạnh tranh cho business này.

Đối thủ founder đề cập: {competitors_known}

Hãy:
1. Phân tích các đối thủ đã biết (nếu có)
2. Identify thêm các đối thủ điển hình trong ngành {session.profile.industry} tại {session.profile.location or 'VN'}
3. Tìm market gaps rõ ràng nhất
4. Đề xuất positioning opportunity{grounded_block}"""


class CustomerInsightSkill(AgentSkill):
    name = "customer_insight"
    system_prompt = CUSTOMER_INSIGHT_SYSTEM
    max_tokens = 16000  # bumped từ 8000 — demo bị cắt giữa câu (stop_reason=max_tokens)
    enable_critic = False
    intake_pattern = IntakePattern.SINGLE_SHOT_FORM  # Phase 3
    context_strategy = ContextStrategy.FULL_PIPELINE

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        return f"""Xây dựng Customer Insight đầy đủ cho business này.

Product/Service: {session.profile.product_service}
Target customer: {session.profile.target_customer}
Location: {session.profile.location or 'Việt Nam'}

Hãy đào sâu vào psychographics, JTBD, và Vietnamese cultural context của ngành {session.profile.industry}."""


class PsychologyPricingSkill(AgentSkill):
    """Combines Marketing Psychology + Pricing Strategy in 1 call to save latency."""
    name = "psychology_pricing"
    max_tokens = 16000  # bumped từ 8000 — psychology+pricing gộp 1 call, demo bị cắt
    enable_critic = False
    intake_pattern = IntakePattern.SINGLE_SHOT_FORM  # Phase 3
    context_strategy = ContextStrategy.FULL_PIPELINE

    @property
    def system_prompt(self) -> str:
        return f"""{MARKETING_PSYCHOLOGY_SYSTEM}

---

{PRICING_STRATEGY_SYSTEM}

Hãy output CẢ HAI phần: Psychology Application VÀ Pricing Strategy trong một response duy nhất, chia section rõ ràng."""

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        return f"""Áp dụng Marketing Psychology VÀ đề xuất Pricing Strategy cho business này.

Budget marketing: {session.profile.monthly_marketing_budget or 'chưa xác định'}
Mục tiêu: {session.profile.primary_goal}
Stage: {session.profile.stage}

Phần 1: Map psychological principles vào từng touchpoint của funnel
Phần 2: Đề xuất pricing model và tactics cụ thể (với số liệu)"""


class SocialListeningSkill(AgentSkill):
    """Tạm tắt — chờ web search VN coverage tốt hơn."""
    name = "social_listening"
    system_prompt = SOCIAL_LISTENING_SYSTEM
    max_tokens = 8000
    enable_critic = False
    context_strategy = ContextStrategy.FULL_PIPELINE

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        return f"""Thiết kế Social Listening System cho business này.

Business: {session.profile.business_name or session.profile.product_service}
Ngành: {session.profile.industry}
Team size: {session.profile.team_size or 'nhỏ'}
Đối thủ biết đến: {session.profile.competitors or 'chưa xác định'}

Tạo system thực tế, phù hợp với team nhỏ, tập trung vào platform VN."""


class UspDefinitionSkill(AgentSkill):
    """Sprint 2: Định nghĩa USP cho business — REFINE draft hoặc FIND from scratch.

    Chạy stage 4.5 trong Full Pipeline, GIỮA Psychology+Pricing và Synthesis.
    Skill này conditional — pipeline runner kiểm `profile.usp_confidence`:
      - 'clear'   → SKIP (đã có USP rõ ràng từ intake)
      - 'draft'   → run REFINE mode
      - 'missing' → run FIND mode
      - None      → SKIP (legacy users, không có data USP từ intake)
    """
    name = "usp_definition"
    system_prompt = USP_DEFINITION_SYSTEM
    max_tokens = 4000  # Output ngắn gọn — 1 USP + variants + reasoning
    enable_critic = True   # USP cần check không bịa số liệu market
    output_format = OutputFormat.STRATEGIC_4_SECTION  # Vẫn theo format strategic
    context_strategy = ContextStrategy.FULL_PIPELINE  # Cần market + competitor + customer + pricing
    accumulate_to_report = True  # Include trong HTML report

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        confidence = (session.profile.usp_confidence or "").lower()
        draft = session.profile.usp or ""

        if confidence == "draft":
            mode_instruction = f"""**Mode: REFINE**

User đã có draft USP nhưng chưa rõ ràng. Draft hiện tại:
"{draft}"

Nhiệm vụ:
1. KHÔNG đổi nội dung gốc — chỉ làm sắc nét format
2. Identify điểm yếu của draft (mơ hồ ở đâu, thiếu differentiator gì)
3. Output USP refined theo format chuẩn
4. Đưa 2 variant alternative (angle khác draft)
"""
        elif confidence == "missing":
            mode_instruction = """**Mode: FIND**

User chưa có USP. Tìm 1 USP từ context Market + Competitor + Customer + Pricing đã có.

Nhiệm vụ:
1. Đọc kỹ market gap (từ Competitor stage) — tìm angle chưa ai sở hữu
2. Đọc Customer Insight — match với pain/desire cốt lõi
3. Apply 1 trong 3 framework (Niche Domination / Antagonist / Combination)
4. Output USP chính + reasoning + 3 variants
"""
        else:
            # confidence None or unknown — fallback to FIND mode
            mode_instruction = """**Mode: FIND** (fallback — confidence không xác định)

Coi như user chưa có USP, tìm từ context."""

        return f"""Define USP cho business này dựa trên 4 stage trước.

{mode_instruction}

**Business profile:**
- Ngành: {session.profile.industry or 'chưa xác định'}
- Sản phẩm/dịch vụ: {session.profile.product_service or 'chưa xác định'}
- Khách hàng: {session.profile.target_customer or 'chưa xác định'}
- Địa bàn: {session.profile.location or 'Việt Nam'}
- Stage: {session.profile.stage or 'chưa rõ'}

Tham chiếu kết quả Market + Competitor + Customer + Psychology+Pricing đã có trong context."""


class StrategySynthesisSkill(AgentSkill):
    name = "synthesis"
    system_prompt = STRATEGY_SYNTHESIZER_SYSTEM
    max_tokens = 40000  # unlock Gemini 2.5 Pro: ~32-40K narrative output (was 10K cap)
    enable_critic = False
    context_strategy = ContextStrategy.FULL_PIPELINE

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        save_prompt = generate_save_analysis(
            industry=session.profile.industry or "",
            business_description=session.profile.product_service or "",
            target_customer=session.profile.target_customer or "",
            product_service=session.profile.product_service or "",
        )
        smart_prompt = format_smart_prompt(
            industry=session.profile.industry or "",
            stage=session.profile.stage or "growth",
            goals=[session.profile.primary_goal or "tăng doanh thu"],
        )
        direction = (session.pending_intake or {}).get("_strategy_direction", "")
        direction_block = (
            f"\n\n## Hướng chiến lược sếp chọn:\n{direction}\n\n"
            f"→ Tập trung kế hoạch theo hướng này. Các phần khác là hỗ trợ."
        ) if direction else ""

        return f"""Tổng hợp tất cả insights đã phân tích thành Marketing Strategy hoàn chỉnh.{direction_block}

{save_prompt}

{smart_prompt}

Yêu cầu:
- Apply SAVE Framework cụ thể cho {session.profile.business_name or 'business này'}
- Tạo 2-3 SMART goals với số liệu thực tế
- 90-day roadmap cụ thể, actionable
- KPI dashboard với targets 30/60/90 ngày
- Quick wins có thể làm ngay trong 2 tuần đầu
- Budget allocation đề xuất"""


class SwotSkill(AgentSkill):
    """Tổng hợp S/W/O/T từ toàn bộ research pipeline — chạy sau USP, trước Synthesis."""
    name = "swot"
    system_prompt = SWOT_SYSTEM
    max_tokens = 22000  # bump — SWOT + ma trận TOWS 4 ô (must-have ở cuối) từng bị cắt giữa Threats
    context_strategy = ContextStrategy.FULL_PIPELINE  # Cần đủ 5 research results

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        p = session.profile
        return f"""Tổng hợp SWOT cho business này từ toàn bộ research đã có trong context (Market, Competitor, Customer, Psychology+Pricing, USP).

**Business:**
- Ngành: {p.industry or 'chưa xác định'}
- Sản phẩm/dịch vụ: {p.product_service or 'chưa xác định'}
- Khách hàng: {p.target_customer or 'chưa xác định'}
- Địa bàn: {p.location or 'Việt Nam'}

Mỗi điểm S/W/O/T phải bám dẫn chứng cụ thể từ research, rồi dựng ma trận SO/WO/ST/WT làm nền cho Synthesis và Tactical Playbook."""


class TacticalPlaybookSkill(AgentSkill):
    """Viết SO/WO/WT tactics per-segment — chạy sau Synthesis, dựa trên SWOT + Synthesis."""
    name = "tactical_playbook"
    system_prompt = TACTICAL_PLAYBOOK_SYSTEM
    max_tokens = 20000  # nhiều phân khúc × SO/WO/WT; 8000 từng bị cắt cụt tệp phụ (Sonnet hỗ trợ tới ~64K out)
    context_strategy = ContextStrategy.FULL_PIPELINE  # Đọc SWOT + Synthesis từ context

    def build_context(self, session: Session) -> str:
        return session.build_pipeline_context()

    def build_user_msg(self, session: Session) -> str:
        p = session.profile

        # Archetype block — cùng resolver với CMO Strategy (v2) để tactics/kênh/copy
        # bám đúng archetype mua hàng (pipeline synthesis chưa inject sẵn archetype).
        archetype_section = ""
        try:
            from frameworks.industry_context import format_archetype_block
            if p.industry:
                archetype_brief_text = " ".join(filter(None, [
                    p.product_service or "",
                    p.target_customer or "",
                ]))
                block = format_archetype_block(p.industry, archetype_brief_text)
                if block:
                    archetype_section = (
                        f"\n\n# ARCHETYPE MUA HÀNG (bám khi chọn kênh / copy / tactics)\n{block}"
                    )
        except Exception:
            archetype_section = ""

        return f"""Viết Tactical Playbook cho business này, dựa trên bảng SWOT và Kế Hoạch Đề Xuất (Synthesis) đã có trong context.

**Business:**
- Ngành: {p.industry or 'chưa xác định'}
- Sản phẩm/dịch vụ: {p.product_service or 'chưa xác định'}
- Khách hàng: {p.target_customer or 'chưa xác định'}
- Địa bàn: {p.location or 'Việt Nam'}{archetype_section}

Bám wedge của Synthesis, đào sâu SO/WO/WT thành tactics thực thi (copy mẫu, kênh, tham số, KPI) cho từng tệp khách hàng chính — kênh và copy phải khớp archetype hiệu lực ở trên."""


# Registry — used by pipeline.py to look up skill by stage_key
SKILL_REGISTRY: dict[str, type[AgentSkill]] = {
    "market_research":    MarketResearchSkill,
    "competitor":         CompetitorSkill,
    "customer_insight":   CustomerInsightSkill,
    "psychology_pricing": PsychologyPricingSkill,
    "usp_definition":     UspDefinitionSkill,
    "swot":               SwotSkill,
    "social_listening":   SocialListeningSkill,
    "synthesis":          StrategySynthesisSkill,
    "tactical_playbook":  TacticalPlaybookSkill,
}
