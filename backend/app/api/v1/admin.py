"""Admin API endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.channel import Channel
from app.models.video import Video
from app.models.summary import VideoSummary
from app.models.subscription import UserChannelSubscription
from app.models.prompt_template import PromptTemplate
from app.models.system_config import SystemConfig
from app.services.prompt_service import prompt_service, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT
from app.services.classification_service import classification_service
from app.services.channel_service import channel_service
from app.services.transcript_service import transcript_service
from app.integrations.llm_client import LLMFactory
from app.integrations.youtube_client import youtube_client
from app.schemas.admin import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTestRequest,
    PromptTestResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
    SystemStatsResponse,
    ClassifyChannelRequest,
    ClassifyChannelResponse,
    ClassifyBatchRequest,
)

router = APIRouter()


# ============ Stats Endpoints ============

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get system statistics.
    """
    # Basic counts
    total_users = db.query(func.count(User.id)).scalar()
    total_channels = db.query(func.count(Channel.id)).scalar()
    total_videos = db.query(func.count(Video.id)).scalar()
    total_summaries = db.query(func.count(VideoSummary.id)).scalar()
    total_subscriptions = db.query(func.count(UserChannelSubscription.id)).filter(
        UserChannelSubscription.is_active == True
    ).scalar()

    # Users by tier
    tier_counts = db.query(
        User.subscription_tier,
        func.count(User.id)
    ).group_by(User.subscription_tier).all()
    users_by_tier = {tier: count for tier, count in tier_counts}

    # Channels by category
    category_counts = db.query(
        Channel.category,
        func.count(Channel.id)
    ).group_by(Channel.category).all()
    channels_by_category = {cat or "unclassified": count for cat, count in category_counts}

    # Recent signups (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_signups = db.query(func.count(User.id)).filter(
        User.created_at >= week_ago
    ).scalar()

    # Summaries generated today
    today = datetime.utcnow().date()
    summaries_today = db.query(func.count(VideoSummary.id)).filter(
        func.date(VideoSummary.created_at) == today
    ).scalar()

    return SystemStatsResponse(
        total_users=total_users,
        total_channels=total_channels,
        total_videos=total_videos,
        total_summaries=total_summaries,
        total_subscriptions=total_subscriptions,
        users_by_tier=users_by_tier,
        channels_by_category=channels_by_category,
        recent_signups=recent_signups,
        summaries_generated_today=summaries_today,
    )


# ============ Prompt Template Endpoints ============

@router.get("/prompt-templates", response_model=list[PromptTemplateResponse])
async def list_prompt_templates(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all prompt templates."""
    templates = prompt_service.get_all_templates(db, active_only=active_only)
    return templates


@router.post("/prompt-templates", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt_template(
    template: PromptTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new prompt template."""
    new_template = prompt_service.create_template(
        db,
        name=template.name,
        system_prompt=template.system_prompt,
        user_prompt_template=template.user_prompt_template,
        category=template.category,
        format_type=template.format_type,
        llm_provider=template.llm_provider,
        llm_model=template.llm_model,
        is_default=template.is_default,
    )
    return new_template


@router.get("/prompt-templates/{template_id}", response_model=PromptTemplateResponse)
async def get_prompt_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific prompt template."""
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.patch("/prompt-templates/{template_id}", response_model=PromptTemplateResponse)
async def update_prompt_template(
    template_id: UUID,
    update: PromptTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a prompt template."""
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Handle setting as default
    if update.is_default:
        db.query(PromptTemplate).filter(
            PromptTemplate.is_default == True
        ).update({"is_default": False})

    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/prompt-templates/{template_id}")
async def delete_prompt_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete (deactivate) a prompt template."""
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.is_active = False
    db.commit()

    return {"message": "Template deactivated"}


@router.post("/prompt-templates/test", response_model=PromptTestResponse)
async def test_prompt_template(
    request: PromptTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test a prompt template with a sample video.

    Fetches the video transcript and generates a summary using the provided prompt.
    """
    # Get video info from YouTube
    video_data = youtube_client.get_video_by_id(request.youtube_video_id)
    if not video_data:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get transcript
    transcript_data = transcript_service.get_transcript(
        request.youtube_video_id,
        use_whisper_fallback=False,  # Don't use Whisper for testing
    )
    if not transcript_data:
        raise HTTPException(
            status_code=400,
            detail="No transcript available for this video"
        )

    # Use provided prompts or defaults
    system_prompt = request.system_prompt or DEFAULT_SYSTEM_PROMPT
    user_prompt_template = request.user_prompt_template or DEFAULT_USER_PROMPT

    # Format user prompt
    user_prompt = user_prompt_template.format(
        title=video_data["title"],
        channel_name=video_data.get("channel_id", "Unknown"),
        transcript=transcript_data["content"][:10000],  # Limit transcript size
        duration="Unknown",
    )

    # Get LLM client
    llm_client = LLMFactory.create(
        provider=request.llm_provider,
        model=request.llm_model,
    )

    # Generate summary
    response = llm_client.generate(
        prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=2000,
        temperature=0.7,
    )

    # Parse response
    import json
    import re
    try:
        json_match = re.search(r'\{[\s\S]*\}', response.content)
        if json_match:
            summary_data = json.loads(json_match.group())
        else:
            summary_data = {"raw_response": response.content}
    except json.JSONDecodeError:
        summary_data = {"raw_response": response.content}

    return PromptTestResponse(
        video_title=video_data["title"],
        channel_name=video_data.get("channel_id", "Unknown"),
        transcript_preview=transcript_data["content"][:500] + "...",
        generated_summary=summary_data,
        tokens_used=response.total_tokens,
        llm_provider=response.provider,
        llm_model=response.model,
    )


# ============ System Config Endpoints ============

@router.get("/config", response_model=list[SystemConfigResponse])
async def list_system_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all system configuration values."""
    configs = db.query(SystemConfig).all()
    return configs


@router.get("/config/{key}", response_model=SystemConfigResponse)
async def get_system_config(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific configuration value."""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config key not found")
    return config


@router.put("/config/{key}", response_model=SystemConfigResponse)
async def update_system_config(
    key: str,
    update: SystemConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a configuration value."""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()

    if config:
        config.value = update.value
        if update.description:
            config.description = update.description
    else:
        config = SystemConfig(
            key=key,
            value=update.value,
            description=update.description,
        )
        db.add(config)

    db.commit()
    db.refresh(config)
    return config


# ============ Classification Endpoints ============

@router.post("/classify", response_model=ClassifyChannelResponse)
async def classify_channel(
    request: ClassifyChannelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Classify a YouTube channel using LLM.

    Creates the channel if it doesn't exist in the database.
    """
    # Get or create channel
    channel, _ = channel_service.get_or_create_from_youtube(
        db, request.youtube_channel_id
    )

    # Classify
    result = classification_service.classify_channel(
        db, channel, force_reclassify=request.force_reclassify
    )

    return ClassifyChannelResponse(
        channel_id=channel.id,
        channel_name=channel.name,
        category=result["category"],
        format_type=result["format_type"],
        confidence=result.get("confidence", 0.5),
        tags=result.get("tags", []),
        reasoning=result.get("reasoning"),
        already_classified=result.get("already_classified", False),
    )


@router.post("/classify/batch")
async def classify_channels_batch(
    request: ClassifyBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Classify unclassified channels in batch.
    """
    # Get unclassified channels
    channels = classification_service.get_unclassified_channels(db, limit=request.limit)

    if not channels:
        return {"message": "No unclassified channels found", "classified": 0}

    # Classify them
    results = classification_service.classify_channel_batch(db, channels)

    return {
        "message": f"Classified {len(results)} channels",
        "results": results,
    }
