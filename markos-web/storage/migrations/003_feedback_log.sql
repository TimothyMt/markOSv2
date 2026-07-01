-- Migration 003: Feedback log để tích lũy industry/skill learning
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS feedback_log (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL,
    skill_name    TEXT NOT NULL,
    rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    industry      TEXT,
    stage         TEXT,
    business_name TEXT,
    output_excerpt TEXT,             -- 500 first chars của output em đưa ra
    user_correction TEXT,            -- Feedback text user gửi nếu rating ≤ 3
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_skill_industry ON feedback_log(skill_name, industry);
CREATE INDEX IF NOT EXISTS idx_feedback_created       ON feedback_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_low_rating    ON feedback_log(rating)
    WHERE rating <= 3;
