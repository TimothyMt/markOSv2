"""
Campaign Execution Plan — Tờ lệnh thực thi sau brief + funnel map.

Input:  session + funnel_map (list từ funnel_mapper) + campaign goal
Output: Telegram-formatted execution roadmap:
          - Hoạt động cụ thể theo ToFu / MoFu / BoFu
          - Thứ tự skills Layer 3 cần chạy tiếp theo
"""
from __future__ import annotations

import logging

from storage.models import Session

logger = logging.getLogger(__name__)


EXECUTION_SYSTEM = """Bạn là Max — CMO AI. Campaign Brief + Funnel Map đã xong.
Viết **Kế hoạch thực thi ngắn** cho founder dựa trên goal type + funnel map + ngành.

QUY TẮC OUTPUT (Telegram):
- Dòng 1: "🗓 *Kế hoạch thực thi — [campaign_name]*\\n_Goal: [goal_type hiển thị đẹp]_"
- 4 section liên tiếp, mỗi section 2-3 bullet activity CỤ THỂ bám ngành:
    🔵 *ToFu — Tiếp cận tệp mới*
    🟡 *MoFu — Nurture & Trust*
    🟢 *BoFu — Chốt & Convert*
    ♻️ *Retention — Giữ data & tối ưu ROI* _(LUÔN CÓ — kể cả campaign acquisition/brand)_
- Mỗi bullet: "• [Tên hoạt động VN ngắn gọn] ← `[skill_name]`"
- Cuối: "*🚀 Thứ tự ưu tiên chạy tiếp:*" → 3-5 bước có số thứ tự, mỗi bước 1 dòng;
  bước CUỐI LUÔN là retention (giữ chân khách vừa thu được từ campaign này).
- Dòng cuối: "_Sếp muốn bắt đầu từ bước nào? Em run luôn._"
- Tổng ≤ 26 dòng. KHÔNG bịa số liệu. Dùng đúng tên skill có sẵn.

🔴 RETENTION LÀ BẮT BUỘC MỌI CAMPAIGN:
- Mọi campaign đều thu data khách (lead/người mua). KHÔNG để lãng phí.
- Dù goal là acquisition/brand/revenue, section ♻️ Retention vẫn phải có 3 ý:
  1. Thu + gắn tag data khách campaign này (`retention_strategy`)
  2. Chuỗi nuôi lead CHƯA chuyển đổi → kéo về mua (`email_zalo_sequence`)
  3. Chuỗi chăm sóc khách ĐÃ mua → giữ chân/tăng repeat (`email_zalo_sequence`)
- Mục tiêu: tối ưu ROI dài hạn — không bỏ sót lead chưa mua, biến khách
  1-lần thành khách lặp lại.

SKILLS CÓ SẴN (dùng đúng tên trong backtick):
- `ads_generator`        — copy quảng cáo ToFu / MoFu / BoFu
- `video_script_gen`        — kịch bản TikTok / Reels / Shorts
- `email_zalo_sequence`  — chuỗi nurture Email + Zalo (3-7 tin)
- `sales_inbox_script`   — kịch bản chốt inbox / DM / Zalo chat
- `post_batch`           — caption + hook bài đăng organic
- `content_calendar`     — lịch đăng (đã auto-gen, sếp có thể tái chạy)
- `retention_strategy`   — hệ thống giữ chân khách cũ
- `winback_campaign`     — thu hồi khách đã bỏ quên

RÀNG BUỘC THEO GOAL TYPE:
- acquisition  → ưu tiên: ads_generator → email_zalo_sequence → sales_inbox_script
- revenue/upsell → ưu tiên: email_zalo_sequence → ads_generator → sales_inbox_script
- brand/awareness → ưu tiên: video_script_gen → ads_generator → post_batch
- retention    → ưu tiên: retention_strategy → email_zalo_sequence → winback_campaign
- mix          → balance acquisition + brand"""


_GOAL_TYPE_LABELS = {
    "acquisition":  "Acquisition — Thu khách mới",
    "revenue":      "Revenue — Tăng doanh thu / AOV",
    "brand":        "Brand — Nhận diện thương hiệu",
    "retention":    "Retention — Giữ chân & Winback",
    "mix":          "Mix — Đa mục tiêu",
}

_OBJ_MAP = {
    "acquisition": "conversion",
    "revenue":     "conversion",
    "brand":       "awareness",
    "retention":   "mix",
    "mix":         "mix",
}

# Lớp retention BẮT BUỘC chèn vào mọi campaign không-phải-retention.
# Mọi campaign đều thu data khách → không để lãng phí, tối ưu ROI dài hạn.
# Nuôi CẢ 2 nhóm: đã mua (giữ chân/repeat) + chưa mua (kéo về chuyển đổi).
_RETENTION_BASELINE = (
    "♻️ *Retention — Giữ data & tối ưu ROI* _(luôn chạy)_\n"
    "• Thu + gắn tag data khách campaign này (lead/mua) ← `retention_strategy`\n"
    "• Chuỗi nuôi lead CHƯA chuyển đổi → kéo về mua ← `email_zalo_sequence`\n"
    "• Chuỗi chăm sóc khách ĐÃ mua → tăng repeat ← `email_zalo_sequence`\n\n"
)

_FALLBACK_ACTIVITIES = {
    "acquisition": (
        "🔵 *ToFu — Tiếp cận tệp mới*\n"
        "• Ads video hook 3 giây tiếp cận cold audience ← `ads_generator`\n"
        "• Kịch bản TikTok/Reels awareness ← `video_script_gen`\n\n"
        "🟡 *MoFu — Nurture & Trust*\n"
        "• Chuỗi Email/Zalo nurture 5 ngày ← `email_zalo_sequence`\n"
        "• Kịch bản chăm lead qua inbox/Zalo ← `sales_inbox_script`\n\n"
        "🟢 *BoFu — Chốt & Convert*\n"
        "• Ads retarget tệp ấm + offer ← `ads_generator`\n"
        "• Kịch bản chốt inbox/DM ← `sales_inbox_script`\n\n"
        + _RETENTION_BASELINE +
        "*🚀 Thứ tự ưu tiên chạy tiếp:*\n"
        "1. `ads_generator` (ToFu + BoFu retarget)\n"
        "2. `email_zalo_sequence` (nurture lead)\n"
        "3. `sales_inbox_script` (chốt cuối phễu)\n"
        "4. `retention_strategy` (giữ chân khách vừa thu — tối ưu ROI)"
    ),
    "revenue": (
        "🔵 *ToFu — Nhắc nhớ & Re-engage*\n"
        "• Post giá trị + showcase sản phẩm ← `post_batch`\n\n"
        "🟡 *MoFu — Upsell & Cross-sell*\n"
        "• Chuỗi Email/Zalo upsell 3-5 ngày ← `email_zalo_sequence`\n"
        "• Ads retarget khách đã mua ← `ads_generator`\n\n"
        "🟢 *BoFu — Chốt nâng đơn*\n"
        "• Bundle / combo offer reveal ← `ads_generator`\n"
        "• Kịch bản inbox upsell ← `sales_inbox_script`\n\n"
        + _RETENTION_BASELINE +
        "*🚀 Thứ tự ưu tiên chạy tiếp:*\n"
        "1. `email_zalo_sequence` (upsell sequence)\n"
        "2. `ads_generator` (BoFu retarget)\n"
        "3. `sales_inbox_script` (chốt upsell)\n"
        "4. `retention_strategy` (giữ chân + tăng repeat — tối ưu ROI)"
    ),
    "brand": (
        "🔵 *ToFu — Viral & Awareness*\n"
        "• Kịch bản video hook TikTok/Reels ← `video_script_gen`\n"
        "• Ads reach rộng cold audience ← `ads_generator`\n\n"
        "🟡 *MoFu — Education & Trust*\n"
        "• Caption + hook bài educate ← `post_batch`\n"
        "• Content pillar Educate + Engage ← `content_calendar`\n\n"
        "🟢 *BoFu — Social Proof & CTA nhẹ*\n"
        "• Testimonial + case study ads ← `ads_generator`\n\n"
        + _RETENTION_BASELINE +
        "*🚀 Thứ tự ưu tiên chạy tiếp:*\n"
        "1. `video_script_gen` (hero content viral)\n"
        "2. `ads_generator` (ToFu reach)\n"
        "3. `post_batch` (organic amplify)\n"
        "4. `retention_strategy` (giữ data follower/lead thu được — tối ưu ROI)"
    ),
    "retention": (
        "🔵 *ToFu — Re-attract khách cũ*\n"
        "• Post nhắc nhớ + value showcase ← `post_batch`\n\n"
        "🟡 *MoFu — Nurture & Loyalty*\n"
        "• Hệ thống giữ chân + loyalty tier ← `retention_strategy`\n"
        "• Chuỗi Zalo/Email re-engage ← `email_zalo_sequence`\n\n"
        "🟢 *BoFu — Winback & Re-activate*\n"
        "• Campaign thu hồi khách bỏ quên ← `winback_campaign`\n"
        "• Kịch bản inbox cá nhân hoá ← `sales_inbox_script`\n\n"
        "*🚀 Thứ tự ưu tiên chạy tiếp:*\n"
        "1. `retention_strategy` (xây hệ thống trước)\n"
        "2. `email_zalo_sequence` (re-engage sequence)\n"
        "3. `winback_campaign` (khách bỏ > 60 ngày)"
    ),
}


def classify_goal_type(campaign_goal: str) -> str:
    """Map campaign_goal text → slug: acquisition / revenue / brand / retention / mix."""
    g = (campaign_goal or "").lower()
    if any(k in g for k in ("acquisition", "khách mới", "thu lead", "thu khách", "khách hàng mới")):
        return "acquisition"
    if any(k in g for k in ("upsell", "aov", "doanh thu", "tăng giá trị", "revenue", "giỏ hàng", "repeat")):
        return "revenue"
    if any(k in g for k in ("brand", "awareness", "nhận diện", "positioning", "viral", "thương hiệu")):
        return "brand"
    if any(k in g for k in ("retention", "giữ chân", "khách cũ", "quay lại", "winback", "churn")):
        return "retention"
    return "mix"


def funnel_map_objective(goal_type: str) -> str:
    """Map goal_type slug → funnel_mapper objective key."""
    return _OBJ_MAP.get(goal_type, "mix")


async def generate_execution_plan(
    session: Session,
    funnel_map: list,
    campaign_name: str,
    campaign_goal: str,
) -> str:
    """Sinh execution roadmap từ funnel_map + goal type.

    Router: Haiku → GPT-5-mini → GPT-5 (CRITIC_REVIEW chain).
    Fallback về hardcode per goal type nếu LLM lỗi.
    """
    from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
    import json as _json

    goal_type = classify_goal_type(campaign_goal)
    goal_label = _GOAL_TYPE_LABELS.get(goal_type, goal_type)

    user_msg = (
        f"# CAMPAIGN\n"
        f"- Tên: {campaign_name}\n"
        f"- Goal: {campaign_goal}\n"
        f"- Goal type: {goal_type} ({goal_label})\n"
        f"- Ngành: {session.profile.industry or 'chưa rõ'}\n\n"
        f"# FUNNEL MAP (per channel)\n"
        + _json.dumps(funnel_map, ensure_ascii=False, indent=2)
        + "\n\nViết execution roadmap theo đúng format yêu cầu trong system prompt."
    )

    try:
        result = await router_call(
            task_type=TaskType.CRITIC_REVIEW,   # Haiku → GPT-5-mini → GPT-5
            system=EXECUTION_SYSTEM,
            user=user_msg,
            max_tokens=1500,
        )
        text = (result.get("output") or "").strip()
        provider = result.get("provider", "unknown")
        if provider != "anthropic_haiku":
            logger.info("execution_plan fallover to provider=%s", provider)
        return text if text else _fallback_plan(campaign_name, goal_type)
    except AllProvidersFailedError as e:
        logger.warning("generate_execution_plan all providers failed: %s", e)
        return _fallback_plan(campaign_name, goal_type)
    except Exception as e:
        logger.warning("generate_execution_plan failed: %s", e)
        return _fallback_plan(campaign_name, goal_type)


def _fallback_plan(campaign_name: str, goal_type: str) -> str:
    activities = _FALLBACK_ACTIVITIES.get(goal_type, _FALLBACK_ACTIVITIES["acquisition"])
    label = _GOAL_TYPE_LABELS.get(goal_type, goal_type)
    return (
        f"🗓 *Kế hoạch thực thi — {campaign_name}*\n"
        f"_Goal: {label}_\n\n"
        f"{activities}\n\n"
        "_Sếp muốn bắt đầu từ bước nào? Em run luôn._"
    )
