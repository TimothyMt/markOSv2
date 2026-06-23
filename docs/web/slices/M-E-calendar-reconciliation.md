# SPEC — M-E: Reconciliation lịch nội dung (bài đã duyệt vs chiến lược đổi)

> Founder (2026-06-23): chốt làm mục #2 trước khi tiến tới "C hoàn chỉnh" (kéo-thả).
> Nguyên tắc tối thượng: **bài founder ĐÃ DUYỆT là tài sản — KHÔNG BAO GIỜ mất thầm lặng.**
> Web-owned; KHÔNG đụng agents/. Spec trước, code sau khi founder duyệt open questions.

## 1. Cơ chế hiện tại (để hiểu vì sao vỡ)
- Lịch **không lưu sẵn** — `calendar_plan()` **sinh lại deterministic** mỗi lần từ chiến lược.
- Bài duyệt-tại-ô lưu ở `profile.intake_extra.calendar_posts[slot_key] = {content, approved}`.
- slot_key nhúng dữ liệu chiến lược:
  - Always-on: `aw|{week}|{day}|{pillarName}` (business.py ~949)
  - Occasion:  `oc|{campaignId}|{phase}` (business.py ~917)
- Render: mỗi ô tra `saved_posts.get(key)` → có thì hiện bài đã lưu, không thì hiện gợi ý.

## 2. Lỗ hổng — "mất bài thầm lặng"
key gắn chặt output chiến lược cũ → chiến lược đổi thì key không khớp, bài thành **orphan**
(vẫn nằm DB nhưng KHÔNG ô nào tra ra, KHÔNG cảnh báo). Các tác nhân gây orphan:

**Always-on (`aw|week|day|pillarName`) — rất dễ vỡ:**
| Hành động của founder | Hệ quả |
|---|---|
| Đổi TÊN pillar | name trong key đổi → orphan |
| Bỏ pillar | không còn slot (đúng) → orphan |
| Đổi horizon 90→30 | tuần > 30 biến mất → orphan các tuần cao |
| Đổi cadence (posts_per_week) | `_assign_days()` phân ngày lại theo index → **day đổi → orphan dù pillar y nguyên** |
| Đổi THỨ TỰ pillar | day_of theo index dịch → **orphan gần như toàn bộ** |

**Occasion (`oc|campaignId|phase`) — ổn hơn nhưng vẫn vỡ:**
| Hành động | Hệ quả |
|---|---|
| Sửa window co lại (5→3 pha) | pha bị nén biến mất → orphan bài của pha đó |
| Xoá campaign | campaignId mất → orphan |
| Đổi ngày dịp/anchor | map ngày đổi (key vẫn theo phase nên còn khớp — ô đúng pha vẫn giữ bài) |

→ Always-on là điểm vỡ chính: key nhúng **vị trí biến động (week/day)** + **tên** thay vì danh tính ổn định.

## 3. Hai hướng thiết kế

### Hướng A — Tối thiểu: giữ key, thêm "khay orphan" + remap heuristic
- Khi `calendar_plan` chạy: tính các key trong `calendar_posts` KHÔNG khớp slot nào → danh sách **orphan**.
- Trả orphan về FE → hiện **khay "Bài chưa xếp lịch"** dưới lịch. Founder: giữ / gán lại / xoá.
- Remap tự động nhẹ: thử ghép orphan vào slot mới theo phần ổn định (cùng pillarName còn tồn tại → gán ô đầu trống của pillar đó; cùng campaignId+phase).
- Ưu: nhanh, ít refactor. Nhược: vẫn chắp vá; reorder/cadence vẫn tạo orphan hàng loạt rồi mới remap; chưa phải nền cho kéo-thả.

### Hướng B — Nâng cấp data model: bài duyệt = THẺ hạng nhất (đề xuất)
Cốt lõi: tách **"bài đã duyệt"** khỏi **"ô gợi ý sinh ra"**.
- Mỗi bài lưu thành thẻ có **danh tính ổn định + tham chiếu + vị trí tự quản**:
  ```
  calendar_posts[postId] = {
    content, approved,
    track: 'always'|'camp',
    ref:   { pillarId | campaignId, phase? },   # danh tính ổn định (KHÔNG dùng name/week/day)
    place: { week, day },                        # vị trí founder đặt — founder kéo đổi được (C)
    status:'placed'|'orphan'
  }
  ```
- `calendar_plan`: (1) sinh grid gợi ý như cũ; (2) **phủ thẻ đã lưu lên grid theo `place`** (thẻ thắng ô gợi ý); (3) thẻ có `ref` trỏ tới pillar/campaign KHÔNG còn tồn tại → `status='orphan'` → khay.
- pillarId: pillars hiện chỉ có name → cần cấp **id ổn định cho mỗi pillar** khi `save_pillars` (vd slug/uuid lưu kèm), để đổi tên KHÔNG mất liên kết.
- Ưu: đổi tên/đổi thứ tự/đổi cadence KHÔNG còn orphan (chỉ phụ thuộc pillarId + place do founder giữ); đây CHÍNH là nền cho "C hoàn chỉnh" (kéo-thả = sửa `place`). Nhược: refactor lớn hơn, cần migration mềm cho `calendar_posts` cũ.

### Migration mềm (cho B)
- key cũ `aw|w|d|name` / `oc|cid|phase` vẫn đọc được: 1 lần convert sang thẻ mới
  (suy `place` từ w/d; `ref.pillarId` = match theo name hiện có, không match → orphan; `ref.campaignId/phase` parse trực tiếp). Không xoá dữ liệu cũ tới khi convert xong.

## 4. Chính sách reconciliation (áp cho cả A/B)
1. **Không bao giờ xoá thầm.** Bài không khớp → chuyển khay orphan, không biến mất.
2. **Thẻ đã duyệt thắng ô gợi ý** tại cùng vị trí (regen không ghi đè bài đã duyệt).
3. **Auto-remap khi an toàn** (cùng ref ổn định còn tồn tại); không chắc → để khay cho founder quyết.
4. **Cảnh báo rõ**: khi mở lịch sau khi đổi chiến lược, banner "N bài cần xếp lại" + khay.

## 5. Phạm vi đề xuất đợt này
- Làm **Hướng B** (vì là nền cho C, tránh làm A rồi đập đi). Gồm:
  1. Cấp `pillarId` ổn định ở `save_pillars` + đọc ra ở `campaign_plan`/`calendar_plan`.
  2. Đổi `save_calendar_post` lưu theo schema thẻ (postId + ref + place); migration mềm key cũ.
  3. `calendar_plan` phủ thẻ theo place + đánh dấu orphan; trả `orphans[]`.
  4. FE: khay "Bài chưa xếp lịch" + banner cảnh báo + nút gán/xoá (kéo-thả để pha C sau).
  5. Mirror app.js ↔ standalone; verify static.
- CHƯA làm kéo-thả thật (đó là C) — đợt này dựng XONG nền dữ liệu + khay + an toàn-không-mất.

## 6. Mở / cần founder chốt
- [ ] Q1: Chọn **Hướng B** (refactor nền, không mất bài, sẵn cho C) hay **Hướng A** (vá nhanh)?
      → đề xuất: B.
- [ ] Q2: pillarId sinh kiểu gì — slug từ name (đọc dễ, nhưng đổi name đổi slug) hay uuid
      (ổn định tuyệt đối, nhưng cần lưu kèm)? → đề xuất: uuid ngắn lưu trong pillar.
- [ ] Q3: Orphan để founder tự xử (gán/xoá) hay Max **tự gợi ý ô phù hợp** (gọi LLM match
      bài↔pillar mới)? → đề xuất: tự xử trước; gợi ý LLM để pha sau.
- [ ] Q4: Khi orphan vì pillar bị bỏ — giữ trong khay vô thời hạn hay có nút "lưu vào Tài liệu"
      để không kẹt ở lịch? → đề xuất: có nút chuyển sang Tài liệu.
