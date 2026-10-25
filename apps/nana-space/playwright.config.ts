import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

export default defineConfig({
  testDir: "./tests",
  testMatch: "space.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/e2e-report.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
    headless: true,
    launchOptions: {
      executablePath:
        process.env.NANA_BROWSER_PATH ||
        (existsSync("/usr/bin/chromium") ? "/usr/bin/chromium" : undefined),
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "zh-CN",
    timezoneId: "Asia/Shanghai",
  },
  webServer: {
    command: "npm run build && npm run preview -- --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    {
      name: "android",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 1,
      },
    },
    {
      name: "small-phone",
      use: {
        viewport: { width: 320, height: 740 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 1,
      },
    },
    {
      name: "tablet",
      use: {
        viewport: { width: 768, height: 1024 },
        hasTouch: true,
        deviceScaleFactor: 1,
      },
    },
    {
      name: "landscape",
      use: {
        viewport: { width: 844, height: 390 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 1,
      },
    },
  ],
});
