from sqlalchemy import CheckConstraint

from app.extensions import db
from app.utils.security import utcnow


class Reaction(db.Model):
    __tablename__ = "reactions"

    TYPE_LIKE = "like"
    TYPE_LOVE = "love"
    TYPE_LAUGH = "laugh"
    TYPE_WOW = "wow"
    TYPE_ANGRY = "angry"
    TYPE_FIRE = "fire"
    TYPES = (TYPE_LIKE, TYPE_LOVE, TYPE_LAUGH, TYPE_WOW, TYPE_ANGRY, TYPE_FIRE)

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    session_hash = db.Column(db.String(64), nullable=False, index=True)
    reaction_type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    article = db.relationship("Article", back_populates="reactions")

    __table_args__ = (
        db.Index("ix_reactions_dedup", "article_id", "session_hash", "user_id"),
    )


class Comment(db.Model):
    """A reader comment on an article. Readers can also react to comments."""
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    session_hash = db.Column(db.String(64), nullable=False, index=True)
    display_name = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    article = db.relationship("Article", back_populates="comments")
    user = db.relationship("User")
    reactions = db.relationship("CommentReaction", back_populates="comment", cascade="all, delete-orphan")


class CommentReaction(db.Model):
    """A reader's reaction (like/love/laugh) on a single comment."""
    __tablename__ = "comment_reactions"

    TYPE_LIKE = "like"
    TYPE_LOVE = "love"
    TYPE_LAUGH = "laugh"
    TYPES = (TYPE_LIKE, TYPE_LOVE, TYPE_LAUGH)

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    session_hash = db.Column(db.String(64), nullable=False, index=True)
    reaction_type = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    comment = db.relationship("Comment", back_populates="reactions")

    __table_args__ = (
        db.Index("ix_comment_reactions_dedup", "comment_id", "session_hash", "user_id"),
    )


class ShareEvent(db.Model):
    __tablename__ = "share_events"

    PLATFORM_WHATSAPP = "whatsapp"
    PLATFORM_X = "x"
    PLATFORM_TWITTER_LEGACY = "twitter_legacy"
    PLATFORM_FACEBOOK = "facebook"
    PLATFORM_INSTAGRAM = "instagram"
    PLATFORM_COPY_LINK = "copy_link"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = db.Column(db.String(32), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    session_hash = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    article = db.relationship("Article", back_populates="share_events")


class ViewEvent(db.Model):
    __tablename__ = "view_events"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    session_hash = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    referrer = db.Column(db.String(500), nullable=True)
    device_type = db.Column(db.String(32), nullable=True)  # mobile | tablet | desktop
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    article = db.relationship("Article", back_populates="view_events")

    __table_args__ = (
        db.Index("ix_view_events_dedup", "article_id", "session_hash", "created_at"),
    )


class Report(db.Model):
    __tablename__ = "reports"

    TARGET_REACTION = "reaction"
    TARGET_COMMENT = "comment"
    TARGET_ARTICLE = "article"

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(32), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    session_hash = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(32), default="open", nullable=False, index=True)  # open | reviewed | dismissed
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Poll(db.Model):
    __tablename__ = "polls"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="draft", nullable=False, index=True)  # draft | active | closed
    start_at = db.Column(db.DateTime(timezone=True), nullable=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=True)
    allow_multiple = db.Column(db.Boolean, default=False, nullable=False)
    show_results = db.Column(db.Boolean, default=True, nullable=False)

    # Mutually exclusive target linkage (enforced by CHECK below)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=True, index=True)
    campus_event_id = db.Column(db.Integer, db.ForeignKey("campus_events.id", ondelete="CASCADE"), nullable=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    article = db.relationship("Article", back_populates="poll")
    campus_event = db.relationship("CampusEvent", back_populates="poll")
    options = db.relationship("PollOption", back_populates="poll", cascade="all, delete-orphan", order_by="PollOption.display_order")

    __table_args__ = (
        CheckConstraint(
            "NOT (article_id IS NOT NULL AND campus_event_id IS NOT NULL)",
            name="ck_poll_mutually_exclusive_target",
        ),
    )


class PollOption(db.Model):
    __tablename__ = "poll_options"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True)
    label = db.Column(db.String(200), nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    vote_count = db.Column(db.Integer, default=0, nullable=False)

    poll = db.relationship("Poll", back_populates="options")