-- Migration 011: Lưu danh sách tất cả Ad Accounts của user (để switch không cần re-OAuth)
ALTER TABLE user_fb_connections
ADD COLUMN IF NOT EXISTS available_accounts JSONB DEFAULT '[]'::jsonb;
