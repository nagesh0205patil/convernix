# Convernix frontend integration

The public homepage uses the Convernix screens, product demos, font, background, and purple theme. Sign In opens an accessible dialog using the existing frontend email/password authentication. Successful authentication opens the existing business selector and dashboard. Invitation links continue to use the existing activation flow.

Backend source and API contracts are unchanged. Google and Microsoft options are shown as unavailable because the existing backend exposes provider configuration flags but does not implement OAuth login/callback endpoints.

## Run locally

From `Frontend`, run `npm install` and `npm run dev`. Open http://127.0.0.1:5173/.

Vite proxies `/api` and `/media` to http://127.0.0.1:9090. A running backend is required for real authentication and workspace data. The existing root Docker Compose configuration can start the backend, PostgreSQL, Redis, and workers when Docker is installed and running. Keep `VITE_API_URL=/api` for the local proxy.

## Validate

- `npm run build`
- `npm run lint`
- `npm run test:e2e` (requires installed Google Chrome; starts Vite if needed)

Browser tests simulate API responses to verify desktop/mobile sign-in, error handling, authentication payloads, token handling, the business selector, and sign-out. They do not validate a live database or identity provider.

The original Convernix source folder is retained. Its website modules are in `src/convernix`; CSS scopes keep the marketing page and existing workspace styles isolated.
