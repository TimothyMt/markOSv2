# SPEC — M4 Wayfinding (luồng "bạn đang ở đâu → bước tiếp")

> Spec-driven. Founder nêu (2026-06-21): nhầm nút "→ Lập chiến dịch" tưởng là tạo lại
> chiến lược. Chốt: **viết spec trước, chưa code.** Tham khảo pattern UI/UX sản phẩm nổi tiếng.

## 0. Vấn đề (gốc, không chỉ là cái nút)
App là **đường ống 5 chặng** (nav ①→⑤): ①Hồ sơ → ②Chiến lược → ③Sản xuất → ④Vận hành → ⑤Học hỏi.
Nhưng mỗi trang là 1 ốc đảo — **không có chỉ dấu "bạn đang ở đâu / bước tiếp là gì".**
Triệu chứng cụ thể (founder gặp thật) ở trang **Chiến lược tổng hợp**:
1. Không có "you are here" trong luồng → không biết đã xong gì, làm gì tiếp.
2. Header 2 nút ngang hàng (`🔨 Tactical Playbook` + `→ Lập chiến dịch`) + nút `↻ Tạo lại`
   bên trong → **không phân cấp**, không rõ nút nào là việc CHÍNH.
3. Nhãn `Lập chiến dịch` mô tả **điểm đến**, không mô tả **việc/bước** → dễ tưởng "tạo lại chiến lược".
   Thêm: "chiến **lược**" vs "chiến **dịch**" gần giống nhau.

> 🔑 Đã có sẵn "bộ xương" nhưng KHÔNG dùng: `M.journey[]` + `journeyMini()` + CSS `.stepper`
> hiện chỉ render ở trang Max chat cũ — mà trang đó đã bị gỡ (route `home/chat → dossier`).
> `journey[].execution.page = 'content'` là link CŨ (trang content đã gỡ ở M3.1) → cần sửa `calendar`.

## 1. Làm rõ hiểu lầm (founder hỏi: "mỗi bản 1 kế hoạch hả?")
**KHÔNG.** Synthesis + Playbook là 2 tài liệu **bổ trợ**, cùng đổ về **MỘT** bước Lập chiến dịch →
**MỘT** kế hoạch chạy. Thẻ "Bước tiếp" chỉ là **biển chỉ đường**, không nhân bản kế hoạch.

```
   ② CHIẾN LƯỢC (2 tài liệu bổ trợ)
   ┌─────────────────────┐     ┌─────────────────────┐
   │ 🎯 Chiến lược (sync) │     │ 🔨 Tactical Playbook │
   │  = la bàn ĐỊNH HƯỚNG │     │  = cách ĐÁNH chi tiết│
   └──────────┬──────────┘     └──────────┬──────────┘
       "Bước tiếp →"               "Bước tiếp →"
              └───────────┬───────────────┘
                          ▼   (cùng đổ về 1 chỗ)
            ┌──────────────────────────────┐
            │  ③ LẬP CHIẾN DỊCH (1 nơi)    │  ← 1 KẾ HOẠCH duy nhất
            │  3 tuyến: Always-on / Dịp /  │
            │  Giữ chân → Lịch nội dung    │
            └──────────────────────────────┘
```

## 2. Tham khảo pattern sản phẩm nổi tiếng
| Sản phẩm | Pattern | Học gì |
|---|---|---|
| Stripe / Vercel onboarding | Stepper tiến trình đánh số, chặng hiện tại sáng | "Bạn đang ở đâu" |
| Shopify Admin · HubSpot | Setup guide / Next best action — luôn nổi 1 việc kế | Hợp người KHÔNG chuyên, giảm tê liệt lựa chọn |
| Notion / Linear | Breadcrumb + nudge cuối tài liệu | Gợi ý việc tiếp NGAY tại chỗ vừa xong |
| Duolingo | Learning path — luôn rõ "bài kế" | Mental model 1 đường đi cho người mới |
| Apple HIG / Material | 1 primary CTA mỗi màn | Phân cấp nút chính/phụ/phá hủy |

## 3. Ba ý tưởng (nhẹ → mạnh)

### 🅐 Phân cấp nút + nhãn "Bước tiếp" *(nhẹ, ~30')*
Trị đúng triệu chứng. Trang Chiến lược (và Playbook):
```
HIỆN TẠI:  [🔨 Tactical Playbook]  [→ Lập chiến dịch]     ← ngang hàng, mơ hồ
ĐỀ XUẤT:   [↻ Tạo lại] [🔨 Playbook]   [→ Bước tiếp: Lập chiến dịch]
           └─ ghost/phụ ─┘              └─ PRIMARY, to, có chữ "Bước tiếp" ─┘
```
Ref: Apple HIG — mỗi màn 1 primary; regenerate là phụ.

### 🅑 Thẻ "Bước tiếp theo" cuối mỗi tài liệu *(vừa, ~2h)* — **fix mạnh nhất**
Dải nổi cuối doc, trả lời đúng chỗ phát sinh nhầm:
```
┌──────────────────────────────────────────────────────────┐
│  ✓ Chiến lược 90 ngày đã xong.                            │
│  Bước tiếp → biến nó thành kế hoạch chạy thật:            │
│        [ → Lập chiến dịch ]  (primary)                    │
│  Hoặc: 🔨 Tactical Playbook · ↻ Tạo lại bản mới          │
└──────────────────────────────────────────────────────────┘
```
- Cuối **Chiến lược (synthesis)**: "✓ Đã có la bàn. Tiếp: chi tiết hóa bằng Playbook (phụ) → **Lập chiến dịch** (chính)".
- Cuối **Tactical Playbook**: "✓ Đã có cách đánh. Tiếp: **Lập chiến dịch** (chính)".
- Cả hai mũi tên chính trỏ **cùng** nút Lập chiến dịch (#occasion). KHÔNG nhân bản kế hoạch.

Ref: HubSpot/Shopify "next best action", Notion nudge cuối trang.

### 🅒 Hồi sinh thanh tiến trình "bạn đang ở đây" toàn app *(lớn, ~half-day)*
Đưa `journeyMini()` lên đầu MỌI trang làm việc (không chỉ chat):
```
🔍 Hồ sơ ─✓─› 🩺 Chẩn đoán ─✓─› 🎯 Chiến lược ──[●]── ✍️ Sản xuất ──○── 📡 Vận hành
                                   bạn đang ở đây
```
- Map stage → page theo nav thật; click stage = nhảy trang.
- Trạng thái done/current/pending suy từ skill_runs thật (đã có pattern `M.bizLatest`).
- Cần sửa `journey[].execution.page` 'content' → 'calendar' (link cũ M3.1).
Ref: Stripe onboarding, Duolingo path. Có sẵn code + CSS → chi phí thấp hơn vẻ ngoài.

## 4. Khuyến nghị & phân kỳ
- **M4.1 = 🅐 + 🅑** (trị đúng chỗ nhầm, chi phí thấp). ƯU TIÊN. → ✅ ĐÃ LÀM (2026-06-21).
- **M4.2 = 🅒** (bản đồ tổng) — đã demo nhưng founder thấy "thô", **HOÃN**, tìm cách hợp hơn sau.
- Nguyên tắc: 1 primary CTA/màn; nhãn mô tả VIỆC không mô tả điểm đến; "next step" đặt nơi vừa hoàn thành.

### Đã triển khai M4.1 (🅐+🅑)
- 🅐 Header phân cấp: nhãn primary đổi `→ Lập chiến dịch` → **`→ Bước tiếp: Lập chiến dịch`**
  (mô tả BƯỚC, hết nhầm với "tạo lại"). Trang Tactical thêm primary cùng đích.
  Regenerate giữ nguyên dạng ghost/phụ.
- 🅑 `nextStepCard()`: thẻ "Bước tiếp theo" cuối **cả** trang Chiến lược (synthesis) và
  Tactical Playbook — **cùng** trỏ về `#occasion` → nhấn mạnh "1 kế hoạch, không tách lẻ".
- Áp ở `web/app.js` + `web/styles.css` (.nextstep) và bản gộp `dashboard-standalone.html`.
- Ảnh xem trước: `M4-ab-preview.png`.

## 5. Chưa làm / cần chốt
- [ ] Founder duyệt hướng (spec này) trước khi code.
- [ ] M4.1: chính xác wording thẻ "Bước tiếp" cho từng trang (synthesis vs playbook).
- [ ] M4.2: có làm stepper toàn app không, hay chỉ nhóm ②③.
- Ngoài phạm vi: gamification kiểu Duolingo (badge/streak), command palette (Linear ⌘K).
