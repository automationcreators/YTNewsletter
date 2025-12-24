"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Create Celery app
celery_app = Celery(
    "yt_newsletter",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.video_tasks",
        "app.tasks.summary_tasks",
        "app.tasks.newsletter_tasks",
    ],
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Rate limiting
    task_annotations={
        "app.tasks.video_tasks.fetch_channel_videos": {"rate_limit": "10/m"},
        "app.tasks.summary_tasks.generate_video_summary": {"rate_limit": "5/m"},
    },

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Beat schedule for periodic tasks
    beat_schedule={
        # Fetch new videos from all active channels every 2 hours
        "fetch-new-videos": {
            "task": "app.tasks.video_tasks.fetch_all_channel_videos",
            "schedule": crontab(minute=0, hour="*/2"),
            "options": {"queue": "default"},
        },
        # Generate summaries for videos without summaries every hour
        "generate-pending-summaries": {
            "task": "app.tasks.summary_tasks.process_pending_summaries",
            "schedule": crontab(minute=30),
            "options": {"queue": "default"},
        },
        # Generate and send weekly newsletters every Monday at 9 AM UTC
        "send-weekly-newsletters": {
            "task": "app.tasks.newsletter_tasks.send_weekly_newsletters",
            "schedule": crontab(minute=0, hour=9, day_of_week=1),
            "options": {"queue": "newsletters"},
        },
        # Clean up old data daily at 3 AM UTC
        "cleanup-old-data": {
            "task": "app.tasks.video_tasks.cleanup_old_videos",
            "schedule": crontab(minute=0, hour=3),
            "options": {"queue": "maintenance"},
        },
    },

    # Task routing
    task_routes={
        "app.tasks.video_tasks.*": {"queue": "default"},
        "app.tasks.summary_tasks.*": {"queue": "summaries"},
        "app.tasks.newsletter_tasks.*": {"queue": "newsletters"},
    },
)


# Optional: Configure task queues
celery_app.conf.task_queues = {
    "default": {},
    "summaries": {},
    "newsletters": {},
    "maintenance": {},
}
