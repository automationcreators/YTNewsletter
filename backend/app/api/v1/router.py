"""Main API router that combines all v1 endpoints."""

from fastapi import APIRouter
from app.api.v1 import auth, users, channels, videos, subscriptions, admin, newsletters

api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(newsletters.router, prefix="/newsletters", tags=["newsletters"])
