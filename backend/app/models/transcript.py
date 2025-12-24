import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False)

    content = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    source = Column(String(50), nullable=False)  # youtube_auto, youtube_manual, whisper

    word_count = Column(Integer)
    duration_coverage = Column(Float)  # Percentage of video covered by transcript

    # Timestamp segments for quote extraction
    # Format: [{"start": 0, "end": 5.2, "text": "..."}, ...]
    segments = Column(JSONB)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="transcript")

    def __repr__(self):
        return f"<Transcript video={self.video_id}>"
