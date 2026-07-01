"""
Campaign Scope Library — Sprint 4.

Industry-aware campaign scopes: recommended channels, KPIs, campaign types,
offer mechanisms. Injected into Campaign Brief system prompt để LLM
đưa ra gợi ý phù hợp ngành thay vì generic.

8 industries được support: fnb, tech_saas, ecommerce, education,
health_beauty, retail, b2b_service, real_estate.
"""

SCOPE_LIBRARY: dict[str, dict] = {
    "fnb": {
        "label": "F&B / Nhà hàng / Quán",
        "top_channels": ["Facebook", "TikTok", "Zalo OA", "Google Maps"],
        "campaign_types": ["Flash sale giờ vàng", "Combo deal", "Loyalty stamp card",
                           "UGC Food Review", "Seasonal menu launch", "Birthday offer"],
        "offer_mechanisms": ["Free appetizer đơn đầu tiên", "Buy 2 get 1",
                             "Loyalty điểm đổi quà", "Happy hour -30%",
                             "Group deal (4+ người)", "Delivery first-order discount"],
        "kpis": ["Foot traffic", "Table turnover", "AOV", "Repeat rate", "Delivery GMV"],
        "content_pillars": ["Món mới / Seasonal", "Behind the scenes (bếp/team)",
                            "Customer UGC review", "Tips / Recipe", "Offer / Flash sale"],
        "typical_duration": "2-4 tuần",
    },
    "tech_saas": {
        "label": "Tech / SaaS / App",
        "top_channels": ["LinkedIn", "Facebook", "Email", "Google Ads", "YouTube"],
        "campaign_types": ["Free trial activation", "Webinar / Demo day", "Case study series",
                           "Feature launch", "Referral program", "Annual plan push"],
        "offer_mechanisms": ["Extended free trial", "Onboarding session miễn phí",
                             "Annual plan giảm 30%", "White-glove setup",
                             "Partner co-marketing", "ROI calculator tool"],
        "kpis": ["Trial signups", "Trial-to-paid conversion", "MRR", "CAC", "NPS", "Churn rate"],
        "content_pillars": ["Product demo / How-to", "Customer success story",
                            "Industry insight", "Comparison vs competitor", "ROI / Data proof"],
        "typical_duration": "3-6 tuần",
    },
    "ecommerce": {
        "label": "Thương mại điện tử / Bán lẻ online",
        "top_channels": ["Facebook", "TikTok Shop", "Shopee", "Lazada", "Instagram", "Email"],
        "campaign_types": ["Mega sale (1/1, 9/9...)", "Flash sale 24h", "Bundle deal",
                           "Free shipping campaign", "New collection launch", "VIP member sale"],
        "offer_mechanisms": ["Voucher stacking", "Flash sale countdown",
                             "Free gift with purchase", "Cashback coin",
                             "Referral discount", "Early bird exclusive"],
        "kpis": ["GMV", "Conversion rate", "ROAS", "AOV", "Cart abandonment", "Return rate"],
        "content_pillars": ["Product showcase", "Unboxing / Review UGC",
                            "Before/After", "Tutorial / How to use", "Flash sale alert"],
        "typical_duration": "1-2 tuần (sale) / 4 tuần (collection)",
    },
    "education": {
        "label": "Giáo dục / Đào tạo / Khóa học",
        "top_channels": ["Facebook Group", "YouTube", "TikTok", "Email", "Zalo Group"],
        "campaign_types": ["Early bird enrollment", "Free workshop/webinar",
                           "Challenge 7/14/21 ngày", "Alumni success story",
                           "Scholarship program", "Cohort launch"],
        "offer_mechanisms": ["Early bird -40%", "Chia trả góp 0%",
                             "Free bonus module", "1-1 coaching session",
                             "Community access lifetime", "Certification fast-track"],
        "kpis": ["Lead gen", "Webinar attendance", "Enrollment rate", "Completion rate",
                 "Referral rate", "NPS"],
        "content_pillars": ["Free value / Tips", "Student transformation story",
                            "Instructor credibility", "Curriculum preview", "FAQ / Objection handle"],
        "typical_duration": "3-4 tuần (enrollment) / 7 ngày (flash)f",
    },
    "health_beauty": {
        "label": "Sức khoẻ / Làm đẹp / Spa / Skincare",
        "top_channels": ["TikTok", "Instagram", "Facebook", "Zalo OA", "YouTube"],
        "campaign_types": ["Before/After transformation", "Product launch + review",
                           "Skin concern education series", "Seasonal skincare routine",
                           "Spa package deal", "Bundle + gift set"],
        "offer_mechanisms": ["Sample trial kit", "Buy routine get free serum",
                             "Membership card", "Skin consultation miễn phí",
                             "Referral a friend + both get discount", "Flash set giá tốt"],
        "kpis": ["Trial kit conversions", "Repeat purchase rate", "Instagram ER",
                 "TikTok views", "Booking rate (spa)", "AOV"],
        "content_pillars": ["Before/After real result", "Ingredient education",
                            "Routine tutorial", "Expert/Doctor tips", "UGC reviews"],
        "typical_duration": "3-4 tuần",
    },
    "retail": {
        "label": "Bán lẻ offline / Chuỗi cửa hàng",
        "top_channels": ["Facebook", "Zalo OA", "Google Business", "SMS/Push notification"],
        "campaign_types": ["Store opening promotion", "Seasonal clearance",
                           "Loyalty member day", "In-store event",
                           "Buy online pick up in store", "Cross-sell bundle"],
        "offer_mechanisms": ["Member-only price", "Stamp card đổi quà",
                             "Giảm thêm khi thanh toán ví điện tử",
                             "Mua nhiều giảm nhiều", "Free gift wrapping",
                             "Layaway / trả góp tại quầy"],
        "kpis": ["Foot traffic", "Same-store sales", "Conversion rate in-store",
                 "Basket size", "Loyalty program enrollment", "NPS"],
        "content_pillars": ["New arrivals / Stock alert", "Style guide / How to match",
                            "Store experience", "Sale countdown", "Staff pick"],
        "typical_duration": "1-4 tuần",
    },
    "b2b_service": {
        "label": "B2B / Dịch vụ doanh nghiệp",
        "top_channels": ["LinkedIn", "Email", "Facebook", "Google Ads", "Webinar"],
        "campaign_types": ["Thought leadership content", "ROI case study",
                           "Free audit / assessment", "Joint webinar với partner",
                           "End-of-quarter push", "Pilot program"],
        "offer_mechanisms": ["Free initial audit", "Pilot 30 ngày không cam kết",
                             "ROI guarantee", "Co-marketing với partner",
                             "Referral fee cho introducer", "Volume pricing"],
        "kpis": ["Qualified leads", "SQL rate", "Pipeline value", "Deal cycle time",
                 "Win rate", "Contract renewal rate"],
        "content_pillars": ["Industry insight / Report", "Case study with numbers",
                            "Process explainer", "Team & credential",
                            "Comparison / Why us"],
        "typical_duration": "4-8 tuần",
    },
    "real_estate": {
        "label": "Bất động sản / Môi giới / Căn hộ",
        "top_channels": ["Facebook", "YouTube", "Zalo", "Google Ads", "OOH + digital retargeting"],
        "campaign_types": ["Project launch event", "Virtual tour series",
                           "Investor briefing", "Early access / Priority booking",
                           "Referral agent network", "Lifestyle content series"],
        "offer_mechanisms": ["Ưu đãi booking giai đoạn đầu", "Hỗ trợ lãi suất 0% 24T",
                             "Gift package nội thất", "Chiết khấu qua giới thiệu",
                             "Thanh toán linh hoạt 10-15-20%",
                             "Bảo lãnh cho thuê cam kết"],
        "kpis": ["Leads", "Site visits", "Booking rate", "Referral conversions",
                 "Cost per qualified lead", "Revenue per agent"],
        "content_pillars": ["Project showcase / Render", "Location advantage",
                            "Developer credibility", "Investor ROI analysis",
                            "Lifestyle aspiration", "Booking progress update"],
        "typical_duration": "4-12 tuần",
    },
}


def get_scope(industry: str) -> dict:
    """Return scope dict cho industry. Fallback về ecommerce nếu không tìm thấy."""
    return SCOPE_LIBRARY.get(industry, SCOPE_LIBRARY["ecommerce"])


def format_scope_for_prompt(industry: str) -> str:
    """Format scope thành text block để inject vào LLM prompt."""
    scope = get_scope(industry)
    lines = [
        f"## 📐 Campaign Scope — {scope['label']}",
        f"**Kênh phù hợp nhất:** {', '.join(scope['top_channels'][:4])}",
        f"**Loại campaign phổ biến:** {', '.join(scope['campaign_types'][:4])}",
        f"**Offer mechanism hay dùng:** {', '.join(scope['offer_mechanisms'][:4])}",
        f"**KPIs quan trọng:** {', '.join(scope['kpis'][:4])}",
        f"**Content pillars:** {', '.join(scope['content_pillars'][:3])}",
        f"**Timeline thông thường:** {scope.get('typical_duration', '2-4 tuần')}",
    ]
    return "\n".join(lines)
