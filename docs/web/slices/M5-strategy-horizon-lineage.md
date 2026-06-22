# SPEC — M5 Strategy horizon linh hoạt + tách định vị bền + rà lineage

> Tiếp nối M4. Founder chốt (2026-06-22): làm "sâu" — horizon linh hoạt (không cứng 90
> ngày) + tách **định vị (bền)** khỏi **roadmap (theo quý)**; VÀ rà lại nguồn để khâu
> "Lập chiến dịch" + downstream không ăn output cũ → đi lệch. Spec trước, code sau theo tăng dần.

## 0. Vì sao
- Marketing hiện đại = **nhiều tầng thời gian lồng nhau**, không 1 horizon cứng:
  always-on (liên tục) · định vị/brand (năm+) · kế hoạch-review (quý/90 ngày) · sprint (2–4 tuần) · moment (dịp).
- App hiện đóng cứng "Chiến lược **90 ngày**": hợp với lớp roadmap, **chật** cho định vị (sống lâu hơn).
- Founder cảnh báo: đổi ở **nguồn** (synthesis) thì "Lập chiến dịch" và downstream phải đọc bản MỚI,
  không thì cache/đầu ra cũ làm lệch.

## 1. Quyết định (đã chốt)
- 🅰 **Horizon linh hoạt** ở gate: 30/60/90 ngày (+ "để Max cân theo stage" = mặc định). Tiền lệ: `agents/prompts.py:651`.
- 🅱 **Tách định vị bền khỏi roadmap quý**: synthesis gồm 2 phần rõ — (i) Định vị/SAVE/JTBD = **bền**;
  (ii) Roadmap = **theo horizon đã chọn**, cuốn chiếu.
- 🆎 (từ M4) đang/đã làm riêng: chốt Synthesis + curate/chốt pillars. idea-3 (posture brand/activation)
  = **optional field ở GATE** (không ở always-on/occasion/hub) — gộp luôn vào đợt gate này.

## 2. 🗺️ Bản đồ lineage (ai đọc strategy outputs)
**Dạng A — Web TEXT** (skill_run markdown, đọc qua `webapp/business.py::_latest_content`):
- `campaign_plan()` (pillars + occasions) — business.py:262/265
- `occasion` brief — business.py:340/343
- `retention`/lifecycle — business.py:495
- content assets ads_copy/inbox/sequence — business.py:804/805 (`get_latest_skill_run synthesis|tactical`)

**Dạng B — Agent DICT** (`strategy` dict, keys: positioning/wedge/`roadmap_90d`/budget_allocation/content_pillars/kpi_dashboard):
- `agents/strategy.py`, `agents/strategy_prompts.py` (sinh + schema)
- `agents/campaign_intake.py` (`build_campaign_draft_from_strategy`, `_strategy_to_ctx`) đọc `roadmap_90d`, `positioning`…
- `agents/workflow_runner.py:92`

## 3. 🔴 Rủi ro cache "ăn data cũ" (bằng chứng)
| Cache (business.py) | Key thật | Mù với |
|---|---|---|
| `_campaign_plan_cache` | `{uid}:hash(synth[:300])` | **wedge, industry, horizon, posture** (đọc trong prompt nhưng KHÔNG có trong key) |
| `_occasion_cache` | `{uid}:hash((occasion,window,budget,baseline,goal,obj))` | **toàn bộ synthesis** (không băm synth) |
| `_retention_cache` | `{uid}:{m}:hash((cycle,channels,offer,hash(synth[:200])))` | phần synth sau 200 ký tự |
| `_market_kpi_cache` | `run_id` | (an toàn) |
> Đều là dict in-memory (reset khi redeploy, giữ trong 1 process).

## 4. 🔴 "90 ngày" hardcode (blast radius khi đổi horizon)
- Key cấu trúc `roadmap_90d`: `agents/strategy.py` (×3), `strategy_prompts.py` (schema), `campaign_intake.py` (×2 reader).
- Text "90 ngày": `strategy_prompts.py`, `operational_prompts.py`, `task_registry.py`, `campaign_ideation.py`, `discovery_prompts.py`, nhãn web (`strategy` page, `strategyMock`).
- ✅ Có sẵn horizon-by-stage ở `agents/prompts.py:651` → chuẩn hoá theo, đừng phát minh lại.

## 5. Kế hoạch sửa (tăng dần, an toàn)
**B1 — Đóng rủi ro cache TRƯỚC (rẻ, gỡ đúng lo ngại founder, làm ngay cả khi chưa đổi horizon):**
- `_campaign_plan_cache` key thêm `wedge, industry, horizon, posture` (hoặc băm cả `synth` đầy đủ + `tact` + các input).
- `_occasion_cache` key thêm `hash(synth)` (+ wedge/usp) để đổi chiến lược ⇒ brief sinh lại.
- `_retention_cache` dùng `hash(synth)` đầy đủ thay vì `[:200]`.
- Cân nhắc: helper chung `strategy_fingerprint(uid)` = hash(synth+tact+positioning_version) để mọi cache + "đã chốt" dùng chung 1 chữ ký.

**B2 — Horizon linh hoạt:**
- Gate thêm field `horizon` (30/60/90/auto) + `posture` (brand/cân bằng/activation/auto) → lưu `profile.intake_extra`.
- `roadmap_90d` → `roadmap` + `horizon_days` (giữ alias đọc `roadmap_90d` cho dữ liệu cũ).
- Prompt synthesis (web TEXT + agent DICT) nhận horizon/posture; bỏ "90 ngày" cứng.

**B3 — Tách định vị bền khỏi roadmap:**
- Synthesis chia 2 block rõ: "Định vị (bền)" vs "Roadmap (horizon)". UI nhãn đổi.
- `campaign_plan`/`occasion` đọc đúng block; positioning đổi ÍT hơn roadmap → fingerprint nên phản ánh.

**B4 — Đồng bộ downstream + nhãn:** campaign_intake/workflow_runner đọc key mới; đổi nhãn UI "Chiến lược 90 ngày".

## 5b. ĐÃ TRIỂN KHAI (2026-06-22)
Founder chỉ đạo: (i) **chỉ sửa cho web**, KHÔNG động `agents/` — bot là code tham khảo,
sẽ xoá/rebuild thành "bot hỗ trợ web" chứ không phải nền tảng độc lập; (ii) **bỏ tiền lệ**
`agents/prompts.py:651` (horizon-theo-stage, founder thấy kém) — thiết kế lại, ưu tiên LLM hơn hardcode.

**Kiến trúc chốt:** Web TỰ SỞ HỮU việc sinh chiến lược (không xuyên pipeline bot cho synthesis).
- ✅ **B1** — `_strategy_fp()` gộp trọn nguồn; vá 3 cache (`webapp/business.py`). [đã push trước]
- ✅ **B2/B3** — `webapp/business.py::strategize_web(uid, progress)`: đọc research (T1-T3+SWOT)
  + gate (wedge/USP/horizon/posture) → 2 LLM call **prompt web tự viết**:
  - Synthesis (`TaskType.SYNTHESIS_LONG_CONTEXT`) — MARKDOWN tách rõ **## 1 Định vị (BỀN)**
    khỏi **## 3 Roadmap (theo nhịp)**; horizon `auto` ⇒ LLM tự chọn nhịp (KHÔNG bảng cứng);
    posture nghiêng the-long/the-short hoặc auto.
  - Tactical (`TaskType.OPS_BRIEF`) — playbook per-segment theo phễu.
  - Lưu skill_run `synthesis` + `tactical_playbook` (model_used="web-strategize").
- ✅ **Định tuyến** `_execute`: `strategize`/`strategy` → `strategize_web`; `full` → research
  (pipeline) rồi `strategize_web`; còn lại (research/market/…) → pipeline như cũ. **Không gọi
  synthesis của pipeline nữa** → bot không bị tác động; agents/ giữ nguyên.
- ✅ **Gate** (`save_gate` + `api/biz/gate` + FE app.js & standalone): thêm ③ horizon
  (30/60/90/auto) + ④ posture (brand/balanced/activation/auto). Bỏ trống = auto.
- ✅ **B4 nhãn**: web bỏ "90 ngày" cứng → "Định vị (bền) · Roadmap theo nhịp".
- ✅ Verify: syntax (node/ast) + import webapp.business + unit-test `_strategy_fp`/guides.

**Lưu ý:** prompt synthesis/tactical bản agent (`agents/strategy_prompts.py`, `roadmap_90d`…)
GIỮ NGUYÊN làm tham khảo — sẽ dọn khi rebuild bot. Web không phụ thuộc chúng nữa.

## 5c. ĐÃ TRIỂN KHAI M4 "1+2" (2026-06-22)
Agency: "Max đề xuất — founder duyệt/sửa", không bắt sáng tác từ 0.
- ✅ **(1) Chốt chiến lược**: `approve_synthesis()` lưu `intake_extra.synthesis_approved_version`;
  FE so version (tạo lại synthesis → version đổi → tự bỏ chốt). nextStepCard ở trang Chiến lược:
  chưa chốt → primary = **"✅ Chốt chiến lược này"**; đã chốt → primary = **"→ Lập chiến dịch"**
  + badge "✓ Đã chốt". Checkpoint mềm (không chặn cứng điều hướng).
- ✅ **(2) Curate + chốt tuyến nền**: pillars có tick **Giữ/Bỏ**; **"✅ Chốt tuyến nền"**
  (`save_pillars` → `intake_extra.pillars_locked`); **"↻ Sinh lại có định hướng"** (steer →
  `campaign_plan(steer=)`, bỏ qua lock để curate bản mới); **"Bỏ chốt"**. `campaign_plan`
  overlay locked pillars (qua `_apply_pillar_lock`) → Lịch always-on dùng bản đã chốt.
- API mới: `/api/biz/synthesis-approve`, `/api/biz/pillars-lock`; `campaign-plan?steer=`.
- FE: app.js + dashboard-standalone.html + CSS (.pillar-keep/.pillar-foot). Verify node/ast/import OK.
- idea-3 (posture) đã nằm ở gate (mục 5b) — KHÔNG ở always-on/occasion (đúng phân tích phản biện).

## 6. Mở / cần chốt
- [ ] Thứ tự: nên làm **B1 (cache) trước** để khoá rủi ro ngay, rồi B2→B4? (khuyến nghị: có)
- [ ] Có gộp "chốt Synthesis" (M4 1+2) với fingerprint ở B1 không (để "đã chốt" cũng theo chữ ký)?
- [ ] `roadmap_90d`: đổi tên hẳn hay giữ + alias? (khuyến nghị: thêm `roadmap`+`horizon_days`, alias đọc cũ)
- [ ] Posture (idea-3) làm cùng đợt này hay tách? (đang gộp vào gate ở B2)
