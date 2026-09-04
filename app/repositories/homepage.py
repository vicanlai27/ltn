from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.extensions import db
from app.models.content import Article, Category
from app.models.editorial import PlacementSlot
from app.repositories.articles import public_articles_query


def _base():
    return public_articles_query()


def _aware(dt: datetime | None) -> datetime | None:
    """
    SQLite doesn't persist tzinfo, so datetimes read back from the DB come
    back naive even though the columns are declared DateTime(timezone=True).
    Treat naive values as UTC (everything in this app is stored/generated in
    UTC) so they can be safely compared/subtracted against tz-aware datetimes.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def hero_primary() -> Article | None:
    """Hero primary slot: manual override wins, else highest-priority published article."""
    manual = PlacementSlot.query.filter_by(
        zone=PlacementSlot.ZONE_HERO_PRIMARY,
        is_manual_override=True,
    ).filter(
        db.or_(PlacementSlot.end_at.is_(None), PlacementSlot.end_at >= datetime.now(timezone.utc))
    ).first()
    if manual:
        article = db.session.get(Article, manual.article_id)
        if article and article.is_publicly_visible:
            return article

    return _base().order_by(
        Article.is_breaking.desc(),
        Article.is_featured.desc(),
        Article.published_at.desc().nullslast(),
    ).first()


def hero_secondary(limit: int = 3) -> list[Article]:
    primary = hero_primary()
    q = _base().order_by(
        Article.is_featured.desc(),
        Article.published_at.desc().nullslast(),
    ).limit(limit + 5)

    results = []
    for a in q.all():
        if primary and a.id == primary.id:
            continue
        results.append(a)
        if len(results) >= limit:
            break
    return results


def trending_now(limit: int = 8) -> list[Article]:
    """
    Hybrid editorial + engagement score.
    Score = (is_editors_pick * 1000) + (is_featured * 500) +
            (view_count * 0.3) + (reaction_count * 2) + (share_count * 5) +
            recency_bonus (decays over 7 days).
    """
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    rows = _base().filter(
        db.or_(Article.published_at.is_(None), Article.published_at >= seven_days_ago)
    ).all()

    def score(a):
        published_or_created = _aware(a.published_at) or _aware(a.created_at)
        age_hours = max(1, (now - published_or_created).total_seconds() / 3600)
        recency = 500 / (1 + age_hours / 24)
        return (
            (1000 if a.is_editors_pick else 0)
            + (500 if a.is_featured else 0)
            + (a.view_count or 0) * 0.3
            + (a.reaction_count or 0) * 2
            + (a.share_count or 0) * 5
            + recency
        )

    rows.sort(key=score, reverse=True)
    return rows[:limit]


def whats_happening(limit: int = 10) -> list[Article]:
    """Fast-moving feed: breaking, viral, recent — mixed."""
    return _base().order_by(
        Article.is_breaking.desc(),
        Article.published_at.desc().nullslast(),
    ).limit(limit).all()


def latest_news(limit: int = 8) -> list[Article]:
    return _base().order_by(Article.published_at.desc().nullslast()).limit(limit).all()


def campus_highlights(limit: int = 4) -> list[Article]:
    return _base().filter(Article.is_campus.is_(True)).order_by(
        Article.published_at.desc().nullslast()
    ).limit(limit).all()


def editors_choice(limit: int = 4) -> list[Article]:
    return _base().filter(Article.is_editors_pick.is_(True)).order_by(
        Article.published_at.desc().nullslast()
    ).limit(limit).all()


def explain_this(limit: int = 3) -> list[Article]:
    return _base().filter(Article.content_type == Article.TYPE_EXPLAINER).order_by(
        Article.published_at.desc().nullslast()
    ).limit(limit).all()


def category_section_articles(category_slug: str, limit: int = 6) -> list[Article]:
    return _base().join(Category).filter(Category.slug == category_slug).order_by(
        Article.published_at.desc().nullslast()
    ).limit(limit).all()