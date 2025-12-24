"""Newsletter generation and delivery tasks."""

import logging
from datetime import datetime
from typing import Optional
from celery import shared_task
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.newsletter import Newsletter, NewsletterStatus
from app.models.subscription import UserChannelSubscription
from app.services.newsletter_service import newsletter_service
from app.integrations.beehiiv_client import beehiiv_client, BeehiivAPIError

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session for tasks."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@shared_task(
    bind=True,
    autoretry_for=(BeehiivAPIError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_user_newsletter(
    self,
    user_id: str,
    days: int = 7,
    publish_to_beehiiv: bool = False,
) -> dict:
    """
    Generate a newsletter for a specific user.

    Args:
        user_id: User UUID
        days: Number of days to include
        publish_to_beehiiv: Whether to publish to Beehiiv automatically

    Returns:
        Dict with newsletter generation results
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found: {user_id}")
            return {"error": "User not found", "user_id": user_id}

        # Check if user has active subscriptions
        sub_count = db.query(UserChannelSubscription).filter(
            UserChannelSubscription.user_id == user.id,
            UserChannelSubscription.is_active == True,
        ).count()

        if sub_count == 0:
            logger.info(f"User {user_id} has no active subscriptions, skipping newsletter")
            return {
                "user_id": str(user.id),
                "status": "skipped",
                "reason": "no_active_subscriptions",
            }

        logger.info(f"Generating newsletter for user: {user.email}")

        # Generate newsletter
        preview = newsletter_service.generate_newsletter(
            db,
            user,
            days=days,
        )

        if preview["video_count"] == 0:
            logger.info(f"No videos with summaries for user {user_id}")
            return {
                "user_id": str(user.id),
                "status": "skipped",
                "reason": "no_videos_with_summaries",
            }

        # Save newsletter
        newsletter = newsletter_service.save_newsletter(db, user, preview)

        result = {
            "user_id": str(user.id),
            "user_email": user.email,
            "newsletter_id": str(newsletter.id),
            "video_count": newsletter.video_count,
            "status": "generated",
        }

        # Optionally publish to Beehiiv
        if publish_to_beehiiv:
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                post = loop.run_until_complete(
                    beehiiv_client.create_post(
                        title=newsletter.title,
                        content_html=newsletter.content_html,
                        subtitle=newsletter.subtitle,
                        status="draft",
                    )
                )

                newsletter.beehiiv_post_id = post.get("id")
                newsletter.beehiiv_url = post.get("web_url")
                newsletter.status = NewsletterStatus.DRAFT.value
                db.commit()

                result["beehiiv_post_id"] = newsletter.beehiiv_post_id
                result["published_to_beehiiv"] = True

            except BeehiivAPIError as e:
                logger.error(f"Failed to publish to Beehiiv: {e}")
                result["beehiiv_error"] = str(e)
                result["published_to_beehiiv"] = False

        logger.info(f"Newsletter generated for {user.email}: {result}")
        return result

    except Exception as e:
        logger.exception(f"Error generating newsletter for user {user_id}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def send_weekly_newsletters(
    self,
    days: int = 7,
    publish_to_beehiiv: bool = True,
) -> dict:
    """
    Generate and send weekly newsletters for all eligible users.

    This is a scheduled task that runs weekly (e.g., Monday 9 AM).
    """
    db = get_db()
    try:
        # Get users with active subscriptions
        users_with_subs = db.query(User).join(
            UserChannelSubscription,
            UserChannelSubscription.user_id == User.id
        ).filter(
            UserChannelSubscription.is_active == True
        ).distinct().all()

        logger.info(f"Sending weekly newsletters to {len(users_with_subs)} users")

        queued = []
        skipped = []

        for user in users_with_subs:
            # Check if user already has a newsletter this week
            from datetime import timedelta
            week_ago = datetime.utcnow() - timedelta(days=7)

            existing_newsletter = db.query(Newsletter).filter(
                Newsletter.user_id == user.id,
                Newsletter.created_at >= week_ago,
                Newsletter.status.in_([
                    NewsletterStatus.SENT.value,
                    NewsletterStatus.SCHEDULED.value,
                ]),
            ).first()

            if existing_newsletter:
                skipped.append({
                    "user_id": str(user.id),
                    "reason": "already_sent_this_week",
                })
                continue

            # Queue newsletter generation
            task = generate_user_newsletter.delay(
                str(user.id),
                days=days,
                publish_to_beehiiv=publish_to_beehiiv,
            )
            queued.append({
                "user_id": str(user.id),
                "user_email": user.email,
                "task_id": task.id,
            })

        return {
            "users_queued": len(queued),
            "users_skipped": len(skipped),
            "tasks": queued,
            "skipped": skipped,
        }

    except Exception as e:
        logger.exception("Error in send_weekly_newsletters")
        raise
    finally:
        db.close()


@shared_task(bind=True)
def publish_newsletter_to_beehiiv(
    self,
    newsletter_id: str,
    schedule_for: Optional[str] = None,
) -> dict:
    """
    Publish a newsletter to Beehiiv.

    Args:
        newsletter_id: Newsletter UUID
        schedule_for: Optional ISO timestamp for scheduled send
    """
    db = get_db()
    try:
        newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
        if not newsletter:
            return {"error": "Newsletter not found"}

        if newsletter.beehiiv_post_id:
            return {
                "newsletter_id": str(newsletter.id),
                "status": "already_published",
                "beehiiv_post_id": newsletter.beehiiv_post_id,
            }

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create post
        post = loop.run_until_complete(
            beehiiv_client.create_post(
                title=newsletter.title,
                content_html=newsletter.content_html,
                subtitle=newsletter.subtitle,
                status="draft",
            )
        )

        beehiiv_post_id = post.get("id")
        beehiiv_url = post.get("web_url")
        new_status = NewsletterStatus.DRAFT.value

        # Schedule if requested
        if schedule_for:
            loop.run_until_complete(
                beehiiv_client.schedule_post(
                    post_id=beehiiv_post_id,
                    send_at=schedule_for,
                )
            )
            new_status = NewsletterStatus.SCHEDULED.value
            newsletter.scheduled_for = datetime.fromisoformat(schedule_for.replace("Z", "+00:00"))

        newsletter.beehiiv_post_id = beehiiv_post_id
        newsletter.beehiiv_url = beehiiv_url
        newsletter.status = new_status
        db.commit()

        return {
            "newsletter_id": str(newsletter.id),
            "beehiiv_post_id": beehiiv_post_id,
            "beehiiv_url": beehiiv_url,
            "status": new_status,
            "scheduled_for": schedule_for,
        }

    except BeehiivAPIError as e:
        logger.exception(f"Beehiiv API error publishing newsletter {newsletter_id}")
        raise
    except Exception as e:
        logger.exception(f"Error publishing newsletter {newsletter_id}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def sync_beehiiv_subscriber(
    self,
    user_id: str,
) -> dict:
    """
    Sync a user to Beehiiv as a subscriber.

    Creates or updates the subscriber in Beehiiv.
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Check if subscriber exists
        existing = loop.run_until_complete(
            beehiiv_client.get_subscriber_by_email(user.email)
        )

        if existing:
            # Update existing
            user.beehiiv_subscriber_id = existing.get("id")
            db.commit()

            return {
                "user_id": str(user.id),
                "status": "existing",
                "beehiiv_subscriber_id": user.beehiiv_subscriber_id,
            }
        else:
            # Create new subscriber
            subscriber = loop.run_until_complete(
                beehiiv_client.create_subscriber(
                    email=user.email,
                    utm_source="api",
                    send_welcome_email=True,
                )
            )

            user.beehiiv_subscriber_id = subscriber.get("id")
            db.commit()

            return {
                "user_id": str(user.id),
                "status": "created",
                "beehiiv_subscriber_id": user.beehiiv_subscriber_id,
            }

    except BeehiivAPIError as e:
        logger.exception(f"Beehiiv API error syncing subscriber {user_id}")
        raise
    except Exception as e:
        logger.exception(f"Error syncing subscriber {user_id}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def bulk_sync_subscribers(self) -> dict:
    """
    Sync all users to Beehiiv.

    Useful for initial setup or resync.
    """
    db = get_db()
    try:
        # Get users without Beehiiv subscriber ID
        users = db.query(User).filter(
            User.beehiiv_subscriber_id == None
        ).all()

        logger.info(f"Syncing {len(users)} users to Beehiiv")

        queued = []
        for user in users:
            task = sync_beehiiv_subscriber.delay(str(user.id))
            queued.append({
                "user_id": str(user.id),
                "email": user.email,
                "task_id": task.id,
            })

        return {
            "users_queued": len(queued),
            "tasks": queued,
        }

    except Exception as e:
        logger.exception("Error in bulk_sync_subscribers")
        raise
    finally:
        db.close()
