// Same-origin proxy to the core so the phone only talks to the app's port.
import { LOGIN_HEADER, parseAllowed } from "@/lib/auth";

const CORE_URL = () => process.env.CORE_URL ?? "http://127.0.0.1:18000";
const ALLOWED = new Set(["health", "worklist", "cases", "activity", "chat", "resident", "reports", "spend", "demo", "station"]);
const SEGMENT = /^[A-Za-z0-9_-]{1,64}$/;
const HEADERS = { "cache-control": "no-store, private", "x-content-type-options": "nosniff" };

async function forward(req: Request, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  if (!ALLOWED.has(path[0]) || path.length > 5 || !path.every((s) => SEGMENT.test(s))) {
    return Response.json({ detail: "not found" }, { status: 404, headers: HEADERS });
  }
  // CSRF: the tailnet identity is ambient (Serve adds it to every request), so every API call (GETs included:
  // /api/resident wakes a GPU) must come from this app's own pages, never from another site the user visits.
  // Page navigations do not go through this route.
  {
    const site = req.headers.get("sec-fetch-site");
    const origin = req.headers.get("origin");
    const self = new URL(req.url).origin;
    const forwarded = req.headers.get("x-forwarded-host");
    const selfForwarded = forwarded ? `https://${forwarded}` : null;
    const sameOrigin = site ? site === "same-origin" : origin !== null && (origin === self || origin === selfForwarded);
    if (!sameOrigin) return Response.json({ detail: "forbidden" }, { status: 403, headers: HEADERS });
  }
  const base = new URL(CORE_URL());
  const target = new URL(`/api/${path.join("/")}`, base);
  target.search = new URL(req.url).search;
  // identity comes only from Tailscale (checked in proxy.ts); client-sent x-resident-* headers are never forwarded
  const login = (req.headers.get(LOGIN_HEADER) ?? "").trim().toLowerCase();
  const admin = parseAllowed(process.env.ADMIN_USERS).has(login);
  // the exact model, tokens and spend are only for admins (ADMIN_USERS); everyone else sees the mode
  if (!admin) target.searchParams.delete("detail");
  if (!admin && (path[0] === "spend" || path[0] === "demo")) {
    return Response.json({ detail: "not found" }, { status: 404, headers: HEADERS });
  }
  // the station's event stream may stay open indefinitely, but the core must start answering within 10 s
  const isStream = path[0] === "station" && path[1] === "events";
  const firstByte = new AbortController();
  const firstByteTimer = isStream ? setTimeout(() => firstByte.abort(), 10_000) : undefined;
  try {
    const res = await fetch(target, {
      method: req.method,
      headers: {
        "content-type": req.headers.get("content-type") ?? "application/json",
        // the core records who drafted/edited and requires it to sign
        "x-resident-login": login,
        ...(admin ? { "x-resident-admin": "1" } : {}),
      },
      body: req.method === "GET" ? undefined : await req.text(),
      cache: "no-store",
      redirect: "error",
      // a chat answer may wait for a cold model (threshold) and then a fallback provider
      // chat may wait for a cold model; report actions re-run QC with the model; the station's event stream
      // stays open (it ends when the browser closes it)
      signal: isStream
        ? AbortSignal.any([req.signal, firstByte.signal])
        : AbortSignal.timeout(path[0] === "chat" ? 120_000 : path[0] === "reports" ? 60_000 : 10_000),
    });
    clearTimeout(firstByteTimer); // headers arrived: the stream itself is not time-limited
    return new Response(res.body, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json", ...HEADERS },
    });
  } catch {
    clearTimeout(firstByteTimer);
    return Response.json({ detail: "core unreachable" }, { status: 502, headers: HEADERS });
  }
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
