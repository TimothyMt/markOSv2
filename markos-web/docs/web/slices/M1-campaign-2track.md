# SPEC — M1 Campaign 2 tuyến: Always-on + Occasion (D-040)

> Spec-driven. Giai đoạn: **Specify + build entry**. Đi từ MARKETING HIỆN ĐẠI,
> không dựa codebase. Industry-aware (15 ngành trong `frameworks/industry_context.py`).
> Nền: D-017/018 (2 track, always-on không tắt), D-029/030 (SMART chỉ ở occasion),
> D-038 (Synthesis = la bàn TRÊN cả 2 track), D-031 (Tactical Playbook = xương always-on).

## 1. Vì sao 2 tuyến (cơ sở marketing)
- **Byron Sharp (How Brands Grow):** phần lớn khách KHÔNG ở trạng thái mua tại bất kỳ
  thời điểm nào → phải hiện diện LIÊN TỤC để được nhớ khi họ vào thị trường (mental
  availability). → cần **Always-on**.
- **Les Binet & Peter Field (The Long and the Short of It):** tăng trưởng bền = ~**60%
  brand-building (dài hạn, reach rộng, cảm xúc)** + **40% activation (ngắn hạn, bán)**.
  Always-on gánh phần nền; **Occasion** tạo các *spike activation*.
- **D-018:** 2 tuyến chạy SONG SONG — occasion CỘNG THÊM, không thay always-on.

## 2. ALWAYS-ON (nền — chạy quanh năm)
**Là gì:** hiện diện thương hiệu + bắt nhu cầu đều đặn, KHÔNG gắn sự kiện. Mục tiêu:
salience (được nhớ) + nuôi khách qua phễu liên tục.

**Dựa vào đâu để ra TUYẾN BÀI (content pillars):**
1. **USP + SAVE** (Synthesis) → thông điệp lõi lặp lại nhất quán.
2. **JTBD + Pain/Gain + Customer Journey** (Customer Insight) → nội dung phục vụ "job"
   của khách ở cả 3 nhiệt độ (cold/warm/hot).
3. **Archetype mua hàng** (lib) → quyết định *STYLE pillar*:
   - `trust_building` → authority/educate, long-form (blog/case/LinkedIn), nuôi tin trước.
   - `demand_gen` → khơi desire/lifestyle, video-first (TikTok/Reels), social proof UGC.
   - `impulse` → hook scroll-stop, social proof định lượng, offer/urgency, paid+live.
4. **Wedge segment** (gate) → pillar nói trúng tệp ưu tiên.
→ **Tuyến bài = 4-6 content pillars**, mỗi pillar có: vai (giáo dục / social proof /
   giá trị sản phẩm / hậu trường-thương hiệu / cộng đồng / chuyển đổi), tầng phễu
   (TOFU/MOFU/BOFU), cadence (mấy bài/tuần), 2-3 góc bài mẫu.
**Theo ngành:** mix pillar + kênh + cadence bám archetype + market_dynamics (vd fnb
hyperlocal → Google Maps/TikTok review-led; tech_saas → blog/case/LinkedIn authority).
**KHÔNG chốt SMART** — always-on là nền (D-029).

## 3. OCCASION (đợt — theo dịp, có window)
**Là gì:** đợt chiến dịch có thời hạn, gắn 1 trigger: mùa vụ (Tết, 8/3, 20/10, 11.11,
Black Friday), ra mắt sản phẩm, promo. Mục tiêu: *activation spike* ngắn hạn, chồng
LÊN always-on.

**Dựa vào đâu:**
1. **Trigger + mùa vụ NGÀNH** (lib `market_dynamics` ghi rõ mùa vụ từng ngành) → chọn
   dịp đáng đánh + thời điểm.
2. **Giai đoạn roadmap Synthesis** đang ở đâu → mục tiêu định hướng của đợt.
3. **Wedge + USP** → góc đánh đợt.
4. → **CHỐT SMART thật** (số, ngân sách đợt, deadline) vì giờ đủ lever (dịp/window/
   baseline) — D-029. Pre-fill từ roadmap (như bot `campaign_intake`).
→ **Cấu trúc đợt = arc:** teaser → build-up → peak (ngày dịp) → last-call → after-sale.
**Theo ngành:** mỗi ngành có lịch dịp đặc trưng (fnb: Tết/hè/cuối tuần; fashion: BST
mùa + 8/3 + 20/10 + 11.11; education: mùa tuyển sinh; real_estate: đợt mở bán; health_
beauty: hè/cận Tết; v.v. — suy từ market_dynamics + lịch VN).

## 4. Hành trình khách × 2 tuyến
| Nhiệt độ | Always-on (liên tục) | Occasion (spike tại moment) |
|---|---|---|
| Cold (chưa biết) | pillar TOFU đều đặn (reach, educate/desire) | hook dịp kéo aware mới |
| Warm (cân nhắc) | pillar MOFU (so sánh, social proof, Fit/demo) | build-up + ưu đãi đúng lúc cân nhắc |
| Hot (sắp mua) | pillar BOFU + retarget thường trực | peak + last-call + urgency thật |
| Retain | cộng đồng/loyalty đều | after-sale + winback quanh dịp |
→ Always-on phủ TOÀN hành trình; Occasion tạo SPIKE → kéo warm→hot + hút aford mới.

## 5. UI/UX (dễ nhìn)
Trang **"Lập chiến dịch"** (#occasion) = HUB rẽ 2 thẻ rõ ràng:
- 🟢 **Always-on (nền)**: hiện **content pillars sinh ra** (tuyến bài) + cadence + nguồn
  (bám USP/JTBD/archetype/wedge) + kênh theo ngành. CTA "→ Đưa vào Lịch nội dung".
  Ghi rõ: "đây là *nền*, không chốt số."
- 🔴 **Theo dịp (Occasion)**: **gợi ý dịp sắp tới THEO NGÀNH** (từ mùa vụ lib) + nút
  "Tạo chiến dịch theo dịp" → luồng chốt SMART (kế thừa roadmap). Phần creation đầy đủ
  = M1 lớn, lần này entry trung thực.
- Banner trên cùng: "Synthesis = la bàn TRÊN cả 2 tuyến; chúng chạy song song."

## 6. Phạm vi build lần này (đợt qua đêm)
- ✅ Spec logic (file này).
- ✅ Endpoint web sinh **content pillars (always-on) + gợi ý occasion theo ngành** từ
  Synthesis + Tactical + industry context (1 LLM call, cache). Chống bịa, degrade {}.
- ✅ Hub UI 2 thẻ (web-only), industry-aware, trung thực (occasion creation = placeholder).
- ⏳ Để sau (M1 lớn): luồng tạo occasion đầy đủ (pre-fill SMART từ roadmap, lịch nội dung
  inline D-019, Gantt D-020).

## 7. Boundaries
- ALWAYS: 2 tuyến song song; always-on KHÔNG chốt SMART; occasion mới chốt SMART; bám
  archetype + market_dynamics theo ngành; không nút giả (D-008).
- ASK FIRST: build luồng tạo occasion đầy đủ (M1 lớn, spec riêng).
- NEVER: gộp 2 tuyến; để always-on trống khi có occasion; chốt SMART ở always-on.
