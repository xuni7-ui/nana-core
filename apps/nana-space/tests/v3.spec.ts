/** SYNTHETIC_HTTP_FIXTURE only. No real Provider, canonical Subject or cloud service.
 * The original BFF/Keystore qualifications are reported separately by v2.spec.ts.
 */
import { test, expect, type Page, type Route } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const API = "/api/nana-space/v2/";
const SUBJECT = "SYNTHETIC-V3-UI-SUBJECT";
const PRIVATE_MARKER = "SYNTHETIC_EPHEMERAL_BODY_NOT_PRIVATE_DATA";
const MEMORY_A = "SYNTHETIC 项目备注：原始来源校验完成";
const MEMORY_B = "SYNTHETIC 兴趣备注：研究公开星图";
const providerSettings = {
  schema_version: 1,
  revision: 4,
  execution_authority: false,
  storage_class: "HOST_LOCAL_NOT_SUBJECT_MEMORY",
  providers: [
    {
      provider_profile_id: "provider-a",
      display_name: "SYNTHETIC Text Resource",
      protocol: "OPENAI_COMPATIBLE_CHAT",
      base_url: "https://provider-a.example/v1",
      locality: "REMOTE",
      enabled: true,
      secret_state: "MISSING",
      permitted_privacy: ["PUBLIC", "PROJECT"],
      default_timeout_ms: 15000,
      default_cost_ceiling: 1000,
    },
    {
      provider_profile_id: "provider-b",
      display_name: "SYNTHETIC Vision Resource",
      protocol: "OPENAI_COMPATIBLE_CHAT",
      base_url: "https://provider-b.example/v1",
      locality: "REMOTE",
      enabled: true,
      secret_state: "UNCONFIGURED",
      permitted_privacy: ["PUBLIC", "PROJECT"],
      default_timeout_ms: 10000,
      default_cost_ceiling: 1000,
    },
  ],
  models: [
    {
      model_profile_id: "a-text",
      provider_profile_id: "provider-a",
      remote_model_id: "fixture-text",
      model_version: "test-only",
      operations: ["COGNITION"],
      input_modalities: ["TEXT"],
      output_modalities: ["TEXT"],
      context_limit: 8192,
      output_limit: 1024,
      enabled: true,
    },
    {
      model_profile_id: "b-vision",
      provider_profile_id: "provider-b",
      remote_model_id: "fixture-vision",
      model_version: "test-only",
      operations: ["VISION"],
      input_modalities: ["TEXT", "IMAGE"],
      output_modalities: ["TEXT"],
      context_limit: 8192,
      output_limit: 1024,
      enabled: true,
    },
  ],
  routes: [
    {
      operation: "COGNITION",
      primary_model_profile_id: "a-text",
      fallback_model_profile_ids: [],
      enabled: true,
      timeout_ceiling_ms: 15000,
      cost_ceiling: 1000,
    },
  ],
};
interface MockState {
  run: string;
  watermark: string;
  loggedIn: boolean;
  revision: number;
  requests: { method: string; path: string }[];
  views: string[];
  abortMessage: boolean;
  delayMessage: boolean;
  messageRoute?: Route;
  delayMemories: boolean;
  memoryRoute?: Route;
  delayPair?: boolean;
  pairRoute?: Route;
  delayConfirmation?: boolean;
  confirmationRoute?: Route;
  capabilities?: Record<string, unknown>;
  roles?: string[];
  history?: Record<string, unknown>;
  historyWatermark?: string;
  shares?: Record<string, unknown>;
  biliHistory?: Record<string, unknown>;
}
function envelope(state: MockState, data: Record<string, unknown>) {
  return {
    contract: "nana-space-live/v2",
    realm: "OWNED_DEVELOPMENT_ONLY",
    execution_authority: false,
    subject_id: SUBJECT,
    lineage_binding: "a".repeat(64),
    owner_epoch: 3,
    as_of_us: 1793026800000000,
    revision: state.revision,
    session_generation: 1,
    run_generation: state.run,
    coverage: "CURRENT",
    privacy_scope: ["PUBLIC", "PROJECT"],
    source_refs: ["SYNTHETIC_HTTP_FIXTURE"],
    capabilities: state.capabilities || {},
    data,
  };
}
const host = {
  process_ready: true,
  owner_epoch: 3,
  state: "ACTIVE",
  same_subject: true,
  queue_depth: 0,
};
function viewData(state: MockState, source: string) {
  return {
    host,
    privacy_watermark: state.watermark,
    items: [
      {
        section: source === "home" ? "activities" : source,
        state: "VERIFIED",
        category: `SYNTHETIC ${source} source record`,
        reference: `fixture:${source}:1`,
        source_memory_ids: ["fixture-memory-a"],
      },
    ],
    memories:
      source === "memories"
        ? [
            {
              memory_id: "fixture-memory-a",
              text: MEMORY_A,
              memory_type: "NOTE",
              privacy_class: "PROJECT",
              epistemic_kind: "USER_PROVIDED",
              assessment: "SYNTHETIC_ONLY",
              source_evidence_id: "fixture-source-project",
              created_at_us: 1793026800000000,
            },
            {
              memory_id: "fixture-memory-b",
              text: MEMORY_B,
              memory_type: "PREFERENCE",
              privacy_class: "PUBLIC",
              epistemic_kind: "RAW_OBSERVATION",
              assessment: "SYNTHETIC_ONLY",
              source_evidence_id: "fixture-source-world",
              created_at_us: 1792940400000000,
            },
          ]
        : [],
    ...(source === "settings" ? { provider_settings: providerSettings } : {}),
    ...(source === "devices"
      ? { surfaces: [{ platform: "SYNTHETIC_WEB", state: "BOUND_FIXTURE" }] }
      : {}),
  };
}
async function installMock(page: Page): Promise<MockState> {
  const state: MockState = {
    run: "b".repeat(32),
    watermark: "fixture-privacy-1",
    loggedIn: true,
    revision: 10,
    requests: [],
    views: [],
    abortMessage: false,
    delayMessage: false,
    delayMemories: false,
  };
  await page.route(`**${API}**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.split(API)[1];
    const method = request.method();
    state.requests.push({ method, path });
    const ok = (data: Record<string, unknown>) =>
      route.fulfill({ status: 200, json: envelope(state, data) });
    if (!state.loggedIn && path !== "session")
      return route.fulfill({ status: 401, json: { code: "SESSION_REQUIRED" } });
    if (path === "session" && method === "DELETE") {
      state.loggedIn = false;
      return ok({ cleared: true });
    }
    if (path === "bootstrap")
      return ok({
        roles: state.roles || ["READER", "CONVERSATION", "MANAGER", "HOST_ADMIN"],
        host,
        csrf: "TEST_ONLY_NOT_SECRET_CSRF_BOUNDARY_00000000",
      });
    if (path === "conversation/history") return ok({...state.history, privacy_watermark: state.historyWatermark || state.watermark});
    if (path === "life/shares") return ok({...state.shares, privacy_watermark: state.watermark});
    if (path === "platform/bilibili") return ok(state.biliHistory || {items: []});
    if (path === "providers/credentials") return ok({vault: {configured: true, storage: "HOST_LOCAL_AES_256_GCM", revision: 7, credential_persisted: true}, profiles: []});
    if (path.startsWith("views/")) {
      const source = path.slice(6);
      state.views.push(source);
      if (source === "memories" && state.delayMemories) {
        state.memoryRoute = route;
        return;
      }
      return ok(viewData(state, source));
    }
    if (path === "devices/offers" && method === "POST" && state.delayPair) {
      state.pairRoute = route;
      return;
    }
    if (
      path === "host/confirmations" &&
      method === "POST" &&
      state.delayConfirmation
    ) {
      state.confirmationRoute = route;
      return;
    }
    if (path === "messages" && method === "POST") {
      if (state.abortMessage) return route.abort("failed");
      if (state.delayMessage) {
        state.messageRoute = route;
        return;
      }
      const body = request.postDataJSON();
      return ok({
        receipt_id: body.client_request_id,
        state: "VERIFIED",
        dispatch_happened: true,
        result: {
          text: `${PRIVATE_MARKER}\n\n**SYNTHETIC** Markdown\n\n\`\`\`ts\nconst status = 'fixture';\n\`\`\``,
          provider_state: "SYNTHETIC_HTTP_FIXTURE_NO_MODEL_CALL",
        },
      });
    }
    if (path.startsWith("receipts/"))
      return ok({
        receipt_id: path.slice(9),
        state: "UNKNOWN",
        dispatch_happened: true,
        result: {},
      });
    return route.fulfill({
      status: 404,
      json: { code: "CAPABILITY_UNAVAILABLE" },
    });
  });
  return state;
}
async function open(page: Page, hash = "home") {
  await page.goto(`/index.html?source=live#${hash}`);
  await expect(page.locator(".live-identity")).toContainText(SUBJECT);
}
async function go(page: Page, target: string, source = target) {
  const loaded = page.waitForResponse(
    (response) =>
      response.url().includes(`${API}views/${source}`) &&
      response.request().method() === "GET",
  );
  await page.evaluate((hash) => {
    location.hash = hash;
  }, target);
  await loaded;
  await expect(page.locator("main h1").first()).toBeVisible();
}
async function noHorizontalOverflow(page: Page) {
  expect(
    await page.evaluate(() => ({
      width: innerWidth,
      scroll: document.documentElement.scrollWidth,
    })),
  ).toEqual(expect.objectContaining({ width: expect.any(Number) }));
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
}

test("SYNTHETIC HTTP: all V3 destinations reuse finite V2 views; responsive screenshots", async ({
  page,
}, info) => {
  const state = await installMock(page);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await open(page);
  await expect(page.getByRole("heading", { name: /把日常/ })).toBeVisible();
  await mkdir("docs/previews/v3", { recursive: true });
  for (const [target, source] of [
    ["home", "home"],
    ["room", "home"],
    ["memories", "memories"],
    ["models", "settings"],
    ["journal", "journal"],
    ["world", "world"],
    ["goals", "goals"],
    ["growth", "growth"],
    ["notifications", "journal"],
    ["devices", "devices"],
    ["backup", "runtime"],
    ["runtime", "runtime"],
    ["settings", "settings"],
    ["chat", "chat"],
  ]) {
    if (target !== "home") await go(page, target, source);
    await noHorizontalOverflow(page);
    await expect(page.locator("main")).not.toContainText(
      "把下一场流星雨留给我们",
    );
    if (
      [
        "home",
        "room",
        "memories",
        "models",
        "settings",
        "chat",
        "devices",
        "backup",
      ].includes(target)
    ) {
      await page.screenshot({
        path: `docs/previews/v3/${info.project.name}-${target}.png`,
        fullPage: true,
      });
    }
  }
  expect(state.views).not.toContain("models");
  expect(state.views).not.toContain("room");
  expect(state.views).not.toContain("backup");
  expect(state.requests.filter((x) => x.method !== "GET")).toEqual([]);
  expect(errors).toEqual([]);
});

test("SYNTHETIC HTTP: provider and memory drafts stay local; no fake write or paid test", async ({
  page,
}) => {
  const state = await installMock(page);
  await open(page, "models");
  await expect(page.locator(".v3-capability-card").first()).toContainText(
    "fixture-text",
  );
  await page.getByRole("button", { name: "添加供应商草稿" }).click();
  await page
    .getByRole("combobox", { name: "供应商预设", exact: true })
    .selectOption("deepseek");
  await page
    .getByLabel("已确认的 Base URL", { exact: true })
    .fill("https://fixture-provider.example/v1");
  await page.getByLabel("远端 Model ID", { exact: true }).fill("fixture-model");
  await page
    .getByLabel("模型别名（本地草稿）", { exact: true })
    .fill("SYNTHETIC local alias");
  await page.getByRole("button", { name: "整理配置草稿" }).click();
  await page.getByText("查看本地审阅草稿（不是应用成功回执）").click();
  await expect(page.locator(".v3-draft-result pre")).toContainText(
    "LOCAL_DRAFT_NOT_APPLIED",
  );
  await expect(
    page.getByRole("button", { name: /测试模型 · 需要后端支持/ }),
  ).toBeDisabled();
  await noHorizontalOverflow(page);
  await go(page, "memories");
  await expect(page.locator(".v3-memory-card")).toHaveCount(2);
  await page.getByLabel("搜索记忆", { exact: true }).fill("星图");
  await expect(page.locator(".v3-memory-card")).toHaveCount(1);
  await expect(page.locator(".v3-memory-card")).toContainText(MEMORY_B);
  await page.getByLabel("搜索记忆", { exact: true }).fill("");
  await page.getByLabel("选择记忆预览文件").setInputFiles({
    name: "synthetic-project-notes.json",
    mimeType: "application/json",
    buffer: Buffer.from(
      JSON.stringify([MEMORY_A, "SYNTHETIC newly supplied note"]),
    ),
  });
  await expect(page.locator(".v3-import-preview")).toContainText("1 条新草稿");
  await expect(page.locator(".v3-import-preview")).toContainText(
    "1 条文本重复",
  );
  await expect(
    page.getByRole("button", { name: "需要后端支持 · 暂不能提交" }).first(),
  ).toBeDisabled();
  await page.getByRole("button", { name: "写一条备注", exact: true }).click();
  await page
    .getByLabel("记忆草稿内容")
    .fill("SYNTHETIC user supplied draft, never lived experience");
  await expect(page.locator(".v3-note-draft")).toContainText("USER_PROVIDED");
  await noHorizontalOverflow(page);
  await go(page, "models", "settings");
  await expect(page.locator(".v3-provider-editor")).toHaveCount(0);
  await go(page, "memories");
  await expect(page.locator(".v3-import-preview")).toHaveCount(0);
  await expect(page.locator(".v3-note-draft")).toHaveCount(0);
  expect(state.requests.filter((x) => x.method !== "GET")).toEqual([]);
});

test("SYNTHETIC HTTP: morning/midnight/system themes, reduced motion and navigation accessibility", async ({
  page,
}) => {
  await installMock(page);
  await page.emulateMedia({ colorScheme: "light", reducedMotion: "reduce" });
  await open(page, "settings");
  await page.getByRole("button", { name: /跟随系统/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.emulateMedia({ colorScheme: "dark", reducedMotion: "reduce" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: /^晨雾 / }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: /^月光 / }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(
    page.getByRole("button", { name: "暂停自主调度" }),
  ).toBeEnabled();
  await go(page, "room", "home");
  expect(
    await page
      .locator(".v3-room-star")
      .first()
      .evaluate((el) => ({
        animation: getComputedStyle(el).animationName,
        transition: getComputedStyle(el).transitionDuration,
      })),
  ).toEqual({ animation: "none", transition: "0s" });
  if (
    await page
      .getByRole("button", { name: "打开更多导航", exact: true })
      .isVisible()
  ) {
    await page
      .getByRole("button", { name: "打开更多导航", exact: true })
      .click();
    await expect(page.locator(".v3-sidebar")).toHaveClass(/open/);
    await page.keyboard.press("Escape");
    await expect(page.locator(".v3-sidebar")).not.toHaveClass(/open/);
  }
  await noHorizontalOverflow(page);
});

test("SYNTHETIC HTTP failure: UNKNOWN uses GET original receipt, never second POST", async ({
  page,
}) => {
  const state = await installMock(page);
  state.abortMessage = true;
  await open(page, "chat");
  await page
    .getByLabel("和奈奈说点什么")
    .fill("SYNTHETIC one-shot uncertain message");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "核验这条回执" }),
  ).toBeVisible();
  await expect(page.locator(".live-turn")).not.toContainText(
    "SYNTHETIC one-shot uncertain message",
  );
  await page.getByRole("button", { name: "核验这条回执" }).click();
  await expect
    .poll(
      () => state.requests.filter((x) => x.path.startsWith("receipts/")).length,
    )
    .toBe(1);
  await expect(page.locator(".live-reply")).toContainText("等待核验");
  await expect(page.locator(".live-reply")).toContainText("先核验原回执，不重复发送");
  expect(
    state.requests.filter((x) => x.method === "POST" && x.path === "messages"),
  ).toHaveLength(1);
  expect(
    state.requests.filter((x) => x.method === "POST" && x.path !== "messages"),
  ).toHaveLength(0);
});

test("SYNTHETIC lifecycle: privacy/run update clears bodies; late reply cannot revive; logout clears ephemeral state", async ({
  page,
}) => {
  const state = await installMock(page);
  await open(page, "chat");
  await page
    .getByLabel("和奈奈说点什么")
    .fill("SYNTHETIC first disposable message");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  await expect(page.locator(".live-reply")).toContainText(PRIVATE_MARKER);
  await expect(page.locator(".live-reply pre code")).toContainText(
    "const status",
  );
  state.watermark = "fixture-privacy-2";
  state.revision++;
  await page.getByRole("button", { name: "刷新真实状态" }).click();
  await expect(page.locator(".live-turn")).toHaveCount(0);
  state.delayMessage = true;
  await page
    .getByLabel("和奈奈说点什么")
    .fill("SYNTHETIC pending disposable message");
  await page.getByRole("button", { name: "发送", exact: true }).click();
  await expect.poll(() => Boolean(state.messageRoute)).toBe(true);
  const oldEnvelope = envelope(state, {
    receipt_id: "fixture-stale",
    state: "VERIFIED",
    dispatch_happened: true,
    result: { text: PRIVATE_MARKER },
  });
  state.watermark = "fixture-privacy-3";
  state.run = "c".repeat(32);
  state.revision++;
  await page.getByRole("button", { name: "刷新真实状态" }).click();
  await expect(page.locator(".live-turn")).toHaveCount(0);
  await state.messageRoute!.fulfill({ status: 200, json: oldEnvelope });
  await expect(page.locator(".live-turn")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText(PRIVATE_MARKER);
  await page
    .getByRole("button", { name: "退出并清除本机视图", exact: true })
    .click();
  await expect(page.getByLabel("Subject ID", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([
    "nana-space.preferences.v1",
  ]);
  expect(
    await page.evaluate(() => JSON.stringify(Object.entries(localStorage))),
  ).not.toMatch(
    /SYNTHETIC_EPHEMERAL_BODY|SYNTHETIC pending|csrf|refresh|password|api_key|token/i,
  );
  await page.reload();
  await expect(page.getByLabel("Subject ID", { exact: true })).toBeVisible();
  await expect(page.locator(".live-turn")).toHaveCount(0);
  expect(
    state.requests.filter((x) => x.method === "POST" && x.path === "messages"),
  ).toHaveLength(2);
});

test("SYNTHETIC race: delayed previous-page projection cannot appear on new destination", async ({
  page,
}) => {
  const state = await installMock(page);
  await open(page);
  state.delayMemories = true;
  await page.evaluate(() => {
    location.hash = "memories";
  });
  await expect.poll(() => Boolean(state.memoryRoute)).toBe(true);
  await go(page, "models", "settings");
  await expect(page.locator(".v3-model-center")).toBeVisible();
  await state.memoryRoute!.fulfill({
    status: 200,
    json: envelope(state, viewData(state, "memories")),
  });
  await expect(page.locator(".v3-model-center")).toBeVisible();
  await expect(page.locator(".v3-memory-card")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText(MEMORY_A);
  await expect(page.locator(".v3-capability-card").first()).toContainText(
    "fixture-text",
  );
  expect(state.requests.filter((x) => x.method !== "GET")).toEqual([]);
});

test("SYNTHETIC pairing race: late one-time offer stays cleared after leaving devices", async ({
  page,
}) => {
  const state = await installMock(page);
  state.delayPair = true;
  await open(page, "devices");
  await page
    .getByRole("button", { name: "生成最小权限一次性配对码", exact: true })
    .click();
  await expect.poll(() => Boolean(state.pairRoute)).toBe(true);
  await go(page, "models", "settings");
  await state.pairRoute!.fulfill({
    status: 200,
    json: envelope(state, {
      pairing_code: "TEST_ONLY_NOT_SECRET_ONE_TIME_PAIR_CODE_1234567890",
    }),
  });
  await go(page, "devices");
  await expect(page.locator(".live-pair-code")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText(
    "TEST_ONLY_NOT_SECRET_ONE_TIME_PAIR_CODE",
  );
  expect(
    state.requests.filter(
      (x) => x.path === "devices/offers" && x.method === "POST",
    ),
  ).toHaveLength(1);
});

test("SYNTHETIC host race: logout while confirmation is pending prevents operation dispatch", async ({
  page,
}) => {
  const state = await installMock(page);
  state.delayConfirmation = true;
  await open(page, "backup");
  page.on("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "请求 Core 一致性备份", exact: true })
    .click();
  await expect.poll(() => Boolean(state.confirmationRoute)).toBe(true);
  await page
    .getByRole("button", { name: "退出并清除本机视图", exact: true })
    .click();
  await expect(page.getByLabel("Subject ID", { exact: true })).toBeVisible();
  await state.confirmationRoute!.fulfill({
    status: 200,
    json: envelope(state, {
      confirmation_id: "TEST_ONLY_NOT_SECRET_CONFIRMATION_1234567890",
    }),
  });
  await expect(page.locator(".live-receipt")).toHaveCount(0);
  expect(
    state.requests.filter(
      (x) => x.path === "host/confirmations" && x.method === "POST",
    ),
  ).toHaveLength(1);
  expect(
    state.requests.filter((x) => x.path === "host/operations"),
  ).toHaveLength(0);
  expect(
    await page.evaluate(() => JSON.stringify(Object.entries(localStorage))),
  ).not.toContain("TEST_ONLY_NOT_SECRET_CONFIRMATION");
});

test("SYNTHETIC browser-only: 120 percent type, route history and native-back event preserve layout", async ({
  page,
}) => {
  const state = await installMock(page);
  await open(page);
  await go(page, "settings");
  const originalSize = await page
    .locator(".v3-page-heading h1")
    .evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  await page
    .getByRole("combobox", { name: "文字大小", exact: true })
    .selectOption("1.2");
  await expect
    .poll(async () =>
      page
        .locator(".v3-page-heading h1")
        .evaluate((el) => parseFloat(getComputedStyle(el).fontSize)),
    )
    .toBeCloseTo(originalSize * 1.2, 1);
  await noHorizontalOverflow(page);
  for (const [target, source] of [
    ["models", "settings"],
    ["memories", "memories"],
    ["chat", "chat"],
    ["home", "home"],
  ]) {
    await go(page, target, source);
    await noHorizontalOverflow(page);
  }
  await go(page, "room", "home");
  await expect(page.locator(".v3-room-page")).toBeVisible();
  const returned = page.waitForResponse(
    (response) =>
      response.url().includes(`${API}views/home`) &&
      response.request().method() === "GET",
  );
  await page.goBack();
  await returned;
  await expect(page).toHaveURL(/#home$/);
  await expect(page.locator(".v3-room-page")).toHaveCount(0);
  const more = page.getByRole("button", { name: "打开更多导航", exact: true });
  if (await more.isVisible()) {
    await more.click();
    await expect(page.locator(".v3-sidebar")).toHaveClass(/open/);
    // This validates the Web listener only, not physical Android back delivery.
    await page.evaluate(() =>
      window.dispatchEvent(new Event("nana-android-back")),
    );
    await expect(page.locator(".v3-sidebar")).not.toHaveClass(/open/);
    await expect(page).toHaveURL(/#home$/);
  }
  await noHorizontalOverflow(page);
  expect(state.requests.filter((x) => x.method !== "GET")).toEqual([]);
});

test("SYNTHETIC living recovery: retained exchanges reopen and only original body-free pending receipts can be verified", async ({page}) => {
  const state = await installMock(page);
  state.capabilities = {conversation_history: true};
  state.history = {items: [{exchange_record_id: "exchange-retained", message_id: "source-reference-not-request-uuid",
    user_text: "SYNTHETIC retained user wording", reply_text: "SYNTHETIC retained sourced reply", created_at_us: 1793026800000000}],
    pending_receipts: [{receipt_id: "original-request-uuid", state: "REQUESTED", text: "NEVER_RESTORE_UNCERTAIN_BODY"}]};
  await open(page, "chat");
  await expect(page.locator(".live-turn")).toHaveCount(2);
  await expect(page.locator(".live-reply").first()).toContainText("retained sourced reply");
  await expect(page.locator("main")).not.toContainText("NEVER_RESTORE_UNCERTAIN_BODY");
  await page.getByRole("button", {name: "核验这条回执"}).click();
  await expect.poll(() => state.requests.filter(x => x.path === "receipts/original-request-uuid").length).toBe(1);
  expect(state.requests.filter(x => x.path.includes("source-reference-not-request-uuid"))).toEqual([]);
  await page.reload();
  await expect(page.locator(".live-turn")).toHaveCount(2);
  await expect(page.locator(".live-reply").first()).toContainText("retained sourced reply");
  state.history = {items: [], pending_receipts: []};
  state.watermark = "fixture-withdrawn";
  await page.getByRole("button", {name: "刷新真实状态"}).click();
  await expect(page.locator(".live-turn")).toHaveCount(0);
  expect(state.requests.filter(x => x.method !== "GET")).toEqual([]);
  expect(await page.evaluate(() => JSON.stringify(Object.entries(localStorage)))).not.toContain("retained user wording");
});

test("SYNTHETIC living privacy: a withdrawal between view and history clears transient bodies and drafts", async ({page}) => {
  const state = await installMock(page);
  state.capabilities = {conversation_history: true};
  state.history = {items: [], pending_receipts: []};
  await open(page, "chat");
  await page.getByLabel("和奈奈说点什么").fill("SYNTHETIC current transient wording");
  await page.getByRole("button", {name: "发送", exact: true}).click();
  await expect(page.locator(".live-reply")).toContainText(PRIVATE_MARKER);
  await page.getByLabel("和奈奈说点什么").fill("SYNTHETIC unfinished draft");
  state.historyWatermark = "fixture-history-newer-than-view";
  await page.getByRole("button", {name: "刷新真实状态"}).click();
  await expect(page.locator(".live-turn")).toHaveCount(0);
  await expect(page.getByLabel("和奈奈说点什么")).toHaveValue("");
  expect(state.requests.filter(x => x.method === "POST" && x.path === "messages")).toHaveLength(1);
});

test("SYNTHETIC living boundaries: reader history stays gated, Bili coverage is honest, web vault remains read-only", async ({page}) => {
  const state = await installMock(page);
  state.roles = ["READER", "HOST_ADMIN"];
  state.capabilities = {conversation_history: true, platform_bilibili_history: true, durable_provider_binding: true, native_secret_binding: true};
  state.biliHistory = {items: [{source_memory_id: "source-public-video", bvid: "BV1t55v6DE2v", title: "SYNTHETIC public source video",
    coverage: "METADATA_ONLY_NOT_WATCHED", observed_at_us: 1793026800000000, comment_samples: 2, visual_frames: 0, source_origin: "REAL_PLATFORM_HTTP", watched: true}]};
  await open(page, "chat");
  await expect(page.getByLabel("和奈奈说点什么")).toBeDisabled();
  expect(state.requests.filter(x => x.path === "conversation/history")).toEqual([]);
  await go(page, "bilibili", "world");
  await expect(page.locator(".v4-bili-card")).toContainText("只读到视频信息");
  await expect(page.locator(".v4-bili-card")).toContainText("尚无可确认的语义理解记录");
  await expect(page.getByRole("link", {name: "在B站打开"})).toHaveAttribute("href", "https://www.bilibili.com/video/BV1t55v6DE2v");
  await noHorizontalOverflow(page);
  await go(page, "models", "settings");
  await expect(page.getByLabel("安全凭据绑定")).toContainText("宿主加密保险库 · revision 7");
  await expect(page.getByRole("button", {name: /绑定 .* 凭据|轮换 .* 凭据|撤销 .* 凭据/})).toHaveCount(0);
  expect(state.requests.filter(x => x.method !== "GET")).toEqual([]);
});

test("SYNTHETIC shared presence: original candidates appear in room without being delivered or notified", async ({page}) => {
  const state = await installMock(page);
  state.capabilities = {shared_life_candidates: true};
  state.shares = {coverage: "ORIGINAL_C_APPROVED_CANDIDATES_ONLY", external_delivery: false,
    items: [{candidate_record_id: "candidate-real-core", cycle_id: "cycle-original-c", topic: "experience.sourced", state: "DEFER_BUSY", delivery: "NONE",
      source_record_ids: ["record-source"], source_memory_ids: ["memory-source"], text: "UNSUPPORTED_NARRATIVE_MUST_NOT_RENDER"}]};
  await open(page, "room");
  const card = page.locator(".v3-card").filter({has: page.getByRole("heading", {name: "她留待分享的片刻"})});
  await expect(card).toContainText("尚未送达");
  await expect(card).toContainText("知道你正忙，先留在这里");
  await expect(card).not.toContainText("UNSUPPORTED_NARRATIVE_MUST_NOT_RENDER");
  await noHorizontalOverflow(page);
  state.shares = {...state.shares, items: []};
  state.watermark = "fixture-shared-source-withdrawn";
  await page.getByRole("button", {name: "刷新真实状态"}).click();
  await expect(card).toHaveCount(0);
  expect(state.requests.filter(x => x.method !== "GET")).toEqual([]);
});
