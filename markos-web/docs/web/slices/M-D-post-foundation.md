# SPEC — M-D: Lớp NỀN cho post (học từ bot, áp vào web)

> Founder (2026-06-22): "từ content pillar sẽ hơi khác 1 chút để làm nền tảng cho post" —
> đọc bot rồi lên KẾ HOẠCH áp vào web. CHƯA code. Không sửa agents/ (bot = tham khảo).

## 1. Khác biệt (bot vs web hiện tại)
- **Web (phẳng):** pillar → chọn 1 "angle" (chuỗi topic) → viết bài.
- **Bot (nhiều tầng):** pillar → Pillar Breakdown (%/số bài/3 angle/framework) → **Story Arc**
  (mạch Awareness→Proof→Offer theo tuần) → mỗi bài = **Content angle (góc khai thác) × Hook
  style (cách mở)** + nhóm khách + funnel + format → mới viết.
- Lỗi khái niệm ở web: `angles` đang là TOPIC, trộn lẫn "góc khai thác" và "cách mở".

## 2. Mô hình nền MỤC TIÊU cho web (1 post sinh ra từ)
```
Pillar (vai + funnel + framework ưu tiên)
  └─ Story-arc week theme (awareness→proof→offer, suy từ horizon + posture)
       └─ Content angle  (góc khai thác — value lens, theo funnel)   ┐
       └─ Hook style     (cách mở — 5 nhóm)                          ├─→ gen_calendar_post
       └─ Audience group (Mới/Active/Nguy cơ/VIP)  [tùy chọn]        ┘
```

## 3. Kế hoạch theo PHA (tăng dần, ưu tiên giá trị/chi phí)

### Pha 1 — Làm giàu NỀN ở pillar *(rẻ, giá trị cao)* ⭐
- `campaign_plan` schema pillar thêm: `framework` (PAS/AIDA/BAB/FAB — LLM chọn theo vai trụ),
  tách `angles` (giữ = TOPIC gợi ý) KHÔNG đổi, **thêm `value_lens`** (góc khai thác chuẩn:
  Pain/Outcome/Social-proof/Aspiration/Objection/USP/Urgency/Authority) cho từng trụ.
- `save_pillars` giữ thêm `framework`, `value_lens`.
- calendar slot kế thừa `funnel` (có) + `framework` + `value_lens` của trụ.
- gen_calendar_post nhận thêm các trường này → bài bám đúng góc + đúng framework (ẩn).
→ Hệ quả: post grounded hơn ngay, KHÔNG đổi UX.

### Pha 2 — 2 TRỤC trong modal slot *(vừa — phần tương tác)* ⭐
- Modal slot hiện cho chọn "💡 Chủ đề" (topic). THÊM:
  - **Góc khai thác** (value lens) — mặc định theo trụ, cho đổi.
  - **Cách mở (Hook style)** — 5 nút (Tò mò/Trái ngược/Cảm xúc/Chuyên gia/Đồng cảm).
- gen_calendar_post nhận `value_lens` + `hook_style` đã chọn → ghép đúng "1 angle × 1 hook"
  như bot. (Prompt đã có 5 hook sẵn từ commit trước — giờ cho founder CHỌN thay vì để LLM tự.)
→ Hệ quả: founder cầm cương "góc + cách mở", đúng tinh thần bot.

### Pha 3 — Story Arc theo tuần *(lớn — biến lịch thành MẠCH kể)*
- Suy theme mỗi tuần từ horizon + posture: vd 4 tuần = Awareness→So sánh→Proof→Offer;
  90 ngày = arc dài hơn. Mỗi tuần có funnel focus + mục tiêu.
- Hiển thị banner/ό theme đầu mỗi tuần ở Lịch; slot kế thừa week-theme → feed gen.
- Cân nhắc: dùng LLM sinh arc 1 lần (lưu intake_extra.story_arc) hay suy deterministic
  từ posture. → bàn lúc làm.
→ Hệ quả: bài nối nhau tiến, không rời rạc (điểm mạnh nhất của bot).

### Pha 4 — Nhóm khách (audience mix) *(tùy chọn, sau)*
- Gắn nhóm khách (Mới/Active/Nguy cơ/VIP) + % cho slot; feed gen để chỉnh giọng/CTA.
- Với founder nhỏ chưa có data khách → có thể để "Mới" mặc định, mở rộng sau.

## 4. Khuyến nghị
- **Làm Pha 1 + Pha 2 trước** (nền pillar giàu + 2 trục trong modal) — đúng "nền tảng cho
  post" Sếp nói, chi phí vừa, không phá UX.
- **Pha 3 (Story Arc)** làm kế tiếp — đây là thứ khiến lịch thành mạch kể (giá trị lớn nhưng nặng hơn).
- **Pha 4** để sau / khi có dữ liệu khách.
- Đồng bộ thuật ngữ: đổi nhãn web "angle" → **"Chủ đề"** (topic) + thêm **"Góc khai thác"** +
  **"Cách mở"** cho rõ 3 thứ khác nhau.

## 4b. ĐÃ TRIỂN KHAI Pha 1 + 2 (2026-06-22)
- Pha 1: `campaign_plan` pillar thêm `framework` (PAS/AIDA/BAB/FAB/Star-Story) + `value_lens`
  (góc khai thác chuẩn); `save_pillars` giữ 2 field; `calendar_plan` slot kế thừa
  funnel + framework + value_lens.
- Pha 2: modal slot thêm 2 select **Góc khai thác** (value_lens, mặc định theo trụ) +
  **Cách mở (hook)** (Tự động + 5 nhóm); `gen_calendar_post(value_lens, hook_style, framework)`
  ép góc + ép hook (nếu chọn) + khung ẩn. API calendar/gen nhận 3 trường.
- FE: app.js + standalone + CSS .slot-axes. Verify node/import OK.

## 5. Mở / cần chốt
- [ ] Làm Pha 1+2 trước? (khuyến nghị)
- [ ] Story Arc (Pha 3): deterministic theo posture hay LLM sinh + lưu?
- [ ] Có cần Audience group (Pha 4) cho tệp founder nhỏ không?
- [ ] Gắn M-D này vào trước hay sau khi làm C đầy đủ (kéo-thả)? (đề xuất: M-D trước vì nó
      cải thiện chất lượng post — thứ founder thấy ngay; C là tiện ích sửa lịch.)
