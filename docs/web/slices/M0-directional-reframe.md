# SPEC — M0 sửa lại theo mô hình "định hướng" (D-029 + D-030)

> Spec-driven. Giai đoạn: **Specify → chờ Founder duyệt**.
> Truy ngược: PRODUCT.md §4 (M0 lõi), §5 (trung thực, không nút giả).
> Quyết định nền: **D-029** (SMART/roadmap chi tiết đẩy xuống Campaign Occasion),
> **D-030** (Synthesis directional sửa TẠI GỐC prompt — cả bot+web),
> D-026 (form-first, bỏ Max-chat trung tâm), D-028 (intake AI-adaptive),
> D-024 (output tương tác được), D-001/D-015 (web non-interactive).
> **D-030 cập nhật cách làm:** trước định "không đổi prompt, chỉ gắn nhãn web" — nay
> sửa thẳng `STRATEGY_SYNTHESIZER_SYSTEM` (`agents/prompts.py:618`, dùng chung bot+web).
> KHÔNG hỏng pre-fill campaign bot (đó đọc JSON từ `CMO_STRATEGY_SYSTEM`, đường khác).
> Vẫn KHÔNG đổi: AI intake (`discovery*.py`), `CMO_STRATEGY_SYSTEM`, multi-agent bot.

## 1. Vì sao có spec này
D-029 vừa đổi mô hình: **Synthesis (M0) = ĐỊNH HƯỚNG** (positioning, wedge,
pillars, % phân bổ ngân sách, 0-30/31-60/61-90 ưu tiên gì), còn **SMART số liệu +
deadline cụ thể chỉ chốt khi lập 1 Campaign Occasion (M1)**.

Nhưng M0 hiện tại đang nói ngược với chính nó (3 chỗ lệch — xem §2). Gốc rễ: prompt
synthesis vẫn đẻ ra `## 4. SMART Goals` số cứng — nên gắn nhãn "(định hướng)" ở web
chỉ là chữa triệu chứng. **D-030 chốt sửa GỐC:** đổi chính prompt thành định hướng
(B0), web tự khắc đúng. Spec này sửa **3 mặt của M0 cho nhất quán**: (A) Intake,
(B) Output (sửa prompt + trình bày Synthesis), (C) UI/UX & tàn dư cũ — TRƯỚC khi
xây occasion creation ở M1 (vì M1 kế thừa).

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

### B. OUTPUT — Synthesis sinh ra "định hướng" (sửa gốc), có cầu nối xuống chiến dịch
- **B0 — Sửa prompt `STRATEGY_SYNTHESIZER_SYSTEM` thành định hướng (D-030).** Đây
  là sửa GỐC, không phải gắn nhãn. `agents/prompts.py:618`:
  - Section `## 4. SMART Goals` (*"con số cụ thể, timeline rõ ràng"*) →
    **`## 4. Mục tiêu định hướng theo giai đoạn`**: định tính, bám roadmap
    (0-30 nhận diện → 31-60 tương tác/lead → 61-90 chuyển đổi). KHÔNG số cam kết,
    KHÔNG deadline cứng. Nêu rõ "SMART số cụ thể chốt khi lập chiến dịch theo dịp".
  - Section `## 7. KPI Dashboard` *"Targets cho mỗi giai đoạn"* →
    **"KPI cần theo dõi"**: chỉ ra *đo cái gì* (primary metric mỗi giai đoạn) +
    red flags, KHÔNG chốt *con số target bao nhiêu*.
  - Section 5 Roadmap đã mềm sẵn ("khung gợi ý") — giữ, không cần đổi.
  - Áp dụng cho **cả bot + web** (prompt dùng chung). KHÔNG hỏng pre-fill campaign
    bot (đó đọc JSON từ `CMO_STRATEGY_SYSTEM`, đường khác — D-030).
  - **AC:** Chạy 1 synthesis thật (web hoặc bot) → output KHÔNG còn SMART số cứng/
    deadline ở section 4; section 7 nêu KPI cần theo dõi, không có dòng target số.
    `campaign_intake.build_campaign_draft_from_strategy` vẫn pre-fill được (test bot).
- **B1 — Reframe trang `#strategy`.** Tiêu đề/sub + 1 banner ngắn nói rõ:
  "Đây là **ĐỊNH HƯỚNG** chiến lược 90 ngày. Con số cụ thể (SMART, ngân sách
  đợt, deadline) sẽ được **chốt khi bạn lập từng chiến dịch theo dịp**."
  - **AC:** Trang strategy có banner định hướng; không còn câu khẳng định "chốt
    SMART/KPI" ở sub.
- **B2 — Lưới an toàn cho số sót.** Sau B0, section 4/7 không còn số cam kết. Nếu
  model vẫn lỡ sinh con số định hướng (vd % phân bổ ở section 6, benchmark) → UI
  gắn nhãn nhẹ "(định hướng)" để không đọc nhầm là cam kết. KHÔNG còn là cơ chế
  chính (B0 đã xử lý gốc), chỉ phòng hờ.
  - **AC:** Không con số nào trong synthesis hiển thị như KPI đã cam kết; số định
    hướng còn lại (nếu có) đều có ngữ cảnh/nhãn rõ.
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
- `agents/prompts.py` — **`STRATEGY_SYNTHESIZER_SYSTEM` section 4 + 7 (B0)** —
  sửa gốc thành định hướng. Dùng chung bot+web; đổi output cả 2 surface (đúng hướng).
- `web/app.js` — `INTAKE_STEPS` (A1/A2), `P.strategy` render + empty-state
  (B1/B2/B3/C2), `ANALYSES` nhãn (C1), `handleIntake` map field (A1).
- `web/data.js` — nếu cần field/label mới cho wizard.
- `web/styles.css` — banner định hướng, nhãn "(định hướng)" lưới an toàn (B2).
- `webapp/business.py` — `save_profile` nhận đủ trường mới (A1) nếu chưa.
- `tests/test_web_api.py` — thêm assert: route occasion-bridge tồn tại / không
  còn `#home` Max-chat ở build; static wizard fields khớp discovery.
- `tests/` (bot) — smoke `campaign_intake.build_campaign_draft_from_strategy` vẫn
  pre-fill OK sau B0 (chứng minh không hỏng cầu nối campaign bot).
- **KHÔNG đụng:** `agents/discovery*.py` (AI intake — A3), `CMO_STRATEGY_SYSTEM`
  (JSON strategy/pre-fill tele), multi-agent pipeline bot.

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
- **B0 (bot không hỏng):** smoke `campaign_intake.build_campaign_draft_from_strategy`
  với strategy JSON mẫu → vẫn pre-fill được (vì đọc `CMO_STRATEGY_SYSTEM`, không
  phải `STRATEGY_SYNTHESIZER_SYSTEM`).
- Thủ công: chạy 1 synthesis thật → output section 4 = định hướng (không SMART số),
  section 7 = KPI cần theo dõi (không target số); mở strategy → banner + cầu nối
  occasion không vỡ.

## 8. Boundaries
- **ALWAYS:** synthesis (cả bot+web) sinh ĐỊNH HƯỚNG, không SMART số cam kết ở M0;
  giữ nguyên flow/intake/pre-fill của bot; CTA không chết; degrade an toàn.
- **ASK FIRST:** đổi hành vi AI intake (bot dùng chung); thêm trang occasion mới
  (đó là M1 — spec riêng); đụng `CMO_STRATEGY_SYSTEM` hoặc multi-agent bot.
- **NEVER:** trình bày số synthesis như cam kết KPI; để nút Max-chat chết; sửa
  `discovery*.py`; làm hỏng `campaign_intake` pre-fill.

## 9. Ngoài phạm vi (lần này)
- **Xây luồng tạo Campaign Occasion thật** (kế thừa `campaign_intake.py`,
  pre-fill SMART từ roadmap) — đó là **M1, spec riêng tiếp theo**. Ở M0 chỉ làm
  CẦU NỐI/empty-state đúng (B3), không build full occasion.
- Sản xuất nội dung, Ads, auth/billing.
- Đổi mô hình AI intake / multi-agent của bot.

## 10. Thứ tự sau khi duyệt
1. Build M0 reframe (spec này) → nghiệm thu trên Railway.
2. Spec M1 "Campaign Occasion creation" (tái dùng `campaign_intake.build_campaign_draft_from_strategy`) → build → SMART chốt số ở đây.
