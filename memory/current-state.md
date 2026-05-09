# Current State

## Implemented
- Fullstack starter: React/Vite/TypeScript/Tailwind/shadcn frontend.
- Backend: FastAPI, async SQLAlchemy 2.0, SQLite, Alembic.
- Docker Compose runs backend on `8000` and frontend on `5173`.
- Auth: email/password register/login, JWT bearer token, `/auth/me`.
- Frontend auth for INIBSA MVP: mocked `Delegado de Ventas` session persisted in `localStorage` under key `inibsa.salesDelegateSession`, guarded dashboard route, no backend auth call.
- Login page: enterprise SaaS mock login for commercial delegates at `/`. Uses `logo.png` in card header and `icon.png` in the challenge badge.
- Dashboard: INIBSA sales alerts MVP at `/dashboard` with mock alert data (dental clinic clients), table-first workflow with pending/attended tab toggle (pending shown first), attended questionnaire modal, and AI insight panel connected to Gemini API via `POST /ai/chat` (real LLM, no mock responses).
- LLM module: `back/app/llm/` with `prompt.yaml` (INIBSA system prompt with alert context injection, guardrails, multilingual), `schemas.py`, `service.py` (Gemini 1.5 Flash, async via `asyncio.to_thread`), `router.py` (`POST /ai/chat`). Requires `GEMINI_API_KEY` env var.
- `AIInsightPanel`: replaced `createMockResponse()` with real backend call; removed opening greeting; added loading spinner; errors shown inline in chat.
- Database models: `Team`, `User`.
- Fixed missing `front/src/lib/utils.ts` utility file for shadcn/ui components.
- Implemented i18n (Catalan default, Spanish toggle) using React Context. Both locales fully translated — no English terms remain in either locale file.
- Enhanced Dashboard layout to fix horizontal scrolling on desktop (widened container to `max-w-[1440px]`).
- Added subtle UI animations using Framer Motion (fade-ins, staggered lists, smooth row expansion).
- Branding: INIBSA full logo (`front/src/assets/logo.png`) used in AppLayout header and Login card. Icon only (`front/src/assets/icon.png`) used as favicon (`front/public/icon.png`) and in login badge. Page title is "INIBSA".
- "Alertas" nav button removed. App subtitle hidden from AppLayout header.
- "Alertes INIBSA" eyebrow label removed from dashboard page header.
- ChurnType is open-ended (`"total" | string`); mock data uses "total", "Producto 1", "Producto 2".
- Percentage columns (churn risk, purchase propensity) display as color-coded pill badges (red/amber/green) instead of progress bars.
- "Marcar atesa" button icon changed from PhoneCall to ClipboardCheck. Both action buttons are `w-full` for consistent layout across languages.
- Docker named volume `frontend_node_modules` must be removed and recreated when new npm packages are added (framer-motion issue resolved this way).

## Broken / Incomplete
- Host `front/npm run typecheck` cannot find `tsc` if not in path; Docker typecheck or local `npm run typecheck` (if tsc installed) works.
- No automated backend test suite yet.
- Sales alerts are frontend mock data only; no alert API or persistence exists yet.
- No password reset, email verification, refresh tokens, roles, or rate limiting.

## Current Sprint Goal
- Deliver a polished frontend-only INIBSA sales alerts MVP while keeping backend and infra unchanged.

## Next Tasks
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
- `/dashboard` protected sales alerts dashboard with mocked dental clinic alerts.
