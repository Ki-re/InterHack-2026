# AGENTS.md

## Stack

- Frontend: React + Vite + TS + Tailwind + shadcn/ui
- Backend: FastAPI
- Infra: Docker Compose

## Commands

### Frontend
run: cd frontend && npm run dev
run: cd frontend && npm run build

### Backend
run: cd backend && uvicorn app.main:app --reload

### Full stack
run: docker compose up --build

## Rules

- Use TypeScript strict mode
- Use functional React components only
- Prefer server-side validation in FastAPI
- Use pydantic models for all API contracts
- Never invent API routes
- Keep components under 250 LOC
- Mobile-first responsive UI
- Use shadcn/ui before custom components
- Use async SQLAlchemy patterns

## UI style

- Minimal dark dashboard
- Rounded-xl cards
- Dense layouts for hackathon speed
- Prioritize usability over animations

## Workflow

When implementing features:
1. Create backend schema
2. Create endpoint
3. Create typed frontend API client
4. Create UI
5. Add loading and error states
6. Verify Docker build works