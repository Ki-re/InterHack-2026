# Copilot Instructions

Build for a fast-moving hackathon team. Favor simple, working, production-aware changes over broad abstractions.

## Project Shape

- `front/` is a Vite React TypeScript app using TailwindCSS, shadcn/ui conventions, React Router, and TanStack Query.
- `back/` is a FastAPI service using async SQLAlchemy 2.0, SQLite, Alembic, and Pydantic.
- Docker Compose is the default local workflow.

## Rules

- Keep backend database access async.
- Add Alembic migrations for database schema changes.
- Keep React components functional and typed.
- Use `@/` imports in the frontend.
- Keep Docker hot reload working on Windows bind mounts.
- Do not commit `.env`, `back/app.db`, `node_modules`, caches, or build output.

## Preferred Commands

```powershell
./start.ps1
docker compose up --build
docker compose run --rm backend alembic upgrade head
docker compose run --rm frontend npm run typecheck
```
