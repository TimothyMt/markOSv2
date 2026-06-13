"""
Output format instructions — 3 variants injected into agent system prompt.

Strategic: 4 sections (Insight / Tóm tắt / Benchmarks / Detail) — existing.
Operational Deliverable: file-style output (ad copy, brief, calendar...) — new.
Operational Analysis: audit-style (verdict + KPI table + actions) — new.

LANGUAGE & DATA DISCIPLINE rules apply to ALL formats uniformly.
"""

# ─────────────────────────────────────────────────────────────────
# Language preference instruction — injected based on user en_level
# ─────────────────────────────────────────────────────────────────

LANG_INSTRUCTIONS = {
    "none": """**NGÔN NGỮ (USER KHÔNG RÀNH TIẾNG ANH):**
- DÙNG THUẦN VIỆT TOÀN BỘ — kể cả thuật ngữ marketing.
- Translate examples:
  * CAC → "chi phí thu một khách hàng"
  * TAM → "quy mô thị trường tối đa"
  * SAM → "thị trường khả thi"
  * SOM → "thị phần khả dĩ"
  * ROAS → "tỷ lệ doanh thu/chi phí ads"
  * CPMess → "chi phí một tin nhắn"
  * AOV → "giá trị đơn hàng trung bình"
  * ICP → "chân dung khách hàng lý tưởng"
  * JTBD → "nhiệm vụ khách cần hoàn thành"
  * TOFU/MOFU/BOFU → "tệp lạnh / tệp ấm / tệp nóng"
  * UGC → "nội dung khách thật làm"
  * EGC → "nội dung nhân viên làm"
  * SMART → "Cụ thể / Đo được / Khả thi / Liên quan / Có thời hạn"
  * SAVE → "Giải pháp / Tiếp cận / Giá trị / Giáo dục"
- KHÔNG dùng từ Anh trong output trừ tên brand (Cocoon, M.O.I, Facebook, TikTok).""",

    "moderate": """**NGÔN NGỮ (USER HIỂU TIẾNG ANH CƠ BẢN):**
- Thuật ngữ marketing Anh BẮT BUỘC kèm giải thích Việt trong ngoặc lần đầu xuất hiện:
  * "TAM (Total Addressable Market — quy mô thị trường tối đa)"
  * "CAC (Customer Acquisition Cost — chi phí thu khách)"
  * "ROAS (Return On Ad Spend — tỷ lệ doanh thu/ads)"
  * "ICP (Ideal Customer Profile — chân dung khách lý tưởng)"
  * "JTBD (Jobs-to-be-Done — nhiệm vụ khách cần làm)"
  * "TOFU/MOFU/BOFU (Top/Middle/Bottom of Funnel — đầu/giữa/cuối phễu)"
- Sau khi giải thích 1 lần → dùng viết tắt tự do
- CHỈ giải thích inline trong ngoặc lần đầu — KHÔNG tạo section "Ghi chú thuật ngữ"/glossary riêng ở cuối.
- SMART/SAVE Goals viết FULL: "S (Specific — Cụ thể): ..." """,

    "fluent": """**NGÔN NGỮ (USER THÔNG THẠO TIẾNG ANH):**
- Dùng thuật ngữ marketing Anh tự nhiên: TAM, SAM, SOM, CAC, ROAS, AOV, ICP, JTBD, TOFU/MOFU/BOFU, UGC/EGC, SMART, SAVE.
- KHÔNG cần giải thích trong ngoặc — user đã hiểu.
- Câu văn vẫn bằng tiếng Việt (chỉ thuật ngữ là English).""",
}


def get_lang_instruction(en_level: str = "moderate") -> str:
    """Get language preference instruction based on user en_level."""
    return LANG_INSTRUCTIONS.get(en_level, LANG_INSTRUCTIONS["moderate"])


# ─────────────────────────────────────────────────────────────────
# Shared rules — applied to all formats
# ─────────────────────────────────────────────────────────────────

_SHARED_DATA_DISCIPLINE = """**NGUYÊN TẮC DỮ LIỆU (BẮT BUỘC — áp dụng cho TẤT CẢ con số/claim):**

**1. CITE NGUỒN khi có data thật trong training:**
- Dùng tên nguồn rõ ràng: "Theo Statista...", "GSO báo cáo...", "Nielsen 2024 chỉ ra..."
- CHỈ được cite nguồn từ danh sách sau:
  `Statista, GSO, Tổng cục Thống kê, WorldBank, Nielsen, Q&Me, Decision Lab, Vietcetera, CafeF, VnEconomy, Brands Vietnam, Advertising Vietnam, iPrice, Cốc Cốc, Adsota, Kantar`
- KHÔNG bịa tên báo cáo: SAI = "Vietnam Beauty Insights 2024" — không tồn tại

**2. KHÔNG CHẮC SỐ LIỆU → dùng RANGE hoặc QUALIFIER:**
- SAI: "TAM ngành F&B = 60 nghìn tỷ VND/năm"
- ĐÚNG: "TAM ước tính ~50-80 nghìn tỷ VND/năm (industry estimate)"

**3. CLAIM VỀ BRAND CỤ THỂ — chỉ nói CHUNG, không số:**
- SAI: "Cocoon có 50,000 active customers"
- ĐÚNG: "Cocoon là local clean beauty brand đã build được presence rõ rệt"

**4. ƯU TIÊN THỨ TỰ:**
- Best: Data thật + cite nguồn từ list known
- OK: Range + qualifier
- Worst: Số chính xác không nguồn → CẤM TUYỆT ĐỐI

**5. DOCUMENT-GROUNDED principle (áp dụng khi user paste data thật):**
- Nếu user paste data trong intake (vd: doanh thu hiện tại, tệp khách, đối thủ cụ thể) → ƯU TIÊN bám vào data đó
- KHÔNG tự gen claim ngoài scope user cung cấp
- Nếu user nói "chưa biết" / "chưa launch" → respect, KHÔNG infer giả định không có cơ sở
- Nếu data user cung cấp mâu thuẫn với common knowledge → vẫn dùng data user (note 1 lần là "data sếp cung cấp khác với benchmark ngành"), KHÔNG override"""


_SHARED_LANGUAGE_RULES = """**NGÔN NGỮ (BẮT BUỘC):**

1. **Ưu tiên tiếng Việt tự nhiên** — viết như tư vấn cho founder VN, không dịch word-by-word

2. **Thuật ngữ marketing tiếng Anh BẮT BUỘC kèm giải thích tiếng Việt trong ngoặc lần đầu xuất hiện:**
   - "TAM (Total Addressable Market — tổng quy mô thị trường tối đa)"
   - "CAC (Customer Acquisition Cost — chi phí thu hút 1 khách hàng)"
   - "ROAS (Return On Ad Spend — tỷ lệ doanh thu trên chi phí ads)"
   - "AOV (Average Order Value — giá trị đơn hàng trung bình)"
   - "CPMess (Cost per Message — chi phí cho 1 inbox)"
   - "CPL (Cost per Lead — chi phí cho 1 lead)"
   - "VTR (View-Through Rate — tỷ lệ xem hết video)"
   - "CTR (Click-Through Rate — tỷ lệ click)"
   - "ICP (Ideal Customer Profile — chân dung khách hàng lý tưởng)"
   - "JTBD (Jobs-to-be-Done — nhiệm vụ khách hàng cần hoàn thành)"
   - "MoM (Month-over-Month — tăng trưởng so với tháng trước)"
   - "YoY (Year-over-Year — tăng trưởng so với năm trước)"
   - "TOFU/MOFU/BOFU (Top/Middle/Bottom of Funnel — đầu/giữa/cuối phễu)"
   - "UGC/EGC/FGC (User/Employee/Founder-Generated Content)"
   - Sau khi đã giải thích lần đầu → có thể dùng viết tắt tự do
   - CHỈ giải thích INLINE trong ngoặc ngay lần đầu. TUYỆT ĐỐI KHÔNG gom thành 1 section "Ghi chú thuật ngữ" / glossary riêng ở cuối — đó là dư thừa.

3. **SMART Goals — viết FULL ngay từ đầu:**
   - "**S (Specific — Cụ thể):** ..."
   - "**M (Measurable — Đo lường được):** ..."
   - "**A (Achievable — Khả thi):** ..."
   - "**R (Relevant — Liên quan đến mục tiêu):** ..."
   - "**T (Time-bound — Có thời hạn):** ..."

4. **SAVE Framework — tương tự:**
   - "**S (Solution — Giải pháp cho vấn đề):** ..."
   - "**A (Access — Cách khách hàng tiếp cận):** ..."
   - "**V (Value — Tổng giá trị nhận được):** ..."
   - "**E (Education — Giáo dục khách hàng):** ..."

5. **TRÁNH dịch literal** — dùng từ tự nhiên cho ngữ cảnh VN."""


_SHARED_MARKDOWN_RULES = """**Quy tắc viết markdown (BẮT BUỘC):**

1. **Dùng markdown tables** cho mọi data so sánh
2. **Bold** cho mọi con số/KPI/%: "Tăng từ **80tr** lên **200tr/tháng** (**40% MoM**)"
3. **Blockquote (>)** cho key takeaway
4. **Sub-headings `### Tên section`** cho các nhóm lớn
5. **Bullet lists với emoji prefix** cho action items: 🟢 Quick wins / 🟡 Medium term / 🔴 Risks

LƯU Ý:
- KHÔNG dùng triple backticks trong output — Telegram render xấu
- Bold tên brand/product khi mention lần đầu trong section"""


# ─────────────────────────────────────────────────────────────────
# Format 1: Strategic 4-section (Insight / Tóm tắt / Benchmarks / Detail)
# ─────────────────────────────────────────────────────────────────

STRATEGIC_4_SECTION_FORMAT = f"""

---

**OUTPUT FORMAT (BẮT BUỘC) — 4 sections, TUYỆT ĐỐI ĐỦ cả 4:**

## 💡 Insight quan trọng nhất
[1-2 câu cốt lõi, đặt trong dấu ngoặc kép — điều quan trọng nhất user cần nhớ.]

## 🎯 Tóm tắt
- bullet 1 (key finding ngắn, max 15 từ)
- bullet 2
- bullet 3
- bullet 4
- bullet 5 (tối đa 5 bullets)

## 📊 Benchmarks
[2-4 dòng KPI/số liệu/threshold cụ thể. Bỏ qua section này CHỈ nếu thực sự không có data số.]

## 📄 Phân tích chi tiết
[BẮT BUỘC PHẢI CÓ. Đây là CORE OUTPUT — full analysis dài 500-1500 từ với sub-headings (### ...), bảng, lý luận sâu. KHÔNG được bỏ qua hay viết qua loa.

VD cấu trúc:
### 1. [Tên sub-section đầu]
[Phân tích...]

### 2. [Tên sub-section 2]
[Phân tích...]

### 3. [Strategic implication]
[3-5 takeaway actionable cho founder]]

⚠️ **QUY TẮC NGHIÊM CẤM:**
- KHÔNG được bỏ section "📄 Phân tích chi tiết" — đây là phần value nhất
- KHÔNG được đổi emoji 📄 sang 📋/📑 — parser cần đúng emoji
- KHÔNG được rút gọn "Phân tích chi tiết" thành 1-2 đoạn — phải đủ chi tiết để user đọc 3-5 phút

---

{_SHARED_DATA_DISCIPLINE}

---

{_SHARED_LANGUAGE_RULES}

---

{_SHARED_MARKDOWN_RULES}
"""


# ─────────────────────────────────────────────────────────────────
# Format 2: Operational Deliverable (file-style output)
# ─────────────────────────────────────────────────────────────────

OPERATIONAL_DELIVERABLE_FORMAT = f"""

---

**OUTPUT FORMAT (BẮT BUỘC) — Theo cấu trúc 2 phần:**

## 🎯 Tóm tắt nhanh
[3-5 bullets — key highlights của deliverable này, dùng để hiển thị trên Telegram preview]
- Bullet 1: ...
- Bullet 2: ...
- Bullet 3: ...

## 📄 Deliverable hoàn chỉnh
[FULL content — theo template cụ thể của skill. Dùng markdown đầy đủ.

Cấu trúc thường có:
- Body content theo template skill (vào thẳng nội dung — KHÔNG mở đầu bằng block "Frontmatter"/metadata date/channel/target/offer rời rạc)
- Lưu ý vận hành / A/B test / KPI tracking ở cuối nếu có

TUYỆT ĐỐI KHÔNG thêm:
- Block "Frontmatter" hay bảng metadata kỹ thuật ở đầu (date/channel/target/offer liệt kê rời) — nếu cần nêu, lồng tự nhiên vào câu mở đầu.
- Section "Ghi chú thuật ngữ" / glossary liệt kê định nghĩa viết tắt ở cuối — thuật ngữ đã được giải thích trong ngoặc ngay lần đầu xuất hiện rồi.
]

---

{_SHARED_DATA_DISCIPLINE}

---

{_SHARED_LANGUAGE_RULES}

---

{_SHARED_MARKDOWN_RULES}

LƯU Ý: Phần "Deliverable hoàn chỉnh" là sản phẩm chính user nhận về — phải đủ chi tiết để dùng ngay,
không cần chỉnh sửa nhiều. Người nhận (designer, dev, creator, sales team) phải hiểu và làm được liền.
"""


# ─────────────────────────────────────────────────────────────────
# Format 3: Operational Analysis (audit-style — verdict + KPI table + actions)
# ─────────────────────────────────────────────────────────────────

OPERATIONAL_ANALYSIS_FORMAT = f"""

---

**OUTPUT FORMAT (BẮT BUỘC) — Theo cấu trúc audit-style 5 sections:**

## 📊 Tóm tắt nhanh
[Verdict cốt lõi 2-3 câu — what's the overall state? Dùng emoji indicator: 🟢 (đang tốt) / 🟡 (cần theo dõi) / 🔴 (cần xử lý ngay)]

> **[Tóm tắt verdict trong blockquote]**
>
> 🟢 **Đang tốt:** [list ngắn]
> 🔴 **Cần xử lý ngay:** [list ngắn]

## 📈 Kết quả vs KPI
[Bảng so sánh KPI vs Reality — bắt buộc table format, có % đạt và status icon]

| Chỉ số | KPI | Thực tế | % Đạt | Đánh giá |
|---|---|---|---|---|
| ... | ... | ... | ... | 🟢/🟡/🔴 |

## 🔬 Phân tích nguyên nhân
[Tối đa 3 nguyên nhân lớn — mỗi cái có:
- Triệu chứng quan sát được
- Nguyên nhân gốc
- Giải pháp cụ thể]

## 🎯 Next Actions
[3 timeframe — bảng action với owner + deadline:]

### ⚡ Xử lý ngay trong 48h
| Hành động | Kỳ vọng kết quả | Owner | Deadline |
|---|---|---|---|

### 📅 Xử lý trong tuần này
| ... |

### 🎯 Điều chỉnh chiến lược tuần/tháng tới
[Bullets actionable]

## 📉 Dự báo
[2 scenarios: nếu fix theo đề xuất vs nếu không fix gì — bảng so sánh nhanh]

---

{_SHARED_DATA_DISCIPLINE}

---

{_SHARED_LANGUAGE_RULES}

---

{_SHARED_MARKDOWN_RULES}
"""


# ─────────────────────────────────────────────────────────────────
# Lookup function
# ─────────────────────────────────────────────────────────────────

from agents.skills import OutputFormat


def get_format_instruction(output_format: OutputFormat) -> str:
    """Return the format instruction to append to agent system prompt."""
    if output_format == OutputFormat.STRATEGIC_4_SECTION:
        return STRATEGIC_4_SECTION_FORMAT
    elif output_format == OutputFormat.OPERATIONAL_DELIVERABLE:
        return OPERATIONAL_DELIVERABLE_FORMAT
    elif output_format == OutputFormat.OPERATIONAL_ANALYSIS:
        return OPERATIONAL_ANALYSIS_FORMAT
    else:
        # Default to strategic
        return STRATEGIC_4_SECTION_FORMAT
