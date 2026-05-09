# Known Issues

## Bugs
- Host `npm run typecheck` in `front/` fails because `tsc` is unavailable on the host install. Use `docker compose run --rm frontend npm run typecheck` instead.

## Incomplete Features
- No automated backend tests.
- No frontend route/auth smoke tests.
- Sales alert data, attended status, follow-up records, and AI responses are mock-only and reset on page refresh.
- No password reset or email verification.
- No refresh token or role/permission model.

## Technical Debt
- JWT secret defaults to development value unless overridden in `.env`.
- Current INIBSA frontend auth is mocked in `localStorage`; replace with backend auth before production use.
- When adding new npm packages, the Docker named volume `interhack-2026_frontend_node_modules` must be manually removed and the container restarted, otherwise the stale volume shadows the new package.
