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

## Đang chờ Founder quyết (mở)
- **Q-A** Người dùng chính của v1? (SME tự làm MKT / Agency / Freelancer)
- **Q-B** Outcome CỐT LÕI v1 (1 luồng vàng đào sâu trước)?
- **Q-C** Mô hình kinh doanh v1?
- **Q-D** Có làm auth ngay ở milestone tới không (chặn public)?
