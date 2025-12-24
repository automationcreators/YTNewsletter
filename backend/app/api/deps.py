"""API dependencies for dependency injection."""

from typing import Generator, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.utils.security import verify_access_token
from app.models.user import User

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Use this for endpoints that work with or without authentication.
    """
    if not credentials:
        return None

    token_data = verify_access_token(credentials.credentials)
    if not token_data:
        return None

    user = db.query(User).filter(User.id == UUID(token_data.user_id)).first()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user.

    Raises 401 if not authenticated.
    Use this for protected endpoints.
    """
    token_data = verify_access_token(credentials.credentials)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == UUID(token_data.user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user and verify they are active.

    Can be extended to check user status, subscription, etc.
    """
    # Add any additional checks here (e.g., is_active, email_verified)
    return current_user
