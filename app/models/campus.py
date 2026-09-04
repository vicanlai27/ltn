from app.extensions import db
from app.utils.security import utcnow


class House(db.Model):
    __tablename__ = "houses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    color = db.Column(db.String(16), nullable=True)  # hex
    house_points = db.Column(db.Integer, default=0, nullable=False)  # denormalized running total
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    scores = db.relationship("HouseScore", back_populates="house", cascade="all, delete-orphan")
    students = db.relationship("StudentProfile", back_populates="house")
    author_profiles = db.relationship("AuthorProfile", back_populates="house")


class HouseScore(db.Model):
    __tablename__ = "house_scores"

    SOURCE_CAMPUS_EVENT = "campus_event"
    SOURCE_FIXTURE = "fixture"
    SOURCE_MANUAL = "manual"

    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(80), nullable=True)
    source_type = db.Column(db.String(32), nullable=False, default=SOURCE_MANUAL)
    source_id = db.Column(db.Integer, nullable=True)  # nullable when source_type = manual
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    house = db.relationship("House", back_populates="scores")

    __table_args__ = (
        db.Index("ix_house_scores_source", "source_type", "source_id"),
    )


class Club(db.Model):
    __tablename__ = "clubs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    cover_image = db.Column(db.String(255), nullable=True)
    meeting_information = db.Column(db.Text, nullable=True)
    leader_name = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class CampusEvent(db.Model):
    __tablename__ = "campus_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(280), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    event_type = db.Column(db.String(60), nullable=True, index=True)  # academic | sports | club | cultural | assembly
    start_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    organizer = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(32), default="scheduled", nullable=False, index=True)  # scheduled | live | completed | cancelled
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    poll = db.relationship("Poll", back_populates="campus_event", uselist=False, cascade="all, delete-orphan")