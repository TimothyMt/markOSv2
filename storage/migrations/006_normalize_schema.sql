-- Migration 006: Full Schema Normalization (Phase 1)
-- ===========================================================
-- Build new normalized tables PARALLEL với schema cũ.
-- Old sessions table TIẾP TỤC HOẠT ĐỘNG bình thường.
-- Backfill script chạy riêng để populate new tables từ sessions.results.
--
-- Strangler Fig pattern: new tables sống cùng old, không xoá gì.
-- Sau khi verify data integrity → flip feature flag để dùng new schema.
-- ===========================================================

-- ════════════════════════════════════════════════════════════
-- 1. USERS — top-level identity (soft delete)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    user_id         BIGINT PRIMARY KEY,         -- Telegram user ID
    name            TEXT,                        -- preferences.user_name
    en_level        TEXT DEFAULT 'moderate',    -- 'none' | 'moderate' | 'fluent'

    -- Token quota system
    token_quota     INT DEFAULT 500000,
    token_used      INT DEFAULT 0,
    plan            TEXT DEFAULT 'free',         -- 'free' | 'pro' | 'admin'

    -- Cached industry để admin query nhanh
    industry_cached TEXT,
    last_active_at  TIMESTAMPTZ DEFAULT NOW(),

    -- Soft delete (không hard delete top-level)
    deleted_at      TIMESTAMPTZ,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_active
    ON users(last_active_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_industry
    ON users(industry_cached) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_quota_warning
    ON users(user_id) WHERE token_used > token_quota * 0.8 AND deleted_at IS NULL;


-- ════════════════════════════════════════════════════════════
-- 2. USER_BUSINESS_PROFILE — queryable profile (1:1 với users)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_business_profile (
    user_id                   BIGINT PRIMARY KEY,

    -- Core business
    business_name             TEXT,
    industry                  TEXT,
    stage                     TEXT,                -- idea/mvp/growth/scale
    product_service           TEXT,
    target_customer           TEXT,
    monthly_revenue           TEXT,
    team_size                 TEXT,
    monthly_marketing_budget  TEXT,
    primary_goal              TEXT,
    current_channels          TEXT,
    main_challenge            TEXT,
    competitors               TEXT,
    location                  TEXT,

    -- USP layer (Sprint 2)
    usp                       TEXT,
    usp_confidence            TEXT,                -- clear/draft/missing

    updated_at                TIMESTAMPTZ DEFAULT NOW(),

    -- FK: profile xoá theo user (RESTRICT để tránh xoá nhầm)
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_profile_industry
    ON user_business_profile(industry);
CREATE INDEX IF NOT EXISTS idx_profile_stage
    ON user_business_profile(stage);


-- ════════════════════════════════════════════════════════════
-- 3. USER_SESSIONS_SLIM — HOT state only (read/write liên tục)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_sessions_slim (
    user_id              BIGINT PRIMARY KEY,

    -- Current pipeline state
    stage                TEXT NOT NULL DEFAULT 'idle',
    selected_task        TEXT,

    -- Transient state (< 5KB)
    pending_intake       JSONB DEFAULT '{}'::jsonb,
    intake_history       JSONB DEFAULT '[]'::jsonb,
    tone_calibration     JSONB DEFAULT '{}'::jsonb,

    -- TTL field — auto reset stage nếu idle quá lâu
    last_message_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_sessions_stale
    ON user_sessions_slim(last_message_at)
    WHERE stage != 'idle';


-- ════════════════════════════════════════════════════════════
-- 4. SKILL_RUNS — immutable history (replace results JSONB)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS skill_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         BIGINT NOT NULL,

    skill_name      TEXT NOT NULL,              -- market_research/competitor/...
    version         INT NOT NULL DEFAULT 1,
    content         TEXT NOT NULL,

    -- Stats
    tokens_used     INT,
    model_used      TEXT,                        -- claude-sonnet-4-6 etc.

    -- Rating + feedback (filled sau khi user rate)
    rating          SMALLINT,                    -- 1-5
    feedback_text   TEXT,

    -- Linkage
    campaign_id     UUID,                        -- nullable, link to campaign
    parent_run_id   UUID,                        -- nullable, for re-runs

    created_at      TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_skill_runs_user_skill
    ON skill_runs(user_id, skill_name, version DESC);
CREATE INDEX IF NOT EXISTS idx_skill_runs_rating
    ON skill_runs(skill_name, rating) WHERE rating IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_skill_runs_recent
    ON skill_runs(created_at DESC);


-- ════════════════════════════════════════════════════════════
-- 5. CAMPAIGNS — proper entity (replace user_campaign_history)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS campaigns (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              BIGINT NOT NULL,

    -- Campaign metadata
    name                 TEXT,                   -- "Tết 2026 Sale"
    status               TEXT DEFAULT 'draft',   -- draft/active/completed/archived

    -- Strategy data
    industry             TEXT,
    primary_goal         TEXT,
    offer_lever          TEXT,                   -- "10% discount" / "free gift" etc.
    start_date           DATE,
    end_date             DATE,

    -- Generated artifacts (FK tới skill_runs)
    brief_skill_run_id   UUID,
    calendar_skill_run_id UUID,

    -- Searchable summary + vector embedding (S8)
    summary              TEXT,
    embedding            vector(1536),

    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (brief_skill_run_id) REFERENCES skill_runs(id) ON DELETE SET NULL,
    FOREIGN KEY (calendar_skill_run_id) REFERENCES skill_runs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_campaigns_user_status
    ON campaigns(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaigns_active
    ON campaigns(user_id) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_campaigns_embedding
    ON campaigns USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);


-- ════════════════════════════════════════════════════════════
-- 6. POSTS — POST-XXX as proper PK (replace content_outputs)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS posts (
    post_id              TEXT PRIMARY KEY,        -- 'POST-001' / 'POST-001-TT'
    user_id              BIGINT NOT NULL,
    campaign_id          UUID,

    -- Metadata
    week                 INT,
    day                  TEXT,                    -- Mon/Tue/...
    channel              TEXT,                    -- facebook/tiktok/zalo/...
    pillar               TEXT,                    -- Educate/Entertain/...
    funnel               TEXT,                    -- TOFU/MOFU/BOFU

    -- Content
    content              TEXT NOT NULL,
    status               TEXT DEFAULT 'draft',    -- draft/approved/posted/deleted

    -- Adaptation tracking
    parent_post_id       TEXT,                    -- nullable, link to original
    adapt_type           TEXT,                    -- 'adapt' / 'variant' / 'edit'

    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_post_id) REFERENCES posts(post_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_user_channel
    ON posts(user_id, channel, status);
CREATE INDEX IF NOT EXISTS idx_posts_campaign
    ON posts(campaign_id, week, day);
CREATE INDEX IF NOT EXISTS idx_posts_parent
    ON posts(parent_post_id) WHERE parent_post_id IS NOT NULL;


-- ════════════════════════════════════════════════════════════
-- 7. TRIGGERS — auto-update timestamps
-- ════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_touch ON users;
CREATE TRIGGER trg_users_touch BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_profile_touch ON user_business_profile;
CREATE TRIGGER trg_profile_touch BEFORE UPDATE ON user_business_profile
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_session_touch ON user_sessions_slim;
CREATE TRIGGER trg_session_touch BEFORE UPDATE ON user_sessions_slim
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_campaigns_touch ON campaigns;
CREATE TRIGGER trg_campaigns_touch BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_posts_touch ON posts;
CREATE TRIGGER trg_posts_touch BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();


-- ════════════════════════════════════════════════════════════
-- 8. AUTO-RESET STALE SESSIONS — Quick Win #1 (root-level)
-- ════════════════════════════════════════════════════════════
-- Sau 24h idle, stage tự reset về 'idle' để khỏi stuck
-- Chạy qua pg_cron extension hoặc Supabase Edge Function scheduled

CREATE OR REPLACE FUNCTION reset_stale_sessions()
RETURNS INT AS $$
DECLARE
    affected_rows INT;
BEGIN
    UPDATE user_sessions_slim
    SET stage = 'idle',
        pending_intake = '{}'::jsonb
    WHERE stage NOT IN ('idle', 'complete')
      AND last_message_at < NOW() - INTERVAL '24 hours';

    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql;

-- Verify schema
COMMENT ON TABLE users IS 'Top-level identity. Soft delete only.';
COMMENT ON TABLE user_business_profile IS 'Queryable business profile, 1:1 with users.';
COMMENT ON TABLE user_sessions_slim IS 'Hot state only — current stage + transient data.';
COMMENT ON TABLE skill_runs IS 'Immutable skill output history. Versioned per skill.';
COMMENT ON TABLE campaigns IS 'Campaign entity with semantic embedding.';
COMMENT ON TABLE posts IS 'POST-XXX as PK. Tracks adapt/variant relationships.';
