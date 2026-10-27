import { test, expect } from "@playwright/test";
import { readFile, mkdir } from "node:fs/promises";
test("V3 real Core provider configuration, model route and backup receipt projection", async ({
  page,
}, info) => {
  const target = JSON.parse(
    await readFile(process.env.NANA_V2_TARGET!, "utf8"),
  );
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const results: any[] = [];
  page.on("response", async (r) => {
    if (r.url().endsWith("/providers/commands")) results.push(await r.json());
  });
  await page.goto("/index.html?source=live#models");
  await page.getByLabel("Subject ID", { exact: true }).fill(target.subject_id);
  await page
    .getByLabel("会话口令", { exact: true })
    .fill("TEST_ONLY_NOT_SECRET_web_password");
  await page.getByRole("button", { name: "安全连接", exact: true }).click();
  await expect(
    page.getByText("宿主已开放配置", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "添加供应商草稿", exact: true })
    .click();
  const suffix = info.project.name.replaceAll("-", "");
  await page
    .getByLabel("供应商配置 ID", { exact: true })
    .fill(`provider.${suffix}`);
  await page.getByLabel("模型配置 ID", { exact: true }).fill(`model.${suffix}`);
  await page
    .getByLabel("已确认的 Base URL", { exact: true })
    .fill("https://provider.example/v1");
  await page
    .getByLabel("远端 Model ID", { exact: true })
    .fill("synthetic.declared.not.called");
  await page.getByRole("button", { name: "应用新供应商", exact: true }).click();
  await expect.poll(() => results.length).toBe(1);
  expect(results[0].data.state).toBe("VERIFIED");
  await expect(
    page.getByRole("button", { name: "注册模型配置", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "注册模型配置", exact: true }).click();
  await expect.poll(() => results.length).toBe(2);
  expect(results[1].data.state).toBe("VERIFIED");
  await page.getByLabel("关闭供应商草稿", { exact: true }).click();
  const panel = page
    .locator(".v3-capability-card")
    .filter({
      has: page.getByRole("heading", { name: "文本与推理", exact: true }),
    });
  await panel.locator("summary").click();
  await panel
    .getByLabel("文本与推理 Primary", { exact: true })
    .selectOption(`model.${suffix}`);
  await panel.getByRole("button", { name: "应用此路由", exact: true }).click();
  await expect.poll(() => results.length).toBe(3);
  expect(results[2].data.state).toBe("VERIFIED");
  expect(
    results.every(
      (r) =>
        r.data.result.network_calls === 0 &&
        r.data.result.live_permission_granted === false,
    ),
  ).toBe(true);
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    )
    .toBe(true);
  await mkdir("test-results/unified-screens", { recursive: true });
  await page.screenshot({
    path: `test-results/unified-screens/${info.project.name}-models.png`,
    fullPage: true,
  });
  await page.goto("/index.html?source=live#backup");
  await expect(
    page.getByText("服务端回执投影", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("NOT_OBSERVED", { exact: false }).first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(() =>
      Object.entries(localStorage).some(([k, v]) =>
        /token|password|secret|refresh/i.test(k + v),
      ),
    ),
  ).toBe(false);
});
