# Known Issues

## Bugs
- Host `npm run typecheck` in `front/` fails because `tsc` is unavailable on the host install.

## Incomplete Features
- No automated backend tests.
- No frontend route/auth smoke tests.
- Sales alert data, attended status, follow-up records, and AI responses are mock-only and reset on page refresh.
- No password reset or email verification.
- No refresh token or role/permission model.

## Technical Debt
- JWT secret defaults to development value unless overridden in `.env`.
- Current INSIBA frontend auth is mocked in `localStorage`; replace with backend auth before production use.
