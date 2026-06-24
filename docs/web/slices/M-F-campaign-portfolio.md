# SPEC — M-F: Campaign Portfolio + Task layer (chiến lược con + thực thi)

> Founder (2026-06-24): chốt hướng A — Max tự đề xuất DANH MỤC chiến dịch từ roadmap (founder duyệt),
> và mỗi campaign phải có TASK/DELIVERABLE thực thi (email, influencer, ads…) chứ không mơ hồ.
> Web-owned; KHÔNG sửa agents/ (chỉ tham khảo). Spec trước — code sau khi founder duyệt open questions.

## 1. Vấn đề — thiếu tầng 2 của tháp kế hoạch
| Tầng | Hiện trạng |
|---|---|
| 1. Chiến lược tổng (synthesis): định vị, mục tiêu, roadmap | ✅ |
| **2. Danh mục chiến dịch (portfolio) — chạy chiến dịch gì, LOẠI nào, KHI nào** | ❌ thiếu → "mơ hồ" |
| 3. Chiến dịch đơn (occasion: arc + SMART) | ⚠️ có nhưng KHÔNG biết "loại", tạo lẻ ad-hoc |
| **3b. Task/deliverable thực thi của campaign (email/ads/influencer…)** | ⚠️ generator CÓ nhưng trôi nổi, không gắn campaign |
| 4. Nội dung (lịch + bài) | ✅ |

→ Cần: (a) campaign có **LOẠI** + playbook; (b) Max suy **danh mục** từ roadmap; (c) mỗi campaign có
**checklist task** móc vào generator sẵn.

## 2. Nguyên tắc phân loại — KHÔNG bê phẳng "16 loại"
16 loại marketing phổ biến trộn 3 trục → tách đúng tầng:
- **Theo MỤC TIÊU = LOẠI chiến dịch thật** (Nhận biết · Ra mắt SP · Sale/Promo · Thu lead · Tương tác/Viral · Giữ-Loyalty/Winback · Tái định vị).
- **Theo KÊNH** (Email · Ads/PPC · Influencer/KOL · UGC · Video · SEO · Social) = **TASK/deliverable BÊN TRONG** campaign, không phải loại.
- **Theo PHONG CÁCH** (Guerrilla · CSR/Cause · Event) = **modifier** sáng tạo, để sau.

## 3. Mô hình dữ liệu

### 3.1 Campaign TYPE = template gắn mục tiêu (deterministic)
Mỗi type = playbook đặt sẵn: objective (1 trong 6 đã có) + hình arc + kênh gợi ý + KPI dạng + window điển hình
+ **bộ task mặc định**.

> Founder (2026-06-24): KHÔNG giới hạn 6. Chia 2 nhóm + cho tự-mô-tả (Max dựng playbook) — không trần cứng.

**Nhóm A — theo MỤC TIÊU (objective-led):**

| Type | Objective | Arc | Window | Task mặc định |
|---|---|---|---|---|
| 📣 Nhận biết | brand | tease→story→amplify | 3-6 tuần | posts, video_script, ugc/influencer brief |
| 🚀 Ra mắt SP | brand+conversion | teaser→reveal→proof→convert | 3-4 tuần | teaser posts, video_script, ads_copy, influencer brief, email seq, (landing) |
| 💰 Sale/Promo | conversion | buildup→peak→last-call→after | 1-3 tuần | promo posts, ads_copy (BOFU), email/Zalo blast, retarget ads, sales_inbox |
| 📞 Thu lead | leadgen | educate→offer tư vấn→nurture | 2-6 tuần | lead-magnet content, ads_copy (lead), email seq nurture, sales_inbox |
| ✨ Tương tác/Viral | engagement | hook→participate→amplify | 1-3 tuần | minigame post, ugc_brief, influencer brief |
| 🔁 Giữ/Winback | retention | (behavior, không window) | n/a | email/Zalo winback seq, loyalty posts, sales_inbox |

**Nhóm B — theo HÌNH THỨC đặc thù (playbook + task riêng):**

| Type | Objective gốc | Đặc trưng playbook/task |
|---|---|---|
| 🔄 Tái định vị (Rebranding) | brand | story chuyển đổi, video manifesto, PR pitch, đồng bộ kênh |
| 🤝 Influencer/KOL-led | brand/engagement/conversion | influencer brief (nhiều tier), outreach (action), tổng hợp UGC |
| 🎪 Event/Trải nghiệm | engagement/brand | pre-hype → ngày event → recap; landing đăng ký (action: tổ chức) |
| ❤️ CSR/Vì cộng đồng | brand | narrative giá trị, PR, kêu gọi tham gia |
| 📚 Content/SEO dài hơi | leadgen/brand | cụm bài SEO, lead magnet, email nurture (window dài) |
| 👥 UGC/Cộng đồng | engagement | ugc_brief, minigame, tổng hợp & re-share |

**+ ✏️ Tự mô tả loại khác** → Max dựng playbook (arc + task + KPI) cho loại đó (1 LLM call, như free-text
mục đích đợt). → KHÔNG có trần cứng số loại.

🔴 Pure-channel (email · ads/PPC · retargeting · social) = **TASK bên trong** campaign, KHÔNG thành "loại".

→ Bảng trên là DEFAULT (code); Max có thể tinh chỉnh task theo bối cảnh (xem 4.2).

### 3.2 Task/deliverable
```
task = { id, kind, label, status:'todo'|'draft'|'approved', run_id? }
```
- `kind` = key generator có sẵn (CONTENT task) hoặc 'action' (việc người làm, Max ra brief).
- **CONTENT task → móc generator đã có** (không build mới):
  `calendar_post · post_channels · video_script · ugc_brief · ads_copy · email_zalo_sequence · sales_inbox_script`.
- **ACTION task** (Max ra brief + mẫu, người thực thi): liên hệ KOL, set-up tài khoản ads, gửi
  sequence qua ESP, đăng bài, tổ chức event. Max **không** thực thi ngoài đời (không integration).
- Generator MỚI (để PHA SAU): landing page copy · SEO outline · event plan · PR pitch · referral.

### 3.3 Portfolio
- `campaign_portfolio` = list campaign Max đề xuất (proposal) lưu `intake_extra.campaign_portfolio`
  trước khi founder commit từng cái. Mỗi item: `{name, type, objective, phase, when_hint, why, window_hint}`.
- Founder duyệt → commit 1 item → tạo bản ghi `campaigns_v2` (như occasion hiện tại) + sinh task checklist.

## 4. Luồng sinh (ranh giới code vs LLM)

### 4.1 Max suy DANH MỤC từ roadmap (Pha B của M-F)
- `gen_campaign_portfolio(uid)` — 1 LLM call: đọc synthesis(roadmap) + industry + archetype + objectives
  → đề xuất N chiến dịch CÓ LOẠI map theo giai đoạn roadmap, kèm lý do gắn từng giai đoạn.
- 🔴 **Code lo NGÀY** (`_week_of`/anchor/horizon): LLM chỉ nói "đầu Quý 1 / trước Tết / tháng 3", code map ra
  window thật. LLM KHÔNG bịa ngày.
- 🔴 **Số/KPI**: chưa baseline → KPI dạng khoảng + nhãn "ước tính" (luật đã có ở occasion_draft).
- 🔴 Ép bám wedge/USP/ngành + bắt nêu lý-do-theo-roadmap; ràng số lượng (vd 3-6) + theo mô hình 2-track.
- Founder curate (giữ/bỏ/sửa) — pattern "Max đề xuất, founder chốt".

### 4.2 Commit 1 campaign → brief + task
- Tạo `campaigns_v2` (tái dùng `save_occasion`); brief chi tiết = **`occasion_draft` đã có** (arc 5 pha + SMART),
  truyền thêm `campaign_type` để bám playbook.
- Task checklist = DEFAULT theo type (3.1) — có thể cho Max tinh chỉnh (thêm/bớt task hợp ngành) bằng 1 call nhẹ
  (tùy Q2). Lưu vào campaign.

### 4.3 Làm từng task
- CONTENT task bấm "Tạo" → gọi generator tương ứng (`gen_content_asset`/`gen_derivative`/`gen_calendar_post`),
  **truyền campaign context** (type/brief/objective) để bám đúng đợt. Lưu skill_run → gắn `run_id` vào task,
  status→draft→approved.
- ACTION task bấm "Brief" → Max ra hướng dẫn + mẫu (vd tin nhắn outreach KOL). status do người tick.

## 5. UI
- **Trang/section "Chiến dịch"**: nút "✨ Max đề xuất danh mục" → list proposal (card mỗi campaign: type icon,
  objective, when, why) → duyệt/sửa/bỏ → "Tạo chiến dịch" từng cái.
- **Chi tiết 1 campaign**: brief (arc/SMART) + **bảng Task** (kind icon · label · status · nút Tạo/Brief · link bài đã sinh).
- Occasion wizard hiện tại: thêm bước **chọn LOẠI** (pre-fill objective/arc/window/task theo template) — nối M-D/M-E2.
- Lịch: campaign band giữ nguyên (M-D Pha 3 arc); task không lên lịch ngày (trừ posts → vẫn vào calendar).

## 6. Max LÀM ĐƯỢC tới đâu (thành thật)
- **Sinh nội dung deliverable**: phần lớn ĐÃ có generator (email/ads/UGC-KOL brief/video/sales/đa kênh) → làm ngay.
- **Suy danh mục + brief typed**: tái dùng `occasions`(thô đã có) + `occasion_draft`(đã có) → khả thi, là orchestration.
- **KHÔNG** thực thi ngoài đời (gửi mail/contact KOL/chạy ads/đăng/event) → ra brief + người làm.
- Generator còn thiếu (landing/SEO/event/PR/referral) → thêm sau, cùng pattern.

## 7. Phạm vi & thứ tự
- **Pha F1 — Type + Task checklist trên 1 campaign** (execution layer founder cần nhất): thêm campaign_type vào
  occasion + bộ task default móc generator sẵn + UI bảng task. KHÔNG cần portfolio để chạy.
- **Pha F2 — Portfolio auto-đề xuất** (`gen_campaign_portfolio` + UI duyệt + code map ngày): tầng 2 "chiến lược con".
- **Pha F3 (sau)** — generator mới (landing/SEO/event) + ACTION-task brief đầy đủ + theo dõi status/kanban.
→ Khuyến nghị làm F1 trước (mỗi campaign hết mơ hồ), rồi F2 (Max lên cả danh mục).

## 8. ĐÃ CHỐT (2026-06-24)
- Q1 = KHÔNG giới hạn 6 → **Nhóm A (6 objective-led) + Nhóm B (6 form/style-led) + tự-mô-tả (Max dựng playbook)**.
- Q2 = **template default + Max tinh chỉnh** nhẹ theo ngành.
- Q3 = ACTION task chỉ **brief + tick tay** (chưa integration). OK.
- Q4 = Generator mới (landing/SEO/event) → **Pha F3**.
- Q5 = **F1 trước F2**.
- Q6 = status task mức **badge đơn giản** (todo/draft/approved).

→ Cleared để code **Pha F1** (campaign_type 2 nhóm + tự-mô-tả; task checklist móc generator sẵn; UI bảng task).

## 9. ĐÃ TRIỂN KHAI
### F1a (2026-06-24) — chọn loại + playbook + lưu task
- Backend: CAMPAIGN_TYPES (12, 2 nhóm) + CAMPAIGN_TASK_LABELS + campaign_types_list + _build_campaign_tasks.
  occasion_draft(campaign_type=) default objective + playbook vào prompt. save_occasion lưu type+tasks
  vào intake_extra.campaign_meta[cid]. biz_data trả bizCampaignMeta + bizCampaignTypes. API +campaign_type.
- FE: wizard bước "1·Loại chiến dịch" (nhóm A/B + tự mô tả, loại trừ); pre-fill mục đích; task preview ở
  review brief; renumber bước 1-4. Mirror + CSS.

### F1b (2026-06-24) — bảng task + sinh deliverable + status
- Backend: gen_campaign_task(cid,task_id) — content task → generator bám BRIEF ĐỢT (_CAMPAIGN_TASK_GEN);
  action task → hướng dẫn + mẫu (_ACTION_TASK_GEN); lưu skill_run + set status=draft+run_id.
  update_campaign_task(status) approve. API: campaign/task-gen, campaign/task-update.
- FE: band campaign clickable → modal chi tiết; bảng task (✍️ content / 🔧 action) + status badge
  (todo/draft/approved) + nút Tạo/Xem/Duyệt. Mirror app.js↔standalone + CSS.
- Verify: ast/import/node --check OK; types=12, tasks đúng.
### F2 (2026-06-24) — Max đề xuất danh mục từ roadmap + tệp nhắm (Pha 4 nhẹ)
- Backend: gen_campaign_portfolio — 1 LLM call suy 3-6 chiến dịch CÓ LOẠI bám roadmap, mỗi cái
  {name,type,objective,audience,why,start_week,window_weeks}. CODE lo NGÀY (start_week→ws/we qua
  anchor+horizon), LLM lo ý; validate type/audience, clamp start_week≤horizon, bỏ loại sai. Lưu
  intake_extra.campaign_portfolio. clear_campaign_portfolio(index) bỏ 1 mục/cả list.
  Pha 4: AUDIENCE_SEGMENTS (Mới/Active/Nguy cơ/VIP/Tất cả) + _TYPE_AUDIENCE default theo loại;
  audience threaded qua occasion_draft (prompt) + save_occasion (campaign_meta). biz_data trả
  bizCampaignPortfolio. API: campaign/portfolio + portfolio-clear.
- FE: nút "🗂️ Danh mục chiến dịch" → modal list (card: loại/tuần/tệp nhắm/why) + "✨ Đề xuất" /
  "↻ Đề xuất lại" + mỗi card "Tạo chiến dịch" (mở wizard điền sẵn type/objective/window/audience) +
  "✕ bỏ". Wizard thêm selector "🎯 Tệp nhắm". openOccasionWizard nhận preset object. Mirror+CSS.
- Verify: ast/import/node --check OK; test date-map/validate/clamp/drop PASS.
### F3 (2026-06-24) — generator mới + kanban
- Backend: thăng các action viết-được thành CONTENT generator: landing_copy · seo_outline · pr_pitch ·
  event_plan · referral_plan (thêm vào _CAMPAIGN_TASK_GEN + CAMPAIGN_TASK_LABELS). Cập nhật task list
  của các loại (launch/leadgen→landing_copy; rebrand/csr→pr_pitch; content_seo→seo_outline; event→
  event_plan; retention→referral_plan). Giữ action thật: setup_ads/contact_kol/run_event.
- FE: campaign detail → KANBAN 3 cột (Chưa làm/Bản nháp/Đã duyệt) gom task theo status + hiện tệp nhắm.
  Tái dùng .kanban grid sẵn + .kb-* mới. Mirror app.js↔standalone.
- Verify: ast/import/node --check OK; _build_campaign_tasks loại mới đúng.
- M-F HOÀN TẤT (F1a/F1b/F2/F3). Còn ngoài M-F: C kéo-thả, theme tháng mềm, test Railway.
