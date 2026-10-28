import { expect, test, type Page } from "@playwright/test";

// Pending items (pending_items): derived from metadata, added from what the radiologist says, listed for tomorrow.
// Nothing is sent to anyone. Shares demo state: serial, after a demo reset (DEMO_RESET_ENABLED + ADMIN_USERS).
test.describe.configure({ mode: "serial" });

const shots = "../docs/screenshots/after";

async function reset(page: Page) {
  const r = await page.request.post("/api/demo/reset-reports", { headers: { origin: new URL(page.url()).origin } });
  expect(r.status(), "demo reset (DEMO_RESET_ENABLED + ADMIN_USERS)").toBe(200);
}

async function ask(page: Page, text: string) {
  await page.getByLabel("Instrucción para el residente").fill(text);
  await page.keyboard.press("Enter");
}

test("pendientes: metadata items, 'pídele previos', '¿qué queda para mañana?', Hecho", async ({ page }, info) => {
  await page.goto("/");
  await reset(page);
  await page.reload();
  await page.getByRole("navigation").getByRole("button", { name: "Pendientes" }).click();
  const list = page.getByTestId("pending-items");
  // from metadata: DEMO-0002 (series to repeat + missing priors) and DEMO-0004 (missing priors)
  await expect(list.locator("li[data-kind=repeat_series]")).toContainText("Serie a repetir");
  await expect(list.locator("li[data-kind=missing_priors]")).toHaveCount(2);
  await expect(page.getByText("Nada se envía a nadie hoy")).toBeVisible();

  // the radiologist asks for something on the open case
  await page.getByRole("navigation").getByRole("button", { name: "Lista" }).click();
  await page.getByRole("button", { name: /^Abrir caso DEMO-0005/ }).click();
  await expect(page.getByRole("region", { name: "Caso DEMO-0005" })).toBeVisible();
  await ask(page, "Pídele previos");
  await expect(page.locator("main").getByText(/Anotado en pendientes de DEMO-0005: Previos que faltan/)).toBeVisible();
  await ask(page, "Segunda revisión mañana");
  await expect(page.locator("main").getByText(/Segunda revisión mañana\. No se envía/)).toBeVisible();

  await ask(page, "¿Qué queda para mañana?");
  const answer = page.locator("main p", { hasText: /^Para mañana:/ }).last();
  await expect(answer).toContainText("DEMO-0005 · Previos que faltan, Segunda revisión mañana");
  await expect(answer).toContainText("DEMO-0002");

  await page.getByRole("navigation").getByRole("button", { name: "Pendientes" }).click();
  const repeat = list.locator("li[data-kind=repeat_series]");
  await repeat.getByRole("button", { name: "Hecho" }).click();
  await expect(repeat.getByRole("button", { name: "Reabrir" })).toBeVisible();
  await page.screenshot({ path: `${shots}/${info.project.name}-12-pendientes.png` });
});
