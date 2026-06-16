# Deploy web dashboard lên Railway

`railway.json` đã cấu hình Railway chạy **web dashboard** (`python run_web.py`),
không phải bot Telegram. Server tự đọc biến `PORT` của Railway.

## Các bước

1. Vào https://railway.app → **New Project** → **Deploy from GitHub repo**
   → chọn repo `TimothyMt/markOSv2`.
2. Mở service → **Settings → Source** → chọn branch
   `claude/web-app-interface-haw8wu` (hoặc `main` sau khi merge).
3. Railway tự build (Nixpacks) và chạy `python run_web.py`.
4. **Settings → Networking → Generate Domain** → nhận URL công khai,
   ví dụ `https://markosv2-web.up.railway.app`. Mở là thấy dashboard,
   các nút thêm/xoá/lưu **hoạt động thật**.

## Lưu trữ dữ liệu

- **Mặc định (SQLite):** chạy được ngay, không cần cấu hình. Nhưng ổ đĩa
  Railway *ephemeral* — dữ liệu **mất khi redeploy/restart**. OK cho demo.
- **Bền vững (khuyến nghị):** dùng Supabase. Vào **Variables** thêm:
  ```
  SUPABASE_URL = https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY = <service_role key>
  ```
  (Chạy `webapp/supabase_schema.sql` trong Supabase trước.) Server sẽ log
  `store=supabase` và dữ liệu được lưu vĩnh viễn trên Supabase.
- Hoặc gắn **Railway Volume** mount vào `/app/webapp` để giữ file SQLite.

## Thông báo qua Telegram (Web → Telegram)

Để nhận thông báo trên Telegram khi có thao tác web (tạo chiến dịch, áp dụng
tối ưu, kết nối tài khoản…), thêm vào **Variables**:
```
TELEGRAM_BOT_TOKEN = <token bot của bạn>
TELEGRAM_CHAT_ID   = <user id / group id nhận thông báo>
```
Lấy `TELEGRAM_CHAT_ID`: nhắn cho bot rồi mở
`https://api.telegram.org/bot<token>/getUpdates` xem `chat.id`, hoặc dùng
@userinfobot. Sau đó vào trang **Cài đặt** trên web bấm **“Gửi thông báo test”**.

## Ghi chú

- Repo này vốn dùng để chạy bot Telegram (`Procfile` → `bot/main.py`).
  `railway.json` ghi đè start command thành web dashboard. Nếu muốn deploy
  bot thay vì web, đổi `startCommand` về `python bot/main.py` (cần đủ env:
  `TELEGRAM_BOT_TOKEN`, `WEBHOOK_URL`, `SUPABASE_*`, …).
- Web service **không cần** credentials nào để chạy ở chế độ SQLite.
