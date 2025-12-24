"""Pydantic schemas for summary-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class TimestampMoment(BaseModel):
    """A notable moment in the video."""
    timestamp: int  # Seconds from start
    description: str


class NotableQuote(BaseModel):
    """A quote from the video."""
    quote: str
    timestamp: Optional[int] = None


class SummaryResponse(BaseModel):
    """Video summary response."""
    id: UUID
    video_id: UUID
    summary_text: str
    key_insights: list[str] = []
    notable_quotes: list[NotableQuote] = []
    timestamp_moments: list[TimestampMoment] = []
    key_takeaways: list[str] = []

    llm_provider: str
    llm_model: str
    generation_tokens: Optional[int] = None

    created_at: datetime

    class Config:
        from_attributes = True


class GenerateSummaryRequest(BaseModel):
    """Request to generate a summary."""
    force_regenerate: bool = False


class VideoWithSummaryResponse(BaseModel):
    """Video with its summary."""
    id: UUID
    youtube_video_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_high_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    published_at: datetime
    view_count: Optional[int] = None

    channel_id: UUID
    channel_name: str
    channel_thumbnail: Optional[str] = None

    transcript_status: str
    summary_status: str

    summary: Optional[SummaryResponse] = None

    class Config:
        from_attributes = True


class VideoFeedItem(BaseModel):
    """Video item in the feed."""
    id: UUID
    youtube_video_id: str
    title: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    published_at: datetime
    view_count: Optional[int] = None

    channel_name: str
    channel_thumbnail: Optional[str] = None

    summary_status: str
    has_summary: bool

    class Config:
        from_attributes = True


class VideoFeedResponse(BaseModel):
    """Paginated video feed."""
    items: list[VideoFeedItem]
    total: int
    page: int
    page_size: int
    has_more: bool
