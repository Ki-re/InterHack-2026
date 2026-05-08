# AGENTS

## Stack

- Frontend: React, Vite, TypeScript, TailwindCSS, shadcn/ui, React Router, TanStack Query.
- Backend: FastAPI, async SQLAlchemy 2.0, SQLite, Alembic, Pydantic.
- Infra: Docker Compose with hot reload for both services.

## Conventions

- Keep changes small, modular, and easy to review.
- Prefer existing folders: `front/src/pages`, `front/src/components`, `back/app/api`, `back/app/models`, `back/app/schemas`, `back/app/services`.
- Backend code is async by default. Do not introduce sync SQLAlchemy sessions.
- Frontend code uses functional components and strict TypeScript.
- Use environment variables from `.env.example`; do not commit `.env` or database files.

## Workflow

- Start locally with `./start.ps1`.
- Run migrations with `docker compose run --rm backend alembic upgrade head`.
- Create migrations with `docker compose run --rm backend alembic revision --autogenerate -m "message"`.
- Typecheck frontend with `docker compose run --rm frontend npm run typecheck`.

## Architecture Rules

- Keep SQLite as the default database unless the project explicitly changes persistence.
- Keep API routes thin; move reusable business logic into `back/app/services`.
- Keep React pages focused on composition; move shared UI into `front/src/components`.
- Avoid enterprise patterns, global state libraries, and background infrastructure until they are needed.
