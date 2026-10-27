/** Exact existing Core commands. No credential input, network probe or new authority. */
import type {
  ProviderCommand,
  ProviderProfile,
  ModelProfile,
} from "./v2.generated";
import {
  validateProviderDraft,
  safeProviderUrl,
  type ProviderDraft,
  type CoreOperation,
} from "./provider-center";
const id = /^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$/;
function profile(value: string) {
  if (!id.test(value))
    throw new Error("配置 ID 应为 provider.name / model.name 形式。");
  return value;
}
export function providerCommand(
  draft: ProviderDraft,
  providerId: string,
  revision: number,
): ProviderCommand {
  const errors = validateProviderDraft(draft);
  if (errors.length) throw new Error(errors[0]);
  if (draft.protocol !== "OPENAI_COMPATIBLE_CHAT")
    throw new Error(
      "此版本仅支持 OpenAI-compatible 远程配置；其他协议保留为草稿。",
    );
  const provider: ProviderProfile = {
    provider_profile_id: profile(providerId),
    display_name: draft.displayName.trim(),
    protocol: "OPENAI_COMPATIBLE_CHAT",
    base_url: safeProviderUrl(draft.baseUrl),
    locality: "REMOTE",
    permitted_privacy: ["PUBLIC", "PROJECT"],
    default_timeout_ms: draft.timeoutMs,
    default_cost_ceiling: 1000,
    enabled: true,
  };
  return {
    operation: "UPSERT_PROVIDER",
    expected_revision: revision,
    provider,
  };
}
export function modelCommand(
  draft: ProviderDraft,
  providerId: string,
  modelId: string,
  revision: number,
): ProviderCommand {
  const errors = validateProviderDraft(draft);
  if (errors.length) throw new Error(errors[0]);
  const op = draft.operation;
  const inputs: Partial<
    Record<CoreOperation, "TEXT" | "IMAGE" | "AUDIO" | "VIDEO">
  > = {
    VISION: "IMAGE",
    VIDEO_UNDERSTAND: "VIDEO",
    STT: "AUDIO",
    AUDIO_UNDERSTAND: "AUDIO",
  };
  const input = inputs[op] ?? "TEXT";
  const output =
    op === "EMBED"
      ? "EMBEDDING"
      : op === "IMAGE_GENERATE"
        ? "IMAGE"
        : ["TTS", "AUDIO_GENERATE"].includes(op)
          ? "AUDIO"
          : "TEXT";
  const model: ModelProfile = {
    model_profile_id: profile(modelId),
    provider_profile_id: profile(providerId),
    remote_model_id: draft.modelId,
    model_version: "user-configured",
    operations: [op],
    input_modalities: [input],
    output_modalities: [output],
    context_limit: draft.contextLimit,
    output_limit: draft.outputLimit,
    enabled: true,
  };
  return { operation: "UPSERT_MODEL", expected_revision: revision, model };
}
export function routeCommand(
  op: CoreOperation,
  primary: string,
  fallbacks: string[],
  revision: number,
): ProviderCommand {
  profile(primary);
  fallbacks.forEach(profile);
  if (new Set([primary, ...fallbacks]).size !== fallbacks.length + 1)
    throw new Error("Primary 和备用模型不能重复。");
  return {
    operation: "SET_CAPABILITY_ROUTE",
    expected_revision: revision,
    route: {
      operation: op,
      primary_model_profile_id: primary,
      fallback_model_profile_ids: fallbacks,
      permitted_privacy: ["PUBLIC", "PROJECT"],
      timeout_ceiling_ms: 15000,
      cost_ceiling: 1000,
      enabled: true,
    },
  };
}
