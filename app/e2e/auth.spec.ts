import { expect, test } from "@playwright/test";

const base = process.env.BASE_URL ?? "http://127.0.0.1:3000";
const viaServe = base.startsWith("https://") && base.includes(".ts.net");

// Local server started with ALLOWED_USERS=tester@example.com (see app/README.md).
test.describe("auth against a local server", () => {
  test.skip(viaServe, "only meaningful when the test controls the identity header");

  test("no identity → 401 on pages and API", async ({ playwright }) => {
    const anon = await playwright.request.newContext({ baseURL: base, extraHTTPHeaders: {} });
    expect((await anon.get("/")).status()).toBe(401);
    const api = await anon.get("/api/worklist");
    expect(api.status()).toBe(401);
    expect(api.headers()["cache-control"]).toContain("no-store");
    expect((await api.json()).detail).toMatch(/tailnet/);
    await anon.dispose();
  });

  test("identity not allowed → 403", async ({ playwright }) => {
    const eve = await playwright.request.newContext({ baseURL: base, extraHTTPHeaders: { "Tailscale-User-Login": "eve@example.com" } });
    expect((await eve.get("/api/me")).status()).toBe(403);
    expect((await eve.get("/")).status()).toBe(403);
    await eve.dispose();
  });

  test("allowed identity → 200, case-insensitive", async ({ playwright }) => {
    const ok = await playwright.request.newContext({ baseURL: base, extraHTTPHeaders: { "Tailscale-User-Login": "Tester@Example.com" } });
    expect((await ok.get("/")).status()).toBe(200);
    expect(await (await ok.get("/api/me")).json()).toEqual({ login: "tester@example.com" });
    await ok.dispose();
  });
});

// Through `tailscale serve`, the header comes from Tailscale; a client-supplied one must not win.
test.describe("auth through tailscale serve", () => {
  test.skip(!viaServe || !process.env.E2E_EXPECT_LOGIN, "needs BASE_URL on *.ts.net and E2E_EXPECT_LOGIN");

  test("a spoofed Tailscale-User-Login header is ignored", async ({ playwright }) => {
    const spoof = await playwright.request.newContext({ baseURL: base, extraHTTPHeaders: { "Tailscale-User-Login": "spoof@example.com" } });
    const res = await spoof.get("/api/me");
    expect(res.status()).toBe(200);
    expect((await res.json()).login).toBe(process.env.E2E_EXPECT_LOGIN!.toLowerCase());
    await spoof.dispose();
  });
});
