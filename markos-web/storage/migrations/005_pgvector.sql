-- Migration 005: pgvector Semantic Search — Sprint 8
-- Run sau migration 004 trong Supabase SQL Editor.
-- Enable pgvector + campaign history table với embedding support.

-- 1. Enable pgvector extension (Supabase đã pre-install sẵn)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Campaign history table
CREATE TABLE IF NOT EXISTS user_campaign_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         BIGINT NOT NULL,

    -- Business context snapshot
    business_name   TEXT,
    industry        TEXT,
    stage           TEXT,
    primary_goal    TEXT,
    usp             TEXT,

    -- Searchable summary (plain text for embedding + display)
    summary         TEXT NOT NULL,

    -- Skill output snapshots (truncated để tiết kiệm storage)
    market_research     TEXT,
    competitor          TEXT,
    customer_insight    TEXT,
    synthesis           TEXT,
    campaign_brief      TEXT,

    -- Vector embedding — text-embedding-3-small = 1536 dims
    embedding       vector(1536),

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Index per user (recency fallback)
CREATE INDEX IF NOT EXISTS idx_campaign_history_user
    ON user_campaign_history(user_id);

-- 4. HNSW index — fast Approximate Nearest Neighbor search
--    m=16, ef_construction=64 là default tốt cho < 1M rows
CREATE INDEX IF NOT EXISTS idx_campaign_history_embedding
    ON user_campaign_history
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 5. RPC function cho semantic search (dùng từ Python client)
CREATE OR REPLACE FUNCTION match_campaign_history(
    query_embedding vector(1536),
    match_user_id   bigint,
    match_count     int DEFAULT 3
)
RETURNS TABLE (
    id              uuid,
    business_name   text,
    industry        text,
    primary_goal    text,
    summary         text,
    created_at      timestamptz,
    similarity      float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        h.id,
        h.business_name,
        h.industry,
        h.primary_goal,
        h.summary,
        h.created_at,
        1 - (h.embedding <=> query_embedding) AS similarity
    FROM user_campaign_history h
    WHERE h.user_id = match_user_id
      AND h.embedding IS NOT NULL
    ORDER BY h.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
