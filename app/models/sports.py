from app.extensions import db
from app.utils.security import utcnow


class Sport(db.Model):
    __tablename__ = "sports"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    teams = db.relationship("Team", back_populates="sport", cascade="all, delete-orphan")


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sport_id = db.Column(db.Integer, db.ForeignKey("sports.id"), nullable=False, index=True)
    logo = db.Column(db.String(255), nullable=True)
    season = db.Column(db.String(40), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    sport = db.relationship("Sport", back_populates="teams")
    home_fixtures = db.relationship("Fixture", back_populates="home_team", foreign_keys="Fixture.home_team_id")
    away_fixtures = db.relationship("Fixture", back_populates="away_team", foreign_keys="Fixture.away_team_id")


class Fixture(db.Model):
    __tablename__ = "fixtures"

    STATUS_SCHEDULED = "scheduled"
    STATUS_LIVE = "live"
    STATUS_COMPLETED = "completed"
    STATUS_POSTPONED = "postponed"
    STATUS_CANCELLED = "cancelled"

    id = db.Column(db.Integer, primary_key=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False, index=True)
    competition = db.Column(db.String(120), nullable=True)
    venue = db.Column(db.String(120), nullable=True)
    match_date = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    status = db.Column(db.String(32), default=STATUS_SCHEDULED, nullable=False, index=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    home_team = db.relationship("Team", back_populates="home_fixtures", foreign_keys=[home_team_id])
    away_team = db.relationship("Team", back_populates="away_fixtures", foreign_keys=[away_team_id])