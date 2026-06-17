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
| D-017 | Lịch nội dung theo mô hình bot: **🟢 Always-on (nền, quanh năm)** + **🔴 Campaign theo dịp (lớp phủ có window)**. Web phải phản ánh 2 track + lifecycle. Thuộc **M1** | ✅ (2026-06) |
| D-018 | **Always-on chạy SONG SONG, KHÔNG tắt** trong tuần có campaign; campaign là lớp CỘNG THÊM (không thay thế). Sai marketing nếu always-on trống khi đang có đợt | ✅ (2026-06) |
| D-019 | **Sinh nội dung inline trong lịch, theo tuần/slot** (nhẹ, đúng ngữ cảnh) thay vì batch cả tháng 1 lần. Trang "Trình tạo nội dung" tách riêng = chế độ batch nâng cao | ✅ (2026-06) |
| D-020 | Lịch có **2 view**: Kế hoạch tháng (Gantt theo tuần) + Chi tiết tuần (ngày) | ✅ (2026-06) |
| D-021 | **Chat ≠ nơi lưu trữ.** Max chat = buồng lái (tạm thời); output Max tạo (skill_runs/strategies) lưu bền ở Supabase, xem lại ở trang chặng + **Hồ sơ doanh nghiệp** | ✅ (2026-06) |
| D-022 | Gộp 2 trang trùng (pipeline + agents) → **1 trang `dossier` "Hồ sơ doanh nghiệp"** (tủ hồ sơ bền vững). `#pipeline`/`#agents` redirect về `#dossier` | ✅ (2026-06) |
| D-023 | **Transcript chat persist vào Supabase** (`web_chat`), bền qua restart; cache in-memory + degrade an toàn nếu chưa tạo bảng | ✅ (2026-06) |
| D-024 | **Output research bền ở `skill_runs`** (versioned), hiển thị 3 nơi; **tương tác được**: 👍/👎 (feed rating/học), Copy, Tạo lại (bản mới). Chat = nhẹ, giữ thoải mái | ✅ (2026-06) |

## Đã chốt các câu hỏi mở (2026-06)
Q-A→D-011 · Q-B→D-012 · Q-C→D-013 · Q-D→D-014.
| D-025 | Bỏ nhóm sidebar **② Chẩn đoán** (5 mục trùng); diagnosis truy cập qua **Hồ sơ doanh nghiệp**. Giữ **function A**: tên phân tích trong khối Chẩn đoán link sang trang chi tiết (biểu đồ + output inline) | ✅ (2026-06) |
| D-026 | **Đảo D-007: bỏ Max chat làm trung tâm.** Entry point = **Hồ sơ doanh nghiệp (form-first)** — user mới điền form hồ sơ rồi chạy chẩn đoán. Lý do: chat trống gây bí cho user mới. Backend chat.py giữ ngủ (gỡ sau) | ✅ (2026-06) |
| D-027 | **Tắt seed demo mặc định** (`WEB_SEED_DEMO`, mặc định off) → user mới thấy trạng thái SẠCH (0 cảnh báo/chiến dịch/jobs giả). Bật khi cần demo showcase | ✅ (2026-06) |
| D-028 | **Intake AI-adaptive**: Max phỏng vấn từng câu thông minh qua `run_discovery_turn` (giữ UI từng-câu). Wizard tĩnh 8 bước = fallback khi chưa có backend | ✅ (2026-06) |
| D-029 | **SMART số liệu + roadmap 90 ngày chi tiết KHÔNG chốt ở Synthesis (M0)** — Synthesis chỉ ra **định hướng giai đoạn** (positioning, wedge, pillars, % phân bổ ngân sách, 0-30/31-60/61-90 = ưu tiên gì). SMART cụ thể (số, deadline, ngân sách thật) chỉ "đóng khung" khi tạo **1 Campaign Occasion cụ thể** (M1), kế thừa giai đoạn roadmap hiện tại. Lý do: Synthesis chưa có lever cụ thể (dịp/ngân sách/baseline) nên SMART ở đó là số đoán; bot Telegram đã làm đúng pattern này (`campaign_intake.build_campaign_draft_from_strategy` đọc `roadmap_90d[phase1]` + budget để pre-fill draft, KHÔNG tự tạo SMART rời). Web M1 occasion creation phải tái dùng pattern này — **không đổi prompt/skill Synthesis** (giữ D-001, bot giữ nguyên) | ✅ (2026-06) |
