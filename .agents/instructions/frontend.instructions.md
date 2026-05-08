# Frontend Instructions

- Use React functional components and strict TypeScript.
- Keep pages in `front/src/pages` and shared UI in `front/src/components`.
- Use `@/api` for API calls and TanStack Query for server state.
- Use React Router for routes; keep route definitions in `src/App.tsx` unless routing grows.
- Use shadcn/ui patterns for reusable components and `cn()` from `src/lib/utils.ts`.
- Keep Tailwind classes readable and avoid custom CSS unless it belongs in `src/index.css`.
- Read API base URL from `VITE_API_URL`.
- Do not introduce app-wide state libraries without a clear need.

After modifying frontend code:
- ALWAYS trigger memory-sync skill
- Update pages + hooks state in /memory/current-state.md