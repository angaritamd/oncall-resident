import { expect, test, type Page } from "@playwright/test";

// Day 4 reading flow, three cases in a row following the rule: one "Lo leo yo", one with AI ("de acuerdo"),
// one with a RAD·QC correction. Counts every tap and times each case. Needs DEMO_RESET_ENABLED=1 and the
// tester in ADMIN_USERS on the server; shares demo state, so it runs serially.
test.describe.configure({ mode: "serial" });

const shots = "../docs/screenshots/after";

async function reset(page: Page) {
  const r = await page.request.post("/api/demo/reset-reports", { headers: { origin: new URL(page.url()).origin } });
  expect(r.status(), "demo reset (DEMO_RESET_ENABLED + ADMIN_USERS)").toBe(200);
}

async function idle(page: Page) {
  await expect(page.locator("[aria-busy=true]")).toHaveCount(0, { timeout: 90_000 });
}

const order = (page: Page) =>
  page.getByTestId("worklist").locator("li").evaluateAll((els) => els.map((e) => e.getAttribute("data-case")));

/** Taps (clicks) and dictations (one typed or spoken instruction) per case, and wall time from open to signed. */
type Metric = { id: string; mode: string; taps: number; dictations: number; seconds: number };

function counter(page: Page) {
  let taps = 0;
  let dictations = 0;
  return {
    tap: async (loc: ReturnType<Page["locator"]>) => {
      taps++;
      await loc.click();
    },
    dictate: async (text: string) => {
      dictations++;
      await page.getByLabel("Instrucción para el residente").fill(text);
      await page.keyboard.press("Enter");
    },
    get: () => ({ taps, dictations }),
  };
}

/** Resolve whatever model "Verificar" items appear (dismiss with a reason): taps counted. */
async function resolveVerify(page: Page, c: ReturnType<typeof counter>) {
  for (let i = 0; i < 6; i++) {
    await idle(page);
    const apply = page.getByRole("button", { name: "Aplicar corrección" });
    const dismiss = page.getByRole("button", { name: "Descartar con motivo" });
    if (await apply.count()) {
      await c.tap(apply.last());
    } else if (await dismiss.count()) {
      await c.tap(dismiss.last());
      await page.getByLabel("Motivo para descartar").last().fill("Verificado en la estación");
      await c.tap(page.getByRole("button", { name: "Descartar", exact: true }).last());
    } else return;
  }
}

async function sign(page: Page, c: ReturnType<typeof counter>) {
  await idle(page);
  await expect(page.getByTestId("ready-to-sign").last()).toBeVisible();
  await c.tap(page.getByRole("button", { name: "Firmar" }).last());
  await c.tap(page.getByRole("button", { name: "Confirmar firma" }).last());
  // back to the list, the signed case out of pending, and the next proposed with the reason
  await expect(page.getByRole("heading", { name: /^Lista de trabajo/ })).toBeVisible();
  await expect(page.getByTestId("next-up")).toContainText("Regla");
}

test("three cases in a row: lo leo yo · con IA · corrección de QC", async ({ page }, info) => {
  test.setTimeout(900_000); // real model turns and model-backed QC
  const metrics: Metric[] = [];
  await page.goto("/");
  await reset(page);
  await page.reload();
  await page.getByRole("navigation").getByRole("button", { name: "Lista" }).click();
  await expect.poll(() => order(page)).toEqual(["DEMO-0001", "DEMO-0002", "DEMO-0005", "DEMO-0004", "DEMO-0003"]);

  // 1 · DEMO-0001 (critical): "Lo leo yo" → dictation → draft only from what was dictated → sign
  {
    const c = counter(page);
    const t0 = Date.now();
    await c.tap(page.getByRole("button", { name: /^Abrir caso DEMO-0001/ }));
    await expect(page.getByTestId("read-choice")).toBeVisible();
    await c.tap(page.getByRole("button", { name: "Lo leo yo" }));
    await c.dictate("Hallazgos: Neumotórax derecho de 2 cm en el ápex, sin desplazamiento mediastínico. Impresión: Neumotórax derecho pequeño.");
    await expect(page.getByRole("region", { name: "Borrador DEMO-0001" }).last()).toContainText("Neumotórax derecho", { timeout: 180_000 });
    await expect(page.getByTestId("proposal-badge")).toHaveCount(0); // dictated, not a proposal
    await resolveVerify(page, c);
    await sign(page, c);
    await expect(page.getByTestId("next-up")).toContainText("DEMO-0002");
    await page.screenshot({ path: `${shots}/${info.project.name}-07-siguiente.png` });
    metrics.push({ id: "DEMO-0001", mode: "lo leo yo", ...c.get(), seconds: (Date.now() - t0) / 1000 });
  }
  await expect.poll(() => order(page)).toEqual(["DEMO-0002", "DEMO-0005", "DEMO-0004", "DEMO-0003"]);

  // 2 · DEMO-0002: "Sí" → template proposal marked to verify → "De acuerdo" → QC → sign
  {
    const c = counter(page);
    const t0 = Date.now();
    await c.tap(page.getByTestId("next-up").getByRole("button", { name: /Abrir caso DEMO-0002/ }));
    await c.tap(page.getByRole("button", { name: "Sí", exact: true }));
    const draft = page.getByRole("region", { name: "Borrador DEMO-0002" }).last();
    await expect(draft.getByTestId("proposal-badge")).toContainText("Propuesta · verificar");
    await expect(page.getByRole("button", { name: "Firmar" }).last()).toBeDisabled();
    await idle(page);
    await draft.scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${shots}/${info.project.name}-08-propuesta.png` });
    await c.tap(page.getByRole("button", { name: "De acuerdo" }).last());
    await resolveVerify(page, c);
    await sign(page, c);
    metrics.push({ id: "DEMO-0002", mode: "con IA", ...c.get(), seconds: (Date.now() - t0) / 1000 });
  }

  // 3 · DEMO-0005: seeded draft with crossed laterality → "Aplicar corrección" → sign
  {
    const c = counter(page);
    const t0 = Date.now();
    await c.tap(page.getByTestId("next-up").getByRole("button", { name: /Abrir caso DEMO-0005/ }));
    const alert = page.getByRole("region", { name: /RAD·QC Lateralidad cruzada/ }).last();
    await expect(alert).toContainText("Error demostrado");
    await expect(page.getByTestId("read-choice")).toHaveCount(0); // a draft exists: no question
    await c.tap(alert.getByRole("button", { name: "Aplicar corrección" }));
    await resolveVerify(page, c);
    await sign(page, c);
    metrics.push({ id: "DEMO-0005", mode: "corrección QC", ...c.get(), seconds: (Date.now() - t0) / 1000 });
  }

  await expect.poll(() => order(page)).toEqual(["DEMO-0004", "DEMO-0003"]);
  await page.getByRole("button", { name: /^Firmados hoy/ }).click();
  await expect(page.getByTestId("signed-list").locator("li")).toHaveCount(3);
  await page.screenshot({ path: `${shots}/${info.project.name}-09-firmados.png` });
  console.log(`METRICS ${info.project.name} ${JSON.stringify(metrics)}`);
  await info.attach("metrics.json", { body: JSON.stringify(metrics, null, 2), contentType: "application/json" });
});

test("while a case is open the list is frozen; new studies wait in an 'N nuevos' chip", async ({ page }) => {
  await page.goto("/");
  await reset(page);
  await page.reload();
  let extra = false;
  await page.route("**/api/worklist**", async (r) => {
    const res = await r.fetch({ headers: { ...r.request().headers(), origin: new URL(r.request().url()).origin } });
    const body = await res.json();
    // a new STAT study arrives: by the rule it goes right after the critical one
    if (extra) body.items.splice(1, 0, { ...body.items[1], case_id: "DEMO-0099", study_uid: "9.9.99", position: 2 });
    await r.fulfill({ response: res, json: body });
  });
  await page.getByRole("navigation").getByRole("button", { name: "Lista" }).click();
  await page.getByRole("button", { name: /^Abrir caso DEMO-0003/ }).click();
  await expect(page.getByTestId("read-choice")).toBeVisible();
  extra = true;
  await page.getByRole("navigation").getByRole("button", { name: "Lista" }).click();
  await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
  // the open case is pinned on top as "En lectura" and the rest does not move
  await expect(page.getByTestId("reading-now")).toContainText("DEMO-0003");
  await expect.poll(() => order(page)).toEqual(["DEMO-0001", "DEMO-0002", "DEMO-0005", "DEMO-0004"]);
  await expect(page.getByTestId("new-chip")).toHaveText(/1 nuevo/, { timeout: 40_000 });
  await expect.poll(() => order(page)).toEqual(["DEMO-0001", "DEMO-0002", "DEMO-0005", "DEMO-0004"]);
  await page.getByTestId("new-chip").click();
  await expect.poll(() => order(page)).toEqual(["DEMO-0001", "DEMO-0099", "DEMO-0002", "DEMO-0005", "DEMO-0004"]);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("switching tabs keeps the chat where it was", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("button", { name: "Lista" }).click();
  await page.getByRole("button", { name: /^Abrir caso DEMO-0003/ }).click();
  await expect(page.getByTestId("read-choice")).toBeInViewport();
  const before = await page.locator("main").evaluate((el) => el.scrollTop);
  await page.getByRole("navigation").getByRole("button", { name: "Actividad" }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Chat" }).click();
  expect(Math.abs((await page.locator("main").evaluate((el) => el.scrollTop)) - before)).toBeLessThan(2);
});
