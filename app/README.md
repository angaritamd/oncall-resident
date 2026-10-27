# app

Mobile-first Next.js PWA for the on-call resident (dark theme, ES/EN).

```sh
npm ci
npm run test:unit                                   # auth rules (node --test)
ALLOWED_USERS=tester@example.com CORE_URL=http://127.0.0.1:18000 npm run dev
# e2e with Brave (mobile 390 px and desktop)
E2E_LOGIN=tester@example.com BASE_URL=http://127.0.0.1:3000 npx playwright test             # local server
E2E_EXPECT_LOGIN=<your tailnet login> BASE_URL=https://<host>.ts.net npx playwright test   # via tailscale serve
```

`/api/*` is a same-origin proxy to the core (allowlisted routes only).

**Access control** (`proxy.ts`, `lib/auth.ts`): every request needs a `Tailscale-User-Login` header, which `tailscale serve` sets. The response is 401 when the header is missing, and 403 when the login is not in `ALLOWED_USERS` (comma-separated, case-insensitive) or the list is empty, so the check fails closed. The app listens only on `127.0.0.1`, so only Serve can reach it.
