/** SYNTHETIC_HTTP_FIXTURE only. No real Provider, canonical Subject or cloud service.
 * The original BFF/Keystore qualifications are reported separately by v2.spec.ts.
 */
import { test, expect, type Page, type Route } from "@playwright/test";
import { createHash } from "node:crypto";
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
  streamInterrupted?: boolean;
  delayMessage: boolean;
  messageRoute?: Route;
  messageRoutes?: Route[];
  messageBodies?: Record<string, unknown>[];
  privacyScope?: string[];
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
  catalogEnabled?: boolean;
  memorySearchRows?: Record<string,unknown>[];
  lifeItems?: Record<string,unknown>[];
  noteRows?: Record<string,unknown>[];
  noteUnknown?: boolean;
  noteReject?: boolean;
  noteResolved?: boolean;
  noteReceipts?: Record<string,string>;
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
    privacy_scope: state.privacyScope || ["PUBLIC", "PROJECT"],
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
    items: state.lifeItems || [
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
        ? state.noteRows || [
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
    ...(source === "settings" ? { provider_settings: state.catalogEnabled ? {
      ...providerSettings,
      providers: [{...providerSettings.providers[0], provider_profile_id:"provider.catalog", revision:1}],
      models: [], routes: [],
    } : providerSettings } : {}),
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
    if (path === "providers/models" && state.catalogEnabled) return ok({models:["catalog.new"], qualification:"NOT_ESTABLISHED", inference_calls:0});
    if (path === "memories/search" && method === "POST") return ok({memories:state.memorySearchRows || [], privacy_watermark:state.watermark, limit:64});
    if (path === "memories/notes" && method === "POST" && state.capabilities?.memory_notes===true) {
      if(state.noteReject)return route.fulfill({status:409,json:{code:"REVISION_CONFLICT"}});
      const body=request.postDataJSON();
      const mid="fixture-note-"+body.client_request_id;
      state.noteRows=[{memory_id:mid,text:body.text,memory_type:"SEMANTIC",epistemic_kind:"STATEMENT",assessment:"CURRENT",privacy_class:body.privacy_class,source_evidence_id:"fixture-note-source",created_at_us:1793026800000000,user_provided_note:true},...(state.noteRows||[]).filter(r=>r.memory_id!==body.target_id)];
      state.noteReceipts={...state.noteReceipts,[body.client_request_id]:mid};state.revision++;
      if(state.noteUnknown)return route.abort("failed");
      return ok({receipt_id:body.client_request_id,state:"VERIFIED",dispatch_happened:true,result:{state:"USER_NOTE_SAVED",memory_id:mid,nana_lived_experience:false}});
    }
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
    if (path === "commands" && method === "POST") {
      const body=request.postDataJSON();
      return ok({receipt_id:body.idempotency_key,client_request_id:body.client_request_id,operation:body.operation,
        state:"VERIFIED",dispatch_happened:true,no_retry:true,result:{subject_desire_rewritten:false}});
    }
    if (path === "messages/stream" && method === "POST" && state.capabilities?.chat_streaming === true) {
      const body = request.postDataJSON();
      (state.messageBodies ||= []).push(body);
      const frames = [{event:"progress",message_id:body.client_request_id,sequence:1,
        data:envelope(state,{state:"PROVISIONAL_MODEL_DRAFT",text:"SYNTHETIC 临时生成文字"})}];
      if (!state.streamInterrupted) frames.push({event:"receipt",message_id:body.client_request_id,
        data:envelope(state,{receipt_id:body.idempotency_key,client_request_id:body.client_request_id,
          operation:"MESSAGE",no_retry:true,state:"VERIFIED",dispatch_happened:true,
          result:{text:"SYNTHETIC 最终核验回复"}})} as typeof frames[number]);
      return route.fulfill({status:200,contentType:"application/x-ndjson",body:frames.map(v=>JSON.stringify(v)).join("\n")+"\n"});
    }
    if (path === "messages" && method === "POST") {
      (state.messageBodies ||= []).push(request.postDataJSON());
      if (state.abortMessage) return route.abort("failed");
      if (state.delayMessage) {
        state.messageRoute = route;
        (state.messageRoutes ||= []).push(route);
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
        state: state.noteResolved && state.noteReceipts?.[path.slice(9)]?"VERIFIED":"UNKNOWN",
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
  await expect(page.locator("main")).toHaveAttribute("data-subject-id", SUBJECT);
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
  await expect(page.locator(".v3-note-draft")).toContainText("你提供的声明");
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

test("SYNTHETIC inner state: sourced concerns use plain Chinese, withdrawal removes them", async ({page}) => {
  const state=await installMock(page);
  state.lifeItems=[
    {section:"affect",category:"SOCIAL_APPETITE",state:"QUIET",reference:"fixture:appetite"},
    {section:"concerns",category:"OPEN_CONCERN",state:"TRANSIENT",reference:"fixture:curiosity",as_of_us:1793026800000000},
  ];
  await open(page,"room");
  await expect(page.locator("main")).toContainText("这会儿想安静一会儿");
  const thought=page.locator(".v3-record").filter({hasText:"心里惦记着的事"});
  await expect(thought).toContainText("刚浮现的念头");
  await expect(thought.locator("summary")).toHaveText(/查看来源/);
  await thought.locator("summary").click();
  await expect(thought).toContainText("fixture:curiosity");
  await expect(thought).toContainText("OPEN_CONCERN");
  await noHorizontalOverflow(page);
  state.lifeItems=[]; state.watermark="fixture-concern-withdrawn";
  await page.getByRole("button",{name:"刷新真实状态"}).click();
  await expect(thought).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText("这会儿想安静一会儿");
  expect(state.requests.filter(x=>x.method!=="GET")).toEqual([]);
});

test("Next Experience: authorized console reads and filters original projections", async ({ page }) => {
  const state = await installMock(page);
  await open(page);
  await go(page, "runtime", "runtime");
  await page.getByRole("button", { name: "读取最新数据" }).click();
  const panel = page.locator(".next-console");
  await expect(panel).toContainText("来源时间");
  await panel.getByLabel("筛选字段或内容").fill("no-such-field-marker");
  await expect(panel.locator("details")).toHaveCount(0);
  await panel.getByLabel("筛选字段或内容").fill("");
  await panel.getByLabel("数据范围").selectOption("memories");
  await expect(panel).toContainText("来源时间");
  await panel.locator("summary", {hasText: /^memories$/}).click();
  await expect(panel).toContainText(MEMORY_A);
  expect(state.requests.filter(r => r.method === "POST")).toHaveLength(0);
});

test("Daily chat: message area owns the screen and options remain reachable", async ({page}) => {
  await installMock(page); await open(page); await go(page, "chat", "chat");
  const log = page.getByRole("log", {name:"当前会话"});
  const box = await log.boundingBox();
  expect(box!.height).toBeGreaterThan(page.viewportSize()!.height * .45);
  await expect(page.locator(".live-identity")).toHaveCount(0);
  await page.getByText("发送选项", {exact:true}).click();
  await expect(page.locator(".next-options-panel")).toBeVisible();
  expect((await log.boundingBox())!.height).toBeGreaterThan(page.viewportSize()!.height * .45);
  await page.getByText("发送选项", {exact:true}).click();
  await page.getByRole("button", {name:"搜索对话",exact:true}).click();
  await expect(page.getByLabel("搜索当前对话")).toBeVisible();
  await page.getByRole("button", {name:"收起搜索",exact:true}).click();
  await page.getByLabel("和奈奈说点什么").focus();
  if (page.viewportSize()!.width < 900) {
    await expect(page.getByRole("navigation",{name:"移动端导航"})).toBeHidden();
    await page.setViewportSize({width:page.viewportSize()!.width,height:480});
    await expect(page.locator("html")).toHaveAttribute("data-nana-short-viewport", "");
    await expect(page.getByRole("button",{name:"发送",exact:true})).toBeVisible();
    expect((await log.boundingBox())!.height).toBeGreaterThan(130);
  }
});

test("SYNTHETIC model catalog: explicit list read fills draft and registers only the chosen model", async ({page}) => {
  const state = await installMock(page);
  state.catalogEnabled = true;
  state.capabilities = {provider_model_discovery:true,provider_configuration_write:true};
  const commands:Record<string,unknown>[]=[];
  await page.route(`**${API}providers/commands`,async route=>{
    const body=route.request().postDataJSON();commands.push(body.command);state.revision++;
    return route.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,state:'VERIFIED',
      dispatch_happened:true,result:{configuration_revision:5}})});
  });
  await open(page, "models");
  const catalog = page.getByLabel("读取服务商模型");
  await catalog.getByRole("button", {name:/读取 .* 模型/}).click();
  await catalog.getByRole("combobox").selectOption("catalog.new");
  await expect(page.getByLabel("远端 Model ID", {exact:true})).toHaveValue("catalog.new");
  expect(state.requests.filter(r => r.path==="providers/models")).toHaveLength(1);
  expect(state.requests.filter(r => r.method!=="GET")).toHaveLength(0);
  const modelId=await page.getByLabel("模型配置 ID",{exact:true}).inputValue();
  expect(modelId).toMatch(/^model\.catalog-[a-f0-9]{16}$/);
  await page.getByRole('button',{name:'注册模型配置',exact:true}).click();
  await expect.poll(()=>commands.length).toBe(1);
  expect(commands[0].operation).toBe('UPSERT_MODEL');
  expect(commands[0].expected_revision).toBe(4);
  expect(commands[0].model).toMatchObject({model_profile_id:modelId,provider_profile_id:'provider.catalog',remote_model_id:'catalog.new'});
  expect(commands[0].provider).toBeUndefined();expect(commands[0].route).toBeUndefined();
  await expect(page.getByText('最近操作 · 已完成',{exact:true})).toBeVisible();
  await noHorizontalOverflow(page);
});

test("SYNTHETIC older-memory search: explicit scoped read, no memory write", async ({page}) => {
  const state = await installMock(page);
  state.capabilities = {memory_search:true};
  state.memorySearchRows = [{memory_id:"older-memory", text:"SYNTHETIC 共同整理了星图，后续回到旧项目",
    memory_type:"EPISODIC", privacy_class:"PROJECT", source_evidence_id:"older-source", created_at_us:1792940400000000}];
  await open(page, "memories");
  await page.getByLabel("搜索记忆", {exact:true}).fill("整理了星图");
  await page.getByRole("button", {name:"查找更早记忆"}).click();
  await expect(page.locator(".v3-memory-center")).toContainText("后续回到旧项目");
  await expect(page.locator(".v3-memory-overview")).toContainText("最多显示64条");
  expect(state.requests.filter(r => r.method==="POST")).toEqual([{method:"POST",path:"memories/search"}]);
  await page.getByLabel("搜索记忆", {exact:true}).fill("");
  await expect(page.locator(".v3-memory-center")).not.toContainText("后续回到旧项目");
  await noHorizontalOverflow(page);
});

test("SYNTHETIC note retention: explicit consent, verified save and current-note correction",async({page})=>{
  const state=await installMock(page);state.capabilities={memory_notes:true};state.noteRows=[];
  await open(page,"memories");
  await page.getByRole("button",{name:"写一条备注",exact:true}).click();
  await page.getByLabel("记忆草稿内容").fill("SYNTHETIC 项目约定为周三");
  await expect(page.getByRole("button",{name:"保存备注",exact:true})).toBeDisabled();
  await page.getByLabel("同意将这条用户备注保存到云端记忆").check();
  await page.getByRole("button",{name:"保存备注",exact:true}).click();
  await expect(page.locator(".v3-memory-card")).toHaveCount(1);
  await expect(page.locator(".v3-memory-card")).toContainText("你提供的备注");
  await page.locator(".v3-memory-card").click();
  await page.getByRole("button",{name:"更新这条备注",exact:true}).click();
  await page.getByLabel("记忆草稿内容").fill("SYNTHETIC 项目约定改为周五");
  await page.getByLabel("同意将这条用户备注保存到云端记忆").check();
  await page.getByRole("button",{name:"保存备注",exact:true}).click();
  await expect(page.locator(".v3-memory-card")).toHaveCount(1);
  await expect(page.locator(".v3-memory-card")).toContainText("周五");
  expect(state.requests.filter(r=>r.method==="POST")).toEqual([{method:"POST",path:"memories/notes"},{method:"POST",path:"memories/notes"}]);
  await noHorizontalOverflow(page);
});

test("SYNTHETIC note UNKNOWN: verify the original receipt without another write",async({page})=>{
  const state=await installMock(page);state.capabilities={memory_notes:true};state.noteRows=[];state.noteUnknown=true;
  await open(page,"memories");
  await page.getByRole("button",{name:"写一条备注",exact:true}).click();
  await page.getByLabel("记忆草稿内容").fill("SYNTHETIC 网络中断后的同一备注");
  await page.getByLabel("同意将这条用户备注保存到云端记忆").check();
  await page.getByRole("button",{name:"保存备注",exact:true}).click();
  await expect(page.getByRole("button",{name:"核验这次保存",exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"保存备注",exact:true})).toBeDisabled();
  await expect(page.getByLabel("记忆草稿内容")).toBeDisabled();
  state.noteResolved=true;
  await page.getByRole("button",{name:"核验这次保存",exact:true}).click();
  await expect(page.getByLabel("用户提供的记忆草稿")).toHaveCount(0);
  expect(state.requests.filter(r=>r.path==="memories/notes")).toHaveLength(1);
  expect(state.requests.filter(r=>r.path.startsWith("receipts/") && r.method==="GET")).toHaveLength(1);
  await noHorizontalOverflow(page);
});

test("SYNTHETIC note admission conflict: no false UNKNOWN or automatic second POST",async({page})=>{
  const state=await installMock(page);state.capabilities={memory_notes:true};state.noteRows=[];state.noteReject=true;
  await open(page,"memories");
  await page.getByRole("button",{name:"写一条备注",exact:true}).click();
  await page.getByLabel("记忆草稿内容").fill("SYNTHETIC rejected before note admission");
  await page.getByLabel("同意将这条用户备注保存到云端记忆").check();
  await page.getByRole("button",{name:"保存备注",exact:true}).click();
  await expect(page.getByRole("button",{name:"核验这次保存",exact:true})).toHaveCount(0);
  await expect(page.getByRole("button",{name:"保存备注",exact:true})).toBeEnabled();
  expect(state.requests.filter(r=>r.path==="memories/notes")).toHaveLength(1);
  expect(state.noteRows).toEqual([]);
});


test("SYNTHETIC retention: connection opt-in survives sends, excludes personal and clears on run change", async ({ page }, info) => {
  const state = await installMock(page);
  state.capabilities = { shared_life_retention: true };
  state.privacyScope = ["PUBLIC", "PROJECT", "PERSONAL"];
  await open(page, "chat");
  await page.locator(".next-send-options summary").click();
  const continuous = page.getByLabel("记住后续对话（本次连接）", { exact: false });
  const personal = page.getByLabel("本次包含个人内容", { exact: false });
  const once = page.getByLabel("记住这次共同经历", { exact: false });
  await expect(continuous).not.toBeChecked();
  await continuous.check();
  const send = async (text: string, keyboard = false) => {
    if (await page.locator(".next-send-options").getAttribute("open") !== null)
      await page.locator(".next-send-options summary").click();
    await page.getByLabel("和奈奈说点什么").fill(text);
    if (keyboard) await page.getByLabel("和奈奈说点什么").press("Control+Enter");
    else await page.getByRole("button", { name: "发送", exact: true }).click();
    await expect(page.getByRole("button", { name: "发送", exact: true })).toBeDisabled();
    await expect(continuous).toBeEnabled();
  };
  await send("SYNTHETIC first retained project turn");
  await expect(continuous).toBeChecked();
  await send("SYNTHETIC second retained project turn", true);
  await page.screenshot({path: `test-results/408-${info.project.name}-chat.png`});
  expect(state.messageBodies?.map(body => body.retain_shared_life)).toEqual([true, true]);
  await page.locator(".next-send-options summary").click();
  await personal.check();
  await expect(continuous).toBeDisabled();
  await expect(continuous).not.toBeChecked();
  await expect(once).not.toBeChecked();
  await send("SYNTHETIC explicitly personal not retained");
  expect(state.messageBodies?.at(-1)?.privacy_class).toBe("PERSONAL");
  expect(state.messageBodies?.at(-1)?.retain_shared_life).toBe(false);
  await expect(continuous).toBeChecked();
  state.capabilities.shared_life_retention = false;
  await page.getByRole("button", { name: "刷新真实状态", exact: true }).click();
  await expect(continuous).toHaveCount(0);
  state.capabilities.shared_life_retention = true;
  await page.getByRole("button", { name: "刷新真实状态", exact: true }).click();
  await expect(continuous).not.toBeChecked();
  await page.locator(".next-send-options summary").click();
  await continuous.check();
  await page.locator(".next-send-options summary").click();
  state.run = "c".repeat(32);
  await page.getByRole("button", { name: "刷新真实状态", exact: true }).click();
  await expect(continuous).not.toBeChecked();
  await expect(once).not.toBeChecked();
  await send("SYNTHETIC after run change");
  expect(state.messageBodies?.at(-1)?.retain_shared_life).toBe(false);
  const persisted = await page.evaluate(() => JSON.stringify(localStorage));
  expect(persisted).not.toContain("retained project turn");
  expect(persisted).not.toContain("rememberConnection");
});


test("SYNTHETIC stream: final receipt replaces provisional text, interruption never retries", async ({page},info)=>{
  const state=await installMock(page);
  state.capabilities={chat_streaming:true};
  await open(page,"chat");
  await expect(page.getByRole("button",{name:"逐字回复 · 开"})).toHaveAttribute("aria-pressed","true");
  await page.getByLabel("和奈奈说点什么").fill("SYNTHETIC stream turn");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect(page.getByText("SYNTHETIC 最终核验回复",{exact:true})).toBeVisible();
  await expect(page.getByText("SYNTHETIC 临时生成文字",{exact:true})).toHaveCount(0);
  state.streamInterrupted=true;
  await page.getByLabel("和奈奈说点什么").fill("SYNTHETIC interrupted turn");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect(page.getByText("这条消息的结果还不能确认。先核验原回执，不重复发送。",{exact:true})).toBeVisible();
  await expect(page.getByText("SYNTHETIC 临时生成文字",{exact:true})).toHaveCount(0);
  expect(state.requests.filter(r=>r.path==="messages/stream" && r.method==="POST")).toHaveLength(2);
  expect(state.requests.filter(r=>r.path==="messages" && r.method==="POST")).toHaveLength(0);
  await expect(page.getByLabel("和奈奈说点什么")).toBeEnabled();
  state.streamInterrupted=false;
  await page.getByLabel("和奈奈说点什么").fill("SYNTHETIC independent message after UNKNOWN");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect(page.getByText("SYNTHETIC 最终核验回复",{exact:true})).toBeVisible();
  expect(state.requests.filter(r=>r.path==="messages/stream" && r.method==="POST")).toHaveLength(3);
  expect(new Set(state.messageBodies?.map(body=>body.client_request_id)).size).toBe(3);
  await noHorizontalOverflow(page);
  await page.screenshot({path:`test-results/409-${info.project.name}-stream.png`});
  expect(await page.evaluate(()=>JSON.stringify(localStorage))).not.toContain("interrupted turn");
});


test("SYNTHETIC in-flight controls: pause stays usable without unlocking the pending message",async({page})=>{
  const state=await installMock(page);state.delayMessage=true;
  await open(page,"chat");
  await page.getByLabel("和奈奈说点什么").fill("SYNTHETIC waiting model request");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect.poll(()=>Boolean(state.messageRoute)).toBe(true);
  await go(page,"settings");
  const pause=page.getByRole("button",{name:"暂停自主调度",exact:true});
  await expect(pause).toBeEnabled();
  await expect(page.getByRole("button",{name:"恢复调度",exact:true})).toBeDisabled();
  await pause.click();
  await expect.poll(()=>state.requests.filter(r=>r.path==="commands" && r.method==="POST").length).toBe(1);
  await expect(pause).toBeEnabled();
  await go(page,"chat");
  await expect(page.getByRole("button",{name:"发送",exact:true})).toBeDisabled();
  const body=state.messageRoute!.request().postDataJSON();
  await state.messageRoute!.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,state:"VERIFIED",dispatch_happened:true,result:{text:"SYNTHETIC finished after manager control"}})});
  await expect(page.getByText("SYNTHETIC finished after manager control",{exact:true})).toBeVisible();
  expect(state.requests.filter(r=>r.path==="messages" && r.method==="POST")).toHaveLength(1);
});

test("SYNTHETIC complete retained long reply restores and withdrawal removes it",async({page})=>{
  const state=await installMock(page);
  const reply="SYNTHETIC_LONG_RESTORE "+"complete explanation. ".repeat(550)+"🌙".repeat(1000);
  state.capabilities={conversation_history:true,conversation_feedback:true};
  state.history={items:[{exchange_record_id:"long-retained",user_text:"SYNTHETIC retained discussion",reply_text:reply,created_at_us:1793026800000000}]};
  await open(page,"chat");
  await expect(page.locator(".live-reply > p").first()).toHaveText(reply);
  await expect(page.getByRole("button",{name:"评价这条回复"})).toHaveCount(0);
  await noHorizontalOverflow(page);
  await page.reload();
  await expect(page.locator(".live-reply > p").first()).toHaveText(reply);
  expect(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)))).not.toContain("SYNTHETIC_LONG_RESTORE");
  state.history={items:[],pending_receipts:[]};state.watermark="fixture-long-withdrawn";
  await page.getByRole("button",{name:"刷新真实状态"}).click();
  await expect(page.locator(".live-turn")).toHaveCount(0);
  expect(state.requests.filter(x=>x.method!=="GET")).toEqual([]);
});

test("SYNTHETIC explicit reply feedback saves once and UNKNOWN only checks its receipt",async({page})=>{
  const state=await installMock(page);
  state.capabilities={conversation_history:true,conversation_feedback:true};
  state.history={items:[{exchange_record_id:"feedback-exchange",message_id:"feedback-message",user_text:"SYNTHETIC retained hello",reply_text:"SYNTHETIC retained reply",created_at_us:1793026800000000}]};
  let posts=0, receiptId="",checks=0;
  await page.route(`**${API}conversation/feedback`,async route=>{
    posts++;
    const body=route.request().postDataJSON();receiptId=body.idempotency_key;
    expect(body.consent).toBe(true);
    expect(body.sample.review_target).toBe("feedback-exchange");
    expect(body.sample.reason_tags).toEqual(["TOO_VERBOSE"]);
    await route.fulfill({status:200,json:envelope(state,{receipt_id:receiptId,state:"UNKNOWN",dispatch_happened:true,result:{}})});
  });
  await page.route(`**${API}receipts/*`,async route=>{
    checks++;expect(route.request().url()).toContain(receiptId);
    await route.fulfill({status:200,json:envelope(state,{receipt_id:receiptId,state:"VERIFIED",dispatch_happened:true,result:{state:"EXPLICIT_FEEDBACK_SAVED",delivery_proven:false}})});
  });
  await open(page,"chat");
  await page.getByRole("button",{name:"评价这条回复"}).click();
  await page.getByRole("button",{name:"保存：有点啰嗦"}).click();
  await expect(page.getByText("保存结果待核验，不会重复提交",{exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"保存：有点啰嗦"})).toHaveCount(0);
  await page.getByRole("button",{name:"核验这条评价"}).click();
  await expect(page.getByText("评价已保存",{exact:true})).toBeVisible();
  expect(posts).toBe(1);expect(checks).toBe(1);
  expect(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)))).not.toContain("SYNTHETIC retained reply");
  await noHorizontalOverflow(page);
});

for (const [mode, label] of [
  ["EXPLICIT_RECALL", "明确回忆"], ["NATURAL_REFERENCE", "自然呼应"],
  ["IMPLICIT_REFERENCE", "放在心里"], ["DO_NOT_MENTION", "暂不提及"],
] as const) {
  test(`SYNTHETIC four memory-use feedback ${mode} binds source and verifies UNKNOWN without resending`, async ({page}) => {
    const state = await installMock(page);
    state.capabilities = {conversation_history: true, conversation_feedback: true, memory_use_feedback: true};
    state.history = {items: [{exchange_record_id: "memory-feedback-exchange", user_text: "SYNTHETIC retained question",
      reply_text: "SYNTHETIC retained reply", created_at_us: 1793026800000000,
      memory_use_delivery_proven: false,
      memory_use_sources: [{memory_id: "memory-source-note", excerpt: "SYNTHETIC retained ORCHID note"}]}]};
    let posts = 0, checks = 0, receiptId = "";
    await page.route(`**${API}conversation/feedback`, async route => {
      posts++;
      const body = route.request().postDataJSON();
      receiptId = body.idempotency_key;
      expect(body.consent).toBe(true);
      expect(body.sample.review_target).toBe("memory-feedback-exchange");
      expect(body.sample.memory_use).toEqual({memory_id: "memory-source-note", mode});
      expect(body.sample.human_judgment).toBe("PARTIAL");
      expect(body.sample.reason_tags).toEqual([]);
      await route.fulfill({status: 200, json: envelope(state, {receipt_id: receiptId, state: "UNKNOWN", dispatch_happened: true, result: {}})});
    });
    await page.route(`**${API}receipts/*`, async route => {
      checks++;
      expect(route.request().url()).toContain(receiptId);
      await route.fulfill({status: 200, json: envelope(state, {receipt_id: receiptId, state: "VERIFIED", dispatch_happened: true,
        result: {state: "EXPLICIT_FEEDBACK_SAVED", delivery_proven: false}})});
    });
    await open(page, "chat");
    await page.getByRole("button", {name: "评价这条回复"}).click();
    await expect(page.getByRole("button", {name: `保存：${label}`, exact: true})).toHaveCount(0);
    await page.getByLabel("选择关联记忆").selectOption("memory-source-note");
    await page.getByRole("button", {name: `保存：${label}`, exact: true}).click();
    await expect(page.getByRole("button", {name: `保存：${label}`, exact: true})).toHaveCount(0);
    await page.getByRole("button", {name: "核验这条记忆偏好"}).click();
    await expect(page.getByText("记忆使用偏好已保存", {exact: true})).toBeVisible();
    expect(posts).toBe(1); expect(checks).toBe(1);
    expect(await page.evaluate(() => JSON.stringify(Object.entries(localStorage)))).not.toContain("SYNTHETIC retained ORCHID note");
    await noHorizontalOverflow(page);
  });
}


test("SYNTHETIC local chat inbox waits, can cancel, and sends remaining turns in order",async({page})=>{
  const state=await installMock(page);state.delayMessage=true;
  await open(page,"chat");
  const input=page.getByLabel("和奈奈说点什么");
  await input.fill("SYNTHETIC first turn");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect.poll(()=>Boolean(state.messageRoute)).toBe(true);
  await input.fill("SYNTHETIC cancel this queued turn");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect(page.getByText("等前一条回复后再发送；现在还没有送出。",{exact:true})).toBeVisible();
  expect(state.messageBodies).toHaveLength(1);
  await page.getByRole("button",{name:"取消这条待发消息"}).click();
  await expect(page.getByText("等前一条回复后再发送；现在还没有送出。",{exact:true})).toHaveCount(0);
  await input.fill("SYNTHETIC second turn");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  expect(state.messageBodies).toHaveLength(1);
  const firstBody=state.messageRoutes![0].request().postDataJSON();
  await state.messageRoutes![0].fulfill({status:200,json:envelope(state,{receipt_id:firstBody.client_request_id,
    state:"VERIFIED",dispatch_happened:true,result:{text:"SYNTHETIC first acknowledged"}})});
  await expect.poll(()=>state.messageRoutes?.length).toBe(2);
  const secondBody=state.messageRoutes![1].request().postDataJSON();
  expect(secondBody.text).toBe("SYNTHETIC second turn");
  expect(secondBody.client_request_id).not.toBe(firstBody.client_request_id);
  await state.messageRoutes![1].fulfill({status:200,json:envelope(state,{receipt_id:secondBody.client_request_id,
    state:"VERIFIED",dispatch_happened:true,result:{text:"SYNTHETIC second acknowledged"}})});
  await expect(page.getByText("SYNTHETIC second acknowledged",{exact:true})).toBeVisible();
  expect(state.messageBodies?.map(body=>body.text)).toEqual(["SYNTHETIC first turn","SYNTHETIC second turn"]);
});

test("SYNTHETIC local chat inbox clears queued text after an unknown original receipt",async({page})=>{
  const state=await installMock(page);state.delayMessage=true;
  await open(page,"chat");
  const input=page.getByLabel("和奈奈说点什么");
  await input.fill("SYNTHETIC first uncertain turn");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect.poll(()=>Boolean(state.messageRoute)).toBe(true);
  await input.fill("SYNTHETIC must not auto-send after UNKNOWN");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect(page.getByText("等前一条回复后再发送；现在还没有送出。",{exact:true})).toBeVisible();
  const firstBody=state.messageRoute!.request().postDataJSON();
  await state.messageRoute!.fulfill({status:200,json:envelope(state,{receipt_id:firstBody.client_request_id,
    state:"UNKNOWN",dispatch_happened:true,result:{}})});
  await expect(page.getByRole("button",{name:"核验这条回执"})).toBeVisible();
  await expect(page.getByText("等前一条回复后再发送；现在还没有送出。",{exact:true})).toHaveCount(0);
  await expect.poll(()=>state.messageBodies).toHaveLength(1);
  expect(state.messageBodies?.map(body=>body.text)).toEqual(["SYNTHETIC first uncertain turn"]);
  expect(state.messageRoutes).toHaveLength(1);
});

test("SYNTHETIC local chat inbox expires unsent bodies while the original request is pending",async({page})=>{
  const state=await installMock(page);state.delayMessage=true;
  await page.clock.install();
  await open(page,"chat");
  const input=page.getByLabel("和奈奈说点什么");
  await input.fill("SYNTHETIC active request stays pending");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect.poll(()=>Boolean(state.messageRoute)).toBe(true);
  await input.fill("SYNTHETIC expired secret must disappear");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect(page.getByRole("button",{name:"取消这条待发消息"})).toBeVisible();
  await page.clock.fastForward(5_000);
  await input.fill("SYNTHETIC later body has its own deadline");
  await page.getByRole("button",{name:"发送",exact:true}).click();
  await expect(page.getByRole("button",{name:"取消这条待发消息"})).toHaveCount(2);
  await page.clock.fastForward(20*60_000-5_000+1);
  await expect(page.getByRole("button",{name:"取消这条待发消息"})).toHaveCount(1);
  await expect(page.locator(".live-turn").filter({hasText:"SYNTHETIC expired secret must disappear"})).toHaveCount(0);
  await expect(page.locator(".live-turn").filter({hasText:"SYNTHETIC later body has its own deadline"})).toHaveCount(1);
  await page.clock.fastForward(5_000);
  await expect(page.getByRole("button",{name:"取消这条待发消息"})).toHaveCount(0);
  await expect(page.locator(".live-turn").filter({hasText:"SYNTHETIC later body has its own deadline"})).toHaveCount(0);
  expect(state.messageBodies).toHaveLength(1);
  const body=state.messageRoute!.request().postDataJSON();
  await state.messageRoute!.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,
    state:"VERIFIED",dispatch_happened:true,result:{text:"SYNTHETIC active reply survives expiry"}})});
  await expect(page.getByText("SYNTHETIC active reply survives expiry",{exact:true})).toBeVisible();
  expect(state.messageBodies).toHaveLength(1);
});

test("SYNTHETIC long reply feedback binds full Unicode response without reposting its body",async({page})=>{
  const state=await installMock(page);
  const reply='🌙'.repeat(3000);
  state.capabilities={conversation_history:true,conversation_feedback:true,long_reply_feedback:true};
  state.history={items:[{exchange_record_id:'long-feedback-exchange',user_text:'SYNTHETIC long discussion',
    reply_text:reply,created_at_us:1793026800000000}]};
  let posts=0,checks=0,id='';
  await page.route(`**${API}conversation/feedback`,async route=>{
    posts++;const body=route.request().postDataJSON();id=body.idempotency_key;
    expect(body.response_sha256).toBe(createHash('sha256').update(reply,'utf8').digest('hex'));
    expect(body.sample.candidate_response).toBe('DEPENDENT_RECORD_BODY');
    expect(body.sample.reason_tags).toEqual(['TOO_VERBOSE']);
    expect(body.exchange_record_id).toBe('long-feedback-exchange');
    expect(JSON.stringify(body)).not.toContain(reply);
    await route.fulfill({status:200,json:envelope(state,{receipt_id:id,state:'UNKNOWN',dispatch_happened:true,result:{}})});
  });
  await page.route(`**${API}receipts/*`,async route=>{
    checks++;expect(route.request().url()).toContain(id);
    await route.fulfill({status:200,json:envelope(state,{receipt_id:id,state:'VERIFIED',dispatch_happened:true,
      result:{state:'EXPLICIT_FEEDBACK_SAVED',delivery_proven:false}})});
  });
  await open(page,'chat');
  await page.getByRole('button',{name:'评价这条回复'}).click();
  await page.getByRole('button',{name:'保存：有点啰嗦'}).click();
  await expect(page.getByText('保存结果待核验，不会重复提交',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'核验这条评价'}).click();
  await expect(page.getByText('评价已保存',{exact:true})).toBeVisible();
  expect(posts).toBe(1);expect(checks).toBe(1);
  expect(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)))).not.toContain(reply);
});


for (const scenario of ['SAVED','LOST_ACK','REJECTED'] as const) test(`SYNTHETIC model setup: numeric UUID ${scenario}`, async ({page}) => {
  const lostAck=scenario==='LOST_ACK';
  const rejected=scenario==='REJECTED';
  const state=await installMock(page);
  state.capabilities={provider_configuration_write:true};
  await page.addInitScript(()=>{
    let next=0;
    crypto.randomUUID=()=>`01234567-89ab-4cde-8fab-${String(++next).padStart(12,'0')}` as `${string}-${string}-${string}-${string}-${string}`;
  });
  let configRevision=providerSettings.revision;
  const commands:Record<string,unknown>[]=[];
  let requestId='';let receiptReads=0;
  await page.route(`**${API}views/settings`,route=>route.fulfill({status:200,json:envelope(state,
    {...viewData(state,'settings'),provider_settings:{...providerSettings,revision:configRevision}})}));
  await page.route(`**${API}providers/commands`,async route=>{
    const body=route.request().postDataJSON();
    commands.push(body.command);requestId=body.client_request_id;
    expect(body.command.expected_revision).toBe(configRevision);
    if(rejected)return route.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,
      state:'REJECTED',dispatch_happened:false,error:'PROVIDER_CONFIG_REVISION_CONFLICT'})});
    configRevision++;state.revision++;
    if(lostAck)return route.abort('failed');
    return route.fulfill({status:200,json:envelope(state,{receipt_id:body.client_request_id,state:'VERIFIED',
      dispatch_happened:true,result:{configuration_revision:configRevision}})});
  });
  await page.route(`**${API}receipts/*`,route=>{
    receiptReads++;
    return route.fulfill({status:200,json:envelope(state,
      {receipt_id:requestId,state:'VERIFIED',dispatch_happened:true,result:{configuration_revision:configRevision}})});
  });
  await open(page,'models');
  const setup=page.locator('.next-setup');
  await setup.locator('button').click();
  if(rejected){
    await expect(page.getByText('最近操作 · 未执行',{exact:true})).toBeVisible();
    expect(commands).toHaveLength(1);expect(configRevision).toBe(providerSettings.revision);expect(receiptReads).toBe(0);
    await expect(page.getByText('最近操作 · 待确认',{exact:true})).toHaveCount(0);
  }else if(lostAck){
    await expect(page.getByText('最近操作 · 待确认',{exact:true})).toBeVisible();
    await expect.poll(()=>commands.length).toBe(1);
    await page.getByText('最近操作 · 待确认',{exact:true}).click();
    await page.getByRole('button',{name:'核验当前回执',exact:true}).click();
    await expect(page.getByText('最近操作 · 已完成',{exact:true})).toBeVisible();
    expect(commands).toHaveLength(1);expect(receiptReads).toBe(1);
  }else{
    await expect(setup).toContainText('供应商与模型已保存');
    expect(commands).toHaveLength(2);
    expect(commands.map(c=>c.operation)).toEqual(['UPSERT_PROVIDER','UPSERT_MODEL']);
    const provider=commands[0].provider as Record<string,unknown>;
    const model=commands[1].model as Record<string,unknown>;
    expect(provider.provider_profile_id).toMatch(/^provider\.[a-z][a-z0-9._-]+$/);
    expect(model.model_profile_id).toMatch(/^model\.[a-z][a-z0-9._-]+$/);
    expect(model.provider_profile_id).toBe(provider.provider_profile_id);
    expect(provider.default_timeout_ms).toBe(120000);
    expect(model.remote_model_id).toBe('deepseek-chat');
  }
  expect(commands.some(c=>c.operation==='SET_CAPABILITY_ROUTE')).toBe(false);
  expect(state.requests.some(r=>r.path==='providers/credentials/bind'||r.path==='providers/models')).toBe(false);
  await noHorizontalOverflow(page);
});
