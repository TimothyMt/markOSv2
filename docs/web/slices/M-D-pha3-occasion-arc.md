# SPEC — M-D Pha 3: Story Arc cho OCCASION trên lịch (occasion arc)

> Founder (2026-06-22): làm spec Pha 3. Bối cảnh: có cả Always-on (chạy nền mãi) lẫn
> Occasion (đợt có window). Kết luận phân tích: Story Arc thuộc về OCCASION, KHÔNG ép vào
> always-on. CHƯA code. Không sửa agents/.

## 1. Nguyên tắc — 3 tầng thời gian, mỗi tầng 1 logic
```
Roadmap (chiến lược, theo horizon) = MACRO arc — hướng từng giai đoạn (đã có ở synthesis)
   └─ Occasion (đợt, có window)     = MESO arc  — Teaser→Build-up→Peak→Last-call→After
        + Always-on (nền chạy mãi)  = DRUMBEAT — KHÔNG leo đỉnh; chỉ cân nhịp funnel (đã ổn sau Pha 1+2)
```
- Always-on ép vào arc kết-bằng-Offer = phá mô hình Byron Sharp → KHÔNG làm.
- Occasion ĐÃ là arc (occasion_draft sinh sẵn 5 pha trong brief) → chỉ cần ĐƯA LÊN LỊCH + sinh bài THEO PHA.

## 2. Hiện trạng & lỗ hổng
- `occasion_draft` (web) sinh brief markdown có "## 2. Arc 5 pha theo timeline" (Teaser→…→After)
  → lưu skill_run `occasion_brief`, ref qua `campaigns_v2.brief_skill_run_id`.
- `calendar_plan` map campaign window → tuần, nhưng chỉ tạo **3 bài generic** cứng:
  "Khởi động / Đẩy mạnh / Chốt — ngày cuối" (business.py ~bands). KHÔNG bám 5 pha thật.
- Bấm tạo bài campaign (`gen_calendar_post track=camp`) đọc cả brief nhưng KHÔNG biết bài thuộc PHA nào.
→ Thiếu: (a) 5 pha hiện trên lịch theo đúng vị trí window; (b) bài campaign sinh bám đúng pha.

## 3. Thiết kế

### 3.1 Suy 5 pha theo window (deterministic — không parse, không LLM)
Pha cố định + tỉ lệ vị trí trong window (start→end):
| Pha | Vai | Vùng window |
|---|---|---|
| 🌱 Teaser (hé lộ) | gây tò mò, chưa lộ offer | 0–18% |
| 🔥 Build-up (nuôi) | giá trị, social proof, xử lý phản đối | 18–55% |
| 🚀 Peak (đỉnh/ngày dịp) | đẩy mạnh nhất | 55–72% |
| ⏰ Last-call (chốt gấp) | urgency, deadline | 72–90% |
| 💌 After (hậu mãi/winback) | cảm ơn, upsell, kéo lỡ | 90–100% |
- Map mỗi pha → (tuần, ngày) trong window bằng `_week_of`/anchor như bands hiện có.
- Window ngắn (1 tuần) → nén: gộp Teaser+Build-up đầu tuần, Peak giữa, Last-call+After cuối.
- Mỗi đợt có thể nhiều bài/pha tùy độ dài (>= 1 beat/pha; pha dài có 2 beat).

### 3.2 calendar_plan — thay 3 bài generic bằng beat theo pha
- Trong vòng tạo `bands`: thay `posts=[Khởi động/Đẩy mạnh/Chốt]` bằng beats suy từ 3.1:
  mỗi beat = `{week, day, phase, title}` (title = "🔥 Build-up — {tên đợt}").
- Mỗi occasion slot mang: `track:'camp'`, `campaignId`, `briefRunId`, `phase`, `key` (vd
  `oc|{campId}|{phase}`), + `saved/post` (tái dùng cơ chế lưu-tại-ô M-C).

### 3.3 gen_calendar_post (camp) — bám PHA
- Thêm param `phase`. Prompt occasion thêm: "Bài thuộc PHA: {phase} — mục tiêu pha: {hint}".
  Phase hint cố định (Teaser=gây tò mò chưa lộ offer; Peak=đẩy mạnh; Last-call=urgency+deadline…).
- Vẫn đọc brief (đã có) để bám SMART/offer của đợt.
- Tái dùng 2 trục Pha 2 (value_lens/hook) nếu muốn — mặc định suy theo pha.

### 3.4 UI lịch
- **View tháng**: band occasion hiện chuỗi pha theo tuần (🌱🔥🚀⏰💌) thay vì 1 ô chung.
- **View tuần**: ô campaign mỗi ngày hiện nhãn pha; bấm → modal (giống slot always-on) nhưng
  header = "{Pha} · {tên đợt}", body cho chọn chủ đề/hook → tạo bài bám pha → sửa/Lưu & Duyệt
  (tái dùng openSlotModal/showSlotResult + slot-save của M-C, key = `oc|...`).
- Legend thêm dòng giải thích 5 pha.

### 3.5 API
- `calendar/gen` thêm `phase` (đã có sẵn các field khác). Lưu bài: tái dùng `calendar/post-save`
  với slot_key occasion.

## 4. (Tùy chọn) Always-on — theme tháng MỀM từ roadmap
- KHÔNG arc. Chỉ banner gợi ý mỗi tuần/tháng kế thừa **roadmap phase** của synthesis
  (vd "Giai đoạn 1: gây nhận biết") để always-on hơi nghiêng theo — KHÔNG ép climax.
- Để cờ riêng, làm sau nếu thấy cần. Mặc định KHÔNG bật.

## 5. Phạm vi & thứ tự
- Lõi Pha 3 = 3.1→3.4 (occasion arc trên lịch + sinh bài theo pha). Tái dùng tối đa hạ tầng M-C.
- KHÔNG đụng always-on (giữ nguyên Pha 1+2).
- Web-owned; không sửa agents/.

## 6. Mở / cần chốt
- [ ] Tỉ lệ 5 pha (bảng 3.1) ok chưa, hay cho founder chỉnh?
- [ ] Window ngắn (≤1 tuần): nén 5→3 pha (Teaser/Peak/Last-call) có hợp không?
- [ ] Có làm theme tháng mềm cho always-on (mục 4) trong đợt này không? (đề xuất: KHÔNG, để sau)
- [ ] Occasion slot có cần 2 trục (value_lens/hook) như always-on, hay chỉ chọn pha + chủ đề?
