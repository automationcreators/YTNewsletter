# Import all models here for Alembic to discover them
from app.models.user import User
from app.models.channel import Channel, ChannelTag
from app.models.subscription import UserChannelSubscription
from app.models.video import Video
from app.models.transcript import Transcript
from app.models.summary import VideoSummary
from app.models.prompt_template import PromptTemplate
from app.models.system_config import SystemConfig
from app.models.newsletter import Newsletter, NewsletterTemplate, NewsletterStatus

__all__ = [
    "User",
    "Channel",
    "ChannelTag",
    "UserChannelSubscription",
    "Video",
    "Transcript",
    "VideoSummary",
    "PromptTemplate",
    "SystemConfig",
    "Newsletter",
    "NewsletterTemplate",
    "NewsletterStatus",
]
