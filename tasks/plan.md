# PLAN — Output Reader & Editor

> Theo spec `docs/web/slices/output-reader-editor.md`. Vertical slices: mỗi task
> chạy thật end-to-end, có test, commit riêng. Checkpoint chờ duyệt giữa các pha.

## Dependency graph
```
T1 Read page (#doc/<id>)  ── nền tảng, mọi feature khác sống trên trang này
   │   + tests/test_web_api.py (test tự động đầu tiên)
   ├─► T2 Sửa tay → version mới (F2)
   ├─► T3 Lịch sử version + đặt-làm-hiện-hành (F4)
   └─► T4 Nhờ Max chỉnh đoạn (F3, surgical_edit.patch_document)
```
T1 trước (bắt buộc). T2/T3/T4 độc lập tương đối sau T1 — làm tuần tự T2→T3→T4.

## Hạ tầng tái dùng (không dựng trùng)
- `storage/v2/skill_runs.insert_skill_run(user_id, skill_name, content, …)` → tự tăng version.
- `storage/v2/skill_runs.list_skill_runs(user_id, skill_name, limit)` → lịch sử.
- `agents/surgical_edit.patch_document(text, comment) -> (status, payload, meta)`:
  - `PATCH_OK` → payload = full text mới → lưu version mới.
  - `PATCH_ASK` → payload = câu hỏi làm rõ → trả về cho user.
  - `PATCH_NOOP` → payload = text gốc → báo "không khớp đoạn nào".
  - `summarize_changes(meta)` → tóm tắt.
- Frontend router: `location.hash` → split `/` để lấy `#doc/<id>`.

---

## T1 — Trang đọc riêng `#doc/<id>` + test đầu tien
**Backend:** không thêm (đã có `GET /api/biz/skillrun/{id}`).
**Frontend (`web/app.js`, `styles.css`):**
- Router: parse `raw.split('/')` → `id='doc'`, `_docId=phần sau`.
- `P.doc`: fetch `/api/biz/skillrun/<id>`, render full-width (override max-height),
  header (skill · version · thời điểm · 👍/👎), nút "← Quay lại Hồ sơ".
- Đổi nút "Xem & tương tác" (Hồ sơ DN), "Xem" (stepper), "Xem output" (agentBar)
  → điều hướng `#doc/<id>` thay vì `showModal`.
**Test (`tests/test_web_api.py` — MỚI):**
- `api_routes()` chứa các path cần thiết.
- `business.skill_run_content('x')` không Supabase → `{}` (không raise).
- `build_standalone.build()` trả HTML chứa `P.doc`.
**AC:** `#doc/<id>` mở thành TRANG, bản dài cuộn mượt, không popup, không cắt khung.
**Verify:** `node --check web/app.js` · `pytest tests/test_web_api.py -q` · build standalone OK.
**Commit:** "feat(web): dedicated #doc reader page + first web test"

### ⛳ CHECKPOINT 1 — duyệt trải nghiệm đọc trước khi thêm sửa.

---

## T2 — Sửa tay → version mới (F2)
**Backend (`business.py`, `api.py`):**
- `business.save_skill_edit(user_id, skill_name, content)` → `insert_skill_run(...)`; trả row mới hoặc `{"error"}`.
- `POST /api/biz/skillrun/save` `{user_id, skill_name, content}`.
**Frontend:** nút "✎ Sửa" → `<textarea>` chứa nội dung gốc; "Lưu"/"Huỷ"; Lưu → POST save →
chuyển sang `#doc/<id mới>` (version mới).
**Test:** route `save` tồn tại; `save_skill_edit` degrade không Supabase.
**AC:** sửa text → Lưu → version tăng, bản cũ còn, trang hiện bản mới.
**Verify:** như T1 + manual.
**Commit:** "feat(web): manual edit saves a new skill_run version"

---

## T3 — Lịch sử version (F4)
**Backend:**
- `business.list_skill_versions(user_id, skill_name)` → `list_skill_runs` (lọc skill).
- `GET /api/biz/skillruns?user_id=&skill=`.
- "Đặt làm hiện hành" = `save_skill_edit` với nội dung bản cũ (tạo version mới trên đầu).
**Frontend:** panel danh sách version (v1..vn + thời điểm) trên trang doc; bấm xem bản cũ
(`#doc/<id cũ>`); nút "Đặt làm hiện hành".
**Test:** route `skillruns`; `list_skill_versions` degrade.
**AC:** thấy danh sách, xem bản cũ, đặt-làm-hiện-hành tạo version mới.
**Commit:** "feat(web): version history + set-as-current on doc page"

---

## T4 — Nhờ Max chỉnh đoạn (F3)
**Backend:**
- `business.patch_skill_run(run_id, comment)`:
  1. đọc content qua `skill_run_content`.
  2. `patch_document(content, comment)`.
  3. `PATCH_OK` → `insert_skill_run` version mới → trả `{status:'ok', summary, run}`.
  4. `PATCH_ASK` → `{status:'ask', question}`. `PATCH_NOOP` → `{status:'noop'}`.
- `POST /api/biz/skillrun/{id}/patch` `{comment}`.
**Frontend:** ô "Nhờ Max chỉnh sửa…" + nút gửi; loading; xử lý 3 trạng thái
(ok→chuyển version mới + toast tóm tắt; ask→hiện câu hỏi; noop→toast).
**Test:** route `patch`; `patch_skill_run` degrade.
**AC:** yêu cầu rõ → version mới + tóm tắt; mơ hồ → câu hỏi làm rõ; không khớp → báo; token vào quota.
**Commit:** "feat(web): ask Max to patch a section (surgical_edit) → new version"

### ⛳ CHECKPOINT 2 — nghiệm thu golden path đầy đủ (đọc → sửa tay → lịch sử → nhờ Max).

---

## Ngoài phạm vi (nhắc lại): diff so sánh, WYSIWYG, sửa content/ads, xuất PDF, auth.
