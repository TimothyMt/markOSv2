# HOW-TO — Viết roadmap/slice để agent "đọc là làm được"

> Mục đích: bạn (founder) viết yêu cầu theo khung này → tôi (agent) hiểu đúng, hỏi đúng chỗ mơ hồ,
> code đúng, ít vòng lặp. Dùng cho re-design website + function.

## 1. Tư duy roadmap — 4 tầng (từ to → nhỏ)
```
North-star  : 1 câu — sản phẩm giúp AI làm được GÌ, khác biệt ở đâu.
  └ Trụ (Pillars) : 3-5 mảng lớn (vd: Chiến lược · Campaign · Lịch nội dung · Vận hành).
      └ Slice     : 1 LÁT CẮT ship được ĐỘC LẬP (vài ngày). Đây là đơn vị tôi làm.
          └ Task  : đầu việc trong slice.
```
🔴 Quy tắc vàng: **mỗi slice phải ship/test được riêng**. Đừng viết 1 slice "làm cả website".

## 2. MẪU 1 SLICE (copy cái này cho mỗi lát cắt)
```md
# [ID vd S-03] Tên slice ngắn gọn

## Vấn đề (vì sao)
1-3 câu: hiện tại đau/rối/thiếu chỗ nào.

## Kết quả mong muốn
Sau slice này, USER làm được gì (câu "user có thể …").

## Phạm vi
- TRONG: gạch đầu dòng những gì LÀM.
- NGOÀI (non-goal): những gì KHÔNG làm ở slice này (chống vẽ thừa).

## Luồng / màn hình
User bấm gì → thấy gì → bước kế. (Càng cụ thể càng tốt: tên nút, tên trang.)

## Dữ liệu
Cần lưu/đọc gì, ở đâu (vd: intake_extra.X / campaigns_v2 / skill_run 'Y').

## Acceptance (done = kiểm thế nào)
- [ ] Bấm A → ra B
- [ ] Trường hợp rỗng/lỗi → hiện C
(Tôi sẽ verify tĩnh + bạn test thật trên Railway theo mấy gạch này.)

## Phụ thuộc
Slice nào phải xong trước.

## Câu hỏi mở (?)  ← QUAN TRỌNG
Chỗ nào bạn CHƯA chốt → đánh dấu "?" để tôi HỎI trước khi code, không tự đoán.
```

## 3. 6 mẹo để tôi làm ĐÚNG (rút từ kinh nghiệm làm với bạn)
1. **Một slice một lúc.** To quá → tôi đoán nhiều → lệch.
2. **Nói "CÁI GÌ" + "VÌ SAO", để tôi lo "THẾ NÀO".** Đừng chỉ đạo code chi tiết — mô tả kết quả.
3. **Chốt hoặc đánh "?".** Quyết định nào bạn đã chốt thì ghi rõ; chưa chốt thì để "?" — tôi sẽ hỏi.
4. **Acceptance cụ thể** (bấm X → thấy Y). Đây là thước đo "xong".
5. **Nêu Non-goal.** Giúp tôi không vẽ thừa (đỡ "cuốn chiếu").
6. **Tham chiếu nếu biết** (tên trang/file/loại data). Không biết cũng được — tôi tự tìm.

## 4. Cách mình chạy vòng lặp (đề xuất)
```
Bạn viết slice (thô cũng được)
  → Tôi đọc → biến thành spec gọn + LIỆT KÊ câu hỏi mở → bạn chốt
  → Tôi code + verify tĩnh (ast/node-check) + commit/push
  → Tôi GỬI before/after để bạn xem → bạn review/test Railway
  → Slice kế.
```

## 5. RÀNG BUỘC cố định của dự án này (tôi luôn tự tuân — bạn không cần nhắc)
- **Web-owned**: chỉ sửa `webapp/` + `web/`. **KHÔNG sửa `agents/`** (chỉ tham khảo).
- **Mirror**: mọi thay đổi FE phải đồng bộ `web/app.js` ↔ `web/dashboard-standalone.html` (+ CSS).
- **Tiếng Việt** cho mọi output; **KHÔNG bịa số** (gắn "(ước tính)"); KPI = đo-gì không-target.
- **Spec-first** cho việc lớn; **note-only** khi bạn nói "note".
- Sandbox không có Supabase/LLM/browser → tôi verify **tĩnh**; **test thật bạn làm trên Railway**.

## 6. Cho re-design lần này — gợi ý cấu trúc roadmap
Tạo `docs/web/roadmap.md` dạng MỤC LỤC:
```md
# ROADMAP — Marketing OS web (re-design)
North-star: ...

## Trụ 1 — Onboarding & Chiến lược   (slices: S-01 intake, S-02 research, S-03 synthesis…)
## Trụ 2 — Campaign Hub              (S-10 branding, S-11 occasion, S-12 portfolio…)
## Trụ 3 — Lịch nội dung             (S-20 brief→calendar, S-21 kéo-thả…)
## Trụ 4 — Vận hành & deliverable    (S-30 task kanban, S-31 generators…)

Thứ tự ưu tiên: S-01 → ...
```
Mỗi slice = 1 file `docs/web/slices/S-xx-*.md` theo mẫu mục 2 (mình đã có sẵn pattern này).
```
```
