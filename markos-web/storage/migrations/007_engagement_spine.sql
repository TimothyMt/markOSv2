-- Migration 007: Engagement Spine (v0.1 redesign — Phase 1)
-- ===========================================================
-- Thêm trục xương sống Discovery → Strategy → Execution.
--
-- 3 entity mới sống PARALLEL với schema 006:
--   engagements        — 1 lần chạy tư vấn (trục liên kết)
--   diagnostic_briefs  — output McKinsey Discovery (facts/hypotheses/gaps)
--   strategies         — output CMO (positioning/wedge/roadmap/KPI)
--
-- skill_runs (006) trở thành Deliverable — gắn thêm strategy_id để
-- mọi execution trace ngược về Strategy đã sinh ra nó.
--
-- Strangler Fig: không xoá gì, additive only. Bật qua DB_V2_WRITE.
-- ===========================================================

-- ════════════════════════════════════════════════════════════
-- 1. ENGAGEMENTS — trục xương sống (1 lần chạy tư vấn)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS engagements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         BIGINT NOT NULL,

    -- Vòng đời: discovery → brief → strategy → execution → complete
    status          TEXT NOT NULL DEFAULT 'discovery',
    title           TEXT,                              -- nhãn tự sinh, vd "Spa laser — 05/2026"

    -- Snapshot 6-7 trường McKinsey hỏi user (irreducible intake)
    discovery_input JSONB DEFAULT '{}'::jsonb,

    -- Con trỏ tới artifact mới nhất (denormalized cho shortcut nhanh)
    brief_id        UUID,
    strategy_id     UUID,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_engagements_user_status
    ON engagements(user_id, status, created_at DESC);
-- Hybrid shortcut: tìm engagement có strategy gần nhất của user
CREATE INDEX IF NOT EXISTS idx_engagements_has_strategy
    ON engagements(user_id, created_at DESC) WHERE strategy_id IS NOT NULL;


-- ════════════════════════════════════════════════════════════
-- 2. DIAGNOSTIC_BRIEFS — output McKinsey Discovery
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS diagnostic_briefs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id   UUID NOT NULL,
    user_id         BIGINT NOT NULL,

    -- Cấu trúc McKinsey (object, không phải văn xuôi)
    facts           JSONB DEFAULT '[]'::jsonb,   -- [{claim, source, confidence}]
    hypotheses      JSONB DEFAULT '[]'::jsonb,   -- [{statement, rank, rationale}]
    gaps            JSONB DEFAULT '[]'::jsonb,   -- [{question, why}] — hỏi lại founder 1 lần
    sources         JSONB DEFAULT '[]'::jsonb,   -- [{name, url}]

    -- Provenance — minh bạch nguồn dữ liệu
    grounded        BOOLEAN DEFAULT FALSE,       -- TRUE nếu dùng grounded web search
    confidence_note TEXT,                         -- caveat khi fallback Claude knowledge
    model_used      TEXT,
    tokens_used     INT,

    -- Full prose render (cho HTML report)
    content         TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (engagement_id) REFERENCES engagements(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)       REFERENCES users(user_id)  ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_briefs_engagement
    ON diagnostic_briefs(engagement_id, created_at DESC);


-- ════════════════════════════════════════════════════════════
-- 3. STRATEGIES — output CMO (Marketing Plan)
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS strategies (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id     UUID NOT NULL,
    user_id           BIGINT NOT NULL,
    brief_id          UUID,
    version           INT NOT NULL DEFAULT 1,

    -- Xương sống CMO plan (SAVE + wedge + SMART roadmap)
    positioning       JSONB DEFAULT '{}'::jsonb,   -- SAVE: {solution, access, value, education}
    wedge             JSONB DEFAULT '{}'::jsonb,   -- {channels[], audience, not_doing[]}
    roadmap_90d       JSONB DEFAULT '[]'::jsonb,   -- [{phase, smart_goals[], milestone}]
    budget_allocation JSONB DEFAULT '{}'::jsonb,
    content_pillars   JSONB DEFAULT '[]'::jsonb,
    kpi_dashboard     JSONB DEFAULT '[]'::jsonb,   -- 3-5 con số chứng minh/bác bỏ
    kill_criteria     JSONB DEFAULT '[]'::jsonb,   -- điều kiện pivot (falsifiable)

    -- Full prose render
    content           TEXT,

    model_used        TEXT,
    tokens_used       INT,
    rating            SMALLINT,
    feedback_text     TEXT,

    created_at        TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (engagement_id) REFERENCES engagements(id)        ON DELETE CASCADE,
    FOREIGN KEY (user_id)       REFERENCES users(user_id)         ON DELETE CASCADE,
    FOREIGN KEY (brief_id)      REFERENCES diagnostic_briefs(id)  ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_strategies_engagement
    ON strategies(engagement_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_strategies_user_recent
    ON strategies(user_id, created_at DESC);


-- ════════════════════════════════════════════════════════════
-- 4. LINK skill_runs → strategy (Execution là con của Strategy)
-- ════════════════════════════════════════════════════════════
-- Mọi deliverable (campaign/content/ads) trace ngược về Strategy.
ALTER TABLE skill_runs
    ADD COLUMN IF NOT EXISTS strategy_id   UUID,
    ADD COLUMN IF NOT EXISTS engagement_id UUID;

CREATE INDEX IF NOT EXISTS idx_skill_runs_strategy
    ON skill_runs(strategy_id) WHERE strategy_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_skill_runs_engagement
    ON skill_runs(engagement_id) WHERE engagement_id IS NOT NULL;


-- ════════════════════════════════════════════════════════════
-- 5. FK bổ sung: engagements.brief_id / strategy_id
-- ════════════════════════════════════════════════════════════
-- Thêm SAU khi các bảng tồn tại (tránh circular dependency lúc CREATE).
-- ON DELETE SET NULL: xoá artifact không làm hỏng engagement.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_engagements_brief'
    ) THEN
        ALTER TABLE engagements
            ADD CONSTRAINT fk_engagements_brief
            FOREIGN KEY (brief_id) REFERENCES diagnostic_briefs(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_engagements_strategy'
    ) THEN
        ALTER TABLE engagements
            ADD CONSTRAINT fk_engagements_strategy
            FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE SET NULL;
    END IF;
END $$;


-- ════════════════════════════════════════════════════════════
-- 6. TRIGGERS — auto updated_at (reuse touch_updated_at từ 006)
-- ════════════════════════════════════════════════════════════
DROP TRIGGER IF EXISTS trg_engagements_touch ON engagements;
CREATE TRIGGER trg_engagements_touch BEFORE UPDATE ON engagements
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();


-- Verify schema
COMMENT ON TABLE engagements       IS 'Trục xương sống — 1 lần chạy Discovery→Strategy→Execution.';
COMMENT ON TABLE diagnostic_briefs IS 'Output McKinsey Discovery — facts/hypotheses/gaps có nguồn.';
COMMENT ON TABLE strategies        IS 'Output CMO — positioning/wedge/roadmap/KPI. Execution trace về đây.';
