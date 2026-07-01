-- Migration 008: Add missing columns to V2 tables
-- Fixes Bugs 1-5 in session_v2_adapter for full V1→V2 cutover.

-- Bug 1: pending_followup_skill missing from user_sessions_slim
ALTER TABLE user_sessions_slim
    ADD COLUMN IF NOT EXISTS pending_followup_skill TEXT;

-- Bug 2: content_outputs (POST-XXX dict) missing from user_sessions_slim
ALTER TABLE user_sessions_slim
    ADD COLUMN IF NOT EXISTS content_outputs JSONB DEFAULT '{}'::jsonb;

-- Bug 3: _token_log missing from user_sessions_slim
ALTER TABLE user_sessions_slim
    ADD COLUMN IF NOT EXISTS token_log JSONB DEFAULT '[]'::jsonb;

-- Bug 5: cost_used_usd missing from users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS cost_used_usd NUMERIC(12,6) DEFAULT 0;
