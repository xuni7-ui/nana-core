import { describe, expect, test } from "vitest";
import {
  capabilityCatalog,
  coreOperations,
  eligibleModels,
  newProviderDraft,
  providerDraftProposal,
  readProviderSettings,
  safeProviderUrl,
  validateProviderDraft,
  modelSetupPresets,
} from "../src/data/provider-center";

test("simple and advanced provider drafts share known addresses and adapted protocols", () => {
  for(const [id,url,protocol] of [
    ['openai','https://api.openai.com/v1','OPENAI_COMPATIBLE_CHAT'],
    ['anthropic','https://api.anthropic.com/v1','ANTHROPIC'],
    ['deepseek','https://api.deepseek.com','OPENAI_COMPATIBLE_CHAT'],
  ]) {
    const draft=newProviderDraft(id);
    expect(draft.baseUrl).toBe(url);expect(draft.protocol).toBe(protocol);
    expect(validateProviderDraft(draft,'PROVIDER')).toEqual([]);
  }
  expect(newProviderDraft('deepseek').modelId).toBe('deepseek-chat');
  expect(newProviderDraft('anthropic').modelId).toBe('');
  expect(newProviderDraft('compatible').baseUrl).toBe('');
  expect(newProviderDraft('qwen').baseUrl).toBe(''); // No guessed regional endpoint.
  expect(modelSetupPresets.map(p=>p.id)).toContain('qwen');
  expect(modelSetupPresets.map(p=>p.id)).not.toContain('gemini');
  expect(modelSetupPresets.map(p=>p.id)).not.toContain('ollama');
  const first=newProviderDraft('openai');first.baseUrl='https://custom.example/v1';
  expect(newProviderDraft('openai').baseUrl).toBe('https://api.openai.com/v1');
});
const config = () => ({
  schema_version: 1,
  revision: 4,
  execution_authority: false,
  storage_class: "HOST_LOCAL_NOT_SUBJECT_MEMORY",
  providers: ["a", "b"].map((id) => ({
    provider_profile_id: id,
    display_name: id,
    protocol: "OPENAI_COMPATIBLE_CHAT",
    base_url: "https://provider.example/v1",
    enabled: true,
    secret_state: "AVAILABLE",
    permitted_privacy: ["PUBLIC", "PROJECT"],
    api_key: "TEST_ONLY_NOT_SECRET",
    secret_ref: "must-not-expose",
  })),
  models: ["a", "b"].map((id) => ({
    model_profile_id: `${id}-text`,
    provider_profile_id: id,
    remote_model_id: "same.remote",
    model_version: "1",
    operations: ["COGNITION"],
    enabled: true,
  })),
  routes: [
    {
      operation: "COGNITION",
      primary_model_profile_id: "a-text",
      fallback_model_profile_ids: ["b-text"],
      enabled: true,
    },
  ],
});
describe("provider projection compatibility", () => {
  test("same remote model on two providers keeps separate identities, no accidental credential fields", () => {
    const view = readProviderSettings(config());
    expect(view.state).toBe("CURRENT");
    expect(view.models.map((x) => x.id)).toEqual(["a-text", "b-text"]);
    expect(JSON.stringify(view)).not.toMatch(
      /TEST_ONLY_NOT_SECRET|secret_ref|must-not-expose|api_key/,
    );
    expect(view.routes[0].fallbacks).toEqual(["b-text"]);
  });
  test("invalid schema, duplicate profile and dangling route fail closed", () => {
    expect(readProviderSettings({ ...config(), schema_version: 2 }).state).toBe(
      "INVALID",
    );
    expect(
      readProviderSettings({
        ...config(),
        providers: [config().providers[0], config().providers[0]],
      }).state,
    ).toBe("INVALID");
    expect(
      readProviderSettings({
        ...config(),
        routes: [
          { operation: "COGNITION", primary_model_profile_id: "missing" },
        ],
      }).state,
    ).toBe("INVALID");
    expect(readProviderSettings(undefined).state).toBe("UNAVAILABLE");
  });
  test("unknown protocol and remote SECRET settings are not treated as usable configuration", () => {
    const bad = config();
    bad.providers[0].protocol = "UNSUPPORTED_NATIVE";
    expect(readProviderSettings(bad).state).toBe("INVALID");
    const privateRoute = config();
    privateRoute.providers[0].permitted_privacy = ["SECRET"];
    expect(readProviderSettings(privateRoute).state).toBe("INVALID");
  });
  test("route candidates require both model and provider enabled and exact operation", () => {
    const c = config();
    c.providers[0].enabled = false;
    const view = readProviderSettings(c);
    expect(eligibleModels(view, "COGNITION").map((x) => x.id)).toEqual([
      "b-text",
    ]);
    expect(eligibleModels(view, "VISION")).toEqual([]);
  });
  test("capability labels map existing operations; rerank/realtime are explicit future slots", () => {
    expect(
      capabilityCatalog
        .filter((c) => c.operation)
        .map((c) => c.operation)
        .sort(),
    ).toEqual([...coreOperations].sort());
    expect(
      capabilityCatalog.find((c) => c.id === "RERANK")?.operation,
    ).toBeUndefined();
    expect(
      capabilityCatalog.find((c) => c.id === "MULTIMODAL")?.operation,
    ).toBeUndefined();
  });
});
test.each([
  "file:///etc/passwd",
  "ftp://provider.example",
  "http://provider.example",
  "https://user:password@provider.example/v1",
  "https://provider.example/v1#fragment",
  "https://provider.example/v1?key=TEST_ONLY_NOT_SECRET",
  "https://provider.example/v1/chat/completions",
  "https://127.0.0.1/v1",
  "https://provider.local/v1",
])("unsafe address never reaches provider projection: %s", (value) =>
  expect(safeProviderUrl(value)).toBe(""),
);
test("draft is explicit no-network proposal, never a Core write or authority", () => {
  const draft = {
    ...newProviderDraft("deepseek"),
    baseUrl: "https://provider.example/v1",
    modelId: "text-model",
    alias: "聊天",
  };
  expect(validateProviderDraft(draft)).toEqual([]);
  const proposal = providerDraftProposal(draft, 4);
  expect(proposal.state).toBe("LOCAL_DRAFT_NOT_APPLIED");
  expect(proposal.execution_authority).toBe(false);
  expect(proposal.no_network_request).toBe(true);
  expect(proposal.based_on_revision).toBe(4);
  expect(JSON.stringify(proposal)).not.toContain("secret_ref");
  expect(() => providerDraftProposal(newProviderDraft())).toThrow();
});
