"""Service for resolving various YouTube channel input formats."""

import re
from typing import Optional
from app.integrations.youtube_client import youtube_client, YouTubeAPIError


class ChannelResolver:
    """
    Resolves various YouTube channel input formats to channel data.

    Supported formats:
    - Channel ID: UCxxxxxx
    - Channel URL: youtube.com/channel/UCxxxxxx
    - Custom URL: youtube.com/c/ChannelName
    - Handle URL: youtube.com/@handle
    - Handle: @handle
    - Legacy username URL: youtube.com/user/username
    - Short URL: youtu.be/channel/UCxxxxxx
    """

    # Regex patterns for different URL formats
    PATTERNS = {
        # Channel ID (starts with UC and is 24 chars)
        "channel_id": re.compile(r"^UC[\w-]{22}$"),

        # youtube.com/channel/UCxxxxxx
        "channel_url": re.compile(
            r"(?:https?://)?(?:www\.)?youtube\.com/channel/(UC[\w-]{22})"
        ),

        # youtube.com/c/ChannelName or youtube.com/ChannelName
        "custom_url": re.compile(
            r"(?:https?://)?(?:www\.)?youtube\.com/(?:c/)?([^/@\s?]+)(?:\?|$|/)"
        ),

        # youtube.com/@handle
        "handle_url": re.compile(
            r"(?:https?://)?(?:www\.)?youtube\.com/@([\w.-]+)"
        ),

        # @handle (standalone)
        "handle": re.compile(r"^@([\w.-]+)$"),

        # youtube.com/user/username
        "user_url": re.compile(
            r"(?:https?://)?(?:www\.)?youtube\.com/user/([\w.-]+)"
        ),
    }

    def __init__(self):
        self.client = youtube_client

    def resolve(self, input_string: str) -> Optional[dict]:
        """
        Resolve any supported input format to channel data.

        Args:
            input_string: Channel ID, URL, or handle

        Returns:
            Channel data dictionary or None if not found
        """
        input_string = input_string.strip()

        # Try each pattern in order of specificity

        # 1. Direct channel ID
        if self.PATTERNS["channel_id"].match(input_string):
            return self.client.get_channel_by_id(input_string)

        # 2. Channel URL (youtube.com/channel/UCxxxxxx)
        match = self.PATTERNS["channel_url"].search(input_string)
        if match:
            return self.client.get_channel_by_id(match.group(1))

        # 3. Handle URL (youtube.com/@handle)
        match = self.PATTERNS["handle_url"].search(input_string)
        if match:
            return self.client.get_channel_by_handle(match.group(1))

        # 4. Standalone handle (@handle)
        match = self.PATTERNS["handle"].match(input_string)
        if match:
            return self.client.get_channel_by_handle(match.group(1))

        # 5. User URL (youtube.com/user/username)
        match = self.PATTERNS["user_url"].search(input_string)
        if match:
            return self.client.get_channel_by_username(match.group(1))

        # 6. Custom URL (youtube.com/c/ChannelName)
        match = self.PATTERNS["custom_url"].search(input_string)
        if match:
            # Try as handle first, then search
            channel = self.client.get_channel_by_handle(match.group(1))
            if channel:
                return channel

        # 7. Fallback: treat as search query and return best match
        results = self.client.search_channels(input_string, max_results=1)
        if results:
            return self.client.get_channel_by_id(results[0]["youtube_channel_id"])

        return None

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from a YouTube video URL.

        Supported formats:
        - youtube.com/watch?v=VIDEO_ID
        - youtu.be/VIDEO_ID
        - youtube.com/embed/VIDEO_ID
        - youtube.com/v/VIDEO_ID

        Args:
            url: YouTube video URL

        Returns:
            Video ID or None if not found
        """
        patterns = [
            # youtube.com/watch?v=VIDEO_ID
            re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([\w-]{11})"),
            # youtu.be/VIDEO_ID
            re.compile(r"(?:https?://)?youtu\.be/([\w-]{11})"),
            # youtube.com/embed/VIDEO_ID
            re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([\w-]{11})"),
            # youtube.com/v/VIDEO_ID
            re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/([\w-]{11})"),
            # Direct video ID (11 chars)
            re.compile(r"^([\w-]{11})$"),
        ]

        for pattern in patterns:
            match = pattern.search(url)
            if match:
                return match.group(1)

        return None


# Singleton instance
channel_resolver = ChannelResolver()
