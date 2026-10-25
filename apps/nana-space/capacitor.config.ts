import type { CapacitorConfig } from "@capacitor/cli";
const config: CapacitorConfig = {
  appId: "life.nana.space",
  appName: "奈奈 · Nana Space",
  webDir: "dist",
  loggingBehavior: "none",
  backgroundColor: "#111226",
  android: { allowMixedContent: false, webContentsDebuggingEnabled: false },
  server: { androidScheme: "https", allowNavigation: [] },
};
export default config;
