"""Newsletter model for tracking generated and sent newsletters."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class NewsletterStatus(str, enum.Enum):
    """Newsletter status enum."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"


class Newsletter(Base):
    """Track generated newsletters."""
    __tablename__ = "newsletters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500))
    content_html = Column(Text, nullable=False)

    # Period covered
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Videos included
    video_ids = Column(JSONB)  # List of video UUIDs included
    video_count = Column(Integer, default=0)

    # Status
    status = Column(String(20), default=NewsletterStatus.DRAFT.value)

    # Beehiiv integration
    beehiiv_post_id = Column(String(100))
    beehiiv_url = Column(String(500))
    sent_at = Column(DateTime(timezone=True))
    scheduled_for = Column(DateTime(timezone=True))

    # Tracking
    is_personalized = Column(Boolean, default=True)  # Per-user newsletter

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="newsletters")

    def __repr__(self):
        return f"<Newsletter {self.title} user={self.user_id}>"


class NewsletterTemplate(Base):
    """Reusable newsletter templates."""
    __tablename__ = "newsletter_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Template components
    header_html = Column(Text)
    footer_html = Column(Text)
    video_card_html = Column(Text)  # Template for each video summary card

    # Styling
    primary_color = Column(String(7), default="#3B82F6")
    secondary_color = Column(String(7), default="#1F2937")
    background_color = Column(String(7), default="#F9FAFB")

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NewsletterTemplate {self.name}>"
