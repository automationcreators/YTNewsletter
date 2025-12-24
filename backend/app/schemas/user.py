"""Pydantic schemas for user-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user fields."""
    email: EmailStr
    display_name: Optional[str] = None


class UserResponse(UserBase):
    """User response for API."""
    id: UUID
    avatar_url: Optional[str] = None
    subscription_tier: str = "free"
    max_channels: int = 3
    beehiiv_subscriber_id: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """User profile with subscription info."""
    id: UUID
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_tier: str
    max_channels: int
    current_channel_count: int
    can_add_channel: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Fields that can be updated by user."""
    display_name: Optional[str] = None


class SubscriptionInfo(BaseModel):
    """User's subscription information."""
    tier: str
    max_channels: int
    current_channel_count: int
    channels_remaining: int
    is_unlimited: bool
