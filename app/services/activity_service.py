"""Audit logging helpers shared by authentication, editorial, and theme flows."""

from app.extensions import db
from app.models.system import ActivityLog


def log_activity(
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    notes: str | None = None,
) -> ActivityLog:
    """Persist an append-only activity record and return it."""
    entry = ActivityLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        notes=notes,
    )
    db.session.add(entry)
    db.session.commit()
    return entry