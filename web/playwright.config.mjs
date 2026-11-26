import { defineConfig } from "@playwright/test";

// The tests run against the PRODUCTION build (with its strict CSP) in your installed Google Chrome,
// so no browser has to be downloaded. `npm run e2e` builds, serves it on :4173 and runs everything.
export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 60_000 },
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:4173", channel: process.env.CI ? undefined : "chrome" /* CI: Playwright's own Chromium */, headless: true, viewport: { width: 1100, height: 900 } },
  webServer: { command: "npm run build && npm run preview", url: "http://localhost:4173", reuseExistingServer: true, timeout: 240_000 },
});
