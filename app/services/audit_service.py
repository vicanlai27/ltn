from datetime import datetime, timezone

from sqlalchemy import func

from app.extensions import db
from app.models.content import Article
from app.models.system import ActivityLog


def get_audit_queue(auditor_id: int, include_breaking_first: bool = True) -> list[Article]:
    """
    Get articles pending audit, excluding those authored or approved by the auditor.
    Breaking news floats to the top.
    """
    # Get articles approved by this auditor (to exclude)
    approved_by_auditor = db.session.query(ActivityLog.target_id).filter(
        ActivityLog.action == "article.approve",
        ActivityLog.actor_id == auditor_id,
    ).subquery()

    query = Article.query.filter(
        Article.status == Article.STATUS_PENDING_AUDIT,
        Article.author_id != auditor_id,
        ~Article.id.in_(approved_by_auditor),
    )

    if include_breaking_first:
        # Sort: breaking first, then by created_at
        query = query.order_by(
            Article.is_breaking.desc(),
            Article.created_at.asc(),
        )
    else:
        query = query.order_by(Article.created_at.asc())

    return query.all()


def get_review_queue() -> list[Article]:
    """Get articles pending editorial review."""
    return Article.query.filter_by(status=Article.STATUS_PENDING_REVIEW)\
        .order_by(Article.created_at.asc()).all()


def count_pending_articles() -> dict:
    """Count articles in each pending state."""
    review_count = Article.query.filter_by(status=Article.STATUS_PENDING_REVIEW).count()
    audit_count = Article.query.filter_by(status=Article.STATUS_PENDING_AUDIT).count()
    return {
        "pending_review": review_count,
        "pending_audit": audit_count,
        "total_pending": review_count + audit_count,
    }