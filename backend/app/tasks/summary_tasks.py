"""Summary generation tasks."""

import logging
from typing import Optional
from celery import shared_task
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.video import Video
from app.models.subscription import UserChannelSubscription
from app.services.summary_service import summary_service

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
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def generate_video_summary(
    self,
    video_id: str,
    force_regenerate: bool = False,
) -> dict:
    """
    Generate summary for a specific video.

    Args:
        video_id: Internal video UUID
        force_regenerate: Whether to regenerate existing summary

    Returns:
        Dict with summary generation results
    """
    db = get_db()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video not found: {video_id}")
            return {"error": "Video not found", "video_id": video_id}

        # Check if already summarized
        if video.summary and not force_regenerate:
            return {
                "video_id": str(video.id),
                "status": "already_summarized",
                "summary_id": str(video.summary.id),
            }

        # Check for transcript
        if not video.transcript or video.transcript_status != "fetched":
            logger.warning(f"No transcript available for video: {video_id}")
            return {
                "video_id": str(video.id),
                "status": "no_transcript",
                "transcript_status": video.transcript_status,
            }

        logger.info(f"Generating summary for video: {video.title}")

        # Update status
        video.summary_status = "processing"
        db.commit()

        try:
            # Generate summary
            summary = summary_service.generate_summary(
                db,
                video,
                force_regenerate=force_regenerate,
            )

            if summary:
                video.summary_status = "completed"
                db.commit()

                return {
                    "video_id": str(video.id),
                    "status": "success",
                    "summary_id": str(summary.id),
                    "llm_provider": summary.llm_provider,
                    "llm_model": summary.llm_model,
                    "tokens_used": summary.generation_tokens,
                }
            else:
                video.summary_status = "failed"
                db.commit()

                return {
                    "video_id": str(video.id),
                    "status": "failed",
                    "error": "Summary generation returned None",
                }

        except Exception as e:
            video.summary_status = "failed"
            db.commit()
            raise

    except Exception as e:
        logger.exception(f"Error generating summary for video {video_id}")
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(bind=True)
def process_pending_summaries(
    self,
    limit: int = 20,
    prioritize_subscribed: bool = True,
) -> dict:
    """
    Process videos that need summaries.

    This is a periodic task that finds videos with transcripts
    but no summaries and queues them for processing.

    Args:
        limit: Maximum videos to process in this batch
        prioritize_subscribed: Prioritize videos from subscribed channels
    """
    db = get_db()
    try:
        # Build query for videos needing summaries
        query = db.query(Video).filter(
            Video.transcript_status == "fetched",
            Video.transcript != None,
            Video.summary == None,
            Video.summary_status.in_(["pending", "failed"]),
        )

        if prioritize_subscribed:
            # Get channels with active subscriptions
            subscribed_channel_ids = db.query(UserChannelSubscription.channel_id).filter(
                UserChannelSubscription.is_active == True
            ).distinct().subquery()

            # Prioritize subscribed channels first
            videos = query.filter(
                Video.channel_id.in_(subscribed_channel_ids)
            ).order_by(Video.published_at.desc()).limit(limit).all()

            # If not enough, get others
            if len(videos) < limit:
                remaining = limit - len(videos)
                other_videos = query.filter(
                    ~Video.channel_id.in_(subscribed_channel_ids)
                ).order_by(Video.published_at.desc()).limit(remaining).all()
                videos.extend(other_videos)
        else:
            videos = query.order_by(Video.published_at.desc()).limit(limit).all()

        logger.info(f"Found {len(videos)} videos needing summaries")

        # Queue summary generation tasks
        queued = []
        for video in videos:
            task = generate_video_summary.delay(str(video.id))
            queued.append({
                "video_id": str(video.id),
                "title": video.title,
                "task_id": task.id,
            })

        return {
            "videos_queued": len(queued),
            "tasks": queued,
        }

    except Exception as e:
        logger.exception("Error in process_pending_summaries")
        raise
    finally:
        db.close()


@shared_task(bind=True)
def batch_generate_summaries(
    self,
    video_ids: list[str],
) -> dict:
    """
    Generate summaries for a batch of videos.

    Useful for manually triggering summary generation for specific videos.

    Args:
        video_ids: List of video UUIDs to process
    """
    db = get_db()
    try:
        results = []
        for video_id in video_ids:
            task = generate_video_summary.delay(video_id)
            results.append({
                "video_id": video_id,
                "task_id": task.id,
            })

        return {
            "videos_queued": len(results),
            "tasks": results,
        }

    except Exception as e:
        logger.exception("Error in batch_generate_summaries")
        raise
    finally:
        db.close()


@shared_task(bind=True)
def regenerate_failed_summaries(self, limit: int = 10) -> dict:
    """
    Retry summary generation for failed videos.

    Only retries videos that failed recently (within last 24 hours).
    """
    db = get_db()
    try:
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(hours=24)

        failed_videos = db.query(Video).filter(
            Video.summary_status == "failed",
            Video.transcript_status == "fetched",
            Video.transcript != None,
            Video.updated_at >= cutoff,
        ).limit(limit).all()

        logger.info(f"Found {len(failed_videos)} failed videos to retry")

        queued = []
        for video in failed_videos:
            # Reset status
            video.summary_status = "pending"
            db.commit()

            # Queue task
            task = generate_video_summary.delay(str(video.id))
            queued.append({
                "video_id": str(video.id),
                "title": video.title,
                "task_id": task.id,
            })

        return {
            "videos_queued": len(queued),
            "tasks": queued,
        }

    except Exception as e:
        logger.exception("Error in regenerate_failed_summaries")
        raise
    finally:
        db.close()
