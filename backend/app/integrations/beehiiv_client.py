"""Beehiiv API integration client."""

import httpx
from typing import Optional
from app.config import settings


class BeehiivAPIError(Exception):
    """Custom exception for Beehiiv API errors."""
    pass


class BeehiivClient:
    """Client for interacting with the Beehiiv API."""

    BASE_URL = "https://api.beehiiv.com/v2"

    def __init__(self):
        self.api_key = settings.beehiiv_api_key
        self.publication_id = settings.beehiiv_publication_id

    @property
    def _headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _check_configured(self):
        """Verify API credentials are configured."""
        if not self.api_key or not self.publication_id:
            raise BeehiivAPIError("Beehiiv API key and publication ID must be configured")

    async def get_publication(self) -> dict:
        """Get publication details."""
        self._check_configured()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/publications/{self.publication_id}",
                headers=self._headers,
            )

            if response.status_code != 200:
                raise BeehiivAPIError(f"Failed to get publication: {response.text}")

            return response.json().get("data", {})

    async def get_subscribers(
        self,
        limit: int = 100,
        page: int = 1,
        status: Optional[str] = "active",
    ) -> dict:
        """
        Get subscribers from Beehiiv.

        Args:
            limit: Number of subscribers to return (max 100)
            page: Page number
            status: Filter by status (active, inactive, pending, validating)

        Returns:
            Dict with subscribers and pagination info
        """
        self._check_configured()

        params = {
            "limit": min(limit, 100),
            "page": page,
        }
        if status:
            params["status"] = status

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/publications/{self.publication_id}/subscriptions",
                headers=self._headers,
                params=params,
            )

            if response.status_code != 200:
                raise BeehiivAPIError(f"Failed to get subscribers: {response.text}")

            return response.json()

    async def get_subscriber_by_email(self, email: str) -> Optional[dict]:
        """
        Get a subscriber by email.

        Args:
            email: Subscriber email

        Returns:
            Subscriber data or None if not found
        """
        self._check_configured()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/publications/{self.publication_id}/subscriptions",
                headers=self._headers,
                params={"email": email},
            )

            if response.status_code != 200:
                return None

            data = response.json().get("data", [])
            return data[0] if data else None

    async def create_subscriber(
        self,
        email: str,
        utm_source: str = "api",
        referring_site: Optional[str] = None,
        custom_fields: Optional[list[dict]] = None,
        send_welcome_email: bool = True,
    ) -> dict:
        """
        Create a new subscriber in Beehiiv.

        Args:
            email: Subscriber email
            utm_source: Attribution source
            referring_site: Referring website URL
            custom_fields: List of custom field values
            send_welcome_email: Whether to send welcome email

        Returns:
            Created subscriber data
        """
        self._check_configured()

        payload = {
            "email": email,
            "utm_source": utm_source,
            "send_welcome_email": send_welcome_email,
        }

        if referring_site:
            payload["referring_site"] = referring_site
        if custom_fields:
            payload["custom_fields"] = custom_fields

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/publications/{self.publication_id}/subscriptions",
                headers=self._headers,
                json=payload,
            )

            if response.status_code not in (200, 201):
                raise BeehiivAPIError(f"Failed to create subscriber: {response.text}")

            return response.json().get("data", {})

    async def update_subscriber(
        self,
        subscription_id: str,
        custom_fields: Optional[list[dict]] = None,
    ) -> dict:
        """
        Update a subscriber's custom fields.

        Args:
            subscription_id: Beehiiv subscription ID
            custom_fields: Updated custom field values

        Returns:
            Updated subscriber data
        """
        self._check_configured()

        payload = {}
        if custom_fields:
            payload["custom_fields"] = custom_fields

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/publications/{self.publication_id}/subscriptions/{subscription_id}",
                headers=self._headers,
                json=payload,
            )

            if response.status_code != 200:
                raise BeehiivAPIError(f"Failed to update subscriber: {response.text}")

            return response.json().get("data", {})

    async def delete_subscriber(self, subscription_id: str) -> bool:
        """
        Delete a subscriber from Beehiiv.

        Args:
            subscription_id: Beehiiv subscription ID

        Returns:
            True if deleted successfully
        """
        self._check_configured()

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/publications/{self.publication_id}/subscriptions/{subscription_id}",
                headers=self._headers,
            )

            return response.status_code == 200

    async def create_post(
        self,
        title: str,
        content_html: str,
        subtitle: Optional[str] = None,
        status: str = "draft",
        send_to_free: bool = True,
        send_to_premium: bool = True,
    ) -> dict:
        """
        Create a new post/newsletter in Beehiiv.

        Args:
            title: Post title
            content_html: HTML content
            subtitle: Post subtitle
            status: Post status (draft, confirmed, archived)
            send_to_free: Include free subscribers
            send_to_premium: Include premium subscribers

        Returns:
            Created post data
        """
        self._check_configured()

        # Build audience
        audience = []
        if send_to_free:
            audience.append("free")
        if send_to_premium:
            audience.append("premium")

        payload = {
            "title": title,
            "content_html": content_html,
            "status": status,
            "audience": audience,
        }

        if subtitle:
            payload["subtitle"] = subtitle

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/publications/{self.publication_id}/posts",
                headers=self._headers,
                json=payload,
            )

            if response.status_code not in (200, 201):
                raise BeehiivAPIError(f"Failed to create post: {response.text}")

            return response.json().get("data", {})

    async def get_post(self, post_id: str) -> dict:
        """Get a specific post by ID."""
        self._check_configured()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/publications/{self.publication_id}/posts/{post_id}",
                headers=self._headers,
            )

            if response.status_code != 200:
                raise BeehiivAPIError(f"Failed to get post: {response.text}")

            return response.json().get("data", {})

    async def schedule_post(
        self,
        post_id: str,
        send_at: str,
    ) -> dict:
        """
        Schedule a post for delivery.

        Args:
            post_id: Post ID
            send_at: ISO 8601 timestamp for scheduled send

        Returns:
            Updated post data
        """
        self._check_configured()

        payload = {
            "status": "confirmed",
            "scheduled_at": send_at,
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/publications/{self.publication_id}/posts/{post_id}",
                headers=self._headers,
                json=payload,
            )

            if response.status_code != 200:
                raise BeehiivAPIError(f"Failed to schedule post: {response.text}")

            return response.json().get("data", {})


# Singleton instance
beehiiv_client = BeehiivClient()
