-- Web dashboard tables (Supabase). Chạy trong SQL Editor của Supabase.
-- Backend tự seed dữ liệu mẫu nếu bảng rỗng.

create table if not exists web_tracked (
  id bigint generated always as identity primary key,
  name text, ads int default 0, status text, last text);

create table if not exists web_jobs (
  name text primary key, when_text text, status text);

create table if not exists web_optimizations (
  id bigint generated always as identity primary key,
  action text, text text, why text);

create table if not exists web_alerts (
  id bigint generated always as identity primary key,
  sev text, icon text, title text, meta text);

create table if not exists web_settings (
  key text primary key, value int);

create table if not exists web_campaigns (
  id bigint generated always as identity primary key,
  name text, status text, budget text, objective text);

create table if not exists web_calendar_posts (
  id bigint generated always as identity primary key,
  day int, pillar text, title text);

create table if not exists web_content_items (
  id bigint generated always as identity primary key,
  idx int, hook text, format text, status text);

create table if not exists web_reports (
  id bigint generated always as identity primary key,
  name text, type text, date text);

create table if not exists web_accounts (
  id bigint generated always as identity primary key,
  name text, acc_id text, status text, spend text);

create table if not exists web_users (
  id bigint generated always as identity primary key,
  uid text, plan text, quota int, used int);

-- Dùng service_role key (server-side) → bỏ qua RLS. Nếu bật RLS, thêm policy phù hợp.

-- ── Realtime (Bước 2): đẩy thay đổi DB tức thì xuống web qua SSE ──
-- Thêm các bảng vào publication realtime của Supabase:
alter publication supabase_realtime add table
  web_tracked, web_jobs, web_optimizations, web_alerts, web_settings,
  web_campaigns, web_calendar_posts, web_content_items, web_reports,
  web_accounts, web_users;

-- Để payload UPDATE/DELETE đầy đủ (không chỉ INSERT):
alter table web_tracked        replica identity full;
alter table web_jobs           replica identity full;
alter table web_optimizations  replica identity full;
alter table web_alerts         replica identity full;
alter table web_settings       replica identity full;
alter table web_campaigns      replica identity full;
alter table web_calendar_posts replica identity full;
alter table web_content_items  replica identity full;
alter table web_reports        replica identity full;
alter table web_accounts       replica identity full;
alter table web_users          replica identity full;
