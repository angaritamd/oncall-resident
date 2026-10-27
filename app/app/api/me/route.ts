import { LOGIN_HEADER } from "@/lib/auth";

// Reached only after proxy.ts authorized the request.
export function GET(request: Request) {
  return Response.json(
    { login: request.headers.get(LOGIN_HEADER)?.trim().toLowerCase() ?? null },
    { headers: { "cache-control": "no-store, private" } },
  );
}
