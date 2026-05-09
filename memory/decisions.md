# Decisions

## Stack
- Frontend uses React, Vite, TypeScript, Tailwind CSS, shadcn/ui, React Router, TanStack Query, and Framer Motion for subtle animations.
- Backend uses FastAPI, Pydantic, async SQLAlchemy 2.0, SQLite, Alembic.
- Infra uses Docker Compose with hot reload for frontend and backend.

## Architecture
- SQLite remains the default local database.
- Backend endpoints stay thin; reusable logic belongs in `back/app/services`.
- Backend database access uses `AsyncSession`; sync SQLAlchemy sessions are not used.
- Frontend pages live in `front/src/pages`; shared UI lives in `front/src/components`.
- shadcn UI components live in `front/src/components/ui` via the `@/components/ui` alias.
- i18n is implemented via a lightweight React Context (`LanguageContext`) and JSON locale files in `front/src/locales`.

## Auth
- Email/password auth uses JWT bearer tokens.
- Frontend stores the access token in `localStorage`.
- Password hashes use stdlib PBKDF2-HMAC SHA-256.
- No OAuth, session cookies, refresh tokens, or roles in the starter auth flow.
- INSIBA frontend MVP temporarily uses mocked localStorage auth for `Delegado de Ventas` and does not call backend auth endpoints.

## INSIBA MVP
- Sales alerts are mocked in the frontend until backend alert endpoints are defined.
- React local state is sufficient for attended status, follow-up questionnaire data, and AI insight panel messages.
- The UI direction is clean enterprise SaaS: neutral surfaces, dense table-first workflow, and restrained blue/green/red status accents.

## Tradeoffs
- Prefer small starter patterns over enterprise abstractions.
- Avoid global state libraries until needed.
- Use Docker Compose commands as the reliable verification path.
