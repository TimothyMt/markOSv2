# TODO — Output Reader & Editor

## T1 — Trang đọc `#doc/<id>` + test đầu tiên
- [x] Router parse `#doc/<id>` trong `web/app.js`
- [x] `P.doc` render full-width + header + nút quay lại
- [x] CSS trang doc (override max-height của `.ai-output`)
- [x] Đổi "Xem"/"Xem & tương tác"/"Xem output" → `#doc/<id>` (bỏ modal)
- [x] `tests/test_web_api.py` (routes + degrade + build) — test tự động đầu tiên
- [x] `node --check` + `pytest` + build standalone + commit
- [ ] ⛳ Checkpoint 1: duyệt

## T2 — Sửa tay → version mới
- [x] `business.save_skill_edit` + `POST /api/biz/skillrun/save`
- [x] UI "✎ Sửa" → textarea → Lưu (version mới)
- [x] test route + degrade; commit

## T3 — Lịch sử version
- [x] `business.list_skill_versions` + `GET /api/biz/skillruns`
- [x] UI panel version + xem bản cũ + "Đặt làm hiện hành"
- [ ] test route + degrade; commit

## T4 — Nhờ Max chỉnh đoạn
- [x] `business.patch_skill_run` (PATCH_OK/ASK/NOOP) + `POST /api/biz/skillrun/{id}/patch`
- [x] UI ô yêu cầu + loading + 3 trạng thái
- [ ] test route + degrade; commit
- [ ] ⛳ Checkpoint 2: nghiệm thu golden path
