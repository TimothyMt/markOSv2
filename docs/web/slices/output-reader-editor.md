# SPEC — Trải nghiệm đọc & chỉnh sửa output research

> Spec-driven (skill `spec-driven-development`). Giai đoạn: **Specify → chờ duyệt**.
> Truy ngược: PRODUCT.md §4 (M0 lõi cố vấn), §5 (trung thực, không nút giả).
> Quyết định liên quan: D-024 (output tương tác được). Chốt phạm vi 2026-06.

## 1. Objective
Cho user **đọc** output research (market/competitor/customer/pricing/swot/synthesis)
thoải mái trên **trang riêng full-width**, và **chỉnh sửa** bằng 2 cách — **sửa tay**
và **nhờ Max chỉnh đoạn** — mỗi lần lưu tạo **version mới**, xem lại được **lịch sử**.

Người dùng: chủ DN / marketer đang xem kết quả Max tạo, muốn tinh chỉnh trước khi dùng.

## 2. Features & Acceptance Criteria

### F1 — Trang đọc riêng `#doc/<run_id>`
- Layout 1 cột rộng, dễ đọc (không phải modal). Header: tên skill · version · thời điểm · rating (👍/👎).
- Render markdown/HTML (tái dùng `renderAIContent`).
- **AC:** Bấm "Xem & tương tác" (Hồ sơ DN) hoặc "Xem" (stepper) → mở **trang** `#doc/<id>`, KHÔNG popup. Bản 2000+ chữ đọc mượt, cuộn trang bình thường.

### F2 — Sửa tay (inline edit)
- Nút "✎ Sửa" → nội dung thành `<textarea>` chứa nội dung gốc (markdown/text). "Lưu" / "Huỷ".
- Lưu → tạo **skill_run version mới** (không ghi đè bản cũ).
- **AC:** Sửa text → Lưu → version tăng (vd v2→v3), trang hiện bản mới, bản cũ vẫn còn trong lịch sử.

### F3 — Nhờ Max chỉnh đoạn
- Ô "Yêu cầu chỉnh sửa" (vd: "viết lại phần định giá ngắn hơn, bỏ phần social listening").
- Gọi backend → `agents/surgical_edit.patch_document(content, comment)` → trả `(content mới, tóm tắt)`.
- Lưu thành version mới + hiện dòng **tóm tắt thay đổi**.
- **AC:** Nhập yêu cầu → có bản mới + tóm tắt "đã đổi …"; token tính vào quota user; KHÔNG regenerate cả bài.

### F4 — Lịch sử version
- Danh sách version (v1..vn) + thời điểm; xem bản cũ; "Đặt làm hiện hành" (= tạo version mới copy nội dung bản cũ).
- **AC:** Thấy danh sách, xem được bản cũ, đặt lại được. Không cần diff/so sánh ở v1.

## 3. Commands (dev)
- Chạy: `python run_web.py` → http://localhost:8000
- Build static: `python webapp/build_standalone.py`
- Test: `pytest tests/test_web_api.py` (mới)
- Kiểm: `node --check web/app.js`, `python -c "import ast; ..."`

## 4. Project structure (đụng tới)
- `webapp/business.py` — thêm `list_skill_versions`, `save_skill_edit`, `patch_skill_run`.
- `webapp/api.py` — thêm: `GET /api/biz/skillruns`, `POST /api/biz/skillrun/save`, `POST /api/biz/skillrun/{id}/patch`.
- `web/app.js` — router parse `#doc/<id>`; trang `P.doc`; đổi "Xem" → điều hướng `#doc/<id>` (thay modal).
- `web/styles.css` — style trang doc + editor.
- `tests/test_web_api.py` — **MỚI** (test tự động đầu tiên của web).

## 5. Code style / ràng buộc kỹ thuật
- Vanilla JS, **không thêm thư viện editor nặng**; sửa tay = `<textarea>` (markdown thô) — đơn giản, chắc.
- Async + LLM (patch) → có trạng thái loading; lỗi → toast, không vỡ trang.
- Tái dùng hạ tầng bot: `skill_runs.insert_skill_run` (versioning), `surgical_edit.patch_document`. KHÔNG dựng trùng.

## 6. Testing strategy
- **Khắc phục điểm yếu lớn nhất: thêm test tự động đầu tiên.** `tests/test_web_api.py`:
  - `api_routes()` chứa đủ route mới (doc/save/patch).
  - Không có Supabase → `business.save_skill_edit/patch_skill_run/list_skill_versions` trả `{"error": ...}` (degrade, không raise).
  - `webapp.build_standalone.build()` chèn được CSS/JS (smoke).
- Kiểm thủ công golden path: chạy 1 agent thật → mở #doc → sửa tay → Lưu (v+1) → nhờ Max sửa → xem lịch sử.

## 7. Boundaries
- **ALWAYS:** sửa = version mới (không phá bản cũ); token AI tính vào quota; degrade an toàn khi chưa có Supabase.
- **ASK FIRST:** xoá version; áp dụng cho output content/ads (ngoài phạm vi).
- **NEVER:** ghi đè huỷ bản cũ; lộ API key ra frontend; thêm dependency nặng không cần.

## 8. Ngoài phạm vi v1
- So sánh diff giữa các version; WYSIWYG editor; chỉnh sửa cộng tác realtime.
- Sửa output content/lịch/ads (slice khác).
- Xuất PDF/Docx (slice khác).
- Auth/phân quyền (M4).
