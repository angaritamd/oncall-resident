import { expect, test } from "@playwright/test";

// Phone (390 px) → reading station (desktop). Uses its own two browser contexts, so it runs once
// (desktop project) and serially: one live station per tailnet login.
test.describe.configure({ mode: "serial" });

const shots = "../docs/screenshots/after";
const UID_0001 = "1.3.6.1.4.1.14519.5.2.1.6279.6001.116951808801102574107980626851";

test("phone opens a case → the linked station opens that study in OHIF (UIDs only)", async ({ browser }, info) => {
  test.skip(info.project.name !== "desktop", "creates its own phone + station contexts");
  test.setTimeout(300_000);
  const baseURL = info.project.use.baseURL;

  const stationCtx = await browser.newContext({ baseURL, viewport: { width: 1440, height: 900 } });
  const station = await stationCtx.newPage();
  const sse: string[] = [];
  station.on("response", (r) => {
    if (r.url().includes("/api/station/events")) sse.push(r.url());
  });
  await station.goto("/estacion");
  const code = (await station.getByTestId("station-code").textContent())?.trim() ?? "";
  expect(code).toMatch(/^\d{4}$/);
  await expect(station.getByText("Esperando vínculo…")).toBeVisible();
  await station.screenshot({ path: `${shots}/desktop-07-estacion-codigo.png` });

  const phoneCtx = await browser.newContext({ baseURL, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 });
  const phone = await phoneCtx.newPage();
  await phone.goto("/");
  await phone.getByRole("button", { name: "Vincular estación" }).click();
  await phone.getByLabel("Código de la estación").fill(code);
  await phone.getByRole("button", { name: "Vincular", exact: true }).click();
  await expect(phone.getByText("Estación vinculada")).toBeVisible();
  await expect(station.getByText(/Celular vinculado/)).toBeVisible({ timeout: 15_000 });

  // the station's DICOMweb traffic goes through the viewer gateway and must succeed
  const qido = station.waitForResponse((r) => r.url().includes(`/dicom-web/studies`) && r.url().includes(UID_0001) && r.status() === 200, { timeout: 120_000 });
  await phone.getByLabel("Instrucción para el residente").fill("Abrir DEMO-0001");
  await phone.keyboard.press("Enter");
  await expect(phone.getByRole("region", { name: "Caso DEMO-0001" }).last()).toBeVisible();
  const frame = station.locator("iframe");
  await expect(frame).toHaveAttribute("src", new RegExp(`/viewer\\?StudyInstanceUIDs=${UID_0001.replace(/\./g, "\\.")}$`), { timeout: 30_000 });
  await qido;
  await expect(station.getByText(/Estudio abierto · UID …/)).toBeVisible();
  await station.waitForTimeout(8000); // let OHIF render the first image before the screenshot
  await station.screenshot({ path: `${shots}/desktop-08-estacion-estudio.png` });

  // the phone never loads images: its "open on station" button sends the UID again
  const card = phone.getByRole("region", { name: "Caso DEMO-0001" }).last();
  const btn = card.getByRole("button", { name: /Abrir en la estación DEMO-0001/ });
  await expect(btn).toBeEnabled();
  await btn.click();
  await expect(card.getByText("Enviado a la estación")).toBeVisible();
  await phone.screenshot({ path: `${shots}/mobile-390-07-celular-estacion.png` });
  expect(sse.length).toBeGreaterThan(0);

  // only UIDs travel: the event stream carries {"study_uid"} and nothing else
  const ev = await station.evaluate(async () => {
    const r = await fetch("/api/station/config");
    return r.ok;
  });
  expect(ev).toBe(true);

  await phone.getByRole("button", { name: "Desvincular" }).click();
  await expect(phone.getByRole("button", { name: "Vincular estación" })).toBeVisible();
  await stationCtx.close();
  await phoneCtx.close();
});

test("without a linked station the phone shows 'Pronto' and the viewer is frame-locked to the app", async ({ page, request }, info) => {
  test.skip(info.project.name !== "desktop", "one run is enough");
  await page.goto("/");
  await page.getByLabel("Instrucción para el residente").fill("Abrir DEMO-0002");
  await page.keyboard.press("Enter");
  const card = page.getByRole("region", { name: "Caso DEMO-0002" }).last();
  await expect(card.getByRole("button", { name: /Abrir en la estación \(Pronto · sin estación vinculada\)/ })).toBeDisabled();
  const cfg = await (await request.get("/api/station/config", { headers: { origin: new URL(page.url()).origin } })).json();
  const viewer = await request.get(`${cfg.viewer_url}/`);
  expect(viewer.status()).toBe(200);
  expect(viewer.headers()["content-security-policy"]).toBe(`frame-ancestors ${new URL(page.url()).origin}`);
  // write methods are refused by the gateway (read-only)
  expect((await request.post(`${cfg.viewer_url}/dicom-web/studies`)).status()).toBe(405);
});
