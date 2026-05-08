# Current State

## Implemented
- Fullstack starter: React/Vite/TypeScript/Tailwind/shadcn frontend.
- Backend: FastAPI, async SQLAlchemy 2.0, SQLite, Alembic.
- Docker Compose runs backend on `8000` and frontend on `5173`.
- Auth: email/password register/login, JWT bearer token, `/auth/me`.
- Frontend auth: token persisted in `localStorage`, guarded dashboard route.
- Landing page: animated shader hero with Register/Login CTAs and inline auth form.
- Dashboard: authenticated main page with backend health status cards.
- Database models: `Team`, `User`.

## Broken / Incomplete
- Host `front/npm run typecheck` cannot find `tsc`; Docker typecheck works.
- No automated backend test suite yet.
- No password reset, email verification, refresh tokens, roles, or rate limiting.

## Current Sprint Goal
- Stabilize the AI-first hackathon starter and keep memory synchronized after every code change.

## Next 3 Tasks
- Add minimal backend auth endpoint tests.
- Add frontend smoke coverage for landing/auth/dashboard routing.
- Replace development `JWT_SECRET_KEY` before any shared deployment.

## Active Endpoints
- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

## Active Frontend Pages
- `/` public landing page with Register/Login actions.
- `/dashboard` protected authenticated dashboard.
