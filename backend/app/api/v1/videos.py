"""Video API endpoints."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.models.user import User
from app.integrations.youtube_client import youtube_client, YouTubeAPIError
from app.services.channel_resolver import channel_resolver
from app.services.transcript_service import transcript_service
from app.services.video_service import video_service
from app.services.summary_service import summary_service
from app.schemas.transcript import TranscriptResponse, TranscriptAvailability
from app.schemas.summary import (
    SummaryResponse,
    VideoWithSummaryResponse,
    VideoFeedItem,
    VideoFeedResponse,
    GenerateSummaryRequest,
)

router = APIRouter()


@router.get("/feed", response_model=VideoFeedResponse)
async def get_video_feed(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get video feed from all subscribed channels.

    Returns recent videos from channels the user is subscribed to.
    """
    offset = (page - 1) * page_size

    videos = video_service.get_videos_for_user(
        db,
        current_user.id,
        days=days,
        limit=page_size + 1,  # Fetch one extra to check has_more
    )

    # Check if there are more
    has_more = len(videos) > page_size
    videos = videos[:page_size]

    items = [
        VideoFeedItem(
            id=v.id,
            youtube_video_id=v.youtube_video_id,
            title=v.title,
            thumbnail_url=v.thumbnail_url,
            duration_seconds=v.duration_seconds,
            published_at=v.published_at,
            view_count=v.view_count,
            channel_name=v.channel.name if v.channel else "Unknown",
            channel_thumbnail=v.channel.thumbnail_url if v.channel else None,
            summary_status=v.summary_status,
            has_summary=v.summary is not None,
        )
        for v in videos
    ]

    return VideoFeedResponse(
        items=items,
        total=len(items),  # Would need count query for accurate total
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/{video_id}")
async def get_video(video_id: str):
    """
    Get detailed information about a specific video.

    Args:
        video_id: YouTube video ID (11 characters)
    """
    # Handle URL input
    extracted_id = channel_resolver.extract_video_id(video_id)
    if extracted_id:
        video_id = extracted_id

    try:
        video_data = youtube_client.get_video_by_id(video_id)

        if not video_data:
            raise HTTPException(status_code=404, detail="Video not found")

        return video_data
    except YouTubeAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{video_id}/transcript", response_model=TranscriptResponse)
async def get_video_transcript(
    video_id: str,
    language: str = Query("en", description="Preferred language code"),
    use_whisper: bool = Query(True, description="Use Whisper fallback if no transcript"),
):
    """
    Get transcript for a video.

    Tries YouTube captions first, falls back to Whisper transcription if enabled.

    Args:
        video_id: YouTube video ID
        language: Preferred language code
        use_whisper: Whether to use Whisper as fallback
    """
    # Handle URL input
    extracted_id = channel_resolver.extract_video_id(video_id)
    if extracted_id:
        video_id = extracted_id

    transcript = transcript_service.get_transcript(
        video_id,
        languages=[language, "en"],
        use_whisper_fallback=use_whisper,
    )

    if not transcript:
        raise HTTPException(
            status_code=404,
            detail="No transcript available for this video",
        )

    return TranscriptResponse(**transcript)


@router.get("/{video_id}/transcript/availability", response_model=TranscriptAvailability)
async def check_transcript_availability(video_id: str):
    """
    Check what transcript options are available for a video.

    Args:
        video_id: YouTube video ID
    """
    # Handle URL input
    extracted_id = channel_resolver.extract_video_id(video_id)
    if extracted_id:
        video_id = extracted_id

    availability = transcript_service.check_transcript_availability(video_id)
    return TranscriptAvailability(**availability)


@router.get("/db/{video_id}", response_model=VideoWithSummaryResponse)
async def get_stored_video(
    video_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a video from the database with its summary.

    Args:
        video_id: Internal video UUID
    """
    video = video_service.get_by_id(db, video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    summary_response = None
    if video.summary:
        summary_response = SummaryResponse(
            id=video.summary.id,
            video_id=video.id,
            summary_text=video.summary.summary_text,
            key_insights=video.summary.key_insights or [],
            notable_quotes=video.summary.notable_quotes or [],
            timestamp_moments=video.summary.timestamp_moments or [],
            key_takeaways=video.summary.key_takeaways or [],
            llm_provider=video.summary.llm_provider,
            llm_model=video.summary.llm_model,
            generation_tokens=video.summary.generation_tokens,
            created_at=video.summary.created_at,
        )

    return VideoWithSummaryResponse(
        id=video.id,
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        description=video.description,
        thumbnail_url=video.thumbnail_url,
        thumbnail_high_url=video.thumbnail_high_url,
        duration_seconds=video.duration_seconds,
        published_at=video.published_at,
        view_count=video.view_count,
        channel_id=video.channel_id,
        channel_name=video.channel.name if video.channel else "Unknown",
        channel_thumbnail=video.channel.thumbnail_url if video.channel else None,
        transcript_status=video.transcript_status,
        summary_status=video.summary_status,
        summary=summary_response,
    )


@router.get("/db/{video_id}/summary", response_model=SummaryResponse)
async def get_video_summary(
    video_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get the summary for a stored video.

    Args:
        video_id: Internal video UUID
    """
    video = video_service.get_by_id(db, video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not video.summary:
        raise HTTPException(
            status_code=404,
            detail="Summary not yet generated for this video",
        )

    return SummaryResponse(
        id=video.summary.id,
        video_id=video.id,
        summary_text=video.summary.summary_text,
        key_insights=video.summary.key_insights or [],
        notable_quotes=video.summary.notable_quotes or [],
        timestamp_moments=video.summary.timestamp_moments or [],
        key_takeaways=video.summary.key_takeaways or [],
        llm_provider=video.summary.llm_provider,
        llm_model=video.summary.llm_model,
        generation_tokens=video.summary.generation_tokens,
        created_at=video.summary.created_at,
    )


@router.post("/db/{video_id}/summary", response_model=SummaryResponse)
async def generate_video_summary(
    video_id: UUID,
    request: GenerateSummaryRequest = GenerateSummaryRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a summary for a video.

    Requires the video to have a transcript available.
    """
    video = video_service.get_by_id(db, video_id)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Check for transcript
    if not video.transcript and video.transcript_status != "fetched":
        raise HTTPException(
            status_code=400,
            detail="Video transcript not available. Fetch transcript first.",
        )

    try:
        summary = summary_service.generate_summary(
            db,
            video,
            force_regenerate=request.force_regenerate,
        )

        if not summary:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate summary",
            )

        return SummaryResponse(
            id=summary.id,
            video_id=video.id,
            summary_text=summary.summary_text,
            key_insights=summary.key_insights or [],
            notable_quotes=summary.notable_quotes or [],
            timestamp_moments=summary.timestamp_moments or [],
            key_takeaways=summary.key_takeaways or [],
            llm_provider=summary.llm_provider,
            llm_model=summary.llm_model,
            generation_tokens=summary.generation_tokens,
            created_at=summary.created_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {str(e)}",
        )
