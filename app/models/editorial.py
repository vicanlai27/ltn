from app.extensions import db
from app.utils.security import utcnow


class Theme(db.Model):
    __tablename__ = "themes"

    TYPE_CALENDAR = "calendar"
    TYPE_SCHOOL_EVENT = "school_event"
    TYPE_SPECIAL_EDITION = "special_edition"
    TYPE_EDITORIAL = "editorial"
    TYPE_MANUAL = "manual"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    theme_type = db.Column(db.String(32), nullable=False, index=True)

    start_date = db.Column(db.DateTime(timezone=True), nullable=True)
    end_date = db.Column(db.DateTime(timezone=True), nullable=True)

    # Visual tokens (override CSS custom properties)
    primary_color = db.Column(db.String(16), nullable=True)
    secondary_color = db.Column(db.String(16), nullable=True)
    accent_color = db.Column(db.String(16), nullable=True)
    background_color = db.Column(db.String(16), nullable=True)
    text_color = db.Column(db.String(16), nullable=True)

    header_logo = db.Column(db.String(255), nullable=True)
    banner_image = db.Column(db.String(255), nullable=True)
    background_image = db.Column(db.String(255), nullable=True)

    decoration_config = db.Column(db.JSON, nullable=True)  # {"motif": "bells", "density": "low"}
    animation_config = db.Column(db.JSON, nullable=True)    # {"snow": true, "speed": "slow"}

    sound_enabled = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    priority = db.Column(db.Integer, default=0, nullable=False, index=True)  # higher wins
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class SpecialEdition(db.Model):
    __tablename__ = "special_editions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    theme_id = db.Column(db.Integer, db.ForeignKey("themes.id"), nullable=True)
    start_at = db.Column(db.DateTime(timezone=True), nullable=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    theme = db.relationship("Theme", foreign_keys=[theme_id])
    articles = db.relationship("Article", back_populates="special_edition")


class PlacementSlot(db.Model):
    __tablename__ = "placement_slots"

    ZONE_HERO_PRIMARY = "hero_primary"
    ZONE_HERO_SECONDARY = "hero_secondary"
    ZONE_TRENDING = "trending_now"
    ZONE_CAMPUS = "campus_highlights"
    ZONE_EDITORS = "editors_choice"
    ZONE_SPECIAL = "special_edition_banner"

    id = db.Column(db.Integer, primary_key=True)
    zone = db.Column(db.String(40), nullable=False, index=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    position = db.Column(db.Integer, default=0, nullable=False)
    is_manual_override = db.Column(db.Boolean, default=False, nullable=False)
    start_at = db.Column(db.DateTime(timezone=True), nullable=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    set_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    article = db.relationship("Article", foreign_keys=[article_id])
    set_by_user = db.relationship("User", foreign_keys=[set_by_user_id])


class SiteAnnouncement(db.Model):
    __tablename__ = "site_announcements"

    DISPLAY_BANNER = "top_banner"
    DISPLAY_MODAL = "modal_popup"
    DISPLAY_SLIDE = "slide_in"

    SEVERITY_INFO = "info"
    SEVERITY_SUCCESS = "success"
    SEVERITY_WARNING = "warning"
    SEVERITY_URGENT = "urgent"

    SCOPE_SITE = "site_wide"
    SCOPE_CAMPUS = "campus_only"
    SCOPE_HOME = "homepage_only"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    display_type = db.Column(db.String(32), nullable=False, default=DISPLAY_BANNER)
    severity = db.Column(db.String(16), nullable=False, default=SEVERITY_INFO, index=True)
    target_scope = db.Column(db.String(32), nullable=False, default=SCOPE_SITE, index=True)
    cta_text = db.Column(db.String(80), nullable=True)
    cta_url = db.Column(db.String(500), nullable=True)
    dismissible = db.Column(db.Boolean, default=True, nullable=False)
    priority = db.Column(db.Integer, default=0, nullable=False)
    start_at = db.Column(db.DateTime(timezone=True), nullable=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        db.Index("ix_announcements_scope_severity", "target_scope", "severity", "is_active"),
    )