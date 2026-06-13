-- Migration 001: Base sessions table
-- Run first in Supabase SQL Editor before any other migration.

CREATE TABLE IF NOT EXISTS sessions (
    user_id        BIGINT PRIMARY KEY,
    stage          TEXT    NOT NULL DEFAULT 'idle',
    profile        JSONB   NOT NULL DEFAULT '{}',
    intake_history JSONB   NOT NULL DEFAULT '[]',
    results        JSONB   NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on every upsert
CREATE OR REPLACE FUNCTION update_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sessions_updated_at ON sessions;
CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_sessions_updated_at();

-- Index for stage filtering (housekeeping queries)
CREATE INDEX IF NOT EXISTS idx_sessions_stage ON sessions(stage);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
