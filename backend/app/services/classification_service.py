"""Channel classification service using LLM."""

import json
import re
from typing import Optional
from sqlalchemy.orm import Session
from app.models.channel import Channel
from app.integrations.llm_client import LLMFactory
from app.services.channel_service import channel_service


CLASSIFICATION_PROMPT = """Analyze this YouTube channel and classify it.

Channel Name: {name}
Description: {description}
Subscriber Count: {subscriber_count}

Based on this information, classify the channel:

1. **Category** - Choose ONE from:
   - tech (technology reviews, software, gadgets)
   - education (tutorials, courses, how-to)
   - entertainment (comedy, vlogs, lifestyle)
   - business (entrepreneurship, finance, marketing)
   - gaming (game reviews, gameplay, esports)
   - music (music videos, covers, production)
   - news (current events, politics, journalism)
   - science (scientific content, research, experiments)
   - health (fitness, wellness, medical)
   - travel (travel vlogs, destinations, culture)
   - food (cooking, recipes, food reviews)
   - sports (sports coverage, training, commentary)
   - arts (art creation, design, crafts)
   - other (if none fit well)

2. **Format Type** - Choose ONE from:
   - tutorials (step-by-step guides, how-to content)
   - reviews (product/service reviews, comparisons)
   - vlogs (personal video blogs, day-in-life)
   - interviews (conversations, podcasts with guests)
   - news (news coverage, updates, commentary)
   - entertainment (scripted content, comedy, skits)
   - documentary (in-depth explorations, storytelling)
   - livestream (primarily live content)
   - shorts (primarily short-form content)
   - mixed (combination of formats)

3. **Suggested Tags** - List 2-4 relevant tags for this channel

Respond in JSON format:
{{
    "category": "tech",
    "format_type": "reviews",
    "tags": ["gadgets", "smartphones"],
    "confidence": 0.85,
    "reasoning": "Brief explanation of classification"
}}"""


class ClassificationService:
    """Service for classifying YouTube channels using LLM."""

    VALID_CATEGORIES = [
        "tech", "education", "entertainment", "business", "gaming",
        "music", "news", "science", "health", "travel", "food",
        "sports", "arts", "other"
    ]

    VALID_FORMAT_TYPES = [
        "tutorials", "reviews", "vlogs", "interviews", "news",
        "entertainment", "documentary", "livestream", "shorts", "mixed"
    ]

    def classify_channel(
        self,
        db: Session,
        channel: Channel,
        force_reclassify: bool = False,
    ) -> dict:
        """
        Classify a channel using LLM.

        Args:
            db: Database session
            channel: Channel to classify
            force_reclassify: If True, reclassify even if already classified

        Returns:
            Classification result dict
        """
        # Check if already classified
        if not force_reclassify and channel.category and channel.format_type:
            return {
                "category": channel.category,
                "format_type": channel.format_type,
                "confidence": channel.classification_confidence,
                "already_classified": True,
            }

        # Build prompt
        prompt = CLASSIFICATION_PROMPT.format(
            name=channel.name,
            description=channel.description or "No description available",
            subscriber_count=self._format_subscriber_count(channel.subscriber_count),
        )

        # Get LLM client
        llm_client = LLMFactory.get_default()

        # Generate classification
        response = llm_client.generate(
            prompt=prompt,
            system_prompt="You are a YouTube channel analyst. Classify channels accurately based on their content type.",
            max_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent classifications
        )

        # Parse response
        classification = self._parse_classification(response.content)

        # Validate and update channel
        category = classification.get("category", "other")
        format_type = classification.get("format_type", "mixed")
        confidence = classification.get("confidence", 0.5)
        tags = classification.get("tags", [])

        # Ensure valid values
        if category not in self.VALID_CATEGORIES:
            category = "other"
        if format_type not in self.VALID_FORMAT_TYPES:
            format_type = "mixed"

        # Update channel
        channel_service.set_classification(
            db,
            channel,
            category=category,
            format_type=format_type,
            confidence=confidence,
        )

        # Add tags
        for tag in tags[:5]:  # Limit to 5 tags
            channel_service.add_tag(db, channel, tag_name=tag)

        return {
            "category": category,
            "format_type": format_type,
            "confidence": confidence,
            "tags": tags,
            "reasoning": classification.get("reasoning", ""),
            "already_classified": False,
        }

    def classify_channel_batch(
        self,
        db: Session,
        channels: list[Channel],
    ) -> list[dict]:
        """Classify multiple channels."""
        results = []
        for channel in channels:
            try:
                result = self.classify_channel(db, channel)
                result["channel_id"] = str(channel.id)
                result["channel_name"] = channel.name
                results.append(result)
            except Exception as e:
                results.append({
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                    "error": str(e),
                })
        return results

    def get_unclassified_channels(
        self,
        db: Session,
        limit: int = 50,
    ) -> list[Channel]:
        """Get channels that haven't been classified yet."""
        return db.query(Channel).filter(
            (Channel.category == None) | (Channel.format_type == None)
        ).limit(limit).all()

    def _parse_classification(self, content: str) -> dict:
        """Parse LLM classification response."""
        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # Fallback: try to extract from text
        result = {
            "category": "other",
            "format_type": "mixed",
            "confidence": 0.5,
            "tags": [],
        }

        content_lower = content.lower()

        # Try to find category
        for cat in self.VALID_CATEGORIES:
            if cat in content_lower:
                result["category"] = cat
                break

        # Try to find format type
        for fmt in self.VALID_FORMAT_TYPES:
            if fmt in content_lower:
                result["format_type"] = fmt
                break

        return result

    def _format_subscriber_count(self, count: Optional[int]) -> str:
        """Format subscriber count for display."""
        if not count:
            return "Unknown"

        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        else:
            return str(count)


# Singleton instance
classification_service = ClassificationService()
