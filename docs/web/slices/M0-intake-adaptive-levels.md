# SPEC — Intake web đa-level: gợi ý động + bỏ qua → AI suy (D-032)

> Spec-driven. Giai đoạn: **Specify → chờ Founder duyệt build**.
> Truy ngược: PRODUCT.md §4 (M0 lõi). Mở rộng **D-028** (intake AI-adaptive web).
> Quyết định nền: **D-032** (gợi ý động + skip→AI + 3 nhãn nguồn gốc + lõi nhỏ),
> D-029/D-030 (M0 định hướng, không SMART số), D-001 (web-only — không đụng bot).

## 0. Phạm vi & cấu trúc (đọc trước)
Codebase = **3 phần**: web (`web/`+`webapp/`) · telegram (`bot/` — sắp xóa, chỉ mẫu) ·
**engine chung** (`agents/`/`frameworks/`/`tools/`/`storage/` = bộ não web dùng qua
`webapp/business.py → agents.pipeline/agents.discovery`). Spec này **chỉ đụng web +
engine web dùng**, **KHÔNG đụng `bot/`**.

## 1. Vì sao có spec này
Bộ câu hỏi "mạnh" (JTBD, lựa-chọn-thay-thế, objection, khác biệt) cho output T1-T3 sắc,
NHƯNG ở "độ cao CMO" — business owner / nhân sự cấp dưới khó trả lời. Hai cực đều sai:
- Hỏi câu CMO trống → owner bí → bỏ trống / "chưa rõ" → mất tín hiệu.
- Để AI suy hết → bịa + generic (bug "Zara", archetype lệch).

Đường đúng (D-032): **giữ câu mạnh nhưng hạ xuống "quan sát hàng ngày" + gợi ý động theo
business + cho bỏ qua → AI suy có gắn nhãn.** Một luồng tự thích nghi theo level.

## 2. Bộ câu hỏi (độ cao "quan sát", web)
Khối nền **bắt buộc** (founder-unique, dễ trả lời — là lõi chống "skip tất"):
- B1 **Bán sản phẩm/dịch vụ gì, giải quyết vấn đề gì?**
- B2 **Ngành + địa bàn?**
- B3 **Khách hàng mục tiêu là ai?**
- B4 **Giá bán / giá trị đơn hàng (AOV) tầm bao nhiêu?** *(chọn khoảng)*
- B5 **Thách thức lớn nhất hiện tại?**

Khối chiến lược **skippable** (có gợi ý động + nút "để Max đoán"):
- S1 **Khách thường tìm đến bạn lúc/dịp nào? Mua để làm gì?** → JTBD (Customer Insight, USP)
- S2 **Khách hay so sánh bạn với ai / trước đây mua ở đâu?** → competitive alternative (Competitor, USP)
- S3 **Khách hay khen gì nhất? Vì sao họ quay lại?** → khác biệt + proof (USP, SWOT-S)
- S4 **Khách hay lo/hỏi gì, hay từ chối vì lý do gì?** → objection (Pain-Gain, Pricing)
- S5 **Đối thủ bạn để ý (tên cụ thể nếu có)?** → neo grounded research (Competitor)

Khối bối cảnh **optional** (chọn khoảng / chip):
- C1 Doanh thu/tháng *(khoảng + "không tiện chia sẻ")* → Market SOM, suy stage
- C2 Ngân sách marketing/tháng *(khoảng)* → tính khả thi
- C3 Ai đang làm marketing *(tự làm / 1 người / team / thuê ngoài)* → đề xuất khả thi
- C4 90 ngày ưu tiên gì *(chọn hướng, không ép số — D-029)* → Synthesis định hướng

> Mỗi output T1-T3 đều có ≥1 câu nuôi (mapping ở §3 spec gốc trao đổi). AI grounded lo
> phần môi trường ngoài (size thị trường, landscape, benchmark) — KHÔNG hỏi user.

## 3. Features & Acceptance Criteria

### A. Gợi ý động grounded (sinh theo business)
- **A1 — Sinh chip gợi ý 1 lần sau khối nền.** Sau khi có B1-B3 (sản phẩm/ngành/khách),
  gọi LLM **1 batch** (web endpoint) sinh 3-5 chip gợi ý cho từng câu S1-S4, bám đúng
  ngách. Dùng grounding nếu có (GEMINI) để chip *thật theo ngành*, không generic.
  - **AC:** Tới câu S1-S4, UI hiện chip gợi ý liên quan ngành user nhập (vd đồ plus-size →
    objection "sợ size không vừa / vải nóng"); không phải chip cứng chung cho mọi ngành.
- **A2 — Gợi-không-gò (chống anchoring).** Mỗi câu S: luôn có ô tự ghi + nút "Khác" +
  **cho chọn nhiều**; chip ghi rõ "*phổ biến trong ngành — chọn nếu đúng với bạn*".
  - **AC:** User gõ tự do được dù có chip; chọn nhiều chip được; không bị ép chỉ-1-chip.
- **A3 — Backend luôn có (Railway) → gợi ý LUÔN grounded.** GitHub Pages tĩnh đã bỏ
  (D-033) nên KHÔNG cần maintain chip ví dụ tĩnh. Nếu mở không backend (local dev) chỉ
  cần **không vỡ** (câu S vẫn hiện + skip được, không chip) — không cần chip fallback.
  - **AC:** Trên Railway, câu S1-S4 có chip grounded theo ngành; chạy local không
    backend → câu S vẫn render + skip được, không lỗi fetch (không bắt buộc có chip).

### B. Quyền bỏ qua → AI suy
- **B1 — Nút "Mình chưa chắc → để Max đoán" trên mọi câu S (+ C).**
  - **AC:** Bấm skip → đi câu tiếp, không chặn; field lưu trạng thái `skipped`.
- **B2 — Lõi bắt buộc KHÔNG skip.** B1-B5 phải có giá trị mới hoàn tất (B4 cho "chưa rõ"
  hợp lệ nhưng phải chọn; B5 bắt buộc).
  - **AC:** Thiếu 1 trong B1-B3/B5 → không cho "Hoàn tất"; B4 cho "chưa rõ".

### C. 3 trạng thái nguồn gốc + nhãn giả định (chống bịa)
- **C1 — Lưu provenance mỗi field:** `typed` (user gõ) | `suggested` (chọn chip AI) |
  `inferred` (skip → AI suy). `typed` + `suggested` = **fact**; `inferred` = **giả định**.
  - **AC:** `webapp` lưu được nguồn gốc từng field; mở lại profile thấy đúng nguồn.
- **C2 — Output T1-T3 gắn nhãn field giả định.** Khi web gọi `run_targeted_pipeline`,
  **inject context note** liệt kê field nào là `inferred` → analyses gắn
  **"(giả định — cần kiểm chứng)"** cho phần dựa trên field đó. Tận dụng rule chống-bịa
  `(ước tính)` đã có trong prompt — KHÔNG cần sửa prompt engine.
  - **AC:** Chạy pipeline với ≥1 field skip → output có nhãn "(giả định)" ở phần liên quan;
    field `typed`/`suggested` KHÔNG bị gắn nhãn.
- **C3 — "Chọn chip AI" = fact, không gắn nhãn.** User chủ động gật ≠ AI đoán ngầm.
  - **AC:** Field `suggested` hiển thị/dùng như `typed`, không "(giả định)".

### D. Thanh minh bạch độ đầy đủ
- **D1 — Hiện tỉ lệ "Max đoán".** Cuối wizard + đầu trang strategy: "Bạn để Max đoán X/Y
  mục — phân tích mang tính giả định; điền thêm sẽ sắc hơn." (chỉ hiện khi có ≥1 inferred).
  - **AC:** Skip ≥1 câu S → thấy thông báo tỉ lệ; skip 0 → không hiện.

## 4. Commands (dev)
- Web: `python run_web.py` → localhost:8000 · Test: `python tests/test_web_api.py`
- Build static: `python webapp/build_standalone.py` · `node --check web/app.js`

## 5. Project structure (đụng tới — web + engine web)
- `web/app.js` — wizard: render chip gợi ý (A1/A2), nút skip (B1), thanh minh bạch (D1),
  gửi provenance khi lưu (C1).
- `webapp/api.py` — endpoint mới `/api/biz/intake/suggest` (sinh chip grounded, A1).
- `webapp/business.py` — lưu provenance vào profile (C1); build context note field
  `inferred` trước khi gọi `run_targeted_pipeline` (C2).
- `web/styles.css` — chip, trạng thái chọn, thanh minh bạch.
- `web/data.js` — bộ câu hỏi mới (không cần chip tĩnh fallback — A3/D-033).
- `agents/discovery.py` — *chỉ nếu cần* cho AI-adaptive path (engine web dùng); ưu tiên
  giữ logic ở web layer. "chưa rõ"/confidence đã có sẵn — tái dùng.
- `tests/test_web_api.py` — assert: endpoint suggest tồn tại; wizard có skip; provenance
  lưu đúng; context note liệt kê inferred fields.
- **KHÔNG đụng:** `bot/` (sắp xóa). Engine prompt T1-T3 (D-031) giữ nguyên — chỉ inject
  context, không sửa prompt.

## 6. Code style / ràng buộc
- Vanilla JS, không thêm lib. Degrade an toàn khi không backend (chip tĩnh + skip).
- Không nút/route chết (D-008). Tái dùng "chưa rõ"/confidence engine đã có.
- KHÔNG sửa prompt engine T1-T3 để gắn nhãn — làm qua context inject (web-side).

## 7. Testing strategy
- `tests/test_web_api.py`: (a) route `/api/biz/intake/suggest` khai báo; (b) wizard có
  nút skip + chỗ render chip; (c) business build context note chứa tên field inferred;
  (d) không backend → wizard vẫn render + skip được (không crash; không bắt buộc chip).
- Thủ công: chạy intake skip vài câu S → output T1-T3 có "(giả định)" đúng field; chọn chip
  → không nhãn; thanh minh bạch hiện đúng tỉ lệ.

## 8. Boundaries
- **ALWAYS:** web-only; lõi B1-B3/B5 bắt buộc; field `inferred` gắn nhãn ở output;
  `suggested`=fact; degrade an toàn.
- **ASK FIRST:** sửa prompt engine T1-T3 (mặc định KHÔNG — chỉ inject context); đổi
  `agents/discovery.py` quá mức (ưu tiên web layer).
- **NEVER:** đụng `bot/`; để field giả định hiển thị như fact (bịa ngầm); chặn user khi
  skip câu chiến lược; ép số ở câu mục tiêu (giữ D-029).

## 9. Ngoài phạm vi (lần này)
- Bot intake (sắp xóa). M1 Occasion (SMART số thật). Pattern "AI nháp đầy đủ → user sửa
  từng dòng" (nâng cấp sau — lần này dừng ở gợi-ý-chip + skip).

## 10. Thứ tự sau khi duyệt
1. Câu hỏi + skip + provenance (web layer).
2. Endpoint suggest grounded (A1) + context note inferred (C2).
3. Thanh minh bạch (D1) + test + nghiệm thu trên Railway.

> Bỏ bước "build static bundle / parity demo tĩnh" (GitHub Pages đã bỏ — D-033).
