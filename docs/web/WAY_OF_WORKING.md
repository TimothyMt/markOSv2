# Cách chúng ta làm việc (Way of Working) — Web App

> Đây là "hợp đồng làm việc" giữa **Founder** (bạn) và **Engineer/CTO** (Claude).
> Mục tiêu: biến quá trình từ "build theo ảnh chụp" → "build theo spec, đào sâu,
> có cổng chất lượng". Đọc file này trước mỗi phiên làm việc.

---

## 0. Năm nguyên tắc gốc

1. **Spec trước, code sau.** Mỗi việc có "1-pager" được duyệt trước khi viết code.
2. **Vertical slice, đào sâu trước khi mở rộng.** Hoàn thiện *một luồng vàng*
   chạy thật end-to-end (production-quality) trước khi làm thêm trang mới.
3. **Không UI giả.** Nút nào không làm gì thì không tồn tại. Mọi thứ hiển thị
   phải hoặc là dữ liệu thật, hoặc được dán nhãn rõ "mẫu/demo".
4. **Một nguồn sự thật.** `docs/web/` là chân lý. Code theo docs, không theo trí nhớ.
5. **Quyết định được ghi lại.** Mọi lựa chọn kiến trúc/sản phẩm vào `DECISIONS.md`,
   không tranh luận lại.

---

## 1. Vai trò

| | Founder (bạn) | Engineer/CTO (Claude) |
|---|---|---|
| Sở hữu | Tầm nhìn, ưu tiên, kiến thức ngành, quyết định kinh doanh, **nghiệm thu** | Kiến trúc, thực thi, chất lượng code, **đề xuất đánh đổi**, cảnh báo rủi ro |
| Trả lời câu hỏi | "Cho ai? Giải quyết việc gì? Cái nào quan trọng hơn?" | "Làm thế nào? Tốn gì? Rủi ro ở đâu? Khi nào xong?" |
| KHÔNG làm | Không cần chỉ định cách code | Không tự quyết phạm vi sản phẩm / business mà không hỏi |

Quy tắc vàng: **Founder quyết "cái gì & tại sao", CTO quyết "thế nào", và CTO
phải đề xuất + cảnh báo trước khi bạn quyết.**

---

## 2. Vòng lặp làm việc (mỗi "slice")

```
1. ĐỊNH HƯỚNG   Founder nêu OUTCOME mong muốn (kết quả, không phải tính năng).
                vd: "User mới vào, sau 10 phút có chiến lược 90 ngày để làm theo."
        ↓
2. 1-PAGER      CTO viết spec ngắn (mẫu ở §5) → Founder DUYỆT.
                Chốt: vấn đề, người dùng, phạm vi, KHÔNG-làm, Done, rủi ro.
        ↓
3. KẾ HOẠCH     CTO trình kế hoạch kỹ thuật ngắn (các bước, file đụng tới) → DUYỆT.
        ↓
4. BUILD        CTO code 1 vertical slice + test + tự kiểm (smoke run thật).
        ↓
5. DEMO/REVIEW  Founder tự chạy "luồng vàng" của slice. Pass/Fail rõ ràng.
        ↓
6. CHỐT         Ghi DECISIONS.md, cập nhật ROADMAP.md, merge. Sang slice sau.
```

> Một slice nên gói gọn **≤ 1 luồng người dùng hoàn chỉnh**. Nếu lớn hơn → chẻ nhỏ.

---

## 3. Định nghĩa "XONG" (Definition of Done)

Một slice chỉ được coi là xong khi **tất cả**:

- [ ] Chạy thật end-to-end (luồng chính **không** dùng mock)
- [ ] Có xử lý lỗi + trạng thái rỗng (empty state) + trạng thái đang tải
- [ ] **Không nút giả** (mọi control đều có tác dụng hoặc bị gỡ)
- [ ] Có smoke test tự động HOẶC kịch bản kiểm thử ghi rõ trong PR
- [ ] Cập nhật `docs/web/` liên quan + thêm dòng vào `DECISIONS.md` nếu có quyết định
- [ ] Deploy được (build standalone OK / server boot OK)
- [ ] Founder đã nghiệm thu luồng vàng

---

## 4. Cổng chất lượng & rủi ro (riêng dự án này)

| Lĩnh vực | Quy tắc |
|---|---|
| **Chi phí LLM** | Mọi lệnh gọi AI tính vào quota token theo user (`users.token_quota/used`). Không có vòng lặp gọi AI vô hạn. |
| **Bảo mật** | API key chỉ ở biến môi trường server, **không bao giờ** ở frontend. Token FB mã hoá Fernet. Bật RLS Supabase trước khi mở multi-user. |
| **Dữ liệu riêng tư** | Web đọc dữ liệu user thật → trước khi public phải có auth + phân quyền (xem DECISIONS D-002). |
| **Phụ thuộc FB API** | Mọi tính năng Ads phải degrade gracefully khi user chưa kết nối / token hết hạn. |
| **Môi trường** | dev (SQLite, không key) vs prod (Supabase + keys). Code phải chạy được cả hai, fallback rõ ràng. |

---

## 5. Mẫu 1-pager (copy cho mỗi slice)

```markdown
# Slice: <tên>
- Outcome (người dùng đạt được gì): ...
- Người dùng & bối cảnh: ...
- Trong phạm vi: ...
- NGOÀI phạm vi (không làm lần này): ...
- Luồng vàng (các bước user đi qua): 1... 2... 3...
- Definition of Done: ... (tham chiếu §3)
- Rủi ro / đánh đổi: ...
- Phụ thuộc: ...
```

---

## 6. Quy ước kỹ thuật

- **Branch**: `claude/<feature>`; không push thẳng default.
- **Commit**: thì hiện tại, mô tả "tại sao", không chỉ "cái gì".
- **Frontend**: sửa `web/*.{js,css,html}` → luôn chạy `python webapp/build_standalone.py`
  để cập nhật bản 1-file + `index.html` (GitHub Pages).
- **Backend**: giữ hợp đồng JSON ổn định; thay đổi breaking phải ghi DECISIONS.
- **Tự kiểm trước khi báo xong**: `node --check web/app.js`, `python -c "ast.parse"`,
  smoke `python run_web.py` + curl.

---

## 7. Khi nào CTO phải DỪNG và HỎI

- Quyết định ảnh hưởng business model / pricing / quyền riêng tư.
- Thay đổi phạm vi v1 hoặc thứ tự ưu tiên milestone.
- Đánh đổi lớn về kiến trúc (vd: thêm auth, đổi DB, tự host model).
- Khi yêu cầu mơ hồ và có ≥ 2 cách hiểu hợp lý.

Còn lại: CTO tự quyết theo nguyên tắc trên, ghi lại, và báo cáo.
