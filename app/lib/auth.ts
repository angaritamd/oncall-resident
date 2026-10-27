// Tailnet identity check. `tailscale serve` adds Tailscale-User-Login to every request it proxies and the
// app only listens on 127.0.0.1, so the header can only come from Serve. Fails closed.

export const LOGIN_HEADER = "tailscale-user-login";

export type AuthResult = { ok: true; login: string } | { ok: false; status: 401 | 403; reason: "missing-identity" | "not-allowed" | "no-allowlist" };

/** "a@x.com, B@y.com" → {"a@x.com", "b@y.com"} */
export function parseAllowed(raw: string | undefined): Set<string> {
  return new Set(
    (raw ?? "")
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean),
  );
}

export function authorize(login: string | null | undefined, allowed: Set<string>): AuthResult {
  const who = (login ?? "").trim().toLowerCase();
  if (!who) return { ok: false, status: 401, reason: "missing-identity" };
  if (allowed.size === 0) return { ok: false, status: 403, reason: "no-allowlist" };
  if (!allowed.has(who)) return { ok: false, status: 403, reason: "not-allowed" };
  return { ok: true, login: who };
}
