"""
Campaign Ideation — Bridge skill giữa Strategy (A→Z) và Campaign Brief.

2 modes:
- PROPOSE: User chưa biết chạy gì → bot đề xuất 3 campaign options dựa vào
  synthesis + customer_insight + market_research.
- REFINE: User đã có idea → bot validate + refine với customer_insight + market_research.

Cả 2 đều output JSON structured để feed thẳng vào campaign_brief skill.
"""
import json
import logging
import re
from typing import Optional

import anthropic

from config import CLAUDE_SONNET_MODEL, ANTHROPIC_API_KEY
from storage.models import Session

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(
    api_key=ANTHROPIC_API_KEY,
    timeout=120.0,
    max_retries=1,
)


# ─────────────────────────────────────────────────────────────────
# DISCOVERY — Max hỏi câu mở đầu campaign, ĐỘNG theo ngành
# ─────────────────────────────────────────────────────────────────

# Fallback khi không rõ ngành / LLM lỗi — câu hỏi generic.
_DISCOVERY_FALLBACK = (
    "🧠 *Max:* Trước khi đề xuất, cho em hỏi nhanh ạ:\n\n"
    "• *Mục tiêu gần nhất* của sếp là gì? "
    "_(thu khách mới · tăng doanh thu/AOV · giữ chân khách cũ · build thương hiệu)_\n"
    "• Sếp *đang ấp ủ campaign nào chưa?* "
    "_(tên/chủ đề, hoặc chỉ 1 từ khoá — vd \"Tết\", \"ra mắt SP\"...)_\n"
    "• Có *mốc thời gian* cần nhắm tới không? "
    "_(dịp lễ, ngày ra mắt, cuối quý đẩy số, khai trương... — để em canh timing + offer)_\n\n"
    "_Sếp mô tả tự do bên dưới → em validate luôn. Hoặc bấm nút để em đề xuất trước._"
)

# Fallback cho câu hỏi nhu cầu (khi không rõ ngành / LLM lỗi).
_NEEDS_FALLBACK = (
    "🔍 *Trước khi đề xuất campaign, em hỏi nhanh sếp 3 ý nhé:*\n\n"
    "1️⃣ *Mục tiêu lúc này là gì?*\n"
    "_(Thu khách mới · Bán thêm cho khách cũ · Ra sản phẩm mới · Kéo khách cũ quay lại)_\n\n"
    "2️⃣ *Có dịp / mùa vụ nào sắp tới không?*\n"
    "_(Tết, 8/3, khai trường, cuối năm... — hoặc 'không có dịp cụ thể')_\n\n"
    "3️⃣ *Ngân sách campaign dự kiến khoảng nào?*\n"
    "_(Nhỏ <10 triệu · Vừa 10-50 triệu · Lớn >50 triệu — hoặc gõ con số)_\n\n"
    "Sếp trả lời cả 3 trong 1 tin giúp em nhé 🙏"
)

NEEDS_QUESTION_SYSTEM = """Bạn là **Max** — CMO AI. Trước khi đề xuất 3 campaign options, hỏi sếp 3 câu NGẮN để hiểu nhu cầu. Câu hỏi PHẢI bám ngành của sếp.

3 câu BẮT BUỘC (theo thứ tự):

1️⃣ **Mục tiêu lúc này** — đưa 4 lựa chọn mục tiêu ĐẶC THÙ NGÀNH (dựa vào growth levers + market dynamics được cung cấp), KHÔNG generic.
   - VD F&B: "Tăng giá trị đơn qua combo/upsell · Lấp giờ thấp điểm · Tăng tần suất quay lại · Thu khách mới khu vực"
   - VD Spa/Clinic: "Đẩy khách trial → liệu trình · Tăng LTV qua gói combo · Win-back khách cũ · Thu khách mới"
   - VD SaaS: "Tăng trial → paid · Giảm churn · Upsell gói cao · Acquisition logo mới"
   - VD Ecom: "Tăng AOV/giỏ hàng · Tăng repeat & LTV · Thu khách mới · Xả hàng tồn"
2️⃣ **Dịp / mùa vụ sắp tới** — gợi ý mốc seasonal đặc thù ngành (vd F&B: Tết, Trung Thu, mùa cưới; Ecom: 11.11/12.12; Education: mùa tuyển sinh). Cho phép "không có dịp cụ thể".
3️⃣ **Ngân sách dự kiến** — Nhỏ <10 triệu · Vừa 10-50 triệu · Lớn >50 triệu (hoặc con số cụ thể).

QUY TẮC OUTPUT (Telegram chat):
- Mở đầu 1 dòng: "🔍 *Trước khi đề xuất campaign, em hỏi nhanh 3 ý nhé:*"
- Mỗi câu 1 block, đánh số 1️⃣ 2️⃣ 3️⃣, *in đậm* tiêu đề + _( )_ chứa lựa chọn ngăn bằng " · ".
- CHỈ dùng *in đậm*, _in nghiêng_. KHÔNG heading #, KHÔNG bảng |.
- Kết thúc 1 dòng: "Sếp trả lời cả 3 trong 1 tin giúp em nhé 🙏"
- KHÔNG bịa số liệu."""

DISCOVERY_SYSTEM = """Bạn là **Max** — CMO AI. Strategy A→Z vừa chốt xong. Việc của bạn: hỏi 3 câu discovery NGẮN để hiểu campaign sếp cần, TRƯỚC khi đề xuất.

3 câu BẮT BUỘC có (theo thứ tự), nhưng diễn đạt phải BÁM NGÀNH của sếp:

1. **Mục tiêu gần nhất** — đưa 3-4 lựa chọn mục tiêu ĐẶC THÙ NGÀNH (dựa vào growth levers + market dynamics được cung cấp), KHÔNG dùng mục tiêu generic.
   - VD F&B: "tăng table turn giờ thấp điểm · tăng repeat visit · cân lại tỷ trọng delivery · đẩy daypart mới (sáng/tối)"
   - VD SaaS: "tăng trial→paid · giảm churn · expansion/upsell tài khoản cũ · acquisition logo mới"
   - VD Ecommerce: "tăng AOV/giỏ hàng · tăng repeat & LTV · thu khách mới · xả hàng tồn"
2. **Campaign đang ấp ủ** — hỏi sếp đã có ý tưởng/chủ đề/từ khoá nào chưa.
3. **Mốc thời gian** — hỏi có dịp/sự kiện cần neo không, GỢI Ý mốc seasonal đặc thù ngành (vd F&B: Tết, Trung Thu, mùa cưới; Ecom: Mega sale 11.11/12.12, Tết; Education: mùa tuyển sinh).

QUY TẮC OUTPUT (Telegram chat):
- Mở đầu đúng 1 dòng: "🧠 *Max:* ..."
- CHỈ dùng *in đậm*, _in nghiêng_, bullet "• ". KHÔNG heading #, KHÔNG bảng |.
- Tổng ≤ 10 dòng. Mỗi câu hỏi 1 bullet, lựa chọn để trong _( )_ ngăn bằng " · ".
- Kết thúc 1 dòng: "_Sếp mô tả tự do bên dưới → em validate luôn. Hoặc bấm nút để em đề xuất trước._"
- KHÔNG bịa số liệu. KHÔNG hỏi budget/team (để bước sau)."""


async def generate_discovery_questions(session: Session) -> str:
    """Sinh 3 câu discovery campaign ĐỘNG theo ngành.

    Router chain: Haiku (primary) → GPT-5-mini (fallback khi Haiku hit RPD) → GPT-5.
    Fallback về câu generic nếu thiếu ngành hoặc cả chain đều lỗi.
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError

    industry = (session.profile.industry or "").strip()
    if not industry:
        return _DISCOVERY_FALLBACK

    ctx_parts = _build_industry_levers_context(session, industry)

    user_msg = (
        "\n\n".join(ctx_parts)
        + "\n\n---\n\nHãy viết 3 câu discovery campaign bám ngành trên, theo đúng format Telegram."
    )

    try:
        # CRITIC_REVIEW chain: Haiku → GPT-5-mini → GPT-5
        # Nếu Haiku hit RPD, router tự failover sang GPT-5-mini — không cần code thêm.
        result = await router_call(
            task_type=TaskType.CRITIC_REVIEW,
            system=DISCOVERY_SYSTEM,
            user=user_msg,
            max_tokens=600,
        )
        text = (result.get("output") or "").strip()
        provider = result.get("provider", "unknown")
        if provider != "anthropic_haiku":
            logger.info("generate_discovery_questions fallover to provider=%s (industry=%s)", provider, industry)
        return text if text else _DISCOVERY_FALLBACK
    except AllProvidersFailedError as e:
        logger.warning("generate_discovery_questions all providers failed (industry=%s): %s", industry, e)
        return _DISCOVERY_FALLBACK
    except Exception as e:
        logger.warning("generate_discovery_questions failed (industry=%s): %s", industry, e)
        return _DISCOVERY_FALLBACK


def _build_industry_levers_context(session: Session, industry: str) -> list[str]:
    """Gom context ngành: growth levers + market dynamics + synthesis excerpt."""
    ctx_parts = [f"# NGÀNH: {industry}"]
    try:
        from frameworks.kpi_library import get_kpi_framework
        fw = get_kpi_framework(industry)
        if fw and getattr(fw, "growth_levers", None):
            ctx_parts.append("## Growth levers của ngành:\n" + "\n".join(f"- {x}" for x in fw.growth_levers))
    except Exception:
        pass
    try:
        from frameworks.industry_context import get_industry_context
        ic = get_industry_context(industry)
        if ic and getattr(ic, "market_dynamics", None):
            ctx_parts.append("## Market dynamics:\n" + ic.market_dynamics)
    except Exception:
        pass
    synthesis = session.get_latest_result("synthesis") or ""
    if synthesis:
        ctx_parts.append("## Trích Strategy (synthesis):\n" + synthesis[:1200])
    return ctx_parts


async def generate_campaign_needs_question(session: Session) -> str:
    """Sinh câu hỏi nhu cầu campaign (mục tiêu + dịp + ngân sách) ĐỘNG theo ngành,
    trước khi đề xuất 3 campaign options. Mục tiêu flex theo growth_levers ngành.
    Fallback generic nếu thiếu ngành / LLM lỗi."""
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError

    industry = (session.profile.industry or "").strip()
    if not industry:
        return _NEEDS_FALLBACK

    ctx_parts = _build_industry_levers_context(session, industry)
    user_msg = (
        "\n\n".join(ctx_parts)
        + "\n\n---\n\nHãy viết 3 câu hỏi nhu cầu campaign bám ngành trên (mục tiêu flex theo growth levers), theo đúng format Telegram."
    )
    try:
        result = await router_call(
            task_type=TaskType.CRITIC_REVIEW,
            system=NEEDS_QUESTION_SYSTEM,
            user=user_msg,
            max_tokens=600,
        )
        text = (result.get("output") or "").strip()
        return text if text else _NEEDS_FALLBACK
    except AllProvidersFailedError as e:
        logger.warning("generate_campaign_needs_question all providers failed (industry=%s): %s", industry, e)
        return _NEEDS_FALLBACK
    except Exception as e:
        logger.warning("generate_campaign_needs_question failed (industry=%s): %s", industry, e)
        return _NEEDS_FALLBACK


PROPOSE_SYSTEM = """Bạn là Max — CMO AI giúp founder VN xác định campaign tiếp theo dựa trên Marketing Strategy đã có.

Dựa vào Strategy synthesis + Customer Insight + Market Research, đề xuất 3 campaign options KHẢ THI nhất.

🔑 QUAN TRỌNG: Context sẽ có section "## Nhu cầu founder vừa chia sẻ" — ĐỌC KỸ và BẮT BUỘC ưu tiên theo đó:
- Nếu founder muốn "thu khách mới" → 3 options phải xoay quanh acquisition
- Nếu có dịp/mùa vụ cụ thể → ít nhất 2/3 options bám dịp đó
- Nếu ngân sách nhỏ → options phải organic-first, chi phí thấp; ngân sách lớn → paid media heavy
- KHÔNG đề xuất campaign trái ngược với nhu cầu founder đã nêu

Mỗi option phải:
- Bám sát SAVE Framework + định hướng giai đoạn trong synthesis (SMART số cụ thể đặt ở chính campaign này)
- Match với pain point từ Customer Insight (cite cụ thể)
- Tận dụng cơ hội từ Market Research (timing, seasonality, market gap)
- Khác biệt rõ ràng giữa 3 options — mỗi option giải quyết 1 mục tiêu chính khác nhau:
  Option 1: Acquisition / thu khách mới
  Option 2: Retention / upsell / tăng AOV
  Option 3: Brand / awareness / positioning

🔴 QUY TẮC TUYỆT ĐỐI — 4 trường SAU DO USER QUYẾT, KHÔNG ĐỀ XUẤT:
- ❌ KHÔNG đề xuất **Budget** (số tiền VND cụ thể)
- ❌ KHÔNG đề xuất **Team size** (số người)
- ❌ KHÔNG đề xuất **Start date** (ngày bắt đầu)
- ❌ KHÔNG đề xuất **% giảm giá** cụ thể trong offer

→ Trong `goal`, `duration`, `key_offer` chỉ đưa BENCHMARK định tính + range gợi ý:
- Goal: "Thu lead mới + chốt booking" (KHÔNG nói "500 booking, doanh thu 350tr" vì chưa biết budget)
- Duration: gợi ý số tuần (vd "4-6 tuần") — KHÔNG ngày cụ thể vì user chọn start date
- Key offer: mô tả CƠ CHẾ offer (combo / bundle / sample / quà tặng) — KHÔNG % giảm cụ thể

OUTPUT BẮT BUỘC dạng JSON (KHÔNG có text khác bên ngoài JSON):

```json
{
  "options": [
    {
      "name": "Tên campaign tiếng Việt, hook-y, ngắn (vd: 'Tặng Mình Trước', 'Cuối Năm Đẹp Hơn')",
      "goal": "Mục tiêu QUALITATIVE (vd: 'Acquisition khách mới ở segment phụ nữ 28-40 chưa từng dùng spa, build initial trust')",
      "key_offer": "MÔ TẢ cơ chế offer KHÔNG có % giảm cụ thể (vd: 'Combo trial 2-buổi + tặng kèm 1 sản phẩm sample. % giảm do sếp quyết')",
      "duration_suggestion": "Gợi ý độ dài (vd: '4-6 tuần để build awareness + chuyển đổi đợt đầu')",
      "target_segment": "Tệp target cụ thể (vd: 'Phụ nữ 28-40 sống Q1/Q3 HCM, đã follow page chưa book')",
      "why_fit": "2-3 câu: tại sao campaign này hợp với business sếp ở thời điểm này — CITE cụ thể từ synthesis/customer/market"
    },
    { ... option 2 ... },
    { ... option 3 ... }
  ]
}
```

QUY TẮC:
- KHÔNG bịa số liệu — chỉ dùng data đã có trong context
- 3 options đa dạng về mục tiêu (acquisition / retention / brand)
- Tên campaign tiếng Việt, không dùng tiếng Anh
- Output CHỈ JSON trong ```json``` block, KHÔNG có text giải thích bên ngoài
"""


REFINE_SYSTEM = """Bạn là Max — CMO AI validate idea campaign của founder VN.

User đã có ý tưởng campaign. Dựa vào Customer Insight + Market Research, hãy:
1. **Validate idea**: idea có hợp với customer pain point + market timing không?
2. **Refine**: đưa ra tên/goal/offer cụ thể hơn nếu user nói chung chung
3. **Cảnh báo risks** (nếu có): timing sai, segment không match, offer yếu, v.v.

🔴 QUY TẮC TUYỆT ĐỐI — 4 trường SAU DO USER QUYẾT, KHÔNG ĐỀ XUẤT:
- ❌ KHÔNG đề xuất **Budget** (số tiền VND cụ thể)
- ❌ KHÔNG đề xuất **Team size** (số người)
- ❌ KHÔNG đề xuất **Start date** (ngày bắt đầu)
- ❌ KHÔNG đề xuất **% giảm giá** cụ thể trong offer

→ Goal/duration/key_offer chỉ benchmark định tính + range gợi ý.

OUTPUT BẮT BUỘC dạng JSON (KHÔNG có text khác bên ngoài JSON):

```json
{
  "refined": {
    "name": "Tên campaign hoàn chỉnh (giữ ý user, refine wording)",
    "goal": "Mục tiêu QUALITATIVE (vd: 'Acquisition khách mới + build initial trust')",
    "key_offer": "MÔ TẢ cơ chế offer KHÔNG có % giảm cụ thể",
    "duration_suggestion": "Gợi ý độ dài (vd: '4-6 tuần')",
    "target_segment": "Tệp target cụ thể"
  },
  "validation": {
    "alignment_score": "high | medium | low",
    "fit_analysis": "2-3 câu phân tích: idea sếp có align với customer pain + market timing không (CITE cụ thể)",
    "risks": ["risk 1 ngắn gọn", "risk 2 (nếu có)"],
    "suggestions": ["gợi ý 1 để tăng impact", "gợi ý 2 (nếu có)"]
  }
}
```

QUY TẮC:
- KHÔNG bịa số — chỉ dùng từ context
- Nếu idea quá vague (vd "chạy combo Tết") → expand chi tiết dựa trên synthesis
- TÔN TRỌNG user intent — không đổi hoàn toàn idea, chỉ refine
- Output CHỈ JSON trong ```json``` block
"""


def _build_ideation_context(session: Session) -> str:
    """Build subset context: profile + customer + market + synthesis + campaign needs."""
    parts = [session.profile.to_context_string()]

    for key, label in [
        ("market_research",   "## Kết quả Nghiên cứu Thị trường"),
        ("customer_insight",  "## Kết quả Customer Insight"),
        ("synthesis",         "## Marketing Strategy (Synthesis)"),
        ("tactical_playbook", "## Tactical Playbook (SO/WO/WT tactics)"),
        ("psychology_pricing","## Pricing & Psychology"),
        ("usp_definition",    "## USP"),
    ]:
        content = session.get_latest_result(key)
        if content:
            parts.append(f"{label}\n{content}")

    # Nhu cầu cụ thể founder vừa trả lời (mục tiêu / dịp / ngân sách)
    needs = (session.pending_intake.get("_campaign_needs_raw") or "").strip()
    obj   = (session.pending_intake.get("campaign_objective") or "").strip()
    occ   = (session.pending_intake.get("upcoming_occasion") or "").strip()
    bgt   = (session.pending_intake.get("budget_range") or "").strip()
    if needs:
        need_lines = [f"## Nhu cầu founder vừa chia sẻ\n_{needs}_"]
        if obj:  need_lines.append(f"- Mục tiêu: {obj}")
        if occ:  need_lines.append(f"- Dịp/mùa vụ: {occ}")
        if bgt:  need_lines.append(f"- Ngân sách: {bgt}")
        parts.append("\n".join(need_lines))

    return "\n\n---\n\n".join(parts)


def _extract_json(text: str) -> Optional[dict]:
    """Extract first ```json``` block from LLM output."""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not match:
        # Fallback: try parsing whole text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from campaign ideation: %s", e)
        return None


EXTRACT_CAMPAIGNS_SYSTEM = """Bạn là Max — CMO AI. Kế hoạch chiến lược 90 ngày vừa được xác nhận.

NHIỆM VỤ: Đọc Kế hoạch chiến lược (synthesis) + 8 hướng chiến lược sếp đã chọn + Ngân sách/Team hiện tại (nếu có) → TRÍCH XUẤT 2-3 campaign cụ thể đã được roadmap đề cập hoặc hàm ý, align hoàn toàn với hướng sếp đã chọn.

NGUYÊN TẮC:
- KHÔNG tạo campaign mới từ không khí — phải dựa trên roadmap/synthesis
- Mỗi campaign phải reflect đúng segment, USP angle, channel, timeline sếp đã chọn trong 8 câu
- Tên campaign tiếng Việt, hook-y, ngắn (4-7 từ)
- KHÔNG đề xuất budget / % giảm cụ thể (sếp quyết ở bước sau)

QUY MÔ (nếu có thông tin Ngân sách/Team):
- Đa số campaign đề xuất (`scale: "fit"`) phải KHẢ THI với ngân sách + team hiện tại
  — số kênh, tần suất nội dung, nhu cầu outsource phải sát quy mô thật, không
  đề xuất campaign cần nhiều kênh/nhiều người hơn team đang có.
- Nếu roadmap có 1 hướng campaign THAM VỌNG hơn (cần outsource thêm, đa kênh
  hơn, ngân sách lớn hơn) — vẫn có thể đưa vào nhưng đánh dấu `scale: "stretch"`.
- Nếu KHÔNG có thông tin Ngân sách/Team, đánh dấu tất cả `scale: "fit"`.

OUTPUT BẮT BUỘC dạng JSON (KHÔNG có text khác bên ngoài JSON):

```json
{
  "campaigns": [
    {
      "name": "Tên campaign tiếng Việt (4-7 từ)",
      "goal": "Mục tiêu cụ thể, định tính",
      "target_segment": "Tệp target align với strategic direction",
      "key_offer": "Cơ chế offer sơ bộ — KHÔNG % giảm cụ thể",
      "duration_suggestion": "Gợi ý độ dài (vd: '4-6 tuần')",
      "channels": "Kênh triển khai theo channel sếp đã chọn",
      "why_fit": "1-2 câu: tại sao campaign này đúng hướng + đúng timing",
      "scale": "fit hoặc stretch — xem QUY MÔ ở trên"
    }
  ]
}
```

QUY TẮC:
- 2-3 campaigns, đa dạng về mục tiêu nếu roadmap đề cập nhiều mục tiêu
- Tối đa 1 campaign `scale: "stretch"` trong số đó
- Output CHỈ JSON trong ```json``` block
- KHÔNG bịa số liệu"""


async def extract_campaigns_from_synthesis(session: Session) -> Optional[list[dict]]:
    """Extract 2-3 campaigns directly from synthesis roadmap + strategy_answers.

    Bridge step: after strategy_confirm, reads 90-day roadmap + 8 strategic choices
    + tactical playbook, returns campaigns already aligned with those choices —
    no re-asking needed. Returns list[dict] or None on failure.
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError

    synthesis = (session.get_latest_result("synthesis") or "").strip()
    if not synthesis:
        return None

    import json as _json
    try:
        answers = _json.loads(session.pending_intake.get("_strategy_answers") or "{}")
    except Exception:
        answers = {}

    label_map = {
        "market_gap":       "Market Gap",
        "target_segment":   "Target Segment",
        "competitor_gap":   "Messaging Gap",
        "positioning":      "Định Vị",
        "pricing_approach": "Pricing",
        "usp_angle":        "USP Angle",
        "channels":         "Kênh Triển Khai",
        "timeline":         "Timeline Triển Khai",
    }
    answer_lines = [
        f"- {label}: {answers[key]}"
        for key, label in label_map.items()
        if answers.get(key)
    ]
    strategy_block = (
        "## 8 Hướng chiến lược sếp đã chọn:\n" + "\n".join(answer_lines) + "\n\n"
        if answer_lines else ""
    )

    # Budget/Team — collected just before campaign extraction (BACKLOG #5),
    # dùng để campaign đề xuất khả thi với quy mô thật.
    budget_team_context = (session.pending_intake.get("_budget_team_context") or "").strip()
    if not budget_team_context:
        budget_team_lines = []
        if session.profile.monthly_marketing_budget:
            budget_team_lines.append(f"Ngân sách marketing/tháng: {session.profile.monthly_marketing_budget}")
        if session.profile.team_size:
            budget_team_lines.append(f"Team: {session.profile.team_size}")
        budget_team_context = "\n".join(budget_team_lines)
    budget_team_block = (
        f"## Ngân sách & Team hiện tại:\n{budget_team_context}\n\n"
        if budget_team_context else ""
    )

    # T5 Tactical Playbook — campaign trích ra phải nhất quán với tactics đã đề xuất.
    # Dùng FULL playbook (~10-12K ký tự): 2500 ký tự đầu chỉ chứa archetype + insight,
    # cắt ngay TRƯỚC các Hướng tactic (SO/WO/WT) — đúng phần cần để trích campaign.
    playbook = (session.get_latest_result("tactical_playbook") or "").strip()
    playbook_block = (
        f"## Tactical Playbook (SO/WO/WT tactics):\n{playbook[:14000]}\n\n"
        if playbook else ""
    )

    user_msg = (
        f"## Kế hoạch chiến lược (Synthesis):\n{synthesis[:14000]}\n\n"
        f"{playbook_block}"
        f"{strategy_block}"
        f"{budget_team_block}"
        "---\n\nTrích 2-3 campaign cụ thể từ roadmap trên, align với hướng sếp đã chọn "
        "và nhất quán với tactics trong Tactical Playbook (nếu có). "
        + ("Ưu tiên campaign khả thi với Ngân sách/Team hiện tại (đánh dấu scale tương ứng)."
           if budget_team_context else "")
    )

    try:
        result = await router_call(
            task_type=TaskType.INTAKE_JSON,
            system=EXTRACT_CAMPAIGNS_SYSTEM,
            user=user_msg,
            max_tokens=1500,
        )
        text = (result.get("output") or "").strip()
    except AllProvidersFailedError as e:
        logger.warning("extract_campaigns_from_synthesis all providers failed: %s", e)
        return None
    except Exception as e:
        logger.warning("extract_campaigns_from_synthesis failed: %s", e)
        return None

    data = _extract_json(text)
    if not data or "campaigns" not in data:
        logger.error("extract_campaigns returned invalid JSON: %s", text[:200])
        return None

    campaigns = data.get("campaigns", [])
    if not isinstance(campaigns, list) or len(campaigns) < 1:
        return None

    return campaigns[:3]


# ─────────────────────────────────────────────────────────────────
# OFFER "MỒI" HINT — câu 1 của offer-preferences, flex theo ngành
# ─────────────────────────────────────────────────────────────────

# Fallback generic khi thiếu ngành / LLM lỗi.
_BAIT_HINT_FALLBACK = "Giảm giá thẳng · Tặng thêm giá trị (quà/topping/combo) · Cho dùng thử · Đặc quyền riêng"

_BAIT_HINT_SYSTEM = """Bạn là Max — CMO AI. Cần gợi ý cho founder 4 CÁCH "MỒI" KHÁCH (cơ chế kéo khách action) ĐẶC THÙ NGÀNH của họ.

Đây là câu hỏi mở đầu để founder chọn hướng ưu đãi — chưa cần parameters.

Ví dụ theo ngành:
- F&B: "Combo tiết kiệm · BOGO (mua 1 tặng 1) · Happy hour giờ thấp điểm · Thẻ tích điểm"
- Beauty/Spa: "Trial buổi đầu · Bundle liệu trình · Tặng kèm sản phẩm (GWP) · Đặc quyền VIP"
- SaaS: "Free trial · Demo 1-1 · Ưu đãi gói năm · Freemium"
- Ecom: "Freeship · Flash sale · Combo/bundle · Hoàn tiền (cashback)"
- Education: "Early bird · Giảm theo nhóm · Học thử miễn phí · Trả góp 0%"

QUY TẮC OUTPUT:
- CHỈ trả về 1 dòng duy nhất: 4 cách "mồi" ngăn nhau bằng " · "
- Mỗi cách 2-5 từ, tiếng Việt, đặc thù ngành
- KHÔNG giải thích, KHÔNG markdown, KHÔNG đánh số"""


async def generate_bait_hint(session: Session) -> str:
    """Sinh 4 cách 'mồi' khách đặc thù ngành cho câu 1 của offer-preferences.
    Fallback generic nếu thiếu ngành / LLM lỗi."""
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError

    industry = (session.profile.industry or "").strip()
    if not industry:
        return _BAIT_HINT_FALLBACK

    ctx_parts = _build_industry_levers_context(session, industry)
    user_msg = (
        "\n\n".join(ctx_parts)
        + "\n\n---\n\nGợi ý 4 cách 'mồi' khách đặc thù ngành trên, 1 dòng ngăn bằng ' · '."
    )
    try:
        result = await router_call(
            task_type=TaskType.CRITIC_REVIEW,
            system=_BAIT_HINT_SYSTEM,
            user=user_msg,
            max_tokens=150,
        )
        text = (result.get("output") or "").strip().replace("\n", " ")
        return text if text else _BAIT_HINT_FALLBACK
    except AllProvidersFailedError as e:
        logger.warning("generate_bait_hint all providers failed (industry=%s): %s", industry, e)
        return _BAIT_HINT_FALLBACK
    except Exception as e:
        logger.warning("generate_bait_hint failed (industry=%s): %s", industry, e)
        return _BAIT_HINT_FALLBACK


async def propose_campaigns(session: Session) -> Optional[list[dict]]:
    """Mode PROPOSE: Đề xuất 3 campaign options.

    Returns list[dict] với 3 options, hoặc None nếu fail.
    """
    context = _build_ideation_context(session)
    user_msg = (
        f"{context}\n\n---\n\n"
        "Đề xuất 3 campaign options khả thi nhất cho business của sếp trong 1-3 tháng tới. "
        "Mỗi option phải khác biệt rõ ràng về mục tiêu."
    )

    try:
        response = await client.messages.create(
            model=CLAUDE_SONNET_MODEL,
            max_tokens=3000,
            system=[{"type": "text", "text": PROPOSE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        logger.exception("Campaign propose API call failed: %s", e)
        return None

    # Token tracking
    try:
        from tools.token_tracker import track_usage
        track_usage(session, response, label="campaign_propose")
    except Exception:
        pass

    raw = response.content[0].text
    data = _extract_json(raw)
    if not data or "options" not in data:
        logger.error("Campaign propose returned invalid JSON: %s", raw[:200])
        return None

    options = data.get("options", [])
    if not isinstance(options, list) or len(options) < 1:
        return None

    return options[:3]  # cap 3


async def refine_user_idea(session: Session, user_idea: str) -> Optional[dict]:
    """Mode REFINE: Validate + refine user's campaign idea.

    Returns dict {refined: {...}, validation: {...}} hoặc None nếu fail.
    """
    context = _build_ideation_context(session)
    user_msg = (
        f"{context}\n\n---\n\n"
        f"**Ý tưởng campaign của sếp:**\n{user_idea}\n\n"
        "Validate + refine idea này dựa trên Customer Insight + Market Research."
    )

    try:
        response = await client.messages.create(
            model=CLAUDE_SONNET_MODEL,
            max_tokens=2000,
            system=[{"type": "text", "text": REFINE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        logger.exception("Campaign refine API call failed: %s", e)
        return None

    try:
        from tools.token_tracker import track_usage
        track_usage(session, response, label="campaign_refine")
    except Exception:
        pass

    raw = response.content[0].text
    data = _extract_json(raw)
    if not data or "refined" not in data:
        logger.error("Campaign refine returned invalid JSON: %s", raw[:200])
        return None

    return data


def format_options_card(options: list[dict]) -> str:
    """Format 3 options thành text card cho user đọc."""
    lines = ["💡 *Em đề xuất 3 campaign options dựa trên Strategy của sếp:*\n"]

    for i, opt in enumerate(options, 1):
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"*OPTION {i}: {opt.get('name', '?')}*\n")
        lines.append(f"🎯 *Mục tiêu:* {opt.get('goal', '?')}")
        lines.append(f"🎁 *Cơ chế offer:* {opt.get('key_offer', '?')}")
        lines.append(f"📅 *Gợi ý độ dài:* {opt.get('duration_suggestion', '?')}")
        lines.append(f"👥 *Target:* {opt.get('target_segment', '?')}")
        lines.append(f"💭 *Vì sao phù hợp:* {opt.get('why_fit', '?')}\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("\n_💰 Budget / 👥 Team / 📅 Thời lượng / 🎟 % giảm — sếp sẽ quyết ở bước sau._\n")
    lines.append("👇 *Sếp chọn option nào để em làm Brief Campaign?*")
    return "\n".join(lines)


def format_refined_card(refined_data: dict) -> str:
    """Format refined idea thành text card cho user confirm."""
    refined = refined_data.get("refined", {})
    validation = refined_data.get("validation", {})

    score_emoji = {
        "high":   "🟢 Cao",
        "medium": "🟡 Trung bình",
        "low":    "🔴 Thấp",
    }.get(validation.get("alignment_score", "").lower(), "⚪️ ?")

    lines = [
        "✨ *Em đã phân tích idea của sếp với Customer + Market:*\n",
        "━━━━━━━━━━━━━━━━━━━━",
        "*📋 CAMPAIGN REFINED*\n",
        f"🏷️ *Tên:* {refined.get('name', '?')}",
        f"🎯 *Mục tiêu:* {refined.get('goal', '?')}",
        f"🎁 *Cơ chế offer:* {refined.get('key_offer', '?')}",
        f"📅 *Gợi ý độ dài:* {refined.get('duration_suggestion', '?')}",
        f"👥 *Target:* {refined.get('target_segment', '?')}\n",
        "━━━━━━━━━━━━━━━━━━━━",
        f"*📊 VALIDATION* — Mức phù hợp: {score_emoji}\n",
        f"_{validation.get('fit_analysis', '')}_\n",
    ]

    risks = validation.get("risks", [])
    if risks:
        lines.append("⚠️ *Risks cần lưu ý:*")
        for r in risks:
            lines.append(f"  • {r}")
        lines.append("")

    suggestions = validation.get("suggestions", [])
    if suggestions:
        lines.append("💡 *Gợi ý tăng impact:*")
        for s in suggestions:
            lines.append(f"  • {s}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("\n_💰 Budget / 👥 Team / 📅 Thời lượng / 🎟 % giảm — sếp sẽ quyết ở bước sau._\n")
    lines.append("👇 *Sếp OK với campaign này không?*")
    return "\n".join(lines)


# ─── OFFER PACKAGES — 3 gói ưu đãi để chọn nhanh (thay 3 câu hỏi cũ) ──
# BACKLOG #6: founder chọn 1 gói (mức "cho đi" nhẹ/vừa/mạnh, phù hợp
# pricing_approach + Budget/Team đã chốt ở #5) thay vì tự trả lời 3 câu hỏi mở.

PROPOSE_PACKAGES_SYSTEM = """Bạn là Max — CMO AI. Campaign vừa được founder VN chốt, cần đề xuất 3 GÓI ƯU ĐÃI
để founder chọn NHANH 1 gói (thay vì tự trả lời câu hỏi mở về triết lý ưu đãi).

Dựa vào: ngành, campaign (goal/target/key_offer), pricing_approach founder đã chọn ở 8 câu
chiến lược, và Ngân sách/Team hiện tại (nếu có) → đề xuất 3 gói với MỨC "CHO ĐI" khác nhau:
- Gói 1: Nhẹ — giữ giá, mồi bằng giá trị cộng thêm (quà/bundle nhỏ/trải nghiệm)
- Gói 2: Vừa — kết hợp giá trị cộng thêm + ưu đãi có điều kiện
- Gói 3: Mạnh — ưu đãi sâu hơn, có thể giảm giá, kèm ràng buộc rõ (giới hạn số lượng/thời gian)

Mỗi gói gồm:
- "name": tên ngắn gọn tiếng Việt (vd "Mồi nhẹ - giữ giá", "Combo giá trị", "Ưu đãi mạnh - giới hạn")
- "mechanism": cơ chế cụ thể đặc thù NGÀNH (KHÔNG bịa % giảm cụ thể cho gói 1-2; gói 3 có thể có % nếu hợp lý)
- "give_away": mức "cho đi" mô tả TƯƠNG ĐỐI (vd "≤10% hoặc quà tặng nhỏ", "bundle 2-3 sản phẩm, giữ giá lẻ", "giảm sâu 1 lần, giới hạn số suất")
- "constraint": ràng buộc đi kèm để bảo vệ margin (vd "giữ giá gốc trên menu", "giới hạn 50 suất đầu", "chỉ áp dụng khách mới")

OUTPUT BẮT BUỘC dạng JSON (KHÔNG có text khác bên ngoài JSON):

```json
{
  "packages": [
    {"name": "...", "mechanism": "...", "give_away": "...", "constraint": "..."},
    {"name": "...", "mechanism": "...", "give_away": "...", "constraint": "..."},
    {"name": "...", "mechanism": "...", "give_away": "...", "constraint": "..."}
  ]
}
```

QUY TẮC:
- ĐÚNG 3 packages, khác biệt rõ về mức "cho đi" (nhẹ → vừa → mạnh)
- Match ngành + goal + target của campaign
- Nếu Budget/Team nhỏ → gói "mạnh" vẫn phải khả thi vận hành (không yêu cầu outsource/đa kênh nếu team không có)
- KHÔNG bịa số liệu doanh thu/khách hàng
- Output CHỈ JSON trong ```json``` block"""


async def propose_offer_packages(session: Session, campaign: dict) -> Optional[list[dict]]:
    """Đề xuất 3 gói ưu đãi (nhẹ/vừa/mạnh) cho campaign vừa chốt — BACKLOG #6.

    Dùng _build_industry_levers_context + pricing_approach (8 câu chiến lược)
    + Budget/Team (BACKLOG #5) để 3 gói sát ngành + quy mô thật.
    Returns list[dict] 3 packages hoặc None nếu fail.
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError

    industry = (session.profile.industry or "").strip()
    ctx_parts = _build_industry_levers_context(session, industry) if industry else []

    campaign_summary = (
        f"**Campaign đã chốt:**\n"
        f"- Tên: {campaign.get('name', '?')}\n"
        f"- Mục tiêu: {campaign.get('goal', '?')}\n"
        f"- Target: {campaign.get('target_segment', '?')}\n"
        f"- Cơ chế offer (định hướng): {campaign.get('key_offer', '?')}\n"
    )

    import json as _json
    try:
        answers = _json.loads(session.pending_intake.get("_strategy_answers") or "{}")
    except Exception:
        answers = {}
    pricing_block = (
        f"\n## Pricing approach founder đã chọn (8 câu chiến lược):\n{answers['pricing_approach']}\n"
        if answers.get("pricing_approach") else ""
    )

    budget_team_context = (session.pending_intake.get("_budget_team_context") or "").strip()
    if not budget_team_context:
        bt_lines = []
        if session.profile.monthly_marketing_budget:
            bt_lines.append(f"Ngân sách marketing/tháng: {session.profile.monthly_marketing_budget}")
        if session.profile.team_size:
            bt_lines.append(f"Team: {session.profile.team_size}")
        budget_team_context = "\n".join(bt_lines)
    budget_team_block = (
        f"\n## Ngân sách & Team hiện tại:\n{budget_team_context}\n" if budget_team_context else ""
    )

    user_msg = (
        "\n\n".join(ctx_parts) + "\n\n" if ctx_parts else ""
    ) + f"{campaign_summary}{pricing_block}{budget_team_block}\n---\n\nĐề xuất 3 gói ưu đãi (nhẹ/vừa/mạnh) cho campaign trên."

    try:
        result = await router_call(
            task_type=TaskType.INTAKE_JSON,
            system=PROPOSE_PACKAGES_SYSTEM,
            user=user_msg,
            max_tokens=1200,
        )
        text = (result.get("output") or "").strip()
    except AllProvidersFailedError as e:
        logger.warning("propose_offer_packages all providers failed: %s", e)
        return None
    except Exception as e:
        logger.warning("propose_offer_packages failed: %s", e)
        return None

    data = _extract_json(text)
    if not data or "packages" not in data:
        logger.error("propose_offer_packages returned invalid JSON: %s", text[:200])
        return None

    packages = data.get("packages", [])
    if not isinstance(packages, list) or len(packages) < 1:
        return None
    return packages[:3]


def format_packages_card(campaign: dict, packages: list[dict]) -> str:
    """Format 3 gói ưu đãi để user pick 1 (BACKLOG #6)."""
    num_emojis = ["1️⃣", "2️⃣", "3️⃣"]
    lines = [
        f"🎁 *Em đề xuất 3 gói ưu đãi cho campaign \"{campaign.get('name', '?')}\":*",
        "",
        "_(Chọn 1 gói — em sẽ đề xuất cơ chế cụ thể trong khuôn khổ gói đó. "
        "Hoặc \"✏️ Tự định nghĩa\" nếu sếp có hướng riêng.)_",
    ]
    for i, p in enumerate(packages):
        num = num_emojis[i] if i < 3 else f"{i+1}."
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"*{num} {p.get('name', '?')}*")
        lines.append(f"🎯 *Cơ chế:* {p.get('mechanism', '?')}")
        lines.append(f"💸 *Mức cho đi:* {p.get('give_away', '?')}")
        lines.append(f"🔒 *Ràng buộc:* {p.get('constraint', '?')}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


# ─── OFFER LEVERS — AI đề xuất 4 cơ chế offer specific cho campaign ──

PROPOSE_LEVERS_SYSTEM = """Bạn là Max — CMO AI giúp founder VN chọn OFFER LEVER cho campaign vừa chốt.

Bối cảnh: User đã chốt 1 campaign cụ thể. Giờ cần chọn CƠ CHẾ OFFER phù hợp — KHÔNG phải lúc nào cũng là discount %.

🔴 NGUYÊN TẮC CỐT LÕI:
- KHÔNG mặc định discount % — đó là lever YẾU NHẤT cho margin
- Đề xuất 4 levers KHÁC NHAU theo ngành + goal + target của campaign
- VD ngành Beauty/Spa thường dùng: Trial / Bundle liệu trình / GWP / Loyalty
- VD ngành F&B thường dùng: Combo / BOGO / Happy hour / Loyalty card
- VD ngành SaaS thường dùng: Free trial / Annual discount / Freemium / Money-back
- VD ngành Ecom thường dùng: Free shipping / Flash sale / Bundle / Cashback
- VD ngành Education thường dùng: Early bird / Group discount / Free preview / Trả góp
- VD ngành B2B Service thường dùng: Free audit / Pilot project / Performance-based pricing
- VD ngành Real Estate thường dùng: Early commit / Payment plan / Furniture package
- VD ngành Health/Clinic thường dùng: Free consultation / Package / Family plan

Theo Goal:
- Acquisition (khách mới) → Trial, GWP, Sample, Free consultation, Early bird
- Retention (khách cũ) → Loyalty tier, Bundle VIP, Early access, Members-only
- Winback (khách bỏ) → Personal discount, Free upgrade, "We miss you" gift
- Brand awareness → KOL collab, UGC contest (không cần price lever)

Discount % chỉ nên là 1/4 nếu CỰC HỢP — không thì BỎ HẲN.

OUTPUT BẮT BUỘC dạng JSON (KHÔNG có text khác bên ngoài JSON):

```json
{
  "levers": [
    {
      "name": "Tên lever ngắn gọn tiếng Việt (vd: 'Trial buổi đầu', 'Combo 3-buổi', 'GWP tặng kèm', 'Loyalty VIP')",
      "mechanism": "1-2 câu mô tả cơ chế cụ thể",
      "why_fit": "1-2 câu: tại sao lever này hợp với campaign + ngành + target",
      "parameters": [
        {"label": "Tên trường user phải điền (ngắn gọn)", "example": "Ví dụ giá trị cụ thể", "required": true},
        {"label": "Trường 2 (nếu cần)", "example": "...", "required": false}
      ]
    },
    { ... 3 levers còn lại ... }
  ]
}
```

QUY TẮC PARAMETERS:
- Mỗi lever có 1-3 parameters TỐI ĐA
- Parameters là số liệu / điều kiện cụ thể user phải nhập (vd: "Giá trial", "Mức tiết kiệm so giá lẻ", "Điều kiện áp dụng")
- KHÔNG hỏi budget / team / ngày (đã có form chung)
- example phải SPECIFIC theo lever đó

🔑 GIỚI HẠN & TRIẾT LÝ FOUNDER (nếu context có section "## Giới hạn ưu đãi founder đặt"):
- BẮT BUỘC tôn trọng 100%. Founder là người nắm quyền — bạn chỉ đề xuất TRONG khuôn khổ đó.
- Nếu founder nói "mồi bằng tặng thêm giá trị, không giảm giá" → TUYỆT ĐỐI không đề lever discount %.
- Nếu founder đặt trần "giảm tối đa 20%" → mọi lever liên quan giá phải ≤ 20%.
- Nếu founder có ràng buộc "giữ giá gốc trên menu" / "không phá giá" → cơ chế phải tuân thủ.
- Nếu founder nói "để em tự đề xuất" → bạn chủ động đề xuất theo best-practice ngành.

QUY TẮC LEVERS:
- 4 levers PHẢI khác nhau về cơ chế (không trùng 2 levers cùng kiểu discount)
- Match đúng ngành (đừng đề Trial cho ngành F&B, đừng đề BOGO cho Beauty)
- Match đúng goal (Acquisition campaign → đừng đề Loyalty cho khách mới)
- Output CHỈ JSON trong ```json``` block
"""


# Common field — chỉ 1 field THỜI LƯỢNG cho Content Calendar (ngày bắt đầu mặc
# định = hôm nay, ngày kết thúc tự tính từ thời lượng — xem merge_to_brief_fields)
COMMON_FINALIZE_FIELDS = [
    {"label": "Thời lượng campaign", "example": "4 tuần / 6 tuần / 2 tháng"},
]


def _parse_duration_days(text: str) -> int:
    """Parse '4 tuần' / '6 tuần' / '2 tháng' / '30 ngày' → số ngày.
    Default 28 ngày (4 tuần) nếu không parse được."""
    if not text:
        return 28
    m = re.search(r"(\d+)\s*tu[aầ]n", text, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 7
    m = re.search(r"(\d+)\s*th[aá]ng", text, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 30
    m = re.search(r"(\d+)\s*ng[aà]y", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 28


async def propose_offer_levers(session: Session, campaign: dict) -> Optional[list[dict]]:
    """Mode propose levers: AI đề xuất 4 offer levers SPECIFIC cho campaign vừa chốt.

    Returns list[dict] 4 levers hoặc None nếu fail.
    """
    context = _build_ideation_context(session)
    campaign_summary = (
        f"**Campaign đã chốt:**\n"
        f"- Tên: {campaign.get('name', '?')}\n"
        f"- Mục tiêu: {campaign.get('goal', '?')}\n"
        f"- Target: {campaign.get('target_segment', '?')}\n"
        f"- Cơ chế offer (định hướng AI gen trước): {campaign.get('key_offer', '?')}\n"
    )

    # Triết lý + giới hạn ưu đãi do founder đặt (nếu có) → AI phải tôn trọng
    offer_prefs = (session.pending_intake.get("_offer_prefs_raw") or "").strip()
    prefs_block = ""
    if offer_prefs and "tự đề xuất" not in offer_prefs.lower():
        prefs_block = (
            "\n\n## Giới hạn ưu đãi founder đặt (BẮT BUỘC tôn trọng):\n"
            f"_{offer_prefs}_\n"
        )

    user_msg = (
        f"{context}{prefs_block}\n\n---\n\n"
        f"{campaign_summary}\n\n"
        "Đề xuất 4 cách ưu đãi specific cho campaign này, hợp với ngành + goal + target, "
        "VÀ nằm trong giới hạn founder đã đặt (nếu có). "
        "Mỗi cách có parameters cụ thể user phải điền (giá, %, điều kiện...)."
    )

    try:
        response = await client.messages.create(
            model=CLAUDE_SONNET_MODEL,
            max_tokens=2500,
            system=[{"type": "text", "text": PROPOSE_LEVERS_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as e:
        logger.exception("Propose levers API call failed: %s", e)
        return None

    try:
        from tools.token_tracker import track_usage
        track_usage(session, response, label="campaign_levers")
    except Exception:
        pass

    raw = response.content[0].text
    data = _extract_json(raw)
    if not data or "levers" not in data:
        logger.error("Levers proposal returned invalid JSON: %s", raw[:200])
        return None

    levers = data.get("levers", [])
    if not isinstance(levers, list) or len(levers) < 1:
        return None
    return levers[:4]  # cap 4


def format_levers_card(campaign: dict, levers: list[dict]) -> str:
    """Format 4 offer lever options để user pick."""
    lines = [
        f"🎯 *Em đề xuất 4 cách ưu đãi cho campaign \"{campaign.get('name', '?')}\":*",
        "",
        "_(Đây là cơ chế ưu đãi để kéo khách action — không nhất thiết phải discount %. Mỗi cách phù hợp với 1 mục tiêu khác nhau.)_",
        "",
    ]

    emoji_num = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    for i, lever in enumerate(levers):
        num = emoji_num[i] if i < 4 else f"{i+1}."
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"*{num} {lever.get('name', '?')}*")
        lines.append(f"🔧 *Cơ chế:* {lever.get('mechanism', '?')}")
        lines.append(f"💡 *Vì sao hợp:* {lever.get('why_fit', '?')}")
        params = lever.get("parameters", [])
        if params:
            param_labels = [p.get("label", "?") for p in params]
            lines.append(f"📝 *Sếp sẽ điền:* {', '.join(param_labels)}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("\n👇 *Sếp chọn cách ưu đãi nào?*")
    return "\n".join(lines)


def get_finalize_fields(lever: dict) -> list[dict]:
    """Build full finalize field list = lever params + common duration field."""
    fields = list(lever.get("parameters", []) or [])
    fields.extend(COMMON_FINALIZE_FIELDS)
    return fields


def format_dynamic_finalize_form(campaign: dict, lever: dict) -> str:
    """Form động dựa trên lever đã chọn: lever params + Thời lượng campaign
    (ngày bắt đầu mặc định = hôm nay, ngày kết thúc tự tính)."""
    lines = [
        f"✅ *Đã chốt: \"{campaign.get('name', '?')}\"*",
        f"🎟 *Cách ưu đãi:* {lever.get('name', '?')}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "*🔧 Sếp điền chi tiết:*",
        "",
    ]

    # Lever-specific parameters
    for f in (lever.get("parameters", []) or []):
        required_mark = "" if f.get("required", True) else " _(không bắt buộc)_"
        lines.append(f"*{f['label']}*{required_mark}:")
        lines.append(f"_Vd: {f.get('example', '...')}_")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("*📅 Thời lượng (cần cho Content Calendar):*")
    lines.append("")
    suggestion = campaign.get("duration_suggestion") or campaign.get("duration")
    for f in COMMON_FINALIZE_FIELDS:
        lines.append(f"*{f['label']}:*")
        example = f.get("example", "...")
        if suggestion:
            lines.append(f"_Vd: {example} — gợi ý AI cho campaign này: {suggestion}_")
        else:
            lines.append(f"_Vd: {example}_")
        lines.append("")
    lines.append(
        "_Ngày bắt đầu mặc định là hôm nay — em tự tính ngày kết thúc theo "
        "thời lượng sếp chọn._"
    )
    lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(
        "💬 *Copy form trên, điền vào, gửi lại 1 lần.*\n"
        "Em parse xong sẽ chạy Brief Campaign luôn ạ."
    )
    return "\n".join(lines)


def parse_dynamic_finalize_form(text: str, fields: list[dict]) -> tuple[dict, list[str]]:
    """Parse user reply theo fields list (label-based matching).
    Returns (parsed_dict keyed by label, missing_labels).
    """
    parsed = {}
    label_set = {f["label"].lower().strip(): f["label"] for f in fields}

    text_lines = text.split("\n")
    current_label = None
    current_parts: list[str] = []

    def _flush():
        nonlocal current_label, current_parts
        if current_label and current_parts:
            val = " ".join(current_parts).strip()
            # Loại bỏ italic "Vd: ..." nếu user paste cả example
            if val.lower().startswith("vd:") or val.lower().startswith("_vd:"):
                val = ""
            if val:
                parsed[current_label] = val
        current_label = None
        current_parts = []

    for line in text_lines:
        line_stripped = line.strip().lstrip("*_").rstrip("*_")
        if not line_stripped:
            continue

        # Match "Label: value"
        m = re.match(r"^([^:]+?)\s*:\s*(.*)$", line_stripped)
        if m:
            label_input = m.group(1).strip().lower()
            value = m.group(2).strip()
            # Tìm label khớp (substring match)
            matched_label = None
            for lbl_lower, lbl_orig in label_set.items():
                if lbl_lower in label_input or label_input in lbl_lower:
                    matched_label = lbl_orig
                    break
            if matched_label:
                _flush()
                current_label = matched_label
                if value:
                    current_parts = [value]
                else:
                    current_parts = []
                continue

        # Continuation line
        if current_label:
            current_parts.append(line_stripped)

    _flush()

    # Validate required only
    missing = [
        f["label"] for f in fields
        if f.get("required", True) and not parsed.get(f["label"])
    ]
    return parsed, missing


def merge_to_brief_fields(
    campaign: dict,
    lever: dict,
    user_inputs: dict,
) -> dict:
    """Merge AI proposal + lever choice + user params → fields cho campaign_brief.

    campaign_brief consume 4 keys: campaign_name, campaign_goal, duration, key_offer
    """
    duration_text = user_inputs.get("Thời lượng campaign", "")
    duration_days = _parse_duration_days(duration_text)

    # Lever parameters (loại field thời lượng)
    lever_params = {
        k: v for k, v in user_inputs.items()
        if k != "Thời lượng campaign"
    }

    lever_params_text = "\n".join(
        f"- {label}: {value}" for label, value in lever_params.items()
    ) if lever_params else "(không có)"

    return {
        "campaign_name": campaign.get("name", ""),
        "campaign_goal": (
            f"{campaign.get('goal', '')}\n\n"
            f"**Target segment:** {campaign.get('target_segment', 'chưa rõ')}"
        ),
        "duration": (
            f"**Thời lượng:** {duration_text or f'{duration_days} ngày'}\n"
            f"_(Gợi ý từ AI: {campaign.get('duration_suggestion') or campaign.get('duration', 'N/A')})_"
        ),
        "key_offer": (
            f"**Offer Lever:** {lever.get('name', '?')}\n"
            f"**Cơ chế:** {lever.get('mechanism', '?')}\n\n"
            f"**Parameters sếp đã quyết:**\n{lever_params_text}"
        ),
    }


# Backward-compat — không còn dùng nhưng giữ để khỏi break import nếu có
def campaign_to_brief_fields(campaign: dict) -> dict:
    fake_lever = {
        "name": "Chưa chọn lever",
        "mechanism": campaign.get("key_offer", ""),
        "parameters": [],
    }
    return merge_to_brief_fields(campaign, fake_lever, {
        "Ngày bắt đầu": "chưa rõ",
        "Ngày kết thúc": "chưa rõ",
    })
