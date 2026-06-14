"""
Bộ não ngành cho content skills — 1 nguồn, nhiều persona ngành.

Tại runtime, _run_skill (agents/pipeline.py — INDUSTRY_BRAIN_SKILLS) detect
session.profile.industry rồi nạp đúng "bộ não ngành" tương ứng vào prompt của
các skill sản xuất content (post_batch, video_script_gen, ugc_brief, ads, email).

Key = KPI library industry key (fnb, health_beauty, tech_saas, ...).
get_social_industry_profile(industry) trả về block text inject vào user_msg.
"""

# Mỗi profile = chuyên môn viết content hữu cơ riêng cho 1 ngành.
# Cấu trúc thống nhất: Hook pattern · Tone · Kênh+giờ vàng · CTA · Tuyến nội dung đặc thù · Tránh.
# LƯU Ý THUẬT NGỮ: "Tuyến nội dung đặc thù" = các FORMAT/tuyến content riêng của ngành
# (food porn, unboxing, before/after...). KHÁC với "Content angle" (lăng kính chiến lược:
# Pain/Outcome/Social proof/Urgency... do Funnel Map quyết định). Mỗi tuyến phục vụ 1 angle —
# dòng "→ Angle tương ứng" map sẵn để LLM điền đúng cột Content angle của Calendar.
SOCIAL_INDUSTRY_PROFILES: dict[str, str] = {
    "fnb": """**🎯 BỘ NÃO NGÀNH: F&B (quán ăn / cafe / nhà hàng)**

**Hook pattern hiệu quả nhất:**
- Hunger trigger — mô tả vị giác cụ thể: "Lớp phô mai kéo sợi 30cm này..."
- Behind-the-scenes — bếp/nguyên liệu tươi: "5h sáng tụi mình đã ra chợ chọn..."
- Vibe/không gian — cảm giác ngồi quán: "Góc cửa sổ nắng chiều + 1 ly trà đào"
- Local pride — đặc sản vùng miền, câu chuyện món

**Tone:** Ấm áp, gần gũi, kích thích giác quan. Dùng tính từ vị giác (giòn/béo/thơm/đậm đà). Tránh academic.

**Kênh + giờ vàng:** Facebook + Instagram (Reels món ăn). Đăng 10-11h (trước bữa trưa) + 17-18h (trước bữa tối) + 20-21h (lướt tối).

**CTA mạnh:** "Tag đứa bạn hay rủ đi ăn" · "Inbox 'đặt bàn' giữ chỗ cuối tuần" · "Comment 'menu' nhận bảng giá"

**Tuyến nội dung đặc thù (format):**
- Món signature cận cảnh (food porn)
- Khách review thật (UGC) + phản ứng lần đầu nếm
- Combo/deal theo khung giờ (happy hour, set trưa)
- Câu chuyện đầu bếp / nguồn nguyên liệu
**→ Angle tương ứng:** food porn→Aspiration · review khách→Social proof · combo/deal→Urgency · chuyện đầu bếp→Authority

**Tránh:** Caption khô kiểu "Quán có món X giá Y". Đừng liệt kê menu — kể trải nghiệm ăn.""",

    "health_beauty": """**🎯 BỘ NÃO NGÀNH: Health & Beauty (spa / skincare / thẩm mỹ)**

**Hook pattern hiệu quả nhất:**
- Transformation — before/after, hành trình da: "30 ngày trước em không dám soi gương..."
- Insecurity chạm sâu (tinh tế, không body-shaming): "Mỗi sáng dậy thấy da xỉn màu là tụt mood cả ngày"
- Myth-busting — đập tan lầm tưởng: "Da dầu KHÔNG nên bỏ kem dưỡng — đây là lý do"
- Self-care permission: "Chăm da không phải phù phiếm — đó là cách yêu bản thân"

**Tone:** Aspirational + empathetic. Đồng cảm pain, rồi nâng đỡ. Chuyên môn nhẹ (đủ tin tưởng, không thành bài giảng da liễu).

**Kênh + giờ vàng:** Facebook + Instagram + TikTok (transformation video). Đăng 12h (nghỉ trưa) + 20-22h (skincare routine tối).

**CTA mạnh:** "Inbox 'tư vấn da' để được soi da free" · "DM 'booking' giữ lịch" · "Comment loại da của bạn để mình gợi ý"

**Tuyến nội dung đặc thù (format):**
- Soi da / phân tích vấn đề da khách thật
- Routine sáng-tối theo loại da
- Khách kể trải nghiệm (UGC, EGC nhân viên)
- Giải thích thành phần (niacinamide, BHA...) đơn giản
**→ Angle tương ứng:** soi da/vấn đề→Pain · routine→Mechanism/Outcome · khách kể→Social proof · thành phần→Authority

**Tránh:** Claim chữa khỏi 100%, cam kết phi thực tế. Đừng dọa khách (fear-mongering quá đà).""",

    "education": """**🎯 BỘ NÃO NGÀNH: Education (khóa học / coaching / trung tâm)**

**Hook pattern hiệu quả nhất:**
- Authority/insider: "10 năm dạy IELTS, đây là sai lầm khiến học viên mãi 6.0"
- Counterintuitive: "Học từ vựng kiểu này khiến bạn quên nhanh hơn"
- Outcome-driven: "Học viên này từ mất gốc → giao tiếp được sau 3 tháng"
- Pain of inaction: "Trì hoãn học tiếng Anh đang khiến bạn mất bao nhiêu cơ hội lương?"

**Tone:** Professional nhưng gần gũi, truyền cảm hứng. Cân bằng uy tín chuyên gia + sự đồng hành.

**Kênh + giờ vàng:** Facebook + YouTube (kiến thức dài) + TikTok (tip ngắn). Đăng 12h + 20-22h (giờ học viên rảnh học buổi tối).

**CTA mạnh:** "Comment 'tài liệu' nhận free lộ trình" · "Inbox 'test trình độ'" · "Join nhóm học miễn phí (link bio)"

**Tuyến nội dung đặc thù (format):**
- Tip/hack học nhanh (giá trị free trước)
- Học viên success story + lộ trình cụ thể
- Phá vỡ lầm tưởng phương pháp học
- Mini-lesson demo chất lượng giảng dạy
**→ Angle tương ứng:** tip/hack→Authority · success story→Social proof/Outcome · phá lầm tưởng→Objection · mini-lesson→Mechanism/Authority

**Tránh:** Hứa "giỏi sau X ngày" phi thực tế. Đừng chỉ khoe bằng cấp — chứng minh bằng giá trị thật.""",

    "ecommerce": """**🎯 BỘ NÃO NGÀNH: E-commerce (shop online / bán hàng đa kênh)**

**Hook pattern hiệu quả nhất:**
- Urgency/scarcity: "Còn 12 cái cuối — đợt sau giá tăng 20%"
- Social proof: "3.000 đơn tháng này, đây là lý do khách quay lại"
- Product curiosity: "Cái máy nhỏ này thay được 5 dụng cụ bếp"
- Problem-solution: "Hết cảnh tủ lạnh bừa bộn với combo hộp này"

**Tone:** Energetic, deal-focused, rõ ràng. Nhấn lợi ích + ưu đãi, tạo cảm giác hành động ngay.

**Kênh + giờ vàng:** Facebook + TikTok Shop (video review/demo) + Instagram. Đăng 12h + 19-22h (peak mua sắm tối).

**CTA mạnh:** "Inbox 'đặt hàng' chốt đơn" · "Link giỏ hàng ở bio/comment" · "Comment 'size' để được tư vấn"

**Tuyến nội dung đặc thù (format):**
- Demo sản phẩm thực tế (unboxing, công dụng)
- Review khách thật + ảnh nhận hàng (UGC)
- Flash sale / combo / freeship theo khung giờ
- So sánh trước-sau khi dùng sản phẩm
**→ Angle tương ứng:** demo/unboxing→Mechanism/Outcome · review khách→Social proof · flash sale/combo→Urgency · trước-sau→Outcome/Pain

**Tránh:** Spam giá liên tục không có giá trị. Đừng dùng ảnh stock — khách e-com tin ảnh thật.""",

    "tech_saas": """**🎯 BỘ NÃO NGÀNH: Tech / SaaS (phần mềm / nền tảng / công cụ)**

**Hook pattern hiệu quả nhất:**
- Problem-solution rõ ROI: "Team bạn mất 10h/tuần làm báo cáo tay — tự động trong 5 phút"
- "Bạn đang làm sai": "90% doanh nghiệp dùng Excel quản kho đang mất tiền âm thầm"
- Data/insight: "Khảo sát 500 SME: lý do #1 thất thoát doanh thu là..."
- Use-case cụ thể: "Cách 1 shop 3 nhân viên xử lý 1.000 đơn/ngày"

**Tone:** Authoritative, precise, đáng tin. Ngôn ngữ business, tập trung hiệu quả + tiết kiệm + tăng trưởng. Ít cảm xúc, nhiều logic.

**Kênh + giờ vàng:** LinkedIn + Facebook (group ngành) + YouTube (demo/webinar). Đăng 8-9h (giờ làm sáng) + 13-14h.

**CTA mạnh:** "Đăng ký demo 1:1 (link bio)" · "Dùng thử miễn phí 14 ngày" · "Inbox 'tư vấn giải pháp'"

**Tuyến nội dung đặc thù (format):**
- Case study khách + con số ROI cụ thể
- So sánh quy trình thủ công vs dùng phần mềm
- Tip/insight ngành (thought leadership)
- Demo tính năng giải quyết pain cụ thể
**→ Angle tương ứng:** case study+ROI→Social proof/Outcome · thủ công vs phần mềm→Objection · tip/insight→Authority · demo tính năng→Mechanism/Pain

**Tránh:** Jargon kỹ thuật quá đà. Đừng nói về tính năng — nói về kết quả kinh doanh tính năng đó tạo ra.""",

    "agency": """**🎯 BỘ NÃO NGÀNH: Agency / Dịch vụ B2B (marketing, tư vấn, dịch vụ chuyên môn)**

**Hook pattern hiệu quả nhất:**
- Thought leadership: "Tại sao 80% campaign chết ở bước này (và cách fix)"
- Case result: "Đưa client từ 50 lead → 300 lead/tháng — đây là chiến lược"
- Contrarian take: "Chạy nhiều ads hơn KHÔNG giải quyết vấn đề doanh thu"
- Behind-the-process: "Cách team mình audit 1 tài khoản ads trong 30 phút"

**Tone:** Chuyên gia tự tin, sắc bén, có quan điểm. Chứng minh năng lực qua insight thật, không khoe khoang rỗng.

**Kênh + giờ vàng:** LinkedIn + Facebook (group founder/marketer). Đăng 8-9h + 13h (giờ decision-maker online).

**CTA mạnh:** "Inbox 'audit miễn phí'" · "Đặt lịch tư vấn 30 phút (link)" · "Comment 'case study' nhận tài liệu"

**Tuyến nội dung đặc thù (format):**
- Case study client + số liệu trước/sau
- Framework/quy trình độc quyền (cho free để build trust)
- Phân tích sai lầm phổ biến của ngành client
- Behind-the-scenes cách team làm việc
**→ Angle tương ứng:** case study→Social proof/Outcome · framework độc quyền→Authority/Mechanism · phân tích sai lầm→Objection/Authority · behind-the-scenes→Authority

**Tránh:** Generic "chúng tôi cung cấp dịch vụ X". Đừng nói chung chung — show kết quả + tư duy cụ thể.""",

    "real_estate": """**🎯 BỘ NÃO NGÀNH: Real Estate (BĐS / môi giới / dự án)**

**Hook pattern hiệu quả nhất:**
- Investment angle: "Khu này tăng 30% trong 2 năm — đây là lý do còn dư địa"
- Lifestyle aspiration: "Sáng cafe ban công nhìn sông — căn này có thật"
- Scarcity: "Chỉ còn 3 căn hướng Đông Nam tầng đẹp"
- Insider knowledge: "Trước khi xuống tiền, kiểm tra 5 điều này về pháp lý"

**Tone:** Aspirational + nghiêm túc đáng tin. Cân bằng cảm xúc (tổ ấm/đầu tư) + lý trí (pháp lý, ROI, vị trí).

**Kênh + giờ vàng:** Facebook + Zalo OA (chăm lead kỹ) + YouTube (review dự án/nhà mẫu). Đăng 12h + 20-21h.

**CTA mạnh:** "Inbox 'xem dự án' nhận bảng giá + chính sách" · "Để lại SĐT nhận tư vấn 1:1" · "Hotline xem nhà mẫu cuối tuần"

**Tuyến nội dung đặc thù (format):**
- Tour dự án/căn hộ (video walkthrough)
- Phân tích tiềm năng tăng giá khu vực + tiện ích
- Hướng dẫn pháp lý / vay mua nhà (giá trị free)
- Câu chuyện khách đã an cư/đầu tư thành công
**→ Angle tương ứng:** tour dự án→Aspiration/Mechanism · tiềm năng tăng giá→Outcome/Authority · pháp lý/vay→Objection/Authority · khách an cư→Social proof

**Tránh:** Cam kết lợi nhuận chắc chắn (rủi ro pháp lý). Đừng spam giá — xây niềm tin trước vì deal lớn, quyết định lâu.""",

    "retail": """**🎯 BỘ NÃO NGÀNH: Retail (cửa hàng / chuỗi bán lẻ)**

**Hook pattern hiệu quả nhất:**
- New arrival/trend: "Hàng mới về — món này đang cháy ở store"
- In-store experience: "Ghé store cuối tuần có gì vui"
- Bundle value: "Mua combo này tiết kiệm hơn mua lẻ 200K"
- Local/community: "Khách quen ở [khu vực] đều mê món này"

**Tone:** Thân thiện, năng động, gần gũi cộng đồng địa phương. Tạo cảm giác muốn ghé trải nghiệm trực tiếp.

**Kênh + giờ vàng:** Facebook + Instagram + TikTok. Đăng 11-12h + 18-21h (sau giờ làm, lên kế hoạch đi shopping).

**CTA mạnh:** "Ghé store [địa chỉ] cuối tuần" · "Inbox giữ hàng" · "Comment 'ship' đặt online"

**Tuyến nội dung đặc thù (format):**
- Hàng mới về / bộ sưu tập theo mùa
- Không khí store, sự kiện tại cửa hàng
- Combo/khuyến mãi theo dịp
- Khách mua sắm thật (UGC tại store)
**→ Angle tương ứng:** hàng mới/BST→Aspiration · không khí store→Aspiration · combo/khuyến mãi→Urgency · khách mua sắm→Social proof

**Tránh:** Chỉ đăng ảnh sản phẩm trên nền trắng. Bán lẻ cần cảm giác cộng đồng + trải nghiệm tại chỗ.""",

    "fashion_retail": """**🎯 BỘ NÃO NGÀNH: Fashion (thời trang / phụ kiện)**

**Hook pattern hiệu quả nhất:**
- Style aspiration: "Outfit này lên hình 10 điểm mà giá chưa tới 500K"
- Trend alert: "Màu đang viral mùa này — phối thế nào cho sang"
- Styling tip: "1 chiếc blazer = 5 cách mặc đi làm tới đi chơi"
- Body confidence: "Dáng người [X] mặc kiểu này tôn dáng nhất"

**Tone:** Cool, aesthetic, truyền cảm hứng phong cách. Hình ảnh là chính — caption ngắn, có gu.

**Kênh + giờ vàng:** Instagram + TikTok (lookbook/styling video) + Facebook. Đăng 12h + 19-22h.

**CTA mạnh:** "Tag đứa bạn hợp set này" · "Inbox 'size' tư vấn" · "Link shop ở bio · Comment 'mã' nhận giá"

**Tuyến nội dung đặc thù (format):**
- Lookbook / phối đồ theo dịp (đi làm, dự tiệc, dạo phố)
- Styling tip theo dáng người / màu da
- Hậu trường photoshoot, BST mới
- Khách mặc thật (UGC) + review chất vải/form
**→ Angle tương ứng:** lookbook/phối đồ→Aspiration · styling tip→Mechanism/Objection · hậu trường/BST→Aspiration/Authority · khách mặc thật→Social proof

**Tránh:** Ảnh sản phẩm phẳng thiếu styling. Thời trang bán bằng cảm hứng phong cách, không bằng thông số.""",

    "health_clinic": """**🎯 BỘ NÃO NGÀNH: Phòng khám / Y tế (nha khoa, đa khoa, chuyên khoa)**

**Hook pattern hiệu quả nhất:**
- Pain point sức khỏe: "Đau răng âm ỉ về đêm — dấu hiệu bạn không nên bỏ qua"
- Expertise/trust: "Bác sĩ 15 năm giải thích vì sao niềng răng sớm quan trọng"
- Myth-busting: "Lấy cao răng KHÔNG làm răng yếu đi — sự thật là..."
- Prevention: "5 thói quen âm thầm phá men răng mỗi ngày"

**Tone:** Chuyên nghiệp, đáng tin, ân cần. Uy tín y khoa + sự an tâm. Tuyệt đối không gây hoang mang quá mức.

**Kênh + giờ vàng:** Facebook + Zalo OA (đặt lịch + nhắc lịch) + YouTube. Đăng 12h + 19-21h.

**CTA mạnh:** "Inbox 'đặt lịch' khám" · "Để lại SĐT nhận tư vấn từ bác sĩ" · "Comment triệu chứng để được hướng dẫn"

**Tuyến nội dung đặc thù (format):**
- Bác sĩ giải thích bệnh lý / quy trình điều trị
- Case điều trị thật (có đồng ý, che thông tin)
- Hướng dẫn phòng ngừa, chăm sóc tại nhà
- Giới thiệu thiết bị/công nghệ + đội ngũ
**→ Angle tương ứng:** bác sĩ giải thích→Authority/Pain · case điều trị→Social proof/Outcome · phòng ngừa→Authority/Pain · thiết bị/đội ngũ→Authority/Mechanism

**Tránh:** Claim chữa khỏi tuyệt đối, so sánh hạ thấp nơi khác. Tuân thủ quảng cáo y tế — không phóng đại.""",

    "pet_care": """**🎯 BỘ NÃO NGÀNH: Pet Care (thú cưng / spa thú / pet shop / phòng khám thú y)**

**Hook pattern hiệu quả nhất:**
- Cuteness + relatable: "Khoảnh khắc boss được tắm xong fluffy như cục bông"
- Pain của sen: "Lông rụng khắp nhà? Đây là lý do và cách xử lý"
- Health awareness: "3 dấu hiệu boss đang đau mà sen hay bỏ qua"
- Before/after grooming: "Từ xù xì → tiểu thư sau 1 buổi spa"

**Tone:** Dễ thương, ấm áp, đồng cảm với "sen". Pha hài hước nhẹ, gọi thú cưng là "boss/bé".

**Kênh + giờ vàng:** Facebook + TikTok + Instagram (video pet cực ăn tương tác). Đăng 12h + 20-22h.

**CTA mạnh:** "Inbox 'đặt lịch spa cho boss'" · "Comment tên bé để được tư vấn" · "Tag hội sen nuôi [loài]"

**Tuyến nội dung đặc thù (format):**
- Before/after grooming, khoảnh khắc dễ thương
- Tip chăm sóc (ăn uống, lông, sức khỏe)
- Case khám/điều trị (thú y)
- Khách + boss thật (UGC)
**→ Angle tương ứng:** before/after grooming→Outcome/Aspiration · tip chăm sóc→Authority/Pain · case khám→Social proof/Authority · khách+boss→Social proof

**Tránh:** Quá khô khan về dịch vụ. Ngành này sống bằng cảm xúc yêu thú cưng — content phải "cưng".""",

    "events_wedding": """**🎯 BỘ NÃO NGÀNH: Events / Wedding (cưới hỏi / sự kiện / tiệc)**

**Hook pattern hiệu quả nhất:**
- Emotional moment: "Khoảnh khắc cô dâu bật khóc khi thấy không gian tiệc"
- Aspiration: "Đám cưới trong mơ không cần ngân sách khổng lồ — đây là cách"
- Behind-the-scenes: "Hậu trường set up 500 bông tươi trong 6 tiếng"
- Tip/checklist: "7 điều cặp đôi hay quên khi lên kế hoạch cưới"

**Tone:** Cảm xúc, lãng mạn, tinh tế. Bán giấc mơ + sự an tâm "có người lo trọn gói".

**Kênh + giờ vàng:** Instagram + Facebook (album/video cảm xúc) + TikTok. Đăng 12h + 20-22h.

**CTA mạnh:** "Inbox 'tư vấn gói cưới'" · "Để lại ngày cưới nhận báo giá" · "Comment 'concept' xem portfolio"

**Tuyến nội dung đặc thù (format):**
- Real wedding / event đã thực hiện (album, video)
- Concept/decor theo phong cách (vintage, hiện đại...)
- Checklist/timeline chuẩn bị (giá trị free)
- Hậu trường ekip + lời cảm ơn từ cặp đôi
**→ Angle tương ứng:** real wedding→Social proof/Aspiration · concept/decor→Aspiration · checklist/timeline→Authority/Objection · hậu trường ekip→Authority/Mechanism

**Tránh:** Chỉ báo giá khô khan. Ngành cảm xúc cao — phải cho khách "thấy" giấc mơ của họ thành hiện thực.""",

    "interior_design": """**🎯 BỘ NÃO NGÀNH: Interior Design (nội thất / thiết kế / thi công)**

**Hook pattern hiệu quả nhất:**
- Transformation: "Căn hộ 50m² từ bừa bộn → sang như showroom"
- Aspiration: "Phòng khách kiểu này ai bước vào cũng phải wow"
- Problem-solution: "Nhà nhỏ vẫn rộng thênh thang nhờ 5 nguyên tắc này"
- Insider tip: "Chọn sai ánh sáng làm hỏng cả thiết kế đẹp"

**Tone:** Tinh tế, có gu, truyền cảm hứng sống đẹp. Cân bằng thẩm mỹ + công năng + ngân sách thực tế.

**Kênh + giờ vàng:** Instagram + Facebook (before/after, 3D render) + YouTube (tour nhà). Đăng 12h + 20-22h.

**CTA mạnh:** "Inbox 'tư vấn thiết kế'" · "Để lại diện tích nhận báo giá" · "Comment 'concept' xem portfolio"

**Tuyến nội dung đặc thù (format):**
- Before/after công trình thực tế
- Tip bố trí không gian / chọn vật liệu / phối màu
- Tour công trình hoàn thiện (video)
- Xu hướng nội thất theo phong cách
**→ Angle tương ứng:** before/after công trình→Outcome/Aspiration · tip bố trí/vật liệu→Authority/Mechanism · tour công trình→Aspiration/Social proof · xu hướng→Aspiration/Authority

**Tránh:** Chỉ khoe render đẹp không kèm câu chuyện/công năng. Khách cần thấy giải pháp cho nhà CỦA HỌ.""",

    "travel_hospitality": """**🎯 BỘ NÃO NGÀNH: Travel / Hospitality (du lịch / khách sạn / homestay / tour)**

**Hook pattern hiệu quả nhất:**
- Wanderlust: "Góc check-in này đẹp tới mức không cần filter"
- Experience: "1 đêm ở đây = quên hết deadline công sở"
- Tip/guide: "Lịch trình 3 ngày 2 đêm [địa danh] chuẩn không cần chỉnh"
- Deal/season: "Mùa này đi [nơi] vừa đẹp vừa rẻ — đây là lý do"

**Tone:** Truyền cảm hứng xê dịch, thư giãn, gợi cảm giác trải nghiệm. Hình ảnh/video cảnh đẹp là linh hồn.

**Kênh + giờ vàng:** Instagram + TikTok (cảnh đẹp/review) + Facebook. Đăng 12h + 20-22h (giờ mơ mộng lên kế hoạch đi chơi).

**CTA mạnh:** "Inbox 'đặt phòng/tour'" · "Tag đứa bạn muốn đi cùng" · "Comment 'lịch trình' nhận guide free"

**Tuyến nội dung đặc thù (format):**
- Cảnh đẹp / góc check-in / không gian lưu trú
- Trải nghiệm khách thật (UGC, review)
- Guide/lịch trình + tip du lịch (giá trị free)
- Combo/ưu đãi theo mùa, dịp lễ
**→ Angle tương ứng:** cảnh đẹp/check-in→Aspiration · trải nghiệm khách→Social proof · guide/lịch trình→Authority/Objection · combo/ưu đãi mùa→Urgency

**Tránh:** Ảnh thiếu cảm xúc/quá chỉnh sửa giả tạo. Du lịch bán bằng cảm giác "muốn đi ngay".""",
}

# Fallback khi industry chưa map (hoặc rỗng).
SOCIAL_GENERIC_PROFILE = """**🎯 BỘ NÃO NGÀNH: Chung (chưa xác định ngành cụ thể)**

**Hook pattern:** Linh hoạt theo 5 nhóm tâm lý (tò mò / trái ngược / cảm xúc / thẩm quyền / đồng cảm) — đây là Hook STYLE (cách mở), KHÔNG phải Content angle.
**Content angle (lăng kính chiến lược):** lấy từ Funnel Map của bài (Pain/Outcome/Social proof/Aspiration/Objection/Mechanism/Urgency/Authority) — KHÔNG tự bịa.
**Tone:** Bám sát profile business + pillar của Calendar. Match cảm xúc với sản phẩm/khách hàng cụ thể.
**Kênh + giờ vàng:** Theo kênh trong Calendar. Facebook 8-9h/11-12h/20-21h · Zalo OA 8h/12h/19h · Instagram/TikTok 12h/20-22h.
**CTA:** Keyword cụ thể (Inbox/Comment/Link) — KHÔNG generic.
**Lưu ý:** Vì chưa rõ ngành, bám CHẶT vào product_service + target_customer trong profile để content không bị chung chung."""


# Gợi ý "tuyến content" TikTok theo ngành — dùng để hỏi user chọn tuyến muốn
# tập trung khi dựng Content Calendar (BACKLOG #10b). Mỗi entry là 3-4 tuyến
# ngắn gọn, đặc thù ngành, phù hợp định dạng video ngắn TikTok.
TIKTOK_CONTENT_LINES: dict[str, str] = {
    "fnb": "Food porn cận cảnh món signature · Behind-the-scenes bếp/sơ chế · Review khách thật (UGC) · Trend âm thanh + món ăn",
    "health_beauty": "Before/after transformation · Routine sáng-tối · Myth-busting da liễu · Khách kể trải nghiệm (UGC/EGC)",
    "education": "Tip/hack học nhanh dạng nhanh · Học viên success story · Phá lầm tưởng phương pháp học · Mini-lesson demo",
    "ecommerce": "Unboxing/demo sản phẩm · Review khách thật (UGC) · Flash sale/đếm ngược · So sánh trước-sau dùng sản phẩm",
    "tech_saas": "Demo tính năng giải pain cụ thể · So sánh thủ công vs dùng phần mềm · Case study + số ROI · Tip/insight ngành",
    "agency": "Behind-the-process làm việc · Case result trước/sau · Contrarian take ngắn · Framework độc quyền (free)",
    "real_estate": "Tour căn hộ/dự án (walkthrough) · Lifestyle aspiration không gian sống · Tip pháp lý/vay mua nhà · Khách an cư thành công",
    "retail": "Hàng mới về / trend · Không khí tại store · Combo/khuyến mãi theo dịp · Khách mua sắm thật (UGC tại store)",
    "fashion_retail": "Lookbook/phối đồ theo dịp · Styling tip theo dáng người · Hậu trường photoshoot/BST mới · Khách mặc thật (UGC)",
    "health_clinic": "Bác sĩ giải thích bệnh lý/quy trình · Hướng dẫn phòng ngừa tại nhà · Giới thiệu thiết bị/đội ngũ · Case điều trị thật (đã đồng ý)",
    "pet_care": "Before/after grooming · Khoảnh khắc dễ thương boss · Tip chăm sóc thú cưng · Khách + boss thật (UGC)",
    "events_wedding": "Real wedding/event highlight · Hậu trường set up · Checklist chuẩn bị (giá trị free) · Khoảnh khắc cảm xúc cặp đôi",
    "interior_design": "Before/after công trình · Tour công trình hoàn thiện · Tip bố trí/chọn vật liệu · Xu hướng nội thất theo phong cách",
    "travel_hospitality": "Cảnh đẹp/góc check-in · Trải nghiệm khách thật (UGC) · Guide/lịch trình ngắn · Combo/ưu đãi theo mùa",
}

TIKTOK_CONTENT_LINES_GENERIC = (
    "Storytime/behind-the-scenes · Tip/hack ngắn liên quan sản phẩm · "
    "Trend/âm thanh viral gắn brand · Khách/người dùng thật (UGC)"
)


def get_tiktok_content_lines(industry: str) -> str:
    """Trả về gợi ý 'tuyến content' TikTok theo industry key (BACKLOG #10b).

    Không match → generic fallback.
    """
    key = (industry or "").strip().lower()
    return TIKTOK_CONTENT_LINES.get(key, TIKTOK_CONTENT_LINES_GENERIC)


def get_social_industry_profile(industry: str) -> str:
    """Trả về bộ não ngành theo industry key.

    industry = session.profile.industry (đã là KPI key, vd 'fnb', 'health_beauty').
    Không match → generic fallback.
    """
    key = (industry or "").strip().lower()
    return SOCIAL_INDUSTRY_PROFILES.get(key, SOCIAL_GENERIC_PROFILE)


# Alias craft-agnostic — dùng chung cho mọi content skill (post / video / ads / email / ugc).
# Bộ não ngành (hook pattern, tone, angle, anti-pattern) transfer được qua mọi craft;
# từng skill tự điều chỉnh phần kênh/CTA cho định dạng của nó.
get_industry_content_profile = get_social_industry_profile
