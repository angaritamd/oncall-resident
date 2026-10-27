// Renders the R monogram icons and iOS splash screens with Playwright (Brave). Run: node scripts/gen-icons.mjs

import { chromium } from "@playwright/test";
import { existsSync } from "node:fs";

// BRAVE_PATH overrides; otherwise the first known install location that exists.
const brave = [
  process.env.BRAVE_PATH,
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
  "/usr/bin/brave",
  "/usr/bin/brave-browser",
  "/opt/brave.com/brave/brave",
].find((p) => p && existsSync(p));
if (!brave) throw new Error("Brave not found; set BRAVE_PATH");
const font = `font-family: Inter, system-ui, -apple-system, Helvetica, Arial, sans-serif;`;

// rounded = regular icon; full-bleed = maskable (glyph kept inside the 80% safe zone)
const icon = (size, { maskable = false, radius = 0.22 } = {}) => `
<body style="margin:0;background:transparent">
  <div style="width:${size}px;height:${size}px;background:#0E1116;border-radius:${maskable ? 0 : size * radius}px;
    display:flex;align-items:center;justify-content:center;${font}color:#F3F5F7;font-weight:500;
    font-size:${size * (maskable ? 0.38 : 0.47)}px;letter-spacing:-0.02em;line-height:1">R</div>
</body>`;

const splash = (w, h) => `
<body style="margin:0;width:${w}px;height:${h}px;background:#E9ECF0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:${w * 0.05}px;${font}">
  <div style="width:${w * 0.22}px;height:${w * 0.22}px;border-radius:${w * 0.05}px;background:#0E1116;color:#F3F5F7;
    display:flex;align-items:center;justify-content:center;font-weight:500;font-size:${w * 0.1}px;line-height:1">R</div>
  <div style="color:#0E1116;font-weight:300;font-size:${w * 0.075}px;letter-spacing:-0.03em">Residente</div>
</body>`;

const jobs = [
  ["public/icons/icon-192.png", 192, icon(192)],
  ["public/icons/icon-512.png", 512, icon(512)],
  ["public/icons/maskable-192.png", 192, icon(192, { maskable: true })],
  ["public/icons/maskable-512.png", 512, icon(512, { maskable: true })],
  ["public/icons/apple-touch-icon.png", 180, icon(180, { maskable: true })], // iOS applies its own mask
];
const splashes = [
  [390, 844],
  [393, 852],
  [430, 932],
  [375, 812],
];

const browser = await chromium.launch({ executablePath: brave });
const page = await browser.newPage();
for (const [path, size, html] of jobs) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(html);
  await page.screenshot({ path, omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
}
for (const [w, h] of splashes) {
  const p = await browser.newPage({ viewport: { width: w * 3, height: h * 3 } });
  await p.setContent(splash(w * 3, h * 3));
  await p.screenshot({ path: `public/splash/splash-${w * 3}x${h * 3}.png` });
  await p.close();
}
await browser.close();
console.log("icons and splash written");
