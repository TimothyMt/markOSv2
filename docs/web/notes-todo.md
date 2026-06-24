# NOTES-TODO (web) — ghi chú chờ làm theo lô

> Quy ước: "note" = chỉ ghi vào đây, KHÔNG tự sửa/push code. Chỉ code khi founder nói "làm các note".

## 🔴 Bug đang mở
- **[N-01] "Đặt hiện hành" version tạo bản MỚI thay vì repoint.**
  Ở trang đọc/sửa doc (vd Market_research), bấm "Đặt hiện hành" cho v1/v2 thì thay vì
  trỏ hiện-hành về v1/v2, hệ thống **đẻ ra v3/v4** (nội dung thật vẫn là v1/v2). Đúng phải:
  set version đã chọn làm current, KHÔNG sinh version mới. (Kiểm tra logic set-current vs patch.)
- **[N-02] Giao diện bị "bóp" khi chạy lại.**
  Khi chạy lại (re-run), layout trang đọc doc — panel "Lịch sử version" bên phải — bị bóp/vỡ.
  (CSS/layout của doc reader khi có panel version history.)
- **[N-03] Competitor "độn" nội dung ICP/JTBD (scope-drift, không phải lỗi web).**
  Trang competitor hiện section "Bối cảnh, ICP và JTBD (giả định)" — vốn thuộc Customer Insight.
  Đã rà: web map task→skill ĐÚNG cả 6 trang; CompetitorSkill dùng đúng COMPETITOR_SYSTEM (không
  yêu cầu ICP/JTBD); competitor chạy TRƯỚC customer nên không phải copy. → Gốc: doanh nghiệp ngách
  (QC/sourcing cho DN Mỹ) khó tìm đối thủ công khai → grounding mỏng → LLM ĐỘN bằng ICP/JTBD tự suy
  từ target_customer để lấp chỗ trống (scope drift). Rủi ro hệ thống của pipeline `agents/` (mỗi
  agent thấy hồ sơ + kết quả trước → dễ lấn mảng kế cận khi data mỏng).
  → KHÔNG sửa sạch được khi research còn chạy qua `agents/` (reference-only). Dứt điểm = rebuild
  research WEB-OWNED, khoá cứng scope từng skill (thiếu data thì ghi "_chưa đủ dữ liệu công khai_",
  KHÔNG độn mảng khác). Gộp vào đợt rebuild research.
  - **N-03b (cùng họ): Customer Insight (và competitor) "độn" ROADMAP.** Output có "6. Strategic
    Implications → 🟢 Quick wins / 🟡 Medium term / 🔴 Risks" — VI PHẠM chính luật prompt
    (`prompts.py:380` + `pipeline.py:173`: research kết bằng so-what, KHÔNG xếp Quick-win/Medium/
    Long-term — việc đó của Synthesis T4/Tactical T5). Nguyên nhân: LLM bỏ qua lệnh phủ định + đoạn
    luật cấm lại IN MẪU 🟢🟡🔴 nên model bắt chước. → Khoá scope khi rebuild research web-owned;
    research dừng ở insight, roadmap chỉ ở Synthesis.

- **[N-04] Bản đồ định vị lòi JSON thô.** `enhancePosMaps` chỉ thay `<pre>` khi parse được map
  (JSON có `items` / ASCII có `^`+`GÓC`); khối JSON pos-map không khớp (thiếu items/parse lỗi/bản
  spec thứ 2) thì `return` bỏ qua → để nguyên `<pre>` JSON thô hiện ra. → Thêm nhánh: khối trông
  như pos-map JSON (có `yTop`/`xLeft`) mà không render được thì ẩn/gỡ, không để lòi.

- **[N-05] Bỏ HẲN "Đối thủ đang theo dõi (Ads Library)" ở T1-T3.** Section trên trang competitor
  (`P.competitor`) hiện DATA MOCK (`M.tracked` từ `web/data.js`: Phúc Long/Katinat) — không liên
  quan business thật, reset không xoá. Founder quyết: **bỏ hẳn section này ở giai đoạn T1-T3**
  (không đổi sang data thật). → Gỡ khối `M.tracked` khỏi render P.competitor.

- **[N-06] Hiện rõ trạng thái task (đang chạy / đã lỗi / xong) cho user.**
  Bấm "Lập chiến lược" (strategize_web ~2 LLM call, chạy ngầm) nhưng KHÔNG có chỉ báo rõ → user
  tưởng "không chạy gì" (thực ra vẫn ra kết quả, chỉ chậm + im lặng). Cần: chỉ báo toàn cục
  (banner/toast/progress) cho biết task ĐANG CHẠY (bước/% nếu có), ĐÃ LỖI (kèm lý do — đã log ở
  2f28497), hay XONG — đừng chỉ dựa nút đổi chữ. Áp cho mọi task (research + strategize).
  → Phụ: nhánh strategize trong `_execute` KHÔNG có timeout (research có `wait_for`) — nếu LLM treo
  thì job kẹt 'running' mãi → thêm timeout + đánh 'error' để khỏi kẹt vô hạn.

## ✅ Đã làm (lưu vết)
- Enter ở ô intake = nút Tiếp (fcbb3e3)
- Báo "agent đang chạy" đúng + bỏ "90 ngày" hardcode intake (04f9a9a)
- Fix reset/_retention_cache (a8cd7b0)
- Bắt + log lý do dừng research (2f28497)

## ⏳ Tính năng đã hoãn (chờ ưu tiên)
- "C hoàn chỉnh" — lịch kéo-thả (nền dữ liệu M-E đã có)
- Theme tháng mềm (always-on nghiêng theo roadmap phase)
- M-D Pha 4 full (phân nhóm khách — bản nhẹ đã lồng vào campaign F2)
- M-F F3 mở rộng đã xong; còn ACTION-task integration thật (gửi mail/ads…) — ngoài phạm vi hiện tại
- Test thật end-to-end trên Railway
