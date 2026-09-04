import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env before any os.environ.get() calls below run. This file is
# imported by every entry point (flask CLI, run.py, seed.py, api/index.py
# on Vercel), so this is the one place that guarantees .env is picked up
# consistently. Flask's own CLI (`flask run`, `flask db migrate`) already
# auto-loads .env on its own, but plain `python` scripts like seed.py do
# not -- without this, those scripts silently fall back to default values
# (e.g. the local SQLite database) instead of your real DATABASE_URL.
# On Vercel, real env vars are already set by the platform and there's no
# .env file to find, so this is a harmless no-op there.
load_dotenv(BASE_DIR / ".env")

INSTANCE_DIR = BASE_DIR / "instance"
try:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Read-only filesystem (e.g. Vercel's serverless runtime). Harmless --
    # this directory is only used for the local-dev SQLite fallback.
    pass


def _normalize_database_url(url: str | None) -> str | None:
    """Supabase (and most hosts) hand out 'postgres://' URLs; SQLAlchemy's
    psycopg2 driver wants 'postgresql://'. Normalize so either form works."""
    if url and url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Local-disk fallback only -- used for `flask run` on a machine with no
    # Supabase credentials set. Production/Vercel never touches this; all
    # uploads go straight to Supabase Storage (see SUPABASE_* below and
    # app/services/storage_service.py).
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "app" / "static" / "uploads"))

    # Supabase Storage (required in production; see .env.example)
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "media")

    # Timezone editors are physically in. Admin "Publish At" datetime-local
    # inputs submit a wall-clock time with no timezone info attached; this
    # tells the server how to convert that local time to UTC for storage
    # (and back again for display) instead of misreading it as UTC.
    SITE_TIMEZONE = os.environ.get("SITE_TIMEZONE", "Africa/Kampala")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 100 * 1024 * 1024))
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm"}
    ALLOWED_AUDIO_EXTENSIONS = {"mp3", "m4a", "ogg", "wav", "webm"}

    # Thumbnails (width in px)
    THUMB_SIZES = {"small": 400, "medium": 800, "large": 1600}

    # Lavisco TV (YouTube channel indexing — no API key required)
    YOUTUBE_CHANNEL_HANDLE = os.environ.get("YOUTUBE_CHANNEL_HANDLE", "@LAVISCOTV-bm1mp")
    # Prefer a stable channel ID in production when available. It avoids an
    # extra handle-resolution request and is not affected by handle changes.
    YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "")
    YOUTUBE_VIDEOS_CACHE_SECONDS = int(os.environ.get("YOUTUBE_VIDEOS_CACHE_SECONDS", 15 * 60))
    YOUTUBE_LIVE_CACHE_SECONDS = int(os.environ.get("YOUTUBE_LIVE_CACHE_SECONDS", 60))

    # Session hash cookie
    SESSION_HASH_COOKIE = "lavisco_sid"
    SESSION_HASH_SALT = os.environ.get("SESSION_HASH_SALT", "dev-salt-rotate-daily-in-prod")
    VIEW_DEDUP_MINUTES = 30

    # Mail (transactional only)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@lavisco.news")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"

    # Rate limits. NOTE: "memory://" resets on every cold start on Vercel
    # (each serverless invocation may get a fresh process), so per-IP limits
    # are only a soft guard there, not a hard one. Point RATELIMIT_STORAGE_URI
    # at Supabase's Redis-compatible add-on or another shared store if you
    # need real cross-instance rate limiting in production.
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # Brand
    SITE_NAME = "Lavisco TV News"
    SITE_TAGLINE = "News. Context. Truth."
    SITE_ORIGIN = "Holy Cross Lake View Wanyange"


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        os.environ.get("DATABASE_URL")
    ) or f"sqlite:///{INSTANCE_DIR / 'lavisco.db'}"
    # Only applied when DATABASE_URL points at Postgres (Supabase); ignored
    # for the SQLite fallback.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SERVER_NAME = "localhost"


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.environ.get("DATABASE_URL"))
    # Vercel functions are short-lived and can run many instances in
    # parallel, so we don't want each one holding a persistent connection
    # pool -- that exhausts Supabase's connection limit fast. Use Supabase's
    # pgbouncer "Transaction" pooler connection string (port 6543) for
    # DATABASE_URL in production, and keep SQLAlchemy's own pool minimal:
    # NullPool opens a fresh connection per request and closes it right
    # after, which pairs correctly with pgbouncer in transaction mode.
    from sqlalchemy.pool import NullPool
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": NullPool,
        "pool_pre_ping": True,
        "connect_args": {"sslmode": "require"},
    }
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
