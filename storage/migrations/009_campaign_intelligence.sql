-- Migration 009: campaign_intelligence — học ngầm để bồi đắp KPI library
-- Run in Supabase SQL Editor
--
-- Mục đích: ghi lại ngành nào / tệp khách hàng nào thì user CẦN và KHÔNG CẦN
-- những thông tin gì trong campaign brief. Chạy ngầm, KHÔNG thông báo cho user.
-- Dùng để phân tích sau → note thêm field vào KPI library (frameworks/kpi_library.py).

CREATE TABLE IF NOT EXISTS campaign_intelligence (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    industry        TEXT,                 -- ngành (khớp KPI library key)
    target_customer TEXT,                 -- tệp khách hàng
    campaign_goal   TEXT,                 -- mục tiêu campaign
    stage           TEXT,                 -- giai đoạn business
    event_type      TEXT NOT NULL,        -- 'brief_approved' | 'brief_edited'
    fields_added    TEXT[] DEFAULT '{}',  -- field user yêu cầu THÊM
    fields_removed  TEXT[] DEFAULT '{}',  -- field user yêu cầu BỎ
    edit_comment    TEXT,                 -- comment thô của user (nếu edit)
    brief_excerpt   TEXT,                 -- 500 ký tự đầu brief để đối chiếu
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campintel_industry ON campaign_intelligence(industry);
CREATE INDEX IF NOT EXISTS idx_campintel_event    ON campaign_intelligence(event_type);
CREATE INDEX IF NOT EXISTS idx_campintel_created  ON campaign_intelligence(created_at DESC);
