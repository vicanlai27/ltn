from datetime import datetime, timezone

from app.extensions import db
from app.models.editorial import SiteAnnouncement


def active_announcements(scope: str | None = None):
    """Return currently active announcements, respecting start/end windows."""
    now = datetime.now(timezone.utc)
    q = SiteAnnouncement.query.filter(SiteAnnouncement.is_active.is_(True))
    if scope:
        q = q.filter(SiteAnnouncement.target_scope == scope)
    q = q.filter(
        db.or_(SiteAnnouncement.start_at.is_(None), SiteAnnouncement.start_at <= now)
    )
    q = q.filter(
        db.or_(SiteAnnouncement.end_at.is_(None), SiteAnnouncement.end_at >= now)
    )
    return q.order_by(SiteAnnouncement.priority.desc()).all()