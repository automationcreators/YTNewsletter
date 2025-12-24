# YouTube Newsletter Summarization SaaS

AI-powered YouTube video summarization with automated weekly newsletter delivery via Beehiiv.

## Features

- **Google OAuth Authentication** - Secure login with Google accounts
- **YouTube Channel Subscriptions** - Search and subscribe to YouTube channels
- **AI Video Summaries** - Automatic summarization with key insights, quotes, and topics
- **Channel Classification** - Categorize channels by type, size, and format
- **Newsletter Generation** - Create HTML newsletters from video summaries
- **Beehiiv Integration** - Publish directly to your Beehiiv newsletter
- **Tiered Subscriptions** - Free tier (3 channels) and Premium tier (20 channels)

## Tech Stack

### Backend
- **FastAPI** - Python async web framework
- **SQLAlchemy** - ORM with PostgreSQL
- **Celery + Redis** - Background task processing
- **Alembic** - Database migrations
- **LLM Integration** - Anthropic Claude / OpenAI GPT

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **React Query** - Server state management
- **Lucide Icons** - Modern icon library

## Project Structure

```
YTNewsletter/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Config, security, deps
│   │   ├── db/              # Database setup
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── tasks/           # Celery tasks
│   ├── alembic/             # Database migrations
│   ├── docker-compose.yml
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── app/             # Next.js pages
    │   ├── components/      # React components
    │   ├── contexts/        # React contexts
    │   └── lib/             # Utilities & API client
    ├── package.json
    └── vercel.json
```

## Prerequisites

- **Node.js** >= 20.9.0 (for Next.js 15)
- **Python** >= 3.11
- **Docker & Docker Compose**
- **PostgreSQL** (or use Docker)
- **Redis** (or use Docker)

## Setup

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repo-url>
cd YTNewsletter

# Backend environment
cd backend
cp .env.example .env
# Edit .env with your credentials
```

### 2. Required Environment Variables

#### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/yt_newsletter

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# YouTube Data API
YOUTUBE_API_KEY=your-youtube-api-key

# LLM (choose one)
ANTHROPIC_API_KEY=your-anthropic-key
# or
OPENAI_API_KEY=your-openai-key

# Beehiiv (optional)
BEEHIIV_API_KEY=your-beehiiv-api-key
BEEHIIV_PUBLICATION_ID=your-publication-id
```

#### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Run with Docker (Recommended)

```bash
cd backend
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- FastAPI backend (port 8000)
- Celery worker
- Celery beat scheduler

### 4. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000

### 5. Database Migrations

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/google/login` | GET | Initiate Google OAuth |
| `/users/me` | GET | Get current user |
| `/channels/search` | GET | Search YouTube channels |
| `/subscriptions` | GET/POST/DELETE | Manage subscriptions |
| `/videos/feed` | GET | Get video feed |
| `/videos/db/{id}/summary` | GET/POST | Get/generate summary |
| `/newsletters` | GET/POST | List/create newsletters |
| `/newsletters/{id}/publish` | POST | Publish to Beehiiv |

## Background Tasks

Celery handles:
- **Video fetching** - Every 2 hours
- **Summary generation** - Every hour for pending videos
- **Weekly newsletters** - Monday 9 AM UTC
- **Data cleanup** - Daily at 3 AM UTC

## Deployment

### Frontend (Vercel)

1. Connect repository to Vercel
2. Set environment variables:
   - `NEXT_PUBLIC_API_URL` = your backend URL
3. Deploy

### Backend (Railway/Render)

1. Create PostgreSQL and Redis instances
2. Deploy backend with environment variables
3. Run `alembic upgrade head` for migrations

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run lint
npm run build
```

## License

MIT License
