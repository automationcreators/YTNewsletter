"""Video service for fetching and storing videos."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import re
from sqlalchemy.orm import Session
from app.models.channel import Channel
from app.models.video import Video
from app.models.transcript import Transcript
from app.integrations.youtube_client import youtube_client
from app.services.transcript_service import transcript_service


class VideoService:
    """Service for video-related database operations."""

    def get_by_id(self, db: Session, video_id: UUID) -> Optional[Video]:
        """Get video by internal ID."""
        return db.query(Video).filter(Video.id == video_id).first()

    def get_by_youtube_id(self, db: Session, youtube_video_id: str) -> Optional[Video]:
        """Get video by YouTube video ID."""
        return db.query(Video).filter(
            Video.youtube_video_id == youtube_video_id
        ).first()

    def get_channel_videos(
        self,
        db: Session,
        channel: Channel,
        limit: int = 10,
        include_pending: bool = True,
    ) -> list[Video]:
        """Get videos for a channel."""
        query = db.query(Video).filter(Video.channel_id == channel.id)

        if not include_pending:
            query = query.filter(Video.summary_status == "completed")

        return query.order_by(Video.published_at.desc()).limit(limit).all()

    def get_videos_for_user(
        self,
        db: Session,
        user_id: UUID,
        days: int = 7,
        limit: int = 50,
    ) -> list[Video]:
        """
        Get recent videos from all channels a user is subscribed to.

        Args:
            db: Database session
            user_id: User ID
            days: Number of days to look back
            limit: Maximum videos to return

        Returns:
            List of videos sorted by published date
        """
        from app.models.subscription import UserChannelSubscription

        cutoff = datetime.utcnow() - timedelta(days=days)

        videos = db.query(Video).join(
            UserChannelSubscription,
            Video.channel_id == UserChannelSubscription.channel_id,
        ).filter(
            UserChannelSubscription.user_id == user_id,
            UserChannelSubscription.is_active == True,
            Video.published_at >= cutoff,
        ).order_by(Video.published_at.desc()).limit(limit).all()

        return videos

    def create_from_youtube(self, db: Session, channel: Channel, youtube_data: dict) -> Video:
        """
        Create a video from YouTube API data.

        Args:
            db: Database session
            channel: Parent channel
            youtube_data: Video data from YouTube API

        Returns:
            Created video
        """
        # Parse duration (ISO 8601 format like PT4M13S)
        duration_seconds = self._parse_duration(youtube_data.get("duration"))

        # Parse published date
        published_at = youtube_data.get("published_at")
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

        video = Video(
            youtube_video_id=youtube_data["youtube_video_id"],
            channel_id=channel.id,
            title=youtube_data["title"],
            description=youtube_data.get("description"),
            thumbnail_url=youtube_data.get("thumbnail_url"),
            thumbnail_high_url=youtube_data.get("thumbnail_high_url"),
            duration_seconds=duration_seconds,
            published_at=published_at,
            view_count=youtube_data.get("view_count"),
            like_count=youtube_data.get("like_count"),
            comment_count=youtube_data.get("comment_count"),
            transcript_status="pending",
            summary_status="pending",
        )

        db.add(video)
        db.commit()
        db.refresh(video)

        return video

    def fetch_channel_videos(
        self,
        db: Session,
        channel: Channel,
        max_results: int = 10,
        published_after: Optional[datetime] = None,
    ) -> list[Video]:
        """
        Fetch new videos from YouTube and store them.

        Args:
            db: Database session
            channel: Channel to fetch videos for
            max_results: Maximum videos to fetch
            published_after: Only fetch videos after this date

        Returns:
            List of new videos created
        """
        # Default to last check time or 7 days ago
        if published_after is None:
            published_after = channel.last_video_check_at or (
                datetime.utcnow() - timedelta(days=7)
            )

        # Fetch from YouTube
        youtube_videos = youtube_client.get_channel_videos(
            channel.youtube_channel_id,
            max_results=max_results,
            published_after=published_after.isoformat() + "Z" if published_after else None,
        )

        new_videos = []
        for yt_video in youtube_videos:
            # Check if already exists
            existing = self.get_by_youtube_id(db, yt_video["youtube_video_id"])
            if existing:
                continue

            # Create new video
            video = self.create_from_youtube(db, channel, yt_video)
            new_videos.append(video)

        # Update channel's last check time
        channel.last_video_check_at = datetime.utcnow()
        db.commit()

        return new_videos

    def fetch_transcript(
        self,
        db: Session,
        video: Video,
        use_whisper: bool = True,
    ) -> Optional[Transcript]:
        """
        Fetch transcript for a video and store it.

        Args:
            db: Database session
            video: Video to fetch transcript for
            use_whisper: Whether to use Whisper as fallback

        Returns:
            Created transcript or None if unavailable
        """
        # Check if transcript already exists
        if video.transcript:
            return video.transcript

        # Fetch transcript
        transcript_data = transcript_service.get_transcript(
            video.youtube_video_id,
            use_whisper_fallback=use_whisper,
        )

        if not transcript_data:
            video.transcript_status = "unavailable"
            db.commit()
            return None

        # Create transcript
        transcript = Transcript(
            video_id=video.id,
            content=transcript_data["content"],
            language=transcript_data.get("language", "en"),
            source=transcript_data["source"],
            word_count=transcript_data.get("word_count"),
            segments=transcript_data.get("segments"),
        )

        db.add(transcript)

        # Update video status
        video.transcript_status = "fetched" if transcript_data["source"] != "whisper" else "whisper_processed"
        db.commit()
        db.refresh(transcript)

        return transcript

    def get_pending_transcripts(self, db: Session, limit: int = 50) -> list[Video]:
        """Get videos that need transcript fetching."""
        return db.query(Video).filter(
            Video.transcript_status == "pending",
        ).order_by(Video.published_at.desc()).limit(limit).all()

    def get_pending_summaries(self, db: Session, limit: int = 50) -> list[Video]:
        """Get videos that need summary generation."""
        return db.query(Video).filter(
            Video.transcript_status.in_(["fetched", "whisper_processed"]),
            Video.summary_status == "pending",
        ).order_by(Video.published_at.desc()).limit(limit).all()

    def _parse_duration(self, duration: Optional[str]) -> Optional[int]:
        """Parse ISO 8601 duration to seconds."""
        if not duration:
            return None

        # Match PT1H2M3S format
        pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, duration)

        if not match:
            return None

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds


# Singleton instance
video_service = VideoService()
