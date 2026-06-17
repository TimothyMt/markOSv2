# TODO — Output Reader & Editor

## T1 — Trang đọc `#doc/<id>` + test đầu tiên
- [ ] Router parse `#doc/<id>` trong `web/app.js`
- [ ] `P.doc` render full-width + header + nút quay lại
- [ ] CSS trang doc (override max-height của `.ai-output`)
- [ ] Đổi "Xem"/"Xem & tương tác"/"Xem output" → `#doc/<id>` (bỏ modal)
- [ ] `tests/test_web_api.py` (routes + degrade + build) — test tự động đầu tiên
- [ ] `node --check` + `pytest` + build standalone + commit
- [ ] ⛳ Checkpoint 1: duyệt

## T2 — Sửa tay → version mới
- [ ] `business.save_skill_edit` + `POST /api/biz/skillrun/save`
- [ ] UI "✎ Sửa" → textarea → Lưu (version mới)
- [ ] test route + degrade; commit

## T3 — Lịch sử version
- [ ] `business.list_skill_versions` + `GET /api/biz/skillruns`
- [ ] UI panel version + xem bản cũ + "Đặt làm hiện hành"
- [ ] test route + degrade; commit

## T4 — Nhờ Max chỉnh đoạn
- [ ] `business.patch_skill_run` (PATCH_OK/ASK/NOOP) + `POST /api/biz/skillrun/{id}/patch`
- [ ] UI ô yêu cầu + loading + 3 trạng thái
- [ ] test route + degrade; commit
- [ ] ⛳ Checkpoint 2: nghiệm thu golden path
