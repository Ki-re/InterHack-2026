# Known Issues

## Bugs
- Host `npm run typecheck` in `front/` fails because `tsc` is unavailable on the host install.

## Incomplete Features
- No automated backend tests.
- No frontend route/auth smoke tests.
- No password reset or email verification.
- No refresh token or role/permission model.

## Technical Debt
- JWT secret defaults to development value unless overridden in `.env`.
- Auth tokens are stored in `localStorage`; acceptable for starter speed, weaker than HTTP-only cookies.
- Shader landing page depends on WebGL2; fallback is a dark static background.
