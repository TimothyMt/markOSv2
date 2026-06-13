# Marketing OS — Workflow 2.0 Implementation Plan

**Version:** 1.0
**Status:** CTO-approved, ready for execution
**Branch:** `content-gen-suite`
**Target completion:** 6-7 sprints

---

## 0. Executive Summary (cho CEO)

Workflow 2.0 redesign **toàn bộ flow từ Strategic → Ops** với 4 checkpoint approval, USP definition layer, Campaign Brief 2.0 conversational, Brand Voice persistent DB, Content Writing tone calibration loop, và mã ID system cho per-post editing.

**Mục đích:** Bridge gap rõ ràng giữa Strategic insight và Ops execution, cho phép founder VN có 1 workflow end-to-end thay vì chạy rời rạc từng skill.

**Tác động:**
- User Strategic xong → có Marketing Strategy complete + USP rõ ràng
- Bridge sang Ops qua Campaign Brief 2.0 (conversation 8 turn auto-fill từ Strategy)
- Brand Voice setup 1 lần, dùng mãi (lưu DB)
- Content production qua tone calibration loop — gen 1 bài check, OK gen N-1 còn lại
- Per-post action: sửa / adapt / variant / xóa qua mã ID `POST-XXX`

**Effort:** ~6-7 tuần phân thành 7 sprint, mỗi sprint test-gated.

---

## 1. Architecture Decisions Locked

### Strategic Layer
| Quyết định | Lock |
|---|---|
| `retention_strategy` + `winback_campaign` strategic | **A1+A2** — thêm 2 stage vào Full Pipeline + giữ standalone |
| USP layer | **Hybrid (A+B)** — intake hỏi confidence, có usp_definition skill mới, Synthesis có section USP cứng |
| USP intake field | Profile có 2 field mới: `usp` + `usp_confidence` (clear/draft/missing) |

### Campaign Bridge Layer
| Quyết định | Lock |
|---|---|
| Campaign Brief format | **8 turn conversation** (bỏ section 10 Risk+Asset) |
| Brief multi-turn | Gap multi-turn text tự do (không button) |
| Mục tiêu options | 5 lựa chọn: Awareness / Consideration / Conversion / Loyalty / Tất cả |
| Audience flow | Confirm explicit (bỏ "ngầm") |
| Campaign options khi lần đầu | Chỉ "Campaign mới" + "Skip" (ẩn "Tối ưu cũ" nếu chưa có data) |

### Brand Voice Layer
| Quyết định | Lock |
|---|---|
| Trigger Brand Voice | **Option 3 — lazy** (hỏi khi user chạy ops creative lần đầu) |
| Persistence | Lưu DB persistent across sessions |
| Override per campaign | Brand Voice base + voice_override trong campaign |

### Content Execution Layer
| Quyết định | Lock |
|---|---|
| Workflow | **Tone Calibration Loop** — gen bài 1 check, OK gen N-1 |
| Loop cap | 3 lần reject → **PA1** ask sample content cũ |
| Output | Excel với mã ID `POST-XXX` |
| Per-post action | Sửa / Adapt / Variant / Xóa qua paste mã ID |
| Versioning | **Overwrite** (không giữ history) |

### Deferred (Phase 2)
- E1+E4 — Data analytics (lấy data thực user) → chuyển qua mục Analytics, xử lý sau

---

## 2. Sprint Breakdown

### Sprint 1 — Foundation (DB Schema)
**Goal:** Setup data structures cho mọi sprint sau dùng được.

**Files modified:**
- `storage/models.py` — thêm USP fields vào `BusinessProfile`
- `storage/models.py` — thêm `tone_calibration` + `content_outputs` + `campaign_brief_versions` vào `Session`

**Schema changes:**

```python
@dataclass
class BusinessProfile:
    # ... existing fields ...
    usp: Optional[str] = None                    # NEW — Unique Selling Proposition
    usp_confidence: Optional[str] = None         # NEW — "clear" / "draft" / "missing"

@dataclass
class Session:
    # ... existing fields ...
    # NEW — Brand Voice rules (persistent across sessions in user_brand_voice DB later)
    # For now stored in session.preferences['brand_voice_id'] to link DB row
    
    # NEW — Tone calibration state (Sprint 6)
    tone_calibration: dict = field(default_factory=dict)
    # Schema: {
    #   "campaign_id": "...",
    #   "locked_signals": {"tone_adj": "...", "body_length": "...", ...},
    #   "rejection_count": 0,
    #   "sample_content_provided": False,
    # }
    
    # NEW — Content outputs với mã ID (Sprint 7)
    content_outputs: dict = field(default_factory=dict)
    # Schema: {
    #   "POST-001": {
    #     "campaign_id": "...",
    #     "week": 1, "day": "Mon",
    #     "channel": "facebook",
    #     "content": {...},
    #     "adapted_versions": ["POST-001-TT"],
    #     "status": "draft",  # draft/approved/posted
    #     "created_at": "..."
    #   },
    #   ...
    # }
```

**Supabase migration:** Session schema lưu JSONB → thêm fields tự động backward-compat (default empty dict). KHÔNG cần ALTER TABLE.

**Tests:**
- Smoke: instantiate BusinessProfile với + không có USP fields
- Smoke: Session.tone_calibration default {}, content_outputs default {}
- Backward-compat: load session cũ (không có new fields) không crash

**Definition of Done:**
- [ ] Models updated
- [ ] Smoke test pass
- [ ] Commit + push

---

### Sprint 2 — USP Layer
**Goal:** User flow USP detection + skill + Synthesis upgrade.

**Files modified/created:**
- `agents/prompts.py` — `INTAKE_SYSTEM` thêm câu hỏi USP confidence
- `agents/prompts.py` — `USP_DEFINITION_SYSTEM` (NEW — skill prompt mới)
- `agents/prompts.py` — `STRATEGY_SYNTHESIZER_SYSTEM` upgrade có section USP cứng
- `agents/skills.py` — `UspDefinitionSkill` class (NEW)
- `agents/skills.py` — Register vào `SKILL_REGISTRY`
- `agents/pipeline.py` — thêm `run_usp_definition` + insert vào `PIPELINE_SEQUENCE`
- `storage/models.py` — `PipelineStage.USP_DEFINITION` (NEW enum value)
- `agents/task_registry.py` — `STRATEGIC_TASKS["full"].pipeline_stages` thêm `usp_definition`

**Logic flow:**

```
1. Intake (Haiku) — extract USP confidence từ user response
   - User trả lời "em có USP X" → usp=X, usp_confidence="clear"
   - "có mà mơ hồ" → usp_draft=Y, usp_confidence="draft"  
   - "chưa có" → usp_confidence="missing"

2. Full Pipeline thêm stage 4.5 USP Definition:
   - Run NẾU usp_confidence != "clear"
   - Skip nếu "clear" (đã có USP rõ ràng)
   - Input: market + competitor + customer + psychology+pricing prose
   - Output: 1-3 USP candidate + 1 chính + reasoning
   - Save: profile.usp (override draft) + session.results["usp_definition"]

3. Synthesis đọc profile.usp + session.results["usp_definition"]:
   - Section USP cứng output:
     "USP chính: [...]"
     "Variants: ..."
     "Reasoning: ..."
```

**Tests:**
- Test 3 path: clear / draft / missing — verify USP skill skip/run correctly
- Smoke: USP skill instantiate, system_prompt loaded, max_tokens correct
- Smoke: Full pipeline với USP stage = 6 stage thay 5

**Definition of Done:**
- [ ] Intake prompt updated (test với 3 mock user input)
- [ ] USP_DEFINITION_SYSTEM prompt written (≥800 chars, có 3 USP framework)
- [ ] UspDefinitionSkill class working
- [ ] Synthesis section USP cứng (test output có dòng "USP chính: ...")
- [ ] Pipeline integration (smoke test full pipeline 6 stages)

---

### Sprint 3 — Retention/Winback Strategic Integration
**Goal:** 2 skill này đã có ở strategic category nhưng chưa nằm trong Full Pipeline. Wire vào.

**Files modified:**
- `storage/models.py` — `PipelineStage.RETENTION_STRATEGY`, `PipelineStage.WINBACK_VISION` (NEW)
- `agents/pipeline.py` — thêm `run_retention_strategy` + `run_winback_vision` + insert vào `PIPELINE_SEQUENCE`
- `agents/task_registry.py` — `STRATEGIC_TASKS["full"].pipeline_stages` thêm 2 stage
- `agents/prompts.py` — `STRATEGY_SYNTHESIZER_SYSTEM` đọc retention + winback prose
- `storage/models.py` `Session.build_pipeline_context()` — thêm retention_strategy + winback_campaign vào stage_labels

**Logic:**

```
Full Pipeline sequence MỚI:
  1. market_research
  2. competitor
  3. customer_insight
  4. psychology_pricing
  4.5. usp_definition (Sprint 2)
  5. retention_strategy (NEW Sprint 3)
  6. winback_vision (NEW Sprint 3)
  7. synthesis (đọc cả 7 stage + USP)
```

**Tests:**
- Smoke: Full pipeline = 7 stage
- Test với mock profile có usp_confidence="clear" → skip USP, vẫn chạy retention+winback
- Test Synthesis output có cả retention + winback sections

**Definition of Done:**
- [ ] 2 stage added to PIPELINE_SEQUENCE
- [ ] PipelineStage enum updated
- [ ] Synthesis prompt aware retention+winback context
- [ ] Smoke test 7-stage pipeline

---

### Sprint 4 — Campaign Brief 2.0 (Multi-turn Conversation Skill)
**Goal:** Replace mega Brief 10-section với conversational 8-turn skill, auto-fill từ Synthesis.

**Complexity:** HIGH — pattern multi-turn khác hẳn current single-shot.

**Files created:**
- `agents/campaign_brief_v2_prompts.py` — 8 turn prompts riêng + final aggregator
- `agents/campaign_brief_v2_skill.py` — `CampaignBriefV2Skill` class với state machine
- `frameworks/campaign_scope_library.py` — 8 ngành × default scopes

**Files modified:**
- `agents/task_registry.py` — `campaign_brief_v2` task entry mới (giữ `campaign_brief` cũ coming-soon)
- `agents/operational_skills_config.py` — factory + registry entry
- `bot/handlers.py` — handle multi-turn conversation state machine
- `bot/keyboards.py` — keyboards cho 5-option (Awareness/Conv/Loyalty/Conv/All) + scope picker

**State machine schema:**

```python
session.pending_intake = {
    "_skill": "campaign_brief_v2",
    "_turn": 0,  # 0-8
    "_scope_industry": "health_beauty",
    "_scope_selected": "Combo Launch",
    "_collected": {
        "gaps": [...],
        "objective": "...",
        "duration": "...",
        "audience": "...",
        "channels": [...],
        "offer": {...},
        "budget": {...},
        "retention_integration": {...},
    },
}
```

**8 turn flow (refer to design doc):**

```
Turn 0: Scope picker (auto-suggest theo ngành từ campaign_scope_library)
Turn 1: Gap multi-turn (text tự do)
Turn 2: Objective (5 options radio)
Turn 3: Timing
Turn 4: Audience confirm
Turn 5: Channels multi-select
Turn 6: Offer + USP override + Urgency
Turn 7: Budget + KPI
Turn 8: Retention/Winback integration
   ↓
Final aggregation → output Brief markdown + save session
```

**Tests:**
- E2E test 1 ngành (Spa) — chạy full 8 turn → output có đủ 8 sections
- Edge case: user skip turn (text "skip") → bot dùng default từ Strategy
- Edge case: user revise turn cũ → bot loop back

**Definition of Done:**
- [ ] 8 turn prompts written
- [ ] State machine handler
- [ ] Campaign scope library (8 ngành × 3-5 scope mỗi ngành)
- [ ] 5-option objective keyboard
- [ ] Final brief markdown output
- [ ] E2E test pass cho 1 ngành

---

### Sprint 5 — Brand Voice DB Persistence
**Goal:** Brand Voice lưu DB user, lazy trigger, auto-inject vào ops creative skills.

**Files modified:**
- `storage/session.py` — thêm `get_brand_voice(user_id)`, `save_brand_voice(user_id, rules)`
- `storage/models.py` — `BrandVoice` dataclass mới
- `agents/operational_skill.py` — `build_user_msg` inject brand voice rules nếu có
- `agents/skills.py` — `BrandVoiceSkill` save vào DB sau gen xong
- `bot/handlers.py` — lazy trigger logic ("chưa có Brand Voice — setup giờ không?")

**Supabase table mới:**

```sql
CREATE TABLE user_brand_voice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    rules JSONB NOT NULL,
    banned_words TEXT[] DEFAULT '{}',
    preferred_words JSONB DEFAULT '[]',
    tone_descriptors TEXT[] DEFAULT '{}',
    industry_context TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_brand_voice_user ON user_brand_voice(user_id) WHERE is_active = true;
```

**Lazy trigger flow:**

```python
# In handle_callback when user picks creative ops skill (post_write/ads_copy/email/...):
async def _ensure_brand_voice(session) -> bool:
    bv = await get_brand_voice(session.user_id)
    if bv:
        return True  # already have it
    # Ask user
    await query.message.reply_text(
        "Em thấy sếp chưa setup Brand Voice. Setup giờ không?",
        reply_markup=BRAND_VOICE_PROMPT_KEYBOARD,
    )
    return False  # user must setup first
```

**Tests:**
- DB CRUD test
- Lazy trigger: user clicks post_write → bot asks BV first
- Voice override: campaign có voice_override → merge với base BV

**Definition of Done:**
- [ ] Supabase table created
- [ ] CRUD functions
- [ ] Lazy trigger UI
- [ ] BrandVoiceSkill save to DB
- [ ] Ops skills auto-load BV in build_user_msg

---

### Sprint 6 — Content Writing Tone Calibration Loop
**Goal:** Sau Content Calendar duyệt → gen bài 1 → user check tone → loop ≤3 → lock tone → gen N-1 bài còn lại.

**Complexity:** HIGH — state machine + parallel gen + tone signal extraction.

**Files created:**
- `agents/tone_calibration_handler.py` — orchestrator cho loop logic
- `agents/tone_signal_extractor.py` — Haiku parse user feedback → structured corrections

**Files modified:**
- `bot/handlers.py` — handler chain cho tone calibration state
- `bot/keyboards.py` — `TONE_CHECK_KEYBOARD` (OK / Sửa / Variant)
- `agents/content_suite_prompts.py` — `POST_WRITE_SYSTEM` aware tone_calibration

**Tone calibration state machine:**

```python
session.tone_calibration = {
    "campaign_id": "...",
    "stage": "waiting_first_post",  # → "checking_tone" → "locked" → "generating_rest" → "done"
    "rejection_count": 0,
    "current_attempt": {...},  # current draft of post 1
    "locked_signals": {},      # populated after OK
    "calendar_remaining": [...],  # N-1 posts to gen after lock
    "sample_content": None,    # PA1 fallback if rejection >= 3
}
```

**Flow handler:**

```python
async def handle_tone_check_callback(query, session):
    if query.data == "tone_ok":
        # Lock signals from current draft, gen N-1 parallel
        session.tone_calibration["stage"] = "locked"
        session.tone_calibration["locked_signals"] = extract_signals_from_draft(session.tone_calibration["current_attempt"])
        await _gen_remaining_posts(session)
    elif query.data == "tone_revise":
        # Ask user feedback
        session.tone_calibration["stage"] = "awaiting_revise_feedback"
        await query.message.reply_text("Sếp nói em sửa gì? Cứ text tự nhiên...")
    elif query.data == "tone_variant":
        # Re-gen with higher creativity
        await _regen_first_post(session, temperature_boost=True)

async def handle_user_revise_text(text, session):
    # Haiku parse feedback → corrections
    corrections = await extract_tone_corrections(text, session.tone_calibration)
    session.tone_calibration["rejection_count"] += 1
    
    if session.tone_calibration["rejection_count"] >= 3 and not session.tone_calibration.get("sample_content"):
        # PA1 fallback
        await query.message.reply_text(
            "Em đã thử 3 lần chưa đúng vibe. Sếp paste 1-2 đoạn content cũ của brand cho em đọc style nhé?"
        )
        session.tone_calibration["stage"] = "awaiting_sample"
        return
    
    # Re-gen with corrections
    session.tone_calibration["current_attempt"] = await regen_post_with_corrections(...)
    await _show_tone_check(session)
```

**Parallel gen N-1 posts:**

```python
async def _gen_remaining_posts(session):
    remaining = session.tone_calibration["calendar_remaining"]
    locked = session.tone_calibration["locked_signals"]
    
    # asyncio.gather để parallel — cap concurrency 3 tránh rate limit
    sem = asyncio.Semaphore(3)
    async def gen_one(row):
        async with sem:
            return await run_post_write_with_tone(row, locked, session)
    
    results = await asyncio.gather(*[gen_one(row) for row in remaining])
    
    # Save each into session.content_outputs với mã ID
    for i, post in enumerate(results, start=2):  # post 1 đã có, bắt đầu từ 2
        post_id = f"POST-{i:03d}"
        session.content_outputs[post_id] = {...}
    
    # Output Excel + Telegram message
    await _send_content_excel(session)
```

**Tests:**
- E2E happy path: gen post 1 → OK → 6 posts gen → Excel có mã ID
- Reject 1 lần: gen post 1 → revise feedback → re-gen → OK → continue
- Reject 3 lần → trigger PA1 sample → user paste → re-gen với sample style
- Edge: timeout 1 post trong N-1 → continue others, mark failed

**Definition of Done:**
- [ ] Tone calibration handler implemented
- [ ] Signal extractor (Haiku)
- [ ] Parallel gen with semaphore cap
- [ ] PA1 fallback after 3 reject
- [ ] Excel output with mã ID column
- [ ] E2E test all 3 flows

---

### Sprint 7 — Mã ID + Per-post Actions
**Goal:** User paste `POST-XXX` → menu action [Sửa / Adapt / Variant / Xóa].

**Files modified:**
- `bot/handlers.py` — `handle_message` parse `POST-XXX` pattern → action menu
- `bot/keyboards.py` — `PER_POST_ACTION_KEYBOARD` (4 button)
- `agents/skills.py` / `agents/operational_skills_config.py` — `post_adapt` accept post_id input
- `bot/renderers.py` — Excel output thêm cột "Mã ID"

**Mã ID logic:**

```python
POST_ID_PATTERN = re.compile(r"^POST-(\d{3})(-(TT|FB|IG|ZALO|EMAIL))?$")

async def handle_message(update, context):
    text = update.message.text.strip().upper()
    match = POST_ID_PATTERN.match(text)
    if match:
        post_id = text
        if post_id not in session.content_outputs:
            await update.message.reply_text(f"Em không thấy bài {post_id}. Sếp check lại mã trong Excel?")
            return
        await _show_per_post_action_menu(update.message, post_id, session)
        return
    # ... existing logic
```

**Action handlers:**

```python
# [✏️ Sửa nội dung]
async def handle_post_edit(query, post_id, session):
    session.pending_intake["_editing_post_id"] = post_id
    await query.message.reply_text("Sếp muốn sửa gì? Cứ text tự nhiên...")
    # → handle_message picks up text → regen with corrections → OVERWRITE

# [🔄 Adapt sang kênh]
async def handle_post_adapt(query, post_id, session):
    # Show channel multi-select keyboard
    await query.message.reply_text(
        f"Bài {post_id} hiện ở {channel}. Adapt sang:",
        reply_markup=ADAPT_CHANNEL_KEYBOARD,
    )

# [🔁 Variant A/B]
async def handle_post_variant(query, post_id, session):
    # Re-gen with creative_temperature boost
    new_id = f"{post_id}-VAR-{next_letter}"
    ...

# [❌ Xóa khỏi Calendar]
async def handle_post_delete(query, post_id, session):
    del session.content_outputs[post_id]
    await query.message.reply_text(f"✅ Đã xóa {post_id}.")
```

**Tests:**
- Paste valid mã ID → action menu hiện
- Paste invalid (POST-999 không tồn tại) → error message
- Edit flow: paste → text revise → overwrite
- Adapt flow: paste → check channels → gen adapted versions với mã ID phụ
- Variant flow: paste → variant A/B/C tự increment letter

**Definition of Done:**
- [ ] Mã ID pattern parser
- [ ] Per-post action menu
- [ ] Edit / Adapt / Variant / Delete handlers
- [ ] Excel cột Mã ID added
- [ ] E2E test all 4 actions

---

## 3. Dependencies & Critical Path

```
Sprint 1 (Foundation DB)
    ↓
    ├─→ Sprint 2 (USP) ─────────────┐
    ├─→ Sprint 3 (Retention/Winback)─┼─→ Sprint 4 (Brief 2.0)
    │                                │         ↓
    └─→ Sprint 5 (Brand Voice DB) ───┴─────────┴─→ Sprint 6 (Tone Calibration)
                                                          ↓
                                                  Sprint 7 (Mã ID + Actions)
```

**Critical path:** S1 → S2 → S3 → S4 → S6 → S7 (~5-6 tuần)
**Parallel possible:** S5 (Brand Voice DB) chạy song song với S4
**S2 + S3 cũng có thể song song** (đều dùng output S1)

---

## 4. Risk Register

| Risk | Mitigation |
|---|---|
| Multi-turn state machine (S4) phức tạp, dễ user lost mid-flow | Save state vào Supabase mỗi turn, có command `/resume_brief` |
| Tone calibration loop (S6) gen song song dễ hit Anthropic rate limit | Semaphore cap 3 concurrent, exponential backoff retry |
| Brand Voice DB migration phá user cũ | Backward-compat: nếu user_brand_voice null → skip, không force |
| Mã ID format conflict với existing text content | Pattern strict `^POST-\d{3}(-CHANNEL)?$`, không match free text |
| Sprint 4 multi-turn cost token cao (8 lần Sonnet) | Dùng Haiku cho turn 1-7 (extract decisions), Sonnet chỉ turn 8 final aggregate |

---

## 5. Definition of Done — toàn dự án

- [ ] All 7 sprints code-complete + tested
- [ ] E2E test: founder VN spa chạy hết workflow từ /start → Strategic → Brief 2.0 → Brand Voice → Calendar → 7 posts với mã ID
- [ ] Migration tested: user cũ với data cũ vẫn dùng được (backward-compat)
- [ ] Documentation updated: CLAUDE.md có workflow 2.0 map
- [ ] Coming-soon skills (campaign_brief cũ) decision: keep parked hoặc fully retire

---

## 6. Session Handoff Notes

**This session (CTO autonomous execution):**
- ✅ Wrote this plan
- ✅ Implemented Sprint 1 (Foundation DB)
- ✅ Implemented Sprint 2 (USP layer)
- ✅ Implemented Sprint 3 (Retention/Winback Strategic integration)
- ✅ Hotfix synthesis timeout + HTML resilience
- ✅ **Designed Sprint 8 — Multi-Agent Orchestrator (foundation)**

**🔄 Priority change (CEO direction):**
> **Sprint 4-7 DEFERRED.** Build Sprint 8 trước vì là **foundation cho cả hệ thống**.
> Sau khi có Multi-Agent Orchestrator → Sprint 4-7 sẽ leverage parallel execution
> + LLM router → effort giảm 30-40% mỗi sprint sau.

**Updated execution order:**
1. ✅ S1-S3 done
2. ✅ Hotfix done
3. 🔜 **Sprint 8 — Multi-Agent Orchestrator (NEW PRIORITY)**
4. ⏳ Sprint 4 — Campaign Brief 2.0 (build on top of orchestrator)
5. ⏳ Sprint 5 — Brand Voice DB
6. ⏳ Sprint 6 — Content Writing Tone Calibration (sử dụng parallel gen từ S8)
7. ⏳ Sprint 7 — Mã ID + Per-post Actions

---

## 7. Sprint 8 Design — Multi-Agent Orchestrator (FOUNDATION)

### 7.1 Why Sprint 8 first?

3 lý do bắt buộc làm trước S4-7:

1. **Giải timeout bug production ngay:** Latency từ 12-15 phút → 4-5 phút. Synthesis không còn bị skip vì context bloat.

2. **Foundation cho LLM Router multi-provider:** Mỗi agent có thể swap provider riêng (Perplexity cho research, GPT-4o cho structured, Gemini cho long context, Sonnet cho creative VN). S8 build infrastructure, các sprint sau swap được dễ dàng.

3. **Sprint 6 (Tone Calibration) cần parallel gen 7-14 bài:** Pattern parallel agent đã có sẵn = không phải code lại.

### 7.2 Architecture — Inspired by Antigravity Multi-Agent

```
┌──────────────────────────────────────────────────────────────┐
│                  🎼 ORCHESTRATOR                              │
│             (light Sonnet — director only)                    │
│  Decides tier sequence, handles progress callbacks            │
└─────────────────────────────────┬────────────────────────────┘
                                  │
   TIER 1 — Foundation (3 agents parallel, no deps)            │
        ├─ 🌍 Anna (Market Research)        [primary: Sonnet]  │
        ├─ 🕵️ Bình (Competitor)             [primary: Sonnet]  │
        └─ 👥 Chi  (Customer Insight)        [primary: Sonnet]  │
        Wait: asyncio.gather → max latency ~80s                 │
                                  ↓                              │
   TIER 2 — Strategy synthesis (2 agents parallel after T1)    │
        ├─ 🎯 Linh (USP Definition)         [primary: Sonnet]  │
        └─ 🧠 David (Psychology+Pricing)    [primary: Sonnet]  │
        Wait: max latency ~80s                                  │
                                  ↓                              │
   TIER 3 — Customer journey (sequential — Winback needs Ret)  │
        ├─ 🔄 Minh (Retention) → 🔁 Phương (Winback)           │
        Wait: ~160s sequential                                   │
                                  ↓                              │
   TIER 4 — Final aggregation                                   │
        └─ 📋 Tâm (Synthesizer)              [Sonnet + cache]  │
        Wait: ~90s                                              │
                                                                 │
   TOTAL: ~80 + 80 + 160 + 90 = ~7 phút (vs current 12-15p)    │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 Files map

**Create:**
- `agents/orchestrator.py` (~300 lines)
  - `TierConfig` dataclass
  - `AgentResult` dataclass
  - `run_tier()` — parallel agents within tier with fault isolation
  - `run_multi_agent_pipeline()` — top-level entry, tier-by-tier
  - `STRATEGIC_PIPELINE_TIERS` — 4-tier definition
- `agents/agent_wrappers.py` (~200 lines)
  - Wrap existing `AgentSkill` classes as async agent functions
  - Each wrapper handles: timeout, error capture, result formatting
- `tools/llm_router.py` (~150 lines — initial stub)
  - `Provider` enum (anthropic_sonnet, anthropic_haiku, openai_gpt4o, perplexity_sonar, gemini_pro)
  - `TaskType` enum (mapping mỗi agent → task type)
  - `ROUTING_TABLE` — primary + fallback chain per task
  - `call()` — single entry point (initial: chỉ wrap Anthropic, sẵn extend)

**Modify:**
- `agents/pipeline.py` — add `run_multi_agent_pipeline()` as ALTERNATIVE entry point
  - Keep `run_targeted_pipeline()` cũ — backward compat, dùng cho single skill
  - Mới `run_multi_agent_pipeline()` — dùng cho `task=full` (multi-agent path)
- `bot/handlers.py` — `_run_pipeline_sequentially()` dispatch:
  - `task=full` → `run_multi_agent_pipeline()` (new path)
  - Single task → `run_targeted_pipeline()` (existing path)
- `bot/handlers.py` — `TASK_STAGE_COUNT` add tier metadata
- `config.py` — feature flag `USE_MULTI_AGENT = True` (toggle để rollback nhanh nếu cần)

**Optional (nice-to-have S8):**
- `agents/digital_twin_personas.py` — light upgrade existing prompts với role name + personality
- `bot/keyboards.py` — progress indicator có tier name (vd: "Tier 2/4: Strategy synthesis...")

### 7.4 Sub-sprints (S8.1 → S8.7)

| Sub | Việc | Effort | Definition of Done |
|---|---|---|---|
| **S8.1** | Core orchestrator skeleton (TierConfig, AgentResult, run_tier) | 4h | Unit test: tier runs N agents parallel, fault isolation pass |
| **S8.2** | Agent wrappers — wrap 8 existing AgentSkill classes | 4h | Each wrapped agent returns AgentResult; smoke test all 8 |
| **S8.3** | LLM Router stub — single provider, prepare interface | 3h | call() works with anthropic; ROUTING_TABLE defined |
| **S8.4** | STRATEGIC_PIPELINE_TIERS definition (4 tier) | 2h | Tier dependencies validated; dry-run shows correct order |
| **S8.5** | Wire vào pipeline.py + handlers (feature flag) | 4h | `task=full` chạy multi-agent path, single task chạy old path |
| **S8.6** | Fault isolation + progress callbacks | 3h | 1 agent fail → others continue; user thấy "Tier 1: 2/3 OK" |
| **S8.7** | Smoke test + E2E test | 4h | Full pipeline 4 tier chạy thành công với mock profile |

**Total effort:** ~24 hours = 3 ngày dev senior.

### 7.5 Backward compatibility — additive, không destructive

```python
# Feature flag in config.py
USE_MULTI_AGENT_PIPELINE = os.getenv("USE_MULTI_AGENT", "true").lower() == "true"

# In handlers.py
if session.selected_task == "full" and USE_MULTI_AGENT_PIPELINE:
    # NEW path
    from agents.orchestrator import run_multi_agent_pipeline
    pipeline_runner = run_multi_agent_pipeline
else:
    # OLD path (single skill OR feature flag off)
    pipeline_runner = run_targeted_pipeline

async for stage_key, result in pipeline_runner(session, ...):
    ...
```

Rollback strategy: set env var `USE_MULTI_AGENT=false` → instant revert.

### 7.6 Test plan

**Unit tests:**
- `run_tier()` với 3 mock agents — verify parallel execution + result aggregation
- Fault isolation: 1 agent raise exception → tier vẫn return, other agents OK
- Critical agent fail → PipelineAbortError

**Integration tests:**
- Mock session với full profile → orchestrator chạy 4 tier → verify order: T1 trước T2 trước T3 trước T4
- Latency benchmark: parallel vs sequential — expect 40-60% reduction

**E2E test (manual):**
- Real user flow trên Telegram bot
- Compare output Sprint 1-3 sequential vs Sprint 8 multi-agent
- Quality scoring qua Haiku critic — expect <5% quality drop

### 7.7 Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Rate limit hit khi 3 agent parallel cùng lúc | Medium | High | Semaphore cap 3 concurrent + exponential backoff |
| Context sharing giữa tiers — agent T2 cần T1 output | High | Medium | Session.results lưu sau mỗi tier xong → T2 đọc qua session.build_pipeline_context() |
| Synthesis vẫn context bloat (cần T1-T3 outputs) | Medium | High | Gemini Pro long context OR Anthropic prompt caching |
| User confused khi 3 progress message cùng lúc | Low | Low | UI hiển thị 1 dòng "Tier 1: đang chạy 3 agent..." |

### 7.8 What Sprint 8 enables (downstream impact)

**Sprint 4 (Brief 2.0):**
- Brief 2.0 conversation 8 turn có thể dùng multiple agents (mỗi turn 1 mini-agent với scope library, decision rules, vv.)
- Final aggregation reuse orchestrator pattern

**Sprint 6 (Tone Calibration):**
- Gen N-1 bài còn lại = N-1 agents parallel
- Reuse `run_tier()` pattern → effort giảm 50%

**Sprint 7 (Mã ID):**
- Edit/Adapt/Variant flows có thể parallel khi user paste nhiều mã ID cùng lúc

**Long-term:**
- Multi-provider migration (Phase P3-P5) chỉ cần update `ROUTING_TABLE` dict — không phải rewrite skill code
- Multi-region Anthropic (direct + Bedrock + Vertex) = thêm provider entries

### 7.9 Definition of Done — Sprint 8

- [ ] `agents/orchestrator.py` working với 4 tier
- [ ] `agents/agent_wrappers.py` wrap 8 strategic skills
- [ ] `tools/llm_router.py` stub với ROUTING_TABLE
- [ ] Feature flag `USE_MULTI_AGENT_PIPELINE` in config
- [ ] Handler dispatch logic
- [ ] Unit tests pass (parallel execution, fault isolation)
- [ ] E2E smoke test: full pipeline complete trong ≤8 phút
- [ ] Latency benchmark vs Sprint 1-3: ≥40% reduction
- [ ] Quality drop ≤5% (Haiku critic scoring)
- [ ] Backward compat verified: single-skill path không thay đổi
- [ ] Documentation update vào IMPLEMENTATION_PLAN.md

---

## 8. Final Roadmap (Updated)

```
✅ S1 Foundation DB              (done)
✅ S2 USP Layer                  (done)
✅ S3 Retention/Winback Strategic (done)
✅ Hotfix synthesis timeout       (done)
🔜 S8 Multi-Agent Orchestrator    (NEXT — foundation)
⏳ S4 Campaign Brief 2.0         (after S8)
⏳ S5 Brand Voice DB              (parallel với S4)
⏳ S6 Tone Calibration Loop       (uses S8 parallel pattern)
⏳ S7 Mã ID + Per-post Actions    (final)
```
