"""Prompt template service for managing and selecting prompts."""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.prompt_template import PromptTemplate
from app.models.channel import Channel


# Default prompt templates
DEFAULT_SYSTEM_PROMPT = """You are an expert content summarizer specializing in YouTube video analysis.
Your task is to create comprehensive, insightful summaries that capture the essence of video content.
Be concise but thorough. Focus on actionable insights and key takeaways."""

DEFAULT_USER_PROMPT = """Analyze the following YouTube video transcript and create a comprehensive summary.

Video Title: {title}
Channel: {channel_name}
Duration: {duration}

Transcript:
{transcript}

Please provide:

1. **Summary** (2-3 paragraphs)
Write a clear, engaging summary of the main content. Focus on the key narrative and most important points discussed.

2. **Key Insights** (3-5 bullet points)
List the most valuable insights or lessons from this video. These should be specific and actionable.

3. **Notable Quotes** (2-3 quotes)
Extract exact quotes from the transcript that are particularly insightful or memorable. Include approximate timestamps if mentioned.

4. **Timestamp Moments** (3-5 moments)
Identify key moments in the video worth watching. Format as "MM:SS - Description of what happens".

5. **Key Takeaways** (3-5 bullet points)
Summarize the main actionable takeaways a viewer should remember from this video.

Format your response as JSON with these exact keys:
{{
    "summary": "...",
    "key_insights": ["...", "..."],
    "notable_quotes": [{{"quote": "...", "timestamp": null}}],
    "timestamp_moments": [{{"timestamp": 0, "description": "..."}}],
    "key_takeaways": ["...", "..."]
}}"""


class PromptService:
    """Service for managing prompt templates."""

    def get_default_template(self, db: Session) -> Optional[PromptTemplate]:
        """Get the default prompt template."""
        return db.query(PromptTemplate).filter(
            PromptTemplate.is_default == True,
            PromptTemplate.is_active == True,
        ).first()

    def get_template_for_channel(
        self,
        db: Session,
        channel: Channel,
    ) -> Optional[PromptTemplate]:
        """
        Get the best matching prompt template for a channel.

        Priority:
        1. Exact match (category + format_type)
        2. Category match only
        3. Format type match only
        4. Default template
        """
        # Try exact match
        if channel.category and channel.format_type:
            template = db.query(PromptTemplate).filter(
                PromptTemplate.category == channel.category,
                PromptTemplate.format_type == channel.format_type,
                PromptTemplate.is_active == True,
            ).first()
            if template:
                return template

        # Try category match
        if channel.category:
            template = db.query(PromptTemplate).filter(
                PromptTemplate.category == channel.category,
                PromptTemplate.format_type == None,
                PromptTemplate.is_active == True,
            ).first()
            if template:
                return template

        # Try format type match
        if channel.format_type:
            template = db.query(PromptTemplate).filter(
                PromptTemplate.category == None,
                PromptTemplate.format_type == channel.format_type,
                PromptTemplate.is_active == True,
            ).first()
            if template:
                return template

        # Fall back to default
        return self.get_default_template(db)

    def get_prompt_config(
        self,
        db: Session,
        channel: Channel,
    ) -> dict:
        """
        Get the prompt configuration for a channel.

        Returns dict with:
        - system_prompt
        - user_prompt_template
        - llm_provider
        - llm_model
        - max_tokens
        - temperature
        """
        template = self.get_template_for_channel(db, channel)

        if template:
            return {
                "system_prompt": template.system_prompt,
                "user_prompt_template": template.user_prompt_template,
                "llm_provider": template.llm_provider or "anthropic",
                "llm_model": template.llm_model,
                "max_tokens": template.max_tokens or 2000,
                "temperature": template.temperature or 0.7,
            }

        # Channel-specific override
        if channel.summary_prompt_template:
            return {
                "system_prompt": DEFAULT_SYSTEM_PROMPT,
                "user_prompt_template": channel.summary_prompt_template,
                "llm_provider": channel.llm_provider or "anthropic",
                "llm_model": channel.llm_model,
                "max_tokens": 2000,
                "temperature": 0.7,
            }

        # Default prompts
        return {
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "user_prompt_template": DEFAULT_USER_PROMPT,
            "llm_provider": "anthropic",
            "llm_model": None,  # Use default
            "max_tokens": 2000,
            "temperature": 0.7,
        }

    def format_prompt(
        self,
        template: str,
        title: str,
        channel_name: str,
        transcript: str,
        duration: Optional[str] = None,
    ) -> str:
        """
        Format a prompt template with video data.

        Args:
            template: Prompt template with placeholders
            title: Video title
            channel_name: Channel name
            transcript: Video transcript
            duration: Video duration string

        Returns:
            Formatted prompt
        """
        return template.format(
            title=title,
            channel_name=channel_name,
            transcript=transcript,
            duration=duration or "Unknown",
        )

    def create_template(
        self,
        db: Session,
        name: str,
        system_prompt: str,
        user_prompt_template: str,
        category: Optional[str] = None,
        format_type: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        is_default: bool = False,
    ) -> PromptTemplate:
        """Create a new prompt template."""
        # If setting as default, unset current default
        if is_default:
            db.query(PromptTemplate).filter(
                PromptTemplate.is_default == True
            ).update({"is_default": False})

        template = PromptTemplate(
            name=name,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            category=category,
            format_type=format_type,
            llm_provider=llm_provider,
            llm_model=llm_model,
            is_default=is_default,
            is_active=True,
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        return template

    def get_all_templates(
        self,
        db: Session,
        active_only: bool = True,
    ) -> list[PromptTemplate]:
        """Get all prompt templates."""
        query = db.query(PromptTemplate)
        if active_only:
            query = query.filter(PromptTemplate.is_active == True)
        return query.all()


# Singleton instance
prompt_service = PromptService()
