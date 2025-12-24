"""Pydantic schemas for channel-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChannelBase(BaseModel):
    """Base channel fields."""
    youtube_channel_id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: Optional[int] = None


class ChannelCreate(ChannelBase):
    """Schema for creating a new channel."""
    banner_url: Optional[str] = None
    video_count: Optional[int] = None
    custom_url: Optional[str] = None


class ChannelClassification(BaseModel):
    """Channel classification details."""
    category: Optional[str] = None
    size_tier: Optional[str] = None
    format_type: Optional[str] = None
    tags: list[str] = []


class ChannelResponse(ChannelBase):
    """Full channel response."""
    id: UUID
    banner_url: Optional[str] = None
    video_count: Optional[int] = None
    custom_url: Optional[str] = None

    # Classification
    category: Optional[str] = None
    size_tier: Optional[str] = None
    format_type: Optional[str] = None

    # Metadata
    is_active: bool = True
    last_video_check_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelSearchResult(BaseModel):
    """Search result item."""
    youtube_channel_id: str
    name: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: Optional[int] = None
    is_subscribed: bool = False


class ChannelResolveRequest(BaseModel):
    """Request to resolve a channel from various input formats."""
    input: str = Field(
        ...,
        description="Channel ID, URL, handle (@username), or search query",
        examples=["@mkbhd", "https://youtube.com/channel/UCxxxxxx", "UCxxxxxx"],
    )


class ChannelResolveResponse(BaseModel):
    """Response from channel resolution."""
    found: bool
    channel: Optional[ChannelSearchResult] = None
    message: Optional[str] = None


class ChannelListResponse(BaseModel):
    """Paginated list of channels."""
    items: list[ChannelResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
