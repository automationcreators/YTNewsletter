"""Subscription service for managing user channel subscriptions."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.channel import Channel
from app.models.subscription import UserChannelSubscription
from app.services.channel_service import channel_service


class SubscriptionError(Exception):
    """Base exception for subscription errors."""
    pass


class TierLimitExceeded(SubscriptionError):
    """Raised when user exceeds their tier's channel limit."""
    pass


class AlreadySubscribed(SubscriptionError):
    """Raised when user is already subscribed to a channel."""
    pass


class NotSubscribed(SubscriptionError):
    """Raised when user is not subscribed to a channel."""
    pass


class SubscriptionService:
    """Service for managing user channel subscriptions."""

    def get_subscription(
        self,
        db: Session,
        user: User,
        channel: Channel,
    ) -> Optional[UserChannelSubscription]:
        """Get a user's subscription to a specific channel."""
        return db.query(UserChannelSubscription).filter(
            UserChannelSubscription.user_id == user.id,
            UserChannelSubscription.channel_id == channel.id,
        ).first()

    def get_active_subscription(
        self,
        db: Session,
        user: User,
        channel: Channel,
    ) -> Optional[UserChannelSubscription]:
        """Get a user's active subscription to a specific channel."""
        return db.query(UserChannelSubscription).filter(
            UserChannelSubscription.user_id == user.id,
            UserChannelSubscription.channel_id == channel.id,
            UserChannelSubscription.is_active == True,
        ).first()

    def get_user_subscriptions(
        self,
        db: Session,
        user: User,
        active_only: bool = True,
    ) -> list[UserChannelSubscription]:
        """Get all subscriptions for a user."""
        query = db.query(UserChannelSubscription).filter(
            UserChannelSubscription.user_id == user.id,
        )

        if active_only:
            query = query.filter(UserChannelSubscription.is_active == True)

        return query.all()

    def get_subscription_count(self, db: Session, user: User) -> int:
        """Get count of user's active subscriptions."""
        return db.query(UserChannelSubscription).filter(
            UserChannelSubscription.user_id == user.id,
            UserChannelSubscription.is_active == True,
        ).count()

    def can_subscribe(self, db: Session, user: User) -> bool:
        """Check if user can subscribe to another channel."""
        if user.max_channels == -1:  # Unlimited
            return True

        current_count = self.get_subscription_count(db, user)
        return current_count < user.max_channels

    def get_remaining_slots(self, db: Session, user: User) -> int:
        """Get number of remaining channel slots for user."""
        if user.max_channels == -1:
            return -1  # Unlimited

        current_count = self.get_subscription_count(db, user)
        return max(0, user.max_channels - current_count)

    def subscribe(
        self,
        db: Session,
        user: User,
        youtube_channel_id: str,
    ) -> UserChannelSubscription:
        """
        Subscribe a user to a YouTube channel.

        Args:
            db: Database session
            user: User subscribing
            youtube_channel_id: YouTube channel ID

        Returns:
            Created or reactivated subscription

        Raises:
            TierLimitExceeded: If user has reached their channel limit
            AlreadySubscribed: If user is already subscribed
        """
        # Check tier limits
        if not self.can_subscribe(db, user):
            raise TierLimitExceeded(
                f"You have reached your limit of {user.max_channels} channels. "
                f"Upgrade your subscription to add more channels."
            )

        # Get or create channel in database
        channel, _ = channel_service.get_or_create_from_youtube(db, youtube_channel_id)

        # Check for existing subscription
        existing = self.get_subscription(db, user, channel)

        if existing:
            if existing.is_active:
                raise AlreadySubscribed(
                    f"You are already subscribed to {channel.name}"
                )

            # Reactivate inactive subscription
            existing.is_active = True
            existing.unsubscribed_at = None
            existing.subscribed_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        # Create new subscription
        subscription = UserChannelSubscription(
            user_id=user.id,
            channel_id=channel.id,
            is_active=True,
            notification_enabled=True,
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        return subscription

    def unsubscribe(
        self,
        db: Session,
        user: User,
        youtube_channel_id: str,
    ) -> UserChannelSubscription:
        """
        Unsubscribe a user from a YouTube channel.

        Args:
            db: Database session
            user: User unsubscribing
            youtube_channel_id: YouTube channel ID

        Returns:
            Deactivated subscription

        Raises:
            NotSubscribed: If user is not subscribed to the channel
        """
        # Get channel from database
        channel = channel_service.get_by_youtube_id(db, youtube_channel_id)
        if not channel:
            raise NotSubscribed("You are not subscribed to this channel")

        # Get active subscription
        subscription = self.get_active_subscription(db, user, channel)
        if not subscription:
            raise NotSubscribed("You are not subscribed to this channel")

        # Deactivate subscription
        subscription.is_active = False
        subscription.unsubscribed_at = datetime.utcnow()

        db.commit()
        db.refresh(subscription)

        return subscription

    def toggle_notifications(
        self,
        db: Session,
        user: User,
        youtube_channel_id: str,
        enabled: bool,
    ) -> UserChannelSubscription:
        """Toggle notifications for a subscription."""
        channel = channel_service.get_by_youtube_id(db, youtube_channel_id)
        if not channel:
            raise NotSubscribed("You are not subscribed to this channel")

        subscription = self.get_active_subscription(db, user, channel)
        if not subscription:
            raise NotSubscribed("You are not subscribed to this channel")

        subscription.notification_enabled = enabled
        db.commit()
        db.refresh(subscription)

        return subscription

    def get_channel_subscriber_count(self, db: Session, channel: Channel) -> int:
        """Get number of users subscribed to a channel."""
        return db.query(UserChannelSubscription).filter(
            UserChannelSubscription.channel_id == channel.id,
            UserChannelSubscription.is_active == True,
        ).count()

    def is_subscribed(
        self,
        db: Session,
        user: User,
        youtube_channel_id: str,
    ) -> bool:
        """Check if user is subscribed to a channel."""
        channel = channel_service.get_by_youtube_id(db, youtube_channel_id)
        if not channel:
            return False

        subscription = self.get_active_subscription(db, user, channel)
        return subscription is not None


# Singleton instance
subscription_service = SubscriptionService()
