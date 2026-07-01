"""
Pricing Segment Library — phân khúc giá + kênh bán điển hình theo ngành.

Dùng cho câu hỏi chiến lược "pricing_approach" (5/8): thay vì hỏi pricing
model generic (premium/competitive/value/bundle...), hỏi founder muốn định
vị ở PHÂN KHÚC GIÁ nào — mỗi phân khúc đã gắn sẵn khoảng giá VND + kênh bán
điển hình phù hợp với ngành đó tại thị trường Việt Nam.

15 ngành cùng cấu trúc 3 phân khúc: Bình dân (Value) / Tầm trung (Mid) / Cao cấp (Premium).
"""

PRICING_SEGMENT_LIBRARY: dict[str, list[dict]] = {

    "fnb": [
        {"segment": "Bình dân", "price_range": "15.000–35.000đ/món",
         "channels": "Quán vỉa hè/take-away + app delivery (GrabFood/ShopeeFood) — volume cao"},
        {"segment": "Tầm trung", "price_range": "35.000–89.000đ/món",
         "channels": "Dine-in tại quán là chính, kết hợp delivery app + đặt trước qua Zalo/Facebook"},
        {"segment": "Cao cấp", "price_range": "90.000–250.000đ+/món",
         "channels": "Nhà hàng/concept store, đặt bàn online, hạn chế phụ thuộc app delivery"},
    ],

    "tech_saas": [
        {"segment": "Entry / Freemium", "price_range": "0–199.000đ/tháng",
         "channels": "Self-serve qua website/app store, free trial, product-led growth"},
        {"segment": "Growth / Pro", "price_range": "200.000–2.000.000đ/tháng",
         "channels": "Website signup + inside sales hỗ trợ demo"},
        {"segment": "Enterprise", "price_range": "2.000.000đ+/tháng hoặc custom quote",
         "channels": "Sales-led, demo trực tiếp, đối tác triển khai"},
    ],

    "ecommerce": [
        {"segment": "Bình dân", "price_range": "dưới 150.000đ/sản phẩm",
         "channels": "Shopee/TikTok Shop/Lazada — cạnh tranh giá, đẩy volume"},
        {"segment": "Tầm trung", "price_range": "150.000–500.000đ/sản phẩm",
         "channels": "Sàn TMĐT kết hợp Facebook/Instagram D2C"},
        {"segment": "Cao cấp", "price_range": "trên 500.000đ/sản phẩm",
         "channels": "Website D2C riêng + Instagram, hạn chế lên sàn để giữ định vị"},
    ],

    "education": [
        {"segment": "Bình dân", "price_range": "dưới 500.000đ (mini course/ebook)",
         "channels": "Facebook Ads → landing page tự động, group Zalo"},
        {"segment": "Tầm trung", "price_range": "500.000–3.000.000đ (khóa online có mentor)",
         "channels": "Webinar funnel, Facebook/YouTube Ads"},
        {"segment": "Cao cấp", "price_range": "trên 3.000.000đ (bootcamp/1-1 coaching)",
         "channels": "Sales call, referral, cộng đồng alumni"},
    ],

    "health_beauty": [
        {"segment": "Bình dân", "price_range": "dưới 200.000đ (sản phẩm) / dưới 300.000đ (dịch vụ)",
         "channels": "Sàn TMĐT, TikTok Shop"},
        {"segment": "Tầm trung", "price_range": "200.000–800.000đ (sản phẩm) / 300.000–1.000.000đ (dịch vụ)",
         "channels": "Facebook/Instagram D2C, spa walk-in"},
        {"segment": "Cao cấp", "price_range": "trên 800.000đ (sản phẩm) / trên 1.000.000đ (dịch vụ)",
         "channels": "Membership, app đặt lịch, spa/showroom cao cấp"},
    ],

    "retail": [
        {"segment": "Bình dân", "price_range": "dưới 100.000đ/sản phẩm",
         "channels": "GT — tạp hóa/đại lý, chợ truyền thống"},
        {"segment": "Tầm trung", "price_range": "100.000–500.000đ/sản phẩm",
         "channels": "Cửa hàng riêng + sàn TMĐT"},
        {"segment": "Cao cấp", "price_range": "trên 500.000đ/sản phẩm",
         "channels": "MT — siêu thị/TTTM, showroom + online D2C"},
    ],

    "b2b_service": [
        {"segment": "Bình dân", "price_range": "dưới 10 triệu đồng/tháng (gói nhỏ)",
         "channels": "Marketplace freelance (Upwork/VLance), referral"},
        {"segment": "Tầm trung", "price_range": "10–50 triệu đồng/tháng",
         "channels": "Outbound sales, website inbound, LinkedIn"},
        {"segment": "Cao cấp", "price_range": "trên 50 triệu đồng/tháng (enterprise retainer)",
         "channels": "Sales-led, network/referral, RFP"},
    ],

    "real_estate": [
        {"segment": "Bình dân", "price_range": "dưới 2 tỷ đồng/căn",
         "channels": "Sàn môi giới, Facebook/Zalo group"},
        {"segment": "Tầm trung", "price_range": "2–5 tỷ đồng/căn",
         "channels": "Sàn môi giới + sự kiện chủ đầu tư, Google Ads"},
        {"segment": "Cao cấp", "price_range": "trên 5 tỷ đồng/căn (cao cấp/villa)",
         "channels": "Private network, sự kiện mời riêng, KOL"},
    ],

    "health_clinic": [
        {"segment": "Bình dân", "price_range": "dưới 300.000đ/lượt khám",
         "channels": "BHYT/walk-in, Zalo OA đặt lịch"},
        {"segment": "Tầm trung", "price_range": "300.000–1.500.000đ/lượt khám",
         "channels": "Facebook/Google Ads, app đặt lịch"},
        {"segment": "Cao cấp", "price_range": "trên 1.500.000đ/gói khám chuyên khoa",
         "channels": "Referral từ bác sĩ, membership, concierge"},
    ],

    "agency": [
        {"segment": "Bình dân", "price_range": "dưới 15 triệu đồng/tháng",
         "channels": "Marketplace freelance, group Facebook ngành"},
        {"segment": "Tầm trung", "price_range": "15–60 triệu đồng/tháng",
         "channels": "Inbound content/SEO, referral"},
        {"segment": "Cao cấp", "price_range": "trên 60 triệu đồng/tháng",
         "channels": "Pitch trực tiếp, network, case study/portfolio site"},
    ],

    "fashion_retail": [
        {"segment": "Bình dân", "price_range": "dưới 200.000đ/sản phẩm",
         "channels": "Shopee/TikTok Shop, chợ online"},
        {"segment": "Tầm trung", "price_range": "200.000–700.000đ/sản phẩm",
         "channels": "Facebook/Instagram D2C, cửa hàng nhỏ"},
        {"segment": "Cao cấp", "price_range": "trên 700.000đ/sản phẩm",
         "channels": "Website riêng, showroom, Instagram/KOL"},
    ],

    "travel_hospitality": [
        {"segment": "Bình dân", "price_range": "dưới 500.000đ/đêm",
         "channels": "Booking.com/Agoda, group Facebook du lịch"},
        {"segment": "Tầm trung", "price_range": "500.000–2.000.000đ/đêm",
         "channels": "OTA kết hợp website riêng, Instagram"},
        {"segment": "Cao cấp", "price_range": "trên 2.000.000đ/đêm (resort/villa)",
         "channels": "Direct booking website, travel agent, KOL/influencer"},
    ],

    "interior_design": [
        {"segment": "Bình dân", "price_range": "dưới 3 triệu đồng/m²",
         "channels": "Facebook group, sàn vật liệu xây dựng"},
        {"segment": "Tầm trung", "price_range": "3–7 triệu đồng/m²",
         "channels": "Website portfolio, Instagram/Pinterest, referral"},
        {"segment": "Cao cấp", "price_range": "trên 7 triệu đồng/m²",
         "channels": "Showroom, network kiến trúc sư, triển lãm"},
    ],

    "pet_care": [
        {"segment": "Bình dân", "price_range": "dưới 150.000đ",
         "channels": "Sàn TMĐT, chợ thú cưng online"},
        {"segment": "Tầm trung", "price_range": "150.000–500.000đ",
         "channels": "Facebook/TikTok D2C, pet shop"},
        {"segment": "Cao cấp", "price_range": "trên 500.000đ (spa/grooming/premium food)",
         "channels": "Booking app, membership, pet hotel cao cấp"},
    ],

    "events_wedding": [
        {"segment": "Bình dân", "price_range": "dưới 30 triệu đồng/sự kiện",
         "channels": "Facebook group cô dâu, marketplace dịch vụ cưới"},
        {"segment": "Tầm trung", "price_range": "30–100 triệu đồng/sự kiện",
         "channels": "Website portfolio, Instagram, wedding fair"},
        {"segment": "Cao cấp", "price_range": "trên 100 triệu đồng/sự kiện",
         "channels": "Referral planner cao cấp, showroom, KOL wedding"},
    ],
}

# Fallback khi industry chưa xác định / không có trong library
_GENERIC_SEGMENTS: list[dict] = [
    {"segment": "Bình dân (Value)", "price_range": "thấp hơn mặt bằng chung thị trường ~10-20%",
     "channels": "Sàn TMĐT / kênh giá rẻ, đẩy volume"},
    {"segment": "Tầm trung (Mid)", "price_range": "ngang mặt bằng chung thị trường",
     "channels": "D2C online (Facebook/website) kết hợp kênh truyền thống"},
    {"segment": "Cao cấp (Premium)", "price_range": "cao hơn mặt bằng chung thị trường ~20-50%+",
     "channels": "D2C/showroom riêng, hạn chế phụ thuộc kênh giá rẻ"},
]


def get_pricing_segments(industry: str | None) -> list[dict]:
    """Trả về 3 phân khúc giá (Bình dân/Tầm trung/Cao cấp) cho ngành.
    Fallback về _GENERIC_SEGMENTS nếu industry None / không có trong library."""
    return PRICING_SEGMENT_LIBRARY.get(industry or "", _GENERIC_SEGMENTS)


def format_pricing_segments_for_prompt(industry: str | None) -> str:
    """Format 3 phân khúc giá thành markdown block để inject vào prompt LLM."""
    segments = get_pricing_segments(industry)
    lines = [f"## Phân khúc giá tham khảo — ngành `{industry or 'chưa xác định'}`"]
    for seg in segments:
        lines.append(f"- **{seg['segment']}**: {seg['price_range']} — kênh bán điển hình: {seg['channels']}")
    return "\n".join(lines)
