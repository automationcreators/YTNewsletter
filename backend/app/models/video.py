import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    youtube_video_id = Column(String(255), unique=True, nullable=False, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text)
    thumbnail_url = Column(String(500))
    thumbnail_high_url = Column(String(500))  # Higher resolution for emails

    duration_seconds = Column(Integer)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Stats
    view_count = Column(BigInteger)
    like_count = Column(BigInteger)
    comment_count = Column(BigInteger)

    # Processing status
    transcript_status = Column(String(50), default="pending", index=True)
    # pending, fetched, whisper_processed, failed, unavailable
    summary_status = Column(String(50), default="pending", index=True)
    # pending, processing, completed, failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    channel = relationship("Channel", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    summary = relationship("VideoSummary", back_populates="video", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video {self.title[:50]}>"
