import { expect, test, type Page } from "@playwright/test";

const shots = "../docs/screenshots/after";

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

async function composerDoesNotCover(page: Page) {
  const [main, footer] = await Promise.all([page.locator("main").boundingBox(), page.locator("footer").boundingBox()]);
  expect(main!.y + main!.height).toBeLessThanOrEqual(footer!.y + 1);
}

async function askPending(page: Page) {
  await page.getByLabel("Instrucción para el residente").fill("¿Qué tengo pendiente?");
  await page.keyboard.press("Enter");
}

async function touchTargets(page: Page) {
  const small = await page.evaluate(() =>
    [...document.querySelectorAll("button, a, input")]
      .map((el) => el.getBoundingClientRect())
      .filter((r) => r.width > 0 && (r.height < 44 || r.width < 44)).length,
  );
  expect(small).toBe(0);
}

test("01 inicio de turno → 03 caso abierto → prioridad", async ({ page }, info) => {
  const p = info.project.name;
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Residente" })).toBeVisible();
  await expect(page.locator("#greeting")).toContainText(/Tienes 5 estudios en cola\./);
  const next = page.getByRole("region", { name: "Siguiente estudio DEMO-0001" });
  await expect(next).toContainText("Crítico · tecnólogo");
  await expect(page.getByText("Críticos", { exact: true }).locator("..").locator("..")).toContainText("1");
  await expect(page.getByRole("button", { name: /Qué quedó para mañana\? \(Disponible pronto\)/ })).toBeDisabled();
  await expect(page.getByRole("button", { name: /Resumir mi turno \(Disponible pronto\)/ })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Dictar (disponible pronto)" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Adjuntar (disponible pronto)" })).toBeDisabled();
  await noHorizontalScroll(page);
  await touchTargets(page);
  await page.screenshot({ path: `${shots}/${p}-01-inicio.png` });

  await next.getByRole("button", { name: "Abrir estudio DEMO-0001" }).click();
  await expect(page.getByText(/^Tú: Abrir DEMO-0001$/)).toBeVisible();
  const card = page.getByRole("region", { name: "Caso DEMO-0001" });
  await expect(card).toContainText("Disnea súbita y dolor torácico derecho.");
  await expect(card).toContainText("Marcado como crítico por el tecnólogo");
  await expect(card).toContainText(/Hombre\s?·\s?34 a/);
  await expect(card.getByText("Marcado como crítico por el tecnólogo")).toBeVisible();
  await expect(card.getByText(/Crítico · tecnólogo/)).toBeVisible();
  await expect(card.getByRole("button", { name: "Ver imágenes (Disponible pronto)" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Caso activo: DEMO-0001" })).toBeVisible();
  await expect(page.getByRole("button", { name: /firmar|sign/i })).toHaveCount(0);
  await noHorizontalScroll(page);
  await composerDoesNotCover(page);
  await expect(card).toBeInViewport();
  await expect(page.getByRole("button", { name: "Volver al inicio" })).toBeInViewport();
  await page.waitForTimeout(400); // let smooth scroll settle before the screenshot
  await page.screenshot({ path: `${shots}/${p}-03-caso.png` });

  await page.getByRole("button", { name: "¿Por qué va primero?" }).last().click();
  await expect(page.getByText(/el tecnólogo lo marcó como crítico/)).toBeVisible();
  await page.getByRole("button", { name: "Ver pendientes" }).last().click();
  await page.getByRole("button", { name: "Ver los 5 estudios" }).click();
  await expect(page.getByRole("button", { name: /^Abrir caso DEMO-0003/ }).first()).toBeVisible();
  await noHorizontalScroll(page);
});

test("opening the same case twice scrolls to the newest card", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("region", { name: /Siguiente estudio/ }).getByRole("button", { name: /Abrir estudio/ }).click();
  await expect(page.getByRole("region", { name: "Caso DEMO-0001" })).toHaveCount(1);
  await page.getByLabel("Instrucción para el residente").fill("Abrir DEMO-0001");
  await page.keyboard.press("Enter");
  const cards = page.getByRole("region", { name: "Caso DEMO-0001" });
  await expect(cards).toHaveCount(2);
  expect(new Set(await cards.evaluateAll((els) => els.map((e) => e.id))).size).toBe(2);
  await expect(cards.last()).toBeInViewport();
});

test("02 pendientes con filtros", async ({ page }, info) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("button", { name: "Pendientes" }).click();
  await expect(page.getByRole("heading", { name: "Críticos · tecnólogo" })).toBeVisible();
  const arrival = page.getByRole("heading", { name: "Por orden de llegada" }).locator("xpath=ancestor::section[1]");
  // oldest first: DEMO-0004 (180 min) before DEMO-0003 (95 min)
  const ids = await arrival.locator("li").allTextContents();
  expect(ids.findIndex((s) => s.includes("DEMO-0004"))).toBeLessThan(ids.findIndex((s) => s.includes("DEMO-0003")));
  await noHorizontalScroll(page);
  await page.screenshot({ path: `${shots}/${info.project.name}-02-pendientes.png` });
  await page.getByRole("button", { name: /^Urgentes/ }).click();
  await expect(page.getByRole("button", { name: /^Urgentes/ })).toHaveAttribute("aria-pressed", "true");
  await expect(arrival.locator("li")).toHaveCount(1);
  await expect(page.getByRole("heading", { name: "Críticos · tecnólogo" })).toHaveCount(0);
  await arrival.getByRole("button", { name: /^Abrir caso DEMO-0002/ }).click();
  await expect(page.getByRole("region", { name: "Caso DEMO-0002" })).toBeVisible();
});

test("studies without order metadata are listed, not hidden", async ({ page }) => {
  await page.route("**/api/worklist**", async (r) => {
    const res = await r.fetch();
    const body = await res.json();
    body.items.push({ ...body.items[0], case_id: "9.9.9", study_uid: "9.9.9", exam: null, modalities: ["CT"], wait_minutes: null, arrived_at: null, critical: false, priority: null, has_metadata: false, reason: null, tech_note: null, reasons: [{ kind: "unknown", label: "Sin prioridad", source: "Sin metadatos" }] });
    await r.fulfill({ response: res, json: body });
  });
  await page.goto("/");
  await page.getByRole("navigation").getByRole("button", { name: "Pendientes" }).click();
  await expect(page.getByRole("heading", { name: "Sin metadatos de la orden · 1" })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Abrir caso 9\.9\.9/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Todos/ })).toContainText("6");
});

test("actividad", async ({ page }, info) => {
  await page.goto("/");
  await page.getByRole("region", { name: /Siguiente estudio/ }).getByRole("button", { name: /Abrir estudio/ }).click();
  await expect(page.getByRole("region", { name: /^Caso DEMO/ })).toBeVisible();
  await page.getByRole("navigation").getByRole("button", { name: "Actividad" }).click();
  await expect(page.getByText("Abrió caso").first()).toBeVisible();
  await page.screenshot({ path: `${shots}/${info.project.name}-04-actividad.png` });
});

test("english", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Cambiar idioma a inglés" }).click();
  await expect(page.locator("#greeting")).toContainText(/You have 5 studies in queue\./);
  await page.getByLabel("Instruction for the resident").fill("What's pending?");
  await page.keyboard.press("Enter");
  await expect(page.getByText(/You have 5 pending studies/)).toBeVisible();
  await page.getByRole("button", { name: "View all pending" }).click();
  await expect(page.getByRole("heading", { name: /^Pending/ })).toBeVisible();
});

test("PACS failure shows retry", async ({ page }) => {
  let fail = true;
  await page.route("**/api/chat", (r) =>
    fail ? r.fulfill({ status: 503, body: JSON.stringify({ detail: "No pude consultar el PACS. Revisa la conexión y reintenta." }), contentType: "application/json" }) : r.fallback(),
  );
  await page.goto("/");
  await askPending(page);
  await expect(page.locator("main").getByRole("alert")).toContainText("No pude consultar el PACS");
  fail = false;
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(page.getByText(/Tienes 5 estudios pendientes/)).toBeVisible();
});

test("worklist failure on home shows retry", async ({ page }) => {
  let fail = true;
  await page.route("**/api/worklist**", (r) => (fail ? r.fulfill({ status: 503, body: "{}", contentType: "application/json" }) : r.fallback()));
  await page.goto("/");
  await expect(page.locator("main").getByRole("alert")).toContainText("No pude consultar el PACS");
  fail = false;
  await page.getByRole("button", { name: "Reintentar" }).click();
  await expect(page.getByRole("region", { name: /Siguiente estudio/ })).toBeVisible();
});

test("offline state", async ({ page, context }) => {
  await page.goto("/");
  await expect(page.getByRole("region", { name: /Siguiente estudio/ })).toBeVisible();
  await context.setOffline(true);
  await expect(page.getByText("Sin conexión", { exact: true }).first()).toBeAttached();
  await askPending(page);
  await expect(page.locator("main").getByRole("alert")).toContainText("Sin conexión");
  await context.setOffline(false);
});

test("keyboard: composer and send", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Instrucción para el residente").focus();
  await page.keyboard.type("pendientes");
  await page.keyboard.press("Tab"); // disabled microphone is skipped
  await expect(page.getByRole("button", { name: "Enviar" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByText(/Tienes 5 estudios pendientes/)).toBeVisible();
});

test("PWA manifest and icons", async ({ request }) => {
  const m = await (await request.get("/manifest.webmanifest")).json();
  expect(m.name).toBe("Residente");
  expect(m.display).toBe("standalone");
  expect(m.theme_color).toBe("#E9ECF0");
  expect(m.icons.some((i: { purpose: string }) => i.purpose === "maskable")).toBe(true);
  for (const i of m.icons) expect((await request.get(i.src)).status()).toBe(200);
  expect((await request.get("/icons/apple-touch-icon.png")).status()).toBe(200);
});
