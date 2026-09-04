from datetime import datetime, timezone
from app.extensions import db
from app.models.system import Advertisement

def active_ad(placement):
    now=datetime.now(timezone.utc)
    return Advertisement.query.filter_by(placement=placement,is_active=True).filter(
        db.or_(Advertisement.start_at.is_(None), Advertisement.start_at <= now),
        db.or_(Advertisement.end_at.is_(None), Advertisement.end_at >= now),
    ).order_by(Advertisement.priority.desc(), Advertisement.id.desc()).first()
