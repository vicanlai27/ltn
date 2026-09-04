-- Lavisco News: full schema for Supabase Postgres
-- Generated from the app's SQLAlchemy models. Run this once in
-- Supabase's SQL Editor (Project -> SQL Editor -> New query) to
-- create every table. Safe to re-run: each statement is guarded
-- with IF NOT EXISTS / DO NOTHING where possible.

BEGIN;

CREATE TABLE IF NOT EXISTS advertisements (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	placement VARCHAR(60) NOT NULL, 
	image VARCHAR(255), 
	html_code TEXT, 
	target_url VARCHAR(500), 
	is_active BOOLEAN NOT NULL, 
	start_at TIMESTAMP WITH TIME ZONE, 
	end_at TIMESTAMP WITH TIME ZONE, 
	priority INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS alumni_profiles (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	graduation_year INTEGER, 
	photo VARCHAR(255), 
	"current_role" VARCHAR(160), 
	location VARCHAR(120), 
	story TEXT, 
	is_featured BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS campus_events (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	slug VARCHAR(280) NOT NULL, 
	description TEXT, 
	event_type VARCHAR(60), 
	start_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_at TIMESTAMP WITH TIME ZONE, 
	location VARCHAR(255), 
	image VARCHAR(255), 
	organizer VARCHAR(120), 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS categories (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	description TEXT, 
	image VARCHAR(255), 
	parent_id INTEGER, 
	display_order INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES categories (id)
);

CREATE TABLE IF NOT EXISTS clubs (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	description TEXT, 
	logo VARCHAR(255), 
	cover_image VARCHAR(255), 
	meeting_information TEXT, 
	leader_name VARCHAR(120), 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS houses (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	description TEXT, 
	logo VARCHAR(255), 
	color VARCHAR(16), 
	house_points INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS podcast_episodes (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	slug VARCHAR(280) NOT NULL, 
	description TEXT, 
	cover_image VARCHAR(255), 
	audio_url VARCHAR(500) NOT NULL, 
	duration INTEGER, 
	episode_number INTEGER, 
	published_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS reports (
	id SERIAL NOT NULL, 
	target_type VARCHAR(32) NOT NULL, 
	target_id INTEGER NOT NULL, 
	reason TEXT NOT NULL, 
	session_hash VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS site_settings (
	id SERIAL NOT NULL, 
	key VARCHAR(120) NOT NULL, 
	value TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS sports (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	description TEXT, 
	icon VARCHAR(255), 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS staff_profiles (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	photo VARCHAR(255), 
	role VARCHAR(120), 
	department VARCHAR(120), 
	bio TEXT, 
	social_links JSON, 
	is_featured BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tags (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS themes (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	description TEXT, 
	theme_type VARCHAR(32) NOT NULL, 
	start_date TIMESTAMP WITH TIME ZONE, 
	end_date TIMESTAMP WITH TIME ZONE, 
	primary_color VARCHAR(16), 
	secondary_color VARCHAR(16), 
	accent_color VARCHAR(16), 
	background_color VARCHAR(16), 
	text_color VARCHAR(16), 
	header_logo VARCHAR(255), 
	banner_image VARCHAR(255), 
	background_image VARCHAR(255), 
	decoration_config JSON, 
	animation_config JSON, 
	sound_enabled BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	priority INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS users (
	id SERIAL NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	account_status VARCHAR(32) NOT NULL, 
	created_by_id INTEGER, 
	verified_by_id INTEGER, 
	verified_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	avatar VARCHAR(255), 
	totp_secret VARCHAR(64), 
	totp_enabled BOOLEAN NOT NULL, 
	totp_backup_codes_hash TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id), 
	FOREIGN KEY(verified_by_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS activity_logs (
	id SERIAL NOT NULL, 
	actor_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	target_type VARCHAR(60), 
	target_id INTEGER, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS author_profiles (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	display_name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	bio TEXT, 
	avatar VARCHAR(255), 
	cover_image VARCHAR(255), 
	school_role VARCHAR(120), 
	house_id INTEGER, 
	social_links JSON, 
	is_verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(house_id) REFERENCES houses (id)
);

CREATE TABLE IF NOT EXISTS galleries (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	slug VARCHAR(280) NOT NULL, 
	description TEXT, 
	cover_image VARCHAR(255), 
	event_id INTEGER, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(event_id) REFERENCES campus_events (id)
);

CREATE TABLE IF NOT EXISTS house_scores (
	id SERIAL NOT NULL, 
	house_id INTEGER NOT NULL, 
	points INTEGER NOT NULL, 
	reason VARCHAR(255) NOT NULL, 
	category VARCHAR(80), 
	source_type VARCHAR(32) NOT NULL, 
	source_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(house_id) REFERENCES houses (id)
);

CREATE TABLE IF NOT EXISTS notification_subscriptions (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	endpoint VARCHAR(500) NOT NULL, 
	subscription_data JSON NOT NULL, 
	preferences JSON, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS notifications (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	message TEXT, 
	link_url VARCHAR(500), 
	read_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS site_announcements (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	display_type VARCHAR(32) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	target_scope VARCHAR(32) NOT NULL, 
	cta_text VARCHAR(80), 
	cta_url VARCHAR(500), 
	dismissible BOOLEAN NOT NULL, 
	priority INTEGER NOT NULL, 
	start_at TIMESTAMP WITH TIME ZONE, 
	end_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	created_by INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS special_editions (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	slug VARCHAR(280) NOT NULL, 
	description TEXT, 
	cover_image VARCHAR(255), 
	theme_id INTEGER, 
	start_at TIMESTAMP WITH TIME ZONE, 
	end_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(theme_id) REFERENCES themes (id)
);

CREATE TABLE IF NOT EXISTS student_profiles (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	photo VARCHAR(255), 
	class_or_level VARCHAR(60), 
	house_id INTEGER, 
	achievements TEXT, 
	bio TEXT, 
	is_featured BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(house_id) REFERENCES houses (id)
);

CREATE TABLE IF NOT EXISTS teams (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	sport_id INTEGER NOT NULL, 
	logo VARCHAR(255), 
	season VARCHAR(40), 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sport_id) REFERENCES sports (id)
);

CREATE TABLE IF NOT EXISTS user_preferences (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	preferred_categories JSON, 
	preferred_campus_sections JSON, 
	dark_mode VARCHAR(16), 
	notification_preferences JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS videos (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	slug VARCHAR(280) NOT NULL, 
	description TEXT, 
	thumbnail VARCHAR(255), 
	video_url VARCHAR(500) NOT NULL, 
	duration INTEGER, 
	category_id INTEGER, 
	author_id INTEGER, 
	published_at TIMESTAMP WITH TIME ZONE, 
	view_count INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id), 
	FOREIGN KEY(author_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS articles (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	slug VARCHAR(280) NOT NULL, 
	excerpt TEXT, 
	body TEXT NOT NULL, 
	featured_image VARCHAR(255), 
	featured_image_alt VARCHAR(255), 
	image_caption VARCHAR(255), 
	youtube_video_id VARCHAR(11), 
	special_edition_id INTEGER, 
	category_id INTEGER, 
	author_id INTEGER, 
	content_type VARCHAR(40) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	is_featured BOOLEAN NOT NULL, 
	is_breaking BOOLEAN NOT NULL, 
	is_trending BOOLEAN NOT NULL, 
	is_editors_pick BOOLEAN NOT NULL, 
	is_campus BOOLEAN NOT NULL, 
	campus_section VARCHAR(60), 
	house_id INTEGER, 
	club_id INTEGER, 
	audio_url VARCHAR(255), 
	audio_duration INTEGER, 
	view_count INTEGER NOT NULL, 
	share_count INTEGER NOT NULL, 
	reaction_count INTEGER NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	is_audited BOOLEAN NOT NULL, 
	audited_by_id INTEGER, 
	audited_at TIMESTAMP WITH TIME ZONE, 
	audit_notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(special_edition_id) REFERENCES special_editions (id) ON DELETE SET NULL, 
	FOREIGN KEY(category_id) REFERENCES categories (id), 
	FOREIGN KEY(author_id) REFERENCES users (id), 
	FOREIGN KEY(house_id) REFERENCES houses (id), 
	FOREIGN KEY(club_id) REFERENCES clubs (id), 
	FOREIGN KEY(audited_by_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS consent_records (
	id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	media_reference_type VARCHAR(40) NOT NULL, 
	media_reference_id INTEGER NOT NULL, 
	consent_given_by VARCHAR(120) NOT NULL, 
	consent_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES student_profiles (id)
);

CREATE TABLE IF NOT EXISTS fixtures (
	id SERIAL NOT NULL, 
	home_team_id INTEGER NOT NULL, 
	away_team_id INTEGER NOT NULL, 
	competition VARCHAR(120), 
	venue VARCHAR(120), 
	match_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	home_score INTEGER, 
	away_score INTEGER, 
	notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(home_team_id) REFERENCES teams (id), 
	FOREIGN KEY(away_team_id) REFERENCES teams (id)
);

CREATE TABLE IF NOT EXISTS gallery_images (
	id SERIAL NOT NULL, 
	gallery_id INTEGER NOT NULL, 
	image VARCHAR(255) NOT NULL, 
	alt_text VARCHAR(255), 
	caption VARCHAR(255), 
	display_order INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(gallery_id) REFERENCES galleries (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS article_images (
	id SERIAL NOT NULL, 
	article_id INTEGER NOT NULL, 
	image VARCHAR(255) NOT NULL, 
	alt_text VARCHAR(255), 
	caption VARCHAR(255), 
	display_order INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS comments (
	id SERIAL NOT NULL, 
	article_id INTEGER NOT NULL, 
	user_id INTEGER, 
	session_hash VARCHAR(64) NOT NULL, 
	display_name VARCHAR(80) NOT NULL, 
	body TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS placement_slots (
	id SERIAL NOT NULL, 
	zone VARCHAR(40) NOT NULL, 
	article_id INTEGER NOT NULL, 
	position INTEGER NOT NULL, 
	is_manual_override BOOLEAN NOT NULL, 
	start_at TIMESTAMP WITH TIME ZONE, 
	end_at TIMESTAMP WITH TIME ZONE, 
	set_by_user_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(set_by_user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS polls (
	id SERIAL NOT NULL, 
	question VARCHAR(255) NOT NULL, 
	description TEXT, 
	status VARCHAR(32) NOT NULL, 
	start_at TIMESTAMP WITH TIME ZONE, 
	end_at TIMESTAMP WITH TIME ZONE, 
	allow_multiple BOOLEAN NOT NULL, 
	show_results BOOLEAN NOT NULL, 
	article_id INTEGER, 
	campus_event_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_poll_mutually_exclusive_target CHECK (NOT (article_id IS NOT NULL AND campus_event_id IS NOT NULL)), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(campus_event_id) REFERENCES campus_events (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reactions (
	id SERIAL NOT NULL, 
	article_id INTEGER NOT NULL, 
	user_id INTEGER, 
	session_hash VARCHAR(64) NOT NULL, 
	reaction_type VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS share_events (
	id SERIAL NOT NULL, 
	article_id INTEGER NOT NULL, 
	platform VARCHAR(32) NOT NULL, 
	user_id INTEGER, 
	session_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS tag_relations (
	id SERIAL NOT NULL, 
	article_id INTEGER NOT NULL, 
	tag_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tag_relations_article_tag UNIQUE (article_id, tag_id), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS view_events (
	id SERIAL NOT NULL, 
	article_id INTEGER NOT NULL, 
	session_hash VARCHAR(64) NOT NULL, 
	user_id INTEGER, 
	referrer VARCHAR(500), 
	device_type VARCHAR(32), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS comment_reactions (
	id SERIAL NOT NULL, 
	comment_id INTEGER NOT NULL, 
	user_id INTEGER, 
	session_hash VARCHAR(64) NOT NULL, 
	reaction_type VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(comment_id) REFERENCES comments (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS poll_options (
	id SERIAL NOT NULL, 
	poll_id INTEGER NOT NULL, 
	label VARCHAR(200) NOT NULL, 
	display_order INTEGER NOT NULL, 
	vote_count INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(poll_id) REFERENCES polls (id) ON DELETE CASCADE
);

-- Indexes (created separately, after all tables exist)

CREATE INDEX IF NOT EXISTS ix_advertisements_is_active ON advertisements (is_active);
CREATE INDEX IF NOT EXISTS ix_advertisements_placement ON advertisements (placement);
CREATE UNIQUE INDEX IF NOT EXISTS ix_alumni_profiles_slug ON alumni_profiles (slug);
CREATE INDEX IF NOT EXISTS ix_alumni_profiles_graduation_year ON alumni_profiles (graduation_year);
CREATE INDEX IF NOT EXISTS ix_alumni_profiles_is_featured ON alumni_profiles (is_featured);
CREATE UNIQUE INDEX IF NOT EXISTS ix_campus_events_slug ON campus_events (slug);
CREATE INDEX IF NOT EXISTS ix_campus_events_status ON campus_events (status);
CREATE INDEX IF NOT EXISTS ix_campus_events_event_type ON campus_events (event_type);
CREATE INDEX IF NOT EXISTS ix_campus_events_start_at ON campus_events (start_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_categories_slug ON categories (slug);
CREATE UNIQUE INDEX IF NOT EXISTS ix_clubs_slug ON clubs (slug);
CREATE UNIQUE INDEX IF NOT EXISTS ix_houses_slug ON houses (slug);
CREATE INDEX IF NOT EXISTS ix_podcast_episodes_published_at ON podcast_episodes (published_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_podcast_episodes_slug ON podcast_episodes (slug);
CREATE INDEX IF NOT EXISTS ix_reports_target_type ON reports (target_type);
CREATE INDEX IF NOT EXISTS ix_reports_target_id ON reports (target_id);
CREATE INDEX IF NOT EXISTS ix_reports_status ON reports (status);
CREATE INDEX IF NOT EXISTS ix_reports_session_hash ON reports (session_hash);
CREATE UNIQUE INDEX IF NOT EXISTS ix_site_settings_key ON site_settings (key);
CREATE UNIQUE INDEX IF NOT EXISTS ix_sports_slug ON sports (slug);
CREATE UNIQUE INDEX IF NOT EXISTS ix_staff_profiles_slug ON staff_profiles (slug);
CREATE INDEX IF NOT EXISTS ix_staff_profiles_is_featured ON staff_profiles (is_featured);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tags_slug ON tags (slug);
CREATE INDEX IF NOT EXISTS ix_themes_priority ON themes (priority);
CREATE INDEX IF NOT EXISTS ix_themes_theme_type ON themes (theme_type);
CREATE UNIQUE INDEX IF NOT EXISTS ix_themes_slug ON themes (slug);
CREATE INDEX IF NOT EXISTS ix_themes_is_active ON themes (is_active);
CREATE INDEX IF NOT EXISTS ix_users_status_role ON users (account_status, role);
CREATE INDEX IF NOT EXISTS ix_users_account_status ON users (account_status);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
CREATE INDEX IF NOT EXISTS ix_activity_logs_action ON activity_logs (action);
CREATE INDEX IF NOT EXISTS ix_activity_logs_created_at ON activity_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_activity_logs_target_type ON activity_logs (target_type);
CREATE INDEX IF NOT EXISTS ix_activity_logs_actor_id ON activity_logs (actor_id);
CREATE INDEX IF NOT EXISTS ix_activity_logs_target_id ON activity_logs (target_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_author_profiles_user_id ON author_profiles (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_author_profiles_slug ON author_profiles (slug);
CREATE INDEX IF NOT EXISTS ix_galleries_event_id ON galleries (event_id);
CREATE INDEX IF NOT EXISTS ix_galleries_published_at ON galleries (published_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_galleries_slug ON galleries (slug);
CREATE INDEX IF NOT EXISTS ix_house_scores_house_id ON house_scores (house_id);
CREATE INDEX IF NOT EXISTS ix_house_scores_source ON house_scores (source_type, source_id);
CREATE INDEX IF NOT EXISTS ix_notification_subscriptions_user_id ON notification_subscriptions (user_id);
CREATE INDEX IF NOT EXISTS ix_notifications_kind ON notifications (kind);
CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);
CREATE INDEX IF NOT EXISTS ix_notifications_read_at ON notifications (read_at);
CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at);
CREATE INDEX IF NOT EXISTS ix_site_announcements_severity ON site_announcements (severity);
CREATE INDEX IF NOT EXISTS ix_site_announcements_is_active ON site_announcements (is_active);
CREATE INDEX IF NOT EXISTS ix_announcements_scope_severity ON site_announcements (target_scope, severity, is_active);
CREATE INDEX IF NOT EXISTS ix_site_announcements_target_scope ON site_announcements (target_scope);
CREATE UNIQUE INDEX IF NOT EXISTS ix_special_editions_slug ON special_editions (slug);
CREATE INDEX IF NOT EXISTS ix_special_editions_is_active ON special_editions (is_active);
CREATE INDEX IF NOT EXISTS ix_student_profiles_house_id ON student_profiles (house_id);
CREATE INDEX IF NOT EXISTS ix_student_profiles_is_featured ON student_profiles (is_featured);
CREATE UNIQUE INDEX IF NOT EXISTS ix_student_profiles_slug ON student_profiles (slug);
CREATE INDEX IF NOT EXISTS ix_teams_sport_id ON teams (sport_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_preferences_user_id ON user_preferences (user_id);
CREATE INDEX IF NOT EXISTS ix_videos_published_at ON videos (published_at);
CREATE INDEX IF NOT EXISTS ix_videos_category_id ON videos (category_id);
CREATE INDEX IF NOT EXISTS ix_videos_author_id ON videos (author_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_videos_slug ON videos (slug);
CREATE INDEX IF NOT EXISTS ix_articles_is_trending ON articles (is_trending);
CREATE INDEX IF NOT EXISTS ix_articles_is_audited ON articles (is_audited);
CREATE UNIQUE INDEX IF NOT EXISTS ix_articles_slug ON articles (slug);
CREATE INDEX IF NOT EXISTS ix_articles_special_edition_id ON articles (special_edition_id);
CREATE INDEX IF NOT EXISTS ix_articles_status ON articles (status);
CREATE INDEX IF NOT EXISTS ix_articles_is_editors_pick ON articles (is_editors_pick);
CREATE INDEX IF NOT EXISTS ix_articles_author_id ON articles (author_id);
CREATE INDEX IF NOT EXISTS ix_articles_campus_section ON articles (is_campus, campus_section, status);
CREATE INDEX IF NOT EXISTS ix_articles_is_featured ON articles (is_featured);
CREATE INDEX IF NOT EXISTS ix_articles_published_at ON articles (published_at);
CREATE INDEX IF NOT EXISTS ix_articles_public ON articles (status, is_audited, published_at);
CREATE INDEX IF NOT EXISTS ix_articles_breaking_queue ON articles (is_breaking, status, created_at);
CREATE INDEX IF NOT EXISTS ix_articles_is_campus ON articles (is_campus);
CREATE INDEX IF NOT EXISTS ix_articles_created_at ON articles (created_at);
CREATE INDEX IF NOT EXISTS ix_articles_is_breaking ON articles (is_breaking);
CREATE INDEX IF NOT EXISTS ix_articles_category_id ON articles (category_id);
CREATE INDEX IF NOT EXISTS ix_articles_content_type ON articles (content_type);
CREATE INDEX IF NOT EXISTS ix_consent_records_student_id ON consent_records (student_id);
CREATE INDEX IF NOT EXISTS ix_consent_records_media_reference_type ON consent_records (media_reference_type);
CREATE INDEX IF NOT EXISTS ix_consent_records_media_reference_id ON consent_records (media_reference_id);
CREATE INDEX IF NOT EXISTS ix_consent_media ON consent_records (media_reference_type, media_reference_id);
CREATE INDEX IF NOT EXISTS ix_fixtures_away_team_id ON fixtures (away_team_id);
CREATE INDEX IF NOT EXISTS ix_fixtures_status ON fixtures (status);
CREATE INDEX IF NOT EXISTS ix_fixtures_home_team_id ON fixtures (home_team_id);
CREATE INDEX IF NOT EXISTS ix_fixtures_match_date ON fixtures (match_date);
CREATE INDEX IF NOT EXISTS ix_gallery_images_gallery_id ON gallery_images (gallery_id);
CREATE INDEX IF NOT EXISTS ix_article_images_article_id ON article_images (article_id);
CREATE INDEX IF NOT EXISTS ix_comments_created_at ON comments (created_at);
CREATE INDEX IF NOT EXISTS ix_comments_session_hash ON comments (session_hash);
CREATE INDEX IF NOT EXISTS ix_comments_user_id ON comments (user_id);
CREATE INDEX IF NOT EXISTS ix_comments_article_id ON comments (article_id);
CREATE INDEX IF NOT EXISTS ix_placement_slots_end_at ON placement_slots (end_at);
CREATE INDEX IF NOT EXISTS ix_placement_slots_article_id ON placement_slots (article_id);
CREATE INDEX IF NOT EXISTS ix_placement_slots_zone ON placement_slots (zone);
CREATE INDEX IF NOT EXISTS ix_polls_status ON polls (status);
CREATE INDEX IF NOT EXISTS ix_polls_article_id ON polls (article_id);
CREATE INDEX IF NOT EXISTS ix_polls_campus_event_id ON polls (campus_event_id);
CREATE INDEX IF NOT EXISTS ix_reactions_session_hash ON reactions (session_hash);
CREATE INDEX IF NOT EXISTS ix_reactions_dedup ON reactions (article_id, session_hash, user_id);
CREATE INDEX IF NOT EXISTS ix_reactions_user_id ON reactions (user_id);
CREATE INDEX IF NOT EXISTS ix_reactions_article_id ON reactions (article_id);
CREATE INDEX IF NOT EXISTS ix_share_events_article_id ON share_events (article_id);
CREATE INDEX IF NOT EXISTS ix_share_events_platform ON share_events (platform);
CREATE INDEX IF NOT EXISTS ix_share_events_session_hash ON share_events (session_hash);
CREATE INDEX IF NOT EXISTS ix_tag_relations_tag_id ON tag_relations (tag_id);
CREATE INDEX IF NOT EXISTS ix_tag_relations_article_id ON tag_relations (article_id);
CREATE INDEX IF NOT EXISTS ix_view_events_created_at ON view_events (created_at);
CREATE INDEX IF NOT EXISTS ix_view_events_article_id ON view_events (article_id);
CREATE INDEX IF NOT EXISTS ix_view_events_dedup ON view_events (article_id, session_hash, created_at);
CREATE INDEX IF NOT EXISTS ix_view_events_session_hash ON view_events (session_hash);
CREATE INDEX IF NOT EXISTS ix_comment_reactions_comment_id ON comment_reactions (comment_id);
CREATE INDEX IF NOT EXISTS ix_comment_reactions_session_hash ON comment_reactions (session_hash);
CREATE INDEX IF NOT EXISTS ix_comment_reactions_dedup ON comment_reactions (comment_id, session_hash, user_id);
CREATE INDEX IF NOT EXISTS ix_comment_reactions_user_id ON comment_reactions (user_id);
CREATE INDEX IF NOT EXISTS ix_poll_options_poll_id ON poll_options (poll_id);

COMMIT;