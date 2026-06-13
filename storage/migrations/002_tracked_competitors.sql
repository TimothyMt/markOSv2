-- Migration 002: Auto-monitor competitor ads tracking
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS tracked_competitors (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL,            -- Telegram chat ID
    page_id        TEXT NOT NULL,              -- Facebook page numeric ID
    page_name      TEXT,                       -- Display name (vd "Bitis Vietnam")
    interval_hours INT NOT NULL DEFAULT 24,    -- Check frequency (3/6/12/24/168)
    last_check_at  TIMESTAMPTZ DEFAULT NOW(),
    last_ad_ids    JSONB DEFAULT '[]'::jsonb,  -- List of ad IDs snapshot
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, page_id)
);

CREATE INDEX IF NOT EXISTS idx_tracked_user ON tracked_competitors(user_id);
CREATE INDEX IF NOT EXISTS idx_tracked_due  ON tracked_competitors(last_check_at, is_active)
    WHERE is_active = TRUE;

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_tracked_competitors_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_tracked_competitors_updated_at ON tracked_competitors;
CREATE TRIGGER trg_tracked_competitors_updated_at
    BEFORE UPDATE ON tracked_competitors
    FOR EACH ROW EXECUTE FUNCTION update_tracked_competitors_updated_at();
