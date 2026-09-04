from datetime import datetime, timezone, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models.campus import CampusEvent, Club, House, HouseScore
from app.models.content import Article
from app.models.engagement import Poll
from app.models.media import Gallery
from app.models.people import AlumniProfile, StaffProfile, StudentProfile
from app.models.sports import Fixture, Sport, Team
from app.repositories.articles import public_articles_query


# === Campus sections (article-backed) ===

CAMPUS_SECTIONS = [
    ("campus-news", "Campus News", "Major school developments, announcements, achievements, visits, partnerships and institutional stories."),
    ("student-life", "Student Life", "Day-to-day school life, traditions, student experiences and community stories."),
    ("academics", "Academics", "Academic achievements, study resources, competitions, projects, university preparation and career guidance."),
    ("sports-games", "Sports & Games", "Fixtures, results, teams, match reports, player profiles, tournaments and sports features."),
    ("student-voice", "Student Voice", "Moderated student opinion, essays, poetry, stories and commentary."),
    ("archive", "School Archive", "Historical stories, old photographs, milestones, former leaders and school memories."),
]

# Sections backed by dedicated models (not article lists)
CAMPUS_MODEL_SECTIONS = {
    "houses", "clubs-societies", "sports-games-model",
    "student-spotlight", "staff-spotlight", "alumni",
    "campus-pulse", "campus-calendar", "campus-gallery", "campus-shorts",
}


def campus_articles_query():
    """Base query for campus-visible articles."""
    return public_articles_query().filter(Article.is_campus.is_(True))


def section_articles(campus_section: str, page: int = 1, per_page: int = 12):
    return campus_articles_query()\
        .filter(Article.campus_section == campus_section)\
        .order_by(Article.published_at.desc().nullslast())\
        .paginate(page=page, per_page=per_page, error_out=False)


def campus_highlights(limit: int = 6):
    return campus_articles_query()\
        .order_by(Article.is_featured.desc(), Article.published_at.desc().nullslast())\
        .limit(limit).all()


# === Houses ===

def house_standings():
    """Houses ordered by points descending."""
    return House.query.filter_by(is_active=True)\
        .order_by(House.house_points.desc(), House.name.asc()).all()


def house_recent_scores(house_id: int, limit: int = 10):
    return HouseScore.query.filter_by(house_id=house_id)\
        .order_by(HouseScore.created_at.desc()).limit(limit).all()


# === Clubs ===

def active_clubs():
    return Club.query.filter_by(is_active=True)\
        .order_by(Club.name.asc()).all()


def club_articles(club_id: int, limit: int = 10):
    return campus_articles_query()\
        .filter(Article.club_id == club_id)\
        .order_by(Article.published_at.desc().nullslast())\
        .limit(limit).all()


# === Sports ===

def active_sports():
    return Sport.query.filter_by(is_active=True)\
        .order_by(Sport.name.asc()).all()


def sport_fixtures(sport_id: int, status: str = None, limit: int = 20):
    q = Fixture.query.join(Team).filter(Team.sport_id == sport_id)
    if status:
        q = q.filter(Fixture.status == status)
    return q.order_by(Fixture.match_date.desc()).limit(limit).all()


def upcoming_fixtures(limit: int = 10):
    now = datetime.now(timezone.utc)
    return Fixture.query.filter(
        Fixture.status.in_([Fixture.STATUS_SCHEDULED, Fixture.STATUS_LIVE]),
        Fixture.match_date >= now,
    ).order_by(Fixture.match_date.asc()).limit(limit).all()


def recent_results(limit: int = 10):
    return Fixture.query.filter(Fixture.status == Fixture.STATUS_COMPLETED)\
        .order_by(Fixture.match_date.desc()).limit(limit).all()


def live_fixtures():
    return Fixture.query.filter_by(status=Fixture.STATUS_LIVE).all()


# === Events / Calendar ===

def upcoming_events(limit: int = 20, from_date: datetime = None):
    from_date = from_date or datetime.now(timezone.utc)
    return CampusEvent.query.filter(
        CampusEvent.start_at >= from_date,
        CampusEvent.status.in_(["scheduled", "live"]),
    ).order_by(CampusEvent.start_at.asc()).limit(limit).all()


def events_in_range(start: datetime, end: datetime):
    return CampusEvent.query.filter(
        CampusEvent.start_at >= start,
        CampusEvent.start_at < end,
    ).order_by(CampusEvent.start_at.asc()).all()


# === People ===

def featured_students(limit: int = 12):
    return StudentProfile.query.filter_by(is_featured=True)\
        .order_by(StudentProfile.created_at.desc()).limit(limit).all()


def all_students(page: int = 1, per_page: int = 24):
    return StudentProfile.query.order_by(StudentProfile.name.asc())\
        .paginate(page=page, per_page=per_page, error_out=False)


def featured_staff(limit: int = 12):
    return StaffProfile.query.filter_by(is_featured=True)\
        .order_by(StaffProfile.name.asc()).limit(limit).all()


def all_staff(page: int = 1, per_page: int = 24):
    return StaffProfile.query.order_by(StaffProfile.name.asc())\
        .paginate(page=page, per_page=per_page, error_out=False)


def featured_alumni(limit: int = 12):
    return AlumniProfile.query.filter_by(is_featured=True)\
        .order_by(AlumniProfile.graduation_year.desc().nullslast()).limit(limit).all()


def all_alumni(page: int = 1, per_page: int = 24):
    return AlumniProfile.query.order_by(AlumniProfile.graduation_year.desc().nullslast(), AlumniProfile.name.asc())\
        .paginate(page=page, per_page=per_page, error_out=False)


# === Polls (Campus Pulse) ===

def active_campus_polls(limit: int = 10):
    """Standalone polls (not attached to articles or events)."""
    now = datetime.now(timezone.utc)
    return Poll.query.filter(
        Poll.status == "active",
        Poll.article_id.is_(None),
        Poll.campus_event_id.is_(None),
        db.or_(Poll.start_at.is_(None), Poll.start_at <= now),
        db.or_(Poll.end_at.is_(None), Poll.end_at >= now),
    ).order_by(Poll.created_at.desc()).limit(limit).all()


# === Galleries ===

def published_galleries(page: int = 1, per_page: int = 12):
    now = datetime.now(timezone.utc)
    return Gallery.query.filter(
        Gallery.published_at.isnot(None),
        Gallery.published_at <= now,
    ).order_by(Gallery.published_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)