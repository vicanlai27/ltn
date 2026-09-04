from app.extensions import db
from app.utils.security import utcnow


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    photo = db.Column(db.String(255), nullable=True)
    class_or_level = db.Column(db.String(60), nullable=True)
    house_id = db.Column(db.Integer, db.ForeignKey("houses.id"), nullable=True, index=True)
    achievements = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    house = db.relationship("House", back_populates="students")


class StaffProfile(db.Model):
    __tablename__ = "staff_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    photo = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(120), nullable=True)
    department = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    social_links = db.Column(db.JSON, nullable=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)


class AlumniProfile(db.Model):
    __tablename__ = "alumni_profiles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    graduation_year = db.Column(db.Integer, nullable=True, index=True)
    photo = db.Column(db.String(255), nullable=True)
    current_role = db.Column(db.String(160), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    story = db.Column(db.Text, nullable=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)