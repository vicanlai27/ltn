# Re-export for convenience — the actual logic lives in the repository
# so it can be reused by templates, API endpoints, and admin widgets.
from app.repositories.homepage import trending_now  # noqa: F401