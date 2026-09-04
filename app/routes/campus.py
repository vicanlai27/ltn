from datetime import datetime, timezone, timedelta
from calendar import monthrange

from flask import Blueprint, abort, render_template, request

from app.models.campus import CampusEvent, Club, House
from app.models.media import Gallery
from app.models.people import AlumniProfile, StaffProfile, StudentProfile
from app.models.sports import Sport
from app.repositories import campus as campus_repo
from app.utils.security import ensure_aware

campus_bp = Blueprint("campus", __name__, url_prefix="/campus")


# === Hub ===

@campus_bp.route("/")
def index():
    return render_template(
        "campus/index.html",
        sections=campus_repo.CAMPUS_SECTIONS,
        highlights=campus_repo.campus_highlights(),
        standings=campus_repo.house_standings()[:4],
        house_of_the_week=campus_repo.house_of_the_week() if hasattr(campus_repo, "house_of_the_week") else None,
        upcoming_events=campus_repo.upcoming_events(limit=6),
        active_polls=campus_repo.active_campus_polls(limit=3),
        upcoming_fixtures=campus_repo.upcoming_fixtures(limit=5),
        recent_results=campus_repo.recent_results(limit=5),
    )


# === Generic article-backed sections ===

@campus_bp.route("/<slug>")
def section(slug):
    # Model-backed sections have their own routes below; this handles article sections
    article_sections = {s[0]: s for s in campus_repo.CAMPUS_SECTIONS}
    if slug not in article_sections:
        abort(404)

    _, title, description = article_sections[slug]
    page = request.args.get("page", 1, type=int)
    articles = campus_repo.section_articles(slug, page=page)

    return render_template(
        "campus/section.html",
        slug=slug,
        title=title,
        description=description,
        articles=articles,
    )


# === Houses ===

@campus_bp.route("/houses")
def houses_index():
    standings = campus_repo.house_standings()
    return render_template("campus/houses_index.html", standings=standings)


@campus_bp.route("/houses/<slug>")
def house_show(slug):
    house = House.query.filter_by(slug=slug).first_or_404()
    recent_scores = campus_repo.house_recent_scores(house.id)
    articles = campus_repo.campus_articles_query()\
        .filter_by(campus_section="houses", house_id=house.id)\
        .order_by(campus_repo.Article.published_at.desc().nullslast()).limit(10).all() if False else []
    # Simpler:
    from app.repositories.articles import public_articles_query
    from app.models.content import Article
    articles = public_articles_query()\
        .filter(Article.is_campus.is_(True), Article.campus_section == "houses", Article.house_id == house.id)\
        .order_by(Article.published_at.desc().nullslast()).limit(10).all()
    students = StudentProfile.query.filter_by(house_id=house.id).limit(12).all()

    return render_template(
        "campus/house_show.html",
        house=house,
        recent_scores=recent_scores,
        articles=articles,
        students=students,
    )


# === Clubs ===

@campus_bp.route("/clubs")
def clubs_index():
    clubs = campus_repo.active_clubs()
    return render_template("campus/clubs_index.html", clubs=clubs)


@campus_bp.route("/clubs/<slug>")
def club_show(slug):
    club = Club.query.filter_by(slug=slug).first_or_404()
    articles = campus_repo.club_articles(club.id)
    return render_template("campus/club_show.html", club=club, articles=articles)


# === Sports ===

@campus_bp.route("/sports")
def sports_index():
    sports = campus_repo.active_sports()
    upcoming = campus_repo.upcoming_fixtures(limit=8)
    recent = campus_repo.recent_results(limit=8)
    live = campus_repo.live_fixtures()
    return render_template(
        "campus/sports_index.html",
        sports=sports,
        upcoming=upcoming,
        recent=recent,
        live=live,
    )


@campus_bp.route("/sports/<slug>")
def sport_show(slug):
    sport = Sport.query.filter_by(slug=slug).first_or_404()
    upcoming = campus_repo.sport_fixtures(sport.id, status="scheduled")
    completed = campus_repo.sport_fixtures(sport.id, status="completed")
    teams = sport.teams
    return render_template(
        "campus/sport_show.html",
        sport=sport,
        upcoming=upcoming,
        completed=completed,
        teams=teams,
    )


# === People ===

@campus_bp.route("/students")
def students_index():
    page = request.args.get("page", 1, type=int)
    students = campus_repo.all_students(page=page)
    featured = campus_repo.featured_students(limit=4)
    return render_template(
        "campus/people_index.html",
        title="Students",
        section_slug="students",
        people=students,
        featured=featured,
        person_type="student",
    )


@campus_bp.route("/students/<slug>")
def student_show(slug):
    student = StudentProfile.query.filter_by(slug=slug).first_or_404()
    return render_template("campus/person_show.html", person=student, person_type="student")


@campus_bp.route("/staff")
def staff_index():
    page = request.args.get("page", 1, type=int)
    staff = campus_repo.all_staff(page=page)
    featured = campus_repo.featured_staff(limit=4)
    return render_template(
        "campus/people_index.html",
        title="Staff",
        section_slug="staff",
        people=staff,
        featured=featured,
        person_type="staff",
    )


@campus_bp.route("/staff/<slug>")
def staff_show(slug):
    person = StaffProfile.query.filter_by(slug=slug).first_or_404()
    return render_template("campus/person_show.html", person=person, person_type="staff")


@campus_bp.route("/alumni")
def alumni_index():
    page = request.args.get("page", 1, type=int)
    alumni = campus_repo.all_alumni(page=page)
    featured = campus_repo.featured_alumni(limit=4)
    return render_template(
        "campus/people_index.html",
        title="Alumni",
        section_slug="alumni",
        people=alumni,
        featured=featured,
        person_type="alumni",
    )


@campus_bp.route("/alumni/<slug>")
def alumni_show(slug):
    person = AlumniProfile.query.filter_by(slug=slug).first_or_404()
    return render_template("campus/person_show.html", person=person, person_type="alumni")


# === Calendar ===

@campus_bp.route("/calendar")
def calendar():
    now = datetime.now(timezone.utc)
    year = request.args.get("year", now.year, type=int)
    month = request.args.get("month", now.month, type=int)

    # Clamp
    if month < 1: month = 12; year -= 1
    if month > 12: month = 1; year += 1

    first_day = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num, 23, 59, 59, tzinfo=timezone.utc)

    # Pad calendar grid: weekday of first day (Mon=0)
    start_weekday = first_day.weekday()
    events = campus_repo.events_in_range(first_day, last_day + timedelta(days=1))

    # Previous/next month navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    # List view toggle
    view = request.args.get("view", "month")
    list_events = campus_repo.upcoming_events(limit=50, from_date=first_day) if view == "list" else []

    return render_template(
        "campus/calendar.html",
        year=year, month=month,
        first_day=first_day, last_day_num=last_day_num,
        start_weekday=start_weekday,
        events=events,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        view=view, list_events=list_events,
        month_name=first_day.strftime("%B"),
    )


@campus_bp.route("/calendar/<int:event_id>")
def event_show(event_id):
    event = CampusEvent.query.get_or_404(event_id)
    return render_template("campus/event_show.html", event=event)


# === Gallery ===

@campus_bp.route("/gallery")
def gallery_index():
    page = request.args.get("page", 1, type=int)
    galleries = campus_repo.published_galleries(page=page)
    return render_template("campus/gallery_index.html", galleries=galleries)


@campus_bp.route("/gallery/<slug>")
def gallery_show(slug):
    gallery = Gallery.query.filter_by(slug=slug).first_or_404()
    if not gallery.published_at or ensure_aware(gallery.published_at) > datetime.now(timezone.utc):
        abort(404)
    return render_template("campus/gallery_show.html", gallery=gallery)


# === Campus Pulse (polls) ===

@campus_bp.route("/pulse")
def pulse():
    polls = campus_repo.active_campus_polls(limit=20)
    return render_template("campus/pulse.html", polls=polls)