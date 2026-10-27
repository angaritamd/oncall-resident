import { NextResponse, type NextRequest } from "next/server";
import { authorize, LOGIN_HEADER, parseAllowed } from "@/lib/auth";

const MESSAGES = {
  "missing-identity": "Acceso solo por la tailnet (falta la identidad de Tailscale).",
  "not-allowed": "Tu usuario de Tailscale no está autorizado.",
  "no-allowlist": "No hay usuarios autorizados configurados (ALLOWED_USERS).",
} as const;

/** Every request (pages, API, assets) needs an allowed tailnet identity. */
export function proxy(request: NextRequest) {
  const result = authorize(request.headers.get(LOGIN_HEADER), parseAllowed(process.env.ALLOWED_USERS));
  if (result.ok) return NextResponse.next();
  const headers = { "cache-control": "no-store, private", "x-content-type-options": "nosniff" };
  const detail = MESSAGES[result.reason];
  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ detail }, { status: result.status, headers });
  }
  return new NextResponse(detail, { status: result.status, headers: { ...headers, "content-type": "text/plain; charset=utf-8" } });
}
