# Marketing OS — Web Dashboard (Max, AI CMO)

Giao diện web đặt **Max (CMO ảo)** làm trung tâm. Người dùng đi theo **hành trình
4 tầng Content Marketing**, sidebar tổ chức theo tầng (bắt đầu từ **Hồ sơ doanh
nghiệp**, không phải khung chat):

**① Nghiên cứu** (Thị trường · Đối thủ · Customer · Tâm lý-Giá · SWOT) →
**② Chiến lược** (Đặt cược → Synthesis + Playbook → 🏛️ Thông điệp) →
**③ Sáng tạo** (6 dạng nội dung · 🎛️ Nhịp nền) →
**④ Phân phối & Đo** (Lịch: nền móng + đợt spike · vòng đo-học).

> Chi tiết hành trình: [`../docs/web/product-journey-4-tang.md`](../docs/web/product-journey-4-tang.md).

Mỗi trang phân tích có nút **⚡ Chạy bằng AI**; output thật render thẳng trong trang.
Cần server có ≥ 1 API key LLM (ANTHROPIC / OpenAI / Gemini). Trên bản demo tĩnh
(GitHub Pages) không có backend, các trang vẫn xem được bằng dữ liệu mẫu.

## Chạy với backend (đầy đủ — có lưu dữ liệu)

Không cần Telegram token hay credentials nào:

```bash
pip install starlette uvicorn        # nếu chưa có
python run_web.py                     # chạy ở repo root → http://localhost:8000
```

Mặc định dùng SQLite (`webapp/markos_web.db`, tự tạo lần đầu). Set `SUPABASE_URL`
+ `SUPABASE_SERVICE_KEY` (và chạy `webapp/supabase_schema.sql`) để dùng Supabase.

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
  api.py             # JSON API /api/biz/* (business thật) + /api/chat
  business.py        # logic nghiệp vụ (research, strategy, messaging, rhythm, calendar…)
  store*.py          # lớp lưu trữ (SQLite / Supabase)
  events.py          # SSE realtime
run_web.py           # server độc lập: static web/ + /api/* (port 8000)
```

## API (tóm tắt — business thật)

| Method | Path | Mô tả |
|--------|------|-------|
| GET    | `/api/biz?user_id=` | Toàn bộ dữ liệu thật của 1 user (profile, campaigns, skill_runs, messaging, rhythm…) |
| GET    | `/api/biz/skillrun/{id}` | Full nội dung 1 skill_run |
| POST   | `/api/biz/agent` | Chạy phân tích `{task, user_id}` — full/market/competitor/customer/pricing/swot/strategy |
| POST   | `/api/biz/messaging/gen` | Nháp Messaging House (stage=core → pillars) |
| POST   | `/api/biz/rhythm/save` | Lưu Nhịp nền (6 dạng × tần suất) |
| GET    | `/api/biz/calendar` | Lịch 2-track (nền + đợt) |
| POST   | `/api/chat` | Một lượt hội thoại tư vấn với Max `{user_id, message}` |

> Chọn user mặc định: query `?user_id=` → env `WEB_DEFAULT_USER_ID` → user active gần nhất.

## Tự cập nhật realtime (SSE)

Web mở 1 kết nối `EventSource('/api/stream')` và tự cập nhật khi dữ liệu đổi —
không cần F5. Chỉ báo **● Live** ở góc trên phải.

- **Watcher** (luôn chạy): server đọc store mỗi ~4s, đẩy khi đổi. Hoạt động với cả SQLite lẫn Supabase.
- **Supabase Realtime** (gần như tức thì): chạy phần cuối `supabase_schema.sql` để bật realtime. Nếu lỗi, watcher vẫn đảm bảo cập nhật.

## Kết nối Facebook Ads (per-user, tuỳ chọn)

Nút **🔗 Kết nối Facebook Ads** gọi `/api/biz/fb/connect-url` → OAuth → callback
`/oauth/fb/callback` lưu token (mã hoá Fernet) vào `user_fb_connections`. Số liệu
Ads pull định kỳ vào `ads_snapshots`; web đọc snapshot đó. Cần server cấu hình
`FB_APP_ID` + `FB_APP_SECRET` + redirect URI đã đăng ký.

---

> **Legacy — tích hợp Telegram:** repo còn phần điều khiển 2 chiều với bot Telegram
> (`bot/web_control.py`, các lệnh `/web_*`, notify về Telegram). Phần này thuộc
> **bot đời đầu** và sẽ được tách khỏi web khi chia repo — web **không cần** nó để chạy.
