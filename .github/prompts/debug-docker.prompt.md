# Debug Docker Prompt

Debug the Docker workflow for this repository.

Start with `docker compose config`, then isolate the failing service. Inspect build logs, runtime logs, bind mounts, ports, environment variables, and whether migrations have run. Keep ports `5173` and `8000`. Preserve hot reload and the frontend `node_modules` volume.

Return the root cause, exact fix, and verification command.
