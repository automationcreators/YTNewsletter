"""Video fetching and management tasks."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from celery import shared_task
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.channel import Channel
from app.models.video import Video
from app.models.subscription import UserChannelSubscription
from app.integrations.youtube_client import youtube_client, YouTubeAPIError
from app.services.video_service import video_service
from app.services.transcript_service import transcript_service

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
    autoretry_for=(YouTubeAPIError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def fetch_channel_videos(
    self,
    channel_id: str,
    max_results: int = 10,
    fetch_transcripts: bool = True,
) -> dict:
    """
    Fetch recent videos from a YouTube channel.

    Args:
        channel_id: Internal channel UUID
        max_results: Maximum videos to fetch
        fetch_transcripts: Whether to fetch transcripts for new videos

    Returns:
        Dict with fetch results
    """
    db = get_db()
    try:
        # Get channel
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            logger.error(f"Channel not found: {channel_id}")
            return {"error": "Channel not found", "channel_id": channel_id}

        logger.info(f"Fetching videos for channel: {channel.name} ({channel.youtube_channel_id})")

        # Fetch videos from YouTube
        try:
            videos_data = youtube_client.get_channel_videos(
                channel.youtube_channel_id,
                max_results=max_results,
            )
        except YouTubeAPIError as e:
            logger.error(f"YouTube API error for channel {channel.name}: {e}")
            raise

        new_videos = 0
        updated_videos = 0
        transcript_fetched = 0

        for video_data in videos_data:
            # Check if video exists
            existing = db.query(Video).filter(
                Video.youtube_video_id == video_data["youtube_video_id"]
            ).first()

            if existing:
                # Update existing video
                existing.view_count = video_data.get("view_count", existing.view_count)
                updated_videos += 1
            else:
                # Create new video
                video = Video(
                    youtube_video_id=video_data["youtube_video_id"],
                    channel_id=channel.id,
                    title=video_data["title"],
                    description=video_data.get("description"),
                    thumbnail_url=video_data.get("thumbnail_url"),
                    thumbnail_high_url=video_data.get("thumbnail_high_url"),
                    duration_seconds=video_data.get("duration_seconds"),
                    published_at=video_data.get("published_at"),
                    view_count=video_data.get("view_count"),
                    transcript_status="pending",
                    summary_status="pending",
                )
                db.add(video)
                new_videos += 1

                # Fetch transcript if requested
                if fetch_transcripts:
                    db.flush()  # Get video ID
                    try:
                        transcript_data = transcript_service.get_transcript(
                            video_data["youtube_video_id"],
                            use_whisper_fallback=False,  # Don't use Whisper for batch fetching
                        )
                        if transcript_data:
                            video.transcript_status = "fetched"
                            video.transcript = transcript_data.get("content")
                            transcript_fetched += 1
                        else:
                            video.transcript_status = "unavailable"
                    except Exception as e:
                        logger.warning(f"Failed to fetch transcript for {video_data['youtube_video_id']}: {e}")
                        video.transcript_status = "failed"

        # Update channel's last_video_fetch
        channel.last_video_fetch = datetime.utcnow()
        db.commit()

        result = {
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "new_videos": new_videos,
            "updated_videos": updated_videos,
            "transcripts_fetched": transcript_fetched,
        }

        logger.info(f"Fetch complete for {channel.name}: {result}")
        return result

    except Exception as e:
        logger.exception(f"Error fetching videos for channel {channel_id}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def fetch_all_channel_videos(self, max_results_per_channel: int = 5) -> dict:
    """
    Fetch videos for all active channels with subscribers.

    This is a periodic task that runs every few hours.
    """
    db = get_db()
    try:
        # Get channels that have active subscriptions
        channels_with_subs = db.query(Channel).join(
            UserChannelSubscription,
            UserChannelSubscription.channel_id == Channel.id
        ).filter(
            UserChannelSubscription.is_active == True
        ).distinct().all()

        logger.info(f"Fetching videos for {len(channels_with_subs)} channels with active subscriptions")

        results = []
        for channel in channels_with_subs:
            # Queue individual channel fetch tasks
            task = fetch_channel_videos.delay(
                str(channel.id),
                max_results=max_results_per_channel,
                fetch_transcripts=True,
            )
            results.append({
                "channel_id": str(channel.id),
                "channel_name": channel.name,
                "task_id": task.id,
            })

        return {
            "channels_queued": len(results),
            "tasks": results,
        }

    except Exception as e:
        logger.exception("Error in fetch_all_channel_videos")
        raise
    finally:
        db.close()


@shared_task(bind=True)
def sync_channel_metadata(self, channel_id: str) -> dict:
    """
    Sync channel metadata from YouTube.

    Updates subscriber count, description, thumbnails, etc.
    """
    db = get_db()
    try:
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return {"error": "Channel not found"}

        # Fetch fresh data from YouTube
        channel_data = youtube_client.get_channel_by_id(channel.youtube_channel_id)
        if not channel_data:
            return {"error": "Channel not found on YouTube"}

        # Update channel
        channel.name = channel_data.get("title", channel.name)
        channel.description = channel_data.get("description", channel.description)
        channel.subscriber_count = channel_data.get("subscriber_count", channel.subscriber_count)
        channel.video_count = channel_data.get("video_count", channel.video_count)
        channel.thumbnail_url = channel_data.get("thumbnail_url", channel.thumbnail_url)

        db.commit()

        return {
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "subscriber_count": channel.subscriber_count,
            "updated": True,
        }

    except Exception as e:
        logger.exception(f"Error syncing channel metadata: {channel_id}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def cleanup_old_videos(self, days_to_keep: int = 90) -> dict:
    """
    Clean up old videos that are no longer needed.

    Removes videos older than specified days that:
    - Have no summary
    - Are from channels with no active subscriptions

    This helps manage storage for the database.
    """
    db = get_db()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Find videos to clean up
        # Keep videos that have summaries or are from actively subscribed channels
        active_channel_ids = db.query(UserChannelSubscription.channel_id).filter(
            UserChannelSubscription.is_active == True
        ).distinct().subquery()

        videos_to_delete = db.query(Video).filter(
            Video.published_at < cutoff_date,
            Video.summary == None,
            ~Video.channel_id.in_(active_channel_ids),
        ).all()

        deleted_count = len(videos_to_delete)

        for video in videos_to_delete:
            db.delete(video)

        db.commit()

        logger.info(f"Cleaned up {deleted_count} old videos")

        return {
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        logger.exception("Error in cleanup_old_videos")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def fetch_video_transcript(
    self,
    video_id: str,
    use_whisper: bool = True,
) -> dict:
    """
    Fetch transcript for a specific video.

    Args:
        video_id: Internal video UUID
        use_whisper: Whether to use Whisper fallback
    """
    db = get_db()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return {"error": "Video not found"}

        if video.transcript_status == "fetched" and video.transcript:
            return {"status": "already_fetched", "video_id": video_id}

        # Fetch transcript
        transcript_data = transcript_service.get_transcript(
            video.youtube_video_id,
            use_whisper_fallback=use_whisper,
        )

        if transcript_data:
            video.transcript = transcript_data.get("content")
            video.transcript_status = "fetched"
            db.commit()

            return {
                "video_id": str(video.id),
                "status": "fetched",
                "source": transcript_data.get("source", "unknown"),
                "language": transcript_data.get("language"),
            }
        else:
            video.transcript_status = "unavailable"
            db.commit()

            return {
                "video_id": str(video.id),
                "status": "unavailable",
            }

    except Exception as e:
        logger.exception(f"Error fetching transcript for video {video_id}")
        db.rollback()
        raise
    finally:
        db.close()
