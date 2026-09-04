import textwrap
from io import BytesIO
from pathlib import Path

from flask import current_app, url_for
from PIL import Image, ImageDraw, ImageFont

from app.models.content import Article


# Brand colors
BRAND_BLUE = (11, 60, 140)       # #0B3C8C
BRAND_NAVY = (10, 31, 68)        # #0A1F44
BRAND_GOLD = (212, 165, 55)      # #D4A537
WHITE = (255, 255, 255)
DARK_TEXT = (17, 20, 24)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if custom font not available."""
    # Try common system font paths; fall back to Pillow's default
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for path in font_candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


def generate_instagram_card(article: Article, size: str = "square") -> bytes:
    """
    Generate an Instagram-ready share card as PNG bytes.
    size: 'square' (1080x1080) or 'portrait' (1080x1350)
    """
    if size == "portrait":
        width, height = 1080, 1350
    else:
        width, height = 1080, 1080

    # Create base image
    img = Image.new("RGB", (width, height), BRAND_NAVY)
    draw = ImageDraw.Draw(img)

    # Featured image (top 55% of card)
    image_height = int(height * 0.55)
    if article.featured_image:
        try:
            from app.services import storage_service
            image_bytes = storage_service.download_bytes(article.featured_image)
            with Image.open(BytesIO(image_bytes)) as featured:
                    featured = featured.convert("RGB")
                    # Crop to fill
                    aspect = width / image_height
                    img_aspect = featured.width / featured.height
                    if img_aspect > aspect:
                        new_width = int(featured.height * aspect)
                        left = (featured.width - new_width) // 2
                        featured = featured.crop((left, 0, left + new_width, featured.height))
                    else:
                        new_height = int(featured.width / aspect)
                        top = (featured.height - new_height) // 2
                        featured = featured.crop((0, top, featured.width, top + new_height))
                    featured = featured.resize((width, image_height), Image.Resampling.LANCZOS)
                    img.paste(featured, (0, 0))
        except Exception:
            pass  # Fall back to solid color

    # Gradient overlay at bottom of image
    for y in range(120):
        alpha = int(255 * (y / 120))
        overlay_color = (
            int(BRAND_NAVY[0] * alpha / 255 + img.getpixel((0, image_height - 120 + y))[0] * (255 - alpha) / 255),
            int(BRAND_NAVY[1] * alpha / 255 + img.getpixel((0, image_height - 120 + y))[1] * (255 - alpha) / 255),
            int(BRAND_NAVY[2] * alpha / 255 + img.getpixel((0, image_height - 120 + y))[2] * (255 - alpha) / 255),
        )
        draw.line([(0, image_height - 120 + y), (width, image_height - 120 + y)], fill=overlay_color)

    # Content area
    content_top = image_height + 40
    content_padding = 60

    # Category badge
    if article.category:
        badge_font = _load_font(24, bold=True)
        badge_text = article.category.name.upper()
        bbox = badge_font.getbbox(badge_text)
        badge_w = bbox[2] - bbox[0] + 32
        badge_h = bbox[3] - bbox[1] + 20
        draw.rectangle(
            [(content_padding, content_top), (content_padding + badge_w, content_top + badge_h)],
            fill=BRAND_GOLD,
        )
        draw.text(
            (content_padding + 16, content_top + 6),
            badge_text,
            fill=BRAND_NAVY,
            font=badge_font,
        )
        content_top += badge_h + 20

    # Headline
    title_font = _load_font(52, bold=True)
    max_text_width = width - (content_padding * 2)
    lines = _wrap_text(article.title, title_font, max_text_width)
    # Limit to 4 lines
    lines = lines[:4]
    if len(lines) == 4 and len(article.title.split()) > 20:
        lines[3] = lines[3].rsplit(" ", 1)[0] + "..."

    y = content_top
    for line in lines:
        draw.text((content_padding, y), line, fill=WHITE, font=title_font)
        bbox = title_font.getbbox(line)
        y += bbox[3] - bbox[1] + 12

    # Author + date
    y += 20
    meta_font = _load_font(24)
    meta_parts = []
    if article.author and article.author.author_profile:
        meta_parts.append(f"By {article.author.author_profile.display_name}")
    if article.published_at:
        meta_parts.append(article.published_at.strftime("%b %d, %Y"))
    meta_text = " · ".join(meta_parts)
    draw.text((content_padding, y), meta_text, fill=(200, 200, 200), font=meta_font)

    # Brand footer
    footer_y = height - 100
    # Gold accent line
    draw.rectangle([(content_padding, footer_y), (content_padding + 80, footer_y + 4)], fill=BRAND_GOLD)
    # Brand name
    brand_font = _load_font(32, bold=True)
    draw.text((content_padding, footer_y + 20), "Lavisco", fill=WHITE, font=brand_font)
    brand_bbox = brand_font.getbbox("Lavisco")
    news_x = content_padding + brand_bbox[2] - brand_bbox[0] + 8
    news_font = _load_font(32)
    draw.text((news_x, footer_y + 20), "News", fill=BRAND_GOLD, font=news_font)
    # Tagline
    tagline_font = _load_font(18)
    draw.text((content_padding, footer_y + 60), "News. Context. Truth.", fill=(180, 180, 180), font=tagline_font)

    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def get_instagram_card_url(article: Article, size: str = "square") -> str:
    """Get the URL for the Instagram share card endpoint."""
    return url_for("api.article_share_card", article_id=article.id, size=size, _external=True)