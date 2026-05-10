# Architecture

## Folder Structure
- `front/`: Vite React app.
- `front/src/pages`: route-level pages.
- `front/src/components`: sales alert table, modal, AI panel, regional dashboard components, and layout components.
- `front/src/components/ui`: shadcn-style reusable UI.
- `front/src/assets`: static brand assets — `logo.png` (full logo), `icon.png` (icon only).
- `front/src/data`: frontend mock datasets for MVP screens.
- `front/src/types`: shared frontend TypeScript domain types.
- `front/src/api`: typed API helpers, including AI chat and regional dashboard reads.
- `front/src/auth`: auth provider and session state.
- `front/src/locales`: i18n JSON files (`ca.json` default, `es.json` toggle). Both fully translated with no English terms.
- `front/public/`: static public assets — `icon.png` used as favicon.
- `back/`: FastAPI app.
- `back/app/api`: route modules.
- `back/app/models`: SQLAlchemy models.
- `back/app/schemas`: Pydantic schemas.
- `back/app/services`: reusable backend logic.
- `back/alembic/versions`: database migrations.
- `memory/`: mandatory AI workflow state.

## Data Flow
- Browser loads Vite frontend from `http://localhost:5173`.
- INIBSA sales alerts MVP uses mock frontend data from `front/src/data/mock-alerts.ts` (dental clinic clients).
- Mock auth provider stores a role-based session in `localStorage` (key: `inibsa.salesDelegateSession`); protected dashboards render when that session exists.
- The selected frontend role (`sales_delegate` or `regional_manager`) routes users to the matching dashboard.
- Alert attended state is held in React state inside the dashboard during the session.
- Regional manager dashboard calls `GET /regional-dashboard` through TanStack Query and renders seeded backend hierarchy/KPI data.
- Existing frontend API helpers and backend auth endpoints remain in the codebase for future integration, but the MVP alert flow does not call them.

## Backend Flow
- FastAPI includes routers from `back/app/api/routes.py`.
- Routes validate with Pydantic schemas.
- Route handlers use async `get_session`.
- Business logic lives in services, including `app/services/auth.py` and `app/services/regional_dashboard.py`.
- SQLAlchemy models are migrated through Alembic.
- Regional hierarchy tables are seeded by migration `0003_create_regional_dashboard.py`.

## Infra Flow
- `./start.ps1` creates `.env` from `.env.example` when missing.
- `./start.ps1` runs Alembic migrations when `back/app.db` is missing.
- Docker Compose starts backend and frontend with bind-mounted source for hot reload.
- Frontend node_modules are persisted in a named Docker volume (`interhack-2026_frontend_node_modules`). Remove and recreate this volume after adding new npm packages.
