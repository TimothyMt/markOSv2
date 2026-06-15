# 📈 SCALE BACKLOG — làm khi scale / chuẩn bị bán cho C-level & Agency

> Note theo yêu cầu (2026-06-15): các hạng mục lớn để dành cho giai đoạn scale.
> Chưa làm bây giờ; nhắc lại khi user bảo "chuẩn bị scale / lên gói / bán".

## #2 — Economics / Feasibility gate
**Vấn đề:** chốt segment+positioning xong nhưng không tính ngược goal × budget × CAC →
kế hoạch có thể bất khả thi mà không ai biết (demo: synthesis set CAC/demo target chưa reconcile).
**Hướng làm:** thêm **câu hỏi thứ 7** ngay sau pricing trong chuỗi quyết định chiến lược:
- Input: `monthly_marketing_budget` (user) + CAC benchmark (`kpi_library`) + goal.
- Tính bằng **Python** (không để LLM bịa số): `budget ÷ CAC = số khách dự kiến` → so goal.
- Output thẻ: "khả thi / cần tăng budget lên Z / cần hạ mục tiêu".
- Gắn nhãn real (user) vs benchmark (kpi_library) vs cần đo.

## #4 — Measurement loop (đóng vòng)
**Vấn đề:** flow chạy 1 chiều rồi dừng — không có publish→đo→học→re-plan. `ads_analytics`
là tool rời, không có mũi tên ngược về strategy/calendar. → đang là "generator", chưa là "OS".
**Hướng làm:** nạp kết quả thật (dù tay) của chu kỳ trước → feed vào calendar chu kỳ sau +
reallocate budget theo kênh/nội dung đang work. Đây là thứ nâng tool → marketing OS.

## #5 — Strategy Object + 3 skin (Owner / C-level / Agency)
**Vấn đề:** 1 output chung cho 3 đối tượng nhu cầu khác hẳn.
**Hướng làm:** 1 **Strategy Object** (segment/positioning/pricing/funnel/economics = data có
cấu trúc, sửa được) → render 3 skin từ cùng nguồn:
- Owner → checklist "tuần này làm gì"
- C-level → exec 1 trang + số bảo vệ được
- Agency → workspace + deck export + multi-tenant + edit assumption (cần RLS — xem LAUNCH_CHECKLIST)
**KHÔNG** xây 3 engine — chỉ 1 data model + 3 lớp trình bày + lớp quyền.

---
_Liên quan: docs/LAUNCH_CHECKLIST.md (security gate trước khi mở thương mại)._
