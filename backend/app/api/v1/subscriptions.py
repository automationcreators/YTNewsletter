"""Subscription API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.subscription_service import (
    subscription_service,
    TierLimitExceeded,
    AlreadySubscribed,
    NotSubscribed,
)
from app.services.channel_service import channel_service
from app.schemas.subscription import (
    SubscribeRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
    SubscriptionStatusResponse,
    NotificationToggleRequest,
)

router = APIRouter()


@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all active subscriptions for the current user.
    """
    subscriptions = subscription_service.get_user_subscriptions(db, current_user)
    remaining = subscription_service.get_remaining_slots(db, current_user)

    items = [
        SubscriptionResponse(
            id=sub.id,
            channel_id=sub.channel_id,
            youtube_channel_id=sub.channel.youtube_channel_id,
            channel_name=sub.channel.name,
            channel_thumbnail=sub.channel.thumbnail_url,
            is_active=sub.is_active,
            notification_enabled=sub.notification_enabled,
            subscribed_at=sub.subscribed_at,
        )
        for sub in subscriptions
    ]

    return SubscriptionListResponse(
        items=items,
        count=len(items),
        max_channels=current_user.max_channels,
        remaining_slots=remaining if remaining >= 0 else 999,
        is_unlimited=current_user.max_channels == -1,
    )


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_to_channel(
    request: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Subscribe to a YouTube channel.

    The channel will be added to your weekly newsletter.
    """
    try:
        subscription = subscription_service.subscribe(
            db,
            current_user,
            request.youtube_channel_id,
        )

        return SubscriptionResponse(
            id=subscription.id,
            channel_id=subscription.channel_id,
            youtube_channel_id=subscription.channel.youtube_channel_id,
            channel_name=subscription.channel.name,
            channel_thumbnail=subscription.channel.thumbnail_url,
            is_active=subscription.is_active,
            notification_enabled=subscription.notification_enabled,
            subscribed_at=subscription.subscribed_at,
        )

    except TierLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except AlreadySubscribed as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{youtube_channel_id}")
async def unsubscribe_from_channel(
    youtube_channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unsubscribe from a YouTube channel.

    The channel will be removed from your weekly newsletter.
    """
    try:
        subscription_service.unsubscribe(db, current_user, youtube_channel_id)
        return {"message": "Successfully unsubscribed"}

    except NotSubscribed as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{youtube_channel_id}/status", response_model=SubscriptionStatusResponse)
async def check_subscription_status(
    youtube_channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if user is subscribed to a channel.
    """
    channel = channel_service.get_by_youtube_id(db, youtube_channel_id)

    if not channel:
        return SubscriptionStatusResponse(is_subscribed=False)

    subscription = subscription_service.get_active_subscription(
        db, current_user, channel
    )

    if subscription:
        return SubscriptionStatusResponse(
            is_subscribed=True,
            subscription_id=subscription.id,
            subscribed_at=subscription.subscribed_at,
        )

    return SubscriptionStatusResponse(is_subscribed=False)


@router.patch("/{youtube_channel_id}/notifications")
async def toggle_notifications(
    youtube_channel_id: str,
    request: NotificationToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle notifications for a subscription.
    """
    try:
        subscription = subscription_service.toggle_notifications(
            db,
            current_user,
            youtube_channel_id,
            request.enabled,
        )

        return {
            "message": f"Notifications {'enabled' if request.enabled else 'disabled'}",
            "notification_enabled": subscription.notification_enabled,
        }

    except NotSubscribed as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
