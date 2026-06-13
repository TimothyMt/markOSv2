# Backlog — Vấn đề để giải quyết sau

Các ý tưởng / tính năng / vấn đề đã bàn nhưng chưa triển khai. Ghi lại để không mất.

---

## 1. ✅ DONE (2026-06-10) — So sánh 1-1 với đối thủ cụ thể (Competitor 1-on-1)

**Vấn đề hiện tại:**
`competitor_comparison` ("🆚 So Sánh Với Đối Thủ") chỉ xuất hiện 1 lần duy nhất sau khi chạy xong "Phân tích đối thủ" — nếu bỏ qua thì không có cách quay lại. Khi chạy, skill này không nhận tên đối thủ cụ thể (`intake_fields=[]`) — chỉ đọc lại bản phân tích landscape cũ (`session.results["competitor"]`) → output chung chung, cảm giác "dùng lại bài gốc".

**Hướng giải quyết đã bàn:**
1. Thêm intake field "Tên đối thủ muốn so sánh trực tiếp" (required) + "Thông tin sếp biết về đối thủ này" (optional)
2. Dùng `Provider.GEMINI_PRO_GROUNDED` (`tools/llm_router.py:360`) — Gemini 2.5 Pro + Google Search grounding — để search thông tin công khai về đối thủ cụ thể đó (website, Google Maps, review...) trước khi chạy comparison
3. Kết hợp: grounded search result + `session.results["competitor"]` (nếu đối thủ đó đã được nhắc) + `session.results["competitor_spy"]` (nếu đã spy) + thông tin sếp tự cung cấp
4. Áp dụng anti-hallucination rule — nếu thiếu data, Max báo thẳng + hướng dẫn sếp bổ sung (pattern giống `competitor_spy`)
5. Thêm vào `owns_skills` của Max persona, chỉ hiện nút khi đã có `session.has_result("competitor")`

**Giới hạn cần nhớ:**
- Gemini grounded search chỉ thấy nội dung công khai đã được Google index — đối thủ nhỏ/local thì data có thể rất ít (metadata fanpage, vài review)
- Facebook fanpage: Gemini chỉ lấy được metadata bề mặt (tên trang, about, rating) — nội dung bài đăng/ads nằm sau login wall, không index được; phải dùng `competitor_spy` (FB Ads Library) để lấy data ads

**Đầu mục so sánh đề xuất (7 mục):**
1. Định vị & thông điệp chủ đạo
2. Sản phẩm/dịch vụ & USP
3. Giá & mô hình kinh doanh
4. Kênh phân phối / cách tiếp cận khách hàng
5. Tín hiệu uy tín (review, chứng nhận, social proof)
6. Điểm mạnh/yếu đối đầu trực diện (head-to-head)
7. Cơ hội khác biệt hoá riêng trước đối thủ này

**File liên quan:**
- `agents/task_registry.py:336` — TaskConfig `competitor_comparison`
- `agents/operational_prompts.py:1771` — `COMPETITOR_COMPARISON_SYSTEM`
- `agents/operational_skills_config.py:384` — `make_competitor_comparison_skill()`
- `tools/llm_router.py:360` — `_call_gemini_pro_grounded()`
- `bot/handlers.py:4704` — follow-up button hiện tại (sau khi chạy competitor)
- `bot/keyboards.py:107` — `COMPARE_PROMPT_KEYBOARD`

> ✅ Đã BẬT LẠI 2026-06-10 theo đúng hướng trên: TaskConfig mới (intake tên đối thủ +
> thông tin sếp biết), `CompetitorComparisonSkill` route qua `TaskType.COMPETITOR_RESEARCH`
> (Gemini Pro Grounded), kết hợp landscape + competitor_spy + user info, anti-hallucination
> rule trong prompt, gắn vào owns_skills của Max + soft-gate gợi ý chạy competitor trước.

---

## 2. ✅ DONE (2026-06-10) — Đã chốt với sếp, đã triển khai toàn bộ

### 2.1. ✅ Xoá dead code `run_ads_after_cal`
Handler `bot/handlers.py` (`if data == "run_ads_after_cal"`) không có button nào emit
callback này — Calendar → Ads tắt thẳng không qua Nam chưa bao giờ chạy được. Xoá block.

### 2.2. ✅ Build skill `brand_positioning` cho Linh (Brand Manager)
Flow đã chốt:
- **Input** (tự đọc từ session, KHÔNG bắt user nhập lại):
  - `usp_definition` (T2) — USP đã chốt + options + reasoning
  - `synthesis` (T4) — `positioning.statement` + 4 trục SAVE
  - `customer_insight` — segments để chia key message
  - Brand Voice DB (nếu có) — tone phải khớp
- **Output — Messaging House** (1 file HTML):
  1. Positioning statement (refine từ T4, không làm lại từ đầu)
  2. Tagline 3-5 option (mài từ USP)
  3. Value prop ladder (functional → emotional → self-expressive)
  4. Key messages per segment (1 thông điệp chính + 2-3 supporting + proof point)
  5. Do's / Don'ts khi viết (cầu nối sang brand_voice)
- **Revise loop (sếp yêu cầu):** sau khi gửi output → hỏi "Sếp muốn sửa gì không?"
  → nhận feedback → LLM update → **ghi bản đã chốt vào session tổng**
  (lưu `brand_positioning` result; các skill sau ưu tiên đọc bản này thay vì
  `synthesis.positioning` gốc)
- Gắn vào `owns_skills` của Linh + gate: chưa có T2/T4 thì gợi ý chạy
  "Nghiên Cứu & Phân Tích Thị Trường" trước (pattern STRATEGY_GATED)
- Messaging house sau đó inject vào context của Nam/Trang/post_voice_check
  (giống pattern tactical_playbook)

### 2.3. ✅ Cải tiến `ads_generator` (3 gap — đã fix cả 3)
1. `ads_format` (Video/Ảnh chọn ở bước 2) KHÔNG được truyền vào prompt —
   copy gen ra giống nhau bất kể format
2. `build_context` chưa inject `usp_definition` — headline ads lẽ ra phải bám USP
3. Platform cứng trong prompt (Meta/TikTok/Google/Zalo) — chưa đọc wedge
   channels từ synthesis để chỉ gen cho đúng kênh mũi nhọn

### 2.4. ✅ Tái cấu trúc `content_calendar` (CONTENT_CALENDAR_SYSTEM) — chống quá tải

**Vấn đề:** prompt hiện có 9 section bắt buộc trong 1 output → model dễ làm mỏng
từng phần. Đồng thời `content_calendar` đã nhận T4 (synthesis + dynamic pillar mix)
và T5 (tactical_playbook) qua `ContextStrategy.PROFILE_PLUS_CAMPAIGN`, nhưng
**CHƯA nhận archetype block** (trust_building/demand_gen/impulse) — khác với
`funnel_mapper` đã archetype-aware.

**Hướng đã thống nhất:**
1. Rút từ 9 section bắt buộc xuống **5 core**:
   - 1. Tổng quan kỳ
   - 2. Story Arc (4-week table)
   - 3. Pillar breakdown (dùng dynamic pillar mix đã tính sẵn)
   - 4. Weekly grid per channel (gộp luôn Content Format Guide vào đây thay vì
     tách section riêng)
   - 5. Vận hành (rút gọn)
2. **2 section optional** (chỉ xuất hiện nếu có input phù hợp):
   - Năng lực team & phân công — chỉ hiện nếu `profile.team_size` có giá trị
   - AI Content Scoring — optional, không bắt buộc
3. **Bỏ hẳn Repurpose Matrix 1:7** — thay bằng 1 dòng pointer: "Muốn nhân bản
   1 bài thành nhiều phiên bản theo audience khác → dùng skill `content_repurpose`"
4. **Fix gap archetype**: inject ARCHETYPE block (giống cách `funnel_mapper.py`
   dùng `resolve_archetype()` + `format_archetype_block()` từ
   `frameworks/industry_context.py`) vào context của `content_calendar`, để
   weekly grid + pillar mix bám đúng semantic phễu theo archetype (vd
   trust_building → thiên Industry/Personal content; impulse → thiên Offer/Convert).
   Cân nhắc luôn: cho `calc_dynamic_pillar_mix()` đọc thêm archetype (hiện chỉ
   đọc `stage` + `primary_goal`).

**File liên quan:**
- `agents/operational_prompts.py` — `CONTENT_CALENDAR_SYSTEM`
- `agents/operational_skills_config.py` — `ContentCalendarDynamicSkill`,
  `calc_dynamic_pillar_mix()`
- `frameworks/industry_context.py` — `resolve_archetype()`, `format_archetype_block()`
- `agents/funnel_mapper.py` — pattern tham khảo cho archetype injection

### 2.5. ✅ Dọn skill của Nam

**a) Xoá hẳn 2 skill** (pattern giống landing_page/performance_audit — gỡ TaskConfig,
factory, prompt, OPERATIONAL_SYSTEMS, owns_skills, html_report/renderers/llm_router
mapping, handlers refs, docs; GIỮ TaskType enum trong storage/models.py):
- **`comment_mining`** — PROFILE_ONLY, không đọc gì từ T1-T5, tách biệt hoàn toàn
- **`post_visual`** — PROFILE_ONLY + output trùng với section "🎨 Visual Brief"
  đã có sẵn trong `post_write`
- Lưu ý khi xoá: cả 2 đang nằm trong `BV_INJECTED_SKILLS` (`agents/pipeline.py:372`,
  post_visual) — gỡ luôn khỏi set đó. `tests/test_content_pipeline_e2e.py` có
  reference comment_mining/post_visual — sửa test.

**b) Xoá hẳn `social_posts`** — trùng vai với `post_batch` (cùng là bài đăng hữu cơ
batch). Lưu ý: `social_posts` đang nằm trong `CALENDAR_DRIVEN_SKILLS`
(`agents/pipeline.py:391`) và `BV_INJECTED_SKILLS` — gỡ khỏi cả 2 set.
KHÔNG nằm trong `ContentGeneratorPipeline.SUB_SKILLS` (pipeline dùng post_batch)
→ xoá không vỡ pipeline.

**c) Chuyển `content_calendar` + `campaign_brief` sang Max (CMO) cầm:**
- Gỡ 2 skill này khỏi `owns_skills` của Nam → thêm vào `owns_skills` của Max
  (`agents/manager_personas.py`, persona key="cmo")
- Lý do: đây là deliverable tầng kế hoạch — Max cầm để Nam/Trang/Linh đều
  truy cập được output từ session (các skill consume qua
  `session.get_latest_result("content_calendar")` / `CALENDAR_DRIVEN_SKILLS`
  và `PROFILE_PLUS_CAMPAIGN` nên KHÔNG phụ thuộc ai own — chỉ đổi người trigger)
- Cập nhật system_prompt của Nam (bỏ mention calendar/brief ở phần "SKILLS BẠN
  GỌI ĐƯỢC") + system_prompt của Max (thêm 2 skill mới)
- Gỡ `campaign_brief` khỏi owns_skills của Hương (marcon_pr, inactive) nếu muốn
  sạch — hoặc giữ vì persona inactive
- Check `trigger_keywords` của Nam ("lịch đăng", "content calendar") — chuyển
  sang Max hoặc giữ ở Nam để route user về đúng chỗ rồi Nam chỉ sang Max

**owns_skills của Nam sau khi dọn:**
`["content_generator", "post_write", "post_batch", "post_hooks", "post_adapt", "post_voice_check"]`

**d) Soft-gate khi chưa có content_calendar/campaign_brief:**
Nếu user gọi thẳng skill của Nam/Trang (vd `post_batch`, `video_script_gen`,
`ugc_brief`, `video_scripts`) khi `session.results` CHƯA có `content_calendar`
(hoặc `campaign_brief`), context vẫn chạy bình thường (chỉ mỏng hơn — chỉ có
profile + synthesis) — không chặn cứng, nhưng nên thêm 1 dòng gợi ý mềm kiểu:
"Chưa có Content Calendar — chạy với Max trước (`content_calendar`) thì kết quả
sẽ bám đúng kế hoạch hơn. Vẫn muốn chạy luôn không?"
Vị trí thêm: `build_user_msg`/`build_context` của các `CALENDAR_DRIVEN_SKILLS`
(`agents/pipeline.py:391`) hoặc handler trước khi dispatch.

---

## 3. ✅ DONE (2026-06-12) — Làm "8 câu hỏi chiến lược" (sau T1-T3) thành flow phụ thuộc nhau

**Vấn đề hiện tại:**
`bot/handlers.py:4931` (`_generate_strategy_questions`) sinh CẢ 8 câu trong
1 LLM call duy nhất, dựa trên 5 research result — TRƯỚC KHI user trả lời câu
nào. Vì vậy câu 4 (`positioning`) không thể gợi ý dựa trên 3 câu trả lời đầu
(`market_gap`, `target_segment`, `competitor_gap`), và câu 5-6
(`pricing_approach`, `usp_angle`) không thể suy ra từ `positioning` user đã chọn.

8 câu hiện tại (`_STRATEGY_Q_KEYS` / `_STRATEGY_Q_LABELS`,
`bot/handlers.py:4908-4928`):
1. `market_gap` — Market Gap
2. `target_segment` — Target Segment
3. `competitor_gap` — Gap Đối Thủ
4. `positioning` — Định Vị
5. `pricing_approach` — Pricing
6. `usp_angle` — USP Angle
7. `channels` — Kênh Triển Khai
8. `timeline` — Timeline Triển Khai

**Thay đổi muốn làm:**

1. **Đổi label `competitor_gap`**: "Gap Đối Thủ" → "Messaging Gap"
   (sửa `_STRATEGY_Q_LABELS` ở `bot/handlers.py:4922` và `label_map` ở
   `agents/campaign_ideation.py:395`).

2. **Sinh câu hỏi theo lô (batch) thay vì 1 lần cho cả 8:**
   - Batch 1 (giữ nguyên, sinh ngay từ research): `market_gap`,
     `target_segment`, `competitor_gap` (Q1-3).
   - Sau khi user trả lời xong Q1-3 → gọi LLM thêm 1 lần để sinh `positioning`
     (Q4), inject 3 câu trả lời vào prompt → options/gợi ý positioning bám
     theo market_gap + target_segment + messaging_gap đã chọn.
   - Sau khi user trả lời `positioning` (Q4) → gọi LLM thêm 1 lần để sinh
     `pricing_approach` + `usp_angle` (Q5-6), inject câu trả lời positioning
     vào prompt → pricing segment + USP angle phải nhất quán với định vị
     đã chọn.
   - `channels` (Q7) và `timeline` (Q8) giữ nguyên — không phụ thuộc gì.

3. **Implementation:**
   - Sửa `_generate_strategy_questions` (`bot/handlers.py:4931`) thành 3 hàm
     nhỏ hơn (hoặc 1 hàm với tham số `batch`): `_gen_q1_3()`, `_gen_q4_positioning(answers)`,
     `_gen_q5_6_pricing_usp(answers)`.
   - Sửa `_ask_next_strategy_question` (`bot/handlers.py:5075`) — sau khi lưu
     answer cho `competitor_gap` (Q3) thì gọi `_gen_q4_positioning` và append
     vào `_strategy_questions`; sau khi lưu answer cho `positioning` (Q4) thì
     gọi `_gen_q5_6_pricing_usp` và append.
   - Giữ fallback (`_default_strategy_questions_fallback`) cho từng batch nếu
     LLM call fail — hiện tại fallback đã có sẵn full 8 câu, chỉ cần tách theo
     batch tương ứng.

**Trade-off:** thêm 2 LLM call giữa flow (latency tăng nhẹ ngay sau khi user
trả lời Q3 và Q4), nhưng đổi lại Q4-6 thực sự "ăn theo" lựa chọn trước —
chiến lược nhất quán hơn (positioning suy từ gap analysis, pricing + USP
angle suy từ positioning).

**Đã làm:**
- Label `competitor_gap`: "Gap Đối Thủ" → "Messaging Gap" trong
  `_STRATEGY_Q_LABELS` (`bot/handlers.py`), `label_map` của
  `extract_campaigns_from_synthesis` (`agents/campaign_ideation.py`), và
  `_format_strategy_answers`.
- `_gen_q4_positioning(session, answers)` (`bot/handlers.py`) — LLM call mới,
  inject market_gap/target_segment/competitor_gap đã chọn + research excerpts
  → regenerate câu positioning với options bám 3 hướng đã chọn.
- `_gen_q5_6_pricing_usp(session, answers)` (`bot/handlers.py`) — LLM call mới,
  inject 4 câu đã chọn (gồm positioning) + psychology_pricing/usp_definition +
  pricing segment library → regenerate pricing_approach (options vẫn lấy
  nguyên văn từ pricing segment library, nhất quán với positioning) +
  usp_angle.
- `_ask_next_strategy_question` (`bot/handlers.py`) — trong nhánh "pop next
  question": nếu `questions[0]["key"] == "positioning"` → gọi
  `_gen_q4_positioning` và replace; nếu `== "pricing_approach"` → gọi
  `_gen_q5_6_pricing_usp` và replace cả pricing_approach + usp_angle. Cả 2 có
  fallback: nếu LLM fail (`None`) → giữ nguyên placeholder từ
  `_generate_strategy_questions` (8 câu baseline) như trước.
- `channels` (Q7) và `timeline` (Q8) giữ nguyên, không phụ thuộc.

---

## 4. ✅ DONE (2026-06-12) — Report sau T4-T5 chỉ gửi 2 tab (không gửi lại T1-T3)

**Vấn đề:** `_run_strategy_plan` (`bot/handlers.py:5189`) sau khi chạy xong
T4 Synthesis + T5 Tactical Playbook, build lại HTML report "đầy đủ A→Z" gồm
8 tab (T1-T3 + T4 + T5) — nhưng T1-T3 đã được gửi 1 lần ở report cuối phase
research rồi → user nhận trùng lặp.

**Đã fix:** Lọc `PIPELINE_DEF` theo `stage_def.phase == "synthesis"` → chỉ
build report 2 tab (T4 Synthesis + T5 Tactical Playbook). Caption đổi từ
"Báo cáo đầy đủ A→Z" → "Kế hoạch chiến lược + Tactical Playbook (T4-T5)".

---

## 5. ✅ DONE (2026-06-12) — Hỏi Budget/Team TRƯỚC khi đề xuất campaign (sau T4-T5)

**Vấn đề hiện tại:**
`_show_extracted_campaigns` (`bot/handlers.py:5296`) gọi
`extract_campaigns_from_synthesis` ngay sau khi confirm strategy — trích
2-3 campaign từ Roadmap mà KHÔNG biết Budget/Team của user. Card hiện tại
ghi chú "💰 Budget / 👥 Team / 📆 Ngày bắt đầu / 🎟 % giảm — sếp quyết ở bước
sau" (`bot/handlers.py:5348`) — nghĩa là campaign đề xuất có thể quá tải so
với quy mô thực tế (vd campaign cần outsource UGC + đa kênh nhưng user chỉ
có 1 người làm content).

**Thay đổi muốn làm:**
1. Trước khi gọi `extract_campaigns_from_synthesis`, hỏi user 2 câu:
   💰 Budget marketing/tháng (hoặc cho campaign này) + 👥 Team size (số người,
   vai trò — vd "1 content + thuê ngoài video").
   - Nếu profile đã có `monthly_marketing_budget`/`team_size`
     (`agents/discovery.py` — xem `bot/handlers.py:3770-3773`) thì show lại
     cho user confirm/sửa thay vì hỏi từ đầu.
2. Inject Budget/Team vào prompt của `extract_campaigns_from_synthesis`
   (`agents/campaign_ideation.py:373`) — campaign đề xuất phải fit quy mô
   (số kênh, tần suất, có cần outsource hay không).
3. Sau khi show campaign(s) fit nhất, thêm dòng: *"Đây là campaign Max thấy
   phù hợp với quy mô hiện tại của sếp. Nếu sếp muốn xem thêm hướng khác
   (tham vọng hơn / cần thêm resource), bấm nút bên dưới"* — thêm nút
   "🔍 Xem thêm phương án khác" trong cùng bước chọn campaign (không phải
   bước riêng).
   - Phương án "khác" có thể là campaign tham vọng hơn mà
     `extract_campaigns_from_synthesis` đã trích nhưng bị filter ra vì
     vượt quy mô — giữ lại trong `_extracted_campaigns` (không discard),
     chỉ ẩn ban đầu.

**Đã làm:**
- `_ask_budget_team_before_campaigns` (`bot/handlers.py`) — gọi trước
  `_show_extracted_campaigns` từ cả 3 entry point (`strategy_confirm`,
  campaign_brief direct test, campaign_brief task dispatch). Nếu profile đã
  có `monthly_marketing_budget` + `team_size` → show lại cho confirm
  (`budget_team_confirm`) / sửa (`budget_team_edit`); nếu chưa có → hỏi free
  text 1 lượt (`_awaiting_budget_team` → `_handle_budget_team_text`). Lưu kết
  quả vào `pending_intake["_budget_team_context"]`, chỉ hỏi 1 lần/session.
- `extract_campaigns_from_synthesis` (`agents/campaign_ideation.py`) — inject
  block "## Ngân sách & Team hiện tại" vào prompt; `EXTRACT_CAMPAIGNS_SYSTEM`
  yêu cầu LLM gắn `scale: "fit"` (khả thi với quy mô) hoặc `scale: "stretch"`
  (tham vọng hơn, tối đa 1 campaign).
- `_show_extracted_campaigns` (`bot/handlers.py`) — campaign `scale: "stretch"`
  bị ẩn ban đầu; note text đổi thành "Đây là campaign Max thấy phù hợp với quy
  mô hiện tại..."; nút mới "🔍 Xem thêm phương án khác (tham vọng hơn)"
  (`extracted_campaign_show_more`) re-render từ `_extracted_campaigns` đã cache
  (không gọi lại LLM) hiện cả campaign stretch. Card note "💰 Budget / 👥 Team"
  đã bỏ (đã hỏi ở bước trước).

---

## 6. ✅ DONE (2026-06-12) — Đổi 3 câu offer-preferences thành 1 bước chọn "gói ưu đãi" (package)

**Vấn đề hiện tại:**
`_ask_offer_preferences` (`bot/handlers.py:7632`) hỏi 3 câu mở về offer:
1️⃣ "mồi" khách (đã có `generate_bait_hint` — đặc thù theo ngành, OK)
2️⃣ "cho đi tới đâu mà vẫn lời" — ví dụ hardcode: "giảm tối đa 20%", "tặng được
   món < 15k", "miễn phí 1 buổi trải nghiệm" (`bot/handlers.py:7649`)
3️⃣ "bắt buộc phải giữ" — ví dụ hardcode: "giá gốc vẫn hiển thị trên menu",
   "không phá giá thị trường", "không tặng tiền mặt" (`bot/handlers.py:7651`)

Ví dụ câu 2-3 nghiêng retail/F&B/dịch vụ ("menu", "món", "buổi trải nghiệm",
"<15k") — KHÔNG hợp với ngành B2B/SaaS/giáo dục/real estate (chênh lệch quy mô
tiền: vài chục nghìn vs vài tỷ). 3 câu mở trừu tượng cũng dễ khiến user bấm
"để em tự đề xuất" → mất input thật.

**Quyết định đã chốt — thay 3 câu mở bằng 1 bước chọn gói:**

Max sinh 3 "gói ưu đãi" trọn (mechanism + mức cho đi + constraint trong 1 gói,
đặc thù theo ngành + `pricing_approach` đã chốt ở 8 câu chiến lược + Budget/Team
từ backlog #5), show dạng nút bấm — user chọn 1 hoặc bấm "✏️ Tự định nghĩa" để
gõ tay như flow cũ. Xem ví dụ minh hoạ (spa/clinic, agency B2B, giáo dục,
real estate) đã thảo luận trong session 2026-06-12.

**KHÔNG thêm câu hỏi mới** (vd margin/giá vốn thật) — lý do: mục tiêu là giảm
tải, không tăng. Capacity vận hành lấy từ Budget/Team (backlog #5, đã hỏi
trước khi đề xuất campaign). Margin/giá vốn thật không hỏi — mỗi gói ghi
"mức cho đi" dạng tương đối (% hoặc trần) để founder tự đối chiếu và sửa qua
"✏️ Tự định nghĩa" nếu lệch.

**Implementation:**
- Thêm hàm sinh package (vd `propose_offer_packages(session, campaign)` trong
  `agents/campaign_ideation.py`, cạnh `propose_offer_levers` hiện có) — dùng
  `_build_industry_levers_context` (`agents/campaign_ideation.py:489`) +
  inject `pricing_approach` (từ `_strategy_answers`) + Budget/Team (backlog #5).
  Output 3 gói, mỗi gói có: `name`, `mechanism`, `give_away` (mức tương đối),
  `constraint`.
- Sửa `_ask_offer_preferences` (`bot/handlers.py:7632`) — thay message 3 câu
  bằng card hiển thị 3 gói + nút chọn (`1️⃣`/`2️⃣`/`3️⃣`/`✏️ Tự định nghĩa`).
- Sửa `_handle_offer_prefs_text` / `propose_offer_levers`
  (`agents/campaign_ideation.py:729`) — nhánh "✏️ Tự định nghĩa" giữ nguyên
  flow 3-câu cũ làm fallback; nhánh chọn gói đi thẳng vào
  `format_levers_card` với gói đã chọn.
- Giữ `generate_bait_hint` làm nguồn data cho mechanism của các gói (không bỏ).

**Đã làm:**
- `propose_offer_packages` + `format_packages_card` + `PROPOSE_PACKAGES_SYSTEM`
  mới trong `agents/campaign_ideation.py` — sinh 3 gói (nhẹ/vừa/mạnh) dùng
  `_build_industry_levers_context` + `pricing_approach` (từ
  `_strategy_answers`) + `_budget_team_context`/profile (BACKLOG #5).
- `_ask_offer_preferences` (`bot/handlers.py`) — rewrite: gọi
  `propose_offer_packages`, show card 3 gói + nút `1️⃣/2️⃣/3️⃣` + "✏️ Tự định
  nghĩa". Logic 3-câu cũ giữ nguyên trong `_ask_offer_preferences_custom` —
  dùng làm fallback khi propose lỗi hoặc user bấm "✏️ Tự định nghĩa".
- Callback `offer_package_pick_{i}` — set `_offer_prefs_raw` từ gói đã chọn
  (mechanism + give_away + constraint) → gọi thẳng `_show_offer_lever_selection`
  (4 levers cụ thể TRONG khuôn khổ gói, không hỏi lại). Callback
  `offer_package_custom` → `_ask_offer_preferences_custom` (flow 3-câu cũ).
- `generate_bait_hint` giữ nguyên, không dùng trực tiếp trong flow mới nhưng
  vẫn dùng trong `_ask_offer_preferences_custom` (câu 1️⃣ của fallback).

**Phụ thuộc:** nên làm SAU backlog #5 (Budget/Team) vì cần info đó để gói
phù hợp quy mô.

---

## 7. ✅ DONE (2026-06-12) — Content Calendar timeline: hỏi "Thời lượng" thay vì "Ngày bắt đầu/Ngày kết thúc"

**Vấn đề cũ:** `COMMON_FINALIZE_FIELDS` (`agents/campaign_ideation.py`) hỏi 2
field "Ngày bắt đầu" + "Ngày kết thúc" — Timeline 8/8 ("Sprint 90 ngày" / "6
tháng"...) là độ dài TOÀN ROADMAP (chứa nhiều campaign), còn campaign đang
finalize chỉ là 1 slice trong đó (`duration_suggestion`, vd "4-6 tuần") —
không thể tái dùng trực tiếp Timeline 8/8 cho 2 field này.

**Đã chốt + fix:** Ngày bắt đầu có default tốt (hôm nay) → không hỏi. Thời
lượng có signal thật từ founder (test nhanh 4 tuần vs full 6 tuần) → hỏi 1
field duy nhất **"Thời lượng campaign"** (gợi ý "4 tuần / 6 tuần / 2 tháng",
kèm gợi ý AI = `duration_suggestion` của campaign đã chọn). `merge_to_brief_fields`
tự parse thời lượng (`_parse_duration_days`, default 28 ngày nếu không parse
được) → tính `start_date = hôm nay`, `end_date = start + duration`.

**Đã sửa:**
- `COMMON_FINALIZE_FIELDS` → 1 field "Thời lượng campaign"
- `_parse_duration_days()` — parse "X tuần/tháng/ngày" → số ngày
- `format_dynamic_finalize_form` — hiển thị gợi ý AI theo `duration_suggestion`
- `merge_to_brief_fields` — tự tính start/end date từ thời lượng
- `_haiku_extract_finalize` system prompt (`bot/handlers.py`) — map "X tuần/tháng"
  vào field "Thời lượng campaign" thay vì NGÀY BẮT ĐẦU/KẾT THÚC
- Các card note "Budget/Team/Ngày bắt đầu/% giảm — quyết ở bước sau" → đổi
  "Ngày bắt đầu" thành "Thời lượng"

---

## 8. ✅ DONE (2026-06-12) — Content Calendar "Kênh": tái dùng từ 8/8 chiến lược / campaign đã chọn, không hỏi lại

**Vấn đề cũ:** `content_calendar` intake có field `"channels"` ("Kênh", vd
"TikTok + Facebook + Zalo OA") nhưng thông tin này đã được chốt ở câu 7/8
chiến lược (`_strategy_answers["channels"]` — "Kênh Triển Khai") và/hoặc nằm
trong `channels` của campaign đã chọn (`_chosen_campaign`) — hỏi lại là hỏi
trùng.

**Đã sửa:** Trong `_send_single_shot_form` (`bot/handlers.py`), sau bước
Smart Pre-fill, nếu `task_name == "content_calendar"` và `"channels"` chưa
được prefill từ profile → tự lấy `_strategy_answers["channels"]`, nếu rỗng
thì fallback `_chosen_campaign["channels"]`, rồi prefill vào `prefilled` +
`pending_intake["channels"]` → field "Kênh" không hiện lại trong form.

---

## 9. ✅ DONE (2026-06-12) — "Vớt khách chưa convert" theo từng campaign — KHÔNG tạo retention_strategy riêng cho campaign

**Câu hỏi gốc:** Có nên có `retention_strategy` riêng cho từng campaign,
mục đích tối ưu ROI + vớt khách đã hứng thú với campaign đó nhưng chưa
chuyển đổi?

**Đã chốt — KHÔNG tạo skill mới:**
- `retention_strategy` hiện tại là hệ thống TOÀN BUSINESS (3 giai đoạn kinh
  doanh + 4 nhóm khách dùng chung cho mọi campaign) — tách riêng theo từng
  campaign sẽ vụn data (1 khách có thể đến từ nhiều campaign).
- Mục tiêu "vớt khách đã hứng thú campaign X nhưng chưa convert" **đã có
  sẵn** ở bullet 2 của `♻️ Retention` baseline (`agents/campaign_execution.py`
  → `_RETENTION_BASELINE`) — gợi ý dùng `email_zalo_sequence` cho "lead chưa
  convert". Hiện tại bullet này CHỈ LÀ TEXT GỢI Ý trong Execution Plan,
  chưa có action nào chạy thật.

**Hướng làm (chưa implement):**
- Thêm 1 action sau Execution Plan (hoặc sau khi campaign chạy 1-2 tuần):
  "🎯 Vớt khách chưa convert — [campaign_name]"
- Action này chạy `email_zalo_sequence` với intake **prefill từ campaign**:
  - `key_offer`/lever đã chốt của campaign → làm offer trong chuỗi nurture
  - Segment = đúng nhóm "đã vào BOFU (Convert stage trong Funnel Map) nhưng
    chưa mua" — lấy từ `_chosen_campaign`/funnel_map context
  - `channel_preference` = channels của campaign (Zalo/Email)
- Output: 1 chuỗi nurture 3-7 tin tập trung 100% vào nhóm "warm nhưng chưa
  chốt" của riêng campaign này — không cần dựng lại retention_strategy
  toàn business.

**Phụ thuộc:** không phụ thuộc backlog #5/#6 (Budget/Team, offer packages) —
có thể làm độc lập.

**Đã làm:**
- Nút mới "🎯 Vớt khách chưa convert" trong `FUNNEL_APPROVE_KEYBOARD`
  (`bot/keyboards.py`), hiện ngay sau khi gửi Funnel Map + Execution Plan
  (cùng bước với "✅ Duyệt kế hoạch").
- Callback `rescue_nonconvert` → `_rescue_nonconvert_action` (`bot/handlers.py`)
  — chạy thẳng `email_zalo_sequence` (không hỏi form, bypass qua
  `_handle_ops_intake_reply(..., "ok")`):
  - `audience_segment` = mô tả stage BOFU (Convert) lấy từ
    `_funnel_map_json` (`bofu.goal` + `stage_labels.bofu` + `bofu.cta`),
    fallback "Khách đã quan tâm/inbox campaign ... nhưng chưa chuyển đổi".
  - `sequence_goal` = "Vớt khách chưa convert từ campaign ... — nurture quay
    lại với offer: {key_offer}" (key_offer từ `_chosen_campaign`).
  - `channel_preference` = channels của campaign, fallback "Zalo OA + Email".
- Không tạo skill `retention_strategy` riêng cho campaign — giữ nguyên hệ
  thống retention toàn business như đã chốt.

---

## 10. ✅ DONE (2026-06-12) — Loạt fix flow Content Calendar → Sản xuất Content

Tất cả sub-items (a)-(g) đã hoàn thành — xem chi tiết "Đã làm" trong từng mục bên dưới.

### (a) ✅ ĐÃ FIX — Cadence mỗi kênh bị lệch số tự bịa
`_handle_calendar_cadence_text` (`bot/handlers.py:7427`) trước đây chỉ
`re.match` đầu MỖI DÒNG sau `split("\n")`, nhưng ví dụ bot đưa ra lại gợi ý
gõ tất cả trên 1 dòng nối bằng " · " (`_prompt_calendar_cadence` line 7418)
→ user gõ theo ví dụ "Facebook: 7 · TikTok: 4 · Zalo: 7" thì CHỈ Facebook
được parse, TikTok/Zalo bị mất → LLM tự bịa 6 và 3.
**Đã fix:** đổi sang `re.finditer` tìm mọi cặp "Kênh: N" bất kể nối bằng
dòng mới hay " · "/",". Đã commit + push.

### (b) ✅ DONE (2026-06-12) — TikTok: hỏi thêm "tuyến content" (theo 15 ngành) + "thuê UGC ngoài?"
Trong `_prompt_calendar_cadence` (`bot/handlers.py:7398`), sau khi user chốt
cadence, nếu `channels` có TikTok → hỏi thêm 2 câu (gộp vào CÙNG 1 bước, không
tách thêm round-trip):
- "Tuyến content TikTok muốn tập trung?" — gợi ý sẵn theo industry (dùng
  `agents/social_industry_profiles.py` làm nguồn — file này đã có
  channel/giờ vàng theo 15 ngành, cần bổ sung thêm "content lines" gợi ý
  theo ngành nếu chưa có)
- "Có thuê UGC ngoài không?" (Có/Không + số lượng nếu có)
Câu trả lời lưu vào `pending_intake` để CONTENT_CALENDAR_SYSTEM
(`agents/operational_prompts.py:98`) dùng define topic/angle cho section
TikTok, và để `ugc_brief` skill dùng sau nếu cần.

**Đã làm:**
- `agents/social_industry_profiles.py`: thêm dict `TIKTOK_CONTENT_LINES`
  (14 ngành, mỗi ngành 3-4 tuyến content TikTok đặc thù — food porn/BTS/UGC
  cho fnb, before-after/routine cho health_beauty, v.v.) + fallback
  `TIKTOK_CONTENT_LINES_GENERIC` + helper `get_tiktok_content_lines(industry)`.
- `bot/handlers.py:_prompt_calendar_cadence` — nếu `channels` chứa "TikTok"
  (case-insensitive), nối thêm vào CÙNG message: gợi ý tuyến theo ngành (từ
  `get_tiktok_content_lines`) + câu hỏi "Tuyến content TikTok muốn tập
  trung?" + "Có thuê UGC ngoài không?", kèm format gợi ý
  `Tuyến: ...` / `UGC: ...`.
- `bot/handlers.py:_handle_calendar_cadence_text` — thêm regex parse
  `Tuyến[...]:` và `UGC[...]:` từ câu trả lời, lưu vào
  `pending_intake["tiktok_content_lines"]` / `pending_intake["ugc_outsource"]`
  (không bắt buộc — nếu user không trả lời thì bỏ qua, không chặn flow).
- `agents/operational_skills_config.py:ContentCalendarDynamicSkill.build_user_msg`
  — inject 2 field trên vào context cho `CONTENT_CALENDAR_SYSTEM` (section
  "TIKTOK — TUYẾN CONTENT DO SẾP CHỐT") để LLM bám tuyến đã chọn cho section
  TikTok của Calendar.

### (c) ✅ DONE (2026-06-12) — Bỏ field ngày không liên quan trong content_calendar output
User feedback: phần "ngày" (Story Arc date range "Tuần 1 (15/06–21/06)"...)
hiển thị trong file Excel "chả liên quan gì". Cần kiểm tra lại: các date
range này tự tính từ `start_date = hôm nay` + `duration` (xem backlog #7,
`merge_to_brief_fields`). Cần xác minh: (1) date range này có đang được hiển
thị đúng & hữu ích không, hay (2) nó gây nhiễu vì user chỉ cần biết
"Tuần 1/2/3/4" mà không cần ngày cụ thể (vì lịch thật sự sẽ dịch theo ngày
campaign chạy thực tế, không phải ngày tạo brief). Có thể bỏ cột/date range
này khỏi Story Arc, chỉ giữ "Tuần X".

**Đã làm:** Xác nhận nguồn: `merge_to_brief_fields` (agents/campaign_ideation.py)
tính `start_date = date.today()` (ngày TẠO BRIEF, không phải ngày campaign
chạy thật) + `end_date = start + duration_days`, rồi nhúng "**Ngày bắt đầu:**
.../**Ngày kết thúc:** ..." vào field `duration` của brief — field này được
đưa vào context cho campaign_brief → content_calendar, khiến LLM tự suy ra
"Tuần 1 (15/06–21/06)" dựa trên ngày tạo brief (sai lệch với ngày chạy thực
tế). Đã xoá hoàn toàn 2 dòng "Ngày bắt đầu"/"Ngày kết thúc" khỏi field
`duration` trong `merge_to_brief_fields` (chỉ còn giữ "Thời lượng: ..." +
gợi ý AI), và xoá luôn phần tính `start`/`end`/`start_date`/`end_date`
(dùng `date`/`timedelta`, không còn cần). Story Arc trong content_calendar
output giờ chỉ còn "Tuần 1/2/3/4" (đã đúng từ template gốc, không có cột
ngày), không còn bị nhiễu bởi ngày tạo brief.

### (d) ✅ DONE (2026-06-12) — Đảo flow: Brand Voice check TRƯỚC "Bài mẫu đầu tiên", rồi bỏ luôn bước "Bài mẫu"
Hiện tại (`_start_tone_calibration`, `bot/handlers.py:8436`):
1. Nếu chưa có Brand Voice → hỏi setup BV trước (gate đã đúng thứ tự)
2. Sau đó LUÔN gen "🎨 Kiểm tra Tone — Bài mẫu đầu tiên" (1 bài sample,
   `generate_sample_post`) → user duyệt/chỉnh tone qua `TONE_CHECK_KEYBOARD`

User muốn: bỏ HẲN bước "Bài mẫu đầu tiên" (tone calibration loop). Sau khi
Brand Voice đã có (hoặc vừa setup xong) → hỏi luôn "Sếp muốn gen content nền
tảng nào trước?" (Facebook/TikTok/Zalo...) → dùng Brand Voice đã có để viết
content cho nền tảng đó luôn, không cần sample-post-to-check-tone riêng.
→ Cần thay `_start_tone_calibration` bằng 1 prompt chọn platform, bỏ
`generate_sample_post` + `TONE_CHECK_KEYBOARD`/`tone_calibration` state
(hoặc giữ lại reject/feedback path cho lần sau nếu cần, nhưng KHÔNG block
flow chính bằng sample post).

**Đã làm:** Viết lại `_start_tone_calibration` (`bot/handlers.py:8874`):
- Giữ nguyên Brand Voice gate (đúng thứ tự — hỏi BV trước nếu chưa có).
- Sau khi BV sẵn sàng: BỎ HẲN bước gen sample post (`generate_sample_post`)
  + `TONE_CHECK_KEYBOARD` + state `checking_tone`. Thay vào đó: parse
  calendar → gán POST-XXX ID ngay (`parse_calendar_to_posts`, set
  `tone_calibration = {"stage": "done"}`), gửi list post ID, rồi hiện luôn
  menu sản xuất content (`CALENDAR_TO_CONTENT_GEN_KEYBOARD`) — đây chính là
  bước "platform/loại content nào trước?" (kết hợp với #10g bên dưới để hỏi
  rõ loại nội dung).
- `_handle_tone_feedback`/`_tone_lock_and_apply`/`_handle_tone_callback`
  (tone_approve/reject/skip) GIỮ NGUYÊN trong code (không xoá) như backlog
  cho phép, nhưng KHÔNG còn được trigger từ flow chính vì
  `TONE_CHECK_KEYBOARD` không còn được gửi đi.

### (e) ✅ DONE (2026-06-12) — Bỏ 4 câu hỏi trong "✅ ✍️ Sản Xuất Nội Dung" (content_generator)
`agents/task_registry.py:230-234` — `content_generator.intake_fields` đang
có 4 field muốn bỏ:
- `video_type` ("Video type tuần này (UGC/EGC/FGC/mix)?")
- `fgc_channel_mode` ("Nếu có FGC: kênh riêng hay kết hợp brand?")
- `ugc_outsource` ("Có thuê creator ngoài làm UGC không?")
- `tone_note` ("Tone note đặc biệt?")
→ Xoá 4 field này khỏi `intake_fields`. Lưu ý: `ugc_outsource` có thể vẫn
cần — nếu (b) thêm câu "thuê UGC ngoài?" ở bước TikTok cadence rồi, thì
field này ở đây là TRÙNG → xoá ở content_generator, giữ ở (b). Kiểm tra
`ContentGeneratorPipeline` xem các field này có được dùng để branch logic
không trước khi xoá (tránh lỗi field-not-found).

**Đã làm:**
- `agents/task_registry.py` — xoá 4 field `video_type`, `fgc_channel_mode`,
  `ugc_outsource`, `tone_note` khỏi `content_generator.intake_fields`
  (giờ chỉ còn `weeks`, `scope`, `highlight_angles`, `ads_usp`).
- `agents/operational_skills_config.py:ContentGeneratorPipeline._prefill_intake`
  — cập nhật theo: `creator_type` mặc định "ugc" (không còn derive từ
  `video_type` — framework động ở (f) đã tự quyết cấu trúc kịch bản theo
  tuyến content, không cần phân loại creator trước); `creator_types` (cho
  `ugc_brief`) vẫn đọc `pi.get("ugc_outsource")` — giờ field này lấy từ câu
  hỏi TikTok ở bước calendar cadence (#10b) nếu có, KHÔNG hỏi lại, tránh
  trùng lặp. `fgc_channel_mode` không còn được set → `VideoScriptsSkill`
  (skill khác, "video_scripts" standalone) tự fallback nhánh "kết hợp brand"
  mặc định, không lỗi field-not-found vì dùng `.get()`.

### (f) ✅ DONE (2026-06-12) — video_script_gen: cấu trúc 13-cột cứng (Hook/Problem/Solution/
### Proof/CTA theo PAS) → thay theo "tuyến content" đã chọn ở (b)
`VIDEO_SCRIPT_GEN_SYSTEM` (`agents/operational_prompts.py:1369-1426`) ép mọi
video vào khung 5-beat PAS cố định (Hook 3s/Problem 10s/Solution 20s/Proof
10s/CTA 7s) — không phù hợp với tuyến content khác (vd: storytime, behind-
the-scenes, day-in-life, listicle... mỗi tuyến có nhịp khác PAS). Cần làm
cấu trúc cột ĐỘNG theo tuyến content của slot đó (lấy từ (b) hoặc từ Hook
angle/Pillar đã gán trong Calendar) — PAS chỉ là 1 trong nhiều framework
khả dụng (xem `agents/content_suite_prompts.py:344-352` đã có sẵn 5
frameworks: PAS/BAB/AIDA/FAB/Star-Story — video script nên theo đúng
framework đã gán cho slot đó trong Calendar, không hard-code PAS).

**Đã làm:** Viết lại toàn bộ `VIDEO_SCRIPT_GEN_SYSTEM`
(`agents/operational_prompts.py:1369+`):
- Thêm bảng 7 FRAMEWORK với nhịp beat + timing riêng: PAS, BAB, AIDA, FAB,
  Star-Story (từ `content_suite_prompts.py`) + 2 framework mới đặc thù video
  ngắn: Storytime/Day-in-life, Listicle/Tips.
- BƯỚC 1: LLM chọn framework match nhất cho TỪNG slot dựa trên "tuyến content"
  (từ section TIKTOK — TUYẾN CONTENT DO SẾP CHỐT của (b)) hoặc Hook
  angle/Pillar/Funnel trong Calendar — không ép PAS, đa dạng framework nếu
  ≥3 video.
- BƯỚC 2: viết lời thoại thật cho từng beat của framework đã chọn, kèm timing.
- Table output đổi từ 13 cột cứng (Hook/Problem/Solution/Proof/CTA riêng) →
  8 cột: Version | Creator Type | Platform | Framework | Beat Breakdown (kèm
  timing) | Visual Direction | Caption Hook + Hashtags | Ghi chú — cột "Beat
  Breakdown" chứa số beat ĐỘNG tùy framework (không cố định 5), mỗi beat ghi
  "Tên beat Xs: lời thoại" nối bằng " / ". Giữ nguyên rule "1 bảng duy nhất"
  để Excel extraction không bị lỗi (không có hardcode tên cột nào ở
  bot/excel_reader.py hay bot/renderers.py phụ thuộc cấu trúc cũ, nên đổi an
  toàn).

### (g) ✅ DONE (2026-06-12) — Sau Content Calendar, không tự cascade chạy hết content_generator
(post + video script + UGC brief + ads cùng lúc) — chỉ chạy phần user chọn
`content_generator` (`agents/task_registry.py:219-236`, skill
`ContentGeneratorPipeline`) mô tả "Sản xuất toàn bộ content package: bài
đăng + video script + UGC brief + ads — output Excel" — 1 lần chạy ra CẢ 4
loại nội dung. User muốn: chỉ gửi/chạy đúng loại nội dung user yêu cầu (vd
chỉ "bài đăng Facebook tuần 1"), không tự động kèm video script/UGC
brief/ads nếu user không hỏi tới. Cần xem lại `ContentGeneratorPipeline` để
tách theo scope/loại nội dung user chọn, hoặc thêm bước hỏi "sếp cần loại
nào: bài đăng / video script / UGC brief / ads / tất cả?" trước khi chạy.

**Đã làm:**
- `bot/keyboards.py` — thêm `CONTENT_TYPE_SCOPE_KEYBOARD` (5 nút: 📝 Bài
  đăng / 🎬 Video Script / 🤝 UGC Brief / 📢 Ads Copy / 📦 Tất cả).
- `bot/handlers.py:_start_content_generation` — nếu chưa có
  `pending_intake["_content_gen_types"]`, lưu `_content_gen_mode`
  (weekly/full) rồi hiện `CONTENT_TYPE_SCOPE_KEYBOARD` và DỪNG (không chạy
  gì cả) — áp dụng cho MỌI entry point (calendar approve, Nam mode, BV-resume
  weekly).
- Callback mới `ctype_*` (`bot/handlers.py`, trước nhóm "Calendar → Content
  Gen chain") — set `_content_gen_types = [skill]` (hoặc full
  `ContentGeneratorPipeline.SUB_SKILLS` nếu chọn "Tất cả"), rồi gọi lại
  `_start_content_generation` với cờ weekly đã lưu.
- `agents/operational_skills_config.py:ContentGeneratorPipeline.run_pipeline`
  — chỉ chạy sub-skill nằm trong `_content_gen_types` (nếu có); không có →
  chạy hết (fallback cho path cũ/test). `MULTI_OUTPUT:...` vẫn hoạt động
  đúng với danh sách rút gọn (1 sub-skill) vì `_send_ops_result` dispatch
  theo danh sách động, không hardcode 4 loại.
- `_continue_after_brand_voice` (resume weekly sau khi setup BV) đổi từ gọi
  `_prompt_week_selection` trực tiếp → gọi `_start_content_generation(weekly=True)`
  để đảm bảo luôn đi qua bước chọn loại nội dung.

---
