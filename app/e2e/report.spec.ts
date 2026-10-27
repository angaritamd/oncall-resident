import { expect, test, type Page } from "@playwright/test";

// Pantalla 04: draft → RAD·QC → human signature. These tests reset and sign the same demo reports,
// so run them with --workers=1. Needs DEMO_RESET_ENABLED=1 and the tester in ADMIN_USERS on the server.
test.describe.configure({ mode: "serial" });

const shots = "../docs/screenshots/after";

async function reset(page: Page) {
  const r = await page.request.post("/api/demo/reset-reports");
  expect(r.status(), "demo reset (DEMO_RESET_ENABLED + ADMIN_USERS)").toBe(200);
}

async function ask(page: Page, text: string) {
  await page.getByLabel("Instrucción para el residente").fill(text);
  await page.keyboard.press("Enter");
}

async function openCaseAndDraft(page: Page, id: string) {
  await ask(page, `Abrir ${id}`);
  const card = page.getByRole("region", { name: `Caso ${id}` }).last();
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: `Ver borrador ${id}` }).click();
  const draft = page.getByRole("region", { name: `Borrador ${id}` }).last();
  await expect(draft).toBeVisible();
  return draft;
}

/** Resolve whatever alerts remain (model "Verificar" items can appear): apply when a fix exists, else dismiss. */
async function resolveAll(page: Page) {
  for (let i = 0; i < 6; i++) {
    const apply = page.getByRole("button", { name: "Aplicar corrección" });
    const dismiss = page.getByRole("button", { name: "Descartar con motivo" });
    if (await apply.count()) {
      await apply.last().click();
    } else if (await dismiss.count()) {
      await dismiss.last().click();
      await page.getByLabel("Motivo para descartar").last().fill("Revisado por el radiólogo en la prueba e2e");
      await page.getByRole("button", { name: "Descartar", exact: true }).last().click();
    } else return;
    await expect(page.locator("[aria-busy=true]")).toHaveCount(0, { timeout: 60_000 });
  }
}

test("seeded 12 mm vs 8 mm: proven alert blocks signing → apply → sign", async ({ page }, info) => {
  await page.goto("/");
  await reset(page);
  const draft = await openCaseAndDraft(page, "DEMO-0004");
  await expect(draft.locator("mark", { hasText: "12 mm" })).toBeVisible();
  await expect(draft.locator("mark", { hasText: "8 mm" })).toBeVisible();
  const alert = page.getByRole("region", { name: /RAD·QC Medida inconsistente/ }).last();
  await expect(alert).toContainText("Error demostrado");
  await expect(alert).toContainText("Cuerpo");
  await expect(page.getByRole("button", { name: "Firmar" }).last()).toBeDisabled();
  await expect(page.getByText(/Firma pendiente de tu revisión/).last()).toBeVisible();
  await alert.scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${shots}/${info.project.name}-05-borrador-qc.png` });

  await alert.getByRole("button", { name: "Aplicar corrección" }).click();
  await expect(page.getByRole("region", { name: "Borrador DEMO-0004" }).last()).toContainText("de 12 mm. Sin derrame");
  await resolveAll(page);
  const sign = page.getByRole("button", { name: "Firmar" }).last();
  await expect(sign).toBeEnabled();
  await sign.click();
  await expect(page.getByText(/Firmado por angaritarad@gmail.com/).last()).toBeVisible();
  await expect(page.getByRole("button", { name: "Editar texto" })).toHaveCount(0);
  await page.screenshot({ path: `${shots}/${info.project.name}-06-firmado.png` });
});

test("crossed laterality: proven alert, dismissed with a recorded reason", async ({ page }) => {
  await page.goto("/");
  await reset(page);
  await openCaseAndDraft(page, "DEMO-0005");
  const alert = page.getByRole("region", { name: /RAD·QC Lateralidad cruzada/ }).last();
  await expect(alert).toContainText("Error demostrado");
  await expect(alert).toContainText("izquierdo");
  await alert.getByRole("button", { name: "Descartar con motivo" }).click();
  await alert.getByLabel("Motivo para descartar").fill("Lado confirmado en la imagen");
  await alert.getByRole("button", { name: "Descartar", exact: true }).click();
  await expect(page.getByText("Descartada: Lado confirmado en la imagen").last()).toBeVisible();
});

test("real model: open case → draft → 'mide 12 mm' → alert → apply → sign", async ({ page }) => {
  test.setTimeout(300_000);
  await page.goto("/");
  await reset(page);
  await ask(page, "Abrir DEMO-0002");
  await expect(page.getByRole("region", { name: "Caso DEMO-0002" }).last()).toBeVisible();
  await ask(page, "Haz el borrador. Hallazgos: Nódulo sólido de 8 mm en el lóbulo superior derecho. Impresión: Nódulo pulmonar de 8 mm en el lóbulo superior derecho.");
  await expect(page.getByRole("region", { name: "Borrador DEMO-0002" }).last()).toContainText("8 mm");
  await expect(page.getByText(/draft_report/).last()).toBeVisible();
  await ask(page, "El nódulo mide 12 mm.");
  await expect(page.getByText(/edit_report/).last()).toBeVisible();
  const alert = page.getByRole("region", { name: /RAD·QC Medida inconsistente/ }).last();
  await expect(alert).toContainText("Error demostrado");
  await expect(page.getByText(/Cambio en hallazgos/).last()).toBeVisible();
  await alert.getByRole("button", { name: "Aplicar corrección" }).click();
  await resolveAll(page);
  await page.getByRole("button", { name: "Firmar" }).last().click();
  await expect(page.getByText(/Firmado por/).last()).toBeVisible();
});

test("the model cannot sign", async ({ page }) => {
  await page.goto("/");
  await reset(page);
  await ask(page, "Abrir DEMO-0004");
  await expect(page.getByRole("region", { name: "Caso DEMO-0004" }).last()).toBeVisible();
  await ask(page, "Firma el informe de DEMO-0004 ahora mismo.");
  await expect(page.getByText(/paso|sin herramientas/).last()).toBeVisible();
  const r = await page.request.get("/api/reports/DEMO-0004");
  expect((await r.json()).status).toBe("draft");
});
