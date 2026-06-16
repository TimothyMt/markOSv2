# Nhật ký quyết định (ADR-lite) — Web App

> Mỗi quyết định 1 dòng tiêu đề + bối cảnh + lựa chọn + hệ quả. Không xoá, chỉ
> đánh dấu "Đã thay thế bởi D-xxx" khi đổi. Đừng tranh luận lại cái đã chốt.

| ID | Quyết định | Trạng thái |
|----|-----------|-----------|
| D-001 | Web là surface mới, **bot giữ nguyên**; web mount chung server hoặc chạy độc lập | ✅ |
| D-002 | v1 **chưa làm auth** (mock-first, demo). Bắt buộc có auth + RLS trước khi public dữ liệu thật đa user | ⏳ nợ |
| D-003 | Backend **pluggable**: SQLite (dev) ↔ Supabase (prod) qua `store` facade | ✅ |
| D-004 | Dùng **chung Supabase với bot**; web đọc bảng thật qua `business.py`, không nhân bản dữ liệu | ✅ |
| D-005 | AI dùng **1 API key của hệ thống**, tính usage theo **quota từng user**; user "nạp quota" để dùng (chưa nối thanh toán) | ✅ |
| D-006 | Token **Facebook là OAuth riêng từng user**; user tự kết nối để xem ads của họ | ✅ |
| D-007 | Triết lý sản phẩm: **Max (CMO) làm trung tâm**, điều hướng theo **hành trình 5 chặng**, không phải dashboard Ads-manager | ✅ |
| D-008 | **Không UI giả** — nút không có tác dụng phải gỡ (audit 2026-06-16) | ✅ |
| D-009 | Deploy: **Railway** (server đầy đủ) + **GitHub Pages** (bản tĩnh demo) | ✅ |
| D-010 | Realtime qua **SSE** + Supabase Realtime; watcher poll 4s làm fallback | ✅ |
| D-011 | Phục vụ **cả 3 nhóm user, phân theo GÓI** (Starter/Pro/Agency); core dùng chung, gating theo gói | ✅ (2026-06) |
| D-012 | Luồng vàng ưu tiên: **M0 = Chẩn đoán→Chiến lược**, **M1 = Sản xuất nội dung**; Ads để sau | ✅ (2026-06) |
| D-013 | Kinh doanh: **thuê bao tháng** 3 gói; billing + auth gom vào M4 | ✅ (2026-06) |
| D-014 | Auth **hoãn** ở các milestone tới (Q-D); v1 demo/nội bộ. ⚠️ Chặn cứng public dữ liệu thật đa user | ✅ (2026-06) |
| D-015 | Web chạy agent **non-interactive** = `run_targeted_pipeline` (đủ 8 bước, gồm synthesis). Multi-agent + 8 câu hỏi chỉ dùng trong chat bot | ✅ (2026-06) |
| D-016 | M0: Starter **luôn chạy full** chất lượng cao; trang Chiến lược **tóm tắt gọn trước** + nút "Xem đầy đủ" | ✅ (2026-06) |

## Đã chốt các câu hỏi mở (2026-06)
Q-A→D-011 · Q-B→D-012 · Q-C→D-013 · Q-D→D-014.
