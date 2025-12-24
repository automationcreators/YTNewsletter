"""Pydantic schemas for video-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class VideoBase(BaseModel):
    """Base video fields."""
    youtube_video_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: datetime
    duration_seconds: Optional[int] = None


class VideoStats(BaseModel):
    """Video statistics."""
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None


class VideoResponse(VideoBase):
    """Full video response."""
    id: UUID
    channel_id: UUID
    thumbnail_high_url: Optional[str] = None

    # Stats
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None

    # Processing status
    transcript_status: str = "pending"
    summary_status: str = "pending"

    created_at: datetime

    class Config:
        from_attributes = True


class TimestampMoment(BaseModel):
    """A notable moment in the video."""
    timestamp: int  # Seconds from start
    description: str


class NotableQuote(BaseModel):
    """A quote from the video."""
    quote: str
    timestamp: Optional[int] = None


class VideoSummaryResponse(BaseModel):
    """Video summary details."""
    id: UUID
    summary_text: str
    key_insights: list[str] = []
    notable_quotes: list[NotableQuote] = []
    timestamp_moments: list[TimestampMoment] = []
    key_takeaways: list[str] = []

    llm_provider: str
    llm_model: str
    created_at: datetime

    class Config:
        from_attributes = True


class VideoWithSummary(VideoResponse):
    """Video with its summary included."""
    summary: Optional[VideoSummaryResponse] = None
    channel_name: Optional[str] = None


class VideoListResponse(BaseModel):
    """Paginated list of videos."""
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
