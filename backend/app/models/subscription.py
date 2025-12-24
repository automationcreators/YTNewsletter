import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class UserChannelSubscription(Base):
    __tablename__ = "user_channel_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    is_active = Column(Boolean, default=True, index=True)
    notification_enabled = Column(Boolean, default=True)

    subscribed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    unsubscribed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="channel_subscriptions")
    channel = relationship("Channel", back_populates="subscriptions")

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),
    )

    def __repr__(self):
        return f"<UserChannelSubscription user={self.user_id} channel={self.channel_id}>"
