# Backend Instructions

- Use FastAPI async endpoints.
- Use SQLAlchemy 2.0 typed models with `Mapped` and `mapped_column`.
- Use `AsyncSession` from `back/app/db.py`; do not create sync engines or sessions.
- Keep API modules in `back/app/api`, models in `back/app/models`, schemas in `back/app/schemas`, and reusable logic in `back/app/services`.
- Add or update Alembic migrations for schema changes.
- Keep SQLite as the default local database with `sqlite+aiosqlite:///./app.db`.
- Validate request and response data with Pydantic models.
- Keep route handlers thin and explicit.

After modifying backend code:
- ALWAYS trigger memory-sync skill
- Update API contracts in /memory/api-contracts.md