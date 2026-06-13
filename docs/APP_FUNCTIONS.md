# Marketing OS Bot — Tài Liệu Chức Năng Đầy Đủ

Trợ lý marketing AI cho founder Việt Nam, chạy trên Telegram. Từ phân tích chiến
lược → sản xuất nội dung → tối ưu ads, tất cả qua chat.

---

## Mục lục
1. [Kiến trúc tổng thể](#1-kiến-trúc-tổng-thể)
2. [Lệnh Telegram](#2-lệnh-telegram)
3. [Layer 1 — Intake](#3-layer-1--intake-thu-thập-thông-tin)
4. [Layer 2 — Strategic (7 skills + Full)](#4-layer-2--strategic-skills)
5. [Layer 3 — Operational (22 skills)](#5-layer-3--operational-skills)
6. [Layer 4 — Analysis (5 skills)](#6-layer-4--analysis-skills)
7. [Pipelines (orchestrators)](#7-pipelines--orchestrators)
8. [Ads Scheduler — báo cáo tự động](#8-ads-scheduler--báo-cáo-tự-động)
9. [Hệ thống nền](#9-hệ-thống-nền)

---

## 1. Kiến trúc tổng thể

```
Telegram (webhook) ─→ bot/handlers.py ─→ agents/pipeline.py ─→ LLM Router
                                                                │
                  ┌─────────────────────────────────────────────┤
                  ▼                                              ▼
         Strategic skills                              Operational skills
         (deep analysis)                               (deliverables)
                  │                                              │
                  └──────────────► session.results ◄────────────┘
                                        │
                  Output: Telegram card + HTML/Excel/Markdown file
```

**4 layer chức năng:**
| Layer | Vai trò | Output |
|---|---|---|
| 1. Intake | Thu thập profile business (8 trường) | BusinessProfile |
| 2. Strategic | Phân tích chiến lược chuyên sâu | Báo cáo 4-section |
| 3. Operational | Sản xuất deliverable cụ thể | HTML/Excel/MD |
| 4. Analysis | Đọc data → chẩn đoán + thực thi | Báo cáo + actions |

**Storage:** Supabase (Postgres). **LLM:** Multi-provider router (Claude Sonnet/Haiku
+ GPT-5 + Gemini fallback). **Deploy:** Railway (webhook + uvicorn).

---

## 2. Lệnh Telegram

### Lệnh người dùng
| Lệnh | Chức năng |
|---|---|
| `/start` | Khởi động bot, hiện menu chọn task |
| `/reset` | Xóa session, bắt đầu lại từ đầu |
| `/help` | Hướng dẫn sử dụng |
| `/settings` (`/setting`, `/config`) | Cài đặt: tên user, ngôn ngữ (mức tiếng Anh) |
| `/history` | Xem lại lịch sử campaign đã chạy (semantic search) |
| `/post` | Thao tác per-post (Sprint 7) |

### Lệnh Ads Scheduler
| Lệnh | Chức năng |
|---|---|
| `/connect_ads` | Kết nối FB Ad Account qua OAuth |
| `/ads_settings` | Chọn chỉ số theo dõi + ngưỡng alert + bật/tắt báo cáo |
| `/disconnect_ads` | Ngắt kết nối, xóa token |

### Lệnh Admin (chỉ ADMIN_IDS)
| Lệnh | Chức năng |
|---|---|
| `/addquota` | Cộng thêm quota cho user |
| `/setquota` | Đặt quota cố định |
| `/resetusage` | Reset usage |
| `/userinfo` | Xem thông tin + usage của user |

---

## 3. Layer 1 — Intake (Thu thập thông tin)

Hội thoại multi-turn thu thập **8 trường bắt buộc**:
`industry, product_service, target_customer, location, monthly_revenue,
current_channels, primary_goal, main_challenge`

- Dùng GPT-5 mini (rẻ) → Haiku fallback
- Tự extract JSON → `BusinessProfile`
- **Smart skip:** lần sau dùng skill khác, nếu profile đã đủ trường cần thiết → không hỏi lại
- Thêm trường USP (Sprint 2): `usp` + `usp_confidence` (clear/draft/missing)

---

## 4. Layer 2 — Strategic Skills

Phân tích chuyên sâu, output báo cáo 4-section (Insight / Tóm tắt / Benchmarks /
Phân tích chi tiết). Có Data Discipline (cite nguồn, dùng range, cấm bịa số).

| Skill | Lệnh menu | Chức năng |
|---|---|---|
| `market` | 📊 Tìm Hiểu Thị Trường | TAM/SAM/SOM + Market Dynamics |
| `competitor` | 🕵️ Phân Tích Đối Thủ | 8 chiều phân tích + Market Gap |
| `customer` | 👥 Insight Khách Hàng | ICP + Jobs-to-be-Done + Pain-Gain Map |
| `pricing` | 💰 Chiến Lược Giá | Pricing Model + Psychology Tactics |
| `strategy` | 🎯 Lập Kế Hoạch Tổng | SAVE Framework + SMART Goals + 90-day Roadmap |
| `retention_strategy` | 🔄 Giữ Chân Khách | Hệ thống retention 3 giai đoạn, phân tầng 4 nhóm khách |
| `winback_campaign` | 🔁 Winback Khách Cũ | Re-engage khách bỏ — sequence 3 bước + offer Tier |

### `full` — 🔍 Trọn Bộ A→Z
Chạy toàn bộ pipeline chiến lược tuần tự:
```
market → competitor → customer → pricing → USP → retention → winback → synthesis
```
USP có điều kiện (skip nếu user đã có USP rõ). Chạy qua **Multi-Agent Orchestrator**
(parallel theo tier) khi bật flag, hoặc sequential.

---

## 5. Layer 3 — Operational Skills

Sản xuất deliverable dùng được ngay. Intake qua single-shot form. Output HTML/Excel/MD.

### Bridge & Calendar
| Skill | Menu | Chức năng |
|---|---|---|
| `campaign_brief` | 📋 Viết Brief Campaign | Cầu nối Strategy→Tactical — Brief 10 sections |
| `content_calendar` | 📅 Lịch Nội Dung | Lịch content tháng — Pillar % động + Funnel + Source mix |

### Content Production (Deep)
| Skill | Menu | Chức năng |
|---|---|---|
| `content_generator` | ✍️ Sản Xuất Nội Dung | **Pipeline** 5 skill (xem §7) |
| `video_script_gen` | 🎬 Kịch Bản Video | Kịch bản video 5-beat (Hook/Pain/Solution/Proof/CTA) đầy đủ thoại — Excel |
| `ugc_brief` | 🤝 Brief Creator UGC | Creator brief (deal/deadline/don'ts) cho UGC/KOL/EGC — Excel |
| `ads_generator` | 📢 Sản Xuất Ads | Ads copy Meta+TikTok 3 tầng (TOFU/MOFU/BOFU) — Excel |
| `email_zalo_sequence` | 📧 Chăm Sóc Khách Hàng | Chuỗi nurture Email + Zalo OA — Excel |

### Content Suite v2 (single-purpose)
| Skill | Menu | Chức năng |
|---|---|---|
| `post_write` | ✍️ Viết 1 Bài Content | 1 row Calendar → Hook 3 variants + Body + CTA + Visual brief |
| `post_adapt` | 🔄 Adapt sang Channel | 1 bài gốc → FB/TikTok/Zalo/IG (4 format) |
| `post_voice_check` | ✅ Check Brand Voice | Check draft theo Brand Voice Rules + fix |
| `post_hooks` | 🪝 Hook Bank | 15 hooks chia 5 nhóm psychological + top 5 |
| `post_batch` | 📚 Batch Tuần | Gen 7-14 bài 1 tuần cùng lúc |
| `video_scripts` | 🎬 Kịch Bản Video | Video TikTok/Reels/Shorts 4 creator type variant |
| `content_repurpose` | ♻️ Tái Sử Dụng | 1 bài gốc → 5 phiên bản khác audience |

### Sales & Web
| Skill | Menu | Chức năng |
|---|---|---|
| `sales_inbox_script` | 💬 Kịch Bản Sales | Script chat cho team sales + objection handling |

### Brand & Insight
| Skill | Menu | Chức năng |
|---|---|---|
| `brand_positioning` | 🏛️ Messaging House | Refine T2 USP + T4 positioning → statement, tagline, value prop ladder, key messages (Linh — có revise loop) |
| `brand_voice` | 🎙️ Brand Voice Rules | Bộ quy tắc giọng văn cho team dùng nhất quán |
| `competitor_spy` | 🔍 Theo Dõi Đối Thủ | Phân tích FB Ads Library đối thủ — pattern + insight |
| `competitor_comparison` | 🆚 So Sánh 1-1 | So sánh trực diện 1 đối thủ cụ thể — Gemini grounded search + data session (Max) |

> **Lưu ý:** Tất cả content skills tự inject **Industry Brain** (14 ngành) + **Brand
> Voice** của user vào prompt lúc chạy — không cần config thủ công.

---

## 6. Layer 4 — Analysis Skills

Đọc data thật (FB API) → chẩn đoán → đề xuất / thực thi.

| Skill | Menu | Chức năng | Data source |
|---|---|---|---|
| `ads_analytics` | 📈 Analytics Tự Động | Phân tích portfolio: winners/losers, creative fatigue, budget | FB Marketing API |
| `ads_optimizer` | ⚡ Tối Ưu Ads Trực Tiếp | Đề xuất + **thực thi** pause/activate/budget trên FB | FB Marketing API (write) |
| `viral_video_analyzer` | 🎥 Phân Tích Video Viral | Reverse-engineer video viral → công thức + production brief | KrillinAI + Vision |
| `ads_intelligence` | 🔎 Ads Intelligence | **Pipeline** spy + analytics (xem §7) | FB Ads Library + Marketing API |

**Nền tảng phân tích ads:** Meta Andromeda framework
(`Expected Value = Bid × P(Action) × Quality Score`) + Frequency Radar 4 mức 🟢🟡🟠🔴
+ benchmark VN 2025-2026.

---

## 7. Pipelines / Orchestrators

Pipeline = chạy nhiều skill tuần tự, mỗi skill 1 file output. Phát hiện qua
`hasattr(skill, 'run_pipeline')`, trả `MULTI_OUTPUT:...` để handler dispatch.

### 7.1 `content_generator` — Full Content Suite
```
content_generator (sau content_calendar)
├─ post_batch          → 📅 bài viết hữu cơ
├─ video_script_gen    → 🎬 kịch bản video 5-beat
├─ ugc_brief           → 🤝 creator brief
├─ ads_generator       → ✍️ ad copy
└─ email_zalo_sequence → 📧 chuỗi email/zalo
```
Auto-fill intake ads/email từ profile + campaign (không stall chờ form).
→ 5 file Excel.

### 7.2 `ads_intelligence` — Ads Intelligence Toàn Diện
```
ads_intelligence
├─ competitor_spy  → spy đối thủ (FB Ads Library)
└─ ads_analytics   → phân tích account mình (FB Marketing API)
```
Handler prefetch cả 2 nguồn data trước (`_fb_data_spy` / `_fb_data_analytics`),
pipeline swap đúng data cho mỗi skill. Graceful degradation nếu 1 nguồn fail.
→ 2 HTML report.

### 7.3 `full` — Strategic Pipeline
Đã mô tả ở §4 (8 stages).

### Luồng chính (chuỗi tự động)
```
Intake → campaign_brief → [auto] content_calendar → [Tone Calibration]
                                                  → [user trigger] content_generator
```

---

## 8. Ads Scheduler — Báo cáo tự động

Báo cáo ads qua Telegram, không cần user hỏi. Mỗi user kết nối FB Ad Account riêng.
Xem chi tiết setup: `docs/ADS_SCHEDULER_SETUP.md`.

### Các job nền
| Job | Lịch | Nội dung |
|---|---|---|
| Daily Digest | 8:00 sáng | Tóm tắt so với hôm qua (health + metrics + alert + winner) |
| Weekly Report | Thứ Hai 8:00 | 7 ngày vừa rồi so với 7 ngày trước |
| Alert Monitor | Mỗi 4 tiếng | Push real-time khi Frequency/ROAS/CPM vượt ngưỡng (cooldown 24h) |
| Token Refresh | 2:00 sáng | Auto-refresh token gần hết hạn (60 ngày) |
| Cleanup | CN 3:00 | Xóa snapshot > 90 ngày |

### Chỉ số (12 metrics)
- **FB trả thẳng:** spend, impressions, reach, clicks, ctr, cpc, cpm, frequency, leads, purchases
- **Tự tính:** ROAS, CPL, CPA, VTR 3s, delta % so kỳ trước
- **Mặc định theo dõi:** Spend · ROAS · CPL · Frequency
- User chọn metric + đặt ngưỡng alert qua `/ads_settings` (bỏ trống = benchmark ngành)

### Bảo mật
- Token FB mã hóa Fernet (`ENCRYPTION_KEY`), không lưu plain text
- OAuth state token CSRF (TTL 15 phút, one-use)
- Token revoke → tự tắt notify + nhắn user reconnect (giữ settings cũ)

---

## 9. Hệ thống nền

### Multi-provider LLM Router
- Primary: Claude Sonnet 4.6 (deep) / Haiku 4.5 (intake)
- Fallback: GPT-5 / GPT-5 mini / Gemini
- Per-skill task type mapping → chọn provider tối ưu chi phí/chất lượng
- Token tracking per-skill (provider + latency + cost)

### Industry Brain (14 ngành)
`fnb, health_beauty, education, ecommerce, tech_saas, agency, real_estate, retail,
fashion_retail, health_clinic, pet_care, events_wedding, interior_design,
travel_hospitality`
→ 1 skill phục vụ nhiều ngành, inject runtime (hook/tone/CTA/giờ vàng/anti-pattern theo ngành).

### Brand Voice
- User build bộ quy tắc giọng văn (`brand_voice` skill) → lưu DB
- Tự inject vào mọi creative skill khi chạy

### Tone Calibration Loop
- Sau `content_calendar`, hỏi user feedback tone → tinh chỉnh trước khi gen content

### Campaign History + Semantic Search
- Tự lưu mỗi pipeline run (pgvector embeddings)
- `/history` semantic search campaign cũ

### Critic
- Một số analysis skill bật Critic review (2-pass) để tăng chất lượng

### Competitor Monitor
- Worker nền theo dõi FB Ads Library của đối thủ đã track → notify khi có ads mới

### Output formats
- **HTML** — báo cáo viewable (universal)
- **Excel** — content calendar / scripts / ads (theo template sheet)
- **Markdown** — landing page / sales script / creator brief

### Quota & Usage
- Per-user quota, admin quản lý qua command
- Token usage tracking + footer hiển thị API nào làm job

---

## 10. Chuyển sang repo mới — mang gì, bỏ gì

### Mang nguyên (core — app không chạy được nếu thiếu)
| Path | Vai trò |
|---|---|
| `bot/` | Telegram handlers, renderers, keyboards, main entrypoint |
| `agents/` | Pipelines, skills, prompts, task registry |
| `tools/` | LLM router, token tracker/billing, FB Marketing/Ads Library, v.v. |
| `frameworks/` | Industry brain (14 ngành), archetype resolver |
| `storage/` (trừ phần liệt kê ở dưới) | Models, session, v2 adapter + tables |
| `storage/migrations/001..011*.sql` | Toàn bộ — cần chạy hết trên Supabase mới để có schema v2 hiện tại |
| `workers/` | Ads scheduler / competitor monitor jobs |
| `services/` | (kiểm tra nội dung — hỗ trợ ads scheduler) |
| `config.py`, `run_local.py`, `Procfile`, `requirements.txt` | Entry/config |
| `content_generation_template.xlsx` | Template Excel cho content_generator |
| `.env.example` | Danh sách env vars cần set ở repo mới (Telegram/Anthropic/OpenAI/Gemini/Supabase/FB/Encryption) |
| `docs/` | Tài liệu — đặc biệt file này + `BACKLOG.md`, `markos-flow.md` |

### Có thể bỏ qua (legacy / one-time, KHÔNG cần ở repo mới)
| Path | Vì sao bỏ |
|---|---|
| `storage/session.py` — nhánh v1 (`_clear_v1_row`, write vào table `sessions` cũ) | Mặc định đã ở Phase D (`DB_V2_READ=true`, `DB_V2_WRITE=false`) — chỉ còn v2. Nhánh v1 chỉ là an toàn lưới cho rollback, repo mới bắt đầu sạch nên không cần. |
| `scripts/backfill_v2.py`, `scripts/verify_v2_drift.py` | Script một-lần cho migration v1→v2 đã xong. Repo mới start thẳng ở v2, không cần backfill. |
| `_pending_three_tier/` | (Đã xoá ở commit này) — code nhánh three-tier không dùng, bản gốc còn trong git history nếu cần tham khảo. |
| `__pycache__/`, `.pytest_cache/` | Build cache, không track. |

### Lưu ý khi setup repo mới
1. Tạo Supabase project mới → chạy lần lượt `storage/migrations/001_initial_sessions.sql` → `011_fb_available_accounts.sql`.
2. Copy `.env.example` → `.env`, điền key thật (Telegram token mới nếu muốn bot riêng).
3. `DB_V2_READ=true`, `DB_V2_WRITE=false` (default) — không cần đụng `storage/session.py` nhánh v1.
4. Nếu muốn dọn tiếp `storage/session.py` (xoá nhánh v1 hẳn) — nên làm ở **repo mới**, sau khi đã chạy ổn vài ngày, để dễ rollback nếu có vấn đề.

---

## Phụ lục — Thống kê

| Hạng mục | Số lượng |
|---|---|
| Strategic skills | 7 + Full pipeline |
| Operational skills | 22 |
| Analysis skills | 5 |
| Pipelines | 3 (full, content_generator, ads_intelligence) |
| Industry brains | 14 ngành |
| Lệnh Telegram | 14 (6 user + 3 ads + 4 admin + aliases) |
| Scheduler jobs | 5 |
| LLM providers | Claude (2) + GPT-5 (3) + Gemini |
