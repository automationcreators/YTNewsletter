import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    youtube_channel_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    thumbnail_url = Column(String(500))
    banner_url = Column(String(500))
    subscriber_count = Column(BigInteger)
    video_count = Column(Integer)
    custom_url = Column(String(255))  # @handle format

    # Classification fields
    category = Column(String(100), index=True)  # tech, entertainment, education, etc.
    size_tier = Column(String(50))  # micro, small, medium, large, mega
    format_type = Column(String(100))  # tutorials, vlogs, interviews, podcasts, etc.

    # AI Prompt Configuration
    summary_prompt_template = Column(Text)  # Custom prompt override for this channel
    llm_provider = Column(String(50), default="anthropic")
    llm_model = Column(String(100))

    # Metadata
    last_video_check_at = Column(DateTime(timezone=True))
    classification_confidence = Column(Float)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tags = relationship("ChannelTag", back_populates="channel", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")
    subscriptions = relationship("UserChannelSubscription", back_populates="channel")

    def __repr__(self):
        return f"<Channel {self.name}>"


class ChannelTag(Base):
    __tablename__ = "channel_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    tag_name = Column(String(100), nullable=False, index=True)
    tag_value = Column(String(255))

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    channel = relationship("Channel", back_populates="tags")

    __table_args__ = (
        # Unique constraint on channel_id + tag_name
        {"sqlite_autoincrement": True},
    )

    def __repr__(self):
        return f"<ChannelTag {self.tag_name}={self.tag_value}>"
