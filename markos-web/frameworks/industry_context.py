"""
Industry Context — lớp bổ sung cho kpi_library, phục vụ McKinsey Discovery.

kpi_library.py đã có: KPI + benchmark + growth_levers + channel_priority + TAM.
Module này thêm 4 lớp mà Discovery + Strategy + Funnel Mapper cần:

  purchase_archetype — impulse | demand_gen | trust_building. Quyết định framework
                       funnel + content pillar style. Có thể blend 2 archetype.
  market_dynamics    — cấu trúc thị trường VN: mùa vụ, margin, mật độ cạnh tranh,
                       đặc thù regulatory/platform. CMO dùng để định khung chiến lược.
  buyer_triggers     — vì sao khách MUA + rào cản KHÔNG mua (objections). McKinsey
                       dùng để dựng hypotheses, CMO dùng cho positioning + content.
  search_keywords    — seed query (tiếng Việt) cho grounded web search: TAM, đối thủ,
                       trend. Phase 2 router nạp vào Gemini Grounded.

Thiết kế "15 ngành cùng sâu" — mọi ngành đều có đủ 4 lớp.
"""
from dataclasses import dataclass, field
from typing import Optional

from frameworks.kpi_library import (
    get_framework_as_text,
    get_kpi_framework,
    list_industries as _kpi_industries,
)


# Archetype constants — single source of truth
ARCHETYPE_IMPULSE        = "impulse"
ARCHETYPE_DEMAND_GEN     = "demand_gen"
ARCHETYPE_TRUST_BUILDING = "trust_building"

ARCHETYPE_LABEL = {
    ARCHETYPE_IMPULSE:        "Impulse purchase (mua cảm xúc nhanh)",
    ARCHETYPE_DEMAND_GEN:     "Demand-generation (khơi gợi desire)",
    ARCHETYPE_TRUST_BUILDING: "Trust-building (xây authority + chuyên môn)",
}


@dataclass
class IndustryContext:
    industry: str
    purchase_archetype: str                                   # primary archetype
    market_dynamics: str       = ""                           # cấu trúc thị trường VN
    buyer_triggers: list[str]  = field(default_factory=list)  # lý do mua
    buyer_barriers: list[str]  = field(default_factory=list)  # rào cản không mua
    search_keywords: dict      = field(default_factory=dict)  # seed queries
    archetype_secondary: str   = ""                           # optional secondary archetype
    archetype_blend: str       = ""                           # "70/30" hoặc "" = pure primary
    archetype_override_signals: list[str] = field(default_factory=list)
    # ↑ keyword trong brief → flip primary ↔ secondary (đảo blend ratio)


INDUSTRY_CONTEXT: dict[str, IndustryContext] = {

    # ─────────────────────────────────────────────────────────────────
    "fnb": IndustryContext(
        industry="fnb",
        purchase_archetype=ARCHETYPE_DEMAND_GEN,
        market_dynamics=(
            "Hyperlocal — 90% doanh thu đến từ khách trong bán kính 1-5km. Margin gộp "
            "60-70% nhưng net mỏng (10-15%) vì rent + nhân sự + COGS. Mùa vụ rõ: Tết "
            "(âm lịch) tăng đột biến, tháng 7 âm (Ngâu) giảm, mùa mưa miền Nam ảnh hưởng "
            "dine-in. Cạnh tranh cực gắt, rào cản gia nhập thấp → vòng đời quán trung bình "
            "12-24 tháng. Platform delivery (GrabFood/ShopeeFood) ăn 20-30% commission, "
            "nguy hiểm nếu phụ thuộc. Google Maps + review là chiến trường acquisition chính."
        ),
        buyer_triggers=[
            "Tiện đường / gần (location convenience)",
            "Review + ảnh đẹp trên Google Maps / TikTok (social proof)",
            "Bạn bè rủ / được giới thiệu (word-of-mouth)",
            "Combo/khuyến mãi hợp lý với giá trị nhận được",
            "Không gian phù hợp dịp (hẹn hò, làm việc, tụ tập)",
        ],
        buyer_barriers=[
            "Sợ dở / không hợp khẩu vị (rủi ro lần đầu)",
            "Giá cao hơn kỳ vọng so với phân khúc",
            "Chỗ đậu xe khó, xa",
            "Review xấu gần đây / vệ sinh đáng ngờ",
        ],
        search_keywords={
            "tam": ["quy mô thị trường F&B Việt Nam", "chi tiêu ăn uống ngoài hàng người Việt", "số lượng quán cà phê TP.HCM"],
            "competitor": ["quán {sản phẩm} {khu vực} review", "top quán {sản phẩm} nổi tiếng {thành phố}"],
            "trend": ["xu hướng F&B Việt Nam 2026", "món ăn trend TikTok", "concept quán cà phê hot"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "tech_saas": IndustryContext(
        industry="tech_saas",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        archetype_secondary=ARCHETYPE_IMPULSE,
        archetype_blend="70/30",
        archetype_override_signals=["self-serve", "freemium", "free trial", "B2C", "PLG", "SMB"],
        market_dynamics=(
            "Kinh tế đơn vị quyết định tất cả — churn cao giết growth dù acquisition tốt. "
            "Margin gộp 70-85% (gần như software thuần). Sales cycle B2C ngắn (self-serve), "
            "B2B dài 1-3 tháng. Thị trường VN còn non: khách quen 'mua đứt' hơn 'thuê bao', "
            "phải educate mô hình subscription. Cạnh tranh không chỉ nội địa mà cả global "
            "SaaS (Notion, Slack...). Đòn bẩy là product-led growth + content compound. "
            "CAC payback và LTV:CAC là hai số sống còn — đốt tiền acquisition mà churn cao = chết."
        ),
        buyer_triggers=[
            "Giải quyết pain cụ thể đang nhức (time-saving / cost-saving rõ ràng)",
            "Free trial / freemium để thử trước khi cam kết",
            "Case study + ROI chứng minh được",
            "Onboarding mượt, đạt aha-moment nhanh",
            "Integration với tool đang dùng",
        ],
        buyer_barriers=[
            "Ngại đổi quy trình / chi phí chuyển đổi (switching cost)",
            "Không rõ ROI, khó justify ngân sách",
            "Lo bảo mật dữ liệu / nhà cung cấp nhỏ biến mất",
            "Quen freebie, ngại trả phí định kỳ (đặc thù VN)",
        ],
        search_keywords={
            "tam": ["quy mô thị trường SaaS Việt Nam", "số doanh nghiệp SME Việt Nam", "chi tiêu phần mềm doanh nghiệp VN"],
            "competitor": ["phần mềm {chức năng} cho doanh nghiệp Việt", "{đối thủ} vs alternatives review"],
            "trend": ["xu hướng SaaS B2B 2026", "AI tools doanh nghiệp Việt Nam", "chuyển đổi số SME"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "ecommerce": IndustryContext(
        industry="ecommerce",
        purchase_archetype=ARCHETYPE_IMPULSE,
        market_dynamics=(
            "Sân chơi của Shopee/TikTok Shop/Lazada — traffic built-in nhưng commission "
            "5-15% + phí ads ăn margin. Blended ROAS quan trọng hơn ROAS từng kênh. "
            "Mega-sale (11/11, 12/12, Tết) chiếm tỷ trọng doanh thu lớn → dòng tiền dồn cục. "
            "TikTok Shop + livestream đang là conversion engine mạnh nhất 2025-2026. "
            "Cạnh tranh về giá khốc liệt, dễ vào race-to-bottom. Repeat purchase mới là "
            "profit thật — acquisition lần đầu thường lỗ. Return rate (đặc biệt fashion) bào margin."
        ),
        buyer_triggers=[
            "Giá tốt + flash sale / mã giảm",
            "Review + số lượng đã bán (social proof định lượng)",
            "Livestream demo trực tiếp, chốt nóng",
            "Freeship / freeship extra",
            "KOC/KOL giới thiệu đáng tin",
        ],
        buyer_barriers=[
            "Sợ hàng không giống hình / kém chất lượng",
            "Phí ship cao so với giá trị đơn",
            "Shop mới, ít review, chưa tin",
            "Thời gian giao lâu",
        ],
        search_keywords={
            "tam": ["quy mô thương mại điện tử Việt Nam", "GMV Shopee TikTok Shop Việt Nam", "doanh số ngành hàng {category} sàn TMĐT"],
            "competitor": ["shop bán {sản phẩm} bán chạy Shopee", "thương hiệu {category} nổi bật TikTok Shop"],
            "trend": ["xu hướng TMĐT Việt Nam 2026", "ngành hàng tăng trưởng Shopee", "livestream commerce trend"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "education": IndustryContext(
        industry="education",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        market_dynamics=(
            "Mua bằng niềm tin + kết quả kỳ vọng → social proof (testimonial outcome) là "
            "đòn bẩy conversion mạnh nhất. Margin cao (60-80% với online course) nhưng "
            "completion rate phản ánh chất lượng và quyết định referral. Mùa vụ theo lịch "
            "học/tuyển sinh + đầu năm (resolution). Funnel điển hình: free content → webinar "
            "→ enroll. Alumni network là moat dài hạn. Cạnh tranh từ free content (YouTube) → "
            "phải chứng minh vì sao trả tiền. Phụ huynh (K-12) vs người học (skill) có hành vi khác hẳn."
        ),
        buyer_triggers=[
            "Testimonial kết quả cụ thể (tăng lương X%, có việc, đỗ trường)",
            "Free value trước (webinar, ebook) tạo trust",
            "Giảng viên có authority / track record",
            "Trả góp / học trước trả sau (giảm barrier)",
            "Cộng đồng học viên + hỗ trợ sau khóa",
        ],
        buyer_barriers=[
            "Sợ học xong không áp dụng được / không có kết quả",
            "Giá cao, chưa thấy ROI rõ",
            "Không có thời gian học (sợ bỏ dở)",
            "Nội dung có thể tự học free trên mạng",
        ],
        search_keywords={
            "tam": ["quy mô thị trường edtech Việt Nam", "chi tiêu giáo dục hộ gia đình Việt Nam", "số người học online Việt Nam"],
            "competitor": ["khóa học {chủ đề} tốt nhất Việt Nam", "{đối thủ} review học viên"],
            "trend": ["xu hướng học online 2026", "kỹ năng hot thị trường lao động Việt Nam", "edtech trend"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "health_beauty": IndustryContext(
        industry="health_beauty",
        purchase_archetype=ARCHETYPE_DEMAND_GEN,
        archetype_secondary=ARCHETYPE_TRUST_BUILDING,
        archetype_blend="60/40",
        archetype_override_signals=["thẩm mỹ y khoa", "phẫu thuật", "bác sĩ", "nội khoa", "cao cấp"],
        market_dynamics=(
            "Trust-based và phụ thuộc người thực hiện hơn thương hiệu. Margin dịch vụ cao "
            "(60-75%), retail sản phẩm bổ sung margin. Before/after là vũ khí viral mạnh "
            "nhất (TikTok/Instagram). Package trả trước = cash flow + retention. Vấn đề "
            "regulatory ngày càng chặt (quảng cáo dịch vụ thẩm mỹ, y tế bị kiểm soát). "
            "No-show và booking utilization là hai killer vận hành. Khách cực nhạy với review "
            "tiêu cực vì liên quan cơ thể/sức khỏe. Repeat + referral là hai số sống còn."
        ),
        buyer_triggers=[
            "Before/after ấn tượng, chân thực",
            "Review + đánh giá cao (đặc biệt từ người giống mình)",
            "Được người quen giới thiệu (trust transfer)",
            "Combo/package giá trị, cam kết kết quả",
            "Chuyên môn / chứng chỉ của người thực hiện",
        ],
        buyer_barriers=[
            "Sợ rủi ro (hỏng da, biến chứng, không an toàn)",
            "Sợ bị chèo kéo upsell quá mức",
            "Giá cao, sợ không xứng đáng",
            "Review tiêu cực / tin đồn xấu",
        ],
        search_keywords={
            "tam": ["quy mô thị trường làm đẹp spa Việt Nam", "chi tiêu làm đẹp phụ nữ Việt", "số lượng spa thẩm mỹ viện {thành phố}"],
            "competitor": ["spa {dịch vụ} {khu vực} review", "thẩm mỹ viện uy tín {thành phố}"],
            "trend": ["xu hướng làm đẹp Việt Nam 2026", "dịch vụ spa hot TikTok", "công nghệ thẩm mỹ mới"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "retail": IndustryContext(
        industry="retail",
        purchase_archetype=ARCHETYPE_IMPULSE,
        market_dynamics=(
            "Cạnh tranh bằng location + product mix + trải nghiệm. Margin theo ngành hàng: "
            "fashion 40-60%, FMCG 15-25%. Quản tồn kho và margin quan trọng HƠN marketing — "
            "đừng marketing business margin thấp. O2O (online đặt, offline lấy) là xu hướng. "
            "Foot traffic giảm dần do TMĐT → phải cho lý do đến cửa hàng (trải nghiệm, tức thì). "
            "Same-store sales growth là thước đo sức khỏe thật. Mùa vụ mạnh: Tết, back-to-school, "
            "mega-sale. Loyalty program + visual merchandising tăng conversion không tốn ad budget."
        ),
        buyer_triggers=[
            "Cần ngay, không chờ ship được (instant gratification)",
            "Được xem/thử trực tiếp trước khi mua",
            "Khuyến mãi tại cửa hàng / loyalty rewards",
            "Vị trí tiện, trên đường di chuyển",
            "Trải nghiệm mua sắm + tư vấn tốt",
        ],
        buyer_barriers=[
            "Giá cao hơn online cùng sản phẩm",
            "Ngại di chuyển, đậu xe",
            "Sản phẩm hết size/màu (stock-out)",
            "Mua online tiện hơn",
        ],
        search_keywords={
            "tam": ["quy mô bán lẻ Việt Nam ngành {category}", "chi tiêu bán lẻ hộ gia đình Việt Nam", "số cửa hàng {ngành} {khu vực}"],
            "competitor": ["cửa hàng {sản phẩm} {khu vực}", "chuỗi bán lẻ {category} lớn Việt Nam"],
            "trend": ["xu hướng bán lẻ Việt Nam 2026", "O2O retail trend", "hành vi mua sắm offline"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "b2b_service": IndustryContext(
        industry="b2b_service",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        market_dynamics=(
            "Bán bằng trust + track record, referral là kênh #1. Margin agency 50%, "
            "consulting 60%+. Retainer revenue là nền tảng, project revenue biến động nguy hiểm. "
            "Sales cycle dài (SME <30 ngày, enterprise 90+). Quyết định mua nhiều người "
            "(decision-making unit) → cần thuyết phục nhiều stakeholder. Thị trường VN chuộng "
            "quan hệ cá nhân + giới thiệu hơn inbound lạnh. Productize service giúp scale. "
            "Niche leader > generalist. Client success trước, marketing sau."
        ),
        buyer_triggers=[
            "Case study + kết quả cụ thể cho khách tương tự",
            "Được đối tác/đồng nghiệp giới thiệu",
            "Thought leadership / chuyên môn được công nhận",
            "Proposal rõ ràng, cam kết deliverable + KPI",
            "Chemistry + tin tưởng người làm trực tiếp",
        ],
        buyer_barriers=[
            "Sợ chọn sai nhà cung cấp (rủi ro cao, khó đổi giữa chừng)",
            "Ngân sách cần nhiều người duyệt (long approval)",
            "Khó so sánh chất lượng giữa các agency",
            "Đã có nhà cung cấp cũ, ngại chuyển",
        ],
        search_keywords={
            "tam": ["quy mô thị trường dịch vụ {ngành} B2B Việt Nam", "số doanh nghiệp cần {dịch vụ} Việt Nam"],
            "competitor": ["agency {dịch vụ} hàng đầu Việt Nam", "công ty tư vấn {lĩnh vực} uy tín"],
            "trend": ["xu hướng outsourcing Việt Nam 2026", "nhu cầu {dịch vụ} doanh nghiệp", "B2B marketing trend"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "real_estate": IndustryContext(
        industry="real_estate",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        market_dynamics=(
            "Giao dịch high-consideration, high-trust — khách research 3-12 tháng. Lead "
            "response time <5 phút là sống còn (lead nguội cực nhanh). Qualified lead quan "
            "trọng hơn số lượng — lead rác giết năng suất sales. Commission-based, giá trị "
            "giao dịch lớn nên CPL cao vẫn hợp lý. Cực nhạy chu kỳ thị trường + chính sách "
            "(lãi suất, pháp lý, quy hoạch). Facebook lead form + batdongsan.com.vn là kênh "
            "chính. Referral từ khách mua thành công là nguồn chất lượng nhất. Trust về pháp lý "
            "+ tài chính (kết nối vay vốn) là đòn bẩy chốt deal."
        ),
        buyer_triggers=[
            "Pháp lý rõ ràng, minh bạch",
            "Vị trí + tiềm năng tăng giá / khai thác",
            "Hỗ trợ vay vốn, phương án tài chính khả thi",
            "Môi giới phản hồi nhanh, tư vấn đáng tin",
            "Video tour / xem thực tế thuyết phục",
        ],
        buyer_barriers=[
            "Sợ rủi ro pháp lý (sổ, tranh chấp, quy hoạch)",
            "Số tiền lớn, sợ quyết định sai",
            "Lo thị trường xuống giá / thanh khoản kém",
            "Không tin môi giới (định kiến ngành)",
        ],
        search_keywords={
            "tam": ["thị trường bất động sản {khu vực} 2026", "số giao dịch BĐS {phân khúc} Việt Nam", "giá bất động sản {khu vực}"],
            "competitor": ["dự án {phân khúc} {khu vực}", "sàn môi giới BĐS {khu vực} uy tín"],
            "trend": ["xu hướng bất động sản Việt Nam 2026", "phân khúc BĐS tăng trưởng", "chính sách BĐS mới"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "health_clinic": IndustryContext(
        industry="health_clinic",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        market_dynamics=(
            "Trust-based tuyệt đối — khách đặt sức khoẻ vào tay người làm. Quyết định mua "
            "phụ thuộc credential bác sĩ + review thật + không gian an toàn. Margin cao (50-70% "
            "với nha khoa, da liễu), nhưng CAC tăng nhanh do regulatory chặt với quảng cáo y tế. "
            "Cấm so sánh trực tiếp, cấm before/after y khoa trên ads chính chủ → phụ thuộc UGC + "
            "KOL bác sĩ. Lead response <30 phút quyết định booking rate. Repeat + referral từ "
            "khách cũ là moat dài hạn — 1 khách giới thiệu 2-3 khách. Mùa vụ nhẹ (Tết, hè cho "
            "thẩm mỹ học sinh). Phòng khám đa khoa cạnh tranh chuỗi lớn (Vinmec, FV) bằng giá + "
            "chuyên môn niche."
        ),
        buyer_triggers=[
            "Bác sĩ có chuyên môn + chứng chỉ rõ ràng (authority cá nhân)",
            "Review thật từ khách đã làm, đặc biệt video kể trải nghiệm",
            "Cơ sở vật chất sạch, vô trùng, máy móc hiện đại",
            "Tư vấn miễn phí trước khi quyết định + minh bạch chi phí",
            "Được người quen / bệnh nhân cũ giới thiệu (referral trust)",
        ],
        buyer_barriers=[
            "Sợ biến chứng / tay nghề bác sĩ không đảm bảo",
            "Giá cao, không biết có xứng đáng / có rẻ hơn ở đâu",
            "Lo bị upsell dịch vụ không cần thiết",
            "Sợ review xấu / scandal trên mạng (kể cả không liên quan trực tiếp)",
        ],
        search_keywords={
            "tam": ["thị trường nha khoa Việt Nam quy mô", "chi tiêu y tế tư nhân hộ gia đình", "số phòng khám {chuyên khoa} {thành phố}"],
            "competitor": ["phòng khám {chuyên khoa} {khu vực} uy tín", "bác sĩ {chuyên khoa} nổi tiếng {thành phố}"],
            "trend": ["xu hướng y tế tư nhân Việt Nam 2026", "công nghệ {chuyên khoa} mới", "phòng khám chuyên sâu"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "agency": IndustryContext(
        industry="agency",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        market_dynamics=(
            "Bán bằng case study + portfolio + chemistry với người dẫn dắt. Margin gross 40-60%, "
            "nhưng net mỏng do nhân sự ăn 50-70% revenue. Retainer revenue = nền tảng, project "
            "revenue biến động. Sales cycle 2-8 tuần với SME, 2-6 tháng với enterprise. Quyết "
            "định mua bởi DMU (marketing director + CEO + finance) → phải convince nhiều tầng. "
            "Niche agency > full-service generalist (Performance / Branding / Content / TikTok). "
            "Thought leadership của founder/lead là vũ khí lớn nhất — agency không có brand cá "
            "nhân coi như agency vô danh. Talent retention quan trọng hơn marketing — mất key "
            "person = mất khách. Referral từ ex-client là kênh #1."
        ),
        buyer_triggers=[
            "Case study cùng ngành + KPI cụ thể (ROAS, CPL, growth %)",
            "Founder/lead có cá tính + quan điểm rõ trên social",
            "Process minh bạch, deliverable + timeline rõ ràng trong proposal",
            "Chemistry với team trực tiếp làm (không phải sales)",
            "Giới thiệu từ partner / khách cũ đã thành công",
        ],
        buyer_barriers=[
            "Sợ agency dùng junior chạy account mình (bait & switch)",
            "Khó so sánh chất lượng giữa các agency cùng giá",
            "Ngại commit retainer dài, sợ kẹt nếu không hợp",
            "Trải nghiệm xấu với agency cũ → cảnh giác với promise",
        ],
        search_keywords={
            "tam": ["thị trường agency marketing Việt Nam quy mô", "chi tiêu marketing outsource doanh nghiệp VN", "số agency {chuyên môn} Việt Nam"],
            "competitor": ["agency {chuyên môn} hàng đầu Việt Nam", "{đối thủ} review case study"],
            "trend": ["xu hướng agency marketing 2026", "performance vs branding agency", "AI agency trend"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "fashion_retail": IndustryContext(
        industry="fashion_retail",
        purchase_archetype=ARCHETYPE_IMPULSE,
        archetype_secondary=ARCHETYPE_DEMAND_GEN,
        archetype_blend="70/30",
        archetype_override_signals=["luxury", "designer", "haute couture", "thiết kế riêng", "may đo"],
        market_dynamics=(
            "Trend cycle ngắn (4-8 tuần) → sell-through rate quyết định margin. Margin gross 50-65% "
            "fashion, nhưng end-of-season discount ăn 20-40%. TikTok + TikTok Shop là acquisition "
            "engine mạnh nhất 2025-2026 — livestream + KOC outfit haul drive 60%+ doanh thu mới. "
            "Return rate cao (15-25% online) bào margin. Repeat purchase + LTV mới là profit thật. "
            "Cạnh tranh khốc liệt với fast fashion (Shein, local fast brand) + secondhand trend. "
            "UGC khách mặc đồ là content authentic nhất — phải design khuyến khích post. "
            "Fashion luxury/designer thì ngược: trust-driven, brand heritage + tay nghề."
        ),
        buyer_triggers=[
            "Outfit đẹp trên KOC/KOL mình theo dõi (aspiration)",
            "Giá hợp + sale + flash deal (price anchor)",
            "Mẫu mới, trend mới, hợp mùa",
            "Review fit/chất liệu đúng kỳ vọng (giảm rủi ro size)",
            "Combo / mua kèm tiết kiệm",
        ],
        buyer_barriers=[
            "Sợ size không vừa / chất không như hình",
            "Đổi trả phức tạp, sợ kẹt hàng",
            "Có thể mua rẻ hơn ở Shein / shop khác",
            "Tủ đã đầy đồ, cảm giác mua thừa",
        ],
        search_keywords={
            "tam": ["thị trường thời trang Việt Nam quy mô", "chi tiêu quần áo người Việt", "số brand fashion {phân khúc} Việt Nam"],
            "competitor": ["brand thời trang {phân khúc} Việt Nam", "shop quần áo {phong cách} TikTok"],
            "trend": ["xu hướng thời trang Việt Nam 2026", "TikTok fashion trend VN", "Gen Z fashion behavior"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "travel_hospitality": IndustryContext(
        industry="travel_hospitality",
        purchase_archetype=ARCHETYPE_DEMAND_GEN,
        archetype_secondary=ARCHETYPE_TRUST_BUILDING,
        archetype_blend="70/30",
        archetype_override_signals=["MICE", "corporate", "resort 5 sao", "wedding destination", "honeymoon cao cấp"],
        market_dynamics=(
            "Mùa vụ cực mạnh: hè (tháng 5-8), Tết, lễ 30/4-1/5. Booking lead time 2-12 tuần "
            "→ campaign phải đẩy đúng window. OTA (Booking, Agoda, Traveloka) ăn 15-25% commission "
            "+ kiểm soát giá → margin direct booking cao hơn nhưng phải tự kéo traffic. Review "
            "TripAdvisor / Google / Booking quyết định trust 80%. Instagram + TikTok là 'desire "
            "engine' — khách quyết đi đâu vì thấy video đẹp. Khách Việt vs khách inbound hành vi "
            "khác hẳn (booking window, payment, kỳ vọng). Repeat booking thấp (1-3 năm/lần với "
            "leisure) → referral + UGC là kênh acquisition rẻ nhất. Resort cao cấp + MICE thì "
            "trust-driven (brand heritage, service quality, decision committee)."
        ),
        buyer_triggers=[
            "Video / ảnh đẹp aspirational (kích desire đi)",
            "Review cao + nhiều (TripAdvisor, Google, Booking)",
            "Giá tốt + early bird / flash deal mùa thấp điểm",
            "Combo bay + khách sạn / package gia đình tiện",
            "KOL travel review đáng tin / influencer outfit + cảnh đẹp",
        ],
        buyer_barriers=[
            "Sợ ảnh đẹp hơn thực tế (over-promise)",
            "Giá cao mùa cao điểm, ngại không xứng đáng",
            "Lo dịch vụ / vệ sinh / an toàn không đảm bảo",
            "Quá nhiều lựa chọn, không biết chọn gì",
        ],
        search_keywords={
            "tam": ["thị trường du lịch Việt Nam quy mô 2026", "chi tiêu du lịch hộ gia đình Việt", "lượng khách nội địa quốc tế Việt Nam"],
            "competitor": ["resort {khu vực} review", "khách sạn {hạng sao} {thành phố} tốt nhất"],
            "trend": ["xu hướng du lịch Việt Nam 2026", "wellness travel trend", "TikTok travel content VN"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "interior_design": IndustryContext(
        industry="interior_design",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        market_dynamics=(
            "High-consideration — khách research 2-6 tháng, so sánh 3-5 design firm trước khi "
            "chốt. Margin gộp 25-40% (thiết kế thuần cao hơn, thi công trọn gói thấp hơn). "
            "Portfolio + Pinterest/Instagram visual là vũ khí #1 — khách không tin design firm "
            "không có portfolio đẹp. Sales cycle 3-8 tuần, decision committee gia đình (vợ "
            "chồng + đôi khi ba mẹ). Project value lớn (200tr-5 tỷ residential, vài tỷ commercial) "
            "→ CPL cao vẫn hợp lý. Referral từ khách cũ + dev BĐS là nguồn chất nhất. Khó "
            "scale: phụ thuộc lead designer + thi công uy tín. Trend Scandinavian / Japandi / "
            "modern Vietnam đang dominate Gen Y - Gen Z."
        ),
        buyer_triggers=[
            "Portfolio đẹp + có project tương tự (style, ngân sách, diện tích)",
            "Designer lead có gu rõ, quan điểm thẩm mỹ thuyết phục",
            "Process minh bạch: timeline, milestone, ngân sách dự kiến",
            "Review khách cũ + video walk-through dự án đã hoàn thiện",
            "Cam kết quản lý thi công đến cuối (không drop sau bản vẽ)",
        ],
        buyer_barriers=[
            "Sợ thực tế không giống render 3D",
            "Lo phát sinh chi phí giữa chừng",
            "Sợ thi công kém / chậm tiến độ",
            "Khó so sánh chất lượng giữa designer cùng giá",
        ],
        search_keywords={
            "tam": ["thị trường thiết kế nội thất Việt Nam quy mô", "chi tiêu nội thất hộ gia đình VN", "số design firm {khu vực}"],
            "competitor": ["công ty thiết kế nội thất {khu vực} uy tín", "designer nội thất {phong cách} Việt Nam"],
            "trend": ["xu hướng thiết kế nội thất 2026", "phong cách nội thất hot Việt Nam", "Pinterest interior trend VN"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "pet_care": IndustryContext(
        industry="pet_care",
        purchase_archetype=ARCHETYPE_DEMAND_GEN,
        archetype_secondary=ARCHETYPE_TRUST_BUILDING,
        archetype_blend="70/30",
        archetype_override_signals=["clinic thú y", "phẫu thuật thú y", "cấp cứu", "nội khoa thú y"],
        market_dynamics=(
            "Thị trường tăng trưởng 15-20%/năm (pet humanization). Margin grooming 50-65%, retail "
            "thức ăn 20-35%, clinic thú y 40-60%. Khách đối xử thú cưng như con — sẵn sàng chi "
            "premium cho chất lượng. TikTok + Instagram pet content viral mạnh, drive cả "
            "awareness lẫn booking. Repeat + LTV cao (grooming monthly, food monthly) → retention "
            "quan trọng hơn acquisition. Trust gắn với người trực tiếp (groomer, vet) hơn brand "
            "store. Clinic thú y thì trust-building tuyệt đối — sai 1 ca = mất uy tín. Pet shop "
            "+ grooming thì demand-gen (cute content khơi gợi)."
        ),
        buyer_triggers=[
            "Content pet cute / video chăm sóc thực tế (cảm xúc + tin tưởng)",
            "Review từ pet parent có thú cưng giống mình",
            "Người làm có kinh nghiệm + yêu động vật rõ rệt",
            "Cơ sở sạch, không gian thân thiện với pet",
            "Combo grooming + check up / package tiết kiệm",
        ],
        buyer_barriers=[
            "Sợ thú cưng bị stress / bị thương khi grooming",
            "Lo dịch vụ y tế tay nghề kém / chẩn đoán sai",
            "Giá cao hơn tự làm tại nhà / shop khác rẻ hơn",
            "Đi xa không tiện, sợ thú cưng say xe",
        ],
        search_keywords={
            "tam": ["thị trường thú cưng Việt Nam quy mô", "chi tiêu pet care hộ gia đình VN", "số lượng pet owner Việt Nam"],
            "competitor": ["pet shop {khu vực}", "clinic thú y {thành phố} uy tín", "grooming pet {khu vực}"],
            "trend": ["xu hướng pet care Việt Nam 2026", "pet humanization trend", "TikTok pet content VN"],
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    "events_wedding": IndustryContext(
        industry="events_wedding",
        purchase_archetype=ARCHETYPE_TRUST_BUILDING,
        archetype_secondary=ARCHETYPE_DEMAND_GEN,
        archetype_blend="60/40",
        market_dynamics=(
            "One-shot, high-emotion, high-stake — khách chỉ làm 1 lần (wedding) hoặc vài lần/năm "
            "(corporate event), không có cơ hội sai. Portfolio + review = trust currency #1. "
            "Margin gross 30-50% (wedding planning) đến 50-70% (concept-heavy), nhưng overhead "
            "cao mùa cao điểm (Q4 + đầu năm). Mùa vụ cực mạnh: cưới (Q4 + sau Tết), corporate "
            "(year-end + kickoff đầu năm). Referral từ couple/khách doanh nghiệp đã làm = nguồn "
            "chất nhất (40-60% revenue). Instagram + TikTok visual aspirational drive lead. "
            "Decision committee phức tạp (cô dâu + chú rể + ba mẹ 2 bên) → cần content thuyết "
            "phục nhiều tệp. Pricing không minh bạch khiến khách e dè — package rõ ràng là edge."
        ),
        buyer_triggers=[
            "Portfolio video/ảnh sự kiện đã làm (cảm xúc + chất lượng visible)",
            "Review couple/client cũ + behind-the-scenes thật",
            "Planner/designer có gu + quan điểm thẩm mỹ rõ",
            "Package minh bạch: include gì, exclude gì, phát sinh ra sao",
            "Được giới thiệu từ couple cũ / wedding venue / vendor partner",
        ],
        buyer_barriers=[
            "Sợ chất lượng không như demo / portfolio chỉ là best case",
            "Lo phát sinh chi phí trong ngày diễn ra",
            "Sợ team chạy sự kiện thiếu kinh nghiệm xử lý sự cố",
            "Khó so sánh giá vì package mỗi nơi gộp khác nhau",
        ],
        search_keywords={
            "tam": ["thị trường wedding Việt Nam quy mô", "chi tiêu đám cưới trung bình Việt Nam", "số couple cưới {thành phố} {năm}"],
            "competitor": ["wedding planner {khu vực} uy tín", "công ty event {thành phố} top"],
            "trend": ["xu hướng wedding Việt Nam 2026", "concept wedding hot Instagram VN", "destination wedding Việt Nam"],
        },
    ),
}


def get_industry_context(industry: str) -> Optional[IndustryContext]:
    """Return industry context, hoặc None nếu chưa định nghĩa."""
    return INDUSTRY_CONTEXT.get(industry)


def get_industry_context_as_text(industry: str) -> str:
    """Format context (archetype + market dynamics + buyer psychology) cho prompt injection.

    KHÔNG bao gồm search_keywords (cái đó cho router, không cho prompt).
    Dùng cho Discovery/Strategy agents.
    """
    ctx = get_industry_context(industry)
    if not ctx:
        return ""

    lines = ["### Archetype mua hàng:"]
    primary_label = ARCHETYPE_LABEL.get(ctx.purchase_archetype, ctx.purchase_archetype)
    if ctx.archetype_secondary and ctx.archetype_blend:
        sec_label = ARCHETYPE_LABEL.get(ctx.archetype_secondary, ctx.archetype_secondary)
        lines.append(
            f"Primary: {primary_label} · Secondary: {sec_label} · Default blend: {ctx.archetype_blend}"
        )
    else:
        lines.append(f"{primary_label} (pure)")
    lines += [
        "",
        "### Động lực thị trường (VN):",
        ctx.market_dynamics,
        "",
        "### Lý do khách MUA (triggers):",
    ]
    lines += [f"- {t}" for t in ctx.buyer_triggers]
    lines += ["", "### Rào cản khách KHÔNG mua (objections):"]
    lines += [f"- {b}" for b in ctx.buyer_barriers]
    return "\n".join(lines)


def get_full_industry_brief(industry: str) -> str:
    """Gộp KPI framework (kpi_library) + industry context thành 1 block đầy đủ.

    Đây là context tổng để inject vào McKinsey Discovery + CMO Strategy.
    """
    parts = [get_framework_as_text(industry)]
    ctx_text = get_industry_context_as_text(industry)
    if ctx_text:
        parts += ["", "## Bối Cảnh Ngành (Market Dynamics & Buyer Psychology)", "", ctx_text]
    return "\n".join(parts)


def suggest_key_message_hint(
    industry: str,
    product_service: str = "",
    target_customer: str = "",
) -> str:
    """Gợi ý cách viết 'thông điệp chính' cho video — dựa trên Business của user
    (product_service / target_customer) ghép với tâm lý mua của ngành (KPI library
    + industry_context).

    Ý tưởng: 'thông điệp chính' mạnh nhất là câu neo vào ĐÚNG lý do khách mua
    (buyer_triggers) hoặc hoá giải ĐÚNG nỗi lo lớn nhất (buyer_barriers) của ngành,
    nói về sản phẩm cụ thể của business — thay vì 1 câu chung chung.

    Trả về block text ngắn (markdown) hiện dưới field key_message trong form.
    Rỗng nếu ngành chưa được định nghĩa → form fallback về example tĩnh.
    """
    ctx = get_industry_context(industry)
    fw = get_kpi_framework(industry)
    if not ctx and not fw:
        return ""

    subject = (product_service or "").strip() or "sản phẩm/dịch vụ của sếp"
    who = (target_customer or "").strip()
    name = fw.display_name if fw else industry

    lines = [f"💡 *Gợi ý cho ngành {name}* — thông điệp khách nhớ nhất thường neo vào:"]

    # Lý do khách MUA (trigger) — khuếch đại điều khách KHAO KHÁT
    if ctx and ctx.buyer_triggers:
        t = ctx.buyer_triggers[0]
        lines.append(f"• Điều khách muốn nhất: _{t}_")
        lines.append(f"  → vd: \"{subject} — {t.split('(')[0].strip().rstrip('.').lower()}\"")

    # Nỗi lo cần GỠ (barrier) — hoá giải rào cản khiến khách chần chừ
    if ctx and ctx.buyer_barriers:
        b = ctx.buyer_barriers[0]
        lines.append(f"• Nỗi lo cần gỡ: _{b}_")
        lines.append(f"  → vd: \"Đừng để {b.split('(')[0].strip().rstrip('.').lower()} cản bạn — {subject} ...\"")

    if who:
        lines.append(f"_(Viết cho đúng tệp: {who})_")

    lines.append("Chọn 1 góc, ghép với sản phẩm thành 1 câu duy nhất khách nhớ.")
    return "\n".join(lines)


def get_search_seeds(industry: str) -> dict:
    """Trả về search keywords seed cho grounded search (Phase 2 router).

    Returns {"tam": [...], "competitor": [...], "trend": [...]}.
    Placeholder {sản phẩm}/{khu vực}/{thành phố} sẽ được fill từ profile.
    """
    ctx = get_industry_context(industry)
    return ctx.search_keywords if ctx else {}


def list_industries() -> list[str]:
    """Danh sách industry keys (đồng bộ với kpi_library)."""
    return list(INDUSTRY_CONTEXT.keys())


# ─────────────────────────────────────────────────────────────────
# Archetype helpers
# ─────────────────────────────────────────────────────────────────

def get_purchase_archetype(industry: str) -> str:
    """Return primary archetype của ngành, hoặc '' nếu chưa định nghĩa."""
    ctx = get_industry_context(industry)
    return ctx.purchase_archetype if ctx else ""


def get_archetype_blend(industry: str) -> Optional[dict]:
    """Return blend declaration của ngành.

    {primary, secondary, blend, signals} hoặc None nếu chưa định nghĩa.
    Ngành pure (không secondary) vẫn return dict với secondary="" + blend="".
    """
    ctx = get_industry_context(industry)
    if not ctx:
        return None
    return {
        "primary":   ctx.purchase_archetype,
        "secondary": ctx.archetype_secondary,
        "blend":     ctx.archetype_blend,
        "signals":   list(ctx.archetype_override_signals),
    }


def resolve_archetype(industry: str, brief_text: str = "") -> dict:
    """Resolve archetype hiệu lực dựa trên brief text + override signals.

    Logic:
    - Pure industry (không secondary) → return primary, không flip.
    - Blend industry → nếu ≥1 signal match trong brief_text → flip primary ↔ secondary,
      đảo blend ratio. Còn lại giữ default.

    Returns:
        {
          "primary": str, "secondary": str, "blend": str,
          "pure": bool, "flipped": bool,
          "matched_signals": list[str],
          "reason": str,
        }
    """
    decl = get_archetype_blend(industry)
    if not decl:
        return {
            "primary": "", "secondary": "", "blend": "",
            "pure": True, "flipped": False,
            "matched_signals": [], "reason": "industry không có archetype declaration",
        }

    primary   = decl["primary"]
    secondary = decl["secondary"]
    blend     = decl["blend"]
    signals   = decl["signals"]

    if not secondary or not blend:
        return {
            "primary": primary, "secondary": "", "blend": "",
            "pure": True, "flipped": False,
            "matched_signals": [], "reason": "pure archetype, không có secondary",
        }

    brief_lower = (brief_text or "").lower()
    matched = [s for s in signals if s.lower() in brief_lower]

    if not matched:
        return {
            "primary": primary, "secondary": secondary, "blend": blend,
            "pure": False, "flipped": False,
            "matched_signals": [],
            "reason": f"default blend ({primary} {blend})",
        }

    # Flip: primary ↔ secondary, đảo blend ratio "A/B" → "B/A"
    parts = blend.split("/")
    flipped_blend = blend
    if len(parts) == 2:
        flipped_blend = f"{parts[1].strip()}/{parts[0].strip()}"

    return {
        "primary":   secondary,
        "secondary": primary,
        "blend":     flipped_blend,
        "pure":      False,
        "flipped":   True,
        "matched_signals": matched,
        "reason": f"flipped do match signals: {', '.join(matched)}",
    }


def list_industries_by_archetype() -> dict[str, list[str]]:
    """Group industry keys theo primary archetype.

    Return: {"impulse": [...], "demand_gen": [...], "trust_building": [...]}
    """
    result: dict[str, list[str]] = {
        ARCHETYPE_IMPULSE:        [],
        ARCHETYPE_DEMAND_GEN:     [],
        ARCHETYPE_TRUST_BUILDING: [],
    }
    for key, ctx in INDUSTRY_CONTEXT.items():
        bucket = result.setdefault(ctx.purchase_archetype, [])
        bucket.append(key)
    return result


def format_archetype_block(industry: str, brief_text: str = "") -> str:
    """Format archetype resolution → text block cho prompt injection (Strategy + Funnel).

    Compact, một block — chứa primary/secondary/blend + lý do flip nếu có.
    """
    res = resolve_archetype(industry, brief_text)
    if not res["primary"]:
        return ""

    primary_label = ARCHETYPE_LABEL.get(res["primary"], res["primary"])
    lines = [f"Archetype hiệu lực: **{primary_label}**"]

    if res["pure"]:
        lines.append("→ Pure archetype, không blend.")
    else:
        sec_label = ARCHETYPE_LABEL.get(res["secondary"], res["secondary"])
        lines.append(f"+ Secondary: {sec_label} (blend {res['blend']})")
        if res["flipped"]:
            lines.append(f"⚡ Đã FLIP từ default — {res['reason']}")
        else:
            lines.append(f"({res['reason']})")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────


def coverage_check() -> dict:
    """Dev helper — verify mọi ngành trong kpi_library đều có context."""
    kpi = set(_kpi_industries())
    ctx = set(INDUSTRY_CONTEXT.keys())
    return {
        "kpi_only":  sorted(kpi - ctx),   # ngành thiếu context
        "ctx_only":  sorted(ctx - kpi),   # context thừa
        "covered":   sorted(kpi & ctx),
        "complete":  kpi == ctx,
    }
