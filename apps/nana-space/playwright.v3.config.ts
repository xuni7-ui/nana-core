import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "v3.spec.ts",
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: [["list"], ["json", { outputFile: "test-results/v3-report.json" }]],
  use: {
    baseURL: "http://127.0.0.1:14173",
    headless: true,
    launchOptions: {
      executablePath: "/usr/bin/chromium",
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    },
  },
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 14173",
    url: "http://127.0.0.1:14173",
    reuseExistingServer: false,
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    ...[360, 390, 412].map((width) => ({
      name: `phone-${width}`,
      use: { viewport: { width, height: 844 }, isMobile: true, hasTouch: true },
    })),
  ],
});
