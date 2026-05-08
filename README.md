# InterHack 2026

Lightweight fullstack hackathon starter with React, Vite, FastAPI, async SQLAlchemy, SQLite, Alembic, and Docker Compose.

## Quick Start

```powershell
./start.ps1
```

The script creates `.env` from `.env.example`, initializes `back/app.db` with Alembic when needed, and starts the Docker stack.

## URLs

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- FastAPI docs: http://localhost:8000/docs

## Stack

- Frontend: React, Vite, TypeScript, TailwindCSS, shadcn/ui, React Router, TanStack Query
- Backend: FastAPI, SQLAlchemy 2.0 async, SQLite, Alembic, Pydantic
- Infra: Docker and Docker Compose

## Useful Commands

```powershell
docker compose up --build
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic revision --autogenerate -m "change name"
docker compose run --rm frontend npm run typecheck
```

## Layout

- `front/`: Vite React app
- `back/`: FastAPI app and Alembic migrations
- `.github/`: assistant instructions, skills, and reusable prompts
- `scripts/`: small project automation scripts
