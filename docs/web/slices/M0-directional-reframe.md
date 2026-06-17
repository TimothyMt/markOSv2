# SPEC — M0 sửa lại theo mô hình "định hướng" (D-029)

> Spec-driven. Giai đoạn: **Specify → chờ Founder duyệt**.
> Truy ngược: PRODUCT.md §4 (M0 lõi), §5 (trung thực, không nút giả).
> Quyết định nền: **D-029** (SMART/roadmap chi tiết đẩy xuống Campaign Occasion),
> D-026 (form-first, bỏ Max-chat trung tâm), D-028 (intake AI-adaptive),
> D-024 (output tương tác được), D-001/D-015 (bot giữ nguyên, web non-interactive).
> KHÔNG đổi prompt/skill Synthesis của bot. Chỉ sửa lớp **web**.

## 1. Vì sao có spec này
D-029 vừa đổi mô hình: **Synthesis (M0) = ĐỊNH HƯỚNG** (positioning, wedge,
pillars, % phân bổ ngân sách, 0-30/31-60/61-90 ưu tiên gì), còn **SMART số liệu +
deadline cụ thể chỉ chốt khi lập 1 Campaign Occasion (M1)**.

Nhưng M0 hiện tại đang nói ngược với chính nó (3 chỗ lệch — xem §2). Spec này sửa
**3 mặt của M0 cho nhất quán**: (A) Intake, (B) Output/trình bày Synthesis,
(C) UI/UX & các tàn dư cũ — TRƯỚC khi xây occasion creation ở M1 (vì M1 kế thừa).

## 2. Ba điểm lệch đã phát hiện (bằng chứng trong code)
- **L1 — Intake lệch trường:** `web/app.js INTAKE_STEPS` (static wizard) thu
  `business_name, industry, product_service, target_customer, location,
  monthly_marketing_budget, primary_goal, main_challenge`. Nhưng
  `agents/discovery.REQUIRED_FIELDS` = `product_service, target_customer,
  monthly_revenue, primary_goal, main_challenge, monthly_marketing_budget,
  current_channels`. → static wizard **thiếu** `monthly_revenue`,
  `current_channels`; câu mục tiêu ép số ("vd +50% đơn online") = ép SMART quá
  sớm (đúng lỗi D-029).
- **L2 — Tàn dư Max-chat:** `P.strategy` empty-state có nút
  `💬 Trò chuyện với Max` → `href="#home"`, mà `#home` redirect về `#dossier`
  (D-026). Nút **chết** → vi phạm D-008 (không UI giả).
- **L3 — Nhãn sai mô hình:** `ANALYSES` (dossier) ghi synthesis =
  `"SAVE + SMART + roadmap 90 ngày"`, và `P.strategy.sub` =
  `"... SAVE/SMART · Roadmap 90 ngày · KPI"` — trình bày như **chốt số**, trái D-029.

## 3. Features & Acceptance Criteria

### A. INTAKE — thu đúng trường, khung định hướng (không ép số)
- **A1 — Đồng bộ trường static wizard ↔ discovery.** Static wizard phải thu đủ
  trường `discovery.REQUIRED_FIELDS` (thêm `monthly_revenue`, `current_channels`).
  `business_name` giữ lại (web cần tên hiển thị) nhưng map vào field hợp lệ, không
  rớt khi lưu.
  - **AC:** Hoàn tất static wizard → `POST /api/biz/profile` lưu đủ 7 trường
    discovery + business_name; mở lại Hồ sơ thấy đủ, không trường nào rỗng do
    wizard không hỏi.
- **A1b — `monthly_revenue` = chọn khoảng, optional, có thể bỏ qua.** Đổi từ ô
  nhập số tự do → chọn 1 trong các khoảng: "Mới mở, chưa có doanh thu" /
  "Dưới 50 triệu" / "50–200 triệu" / "200 triệu–1 tỷ" / "Trên 1 tỷ" /
  **"Không tiện chia sẻ"**. Đánh dấu `optional: true` như `monthly_marketing_budget`.
  Khi user chọn "Không tiện chia sẻ" hoặc bỏ qua → lưu giá trị `"chưa rõ"` (khớp
  cách AI-adaptive mode đã xử lý sẵn trong `discovery_prompts.py`). KHÔNG thêm câu
  hỏi "giai đoạn DN" riêng — `stage` vẫn để AI tự suy từ doanh thu+ngành
  (`frameworks/kpi_library.py` đã có band theo ngành, hỏi thêm là trùng việc).
  - **AC:** Bước doanh thu hiện dạng chọn khoảng (không phải input số); có lựa
    chọn bỏ qua rõ ràng; chọn/bỏ qua xong vẫn hoàn tất wizard được; giá trị lưu
    là 1 trong các khoảng hoặc "chưa rõ", không bao giờ rỗng/undefined.
- **A2 — Câu hỏi mục tiêu = ĐỊNH HƯỚNG, không ép số (web static wizard).** Đổi
  `primary_goal` từ "vd +50% đơn online" → hỏi ưu tiên định hướng (gợi ý: tăng
  nhận diện / ra đơn / giữ chân khách / ra mắt sản phẩm). KHÔNG bắt nhập con số.
  - **AC:** Bước mục tiêu hiện lựa chọn/placeholder định hướng; không có chữ ép %;
    user bỏ trống số vẫn hoàn tất được.
- **A3 — KHÔNG đổi AI intake của bot.** `agents/discovery.py` /
  `discovery_prompts.py` / `run_discovery_turn` giữ nguyên (dùng chung bot — D-001).
  Chỉ điều chỉnh **static wizard (web-only)** + nhãn.
  - **AC:** `git diff` không chạm `agents/discovery*.py`.

### B. OUTPUT — trình bày Synthesis như "định hướng", có cầu nối xuống chiến dịch
- **B1 — Reframe trang `#strategy`.** Tiêu đề/sub + 1 banner ngắn nói rõ:
  "Đây là **ĐỊNH HƯỚNG** chiến lược 90 ngày. Con số cụ thể (SMART, ngân sách
  đợt, deadline) sẽ được **chốt khi bạn lập từng chiến dịch theo dịp**."
  - **AC:** Trang strategy có banner định hướng; không còn câu khẳng định "chốt
    SMART/KPI" ở sub.
- **B2 — Mọi con số trong roadmap/SMART của synthesis hiển thị có nhãn "(định
  hướng — chốt số khi lập chiến dịch)".** Không xoá số (bot vẫn sinh ra), chỉ
  đóng khung lại để không đọc nhầm là cam kết.
  - **AC:** Khi synthesis thật có `smart_goals` chứa số → UI kèm nhãn định hướng;
    không hiện như KPI đã cam kết.
- **B3 — Cầu nối "→ Lập chiến dịch theo dịp".** Thay CTA `→ Campaign Brief`
  (mock cũ) bằng CTA dẫn tới luồng tạo occasion (M1) — placeholder ở M0 (nút dẫn
  tới trang occasion, kể cả khi M1 chưa xong thì hiện empty "sắp ra mắt", KHÔNG
  để nút chết).
  - **AC:** CTA tồn tại, bấm vào không dẫn tới trang vỡ/chết; nếu M1 chưa build →
    trang đích hiện state "đang phát triển" rõ ràng (không phải mock giả là thật).
- **B4 — Đọc/sửa synthesis tái dùng doc reader.** Synthesis vẫn đọc & chỉnh qua
  hạ tầng `#doc`/`agentSection` đã có (output-reader-editor slice) — không dựng
  trình đọc riêng.
  - **AC:** Mở synthesis → đọc full, sửa tay/nhờ Max chỉnh hoạt động như các
    output khác.

### C. UI/UX — dọn tàn dư, nhãn nhất quán
- **C1 — Sửa nhãn dossier `ANALYSES`:** synthesis đổi mô tả từ
  "SAVE + SMART + roadmap 90 ngày" → "SAVE + định hướng 90 ngày" (hoặc tương
  đương, bỏ ngụ ý chốt số).
  - **AC:** Dòng synthesis trong khối Chẩn đoán không còn chữ "SMART ... roadmap"
    kiểu cam kết.
- **C2 — Gỡ nút chết Max-chat (L2).** Empty-state `P.strategy` thay
  "💬 Trò chuyện với Max → #home" bằng đường đi form-first đúng D-026:
  "Điền Hồ sơ doanh nghiệp → Chạy chẩn đoán" (link `#dossier` + nút
  `run-agent task=full`).
  - **AC:** Không còn link `#home`/Max-chat ở M0; mọi nút trong empty-state dẫn
    tới hành động thật.
- **C3 — Nhất quán thông điệp 2 tầng** ở những nơi user đọc chiến lược:
  Synthesis = la bàn (định hướng ổn định); Chiến dịch theo dịp = bản đồ (số cụ
  thể). Diễn đạt cho user hiểu, không thuật ngữ trần.
  - **AC:** Ít nhất trang strategy + cầu nối occasion truyền tải đúng 2 tầng này.

## 4. Commands (dev)
- Chạy: `python run_web.py` → http://localhost:8000
- Build static: `python webapp/build_standalone.py`
- Test: `python tests/test_web_api.py` (runner riêng) hoặc `pytest tests/test_web_api.py`
- Kiểm: `node --check web/app.js`

## 5. Project structure (đụng tới)
- `web/app.js` — `INTAKE_STEPS` (A1/A2), `P.strategy` render + empty-state
  (B1/B2/B3/C2), `ANALYSES` nhãn (C1), `handleIntake` map field (A1).
- `web/data.js` — nếu cần field/label mới cho wizard.
- `web/styles.css` — banner định hướng, nhãn "(định hướng)".
- `webapp/business.py` — `save_profile` nhận đủ trường mới (A1) nếu chưa.
- `tests/test_web_api.py` — thêm assert: route occasion-bridge tồn tại / không
  còn `#home` Max-chat ở build; static wizard fields khớp discovery.
- **KHÔNG đụng:** `agents/discovery*.py`, prompt/skill Synthesis (A3).

## 6. Code style / ràng buộc
- Vanilla JS, không thêm lib. Degrade an toàn khi chưa có Supabase (giữ chế độ
  xem trước).
- Không tạo nút/route chết — mọi CTA dẫn tới hành động thật hoặc empty-state
  trung thực (D-008).
- Tái dùng doc reader (`#doc`/`agentSection`), không dựng trùng.

## 7. Testing strategy
- `tests/test_web_api.py`: (a) static wizard fields ⊇ discovery.REQUIRED_FIELDS;
  (b) build_standalone không còn CTA Max-chat `#home` ở M0; (c) route/biz
  degrade an toàn không Supabase.
- Thủ công: chạy 1 synthesis thật → mở strategy → thấy banner định hướng + nhãn
  số + cầu nối occasion không vỡ.

## 8. Boundaries
- **ALWAYS:** giữ bot nguyên; số synthesis có nhãn định hướng; CTA không chết;
  degrade an toàn.
- **ASK FIRST:** đổi hành vi AI intake (bot dùng chung); thêm trang occasion mới
  (đó là M1 — spec riêng).
- **NEVER:** đổi prompt/skill Synthesis; trình bày số synthesis như cam kết KPI;
  để nút Max-chat chết.

## 9. Ngoài phạm vi (lần này)
- **Xây luồng tạo Campaign Occasion thật** (kế thừa `campaign_intake.py`,
  pre-fill SMART từ roadmap) — đó là **M1, spec riêng tiếp theo**. Ở M0 chỉ làm
  CẦU NỐI/empty-state đúng (B3), không build full occasion.
- Sản xuất nội dung, Ads, auth/billing.
- Đổi mô hình AI intake / multi-agent của bot.

## 10. Thứ tự sau khi duyệt
1. Build M0 reframe (spec này) → nghiệm thu trên Railway.
2. Spec M1 "Campaign Occasion creation" (tái dùng `campaign_intake.build_campaign_draft_from_strategy`) → build → SMART chốt số ở đây.
