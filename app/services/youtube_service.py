"""
Lavisco TV — YouTube channel indexing without a Data API key.

Two well-known no-key tricks are used:

1. Latest videos: every YouTube channel exposes a public Atom feed at
   /feeds/videos.xml?channel_id=... with its most recent uploads. No key,
   no quota.
2. Live status: requesting /<handle>/live redirects to the live watch page
   if the channel is currently streaming, or to the channel's regular page
   otherwise. We follow the redirect and check the watch page for YouTube's
   own "isLive"/"isLiveNow" flags embedded in its player response JSON.

Both are best-effort scrapes of public pages rather than a supported API,
so every call is defensive: on any failure we fall back to the last good
cached value instead of breaking the page that embeds this.

Results are cached in SiteSetting (a simple key/value table already used
elsewhere in this app) so we don't hit YouTube on every request.
"""
import json
import re
import time
import urllib.error
import urllib.request
from xml.etree import ElementTree

from flask import current_app

from app.extensions import db
from app.models.system import SiteSetting

_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}

_CACHE_KEY = "youtube_tv_cache"
_USER_AGENT = "Mozilla/5.0 (compatible; LaviscoNewsBot/1.0; +https://lavisco.news)"

_CHANNEL_ID_RE = re.compile(r'"channelId":"(UC[a-zA-Z0-9_-]{10,32})"')
_CANONICAL_CHANNEL_RE = re.compile(
    r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[a-zA-Z0-9_-]{10,32})">'
)
_WATCH_ID_RE = re.compile(r"[?&]v=([a-zA-Z0-9_-]{11})")
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
_LIVE_FLAG_RE = re.compile(r'"isLive(?:Now)?"\\s*:\\s*true', re.IGNORECASE)
_YOUTUBE_VIDEO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{11}$")


def normalize_video_id(value: str | None) -> str | None:
    """Normalize a YouTube video ID or supported YouTube URL to its 11-char ID."""
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    if _YOUTUBE_VIDEO_ID_RE.fullmatch(value):
        return value

    from urllib.parse import parse_qs, urlparse

    # Accept a pasted YouTube URL even when the user omitted the scheme.
    parse_value = value if "://" in value else f"https://{value}"
    try:
        parsed = urlparse(parse_value)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower().rstrip(".")
    if host == "www.youtube.com" or host == "youtube.com":
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif parsed.path.startswith("/embed/"):
            candidate = parsed.path.split("/embed/", 1)[1].split("/", 1)[0]
        else:
            candidate = None
    elif host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/", 1)[0]
    else:
        candidate = None

    return candidate if candidate and _YOUTUBE_VIDEO_ID_RE.fullmatch(candidate) else None


def _fetch(url: str, timeout: int = 6) -> tuple[str, str]:
    """GET a URL, following redirects. Returns (body_text, final_url)."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        final_url = resp.geturl()
        body = resp.read().decode("utf-8", errors="replace")
    return body, final_url


def _load_cache() -> dict:
    row = SiteSetting.query.filter_by(key=_CACHE_KEY).first()
    if not row or not row.value:
        return {}
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        return {}


def _save_cache(data: dict) -> None:
    """Persist cache state without allowing cache failures to break requests."""
    try:
        row = SiteSetting.query.filter_by(key=_CACHE_KEY).first()
        if row is None:
            row = SiteSetting(key=_CACHE_KEY, value=json.dumps(data))
            db.session.add(row)
        else:
            row.value = json.dumps(data)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.debug("Lavisco TV: cache write skipped: %s", exc)


def _channel_handle() -> str:
    handle = current_app.config.get("YOUTUBE_CHANNEL_HANDLE", "@LAVISCOTV-bm1mp")
    return handle if handle.startswith("@") else f"@{handle}"


def resolve_channel_id(force_refresh: bool = False) -> str | None:
    """
    Resolve the channel's stable UC... ID from its @handle. Cached
    indefinitely once found (a channel's ID never changes, only its handle).
    """
    cache = _load_cache()

    configured_id = (current_app.config.get("YOUTUBE_CHANNEL_ID") or "").strip()
    if configured_id and re.fullmatch(r"UC[a-zA-Z0-9_-]{10,32}", configured_id):
        if cache.get("channel_id") != configured_id:
            cache["channel_id"] = configured_id
            _save_cache(cache)
        return configured_id

    if not force_refresh and cache.get("channel_id"):
        return cache["channel_id"]

    handle = _channel_handle()
    try:
        html, _ = _fetch(f"https://www.youtube.com/{handle}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        current_app.logger.warning("Lavisco TV: could not resolve channel id for %s: %s", handle, exc)
        return cache.get("channel_id")

    match = _CHANNEL_ID_RE.search(html) or _CANONICAL_CHANNEL_RE.search(html)
    if not match:
        current_app.logger.warning("Lavisco TV: channel id not found in page for %s", handle)
        return cache.get("channel_id")

    channel_id = match.group(1)
    cache["channel_id"] = channel_id
    _save_cache(cache)
    return channel_id


def get_latest_videos(limit: int = 12, force_refresh: bool = False) -> list[dict]:
    """
    Latest uploads from the channel's public RSS feed. Each item:
    {video_id, title, description, thumbnail, published_at, url}
    Returns the last known-good list (possibly stale, possibly empty) on
    any fetch failure rather than raising.
    """
    cache = _load_cache()
    now = time.time()
    ttl = current_app.config.get("YOUTUBE_VIDEOS_CACHE_SECONDS", 900)

    if not force_refresh and cache.get("videos") and (now - cache.get("videos_fetched_at", 0) < ttl):
        return cache["videos"][:limit]

    channel_id = cache.get("channel_id") or resolve_channel_id()
    if not channel_id:
        return cache.get("videos", [])[:limit]

    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        xml_text, _ = _fetch(feed_url)
        root = ElementTree.fromstring(xml_text)
    except (urllib.error.URLError, TimeoutError, OSError, ElementTree.ParseError) as exc:
        current_app.logger.warning("Lavisco TV: could not fetch video feed: %s", exc)
        return cache.get("videos", [])[:limit]

    videos = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        video_id = entry.findtext("yt:videoId", default="", namespaces=_ATOM_NS)
        if not video_id:
            continue
        title = entry.findtext("atom:title", default="", namespaces=_ATOM_NS)
        published = entry.findtext("atom:published", default="", namespaces=_ATOM_NS)

        description = ""
        media_group = entry.find("media:group", _ATOM_NS)
        if media_group is not None:
            desc_el = media_group.find("media:description", _ATOM_NS)
            if desc_el is not None and desc_el.text:
                description = desc_el.text

        # Thumbnails are fetched deterministically from i.ytimg.com rather than
        # trusting the RSS-provided URL (which is often a lower-res default
        # and occasionally missing). maxresdefault gives the best quality but
        # doesn't exist for every video, so the template falls back through
        # sddefault -> hqdefault -> mqdefault client-side if a request 404s.
        thumbnails = {
            quality: f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg"
            for quality in ("maxresdefault", "sddefault", "hqdefault", "mqdefault")
        }

        videos.append({
            "video_id": video_id,
            "title": title,
            "description": description,
            "thumbnail": thumbnails["maxresdefault"],
            "thumbnail_fallbacks": [
                thumbnails["sddefault"], thumbnails["hqdefault"], thumbnails["mqdefault"],
            ],
            "published_at": published,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    cache["videos"] = videos
    cache["videos_fetched_at"] = now
    cache["channel_id"] = channel_id
    _save_cache(cache)
    return videos[:limit]


def get_live_status(force_refresh: bool = False) -> dict:
    """
    {is_live, video_id, title}. Checked by following the channel's /live
    redirect: if it lands on a watch page whose player response reports
    a live broadcast, the channel is live right now.
    """
    cache = _load_cache()
    now = time.time()
    ttl = current_app.config.get("YOUTUBE_LIVE_CACHE_SECONDS", 60)

    if not force_refresh and "live" in cache and (now - cache.get("live_fetched_at", 0) < ttl):
        return cache["live"]

    handle = _channel_handle()
    fallback = cache.get("live", {"is_live": False, "video_id": None, "title": None})

    try:
        html, final_url = _fetch(f"https://www.youtube.com/{handle}/live")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        current_app.logger.warning("Lavisco TV: could not check live status: %s", exc)
        cache["live"] = fallback
        cache["live_fetched_at"] = now
        _save_cache(cache)
        return fallback

    result = {"is_live": False, "video_id": None, "title": None}
    if "/watch" in final_url and _LIVE_FLAG_RE.search(html):
        id_match = _WATCH_ID_RE.search(final_url)
        title_match = _TITLE_RE.search(html)
        result = {
            "is_live": True,
            "video_id": id_match.group(1) if id_match else None,
            "title": title_match.group(1).replace(" - YouTube", "").strip() if title_match else None,
        }

    cache["live"] = result
    cache["live_fetched_at"] = now
    _save_cache(cache)
    return result
