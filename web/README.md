# Marketing OS — Web Dashboard

Giao diện web app (demo) cho nền tảng Marketing OS / Auto Ads Facebook.

## Chạy với backend (đầy đủ — có lưu dữ liệu)

Không cần Telegram token hay credentials nào:

```bash
pip install starlette uvicorn        # nếu chưa có
python run_web.py                     # chạy ở repo root
# mở http://localhost:8000
```

Backend dùng SQLite (`webapp/markos_web.db`, tự tạo lần đầu). Các thao tác sau
lưu thật và còn sau khi tải lại trang:

- Thêm / bỏ đối thủ theo dõi (trang *Phân tích đối thủ*)
- Bật / tắt tác vụ tự động (trang *Lịch trình & cảnh báo*)
- Áp dụng / bỏ qua đề xuất tối ưu (trang *Tối ưu tự động*)
- Đóng cảnh báo
- Lưu cài đặt thông báo (trang *Cài đặt*)

## Xem nhanh không cần backend

Mở thẳng `web/index.html` hoặc `web/dashboard-standalone.html` bằng trình duyệt.
Khi không có backend, giao diện tự dùng dữ liệu mock nhúng sẵn (`web/data.js`);
các nút thao tác sẽ báo cần chạy backend.

## Kiến trúc

```
web/                 # frontend (HTML/CSS/JS, SPA hash-router)
  index.html         # app shell
  styles.css
  data.js            # dữ liệu mock tĩnh + cấu hình navigation (fallback)
  app.js             # router + render các trang + gọi API
  dashboard-standalone.html  # bản gộp 1 file (cho GitHub Pages / mở offline)
webapp/              # backend
  store.py           # SQLite store (mock-first), seed + CRUD
  api.py             # JSON API: /api/bootstrap, /api/tracked, /api/jobs/... ...
run_web.py           # server độc lập: static web/ + /api/* (port 8000)
```

`bot/main.py` (server Telegram production) cũng mount sẵn `/api/*` và `/web`,
nên dashboard chạy chung cùng bot khi deploy.

## API (tóm tắt)

| Method | Path | Mô tả |
|--------|------|-------|
| GET    | `/api/bootstrap` | Lấy state động (tracked, jobs, optimizations, alerts, settings) |
| POST   | `/api/tracked` | Thêm đối thủ theo dõi `{name}` |
| DELETE | `/api/tracked/{id}` | Bỏ theo dõi |
| POST   | `/api/jobs/{name}/toggle` | Bật/tắt tác vụ nền |
| POST   | `/api/optimizations/{id}/apply` | Áp dụng / bỏ đề xuất |
| POST   | `/api/alerts/{id}/dismiss` | Đóng cảnh báo |
| POST   | `/api/settings` | Lưu cài đặt `{key, value}` |

> Dữ liệu hiện là **mock-first**. Khi nối nguồn thật (Supabase, Facebook
> Marketing API, AI agents), chỉ cần thay phần đọc/ghi trong `webapp/store.py` —
> hợp đồng JSON với frontend giữ nguyên.

## Điều khiển 2 chiều với Telegram

**Web → Telegram (thông báo):** đặt `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
→ các thao tác (tạo chiến dịch, áp dụng tối ưu, kết nối tài khoản) gửi thông
báo về Telegram. Thử ở trang *Cài đặt* → *Gửi thông báo test*.

**Telegram → Web (điều khiển từ điện thoại):** bot có các lệnh `/web_*` ghi vào
cùng store với web (`bot/web_control.py`):

| Lệnh | Tác dụng |
|------|----------|
| `/web_status` | Tổng quan: số chiến dịch, đối thủ, cảnh báo, tài khoản |
| `/web_campaign <tên>` | Tạo chiến dịch mới |
| `/web_track <tên>` | Thêm đối thủ theo dõi |
| `/web_optimize` | Áp dụng đề xuất tối ưu đầu tiên |
| `/web_alerts` | Xem cảnh báo hiện tại |
| `/web_help` | Danh sách lệnh |

> Để bot và web **thấy chung dữ liệu**, cả hai phải cùng cấu hình Supabase
> (`SUPABASE_URL` + `SUPABASE_SERVICE_KEY`). Nếu mỗi bên dùng SQLite riêng
> (2 service tách biệt) thì dữ liệu không chia sẻ.

## Tự cập nhật realtime (SSE)

Web mở 1 kết nối `EventSource('/api/stream')` và tự cập nhật khi dữ liệu đổi —
không cần F5. Chỉ báo **● Live** ở góc trên phải.

- **Watcher** (luôn chạy): server đọc store mỗi ~4s, đẩy khi đổi. Hoạt động với
  cả SQLite lẫn Supabase, kể cả thay đổi đến từ bot (process khác).
- **Supabase Realtime** (gần như tức thì): chạy phần cuối `supabase_schema.sql`
  để bật realtime cho bảng `web_*`. Khi có Supabase, server lắng nghe
  `postgres_changes` và đẩy ngay. Nếu realtime lỗi, watcher vẫn đảm bảo cập nhật.

> Realtime/SSE chỉ chạy khi có backend (`run_web.py`/cloud). Trên GitHub Pages
> tĩnh, web tự bỏ qua SSE và dùng dữ liệu mock.
