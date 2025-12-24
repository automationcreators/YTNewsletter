"""Pydantic schemas for subscription-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class SubscribeRequest(BaseModel):
    """Request to subscribe to a channel."""
    youtube_channel_id: str


class SubscriptionResponse(BaseModel):
    """Subscription response."""
    id: UUID
    channel_id: UUID
    youtube_channel_id: str
    channel_name: str
    channel_thumbnail: Optional[str] = None
    is_active: bool
    notification_enabled: bool
    subscribed_at: datetime

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """List of subscriptions."""
    items: list[SubscriptionResponse]
    count: int
    max_channels: int
    remaining_slots: int
    is_unlimited: bool


class SubscriptionStatusResponse(BaseModel):
    """Status of a subscription check."""
    is_subscribed: bool
    subscription_id: Optional[UUID] = None
    subscribed_at: Optional[datetime] = None


class NotificationToggleRequest(BaseModel):
    """Request to toggle notifications."""
    enabled: bool
