"""Newsletter generation service."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.video import Video
from app.models.newsletter import Newsletter, NewsletterTemplate, NewsletterStatus
from app.services.subscription_service import subscription_service
from app.config import settings


# Default HTML template for video cards
DEFAULT_VIDEO_CARD_TEMPLATE = """
<div style="background: white; border-radius: 12px; margin-bottom: 24px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
    <!-- Thumbnail -->
    <div style="position: relative;">
        <img src="{thumbnail_url}" alt="{title}" style="width: 100%; height: auto; display: block;">
        {duration_badge}
    </div>

    <!-- Content -->
    <div style="padding: 20px;">
        <!-- Channel info -->
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
            {channel_thumbnail}
            <div>
                <div style="font-weight: 600; color: {primary_color}; font-size: 14px;">{channel_name}</div>
                <div style="font-size: 12px; color: #6B7280;">{published_date} &bull; {view_count} views</div>
            </div>
        </div>

        <!-- Title -->
        <h2 style="margin: 0 0 12px; font-size: 18px; font-weight: 700; color: {secondary_color}; line-height: 1.3;">
            <a href="https://www.youtube.com/watch?v={youtube_video_id}" style="color: inherit; text-decoration: none;">{title}</a>
        </h2>

        <!-- Summary -->
        <p style="margin: 0 0 16px; color: #4B5563; font-size: 14px; line-height: 1.6;">
            {summary_text}
        </p>

        {key_insights_section}

        {key_takeaways_section}

        {notable_quotes_section}

        <!-- Watch button -->
        <div style="margin-top: 16px;">
            <a href="https://www.youtube.com/watch?v={youtube_video_id}" style="display: inline-block; background: {primary_color}; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px;">
                Watch Video
            </a>
        </div>
    </div>
</div>
"""

DEFAULT_HEADER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: {background_color}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="margin: 0 0 8px; font-size: 28px; font-weight: 700; color: {secondary_color};">{title}</h1>
            {subtitle_section}
            <p style="margin: 16px 0 0; font-size: 14px; color: #6B7280;">
                {period_start} - {period_end} &bull; {video_count} videos
            </p>
        </div>

        <!-- Videos -->
"""

DEFAULT_FOOTER_TEMPLATE = """
        <!-- Footer -->
        <div style="text-align: center; margin-top: 40px; padding-top: 24px; border-top: 1px solid #E5E7EB;">
            <p style="margin: 0 0 8px; font-size: 14px; color: #6B7280;">
                You're receiving this because you subscribed to these channels.
            </p>
            <p style="margin: 0; font-size: 12px; color: #9CA3AF;">
                Powered by YouTube Newsletter
            </p>
        </div>
    </div>
</body>
</html>
"""


class NewsletterService:
    """Service for generating and managing newsletters."""

    def generate_newsletter(
        self,
        db: Session,
        user: User,
        days: int = 7,
        channel_ids: Optional[list[UUID]] = None,
        custom_title: Optional[str] = None,
    ) -> dict:
        """
        Generate a newsletter preview for a user.

        Args:
            db: Database session
            user: User to generate newsletter for
            days: Number of days to look back
            channel_ids: Specific channels to include (None = all subscribed)
            custom_title: Custom title override

        Returns:
            Newsletter preview dict with HTML and metadata
        """
        # Calculate period
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        # Get subscribed channels
        if channel_ids:
            subscriptions = subscription_service.get_user_subscriptions(db, user)
            channels = [s.channel for s in subscriptions if s.channel_id in channel_ids]
        else:
            subscriptions = subscription_service.get_user_subscriptions(db, user)
            channels = [s.channel for s in subscriptions]

        if not channels:
            return {
                "title": custom_title or "Your Weekly Video Digest",
                "subtitle": None,
                "period_start": period_start,
                "period_end": period_end,
                "video_count": 0,
                "videos": [],
                "content_html": self._generate_empty_newsletter_html(),
            }

        # Get videos with summaries from these channels
        channel_ids_list = [c.id for c in channels]
        videos = db.query(Video).filter(
            Video.channel_id.in_(channel_ids_list),
            Video.published_at >= period_start,
            Video.published_at <= period_end,
            Video.summary != None,
        ).order_by(Video.published_at.desc()).all()

        # Build video items
        video_items = []
        for video in videos:
            if video.summary:
                video_items.append({
                    "video_id": video.id,
                    "youtube_video_id": video.youtube_video_id,
                    "title": video.title,
                    "channel_name": video.channel.name if video.channel else "Unknown",
                    "channel_thumbnail": video.channel.thumbnail_url if video.channel else None,
                    "thumbnail_url": video.thumbnail_high_url or video.thumbnail_url,
                    "duration_seconds": video.duration_seconds,
                    "published_at": video.published_at,
                    "view_count": video.view_count,
                    "summary_text": video.summary.summary_text,
                    "key_insights": video.summary.key_insights or [],
                    "notable_quotes": video.summary.notable_quotes or [],
                    "timestamp_moments": video.summary.timestamp_moments or [],
                    "key_takeaways": video.summary.key_takeaways or [],
                })

        # Generate title
        title = custom_title or self._generate_title(period_start, period_end)
        subtitle = f"{len(video_items)} new videos from your subscriptions"

        # Get template
        template = self._get_default_template(db)

        # Generate HTML
        content_html = self._generate_newsletter_html(
            title=title,
            subtitle=subtitle,
            period_start=period_start,
            period_end=period_end,
            videos=video_items,
            template=template,
        )

        return {
            "title": title,
            "subtitle": subtitle,
            "period_start": period_start,
            "period_end": period_end,
            "video_count": len(video_items),
            "videos": video_items,
            "content_html": content_html,
        }

    def save_newsletter(
        self,
        db: Session,
        user: User,
        preview: dict,
    ) -> Newsletter:
        """
        Save a newsletter preview to the database.

        Args:
            db: Database session
            user: User who owns the newsletter
            preview: Newsletter preview dict

        Returns:
            Created Newsletter model
        """
        newsletter = Newsletter(
            user_id=user.id,
            title=preview["title"],
            subtitle=preview.get("subtitle"),
            content_html=preview["content_html"],
            period_start=preview["period_start"],
            period_end=preview["period_end"],
            video_ids=[str(v["video_id"]) for v in preview["videos"]],
            video_count=preview["video_count"],
            status=NewsletterStatus.DRAFT.value,
        )

        db.add(newsletter)
        db.commit()
        db.refresh(newsletter)

        return newsletter

    def get_user_newsletters(
        self,
        db: Session,
        user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Newsletter], int]:
        """Get newsletters for a user."""
        query = db.query(Newsletter).filter(Newsletter.user_id == user.id)
        total = query.count()
        newsletters = query.order_by(Newsletter.created_at.desc()).offset(offset).limit(limit).all()
        return newsletters, total

    def get_newsletter_by_id(
        self,
        db: Session,
        newsletter_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Newsletter]:
        """Get a specific newsletter."""
        query = db.query(Newsletter).filter(Newsletter.id == newsletter_id)
        if user_id:
            query = query.filter(Newsletter.user_id == user_id)
        return query.first()

    def update_newsletter_status(
        self,
        db: Session,
        newsletter: Newsletter,
        status: str,
        beehiiv_post_id: Optional[str] = None,
        beehiiv_url: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> Newsletter:
        """Update newsletter status after Beehiiv operations."""
        newsletter.status = status
        if beehiiv_post_id:
            newsletter.beehiiv_post_id = beehiiv_post_id
        if beehiiv_url:
            newsletter.beehiiv_url = beehiiv_url
        if sent_at:
            newsletter.sent_at = sent_at
        if scheduled_for:
            newsletter.scheduled_for = scheduled_for

        db.commit()
        db.refresh(newsletter)
        return newsletter

    def _get_default_template(self, db: Session) -> Optional[NewsletterTemplate]:
        """Get the default newsletter template."""
        return db.query(NewsletterTemplate).filter(
            NewsletterTemplate.is_default == True,
            NewsletterTemplate.is_active == True,
        ).first()

    def _generate_title(self, start: datetime, end: datetime) -> str:
        """Generate a newsletter title based on the period."""
        if (end - start).days <= 7:
            return f"Your Weekly Video Digest - {end.strftime('%B %d, %Y')}"
        else:
            return f"Video Digest: {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"

    def _generate_newsletter_html(
        self,
        title: str,
        subtitle: Optional[str],
        period_start: datetime,
        period_end: datetime,
        videos: list[dict],
        template: Optional[NewsletterTemplate] = None,
    ) -> str:
        """Generate the full newsletter HTML."""
        # Get template values or defaults
        primary_color = template.primary_color if template else "#3B82F6"
        secondary_color = template.secondary_color if template else "#1F2937"
        background_color = template.background_color if template else "#F9FAFB"
        header_html = template.header_html if template and template.header_html else DEFAULT_HEADER_TEMPLATE
        footer_html = template.footer_html if template and template.footer_html else DEFAULT_FOOTER_TEMPLATE
        video_card_html = template.video_card_html if template and template.video_card_html else DEFAULT_VIDEO_CARD_TEMPLATE

        # Build subtitle section
        subtitle_section = ""
        if subtitle:
            subtitle_section = f'<p style="margin: 0; font-size: 16px; color: #6B7280;">{subtitle}</p>'

        # Format header
        html = header_html.format(
            title=title,
            subtitle_section=subtitle_section,
            period_start=period_start.strftime("%B %d"),
            period_end=period_end.strftime("%B %d, %Y"),
            video_count=len(videos),
            primary_color=primary_color,
            secondary_color=secondary_color,
            background_color=background_color,
        )

        # Add video cards
        for video in videos:
            html += self._generate_video_card_html(video, video_card_html, primary_color, secondary_color)

        # Add footer
        html += footer_html.format(
            primary_color=primary_color,
            secondary_color=secondary_color,
            background_color=background_color,
        )

        return html

    def _generate_video_card_html(
        self,
        video: dict,
        template: str,
        primary_color: str,
        secondary_color: str,
    ) -> str:
        """Generate HTML for a single video card."""
        # Duration badge
        duration_badge = ""
        if video.get("duration_seconds"):
            minutes = video["duration_seconds"] // 60
            seconds = video["duration_seconds"] % 60
            duration_badge = f'''
                <div style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600;">
                    {minutes}:{seconds:02d}
                </div>
            '''

        # Channel thumbnail
        channel_thumbnail = ""
        if video.get("channel_thumbnail"):
            channel_thumbnail = f'''
                <img src="{video['channel_thumbnail']}" alt="{video['channel_name']}" style="width: 36px; height: 36px; border-radius: 50%; margin-right: 10px;">
            '''

        # Key insights section
        key_insights_section = ""
        if video.get("key_insights"):
            insights_html = "".join([
                f'<li style="margin-bottom: 6px; color: #4B5563;">{insight}</li>'
                for insight in video["key_insights"][:3]
            ])
            key_insights_section = f'''
                <div style="background: {primary_color}10; border-left: 3px solid {primary_color}; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
                    <div style="font-weight: 600; color: {primary_color}; font-size: 13px; margin-bottom: 8px;">KEY INSIGHTS</div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px;">
                        {insights_html}
                    </ul>
                </div>
            '''

        # Key takeaways section
        key_takeaways_section = ""
        if video.get("key_takeaways"):
            takeaways_html = "".join([
                f'<li style="margin-bottom: 6px; color: #4B5563;">{takeaway}</li>'
                for takeaway in video["key_takeaways"][:3]
            ])
            key_takeaways_section = f'''
                <div style="background: #FEF3C7; border-left: 3px solid #F59E0B; padding: 12px 16px; margin: 16px 0; border-radius: 0 8px 8px 0;">
                    <div style="font-weight: 600; color: #B45309; font-size: 13px; margin-bottom: 8px;">KEY TAKEAWAYS</div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px;">
                        {takeaways_html}
                    </ul>
                </div>
            '''

        # Notable quotes section
        notable_quotes_section = ""
        if video.get("notable_quotes"):
            quotes = video["notable_quotes"][:2]
            quotes_html = ""
            for quote in quotes:
                quote_text = quote.get("quote", quote) if isinstance(quote, dict) else quote
                quotes_html += f'''
                    <div style="font-style: italic; color: #4B5563; padding: 8px 0; border-bottom: 1px solid #E5E7EB;">
                        "{quote_text}"
                    </div>
                '''
            notable_quotes_section = f'''
                <div style="margin: 16px 0;">
                    <div style="font-weight: 600; color: {secondary_color}; font-size: 13px; margin-bottom: 8px;">NOTABLE QUOTES</div>
                    {quotes_html}
                </div>
            '''

        # View count formatting
        view_count = video.get("view_count", 0)
        if view_count >= 1_000_000:
            view_count_str = f"{view_count / 1_000_000:.1f}M"
        elif view_count >= 1_000:
            view_count_str = f"{view_count / 1_000:.1f}K"
        else:
            view_count_str = str(view_count)

        # Published date
        published_date = video["published_at"].strftime("%b %d, %Y") if isinstance(video["published_at"], datetime) else video["published_at"]

        return template.format(
            youtube_video_id=video["youtube_video_id"],
            title=video["title"],
            channel_name=video["channel_name"],
            channel_thumbnail=channel_thumbnail,
            thumbnail_url=video.get("thumbnail_url") or "https://via.placeholder.com/600x338?text=No+Thumbnail",
            duration_badge=duration_badge,
            published_date=published_date,
            view_count=view_count_str,
            summary_text=video["summary_text"],
            key_insights_section=key_insights_section,
            key_takeaways_section=key_takeaways_section,
            notable_quotes_section=notable_quotes_section,
            primary_color=primary_color,
            secondary_color=secondary_color,
        )

    def _generate_empty_newsletter_html(self) -> str:
        """Generate HTML for an empty newsletter."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; background-color: #F9FAFB; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px; text-align: center;">
                <h1 style="color: #1F2937;">No New Videos</h1>
                <p style="color: #6B7280;">No new videos with summaries were found for this period. Subscribe to more channels or check back later!</p>
            </div>
        </body>
        </html>
        """


# Singleton instance
newsletter_service = NewsletterService()
