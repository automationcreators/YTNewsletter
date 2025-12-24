"""Summary generation service."""

import json
import re
from typing import Optional
from sqlalchemy.orm import Session
from app.models.video import Video
from app.models.summary import VideoSummary
from app.models.channel import Channel
from app.integrations.llm_client import LLMFactory, LLMResponse
from app.services.prompt_service import prompt_service


class SummaryService:
    """Service for generating video summaries using LLMs."""

    def get_summary(self, db: Session, video: Video) -> Optional[VideoSummary]:
        """Get existing summary for a video."""
        return db.query(VideoSummary).filter(
            VideoSummary.video_id == video.id
        ).first()

    def generate_summary(
        self,
        db: Session,
        video: Video,
        force_regenerate: bool = False,
    ) -> Optional[VideoSummary]:
        """
        Generate a summary for a video.

        Args:
            db: Database session
            video: Video to summarize
            force_regenerate: If True, regenerate even if summary exists

        Returns:
            VideoSummary or None if transcript unavailable
        """
        # Check for existing summary
        if not force_regenerate and video.summary:
            return video.summary

        # Ensure transcript exists
        if not video.transcript:
            video.summary_status = "failed"
            db.commit()
            return None

        # Get channel for prompt config
        channel = video.channel

        # Get prompt configuration
        prompt_config = prompt_service.get_prompt_config(db, channel)

        # Format duration
        duration_str = self._format_duration(video.duration_seconds)

        # Format the prompt
        user_prompt = prompt_service.format_prompt(
            template=prompt_config["user_prompt_template"],
            title=video.title,
            channel_name=channel.name,
            transcript=video.transcript.content,
            duration=duration_str,
        )

        # Get LLM client
        llm_client = LLMFactory.create(
            provider=prompt_config["llm_provider"],
            model=prompt_config["llm_model"],
        )

        try:
            # Update status
            video.summary_status = "processing"
            db.commit()

            # Generate summary
            response = llm_client.generate(
                prompt=user_prompt,
                system_prompt=prompt_config["system_prompt"],
                max_tokens=prompt_config["max_tokens"],
                temperature=prompt_config["temperature"],
            )

            # Parse response
            summary_data = self._parse_summary_response(response.content)

            # Calculate cost (rough estimate)
            cost_cents = self._estimate_cost(
                response.provider,
                response.model,
                response.input_tokens,
                response.output_tokens,
            )

            # Create or update summary
            if video.summary:
                summary = video.summary
                summary.summary_text = summary_data["summary"]
                summary.key_insights = summary_data["key_insights"]
                summary.notable_quotes = summary_data["notable_quotes"]
                summary.timestamp_moments = summary_data["timestamp_moments"]
                summary.key_takeaways = summary_data["key_takeaways"]
                summary.llm_provider = response.provider
                summary.llm_model = response.model
                summary.prompt_template_used = prompt_config["user_prompt_template"][:500]
                summary.generation_tokens = response.total_tokens
                summary.generation_cost_cents = cost_cents
            else:
                summary = VideoSummary(
                    video_id=video.id,
                    summary_text=summary_data["summary"],
                    key_insights=summary_data["key_insights"],
                    notable_quotes=summary_data["notable_quotes"],
                    timestamp_moments=summary_data["timestamp_moments"],
                    key_takeaways=summary_data["key_takeaways"],
                    llm_provider=response.provider,
                    llm_model=response.model,
                    prompt_template_used=prompt_config["user_prompt_template"][:500],
                    generation_tokens=response.total_tokens,
                    generation_cost_cents=cost_cents,
                )
                db.add(summary)

            # Update video status
            video.summary_status = "completed"
            db.commit()
            db.refresh(summary)

            return summary

        except Exception as e:
            video.summary_status = "failed"
            db.commit()
            raise e

    def _parse_summary_response(self, content: str) -> dict:
        """
        Parse the LLM response into structured summary data.

        Args:
            content: Raw LLM response

        Returns:
            Parsed summary dictionary
        """
        # Try to parse as JSON first
        try:
            # Find JSON in response (might be wrapped in markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "summary": data.get("summary", ""),
                    "key_insights": data.get("key_insights", []),
                    "notable_quotes": data.get("notable_quotes", []),
                    "timestamp_moments": data.get("timestamp_moments", []),
                    "key_takeaways": data.get("key_takeaways", []),
                }
        except json.JSONDecodeError:
            pass

        # Fallback: parse markdown-style response
        return self._parse_markdown_response(content)

    def _parse_markdown_response(self, content: str) -> dict:
        """Parse a markdown-formatted response."""
        result = {
            "summary": "",
            "key_insights": [],
            "notable_quotes": [],
            "timestamp_moments": [],
            "key_takeaways": [],
        }

        # Split into sections
        sections = re.split(r'\n##?\s*\*?\*?', content)

        for section in sections:
            section_lower = section.lower()

            if "summary" in section_lower[:50]:
                # Extract summary text (everything after the header)
                lines = section.split('\n', 1)
                if len(lines) > 1:
                    result["summary"] = lines[1].strip()

            elif "insight" in section_lower[:50]:
                result["key_insights"] = self._extract_bullet_points(section)

            elif "quote" in section_lower[:50]:
                quotes = self._extract_bullet_points(section)
                result["notable_quotes"] = [
                    {"quote": q, "timestamp": None} for q in quotes
                ]

            elif "timestamp" in section_lower[:50] or "moment" in section_lower[:50]:
                moments = self._extract_bullet_points(section)
                result["timestamp_moments"] = [
                    {"timestamp": 0, "description": m} for m in moments
                ]

            elif "takeaway" in section_lower[:50]:
                result["key_takeaways"] = self._extract_bullet_points(section)

        return result

    def _extract_bullet_points(self, text: str) -> list[str]:
        """Extract bullet points from text."""
        points = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith(('-', '*', '•', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                # Remove bullet/number prefix
                point = re.sub(r'^[-*•\d]+\.?\s*', '', line).strip()
                if point:
                    points.append(point)
        return points

    def _format_duration(self, seconds: Optional[int]) -> str:
        """Format duration in seconds to human readable string."""
        if not seconds:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _estimate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> int:
        """
        Estimate cost in cents.

        Rough estimates based on typical pricing.
        """
        # Pricing per 1M tokens (in cents)
        pricing = {
            "anthropic": {
                "claude-sonnet-4-20250514": {"input": 300, "output": 1500},
                "claude-3-5-sonnet": {"input": 300, "output": 1500},
                "claude-3-haiku": {"input": 25, "output": 125},
            },
            "openai": {
                "gpt-4-turbo-preview": {"input": 1000, "output": 3000},
                "gpt-4o": {"input": 500, "output": 1500},
                "gpt-3.5-turbo": {"input": 50, "output": 150},
            },
        }

        provider_pricing = pricing.get(provider, {})
        model_pricing = provider_pricing.get(model, {"input": 300, "output": 1500})

        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]

        return int((input_cost + output_cost) * 100)  # Convert to cents


# Singleton instance
summary_service = SummaryService()
