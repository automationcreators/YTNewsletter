"""Celery tasks package."""

from app.tasks.video_tasks import (
    fetch_channel_videos,
    fetch_all_channel_videos,
    cleanup_old_videos,
)
from app.tasks.summary_tasks import (
    generate_video_summary,
    process_pending_summaries,
)
from app.tasks.newsletter_tasks import (
    generate_user_newsletter,
    send_weekly_newsletters,
)

__all__ = [
    "fetch_channel_videos",
    "fetch_all_channel_videos",
    "cleanup_old_videos",
    "generate_video_summary",
    "process_pending_summaries",
    "generate_user_newsletter",
    "send_weekly_newsletters",
]
