"""Pydantic schemas for admin endpoints."""

from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field


# Prompt Template Schemas

class PromptTemplateBase(BaseModel):
    """Base prompt template fields."""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    format_type: Optional[str] = None
    system_prompt: str
    user_prompt_template: str
    llm_provider: Optional[str] = "anthropic"
    llm_model: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7


class PromptTemplateCreate(PromptTemplateBase):
    """Create a new prompt template."""
    is_default: bool = False


class PromptTemplateUpdate(BaseModel):
    """Update an existing prompt template."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    format_type: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class PromptTemplateResponse(PromptTemplateBase):
    """Prompt template response."""
    id: UUID
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptTestRequest(BaseModel):
    """Request to test a prompt template."""
    youtube_video_id: str = Field(
        ...,
        description="YouTube video ID to test the prompt with"
    )
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class PromptTestResponse(BaseModel):
    """Response from prompt test."""
    video_title: str
    channel_name: str
    transcript_preview: str
    generated_summary: dict
    tokens_used: int
    llm_provider: str
    llm_model: str


# System Config Schemas

class SystemConfigResponse(BaseModel):
    """System config response."""
    key: str
    value: Any
    description: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    """Update system config."""
    value: Any
    description: Optional[str] = None


# Stats Schemas

class SystemStatsResponse(BaseModel):
    """System statistics."""
    total_users: int
    total_channels: int
    total_videos: int
    total_summaries: int
    total_subscriptions: int

    users_by_tier: dict
    channels_by_category: dict
    recent_signups: int  # Last 7 days
    summaries_generated_today: int


# Classification Schemas

class ClassifyChannelRequest(BaseModel):
    """Request to classify a channel."""
    youtube_channel_id: str
    force_reclassify: bool = False


class ClassifyChannelResponse(BaseModel):
    """Classification result."""
    channel_id: UUID
    channel_name: str
    category: str
    format_type: str
    confidence: float
    tags: list[str]
    reasoning: Optional[str] = None
    already_classified: bool


class ClassifyBatchRequest(BaseModel):
    """Request to classify multiple channels."""
    limit: int = Field(default=10, ge=1, le=50)
    force_reclassify: bool = False
