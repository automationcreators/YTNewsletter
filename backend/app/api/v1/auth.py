"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.google_oauth import google_oauth
from app.services.user_service import user_service
from app.utils.security import (
    create_token_pair,
    verify_refresh_token,
    create_access_token,
)
from app.schemas.auth import (
    GoogleCallbackRequest,
    TokenResponse,
    RefreshTokenRequest,
    AuthUrlResponse,
)
from app.config import settings

router = APIRouter()


@router.get("/google", response_model=AuthUrlResponse)
async def google_auth_url(redirect_url: str = None):
    """
    Get the Google OAuth authorization URL.

    The frontend should redirect the user to this URL to start the OAuth flow.
    """
    # Use redirect_url as state to remember where to send user after auth
    state = redirect_url or settings.frontend_url

    auth_url = google_oauth.get_authorization_url(state=state)

    return AuthUrlResponse(auth_url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback.

    This endpoint is called by Google after the user authorizes.
    It exchanges the code for tokens and creates/updates the user.

    For web apps, redirects to frontend with tokens.
    """
    # Authenticate with Google
    google_info = await google_oauth.authenticate(code)

    if not google_info:
        raise HTTPException(
            status_code=401,
            detail="Failed to authenticate with Google",
        )

    # Get or create user
    user, is_new = user_service.get_or_create_from_google(db, google_info)

    # Create JWT tokens
    tokens = create_token_pair(user.id, user.email)

    # Redirect to frontend with tokens
    redirect_url = state or settings.frontend_url
    separator = "&" if "?" in redirect_url else "?"

    return RedirectResponse(
        url=f"{redirect_url}{separator}access_token={tokens.access_token}&refresh_token={tokens.refresh_token}&is_new={str(is_new).lower()}",
        status_code=302,
    )


@router.post("/google/token", response_model=TokenResponse)
async def google_token_exchange(
    request: GoogleCallbackRequest,
    db: Session = Depends(get_db),
):
    """
    Exchange Google OAuth code for JWT tokens.

    Alternative to callback redirect for SPAs that handle the OAuth flow themselves.
    """
    # Authenticate with Google
    google_info = await google_oauth.authenticate(request.code)

    if not google_info:
        raise HTTPException(
            status_code=401,
            detail="Failed to authenticate with Google",
        )

    # Get or create user
    user, _ = user_service.get_or_create_from_google(db, google_info)

    # Create JWT tokens
    tokens = create_token_pair(user.id, user.email)

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """
    Refresh an access token using a refresh token.
    """
    # Verify refresh token
    token_data = verify_refresh_token(request.refresh_token)

    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    # Get user to ensure they still exist
    from uuid import UUID
    user = user_service.get_by_id(db, UUID(token_data.user_id))

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    # Create new token pair
    tokens = create_token_pair(user.id, user.email)

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post("/logout")
async def logout():
    """
    Logout endpoint.

    Note: Since we use JWTs, we can't truly invalidate tokens server-side
    without a blocklist. The frontend should clear the tokens from storage.
    """
    return {"message": "Logged out successfully"}
