# ROADMAP — Marketing OS web (re-design) — BẢN MẪU (founder sửa thoải mái)

> Đây là draft tôi (agent) dựng từ những gì mình đã bàn. Bạn sửa North-star/Trụ/thứ tự/câu hỏi mở.
> Mỗi slice = 1 lát ship được. Trạng thái: ✅ xong · 🔵 đang làm · ⬜ chưa · 🟡 phần (agents/ chờ rebuild).

**North-star:** Biến founder Việt (không có CMO) thành "có-CMO": đi 1 mạch
**Hồ sơ → Chiến lược → Campaign → Lịch nội dung → Deliverable** — Max làm, founder duyệt/sửa. Web-owned.

## Luồng chủ đạo (founder 2026-06-25)
```
Intake → Research (T1-T3) → BÓC GAP/cơ hội (market/segment/định vị/tin cậy/kênh/giá)
   → Tạo CAMPAIGN TỔNG: user chọn [đánh GAP nào] + [tệp khách/wedge] + [USP]  ← "đặt cược chiến lược"
   → Max viết brief campaign tổng + dựng các TUYẾN BÀI (Khai sáng/Tin cậy/Chuyển hoá/Lan toả)
   → Campaign tổng có HUB (xem mọi thứ). KHÔNG phải campaign duy nhất —
     còn occasion + campaign khác chạy cùng.
   → Từ tuyến bài → Lịch nội dung.
```

---

## TRỤ 1 — Onboarding & Chiến lược
| Slice | Mô tả (1 dòng) | TT |
|---|---|---|
| S-01 Intake gọn | 13 câu, bỏ câu thừa/trùng, thêm team_size + wire vào chiến lược | ✅ |
| S-02 Research T1-T3 | market/competitor/customer/pricing/SWOT (đang chạy `agents/`) | 🟡 |
| S-03 Synthesis + Playbook | nâng prompt (mạch lập luận, TOWS, USP variants, archetype) | ✅ |
| S-05 Bóc GAP & cơ hội | sau research → trích các gap (thị trường/tệp/định vị/tin cậy/kênh/giá) trình user chọn | ⬜ |
| S-04 Research web-owned | viết lại T1-T3 web-owned, khoá scope (gỡ N-03 scope-drift) | ⬜ |

## TRỤ 2 — Campaign Hub (campaign-first)
| Slice | Mô tả | TT |
|---|---|---|
| S-10 **Campaign tổng** (mũi nhọn) | chọn gap+wedge+USP → Max viết brief + tuyến bài (Khai sáng/Tin cậy/Chuyển hoá/Lan toả) → hub. KHÔNG phải campaign duy nhất | 🔵 |
| S-11 Trang "Campaign" (list-first) | thay màn "Lập chiến dịch" rối → 1 danh sách campaign (tổng + occasion + …) + "Tạo campaign" | ⬜ |
| S-12 Hub detail (trang riêng, 10 mục) | brief · gap/wedge/USP · tuyến bài · kênh · lịch · task · KPI · ngân sách · rủi ro · lineage · % | ⬜ |
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
