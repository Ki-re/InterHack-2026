# Instructions from .github/copilot-instructions.md

<!-- agentsync:agent-config-layout:start -->
## Agent config layout

`.agents/` is the canonical source for shared instructions, skills, and commands in this project.

- Instructions: `.agents/AGENTS.md` is the canonical instructions file, and these `symlink` targets reflect it directly in `CLAUDE.md`, `.github/copilot-instructions.md`, `GEMINI.md`, `OPENCODE.md`, `AGENTS.md`.

- Skills: `.agents/skills/` is the canonical skills directory.
  - `.claude/skills` reflects `.agents/skills/` directly because this target uses `symlink`.
  - `.codex/skills` reflects `.agents/skills/` directly because this target uses `symlink`.
  - `.gemini/skills` reflects `.agents/skills/` directly because this target uses `symlink`.
  - `.opencode/skills` reflects `.agents/skills/` directly because this target uses `symlink`.

- Commands: `.agents/commands/` is the canonical commands directory, `agentsync apply` populates command entries into `.claude/commands`, `.gemini/commands`, `.opencode/command`, and `agentsync status` validates those destinations as managed container directories rather than requiring the destination path itself to be a symlink.

<!-- agentsync:agent-config-layout:end -->

# AGENTS.md

Every task has 3 phases:

1. PLAN
2. IMPLEMENT
3. MEMORY SYNC (mandatory)

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

## MEMORY SYSTEM (MANDATORY)

After ANY code change, the agent MUST:

- Run memory-sync skill implicitly
- Update /memory folder before finishing the task
- Treat memory update as part of the task definition, not optional work

No task is complete until memory-sync has been executed.

## After every task completion:

- You MUST update /memory/current-state.md
- If backend changed → update /memory/api-contracts.md
- If architecture changed → update /memory/decisions.md
- If something is broken → update /memory/known-issues.md

Failure to update memory is considered an incomplete task.

---

# Instructions from AGENTS.md

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
- After every implementation task, update the `/memory` files before finishing.

## Architecture Rules

- Keep SQLite as the default database unless the project explicitly changes persistence.
- Keep API routes thin; move reusable business logic into `back/app/services`.
- Keep React pages focused on composition; move shared UI into `front/src/components`.
- Avoid enterprise patterns, global state libraries, and background infrastructure until they are needed.

## Memory System

- `/memory` is mandatory runtime workflow state, not optional documentation.
- Always read `/memory/current-state.md` before planning non-trivial work.
- Update `/memory/current-state.md` after any code, config, schema, or page change.
- Update `/memory/api-contracts.md` when backend endpoints or schemas change.
- Update `/memory/decisions.md` when stack, architecture, persistence, auth, or infra decisions change.
- Update `/memory/architecture.md` when folder structure, data flow, or service boundaries change.
- Update `/memory/known-issues.md` when bugs, broken workflows, or incomplete features are discovered.
- Keep memory files short, factual, and current.
