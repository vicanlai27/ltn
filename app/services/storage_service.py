"""
Supabase Storage backend for user-uploaded media.

Vercel's serverless filesystem is ephemeral and mostly read-only, so this
app no longer writes uploads to local disk. Every uploaded file (article
images, videos, audio, avatars, logos, etc.) is stored in a Supabase
Storage bucket instead, addressed by an object "key" such as
``articles/2026/09/ab12cd34.jpg``. That key is what gets saved in the
database (in the same columns that used to hold a local relative path),
and ``media_url(key)`` (registered as a Jinja global in app/__init__.py)
turns a key into a fetchable URL at render time.

Configuration (see .env.example):
    SUPABASE_URL                 e.g. https://xyzcompany.supabase.co
    SUPABASE_SERVICE_ROLE_KEY    server-side key with storage read/write
    SUPABASE_STORAGE_BUCKET      bucket name, default "media"

Only this module talks to Supabase's Storage REST API directly (via
``requests``) so the rest of the app never has to know how a file is
physically stored.
"""
from __future__ import annotations

import mimetypes

import requests
from flask import current_app


class StorageError(RuntimeError):
    """Raised when a Supabase Storage request fails."""


def _base_url() -> str:
    url = current_app.config.get("SUPABASE_URL")
    if not url:
        raise StorageError(
            "SUPABASE_URL is not configured. Set it in your environment "
            "(see .env.example)."
        )
    return url.rstrip("/")


def _service_key() -> str:
    key = current_app.config.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise StorageError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured. Set it in your "
            "environment (see .env.example)."
        )
    return key


def _bucket() -> str:
    return current_app.config.get("SUPABASE_STORAGE_BUCKET", "media")


def _auth_headers(content_type: str | None = None) -> dict:
    key = _service_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> str:
    """Upload raw bytes to the storage bucket at ``key`` (overwrites if present).

    Returns the key unchanged, so callers can chain this.
    """
    content_type = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
    url = f"{_base_url()}/storage/v1/object/{_bucket()}/{key}"
    headers = _auth_headers(content_type)
    headers["x-upsert"] = "true"
    resp = requests.post(url, headers=headers, data=data, timeout=30)
    if resp.status_code not in (200, 201):
        raise StorageError(f"Upload failed for '{key}': {resp.status_code} {resp.text}")
    return key


def download_bytes(key: str) -> bytes:
    """Download and return the raw bytes stored at ``key``."""
    url = f"{_base_url()}/storage/v1/object/{_bucket()}/{key}"
    resp = requests.get(url, headers=_auth_headers(), timeout=30)
    if resp.status_code != 200:
        raise StorageError(f"Download failed for '{key}': {resp.status_code} {resp.text}")
    return resp.content


def delete_object(key: str) -> None:
    """Delete a single object. Silently ignores objects that don't exist."""
    if not key:
        return
    url = f"{_base_url()}/storage/v1/object/{_bucket()}/{key}"
    resp = requests.delete(url, headers=_auth_headers(), timeout=30)
    # Supabase returns 200 on success; a missing object is not fatal here.
    if resp.status_code not in (200, 404):
        current_app.logger.warning(f"Storage delete failed for '{key}': {resp.status_code} {resp.text}")


def delete_prefix(prefix: str) -> None:
    """Delete every object under a folder-style prefix (e.g. an item's thumbs/ dir)."""
    if not prefix:
        return
    list_url = f"{_base_url()}/storage/v1/object/list/{_bucket()}"
    resp = requests.post(
        list_url,
        headers=_auth_headers("application/json"),
        json={"prefix": prefix, "limit": 100},
        timeout=30,
    )
    if resp.status_code != 200:
        return
    names = [f"{prefix.rstrip('/')}/{item['name']}" for item in resp.json() if item.get("name")]
    if names:
        requests.post(
            f"{_base_url()}/storage/v1/object/{_bucket()}",
            headers=_auth_headers("application/json"),
            json={"prefixes": names},
            timeout=30,
        )


def get_public_url(key: str) -> str:
    """Build the public CDN URL for an object key.

    Assumes the bucket is configured as public (see SUPABASE_SETUP in the
    docs). For a private bucket, swap this for a signed-URL call instead.
    """
    if not key:
        return ""
    if key.startswith("http://") or key.startswith("https://"):
        return key
    return f"{_base_url()}/storage/v1/object/public/{_bucket()}/{key}"
