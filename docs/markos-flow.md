# MarkOS — Flow Làm Việc Đầy Đủ

> Cập nhật: 2026-06-05 | Branch: integration/consolidated

---

## Tổng quan kiến trúc

```
User (Telegram)
    ↓
bot/handlers.py          ← State machine chính (dispatcher)
    ↓
agents/pipeline.py       ← Strategic pipeline orchestration
agents/operational_skills_config.py  ← Operational skill execution
    ↓
tools/llm_router.py      ← Multi-LLM routing + failover
    ↓
Anthropic Sonnet / OpenAI GPT-5 / Gemini Pro
    ↓
bot/renderers.py         ← Excel + Telegram card output
    ↓
User nhận file .xlsx + preview text
```

---

## Layer 1 — Entry & Onboarding

### /start

```
User gửi /start
    │
    ├─ Lần đầu (không có user_name)
    │   ├─ Hỏi tên → _awaiting_user_name = 1
    │   └─ Có tên → hỏi mức tiếng Anh → LANG_LEVEL_KEYBOARD
    │       [lang_none / lang_moderate / lang_fluent]
    │       └─ Lưu en_level → hiện MAIN_MENU
    │
    └─ Returning user
        ├─ Clear toàn bộ transient flags (xem danh sách mục 7)
        ├─ Reset stage = TASK_SELECT
        └─ Hiện status (tên business, chiến lược có chưa) + MAIN_MENU
```

**Transient flags bị clear khi /start** (`handlers.py:242-251`):
`_awaiting_feedback_for`, `_awaiting_rating_for`, `_awaiting_followup_for`,
`_awaiting_image_edit`, `_awaiting_image_reference`, `_pending_regen_skill`,
`_pending_feedback`, `_monitor_pending_page_id`, `_last_image_b64`,
`_advisor_mode`, `_awaiting_calendar_edit`

---

## Layer 2 — McKinsey Gate (Profile Check)

Trước khi chạy BẤT KỲ skill nào, bot kiểm tra `is_basic_business_context_ready()`:

**5 fields bắt buộc** (`storage/models.py:81-144`):

| Field | Mô tả |
|---|---|
| `industry` | Ngành kinh doanh |
| `product_service` | Sản phẩm/dịch vụ cụ thể |
| `target_customer` | Khách hàng mục tiêu |
| `stage` | Giai đoạn (startup/growth/scale) |
| `primary_goal` | Mục tiêu chính (revenue/awareness/retention) |

```
Gate fail → BIZ_CONTEXT_AWAITING = pending_skill_name
  → Bot hiện form hỏi đúng các field còn thiếu
  → User fill → check lại → pass → chạy skill đã queue
```

---

## Layer 3 — Intake Multi-turn (8 Fields)

**Trigger:** Khi user chọn task chiến lược lần đầu

**8 fields bắt buộc** (`storage/models.py:107-128`):

| # | Field | Ví dụ |
|---|---|---|
| 1 | `industry` | FnB, SaaS, Retail, Spa |
| 2 | `product_service` | Spa Đông y, App quản lý, Cà phê |
| 3 | `target_customer` | Phụ nữ 25-40, SME owner |
| 4 | `location` | TPHCM Q7, Hà Nội, Toàn quốc |
| 5 | `monthly_revenue` | 50-100tr, < 30tr |
| 6 | `current_channels` | Facebook, TikTok, Zalo OA |
| 7 | `primary_goal` | Tăng doanh thu, Brand awareness |
| 8 | `main_challenge` | Chi phí ads cao, Khách không quay lại |

**Optional** (Sprint 2): `usp`, `usp_confidence` (clear / draft / missing)

```
Stage = INTAKE
    ↓
User gõ tự do → run_intake(session, user_msg)
    → LLM route: GPT-5-mini primary → Haiku fallback → Sonnet last
    → Parse JSON từ ```json...``` block
    → is_intake_complete()?
        ├─ NO  → tiếp tục hỏi phần còn thiếu
        └─ YES → Stage = CONFIRMED
                  → Hiện profile summary
                  → CONFIRM_KEYBOARD: "Đúng rồi" / "Sửa lại"
    
User click "Đúng rồi, bắt đầu!"
    → _proceed_after_confirm()
    → Stage = MARKET_RESEARCH (nếu task = full)
    → Hoặc thẳng vào targeted stage
```

---

## Layer 4 — Strategic Pipeline

**6 stages** (`agents/pipeline.py:644-652`):

### Stage 1 — Market Research
```
run_market_research(session)
    → TaskType.MARKET_RESEARCH_DATA
    → Provider: Gemini Pro Grounded (có Google Search citation)
    → Fallback: Gemini Pro → Sonnet
    → Output: TAM/SAM/SOM, xu hướng ngành, cơ hội
    → Lưu: session.results["market_research"]
```

### Stage 2 — Competitor Analysis
```
run_competitor_analysis(session)
    → TaskType.COMPETITOR_MATRIX
    → Output: Ma trận so sánh đối thủ, điểm mù của thị trường
    → Button: "Phân tích sâu 1 đối thủ" [run_compare] (Sprint 4)
```

### Stage 3 — Customer Insight
```
run_customer_insight(session)
    → TaskType.CUSTOMER_INSIGHT → Sonnet primary
    → Output: ICP profile, Jobs-to-be-Done, Customer Journey Map
```

### Stage 4 — Psychology & Pricing
```
run_psychology_and_pricing(session)
    → TaskType.PSYCHOLOGY → GPT-5 primary
    → (Dùng GPT-5 vì Sonnet hay timeout ở 8-10K token output)
    → Output: Pricing model, psychology tactics, revenue optimization
```

### Stage 5 — USP Definition (conditional)
```
if usp_confidence == "clear"  → SKIP (user đã có USP rõ)
if usp_confidence == "draft"  → REFINE mode
if usp_confidence == "missing" hoặc None → FIND mode

run_usp_definition(session)
    → Output: USP statement, proof points, differentiation angle
```

### Stage 6 — Strategy Synthesis (interactive)
```
KHÁ KHÁC 5 STAGE KIA — không tự động chạy.

Sau stage 5, bot hiện "Tiếp tục chiến lược" button
    → _start_strategic_consultation()
    → 7 strategy questions, mỗi câu có options hoặc custom answer
    → Lưu vào session.pending_intake["_strategy_answers"] = JSON
    → User OK all 7 → run_strategy_synthesis()
    → Output: SAVE Framework + SMART Goals + 90-day Roadmap
```

**Routing theo task** (`TASK_PIPELINE_MAP`):
```
"full"       → [MARKET, COMPETITOR, CUSTOMER, PSYCHOLOGY, USP, SYNTHESIS]
"market"     → [MARKET_RESEARCH] only
"competitor" → [COMPETITOR] only
"customer"   → [CUSTOMER_INSIGHT] only
"pricing"    → [PSYCHOLOGY_PRICING] only
"strategy"   → [SYNTHESIS] only
```

---

## Layer 5 — Operational Skills (Single-shot)

### Content Calendar
```
User chọn "Lịch Nội Dung"
    → _send_single_shot_form() với 3 fields:
        duration (default: 4 tuần)
        channels (default: Facebook + TikTok)
        budget (optional)
    → User fill → run_operational_skill("content_calendar")
    → LLM: CONTENT_TABLE → GPT-5-mini
    → Output: Markdown với per-channel sections
    → Excel: dynamic renderer (pillar coloring)
    → Sau khi xong → CALENDAR_TO_CONTENT_GEN_KEYBOARD:
        ✅ Chạy hết nội dung theo lịch  [run_content_gen_after_cal]
        ✏️ Cần sửa lịch                  [calendar_edit_request]
        ⏭️ Để sau                        [skip_content_gen_after_cal]
```

### ContentGeneratorPipeline (chạy 4 skills liền)
```
ContentGeneratorPipeline.run_pipeline(session):
    _prefill_intake(session)  ← Derive creator_type, scope, funnel từ gate answers
    
    Chạy tuần tự:
    1. post_batch        → GPT-5-mini (OPS_CONTENT_BULK)
    2. video_script_gen  → GPT-5 (OPS_CONTENT_CREATIVE)
    3. ugc_brief         → GPT-5 (OPS_CONTENT_CREATIVE)
    4. ads_generator     → GPT-5 (OPS_CONTENT_CREATIVE)
    
    Mỗi sub-skill: try/except độc lập
        → fail 1 skill không crash toàn pipeline
    
    Return "MULTI_OUTPUT:post_batch,video_script_gen,ugc_brief,ads_generator"
```

### Các operational skills khác
| Skill | LLM Route | Output |
|---|---|---|
| `campaign_brief` | OPS_BRIEF (GPT-5) | 10-section campaign plan |
| `ads_copy` | OPS_CONTENT_CREATIVE (GPT-5) | 3 tầng × 2 variant |
| `video_scripts` | OPS_CONTENT_CREATIVE | Kịch bản 4 creator type |
| `post_write` | OPS_CONTENT_CREATIVE | 1 bài hoàn chỉnh, 3 hook variants |
| `post_adapt` | CHANNEL_ADAPT (GPT-5-mini) | 1 bài → N channel formats |
| `post_voice_check` | CRITIC_REVIEW (Haiku) | Voice score /10 + fix suggestions |

---

## Layer 6 — Tone Calibration (Sprint 6)

**Trigger:** Tự động sau `content_calendar` kết quả

```
_start_tone_calibration(message, session, calendar_result)
    │
    ├─ Extract bài viết 1 từ calendar
    ├─ Generate draft post 1 với tone check
    ├─ Hiện post 1 + TONE_CHECK_KEYBOARD:
    │   ✅ Tone đúng — Lock & gen tiếp  [tone_approve]
    │   ✏️ Chỉnh tone (gõ feedback)    [tone_reject]
    │   ⏭ Bỏ qua kiểm tra              [tone_skip]
    │
    ├─ Nếu tone_reject:
    │   ├─ User gõ feedback text
    │   ├─ Inject vào post 1 prompt → regenerate
    │   ├─ Show lại + TONE_REGEN_KEYBOARD
    │   └─ Loop đến khi approve HOẶC rejection_count >= 3
    │       └─ >= 3 → fallback PA1 tone, proceed anyway
    │
    └─ Khi tone LOCKED:
        session.tone_calibration["locked_signals"] = {feedback của user}
        → Generate N-1 posts còn lại với signals injected
```

**session.tone_calibration structure:**
```python
{
    "stage": "waiting_first" | "checking_tone" | "locked" | "generating_rest" | "done",
    "rejection_count": 0,
    "locked_signals": {},       # feedback user đã approve → apply cho N-1
    "calendar_remaining": [],   # posts 2..N chờ gen
    "sample_content": None,     # PA1 fallback nếu rejection >= 3
}
```

---

## Layer 7 — LLM Routing

**`tools/llm_router.py` — ROUTING_TABLE:**

| TaskType | Primary | Fallback | Last | Lý do |
|---|---|---|---|---|
| `MARKET_RESEARCH_DATA` | Gemini Pro Grounded | Gemini Pro | Sonnet | Cần Google Search citation |
| `INTAKE_JSON` | GPT-5-mini | Haiku | Sonnet | Fast JSON parsing |
| `CUSTOMER_INSIGHT` | Sonnet | GPT-5 | Gemini | Tốt nhất tiếng Việt narrative |
| `PSYCHOLOGY` | GPT-5 | Sonnet | GPT-5-mini | Sonnet timeout @ 8-10K output |
| `SYNTHESIS_LONG_CONTEXT` | Gemini Pro | GPT-5-mini | Sonnet | Cần 1M context window |
| `OPS_CONTENT_CREATIVE` | GPT-5 | Sonnet | GPT-5-mini | Writing quality |
| `OPS_CONTENT_BULK` | GPT-5-mini | Sonnet | Gemini Flash | Volume + cost |
| `CRITIC_REVIEW` | Haiku | GPT-5-mini | — | Fast review, không cần sáng tạo |

**Failover logic** (`llm_router.py:658-744`):
```python
for provider in ROUTING_TABLE[task_type]:
    try:
        result = await asyncio.wait_for(provider_call(), timeout=per_provider_timeout)
        return result
    except (TimeoutError, RateLimitError, ProviderUnavailable):
        continue  # thử provider kế tiếp

raise AllProvidersFailedError(...)
```

**Per-provider timeout:** Sonnet 55s / GPT-5 90s / Haiku 45s

---

## Layer 8 — Excel Rendering

**2 paths:**

### Path A — Template-based (dùng `content_generation_template.xlsx`)
```
Skill có trong SKILL_TEMPLATE_SHEET:
    post_batch, content_generator  → sheet "📅 Content Calendar"
    ads_generator, ads_copy                       → sheet "✍️ Ad Copy"
    video_scripts, video_script_gen               → sheet "🎬 Video Script"
    ugc_brief                                      → sheet "🤝 UGC Brief"
    email_zalo_sequence                            → sheet "📧 Email & Zalo"

render_template_excel():
    1. Load template .xlsx
    2. Extract markdown tables từ LLM output
    3. Fuzzy-match LLM column headers → template column headers (_norm_header)
    4. Fill rows từ row 4+ (row 3 = header)
    5. Stamp business_name vào A1
    6. Xóa sheets không dùng, giữ target sheet + "📖 Hướng dẫn"
    7. Return .xlsx bytes
```

### Path B — Dynamic (tạo workbook mới)
```
Skill KHÔNG có trong SKILL_TEMPLATE_SHEET (vd: content_calendar):

render_excel_file():
    1. Extract markdown tables từ LLM output
    2. _pivot_keyvalue_tables() → gộp mini KV tables thành 1 sheet Tổng quan
    3. Tạo Workbook mới, 1 sheet per table (tối đa 8 sheets)
    4. Detect cột "Pillar" / "Content Pillar" → tô màu theo pillar:
        Educate → xanh lá nhạt E8F5E9
        Trust   → xanh dương nhạt E3F2FD
        Engage  → vàng nhạt FFFDE7
        Convert → hồng nhạt FFEBEE
    5. Header fill: 2C3E50 (dark navy)
    6. Auto column width (capped 60)
    7. Freeze header row
    8. Return .xlsx bytes

Fallback nếu không tìm thấy pipe table:
    → _haiku_rebuild_table(): gọi Haiku để convert narrative → markdown table
    → Nếu Haiku cũng fail → return None (file rỗng, không crash)
```

---

## Layer 9 — Rating & Feedback Loop

```
_send_ops_result(message, session, skill_name, result)
    ├─ Parse LLM output → parse_by_format()
    ├─ Format Telegram preview card
    ├─ Attach .xlsx file nếu có
    ├─ Hiện RATING_KEYBOARD (⭐×5 + bỏ qua)
    └─ pending_intake["_awaiting_rating_for"] = skill_name

User click rating:
    ├─ Rating >= 4 ★
    │   ├─ "Cảm ơn sếp!" → ACTION_KEYBOARD
    │   └─ Options: Về menu / Hỏi thêm / Next skill
    │
    └─ Rating <= 3 ★
        ├─ FEEDBACK_PROMPT_KEYBOARD
        ├─ User gõ feedback OR click "Bỏ qua"
        ├─ Feedback → pending_intake["_pending_feedback"]
        ├─ REGEN_PROMPT_KEYBOARD:
        │   ✅ Chạy lại theo feedback  [regen_yes]
        │   ⏭️ Bỏ qua                  [regen_no]
        └─ regen_yes → rerun skill với _user_correction injected vào prompt
```

**Feedback storage** (tối đa 5 versions/skill, FIFO):
```python
session.feedback["skill_name"] = [
    {"version": 2, "rating": 3, "feedback": "khô quá", "created_at": "..."},
    ...
]
```

---

## Layer 10 — State Machine: Toàn bộ flags

**Flags trong `pending_intake`** — cái nào bật thì handler đó chạy:

```
Onboarding:
    _awaiting_user_name          → Đang hỏi tên
    (en_level = None)            → Đang hỏi mức tiếng Anh

Intake & Profile:
    BIZ_CONTEXT_AWAITING         → McKinsey gate form đang fill
    BIZ_CONTEXT_PENDING_SKILL    → Skill chờ sau khi gate pass
    OPS_INTAKE_AWAITING          → Ops skill form đang fill

After skill:
    _awaiting_feedback_for       → User đang gõ feedback text
    _awaiting_rating_for         → User đang pick rating
    _awaiting_followup_for       → User đang hỏi Q&A về output

Strategic consultation:
    _awaiting_strategy_q_custom  → User gõ custom answer cho strategy Q
    _awaiting_strategy_edit      → User mô tả chỉnh sửa chiến lược
    _strategy_questions          → Queue Q còn lại
    _strategy_answers            → JSON {q_key: answer} đã trả lời

Calendar edit:
    _awaiting_calendar_edit      → User đang mô tả sửa lịch
    _calendar_feedback           → Feedback tích lũy để re-run calendar

Campaign ideation (post A→Z):
    _awaiting_campaign_idea      → User mô tả ý tưởng campaign
    _awaiting_campaign_needs     → User trả lời questionnaire needs
    _awaiting_offer_prefs        → User chọn offer philosophy
    _awaiting_campaign_finalize  → User fill 4 fields (budget/team/start/discount)

Image generation:
    _awaiting_image_reference    → User upload ảnh mẫu
    _awaiting_image_edit         → User mô tả chỉnh ảnh
    _last_image_b64, _last_image_size, _img_prompt, _img_n

Other:
    _post_editing                → User đang edit post text
    _awaiting_brief_edit         → User mô tả chỉnh brief
    _awaiting_research_paste     → User paste tài liệu research
    _advisor_mode                → Đang trong chế độ tư vấn tự do
```

**PipelineStage enum** (`storage/models.py`):
```
IDLE → TASK_SELECT → INTAKE → CONFIRMED →
MARKET_RESEARCH → COMPETITOR → CUSTOMER_INSIGHT →
PSYCHOLOGY_PRICING → USP → SYNTHESIS → COMPLETE
```

---

## Sơ đồ tổng thể

```
/start
  ↓
[Layer 1] Onboarding check
  ├─ Lần đầu: tên + en_level
  └─ Returning: clear flags + MAIN_MENU
        ↓
[Layer 2] McKinsey Gate
  └─ 5 fields cơ bản → gate form nếu thiếu
        ↓
[Layer 3] Intake (nếu chưa có đủ 8 fields)
  └─ LLM multi-turn → JSON parse → confirm
        ↓
[Layer 4] Strategic Pipeline (nếu chọn task chiến lược)
  Market → Competitor → Customer → Psychology → USP → Synthesis
        ↓
[Layer 5] Operational Skills (single-shot hoặc pipeline 4 sub-skills)
  content_calendar / post_batch / video_scripts / ugc / ads / ...
        ↓
[Layer 6] Tone Calibration (tự động sau content_calendar)
  Post 1 preview → user approve/reject → lock signals → gen N-1
        ↓
[Layer 7] LLM Router
  Task type → provider chain → failover → result
        ↓
[Layer 8] Excel Renderer
  Template-based hoặc Dynamic → .xlsx bytes
        ↓
[Layer 9] Rating & Feedback
  1-5 sao → feedback → optional regen
        ↓
[Layer 10] State cleanup
  ACTION_KEYBOARD → menu / followup / next skill
```

---

## Gaps đã xác định (từ audit 2026-06-05)

| Gap | Severity | Mô tả |
|---|---|---|
| Voice Check không ở main pipeline | High | `ContentGeneratorPipeline` không gọi `post_voice_check` |
| `post_batch` thiếu channel-specific tone | High | Zalo OA và Facebook nhận cùng instruction |
| Không có post-LLM validator | Medium | Hook length, CTA dedup chỉ là text trong prompt |
| Excel schema mềm | Medium | Cột bị drop âm thầm nếu LLM đặt tên lệch |
| Multi-LLM inconsistency | Medium | Cùng skill, khác provider → khác giọng văn |
| Input validation form | Low | Nhập rác vào field budget vẫn nhận |
| UGC authenticity | Structural | AI + RLHF model = fluent, không thể "vụng về tự nhiên" |
