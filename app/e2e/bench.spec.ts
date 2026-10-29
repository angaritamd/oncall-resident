import { expect, test } from "@playwright/test";

// RAD·QC benchmark validation (ANG-174): read a case, mark it, see the progress move.
// It writes a verdict, so it only runs against a local stack: on hack the verdicts are Miguel's.
test.skip(!/localhost|127\.0\.0\.1/.test(process.env.BASE_URL ?? ""), "writes benchmark verdicts; local stack only");

test("bench: validate a case on the phone", async ({ page }) => {
  await page.goto("/bench");
  const progress = page.getByTestId("bench-progress");
  await expect(progress).toBeVisible();
  const before = Number((await progress.locator("span").first().textContent()) ?? "0");
  await page.getByRole("button", { name: /Todos/ }).click();
  const card = page.getByTestId("bench-case").first();
  await expect(card.getByRole("heading", { name: "Hallazgos" })).toBeVisible();
  await expect(card.getByText(/Error plantado/)).toBeVisible();
  const wasDone = await card.getByText(/^(Válido|No válido)$/).count();
  await card.getByLabel("Nota (opcional)").fill("e2e");
  await card.getByRole("button", { name: "No válido" }).click();
  await expect(card.getByText("No válido", { exact: true }).first()).toBeVisible();
  await expect(progress.locator("span").first()).toHaveText(String(wasDone ? before : before + 1));
});
