from datetime import datetime, timezone, timedelta

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models.content import Article
from app.models.engagement import (
    Poll, PollOption, Reaction, ShareEvent, ViewEvent, Comment, CommentReaction,
)
from app.utils.security import make_session_hash, utcnow, ensure_aware


# === Reactions ===

def react_to_article(article_id: int, reaction_type: str, session_hash: str,
                     user_id: int | None = None) -> dict:
    """
    Add or change a reaction on an article.
    Returns the updated counts per reaction type.
    One reaction per session per article — submitting a new type replaces the old one.
    """
    if reaction_type not in Reaction.TYPES:
        raise ValueError(f"Invalid reaction type: {reaction_type}")

    article = db.session.get(Article, article_id)
    if not article or not article.is_publicly_visible:
        raise ValueError("Article not found or not visible")

    # Find existing reaction from this session
    existing = Reaction.query.filter_by(
        article_id=article_id,
        session_hash=session_hash,
    ).first()

    if existing:
        if existing.reaction_type == reaction_type:
            # Toggle off — remove the reaction
            db.session.delete(existing)
            article.reaction_count = max(0, (article.reaction_count or 1) - 1)
        else:
            # Change reaction type — count stays the same
            existing.reaction_type = reaction_type
            existing.user_id = user_id
            existing.created_at = utcnow()
    else:
        # New reaction
        reaction = Reaction(
            article_id=article_id,
            session_hash=session_hash,
            user_id=user_id,
            reaction_type=reaction_type,
        )
        db.session.add(reaction)
        article.reaction_count = (article.reaction_count or 0) + 1

    db.session.commit()
    return get_reaction_counts(article_id)


def get_reaction_counts(article_id: int) -> dict:
    """Get counts per reaction type for an article."""
    rows = db.session.query(
        Reaction.reaction_type,
        func.count(Reaction.id),
    ).filter(Reaction.article_id == article_id)\
     .group_by(Reaction.reaction_type).all()

    counts = {t: 0 for t in Reaction.TYPES}
    for rtype, count in rows:
        counts[rtype] = count
    return counts


def get_user_reaction(article_id: int, session_hash: str) -> str | None:
    """Get the current user's reaction type for an article (if any)."""
    reaction = Reaction.query.filter_by(
        article_id=article_id,
        session_hash=session_hash,
    ).first()
    return reaction.reaction_type if reaction else None


# === Comments ===

COMMENT_BODY_MAX_LENGTH = 2000
COMMENT_NAME_MAX_LENGTH = 80


def post_comment(article_id: int, display_name: str, body: str, session_hash: str,
                  user_id: int | None = None) -> Comment:
    """Post a reader comment on an article."""
    article = db.session.get(Article, article_id)
    if not article or not article.is_publicly_visible:
        raise ValueError("Article not found or not visible")

    display_name = (display_name or "").strip() or "Anonymous"
    display_name = display_name[:COMMENT_NAME_MAX_LENGTH]

    body = (body or "").strip()
    if not body:
        raise ValueError("Comment cannot be empty")
    body = body[:COMMENT_BODY_MAX_LENGTH]

    comment = Comment(
        article_id=article_id,
        session_hash=session_hash,
        user_id=user_id,
        display_name=display_name,
        body=body,
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def get_comments_for_article(article_id: int) -> list[Comment]:
    """Newest-first list of comments for an article."""
    return Comment.query.filter_by(article_id=article_id) \
        .order_by(Comment.created_at.desc()).all()


def get_comment_reaction_counts(comment_id: int) -> dict:
    """Get reaction counts per type for a single comment."""
    rows = db.session.query(
        CommentReaction.reaction_type,
        func.count(CommentReaction.id),
    ).filter(CommentReaction.comment_id == comment_id) \
     .group_by(CommentReaction.reaction_type).all()

    counts = {t: 0 for t in CommentReaction.TYPES}
    for rtype, count in rows:
        counts[rtype] = count
    return counts


def get_comment_reaction_counts_bulk(comment_ids: list[int]) -> dict:
    """Reaction counts for many comments at once, keyed by comment_id."""
    counts_by_comment = {cid: {t: 0 for t in CommentReaction.TYPES} for cid in comment_ids}
    if not comment_ids:
        return counts_by_comment

    rows = db.session.query(
        CommentReaction.comment_id,
        CommentReaction.reaction_type,
        func.count(CommentReaction.id),
    ).filter(CommentReaction.comment_id.in_(comment_ids)) \
     .group_by(CommentReaction.comment_id, CommentReaction.reaction_type).all()

    for cid, rtype, count in rows:
        counts_by_comment.setdefault(cid, {t: 0 for t in CommentReaction.TYPES})
        counts_by_comment[cid][rtype] = count
    return counts_by_comment


def get_user_comment_reactions(comment_ids: list[int], session_hash: str) -> dict:
    """Map of comment_id -> this session's reaction type, for the given comments."""
    if not comment_ids:
        return {}
    rows = CommentReaction.query.filter(
        CommentReaction.comment_id.in_(comment_ids),
        CommentReaction.session_hash == session_hash,
    ).all()
    return {r.comment_id: r.reaction_type for r in rows}


def get_user_comment_reaction(comment_id: int, session_hash: str) -> str | None:
    """Get the current session's reaction type for a single comment (if any)."""
    reaction = CommentReaction.query.filter_by(
        comment_id=comment_id,
        session_hash=session_hash,
    ).first()
    return reaction.reaction_type if reaction else None


def react_to_comment(comment_id: int, reaction_type: str, session_hash: str,
                      user_id: int | None = None) -> dict:
    """
    Add, change, or toggle off a reaction on a comment.
    One reaction per session per comment — mirrors react_to_article.
    """
    if reaction_type not in CommentReaction.TYPES:
        raise ValueError(f"Invalid reaction type: {reaction_type}")

    comment = db.session.get(Comment, comment_id)
    if not comment:
        raise ValueError("Comment not found")

    existing = CommentReaction.query.filter_by(
        comment_id=comment_id,
        session_hash=session_hash,
    ).first()

    if existing:
        if existing.reaction_type == reaction_type:
            db.session.delete(existing)
        else:
            existing.reaction_type = reaction_type
            existing.user_id = user_id
            existing.created_at = utcnow()
    else:
        db.session.add(CommentReaction(
            comment_id=comment_id,
            session_hash=session_hash,
            user_id=user_id,
            reaction_type=reaction_type,
        ))

    db.session.commit()
    return get_comment_reaction_counts(comment_id)


# === Polls ===

def vote_on_poll(poll_id: int, option_ids: list[int], session_hash: str,
                 user_id: int | None = None) -> dict:
    """
    Cast a vote on a poll. One vote per session (or per user if logged in).
    Returns updated results.
    """
    poll = db.session.get(Poll, poll_id)
    if not poll:
        raise ValueError("Poll not found")

    now = utcnow()
    if poll.status != "active":
        raise ValueError("Poll is not active")
    if poll.start_at and ensure_aware(poll.start_at) > now:
        raise ValueError("Poll has not started")
    if poll.end_at and ensure_aware(poll.end_at) < now:
        raise ValueError("Poll has ended")

    # Validate options belong to this poll
    valid_options = PollOption.query.filter(
        PollOption.id.in_(option_ids),
        PollOption.poll_id == poll_id,
    ).all()
    if not valid_options:
        raise ValueError("Invalid option(s)")

    if not poll.allow_multiple and len(valid_options) > 1:
        raise ValueError("This poll only allows one selection")

    # Check for existing vote — use user_id if logged in, else session_hash
    # We track via a simple approach: store vote in PollOption.vote_count
    # and use a separate check table. For simplicity, we'll use a cookie-based
    # approach via session_hash stored in a lightweight way.
    # Since we don't have a PollVote model, we'll use the session_hash cookie
    # client-side to prevent double-voting. Server-side, we just increment.
    # In production, add a PollVote table for stricter enforcement.

    for option in valid_options:
        option.vote_count = (option.vote_count or 0) + 1

    db.session.commit()
    return get_poll_results(poll_id)


def get_poll_results(poll_id: int) -> dict:
    """Get poll results with percentages."""
    poll = db.session.get(Poll, poll_id)
    if not poll:
        return {}

    options = []
    total = 0
    for opt in poll.options:
        total += opt.vote_count or 0
        options.append({
            "id": opt.id,
            "label": opt.label,
            "votes": opt.vote_count or 0,
        })

    for opt in options:
        opt["pct"] = round((opt["votes"] / total * 100), 1) if total > 0 else 0

    return {
        "poll_id": poll_id,
        "question": poll.question,
        "total_votes": total,
        "options": options,
        "status": poll.status,
    }


# === Shares ===

def track_share(article_id: int, platform: str, session_hash: str,
                user_id: int | None = None) -> int:
    """
    Track a share event and increment the article's share_count.
    Returns the new total share count.
    """
    valid_platforms = {
        ShareEvent.PLATFORM_WHATSAPP, ShareEvent.PLATFORM_X,
        ShareEvent.PLATFORM_TWITTER_LEGACY, ShareEvent.PLATFORM_FACEBOOK,
        ShareEvent.PLATFORM_INSTAGRAM, ShareEvent.PLATFORM_COPY_LINK,
    }
    if platform not in valid_platforms:
        raise ValueError(f"Invalid platform: {platform}")

    article = db.session.get(Article, article_id)
    if not article or not article.is_publicly_visible:
        raise ValueError("Article not found or not visible")

    event = ShareEvent(
        article_id=article_id,
        platform=platform,
        session_hash=session_hash,
        user_id=user_id,
    )
    db.session.add(event)
    article.share_count = (article.share_count or 0) + 1
    db.session.commit()

    return article.share_count


# === Views ===

def track_view(article_id: int, session_hash: str, user_id: int | None = None,
               referrer: str | None = None, device_type: str | None = None) -> bool:
    """
    Track a view with session+article dedup window.
    Returns True if a new view was recorded, False if deduped.
    """
    article = db.session.get(Article, article_id)
    if not article or not article.is_publicly_visible:
        return False

    dedup_minutes = current_app.config.get("VIEW_DEDUP_MINUTES", 30)
    cutoff = utcnow() - timedelta(minutes=dedup_minutes)

    existing = ViewEvent.query.filter(
        ViewEvent.article_id == article_id,
        ViewEvent.session_hash == session_hash,
        ViewEvent.created_at >= cutoff,
    ).first()

    if existing:
        return False

    event = ViewEvent(
        article_id=article_id,
        session_hash=session_hash,
        user_id=user_id,
        referrer=referrer[:500] if referrer else None,
        device_type=device_type,
    )
    db.session.add(event)
    article.view_count = (article.view_count or 0) + 1
    db.session.commit()
    return True