# SPEC — M1 Luồng tạo Campaign Occasion đầy đủ (chốt SMART thật)

> Spec-driven. Giai đoạn: **Specify → chờ duyệt build**. Đi từ marketing hiện đại,
> tái dùng pattern bot (KHÔNG nhân bản logic). Industry-aware (15 ngành).
> Nền: D-029 (SMART chỉ chốt ở occasion, pre-fill từ roadmap) · D-040 (2 tuyến,
> occasion = spike) · D-041 (wedge/USP đã chọn ở gate) · D-038 (Synthesis=la bàn) ·
> D-017/018/019/020 (lịch 2-track, sinh inline, 2 view) · D-008 (không UI giả).

## 1. Occasion là gì (cơ sở marketing)
Một **đợt chiến dịch có WINDOW**, gắn 1 trigger cụ thể (dịp/sự kiện/promo/launch).
Vai trò: tạo **activation spike** ngắn hạn (Binet&Field "the short"), CHỒNG lên
always-on (D-018, nền không tắt). Khác always-on ở chỗ: **giờ ĐỦ LEVER** (dịp gì /
window bao lâu / ngân sách đợt / baseline hiện tại) → **chốt được SMART THẬT** (D-029).

**Cấu trúc 1 đợt = arc theo thời gian:**
`Teaser (hé lộ) → Build-up (nuôi) → Peak (ngày dịp, đẩy mạnh) → Last-call (chốt gấp) → After (hậu mãi/winback)`.
Mỗi pha bám **archetype ngành** (impulse → hook+urgency; demand_gen → desire+UGC;
trust_building → proof+tư vấn) và **phễu** (TOFU hút mới → BOFU chốt).

## 2. Occasion kế thừa gì (không bắt user nhập lại) — KẾ THỪA = MẶC ĐỊNH, KHÔNG LOCK
> 🔴 **Founder GIỮ TOÀN QUYỀN QUYẾT ĐỊNH.** Mọi giá trị kế thừa dưới đây chỉ là
> **pre-fill (gợi ý mặc định)** để đỡ nhập lại + giữ nhất quán với la bàn — founder
> **sửa/đè được HẾT** ở từng đợt. Vì 1 đợt có thể đánh khác chiến lược nền (vd wedge
> chính = mẹ bỉm, nhưng đợt 20/10 mở rộng ra phụ nữ công sở). **SMART số là của
> founder** — Max gợi ý từ baseline+giai đoạn, founder chốt con số cuối.

- **Từ Synthesis (la bàn):** USP, wedge segment, giai đoạn roadmap đang active → mục
  tiêu định hướng của đợt. *(pre-fill, sửa được)*
- **Từ Tactical Playbook (T5):** cách đánh per-segment (copy angle, kênh, archetype). *(gợi ý)*
- **Từ profile:** ngành (→ mùa vụ, archetype), ngân sách marketing/tháng (gợi ý ngân sách đợt). *(gợi ý)*
- **Lever do user nhập cho đợt này:** dịp + ngày/window + ngân sách đợt + baseline (số
  hiện tại nếu có) → đây là cái biến "định hướng" thành "SMART số".

**🚧 Lan can nhất quán (KHÔNG chặn, chỉ NHẮC):** nếu founder đè lệch khỏi la bàn (đổi
segment/định vị khác hẳn) → Max nhắc nhẹ *"Đợt này lệch khỏi wedge/định vị chính — chắc
chứ?"* → founder vẫn quyết, chỉ là **quyết có ý thức** (tránh đợt phá vỡ định vị thương
hiệu — sai lầm marketing kinh điển). KHÔNG block.

## 3. SMART pre-fill — TÁI DÙNG pattern bot (BẮT BUỘC, D-029)
KHÔNG tự đẻ SMART rời. Tái dùng `campaign_intake.build_campaign_draft_from_strategy`
(bot) — đọc `roadmap_90d[phase]` + budget từ JSON strategy (`CMO_STRATEGY_SYSTEM`) →
pre-fill draft. Web M1:
- Nếu đã có JSON strategy (đường tele) → dùng thẳng pattern đó.
- Nếu chỉ có Markdown synthesis (đường web) → trích giai đoạn roadmap + mục tiêu định
  hướng (web-side, giống `market_kpis`/`campaign_plan`) rồi feed vào draft.
→ SMART số = **suy từ baseline + mục tiêu giai đoạn + window**, gắn "(dựa baseline X)";
  KHÔNG bịa số khi thiếu baseline (hỏi user hoặc để khoảng + nhãn).

## 4. Hành trình tạo Occasion (UI/UX)
Từ hub "Lập chiến dịch" (D-040) → thẻ 🔴 Occasion → nút "Tạo chiến dịch theo dịp":

**Bước 1 — Chọn dịp** (industry-aware)
- Gợi ý dịp theo ngành (từ `campaign_plan.occasions` đã có) + cho tự nhập dịp.
- Chọn dịp → set **ngày/window** (mặc định gợi ý theo loại dịp: vd Tết ~3 tuần).

**Bước 2 — Lever** (cái khoá SMART)
- Ngân sách đợt (gợi ý từ % always-on vs burst + ngân sách/tháng).
- Baseline (số hiện tại: đơn/tháng, AOV... — optional, "chưa rõ" → SMART để khoảng).
- Mục tiêu chính của đợt (kế thừa giai đoạn roadmap, cho chỉnh).

**Bước 3 — Max sinh Campaign Brief đợt** (AI, 1 lần)
- Kế thừa USP/wedge/playbook + lever → sinh: **SMART goals (số thật)** + **arc 5 pha**
  (teaser→...→after) theo timeline + kênh + góc copy theo archetype + KPI có target
  (vì có baseline) + phân bổ ngân sách đợt.
- Bám mùa vụ + văn hoá ngành (vd fnb Tết; fashion 8/3).

**Bước 4 — Review & chỉnh** → lưu vào `campaigns`/`campaigns_v2` (đã có bảng).
- Sửa tay / nhờ Max chỉnh (tái dùng doc-reader như output khác).

**Bước 5 — Đưa vào Lịch** (D-019/020)
- Đợt hiện trên lịch như **lớp phủ có window** chồng lên always-on (D-018).
- Sinh nội dung từng slot inline (D-019), 2 view tháng/tuần (D-020).

## 5. Data model (tái dùng, không tạo mới nếu tránh được)
- `campaigns_v2` (đã có) lưu occasion: name, occasion_trigger, window (start/end),
  budget, smart_goals, arc/phases, status, segment(wedge), created_at, version.
- Cần xác nhận cột: nếu thiếu `occasion_trigger`/`window`/`smart_goals` → migration nhỏ
  (JSONB `campaign_meta`) thay vì nhiều cột.
- Always-on KHÔNG nằm ở đây (always-on = content pillars, không phải campaign record).

## 6. Backend (web)
- `business.py occasion_draft(user_id, occasion, window, budget, baseline)` → kế thừa
  synthesis+playbook+industry → 1 LLM call sinh draft (SMART + arc + KPI có target).
  Tái dùng/đồng bộ với bot `campaign_intake` pattern. Cache, degrade {}.
- Route POST `/api/biz/occasion`.
- Lưu draft → `campaigns_v2` qua store v2.

## 7. Phạm vi / phân kỳ
- **M1.1 — ✅ ĐÃ BUILD (2026-06-21):** Bước 1-4 (chọn dịp → lever → sinh brief
  SMART → lưu). Backend `business.occasion_draft`/`save_occasion` (web-side 1 LLM call,
  OPS_BRIEF) + route `/api/biz/occasion`(+`/save`) + FE wizard (`openOccasionWizard`).
  Lưu = skill_run `occasion_brief` + record `campaigns` (KHÔNG cần migration).
- **M1.2 (kế tiếp):** Bước 5 — Lịch nội dung 2-track (D-019/020), sinh nội dung từng slot.
- **M1.3:** Always-on activation thành lịch chạy đều (từ pillars D-040).

## 8. Boundaries
- ALWAYS: SMART chỉ ở đây (có lever); kế thừa Synthesis/Playbook (không bắt nhập lại);
  occasion CHỒNG always-on (không thay); industry-aware; tái dùng pattern bot; không số bịa.
- ASK FIRST: thêm cột campaigns; build lịch (M1.2); đụng `CMO_STRATEGY_SYSTEM`.
- NEVER: chốt SMART ở always-on; tạo SMART rời không từ baseline/roadmap; UI giả.

## 9. Quyết định đã chốt (2026-06-21, Founder)
- ✅ **Baseline khi "chưa rõ":** SMART **để khoảng + nhãn (ước tính)** — KHÔNG chặn flow.
  Sinh số dạng khoảng + gắn `(ước tính — chưa có baseline)`, founder chỉnh sau.
- ✅ **Sinh brief:** **web-side 1 LLM call** (`business.occasion_draft`, giống
  `market_kpis`/`campaign_plan`) — gọn, đồng bộ 2-phase, KHÔNG kéo dependency bot.
