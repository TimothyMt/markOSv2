# Ads Scheduler — Hướng Dẫn Setup

Báo cáo ads tự động qua Telegram: digest 8:00 sáng (so hôm qua), weekly thứ Hai
(so 7 ngày trước), alert real-time mỗi 4 tiếng.

Mỗi user kết nối FB Ad Account riêng qua OAuth → bot tự pull data → phân tích → đẩy Telegram.

---

## Tổng quan kiến trúc

```
User /connect_ads → OAuth FB → callback lưu token (encrypted) per-user
                                      │
        ┌─────────────────────────────┴──────────────────────────┐
        ▼                                                          ▼
  Scheduler (asyncio loop)                              /ads_settings
  ├─ 8:00   Daily digest (T2 = Weekly)                  chọn metrics + ngưỡng
  ├─ /4h    Alert monitor (Freq/ROAS/CPM)
  ├─ 2:00   Token auto-refresh
  └─ CN 3:00 Cleanup snapshot >90 ngày
```

---

## Bước 1 — Chạy Database Migration

Mở **Supabase → SQL Editor**, paste toàn bộ nội dung file:

```
storage/migrations/010_fb_connections.sql
```

Tạo 4 bảng:
- `user_fb_connections` — token (encrypted) + settings per-user
- `oauth_states` — CSRF state token (TTL 15 phút)
- `ads_snapshots` — data ngày (giữ 90 ngày, để tính delta)
- `ads_alert_cooldowns` — chống spam alert (24h/alert)

**Verify:** chạy `SELECT * FROM user_fb_connections LIMIT 1;` — không lỗi là OK.

---

## Bước 2 — Tạo ENCRYPTION_KEY

Token FB **không lưu plain text**. Cần 1 Fernet key để mã hóa.

Tạo key (chạy local hoặc bất kỳ máy nào có Python):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Output dạng: `kJ8xR2..._q9zB4=` (44 ký tự, base64)

→ Set vào env var `ENCRYPTION_KEY` trên Railway.

> ⚠️ **Giữ key này cẩn thận.** Đổi key = mất toàn bộ token đã lưu (user phải /connect_ads lại).

---

## Bước 3 — Cấu hình Facebook App

### 3.1 Lấy App ID + Secret

1. Vào https://developers.facebook.com/apps/
2. Chọn App (hoặc tạo mới: type **Business**)
3. **Settings → Basic** → copy **App ID** và **App Secret**
4. Set env vars trên Railway:
   - `FB_APP_ID`
   - `FB_APP_SECRET`

### 3.2 Thêm OAuth Redirect URI

1. Trong App → **Use cases** → **Facebook Login** → **Settings**
   (hoặc **Products → Facebook Login → Settings**)
2. Mục **Valid OAuth Redirect URIs**, thêm:
   ```
   https://<WEBHOOK_URL của bạn>/oauth/fb/callback
   ```
   Ví dụ: `https://marketing-os-bot.up.railway.app/oauth/fb/callback`
3. Save.

> `WEBHOOK_URL` là domain Railway đã có sẵn (env var hiện tại). Redirect URI =
> `{WEBHOOK_URL}/oauth/fb/callback` — code tự ghép trong `services/fb_oauth.py`.

### 3.3 Xin quyền (App Review)

Bot cần 3 permissions:

| Permission | Dùng để |
|---|---|
| `ads_read` | Đọc danh sách campaign + insights |
| `read_insights` | Đọc metrics (spend, CPM, frequency...) |
| `ads_management` | `ads_optimizer` pause/activate/đổi budget |

**Chế độ Development (test ngay, không cần review):**
- App ở mode **Development** → chỉ tài khoản có **role** trong App (Admin/Developer/Tester) mới OAuth được.
- Thêm tester: **App Roles → Roles → Add People → Testers**.
- Đủ để test với chính tài khoản của bạn / team.

**Chế độ Production (mọi user):**
- Submit **App Review** cho 3 permissions trên → FB duyệt (vài ngày, cần screencast + mô tả).
- Sau khi duyệt → bất kỳ user nào cũng OAuth được.

> 💡 **Khuyến nghị:** test ở Development mode trước với tài khoản của bạn. Khi
> chạy ổn mới submit App Review cho production.

---

## Bước 4 — Env Vars Tổng Hợp (Railway)

Thêm các biến mới (các biến cũ giữ nguyên):

```
ENCRYPTION_KEY=<Fernet key từ bước 2>
FB_APP_ID=<App ID từ bước 3.1>
FB_APP_SECRET=<App Secret từ bước 3.1>
```

> `FB_ACCESS_TOKEN` và `FB_AD_ACCOUNT_ID` cũ vẫn dùng cho các skill khác
> (`ads_analytics` on-demand, `competitor_spy`). Scheduler dùng token per-user, không đụng.

---

## Bước 5 — Deploy & Verify

### 5.1 Cài dependencies

`requirements.txt` đã thêm: `cryptography`, `uvicorn`, `starlette`.
Railway tự `pip install` khi deploy.

> ⚠️ **Lưu ý quan trọng về entry point:** `bot/main.py` đã chuyển từ
> `app.run_webhook` (tornado) sang **starlette + uvicorn** để host được
> OAuth callback `/oauth/fb/callback` cùng port với Telegram webhook.
> Procfile (`web: python bot/main.py`) không đổi.

### 5.2 Checklist sau deploy

1. **Bot khởi động:** log thấy `PTB webhook registered` + `Background tasks started (... + ads scheduler)`
2. **Telegram webhook còn chạy:** gửi `/start` → bot phản hồi
3. **OAuth flow:** gửi `/connect_ads` → nhận link → bấm → approve trên FB →
   thấy trang "✅ Kết nối thành công" → Telegram nhận card xác nhận
4. **Settings:** `/ads_settings` → hiện keyboard chọn metric + toggle

### 5.3 Test scheduler nhanh (không đợi 8:00)

Tạm sửa giờ trong `services/ads_scheduler.py` `_tick()` để fire ngay (ví dụ
đổi `hour == 8` thành giờ hiện tại), deploy, chờ ≤30s, kiểm tra Telegram nhận
digest. **Nhớ revert** sau khi test.

---

## Các lệnh người dùng

| Lệnh | Chức năng |
|---|---|
| `/connect_ads` | Kết nối FB Ad Account (OAuth) |
| `/ads_settings` | Chọn chỉ số theo dõi + đặt ngưỡng alert + bật/tắt |
| `/disconnect_ads` | Ngắt kết nối, xóa token |

### Đặt ngưỡng alert (trong /ads_settings → "Đặt ngưỡng alert")

Gửi text format (bỏ trống dòng nào = Max tự dùng benchmark ngành):
```
frequency: 5.0
roas_drop: 20
cpm_spike: 30
```

---

## Chỉ số hỗ trợ

**FB trả thẳng:** spend, impressions, reach, clicks, ctr, cpc, cpm, frequency,
actions (leads/purchases), video views.

**Bot tự tính:** ROAS (= purchase_value/spend), CPL (= spend/leads),
VTR 3s (= video_3s/impressions), delta % so kỳ trước.

**Recommended (mặc định):** Spend · ROAS · CPL · Frequency

---

## Benchmark mặc định (khi user không set ngưỡng)

| Ngưỡng | Default | Ý nghĩa |
|---|---|---|
| Frequency max | 5.0 | > 5.0 = saturation → push alert |
| ROAS drop | 20% | giảm > 20% trong 24h → alert |
| CPM spike | 30% | tăng > 30% trong 24h → alert |

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `/connect_ads` báo "FB App chưa cấu hình" | thiếu `FB_APP_ID`/`FB_APP_SECRET` | set env vars (bước 3) |
| `/connect_ads` báo "ENCRYPTION_KEY chưa set" | thiếu key | bước 2 |
| OAuth báo "Link hết hạn" | state token > 15 phút | `/connect_ads` lại |
| Trang callback lỗi "redirect_uri" | URI chưa khớp trong FB App | bước 3.2 — check chính xác domain |
| Không nhận digest sáng | scheduler chưa chạy / token revoked | check log; user `/connect_ads` lại |
| Bot báo "Kết nối đã ngắt" | token hết hạn/revoke | user `/connect_ads` lại (settings giữ nguyên) |

---

## Token Lifecycle (tự động, user không cần làm gì)

```
Approve 1 lần → short token (2h) → bot extend → long token (60 ngày)
                                         │
                          Scheduler 2:00 sáng kiểm tra
                          còn < 7 ngày → tự refresh → 60 ngày mới
                                         │
                          Refresh fail (user revoke) → tắt notify
                          + nhắn user /connect_ads lại
```

Snapshot giữ **90 ngày**, tự xóa Chủ Nhật 3:00 sáng.
