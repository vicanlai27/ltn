# Re-export every model so `from app.models import Article` works
# and Flask-Migrate picks them up for autogenerate.

from app.models.user import (
    User, AuthorProfile, UserPreference, NotificationSubscription,
)
from app.models.content import Article, Category, Tag, TagRelation, ArticleImage
from app.models.campus import House, HouseScore, Club, CampusEvent
from app.models.sports import Sport, Team, Fixture
from app.models.people import StudentProfile, StaffProfile, AlumniProfile
from app.models.engagement import (
    Reaction, ShareEvent, ViewEvent, Report, Poll, PollOption, Comment, CommentReaction,
)
from app.models.media import Gallery, GalleryImage, Video, PodcastEpisode
from app.models.editorial import (
    Theme, SpecialEdition, PlacementSlot, SiteAnnouncement,
)
from app.models.notifications import Notification
from app.models.system import (
    SiteSetting, Advertisement, ActivityLog, ConsentRecord,
)

__all__ = [
    "User", "AuthorProfile", "UserPreference", "NotificationSubscription",
    "Article", "Category", "Tag", "TagRelation", "ArticleImage",
    "House", "HouseScore", "Club", "CampusEvent",
    "Sport", "Team", "Fixture",
    "StudentProfile", "StaffProfile", "AlumniProfile",
    "Reaction", "ShareEvent", "ViewEvent", "Report", "Poll", "PollOption", "Comment", "CommentReaction",
    "Gallery", "GalleryImage", "Video", "PodcastEpisode",
    "Theme", "SpecialEdition", "PlacementSlot", "SiteAnnouncement",
    "SiteSetting", "Advertisement", "ActivityLog", "ConsentRecord", "Notification",
]