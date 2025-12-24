"""YouTube Data API client for channel and video operations."""

from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings


class YouTubeClient:
    """Client for interacting with YouTube Data API v3."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.youtube_api_key
        self._service = None

    @property
    def service(self):
        """Lazy initialization of YouTube API service."""
        if self._service is None:
            self._service = build("youtube", "v3", developerKey=self.api_key)
        return self._service

    def search_channels(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search for YouTube channels by query string.

        Args:
            query: Search term
            max_results: Maximum number of results (default 10, max 50)

        Returns:
            List of channel data dictionaries
        """
        try:
            response = self.service.search().list(
                part="snippet",
                q=query,
                type="channel",
                maxResults=min(max_results, 50),
            ).execute()

            channels = []
            for item in response.get("items", []):
                channels.append({
                    "youtube_channel_id": item["id"]["channelId"],
                    "name": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "thumbnail_url": item["snippet"]["thumbnails"].get("default", {}).get("url"),
                })

            return channels
        except HttpError as e:
            raise YouTubeAPIError(f"Search failed: {e}")

    def get_channel_by_id(self, channel_id: str) -> Optional[dict]:
        """
        Get detailed channel information by channel ID.

        Args:
            channel_id: YouTube channel ID (e.g., UCxxxxxx)

        Returns:
            Channel data dictionary or None if not found
        """
        try:
            response = self.service.channels().list(
                part="snippet,statistics,brandingSettings",
                id=channel_id,
            ).execute()

            items = response.get("items", [])
            if not items:
                return None

            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            branding = item.get("brandingSettings", {}).get("channel", {})

            return {
                "youtube_channel_id": item["id"],
                "name": snippet.get("title"),
                "description": snippet.get("description"),
                "custom_url": snippet.get("customUrl"),  # @handle
                "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                "banner_url": branding.get("bannerExternalUrl"),
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "view_count": int(stats.get("viewCount", 0)),
            }
        except HttpError as e:
            raise YouTubeAPIError(f"Get channel failed: {e}")

    def get_channel_by_username(self, username: str) -> Optional[dict]:
        """
        Get channel by legacy username.

        Args:
            username: Legacy YouTube username

        Returns:
            Channel data dictionary or None if not found
        """
        try:
            response = self.service.channels().list(
                part="snippet,statistics",
                forUsername=username,
            ).execute()

            items = response.get("items", [])
            if not items:
                return None

            return self.get_channel_by_id(items[0]["id"])
        except HttpError as e:
            raise YouTubeAPIError(f"Get channel by username failed: {e}")

    def get_channel_by_handle(self, handle: str) -> Optional[dict]:
        """
        Get channel by @handle using search.

        Args:
            handle: Channel handle (with or without @)

        Returns:
            Channel data dictionary or None if not found
        """
        # Remove @ if present
        handle = handle.lstrip("@")

        try:
            # Search for the handle
            response = self.service.search().list(
                part="snippet",
                q=f"@{handle}",
                type="channel",
                maxResults=5,
            ).execute()

            # Find exact match
            for item in response.get("items", []):
                channel_id = item["id"]["channelId"]
                channel_data = self.get_channel_by_id(channel_id)
                if channel_data and channel_data.get("custom_url", "").lower() == f"@{handle}".lower():
                    return channel_data

            # If no exact match, return first result
            items = response.get("items", [])
            if items:
                return self.get_channel_by_id(items[0]["id"]["channelId"])

            return None
        except HttpError as e:
            raise YouTubeAPIError(f"Get channel by handle failed: {e}")

    def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 10,
        published_after: Optional[str] = None,
    ) -> list[dict]:
        """
        Get recent videos from a channel.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos (default 10, max 50)
            published_after: ISO 8601 datetime string to filter videos

        Returns:
            List of video data dictionaries
        """
        try:
            request_params = {
                "part": "snippet",
                "channelId": channel_id,
                "type": "video",
                "order": "date",
                "maxResults": min(max_results, 50),
            }

            if published_after:
                request_params["publishedAfter"] = published_after

            response = self.service.search().list(**request_params).execute()

            video_ids = [item["id"]["videoId"] for item in response.get("items", [])]

            if not video_ids:
                return []

            # Get detailed video info
            return self.get_videos_by_ids(video_ids)
        except HttpError as e:
            raise YouTubeAPIError(f"Get channel videos failed: {e}")

    def get_videos_by_ids(self, video_ids: list[str]) -> list[dict]:
        """
        Get detailed information for multiple videos.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            List of video data dictionaries
        """
        if not video_ids:
            return []

        try:
            response = self.service.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(video_ids),
            ).execute()

            videos = []
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})

                videos.append({
                    "youtube_video_id": item["id"],
                    "channel_id": snippet.get("channelId"),
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    "thumbnail_high_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "published_at": snippet.get("publishedAt"),
                    "duration": content.get("duration"),  # ISO 8601 duration
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)),
                    "comment_count": int(stats.get("commentCount", 0)),
                })

            return videos
        except HttpError as e:
            raise YouTubeAPIError(f"Get videos failed: {e}")

    def get_video_by_id(self, video_id: str) -> Optional[dict]:
        """
        Get detailed information for a single video.

        Args:
            video_id: YouTube video ID

        Returns:
            Video data dictionary or None if not found
        """
        videos = self.get_videos_by_ids([video_id])
        return videos[0] if videos else None


class YouTubeAPIError(Exception):
    """Exception raised for YouTube API errors."""
    pass


# Singleton instance
youtube_client = YouTubeClient()
