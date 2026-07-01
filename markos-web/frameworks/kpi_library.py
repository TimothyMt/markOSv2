"""
KPI Library — Pre-calibrated frameworks for each industry.
Intake agent detects industry → load matching KPIFramework → inject into all downstream agents.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class KPIFramework:
    industry: str
    display_name: str
    primary_kpis: list[dict]       # KPIs mà mọi business trong ngành PHẢI đo
    secondary_kpis: list[dict]     # KPIs quan trọng nhưng tùy stage
    vanity_kpis: list[dict]        # KPIs trông đẹp nhưng không drive decision
    benchmarks: dict               # Benchmark numbers theo stage
    unit_economics: dict           # Công thức tính unit economics của ngành
    growth_levers: list[str]       # Đòn bẩy tăng trưởng chính của ngành
    channel_priority: list[str]    # Kênh marketing ưu tiên theo ngành
    tam_methodology: str           # Cách ước lượng TAM phù hợp ngành
    context_note: str              # Lưu ý đặc thù ngành cho AI agents


KPI_LIBRARY: dict[str, KPIFramework] = {

    # ─────────────────────────────────────────────────────────────────
    # F&B: Nhà hàng, Cà phê, Quán ăn, Food Delivery, Cloud Kitchen
    # ─────────────────────────────────────────────────────────────────
    "fnb": KPIFramework(
        industry="fnb",
        display_name="F&B (Nhà hàng / Cà phê / Quán ăn)",
        primary_kpis=[
            {"name": "Average Order Value (AOV)", "formula": "Doanh thu / Số đơn", "target": "Tăng 15-25% so với baseline"},
            {"name": "Table Turn Rate", "formula": "Số lượt khách / Số bàn / Ca", "target": "> 2.0 cho bữa trưa, > 1.5 cho tối"},
            {"name": "Repeat Visit Rate (30 ngày)", "formula": "Khách quay lại / Tổng khách", "target": "> 30% trong tháng đầu"},
            {"name": "Cost of Goods Sold (COGS) %", "formula": "Giá vốn / Doanh thu", "target": "< 30% cho café, < 35% cho nhà hàng"},
            {"name": "Revenue per Square Meter", "formula": "Doanh thu tháng / Diện tích (m²)", "target": "Benchmark theo phân khúc"},
            {"name": "Google Maps Rating × Review Volume", "formula": "Rating ≥ 4.3 + > 200 reviews", "target": "Cần cả hai yếu tố"},
        ],
        secondary_kpis=[
            {"name": "Delivery % of Total Revenue", "formula": "Doanh thu app / Tổng doanh thu", "target": "< 40% để không bị phụ thuộc platform"},
            {"name": "Customer Acquisition Cost (CAC)", "formula": "Chi phí marketing / Khách mới", "target": "< 1 lần AOV"},
            {"name": "Peak Hour Utilization", "formula": "Capacity used / Total capacity", "target": "> 80% trong giờ cao điểm"},
            {"name": "Staff Cost %", "formula": "Chi phí nhân sự / Doanh thu", "target": "< 30%"},
            {"name": "Net Promoter Score (NPS)", "formula": "% Promoters - % Detractors", "target": "> 50"},
        ],
        vanity_kpis=[
            {"name": "Lượt follow Facebook/Instagram", "why": "Không liên quan trực tiếp đến revenue"},
            {"name": "Reach/Impression của bài post", "why": "Không đo được conversion về offline"},
            {"name": "Số lượng check-in", "why": "Tốt nhưng không predict revenue"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "30-80 triệu VND", "repeat_rate": "> 20%", "google_rating": "> 4.0"},
            "growth": {"monthly_revenue": "100-500 triệu VND", "repeat_rate": "> 30%", "google_rating": "> 4.3"},
            "scale": {"monthly_revenue": "> 500 triệu VND", "repeat_rate": "> 40%", "google_rating": "> 4.5"},
        },
        unit_economics={
            "ltv_formula": "AOV × Avg visits/year × Avg customer lifespan (years)",
            "payback_period": "CAC / (AOV × Gross Margin %)",
            "break_even": "Fixed costs / (1 - Variable cost %)",
        },
        growth_levers=[
            "Tăng AOV qua upsell & bundle (hiệu quả nhất, không tốn CAC)",
            "Tăng frequency qua loyalty program (stamp card, app points)",
            "Mở rộng giờ phục vụ / daypart mới (breakfast nếu chỉ có lunch)",
            "Delivery để mở rộng bán kính phục vụ mà không mở thêm mặt bằng",
            "UGC: Khuyến khích khách check-in, review đổi voucher",
            "Corporate catering / B2B để fill capacity ngày thường",
        ],
        channel_priority=[
            "Google Maps & Google Business Profile (priority #1 — intent-based)",
            "Facebook Ads (retargeting địa lý 3-5km)",
            "TikTok (viral food content — đặc biệt cà phê & món đặc sắc)",
            "Shopee Food / GrabFood (acquisition nhưng cẩn thận margin)",
            "Zalo OA (CRM & loyalty — chi phí thấp, reach cao)",
            "Instagram (thương hiệu, aesthetic)",
        ],
        tam_methodology="Bottom-up: (Dân số trong bán kính 3km × % target segment × Dining frequency/month × AOV) × 12",
        context_note="FnB là ngành hyperlocal — mọi strategy phải bắt đầu từ bán kính 1-5km. Repeat purchase và word-of-mouth quan trọng hơn acquisition. COGS và staff cost là hai killer chính — phải kiểm soát trước khi scale marketing.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Tech SaaS / App / Digital Product
    # ─────────────────────────────────────────────────────────────────
    "tech_saas": KPIFramework(
        industry="tech_saas",
        display_name="Tech SaaS / App / Digital Product",
        primary_kpis=[
            {"name": "Monthly Recurring Revenue (MRR)", "formula": "Số subscribers × ARPU", "target": "MoM growth > 15% ở giai đoạn growth"},
            {"name": "Churn Rate", "formula": "Khách hủy / Tổng khách đầu tháng", "target": "< 5%/tháng (B2C), < 2%/tháng (B2B)"},
            {"name": "LTV:CAC Ratio", "formula": "LTV / CAC", "target": "> 3:1 để sustainable, > 5:1 để scale"},
            {"name": "Activation Rate", "formula": "Users đạt aha-moment / Total signups", "target": "> 40% trong 7 ngày đầu"},
            {"name": "Net Revenue Retention (NRR)", "formula": "(MRR đầu + Expansion - Churn - Contraction) / MRR đầu", "target": "> 100% = healthy growth"},
            {"name": "CAC Payback Period", "formula": "CAC / (ARPU × Gross Margin %)", "target": "< 12 tháng (B2C), < 18 tháng (B2B)"},
        ],
        secondary_kpis=[
            {"name": "Daily/Monthly Active Users (DAU/MAU)", "formula": "DAU / MAU", "target": "> 20% DAU/MAU ratio = sticky product"},
            {"name": "Trial-to-Paid Conversion Rate", "formula": "Paid users / Trial users", "target": "> 15% (B2C), > 25% (B2B)"},
            {"name": "Expansion MRR", "formula": "Upsell + Cross-sell MRR/tháng", "target": "> 20% of new MRR"},
            {"name": "NPS Score", "formula": "% Promoters - % Detractors", "target": "> 40"},
            {"name": "Feature Adoption Rate", "formula": "Users dùng feature / Total users", "target": "Core feature > 60%"},
        ],
        vanity_kpis=[
            {"name": "Total registered users", "why": "Không phản ánh engagement hoặc revenue"},
            {"name": "App downloads", "why": "Download ≠ activation ≠ retention"},
            {"name": "Page views / Sessions", "why": "Không liên quan đến revenue nếu không track conversion"},
        ],
        benchmarks={
            "mvp": {"mrr": "< 50 triệu VND", "churn": "< 10%/tháng OK", "ltv_cac": "> 2:1 là ổn"},
            "growth": {"mrr": "50-500 triệu VND", "churn": "< 5%/tháng", "ltv_cac": "> 3:1"},
            "scale": {"mrr": "> 500 triệu VND", "churn": "< 2%/tháng", "ltv_cac": "> 5:1"},
        },
        unit_economics={
            "ltv_formula": "ARPU / Churn Rate",
            "cac_formula": "Total Sales & Marketing spend / New customers acquired",
            "magic_number": "Net New ARR / S&M Spend (> 0.75 là efficient)",
        },
        growth_levers=[
            "Product-led growth: Free tier → viral loop → paid conversion",
            "Content marketing + SEO: Compound, thấp CAC dài hạn",
            "Integration & partnerships: Distribution qua ecosystem của sản phẩm khác",
            "Community building: Users dạy users → giảm support cost, tăng retention",
            "Customer success: Proactive onboarding giảm churn, tăng expansion",
            "Referral program: B2B word-of-mouth có conversion rate cao nhất",
        ],
        channel_priority=[
            "SEO / Content Marketing (compound, low CAC dài hạn)",
            "Product Hunt / AppSumo (launch burst, early adopters)",
            "LinkedIn Ads (B2B targeting chính xác)",
            "Google Ads — intent keywords (người đang search solution)",
            "YouTube / TikTok tutorials (educate + convert)",
            "Partner/Integration marketplace",
        ],
        tam_methodology="Top-down: Tổng thị trường phần mềm phân khúc × % có thể tiếp cận. Bottom-up: Số ICP companies/users × ARPU × 12",
        context_note="SaaS là ngành mà retention quan trọng hơn acquisition — churn cao sẽ giết growth dù acquisition tốt. Tập trung activation (aha-moment trong 7 ngày đầu) trước khi scale paid acquisition. LTV:CAC là chỉ số kinh tế đơn vị quan trọng nhất.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # E-commerce / Thương mại điện tử
    # ─────────────────────────────────────────────────────────────────
    "ecommerce": KPIFramework(
        industry="ecommerce",
        display_name="E-commerce / Thương mại điện tử",
        primary_kpis=[
            {"name": "Return on Ad Spend (ROAS)", "formula": "Doanh thu từ ads / Chi phí ads", "target": "> 3x (Shopee), > 4x (Meta/TikTok)"},
            {"name": "Repeat Purchase Rate", "formula": "Khách mua ≥ 2 lần / Tổng khách", "target": "> 25% trong 90 ngày"},
            {"name": "Cart Abandonment Rate", "formula": "Giỏ hàng bị bỏ / Tổng giỏ hàng tạo", "target": "< 70%"},
            {"name": "Average Order Value (AOV)", "formula": "Doanh thu / Số đơn hàng", "target": "Tăng 20%+ qua bundle/upsell"},
            {"name": "Return Rate", "formula": "Đơn hoàn hàng / Tổng đơn", "target": "< 5% (fashion < 15%)"},
            {"name": "Gross Merchandise Value (GMV)", "formula": "Tổng giá trị hàng bán ra", "target": "MoM growth > 20% ở giai đoạn growth"},
        ],
        secondary_kpis=[
            {"name": "Customer Acquisition Cost (CAC)", "formula": "Marketing spend / New customers", "target": "< 0.5 lần AOV"},
            {"name": "Conversion Rate (CVR)", "formula": "Đơn hàng / Lượt xem sản phẩm", "target": "> 2% (Shopee), > 1% (website)"},
            {"name": "Revenue per Visitor (RPV)", "formula": "Doanh thu / Số lượt visit", "target": "Benchmark theo category"},
            {"name": "Seller Rating", "formula": "Average star rating", "target": "> 4.7 trên Shopee/Lazada"},
            {"name": "Inventory Turnover", "formula": "COGS / Avg Inventory", "target": "> 6x/năm"},
        ],
        vanity_kpis=[
            {"name": "Shop followers", "why": "Không predict purchase intent"},
            {"name": "Wishlist count", "why": "High wishlist ≠ high conversion"},
            {"name": "Livestream viewers", "why": "Measure conversion rate, không phải viewer"},
        ],
        benchmarks={
            "mvp": {"monthly_gmv": "< 200 triệu VND", "roas": "> 2x chấp nhận được"},
            "growth": {"monthly_gmv": "200 triệu - 2 tỷ VND", "roas": "> 3.5x", "repeat_rate": "> 20%"},
            "scale": {"monthly_gmv": "> 2 tỷ VND", "roas": "> 4x", "repeat_rate": "> 35%"},
        },
        unit_economics={
            "ltv_formula": "AOV × Purchase frequency/year × Customer lifespan",
            "contribution_margin": "Revenue - COGS - Shipping - Platform fee - Ad spend",
            "blended_roas": "Total Revenue / Total Marketing Spend (quan trọng hơn channel ROAS)",
        },
        growth_levers=[
            "Tăng AOV: Bundle, cross-sell, minimum order free ship",
            "Tăng repeat purchase: Post-purchase flow, loyalty points, email/Zalo remarketing",
            "Tối ưu listing: Ảnh, video, review → tăng CVR không tốn thêm ad spend",
            "Flash sale & campaign: 11/11, 12/12, Brand Day",
            "Affiliate / KOC: Performance-based, low risk",
            "Livestream: TikTok Shop, Shopee Live — conversion rate cao nhất hiện tại",
        ],
        channel_priority=[
            "Shopee / TikTok Shop (volume + built-in traffic)",
            "TikTok Ads + Livestream (highest conversion rate hiện tại)",
            "Meta Ads (retargeting + lookalike)",
            "Zalo OA (CRM, remarketing cost-effective)",
            "Google Shopping (intent-based)",
            "KOC / Affiliate network",
        ],
        tam_methodology="Category approach: Tổng GMV category trên Shopee/Lazada × market share có thể đạt",
        context_note="E-commerce cạnh tranh bằng giá + tốc độ + trải nghiệm sau mua. Đừng chỉ tối ưu ROAS từng kênh riêng lẻ — nhìn blended ROAS và LTV. Repeat purchase là profit thật sự, acquisition chỉ là chi phí.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Education / Coaching / Online Course / Training
    # ─────────────────────────────────────────────────────────────────
    "education": KPIFramework(
        industry="education",
        display_name="Giáo dục / Coaching / Khóa học",
        primary_kpis=[
            {"name": "Enrollment Rate", "formula": "Học viên đăng ký / Lead tiếp cận", "target": "> 10% (online), > 20% (tư vấn trực tiếp)"},
            {"name": "Course Completion Rate", "formula": "Học viên hoàn thành / Tổng đăng ký", "target": "> 60% (live), > 30% (self-paced)"},
            {"name": "Referral Rate", "formula": "Học viên giới thiệu người khác / Tổng học viên", "target": "> 20%"},
            {"name": "Net Promoter Score (NPS)", "formula": "% Promoters - % Detractors", "target": "> 60"},
            {"name": "Revenue per Lead", "formula": "Doanh thu / Tổng leads", "target": "Benchmark theo price point"},
            {"name": "Alumni Upsell Rate", "formula": "Học viên mua khóa tiếp / Tổng alumni", "target": "> 30%"},
        ],
        secondary_kpis=[
            {"name": "Cost per Lead (CPL)", "formula": "Ad spend / Số leads", "target": "< 10% course price"},
            {"name": "Show-up Rate (Webinar/Demo)", "formula": "Người tham dự / Đăng ký", "target": "> 40%"},
            {"name": "Sales Call Conversion", "formula": "Chốt / Số cuộc gọi", "target": "> 25%"},
            {"name": "Content-to-Lead Rate", "formula": "Leads từ content / Tổng views", "target": "Benchmark theo niche"},
            {"name": "Lifetime Value per Student", "formula": "Revenue từ 1 học viên suốt vòng đời", "target": "LTV > 3x khóa đầu tiên"},
        ],
        vanity_kpis=[
            {"name": "Số người theo dõi fanpage", "why": "Follower không đăng ký khóa học"},
            {"name": "Video views", "why": "Views không = enrollment"},
            {"name": "Webinar registrations", "why": "Chỉ ý nghĩa khi kèm show-up rate"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "< 100 triệu VND", "completion_rate": "> 40%"},
            "growth": {"monthly_revenue": "100-500 triệu VND", "nps": "> 50", "referral_rate": "> 15%"},
            "scale": {"monthly_revenue": "> 500 triệu VND", "alumni_upsell": "> 35%"},
        },
        unit_economics={
            "ltv_formula": "Avg revenue per student × Number of courses × Referral multiplier",
            "cpl_to_enrollment": "CPL / Enrollment rate = Cost per enrolled student",
            "cohort_value": "Revenue từ cohort / Số học viên trong cohort",
        },
        growth_levers=[
            "Outcome marketing: Testimonial kết quả cụ thể (lương tăng X%, việc làm Y)",
            "Webinar funnel: Free value → trust → enroll",
            "Alumni community: Mạng lưới alumni là moat cạnh tranh mạnh nhất",
            "Content authority: YouTube/TikTok dạy miễn phí → convert vào premium",
            "Partnership: Công ty trả học phí cho nhân viên (B2B2C)",
            "Installment / Study-now-pay-later: Giảm barrier to entry",
        ],
        channel_priority=[
            "YouTube (authority building, compound)",
            "Facebook Ads (lead gen, webinar traffic)",
            "TikTok (reach rộng, đặc biệt 18-30 tuổi)",
            "Email marketing (nurture leads, upsell alumni)",
            "LinkedIn (B2B, corporate training)",
            "Referral program (highest quality leads)",
        ],
        tam_methodology="Số người trong target demographic × % quan tâm chủ đề × % sẵn trả tiền học online",
        context_note="Education mua bằng niềm tin và kết quả kỳ vọng — social proof (testimonial + outcome) là conversion lever mạnh nhất. Completion rate phản ánh product quality; NPS cao thì referral tự nhiên tăng. Alumni network là growth engine dài hạn.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Health & Beauty / Spa / Clinic / Thẩm mỹ
    # ─────────────────────────────────────────────────────────────────
    "health_beauty": KPIFramework(
        industry="health_beauty",
        display_name="Sức khỏe & Làm đẹp / Spa / Clinic",
        primary_kpis=[
            {"name": "Repeat Client Rate", "formula": "Khách quay lại / Tổng khách", "target": "> 50% trong 60 ngày"},
            {"name": "Average Revenue per Visit", "formula": "Doanh thu / Số lượt khách", "target": "Tăng qua upsell treatment"},
            {"name": "Booking Utilization Rate", "formula": "Slot đã book / Tổng slot available", "target": "> 75%"},
            {"name": "Treatment Package Uptake", "formula": "Khách mua package / Tổng khách mới", "target": "> 40%"},
            {"name": "Google & Zalo Rating", "formula": "Rating ≥ 4.5 + review volume", "target": "Cần cả hai"},
            {"name": "Referral Rate", "formula": "Khách từ giới thiệu / Tổng khách mới", "target": "> 30%"},
        ],
        secondary_kpis=[
            {"name": "No-show Rate", "formula": "Lịch hẹn bị bỏ / Tổng lịch hẹn", "target": "< 10%"},
            {"name": "Retail Product Revenue %", "formula": "Doanh thu retail / Tổng doanh thu", "target": "> 15% (high margin)"},
            {"name": "Staff Utilization Rate", "formula": "Giờ làm việc tạo revenue / Tổng giờ làm", "target": "> 70%"},
            {"name": "Customer Acquisition Cost", "formula": "Marketing spend / Khách mới", "target": "< 1 lần avg visit value"},
            {"name": "Membership Conversion Rate", "formula": "Members / Tổng khách active", "target": "> 20%"},
        ],
        vanity_kpis=[
            {"name": "Instagram followers", "why": "Beauty content viral không = booking"},
            {"name": "TikTok views", "why": "Cần track từ view → DM → booking"},
            {"name": "Reach của bài quảng cáo", "why": "Đo số booking, không đo reach"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "50-200 triệu VND", "repeat_rate": "> 35%"},
            "growth": {"monthly_revenue": "200 triệu - 1 tỷ VND", "repeat_rate": "> 50%", "referral_rate": "> 25%"},
            "scale": {"monthly_revenue": "> 1 tỷ VND", "booking_utilization": "> 80%"},
        },
        unit_economics={
            "ltv_formula": "Avg revenue per visit × Avg visits/year × Customer lifespan",
            "cac_recovery": "CAC / (Avg visit value × Gross margin %)",
            "package_value": "Package price × Gross margin % — đây là real profit driver",
        },
        growth_levers=[
            "Before/After content: TikTok & Instagram — cực kỳ viral trong ngành beauty",
            "Package deal: Commit nhiều session trả trước → cash flow + retention",
            "Referral program: Đưa bạn đến được giảm giá cho cả 2",
            "Membership tier: Bronze/Silver/Gold → loyalty + predictable revenue",
            "Corporate wellness: B2B với công ty, trả theo nhóm",
            "Đào tạo + chứng chỉ: Authority positioning, attract premium clients",
        ],
        channel_priority=[
            "TikTok Before/After content (viral, high intent)",
            "Google Maps (người search 'spa gần tôi')",
            "Instagram (portfolio, aesthetic, DM booking)",
            "Facebook Ads (remarketing, local targeting)",
            "Zalo OA (CRM, nhắc lịch, promotion)",
            "KOL/KOC beauty (trust transfer)",
        ],
        tam_methodology="Dân số target demographic trong bán kính × Spending on beauty/health per year × Market share có thể đạt",
        context_note="Health & Beauty là ngành trust-based — khách hàng mua bằng sự tin tưởng vào người thực hiện dịch vụ, không phải thương hiệu. Before/after results và testimonial là công cụ marketing mạnh nhất. Repeat rate và referral rate là hai chỉ số sống còn.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Retail / Bán lẻ offline / Chuỗi cửa hàng
    # ─────────────────────────────────────────────────────────────────
    "retail": KPIFramework(
        industry="retail",
        display_name="Bán lẻ / Chuỗi cửa hàng",
        primary_kpis=[
            {"name": "Same-store Sales Growth", "formula": "Revenue store hiện tại YoY", "target": "> 15% YoY"},
            {"name": "Conversion Rate (Store)", "formula": "Người mua / Người vào cửa hàng", "target": "> 30%"},
            {"name": "Average Transaction Value (ATV)", "formula": "Doanh thu / Số giao dịch", "target": "Tăng qua cross-sell"},
            {"name": "Gross Margin %", "formula": "(Revenue - COGS) / Revenue", "target": "> 40% (fashion), > 25% (FMCG)"},
            {"name": "Inventory Turnover", "formula": "COGS / Avg Inventory value", "target": "> 4x/năm"},
            {"name": "Revenue per Square Meter", "formula": "Doanh thu / Diện tích", "target": "Benchmark theo location tier"},
        ],
        secondary_kpis=[
            {"name": "Foot Traffic", "formula": "Số người vào cửa hàng / ngày", "target": "Tăng through marketing"},
            {"name": "Customer Loyalty Rate", "formula": "Khách có thẻ thành viên / Tổng khách", "target": "> 40%"},
            {"name": "Stock-out Rate", "formula": "SKU hết hàng / Tổng SKU", "target": "< 5%"},
            {"name": "Shrinkage Rate", "formula": "Hàng thất thoát / Tổng hàng nhập", "target": "< 1%"},
            {"name": "Units per Transaction (UPT)", "formula": "Tổng items / Tổng giao dịch", "target": "> 2.5"},
        ],
        vanity_kpis=[
            {"name": "Social media followers", "why": "Không drive foot traffic trực tiếp"},
            {"name": "Brand awareness score", "why": "Trừ khi đo được correlation với foot traffic"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "100-500 triệu VND", "gross_margin": "> 30%"},
            "growth": {"monthly_revenue": "500 triệu - 5 tỷ VND", "conversion_rate": "> 25%"},
            "scale": {"monthly_revenue": "> 5 tỷ VND", "same_store_growth": "> 10% YoY"},
        },
        unit_economics={
            "four_wall_ebitda": "Revenue - COGS - Direct labor - Rent - Utilities",
            "payback_per_store": "Store setup cost / Monthly four-wall EBITDA",
            "ltv_formula": "ATV × Purchase frequency × Customer lifespan",
        },
        growth_levers=[
            "Loyalty program: Points, tiers, birthday rewards",
            "Omnichannel: Online đặt, offline lấy (O2O)",
            "Visual merchandising: Tăng conversion và UPT không tốn marketing budget",
            "Staff training: Upsell và cross-sell skills",
            "Hyper-local marketing: Leaflet, OOH trong bán kính 2km",
            "New store openings: Tận dụng brand recognition",
        ],
        channel_priority=[
            "Google Maps / Local SEO",
            "Facebook Ads (địa lý targeting hẹp)",
            "Zalo OA (thành viên thân thiết)",
            "In-store promotion (đã có khách — upsell ngay)",
            "OOH / Signage (brand visibility local)",
            "Influencer local",
        ],
        tam_methodology="Số hộ gia đình trong catchment area × Spending per category × Market share",
        context_note="Retail cạnh tranh bằng location, product mix, và trải nghiệm mua sắm. Online và offline phải bổ trợ nhau, không cạnh tranh. Quản lý tồn kho và margin quan trọng hơn marketing budget — đừng marketing một business có gross margin thấp.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # B2B Services / Agency / Tư vấn / Outsourcing
    # ─────────────────────────────────────────────────────────────────
    "b2b_service": KPIFramework(
        industry="b2b_service",
        display_name="B2B Services / Agency / Tư vấn",
        primary_kpis=[
            {"name": "Monthly Recurring Revenue (MRR)", "formula": "Retainer contracts × Monthly value", "target": "Tỷ lệ retainer > 60% total revenue"},
            {"name": "Client Retention Rate", "formula": "Clients còn lại / Tổng clients", "target": "> 85%/năm"},
            {"name": "Revenue per Employee", "formula": "Total revenue / Headcount", "target": "> 150 triệu VND/người/năm"},
            {"name": "Net Revenue Retention", "formula": "(Start MRR + Expansion - Churn) / Start MRR", "target": "> 110%"},
            {"name": "Gross Margin %", "formula": "(Revenue - Direct delivery cost) / Revenue", "target": "> 50% (agency), > 60% (consulting)"},
            {"name": "Win Rate", "formula": "Proposals won / Proposals sent", "target": "> 30%"},
        ],
        secondary_kpis=[
            {"name": "Sales Cycle Length", "formula": "Ngày từ lead → close", "target": "< 30 ngày (SME), < 90 ngày (enterprise)"},
            {"name": "Referral Rate", "formula": "New clients từ giới thiệu / Tổng new clients", "target": "> 40%"},
            {"name": "Average Contract Value (ACV)", "formula": "Total contract value / Số hợp đồng", "target": "Tăng dần qua upsell"},
            {"name": "Utilization Rate", "formula": "Billable hours / Total hours", "target": "> 70%"},
            {"name": "Net Promoter Score (NPS)", "formula": "% Promoters - % Detractors", "target": "> 50"},
        ],
        vanity_kpis=[
            {"name": "LinkedIn followers", "why": "B2B mua qua mối quan hệ, không qua follower"},
            {"name": "Số awards / giải thưởng ngành", "why": "Tốt cho PR nhưng không drive revenue"},
            {"name": "Website traffic", "why": "Trừ khi B2B có inbound funnel rõ ràng"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "50-200 triệu VND", "clients": "3-10 clients"},
            "growth": {"monthly_revenue": "200 triệu - 2 tỷ VND", "retention": "> 80%"},
            "scale": {"monthly_revenue": "> 2 tỷ VND", "mrr_ratio": "> 60%", "nrr": "> 110%"},
        },
        unit_economics={
            "ltv_formula": "ACV × Avg client lifespan (years)",
            "cac_formula": "Sales & marketing cost / New clients",
            "efficiency_ratio": "Revenue / (Salaries + Overhead) — target > 2x",
        },
        growth_levers=[
            "Case studies & referrals: Kết quả cụ thể cho khách hàng → referral tự nhiên",
            "Thought leadership: Content/speaking giúp inbound leads chất lượng cao",
            "Productize services: Đóng gói service thành package cố định → scalable hơn",
            "Upsell existing clients: Rẻ hơn 5-7x so với acquire client mới",
            "Strategic partnerships: Agency bổ sung nhau (design + dev + marketing)",
            "Niche specialization: Leader trong một niche > generalist mọi thứ",
        ],
        channel_priority=[
            "Referral network (priority #1 trong B2B)",
            "LinkedIn (content + outreach)",
            "Speaking / Events ngành",
            "Case study content (SEO + trust)",
            "Cold outreach (personalized, không spam)",
            "Partner ecosystem",
        ],
        tam_methodology="Số doanh nghiệp trong target segment × % cần dịch vụ × Average contract value",
        context_note="B2B service bán bằng trust và track record. Referral là kênh acquisition hiệu quả nhất — đầu tư vào client success trước, marketing sau. Retainer revenue là nền tảng — project revenue là biến động, nguy hiểm nếu phụ thuộc quá nhiều.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Real Estate / Bất động sản
    # ─────────────────────────────────────────────────────────────────
    "real_estate": KPIFramework(
        industry="real_estate",
        display_name="Bất động sản",
        primary_kpis=[
            {"name": "Lead-to-Viewing Rate", "formula": "Số lượt xem thực tế / Tổng leads", "target": "> 20%"},
            {"name": "Viewing-to-Offer Rate", "formula": "Số offer / Số lượt xem", "target": "> 15%"},
            {"name": "Cost per Qualified Lead (CPQL)", "formula": "Ad spend / Qualified leads", "target": "< 500k VND/lead (tùy phân khúc)"},
            {"name": "Sales Cycle Length", "formula": "Ngày từ lead → ký HĐ", "target": "< 30 ngày (mass-market), < 90 ngày (premium)"},
            {"name": "Transaction Volume", "formula": "Số giao dịch thành công / tháng", "target": "Tăng dần theo team size"},
            {"name": "Revenue per Agent", "formula": "Total commission / Số agent", "target": "Benchmark theo phân khúc"},
        ],
        secondary_kpis=[
            {"name": "Lead Response Time", "formula": "Thời gian từ lead → gọi lại", "target": "< 5 phút (critical!)"},
            {"name": "Referral Transaction Rate", "formula": "Giao dịch từ giới thiệu / Tổng giao dịch", "target": "> 25%"},
            {"name": "Online Listing CTR", "formula": "Clicks / Impressions trên listing site", "target": "> 3%"},
            {"name": "Brand Search Volume", "formula": "Search volume của tên brand/dự án", "target": "Tăng MoM"},
        ],
        vanity_kpis=[
            {"name": "Tổng leads (không qualified)", "why": "Lead rác giết năng suất sales team"},
            {"name": "Facebook reach", "why": "Chỉ ý nghĩa khi convert thành qualified leads"},
        ],
        benchmarks={
            "mvp": {"monthly_transactions": "2-5 giao dịch", "cpql": "< 1 triệu VND"},
            "growth": {"monthly_transactions": "5-20 giao dịch", "referral_rate": "> 20%"},
            "scale": {"monthly_transactions": "> 20 giao dịch", "revenue_per_agent": "> 50 triệu VND/tháng"},
        },
        unit_economics={
            "revenue_formula": "Transaction value × Commission rate %",
            "cost_per_transaction": "Total marketing + sales cost / Number of transactions",
            "agent_roi": "Commission earned by agent / (Salary + Lead cost allocated)",
        },
        growth_levers=[
            "Lead qualification system: Lọc leads ngay từ đầu để sales tập trung đúng chỗ",
            "Video tour & 3D walkthrough: Tăng viewing-to-offer rate",
            "Referral từ khách cũ: Happy buyers = best salespeople",
            "Local community trust: Zalo group khu vực, hội nhóm địa phương",
            "Content: Giáo dục thị trường (pháp lý, tài chính, quy hoạch)",
            "Bank partnership: Kết nối vay vốn → giảm barrier to purchase",
        ],
        channel_priority=[
            "Facebook Ads (lead gen form — hiệu quả nhất VN hiện tại)",
            "Batdongsan.com.vn / Nha.vn (intent-based)",
            "YouTube (project showcase, area review)",
            "Zalo OA + local groups",
            "Google Ads (brand + location keywords)",
            "Referral network của môi giới",
        ],
        tam_methodology="Số giao dịch BĐS trong khu vực × Avg transaction value × Commission rate",
        context_note="BĐS là giao dịch high-consideration, high-trust — khách có thể research 3-12 tháng trước khi mua. Lead response time < 5 phút là yếu tố sống còn. Qualified lead quan trọng hơn số lượng lead. Referral từ khách mua thành công là channel chất lượng nhất.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Health / Clinic — Phòng khám, Nha khoa, Da liễu, Thẩm mỹ y tế
    # ─────────────────────────────────────────────────────────────────
    "health_clinic": KPIFramework(
        industry="health_clinic",
        display_name="Health / Clinic (Phòng khám / Nha khoa / Da liễu)",
        primary_kpis=[
            {"name": "New Patient Rate", "formula": "Bệnh nhân mới / Tổng lượt khám", "target": "> 30% ở giai đoạn growth"},
            {"name": "Appointment Fill Rate", "formula": "Slot đã đặt / Tổng slot khả dụng", "target": "> 75% — dưới 60% = cần marketing mạnh hơn"},
            {"name": "No-show Rate", "formula": "Số ca không đến / Tổng đặt lịch", "target": "< 15% — cần SMS/Zalo reminder tự động"},
            {"name": "Average Revenue per Visit", "formula": "Tổng doanh thu / Tổng lượt khám", "target": "Tăng 15% YoY qua upsell treatment"},
            {"name": "Patient Retention Rate (6 tháng)", "formula": "Bệnh nhân quay lại / Tổng bệnh nhân", "target": "> 50% với điều trị dài kỳ"},
            {"name": "Google Maps Rating × Review Volume", "formula": "Rating ≥ 4.5 + > 100 reviews", "target": "Rating cao = acquisition miễn phí"},
        ],
        secondary_kpis=[
            {"name": "Cost per New Patient (CAC)", "formula": "Marketing spend / Bệnh nhân mới", "target": "< 300k–800k tùy chuyên khoa"},
            {"name": "Patient Lifetime Value (LTV)", "formula": "Avg revenue/visit × avg visits/year × avg lifespan (năm)", "target": "LTV:CAC > 5:1"},
            {"name": "Treatment Completion Rate", "formula": "Bệnh nhân hoàn thành liệu trình / Tổng bắt đầu", "target": "> 70%"},
            {"name": "Referral Rate", "formula": "Bệnh nhân từ giới thiệu / Tổng bệnh nhân mới", "target": "> 25% — càng cao càng tốt"},
            {"name": "Online Booking Rate", "formula": "Đặt lịch online / Tổng đặt lịch", "target": "> 40% — giảm tải hotline"},
        ],
        vanity_kpis=[
            {"name": "Facebook page followers", "why": "Không drive appointments — engagement rate quan trọng hơn"},
            {"name": "Số lượt xem video sức khỏe", "why": "Views ≠ appointments nếu không có CTA rõ ràng"},
            {"name": "Tổng số lượt khám tích lũy", "why": "Revenue per visit quan trọng hơn số lượt thô"},
        ],
        benchmarks={
            "mvp": {"monthly_visits": "50–150 lượt/tháng", "fill_rate": "> 50%", "google_rating": "> 4.2"},
            "growth": {"monthly_visits": "200–600 lượt/tháng", "fill_rate": "> 75%", "referral_rate": "> 20%"},
            "scale": {"monthly_visits": "> 600 lượt/tháng", "fill_rate": "> 85%", "ltv_cac": "> 5:1"},
        },
        unit_economics={
            "ltv_formula": "Avg revenue/visit × avg visits/year × avg patient lifespan (năm)",
            "cac_formula": "Marketing + sales spend / New patients acquired",
            "margin_per_visit": "Revenue per visit - (Doctor/nurse cost + Supplies + Overhead allocated)",
        },
        growth_levers=[
            "Google Maps optimization: Rating > 4.5 + 100+ reviews là acquisition engine tự nhiên mạnh nhất",
            "Bác sĩ personal brand: Expertise content trên Facebook/YouTube → trust → appointment",
            "Loyalty package: Gói điều trị trọn liệu trình (giảm no-show + lock revenue trước)",
            "Referral program: Bệnh nhân giới thiệu → giảm giá hoặc quà tặng (ethical, không conflict interest)",
            "Corporate health package: B2B với công ty 50+ nhân viên",
            "Telemedicine: Tư vấn online → tăng reach ngoài bán kính địa lý",
        ],
        channel_priority=[
            "Google Maps / Google Search (intent-based, priority #1)",
            "Facebook (health education content + retargeting)",
            "Zalo OA (booking, reminder, post-visit care)",
            "YouTube (bác sĩ authority content)",
            "Referral từ bệnh nhân cũ",
            "Bookingcare / Vivmedical / Medpro (healthcare platforms VN)",
        ],
        tam_methodology="Dân số trong bán kính phục vụ × % target demographic × visit frequency/year × Avg revenue/visit",
        context_note="Y tế bị regulate mạnh — content KHÔNG được claim cure/treatment cụ thể, tránh before/after gây hiểu lầm. Trust là yếu tố #1: bác sĩ personal brand quan trọng hơn brand phòng khám ở giai đoạn đầu. Google Maps là acquisition channel chính vì patient search intent rất cao. No-show là killer kinh doanh — SMS/Zalo reminder trước 24h là must-have.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Agency — Marketing Agency, Creative Agency, PR Agency
    # (tách riêng khỏi b2b_service — dynamics khác biệt)
    # ─────────────────────────────────────────────────────────────────
    "agency": KPIFramework(
        industry="agency",
        display_name="Agency (Marketing / Creative / PR / Digital)",
        primary_kpis=[
            {"name": "Monthly Recurring Revenue (MRR) từ retainer", "formula": "Số retainer clients × Avg retainer fee", "target": "MRR > 60% tổng doanh thu mới sustainable"},
            {"name": "Client Retention Rate (12 tháng)", "formula": "Clients còn lại sau 12T / Clients đầu kỳ", "target": "> 75% — dưới 60% = product/delivery có vấn đề"},
            {"name": "Revenue per FTE", "formula": "Total revenue / Số headcount", "target": "> 200–400 triệu/FTE/năm tùy service tier"},
            {"name": "Gross Margin per Project/Retainer", "formula": "(Revenue - Direct delivery cost) / Revenue", "target": "> 50% project, > 60% retainer"},
            {"name": "Pitch Win Rate", "formula": "Số pitch thắng / Tổng pitch", "target": "> 30% — dưới 20% cần review positioning"},
            {"name": "Average Contract Value (ACV)", "formula": "Tổng contract value / Số clients", "target": "Tăng 20% YoY qua upsell"},
        ],
        secondary_kpis=[
            {"name": "Utilization Rate", "formula": "Billable hours / Total capacity hours", "target": "70–80% — > 85% risk burnout, < 60% = overstaffed"},
            {"name": "Referral Rate từ clients", "formula": "New clients từ referral / Tổng new clients", "target": "> 40% — top agencies thường > 60%"},
            {"name": "Case Study Production Rate", "formula": "Số case study published / Số clients served", "target": "> 30% clients có documented case study"},
            {"name": "Time to First Deliverable", "formula": "Ngày từ ký HĐ → deliverable đầu tiên", "target": "< 5 ngày để set expectation tốt"},
            {"name": "Scope Creep Rate", "formula": "Extra hours không tính phí / Total hours", "target": "< 15% — cần SOW rõ ràng"},
        ],
        vanity_kpis=[
            {"name": "Số awards / giải thưởng ngành", "why": "Tốt cho PR nhưng không drive revenue — clients mua kết quả, không mua trophy"},
            {"name": "Agency headcount", "why": "Revenue per FTE quan trọng hơn số người — lớn không có nghĩa là profitable"},
            {"name": "Tổng campaigns đã chạy", "why": "Volume không thay thế được case study có số liệu cụ thể"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "50–200 triệu", "clients": "3–8 clients", "retainer_ratio": "> 30%"},
            "growth": {"monthly_revenue": "300 triệu–2 tỷ", "clients": "10–25 clients", "retention": "> 75%"},
            "scale": {"monthly_revenue": "> 2 tỷ", "retainer_ratio": "> 60%", "revenue_per_fte": "> 300 triệu/năm"},
        },
        unit_economics={
            "revenue_per_fte": "Total revenue / Headcount — benchmark 200–400 triệu/năm",
            "ltv_formula": "ACV × Avg client retention (năm)",
            "cac_formula": "Business development cost / New clients acquired",
        },
        growth_levers=[
            "Niche specialization: Agency dẫn đầu 1 vertical (F&B, HealthTech, Edu...) → premium pricing + easier sales",
            "Case studies với số liệu cụ thể: ROAS tăng X%, CPL giảm Y% → inbound leads chất lượng cao",
            "Founder personal brand: LinkedIn/Facebook thought leadership → inbound không cần cold outreach",
            "Upsell project → retainer: Project thành công = cơ hội convert sang retainer 6–12 tháng",
            "White-label partnership: Làm execution cho agency khác không có capability",
            "Productize service: Đóng gói thành package cố định (Content Pack, Ads Setup, etc.) → scalable hơn",
        ],
        channel_priority=[
            "Client referrals (priority #1 — lowest CAC, highest quality)",
            "Founder personal brand (LinkedIn, Facebook, podcast)",
            "Portfolio/case study content (SEO long-term)",
            "Industry events / speaking opportunities",
            "Cold outreach (targeted, personalized — không spam)",
            "Partnership với complementary vendors (web dev, production house)",
        ],
        tam_methodology="Số doanh nghiệp trong target segment × % outsource marketing × Avg agency spend/năm",
        context_note="Agency bán bằng portfolio, con người, và track record — không phải price. Retainer revenue là survival: project-only agencies có cash flow bất ổn. Founder personal brand thường = agency brand ở giai đoạn early. Niche beats generalist: tốt hơn là top agency cho F&B hơn là OK agency cho mọi thứ. Utilization rate 70–80% là sweet spot — cao hơn dễ burnout team.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Fashion / Retail — Thời trang, Phụ kiện, Lifestyle brand
    # ─────────────────────────────────────────────────────────────────
    "fashion_retail": KPIFramework(
        industry="fashion_retail",
        display_name="Fashion / Retail (Thời trang / Phụ kiện / Lifestyle)",
        primary_kpis=[
            {"name": "Sell-through Rate", "formula": "Số đơn vị bán / Tổng hàng tồn kho đầu kỳ", "target": "> 70% per collection — dưới 50% = discount bắt buộc"},
            {"name": "Average Order Value (AOV)", "formula": "Tổng doanh thu / Số đơn hàng", "target": "Tăng 15–20% qua bundling và outfit styling"},
            {"name": "Repeat Purchase Rate (60 ngày)", "formula": "Khách mua ≥ 2 lần / Tổng khách", "target": "> 25% — fashion loyalty thấp hơn service"},
            {"name": "Return Rate", "formula": "Số đơn hoàn / Tổng đơn", "target": "< 10% online, < 5% offline — return cao = size/quality issue"},
            {"name": "ROAS (Return on Ad Spend)", "formula": "Doanh thu từ ads / Chi phí ads", "target": "> 3x ổn, > 5x tốt với fashion"},
            {"name": "Revenue per Square Meter (offline)", "formula": "Doanh thu / Diện tích cửa hàng (m²)", "target": "Benchmark theo vị trí và phân khúc"},
        ],
        secondary_kpis=[
            {"name": "Inventory Turnover Rate", "formula": "COGS / Avg inventory value", "target": "> 4x/năm — < 3x = tồn kho chết nhiều"},
            {"name": "Customer Acquisition Cost (CAC)", "formula": "Marketing spend / Khách mới", "target": "< 1× AOV để có margin"},
            {"name": "UGC Volume (khách tự post)", "formula": "Số post organic về brand / tháng", "target": "Tăng 20% MoM — UGC = trust + free content"},
            {"name": "Cart Abandonment Rate (online)", "formula": "Carts không checkout / Tổng carts", "target": "< 65% — VN benchmark ~70%"},
            {"name": "TikTok Shop GMV", "formula": "Gross merchandise value qua TikTok Shop", "target": "Target tùy ngân sách — track MoM growth"},
        ],
        vanity_kpis=[
            {"name": "Instagram followers", "why": "Reach không bằng engagement rate và conversion — micro-influencer với 10k followers có thể hiệu quả hơn account 100k"},
            {"name": "Số lượt thích bài đăng sản phẩm", "why": "Likes ≠ sales — track click-to-product và add-to-cart"},
            {"name": "PR placements và media mentions", "why": "Tốt cho awareness nhưng không thay thế conversion tracking"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "20–100 triệu", "sell_through": "> 50%", "repeat_rate": "> 15%"},
            "growth": {"monthly_revenue": "200–800 triệu", "sell_through": "> 70%", "roas": "> 3x"},
            "scale": {"monthly_revenue": "> 1 tỷ", "channels": "DTC + Shopee + TikTok Shop + offline", "ltv_cac": "> 3:1"},
        },
        unit_economics={
            "gross_margin": "(Selling price - COGS) / Selling price — target > 50% fashion",
            "ltv_formula": "AOV × avg orders/year × avg customer lifespan (năm)",
            "cac_payback": "CAC / (AOV × Gross margin %)",
        },
        growth_levers=[
            "Product drops + limited editions: Tạo scarcity và FOMO — flash sale định kỳ",
            "TikTok Shop + organic: Fashion là category top-performing trên TikTok VN hiện tại",
            "KOC/micro-influencer seeding: 50–100 KOC mặc sản phẩm > 1 KOL đắt tiền",
            "Outfit bundle styling: 'Mix & match' tăng AOV 30–50% so với single item",
            "Seasonal collection cadence: Align với VN calendar (Tết, 8/3, summer, back-to-school)",
            "Loyalty với early access: Members được mua collection trước → exclusivity feeling",
        ],
        channel_priority=[
            "TikTok + TikTok Shop (priority #1 — highest organic reach cho fashion VN 2025–2026)",
            "Instagram (brand aesthetic + shopping tag)",
            "Shopee / Lazada (volume acquisition, cần quản lý margin)",
            "Facebook Ads (retargeting warm audience)",
            "KOC/micro-influencer network",
            "Zalo OA (new collection alert, VIP loyalty)",
        ],
        tam_methodology="Tổng chi tiêu thời trang của target demographic trong khu vực × % market share có thể capture",
        context_note="Fashion có seasonality cao và trend cycle ngắn — inventory management quan trọng ngang marketing. Sell-through rate thấp = margin bị ăn bởi discount. TikTok + TikTok Shop đang disrupting fashion acquisition tại VN mạnh nhất. UGC từ customers mặc sản phẩm là content authentic nhất — thiết kế khuyến khích khách post.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Travel / Hospitality — Khách sạn, Resort, Homestay, Tour, OTA
    # ─────────────────────────────────────────────────────────────────
    "travel_hospitality": KPIFramework(
        industry="travel_hospitality",
        display_name="Travel / Hospitality (Khách sạn / Resort / Homestay / Tour)",
        primary_kpis=[
            {"name": "Occupancy Rate", "formula": "Số phòng/tour đã bán / Tổng capacity", "target": "> 65% average, > 85% peak season"},
            {"name": "Revenue per Available Room (RevPAR)", "formula": "ADR × Occupancy Rate", "target": "Benchmark theo phân khúc và địa bàn"},
            {"name": "Average Daily Rate (ADR)", "formula": "Tổng room revenue / Số phòng đã bán", "target": "Tăng 10–15% YoY qua positioning và upsell"},
            {"name": "Direct Booking Rate", "formula": "Bookings trực tiếp / Tổng bookings", "target": "> 25% để giảm OTA commission (15–25%)"},
            {"name": "Guest Review Score", "formula": "Avg rating trên Booking.com / Agoda / TripAdvisor", "target": "> 8.5/10 — dưới 8.0 ảnh hưởng ADR"},
            {"name": "Booking Lead Time", "formula": "Avg số ngày đặt trước khi check-in", "target": "Hiểu để plan pricing và inventory strategy"},
        ],
        secondary_kpis=[
            {"name": "OTA Commission Cost %", "formula": "Tổng OTA commission / Tổng revenue", "target": "< 20% tổng revenue — tối ưu dần bằng direct channel"},
            {"name": "Repeat Guest Rate", "formula": "Khách quay lại / Tổng khách", "target": "> 20% resort/luxury, > 30% business hotel"},
            {"name": "Average Length of Stay (ALOS)", "formula": "Tổng đêm / Số lượt check-in", "target": "Tăng ALOS bằng packages giảm CAC per night"},
            {"name": "F&B Revenue per Guest", "formula": "Tổng F&B revenue / Số khách", "target": "Target tùy loại property"},
            {"name": "Group/Corporate Booking %", "formula": "Group + corp revenue / Tổng revenue", "target": "> 20% để reduce OTA dependency"},
        ],
        vanity_kpis=[
            {"name": "Social media followers", "why": "Followers không fill rooms — focus vào direct booking conversion"},
            {"name": "PR mentions và media coverage", "why": "Brand awareness tốt nhưng cần đo conversion về actual bookings"},
            {"name": "Số ảnh đẹp trên Instagram", "why": "Visual content quan trọng nhưng track booking attribution từ Instagram"},
        ],
        benchmarks={
            "mvp": {"occupancy": "40–60%", "review_score": "> 8.0", "direct_booking": "> 10%"},
            "growth": {"occupancy": "65–75%", "review_score": "> 8.5", "direct_booking": "> 25%"},
            "scale": {"occupancy": "> 75%", "revpar": "top 25% ngành", "direct_booking": "> 35%"},
        },
        unit_economics={
            "revpar": "ADR × Occupancy Rate — primary revenue health metric",
            "goppar": "Gross Operating Profit Per Available Room — profitability metric",
            "cost_per_occupied_room": "Total operating cost / Occupied rooms",
        },
        growth_levers=[
            "Direct booking channel: Website + Zalo OA + email — save 15–25% OTA commission per booking",
            "Package deals: Stay + F&B + experience → tăng ALOS và RevPAR",
            "Review management: Chủ động xin review sau check-out → score > 8.5 tự nhiên tăng ADR",
            "Corporate/MICE sales: Doanh nghiệp book recurring → giảm OTA dependency",
            "Seasonal yield management: Dynamic pricing peak/off-peak tối ưu RevPAR",
            "Loyalty program: Repeat guests → giảm CAC + tăng ALOS",
        ],
        channel_priority=[
            "Booking.com / Agoda / Expedia (OTA acquisition — không thể bỏ, cần quản lý commission)",
            "Google Hotel Ads + Google Maps",
            "Direct website với booking engine",
            "Facebook Ads (seasonal promotion, remarketing)",
            "Instagram (visual storytelling, lifestyle content)",
            "Corporate sales team + travel agent network",
        ],
        tam_methodology="Số khách du lịch đến khu vực × % target segment × ADR × avg stay nights",
        context_note="Travel là ngành seasonal mạnh và review-dependent. OTA acquisition không thể tránh nhưng cần chiến lược giảm dần dependency — mỗi 1% direct booking tăng = tiết kiệm đáng kể commission. Review score trên OTA ảnh hưởng trực tiếp đến ranking và ADR. Peak season (lễ, Tết, hè) cần pre-sell trước 2–3 tháng. Low season cần package sáng tạo để fill capacity.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Interior Design — Thiết kế nội thất, Kiến trúc, Home décor
    # ─────────────────────────────────────────────────────────────────
    "interior_design": KPIFramework(
        industry="interior_design",
        display_name="Interior Design (Nội thất / Kiến trúc / Home Décor)",
        primary_kpis=[
            {"name": "Project Pipeline Value", "formula": "Tổng giá trị các dự án trong backlog", "target": "> 3 tháng revenue backlog = healthy, > 6 tháng = scale được"},
            {"name": "Inquiry-to-Contract Rate", "formula": "Số HĐ ký / Tổng inquiry", "target": "> 20–30% — dưới 15% cần review pricing hoặc portfolio"},
            {"name": "Average Project Value (APV)", "formula": "Tổng revenue / Số dự án", "target": "Tăng 20% YoY qua nâng cấp segment và upsell materials"},
            {"name": "Project On-Time Completion Rate", "formula": "Dự án hoàn thành đúng hạn / Tổng dự án", "target": "> 80% — tiến độ là trust factor lớn nhất"},
            {"name": "Client Referral Rate", "formula": "Dự án đến từ referral / Tổng dự án mới", "target": "> 40% ở giai đoạn growth và scale"},
            {"name": "Portfolio Showcase Rate", "formula": "Dự án có documented portfolio / Tổng dự án", "target": "> 60% — portfolio là asset marketing quan trọng nhất"},
        ],
        secondary_kpis=[
            {"name": "Revenue per Designer", "formula": "Total revenue / Số designer", "target": "> 150–300 triệu/designer/năm tùy phân khúc"},
            {"name": "Material Markup Revenue %", "formula": "Markup từ vật tư / Tổng revenue", "target": "15–30% markup là phổ biến — cần minh bạch với client"},
            {"name": "Lead Response Time", "formula": "Giờ từ inquiry → first contact", "target": "< 2 giờ trong giờ hành chính — slow response = lost lead"},
            {"name": "3D/Visualization Win Rate", "formula": "Dự án ký sau khi xem 3D / Tổng 3D presented", "target": "> 60% — 3D giảm decision anxiety mạnh"},
            {"name": "Media Feature Rate", "formula": "Dự án được featured trên báo/blog/page / năm", "target": "> 3–5 features/năm để xây portfolio trust"},
        ],
        vanity_kpis=[
            {"name": "Instagram followers của trang studio", "why": "Follower ít nhưng portfolio chất lượng convert tốt hơn follower nhiều không có project showcase"},
            {"name": "Số giải thưởng thiết kế", "why": "Tốt cho brand nhưng client VN quyết định dựa trên portfolio + giá + tiến độ — không phải trophy"},
            {"name": "Tổng số dự án đã làm", "why": "Volume không thay thế được quality showcase — 5 project đẹp tốt hơn 50 project không documented"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "50–200 triệu", "projects_per_month": "2–5 dự án nhỏ"},
            "growth": {"monthly_revenue": "300 triệu–1.5 tỷ", "backlog": "> 3 tháng", "referral_rate": "> 30%"},
            "scale": {"monthly_revenue": "> 1.5 tỷ", "apv": "tăng segment premium", "team": "specialized design + PM"},
        },
        unit_economics={
            "revenue_formula": "Số dự án × APV (design fee + material markup)",
            "margin": "(Design fee + Material markup - Designer time cost - Material procurement cost - PM overhead)",
            "pipeline_value": "Tổng contract value signed chưa collect revenue",
        },
        growth_levers=[
            "Một landmark project xuất sắc > 10 bài quảng cáo — đầu tư vào portfolio photography và video",
            "Before/after content TikTok/Instagram: Transform video là format viral nhất cho ngành",
            "Referral từ dự án cũ: Client hài lòng → giới thiệu bạn bè mua nhà/sửa nhà",
            "Real estate developer partnership: Bán kèm gói thiết kế với căn hộ → B2B pipeline ổn định",
            "Showroom / 3D visualization: Giảm decision anxiety → tăng conversion rate",
            "Contractor network: Xây dựng - điện - nước - cửa → cross-referral ecosystem",
        ],
        channel_priority=[
            "Instagram (before/after portfolio — priority #1, visual category)",
            "TikTok (transform reveal video — viral potential cao nhất)",
            "Facebook (targeted ads đến homeowner + real estate buyer)",
            "Referral network (contractor, real estate agent, architect)",
            "Batdongsan.com / real estate channels (homebuyer intent)",
            "Pinterest (luxury / expat segment)",
        ],
        tam_methodology="Số căn hộ/nhà hoàn thiện + renovation/năm trong khu vực × % sử dụng design service × Avg project value",
        context_note="Interior design bán bằng visual portfolio — 1 project showcase đẹp có thể generate leads trong nhiều năm. Before/after video trên TikTok là ROI cao nhất. Referral từ homeowner hài lòng và từ contractor network là quality cao nhất. Tiến độ dự án là trust factor quan trọng nhất: VN market rất sensitive với trễ tiến độ — build reputation về on-time delivery.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Pet Care — Thú y, Grooming, Pet shop, Pet hotel, Pet food
    # ─────────────────────────────────────────────────────────────────
    "pet_care": KPIFramework(
        industry="pet_care",
        display_name="Pet Care (Thú y / Grooming / Pet Shop / Pet Hotel)",
        primary_kpis=[
            {"name": "Active Pet Owner Customer Rate", "formula": "Khách mua/dùng dịch vụ trong 60 ngày / Tổng khách", "target": "> 50% — pet care là ngành high-frequency"},
            {"name": "Average Transaction Value", "formula": "Tổng doanh thu / Số lượt giao dịch", "target": "Tăng 20% qua bundle và subscription"},
            {"name": "Service vs Product Revenue Mix", "formula": "Service revenue / Tổng revenue", "target": "> 40% service — higher margin và stickier"},
            {"name": "Appointment/Service Booking Rate", "formula": "Lượt đặt dịch vụ / Tổng lịch khả dụng", "target": "> 70% — dưới 50% cần marketing mạnh hơn"},
            {"name": "Google Maps Rating × Review Volume", "formula": "Rating ≥ 4.5 + > 50 reviews", "target": "Pet owners refer nhau dựa trên reviews rất nhiều"},
            {"name": "Subscription/Package Adoption Rate", "formula": "Khách đăng ký gói / Tổng khách active", "target": "> 20% — gói grooming monthly là LTV lever mạnh nhất"},
        ],
        secondary_kpis=[
            {"name": "Customer Acquisition Cost (CAC)", "formula": "Marketing spend / Khách mới", "target": "< 200k–500k — pet category có word-of-mouth mạnh"},
            {"name": "Pet Owner LTV", "formula": "Monthly spend × 12 × avg customer lifespan (năm)", "target": "LTV:CAC > 8:1 — loyalty rất cao nếu trust xây được"},
            {"name": "UGC Volume (pet photos)", "formula": "Số post organic tag brand / tháng", "target": "Tăng MoM — pet photos = free viral content"},
            {"name": "Referral Rate", "formula": "Khách mới từ giới thiệu / Tổng khách mới", "target": "> 35% — pet community word-of-mouth rất mạnh"},
            {"name": "Product Repeat Purchase Rate (30 ngày)", "formula": "Khách mua lại trong 30 ngày / Tổng khách mua", "target": "> 40% cho pet food/supplies"},
        ],
        vanity_kpis=[
            {"name": "Số lượt xem video thú cưng cute", "why": "Views không có CTA = entertainment, không phải marketing — cần link booking rõ ràng"},
            {"name": "Followers của trang pet shop", "why": "Pet community follow nhiều page cùng lúc — conversion rate quan trọng hơn follower count"},
            {"name": "Số lượng sản phẩm trong inventory", "why": "Depth beats breadth: tốt hơn 20 SKU bán được hơn 200 SKU tồn kho"},
        ],
        benchmarks={
            "mvp": {"monthly_revenue": "30–80 triệu", "active_customers": "50–150 pet owners"},
            "growth": {"monthly_revenue": "150–500 triệu", "subscription_rate": "> 15%", "referral_rate": "> 30%"},
            "scale": {"monthly_revenue": "> 500 triệu", "multi_service": "grooming + vet + boarding + supplies", "franchise_potential": "check"},
        },
        unit_economics={
            "ltv_formula": "Monthly spend × 12 × avg lifespan với brand (5–8 năm với loyal pet owners)",
            "cac_formula": "Marketing + referral cost / New pet owner customers",
            "subscription_value": "Monthly package fee × avg subscription duration (tháng)",
        },
        growth_levers=[
            "Subscription grooming package: 'Gói 4 lần/tháng giảm 20%' → lock LTV + predictable revenue",
            "Pet owner community: Facebook group / Zalo group → free acquisition + retention",
            "Birthday package cho thú cưng: Emotional marketing — chủ thú cưng chi tiêu cao cho occasions",
            "Preventive health bundle: Vaccine + checkup + tick prevention → upsell và trust building",
            "One-stop service: Grooming + vet + boarding + supplies dưới 1 mái nhà → switching cost cao",
            "UGC khuyến khích: Khách post ảnh thú cưng tại shop → tag brand → free reach trong pet community",
        ],
        channel_priority=[
            "Facebook (pet owner community + ads targeting pet owners)",
            "Zalo OA (booking, reminder, community broadcast)",
            "TikTok (cute pet content → organic viral trong pet community)",
            "Google Maps (local search 'thú y gần đây', 'grooming thú cưng')",
            "Referral giữa pet owners (very high trust category)",
            "Facebook Groups của pet owners địa phương",
        ],
        tam_methodology="Số hộ nuôi thú cưng trong khu vực × avg annual pet spending per household",
        context_note="Pet care là ngành loyalty cực cao — pet owners hiếm khi switch provider nếu trust xây được. Emotional bond với thú cưng = emotional bond với provider. UGC miễn phí: thiết kế experience và khuyến khích khách post ảnh thú cưng tại shop. Subscription/package hóa là LTV lever mạnh nhất. Pet community word-of-mouth rất mạnh — 1 chủ chó hài lòng có thể refer cả chung cư.",
    ),

    # ─────────────────────────────────────────────────────────────────
    # Events / Wedding — Event Management, Wedding Planner, Venue
    # ─────────────────────────────────────────────────────────────────
    "events_wedding": KPIFramework(
        industry="events_wedding",
        display_name="Events / Wedding (Tổ chức Sự kiện / Tiệc cưới / Venue)",
        primary_kpis=[
            {"name": "Booking Conversion Rate", "formula": "Số HĐ ký / Tổng inquiry", "target": "> 25% — dưới 15% cần review portfolio hoặc pricing"},
            {"name": "Average Event Value", "formula": "Tổng revenue / Số events", "target": "Tăng 15–20% YoY qua upsell và segment nâng cấp"},
            {"name": "Lead Time to Booking", "formula": "Avg số tháng đặt trước event", "target": "Wedding: 6–12 tháng; Corporate: 1–3 tháng — biết để plan pipeline"},
            {"name": "Client Referral Rate", "formula": "Events từ referral / Tổng events mới", "target": "> 35% — top planner thường > 50%"},
            {"name": "Vendor Partnership Revenue", "formula": "Commission/kickback từ vendor / Tổng revenue", "target": "5–15% additional revenue từ vendor ecosystem"},
            {"name": "Testimonial / Review Collection Rate", "formula": "Events có documented testimonial / Tổng events done", "target": "> 50% — testimonial = acquisition asset dài hạn"},
        ],
        secondary_kpis=[
            {"name": "Venue/Resource Utilization Rate", "formula": "Booked dates / Available dates", "target": "> 60% — mùa cưới (tháng 10, 11, 12, 1) > 85%"},
            {"name": "Corporate Repeat Client Rate", "formula": "Corp client book lại / Tổng corp clients", "target": "> 50% — corporate recurring là revenue ổn định"},
            {"name": "Deposit Collection Rate", "formula": "Tổng deposit đã thu / Tổng contract value", "target": "> 30% deposit giữ chỗ — giảm cancellation risk"},
            {"name": "Event Profitability per Type", "formula": "Margin từng loại event (wedding/corp/birthday)", "target": "Track để biết loại event nào nên focus"},
            {"name": "Media Documentation Rate", "formula": "Events được photo/video và published / Tổng events", "target": "> 40% — mỗi event tốt = portfolio asset"},
        ],
        vanity_kpis=[
            {"name": "Instagram wedding photo likes", "why": "Aesthetic content quan trọng nhưng bookings đến từ portfolio quality và referral — không phải likes"},
            {"name": "Pinterest saves", "why": "Inspiration platform — bride save nhưng book theo referral và trust, không phải Pinterest discovery"},
            {"name": "Tổng số event đã tổ chức", "why": "Chất lượng portfolio và referral rate quan trọng hơn số lượng thô"},
        ],
        benchmarks={
            "mvp": {"events_per_month": "2–5 events", "avg_event_value": "15–50 triệu", "referral_rate": "> 20%"},
            "growth": {"events_per_month": "8–20 events", "avg_wedding_value": "100–500 triệu", "utilization": "> 60%"},
            "scale": {"events_per_month": "> 20 events", "corporate_rate": "> 30% revenue", "vendor_ecosystem": "established"},
        },
        unit_economics={
            "revenue_formula": "Số events × Avg event value + Vendor commission",
            "margin": "Revenue - (Staff time + Venue cost + F&B + Equipment + Decoration + Management overhead)",
            "referral_value": "Avg event value × referral booking conversion rate",
        },
        growth_levers=[
            "Wedding portfolio photography: 1 bộ ảnh đám cưới đẹp có thể generate leads trong nhiều năm",
            "Vendor referral ecosystem: Venue ↔ Planner ↔ Photographer ↔ Florist ↔ MC ↔ DJ — cross-referral mạnh",
            "Corporate recurring clients: Công ty book team building/year-end party hàng năm → stable revenue",
            "Early booking incentive: Đặt trước 6+ tháng được ưu đãi → fill pipeline sớm",
            "TikTok/Instagram wedding reveal video: Viral potential cao — 1 video tốt = nhiều inquiry",
            "Cặp đôi vừa đính hôn targeting: Facebook ads target relationship milestone để catch early in journey",
        ],
        channel_priority=[
            "Instagram (wedding portfolio — priority #1, visual decision category)",
            "TikTok (behind-the-scenes, reveal videos — viral potential)",
            "Facebook Ads (target newly engaged + anniversary + corporate event planners)",
            "Google Search (intent: 'wedding planner HCM', 'tổ chức tiệc cưới')",
            "Vendor referral network (venue, photographer, florist, catering)",
            "Wedding fairs / exhibitions (Marry.vn, các hội chợ cưới)",
        ],
        tam_methodology="Số đám cưới/năm trong khu vực × % sử dụng professional planner × Avg spend per wedding event",
        context_note="Events/Wedding là ngành trust và visual-first — 1 event được documented tốt có thể generate leads trong nhiều năm. Vendor referral network là acquisition quality cao nhất: venue giới thiệu planner, planner giới thiệu photographer, v.v. Seasonal peaks mạnh (tháng 10, 11, 12, tháng tốt VN theo lịch âm) — cần build pipeline 6–12 tháng trước. Corporate events (team building, year-end, conference) là segment ổn định hơn wedding để balance seasonality.",
    ),
}


def get_kpi_framework(industry: str) -> Optional[KPIFramework]:
    """Return KPI framework for a given industry key."""
    return KPI_LIBRARY.get(industry)


def get_framework_as_text(industry: str) -> str:
    """Format KPI framework as readable text for injection into agent prompts."""
    fw = get_kpi_framework(industry)
    if not fw:
        return "Ngành chưa được định nghĩa — sử dụng framework chung."

    lines = [
        f"## KPI Framework: {fw.display_name}",
        "",
        "### KPIs Cốt Lõi (BẮT BUỘC theo dõi):",
    ]
    for kpi in fw.primary_kpis:
        lines.append(f"- **{kpi['name']}**: {kpi['formula']} → Target: {kpi['target']}")

    lines += ["", "### KPIs Quan Trọng:"]
    for kpi in fw.secondary_kpis:
        lines.append(f"- **{kpi['name']}**: {kpi['formula']} → Target: {kpi['target']}")

    lines += ["", "### KPIs Nên Tránh (Vanity Metrics):"]
    for kpi in fw.vanity_kpis:
        lines.append(f"- ~~{kpi['name']}~~: {kpi['why']}")

    lines += ["", "### Đòn Bẩy Tăng Trưởng Chính:"]
    for lever in fw.growth_levers:
        lines.append(f"- {lever}")

    lines += ["", "### Kênh Marketing Ưu Tiên:"]
    for i, channel in enumerate(fw.channel_priority, 1):
        lines.append(f"{i}. {channel}")

    lines += [
        "",
        "### Lưu ý đặc thù ngành:",
        fw.context_note,
    ]

    return "\n".join(lines)


def list_industries() -> list[str]:
    return list(KPI_LIBRARY.keys())
