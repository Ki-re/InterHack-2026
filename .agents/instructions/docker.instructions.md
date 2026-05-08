# Docker Instructions

- Use Docker Compose as the default development entrypoint.
- Keep frontend port `5173` and backend port `8000`.
- Preserve bind mounts for hot reload.
- Keep frontend `node_modules` in the named Docker volume, not the host bind mount.
- Run database migrations through the backend container.
- Do not bake `.env`, SQLite databases, caches, or build output into images.
- Keep service commands explicit and readable in `docker-compose.yml`.
