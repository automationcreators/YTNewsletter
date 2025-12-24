import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class VideoSummary(Base):
    __tablename__ = "video_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Summary components
    summary_text = Column(Text, nullable=False)
    key_insights = Column(JSONB)  # ["insight1", "insight2", ...]
    notable_quotes = Column(JSONB)  # [{"quote": "...", "timestamp": 123}, ...]
    timestamp_moments = Column(JSONB)  # [{"timestamp": 123, "description": "..."}, ...]
    key_takeaways = Column(JSONB)  # ["takeaway1", "takeaway2", ...]

    # Metadata
    llm_provider = Column(String(50), nullable=False)
    llm_model = Column(String(100), nullable=False)
    prompt_template_used = Column(Text)

    # Cost tracking
    generation_tokens = Column(Integer)
    generation_cost_cents = Column(Integer)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="summary")

    def __repr__(self):
        return f"<VideoSummary video={self.video_id}>"
