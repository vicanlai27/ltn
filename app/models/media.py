from app.extensions import db
from app.utils.security import utcnow


class Gallery(db.Model):
    __tablename__ = "galleries"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey("campus_events.id"), nullable=True, index=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    images = db.relationship("GalleryImage", back_populates="gallery", cascade="all, delete-orphan", order_by="GalleryImage.display_order")


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    gallery_id = db.Column(db.Integer, db.ForeignKey("galleries.id", ondelete="CASCADE"), nullable=False, index=True)
    image = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.String(255), nullable=True)
    display_order = db.Column(db.Integer, default=0, nullable=False)

    gallery = db.relationship("Gallery", back_populates="images")


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    thumbnail = db.Column(db.String(255), nullable=True)
    video_url = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # seconds
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    view_count = db.Column(db.Integer, default=0, nullable=False)


class PodcastEpisode(db.Model):
    __tablename__ = "podcast_episodes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    audio_url = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # seconds
    episode_number = db.Column(db.Integer, nullable=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)