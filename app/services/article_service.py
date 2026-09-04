"""
Article service — read + write operations.
Combines Phase 4 (public reading, view tracking) with Phase 6 (editorial workflow).
"""
from datetime import datetime, timezone, timedelta

from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.models.content import Article, Category, Tag, TagRelation, ArticleImage
from app.models.engagement import ViewEvent, Poll, PollOption
from app.models.system import ActivityLog
from app.models.user import User
from app.repositories.articles import get_public_article_by_slug
from app.services.activity_service import log_activity
from app.utils.security import slugify, utcnow


# ============================================================
# READ operations (Phase 4)
# ============================================================

def get_article_for_reading(slug: str) -> Article | None:
    """Fetch a publicly visible article by slug."""
    return get_public_article_by_slug(slug)


def increment_view(
    article: Article,
    session_hash: str,
    user_id: int | None,
    referrer: str | None,
    device_type: str | None,
    dedup_minutes: int = 30,
) -> bool:
    """
    Record a view event with session+article dedup window.
    Returns True if a new view was recorded, False if deduped.
    """
    if not article.is_publicly_visible:
        return False

    cutoff = utcnow() - timedelta(minutes=dedup_minutes)
    existing = ViewEvent.query.filter(
        ViewEvent.article_id == article.id,
        ViewEvent.session_hash == session_hash,
        ViewEvent.created_at >= cutoff,
    ).first()

    if existing:
        return False

    event = ViewEvent(
        article_id=article.id,
        session_hash=session_hash,
        user_id=user_id,
        referrer=referrer[:500] if referrer else None,
        device_type=device_type,
    )
    db.session.add(event)
    article.view_count = (article.view_count or 0) + 1
    db.session.commit()
    return True


def estimate_reading_time(body: str) -> int:
    """Average reading speed: 225 words per minute, minimum 1."""
    if not body:
        return 1
    words = len(body.split())
    return max(1, round(words / 225))


# ============================================================
# WRITE operations (Phase 6)
# ============================================================

def create_article(data: dict, author_id: int) -> Article:
    """Create a new article with tags."""
    article = Article(
        title=data["title"],
        slug=generate_unique_slug(data["title"]),
        excerpt=data.get("excerpt"),
        body=data["body"],
        featured_image=data.get("featured_image"),
        featured_image_alt=data.get("featured_image_alt"),
        image_caption=data.get("image_caption"),
        youtube_video_id=data.get("youtube_video_id"),
        special_edition_id=data.get("special_edition_id"),
        category_id=data.get("category_id"),
        author_id=author_id,
        content_type=data.get("content_type", Article.TYPE_NEWS),
        status=Article.STATUS_DRAFT,
        is_campus=data.get("is_campus", False),
        campus_section=data.get("campus_section"),
        house_id=data.get("house_id"),
        club_id=data.get("club_id"),
        audio_url=data.get("audio_url"),
        audio_duration=data.get("audio_duration"),
    )
    db.session.add(article)
    db.session.commit()

    if data.get("tags"):
        _set_tags(article, data["tags"])

    log_activity(author_id, "article.create", "article", article.id, f"Created '{article.title}'")
    return article


def update_article(article: Article, data: dict) -> Article:
    """Update an article's fields and tags."""
    for field in [
        "title", "excerpt", "body", "featured_image", "featured_image_alt",
        "image_caption", "youtube_video_id", "special_edition_id", "category_id", "content_type", "is_campus",
        "campus_section", "house_id", "club_id", "audio_url", "audio_duration",
    ]:
        if field in data:
            setattr(article, field, data[field])

    if "title" in data and data["title"] != article.title:
        article.slug = generate_unique_slug(data["title"])

    if "tags" in data:
        _set_tags(article, data["tags"])

    article.updated_at = utcnow()
    db.session.commit()

    log_activity(current_user.id, "article.update", "article", article.id, f"Updated '{article.title}'")
    return article


def submit_for_review(article: Article) -> Article:
    """Submit article for editorial review."""
    if article.status not in (Article.STATUS_DRAFT, Article.STATUS_REJECTED):
        raise ValueError(f"Cannot submit article in status '{article.status}'")

    article.status = Article.STATUS_PENDING_REVIEW
    db.session.commit()
    log_activity(current_user.id, "article.submit", "article", article.id)
    from app.services.notification_service import notify_roles
    notify_roles(User.STAFF_ROLES, "article_submitted", "New article submitted for review", article.title, f"/admin/articles/{article.id}/edit", exclude_user_id=article.author_id)
    return article


def approve_for_audit(article: Article, reviewer_id: int) -> Article:
    """Editor approves article -> moves to pending_audit queue."""
    if article.status != Article.STATUS_PENDING_REVIEW:
        raise ValueError(f"Cannot approve article in status '{article.status}'")

    if reviewer_id == article.author_id:
        raise PermissionError("Authors cannot approve their own articles")

    article.status = Article.STATUS_PENDING_AUDIT
    db.session.commit()
    log_activity(reviewer_id, "article.approve", "article", article.id, "Approved for audit")
    from app.services.notification_service import notify_user
    if article.author_id:
        notify_user(article.author_id, "article_approved", "Article approved for audit", article.title, f"/newsroom/articles/{article.id}/edit")
    return article


def reject_article(article: Article, reviewer_id: int, notes: str) -> Article:
    """Editor rejects article -> returns to rejected status."""
    if article.status not in (Article.STATUS_PENDING_REVIEW, Article.STATUS_PENDING_AUDIT):
        raise ValueError(f"Cannot reject article in status '{article.status}'")

    article.status = Article.STATUS_REJECTED
    article.audit_notes = notes
    db.session.commit()
    log_activity(reviewer_id, "article.reject", "article", article.id, notes)
    return article


def audit_approve(article: Article, auditor_id: int) -> Article:
    """Final audit approval -> publishes the article."""
    if article.status != Article.STATUS_PENDING_AUDIT:
        raise ValueError(f"Cannot audit article in status '{article.status}'")

    if auditor_id == article.author_id:
        raise PermissionError("Authors cannot audit their own articles")

    approval_log = ActivityLog.query.filter_by(
        action="article.approve",
        target_type="article",
        target_id=article.id,
    ).order_by(ActivityLog.created_at.desc()).first()

    if approval_log and approval_log.actor_id == auditor_id:
        raise PermissionError("Cannot audit an article you approved for review")

    article.status = Article.STATUS_PUBLISHED
    article.is_audited = True
    article.audited_by_id = auditor_id
    article.audited_at = utcnow()
    article.published_at = article.published_at or utcnow()
    db.session.commit()

    log_activity(auditor_id, "article.audit.approve", "article", article.id, "Audit approved")
    from app.services.notification_service import notify_user
    if article.author_id:
        notify_user(article.author_id, "article_published", "Article published", article.title, f"/news/{article.slug}")
    return article


def audit_reject(article: Article, auditor_id: int, notes: str) -> Article:
    """Audit rejection -> returns to rejected status."""
    if article.status != Article.STATUS_PENDING_AUDIT:
        raise ValueError(f"Cannot audit article in status '{article.status}'")

    if auditor_id == article.author_id:
        raise PermissionError("Authors cannot audit their own articles")

    approval_log = ActivityLog.query.filter_by(
        action="article.approve",
        target_type="article",
        target_id=article.id,
    ).order_by(ActivityLog.created_at.desc()).first()

    if approval_log and approval_log.actor_id == auditor_id:
        raise PermissionError("Cannot audit an article you approved for review")

    article.status = Article.STATUS_REJECTED
    article.audit_notes = notes
    db.session.commit()

    log_activity(auditor_id, "article.audit.reject", "article", article.id, notes)
    return article


def delete_article(article: Article) -> None:
    """
    Permanently delete an article.

    Tag relations, reactions, share events, and view events cascade via the
    ORM relationships on Article. Placement slots aren't a cascaded
    relationship, so they're cleared explicitly to avoid leaving stale
    homepage placements pointing at a deleted article.
    """
    from app.models.editorial import PlacementSlot

    title = article.title
    article_id = article.id

    PlacementSlot.query.filter_by(article_id=article.id).delete()
    db.session.delete(article)
    db.session.commit()

    log_activity(current_user.id, "article.delete", "article", article_id, f"Deleted '{title}'")


def schedule_article(article: Article, publish_at: datetime) -> Article:
    """Schedule article for future publication."""
    if article.status not in (Article.STATUS_DRAFT, Article.STATUS_PENDING_REVIEW):
        raise ValueError(f"Cannot schedule article in status '{article.status}'")

    article.status = Article.STATUS_SCHEDULED
    article.published_at = publish_at
    db.session.commit()
    log_activity(current_user.id, "article.schedule", "article", article.id, f"Scheduled for {publish_at}")
    return article


def add_gallery_images(article: Article, image_paths: list[str]) -> list[ArticleImage]:
    """
    Attach additional gallery images to an article (appended after any
    that already exist), so readers can navigate through them alongside
    the single featured image.
    """
    if not image_paths:
        return []

    start_order = (
        db.session.query(db.func.coalesce(db.func.max(ArticleImage.display_order), -1))
        .filter(ArticleImage.article_id == article.id)
        .scalar()
    ) + 1

    created = []
    for i, path in enumerate(image_paths):
        img = ArticleImage(
            article_id=article.id,
            image=path,
            display_order=start_order + i,
        )
        db.session.add(img)
        created.append(img)

    db.session.commit()
    return created


def remove_gallery_image(article: Article, image_id: int) -> None:
    """Remove a single gallery image (and its file) from an article."""
    from app.services.media_service import delete_upload

    image = next((img for img in article.images if img.id == image_id), None)
    if not image:
        raise ValueError("Image not found on this article")

    delete_upload(image.image)
    db.session.delete(image)
    db.session.commit()


def set_article_poll(article: Article, question: str, description: str,
                      allow_multiple: bool, option_labels: list[str]) -> Poll:
    """
    Attach a poll to an article, or replace its question/options if it
    already has one. Goes live (status='active') immediately — there's
    no separate scheduling step for article-attached polls.
    """
    question = (question or "").strip()
    labels = [l.strip() for l in option_labels if l and l.strip()]

    if not question or len(labels) < 2:
        raise ValueError("A poll needs a question and at least 2 options")

    poll = article.poll
    if not poll:
        poll = Poll(article_id=article.id, status="active")
        db.session.add(poll)
    else:
        # Replacing options wholesale is only safe pre-launch; this is a
        # simple "authors edit their own poll" flow, not a full lifecycle.
        for opt in list(poll.options):
            db.session.delete(opt)

    poll.question = question
    poll.description = (description or "").strip() or None
    poll.allow_multiple = allow_multiple
    poll.status = "active"

    for i, label in enumerate(labels):
        db.session.add(PollOption(poll=poll, label=label, display_order=i))

    db.session.commit()
    return poll


def remove_article_poll(article: Article) -> None:
    """Detach and delete an article's poll, if any."""
    if article.poll:
        db.session.delete(article.poll)
        db.session.commit()


# ============================================================
# Helpers
# ============================================================

def generate_unique_slug(title: str) -> str:
    """Generate a unique slug for an article."""
    base = slugify(title)
    candidate = base
    counter = 2
    while Article.query.filter_by(slug=candidate).first():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _set_tags(article: Article, tag_names: list[str]):
    """Set article tags by name, creating new tags as needed."""
    TagRelation.query.filter_by(article_id=article.id).delete()

    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name, slug=slugify(name))
            db.session.add(tag)
            db.session.flush()
        db.session.add(TagRelation(article_id=article.id, tag_id=tag.id))

    db.session.commit()
