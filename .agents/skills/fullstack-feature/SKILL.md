---
name: fullstack-feature
description: Use when adding a feature that touches both React and FastAPI — covers API contract, backend, migration, frontend, and validation
---

# Fullstack Feature

Use this workflow when adding a feature that touches both React and FastAPI.

1. Define the user-visible behavior and the API contract first.
2. Add or update backend models, schemas, services, and routes.
3. Create an Alembic migration for schema changes.
4. Add a typed frontend API function under `front/src/api`.
5. Use TanStack Query for reads and mutations.
6. Compose the UI in a page or shared component.
7. Validate with Docker Compose, backend health, and frontend typecheck.

Keep the feature thin and shippable. Defer generic abstractions until two real call sites exist.
