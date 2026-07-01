# SPEC — TOWS về đúng tầng + T5 Tactical đổi xương sống (D-031)

> Spec-driven. Giai đoạn: **Specify → chờ Founder duyệt build**.
> Truy ngược: PRODUCT.md §4 (M0 lõi). Tiếp nối **M0-directional-reframe** (D-029/D-030).
> Quyết định nền: **D-031** (TOWS ở T3, T5 = Segment→Phễu, đường giữa cho số),
> D-029/D-030 (M0 = định hướng, SMART số dồn xuống M1 Occasion),
> D-001 (bot dùng chung — sửa-cho-đúng cả 2 surface như tinh thần D-030).

## 1. Vì sao có spec này
Báo cáo thật của H&Y Co. (2 file demo Founder gửi) phơi ra 2 vấn đề cấu trúc ở
tầng tactical, NGOÀI chuyện SMART số đã xử ở D-030:

1. **T5 Tactical Playbook đang ép SO/WO/WT làm xương sống cho TỪNG tệp khách** —
   mỗi segment → 3 khối SO/WO/WT, mỗi khối 2-3 "Hướng". Đây là **lỗi tầng**: TOWS
   là công cụ *suy ra chiến lược từ SWOT* (việc của T3→T4), không phải khung
   *thực thi*. Hệ quả: (a) trùng với ma trận TOWS đã có ở T3 SWOT; (b) thiếu hẳn
   ST (chỉ có SO/WO/WT); (c) ép horizon bịa (SO=ngắn, WO=trung, WT=dài); (d) kéo
   abstraction chiến lược ngược vào tầng đáng lẽ chỉ nói "copy gì, kênh nào".
2. **Archetype banner nhiễm fallback generic** — file demo ghi *"Impulse purchase /
   Gen Z / cạnh tranh Zara"* cho business đồ mặc nhà plus-size nữ 25-45 / mẹ bỉm.
   Sai segment → toàn bộ tactic lệch theo.

Founder **thích TOWS** → không bỏ, mà **trả về đúng nhà** (T3, đủ 4 ô) rồi để
T4/T5 *tham chiếu*. Spec này sửa **3 prompt cho nhất quán 3 tầng**.

## 2. Bằng chứng trong code
- **T3 đã có TOWS đủ 4 ô:** `agents/prompts.py` `SWOT_SYSTEM` dòng 1114-1124 —
  `### SO`, `### WO`, `### ST`, `### WT`. Nhà của TOWS đã đúng; chỉ cần tinh chỉnh
  (mỗi nước gắn rõ S×O / W×T cụ thể, bỏ map horizon nếu có).
- **T5 ép SO/WO/WT per-segment:** `agents/strategy_prompts.py`
  `TACTICAL_PLAYBOOK_SYSTEM` dòng 125-174 — template mỗi tệp = `## SO — TẤN CÔNG`
  / `## WO — PHÁT TRIỂN` / `## WT — PHÒNG THỦ`; NGUYÊN TẮC 5 "Bám SWOT — SO tận
  dụng đúng S×O...". Bảng tổng hợp (170-174) cũng theo SO/WO/WT + cột "Chi Phí
  ước tính".
- **Số tuyệt đối ở T5:** NGUYÊN TẮC 2 yêu cầu "tham số chiến dịch (budget test,
  frequency, format)" → model đẻ ra "8-12 triệu/tuần" (số đoán, đúng lỗi D-029).
- **T4 % phân bổ:** `STRATEGY_SYNTHESIZER_SYSTEM` section 6 (budget allocation) —
  giữ theo D-031 4b nhưng cần nhãn (định hướng) + diễn theo ưu tiên.

## 3. Features & Acceptance Criteria

### A. T3 — TOWS đủ 4 ô, đúng vai cầu nối (tinh chỉnh nhẹ)
- **A1 — Giữ 4 ô SO/ST/WO/WT, mỗi nước gắn rõ giao SWOT.** Mỗi gạch đầu dòng nêu
  rõ bắc cầu từ ô nào (vd "SO1 (S2 × O1): ..."). Bỏ mọi gán horizon cứng vào ô
  (không "SO = ngắn hạn"); horizon là thuộc tính của từng nước, không của cả ô.
  - **AC:** Output SWOT có đủ 4 ô; mỗi nước có ký hiệu giao (Sx×Oy...); không còn
    câu gán kiểu "SO luôn là ngắn hạn".
- **A2 — TOWS là `must_have` an toàn.** T3 SWOT đã `must_have=True` → dù T5 bị
  skip (pipeline đuối, `must_have=False`), user vẫn có đủ 4 nước chiến lược.
  - **AC:** Không di chuyển TOWS sang T5; xác nhận T3 vẫn sinh đủ 4 ô độc lập.

### B. T4 — Synthesis trích dẫn TOWS để chọn wedge (không lặp bảng)
- **B1 — Thêm 1 đoạn "chọn nước" dẫn lại TOWS.** Trong synthesis, chỗ chốt wedge
  nêu rõ: chọn nước nào (vd SO1) làm trục 90 ngày, nước nào hỗ trợ (WT2 dựng
  moat), vì sao — KHÔNG in lại bảng TOWS 4 ô (đã có ở T3).
  - **AC:** Synthesis có câu chọn/biện minh wedge tham chiếu ký hiệu TOWS; KHÔNG
    có bảng/heading lặp lại đủ 4 ô SO/ST/WO/WT.
- **B2 — % phân bổ ngân sách: đường giữa (D-031 4b).** Giữ % ở section 6 nhưng
  (a) gắn nhãn **(định hướng/ước tính)**, (b) diễn theo **thứ tự ưu tiên** ("kênh
  đặt cược chính → kế đến"), không trình bày như ngân sách đã chốt.
  - **AC:** Section 6 còn %, mỗi % có nhãn định hướng; có câu nói rõ số tiền thật
    chốt khi lập occasion (M1).
- **B3 — KHÔNG tái mở SMART số (giữ D-030).** Section 4/7 vẫn định hướng như B0
  của slice trước; spec này không nới lỏng.
  - **AC:** `git diff` section 4/7 không thêm lại SMART số cam kết.

### C. T5 — Đổi xương sống Segment → Phễu, TOWS chỉ còn tag
- **C1 — Thay template per-segment.** `TACTICAL_PLAYBOOK_SYSTEM` output mỗi tệp:
  ```
  # [TÊN TỆP] (archetype: <hiệu lực>)
  ## TOFU — Khơi/Bắt nhu cầu   (tag: phục vụ <SOx/WOx>)
     🎯 Hướng: hook, copy mẫu, kênh, khung thử
  ## MOFU — Nuôi & thuyết phục  (tag: ...)
     🎯 Hướng: nội dung, Fit Quiz..., kênh
  ## BOFU — Chốt                (tag: ...)
     🎯 Hướng: live/retarget, combo, CTA
  ```
  Tệp ƯU TIÊN (wedge của Synthesis) viết đủ 3 tầng phễu; tệp phụ gọn (1-2 mũi).
  - **AC:** Output T5 KHÔNG còn heading `## SO/WO/WT`; tổ chức theo Segment→Phễu;
    mỗi tệp bám archetype hiệu lực.
- **C2 — TOWS thành nhãn 1 dòng.** Mỗi mũi tactic mở đầu/đính 1 tag ngắn dẫn về
  nước TOWS nó phục vụ — KHÔNG làm bộ xương.
  - **AC:** Có tag dạng "(phục vụ SO1)"; bỏ tag vẫn đọc hiểu được (tag là phụ).
- **C3 — Test-param: đường giữa (D-031 4a).** Giữ *cấu trúc* thử + ngưỡng cut
  theo **chỉ số tương đối** (CTR/ROAS/CVR) + thời lượng test; **BỎ số tiền tuyệt
  đối** ("8-12 triệu/tuần" → "ngân sách thử nhỏ/đợt"). KPI mỗi mũi nêu *đo gì*,
  số target cụ thể để dành M1.
  - **AC:** T5 không còn số tiền VND tuyệt đối cho budget; vẫn còn cấu trúc test
    (giai đoạn thử, ngưỡng tương đối, KPI cần theo dõi).
- **C4 — Bảng tổng hợp đổi trục.** Bảng cuối T5 đổi từ SO/WO/WT → theo Segment ×
  Phễu (hoặc Segment × mũi nhọn), bỏ cột "Chi Phí ước tính" số tiền (thay bằng
  "mức đầu tư: Thấp/Trung/Cao" định tính nếu cần).
  - **AC:** Bảng tổng hợp không dùng SO/WO/WT làm hàng; không có cột số tiền.

### D. Fix bug archetype fallback
- **D1 — Banner archetype phải khớp business thật.** Truy nguồn vì sao H&Y (đồ
  nhà plus-size nữ 25-45) lại ra archetype "Impulse / Gen Z / Zara". Nếu do
  fallback generic khi thiếu tín hiệu → sửa để không gán nhãn segment/đối thủ
  bịa; nếu thiếu dữ liệu thì diễn đạt thận trọng, không phịa "Gen Z/Zara".
  - **AC:** Với input plus-size homewear nữ trung niên, banner KHÔNG ghi
    "Gen Z/Zara/Impulse" mặc định; archetype phản ánh đúng tín hiệu segment.

## 4. Commands (dev)
- Test web: `python tests/test_web_api.py`
- Build static: `python webapp/build_standalone.py`
- Chạy thật để nghiệm: 1 synthesis + 1 tactical playbook trên business mẫu
  plus-size, so output 3 tầng.

## 5. Project structure (đụng tới)
- `agents/prompts.py` — `SWOT_SYSTEM` (A1: TOWS 4 ô gắn giao, bỏ horizon cứng);
  `STRATEGY_SYNTHESIZER_SYSTEM` (B1 trích wedge, B2 nhãn % — KHÔNG đụng section 4/7).
- `agents/strategy_prompts.py` — `TACTICAL_PLAYBOOK_SYSTEM` (C1-C4: đổi template
  Segment→Phễu, tag TOWS, bỏ số tiền tuyệt đối, bảng tổng hợp).
- Nguồn archetype banner (truy: `agents/skills.py` / `agent_wrappers.py` / nơi
  build archetype block) — D1 fix fallback.
- `tests/` — assert T5 prompt không còn `## SO`/`## WO`/`## WT` làm heading; có
  TOFU/MOFU/BOFU; smoke pipeline không vỡ.
- **KHÔNG đụng:** `CMO_STRATEGY_SYSTEM` (JSON pre-fill tele), `discovery*.py`,
  logic multi-agent ngoài 3 prompt trên.

## 6. Code style / ràng buộc
- Chỉ sửa nội dung prompt (text) + chỗ build archetype — không đổi kiến trúc
  pipeline.
- Giữ D-029/D-030: M0 không SMART số cam kết.
- Bot dùng chung 3 prompt này → thay đổi áp cả bot. Đây là sửa-cho-đúng (tinh
  thần D-030), nhưng PHẢI smoke pipeline bot không vỡ trước khi chốt.

## 7. Testing strategy
- **Tĩnh:** grep prompt T5 — không còn heading SO/WO/WT; có TOFU/MOFU/BOFU + chỗ
  tag TOWS; không còn mẫu số tiền tuyệt đối trong template.
- **Pipeline smoke:** chạy `run_targeted_pipeline` (hoặc tương đương) trên 1
  business mẫu → T3 ra đủ 4 ô TOWS; T5 ra theo Segment→Phễu, không cụt tệp.
- **Bot không hỏng:** xác nhận `campaign_intake` pre-fill (đọc `CMO_STRATEGY_SYSTEM`)
  KHÔNG bị ảnh hưởng (đường khác).
- **Thủ công:** đọc 1 báo cáo HTML mới → SWOT có TOWS 4 ô; Synthesis chọn wedge
  dẫn TOWS, % có nhãn; Tactical theo phễu, tag TOWS, không số tiền cam kết;
  banner archetype khớp segment.

## 8. Boundaries
- **ALWAYS:** TOWS đủ 4 ô ở T3; T4 trích dẫn không lặp; T5 = Segment→Phễu + tag;
  giữ M0 không SMART số; smoke bot trước khi chốt.
- **ASK FIRST:** đổi kiến trúc pipeline/stage; đụng `CMO_STRATEGY_SYSTEM` hay
  multi-agent ngoài 3 prompt; đổi archetype taxonomy (chỉ fix fallback, không
  định nghĩa lại archetype).
- **NEVER:** để TOWS xuất hiện 2 nơi (T3 + T5); in số tiền cam kết ở T4/T5; gán
  segment/đối thủ bịa trong banner; tái mở SMART số ở section 4/7.

## 9. Ngoài phạm vi (lần này)
- M1 Occasion (nơi chốt SMART số thật) — spec riêng.
- Đổi visual HTML report (chỉ đổi nội dung prompt sinh ra, không đổi template
  render trừ khi banner archetype cần).
- Định nghĩa lại bộ archetype.

## 10. Thứ tự sau khi duyệt
1. C (T5 đổi xương sống) + B1 (T4 trích wedge) + A1 (T3 tinh chỉnh) — cùng đợt
   vì liên thông 3 tầng.
2. D1 (fix archetype fallback) — độc lập, có thể song song.
3. Smoke pipeline + bot → nghiệm thu trên 1 report thật.
