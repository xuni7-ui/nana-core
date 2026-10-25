import { test, expect } from "@playwright/test";
import { readFile, mkdir } from "node:fs/promises";
const targetPath = process.env.NANA_V2_TARGET!;
test("v2 actual same Core ten pages, scoped dialogue, cookies, revoke and host lifecycle", async ({
  page,
}, info) => {
  const target = JSON.parse(await readFile(targetPath, "utf8"));
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/index.html?source=live#home");
  await page.getByLabel("Subject ID", { exact: true }).fill(target.subject_id);
  await page
    .getByLabel("会话口令", { exact: true })
    .fill("TEST_ONLY_NOT_SECRET_web_password");
  await page.getByRole("button", { name: "安全连接", exact: true }).click();
  await expect(page.locator(".live-identity")).toContainText(target.subject_id);
  const cookies = await page.context().cookies();
  expect(cookies.find((c) => c.name === "__Host-nana_v2")).toMatchObject({
    httpOnly: true,
    secure: true,
    sameSite: "Strict",
  });
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
    await page.goto("/index.html?source=live#" + route);
    await expect(page.locator(".live-identity")).toContainText(
      target.subject_id,
    );
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
  await page.getByLabel("和奈奈说点什么").fill("先别分析这个话题");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  await expect(page.locator(".live-reply")).toContainText("VERIFIED");
  await expect(page.locator(".live-reply")).toContainText("这个话题先停在这里");
  await expect(page.locator(".live-reply")).toContainText(
    "TOPIC_BOUNDARY_NO_MODEL_CALL",
  );
  expect(
    await page.evaluate(() =>
      Object.entries(localStorage).some(([k, v]) =>
        /token|password|secret|refresh/i.test(k + v),
      ),
    ),
  ).toBe(false);
  await mkdir("docs/previews/v2", { recursive: true });
  await page.screenshot({
    path: `docs/previews/v2/${info.project.name}-chat.png`,
    fullPage: true,
  });
  await page.reload();
  await expect(page.locator(".live-identity")).toContainText(target.subject_id);
  await expect(page.locator(".live-turn")).toHaveCount(0); // no private browser cache/replay
  await page.getByRole("button", { name: "退出并清除本机视图" }).click();
  await expect(page.getByLabel("Subject ID", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Subject ID", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
