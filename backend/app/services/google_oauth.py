"""Google OAuth service for authentication."""

from typing import Optional
import httpx
from pydantic import BaseModel
from app.config import settings


class GoogleUserInfo(BaseModel):
    """User info from Google OAuth."""
    google_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False


class GoogleOAuthService:
    """Service for handling Google OAuth authentication."""

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = f"{settings.backend_url}/api/v1/auth/google/callback"

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get the Google OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.GOOGLE_AUTH_URL}?{query_string}"

    async def exchange_code_for_tokens(self, code: str) -> Optional[dict]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from Google

        Returns:
            Token response dict or None if failed
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )

            if response.status_code != 200:
                return None

            return response.json()

    async def get_user_info(self, access_token: str) -> Optional[GoogleUserInfo]:
        """
        Get user info from Google using access token.

        Args:
            access_token: Google OAuth access token

        Returns:
            GoogleUserInfo or None if failed
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                return None

            data = response.json()

            return GoogleUserInfo(
                google_id=data.get("id"),
                email=data.get("email"),
                name=data.get("name"),
                picture=data.get("picture"),
                email_verified=data.get("verified_email", False),
            )

    async def authenticate(self, code: str) -> Optional[GoogleUserInfo]:
        """
        Full authentication flow: exchange code and get user info.

        Args:
            code: Authorization code from Google

        Returns:
            GoogleUserInfo or None if authentication failed
        """
        tokens = await self.exchange_code_for_tokens(code)
        if not tokens:
            return None

        access_token = tokens.get("access_token")
        if not access_token:
            return None

        return await self.get_user_info(access_token)


# Singleton instance
google_oauth = GoogleOAuthService()
