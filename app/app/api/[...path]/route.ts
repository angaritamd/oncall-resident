// Same-origin proxy to the core so the phone only talks to the app's port.
const CORE_URL = () => process.env.CORE_URL ?? "http://127.0.0.1:18000";

async function forward(req: Request, ctx: RouteContext<"/api/[...path]">) {
  const { path } = await ctx.params;
  const url = new URL(req.url);
  const target = `${CORE_URL()}/api/${path.map(encodeURIComponent).join("/")}${url.search}`;
  try {
    const res = await fetch(target, {
      method: req.method,
      headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
      body: req.method === "GET" ? undefined : await req.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    return new Response(res.body, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "core unreachable" }, { status: 502 });
  }
}

export const GET = forward;
export const POST = forward;
