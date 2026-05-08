---
name: fastapi-crud
description: Use to add a small CRUD resource to the FastAPI backend — model, schemas, service, routes, router registration, and Alembic migration
---

# FastAPI CRUD

Use this workflow to add a small CRUD resource.

1. Add a SQLAlchemy model in `back/app/models`.
2. Add Pydantic create/read/update schemas in `back/app/schemas`.
3. Add service functions that accept `AsyncSession`.
4. Add FastAPI routes with explicit response models.
5. Register the router in `back/app/api/routes.py`.
6. Generate an Alembic migration and check it matches the model.
7. Verify with `docker compose run --rm backend alembic upgrade head`.

Use clear 404 responses, avoid hidden commits inside services, and keep transactions easy to follow.
