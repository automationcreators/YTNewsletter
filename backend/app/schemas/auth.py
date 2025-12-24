"""Pydantic schemas for authentication."""

from typing import Optional
from pydantic import BaseModel, EmailStr


class GoogleAuthRequest(BaseModel):
    """Request to initiate Google OAuth."""
    redirect_url: Optional[str] = None  # Where to redirect after auth


class GoogleCallbackRequest(BaseModel):
    """Request with Google OAuth callback data."""
    code: str
    state: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


class AuthUrlResponse(BaseModel):
    """Response with Google OAuth URL."""
    auth_url: str


class AuthStatusResponse(BaseModel):
    """Response indicating auth status."""
    authenticated: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
