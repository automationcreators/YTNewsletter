# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This App Does

YTNewsletter is an AI-powered YouTube content aggregation and newsletter platform. Users authenticate via Google OAuth, subscribe to YouTube channels, get AI-generated video summaries (via OpenAI), and auto-generate newsletters they can export or publish to Beehiiv.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS 3, TanStack React Query |
| Backend | FastAPI (Python 3.9), SQLAlchemy ORM, JWT auth |
| Integrations | YouTube API, OpenAI API, Beehiiv API |
| Task Queue | Kombu |

## Commands

**Frontend** (from `frontend/`):
```bash
npm run dev      # dev server on port 3000
npm run build    # production build
npm run lint     # ESLint
```

**Backend** (from `backend/`):
```bash
source venv/bin/activate
uvicorn app.main:app --reload   # dev server on port 8000
```

## Architecture

### Backend

Routes are in `app/api/v1/` — one file per resource (`channels.py`, `videos.py`, `newsletters.py`, `subscriptions.py`, `users.py`, `auth.py`, `admin.py`). All routes registered in `router.py`.

Business logic lives in `app/services/` (not in routes):
- `newsletter_service.py` — newsletter generation
- `video_service.py` — video DB operations
- `summary_service.py` — OpenAI summary generation
- `transcript_service.py` — transcript fetching (with Whisper fallback)
- `google_oauth.py` — OAuth flow
- `user_service.py` — user CRUD

External API wrappers are in `app/integrations/`:
- `youtube_client.py` — YouTube API
- `beehiiv_client.py` — Beehiiv API

Models are in `app/models/`.

### Frontend

App Router pages in `src/app/`: `dashboard/`, `channels/`, `feed/[id]/`, `newsletters/`, `settings/`, `login/`, `auth/callback/`.

Shared utilities:
- `src/lib/api` — API client; all backend calls go through here
- `src/lib/types` — shared TypeScript types
- `src/contexts/AuthContext` — auth state
- `src/components/ui/` — Button, Card, Input base components

The frontend expects the backend at `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api/v1`).

## Key API Endpoints

- `GET /videos/feed` — paginated video feed from subscriptions
- `POST /videos/db/{video_id}/summary` — trigger AI summary generation
- `POST /newsletters/generate` — generate newsletter preview
- `POST /newsletters/{id}/publish` — publish to Beehiiv
- `POST /newsletters/{id}/export` — export as HTML or Markdown
- `GET /channels/search` — YouTube channel search
- `POST /auth/google/token` — exchange OAuth code for JWT

## Environment Variables Needed

```
NEXT_PUBLIC_API_URL          # frontend → backend URL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
OPENAI_API_KEY
YOUTUBE_API_KEY
BEEHIIV_API_KEY
```

## Path Note

This project lives in iCloud (`~/Library/Mobile Documents/com~apple~CloudDocs/...`). The space in `Mobile Documents` can cause shell path issues. Always use quoted absolute paths in scripts.
