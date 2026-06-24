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
