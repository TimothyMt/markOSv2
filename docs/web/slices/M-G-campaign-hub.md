# SPEC — M-G: Campaign Hub (gom mọi thứ về campaign; always-on = 1 campaign nền)

> Founder (2026-06-25): màn "Lập chiến dịch" rối (pillars rời + occasion tách). Chốt: đóng gói
> always-on thành 1 CAMPAIGN nền (Branding) — vẫn giữ bản chất liên tục/không-deadline; mỗi campaign
> là 1 HUB gom 10 thành phần (đã duyệt). Web-owned; KHÔNG sửa agents/. Spec trước — code sau khi duyệt.

## 1. Vấn đề
- Always-on đang hiện dưới dạng **content pillars rời** ở 1 cột, occasion ở cột khác → 2 thứ khác loại, rối.
- Always-on KHÔNG được mô hình hoá thành "campaign" → không thống nhất với lớp campaign (M-F).

## 2. Mô hình thống nhất
**Mọi thứ là CAMPAIGN.** 2 loại:
- 🟢 **Always-on (Branding)** — **1 cái DUY NHẤT, chạy liên tục, KHÔNG window/deadline/arc/SMART số**
  (Byron Sharp drumbeat). Nội dung = content pillars + always-on calendar.
- 🔴 **Occasion** — nhiều, có window + arc + SMART (như M-F hiện có).

→ UI: **1 danh sách campaign** = [🟢 Branding] + [🔴 occasions]. Bấm vào ra **HUB** đủ thành phần.

## 3. Campaign = HUB gom 10 thành phần (đã founder duyệt)
| # | Thành phần | Always-on (Branding) | Occasion |
|---|---|---|---|
| 1 | Đầu campaign | tên · loại · mục tiêu · tệp nhắm · **liên tục** | + window |
| 2 | Brief/định hướng | định vị nền + **big idea** + key message (bám synthesis) — KHÔNG SMART/deadline | arc 5 pha + SMART + offer |
| 3 | Kênh triển khai | kênh + vai trò mỗi kênh | (như vậy) |
| 4 | Content backbone | **pillars** + content calendar (always-on track) | bài theo arc + calendar band |
| 5 | Deliverables/Task (kanban) | posts · video · ugc | + ads · email · landing · inbox |
| 6 | KPI | reach/nhớ (định hướng) | số theo mục đích |
| 7 | Ngân sách | % nền (định hướng, không số) | số đợt (SMART) |
| 8 | Rủi ro & cờ đỏ | có | có |
| 9 | Liên kết nguồn (lineage) | synthesis/playbook bản nào | + research |
| 10 | Trạng thái tổng | % task xong | % task xong |

🔴 GIỮ bản chất always-on: liên tục · không deadline · không arc · không SMART số (D-029). "Campaign"
ở đây = container thương hiệu có tên, KHÔNG phải burst.

## 4. Data model (đề xuất — chờ chốt Q1)
- **Occasion**: giữ nguyên `campaigns_v2` row + `intake_extra.campaign_meta[cid]` (M-F).
- **Always-on**: **VIRTUAL** (không tạo DB row) — id quy ước `"always-on"`. Meta lưu
  `intake_extra.campaign_meta["always-on"]` = {type:'branding', tasks, channels, audience, kpi…}.
  Nội dung backbone DERIVE từ: `pillars_locked` (pillars) + `calendar_plan` always-on track + synthesis
  (định vị/big idea). → KHÔNG cần migration, 1 always-on/user.
- Brand brief (big idea/key message/định vị nền): sinh nhẹ từ synthesis (1 LLM call, KHÔNG SMART) hoặc
  trích mục Định-vị của synthesis. (Q2)

## 5. Generation
- **Brand brief** (`gen_brand_campaign_brief` hoặc trích synthesis): định vị nền + big idea + key message
  + KPI nhận biết (định hướng) — KHÔNG deadline/số cứng. Bám synthesis + USP + archetype.
- **Pillars + calendar**: tái dùng `campaign_plan` (pillars) + `calendar_plan` (always-on track) — đã có.
- **Tasks always-on**: bộ task brand mặc định (posts/video/ugc) — tái dùng `_CAMPAIGN_TASK_GEN` + kanban M-F. (Q3)
- **Occasion**: nguyên M-F.

## 6. UI
- **Trang "Chiến dịch" (hub list)**: thay màn "Lập chiến dịch" rối hiện tại bằng **1 danh sách campaign**:
  card [🟢 Branding nền] luôn đứng đầu + [🔴 các occasion]. Nút "✨ Đề xuất danh mục" (F2) + "🎯 Tạo đợt".
- **Hub detail** (bấm vào 1 campaign): 10 mục mục 3 — tái dùng/ mở rộng `renderCampDetail` (M-F F1b) +
  kanban task (F3). Always-on detail: ẩn window/SMART, hiện pillars + link calendar; Occasion: như M-F.
- **Lịch nội dung**: giữ — always-on track = "content của campaign Branding"; occasion band = campaign đợt.

## 7. Phạm vi & thứ tự
- **G1 — Hợp nhất UI**: hiện always-on như 1 card "Branding" trong danh sách campaign + hub detail đọc
  dữ liệu sẵn có (pillars/channels/calendar/tasks). Ít đụng data (virtual always-on).
- **G2 — Bổ thành phần hub còn thiếu**: brand brief (big idea/key message) + kênh-vai-trò + KPI + rủi ro
  + lineage + % tiến độ. Sinh/lưu khi cần.
- **G3 — Polish**: task brand cho always-on, badge lineage lệch nguồn (nối N-07), v.v.

## 8. Mở / cần founder chốt
- [ ] Q1: Always-on = **virtual** (derive, không DB row — đề xuất) hay tạo **row campaigns_v2 thật**?
- [ ] Q2: Brand brief = **sinh riêng 1 LLM call** (big idea/key message) hay **trích mục Định-vị** của synthesis?
      → đề xuất: sinh nhẹ 1 call (sắc hơn), KHÔNG SMART.
- [ ] Q3: Always-on có **bộ task deliverable** (posts/video/ugc) như occasion không? → đề xuất: CÓ (nhẹ).
- [ ] Q4: Hub detail = **trang riêng** hay **modal** (như campCard hiện tại)? → đề xuất: trang riêng (gọn, đủ chỗ 10 mục).
- [ ] Q5: Thứ tự **G1 trước** (hợp nhất UI) rồi G2/G3? → đề xuất: đúng vậy.
