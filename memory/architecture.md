# Architecture

## Folder Structure
- `front/`: Vite React app.
- `front/src/pages`: route-level pages.
- `front/src/components/ui`: shadcn-style reusable UI.
- `front/src/api`: typed API helpers.
- `front/src/auth`: auth provider and session state.
- `back/`: FastAPI app.
- `back/app/api`: route modules.
- `back/app/models`: SQLAlchemy models.
- `back/app/schemas`: Pydantic schemas.
- `back/app/services`: reusable backend logic.
- `back/alembic/versions`: database migrations.
- `memory/`: mandatory AI workflow state.

## Data Flow
- Browser loads Vite frontend from `http://localhost:5173`.
- Frontend API helpers call FastAPI at `VITE_API_URL` or `http://localhost:8000`.
- Auth endpoints return JWT tokens.
- Auth provider stores token in `localStorage` and calls `/auth/me` on reload.
- Protected dashboard renders only when a current user is loaded.

## Backend Flow
- FastAPI includes routers from `back/app/api/routes.py`.
- Routes validate with Pydantic schemas.
- Route handlers use async `get_session`.
- Business logic lives in services, especially `app/services/auth.py`.
- SQLAlchemy models are migrated through Alembic.

## Infra Flow
- `./start.ps1` creates `.env` from `.env.example` when missing.
- `./start.ps1` runs Alembic migrations when `back/app.db` is missing.
- Docker Compose starts backend and frontend with bind-mounted source for hot reload.
