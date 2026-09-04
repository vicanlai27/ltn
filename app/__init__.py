import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template

from app.config import config_by_name
from app.extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=False,
        static_folder="static",
        template_folder="templates",
    )

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Ensure instance + local-upload-fallback folders exist. Skipped when the
    # filesystem is read-only (e.g. Vercel's serverless runtime) -- uploads
    # in that environment go straight to Supabase Storage and never touch
    # local disk, so a failure here is harmless.
    try:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    _init_extensions(app)
    _register_blueprints(app)
    _register_context_processors(app)
    _register_filters(app)
    _register_performance(app)
    _register_a11y(app)
    _register_error_handlers(app)
    _register_shell_context(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Exempt the JSON API from CSRF (it uses session hash + rate limiting)
    from app.routes.api import api_bp
    csrf.exempt(api_bp)


def _register_blueprints(app: Flask) -> None:
    from app.routes.public import public_bp
    from app.routes.campus import campus_bp
    from app.routes.media import media_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.newsroom import newsroom_bp
    from app.routes.api import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(campus_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(newsroom_bp)
    app.register_blueprint(api_bp)


def _register_context_processors(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        from app.services.theme_service import resolve_active_theme
        from app.services.announcement_service import active_announcements

        theme = resolve_active_theme()
        unread_notifications = 0
        try:
            from flask_login import current_user
            from app.models.notifications import Notification
            if current_user.is_authenticated:
                unread_notifications = Notification.query.filter_by(user_id=current_user.id, read_at=None).count()
        except Exception:
            unread_notifications = 0
        return {
            "site_name": app.config["SITE_NAME"],
            "site_tagline": app.config["SITE_TAGLINE"],
            "site_origin": app.config["SITE_ORIGIN"],
            "current_year": datetime.now(timezone.utc).year,
            "active_theme": theme,
            "active_announcements": active_announcements(),
            "unread_notifications": unread_notifications,
        }

    @app.context_processor
    def inject_nav_categories():
        """Make shared navigation data available to every blueprint."""
        from datetime import datetime, timezone

        from app.models.content import Category
        from app.models.media import PodcastEpisode, Video

        categories = (
            Category.query.filter_by(is_active=True, parent_id=None)
            .order_by(Category.display_order.asc(), Category.name.asc())
            .all()
        )
        now = datetime.now(timezone.utc)
        return {
            "nav_categories": categories,
            "has_shorts": Video.query.filter(
                Video.published_at.isnot(None),
                Video.published_at <= now,
                Video.duration.isnot(None),
                Video.duration <= 90,
            ).first()
            is not None,
            "has_podcasts": PodcastEpisode.query.filter(
                PodcastEpisode.published_at.isnot(None),
                PodcastEpisode.published_at <= now,
            ).first()
            is not None,
        }


def _register_filters(app: Flask) -> None:
    import hashlib

    from app.services.theme_service import render_theme_css

    @app.template_filter("render_theme_css")
    def render_theme_css_filter(theme):
        return render_theme_css(theme)

    @app.template_filter("hash")
    def hash_filter(value):
        return hashlib.md5(
            str(value).encode("utf-8")
        ).hexdigest()[:12]

    from app.services.storage_service import get_public_url

    @app.template_global("media_url")
    def media_url(key):
        """Resolve a Supabase Storage object key (or a raw URL) to a fetchable URL."""
        if not key:
            return ""
        return get_public_url(key)


def _register_performance(app: Flask) -> None:
    from app.utils.performance import (
        add_cache_headers,
        add_security_headers,
        responsive_srcset,
        responsive_sizes,
        get_critical_css,
    )

    add_cache_headers(app)
    add_security_headers(app)

    @app.template_global("responsive_srcset")
    def tpl_responsive_srcset(path, sizes=("small", "medium", "large")):
        return responsive_srcset(path, sizes)

    @app.template_global("responsive_sizes")
    def tpl_responsive_sizes(hint="default"):
        return responsive_sizes(hint)

    @app.context_processor
    def inject_critical_css():
        return {"critical_css": get_critical_css()}


def _register_a11y(app: Flask) -> None:
    from app.utils.accessibility import (
        strip_html,
        truncate_text,
        reading_level_aria,
    )

    @app.template_filter("strip_html")
    def strip_html_filter(s):
        return strip_html(s)

    @app.template_filter("truncate_text")
    def truncate_text_filter(s, length=160):
        return truncate_text(s, length)

    @app.template_filter("aria_content_type")
    def aria_content_type_filter(s):
        return reading_level_aria(s)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/500.html"), 500


def _register_shell_context(app: Flask) -> None:
    @app.shell_context_processor
    def shell_ctx():
        from app import models  # noqa: F401 — registers models with SQLAlchemy
        from app.extensions import db as _db
        from app.models import (
            User, Article, Category, Tag, House, Club, Sport, Team, Fixture,
            CampusEvent, StudentProfile, StaffProfile, AlumniProfile,
            Theme, SiteSetting, ActivityLog, Video, PodcastEpisode, Gallery,
        )
        return {
            "db": _db,
            "User": User, "Article": Article, "Category": Category, "Tag": Tag,
            "House": House, "Club": Club, "Sport": Sport, "Team": Team, "Fixture": Fixture,
            "CampusEvent": CampusEvent,
            "StudentProfile": StudentProfile, "StaffProfile": StaffProfile, "AlumniProfile": AlumniProfile,
            "Theme": Theme, "SiteSetting": SiteSetting, "ActivityLog": ActivityLog,
            "Video": Video, "PodcastEpisode": PodcastEpisode, "Gallery": Gallery,
        }