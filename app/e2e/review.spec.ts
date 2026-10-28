import { expect, test, type Page } from "@playwright/test";

// Shift review (review_all): "revisa todos los estudios" → the "Revisión del turno"
// card with one row per pending study, DEMO-0001 (critical, no draft) first.
// Needs DEMO_RESET_ENABLED=1 and the tester in ADMIN_USERS on the server.
// Starts from the default seed so the 5 rows below hold; shares demo state, serial.
test.describe.configure({ mode: "serial" });

async function reset(page: Page) {
  const r = await page.request.post("/api/demo/reset-reports", { headers: { origin: new URL(page.url()).origin } });
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

test("revisa todos los estudios → tarjeta con 5 filas, DEMO-0001 arriba", async ({ page }) => {
  test.setTimeout(900_000); // real-model turns take minutes; rules fallback is instant
  await page.goto("/");
  await reset(page);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Residente" })).toBeVisible();

  await page.getByLabel("Instrucción para el residente").fill("revisa todos los estudios");
  await page.keyboard.press("Enter");
  const card = page.getByTestId("review-card");
  await expect(card).toBeVisible({ timeout: 60_000 });
  await expect(card).toContainText(/0 de 5|En curso/);

  // the run advances in the background; the card polls until it stops
  await expect(card.getByText(/Terminada|Pausada/)).toBeVisible({ timeout: 840_000 });

  const rows = card.locator("ol > li");
  await expect(rows).toHaveCount(5);
  await expect(rows.first()).toContainText("DEMO-0001");
  await expect(rows.first()).toContainText("Sin borrador");
  await expect(card).toContainText("No se modificó ningún informe. La firma es del radiólogo.");

  await noHorizontalScroll(page);
  await cardTouchTargets(page);

  // "Abrir caso" opens the study
  await rows.first().getByRole("button", { name: "Abrir caso DEMO-0001" }).click();
  await expect(page.getByRole("region", { name: "Caso DEMO-0001" })).toBeVisible();
  await noHorizontalScroll(page);
});
