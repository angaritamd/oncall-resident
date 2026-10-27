import { defineConfig } from "@playwright/test";

const brave = process.platform === "darwin" ? "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" : "/usr/bin/brave";

export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  // model answers take seconds (and a cold start up to the fallback threshold)
  expect: { timeout: 110_000 }, // above the core's 100 s whole-answer budget (cold start + fallback)
  // one worker: report and station tests share demo state (reports, station link) on the same login
  workers: 1,
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:3000",
    browserName: "chromium",
    // software WebGL so OHIF can render images in headless runs
    launchOptions: { executablePath: brave, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] },
    // local servers need an identity header; through tailscale serve it is set by Tailscale
    extraHTTPHeaders: process.env.E2E_LOGIN ? { "Tailscale-User-Login": process.env.E2E_LOGIN } : undefined,
  },
  projects: [
    { name: "mobile-390", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3 } },
    { name: "desktop", use: { viewport: { width: 1280, height: 800 } } },
  ],
});
