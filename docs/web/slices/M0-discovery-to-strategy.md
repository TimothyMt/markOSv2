# Slice M0 — Khám phá → Chẩn đoán → Chiến lược 90 ngày

> 1-pager để Founder DUYỆT trước khi code. (Way of Working §5)

## Outcome
Một chủ doanh nghiệp mới mở web, **trò chuyện với Max**, khai báo doanh nghiệp,
rồi nhận **một bản chiến lược 90 ngày dùng được** — tất cả chạy bằng dữ liệu thật,
mượt, không mock ở luồng chính.

## Người dùng & bối cảnh
Starter (chủ DN nhỏ tự làm MKT). Vào lần đầu, chưa có hồ sơ. Dùng trên desktop.

## Luồng vàng (các bước user đi qua)
1. Mở `#home` → Max chào, gợi ý ví dụ.
2. User kể về DN → Max phỏng vấn (discovery) đến khi đủ hồ sơ.
3. Hồ sơ đủ → Max nói "để em chạy chẩn đoán" + nút **Chạy phân tích**.
4. User bấm → pipeline chạy nền, **tiến trình hiện realtime** trong hội thoại.
5. Xong chẩn đoán → Max tự **tổng hợp chiến lược 90 ngày**.
6. Max gửi tóm tắt + nút **Xem chiến lược** → mở trang `#strategy` render **bản thật**
   (định vị, SAVE/SMART, roadmap 90 ngày, KPI) từ output AI, đẹp & đọc được.

## Trong phạm vi
- Hoàn thiện discovery qua chat (đã có `run_discovery_turn`) — mượt, không kẹt.
- Trigger pipeline chẩn đoán + synthesis thật, hiển thị tiến trình.
- Trang `#strategy` đọc **strategy thật** (bảng `strategies`/`skill_runs`) và render
  có cấu trúc (không phải đổ text thô).
- Trạng thái: loading, đang chạy, lỗi, rỗng (chưa có hồ sơ / chưa chạy).
- Smoke test cho luồng (script chạy thật với 1 user mẫu).

## NGOÀI phạm vi (không làm lần này)
- Sản xuất nội dung (M1), Ads (sau), auth/billing (M4).
- Multi-client agency. Sửa hồ sơ thủ công bằng form (Max thu thập là đủ).
- Xuất PDF (để M1).

## Definition of Done
- [ ] Luồng 6 bước chạy thật end-to-end với 1 user thật trên Supabase.
- [ ] Tiến trình pipeline hiển thị realtime, có xử lý timeout/lỗi từng bước.
- [ ] Trang `#strategy` render strategy thật có cấu trúc; có empty state khi chưa có.
- [ ] Không nút giả trên luồng; chi phí token tính vào quota user.
- [ ] Smoke test + Founder nghiệm thu.

## Rủi ro / đánh đổi
- **Thời gian chạy pipeline dài** (phút) → phải chạy nền + tiến trình rõ, không block UI.
- **Chi phí token** mỗi lần chạy → cảnh báo quota; cân nhắc cho chạy "nhanh" (ít agent) ở Starter.
- **Chất lượng render**: output AI là HTML/markdown đa dạng → parser phải chịu được biến thể.
- **Phụ thuộc key LLM** ở server (Railway). Dev không key → luồng này tắt, hiển thị mời cấu hình.

## Phụ thuộc
`agents/discovery.py`, `agents/pipeline.py` (run_multi_agent_targeted/run_targeted),
`agents/strategy.py` (run_advisor/persist), `storage/v2/strategies.py`,
`webapp/business.py` (run_agent), `webapp/chat.py`.

## Founder đã chốt (2026-06)
1. **Luôn chạy full** chất lượng cao (D-016).
2. Trang Chiến lược **tóm tắt gọn trước**, có nút "Xem đầy đủ" (D-016).

## Tiến độ build
- [x] Backend: `business._execute` chạy `run_targeted_pipeline` full (D-015) → ra synthesis.
- [x] Chat: nhãn gợi ý "Chạy chẩn đoán & lập chiến lược".
- [x] Trang Chiến lược: render synthesis thật, collapsible tóm-tắt-trước, empty state.
- [ ] Smoke test luồng thật với 1 user trên Supabase (cần env prod).
- [ ] Founder nghiệm thu trên Railway.
