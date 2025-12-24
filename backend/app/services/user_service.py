"""User service for database operations."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.user import User
from app.services.google_oauth import GoogleUserInfo


class UserService:
    """Service for user-related database operations."""

    def get_by_id(self, db: Session, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    def get_by_google_id(self, db: Session, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        return db.query(User).filter(User.google_id == google_id).first()

    def create_from_google(self, db: Session, google_info: GoogleUserInfo) -> User:
        """
        Create a new user from Google OAuth info.

        Args:
            db: Database session
            google_info: User info from Google

        Returns:
            Created user
        """
        user = User(
            email=google_info.email,
            google_id=google_info.google_id,
            display_name=google_info.name,
            avatar_url=google_info.picture,
            last_login_at=datetime.utcnow(),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    def get_or_create_from_google(
        self,
        db: Session,
        google_info: GoogleUserInfo,
    ) -> tuple[User, bool]:
        """
        Get existing user or create new one from Google OAuth.

        Args:
            db: Database session
            google_info: User info from Google

        Returns:
            Tuple of (user, is_new)
        """
        # Try to find by Google ID first
        user = self.get_by_google_id(db, google_info.google_id)
        if user:
            # Update last login
            user.last_login_at = datetime.utcnow()
            # Update profile info if changed
            if google_info.name and user.display_name != google_info.name:
                user.display_name = google_info.name
            if google_info.picture and user.avatar_url != google_info.picture:
                user.avatar_url = google_info.picture
            db.commit()
            return user, False

        # Try to find by email (in case they registered differently)
        user = self.get_by_email(db, google_info.email)
        if user:
            # Link Google account to existing user
            user.google_id = google_info.google_id
            user.last_login_at = datetime.utcnow()
            if not user.avatar_url and google_info.picture:
                user.avatar_url = google_info.picture
            db.commit()
            return user, False

        # Create new user
        user = self.create_from_google(db, google_info)
        return user, True

    def update_last_login(self, db: Session, user: User) -> User:
        """Update user's last login timestamp."""
        user.last_login_at = datetime.utcnow()
        db.commit()
        return user

    def update_subscription_tier(
        self,
        db: Session,
        user: User,
        tier: str,
        max_channels: Optional[int] = None,
    ) -> User:
        """
        Update user's subscription tier.

        Args:
            db: Database session
            user: User to update
            tier: New subscription tier
            max_channels: Optional custom channel limit

        Returns:
            Updated user
        """
        user.subscription_tier = tier

        if max_channels is not None:
            user.max_channels = max_channels
        else:
            # Set default based on tier
            tier_defaults = {
                "free": 3,
                "premium": 20,
                "enterprise": -1,  # unlimited
            }
            user.max_channels = tier_defaults.get(tier, 3)

        db.commit()
        db.refresh(user)
        return user

    def link_beehiiv(
        self,
        db: Session,
        user: User,
        beehiiv_subscriber_id: str,
    ) -> User:
        """Link Beehiiv subscriber ID to user."""
        user.beehiiv_subscriber_id = beehiiv_subscriber_id
        db.commit()
        db.refresh(user)
        return user

    def get_active_subscription_count(self, db: Session, user: User) -> int:
        """Get count of user's active channel subscriptions."""
        return len([s for s in user.channel_subscriptions if s.is_active])

    def can_subscribe_to_channel(self, db: Session, user: User) -> bool:
        """Check if user can subscribe to another channel based on tier limits."""
        if user.max_channels == -1:  # Unlimited
            return True

        current_count = self.get_active_subscription_count(db, user)
        return current_count < user.max_channels


# Singleton instance
user_service = UserService()
