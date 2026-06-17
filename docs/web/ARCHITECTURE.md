# Kiến trúc Web App (hiện trạng)

> Cập nhật khi đổi kiến trúc. Đây là bản đồ để code đúng, không đoán.

## Tổng quan

```
Trình duyệt (SPA, hash router)
  web/index.html · styles.css · data.js (mock fallback) · app.js
        │  fetch /api/*  +  EventSource /api/stream (SSE)
        ▼
Starlette (run_web.py ĐỘC LẬP  |  hoặc mount chung trong bot/main.py)
        │
  webapp/api.py        ← khai báo route + SSE
  webapp/store.py      ← facade: SQLite (dev) | Supabase (prod) cho bảng web_*
  webapp/business.py   ← đọc DỮ LIỆU THẬT của bot + trigger AI agent
  webapp/chat.py       ← lõi hội thoại Max trên web
  webapp/events.py     ← Hub SSE + watcher + Supabase Realtime
  webapp/notify.py     ← bắn thông báo Telegram (best-effort)
        │
        ├── Bảng web_* (state của dashboard: tracked, jobs, campaigns…)
        └── Tái dùng code bot:
              storage/ (session, v2/*, brand_voice, tracked_competitors, fb_connections)
              agents/  (discovery, pipeline, strategy, orchestrator)
              tools/llm_router.py (đa nhà cung cấp LLM)
        ▼
Supabase (CÙNG project với bot) + Anthropic/OpenAI/Gemini + Facebook Graph API
```

## Hai chế độ chạy
- **Dev**: không key → `store` dùng SQLite, `business/chat` trả `enabled:false`,
  frontend dùng mock trong `data.js`. Mở thẳng `web/index.html` cũng xem được UI.
- **Prod**: có `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (+ key LLM) → dữ liệu thật,
  Max hoạt động, SSE realtime.

## Ranh giới dữ liệu (quan trọng)
- **`web_*`**: state riêng của dashboard (mock-first, có thể seed). Quản lý bởi `store`.
- **Bảng thật của bot** (`users`, `user_business_profile`, `campaigns`,
  `tracked_competitors`, `skill_runs`, `user_brand_voice`, `ads_snapshots`,
  `user_fb_connections`): CHỈ đọc/ghi qua `business.py`, tái dùng hàm `storage/*`.
  Không tạo bảng trùng lặp.

## Hợp đồng API (tóm tắt)
- Trạng thái: `GET /api/bootstrap`, `GET /api/stream` (SSE), các mutation `web_*`.
- Dữ liệu thật: `GET /api/biz`, `/api/biz/ads`, `/api/biz/skillrun/{id}`,
  `POST /api/biz/agent`, `GET /api/biz/fb/connect-url`.
- Max: `POST /api/chat`, `GET /api/chat/history`.

## Realtime
`events.Hub` dedupe theo hash; `watcher` (poll ~4s, nhẹ) + `realtime_listener`
(Supabase postgres_changes). `agentJobs` (in-memory) nằm trong `full_state` nên
tiến độ agent đẩy live mà không nện DB.

## Frontend
- SPA 1 IIFE trong `app.js`; pages trong object `P`; router theo `location.hash`.
- `body.chat-mode` cho trang Max (ẩn rail, bố cục hội thoại).
- Build 1-file: `python webapp/build_standalone.py` → `web/dashboard-standalone.html`
  + `index.html` (GitHub Pages).

## Nợ kỹ thuật đã biết (cần trả)
- Chưa có **auth** → chưa được public với dữ liệu thật đa user (D-002).
- Nhiều trang vẫn render **biểu đồ/bảng mock** làm minh hoạ (chưa nối số thật).
- Chat transcript của Max **persist vào `web_chat`** (Supabase), bền qua restart;
  cache in-memory để nhanh. Cần chạy DDL `web_chat` trong `supabase_schema.sql`.
- Chưa có test tự động cho frontend; backend mới chỉ smoke test thủ công.
