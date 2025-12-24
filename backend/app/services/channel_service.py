"""Channel service for database operations."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.channel import Channel, ChannelTag
from app.integrations.youtube_client import youtube_client


class ChannelService:
    """Service for channel-related database operations."""

    def get_by_id(self, db: Session, channel_id: UUID) -> Optional[Channel]:
        """Get channel by internal ID."""
        return db.query(Channel).filter(Channel.id == channel_id).first()

    def get_by_youtube_id(self, db: Session, youtube_channel_id: str) -> Optional[Channel]:
        """Get channel by YouTube channel ID."""
        return db.query(Channel).filter(
            Channel.youtube_channel_id == youtube_channel_id
        ).first()

    def create_from_youtube(self, db: Session, youtube_data: dict) -> Channel:
        """
        Create a new channel from YouTube API data.

        Args:
            db: Database session
            youtube_data: Channel data from YouTube API

        Returns:
            Created channel
        """
        # Determine size tier based on subscriber count
        subscriber_count = youtube_data.get("subscriber_count", 0)
        size_tier = self._calculate_size_tier(subscriber_count)

        channel = Channel(
            youtube_channel_id=youtube_data["youtube_channel_id"],
            name=youtube_data["name"],
            description=youtube_data.get("description"),
            thumbnail_url=youtube_data.get("thumbnail_url"),
            banner_url=youtube_data.get("banner_url"),
            subscriber_count=subscriber_count,
            video_count=youtube_data.get("video_count"),
            custom_url=youtube_data.get("custom_url"),
            size_tier=size_tier,
            # Category and format_type will be set by classification service
        )

        db.add(channel)
        db.commit()
        db.refresh(channel)

        return channel

    def get_or_create_from_youtube(
        self,
        db: Session,
        youtube_channel_id: str,
    ) -> tuple[Channel, bool]:
        """
        Get existing channel or create from YouTube API.

        Args:
            db: Database session
            youtube_channel_id: YouTube channel ID

        Returns:
            Tuple of (channel, is_new)
        """
        # Check if already exists
        channel = self.get_by_youtube_id(db, youtube_channel_id)
        if channel:
            return channel, False

        # Fetch from YouTube API
        youtube_data = youtube_client.get_channel_by_id(youtube_channel_id)
        if not youtube_data:
            raise ValueError(f"Channel not found: {youtube_channel_id}")

        # Create new channel
        channel = self.create_from_youtube(db, youtube_data)
        return channel, True

    def update_from_youtube(self, db: Session, channel: Channel) -> Channel:
        """
        Update channel with fresh data from YouTube API.

        Args:
            db: Database session
            channel: Channel to update

        Returns:
            Updated channel
        """
        youtube_data = youtube_client.get_channel_by_id(channel.youtube_channel_id)
        if not youtube_data:
            return channel

        channel.name = youtube_data.get("name", channel.name)
        channel.description = youtube_data.get("description", channel.description)
        channel.thumbnail_url = youtube_data.get("thumbnail_url", channel.thumbnail_url)
        channel.banner_url = youtube_data.get("banner_url", channel.banner_url)
        channel.subscriber_count = youtube_data.get("subscriber_count", channel.subscriber_count)
        channel.video_count = youtube_data.get("video_count", channel.video_count)
        channel.size_tier = self._calculate_size_tier(channel.subscriber_count or 0)
        channel.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(channel)

        return channel

    def set_classification(
        self,
        db: Session,
        channel: Channel,
        category: Optional[str] = None,
        format_type: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Channel:
        """
        Set channel classification fields.

        Args:
            db: Database session
            channel: Channel to update
            category: Channel category (tech, education, etc.)
            format_type: Content format (tutorials, vlogs, etc.)
            confidence: Classification confidence score

        Returns:
            Updated channel
        """
        if category:
            channel.category = category
        if format_type:
            channel.format_type = format_type
        if confidence is not None:
            channel.classification_confidence = confidence

        channel.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(channel)

        return channel

    def add_tag(
        self,
        db: Session,
        channel: Channel,
        tag_name: str,
        tag_value: Optional[str] = None,
    ) -> ChannelTag:
        """Add a tag to a channel."""
        # Check if tag already exists
        existing = db.query(ChannelTag).filter(
            ChannelTag.channel_id == channel.id,
            ChannelTag.tag_name == tag_name,
        ).first()

        if existing:
            existing.tag_value = tag_value
            db.commit()
            db.refresh(existing)
            return existing

        tag = ChannelTag(
            channel_id=channel.id,
            tag_name=tag_name,
            tag_value=tag_value,
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)

        return tag

    def remove_tag(self, db: Session, channel: Channel, tag_name: str) -> bool:
        """Remove a tag from a channel."""
        result = db.query(ChannelTag).filter(
            ChannelTag.channel_id == channel.id,
            ChannelTag.tag_name == tag_name,
        ).delete()
        db.commit()
        return result > 0

    def get_all_active(self, db: Session, limit: int = 100) -> list[Channel]:
        """Get all active channels."""
        return db.query(Channel).filter(
            Channel.is_active == True
        ).limit(limit).all()

    def _calculate_size_tier(self, subscriber_count: int) -> str:
        """Calculate size tier from subscriber count."""
        if subscriber_count < 10000:
            return "micro"
        elif subscriber_count < 100000:
            return "small"
        elif subscriber_count < 1000000:
            return "medium"
        elif subscriber_count < 10000000:
            return "large"
        else:
            return "mega"


# Singleton instance
channel_service = ChannelService()
