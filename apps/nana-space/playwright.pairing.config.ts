import base from "./playwright.v3.config";
import { defineConfig } from "@playwright/test";
export default defineConfig({
  ...base,
  testMatch: "pairing.spec.ts",
  reporter: "list",
  projects: [
    {
      name: "android-native-bridge-fixture",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  use: { ...base.use, trace: "off", video: "off", screenshot: "off" },
});
