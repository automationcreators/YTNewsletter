# Project Context

## Overview

YouTube Newsletter Summarization SaaS - An AI-powered platform that automatically summarizes YouTube videos from subscribed channels and delivers weekly email newsletters.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js 14    │────▶│    FastAPI      │────▶│   PostgreSQL    │
│   Frontend      │     │    Backend      │     │   Database      │
│   (Port 3000)   │     │   (Port 8000)   │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────┴────────┐
                        ▼                 ▼
               ┌─────────────┐   ┌─────────────┐
               │   Celery    │   │    Redis    │
               │   Workers   │   │    Cache    │
               └─────────────┘   └─────────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
     ┌───────────┐ ┌─────────┐ ┌─────────┐
     │  YouTube  │ │   LLM   │ │ Beehiiv │
     │  Data API │ │  (AI)   │ │   API   │
     └───────────┘ └─────────┘ └─────────┘
```

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **ORM**: SQLAlchemy 2.0 with async support
- **Database**: PostgreSQL
- **Cache/Queue**: Redis
- **Task Queue**: Celery
- **Migrations**: Alembic
- **Auth**: Google OAuth 2.0 + JWT

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: React Query (TanStack Query)
- **Icons**: Lucide React

### External APIs
- YouTube Data API v3
- Anthropic Claude / OpenAI GPT
- Beehiiv (newsletter publishing)

## Data Models

### User
- Google OAuth credentials
- Subscription tier (free/premium)
- Max channels limit

### Channel
- YouTube channel metadata
- Classification (category, format, size)
- Subscriber count, video count

### Subscription
- User-channel relationship
- Created timestamp

### Video
- YouTube video metadata
- Transcript (when available)
- Published date, view count, duration

### Summary
- AI-generated summary text
- Key insights (array)
- Notable quotes (array)
- Topics/tags (array)

### Newsletter
- Generated HTML content
- Included videos
- Status (draft/scheduled/sent)
- Beehiiv integration status

## Subscription Tiers

| Feature | Free | Premium |
|---------|------|---------|
| Channels | 3 | 20 |
| Digest Frequency | Weekly | Daily |
| AI Summaries | Yes | Yes |
| Priority Processing | No | Yes |
| Price | $0 | $9/month |

## Environment Variables

### Required (Backend)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth secret
- `YOUTUBE_API_KEY` - YouTube Data API key
- `JWT_SECRET_KEY` - Secret for JWT tokens
- One of: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

### Optional (Backend)
- `BEEHIIV_API_KEY` - For newsletter publishing
- `BEEHIIV_PUBLICATION_ID` - Beehiiv publication ID

### Required (Frontend)
- `NEXT_PUBLIC_API_URL` - Backend API URL

## Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| fetch_all_channel_videos | Every 2 hours | Fetch new videos from subscribed channels |
| process_pending_summaries | Every hour | Generate AI summaries for new videos |
| send_weekly_newsletters | Monday 9 AM UTC | Send weekly digest emails |
| cleanup_old_data | Daily 3 AM UTC | Remove old videos and summaries |

## API Routes

### Authentication
- `GET /api/v1/auth/google/login` - Initiate OAuth
- `GET /api/v1/auth/google/callback` - OAuth callback
- `GET /api/v1/users/me` - Current user

### Channels
- `GET /api/v1/channels/search?q=` - Search YouTube
- `GET /api/v1/channels/resolve?input=` - Resolve URL/handle
- `GET /api/v1/channels/{id}` - Get channel
- `GET /api/v1/channels/{id}/videos` - Get channel videos

### Subscriptions
- `GET /api/v1/subscriptions` - List subscriptions
- `POST /api/v1/subscriptions` - Subscribe
- `DELETE /api/v1/subscriptions/{channel_id}` - Unsubscribe
- `GET /api/v1/subscriptions/limit` - Check limits

### Videos
- `GET /api/v1/videos/feed` - Video feed
- `GET /api/v1/videos/db/{id}` - Get video
- `GET /api/v1/videos/db/{id}/summary` - Get summary
- `POST /api/v1/videos/db/{id}/summary` - Generate summary

### Newsletters
- `GET /api/v1/newsletters` - List newsletters
- `POST /api/v1/newsletters` - Create newsletter
- `GET /api/v1/newsletters/{id}` - Get newsletter
- `GET /api/v1/newsletters/{id}/html` - Get HTML
- `POST /api/v1/newsletters/{id}/publish` - Publish
- `POST /api/v1/newsletters/{id}/export` - Export
- `DELETE /api/v1/newsletters/{id}` - Delete

## Development Commands

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev

# Database migrations
alembic upgrade head

# Docker (full stack)
docker-compose up -d
```
