import hashlib
import hmac
import os
import re
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app, request
from werkzeug.utils import secure_filename as _secure_filename


def utcnow() -> datetime:
    """Timezone-aware UTC now. Preferred over datetime.utcnow()."""
    return datetime.now(timezone.utc)


def ensure_aware(dt: "datetime | None") -> "datetime | None":
    """
    Coerce a datetime back into UTC-aware form before comparing it to
    ``utcnow()``/``datetime.now(timezone.utc)``.

    SQLite (the default local/dev database) does not actually persist
    timezone info even on columns declared ``DateTime(timezone=True)`` —
    values round-trip as naive datetimes. Comparing a naive datetime to
    an aware one raises ``TypeError: can't compare offset-naive and
    offset-aware datetimes``. Every value this app writes is UTC (via
    ``utcnow()``), so a naive value read back is safely assumed to be UTC.
    On backends that do preserve tzinfo (e.g. Postgres), this is a no-op.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def site_timezone() -> ZoneInfo:
    """The timezone editors are physically in (see Config.SITE_TIMEZONE)."""
    return ZoneInfo(current_app.config.get("SITE_TIMEZONE", "UTC"))


def local_naive_to_utc(dt: "datetime | None") -> "datetime | None":
    """
    Convert a naive local wall-clock datetime (as submitted by an HTML
    ``<input type="datetime-local">`` field, e.g. from DateTimeLocalField)
    into an aware UTC datetime for storage.

    Browsers send datetime-local values with no timezone info — just the
    numbers the editor typed/picked, in their own local time. Storing that
    naive value directly (or tagging it as UTC) silently shifts the publish
    time by the site's UTC offset. This converts it correctly instead.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Already aware for some reason — trust it, just normalize to UTC.
        return dt.astimezone(timezone.utc)
    localized = dt.replace(tzinfo=site_timezone())
    return localized.astimezone(timezone.utc)


def utc_to_local_naive(dt: "datetime | None") -> "datetime | None":
    """
    Convert a stored UTC datetime back into a naive local wall-clock
    datetime, for pre-filling a DateTimeLocalField on an edit form so the
    editor sees the same local time they originally chose.
    """
    if dt is None:
        return None
    aware = ensure_aware(dt)
    local = aware.astimezone(site_timezone())
    return local.replace(tzinfo=None)


def make_session_hash() -> str:
    """
    Deterministic-per-request anonymous identifier.
    HMAC-SHA256 of (IP + User-Agent + daily rotating salt).
    Rotating the salt daily limits long-term tracking while still
    deduplicating reactions/views/polls within a reasonable window.
    """
    salt = current_app.config["SESSION_HASH_SALT"]
    day_bucket = int(time.time()) // 86400
    raw = f"{request.remote_addr or ''}|{request.headers.get('User-Agent', '')}|{day_bucket}"
    return hmac.new(salt.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def safe_filename(upload) -> str:
    """UUID-prefixed sanitized filename to prevent collisions and traversal."""
    original = getattr(upload, "filename", "") or ""
    base = _secure_filename(original) or "file"
    ext = os.path.splitext(base)[1].lower()
    return f"{uuid.uuid4().hex}{ext}"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_length: int = 120) -> str:
    text = (text or "").lower().strip()
    text = _SLUG_RE.sub("-", text)
    text = text.strip("-")
    return text[:max_length].rstrip("-") or "untitled"