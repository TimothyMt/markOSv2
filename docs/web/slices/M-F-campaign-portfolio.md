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
+ **bộ task mặc định**. Bảng dự kiến:

| Type | Objective | Arc | Window | Task mặc định |
|---|---|---|---|---|
| 📣 Nhận biết | brand | tease→story→amplify | 3-6 tuần | posts, video_script, ugc/influencer brief |
| 🚀 Ra mắt SP | brand+conversion | teaser→reveal→proof→convert | 3-4 tuần | teaser posts, video_script, ads_copy, influencer brief, email seq, (landing) |
| 💰 Sale/Promo | conversion | buildup→peak→last-call→after | 1-3 tuần | promo posts, ads_copy (BOFU), email/Zalo blast, retarget ads, sales_inbox |
| 📞 Thu lead | leadgen | educate→offer tư vấn→nurture | 2-6 tuần | lead-magnet content, ads_copy (lead), email seq nurture, sales_inbox |
| ✨ Tương tác/Viral | engagement | hook→participate→amplify | 1-3 tuần | minigame post, ugc_brief, influencer brief |
| 🔁 Giữ/Winback | retention | (behavior, không window) | n/a | email/Zalo winback seq, loyalty posts, sales_inbox |

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

## 8. Mở / cần founder chốt
- [ ] Q1: Bộ LOẠI campaign (6 cái mục 3.1) đủ/đúng chưa? thêm "Tái định vị", bớt cái nào?
- [ ] Q2: Task checklist — **fixed theo template** (code, nhanh, đoán được) hay **Max tinh chỉnh theo ngành**
      (1 call thêm)? → đề xuất: template default + Max chỉ thêm/bớt nhẹ khi rõ ràng.
- [ ] Q3: ACTION task (contact KOL/chạy ads…) đợt này chỉ **brief + tick tay** (chưa integration) — OK chứ?
- [ ] Q4: Generator mới (landing/SEO/event) — để **Pha F3** (đề xuất) hay cần ngay?
- [ ] Q5: Thứ tự **F1 trước F2** (đề xuất) hay bạn muốn F2 (portfolio) trước?
- [ ] Q6: Theo dõi status task (todo/draft/approved) đợt này ở mức **đơn giản** (badge) — đủ chưa, hay cần kanban?
