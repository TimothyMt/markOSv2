"""
SMART Goals Framework — calibrated per industry and business stage.
SMART: Specific / Measurable / Achievable / Relevant / Time-bound
"""

SMART_STAGE_MULTIPLIERS = {
    "idea":   {"growth_rate": 0,    "note": "Validate trước — đừng set revenue targets khi chưa có product-market fit"},
    "mvp":    {"growth_rate": 0.20, "note": "Focus vào retention và referral rate, không phải acquisition scale"},
    "growth": {"growth_rate": 0.15, "note": "Scale cái đang work — đừng experiment quá nhiều cùng lúc"},
    "scale":  {"growth_rate": 0.10, "note": "Efficiency và margin quan trọng hơn growth rate thuần túy"},
}

SMART_GOAL_TEMPLATES = {
    "fnb": [
        {
            "goal_type": "Revenue",
            "template": "Tăng doanh thu {timeframe} từ {current}tr/tháng lên {target}tr/tháng ({growth_rate}% MoM) bằng cách tăng AOV {aov_increase}% và repeat visit rate lên {repeat_target}%",
            "metrics": ["Monthly Revenue", "AOV", "Repeat Visit Rate", "Table Turn Rate"],
            "timeframe_default": "90 ngày",
        },
        {
            "goal_type": "Acquisition",
            "template": "Thu hút {new_customers} khách mới/tháng với CAC < {cac_target}k VND trong {timeframe} thông qua Google Maps optimization và TikTok content",
            "metrics": ["New customers/month", "CAC", "Google Maps Rating"],
            "timeframe_default": "60 ngày",
        },
        {
            "goal_type": "Retention",
            "template": "Tăng repeat visit rate (30 ngày) từ {current_repeat}% lên {target_repeat}% trong {timeframe} qua loyalty program và Zalo OA CRM",
            "metrics": ["Repeat Visit Rate", "Loyalty Members", "Zalo OA Open Rate"],
            "timeframe_default": "90 ngày",
        },
    ],
    "tech_saas": [
        {
            "goal_type": "MRR Growth",
            "template": "Tăng MRR từ {current_mrr}tr lên {target_mrr}tr trong {timeframe} với churn < {churn_target}%/tháng và LTV:CAC > {ltv_cac_target}:1",
            "metrics": ["MRR", "Churn Rate", "LTV:CAC", "CAC Payback Period"],
            "timeframe_default": "90 ngày",
        },
        {
            "goal_type": "Activation",
            "template": "Tăng activation rate (7 ngày) từ {current_activation}% lên {target_activation}% trong {timeframe} bằng cách redesign onboarding flow và trigger aha-moment sớm hơn",
            "metrics": ["Activation Rate Day-7", "Trial-to-Paid CVR", "Time to Value"],
            "timeframe_default": "60 ngày",
        },
        {
            "goal_type": "Retention",
            "template": "Giảm monthly churn từ {current_churn}% xuống {target_churn}% trong {timeframe} qua customer success program và in-app engagement triggers",
            "metrics": ["Monthly Churn Rate", "NRR", "NPS", "Feature Adoption Rate"],
            "timeframe_default": "90 ngày",
        },
    ],
    "ecommerce": [
        {
            "goal_type": "GMV",
            "template": "Tăng monthly GMV từ {current_gmv}tr lên {target_gmv}tr trong {timeframe} với blended ROAS > {roas_target}x và CAC < {cac_target}k VND",
            "metrics": ["Monthly GMV", "Blended ROAS", "CAC", "AOV"],
            "timeframe_default": "90 ngày",
        },
        {
            "goal_type": "Repeat Purchase",
            "template": "Tăng repeat purchase rate (90 ngày) từ {current_repeat}% lên {target_repeat}% trong {timeframe} qua post-purchase email/Zalo flow và loyalty program",
            "metrics": ["Repeat Purchase Rate", "Email Open Rate", "LTV"],
            "timeframe_default": "90 ngày",
        },
    ],
    "education": [
        {
            "goal_type": "Enrollment",
            "template": "Enroll {target_students} học viên cho khóa {cohort_name} trong {timeframe} với CPL < {cpl_target}k VND và enrollment rate > {enrollment_rate_target}%",
            "metrics": ["Enrollments", "CPL", "Enrollment Rate", "Show-up Rate"],
            "timeframe_default": "45 ngày (pre-launch)",
        },
        {
            "goal_type": "Completion & NPS",
            "template": "Đạt completion rate > {completion_target}% và NPS > {nps_target} cho cohort {cohort_name} trong {timeframe} để tạo testimonials và referrals cho cohort tiếp theo",
            "metrics": ["Completion Rate", "NPS", "Referral Rate", "Alumni Upsell Rate"],
            "timeframe_default": "Trong khóa học",
        },
    ],
    "health_beauty": [
        {
            "goal_type": "Booking & Revenue",
            "template": "Đạt {target_bookings} bookings/tháng với utilization rate > {utilization_target}% và avg revenue per visit > {arv_target}k VND trong {timeframe}",
            "metrics": ["Bookings/month", "Utilization Rate", "Revenue per Visit", "No-show Rate"],
            "timeframe_default": "60 ngày",
        },
        {
            "goal_type": "Retention",
            "template": "Tăng repeat client rate (60 ngày) từ {current_repeat}% lên {target_repeat}% trong {timeframe} qua follow-up protocol và membership program",
            "metrics": ["Repeat Client Rate", "Package Uptake Rate", "Membership Count"],
            "timeframe_default": "90 ngày",
        },
    ],
    "retail": [
        {
            "goal_type": "Same-store Sales",
            "template": "Tăng same-store sales {growth_target}% trong {timeframe} bằng cách tăng ATV {atv_increase}% và conversion rate từ {current_cvr}% lên {target_cvr}%",
            "metrics": ["Same-store Sales Growth", "ATV", "Conversion Rate", "UPT"],
            "timeframe_default": "90 ngày",
        },
    ],
    "b2b_service": [
        {
            "goal_type": "MRR & Retention",
            "template": "Tăng MRR từ {current_mrr}tr lên {target_mrr}tr trong {timeframe} với client retention > {retention_target}% và tỷ lệ retainer revenue > {retainer_pct}% total",
            "metrics": ["MRR", "Client Retention Rate", "Retainer %", "NRR"],
            "timeframe_default": "90 ngày",
        },
        {
            "goal_type": "Pipeline",
            "template": "Build pipeline {pipeline_value}tr trong {timeframe} với {qualified_leads} qualified leads/tháng và win rate > {win_rate_target}%",
            "metrics": ["Pipeline Value", "Qualified Leads/month", "Win Rate", "Sales Cycle Length"],
            "timeframe_default": "60 ngày",
        },
    ],
    "real_estate": [
        {
            "goal_type": "Transactions",
            "template": "Đóng {target_transactions} giao dịch trong {timeframe} với CPQL < {cpql_target}k VND và lead-to-viewing rate > {viewing_rate_target}%",
            "metrics": ["Transactions", "CPQL", "Lead-to-Viewing Rate", "Sales Cycle Length"],
            "timeframe_default": "90 ngày",
        },
    ],
}


def get_smart_templates(industry: str) -> list[dict]:
    return SMART_GOAL_TEMPLATES.get(industry, [])


def format_smart_prompt(industry: str, stage: str, goals: list[str]) -> str:
    """Build instruction text for AI to generate SMART goals."""
    templates = get_smart_templates(industry)
    stage_info = SMART_STAGE_MULTIPLIERS.get(stage, SMART_STAGE_MULTIPLIERS["growth"])

    lines = [
        "## SMART Goals Framework",
        "",
        f"**Stage hiện tại**: {stage.upper()} — {stage_info['note']}",
        "",
        "Hãy xây dựng SMART goals theo nguyên tắc:",
        "- **S**pecific: Mục tiêu đủ cụ thể, không mơ hồ",
        "- **M**easurable: Có con số đo được rõ ràng",
        "- **A**chievable: Thực tế với nguồn lực hiện có (không quá dễ, không unrealistic)",
        "- **R**elevant: Liên quan trực tiếp đến business goal",
        "- **T**ime-bound: Có deadline rõ ràng",
        "",
        "**Mục tiêu founder đề ra**: " + ", ".join(goals) if goals else "Tăng doanh thu và khách hàng",
        "",
        "**SMART Goal Templates cho ngành này**:",
    ]

    for tmpl in templates:
        lines += [
            f"",
            f"**{tmpl['goal_type']}** (timeframe mặc định: {tmpl['timeframe_default']}):",
            f"_{tmpl['template']}_",
            f"KPIs cần track: {', '.join(tmpl['metrics'])}",
        ]

    lines += [
        "",
        "Dựa trên thông tin business đã thu thập, hãy điền vào template phù hợp với con số THỰC TẾ,",
        "không dùng placeholder. Ưu tiên 2-3 SMART goals quan trọng nhất, không liệt kê tất cả.",
    ]

    return "\n".join(lines)
