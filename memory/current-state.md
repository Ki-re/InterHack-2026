# Current State

## Implemented
- Fullstack starter: React/Vite/TypeScript/Tailwind/shadcn frontend.
- Backend: FastAPI, async SQLAlchemy 2.0, SQLite, Alembic.
- Docker Compose runs backend on `8000` and frontend on `5173`.
- Auth: email/password register/login, JWT bearer token, `/auth/me`.
- Frontend auth for INIBSA MVP: mocked `Delegado de Ventas` session persisted in `localStorage`, guarded dashboard route, no backend auth call.
- Login page: enterprise SaaS mock login for commercial delegates at `/`.
- Dashboard: INIBSA sales alerts MVP at `/dashboard` with mock alert data (dental clinic clients), table-first workflow, attended questionnaire modal, and AI insight panel with inviting conversational prompts.
- Database models: `Team`, `User`.
- Fixed missing `front/src/lib/utils.ts` utility file for shadcn/ui components.
- Implemented i18n (Catalan default, Spanish toggle) using React Context.
- Enhanced Dashboard layout to fix horizontal scrolling on desktop (widened container to `max-w-[1440px]`).
- Added subtle UI animations using Framer Motion (fade-ins, staggered lists, smooth row expansion).
- Branding: INIBSA logo (`front/src/assets/logo.png`) used in AppLayout header and Login card. "Alertas" nav button and app subtitle hidden. ChurnType is now open-ended ("total" or any product string like "Producto 1").

## Broken / Incomplete
- Host `front/npm run typecheck` cannot find `tsc` if not in path; Docker typecheck or local `npm run typecheck` (if tsc installed) works.
- No automated backend test suite yet.
- Sales alerts are frontend mock data only; no alert API or persistence exists yet.
- No password reset, email verification, refresh tokens, roles, or rate limiting.

## Current Sprint Goal
- Deliver a polished frontend-only INSIBA sales alerts MVP while keeping backend and infra unchanged.

## Next 3 Tasks
- Add frontend smoke coverage for login, dashboard routing, attended flow, and AI panel.
- Define backend alert API contracts when persistence/integration starts.
- Replace development `JWT_SECRET_KEY` before any shared deployment if backend auth is reintroduced in the frontend flow.

## Active Endpoints
- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

## Active Frontend Pages
- `/` public mock login page for `Delegado de Ventas`.
- `/dashboard` protected sales alerts dashboard with mocked alerts.
