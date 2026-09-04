import os
from datetime import datetime, timezone
from io import BytesIO

from flask import current_app
from PIL import Image

from app.services import storage_service
from app.utils.security import safe_filename


ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "webm"}
ALLOWED_AUDIO_EXT = {"mp3", "m4a", "ogg", "wav", "webm"}
ALLOWED_EXT = ALLOWED_IMAGE_EXT | ALLOWED_VIDEO_EXT | ALLOWED_AUDIO_EXT


def validate_upload(upload) -> tuple[bool, str]:
    """Validate file extension and size. Returns (is_valid, error_message)."""
    if not upload or not upload.filename:
        return False, "No file provided"

    ext = os.path.splitext(upload.filename)[1].lower().lstrip(".")
    if ext not in ALLOWED_EXT:
        return False, f"File type .{ext} not allowed"

    max_size = current_app.config["MAX_CONTENT_LENGTH"]
    upload.stream.seek(0, 2)
    size = upload.stream.tell()
    upload.stream.seek(0)
    if size > max_size:
        return False, f"File too large (max {max_size // (1024*1024)}MB)"

    return True, ""


def save_upload(upload, subfolder: str = "images") -> str:
    """
    Upload a file to Supabase Storage at {subfolder}/{YYYY}/{MM}/{uuid}.{ext}.
    Returns the storage key (e.g. 'articles/2026/09/abc123.jpg') -- this is
    what gets stored in the database. Use media_url(key) in templates (or
    storage_service.get_public_url(key) in Python) to resolve it to a URL.
    Generates WebP thumbnails alongside the original for images.
    """
    is_valid, error = validate_upload(upload)
    if not is_valid:
        raise ValueError(error)

    ext = os.path.splitext(upload.filename)[1].lower().lstrip(".")
    filename = safe_filename(upload)

    now = datetime.now(timezone.utc)
    date_path = f"{now.year}/{now.month:02d}"
    key = f"{subfolder}/{date_path}/{filename}"

    upload.stream.seek(0)
    data = upload.stream.read()
    storage_service.upload_bytes(key, data, content_type=upload.mimetype)

    if ext in ALLOWED_IMAGE_EXT:
        _generate_thumbnails(key, data)

    return key


def _thumb_key(key: str, size_name: str) -> str:
    subfolder, stem = key.rsplit("/", 1)
    stem = stem.rsplit(".", 1)[0]
    return f"{subfolder}/thumbs/{stem}_{size_name}.webp"


def _generate_thumbnails(key: str, data: bytes) -> None:
    """Generate small/medium/large WebP thumbnails in memory and upload them."""
    thumb_sizes = current_app.config.get("THUMB_SIZES", {"small": 400, "medium": 800, "large": 1600})

    try:
        with Image.open(BytesIO(data)) as img:
            img = img.convert("RGB")
            for size_name, width in thumb_sizes.items():
                ratio = width / img.width
                height = int(img.height * ratio)
                resized = img.resize((width, height), Image.Resampling.LANCZOS)
                buf = BytesIO()
                resized.save(buf, "WEBP", quality=85)
                storage_service.upload_bytes(
                    _thumb_key(key, size_name), buf.getvalue(), content_type="image/webp"
                )
    except Exception as e:
        current_app.logger.error(f"Thumbnail generation failed for {key}: {e}")


def get_thumbnail_url(image_key: str, size: str = "medium") -> str | None:
    """Get the public URL for a thumbnail. Returns None if no key is given."""
    if not image_key:
        return None
    return storage_service.get_public_url(_thumb_key(image_key, size))


def delete_upload(key: str):
    """Delete an uploaded file and its thumbnails from Supabase Storage."""
    if not key or key.startswith("http://") or key.startswith("https://"):
        return

    storage_service.delete_object(key)

    subfolder, stem = key.rsplit("/", 1)
    storage_service.delete_prefix(f"{subfolder}/thumbs")


def get_audio_duration(audio_key: str) -> int | None:
    """
    Get audio duration in seconds. Downloads the file from Supabase Storage
    and reads it with mutagen. Falls back gracefully -- duration is optional
    metadata.
    """
    try:
        from mutagen.mp3 import MP3
        from mutagen.mp4 import MP4

        if not audio_key:
            return None

        data = storage_service.download_bytes(audio_key)
        ext = os.path.splitext(audio_key)[1].lower()
        buf = BytesIO(data)
        if ext == ".mp3":
            audio = MP3(buf)
            return int(audio.info.length)
        elif ext in (".m4a", ".mp4"):
            audio = MP4(buf)
            return int(audio.info.length)
        return None
    except Exception:
        return None
