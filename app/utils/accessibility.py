"""
Accessibility helpers: contrast checking, reading time, ARIA helpers.
"""
import re


def strip_html(html: str) -> str:
    """Strip HTML tags for plain-text extraction (alt text, summaries)."""
    if not html:
        return ""
    return re.sub(r"<[^>]+>", "", html).strip()


def truncate_text(text: str, length: int = 160) -> str:
    """Truncate text to a given length, breaking at word boundaries."""
    if not text or len(text) <= length:
        return text or ""
    truncated = text[:length].rsplit(" ", 1)[0]
    return truncated.rstrip(".,;:!?") + "…"


def reading_level_aria(content_type: str) -> str:
    """Return an appropriate ARIA label for content type badges."""
    labels = {
        "breaking_news": "Breaking news alert",
        "explainer": "Explainer article",
        "opinion": "Opinion piece",
        "analysis": "Analysis",
        "investigation": "Investigative report",
        "interview": "Interview",
        "60_second_read": "60 second read",
        "live_story": "Live developing story",
    }
    return labels.get(content_type, content_type.replace("_", " ").title())


def contrast_ratio(fg: str, bg: str) -> float:
    """
    Compute WCAG contrast ratio between two hex colors.
    Returns a float >= 1. AA requires 4.5:1 for normal text, 3:1 for large text.
    """
    def luminance(hex_color: str) -> float:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return 0
        r, g, b = (int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
        def linearize(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

    l1 = luminance(fg)
    l2 = luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def meets_wcag_aa(fg: str, bg: str, large_text: bool = False) -> bool:
    """Check if a color pair meets WCAG 2.2 AA contrast requirements."""
    ratio = contrast_ratio(fg, bg)
    threshold = 3.0 if large_text else 4.5
    return ratio >= threshold