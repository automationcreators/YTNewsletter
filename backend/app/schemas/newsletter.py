"""Pydantic schemas for newsletter endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# Newsletter Generation Schemas

class NewsletterGenerateRequest(BaseModel):
    """Request to generate a newsletter."""
    days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Number of days to include videos from"
    )
    include_channels: Optional[list[UUID]] = Field(
        default=None,
        description="Specific channel IDs to include (None = all subscribed)"
    )
    title: Optional[str] = Field(
        default=None,
        description="Custom newsletter title"
    )


class VideoSummaryItem(BaseModel):
    """Video summary for newsletter display."""
    video_id: UUID
    youtube_video_id: str
    title: str
    channel_name: str
    channel_thumbnail: Optional[str] = None
    thumbnail_url: Optional[str] = None
    thumbnail_high_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    published_at: datetime
    view_count: Optional[int] = None

    # Summary content
    summary_text: str
    key_insights: list[str] = []
    notable_quotes: list[dict] = []
    timestamp_moments: list[dict] = []
    key_takeaways: list[str] = []


class NewsletterPreview(BaseModel):
    """Preview of a generated newsletter."""
    title: str
    subtitle: Optional[str] = None
    period_start: datetime
    period_end: datetime
    video_count: int
    videos: list[VideoSummaryItem]
    content_html: str


class NewsletterResponse(BaseModel):
    """Newsletter response."""
    id: UUID
    user_id: UUID
    title: str
    subtitle: Optional[str] = None
    period_start: datetime
    period_end: datetime
    video_count: int
    status: str
    beehiiv_post_id: Optional[str] = None
    beehiiv_url: Optional[str] = None
    sent_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NewsletterListResponse(BaseModel):
    """List of newsletters."""
    items: list[NewsletterResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Beehiiv Integration Schemas

class PublishToBeehiivRequest(BaseModel):
    """Request to publish newsletter to Beehiiv."""
    newsletter_id: UUID
    schedule_for: Optional[datetime] = Field(
        default=None,
        description="Schedule for future delivery (ISO 8601). If None, creates as draft."
    )
    send_to_free: bool = True
    send_to_premium: bool = True


class PublishToBeehiivResponse(BaseModel):
    """Response from Beehiiv publish."""
    newsletter_id: UUID
    beehiiv_post_id: str
    beehiiv_url: Optional[str] = None
    status: str
    scheduled_for: Optional[datetime] = None


# Template Schemas

class NewsletterTemplateCreate(BaseModel):
    """Create a new newsletter template."""
    name: str
    description: Optional[str] = None
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    video_card_html: Optional[str] = None
    primary_color: str = "#3B82F6"
    secondary_color: str = "#1F2937"
    background_color: str = "#F9FAFB"
    is_default: bool = False


class NewsletterTemplateUpdate(BaseModel):
    """Update a newsletter template."""
    name: Optional[str] = None
    description: Optional[str] = None
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    video_card_html: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    background_color: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class NewsletterTemplateResponse(BaseModel):
    """Newsletter template response."""
    id: UUID
    name: str
    description: Optional[str] = None
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    video_card_html: Optional[str] = None
    primary_color: str
    secondary_color: str
    background_color: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Export Schemas

class ExportNewsletterRequest(BaseModel):
    """Request to export newsletter HTML."""
    newsletter_id: UUID
    format: str = Field(
        default="html",
        description="Export format: html or markdown"
    )


class ExportNewsletterResponse(BaseModel):
    """Exported newsletter content."""
    newsletter_id: UUID
    title: str
    content: str
    format: str
