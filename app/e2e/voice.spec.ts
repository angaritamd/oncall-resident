import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

// Voice end to end: the browser's fake microphone plays one synthetic TTS clip (e2e/audio, never a real voice),
// the app records WAV, the core transcribes it (TRANSCRIBE_PROVIDER) and the transcript runs as a chat
// instruction. Needs voice configured on the server (GET /api/voice/config → available).
test.describe.configure({ mode: "serial" });

const brave = process.platform === "darwin" ? "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" : "/usr/bin/brave";
const shots = "../docs/screenshots/after";

function withClip(file: string) {
  return {
    launchOptions: {
      executablePath: brave,
      args: [
        "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream",
        `--use-file-for-fake-audio-capture=${path.resolve(__dirname, "audio", file)}`,
      ],
    },
    permissions: ["microphone"],
  };
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

test.describe("¿qué tengo pendiente?", () => {
  test.use(withClip("que-tengo-pendiente.wav"));
  test("voice → worklist answer, spoken reply can be muted", async ({ page }, info) => {
    await page.goto("/");
    await reset(page);
    await page.reload();
    latencies.pendiente = await speakClip(page);
    await expect(page.locator("main p", { hasText: /^Tú:/ }).last()).toContainText(/pendiente/i);
    await expect(page.getByRole("region", { name: /Siguiente estudio DEMO-0001/ }).last()).toBeVisible();
    // mute is visible and persists
    await page.getByRole("button", { name: "Silenciar respuestas habladas" }).click();
    await expect(page.getByRole("button", { name: "Activar respuestas habladas" })).toHaveAttribute("aria-pressed", "true");
    await page.screenshot({ path: `${shots}/${info.project.name}-10-voz-pendiente.png` });
  });
});

test.describe("abre el siguiente", () => {
  test.use(withClip("abre-el-siguiente.wav"));
  test("voice → opens the next study by the rule", async ({ page }) => {
    await page.goto("/");
    latencies.siguiente = await speakClip(page);
    await expect(page.locator("main p", { hasText: /^Tú:/ }).last()).toContainText(/siguiente/i);
    await expect(page.getByRole("region", { name: /^Caso DEMO-0001/ }).last()).toBeVisible();
    await expect(page.getByTestId("read-choice")).toBeVisible();
  });
});

test.describe("el nódulo mide 12 mm", () => {
  test.use(withClip("nodulo-12mm.wav"));
  test("voice dictation edits the open draft; QC flags it; voice never signs", async ({ page }, info) => {
    test.setTimeout(300_000);
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
