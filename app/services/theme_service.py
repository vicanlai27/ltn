from datetime import datetime, timezone

from app.extensions import db
from app.models.editorial import Theme, SpecialEdition


# Priority tiers (higher number wins)
PRIORITY_MANUAL_OVERRIDE = 1000
PRIORITY_SPECIAL_EDITION = 500
PRIORITY_SCHOOL_EVENT = 300
PRIORITY_CALENDAR = 100
PRIORITY_DEFAULT = 0


def resolve_active_theme(scope: str | None = None) -> Theme | None:
    """
    Resolve the currently active theme by priority.
    Priority order (highest wins):
      1. Manual override (admin-pinned)
      2. Special edition with active theme
      3. School event within date range
      4. Calendar theme (seasonal)
      5. Default (None — base blue & gold applies)

    If scope is provided (e.g., 'campus'), prefer themes matching that scope.
    """
    now = datetime.now(timezone.utc)

    # Build a query for all potentially active themes
    q = Theme.query.filter(Theme.is_active.is_(True))
    q = q.filter(
        db.or_(Theme.start_date.is_(None), Theme.start_date <= now)
    )
    q = q.filter(
        db.or_(Theme.end_date.is_(None), Theme.end_date >= now)
    )

    candidates = q.all()
    if not candidates:
        return None

    # Sort by priority desc, then by id desc (newer wins ties)
    candidates.sort(key=lambda t: (t.priority or 0, t.id or 0), reverse=True)
    return candidates[0]


def get_theme_css_variables(theme: Theme) -> dict:
    """
    Extract non-null color variables from a theme for injection into templates.
    Returns only the variables that are set (so unset ones fall back to defaults).
    """
    if not theme:
        return {}

    mapping = {
        "primary_color": "--brand-primary",
        "secondary_color": "--brand-secondary",
        "accent_color": "--accent",
        "background_color": "--background",
        "text_color": "--text",
    }

    variables = {}
    for attr, css_var in mapping.items():
        value = getattr(theme, attr, None)
        if value:
            variables[css_var] = value

    return variables


def render_theme_css(theme: Theme) -> str:
    """Render the CSS variable overrides for a theme as an inline <style> block."""
    variables = get_theme_css_variables(theme)
    if not variables:
        return ""

    lines = [":root {"]
    for css_var, value in variables.items():
        lines.append(f"  {css_var}: {value};")
    lines.append("}")
    return "\n".join(lines)


def get_theme_decorations(theme: Theme) -> dict:
    """
    Return decoration config for a theme (motifs, animations, density).
    Used by the theme_decorations component to render subtle CSS effects.
    """
    if not theme:
        return {"motif": None, "animations": [], "density": "none"}

    decoration_config = theme.decoration_config or {}
    animation_config = theme.animation_config or {}

    return {
        "motif": decoration_config.get("motif"),
        "density": decoration_config.get("density", "low"),
        "animations": animation_config.get("enabled", []) or [],
        "sound_enabled": theme.sound_enabled,
    }


def preview_theme(theme_id: int) -> Theme | None:
    """Get a theme for preview purposes (ignores active/date constraints)."""
    return db.session.get(Theme, theme_id)


def activate_theme(theme_id: int, admin_id: int) -> Theme:
    """Manually activate a theme (sets priority to manual override level)."""
    from app.services.activity_service import log_activity

    theme = db.session.get(Theme, theme_id)
    if not theme:
        raise ValueError("Theme not found")

    theme.is_active = True
    theme.priority = PRIORITY_MANUAL_OVERRIDE
    db.session.commit()

    log_activity(admin_id, "theme.activate", "theme", theme_id, f"Activated '{theme.name}'")
    return theme


def deactivate_theme(theme_id: int, admin_id: int) -> Theme:
    """Deactivate a theme."""
    from app.services.activity_service import log_activity

    theme = db.session.get(Theme, theme_id)
    if not theme:
        raise ValueError("Theme not found")

    theme.is_active = False
    theme.priority = PRIORITY_DEFAULT
    db.session.commit()

    log_activity(admin_id, "theme.deactivate", "theme", theme_id, f"Deactivated '{theme.name}'")
    return theme