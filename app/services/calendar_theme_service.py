"""
Auto-generate calendar themes based on the current date.
These are created once as seed data and can be edited/disabled by admins.
Ugandan calendar awareness: Independence (Oct 9), Easter (variable), Eid (variable).
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.editorial import Theme


# Calendar theme templates — used by seed.py to bootstrap themes
CALENDAR_THEME_TEMPLATES = [
    {
        "name": "Christmas Edition",
        "slug": "christmas",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Festive seasonal theme with deep red, green accents, and gold.",
        "month": 12,  # Active all of December
        "primary_color": "#8B1A1A",       # Deep festive red
        "secondary_color": "#0A1F44",     # Keep navy base
        "accent_color": "#D4A537",        # Gold
        "background_color": None,         # Inherit default
        "text_color": None,
        "decoration_config": {
            "motif": "christmas",
            "density": "low",
        },
        "animation_config": {
            "enabled": ["snow"],
            "respect_reduced_motion": True,
        },
        "priority": 100,
    },
    {
        "name": "New Year",
        "slug": "new-year",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Midnight tones with gold celebration accents.",
        "month": 1,
        "primary_color": "#1E3A8A",
        "secondary_color": "#0A1F44",
        "accent_color": "#F2C75C",
        "decoration_config": {"motif": "celebration", "density": "low"},
        "animation_config": {"enabled": ["sparkle"]},
        "priority": 100,
    },
    {
        "name": "Valentine's",
        "slug": "valentines",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Soft red and pink accents with subtle heart motifs.",
        "month": 2,
        "primary_color": "#BE185D",
        "secondary_color": "#0A1F44",
        "accent_color": "#FDA4AF",
        "decoration_config": {"motif": "hearts", "density": "low"},
        "animation_config": {"enabled": []},
        "priority": 100,
    },
    {
        "name": "Easter",
        "slug": "easter",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Purple and gold with soft seasonal accents.",
        # Variable — seed script should set dates per year
        "month": None,  # Set manually per year
        "primary_color": "#6B21A8",
        "secondary_color": "#0A1F44",
        "accent_color": "#D4A537",
        "decoration_config": {"motif": "floral", "density": "low"},
        "animation_config": {"enabled": []},
        "priority": 100,
    },
    {
        "name": "Eid",
        "slug": "eid",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Emerald and gold with crescent-inspired motifs.",
        "month": None,  # Variable — Islamic calendar
        "primary_color": "#047857",
        "secondary_color": "#0A1F44",
        "accent_color": "#D4A537",
        "decoration_config": {"motif": "crescent", "density": "low"},
        "animation_config": {"enabled": []},
        "priority": 100,
    },
    {
        "name": "Independence (Uganda)",
        "slug": "uganda-independence",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Uganda-inspired restrained accents — black, yellow, red.",
        "month": 10,  # October (Independence Day: Oct 9)
        "primary_color": "#0B3C8C",       # Keep brand blue
        "secondary_color": "#0A1F44",
        "accent_color": "#FCDC2A",        # Ugandan yellow
        "decoration_config": {"motif": "independence", "density": "low"},
        "animation_config": {"enabled": []},
        "priority": 150,  # Slightly higher than generic calendar
    },
    {
        "name": "Back to School",
        "slug": "back-to-school",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Fresh start theme for the beginning of term.",
        "month": 2,  # February (Ugandan schools often start terms in Feb/May/Sep)
        "primary_color": "#0B3C8C",
        "secondary_color": "#0A1F44",
        "accent_color": "#D4A537",
        "decoration_config": {"motif": "books", "density": "low"},
        "animation_config": {"enabled": []},
        "priority": 100,
    },
    {
        "name": "Exam Season",
        "slug": "exam-season",
        "theme_type": Theme.TYPE_CALENDAR,
        "description": "Focused, calm theme for exam periods.",
        "month": 11,  # November (end of year exams)
        "primary_color": "#1E40AF",
        "secondary_color": "#0A1F44",
        "accent_color": "#D4A537",
        "decoration_config": {"motif": None, "density": "none"},
        "animation_config": {"enabled": []},
        "priority": 100,
    },
]


def seed_calendar_themes():
    """
    Create the default calendar themes if they don't exist.
    Called from seed.py during initial setup.
    """
    created = 0
    for template in CALENDAR_THEME_TEMPLATES:
        if Theme.query.filter_by(slug=template["slug"]).first():
            continue

        # Calculate start/end dates based on month
        if template.get("month"):
            year = datetime.now(timezone.utc).year
            month = template["month"]
            # Start on the 1st of the month, end on the last day
            start_date = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        else:
            # Variable-date themes (Easter, Eid) — admin sets dates manually
            start_date = None
            end_date = None

        theme = Theme(
            name=template["name"],
            slug=template["slug"],
            theme_type=template["theme_type"],
            description=template.get("description"),
            start_date=start_date,
            end_date=end_date,
            primary_color=template.get("primary_color"),
            secondary_color=template.get("secondary_color"),
            accent_color=template.get("accent_color"),
            background_color=template.get("background_color"),
            text_color=template.get("text_color"),
            decoration_config=template.get("decoration_config"),
            animation_config=template.get("animation_config"),
            priority=template.get("priority", 100),
            is_active=True,
        )
        db.session.add(theme)
        created += 1

    db.session.commit()
    return created