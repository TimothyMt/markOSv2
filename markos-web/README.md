# Marketing OS — AI CMO ("Max") cho founder Việt

Web app giúp chủ doanh nghiệp / SME Việt tự vận hành marketing như có một **CMO**:
**nghiên cứu thị trường → chiến lược → thông điệp → sản xuất nội dung → lịch phân phối & đo hiệu quả** — tất cả bằng tiếng Việt tự nhiên.

> **Trạng thái repo:** đây là repo của **web app** (phần chính). Một **Telegram bot đời đầu**
> (`bot/`) hiện vẫn nằm chung trong repo như phần *legacy* — sẽ được tách ra repo riêng.
> Web app **không cần** Telegram để chạy.

---

## Chạy web (không cần Telegram token)

```bash
pip install -r requirements.txt
cp .env.example .env          # điền ít nhất 1 khoá LLM (xem bên dưới)
python run_web.py             # → http://localhost:8000
```

- **Lưu trữ mặc định:** SQLite (`webapp/markos_web.db`) — chạy được ngay, không cần cấu hình.
- **Supabase (tuỳ chọn):** set `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` rồi chạy
  `webapp/supabase_schema.sql`. Có đủ 2 biến này thì web tự dùng Supabase thay SQLite.
- **Khoá LLM (cần ≥ 1):** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, hoặc `GEMINI_API_KEY`
  (`llm_router` tự chọn nhà cung cấp theo loại tác vụ). Xem `.env.example`.
- **Facebook Ads (tuỳ chọn):** các biến `FB_*` chỉ cần khi dùng phần quảng cáo/đo hiệu quả.

---

## Hệ thống 4 tầng (Content Marketing)

Max làm hộ founder **3 tầng hay bị bỏ** (Tâm lý · Chiến lược · Phân phối-đo), không chỉ "viết bài đẹp":

| Tầng | Làm gì | Trang |
|---|---|---|
| **① Nghiên cứu** | T1–T5: Thị trường · Đối thủ · Customer Insight · Tâm lý-Giá · SWOT (web-owned, grounded search) | Hồ sơ → Nghiên cứu |
| **② Chiến lược** | Đặt cược 5 nhóm → Synthesis + Tactical Playbook → 🏛️ **Thông điệp** (Messaging House: cốt lõi + trụ + giọng + trọng tâm) | Chiến lược · Thông điệp |
| **③ Sáng tạo** | 6 **dạng nội dung** (mỗi dạng mang vai trò phễu) · 🎛️ **Nhịp nền** (dạng × tần suất) | Lập chiến dịch |
| **④ Phân phối & Đo** | Lịch timeline: 🟢 nền MÓNG (liên tục) + 🔴 đợt SPIKE (đúng dịp); vòng đo-học | Lịch |

→ Chi tiết: [`docs/web/product-journey-4-tang.md`](docs/web/product-journey-4-tang.md).

Mọi bài (nền + đợt) **tự bám Thông điệp** (cốt lõi + giọng) để nhất quán; Nhịp nền rải đều lên Lịch để chạy như một hệ thống, không phải công cụ bấm-mới-làm.

---

## Kiến trúc

- **Backend:** [Starlette](https://www.starlette.io/) + `uvicorn` — `webapp/` (API + logic nghiệp vụ + SSE realtime).
- **Frontend:** SPA thuần JavaScript (không framework) — `web/` (`app.js` + `styles.css`).
- **LLM:** `tools/llm_router.py` định tuyến đa nhà cung cấp (Gemini Pro grounded · GPT-5 · Claude) theo loại tác vụ.
- **Lưu trữ:** Supabase (schema v2) hoặc SQLite; SSE (`webapp/events.py`) đẩy cập nhật realtime về FE.

---

## Cấu trúc thư mục

```
markOSv2/
├── run_web.py            # ⭐ Entry point web (python run_web.py)
├── config.py            # Cấu hình / biến môi trường
├── webapp/              # Backend web
│   ├── api.py           #   routes /api/biz/*
│   ├── business.py      #   logic nghiệp vụ (research, strategy, messaging, rhythm, calendar…)
│   ├── events.py        #   SSE realtime (watcher + Supabase Realtime)
│   ├── store*.py        #   lớp lưu trữ (SQLite / Supabase)
│   └── supabase_schema.sql
├── web/                 # Frontend SPA
│   ├── index.html · app.js · styles.css
│   └── dashboard-standalone.html   # bản build gộp 1 file
├── storage/             # Data layer (profiles, campaigns_v2, skill_runs…)
├── frameworks/          # industry_context · save_framework · kpi_library
├── tools/               # llm_router · token_tracker · fb_ads
├── agents/              # Thư viện PROMPT (prompts.py, operational_prompts.py) [+ orchestration legacy]
├── bot/                 # 🕰️ Telegram bot (LEGACY — sẽ tách repo riêng)
└── docs/                # Tài liệu (xem docs/web/)
```

---

## Tài liệu

- [`docs/web/PRODUCT.md`](docs/web/PRODUCT.md) — sản phẩm & định vị
- [`docs/web/ARCHITECTURE.md`](docs/web/ARCHITECTURE.md) — kiến trúc kỹ thuật
- [`docs/web/product-journey-4-tang.md`](docs/web/product-journey-4-tang.md) — hành trình 4 tầng
- [`docs/web/ROADMAP.md`](docs/web/ROADMAP.md) — lộ trình

---

## Legacy — Telegram bot

Bot Telegram đời đầu vẫn chạy được (sẽ tách sang repo riêng):

```bash
# cần TELEGRAM_BOT_TOKEN trong .env
python bot/main.py
```
