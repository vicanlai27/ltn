from datetime import datetime, timezone

import bcrypt
from flask_login import UserMixin

from app.extensions import db, login_manager
from app.utils.security import utcnow


class User(UserMixin, db.Model):
    __tablename__ = "users"

    ROLE_SUPER_ADMIN = "super_admin"
    ROLE_ADMIN = "admin"
    ROLE_EDITOR = "editor"
    ROLE_TEACHER_EDITOR = "teacher_editor"
    ROLE_AUTHOR = "author"
    ROLE_STUDENT_JOURNALIST = "student_journalist"
    ROLE_STUDENT_CONTRIBUTOR = "student_contributor"
    ROLE_ALUMNI_CONTRIBUTOR = "alumni_contributor"

    ROLES = (
        ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_EDITOR, ROLE_TEACHER_EDITOR,
        ROLE_AUTHOR, ROLE_STUDENT_JOURNALIST, ROLE_STUDENT_CONTRIBUTOR,
        ROLE_ALUMNI_CONTRIBUTOR,
    )
    STAFF_ROLES = (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_EDITOR, ROLE_TEACHER_EDITOR)
    CONTRIBUTOR_ROLES = (ROLE_STUDENT_JOURNALIST, ROLE_STUDENT_CONTRIBUTOR, ROLE_ALUMNI_CONTRIBUTOR)

    STATUS_PENDING = "pending_verification"
    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_DEACTIVATED = "deactivated"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default=ROLE_STUDENT_CONTRIBUTOR, index=True)
    account_status = db.Column(db.String(32), nullable=False, default=STATUS_PENDING, index=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verified_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verified_at = db.Column(db.DateTime(timezone=True), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    avatar = db.Column(db.String(255), nullable=True)

    # Two-factor auth (TOTP)
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    totp_backup_codes_hash = db.Column(db.Text, nullable=True)  # JSON list of hashes

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    created_by = db.relationship("User", remote_side="User.id", foreign_keys=[created_by_id])
    verified_by = db.relationship("User", foreign_keys=[verified_by_id])
    author_profile = db.relationship("AuthorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    articles = db.relationship("Article", back_populates="author", foreign_keys="Article.author_id")
    audit_passes = db.relationship("Article", back_populates="audited_by", foreign_keys="Article.audited_by_id")
    preferences = db.relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notification_subscriptions = db.relationship("NotificationSubscription", back_populates="user", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", back_populates="actor", foreign_keys="ActivityLog.actor_id")

    __table_args__ = (
        db.Index("ix_users_status_role", "account_status", "role"),
    )

    def set_password(self, raw: str) -> None:
        self.password_hash = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        try:
            return bcrypt.checkpw(raw.encode("utf-8"), self.password_hash.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    @property
    def is_verified(self) -> bool:
        return self.account_status == self.STATUS_ACTIVE and self.verified_at is not None

    @property
    def can_login(self) -> bool:
        return self.is_active and self.account_status == self.STATUS_ACTIVE

    @property
    def requires_2fa(self) -> bool:
        return self.role in (self.ROLE_SUPER_ADMIN, self.ROLE_ADMIN) and self.totp_enabled

    def is_at_least(self, role: str) -> bool:
        """Hierarchical role check. super_admin > admin > editor > teacher_editor > author > contributors."""
        hierarchy = [
            self.ROLE_SUPER_ADMIN, self.ROLE_ADMIN, self.ROLE_EDITOR,
            self.ROLE_TEACHER_EDITOR, self.ROLE_AUTHOR,
            self.ROLE_STUDENT_JOURNALIST, self.ROLE_STUDENT_CONTRIBUTOR, self.ROLE_ALUMNI_CONTRIBUTOR,
        ]
        try:
            return hierarchy.index(self.role) <= hierarchy.index(role)
        except ValueError:
            return False


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class AuthorProfile(db.Model):
    __tablename__ = "author_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    bio = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.String(255), nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    school_role = db.Column(db.String(120), nullable=True)
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=True)
    social_links = db.Column(db.JSON, nullable=True)  # {"twitter": "...", "instagram": "..."}
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="author_profile")
    house = db.relationship("House", foreign_keys=[house_id])


class UserPreference(db.Model):
    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    preferred_categories = db.Column(db.JSON, default=list)      # list of category ids
    preferred_campus_sections = db.Column(db.JSON, default=list) # list of slug strings
    dark_mode = db.Column(db.String(16), default="system")       # light | dark | system
    notification_preferences = db.Column(db.JSON, default=dict)

    user = db.relationship("User", back_populates="preferences")


class NotificationSubscription(db.Model):
    __tablename__ = "notification_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    endpoint = db.Column(db.String(500), nullable=False)
    subscription_data = db.Column(db.JSON, nullable=False)
    preferences = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="notification_subscriptions")