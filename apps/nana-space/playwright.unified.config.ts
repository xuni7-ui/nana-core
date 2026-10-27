import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "unified.spec.ts",
  workers: 1,
  retries: 0,
  timeout: 45000,
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/unified-report.json" }],
  ],
  use: {
    baseURL: "https://127.0.0.1:18445",
    ignoreHTTPSErrors: true,
    headless: true,
    launchOptions: {
      executablePath: "/usr/bin/chromium",
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    },
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    ...[360, 390, 412].map((width) => ({
      name: `phone-${width}`,
      use: { viewport: { width, height: 844 }, isMobile: true, hasTouch: true },
    })),
  ],
});
