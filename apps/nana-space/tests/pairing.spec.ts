/** Native bridge fixture only. Pairing material is generated in browser memory,
 * never a user's code or a real server request; no trace/video/screenshots. */
import { test, expect } from "@playwright/test";
test("native pairing can submit, explains invalid input and network errors, then opens chat", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const w = window as any;
    w.androidBridge = {};
    w.pairCalls = 0;
    w.pairFails = true;
    const envelope = () => ({
      contract: "nana-space-live/v2",
      realm: "PRODUCTION_SINGLE_SUBJECT",
      execution_authority: false,
      subject_id: "8acff4fb-2532-4a97-a4b7-e59e2ae2f797",
      lineage_binding: "a".repeat(64),
      owner_epoch: 1,
      as_of_us: 1,
      revision: 1,
      session_generation: 1,
      run_generation: "b".repeat(32),
      coverage: "NO_DATA",
      privacy_scope: ["PUBLIC", "PROJECT"],
      source_refs: [],
      capabilities: {},
      data: { roles: ["READER", "CONVERSATION"] },
    });
    w.Capacitor = {
      PluginHeaders: [
        {
          name: "NanaHost",
          methods: ["status", "launchRoute", "pair", "call"].map((name) => ({
            name,
            rtype: "promise",
          })),
        },
      ],
      nativePromise: async (_p: string, method: string, data: any) => {
        if (method === "status") return { paired: false };
        if (method === "launchRoute") return { page: "home" };
        if (method === "pair") {
          w.pairCalls++;
          w.pairFieldsValid =
            data.base === "https://nana-core-host.tail62e848.ts.net:8443" &&
            data.subject_id === "8acff4fb-2532-4a97-a4b7-e59e2ae2f797" &&
            data.device_name === "这台安卓手机" &&
            data.code.length >= 24;
          if (w.pairFails) throw new Error("NETWORK_OR_EXECUTION_UNKNOWN");
          return envelope();
        }
        return envelope();
      },
    };
  });
  await page.goto("/index.html?source=live");
  const button = page.getByRole("button", { name: "安全连接", exact: true });
  await expect(button).toBeEnabled();
  await button.tap();
  await expect(page.getByRole("alert")).toContainText("Subject ID");
  await page
    .getByLabel("私有 HTTPS 地址", { exact: true })
    .fill("https://nana-core-host.tail62e848.ts.net:8443");
  await page
    .getByLabel("Subject ID", { exact: true })
    .fill("8acff4fb-2532-4a97-a4b7-e59e2ae2f797");
  await page.getByLabel("手机名称", { exact: true }).fill("这台安卓手机");
  await button.tap();
  await expect(page.getByRole("alert")).toContainText("24–128");
  expect(await page.evaluate(() => (window as any).pairCalls)).toBe(0);
  const ephemeralInput = async () =>
    page.evaluate(() => {
      const input = document.querySelector<HTMLInputElement>(
        'input[aria-label="一次性配对码"]',
      )!;
      const material = Array.from(
        crypto.getRandomValues(new Uint8Array(24)),
        (v) => v.toString(16).padStart(2, "0"),
      ).join("");
      Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype,
        "value",
      )!.set!.call(input, material);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  await ephemeralInput();
  await expect(button).toBeEnabled();
  await button.tap();
  await expect(page.getByRole("alert")).toContainText("Tailscale");
  expect(await page.evaluate(() => (window as any).pairCalls)).toBe(1);
  expect(await page.evaluate(() => (window as any).pairFieldsValid)).toBe(true);
  await page.evaluate(() => ((window as any).pairFails = false));
  await ephemeralInput();
  await button.tap();
  await expect(page).toHaveURL(/#chat$/);
  expect(await page.evaluate(() => (window as any).pairCalls)).toBe(2);
});
