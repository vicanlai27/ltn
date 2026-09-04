"""Queries used by the editorial dashboards.

The dashboard deliberately combines the denormalized counters on Article with
the event tables. Counters provide a fast all-time snapshot while events make
the selected reporting window meaningful.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models.content import Article, Category
from app.models.engagement import Reaction, ShareEvent, ViewEvent
from app.utils.security import utcnow


REPORTING_WINDOWS = (7, 30, 90, 365)


def _bucket_label(bucket: date, days: int) -> str:
    if days > 90:
        return bucket.strftime("%b %Y")
    if days > 31:
        return f"Week of {bucket.strftime('%b %d').replace(' 0', ' ')}"
    return bucket.strftime("%b %d").replace(" 0", " ")


def _build_view_trend(since, now, days: int):
    """Return a small, database-agnostic set of view trend points."""
    day_expression = func.date(ViewEvent.created_at)
    rows = (
        db.session.query(day_expression.label("day"), func.count(ViewEvent.id))
        .filter(ViewEvent.created_at >= since, ViewEvent.created_at <= now)
        .group_by(day_expression)
        .all()
    )

    daily = {}
    for day_value, count in rows:
        if isinstance(day_value, datetime):
            day_key = day_value.date()
        elif isinstance(day_value, date):
            day_key = day_value
        else:
            day_key = date.fromisoformat(str(day_value)[:10])
        daily[day_key] = int(count or 0)

    start = since.date()
    end = now.date()
    buckets = {}
    cursor = start
    while cursor <= end:
        if days > 90:
            bucket = cursor.replace(day=1)
        elif days > 31:
            bucket = cursor - timedelta(days=cursor.weekday())
        else:
            bucket = cursor
        buckets.setdefault(bucket, 0)
        buckets[bucket] += daily.get(cursor, 0)
        cursor += timedelta(days=1)

    points = [
        {"label": _bucket_label(bucket, days), "value": value}
        for bucket, value in sorted(buckets.items())
    ]
    return points, max((point["value"] for point in points), default=0)


def get_dashboard_analytics(days: int = 30) -> dict:
    """Build the content-performance view shared by admin roles."""
    days = days if days in REPORTING_WINDOWS else 30
    now = utcnow()
    since = now - timedelta(days=days)
    published_filter = Article.status == Article.STATUS_PUBLISHED

    totals = (
        db.session.query(
            func.coalesce(func.sum(Article.view_count), 0),
            func.coalesce(func.sum(Article.share_count), 0),
            func.coalesce(func.sum(Article.reaction_count), 0),
        )
        .filter(published_filter)
        .one()
    )

    period_views = ViewEvent.query.filter(
        ViewEvent.created_at >= since,
        ViewEvent.created_at <= now,
    ).count()
    period_shares = ShareEvent.query.filter(
        ShareEvent.created_at >= since,
        ShareEvent.created_at <= now,
    ).count()
    period_reactions = Reaction.query.filter(
        Reaction.created_at >= since,
        Reaction.created_at <= now,
    ).count()
    published_in_period = Article.query.filter(
        published_filter,
        Article.published_at.isnot(None),
        Article.published_at >= since,
        Article.published_at <= now,
    ).count()

    published_count = Article.query.filter(published_filter).count()
    engagement_rate = (
        round(((period_shares + period_reactions) / period_views) * 100, 1)
        if period_views
        else 0
    )

    type_rows = (
        db.session.query(
            Article.content_type,
            func.count(Article.id),
            func.coalesce(func.sum(Article.view_count), 0),
        )
        .filter(published_filter)
        .group_by(Article.content_type)
        .order_by(func.count(Article.id).desc())
        .all()
    )
    content_mix = [
        {
            "label": (content_type or "Unspecified").replace("_", " ").title(),
            "count": int(count or 0),
            "views": int(views or 0),
            "percent": round((count / published_count) * 100) if published_count else 0,
        }
        for content_type, count, views in type_rows
    ]

    category_rows = (
        db.session.query(
            Category.name,
            func.count(Article.id),
            func.coalesce(func.sum(Article.view_count), 0),
        )
        .join(Article, Article.category_id == Category.id)
        .filter(published_filter)
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Article.view_count).desc(), func.count(Article.id).desc())
        .limit(6)
        .all()
    )
    category_performance = [
        {"label": name, "count": int(count or 0), "views": int(views or 0)}
        for name, count, views in category_rows
    ]

    top_articles = (
        Article.query.filter(published_filter)
        .order_by(
            Article.view_count.desc(),
            Article.reaction_count.desc(),
            Article.published_at.desc(),
        )
        .limit(5)
        .all()
    )
    trend, max_trend_views = _build_view_trend(since, now, days)

    return {
        "days": days,
        "period_views": period_views,
        "period_shares": period_shares,
        "period_reactions": period_reactions,
        "published_in_period": published_in_period,
        "all_time_views": int(totals[0] or 0),
        "all_time_shares": int(totals[1] or 0),
        "all_time_reactions": int(totals[2] or 0),
        "engagement_rate": engagement_rate,
        "content_mix": content_mix,
        "category_performance": category_performance,
        "top_articles": top_articles,
        "view_trend": trend,
        "max_trend_views": max_trend_views,
    }