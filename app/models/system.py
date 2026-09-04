from app.extensions import db
from app.utils.security import utcnow


class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)


class Advertisement(db.Model):
    __tablename__ = "advertisements"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    placement = db.Column(db.String(60), nullable=False, index=True)  # header | after_hero | article_middle | sidebar | ...
    image = db.Column(db.String(255), nullable=True)
    html_code = db.Column(db.Text, nullable=True)
    target_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    start_at = db.Column(db.DateTime(timezone=True), nullable=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=True)
    priority = db.Column(db.Integer, default=0, nullable=False)


class ActivityLog(db.Model):
    """Append-only audit trail: who did what, when, to which target."""
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)  # article.publish | article.audit.approve | user.verify | ...
    target_type = db.Column(db.String(60), nullable=True, index=True)  # article | user | theme | ...
    target_id = db.Column(db.Integer, nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    actor = db.relationship("User", back_populates="activity_logs", foreign_keys=[actor_id])


class ConsentRecord(db.Model):
    """Media consent for minors, captured before publishing associated media."""
    __tablename__ = "consent_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"), nullable=False, index=True)
    media_reference_type = db.Column(db.String(40), nullable=False, index=True)  # article | gallery | video
    media_reference_id = db.Column(db.Integer, nullable=False, index=True)
    consent_given_by = db.Column(db.String(120), nullable=False)  # parent/guardian name
    consent_date = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.Index("ix_consent_media", "media_reference_type", "media_reference_id"),
    )