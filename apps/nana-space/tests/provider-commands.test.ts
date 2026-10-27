import { expect, test } from "vitest";
import {
  providerCommand,
  modelCommand,
  routeCommand,
} from "../src/data/provider-commands";
import { newProviderDraft } from "../src/data/provider-center";
const draft = () => ({
  ...newProviderDraft(),
  baseUrl: "https://provider.example/v1",
  modelId: "same.model",
  displayName: "Synthetic declared provider",
});
test("commands use original model/provider IDs and exact config revision without secrets", () => {
  const p = providerCommand(draft(), "provider.a", 3);
  expect(p.expected_revision).toBe(3);
  expect(p.provider?.provider_profile_id).toBe("provider.a");
  expect(JSON.stringify(p)).not.toMatch(/secret_ref|api_key|credential/);
  const a = modelCommand(draft(), "provider.a", "model.a", 4),
    b = modelCommand(draft(), "provider.b", "model.b", 4);
  expect(a.model?.remote_model_id).toBe(b.model?.remote_model_id);
  expect(a.model?.model_profile_id).not.toBe(b.model?.model_profile_id);
  expect(a.model?.output_modalities).toEqual(["TEXT"]);
});
test("unsupported protocol, wrong IDs and repeated fallback refuse locally", () => {
  expect(() =>
    providerCommand({ ...draft(), protocol: "ANTHROPIC" }, "provider.a", 0),
  ).toThrow();
  expect(() => providerCommand(draft(), "not_valid_without_dot", 0)).toThrow();
  expect(() => routeCommand("VISION", "model.a", ["model.a"], 1)).toThrow();
  const r = routeCommand("COGNITION", "model.a", ["model.b"], 5);
  expect(r.route?.permitted_privacy).toEqual(["PUBLIC", "PROJECT"]);
});
