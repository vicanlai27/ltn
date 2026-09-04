from flask import Blueprint, jsonify, request, Response, send_file, url_for
from datetime import datetime, timezone
from flask_login import current_user
from io import BytesIO

from app.extensions import csrf, limiter, db
from app.models.content import Article
from app.models.media import Gallery, GalleryImage, Video, PodcastEpisode
from app.models.engagement import Poll
from app.repositories.homepage import trending_now
from app.services.engagement_service import (
    react_to_article, get_reaction_counts, get_user_reaction,
    vote_on_poll, get_poll_results,
    track_share, track_view,
    react_to_comment, get_comment_reaction_counts, get_user_comment_reaction,
)
from app.services.share_card_service import generate_instagram_card
from app.services import youtube_service
from app.utils.security import make_session_hash, ensure_aware

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# Exempt all API routes from CSRF (they use session hash + rate limiting instead)
csrf.exempt(api_bp)


def _get_session_hash() -> str:
    return make_session_hash()


def _get_user_id() -> int | None:
    return current_user.id if current_user.is_authenticated else None


# === Health ===

@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "phase": 7})


# === Reactions ===

@api_bp.route("/articles/<int:article_id>/reactions", methods=["GET"])
def get_reactions(article_id):
    """Get reaction counts and current user's reaction."""
    session_hash = _get_session_hash()
    counts = get_reaction_counts(article_id)
    user_reaction = get_user_reaction(article_id, session_hash)
    return jsonify({
        "counts": counts,
        "user_reaction": user_reaction,
    })


@api_bp.route("/articles/<int:article_id>/reactions", methods=["POST"])
@limiter.limit("30 per minute")
def post_reaction(article_id):
    """Add or change a reaction."""
    data = request.get_json(silent=True) or {}
    reaction_type = data.get("type")
    if not reaction_type:
        return jsonify({"error": "Missing reaction type"}), 400

    session_hash = _get_session_hash()
    user_id = _get_user_id()

    try:
        counts = react_to_article(article_id, reaction_type, session_hash, user_id)
        user_reaction = get_user_reaction(article_id, session_hash)
        return jsonify({
            "counts": counts,
            "user_reaction": user_reaction,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# === Comment Reactions ===

@api_bp.route("/comments/<int:comment_id>/reactions", methods=["POST"])
@limiter.limit("30 per minute")
def post_comment_reaction(comment_id):
    """Add, change, or toggle off a reaction on a comment."""
    data = request.get_json(silent=True) or {}
    reaction_type = data.get("type")
    if not reaction_type:
        return jsonify({"error": "Missing reaction type"}), 400

    session_hash = _get_session_hash()
    user_id = _get_user_id()

    try:
        counts = react_to_comment(comment_id, reaction_type, session_hash, user_id)
        user_reaction = get_user_comment_reaction(comment_id, session_hash)
        return jsonify({"counts": counts, "user_reaction": user_reaction})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# === Polls ===

@api_bp.route("/polls/<int:poll_id>", methods=["GET"])
def get_poll(poll_id):
    """Get poll results."""
    results = get_poll_results(poll_id)
    if not results:
        return jsonify({"error": "Poll not found"}), 404
    return jsonify(results)


@api_bp.route("/polls/<int:poll_id>/vote", methods=["POST"])
@limiter.limit("10 per minute")
def vote_poll(poll_id):
    """Cast a vote on a poll."""
    data = request.get_json(silent=True) or {}
    option_ids = data.get("option_ids", [])
    if not option_ids:
        return jsonify({"error": "No options selected"}), 400

    if not isinstance(option_ids, list):
        option_ids = [option_ids]

    session_hash = _get_session_hash()
    user_id = _get_user_id()

    try:
        results = vote_on_poll(poll_id, option_ids, session_hash, user_id)
        return jsonify(results)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# === Shares ===

@api_bp.route("/articles/<int:article_id>/share", methods=["POST"])
@limiter.limit("20 per minute")
def track_share_event(article_id):
    """Track a share event."""
    data = request.get_json(silent=True) or {}
    platform = data.get("platform")
    if not platform:
        return jsonify({"error": "Missing platform"}), 400

    session_hash = _get_session_hash()
    user_id = _get_user_id()

    try:
        new_count = track_share(article_id, platform, session_hash, user_id)
        return jsonify({"share_count": new_count})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# === Views ===

@api_bp.route("/articles/<int:article_id>/view", methods=["POST"])
@limiter.limit("60 per minute")
def track_view_event(article_id):
    """Track a view event (called client-side on article load)."""
    session_hash = _get_session_hash()
    user_id = _get_user_id()
    referrer = request.headers.get("Referer")
    device_type = request.headers.get("X-Device-Type")

    recorded = track_view(article_id, session_hash, user_id, referrer, device_type)
    return jsonify({"recorded": recorded})


# === Trending ===

@api_bp.route("/trending")
def get_trending():
    """Get trending articles."""
    limit = request.args.get("limit", 10, type=int)
    limit = min(limit, 50)
    articles = trending_now(limit=limit)
    return jsonify({
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "slug": a.slug,
                "url": request.host_url.rstrip("/") + f"/news/{a.slug}",
                "category": a.category.name if a.category else None,
                "view_count": a.view_count,
                "reaction_count": a.reaction_count,
                "share_count": a.share_count,
            }
            for a in articles
        ]
    })


# === Media ===

def _published_at_iso(value):
    return value.isoformat() if value else None


@api_bp.route("/media/videos")
def media_videos():
    """Return a paginated list of published locally hosted videos."""
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 12, type=int), 1), 50)
    pagination = Video.query.filter(
        Video.published_at.isnot(None),
        Video.published_at <= db.func.now(),
    ).order_by(Video.published_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [{
            "id": v.id, "title": v.title, "slug": v.slug,
            "description": v.description, "thumbnail": v.thumbnail,
            "duration": v.duration, "published_at": _published_at_iso(v.published_at),
            "view_count": v.view_count or 0,
            "url": request.host_url.rstrip("/") + f"/video/{v.slug}",
        } for v in pagination.items],
        "page": pagination.page, "per_page": pagination.per_page,
        "pages": pagination.pages, "total": pagination.total,
    })


@api_bp.route("/media/galleries")
def media_galleries():
    """Return a paginated list of published galleries with image metadata."""
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 12, type=int), 1), 50)
    pagination = Gallery.query.filter(
        Gallery.published_at.isnot(None),
        Gallery.published_at <= db.func.now(),
    ).order_by(Gallery.published_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [{
            "id": g.id, "title": g.title, "slug": g.slug,
            "description": g.description, "cover_image": g.cover_image,
            "published_at": _published_at_iso(g.published_at),
            "image_count": len(g.images),
            "url": request.host_url.rstrip("/") + f"/campus/gallery/{g.slug}",
        } for g in pagination.items],
        "page": pagination.page, "per_page": pagination.per_page,
        "pages": pagination.pages, "total": pagination.total,
    })


@api_bp.route("/media/galleries/<slug>")
def media_gallery(slug):
    """Return one published gallery and its ordered image metadata."""
    gallery = Gallery.query.filter_by(slug=slug).first()
    if not gallery or not gallery.published_at or ensure_aware(gallery.published_at) > datetime.now(timezone.utc):
        return jsonify({"error": "Gallery not found"}), 404
    return jsonify({
        "id": gallery.id, "title": gallery.title, "slug": gallery.slug,
        "description": gallery.description, "cover_image": gallery.cover_image,
        "published_at": _published_at_iso(gallery.published_at),
        "images": [{
            "id": image.id, "image": request.host_url.rstrip("/") + url_for("media.gallery_image", image_id=image.id), "alt_text": image.alt_text,
            "caption": image.caption, "display_order": image.display_order,
        } for image in gallery.images],
        "url": request.host_url.rstrip("/") + f"/campus/gallery/{gallery.slug}",
    })


@api_bp.route("/media/podcasts")
def media_podcasts():
    """Return a paginated list of published podcast episodes."""
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 12, type=int), 1), 50)
    pagination = PodcastEpisode.query.filter(
        PodcastEpisode.published_at.isnot(None),
        PodcastEpisode.published_at <= db.func.now(),
    ).order_by(PodcastEpisode.published_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [{
            "id": ep.id, "title": ep.title, "slug": ep.slug,
            "description": ep.description, "cover_image": ep.cover_image,
            "audio_url": ep.audio_url, "duration": ep.duration,
            "episode_number": ep.episode_number,
            "published_at": _published_at_iso(ep.published_at),
            "url": request.host_url.rstrip("/") + f"/podcast/{ep.slug}",
        } for ep in pagination.items],
        "page": pagination.page, "per_page": pagination.per_page,
        "pages": pagination.pages, "total": pagination.total,
    })


@api_bp.route("/media/youtube")
def media_youtube():
    """Return the cached/latest public YouTube channel uploads."""
    limit = min(max(request.args.get("limit", 12, type=int), 1), 24)
    return jsonify({"videos": youtube_service.get_latest_videos(limit=limit)})


# === Lavisco TV (YouTube live status) ===

@api_bp.route("/tv/live-status")
@limiter.limit("60 per minute")
def tv_live_status():
    """
    Polled by the homepage and /tv page to flip on the live banner/player
    the moment Lavisco TV goes live on YouTube, without a full page reload.
    Backed by a short server-side cache, so polling this is cheap.
    """
    return jsonify(youtube_service.get_live_status())


# === Instagram Share Card ===

@api_bp.route("/articles/<int:article_id>/share-card")
@limiter.limit("30 per minute")
def article_share_card(article_id):
    """Generate an Instagram-ready share card image."""
    article = db.session.get(Article, article_id)
    if not article or not article.is_publicly_visible:
        return jsonify({"error": "Article not found"}), 404

    size = request.args.get("size", "square")
    if size not in ("square", "portrait"):
        size = "square"

    try:
        image_bytes = generate_instagram_card(article, size=size)
        return send_file(
            BytesIO(image_bytes),
            mimetype="image/png",
            as_attachment=True,
            download_name=f"lavisco-{article.slug}-{size}.png",
        )
    except Exception as e:
        return jsonify({"error": f"Card generation failed: {str(e)}"}), 500
