# CLAUDE.md — hướng dẫn cho AI coding agent

Marketing OS — **web app** ("Max", AI CMO) cho founder/SME Việt. KHÔNG phải Telegram bot.
Mọi nội dung hướng tới người dùng viết **tiếng Việt tự nhiên** (không dịch máy).

## Chạy & kiểm thử
```bash
pip install -r requirements.txt
python run_web.py            # → http://localhost:8000 (SQLite mặc định, KHÔNG cần Telegram)
```
- Lưu trữ: SQLite (`webapp/markos_web.db`) mặc định; Supabase nếu set `SUPABASE_URL`+`SUPABASE_SERVICE_KEY` (chạy `webapp/supabase_schema.sql`).
- LLM: cần ≥1 khoá `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GEMINI_API_KEY`.

## ⚠️ BẪY QUAN TRỌNG NHẤT — mirror frontend
`web/app.js` và `web/dashboard-standalone.html` chứa **cùng một mã JS** (standalone là bản gộp 1 file).
**Mọi sửa đổi ở `web/app.js` PHẢI mirror y hệt sang `<script>` trong `dashboard-standalone.html`** (và CSS: `web/styles.css` ↔ `<style>` trong standalone). Quên là 2 bản lệch nhau.

Kiểm sau khi sửa FE:
```bash
node --check web/app.js
# trích script lớn nhất trong standalone rồi check cú pháp:
python3 -c "import re;h=open('web/dashboard-standalone.html').read();open('/tmp/s.js','w').write(max(re.findall(r'<script[^>]*>(.*?)</script>',h,re.S),key=len))" && node --check /tmp/s.js
```
Kiểm backend: `python3 -c "import webapp.business, webapp.api"`.

## Kiến trúc
- **Backend** `webapp/`: Starlette + uvicorn.
  - `api.py` — routes `/api/biz/*` (đăng ký ở `api_routes()`).
  - `business.py` — TOÀN BỘ logic nghiệp vụ (research, strategy, messaging, rhythm, calendar, gen bài…). File lớn; hàm `async def`, import nội bộ **lazy** (trong hàm).
  - `events.py` — SSE realtime (watcher 4s + Supabase Realtime).
  - `store*.py` — lớp lưu trữ SQLite/Supabase.
- **Frontend** `web/`: SPA thuần JS (hash-router trong `app.js`), không framework.
- **LLM** `tools/llm_router.py` — định tuyến đa nhà cung cấp theo `TaskType` (Gemini grounded / GPT-5 / Claude).
- **`agents/`** = thư viện PROMPT + logic AI dùng chung (KHÔNG phải bot). `business.py` tái dùng prompt bot (`agents.prompts`, `agents.operational_prompts`) qua import lazy/try-except — **đây là chủ ý để giữ chất lượng**, đừng thay bằng prompt tự chế mỏng.

## Quy ước dữ liệu (KHÔNG đổi schema DB)
- Dữ liệu người dùng nằm ở `profile.intake_extra` (dict) + bảng `campaigns_v2` + `skill_runs` (append-only, bản mới nhất thắng).
- Cấu hình mới → thêm key vào `intake_extra`, KHÔNG thêm cột/bảng.
- Ví dụ đã có trong `intake_extra`: `bet_choices`, `messaging` (cốt lõi+trụ+giọng+focus), `content_rhythm` (6 dạng × tần suất), `funnel_map`, `calendar_posts`.

## Mô hình sản phẩm (4 tầng Content Marketing)
① Nghiên cứu (T1-T5) → ② Chiến lược (Đặt cược → Synthesis+Playbook → 🏛️ Thông điệp) →
③ Sáng tạo (6 dạng nội dung · 🎛️ Nhịp nền) → ④ Phân phối & Đo (Lịch: nền móng + đợt spike).
Chi tiết: `docs/web/product-journey-4-tang.md`. Mọi bài **tự bám Thông điệp** (cốt lõi+giọng) để nhất quán.

## Khi thêm route/tính năng
1. `business.py`: viết hàm `async def` (lazy import deps).
2. `api.py`: thêm handler + `Route(...)` trong `api_routes()`.
3. `business.py biz_data()`: expose dữ liệu ra key `bizXxx` cho FE.
4. FE `app.js`: render + handler trong `handleAction()`; **mirror sang standalone**.
5. Verify (mục trên) rồi commit.

## Không làm
- Không thêm phụ thuộc Telegram / không đụng `bot/` (đã tách khỏi repo này).
- Không đổi schema DB. Không bịa số liệu trong output AI (prompt đã cấm — giữ nguyên).
