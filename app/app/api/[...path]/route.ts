// Same-origin proxy to the core so the phone only talks to the app's port.
const CORE_URL = () => process.env.CORE_URL ?? "http://127.0.0.1:18000";
const ALLOWED = new Set(["health", "worklist", "cases", "activity", "chat"]);
const SEGMENT = /^[A-Za-z0-9_-]{1,64}$/;
const HEADERS = { "cache-control": "no-store, private", "x-content-type-options": "nosniff" };

async function forward(req: Request, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  if (!ALLOWED.has(path[0]) || path.length > 2 || !path.every((s) => SEGMENT.test(s))) {
    return Response.json({ detail: "not found" }, { status: 404, headers: HEADERS });
  }
  const base = new URL(CORE_URL());
  const target = new URL(`/api/${path.join("/")}`, base);
  target.search = new URL(req.url).search;
  try {
    const res = await fetch(target, {
      method: req.method,
      headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
      body: req.method === "GET" ? undefined : await req.text(),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
    });
    return new Response(res.body, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json", ...HEADERS },
    });
  } catch {
    return Response.json({ detail: "core unreachable" }, { status: 502, headers: HEADERS });
  }
}

export const GET = forward;
export const POST = forward;
