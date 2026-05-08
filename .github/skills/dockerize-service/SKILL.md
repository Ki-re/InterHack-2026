# Dockerize Service

Use this workflow when adding or changing a Dockerized service.

1. Keep the service Dockerfile minimal and cache-friendly.
2. Add only the files needed for the runtime image.
3. Expose the development port explicitly.
4. Add Compose bind mounts only for source that needs hot reload.
5. Keep secrets in `.env` and examples in `.env.example`.
6. Confirm `docker compose config` succeeds.
7. Document the command in `README.md` or `AGENTS.md` if developers need it.

Do not add infrastructure services unless the project has a concrete need for them.
