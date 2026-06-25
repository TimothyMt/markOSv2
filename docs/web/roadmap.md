# ROADMAP — Marketing OS web (re-design) — BẢN MẪU (founder sửa thoải mái)

> Đây là draft tôi (agent) dựng từ những gì mình đã bàn. Bạn sửa North-star/Trụ/thứ tự/câu hỏi mở.
> Mỗi slice = 1 lát ship được. Trạng thái: ✅ xong · 🔵 đang làm · ⬜ chưa · 🟡 phần (agents/ chờ rebuild).

**North-star:** Biến founder Việt (không có CMO) thành "có-CMO": đi 1 mạch
**Hồ sơ → Chiến lược → Campaign → Lịch nội dung → Deliverable** — Max làm, founder duyệt/sửa. Web-owned.

## Luồng chủ đạo — VISION A (founder chốt 2026-06-25, luồng thẳng)
```
Intake → Research (T1-T3)
   → ĐẶT CƯỢC theo 5 NHÓM: Thị trường · Tệp · Định vị · Giá-trị · Kênh
     (mỗi nhóm: Max rút option từ T1-T3 + user tự ghi; khuyên chọn 1/nhóm cho tập trung)
   → Chạy T4-T5 (Synthesis + Playbook) BÁM ĐÚNG đặt cược
   → Chia TUYẾN NỘI DUNG (Khai sáng/Tin cậy/Chuyển hoá/Lan toả — Tin cậy = trust ở đây)
   → Lịch nội dung dựa vào tuyến (bài bám vai-trò-tuyến).
```
> ⏸️ Lớp "Campaign TỔNG → sub-campaign + hub" (bản trước) đã CẤT (code để dạng ngủ),
> để dành cho phần ĐỢT/OCCASION (Binet&Field) cần brief + task riêng về sau.

---

## TRỤ 1 — Onboarding & Chiến lược
| Slice | Mô tả (1 dòng) | TT |
|---|---|---|
| S-01 Intake gọn | 13 câu, bỏ câu thừa/trùng, thêm team_size + wire vào chiến lược | ✅ |
| S-02 Research T1-T3 | market/competitor/customer/pricing/SWOT (đang chạy `agents/`) | 🟡 |
| S-03 Synthesis + Playbook | nâng prompt (mạch lập luận, TOWS, USP variants, archetype) | ✅ |
| S-05 **Đặt cược theo 5 nhóm** (Vision A) | sau research → Max rút option cho 5 nhóm (TT·tệp·định vị·giá·kênh) + user tự ghi → chọn → chạy T4-T5 bám đúng | ✅ |
| S-04 Research web-owned | viết lại T1-T3 web-owned, khoá scope (gỡ N-03 scope-drift) | ⬜ |

## TRỤ 2 — Campaign Hub (campaign-first)
| Slice | Mô tả | TT |
|---|---|---|
| S-10/11/12 Campaign tổng → sub + hub | ĐÃ build (engine + UI) nhưng **CẤT** theo Vision A — code để ngủ, dành cho ĐỢT/occasion sau | ⏸️ |
| S-13 Occasion typed + Portfolio | loại campaign + task kanban + Max đề xuất danh mục | ✅ |

## TRỤ 3 — Lịch nội dung
| Slice | Mô tả | TT |
|---|---|---|
| S-20 Brief → Funnel → Calendar | port mạch bot: từ campaign brief dựng lịch (thay calendar-from-pillars) | ⬜ |
| S-21 Lịch hợp nhất nhiều campaign | 1 lịch, lọc/gom theo campaign, không rối khi nhiều campaign | ⬜ |
| S-22 "C hoàn chỉnh" — kéo-thả | kéo bài đổi ngày/ô (nền M-E đã có) | ⬜ |
| S-23 Reconciliation + Topics | thẻ hạng nhất không-mất-bài + Max sinh chủ đề/góc per-bài | ✅ |

## TRỤ 4 — Deliverable & Vận hành
| Slice | Mô tả | TT |
|---|---|---|
| S-30 Task kanban + Generators | mỗi campaign có việc cần làm → Max sinh (ads/email/video/ugc/landing…) | ✅ |
| S-31 Retention/Winback | cẩm nang giữ chân (no-data) — đã nâng theo bot | ✅ |

## TRỤ 5 — Nền tảng & UX (cross-cutting)
| Slice | Mô tả | TT |
|---|---|---|
| S-40 Trạng thái task rõ ràng | banner đang-chạy/lỗi/xong + timeout strategize (N-06) | ⬜ |
| S-41 Sửa lỗi UX gói nhỏ | version đặt-hiện-hành (N-01) · UI bóp (N-02) · posmap JSON (N-04) · bỏ tracked mock (N-05) | ⬜ |
| S-42 Reset để test | giữ-hồ-sơ / xoá-sạch | ✅ |

---

## Thứ tự ưu tiên đề xuất
1. **S-10 → S-11 → S-12** (đóng gói campaign-hub cho hết rối — bạn đang muốn cái này)
2. **S-20 → S-21** (brief→lịch + lịch gọn khi nhiều campaign)
3. **S-40 + S-41** (gói fix UX nhỏ — nhanh, đỡ khó chịu)
4. **S-22** (kéo-thả C) · **S-04** (rebuild research web-owned — lớn, để sau)

## 🧪 Quy tắc TEST (founder chốt 2026-06-25)
- **Test theo slice, không dồn:** xong 1 slice → deploy Railway test ngay (lỗi nông, dễ sửa).
- **Test checkpoint sau mỗi nhóm:** dưới đây là các điểm DỪNG để bạn test thật trước khi đi tiếp.
  - 🧪 CP-A (sau S-05/S-10 engine): bóc gap có trúng? tạo tổng + sub có đúng?
  - 🧪 CP-B (sau S-10c + bài): brief sub + topics theo tuyến + bài đăng có sắc, đúng vai-trò-tuyến?
  - 🧪 CP-C (sau UX/UI): luồng gap→tổng→sub→tuyến→bài chạy mượt, lịch không rối khi nhiều campaign?
- Tôi sẽ **viết vài test thuần Python** cho phần logic (như đã làm cho reconciliation/topics) để bắt
  "sửa mới hỏng cũ" mà không cần chạy full app.

---

## ════ VÍ DỤ 1 SLICE VIẾT ĐẦY ĐỦ (mẫu để bạn copy) ════

# S-11 Trang "Campaign" (list-first)

## Vấn đề
Màn "Lập chiến dịch" bày pillars + occasion + retention rời rạc → rối. Branding chưa có chỗ đứng.

## Kết quả mong muốn
User vào 1 trang **"Campaign"** thấy **1 danh sách**: 🟢 Branding nền + 🔴 các occasion (+ 🔁 retention),
mỗi cái 1 card; bấm "Tạo campaign" để thêm; bấm card → mở hub.

## Phạm vi
- TRONG: trang list + card mỗi campaign (đọc `bizCampaignMeta` + campaigns_v2) + nút Tạo.
- NGOÀI: hub detail trang riêng (đó là S-12); kéo-thả lịch (S-22).

## Luồng / màn hình
Sidebar "Lập chiến dịch" → trang list. Card hiện: icon loại · tên · trạng thái · % task.
Nút "🟢 Tạo Branding nền" · "🔴 Tạo theo dịp" · "🗂️ Đề xuất danh mục". Bấm card → S-12.

## Dữ liệu
Đọc `bizCampaignMeta` (đã có) + `bizCampaigns`. Không thêm bảng.

## Acceptance
- [ ] Có ≥1 campaign → list hiện đủ (branding + occasion).
- [ ] Chưa có → empty state + nút Tạo.
- [ ] Bấm card → mở hub (S-12 hoặc tạm modal).

## Phụ thuộc
S-10 (branding tồn tại). Nối S-12 (hub).

## Câu hỏi mở (?)
- ? Retention (cẩm nang) có hiện như 1 "campaign" trong list không, hay để khu riêng?
- ? Card có cần preview brief ngắn không, hay chỉ tên + trạng thái?
