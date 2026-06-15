# 🚦 PRE-LAUNCH CHECKLIST — phải xử lý TRƯỚC khi mở cho khách thật trả tiền

> Ghi chú: các mục dưới đây KHÔNG cần làm khi còn solo-test, nhưng là **cổng bắt
> buộc** trước khi commercial / multi-tenant. Khi user nói "chuẩn bị mở / go-live /
> launch / bán" → nhắc lại checklist này.

## 🔒 Security gate (P0 — chặn thương mại hoá)

- [ ] **Bật Row-Level Security (RLS) trên Supabase.**
  - Hiện cô lập khách hàng CHỈ dựa vào mỗi query nhớ gắn `.eq(user_id)` + app dùng
    `service_role` key (bypass RLS). Quên 1 filter = khách A thấy chiến lược/doanh
    thu/đối thủ của khách B.
  - Việc cần: bật RLS + policy `user_id = auth.uid()` trên mọi bảng có dữ liệu
    user; chuyển app sang scoped key thay vì service_role nơi có thể.

- [ ] **Webhook secret token.**
  - `bot/main.py` set webhook KHÔNG có `secret_token`; handler không validate
    `X-Telegram-Bot-Api-Secret-Token`. Ai biết URL có thể giả request → mạo danh
    user, đốt token tiền.
  - Việc cần: set `secret_token` khi `set_webhook` + validate header mỗi request.

- [ ] **Cost hard-stop giữa job + token accounting atomic** (liên quan, nên làm cùng).
  - Quota hiện chỉ pre-check; user còn 1% vẫn chạy full A→Z không dừng. Token đếm
    bị race khi chạy song song.
  - Việc cần: atomic RPC tăng token + hard-stop khi vượt quota giữa pipeline.

---
_Nguồn: review flow 2026-06-15. Cập nhật khi xử lý xong từng mục._
