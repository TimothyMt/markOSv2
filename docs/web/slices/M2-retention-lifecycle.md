# SPEC — M2 Retention / Lifecycle (tuyến behavior-triggered)

> Spec-driven. Giai đoạn: **Specify → chờ duyệt build**. Đi từ marketing hiện đại,
> TÁI DÙNG engine bot (skills `retention_strategy` + `winback_campaign` đã có — KHÔNG
> nhân bản logic). Industry-aware (15 ngành). Nền: D-040 (2 tuyến WHEN) · D-043 (occasion) ·
> D-044 (trục mục đích WHY là tag, không phải tuyến) · D-029 (SMART) · D-008 (không UI giả).

## 0. Vì sao Retention là MODULE RIÊNG (không gộp vào occasion)
Hai trục khác nhau — đừng trộn:
- **Trục WHEN (kích hoạt):** Always-on (liên tục) ↔ Occasion (đợt có window). → đã có (M1).
- **Trục WHY (mục đích):** brand · acquisition · conversion · **retention/winback**. → tag (D-044).

Brand/acquisition/conversion đã được Always-on + Occasion phục vụ tốt. **Retention/Winback
thì KHÔNG** — vì nó **kích hoạt bởi HÀNH VI khách**, không phải lịch/dịp:

| | Occasion (M1) | Retention/Lifecycle (M2) |
|---|---|---|
| Kích hoạt | Lịch/dịp (window cố định) | **Hành vi/vòng đời khách** (vừa mua / im ắng / lapsed) |
| Tệp nhắm | Mở (thường khách mới) | **Tệp đã có quan hệ** (đã mua ≥1 lần) |
| Cấu trúc | Arc 5 pha theo timeline | **Flow theo lifecycle stage** (trigger → chuỗi chạm) |
| KPI | ROAS/CPA/lead | **Repeat rate · AOV · CLV · churn** |
| Cơ chế | Burst ngân sách | Owned media (CRM/Zalo/email) — rẻ, ít đốt ads |

→ Gộp vào occasion sẽ méo cả 2. Tách riêng, nhưng **cùng hệ** (vẫn kế thừa Synthesis là bàn).

## 1. KHÔNG cần order data — M2.1 là CẨM NANG if-then (Founder quyết 2026-06-21)
> 🔴 **Quyết định chốt:** M2.1 làm được **HOÀN TOÀN KHÔNG cần dữ liệu đơn hàng.** Tách 2 việc:
> - **Biết phải làm gì** trong mỗi tình huống khách → **KHÔNG cần data** (Max sinh playbook). ✅ M2.1
> - **Tự phát hiện** khách nào đang ở tình huống nào → cần RFM data. ⏳ để Mức B sau.

Không có data thì Max **không tự dò** "khách nào sắp rời bỏ" — nhưng **founder tự nhìn ra được**
("chị này 3 tuần không quay lại"). Việc của Max = đưa **cẩm nang if-then**: *tình huống (dấu
hiệu nhận biết) → nên làm gì → kênh → mẫu tin*. Founder đối chiếu khách của mình rồi áp tay.

- **Mức A — Playbook if-then (M2.1, MVP):** engine skill `retention_strategy`
  (`PROFILE_PLUS_STRATEGY`) + `winback_campaign` từ profile + Synthesis → **bảng cẩm nang**
  theo lifecycle stage: dấu hiệu nhận biết + hành động + kênh owned + tin mẫu + KPI. Founder
  tự nhận diện & gửi thủ công. **Không cần 1 dòng data.**
- **Mức B — Data-driven (sau):** kết nối nguồn đơn hàng → tự phân tệp RFM → tự phát hiện +
  cá nhân hoá threshold. Cần Sheet/Pancake/Sapo/Haravan — **ngoài M2.1.**

> 🔴 D-008: threshold thời gian ("im ắng ~3 tuần", "lapsed > 2 tháng") để dạng "≈ X× chu kỳ
> mua trung bình NGÀNH" + nhãn **(ước tính)** — founder chỉnh khi thấy thực tế khác. KHÔNG bịa
> số đo lường. Thành thật về giới hạn: gửi tin THỦ CÔNG (founder tự chọn ai, tự gửi) ở M2.1.

## 2. Lifecycle stages (khung chuẩn, industry-aware)
`Khách mới → Active/Repeat → At-risk (chậm lại) → Churned/Lapsed → Win-back`.
Trọng số theo archetype ngành (15 lib):
- `impulse` (F&B tần suất cao): retention = **xương sống** (frequency là tiền) → nặng
  Active/Repeat, nhịp dày, loyalty/combo.
- `trust_building` (AOV cao, mua thưa): retention chậm → nặng **after-sale + referral**
  (khách hài lòng giới thiệu) hơn là ép mua lại.
- `demand_gen`: cân bằng — nurture giữa các lần mua.

## 3. Kế thừa gì (KẾ THỪA = MẶC ĐỊNH, KHÔNG LOCK — như M1)
> 🔴 Founder giữ toàn quyền. Mọi giá trị dưới là **pre-fill**, sửa/đè được hết.
- **Từ Synthesis (la bàn):** USP, wedge, giai đoạn roadmap → định hướng retention.
- **Từ profile:** ngành (→ archetype, chu kỳ mua điển hình), kênh owned (Zalo OA/email/SMS).
- **Từ Ads/occasion đã lưu:** khách đến từ đợt nào → nuôi tiếp (nối M1 → M2).

## 4. Luồng người dùng (M2.1 — MVP, mức A)
Tương tự wizard occasion (D-043), nhưng "lever" là **lifecycle** thay vì window:
1. **Chọn loại:** `Giữ chân & tăng tần suất (retention)` | `Kéo khách cũ quay lại (winback)`.
2. **Lever nhẹ:** chu kỳ mua điển hình (vd "30 ngày" — trống thì suy theo ngành) ·
   kênh owned đang có (Zalo/email/SMS) · ưu đãi loyalty nếu có.
3. **Max sinh playbook:** gọi engine skill thật (`retention_strategy`/`winback_campaign`)
   web-side (reuse, KHÔNG nhân bản) → Markdown: stages + trigger + sequence chạm + nội
   dung mẫu + KPI (repeat/AOV/CLV) + threshold (ước tính nếu thiếu data).
4. **Review → lưu:** skill_run (`retention_playbook`/`winback_playbook`) + record
   `campaigns` (primary_goal=`retention`, không window cố định). Tái dùng hạ tầng M1.

## 5. Tái dùng (KHÔNG nhân bản)
- Engine: `agents/operational_skills_config.py` → `make_retention_strategy_skill`,
  `make_winback_campaign_skill` (đã tồn tại). Web gọi qua agent wrapper như occasion gọi OPS_BRIEF.
- Web: pattern `business.occasion_draft/save_occasion` → `retention_draft/save_retention`;
  wizard `openOccasionWizard` → `openLifecycleWizard` (cùng khung modal + CSS `.occ-*`).
- Lưu: skill_runs + campaigns (KHÔNG migration), giống M1.

## 6. Ranh giới / phân kỳ
- **M2.1 (MVP, mức A):** wizard retention + winback playbook strategy-only. KHÔNG cần order data.
- **M2.2 (data-driven, mức B):** kết nối nguồn đơn hàng → phân tệp RFM thật → threshold cá nhân hoá.
- **M2.3 (automation):** trigger flow tự chạy (gửi qua Zalo/email khi khách chạm điều kiện) —
  cần tích hợp gửi tin; xa, chỉ ghi nhận tầm nhìn.
- **NGOÀI phạm vi M2:** không làm CDP/CRM đầy đủ; không gửi tin thật ở M2.1/2.2.

## 7. Quan hệ với M1 (occasion)
Occasion **đổ khách mới vào** → Retention **giữ & tăng giá trị**. Cùng la bàn Synthesis.
1 đợt occasion mục đích=`retention` (D-044) là *spike ngắn* nhắm khách cũ; còn M2 là
*flow liên tục theo hành vi*. Bổ sung nhau, không trùng.

## 8. Quyết định đã chốt + còn mở
- ✅ **Founder (2026-06-21):** M2.1 = **playbook if-then, KHÔNG cần order data** (mục 1). Data-driven (Mức B) để sau.
- (mở) Winback: tuyến riêng hay 1 stage trong retention playbook? → nghiêng gộp 1 module, 2 chế độ.
- (mở, cho Mức B sau) Nguồn order data: ưu tiên Google Sheet upload (rẻ, phổ biến VN) hơn tích hợp Pancake/Sapo/Haravan.
