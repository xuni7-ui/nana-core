import { test, expect, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const routes = [
  ["home", "生活空间"],
  ["chat", "和奈奈聊聊"],
  ["memories", "共同记忆"],
  ["goals", "小小计划"],
  ["journal", "生活手记"],
  ["world", "世界与发现"],
  ["growth", "成长轨迹"],
  ["devices", "连接的世界"],
  ["runtime", "运行与边界"],
  ["settings", "空间设置"],
] as const;

async function visit(page: Page, route: string) {
  await page.goto(`/#${route}`);
  await expect(page.locator("main")).toBeVisible();
  await expect(page.locator("main h1").first()).toBeVisible();
}

async function noHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    width: window.innerWidth,
    body: document.body.scrollWidth,
    html: document.documentElement.scrollWidth,
  }));
  expect(dimensions.body, JSON.stringify(dimensions)).toBeLessThanOrEqual(
    dimensions.width + 1,
  );
  expect(dimensions.html, JSON.stringify(dimensions)).toBeLessThanOrEqual(
    dimensions.width + 1,
  );
}

async function scenario(page: Page, value: string) {
  await visit(page, "settings");
  await page.getByLabel("选择演示场景").selectOption(value);
  await page.waitForTimeout(value === "slow" ? 2500 : 350);
}

test("all product routes render meaningful content without errors or horizontal overflow", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mkdir(resolve("docs/previews"), { recursive: true });
  for (const [route] of routes) {
    await visit(page, route);
    await noHorizontalOverflow(page);
    await expect(page.locator("main")).not.toContainText(
      "这间小房间还在布置中",
    );
    if (
      (["desktop", "android"].includes(testInfo.project.name) &&
        ["home", "chat", "world", "settings"].includes(route)) ||
      route === "home"
    ) {
      await page.screenshot({
        path: resolve(`docs/previews/${testInfo.project.name}-${route}.png`),
        fullPage: true,
        animations: "disabled",
      });
    }
  }
  expect(errors).toEqual([]);
});

test("shared memories support search, correction and withdrawal provenance", async ({
  page,
}) => {
  await visit(page, "memories");
  const search = page.getByRole("textbox", { name: "搜索记忆、主题或来源…" });
  await search.fill("流星雨");
  await expect(
    page.getByRole("heading", { name: "把下一场流星雨留给我们" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "小房间里的第一盏灯" }),
  ).toHaveCount(0);
  await search.fill("zz-no-record-274");
  await expect(page.getByText("这里暂时没有匹配的记忆")).toBeVisible();
  await page.getByRole("button", { name: "清空搜索" }).click();
  const withdrawn = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", { name: "一条已撤回的共享记录" }),
    })
    .last();
  await expect(withdrawn).toContainText("来源已撤回，正文不再呈现");
  await expect(page.getByText("已纠正", { exact: true })).toBeVisible();
});

test("goal controls remain local demo and UNKNOWN never exposes retry", async ({
  page,
}) => {
  await visit(page, "goals");
  const goal = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", { name: "为下一次观星做一点准备" }),
    })
    .last();
  await goal.getByRole("button", { name: "演示暂停", exact: true }).click();
  await expect(goal).toContainText("暂时放下");
  await goal.getByRole("button", { name: "演示恢复", exact: true }).click();
  await expect(goal).toContainText("正在继续");
  const unknown = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", { name: "确认共享星图是否已保存" }),
    })
    .last();
  await unknown.locator("summary").click();
  await expect(unknown).toContainText("UNKNOWN 不等于失败");
  await expect(
    unknown.getByRole("button", { name: /重试|恢复|重新执行/ }),
  ).toHaveCount(0);
  const blocked = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: "看看今晚窗外的云" }) })
    .last();
  await expect(blocked).toContainText("想继续");
  const declined = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: "每天固定写一份日记" }) })
    .last();
  await expect(declined).toContainText("选择不做");
});

test("demo chat streams and preserves message boundaries", async ({ page }) => {
  await visit(page, "chat");
  const message = page.getByRole("textbox", { name: "给奈奈的消息" });
  await message.fill("一起看看今晚的星空");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(
    page.getByText("一起看看今晚的星空", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("流式演示中", { exact: false })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "发送消息", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".message-nana").last()).toContainText(
    "这是本地预设的演示文本",
  );
  await expect(page.getByText("流式演示中", { exact: false })).toHaveCount(0);
  await expect(page.locator(".message-user").last()).toContainText(
    "已送达演示适配器",
  );
  await noHorizontalOverflow(page);
});

test("local theme, motion and scale survive refresh", async ({ page }) => {
  await visit(page, "settings");
  await page.getByRole("button", { name: /晨间薄雾/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("switch", { name: "轻柔动效" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-motion", "reduced");
  await page
    .getByRole("combobox", { name: "字体与界面缩放" })
    .selectOption("1.1");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.getByRole("switch", { name: "轻柔动效" })).toHaveAttribute(
    "aria-checked",
    "false",
  );
  await expect(
    page.getByRole("combobox", { name: "字体与界面缩放" }),
  ).toHaveValue("1.1");
  await noHorizontalOverflow(page);
});

test("research uncertainty and device limits remain inspectable", async ({
  page,
}) => {
  await visit(page, "world");
  const research = page
    .locator("section")
    .filter({
      has: page.getByRole("heading", { name: "秋天，什么时候最适合看星星？" }),
    })
    .last();
  await research.locator("summary").click();
  await expect(research).toContainText("气象来源 A（虚构）");
  await expect(research).toContainText("气象来源 B（虚构）");
  await expect(research).toContainText("暂不承诺最佳时段");
  await visit(page, "devices");
  const camera = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: "摄像头", exact: true }) })
    .last();
  await camera.locator("summary").click();
  await expect(camera).toContainText("正式主机绑定");
  await expect(
    camera.getByRole("button", { name: /连接设备|开启摄像头|立即授权/ }),
  ).toHaveCount(0);
});

test("search dialog supports keyboard focus, navigation and escape", async ({
  page,
}, testInfo) => {
  await visit(page, "home");
  await page.keyboard.press("Control+k");
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const search = dialog.getByRole("textbox", { name: "搜索页面、记忆或计划" });
  await expect(search).toBeFocused();
  await search.fill("共同记忆");
  await dialog.getByRole("button", { name: /共同记忆/ }).click();
  await expect(page).toHaveURL(/#memories$/);
  await expect(dialog).toHaveCount(0);
  await page.keyboard.press("Control+k");
  await expect(dialog).toBeVisible();
  for (let index = 0; index < 5; index++) await page.keyboard.press("Tab");
  expect(
    await dialog.evaluate((element) =>
      element.contains(document.activeElement),
    ),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  if (["android", "small-phone"].includes(testInfo.project.name)) {
    await page
      .getByRole("button", { name: "打开导航菜单", exact: true })
      .click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "打开导航菜单", exact: true }),
    ).toBeFocused();
  }
});

test("Inspector import rejects malformed, privileged and mismatched snapshots", async ({
  page,
}) => {
  await visit(page, "runtime");
  const input = page.getByLabel("导入只读 Inspector JSON");
  async function upload(value: unknown) {
    await input.setInputFiles({
      name: "inspection.json",
      mimeType: "application/json",
      buffer: Buffer.from(
        typeof value === "string" ? value : JSON.stringify(value),
      ),
    });
  }
  const valid = {
    schema_version: 1,
    derived: true,
    read_only: true,
    identity_id: "test:e2e:subject-one",
    as_of_us: 1_792_800_000_000_000,
    coverage: "BOUNDED_METADATA_ONLY",
    governance_visibility: "LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE",
    execution_authority: false,
    sections: {
      runtime: [
        {
          category: "RUNTIME",
          reference: "test:runtime:metadata",
          state: "UNKNOWN",
          record_id: null,
          as_of_us: null,
          source_memory_ids: [],
        },
      ],
    },
    resources: { VmRSS: 42000, Threads: 1 },
    self_view: { private_content: "PRIVATE_SENTINEL_MUST_NOT_RENDER" },
    advanced_life: { reasoning: "INTERNAL_SENTINEL_MUST_NOT_RENDER" },
  };
  await upload("{malformed json");
  await expect(page.getByText(/快照未载入|导入被拒绝/).first()).toBeVisible();
  await expect(
    page.getByText("test:e2e:subject-one", { exact: true }),
  ).toHaveCount(0);
  await upload({ ...valid, execution_authority: true });
  await expect(page.getByText(/快照未载入|导入被拒绝/).first()).toBeVisible();
  await expect(
    page.getByText("test:e2e:subject-one", { exact: true }),
  ).toHaveCount(0);
  await upload(valid);
  await expect(
    page.getByText("test:e2e:subject-one", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText(
    "PRIVATE_SENTINEL_MUST_NOT_RENDER",
  );
  await expect(page.locator("body")).not.toContainText(
    "INTERNAL_SENTINEL_MUST_NOT_RENDER",
  );
  await expect(page.locator("body")).toContainText("静态快照，非实时状态");
  await upload({ ...valid, identity_id: "test:e2e:subject-two" });
  await expect(page.getByText(/快照未载入|导入被拒绝/).first()).toBeVisible();
  await expect(
    page.getByText("test:e2e:subject-two", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByText("test:e2e:subject-one", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "清除快照" }).click();
  await expect(page.getByText("还没有载入快照", { exact: true })).toBeVisible();
  await expect(
    page.getByText("test:e2e:subject-one", { exact: true }),
  ).toHaveCount(0);
});

test("error, offline, partial and recovery scenarios communicate their limits", async ({
  page,
}) => {
  await scenario(page, "partial");
  await page.goto("/#home");
  await expect(page.locator("body")).toContainText(/部分|缺失|不可用/);
  await noHorizontalOverflow(page);
  await scenario(page, "offline");
  await page.goto("/#chat");
  await expect(page.locator("body")).toContainText(/离线|断开|中断/);
  const message = page.getByRole("textbox", { name: "给奈奈的消息" });
  await message.fill("这是离线发送检查");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText("发送失败");
  await expect(
    page.getByRole("button", { name: "重试演示消息" }),
  ).toBeVisible();
  await scenario(page, "restart");
  await page.goto("/#chat");
  await page
    .getByRole("textbox", { name: "给奈奈的消息" })
    .fill("检查恢复中的消息");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText(
    "送达状态未知",
  );
  await expect(
    page.locator(".message-user").last().getByRole("button", { name: /重试/ }),
  ).toHaveCount(0);
  await scenario(page, "error");
  await expect(page.locator("body")).toContainText(
    /加载失败|加载遇到|加载错误/,
  );
});

test("attachments survive additions, release on removal and remain local metadata after sending", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const create = URL.createObjectURL.bind(URL),
      revoke = URL.revokeObjectURL.bind(URL);
    const active = new Set<string>();
    Object.assign(window, { __nanaObjectURLs: active });
    URL.createObjectURL = (blob: Blob) => {
      const url = create(blob);
      active.add(url);
      return url;
    };
    URL.revokeObjectURL = (url: string) => {
      active.delete(url);
      revoke(url);
    };
  });
  await visit(page, "chat");
  const upload = page.locator(".composer-tools input[type=file]");
  const pixel = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3ioAAAAASUVORK5CYII=",
    "base64",
  );
  for (const name of ["one.png", "two.png", "three.png"])
    await upload.setInputFiles({ name, mimeType: "image/png", buffer: pixel });
  await expect(page.locator(".attachment-preview img")).toHaveCount(3);
  await expect
    .poll(() =>
      page
        .locator(".attachment-preview img")
        .evaluateAll((images) =>
          images.every((img) => (img as HTMLImageElement).naturalWidth > 0),
        ),
    )
    .toBe(true);
  await page.getByRole("button", { name: "移除 two.png" }).click();
  await expect(page.locator(".attachment-preview img")).toHaveCount(2);
  await expect
    .poll(() =>
      page
        .locator(".attachment-preview img")
        .evaluateAll((images) =>
          images.every((img) => (img as HTMLImageElement).naturalWidth > 0),
        ),
    )
    .toBe(true);
  await page
    .getByRole("textbox", { name: "给奈奈的消息" })
    .fill("分享两张本地图片");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText("one.png");
  await expect(page.locator(".message-user").last()).toContainText("three.png");
  await expect(page.locator(".message-user").last()).toContainText("未上传");
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as unknown as { __nanaObjectURLs: Set<string> })
            .__nanaObjectURLs.size,
      ),
    )
    .toBe(0);
  await upload.setInputFiles({
    name: "leave.png",
    mimeType: "image/png",
    buffer: pixel,
  });
  await page.goto("/#home");
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as unknown as { __nanaObjectURLs: Set<string> })
            .__nanaObjectURLs.size,
      ),
    )
    .toBe(0);
});

test("input length, failed retry and UNKNOWN preserve clear message semantics", async ({
  page,
}) => {
  await visit(page, "chat");
  const input = page.getByRole("textbox", { name: "给奈奈的消息" });
  await expect(input).toHaveAttribute("maxlength", "8000");
  await input.fill("长".repeat(8000));
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText(
    "长".repeat(8000),
  );
  await expect(page.locator(".message-user").last()).toContainText(
    "已送达演示适配器",
  );
  await noHorizontalOverflow(page);
  await scenario(page, "offline");
  await page.goto("/#chat");
  await expect(page.locator(".scenario-banner")).toContainText("连接中断");
  const count = await page.locator(".message-user").count();
  await input.fill("请保留这条失败消息");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText("发送失败");
  await page.getByRole("button", { name: "重试演示消息" }).click();
  await expect(page.locator(".message-user").last()).toContainText(
    "请保留这条失败消息",
  );
  await expect(page.locator(".message-user").last()).toContainText("发送失败");
  await expect(page.locator(".message-user")).toHaveCount(count + 1);
});

test("quiet days have no fabricated sharing and quiet preference suppresses optional notices", async ({
  page,
}) => {
  await scenario(page, "quiet");
  await page.goto("/#home");
  await expect(page.locator(".scenario-banner")).toContainText("安静的几天");
  await expect(page.locator(".nana-note")).toContainText("留一点安静的空白");
  await expect(page.locator(".notification-button i")).toHaveCount(0);
  await page.getByRole("button", { name: "打开分享与通知" }).click();
  await expect(page.getByRole("dialog")).toContainText("此刻，没有新的分享");
  await page.keyboard.press("Escape");
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(page.locator(".toast")).toHaveCount(0);
  await page.goto("/#settings");
  await page.getByRole("switch", { name: "安静模式" }).click();
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(page.locator(".toast")).toContainText("网络已恢复");
});

test("light theme, 120 percent zoom and reduced motion keep key pages readable", async ({
  page,
}, testInfo) => {
  await visit(page, "settings");
  await page.getByRole("button", { name: /晨间薄雾/ }).click();
  await page
    .getByRole("combobox", { name: "字体与界面缩放" })
    .selectOption("1.2");
  await page.getByRole("switch", { name: "轻柔动效" }).click();
  for (const route of ["home", "chat", "memories", "runtime", "settings"]) {
    await page.goto(`/#${route}`);
    await expect(page.locator("main h1").first()).toBeVisible();
    await noHorizontalOverflow(page);
    const contrast = await page
      .locator("main h1")
      .first()
      .evaluate((el) => {
        const heading = getComputedStyle(el).color;
        const background = getComputedStyle(
          document.querySelector(".app-shell")!,
        ).backgroundColor;
        const luminance = (color: string) => {
          const channels = (color.match(/\d+(?:\.\d+)?/g) || [])
            .slice(0, 3)
            .map(Number)
            .map((v) => {
              const c = v / 255;
              return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
            });
          return (
            channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
          );
        };
        const fg = luminance(heading),
          bg = luminance(background);
        return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
      });
    expect(contrast, "light-theme title contrast").toBeGreaterThanOrEqual(4.5);
  }
  if (["desktop", "android"].includes(testInfo.project.name))
    await page.screenshot({
      path: resolve(`docs/previews/${testInfo.project.name}-light-120.png`),
      fullPage: true,
      animations: "disabled",
    });
  await page.goto("/#chat");
  const composer = page.getByRole("textbox", { name: "给奈奈的消息" });
  await expect(composer).toBeInViewport();
  await expect(
    page.getByRole("button", { name: "发送消息", exact: true }),
  ).toBeInViewport();
});

test("switching scenes cancels pending streams and delayed projections", async ({
  page,
}) => {
  await visit(page, "chat");
  await page
    .getByRole("textbox", { name: "给奈奈的消息" })
    .fill("这条消息不应进入另一个演示场景");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await scenario(page, "quiet");
  await page.goto("/#chat");
  await expect(page.locator(".scenario-banner")).toContainText("安静的几天");
  await expect(page.locator("main")).not.toContainText(
    "这条消息不应进入另一个演示场景",
  );
  await page.goto("/#settings");
  await page.getByLabel("选择演示场景").selectOption("slow");
  await expect(
    page.getByRole("status").filter({ hasText: "正在轻轻推开" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "返回日常", exact: true }).click();
  await expect(page.locator(".scenario-banner")).toHaveCount(0);
  await expect(page.locator("main h1").first()).toBeVisible();
});

test("clearing a snapshot cancels an in-flight import without restoring old authority", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const read = File.prototype.text;
    File.prototype.text = async function () {
      if (this.name === "slow.json")
        await new Promise((resolve) => setTimeout(resolve, 500));
      return read.call(this);
    };
  });
  await visit(page, "runtime");
  const snapshot = {
    schema_version: 1,
    derived: true,
    read_only: true,
    identity_id: "test:clear-race",
    as_of_us: 1792800000000000,
    coverage: "BOUNDED_METADATA_ONLY",
    governance_visibility: "LOCAL_METADATA_NOT_RECIPIENT_DISCLOSURE",
    execution_authority: false,
    sections: {},
    resources: null,
  };
  const input = page.getByLabel("导入只读 Inspector JSON");
  const buffer = Buffer.from(JSON.stringify(snapshot));
  await input.setInputFiles({
    name: "initial.json",
    mimeType: "application/json",
    buffer,
  });
  await expect(
    page.getByText("test:clear-race", { exact: true }),
  ).toBeVisible();
  await input.setInputFiles({
    name: "slow.json",
    mimeType: "application/json",
    buffer,
  });
  await page.getByRole("button", { name: "清除快照" }).click();
  await expect(page.getByRole("alert")).toContainText("导入已被取消");
  await expect(page.getByText("还没有载入快照", { exact: true })).toBeVisible();
  await expect(page.getByText("test:clear-race", { exact: true })).toHaveCount(
    0,
  );
});

test("demo chat works on non-secure LAN origins without randomUUID support", async ({
  page,
}) => {
  await page.addInitScript(() =>
    Object.defineProperty(crypto, "randomUUID", {
      value: undefined,
      configurable: true,
    }),
  );
  await visit(page, "chat");
  await page
    .getByRole("textbox", { name: "给奈奈的消息" })
    .fill("通过手机局域网打开的演示消息");
  await page.getByRole("button", { name: "发送消息", exact: true }).click();
  await expect(page.locator(".message-user").last()).toContainText(
    "通过手机局域网打开的演示消息",
  );
  await expect(page.locator(".message-user").last()).toContainText(
    "已送达演示适配器",
  );
});
