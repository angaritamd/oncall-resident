// Run: node --test lib/auth.test.ts
import { strict as assert } from "node:assert";
import { test } from "node:test";
import { authorize, parseAllowed } from "./auth.ts";

const allowed = parseAllowed(" Ana@Example.com , ,bob@example.org ");

test("parseAllowed trims, lowercases and drops blanks", () => {
  assert.deepEqual([...allowed], ["ana@example.com", "bob@example.org"]);
  assert.equal(parseAllowed(undefined).size, 0);
});

test("missing or blank identity → 401", () => {
  for (const v of [null, undefined, "", "   "]) assert.deepEqual(authorize(v, allowed), { ok: false, status: 401, reason: "missing-identity" });
});

test("identity not in the allowlist → 403", () => {
  assert.deepEqual(authorize("eve@example.com", allowed), { ok: false, status: 403, reason: "not-allowed" });
});

test("empty allowlist fails closed → 403", () => {
  assert.deepEqual(authorize("ana@example.com", new Set()), { ok: false, status: 403, reason: "no-allowlist" });
});

test("allowed identity, case-insensitive", () => {
  assert.deepEqual(authorize("ANA@example.COM", allowed), { ok: true, login: "ana@example.com" });
});

test("no partial matches", () => {
  assert.equal(authorize("ana@example.co", allowed).ok, false);
  assert.equal(authorize("xana@example.com", allowed).ok, false);
});
