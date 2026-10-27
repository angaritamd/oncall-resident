import { expect, test, type Page } from "@playwright/test";

const shots = "../docs/screenshots";

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

async function composerDoesNotCover(page: Page) {
  // the scroll area ends where the footer begins: nothing in main can sit under the composer
  const [main, footer] = await Promise.all([page.locator("main").boundingBox(), page.locator("footer").boundingBox()]);
  expect(main!.y + main!.height).toBeLessThanOrEqual(footer!.y + 1);
}

test("pending → priority → open case → back to chat", async ({ page }, info) => {
  const p = info.project.name;
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Residente" })).toBeVisible();
  await expect(page.getByText("Esperando instrucción")).toBeVisible();
  await expect(page.getByRole("button", { name: "Micrófono (no disponible)" })).toBeDisabled();
  await page.screenshot({ path: `${shots}/${p}-1-empty.png` });

  await page.getByLabel("Instrucción para el residente").fill("¿Qué tengo pendiente?");
  await page.keyboard.press("Enter");
  const next = page.getByRole("region", { name: /Siguiente estudio DEMO-0001/ });
  await expect(next).toBeVisible();
  await expect(next.getByText("Crítico")).toBeVisible();
  await expect(next.getByText("Tecnólogo")).toBeVisible();
  await page.getByRole("button", { name: "Ver los 5 estudios" }).click();
  await expect(page.getByRole("button", { name: "Abrir caso DEMO-0003" })).toBeVisible();
  await noHorizontalScroll(page);
  await composerDoesNotCover(page);
  await page.screenshot({ path: `${shots}/${p}-2-pending.png` });

  await next.getByRole("button", { name: "¿Por qué primero?" }).click();
  await expect(page.getByText(/el tecnólogo lo marcó como crítico/)).toBeVisible();
  await page.screenshot({ path: `${shots}/${p}-3-why.png` });

  await page.getByRole("region", { name: /Origen de la prioridad DEMO-0001/ }).getByRole("button", { name: /Abrir caso DEMO-0001/ }).click();
  await expect(page.getByText("Indicación (orden)")).toBeVisible();
  await expect(page.getByText("Disnea súbita y dolor torácico derecho.")).toBeVisible();
  await expect(page.getByText("Marcado como crítico por el tecnólogo")).toBeVisible();
  await expect(page.getByText("No disponible hoy")).toBeVisible();
  await expect(page.getByRole("button", { name: "Caso activo: DEMO-0001" })).toBeVisible();
  await noHorizontalScroll(page);
  await page.screenshot({ path: `${shots}/${p}-4-case.png`, fullPage: true });

  await page.getByRole("button", { name: "Volver al chat" }).first().click();
  await expect(page.getByText("Abrí DEMO-0001.")).toBeVisible();
  await expect(page.getByLabel("Instrucción para el residente")).toBeFocused();

  await page.getByRole("button", { name: "Pendientes" }).click();
  await expect(page.getByRole("heading", { name: "Pendientes" })).toBeVisible();
  await noHorizontalScroll(page);
  await page.screenshot({ path: `${shots}/${p}-5-pending-tab.png` });

  await page.getByRole("button", { name: "Actividad" }).click();
  await expect(page.getByText("Abrió caso").first()).toBeVisible();
  await page.screenshot({ path: `${shots}/${p}-6-activity.png` });
});

test("english", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cambiar idioma a inglés" }).click();
  await page.getByRole("button", { name: "What's pending?" }).click();
  await expect(page.getByText(/You have 5 pending studies/)).toBeVisible();
  await expect(page.getByText("Technologist").first()).toBeVisible();
});

test("PACS failure shows retry", async ({ page }) => {
  await page.route("**/api/chat", (r) => r.fulfill({ status: 503, body: JSON.stringify({ detail: "No pude consultar el PACS. Revisa la conexión y reintenta." }), contentType: "application/json" }));
  await page.goto("/");
  await page.getByRole("button", { name: "¿Qué tengo pendiente?" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("No pude consultar el PACS");
  await page.unroute("**/api/chat");
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(page.getByRole("region", { name: /Siguiente estudio/ })).toBeVisible();
});

test("offline state", async ({ page, context }) => {
  await page.goto("/");
  await context.setOffline(true);
  await expect(page.getByText("Sin conexión", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "¿Qué tengo pendiente?" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("Sin conexión");
  await context.setOffline(false);
});

test("keyboard: tab reaches composer and send", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Instrucción para el residente").focus();
  await page.keyboard.type("pendientes");
  await page.keyboard.press("Tab"); // the disabled microphone is skipped
  await expect(page.getByRole("button", { name: "Enviar" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", { name: /Siguiente estudio/ })).toBeVisible();
});
