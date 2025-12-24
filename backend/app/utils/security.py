"""JWT token utilities for authentication."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from jose import JWTError, jwt
from pydantic import BaseModel
from app.config import settings


class TokenData(BaseModel):
    """Data encoded in JWT token."""
    user_id: str
    email: str
    exp: datetime


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


def create_access_token(
    user_id: UUID,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's UUID
        email: User's email
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=settings.jwt_expiration_hours)

    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    user_id: UUID,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token (longer lived).

    Args:
        user_id: User's UUID
        email: User's email
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    if expires_delta is None:
        # Refresh tokens last 30 days
        expires_delta = timedelta(days=30)

    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_token_pair(user_id: UUID, email: str) -> TokenPair:
    """
    Create both access and refresh tokens.

    Args:
        user_id: User's UUID
        email: User's email

    Returns:
        TokenPair with access and refresh tokens
    """
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id, email)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expiration_hours * 3600,
    )


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        # Check token type
        if payload.get("type") != token_type:
            return None

        user_id = payload.get("sub")
        email = payload.get("email")
        exp = payload.get("exp")

        if user_id is None or email is None:
            return None

        return TokenData(
            user_id=user_id,
            email=email,
            exp=datetime.fromtimestamp(exp),
        )

    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[TokenData]:
    """Verify an access token."""
    return verify_token(token, "access")


def verify_refresh_token(token: str) -> Optional[TokenData]:
    """Verify a refresh token."""
    return verify_token(token, "refresh")
