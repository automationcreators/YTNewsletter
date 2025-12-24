from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "YouTube Newsletter API"
    debug: bool = False

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/yt_newsletter"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # YouTube
    youtube_api_key: str = ""

    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-20250514"

    # Beehiiv
    beehiiv_api_key: str = ""
    beehiiv_publication_id: str = ""
    beehiiv_webhook_secret: str = ""

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # URLs
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Tier Configuration (can be overridden via system_config table)
    default_free_max_channels: int = 3
    default_premium_max_channels: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars not in model


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
