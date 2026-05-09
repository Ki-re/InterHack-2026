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
- INIBSA frontend MVP temporarily uses mocked localStorage auth for `Delegado de Ventas` (key: `inibsa.salesDelegateSession`) and does not call backend auth endpoints.

## INIBSA MVP
- Sales alerts are mocked in the frontend until backend alert endpoints are defined.
- React local state is sufficient for attended status, follow-up questionnaire data, and AI insight panel messages.
- The UI direction is clean enterprise SaaS: neutral surfaces, dense table-first workflow, and restrained blue/green/red status accents.
- Mock clients are dental clinics with dental supply context.
- ChurnType is open-ended (`"total" | string`) — "total" is translated via i18n, any other string (e.g. "Producto 1") is displayed as-is.
- Percentage columns use color-coded pill badges (not progress bars): risk uses red/amber/green, opportunity uses the inverse.

## Branding
- Brand name is INIBSA (not INSIBA).
- `front/src/assets/logo.png`: full logo (icon + name). Used in AppLayout header and Login card.
- `front/src/assets/icon.png`: icon only. Used as favicon (`front/public/icon.png`), page title "INIBSA", and small badge contexts in Login.
- No nav links or subtitles shown in the AppLayout header — logo stands alone.

## Docker
- Frontend uses a named volume (`frontend_node_modules`) to persist node_modules for hot-reload performance.
- When new npm packages are added to `package.json`, the volume must be removed (`docker volume rm interhack-2026_frontend_node_modules`) and the container restarted so it repopulates from the rebuilt image.

## Tradeoffs
- Prefer small starter patterns over enterprise abstractions.
- Avoid global state libraries until needed.
- Use Docker Compose commands as the reliable verification path.
