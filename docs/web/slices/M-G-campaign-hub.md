# SPEC — M-G: Campaign Hub (campaign-first; mọi thứ bắt đầu từ campaign)

> Founder (2026-06-25): reframe lớn. KHÔNG còn "always-on pillars trôi nổi". Luồng mới:
> T1-T5 xong → user XÂY DỰNG CAMPAIGN (chọn loại: branding/awareness/...) → Max sinh CAMPAIGN BRIEF
> theo lựa chọn → từ brief DỰNG LỊCH NỘI DUNG (tham khảo bot). Branding = 1 campaign XUYÊN SUỐT, LƯU THẬT.
> Web-owned; KHÔNG sửa agents/. Spec — code sau khi duyệt.

## 1. LUỒNG CHỦ ĐẠO (mới — founder chốt)
```
T1-T3 (research) → T4-T5 (synthesis + playbook = phương án khả thi)
   → BƯỚC XÂY DỰNG CAMPAIGN:
       1. User tạo campaign + CHỌN LOẠI (branding · awareness · ra mắt · sale · thu lead · …)
       2. Max sinh CAMPAIGN BRIEF theo loại + bám synthesis/playbook (lựa chọn user định hình brief)
       3. Từ brief → Max DỰNG LỊCH NỘI DUNG  (tham khảo bot: brief → funnel map → content calendar)
   → Campaign = HUB gom mọi thứ (10 thành phần)
```
- **Branding** = campaign **xuyên suốt** (persistent, không window/deadline) — giữ bản chất "nền được nhớ"
  (Byron Sharp) nhưng GÓI thành 1 campaign có tên, **lưu thật**.
- **Occasion** = campaign có window (như M-F). Cả 2 đều là campaign lưu trong DB.

## 2. Tham khảo BOT cho "brief → lịch nội dung" (mắt xích then chốt)
Bot có sẵn chuỗi (agents/, reference-only):
- `CAMPAIGN_BRIEF_SYSTEM` → brief 10 mục.
- `FUNNEL_MAPPER_SYSTEM` → map brief thành **3-stage funnel (TOFU/MOFU/BOFU) cho TỪNG kênh** theo archetype.
- `CONTENT_CALENDAR_SYSTEM` → từ brief + funnel map → **lịch nội dung** (Story Arc theo tuần + weekly grid,
  mỗi bài: Pillar/Funnel/Nhóm khách/Format/Content angle/Hook/Topic).
→ Web sẽ port mạch này: **campaign brief → (funnel map) → content calendar của campaign**, thay vì
calendar dựng từ "pillars toàn cục" như hiện tại.

## 3. Campaign = HUB 10 thành phần (đã duyệt)
| # | Thành phần | Branding (xuyên suốt) | Occasion |
|---|---|---|---|
| 1 | Đầu campaign | tên · loại · mục tiêu · tệp nhắm · **liên tục** | + window |
| 2 | Brief/định hướng | định vị nền + big idea + key message (sinh từ synthesis, KHÔNG SMART/deadline) | arc 5 pha + SMART + offer |
| 3 | Kênh + vai trò mỗi kênh (funnel map per-kênh) | có | có |
| 4 | Content backbone + **lịch nội dung của campaign** | pillars + lịch liên tục | bài theo arc + band |
| 5 | Deliverables/Task (kanban) — campaign bthg | posts·video·ugc… | + ads·email·landing·inbox |
| 6 | KPI | reach/nhớ (định hướng) | số theo mục đích |
| 7 | Ngân sách | định hướng (không số) | số đợt (SMART) |
| 8 | Rủi ro & cờ đỏ | có | có |
| 9 | Liên kết nguồn (lineage: synthesis/playbook bản nào) | có | có |
| 10 | Trạng thái tổng (% task) | có | có |

🔴 GIỮ bản chất: Branding **liên tục, không deadline/arc/SMART số** (D-029). "Campaign" = container có tên.

## 4. ĐÃ CHỐT (2026-06-25)
- **Q1 = LƯU THẬT**: Branding là 1 **`campaigns_v2` row** (type=`branding`, không start/end_date → "xuyên suốt").
  Tạo khi user dựng campaign branding (không auto-đẻ). Meta/task ở `campaign_meta[cid]` như M-F.
- **Q2 = (A)** Brand brief **sinh nhẹ 1 LLM call** (big idea + key message + định vị nền), **bám synthesis**,
  KHÔNG SMART/deadline.
- **Q3 = CÓ** bộ task deliverable cho branding (như campaign thường).
- **Q4 = TRANG RIÊNG** cho hub detail (đủ chỗ 10 mục).
- **Q5** = xem mục 6 (conflict check).

## 5. Data & generation
- Branding: `campaigns_v2` row {type:'branding', start/end=null}; `campaign_meta[cid]`={type,tasks,channels,
  audience,kpi,brand_brief_run_id,lineage_fp…}. Brief lưu skill_run 'branding_brief'.
- `gen_branding_brief(uid)`: 1 LLM call đọc synthesis+playbook+USP+archetype+resource → big idea/key
  message/định vị nền/KPI định hướng (KHÔNG SMART). Tái dùng resource_block (team_size) đã có.
- **Lịch nội dung từ brief**: pha sau — port mạch bot (brief → funnel map → calendar). Pha đầu: branding
  calendar tái dùng pillars+`calendar_plan` (đã có) như content engine; occasion giữ M-D.
- Occasion: nguyên M-F.

## 6. Q5 — CONFLICT CHECK với cái đang có (M-A…M-F)
KHÔNG xung đột nền tảng — chủ yếu **tái dùng + tái đóng gói**, đổi ENTRY UX:
| Đang có | Số phận trong M-G |
|---|---|
| pillars_locked + calendar_plan always-on (M-A) | → trở thành **content engine của campaign Branding** (tái dùng) |
| occasion arc trên lịch (M-D) | → giữ, là content của campaign occasion |
| reconciliation + topics (M-E/E2) | → áp cho lịch của campaign (tái dùng) |
| campaign type + task + kanban + portfolio (M-F) | → NỀN của M-G; **thêm type 'branding' xuyên suốt** |
| Trang "Lập chiến dịch" (pillars trái + occasion phải) | → **THAY** bằng: danh sách campaign + nút "Tạo campaign" |

⚠️ Điểm cần xử khi làm (không phải conflict chặn, mà là việc):
1. **Lịch hiện là "always-on toàn cục"** (1 track từ pillars chung). Khi branding thành campaign, lịch nội
   dung = **content của campaign Branding** (đổi nhãn, logic gần như cũ vì cũng từ pillars). Occasion vẫn là band.
2. Mạch **brief → funnel → calendar** (bot) là phần MỚI, làm ở pha sau (G2), thay dần cách dựng calendar
   từ pillars chung.
3. `pillars_locked` (toàn cục) → gắn vào campaign Branding (1 cái) — không cần migration phức tạp vì 1 user
   1 branding.

→ Kết luận Q5: **không conflict**; thứ tự G1 (hợp nhất hiển thị, tái dùng data) vẫn hợp lý, rồi G2 port
mạch brief→calendar của bot.

## 7. Phạm vi & thứ tự (điều chỉnh theo reframe)
- **G1 — Entry campaign-first + Branding là campaign thật**: thêm type 'branding' (xuyên suốt) vào bộ loại;
  thay trang "Lập chiến dịch" bằng **danh sách campaign + "Tạo campaign"**; tạo branding → `campaigns_v2` row;
  hub detail **trang riêng** (10 mục, đọc data sẵn: pillars/kênh/lịch/task). `gen_branding_brief` (Q2-A).
- **G2 — Brief → Lịch nội dung (port bot)**: funnel map + content_calendar từ brief của campaign (thay dần
  calendar-from-pillars-toàn-cục). Áp cho cả branding lẫn occasion.
- **G3 — Hoàn thiện hub**: KPI/rủi ro/lineage/% tiến độ + badge lệch nguồn (nối N-07).

## 8. Mở / cần chốt thêm
- [ ] Lịch nội dung: **1 lịch hợp nhất** (mọi campaign đổ vào) hay **lịch riêng từng campaign**? (đề xuất:
      1 lịch hợp nhất, lọc theo campaign — quen thuộc, đỡ phân mảnh.)
- [ ] G1 có cần **auto-tạo** sẵn 1 campaign Branding sau khi chốt chiến lược, hay **user tự tạo**? (founder
      nói "user sẽ xây dựng" → để user tạo; có thể gợi ý 1 nút "Tạo campaign Branding nền".)
