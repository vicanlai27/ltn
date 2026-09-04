from datetime import datetime, timezone

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from app.models.media import Gallery, GalleryImage, PodcastEpisode, Video
from app.services import youtube_service
from app.services.storage_service import get_public_url
from app.utils.security import ensure_aware

media_bp = Blueprint("media", __name__)


# === Media Hub ===

@media_bp.route("/media")
def media_index():
    """Unified public media hub for locally managed media."""
    now = datetime.now(timezone.utc)
    galleries = Gallery.query.filter(
        Gallery.published_at.isnot(None),
        Gallery.published_at <= now,
    ).order_by(Gallery.published_at.desc()).limit(6).all()
    videos = Video.query.filter(
        Video.published_at.isnot(None),
        Video.published_at <= now,
    ).order_by(Video.published_at.desc()).limit(6).all()
    podcasts = PodcastEpisode.query.filter(
        PodcastEpisode.published_at.isnot(None),
        PodcastEpisode.published_at <= now,
    ).order_by(PodcastEpisode.published_at.desc()).limit(6).all()
    shorts = Video.query.filter(
        Video.published_at.isnot(None),
        Video.published_at <= now,
        Video.duration.isnot(None),
        Video.duration <= 90,
    ).order_by(Video.published_at.desc()).limit(6).all()
    return render_template(
        "media/index.html",
        galleries=galleries,
        videos=videos,
        podcasts=podcasts,
        shorts=shorts,
    )


# === Galleries ===

def _gallery_is_published(gallery) -> bool:
    """Return True only when a gallery has reached its publish time."""
    return bool(
        gallery
        and gallery.published_at
        and ensure_aware(gallery.published_at) <= datetime.now(timezone.utc)
    )


@media_bp.route("/media/gallery-image/<int:image_id>")
def gallery_image(image_id):
    """Redirect to a published gallery image's Supabase Storage URL."""
    image = GalleryImage.query.get_or_404(image_id)
    if not _gallery_is_published(image.gallery) or not image.image:
        abort(404)
    return redirect(get_public_url(image.image), code=302)


@media_bp.route("/media/gallery-cover/<int:gallery_id>")
def gallery_cover(gallery_id):
    """Redirect to a published gallery cover's Supabase Storage URL."""
    gallery = Gallery.query.get_or_404(gallery_id)
    if not _gallery_is_published(gallery) or not gallery.cover_image:
        abort(404)
    return redirect(get_public_url(gallery.cover_image), code=302)


@media_bp.route("/media/gallery/<slug>")
def gallery_show(slug):
    """Backward-compatible public gallery URL.

    Older API responses/bookmarks used /media/gallery/<slug>, while the
    canonical public route is /campus/gallery/<slug>. Keep the alias alive
    for published galleries and return a normal 404 for drafts/non-existent
    galleries rather than exposing unpublished media.
    """
    gallery = Gallery.query.filter_by(slug=slug).first_or_404()
    if not _gallery_is_published(gallery):
        abort(404)
    return redirect(url_for("campus.gallery_show", slug=gallery.slug), code=301)


# === Videos ===

@media_bp.route("/videos")
def videos_feed():
    """Paginated archive of published locally hosted videos."""
    page = request.args.get("page", 1, type=int)
    videos = Video.query.filter(
        Video.published_at.isnot(None),
        Video.published_at <= datetime.now(timezone.utc),
    ).order_by(Video.published_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template("media/videos.html", videos=videos)

@media_bp.route("/video/<slug>")
def video_show(slug):
    video = Video.query.filter_by(slug=slug).first_or_404()
    if not video.published_at or ensure_aware(video.published_at) > datetime.now(timezone.utc):
        abort(404)

    # Track view (simple counter for videos)
    video.view_count = (video.view_count or 0) + 1
    from app.extensions import db
    db.session.commit()

    # Related videos in same category
    related = []
    if video.category_id:
        related = Video.query.filter(
            Video.category_id == video.category_id,
            Video.id != video.id,
            Video.published_at.isnot(None),
            Video.published_at <= datetime.now(timezone.utc),
        ).order_by(Video.published_at.desc()).limit(6).all()

    return render_template("media/video_show.html", video=video, related=related)


# === Shorts ===

@media_bp.route("/shorts")
def shorts_feed():
    """Vertical snap-scroll feed of short-form videos."""
    page = request.args.get("page", 1, type=int)
    shorts = Video.query.filter(
        Video.published_at.isnot(None),
        Video.published_at <= datetime.now(timezone.utc),
        Video.duration.isnot(None),
        Video.duration <= 90,  # Shorts are under 90 seconds
    ).order_by(Video.published_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("media/shorts_feed.html", shorts=shorts)


@media_bp.route("/shorts/<slug>")
def short_show(slug):
    short = Video.query.filter_by(slug=slug).first_or_404()
    if not short.published_at or ensure_aware(short.published_at) > datetime.now(timezone.utc):
        abort(404)

    short.view_count = (short.view_count or 0) + 1
    from app.extensions import db
    db.session.commit()

    # Load more shorts for the feed
    more_shorts = Video.query.filter(
        Video.id != short.id,
        Video.published_at.isnot(None),
        Video.published_at <= datetime.now(timezone.utc),
        Video.duration.isnot(None),
        Video.duration <= 90,
    ).order_by(Video.published_at.desc()).limit(10).all()

    return render_template("media/short_show.html", short=short, more_shorts=more_shorts)


# === Lavisco TV (YouTube channel) ===

@media_bp.route("/tv")
def tv_index():
    """Lavisco TV hub — latest uploads indexed from the YouTube channel,
    with the live stream front and center whenever the channel is live."""
    live = youtube_service.get_live_status()
    videos = youtube_service.get_latest_videos(limit=24)
    return render_template(
        "media/tv_index.html",
        live=live,
        videos=videos,
        youtube_handle=current_app.config.get("YOUTUBE_CHANNEL_HANDLE", "@LAVISCOTV-bm1mp"),
    )


# === Podcasts (Lavisco Voices) ===

@media_bp.route("/podcasts")
def podcast_index():
    """Podcast hub — 'Lavisco Voices' brand."""
    page = request.args.get("page", 1, type=int)
    episodes = PodcastEpisode.query.filter(
        PodcastEpisode.published_at.isnot(None),
        PodcastEpisode.published_at <= datetime.now(timezone.utc),
    ).order_by(PodcastEpisode.published_at.desc()).paginate(page=page, per_page=12, error_out=False)

    latest = episodes.items[0] if episodes.items else None
    return render_template(
        "media/podcast_index.html",
        episodes=episodes,
        latest=latest,
    )


@media_bp.route("/podcast/<slug>")
def podcast_show(slug):
    episode = PodcastEpisode.query.filter_by(slug=slug).first_or_404()
    if not episode.published_at or ensure_aware(episode.published_at) > datetime.now(timezone.utc):
        abort(404)

    # Other episodes
    others = PodcastEpisode.query.filter(
        PodcastEpisode.id != episode.id,
        PodcastEpisode.published_at.isnot(None),
        PodcastEpisode.published_at <= datetime.now(timezone.utc),
    ).order_by(PodcastEpisode.published_at.desc()).limit(8).all()

    return render_template("media/podcast_show.html", episode=episode, others=others)