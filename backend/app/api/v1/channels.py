"""Channel API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user_optional
from app.models.user import User
from app.integrations.youtube_client import youtube_client, YouTubeAPIError
from app.services.channel_resolver import channel_resolver
from app.services.subscription_service import subscription_service
from app.schemas.channel import (
    ChannelSearchResult,
    ChannelResolveRequest,
    ChannelResolveResponse,
)

router = APIRouter()


@router.get("/search", response_model=list[ChannelSearchResult])
async def search_channels(
    q: str = Query(..., min_length=1, description="Search query"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Search for YouTube channels by name or keyword.

    Returns a list of matching channels with basic info.
    If authenticated, includes subscription status.
    """
    try:
        results = youtube_client.search_channels(q, max_results=max_results)

        channels = []
        for r in results:
            is_subscribed = False
            if current_user:
                is_subscribed = subscription_service.is_subscribed(
                    db, current_user, r["youtube_channel_id"]
                )

            channels.append(ChannelSearchResult(
                youtube_channel_id=r["youtube_channel_id"],
                name=r["name"],
                description=r.get("description"),
                thumbnail_url=r.get("thumbnail_url"),
                is_subscribed=is_subscribed,
            ))

        return channels
    except YouTubeAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/resolve", response_model=ChannelResolveResponse)
async def resolve_channel(request: ChannelResolveRequest):
    """
    Resolve a channel from various input formats.

    Supports:
    - Channel ID (UCxxxxxx)
    - Channel URL (youtube.com/channel/UCxxxxxx)
    - Handle (@username or youtube.com/@username)
    - Custom URL (youtube.com/c/ChannelName)
    - Legacy username URL (youtube.com/user/username)
    - Search query (returns best match)
    """
    try:
        channel_data = channel_resolver.resolve(request.input)

        if not channel_data:
            return ChannelResolveResponse(
                found=False,
                message=f"No channel found for: {request.input}",
            )

        return ChannelResolveResponse(
            found=True,
            channel=ChannelSearchResult(
                youtube_channel_id=channel_data["youtube_channel_id"],
                name=channel_data["name"],
                description=channel_data.get("description"),
                thumbnail_url=channel_data.get("thumbnail_url"),
                subscriber_count=channel_data.get("subscriber_count"),
                is_subscribed=False,  # TODO: Check against user's subscriptions
            ),
        )
    except YouTubeAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{channel_id}", response_model=ChannelSearchResult)
async def get_channel(channel_id: str):
    """
    Get detailed information about a specific channel.

    Args:
        channel_id: YouTube channel ID (UCxxxxxx format)
    """
    try:
        channel_data = youtube_client.get_channel_by_id(channel_id)

        if not channel_data:
            raise HTTPException(status_code=404, detail="Channel not found")

        return ChannelSearchResult(
            youtube_channel_id=channel_data["youtube_channel_id"],
            name=channel_data["name"],
            description=channel_data.get("description"),
            thumbnail_url=channel_data.get("thumbnail_url"),
            subscriber_count=channel_data.get("subscriber_count"),
            is_subscribed=False,  # TODO: Check against user's subscriptions
        )
    except YouTubeAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{channel_id}/videos")
async def get_channel_videos(
    channel_id: str,
    max_results: int = Query(10, ge=1, le=50, description="Maximum results"),
    published_after: Optional[str] = Query(
        None,
        description="ISO 8601 datetime to filter videos (e.g., 2024-01-01T00:00:00Z)",
    ),
):
    """
    Get recent videos from a channel.

    Args:
        channel_id: YouTube channel ID
        max_results: Maximum number of videos to return
        published_after: Only return videos published after this date
    """
    try:
        videos = youtube_client.get_channel_videos(
            channel_id,
            max_results=max_results,
            published_after=published_after,
        )

        return {"items": videos, "count": len(videos)}
    except YouTubeAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
