# YTNewsletter

AI-assisted YouTube digest. A signed-in user follows channels, the backend pulls videos and transcripts, an LLM writes summaries, and the app can export a newsletter or hand it to Beehiiv.

This repository is a **partial snapshot**: API route modules and a few Next.js pages. It does not contain the FastAPI app entrypoint, models, services, integrations, `package.json`, or the frontend API client. You can read the shape of the product here. You cannot boot a working demo from this tree alone.

## What is in the tree

| Path | What it is |
|------|------------|
| `backend/app/api/v1/` | FastAPI routers for auth, users, channels, videos, subscriptions, newsletters, admin |
| `frontend/src/app/` | Next.js App Router pages: login, dashboard, channels, feed, newsletters, settings |
| `frontend/src/components/` | Navigation plus Button, Card, Input |
| `.env.example` | Placeholder env vars only |

Routes import modules that are **not** in this snapshot (`app.main`, `app.config`, `app.services.*`, `app.models.*`, `app.integrations.*`, `@/lib/api`, `@/contexts/AuthContext`).

## Run (when the missing app code is present)

Do not put real keys in git. Copy the example file and fill it locally:

```bash
cp .env.example .env
```

`.env` is gitignored. `.env.example` is the only env file that belongs in the repo, and every value in it is a placeholder (`REDACTED`, `example.com`, localhost).

**Frontend** (from `frontend/`, after a real `package.json` exists):

```bash
npm install
npm run dev    # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` (default in the login page is `http://localhost:8000/api/v1`).

**Backend** (from `backend/`, after the app package and a virtualenv exist):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000
```

### Env vars

| Variable | Used for |
|----------|----------|
| `NEXT_PUBLIC_API_URL` | Browser calls to the API |
| `FRONTEND_URL` | Where auth sends the browser after Google (`settings.frontend_url`) |
| `GOOGLE_CLIENT_ID` | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `YOUTUBE_API_KEY` | Channel search, video metadata |
| `OPENAI_API_KEY` | Summaries |
| `BEEHIIV_API_KEY` | Publish |
| `SUPPORT_EMAIL` | Docs/contact placeholder only (`support@example.com`) |

Supply those yourself. Nothing in git is a live credential.

## Demo vs production

**Safe to show as code:** yes. A full-tree scan of the working copy and of every historical file blob found no API keys, tokens, passwords, private keys, phone numbers, customer records, or real email addresses in file contents. No `.env` was ever committed.

**Not a live demo:** the process cannot start. Even with keys, the imported app layers are missing.

**Not production / not monetize-ready.** These are in the scaffold today and are not fixed in this pass:

- Google callback puts access and refresh tokens in the redirect query string.
- `redirect_url` / OAuth `state` is used as the post-login redirect with no allowlist (open redirect).
- `POST /newsletters/webhook/beehiiv` accepts a JSON body with no signature check.
- `/admin/*` only requires a logged-in user, not an admin role.
- Settings shows a $9/mo premium plan in the UI. There is no billing integration in this tree.
- Newsletter publish calls Beehiiv with whatever `BEEHIIV_API_KEY` the server has. There is no per-user key isolation here.

Git history on `main` still has a personal email in commit author/committer metadata (not in file contents). This branch does not rewrite that history. See the pull request for the rotation note.
