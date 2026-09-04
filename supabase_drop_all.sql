-- Lavisco News: drop all app tables from Supabase
-- Run in Supabase's SQL Editor. CASCADE also drops any
-- foreign-key-dependent objects, so order doesn't matter,
-- but tables are still listed child-first for clarity.
-- This only touches the 'public' schema -- Supabase's own
-- auth/storage/realtime tables live in separate schemas
-- and are untouched.

BEGIN;

DROP TABLE IF EXISTS poll_options CASCADE;
DROP TABLE IF EXISTS comment_reactions CASCADE;
DROP TABLE IF EXISTS view_events CASCADE;
DROP TABLE IF EXISTS tag_relations CASCADE;
DROP TABLE IF EXISTS share_events CASCADE;
DROP TABLE IF EXISTS reactions CASCADE;
DROP TABLE IF EXISTS polls CASCADE;
DROP TABLE IF EXISTS placement_slots CASCADE;
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS article_images CASCADE;
DROP TABLE IF EXISTS gallery_images CASCADE;
DROP TABLE IF EXISTS fixtures CASCADE;
DROP TABLE IF EXISTS consent_records CASCADE;
DROP TABLE IF EXISTS articles CASCADE;
DROP TABLE IF EXISTS videos CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
DROP TABLE IF EXISTS student_profiles CASCADE;
DROP TABLE IF EXISTS special_editions CASCADE;
DROP TABLE IF EXISTS site_announcements CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS notification_subscriptions CASCADE;
DROP TABLE IF EXISTS house_scores CASCADE;
DROP TABLE IF EXISTS galleries CASCADE;
DROP TABLE IF EXISTS author_profiles CASCADE;
DROP TABLE IF EXISTS activity_logs CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS themes CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS staff_profiles CASCADE;
DROP TABLE IF EXISTS sports CASCADE;
DROP TABLE IF EXISTS site_settings CASCADE;
DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS podcast_episodes CASCADE;
DROP TABLE IF EXISTS houses CASCADE;
DROP TABLE IF EXISTS clubs CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS campus_events CASCADE;
DROP TABLE IF EXISTS alumni_profiles CASCADE;
DROP TABLE IF EXISTS advertisements CASCADE;

-- Also drop Alembic's migration-tracking table, if you ever
-- ran `flask db upgrade` against this database (harmless if
-- it doesn't exist -- IF EXISTS handles that).
DROP TABLE IF EXISTS alembic_version CASCADE;

COMMIT;