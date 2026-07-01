# CLAUDE.md — hướng dẫn cho AI coding agent

Repo này chứa **web app** "Marketing OS" (Max, AI CMO) — **phần đang phát triển chính** —
cùng một **Telegram bot đời đầu** (`bot/`, LEGACY) và thư mục staging `markos-web/`
(bản web đã tách, để cp ra repo riêng). Mọi nội dung hướng tới người dùng viết
**tiếng Việt tự nhiên** (không dịch máy).

## Chạy
```bash
python run_web.py          # ⭐ WEB (Max) → http://localhost:8000, KHÔNG cần Telegram
python bot/main.py         # LEGACY telebot (cần TELEGRAM_BOT_TOKEN)
```
Lưu trữ: SQLite (`webapp/markos_web.db`) mặc định; Supabase nếu set `SUPABASE_URL`+`SUPABASE_SERVICE_KEY`.
LLM: cần ≥1 khoá `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GEMINI_API_KEY`.

## ⚠️ BẪY QUAN TRỌNG NHẤT — mirror frontend
`web/app.js` và `web/dashboard-standalone.html` chứa **cùng một mã JS** (standalone là bản gộp 1 file).
**Mọi sửa ở `web/app.js` PHẢI mirror y hệt sang `<script>` trong `dashboard-standalone.html`**
(CSS: `web/styles.css` ↔ `<style>` trong standalone). Quên là 2 bản lệch nhau.

Kiểm sau khi sửa FE:
```bash
node --check web/app.js
python3 -c "import re;h=open('web/dashboard-standalone.html').read();open('/tmp/s.js','w').write(max(re.findall(r'<script[^>]*>(.*?)</script>',h,re.S),key=len))" && node --check /tmp/s.js
```
Kiểm backend: `python3 -c "import webapp.business, webapp.api"`.
(Import `agents.*` có thể fail trong sandbox do thiếu `anthropic` — bình thường; prod có đủ.)

## Kiến trúc web (thư mục chính)
- `webapp/` — backend Starlette: `api.py` (routes `/api/biz/*`), `business.py` (TOÀN BỘ logic; hàm async, import lazy), `events.py` (SSE), `store*.py` (SQLite/Supabase).
- `web/` — SPA thuần JS (hash-router trong `app.js`), không framework.
- `tools/llm_router.py` — định tuyến LLM đa nhà cung cấp theo `TaskType`.
- `agents/` — thư viện PROMPT + AI dùng chung (web tái dùng `agents.prompts`/`agents.operational_prompts` qua import lazy — **chủ ý giữ chất lượng, đừng thay bằng prompt tự chế mỏng**).
- `bot/` — Telegram bot LEGACY (web KHÔNG import; sẽ tách repo).

## Quy ước dữ liệu (KHÔNG đổi schema DB)
Dữ liệu ở `profile.intake_extra` (dict) + `campaigns_v2` + `skill_runs` (append-only, mới nhất thắng).
Cấu hình mới → thêm key vào `intake_extra`, KHÔNG thêm cột/bảng.
Key đã có: `bet_choices`, `messaging` (cốt lõi+trụ+giọng+focus), `content_rhythm`, `funnel_map`, `calendar_posts`.

## Thêm route/tính năng
1. `business.py`: hàm `async def` (lazy import). 2. `api.py`: handler + `Route(...)`.
3. `biz_data()`: expose key `bizXxx`. 4. `app.js`: render + handler trong `handleAction()` → **mirror standalone**. 5. Verify → commit.

## Không làm
- Không đổi schema DB. Không bịa số liệu trong output AI (prompt đã cấm).
- Không thêm phụ thuộc Telegram vào web.
