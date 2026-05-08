# Patterns

## Create Backend Endpoints
- Add schema in `back/app/schemas`.
- Add reusable logic in `back/app/services`.
- Add async route in `back/app/api`.
- Register router in `back/app/api/routes.py`.
- Use `AsyncSession` from `back/app/db.py`.
- Update `memory/current-state.md` and `memory/api-contracts.md`.

## Create Database Models
- Add model in `back/app/models`.
- Export model in `back/app/models/__init__.py`.
- Import model in `back/alembic/env.py`.
- Add Alembic migration in `back/alembic/versions`.
- Update `memory/current-state.md`, `memory/architecture.md`, and `memory/decisions.md` if needed.

## Create Frontend Pages
- Add page in `front/src/pages`.
- Wire route in `front/src/App.tsx`.
- Keep shared UI in `front/src/components`.
- Keep API calls in `front/src/api`.
- Add loading and error states.
- Update `memory/current-state.md`.

## Create Fullstack Features
- Define API schema and contract first.
- Implement backend route and service.
- Add typed frontend API helper.
- Compose UI from page + shared components.
- Verify with Docker typecheck/build.
- Update memory before finishing.

## Memory Update Loop
- Always update `memory/current-state.md` after implementation.
- Update `memory/api-contracts.md` when APIs change.
- Update `memory/decisions.md` when architectural choices change.
- Update `memory/known-issues.md` when something is broken or incomplete.
- Keep memory concise and factual.
