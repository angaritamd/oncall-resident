import { expect, test, type Page } from "@playwright/test";

// Shift review (review_all) on the live review set (?set=review): DEMO-0006/0007/0008
// reuse the public LIDC studies already in Orthanc by reference, with their own case_ids.
// "revisa todos los estudios" → the "Revisión del turno" card, DEMO-0006 first.
// Needs DEMO_RESET_ENABLED=1 and the tester in ADMIN_USERS on the server.
// Shares demo state, serial; leaves the default set restored for the specs after it.
test.describe.configure({ mode: "serial" });

async function reset(page: Page, set: string) {
  // sec-fetch-site is what a real browser sends on fetch; without Serve there is no x-forwarded-host
  const r = await page.request.post(`/api/demo/reset-reports${set === "default" ? "" : "?set=review"}`, {
    headers: { origin: new URL(page.url()).origin, "sec-fetch-site": "same-origin" },
  });
  expect(r.status(), "demo reset (DEMO_RESET_ENABLED + ADMIN_USERS)").toBe(200);
}

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

async function cardTouchTargets(page: Page) {
  const small = await page
    .getByTestId("review-card")
    .locator("button, a")
    .evaluateAll((els) => els.map((el) => el.getBoundingClientRect()).filter((r) => r.width > 0 && (r.height < 44 || r.width < 44)).length);
  expect(small).toBe(0);
}

test.afterAll(async ({ request, baseURL }) => {
  const r = await request.post("/api/demo/reset-reports", {
    headers: { origin: new URL(baseURL!).origin, "sec-fetch-site": "same-origin" },
  });
  expect(r.status(), "restore default set").toBe(200);
});

test("revisa todos los estudios → tarjeta con DEMO-0006 primero", async ({ page }) => {
  test.setTimeout(900_000); // real-model turns take minutes; rules fallback is instant
  await page.goto("/");
  await reset(page, "review");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Residente" })).toBeVisible();

  await page.getByLabel("Instrucción para el residente").fill("revisa todos los estudios");
  await page.keyboard.press("Enter");
  const card = page.getByTestId("review-card");
  await expect(card).toBeVisible({ timeout: 60_000 });

  // the run advances in the background; the card polls until it stops
  await expect(card.getByText(/Terminada|Pausada/)).toBeVisible({ timeout: 840_000 });

  const rows = card.locator("ol > li");
  await expect(rows).toHaveCount(5);
  await expect(rows.first()).toContainText("DEMO-0006");
  // rules fallback says "No evaluado"; a real model answers "Crítico sin respuesta"
  await expect(rows.first()).toContainText(/No evaluado|Crítico sin respuesta/);
  await expect(card).toContainText("No se modificó ningún informe. La firma es del radiólogo.");

  await noHorizontalScroll(page);
  await cardTouchTargets(page);

  // "Abrir caso" opens the study
  await rows.first().getByRole("button", { name: "Abrir caso DEMO-0006" }).click();
  await expect(page.getByRole("region", { name: "Caso DEMO-0006" })).toBeVisible();
  await noHorizontalScroll(page);
});
