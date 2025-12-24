import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    google_id = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255))
    avatar_url = Column(String(500))

    # Beehiiv integration
    beehiiv_subscriber_id = Column(String(255), unique=True, index=True)

    # Subscription tier
    subscription_tier = Column(String(50), default="free")  # free, premium, enterprise
    max_channels = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    channel_subscriptions = relationship(
        "UserChannelSubscription",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    newsletters = relationship(
        "Newsletter",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email}>"
