-- Migration 004: Brand Voice persistent DB
-- Run in Supabase SQL Editor sau migration 003.
-- Lưu Brand Voice rules per user — auto-inject vào ops creative skills.

CREATE TABLE IF NOT EXISTS user_brand_voice (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           BIGINT NOT NULL,
    version           INT NOT NULL DEFAULT 1,

    -- Core rules
    do_rules          JSONB DEFAULT '[]'::jsonb,    -- list[str] — 3-5 things to DO
    dont_rules        JSONB DEFAULT '[]'::jsonb,    -- list[str] — 3-5 things to AVOID
    tone_descriptors  JSONB DEFAULT '[]'::jsonb,    -- list[str] — ["warm", "expert", "playful"]
    banned_words      JSONB DEFAULT '[]'::jsonb,    -- list[str]
    preferred_words   JSONB DEFAULT '[]'::jsonb,    -- list[{from,to}]
    sample_content    TEXT,                          -- 1-2 đoạn content cũ user paste

    -- Generated artifacts (output từ BrandVoiceSkill)
    rules_markdown    TEXT,                          -- Full markdown output cho user reference
    industry_context  TEXT,

    is_active         BOOLEAN DEFAULT true,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Lookup nhanh BV active của user
CREATE INDEX IF NOT EXISTS idx_brand_voice_user
    ON user_brand_voice(user_id)
    WHERE is_active = true;

-- Trigger auto-update updated_at
CREATE OR REPLACE FUNCTION update_brand_voice_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_brand_voice_updated_at ON user_brand_voice;
CREATE TRIGGER trg_brand_voice_updated_at
    BEFORE UPDATE ON user_brand_voice
    FOR EACH ROW
    EXECUTE FUNCTION update_brand_voice_timestamp();
