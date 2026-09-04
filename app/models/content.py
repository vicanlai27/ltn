from app.extensions import db
from app.utils.security import utcnow


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    parent = db.relationship("Category", remote_side="Category.id", backref="children")
    articles = db.relationship("Article", back_populates="category")


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)

    articles = db.relationship("TagRelation", back_populates="tag", cascade="all, delete-orphan")


class Article(db.Model):
    __tablename__ = "articles"

    # Content types
    TYPE_NEWS = "news_article"
    TYPE_OPINION = "opinion"
    TYPE_ANALYSIS = "analysis"
    TYPE_INVESTIGATION = "investigation"
    TYPE_INTERVIEW = "interview"
    TYPE_EXPLAINER = "explainer"
    TYPE_60S = "60_second_read"
    TYPE_BREAKING = "breaking_news"
    TYPE_LIVE = "live_story"
    TYPE_CAMPUS = "campus_story"
    TYPE_SPORTS = "sports_story"
    TYPE_CREATOR_PROFILE = "creator_profile"
    TYPE_STUDENT_SPOTLIGHT = "student_spotlight"
    TYPE_STAFF_SPOTLIGHT = "staff_spotlight"
    TYPE_ALUMNI_STORY = "alumni_story"

    # Statuses
    STATUS_DRAFT = "draft"
    STATUS_PENDING_REVIEW = "pending_review"
    STATUS_PENDING_AUDIT = "pending_audit"
    STATUS_SCHEDULED = "scheduled"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_REJECTED = "rejected"

    PUBLIC_STATUSES = (STATUS_PUBLISHED, STATUS_SCHEDULED)

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    excerpt = db.Column(db.Text, nullable=True)
    body = db.Column(db.Text, nullable=False)

    featured_image = db.Column(db.String(255), nullable=True)
    featured_image_alt = db.Column(db.String(255), nullable=True)
    image_caption = db.Column(db.String(255), nullable=True)
    youtube_video_id = db.Column(db.String(11), nullable=True)
    special_edition_id = db.Column(db.Integer, db.ForeignKey("special_editions.id", ondelete="SET NULL"), nullable=True, index=True)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    content_type = db.Column(db.String(40), nullable=False, default=TYPE_NEWS, index=True)

    status = db.Column(db.String(32), nullable=False, default=STATUS_DRAFT, index=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_breaking = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_trending = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_editors_pick = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Campus linkage
    is_campus = db.Column(db.Boolean, default=False, nullable=False, index=True)
    campus_section = db.Column(db.String(60), nullable=True)
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=True)

    # Audio narration ("Listen to this story")
    audio_url = db.Column(db.String(255), nullable=True)
    audio_duration = db.Column(db.Integer, nullable=True)

    # Engagement counters (denormalized; kept in sync by services)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    share_count = db.Column(db.Integer, default=0, nullable=False)
    reaction_count = db.Column(db.Integer, default=0, nullable=False)

    published_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Audit trail
    is_audited = db.Column(db.Boolean, default=False, nullable=False, index=True)
    audited_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    audited_at = db.Column(db.DateTime(timezone=True), nullable=True)
    audit_notes = db.Column(db.Text, nullable=True)

    # Relationships
    category = db.relationship("Category", back_populates="articles")
    author = db.relationship("User", back_populates="articles", foreign_keys=[author_id])
    audited_by = db.relationship("User", back_populates="audit_passes", foreign_keys=[audited_by_id])
    house = db.relationship("House", foreign_keys=[house_id])
    club = db.relationship("Club", foreign_keys=[club_id])
    special_edition = db.relationship("SpecialEdition", back_populates="articles")
    tag_relations = db.relationship("TagRelation", back_populates="article", cascade="all, delete-orphan")
    reactions = db.relationship("Reaction", back_populates="article", cascade="all, delete-orphan")
    share_events = db.relationship("ShareEvent", back_populates="article", cascade="all, delete-orphan")
    view_events = db.relationship("ViewEvent", back_populates="article", cascade="all, delete-orphan")
    poll = db.relationship("Poll", back_populates="article", uselist=False, cascade="all, delete-orphan")
    images = db.relationship("ArticleImage", back_populates="article", cascade="all, delete-orphan", order_by="ArticleImage.display_order")
    comments = db.relationship("Comment", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_articles_public", "status", "is_audited", "published_at"),
        db.Index("ix_articles_campus_section", "is_campus", "campus_section", "status"),
        db.Index("ix_articles_breaking_queue", "is_breaking", "status", "created_at"),
    )

    @property
    def tags(self):
        return [tr.tag for tr in self.tag_relations]

    @property
    def is_publicly_visible(self) -> bool:
        return self.status in self.PUBLIC_STATUSES and self.is_audited

    @property
    def gallery(self) -> list:
        """
        Ordered list of navigable images for the reader-facing lightbox:
        the featured image first (if set), followed by any additional
        gallery images the author uploaded.
        """
        items = []
        if self.featured_image:
            items.append({
                "src": self.featured_image,
                "alt": self.featured_image_alt or self.title,
                "caption": self.image_caption or "",
                "is_featured": True,
            })
        for img in self.images:
            items.append({
                "src": img.image,
                "alt": img.alt_text or self.title,
                "caption": img.caption or "",
                "is_featured": False,
                "id": img.id,
            })
        return items


class TagRelation(db.Model):
    __tablename__ = "tag_relations"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)

    article = db.relationship("Article", back_populates="tag_relations")
    tag = db.relationship("Tag", back_populates="articles")

    __table_args__ = (
        db.UniqueConstraint("article_id", "tag_id", name="uq_tag_relations_article_tag"),
    )


class ArticleImage(db.Model):
    """
    Additional images an author attaches to an article beyond the single
    featured_image on Article. Rendered as a navigable gallery/lightbox on
    the article read page (featured image is slide one, these follow).
    """
    __tablename__ = "article_images"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
    image = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.String(255), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    article = db.relationship("Article", back_populates="images")