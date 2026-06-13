# Max (CMO) — Bản đồ Function & Skill

> Max = persona Layer 2 (`key="cmo"`, `is_orchestrator=True`) trong `agents/manager_personas.py`.
> Vai trò: ra chiến lược tổng + điều phối team Layer 3 thực thi.
> Cập nhật: 2026-06.

---

## 1. Định danh Max

| Thuộc tính | Giá trị |
|-----------|---------|
| key | `cmo` |
| name | Max |
| emoji | 🧠 |
| role | CMO — Chiến lược & Điều phối |
| is_orchestrator | `True` (persona duy nhất) |
| Tag alias | `max` → `cmo` (trong `TAG_MAP`) |
| Vị trí | `agents/manager_personas.py` (persona #0, đầu list) |
| Menu | nút đầu `MAIN_MENU_KEYBOARD` → `persona_menu_cmo` |

---

## 2. Skills chiến lược Max TỰ chạy (Layer 2)

`owns_skills = ["full", "strategy", "market", "competitor", "customer", "pricing"]`

| Skill | Việc | Pipeline function | Provider chính (sau fix routing) |
|-------|------|-------------------|----------------------------------|
| `full` | Trọn bộ A→Z (6 bước) | `PIPELINE_SEQUENCE` (pipeline.py) | xem từng bước dưới |
| `market` | Nghiên cứu thị trường TAM/SAM/SOM | `run_market_research` | Gemini Grounded (citations) |
| `competitor` | Phân tích đối thủ 8 chiều | `run_competitor_analysis` | GPT-5 (structured matrix) |
| `customer` | Insight ICP + JTBD | `run_customer_insight` | Sonnet (VN nuance) |
| `pricing` | Chiến lược giá + psychology | `run_psychology_and_pricing` | GPT-5 (tránh timeout) |
| `strategy` | Kế hoạch tổng SAVE+SMART+90d | `run_strategy_synthesis` | Gemini Pro (1M ctx, ~40K out) |
| (usp ngầm) | USP definition (conditional) | `run_usp_definition` | Sonnet |

**Routing map**: `OPS_SKILL_TASK_TYPES` trong `tools/llm_router.py` (đã thêm 6 entry strategic).
Mọi skill chạy qua `_run_skill()` → `route(task_type, ...)` với failover chain riêng.

### Pipeline A→Z (`PIPELINE_SEQUENCE`) — thứ tự 6 bước
```
1. market_research      → MARKET_RESEARCH_DATA   (Gemini Grounded → Gemini Pro → Sonnet)
2. competitor           → COMPETITOR_MATRIX      (GPT-5 → Gemini Pro → Sonnet)
3. customer_insight     → CUSTOMER_INSIGHT       (Sonnet → GPT-5 → Gemini Pro)
4. psychology_pricing   → PSYCHOLOGY             (GPT-5 → Sonnet → Gemini Pro)
5. usp_definition       → USP_CREATIVE           (Sonnet → GPT-5 → Gemini Pro) [skip nếu usp='clear']
6. synthesis            → SYNTHESIS_LONG_CONTEXT  (Gemini Pro → GPT-5-mini → Sonnet)
```
(retention/winback đã tách sang Layer 3 — Khoa)

---

## 3. Cầu nối Strategy → Campaign (sau synthesis)

### 3a. Discovery — `agents/campaign_ideation.py`
| Function | Việc | Router |
|----------|------|--------|
| `generate_discovery_questions(session)` | 3 câu discovery ĐỘNG theo ngành (mục tiêu/campaign/deadline) | CRITIC_REVIEW: Haiku → GPT-5-mini → GPT-5 |

Gọi tại `strategy_confirm` (handlers.py:1104). Fallback `_DISCOVERY_FALLBACK` nếu thiếu ngành/lỗi.
Câu trả lời free-text của user → `_handle_campaign_idea_text` → refine.

### 3b. Ideation 2 nhánh — `agents/campaign_ideation.py`
| Function | Mode | Router |
|----------|------|--------|
| `propose_campaigns(session)` | Đề xuất 3 campaign options | Sonnet |
| `refine_user_idea(session, idea)` | Validate + refine idea user gõ | Sonnet |
| `propose_offer_levers(session, campaign)` | 4 offer levers (KHÔNG mặc định discount) | Sonnet |
| `format_options_card / format_refined_card / format_levers_card` | Render Telegram card | — |
| `format_dynamic_finalize_form / parse_dynamic_finalize_form` | Form ngày + lever params | — |
| `merge_to_brief_fields(campaign, lever, inputs)` | Gộp → 4 field cho campaign_brief | — |

### 3c. Campaign Brief — skill `campaign_brief`
- Config: `make_campaign_brief_skill()` (operational_skills_config.py), max_tokens=10K
- Prompt: `CAMPAIGN_BRIEF_SYSTEM` (operational_prompts.py) — 10 section
- Route: OPS_BRIEF (GPT-5 → Sonnet → Gemini Pro)

---

## 4. Sau khi Brief duyệt (`_confirm_brief_and_gen_calendar` — handlers.py:4682)

Thứ tự thực thi mới:
```
brief_confirm
  ├─ lưu campaign DB + log intelligence (ngầm)
  ├─ 🗺 generate_funnel_map()        → ToFu/MoFu/BoFu per channel
  ├─ 🗓 generate_execution_plan()    → roadmap skills theo goal type + retention
  ├─ 📅 content_calendar (auto)
  └─ tone calibration → production keyboard
```

### 4a. Funnel Map — `agents/funnel_mapper.py`
| Function | Việc | Router |
|----------|------|--------|
| `generate_funnel_map(session, campaign)` | Map ToFu/MoFu/BoFu cho từng kênh | GENERIC_CREATIVE |
| `parse_funnel_map(text)` | Extract JSON array | — |
| `render_funnel_map_card(funnel_map)` | Card Telegram | — |
| `funnel_map_to_calendar_input(funnel_map, campaign)` | Bridge → content_calendar | — |
| `_fallback_funnel_map(channels, objective)` | Fallback khi LLM lỗi | — |

Prompt: `FUNNEL_MAPPER_SYSTEM` (campaign_intake_prompts.py).
Lưu vào `session.results["funnel_map"]` + `pending_intake["_funnel_map_json"]`.

### 4b. Execution Plan — `agents/campaign_execution.py` (SKILL MỚI)
| Function | Việc | Router |
|----------|------|--------|
| `classify_goal_type(goal)` | text → acquisition/revenue/brand/retention/mix | — (rule-based) |
| `funnel_map_objective(goal_type)` | goal_type → objective key cho funnel mapper | — |
| `generate_execution_plan(session, funnel_map, name, goal)` | Roadmap thực thi 4 tầng | CRITIC_REVIEW: Haiku → GPT-5-mini → GPT-5 |
| `_fallback_plan(name, goal_type)` | Fallback hardcode per goal type | — |

Output 4 tầng (mọi campaign):
```
🔵 ToFu — Tiếp cận tệp mới
🟡 MoFu — Nurture & Trust
🟢 BoFu — Chốt & Convert
♻️ Retention — Giữ data & tối ưu ROI (LUÔN CÓ):
   • Thu + gắn tag data khách        ← retention_strategy
   • Nuôi lead CHƯA chuyển đổi        ← email_zalo_sequence
   • Chăm sóc khách ĐÃ mua            ← email_zalo_sequence
+ 🚀 Thứ tự ưu tiên chạy tiếp (bước cuối luôn là retention)
```

---

## 5. Điều phối Layer 3 (Max giao việc)

Cơ chế: `_build_orchestration_suffix()` inject roster Layer 3 vào system prompt khi `is_orchestrator=True`.
Max kết thúc response bằng marker:
- `[SKILL_DISPATCH:name]` → tự chạy skill chiến lược của mình
- `[PERSONA_DISPATCH:key]` → giao cho manager Layer 3 (handlers parse → đổi persona + show menu)

### Team Layer 3 Max điều phối
| key | Manager | Domain |
|-----|---------|--------|
| `digital_marketing` | Minh 📊 | Paid ads, performance, competitor intel |
| `brand` | Linh 🎨 | Brand voice, positioning |
| `marcon_pr` | Hương 📣 | MarCom, PR |
| `content` | Nam ✍️ | Content writing |
| `tiktok` | Trang 🎵 | TikTok/short video |
| `growth` | Khoa 🚀 | Retention, winback, growth ops |
| `crm` | Mai 💬 | CRM, email/zalo, sales script |
| `ecommerce` | Đức 🛒 | Sàn TMĐT |

---

## 6. Handler chính liên quan Max (`bot/handlers.py`)

| Handler / callback | Việc |
|--------------------|------|
| `persona_menu_cmo` | Mở menu Max |
| `_try_persona_route()` | Route free-text → persona (gồm parse PERSONA_DISPATCH) |
| `strategy_confirm` | Chốt strategy → discovery questions |
| `strategy_edit` | Surgical edit strategy |
| `az_have_idea` / `az_propose_campaign` | 2 nhánh ideation |
| `campaign_pick_X` / `lever_pick_X` | Chọn option / lever |
| `brief_confirm` → `_confirm_brief_and_gen_calendar` | Funnel map → execution → calendar |
| `_handle_campaign_idea_text` | Free-text idea → refine |
| `_handle_campaign_finalize_text` | Parse form → campaign_brief |

---

## 7. Nguyên tắc routing (chống RPD)

- Tác vụ ngắn (discovery, execution plan): **CRITIC_REVIEW** = Haiku → GPT-5-mini → GPT-5.
- Tác vụ dài (synthesis): **SYNTHESIS_LONG_CONTEXT** = Gemini Pro → GPT-5-mini → Sonnet.
- RPM/ITPM/OTPM tính **riêng theo từng model + nhà cung cấp** → tải chia 3 nhà (Anthropic/OpenAI/Google).
- Cần env: `ANTHROPIC_API_KEY` (bắt buộc), `GEMINI_API_KEY` + `OPENAI_API_KEY` (để phân tải; thiếu → tự fallback Sonnet).
