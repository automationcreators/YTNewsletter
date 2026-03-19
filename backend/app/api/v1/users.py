"""User API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.user_service import user_service
from app.schemas.user import UserResponse, UserProfile, UserUpdate, SubscriptionInfo

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current authenticated user's profile.

    Includes subscription info and channel limits.
    """
    current_count = user_service.get_active_subscription_count(db, current_user)
    can_add = user_service.can_subscribe_to_channel(db, current_user)

    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        subscription_tier=current_user.subscription_tier,
        max_channels=current_user.max_channels,
        current_channel_count=current_count,
        can_add_channel=can_add,
        created_at=current_user.created_at,
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.

    Only display_name can be updated by the user directly.
    """
    if update.display_name is not None:
        current_user.display_name = update.display_name
        db.commit()
        db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.get("/me/subscription", response_model=SubscriptionInfo)
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's subscription information.
    """
    current_count = user_service.get_active_subscription_count(db, current_user)
    max_channels = current_user.max_channels
    is_unlimited = max_channels == -1

    return SubscriptionInfo(
        tier=current_user.subscription_tier,
        max_channels=max_channels,
        current_channel_count=current_count,
        channels_remaining=0 if is_unlimited else max(0, max_channels - current_count),
        is_unlimited=is_unlimited,
    )


@router.get("/me/subscriptions")
async def get_user_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's channel subscriptions.
    """
    subscriptions = [
        {
            "id": str(sub.id),
            "channel_id": str(sub.channel_id),
            "channel": {
                "id": str(sub.channel.id),
                "youtube_channel_id": sub.channel.youtube_channel_id,
                "name": sub.channel.name,
                "thumbnail_url": sub.channel.thumbnail_url,
                "category": sub.channel.category,
            } if sub.channel else None,
            "is_active": sub.is_active,
            "subscribed_at": sub.subscribed_at.isoformat() if sub.subscribed_at else None,
        }
        for sub in current_user.channel_subscriptions
        if sub.is_active
    ]

    return {
        "items": subscriptions,
        "count": len(subscriptions),
        "max_channels": current_user.max_channels,
    }
