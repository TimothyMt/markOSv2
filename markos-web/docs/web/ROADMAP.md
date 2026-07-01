# Lộ trình (Roadmap) — Web App

> Nguyên tắc: **đào sâu 1 luồng vàng đến mức production trước khi mở rộng.**
> Mỗi milestone = 1 luồng người dùng chạy thật. Không tích nợ "mock cho đẹp".

## Trạng thái hiện tại (2026-06)
Đã có: shell SPA + 22 trang (phần lớn mock), Max chat (discovery + advisory),
trigger agent thật, đọc dữ liệu thật (profile/campaigns/competitors/skill_runs/
ads), FB OAuth từ web, SSE realtime, audit bỏ UI giả.
**Thiếu để gọi là "app hoàn chỉnh": chưa có 1 luồng vàng nào được nghiệm thu
end-to-end + chưa có auth + chưa có test.**

---

## M0 — Nền móng & 1 luồng vàng (ƯU TIÊN)
**Outcome**: user mới trò chuyện với Max → khai báo doanh nghiệp → chạy **một**
phân tích thật → xem kết quả AI ngay trong trang. Chạy mượt, không lỗi, không mock
ở luồng chính.
- [ ] Chốt PRODUCT.md (sau khi Founder trả lời Q-A..Q-D)
- [ ] Golden path: `home` → discovery → 1 task (vd "competitor") → kết quả render
- [ ] Xử lý lỗi/empty/loading đầy đủ trên luồng đó
- [ ] Smoke test tự động cho luồng đó
- [ ] Nghiệm thu bởi Founder
**Done = demo được cho người ngoài mà không cần giải thích.**

## M1 — Hoàn thiện chặng Chẩn đoán → Chiến lược
Tất cả 6 phân tích + tổng hợp chiến lược chạy thật, kết quả lưu & hiển thị đẹp,
có trạng thái tiến trình. Xuất được bản tóm tắt (PDF/HTML thật).

## M2 — Sản xuất nội dung thật
Brief → calendar → content/video/ugc/ads-copy nối skill thật, lưu `posts`,
chỉnh sửa & duyệt được.

## M3 — Vận hành & Ads thật
Ads analytics từ snapshot thật, optimizer đề xuất thật, theo dõi đối thủ thật.

## M4 — Sẵn sàng public
**Auth + phân quyền + RLS**, billing/nạp quota, onboarding, polish, observability
(log lỗi, theo dõi chi phí token), test coverage.

---

## Quy tắc ưu tiên
1. Sửa lỗi trên luồng vàng > thêm trang mới.
2. Một thứ chạy thật > năm thứ mock.
3. Trước khi public: D-002 (auth) là **chặn cứng**.
