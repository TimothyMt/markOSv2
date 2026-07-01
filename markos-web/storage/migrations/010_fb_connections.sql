-- Migration 010: FB OAuth per-user + Ads Scheduler
-- Chạy trong Supabase SQL Editor

-- ── 1. Kết nối FB per-user ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_fb_connections (
    user_id              BIGINT PRIMARY KEY,         -- Telegram user_id
    encrypted_token      TEXT NOT NULL,              -- Fernet encrypted long-lived token
    ad_account_id        TEXT NOT NULL,              -- "act_XXXXXXXXXX"
    account_name         TEXT,                       -- tên account friendly
    expires_at           TIMESTAMPTZ,                -- token expiry (long-lived ~60 ngày)
    connected_at         TIMESTAMPTZ DEFAULT NOW(),
    last_pull_at         TIMESTAMPTZ,                -- lần cuối scheduler pull thành công

    -- Notification settings
    notification_enabled BOOLEAN DEFAULT TRUE,
    notify_time          TEXT DEFAULT '08:00',       -- "HH:MM" Asia/Ho_Chi_Minh
    timezone             TEXT DEFAULT 'Asia/Ho_Chi_Minh',

    -- Metrics user muốn theo dõi (chọn lúc setup)
    -- Supported keys: spend, roas, cpl, frequency, cpm, ctr, vtr_3s, reach, purchases, cpa, cpc, lead_rate
    tracked_metrics      TEXT[] DEFAULT ARRAY['spend','roas','cpl','frequency'],

    -- Alert thresholds — NULL = Max tự dùng benchmark ngành
    alert_frequency_max  FLOAT,                      -- push khi F vượt mức này
    alert_roas_drop_pct  FLOAT,                      -- push khi ROAS giảm X% trong 24h
    alert_cpm_spike_pct  FLOAT                       -- push khi CPM tăng X% trong 24h
);

-- ── 2. OAuth state tokens (CSRF protection, TTL 15 phút) ────────
CREATE TABLE IF NOT EXISTS oauth_states (
    state_token TEXT PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL
);

-- ── 3. Daily snapshots (giữ 90 ngày, dùng tính delta) ──────────
CREATE TABLE IF NOT EXISTS ads_snapshots (
    user_id        BIGINT NOT NULL,
    snapshot_date  DATE NOT NULL,
    campaign_id    TEXT NOT NULL,
    campaign_name  TEXT,

    -- Direct từ FB API
    spend          NUMERIC DEFAULT 0,
    impressions    NUMERIC DEFAULT 0,
    reach          NUMERIC DEFAULT 0,
    clicks         NUMERIC DEFAULT 0,
    ctr            FLOAT DEFAULT 0,
    cpm            FLOAT DEFAULT 0,
    frequency      FLOAT DEFAULT 0,
    leads          NUMERIC DEFAULT 0,
    purchases      NUMERIC DEFAULT 0,
    purchase_value NUMERIC DEFAULT 0,
    video_views_3s NUMERIC DEFAULT 0,

    -- Computed khi insert
    roas           FLOAT DEFAULT 0,    -- purchase_value / spend
    cpl            FLOAT DEFAULT 0,    -- spend / leads
    vtr_3s         FLOAT DEFAULT 0,    -- video_views_3s / impressions

    created_at     TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (user_id, snapshot_date, campaign_id)
);

CREATE INDEX IF NOT EXISTS idx_ads_snapshots_user_date
    ON ads_snapshots (user_id, snapshot_date DESC);

-- ── 4. Alert cooldowns (tránh spam cùng 1 alert > 1 lần/24h) ───
CREATE TABLE IF NOT EXISTS ads_alert_cooldowns (
    user_id      BIGINT NOT NULL,
    campaign_id  TEXT NOT NULL,
    alert_type   TEXT NOT NULL,   -- 'frequency' | 'cpm_spike' | 'roas_drop'
    last_sent_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, campaign_id, alert_type)
);

-- ── Cleanup: xóa snapshot > 90 ngày (chạy bởi scheduler hàng tuần) ──
-- Không dùng pg_cron — scheduler Python sẽ gọi DELETE thủ công
