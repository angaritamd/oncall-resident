# app

Mobile-first Next.js PWA for the on-call resident (dark theme, ES/EN).

```sh
npm ci
CORE_URL=http://127.0.0.1:18000 npm run dev
BASE_URL=http://<host>:13000 npx playwright test   # e2e with Brave, mobile 390 px and desktop
```

`/api/*` is a same-origin proxy to the core (allowlisted routes only).
