"""Newsletter API endpoints."""

from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.newsletter import Newsletter, NewsletterTemplate, NewsletterStatus
from app.services.newsletter_service import newsletter_service
from app.integrations.beehiiv_client import beehiiv_client, BeehiivAPIError
from app.schemas.newsletter import (
    NewsletterGenerateRequest,
    NewsletterPreview,
    NewsletterResponse,
    NewsletterListResponse,
    VideoSummaryItem,
    PublishToBeehiivRequest,
    PublishToBeehiivResponse,
    NewsletterTemplateCreate,
    NewsletterTemplateUpdate,
    NewsletterTemplateResponse,
    ExportNewsletterRequest,
    ExportNewsletterResponse,
)

router = APIRouter()


# ============ Newsletter Generation ============

@router.post("/generate", response_model=NewsletterPreview)
async def generate_newsletter_preview(
    request: NewsletterGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a newsletter preview.

    Creates a preview of the newsletter with all video summaries.
    Does not save to database - use POST /newsletters to save.
    """
    preview = newsletter_service.generate_newsletter(
        db,
        current_user,
        days=request.days,
        channel_ids=request.include_channels,
        custom_title=request.title,
    )

    return NewsletterPreview(
        title=preview["title"],
        subtitle=preview.get("subtitle"),
        period_start=preview["period_start"],
        period_end=preview["period_end"],
        video_count=preview["video_count"],
        videos=[VideoSummaryItem(**v) for v in preview["videos"]],
        content_html=preview["content_html"],
    )


@router.post("", response_model=NewsletterResponse, status_code=status.HTTP_201_CREATED)
async def create_newsletter(
    request: NewsletterGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate and save a newsletter.

    Creates a newsletter draft that can be exported or published to Beehiiv.
    """
    # Generate preview
    preview = newsletter_service.generate_newsletter(
        db,
        current_user,
        days=request.days,
        channel_ids=request.include_channels,
        custom_title=request.title,
    )

    # Save to database
    newsletter = newsletter_service.save_newsletter(db, current_user, preview)

    return NewsletterResponse(
        id=newsletter.id,
        user_id=newsletter.user_id,
        title=newsletter.title,
        subtitle=newsletter.subtitle,
        period_start=newsletter.period_start,
        period_end=newsletter.period_end,
        video_count=newsletter.video_count,
        status=newsletter.status,
        beehiiv_post_id=newsletter.beehiiv_post_id,
        beehiiv_url=newsletter.beehiiv_url,
        sent_at=newsletter.sent_at,
        scheduled_for=newsletter.scheduled_for,
        created_at=newsletter.created_at,
    )


@router.get("", response_model=NewsletterListResponse)
async def list_newsletters(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List user's newsletters.
    """
    offset = (page - 1) * page_size
    newsletters, total = newsletter_service.get_user_newsletters(
        db, current_user, limit=page_size + 1, offset=offset
    )

    has_more = len(newsletters) > page_size
    newsletters = newsletters[:page_size]

    return NewsletterListResponse(
        items=[
            NewsletterResponse(
                id=n.id,
                user_id=n.user_id,
                title=n.title,
                subtitle=n.subtitle,
                period_start=n.period_start,
                period_end=n.period_end,
                video_count=n.video_count,
                status=n.status,
                beehiiv_post_id=n.beehiiv_post_id,
                beehiiv_url=n.beehiiv_url,
                sent_at=n.sent_at,
                scheduled_for=n.scheduled_for,
                created_at=n.created_at,
            )
            for n in newsletters
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/{newsletter_id}", response_model=NewsletterResponse)
async def get_newsletter(
    newsletter_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific newsletter.
    """
    newsletter = newsletter_service.get_newsletter_by_id(
        db, newsletter_id, user_id=current_user.id
    )

    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    return NewsletterResponse(
        id=newsletter.id,
        user_id=newsletter.user_id,
        title=newsletter.title,
        subtitle=newsletter.subtitle,
        period_start=newsletter.period_start,
        period_end=newsletter.period_end,
        video_count=newsletter.video_count,
        status=newsletter.status,
        beehiiv_post_id=newsletter.beehiiv_post_id,
        beehiiv_url=newsletter.beehiiv_url,
        sent_at=newsletter.sent_at,
        scheduled_for=newsletter.scheduled_for,
        created_at=newsletter.created_at,
    )


@router.get("/{newsletter_id}/html")
async def get_newsletter_html(
    newsletter_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the raw HTML content of a newsletter.
    """
    newsletter = newsletter_service.get_newsletter_by_id(
        db, newsletter_id, user_id=current_user.id
    )

    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    return Response(
        content=newsletter.content_html,
        media_type="text/html",
    )


@router.delete("/{newsletter_id}")
async def delete_newsletter(
    newsletter_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a newsletter.
    """
    newsletter = newsletter_service.get_newsletter_by_id(
        db, newsletter_id, user_id=current_user.id
    )

    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    db.delete(newsletter)
    db.commit()

    return {"message": "Newsletter deleted"}


# ============ Beehiiv Integration ============

@router.post("/{newsletter_id}/publish", response_model=PublishToBeehiivResponse)
async def publish_to_beehiiv(
    newsletter_id: UUID,
    schedule_for: Optional[datetime] = None,
    send_to_free: bool = True,
    send_to_premium: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Publish a newsletter to Beehiiv.

    Creates a draft or scheduled post in Beehiiv.
    """
    newsletter = newsletter_service.get_newsletter_by_id(
        db, newsletter_id, user_id=current_user.id
    )

    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    if newsletter.beehiiv_post_id:
        raise HTTPException(
            status_code=400,
            detail="Newsletter already published to Beehiiv"
        )

    try:
        # Create post in Beehiiv
        post = await beehiiv_client.create_post(
            title=newsletter.title,
            content_html=newsletter.content_html,
            subtitle=newsletter.subtitle,
            status="draft",
            send_to_free=send_to_free,
            send_to_premium=send_to_premium,
        )

        beehiiv_post_id = post.get("id")
        beehiiv_url = post.get("web_url")
        new_status = NewsletterStatus.DRAFT.value

        # Schedule if requested
        if schedule_for:
            await beehiiv_client.schedule_post(
                post_id=beehiiv_post_id,
                send_at=schedule_for.isoformat(),
            )
            new_status = NewsletterStatus.SCHEDULED.value

        # Update newsletter
        newsletter = newsletter_service.update_newsletter_status(
            db,
            newsletter,
            status=new_status,
            beehiiv_post_id=beehiiv_post_id,
            beehiiv_url=beehiiv_url,
            scheduled_for=schedule_for,
        )

        return PublishToBeehiivResponse(
            newsletter_id=newsletter.id,
            beehiiv_post_id=beehiiv_post_id,
            beehiiv_url=beehiiv_url,
            status=new_status,
            scheduled_for=schedule_for,
        )

    except BeehiivAPIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Beehiiv API error: {str(e)}"
        )


# ============ Export ============

@router.post("/{newsletter_id}/export", response_model=ExportNewsletterResponse)
async def export_newsletter(
    newsletter_id: UUID,
    format: str = Query("html", description="Export format: html or markdown"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export newsletter content.

    Supports HTML and Markdown formats.
    """
    newsletter = newsletter_service.get_newsletter_by_id(
        db, newsletter_id, user_id=current_user.id
    )

    if not newsletter:
        raise HTTPException(status_code=404, detail="Newsletter not found")

    if format == "html":
        content = newsletter.content_html
    elif format == "markdown":
        # Convert HTML to basic markdown
        content = _html_to_markdown(newsletter.content_html)
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'html' or 'markdown'")

    return ExportNewsletterResponse(
        newsletter_id=newsletter.id,
        title=newsletter.title,
        content=content,
        format=format,
    )


# ============ Templates (Admin) ============

@router.get("/templates", response_model=list[NewsletterTemplateResponse])
async def list_templates(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List newsletter templates.
    """
    query = db.query(NewsletterTemplate)
    if active_only:
        query = query.filter(NewsletterTemplate.is_active == True)
    templates = query.all()
    return templates


@router.post("/templates", response_model=NewsletterTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: NewsletterTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new newsletter template.
    """
    # Handle default
    if template.is_default:
        db.query(NewsletterTemplate).filter(
            NewsletterTemplate.is_default == True
        ).update({"is_default": False})

    new_template = NewsletterTemplate(
        name=template.name,
        description=template.description,
        header_html=template.header_html,
        footer_html=template.footer_html,
        video_card_html=template.video_card_html,
        primary_color=template.primary_color,
        secondary_color=template.secondary_color,
        background_color=template.background_color,
        is_default=template.is_default,
    )

    db.add(new_template)
    db.commit()
    db.refresh(new_template)

    return new_template


@router.patch("/templates/{template_id}", response_model=NewsletterTemplateResponse)
async def update_template(
    template_id: UUID,
    update: NewsletterTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a newsletter template.
    """
    template = db.query(NewsletterTemplate).filter(
        NewsletterTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Handle default
    if update.is_default:
        db.query(NewsletterTemplate).filter(
            NewsletterTemplate.is_default == True
        ).update({"is_default": False})

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)

    return template


# ============ Webhook Handler ============

@router.post("/webhook/beehiiv")
async def beehiiv_webhook(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Handle Beehiiv webhooks.

    Processes events like post sent, subscriber changes, etc.
    """
    event_type = payload.get("type")
    data = payload.get("data", {})

    if event_type == "post.sent":
        # Update newsletter status when post is sent
        post_id = data.get("id")
        if post_id:
            newsletter = db.query(Newsletter).filter(
                Newsletter.beehiiv_post_id == post_id
            ).first()

            if newsletter:
                newsletter.status = NewsletterStatus.SENT.value
                newsletter.sent_at = datetime.utcnow()
                db.commit()

    elif event_type == "subscription.created":
        # Could sync new subscribers to our user database
        pass

    elif event_type == "subscription.deleted":
        # Could update user records
        pass

    return {"status": "ok"}


# ============ Helper Functions ============

def _html_to_markdown(html: str) -> str:
    """
    Convert HTML to basic markdown.

    This is a simple converter for newsletter export.
    """
    import re

    # Remove HTML doctype, head, style tags
    md = re.sub(r'<!DOCTYPE[^>]*>', '', html)
    md = re.sub(r'<head>.*?</head>', '', md, flags=re.DOTALL)
    md = re.sub(r'<style[^>]*>.*?</style>', '', md, flags=re.DOTALL)

    # Convert headers
    md = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', md)
    md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', md)
    md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', md)

    # Convert links
    md = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', md)

    # Convert images
    md = re.sub(r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>',r'![\2](\1)', md)

    # Convert paragraphs
    md = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', md, flags=re.DOTALL)

    # Convert list items
    md = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', md)

    # Convert bold/strong
    md = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', md)

    # Convert italic/em
    md = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', md)

    # Remove remaining HTML tags
    md = re.sub(r'<[^>]+>', '', md)

    # Clean up whitespace
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = md.strip()

    return md
