from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    key = Column(String(255), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)

    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemConfig {self.key}>"


# Default configuration values to seed
DEFAULT_CONFIGS = {
    "tier_limits": {
        "value": {
            "free": {"max_channels": 3},
            "premium": {"max_channels": 20},
            "enterprise": {"max_channels": -1}  # unlimited
        },
        "description": "Channel limits per subscription tier"
    },
    "default_llm": {
        "value": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514"
        },
        "description": "Default LLM provider and model for summaries"
    },
    "newsletter_schedule": {
        "value": {
            "day_of_week": "monday",
            "hour_utc": 9
        },
        "description": "Weekly newsletter send schedule"
    },
    "classification_categories": {
        "value": [
            "tech", "education", "entertainment", "business",
            "lifestyle", "gaming", "music", "news", "sports",
            "science", "health", "finance", "travel", "food"
        ],
        "description": "Valid channel categories for classification"
    },
    "size_tiers": {
        "value": {
            "micro": {"min": 0, "max": 10000},
            "small": {"min": 10000, "max": 100000},
            "medium": {"min": 100000, "max": 1000000},
            "large": {"min": 1000000, "max": 10000000},
            "mega": {"min": 10000000, "max": None}
        },
        "description": "Subscriber count ranges for size tier classification"
    }
}
