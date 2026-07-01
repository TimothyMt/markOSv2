# SPEC — M3 Content Suite (hybrid, post-centric)

> Spec-driven. Founder chốt (2026-06-21): **Hybrid + làm đầy đủ**; **gỡ hẳn "Trình tạo
> nội dung"**. Nền: M1.2 (Lịch tạo bài thật) · D-040 (pillars) · D-008 (không UI giả).

## 0. Vấn đề
Việc tạo content đang TRÙNG: Lịch nội dung đã có "⚡ Tạo bài" thật, nhưng còn ~6 trang
content rời (mock) cũng "tạo bài" → rối, 2 nơi.

## 1. Mô hình hybrid (chốt)
**Content gốc tạo TRONG Lịch. Biến thể là PHÁI SINH của 1 bài. Vài loại đặc thù giữ trang riêng.**

| Loại | Bản chất | Nơi | Skill engine tái dùng |
|---|---|---|---|
| Post organic | bài nền/đợt theo slot | **Lịch** (đã có) | post_write |
| 📱 Đa kênh | 1 bài → FB/TikTok/Zalo | **phái sinh từ bài** (modal) | post_adapt |
| 🎬 Kịch bản video | 1 bài/ý → script | **phái sinh từ bài** | video_script_gen |
| 📸 UGC brief | 1 bài/ý → brief creator | **phái sinh từ bài** | ugc_brief |
| 🧲 Ads copy | creative theo phễu (TOFU/MOFU/BOFU) | **trang riêng** (real) | post_hooks/creative |
| ✉️ Email/Zalo chuỗi | sequence nurture | **trang riêng** (real, gần Retention) | email_zalo_sequence |
| 💬 Sales Inbox | script CS xử lý từ chối | **trang riêng** (real) | sales_inbox_script |
| 🗣️ Brand Voice | config giọng | **trang riêng** (đọc real bizBrandVoice) | post_voice_check |

## 2. Phân kỳ
- **M3.1 — consolidate (build trước):**
  - GỠ trang "Trình tạo nội dung" (`content`) — trùng nút Tạo bài. Redirect `#content`→`#calendar`.
  - GỠ trang standalone `video`, `ugc` mock → biến thành **phái sinh từ 1 bài** (modal Lịch).
  - Backend `gen_derivative(uid, kind, source)` (kind: channels/video/ugc) → router_call → skill_run.
  - FE: modal sau "⚡ Tạo bài" có nút 📱/🎬/📸 → sinh biến thể thật → hiện + lưu.
- **M3.2 — trang đặc thù thật:** Ads copy (phễu), Email/Zalo chuỗi, Sales Inbox — mỗi trang
  1 generator thật bám strategy/USP, lưu skill_run, degrade rõ. Brand Voice: đọc real + cho tạo.
- **NGOÀI M3:** lịch xuất bản tự động, A/B copy, kho asset.

## 3. Tái dùng / degrade (D-008)
- Web-side `router_call` (OPS_CONTENT_CREATIVE / CHANNEL_ADAPT / OPS_CONTENT_BULK) — KHÔNG nhân bản engine.
- Mọi generator: thiếu strategy/USP hoặc lỗi → toast/empty, KHÔNG mock số. Lưu skill_run để tái dùng doc-reader.
