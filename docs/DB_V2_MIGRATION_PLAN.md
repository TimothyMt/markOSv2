# 📋 DB v2 Migration Plan & Test Runbook

> **Status**: Phase A (chưa bắt đầu migrate) | **Branch**: `refactor/db-v2-normalize`
> **Tài liệu này = runbook**: làm tới đâu tick tới đó. Quay lại check bất cứ lúc nào.

---

## 🎯 Mục tiêu

Refactor `sessions` monolithic JSONB → 6 bảng chuẩn hoá (users, profile, sessions_slim, skill_runs, campaigns, posts). Migrate bằng **Dual-Write** pattern, zero downtime, rollback dễ.

---

## 🚦 Trạng thái hiện tại

```
✅ Phase 1 Done — Build phase
   - Migration SQL 006 sẵn sàng
   - 6 storage modules (storage/v2/*) sẵn sàng
   - Adapter layer (session_v2_adapter.py) sẵn sàng
   - Backfill script (scripts/backfill_v2.py) sẵn sàng
   - Drift detection (scripts/verify_v2_drift.py) sẵn sàng
   - Branch refactor/db-v2-normalize đã push
   - USE_DB_V2 default False → production an toàn

⏳ Phase 2 — Sếp cần làm thủ công (xem checklist dưới)
⏳ Phase 3-5 — Sau khi Phase 2 stable
```

---

## ✅ CHECKLIST PHASE 2 — Bắt đầu Dual-Write

### Bước 1 — Apply migration 006 trong Supabase

- [ ] Mở Supabase Dashboard → SQL Editor → New Query
- [ ] Copy nội dung file `storage/migrations/006_normalize_schema.sql`
- [ ] Paste vào SQL Editor → Click **Run**
- [ ] Verify: chạy query sau, expect 6 tables hiện ra
  ```sql
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN (
      'users', 'user_business_profile', 'user_sessions_slim',
      'skill_runs', 'campaigns', 'posts'
    )
  ORDER BY table_name;
  ```

**Rollback nếu lỗi**: Drop các table mới
```sql
DROP TABLE IF EXISTS posts CASCADE;
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS skill_runs CASCADE;
DROP TABLE IF EXISTS user_sessions_slim CASCADE;
DROP TABLE IF EXISTS user_business_profile CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP FUNCTION IF EXISTS touch_updated_at();
DROP FUNCTION IF EXISTS reset_stale_sessions();
```

---

### Bước 2 — Chạy backfill script (1 lần)

- [ ] Mở terminal local trong thư mục `marketing-os-bot`
- [ ] Đảm bảo `.env` file có `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`
- [ ] Chạy:
  ```bash
  python -m scripts.backfill_v2
  ```
- [ ] Đợi script chạy xong, đọc summary cuối:
  ```
  BACKFILL COMPLETE
    Users created:       X
    Profiles created:    Y
    Sessions migrated:   Z
    Skill runs migrated: N
    Errors:              0   ← phải là 0
  ```
- [ ] Verify trong Supabase SQL Editor:
  ```sql
  -- Count tổng
  SELECT 
    (SELECT COUNT(*) FROM users)                    AS total_users,
    (SELECT COUNT(*) FROM user_business_profile)    AS total_profiles,
    (SELECT COUNT(*) FROM user_sessions_slim)       AS total_sessions,
    (SELECT COUNT(*) FROM skill_runs)               AS total_runs,
    (SELECT COUNT(*) FROM sessions)                 AS v1_sessions;
  ```
  → `total_users` phải ≈ `v1_sessions` (cùng số lượng)

**Rollback**: Backfill idempotent (UPSERT), chạy lại không hỏng. Nếu muốn xoá data v2:
```sql
TRUNCATE skill_runs, posts, campaigns,
         user_sessions_slim, user_business_profile, users CASCADE;
```

---

### Bước 3 — Switch Railway sang branch refactor

- [ ] Vào Railway Dashboard → Service → Settings → **Source**
- [ ] Đổi Branch: `content-gen-suite` → `refactor/db-v2-normalize`
- [ ] Save → Railway tự redeploy (~2-3 phút)
- [ ] Kiểm tra Logs → bot start thành công, không error import

**Rollback**: Đổi branch về `content-gen-suite` → redeploy

---

### Bước 4 — Bật DUAL-WRITE mode

- [ ] Railway → Variables → Thêm:
  ```
  DB_V2_WRITE=true
  DB_V2_READ=false
  ```
- [ ] Railway tự redeploy
- [ ] Kiểm tra Logs sau redeploy:
  - Không có spam error `Dual-write v2 failed`
  - Hoặc nếu có vài lỗi → đọc message, fix nếu cần

**Status sau bước này**: Bot ghi cả v1 + v2. Read vẫn từ v1.

---

### Bước 5 — Test smoke: bot vẫn hoạt động bình thường

- [ ] Gửi `/start` → bot phản hồi
- [ ] Gửi `max ơi` → bot show menu (không hỏi business như trước)
- [ ] Chọn 1 skill (vd: Market Research) → chạy xong, có kết quả
- [ ] Check Supabase:
  ```sql
  -- User cũ có sync sang v2 chưa?
  SELECT * FROM users WHERE user_id = 7011450357;
  SELECT * FROM user_business_profile WHERE user_id = 7011450357;
  SELECT * FROM user_sessions_slim WHERE user_id = 7011450357;
  
  -- Skill runs mới có ghi không?
  SELECT skill_name, version, created_at
  FROM skill_runs
  WHERE user_id = 7011450357
  ORDER BY created_at DESC
  LIMIT 5;
  ```

---

## 🔍 CHECKLIST PHASE 3 — Verify drift, chuẩn bị cutover

### Bước 6 — Đợi 2-3 ngày, dual-write tích luỹ data

- [ ] Người dùng tương tác bot bình thường
- [ ] Mỗi save_session ghi cả 2 bảng

### Bước 7 — Chạy drift detection

- [ ] Local terminal:
  ```bash
  # Check toàn bộ user
  python -m scripts.verify_v2_drift
  
  # Hoặc check 1 user cụ thể
  python -m scripts.verify_v2_drift 7011450357
  ```
- [ ] Đọc DRIFT REPORT cuối:
  ```
  Total users checked: X
  Clean (no drift):    Y
  Drifted:             Z  ← target: 0 hoặc < 5%
  ```
- [ ] Nếu có drift → đọc chi tiết để biết field nào sai
  - Common drift: `token_used` (race condition khi save fast) → acceptable
  - Critical drift: `profile.business_name`, `session.stage` → phải fix

### Bước 8 — Decision: cutover hay fix drift

**Nếu drift = 0% hoặc < 5% non-critical** → tiến tới Phase 4

**Nếu drift > 5% hoặc có critical fields** → KHÔNG cutover, debug:
- Đọc Railway logs tìm `Dual-write v2 failed`
- Fix bug trong `storage/session_v2_adapter.py`
- Push fix → wait 1-2 ngày → run drift lại

---

## 🚀 CHECKLIST PHASE 4 — Cutover sang V2

### Bước 9 — Switch READ sang V2

- [ ] Railway → Variables → đổi:
  ```
  DB_V2_WRITE=true      ← vẫn dual-write làm backup
  DB_V2_READ=true       ← đọc từ v2 production
  ```
- [ ] Redeploy → test bot vài lần
- [ ] Kiểm tra Logs xem có lỗi `V2 get_session failed` không
  - Nếu có → tự động fallback v1 (an toàn)
  - Nhưng phải xem lỗi gì để fix

**Rollback**: set `DB_V2_READ=false` → quay về đọc v1 ngay

### Bước 10 — Theo dõi 1-2 tuần

- [ ] Daily check Railway logs cho lỗi
- [ ] Weekly chạy drift script
- [ ] Verify performance:
  - Bot response time có nhanh hơn không?
  - Supabase metrics: query count giảm?

---

## 🧹 CHECKLIST PHASE 5 — Cleanup (1 tháng sau cutover ổn định)

### Bước 11 — Tắt dual-write

- [ ] Railway → Variables → đổi:
  ```
  DB_V2_WRITE=false     ← V1 không update nữa
  DB_V2_READ=true
  ```
- [ ] V1 sessions table trở thành read-only backup

### Bước 12 — Drop V1 table (DECISION POINT — không revert được)

⚠️ **Chỉ làm khi đã chắc chắn V2 stable 1 tháng**

- [ ] Backup V1 trước:
  ```sql
  CREATE TABLE sessions_archive_2026 AS 
  SELECT * FROM sessions;
  ```
- [ ] Drop V1:
  ```sql
  DROP TABLE sessions;
  ```
- [ ] Clean up legacy code:
  - Xoá `storage/session.py:_row_to_session()` (dùng cho v1 only)
  - Xoá fallback logic trong `get_session()` / `save_session()`
  - Tạo PR riêng để review kỹ

### Bước 13 — Setup auto-reset cron

- [ ] Trong Supabase → Database → Extensions → enable `pg_cron`
- [ ] Tạo cron job:
  ```sql
  SELECT cron.schedule(
    'reset-stale-sessions',
    '0 * * * *',  -- mỗi giờ
    $$SELECT reset_stale_sessions()$$
  );
  ```
- [ ] Verify job chạy:
  ```sql
  SELECT * FROM cron.job;
  SELECT * FROM cron.job_run_details ORDER BY end_time DESC LIMIT 10;
  ```

---

## 🆘 EMERGENCY ROLLBACK MATRIX

| Tình huống | Action ngay | Hiệu lực |
|-----------|-------------|---------|
| Bot crash sau khi flip flag | Railway env: `DB_V2_WRITE=false DB_V2_READ=false` → redeploy | < 3 phút về v1 |
| Drift quá nhiều (>20%) | Như trên, debug rồi thử lại sau | Quay về Phase A |
| V2 read trả về sai data | `DB_V2_READ=false` | Đọc v1 ngay |
| Migration 006 lỗi | DROP tables (xem rollback Bước 1) | V1 không ảnh hưởng |
| Backfill lỗi giữa chừng | Chạy lại — idempotent | Không hỏng |

---

## 📊 KPIs để đo lường thành công

### Trước migration (baseline)
- [ ] Bot response time avg: _____ ms
- [ ] Supabase query count/min: _____
- [ ] Row size sessions trung bình: _____ KB
- [ ] Số bug "stuck stage" / tuần: _____

### Sau Phase D (cutover xong)
- [ ] Bot response time avg: _____ ms (kỳ vọng < 50% baseline)
- [ ] Supabase query count/min: _____ (giảm 70-90%)
- [ ] Row size trung bình: _____ KB (giảm 90%+)
- [ ] Số bug "stuck stage": 0 (auto-reset cron giải quyết)

---

## 📝 LOG QUÁ TRÌNH

> Sếp ghi lại mỗi lần làm 1 bước để track tiến độ

| Date | Step | Result | Notes |
|------|------|--------|-------|
| YYYY-MM-DD | Bước 1: Apply migration | ✅/❌ | ... |
| YYYY-MM-DD | Bước 2: Backfill | ✅/❌ | Stats: ... |
| YYYY-MM-DD | Bước 4: WRITE=true | ✅/❌ | ... |
| YYYY-MM-DD | Bước 7: First drift check | ... | Drift %: ... |
| YYYY-MM-DD | Bước 9: READ=true | ✅/❌ | ... |
| YYYY-MM-DD | Bước 11: WRITE=false | ✅/❌ | ... |
| YYYY-MM-DD | Bước 12: Drop sessions | ⚠️ | Backup name: ... |

---

## 🔗 Tham khảo

- Migration SQL: `storage/migrations/006_normalize_schema.sql`
- Storage modules: `storage/v2/`
- Adapter: `storage/session_v2_adapter.py`
- Backfill: `scripts/backfill_v2.py`
- Drift check: `scripts/verify_v2_drift.py`
- Config flags: `config.py` → `DB_V2_WRITE` / `DB_V2_READ`

**Branch**: `refactor/db-v2-normalize`
**Main production branch**: `content-gen-suite`
