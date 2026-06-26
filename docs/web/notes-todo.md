# NOTES-TODO (web) — ghi chú chờ làm theo lô

> Quy ước: "note" = chỉ ghi vào đây, KHÔNG tự sửa/push code. Chỉ code khi founder nói "làm các note".

## ✅ TRẠNG THÁI (dọn 2026-06-26 — founder "làm các note")
- **ĐÃ LÀM:** N-01, N-02, N-03, N-03b, N-04, N-05, N-06, N-08, N-09, N-10, N-11, N-12, N-13, N-14,
  N-15, N-16, N-17 ·
  N-07 (✅ đủ: timeout + regen + badge playbook) ·
  N-18 (declutter — đã gỡ leftover; **rebuild 4-tuyến đầy đủ còn để slice riêng**).
- **N-03/N-03b/N-15 ĐÃ XỬ (Lô F):** viết lại Research T1-T3 WEB-OWNED (`research_web`) — 5 skill prompt
  riêng khoá scope (competitor không ICP/JTBD; research kết so-what, không roadmap) + chống bịa số
  (kèm nguồn/'(ước tính)'; thiếu data → '_chưa đủ dữ liệu công khai_'). `_execute` bỏ pipeline agents/.
  ⚠️ CẦN TEST THẬT trên Railway (sandbox không chạy LLM được).
- **CÒN LẠI (slice riêng):** rebuild 4-tuyến nội dung đầy đủ (N-18 sâu) · regen/badge playbook (N-07b).

## 🔴 Bug đang mở
- **[N-01] "Đặt hiện hành" version tạo bản MỚI thay vì repoint.**
  Ở trang đọc/sửa doc (vd Market_research), bấm "Đặt hiện hành" cho v1/v2 thì thay vì
  trỏ hiện-hành về v1/v2, hệ thống **đẻ ra v3/v4** (nội dung thật vẫn là v1/v2). Đúng phải:
  set version đã chọn làm current, KHÔNG sinh version mới. (Kiểm tra logic set-current vs patch.)
- **[N-02] Giao diện bị "bóp" khi chạy lại.**
  Khi chạy lại (re-run), layout trang đọc doc — panel "Lịch sử version" bên phải — bị bóp/vỡ.
  (CSS/layout của doc reader khi có panel version history.)
- **[N-03] Competitor "độn" nội dung ICP/JTBD (scope-drift, không phải lỗi web).**
  Trang competitor hiện section "Bối cảnh, ICP và JTBD (giả định)" — vốn thuộc Customer Insight.
  Đã rà: web map task→skill ĐÚNG cả 6 trang; CompetitorSkill dùng đúng COMPETITOR_SYSTEM (không
  yêu cầu ICP/JTBD); competitor chạy TRƯỚC customer nên không phải copy. → Gốc: doanh nghiệp ngách
  (QC/sourcing cho DN Mỹ) khó tìm đối thủ công khai → grounding mỏng → LLM ĐỘN bằng ICP/JTBD tự suy
  từ target_customer để lấp chỗ trống (scope drift). Rủi ro hệ thống của pipeline `agents/` (mỗi
  agent thấy hồ sơ + kết quả trước → dễ lấn mảng kế cận khi data mỏng).
  → KHÔNG sửa sạch được khi research còn chạy qua `agents/` (reference-only). Dứt điểm = rebuild
  research WEB-OWNED, khoá cứng scope từng skill (thiếu data thì ghi "_chưa đủ dữ liệu công khai_",
  KHÔNG độn mảng khác). Gộp vào đợt rebuild research.
  - **N-03b (cùng họ): Customer Insight (và competitor) "độn" ROADMAP.** Output có "6. Strategic
    Implications → 🟢 Quick wins / 🟡 Medium term / 🔴 Risks" — VI PHẠM chính luật prompt
    (`prompts.py:380` + `pipeline.py:173`: research kết bằng so-what, KHÔNG xếp Quick-win/Medium/
    Long-term — việc đó của Synthesis T4/Tactical T5). Nguyên nhân: LLM bỏ qua lệnh phủ định + đoạn
    luật cấm lại IN MẪU 🟢🟡🔴 nên model bắt chước. → Khoá scope khi rebuild research web-owned;
    research dừng ở insight, roadmap chỉ ở Synthesis.

- **[N-04] Bản đồ định vị lòi JSON thô.** `enhancePosMaps` chỉ thay `<pre>` khi parse được map
  (JSON có `items` / ASCII có `^`+`GÓC`); khối JSON pos-map không khớp (thiếu items/parse lỗi/bản
  spec thứ 2) thì `return` bỏ qua → để nguyên `<pre>` JSON thô hiện ra. → Thêm nhánh: khối trông
  như pos-map JSON (có `yTop`/`xLeft`) mà không render được thì ẩn/gỡ, không để lòi.

- **[N-05] Bỏ HẲN "Đối thủ đang theo dõi (Ads Library)" ở T1-T3.** Section trên trang competitor
  (`P.competitor`) hiện DATA MOCK (`M.tracked` từ `web/data.js`: Phúc Long/Katinat) — không liên
  quan business thật, reset không xoá. Founder quyết: **bỏ hẳn section này ở giai đoạn T1-T3**
  (không đổi sang data thật). → Gỡ khối `M.tracked` khỏi render P.competitor.

- **[N-06] Hiện rõ trạng thái task (đang chạy / đã lỗi / xong) cho user.**
  Bấm "Lập chiến lược" (strategize_web ~2 LLM call, chạy ngầm) nhưng KHÔNG có chỉ báo rõ → user
  tưởng "không chạy gì" (thực ra vẫn ra kết quả, chỉ chậm + im lặng). Cần: chỉ báo toàn cục
  (banner/toast/progress) cho biết task ĐANG CHẠY (bước/% nếu có), ĐÃ LỖI (kèm lý do — đã log ở
  2f28497), hay XONG — đừng chỉ dựa nút đổi chữ. Áp cho mọi task (research + strategize).
  → Phụ: nhánh strategize trong `_execute` KHÔNG có timeout (research có `wait_for`) — nếu LLM treo
  thì job kẹt 'running' mãi → thêm timeout + đánh 'error' để khỏi kẹt vô hạn.

- **[N-07] Build/refresh Playbook SAU khi chốt chiến lược + cờ lệch nguồn.**
  Hiện `strategize_web` sinh synthesis + playbook cùng lúc; nhưng nếu sửa synthesis sau đó
  (doc "Sửa tay"/"Nhờ Max chỉnh" → version mới) thì **playbook KHÔNG regen** → bám synthesis cũ.
  `approve_synthesis` (chốt) cũng không regen. → (1) Regen playbook khi bấm "Chốt chiến lược"
  (đọc synthesis mới nhất); (2) gắn playbook với version/fingerprint synthesis nó dựa vào, lệch
  thì hiện badge "Playbook theo chiến lược cũ — cập nhật?" (tái dùng `_strategy_fp`).

- **[N-08] Chất lượng output Playbook hơi kém — rà cấu trúc/prompt.**
  Playbook web do prompt `tac_system` trong `strategize_web` sinh (WEB-OWNED, không phải agents/).
  Cấu trúc hiện: mỗi tệp × phễu TOFU/MOFU/BOFU, mỗi mũi có góc/insight + copy mẫu + kênh + khung
  test (ngưỡng tương đối) + KPI; tệp ưu tiên full, tệp phụ gọn; kết bằng bảng. Founder thấy output
  "hơi kém". Nghi 2 nguồn: (a) prompt còn chung chung/cần cụ thể hơn; (b) UPSTREAM — research T1-T3
  chưa đủ (mới market) → synthesis mỏng → playbook mỏng (garbage-in). → Khi làm: hỏi rõ "kém" ở
  điểm nào (chung chung? thiếu copy thật? thiếu kênh cụ thể? test mơ hồ?) rồi nâng prompt + đảm bảo
  research đủ trước khi lập.

- **[N-09] Heading `####` hiện RAW (dấu thăng lòi) trong output research — xấu.**
  Triệu chứng (ảnh founder): các mục như `#### Tốc độ tăng trưởng (CAGR)`, `#### Xu hướng nổi
  bật`, `#### Timing: Đây có phải thời điểm tốt không?` hiện NGUYÊN dấu `####` thay vì thành tiêu đề.
  **Xác định "nó là cái gì":** LLM xuất heading `####` **NẰM TRONG bullet** — dòng dạng
  `- #### Xu hướng nổi bật:` (markdown lồng sai). Renderer `renderAIContent` (web/app.js ~dòng
  220-224) CHỈ nhận heading khi `####`/`###`/`##` ở **ĐẦU DÒNG** (`/^####\s+/`); khi đứng sau dấu
  bullet (`- `/`•`) thì regex KHÔNG khớp → render thành `<li>#### …</li>` để lộ dấu thăng.
  Gốc prompt: research T1-T3 đang chạy `agents/` (reference-only, KHÔNG sửa) → fix ở **renderer web**.
  → Cách làm (sau, áp cho TẤT CẢ mục, kể cả các mục đằng sau):
    1. Trong `renderAIContent`: khi xử lý 1 item list, nếu nội dung mở đầu bằng `#{2,6}\s+` (heading
       lồng trong bullet) → tách ra render thành **tiểu mục có style** (vd `<h6 class="md-subh">` hoặc
       `<p class="md-subh"><b>…</b></p>`), KHÔNG để lộ `#`.
    2. Thêm 1 pass chuẩn hoá chung: mọi run `#` không phải heading-đầu-dòng-hợp-lệ → hoặc nâng thành
       tiểu mục, hoặc strip. (Phủ hết các biến thể `####`/`#####` rải rác.)
    3. Bỏ luôn dấu `:` cuối heading cho đồng nhất; thêm CSS `.md-subh` cho gọn-đẹp.
  - Mirror app.js ↔ standalone. (Cùng họ trình bày output: cân nhắc gộp với N-04 posmap khi làm.)

- **[N-10] Chuyển trang KHÔNG tự cuộn lên đầu.**
  Đọc 1 doc dài (vd competitor) cuộn xuống giữa, bấm sang trang khác → trang mới vẫn ở vị trí cuộn
  cũ (phải tự kéo lên). `route()` CÓ `document.querySelector('.main').scrollTo(0,0)` (app.js ~1993)
  nhưng không ăn → element đang cuộn THỰC TẾ không phải `.main` (có thể window/body, hoặc nội dung
  doc cuộn trong `.ai-output` max-height:560 overflow:auto). → Fix sau: thêm `window.scrollTo(0,0)`
  + reset `.ai-output`/scroll-container về 0 trong `route()` (và sau `injectPageNav` chuyển tab T1→T5).
  Mirror 2 file.

- **[N-11] Tiếng Việt output chưa tự nhiên — dịch máy / ghép từ Tây.**
  Ví dụ (ảnh competitor): `cạnh tranh "đầu-đầu"` (head-to-head dịch sát), `"generalist"`, `"category
  leader"`… đọc gượng. Gốc prompt research = `agents/` (reference-only). → Phương án xử lý:
    1. Khi rebuild research WEB-OWNED: thêm luật prompt "TIẾNG VIỆT TỰ NHIÊN — KHÔNG dịch sát/ghép từ
       Tây (đầu-đầu→trực diện/đối đầu trực tiếp; generalist→làm tất-không-chuyên); thuật ngữ Anh phải
       kèm giải thích ngắn." (Tái dùng tinh thần đã có ở `syn_system`/`tac_system` web-owned.)
    2. Output web-owned (synthesis/playbook) CÓ THỂ thêm luật này NGAY (không chờ research).
    3. (tuỳ chọn) glossary hậu-xử-lý thay vài cụm sát-nghĩa cố định — nhẹ, nhưng dễ sót.
  → Gộp vào đợt nâng prompt + rebuild research.

- **[N-12] Output research bị CẮT giữa câu — do thinking budget, KHÔNG phải max_tokens thấp.**
  Research max_tokens = 16,000 (đủ), nhưng chạy Gemini 2.5 Pro → token "thinking" tính VÀO output:
  `_calc_thinking_budget(16000)=min(8000,40%×16000)=6,400` → chữ thấy được chỉ ≈ 9,600 token → bài
  dài bị cụt. → Fix (A, web-owned): trong `tools/llm_router.py › _calc_thinking_budget`, giảm cap dải
  5K–20K (vd `min(4000, 25%)`) → research thinking ≈4,000 → output ≈12,000 (+~2,400). Chỉ ảnh hưởng
  dải giữa (research + content assets), KHÔNG đụng Synthesis/SWOT/Playbook (≥20K). Hoặc gộp vào
  rebuild research web-owned (tự set token + scope). (Founder hỏi 2026-06-25, chốt: note để sửa 1 thể.)

- **[N-13] (quan sát thêm) Bảng markdown rộng bị CẮT cạnh phải.**
  Bảng competitor nhiều cột (…Estimated Spend · Audience) tràn khung, cột phải bị cắt, không cuộn
  ngang được. CSS có sẵn `.tbl-wrap{overflow-x:auto}` (styles.css:280) nhưng `renderAIContent` có vẻ
  KHÔNG bọc `<table>` vào `.tbl-wrap`. → Fix sau: bọc mọi `<table>` render từ markdown trong
  `<div class="tbl-wrap">` để cuộn ngang thay vì cắt. Mirror 2 file.

- **[N-14] "Nhờ Max chỉnh" báo "không tìm thấy đoạn khớp" với góp ý theo TIỂU MỤC.**
  Founder gõ "cảm thấy Messaging Gap chưa đủ sâu, chưa đánh sâu tâm lý nam" → `patch_skill_run`
  → `agents/surgical_edit.patch_document` trả PATCH_ASK "Không tìm thấy đoạn khớp". Gốc:
  `split_sections` chỉ tách theo `_SECTION_RE` = heading **đánh số `## N. Title`**; "Messaging Gap"
  là **tiểu mục** nằm trong "2) Market Gap Analysis" (lại còn format `2)` không phải `2.`) → detector
  không thấy trong outline → không map được → hỏi lại. ⇒ Góp ý theo tiểu mục / heading phụ luôn fail.
  `surgical_edit` ở `agents/` (reference-only) → fix WEB-OWNED ở `patch_skill_run`:
    1. Khi nhận PATCH_ASK → **fallback revise toàn-doc**: gọi llm_router viết lại CẢ doc áp dụng góp ý
       (giữ cấu trúc/section, chỉ đào sâu phần liên quan — vd Messaging Gap) → lưu version mới. Để góp
       ý "lỏng" vẫn ra kết quả thay vì bế tắc.
    2. (phụ) Nếu vẫn muốn surgical: nới matcher nhận cả tiểu mục in đậm + heading `N)`/`####` —
       nhưng cái này ở agents/, chờ rebuild. Trước mắt dùng (1).

- **[N-15] Research BỊA SỐ không nguồn, không gắn "(ước tính)".**
  Ví dụ (ảnh customer_insight): "Thiết bị: **99% smartphone** (Android phổ biến hơn iOS ở phân khúc
  này)" — con số bịa, KHÔNG nguồn nào đo được cho tệp ngách (GenZ nam triệt vùng kín HN); cũng KHÔNG
  gắn "(ước tính)". Vi phạm luật cốt lõi *KHÔNG bịa số → nếu suy đoán PHẢI gắn "(ước tính)"*. Cùng họ
  N-03/N-03b/N-11: pipeline `agents/` khi data mỏng → LLM "độn" số cho đầy section. Gốc prompt ở
  `agents/` (reference-only). → Dứt điểm khi rebuild research WEB-OWNED:
    1. Luật cứng: KHÔNG nêu số tuyệt đối nếu không có nguồn grounded; suy đoán → BẮT BUỘC "(ước tính)"
       + nói rõ cơ sở suy ra.
    2. Mục không có dữ liệu (vd tỉ lệ thiết bị tệp ngách) → ghi "_chưa đủ dữ liệu công khai_", KHÔNG
       bịa.
    3. (kiểm thử) thêm 1 pass tự-soát "số nào không có nguồn?" trước khi lưu.

- **[N-16] Gợi ý "Đặt cược" (5 nhóm) còn KÉM — nâng theo cách bot làm strategy.**
  Founder thấy option `gen_bet_options` (market/segment/positioning/price/channel) hời hợt, generic.
  Gốc: `gen_bet_options` (webapp/business.py — WEB-OWNED, sửa được) đang dùng prompt MỎNG +
  `TaskType.INTAKE_JSON` (GPT-5-mini, tier yếu nhất): chỉ "rút 2-4 option/nhóm: title/desc/why",
  KHÔNG framework, KHÔNG bước suy luận CMO.
  → Tham khảo BOT (chỉ đọc, đừng sửa `agents/`):
    - `agents/strategy_prompts.py › CMO_STRATEGY_SYSTEM`: persona "cố vấn 10 năm", luật anti-jargon,
      positioning theo **SAVE** (solution/access/value/education), wedge {audience/channels/not_doing/
      rationale}, content bám **archetype**.
    - `agents/strategy.py › generate_strategy`: nạp **frameworks** — `get_full_industry_brief`,
      `generate_save_analysis`, `format_archetype_block`, SMART; route **Sonnet** (GENERIC_CREATIVE),
      max_tokens 10K (KHÔNG dùng tier mini).
    - `agents/discovery.py`: Diagnostic Brief = facts + **giả thuyết XẾP HẠNG** + gaps → input cho CMO
      (option bám giả thuyết đã rank, không phán generic).
  → Việc làm (web-owned) khi dọn:
    1. Đổi model `gen_bet_options`: INTAKE_JSON → OPS_BRIEF/SYNTHESIS (GPT-5/Gemini/Sonnet).
    2. Nhồi framework vào prompt: industry_context (archetype + market_dynamics) + SAVE cho nhóm Định
       vị; thêm bước "suy luận CMO ngắn" trước khi rút option.
    3. Mỗi option 'why' phải DẪN phát hiện research THẬT (chống generic), gắn "(ước tính)" nếu suy.
    4. Cân nhắc 2 call: (a) CMO reasoning từ research → (b) chẻ thành 5 nhóm option. (Giống mạch
       brief→funnel của bot.)

- **[N-17] Flow ĐANG BỎ QUA bước Playbook — nhảy thẳng "Lập chiến dịch".**
  Sau "✓ Đã chốt Chiến lược", nút CHÍNH là **"→ Lập chiến dịch"**; Tactical Playbook chỉ là nút phụ
  "Chi tiết hoá bằng Tactical Playbook" → user dễ nhảy thẳng sang campaign, BỎ QUA Playbook (T5 — cách
  đánh chi tiết per tệp × phễu TOFU/MOFU/BOFU: copy mẫu, kênh, test, KPI). Mất cầu nối chiến lược→thực
  thi. Lưu ý: `strategize_web` ĐÃ sinh playbook CÙNG synthesis (tồn tại sẵn, chỉ không bắt xem/dùng).
  → ✅ FOUNDER CHỐT (2026-06-25): **(b) — Playbook là NỀN NGẦM.** Tuyến nội dung + lịch + bài TỰ bám
    playbook (kế thừa) dù user không mở tab; vẫn để link xem Playbook. Bắt buộc: khâu sinh tuyến/bài
    ĐỌC CẢ playbook, không chỉ synthesis. (Liên quan N-07: playbook refresh khi synthesis đổi.)

- **[N-18] Trang "Lập chiến dịch" (#occasion) UI/UX còn RỐI — CHƯA dọn (bản legacy revert).**
  Founder tưởng đã dọn — thực tế CHƯA. Lịch sử: page này từng được dựng "campaign-first hero" (gap→
  master→hub), nhưng khi chốt **Vision A** mình đã GỠ hero đó và **REVERT page về layout LEGACY**
  (Always-on pillars TOFU/MOFU/BOFU + Occasion gợi ý + Retention + "Chốt tuyến nền"/"Sinh lại"/"Lên
  lịch"/"Max viết brief thương hiệu"). → Nên nó vẫn rối + còn sót khái niệm chồng chéo (pillars vs
  tuyến vs branding-campaign vs occasion). Phần ĐÃ dọn = **Strategy (đặt cược) + Intake**, KHÔNG phải
  page này.
  → Việc làm (slice tuyến nội dung, ~S-20/S-21): redesign #occasion thành **"Tuyến nội dung" gọn theo
    Vision A**: T4-T5 → các tuyến (Khai sáng/Tin cậy/Chuyển hoá/Lan toả) bám playbook ngầm (N-17b) →
    lịch. Bỏ/gộp các khối chồng chéo legacy (branding-campaign packaging, occasion rời, retention để
    riêng). Mirror 2 file.

- **[N-19] `<br>` hiện RAW trong ô bảng (competitor 8 chiều).**
  Ô bảng có "…bảo hành).`<br>`Điểm yếu:…" — LLM xuất `<br>` để xuống dòng trong cell (tách Điểm mạnh/
  Điểm yếu), nhưng `renderAIContent.inline()` chạy `esc()` escape `<` → `&lt;` ⇒ hiện chữ `<br>` thô.
  → Fix sau (1 regex, an toàn): trong `inline()`, SAU esc thêm `.replace(/&lt;br\s*\/?&gt;/gi, '<br>')`
  → chuyển `<br>` đã-escape về xuống dòng thật. Mirror app.js ↔ standalone. (cùng họ render N-09/N-13)

## ✅ Đã làm (lưu vết)
- Enter ở ô intake = nút Tiếp (fcbb3e3)
- Báo "agent đang chạy" đúng + bỏ "90 ngày" hardcode intake (04f9a9a)
- Fix reset/_retention_cache (a8cd7b0)
- Bắt + log lý do dừng research (2f28497)

## ⏳ Tính năng đã hoãn (chờ ưu tiên)
- **[Lô I+ — Vòng phản hồi AUTO-PULL] nền `content_feedback` ĐÃ CÓ (nhập tay = tạm, "không ai nhập").**
  Founder chốt: bản thật phải **TỰ KÉO SỐ từ FB/TikTok** (đã có nền kết nối FB Ads + ads_snapshots) →
  map số liệu post ↔ bài (skill_run content) → tự gọi `content_feedback` → Max chấm + tối ưu, KHÔNG
  bắt nhập tay. Nâng thêm: gom nhiều bài → rút quy luật "loại nội dung/hook/kênh nào ăn nhất". Giữ ô
  nhập tay làm fallback. → Làm khi ưu tiên (cần map FB post id ↔ skill_run).
- "C hoàn chỉnh" — lịch kéo-thả (nền dữ liệu M-E đã có)
- Theme tháng mềm (always-on nghiêng theo roadmap phase)
- M-D Pha 4 full (phân nhóm khách — bản nhẹ đã lồng vào campaign F2)
- M-F F3 mở rộng đã xong; còn ACTION-task integration thật (gửi mail/ads…) — ngoài phạm vi hiện tại
- Test thật end-to-end trên Railway
