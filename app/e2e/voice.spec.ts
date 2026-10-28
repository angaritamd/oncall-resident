import path from "node:path";
import { chromium, expect, test, type Page, type TestInfo } from "@playwright/test";

// Voice end to end: the browser's fake microphone plays one synthetic TTS clip (e2e/audio, never a real voice),
// the app records WAV, the core transcribes it (TRANSCRIBE_PROVIDER) and the transcript runs as a chat
// instruction. Needs voice configured on the server (GET /api/voice/config → available).
test.describe.configure({ mode: "serial" });

const brave = process.platform === "darwin" ? "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" : "/usr/bin/brave";
const shots = "../docs/screenshots/after";

/** Each clip needs its own browser (the fake microphone file is a launch flag), with the project's device. */
async function withClip(file: string, info: TestInfo, run: (page: Page) => Promise<void>) {
  const browser = await chromium.launch({
    executablePath: brave,
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", `--use-file-for-fake-audio-capture=${path.resolve(__dirname, "audio", file)}`],
  });
  const { viewport, isMobile, hasTouch, deviceScaleFactor, baseURL, extraHTTPHeaders } = info.project.use;
  // E2E_VIDEO=1 records the walkthrough (the phone-size project is the delivery video)
  const recordVideo = process.env.E2E_VIDEO ? { dir: `${shots}/video`, size: { width: 390, height: 844 } } : undefined;
  const ctx = await browser.newContext({ viewport, isMobile, hasTouch, deviceScaleFactor, baseURL, extraHTTPHeaders, permissions: ["microphone"], recordVideo });
  try {
    await run(await ctx.newPage());
  } finally {
    await browser.close();
  }
}

async function reset(page: Page) {
  const r = await page.request.post("/api/demo/reset-reports", { headers: { origin: new URL(page.url()).origin } });
  expect(r.status(), "demo reset (DEMO_RESET_ENABLED + ADMIN_USERS)").toBe(200);
}

/** Tap the mic, let the clip play once (the clips end in 3 s of silence), tap again; returns the latency shown. */
async function speakClip(page: Page) {
  const mic = page.getByRole("button", { name: "Dictar por voz" });
  await expect(mic).toBeEnabled();
  await mic.click();
  await expect(page.getByRole("button", { name: "Detener y enviar" })).toBeVisible();
  await page.waitForTimeout(2600);
  await page.getByRole("button", { name: "Detener y enviar" }).click();
  const note = page.getByTestId("voice-note").last();
  await expect(note).toBeVisible({ timeout: 40_000 });
  const s = Number((await note.textContent())!.match(/([\d.]+) s/)![1]);
  return s;
}

const latencies: Record<string, number> = {};

test("voz · ¿qué tengo pendiente? → worklist answer, spoken reply can be muted", async ({}, info) => {
  await withClip("que-tengo-pendiente.wav", info, async (page) => {
    await page.goto("/");
    await reset(page);
    await page.reload();
    await expect(page.getByTestId("voice-disclaimer")).toHaveText("Demo: el audio se procesa en la API de Meta; no dictes datos reales.");
    latencies.pendiente = await speakClip(page);
    await expect(page.locator("main p", { hasText: /^Tú:/ }).last()).toContainText(/pendiente/i);
    await expect(page.getByRole("region", { name: /Siguiente estudio DEMO-0001/ }).last()).toBeVisible();
    // mute is visible and persists
    await page.getByRole("button", { name: "Silenciar respuestas habladas" }).click();
    await expect(page.getByRole("button", { name: "Activar respuestas habladas" })).toHaveAttribute("aria-pressed", "true");
    await page.screenshot({ path: `${shots}/${info.project.name}-10-voz-pendiente.png` });
  });
});

test("voz · abre el siguiente → opens the next study by the rule", async ({}, info) => {
  await withClip("abre-el-siguiente.wav", info, async (page) => {
    await page.goto("/");
    latencies.siguiente = await speakClip(page);
    await expect(page.locator("main p", { hasText: /^Tú:/ }).last()).toContainText(/siguiente/i);
    await expect(page.getByRole("region", { name: /^Caso DEMO-0001/ }).last()).toBeVisible();
    await expect(page.getByTestId("read-choice")).toBeVisible();
  });
});

test("voz · el nódulo mide 12 mm → dictation on the open draft; voice never signs", async ({}, info) => {
  test.setTimeout(300_000);
  await withClip("nodulo-12mm.wav", info, async (page) => {
    await page.goto("/");
    await reset(page);
    await page.reload();
    await page.getByRole("navigation").getByRole("button", { name: "Lista" }).click();
    await page.getByRole("button", { name: /^Abrir caso DEMO-0004/ }).click();
    await expect(page.getByRole("region", { name: "Borrador DEMO-0004" }).last()).toBeVisible();
    latencies.nodulo = await speakClip(page);
    await expect(page.locator("main p", { hasText: /^Tú:/ }).last()).toContainText(/n[oó]dulo/i);
    // whatever the model did with it, nothing is ever signed by voice
    await expect(page.getByText(/paso|sin herramientas/).last()).toBeVisible();
    const r = await page.request.get("/api/reports/DEMO-0004", { headers: { origin: new URL(page.url()).origin } });
    expect((await r.json()).status).toBe("draft");
    await page.screenshot({ path: `${shots}/${info.project.name}-11-voz-nodulo.png` });
    console.log(`VOICE ${info.project.name} ${JSON.stringify(latencies)}`);
  });
});
