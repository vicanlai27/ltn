"""One-off seed script: publishes sample Gallery / Video / PodcastEpisode
records with real accompanying image/video/audio files, so the Media hub,
Videos, Shorts, and Podcasts sections have visible published content.

Run once with: python3 seed_media.py
Safe to re-run: it skips creation if matching slugs already exist.
"""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from werkzeug.datastructures import FileStorage

from app import create_app
from app.extensions import db
from app.models.content import Category
from app.models.media import Gallery, GalleryImage, PodcastEpisode, Video
from app.models.user import User
from app.services.media_service import save_upload
from app.utils.security import slugify

ASSETS = Path("/home/claude/seed_assets")
NOW = datetime.now(timezone.utc)


def _fs(path: Path, content_type: str) -> FileStorage:
    return FileStorage(stream=BytesIO(path.read_bytes()), filename=path.name, content_type=content_type)


def main():
    app = create_app()
    with app.app_context():
        author = User.query.filter_by(username="author").first() or User.query.first()
        sports_cat = Category.query.filter(Category.name.ilike("sports")).first()

        # --- Gallery -------------------------------------------------
        if not Gallery.query.filter_by(slug="campus-life-2026").first():
            gallery = Gallery(
                title="Campus Life 2026",
                slug="campus-life-2026",
                description="A photo look back at campus life this term — events, sports, and everyday moments.",
                published_at=NOW - timedelta(days=1),
            )
            gallery.cover_image = save_upload(_fs(ASSETS / "gallery_1.jpg", "image/jpeg"), "galleries")
            db.session.add(gallery)
            db.session.flush()

            captions = ["Campus Life", "Sports Day", "Science Fair", "Graduation"]
            for i, name in enumerate(["gallery_1.jpg", "gallery_2.jpg", "gallery_3.jpg", "gallery_4.jpg"]):
                path = save_upload(_fs(ASSETS / name, "image/jpeg"), "galleries")
                db.session.add(GalleryImage(
                    gallery_id=gallery.id, image=path,
                    alt_text=captions[i], caption=captions[i], display_order=i,
                ))
            db.session.commit()
            print("Created gallery:", gallery.slug)
        else:
            print("Gallery already exists, skipping")

        # --- Video -----------------------------------------------------
        if not Video.query.filter_by(slug="campus-roundup").first():
            video = Video(
                title="Campus Roundup — This Week",
                slug="campus-roundup",
                description="A quick roundup of what happened around campus this week.",
                video_url=save_upload(_fs(ASSETS / "video_1.mp4", "video/mp4"), "videos"),
                thumbnail=save_upload(_fs(ASSETS / "video_1_thumb.jpg", "image/jpeg"), "videos"),
                duration=8,
                category_id=sports_cat.id if sports_cat else None,
                author_id=author.id if author else None,
                published_at=NOW - timedelta(hours=6),
            )
            db.session.add(video)
            db.session.commit()
            print("Created video:", video.slug)
        else:
            print("Video already exists, skipping")

        # --- Short -------------------------------------------------
        if not Video.query.filter_by(slug="around-campus-short").first():
            short = Video(
                title="Around Campus",
                slug="around-campus-short",
                description="A quick vertical look around campus.",
                video_url=save_upload(_fs(ASSETS / "short_1.mp4", "video/mp4"), "videos"),
                thumbnail=save_upload(_fs(ASSETS / "short_1_thumb.jpg", "image/jpeg"), "videos"),
                duration=6,
                author_id=author.id if author else None,
                published_at=NOW - timedelta(hours=2),
            )
            db.session.add(short)
            db.session.commit()
            print("Created short:", short.slug)
        else:
            print("Short already exists, skipping")

        # --- Podcast -----------------------------------------------
        if not PodcastEpisode.query.filter_by(slug="lavisco-voices-ep1").first():
            episode = PodcastEpisode(
                title="Lavisco Voices — Episode 1: Welcome Back",
                slug="lavisco-voices-ep1",
                description="Kicking off the new season of Lavisco Voices with a look at what's ahead this term.",
                audio_url=save_upload(_fs(ASSETS / "podcast_1.mp3", "audio/mpeg"), "podcasts"),
                cover_image=save_upload(_fs(ASSETS / "podcast_1_cover.jpg", "image/jpeg"), "podcasts"),
                duration=45,
                episode_number=1,
                published_at=NOW - timedelta(days=2),
            )
            db.session.add(episode)
            db.session.commit()
            print("Created podcast episode:", episode.slug)
        else:
            print("Podcast episode already exists, skipping")


if __name__ == "__main__":
    main()
