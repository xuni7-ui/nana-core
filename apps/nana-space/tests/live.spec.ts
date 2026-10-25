import { test, expect } from "@playwright/test";
import { readFile, mkdir } from "node:fs/promises";
async function login(page: import("@playwright/test").Page) {
  const target = JSON.parse(
    await readFile(new URL("../.live-target.json", import.meta.url), "utf8"),
  );
  await page.goto("/?source=core#home");
  await page.getByLabel("预期 Subject ID").fill(target.subject_id);
  await page.getByLabel("本机开发会话口令").fill("qualification-only-access");
  await page.getByRole("button", { name: "验证并连接" }).click();
  await expect(
    page.getByText("DEV CORE · CONNECTED", { exact: true }),
  ).toBeVisible();
  return target.subject_id as string;
}
test("real owner feeds every page, returns Core dialogue and never mixes Demo stories", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const identity = await login(page);
  for (const route of [
    "home",
    "memories",
    "goals",
    "journal",
    "world",
    "growth",
    "devices",
    "runtime",
    "settings",
    "chat",
  ]) {
    await page.goto(`/?source=core#${route}`);
    await expect(page.locator(".core-identity")).toContainText(identity);
    await expect(page.locator("main h1").first()).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    await expect(page.locator("main")).not.toContainText(
      "把下一场流星雨留给我们",
    );
  }
  const input = page.getByRole("textbox", { name: "发送给真实开发 Core" });
  await expect(input).toBeInViewport();
  await input.fill("先别分析这个话题");
  await page.getByRole("button", { name: "发送给 Core", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText(
    "原 Core 已审阅",
  );
  await expect(page.locator(".message-nana").last()).toContainText(
    "这个话题先停在这里",
  );
  await expect(page.locator(".core-reply-meta").last()).toContainText(
    "消息元数据引用",
  );
  await expect(page.locator("main")).not.toContainText("演示回复");
  await mkdir("docs/previews/live", { recursive: true });
  await page.screenshot({
    path: `docs/previews/live/${info.project.name}-chat.png`,
    fullPage: true,
  });
  await page.goto("/?source=core#runtime");
  await page.screenshot({
    path: `docs/previews/live/${info.project.name}-runtime.png`,
    fullPage: true,
  });
  await page.reload();
  await expect(page.locator(".core-identity")).toContainText(identity);
  expect(errors).toEqual([]);
});
test("bad identity and unauthenticated sessions fail closed", async ({
  page,
}) => {
  const response = await page.request.get("/api/nana-space/v1/snapshot");
  expect(response.status()).toBe(401);
  await page.goto("/?source=core");
  await page.getByLabel("预期 Subject ID").fill("wrong-subject");
  await page.getByLabel("本机开发会话口令").fill("qualification-only-access");
  await page.getByRole("button", { name: "验证并连接" }).click();
  await expect(page.getByRole("alert")).toContainText("不匹配");
  await expect(
    page.getByText("DEV CORE · CONNECTED", { exact: true }),
  ).toHaveCount(0);
  await expect(page.getByLabel("本机开发会话口令")).toHaveValue("");
});
test("lost reply is verified through receipt without re-sending the real input", async ({
  page,
}) => {
  await login(page);
  await page.goto("/?source=core#chat");
  let posts = 0;
  page.on("request", (req) => {
    if (req.method() === "POST" && req.url().endsWith("/messages")) posts++;
  });
  await page.route("**/api/nana-space/v1/messages", async (route) => {
    await route.fetch();
    await route.abort();
  });
  await page
    .getByRole("textbox", { name: "发送给真实开发 Core" })
    .fill("先别分析");
  await page.getByRole("button", { name: "发送给 Core", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText("UNKNOWN");
  await page.route("**/api/nana-space/v1/receipts/*", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: { ...body, run_id: "1111111111111111" },
    });
  });
  await page.getByRole("button", { name: "核验原消息结果" }).click();
  await expect(page.getByRole("alert")).toContainText("旧消息不可重新发送");
  await page.unroute("**/api/nana-space/v1/receipts/*");
  await page.getByRole("button", { name: "核验原消息结果" }).click();
  await expect(page.locator(".message-user").last()).toContainText(
    "原 Core 已审阅",
  );
  expect(posts).toBe(1);
});
test("unavailable projection clears live data and never falls back to Demo", async ({
  page,
}) => {
  await login(page);
  await page.route("**/api/nana-space/v1/snapshot", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ code: "CORE_UNAVAILABLE" }),
    }),
  );
  await page.getByRole("button", { name: "刷新 Core 投影" }).click();
  await expect(page.getByRole("alert")).toContainText("原 Core owner 暂不可用");
  await expect(page.locator(".core-identity")).toHaveCount(0);
  await expect(page.getByText("DEMO 演示空间", { exact: true })).toHaveCount(0);
});
