# React Page

Use this workflow to add a new frontend page.

1. Create the page in `front/src/pages`.
2. Add the route in `front/src/App.tsx`.
3. Put API calls in `front/src/api` and query hooks in `front/src/hooks`.
4. Reuse shadcn-style UI components from `front/src/components/ui`.
5. Keep loading, empty, success, and error states visible.
6. Run `docker compose run --rm frontend npm run typecheck`.

Prefer dense, useful screens over marketing layouts. Keep text concise and action-oriented.
