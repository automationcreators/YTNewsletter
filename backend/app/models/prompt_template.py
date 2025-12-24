import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Targeting - templates can be matched to channels by these fields
    # NULL means "default" / matches all
    category = Column(String(100), index=True)  # tech, entertainment, education, etc.
    format_type = Column(String(100))  # tutorials, vlogs, interviews, etc.
    size_tier = Column(String(50))  # micro, small, medium, large, mega

    # Template content
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)  # Supports {transcript}, {title}, {channel_name}

    # LLM Configuration
    llm_provider = Column(String(50), default="anthropic")
    llm_model = Column(String(100))
    max_tokens = Column(Integer, default=2000)
    temperature = Column(Float, default=0.7)

    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PromptTemplate {self.name}>"
