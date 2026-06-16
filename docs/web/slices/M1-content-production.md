# Slice M1 — Sản xuất nội dung (Always-on + Campaign theo dịp)

> 1-pager nháp. Bắt đầu sau khi M0 được nghiệm thu. (Way of Working §5)

## Outcome
Từ chiến lược đã có, user sản xuất **lịch nội dung thật** thể hiện đúng mô hình
markOS: **🟢 Always-on (nền, quanh năm)** + **🔴 Campaign theo dịp (lớp phủ có
khung thời gian)** — rồi sinh nội dung thật theo brand voice.

## Mô hình domain (đã có trong bot — web phải phản ánh)
Nguồn: `agents/operational_prompts.py`, `agents/campaign_ideation.py`,
`agents/campaign_scope_library.py`.
- **🟢 Always-on**: bài brand bám pillar/funnel, KHÔNG offer/deadline, phủ TOÀN BỘ kỳ.
- **🔴 Campaign**: chỉ khi có dịp/offer; chạy SONG SONG 🟢 trong các TUẦN thuộc đợt
  (`duration`); hết đợt → bỏ 🔴, giữ 🟢. Hai track có thể trùng ngày.
- **Dịp/mùa vụ** neo theo ngành (F&B: Tết/Trung Thu; Ecom: 11.11/12.12; Edu: tuyển sinh).

## Trong phạm vi
- **Lịch nội dung 2 track**: cột/nhãn Track 🟢/🔴; 🔴 chỉ hiện trong tuần thuộc đợt;
  đánh dấu window đợt across các tuần.
- **Tạo campaign theo dịp**: form hỏi *dịp* (gợi ý seasonal theo ngành) + *start/end*
  (window) + *offer/lever* → sinh lớp 🔴 đúng tuần.
- **Always-on baseline**: tự sinh từ content pillars (không offer/deadline).
- **Sinh nội dung thật**: truyền campaign context vào operational skill (skill tự xuất 2 track).
- Đọc/ghi đúng bảng thật (`posts`, `campaigns`) thay vì web_* mock.

## Thay đổi dữ liệu cần làm
- `campaigns` (hoặc web layer): thêm **occasion**, **start_date/end_date** (window), trạng thái.
- `posts`/calendar: thêm trường **track** ('always_on' | 'campaign') + liên kết campaign.

## NGOÀI phạm vi M1
- Tối ưu Ads (luồng c). Auth/billing (M4). Đa kênh nâng cao có thể cắt bớt.

## Definition of Done
- [ ] Lịch hiển thị đúng 2 track + lifecycle window (🔴 chỉ trong đợt).
- [ ] Tạo campaign theo dịp → lớp 🔴 xuất hiện đúng tuần; hết đợt chỉ còn 🟢.
- [ ] Sinh nội dung thật theo brand voice, lưu `posts`, hiển thị & duyệt được.
- [ ] Không nút giả; chi phí token vào quota; smoke test + Founder nghiệm thu.

## Rủi ro
- Mapping window theo TUẦN (không phải ngày lẻ) — phải khớp cách bot tính `duration`.
- Output skill là bảng markdown 2 track → web parse/hiển thị phải chịu biến thể.
