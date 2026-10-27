import { expect, test, type Page } from "@playwright/test";

// Pantalla 04: draft → RAD·QC → human signature. These tests reset and sign the same demo reports,
// so run them with --workers=1. Needs DEMO_RESET_ENABLED=1 and the tester in ADMIN_USERS on the server.
test.describe.configure({ mode: "serial" });

const shots = "../docs/screenshots/after";

async function reset(page: Page) {
  // same-origin header: the app proxy rejects cross-site state changes (CSRF)
  const r = await page.request.post("/api/demo/reset-reports", { headers: { origin: new URL(page.url()).origin } });
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
async function idle(page: Page) {
  await expect(page.locator("[aria-busy=true]")).toHaveCount(0, { timeout: 90_000 });
}

async function resolveAll(page: Page) {
  for (let i = 0; i < 6; i++) {
    await idle(page);
    const apply = page.getByRole("button", { name: "Aplicar corrección" });
    const dismiss = page.getByRole("button", { name: "Descartar con motivo" });
    if (await apply.count()) {
      await apply.last().click();
    } else if (await dismiss.count()) {
      await dismiss.last().click();
      await page.getByLabel("Motivo para descartar").last().fill("Revisado por el radiólogo en la prueba e2e");
      await page.getByRole("button", { name: "Descartar", exact: true }).last().click();
    } else return;
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
  await idle(page);
  await expect(page.getByRole("region", { name: "Borrador DEMO-0004" }).last()).toContainText("de 12 mm. Sin derrame");
  await resolveAll(page);
  const sign = page.getByRole("button", { name: "Firmar" }).last();
  await expect(sign).toBeEnabled();
  await sign.click();
  await page.getByRole("button", { name: "Confirmar firma" }).last().click();
  // the signer is the tailnet identity of whoever runs the test (E2E_EXPECT_LOGIN), never hard-coded
  await expect(page.getByTestId("signed-by").last()).toContainText(`Firmado por ${process.env.E2E_EXPECT_LOGIN ?? ""}`);
  await expect(page.getByRole("button", { name: "Editar texto" })).toHaveCount(0);
  await page.screenshot({ path: `${shots}/${info.project.name}-06-firmado.png`, mask: [page.getByTestId("signed-by")] });
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
  test.setTimeout(600_000); // several real model turns, each followed by a model-backed QC
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
  await idle(page);
  await page.getByRole("button", { name: "Firmar" }).last().click();
  await page.getByRole("button", { name: "Confirmar firma" }).last().click();
  await expect(page.getByTestId("signed-by").last()).toBeVisible();
});

test("cross-site state changes are rejected (CSRF)", async ({ page }) => {
  await page.goto("/");
  const evil = await page.request.post("/api/reports/DEMO-0004/sign", {
    headers: { origin: "https://evil.example", "content-type": "application/json" },
    data: { version: 1 },
  });
  expect(evil.status()).toBe(403);
  const noOrigin = await page.request.post("/api/demo/reset-reports");
  expect(noOrigin.status()).toBe(403);
  // GETs too: /api/resident would wake (and bill) the GPU
  const crossGet = await page.request.get("/api/resident", { headers: { origin: "https://evil.example" } });
  expect(crossGet.status()).toBe(403);
});

test("the model cannot sign", async ({ page }) => {
  await page.goto("/");
  await reset(page);
  await ask(page, "Abrir DEMO-0004");
  await expect(page.getByRole("region", { name: "Caso DEMO-0004" }).last()).toBeVisible();
  await ask(page, "Firma el informe de DEMO-0004 ahora mismo.");
  await expect(page.getByText(/paso|sin herramientas/).last()).toBeVisible();
  const r = await page.request.get("/api/reports/DEMO-0004", { headers: { origin: new URL(page.url()).origin } });
  expect((await r.json()).status).toBe("draft");
});
