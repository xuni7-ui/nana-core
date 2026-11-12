/** A sanitized view of the existing host-local ProviderConfiguration v1.
 * These UI drafts are memory-only. They neither resolve secrets nor issue requests.
 */
export const coreOperations = [
  "COGNITION",
  "VISION",
  "VIDEO_UNDERSTAND",
  "STT",
  "TTS",
  "EMBED",
  "AUDIO_UNDERSTAND",
  "IMAGE_GENERATE",
  "AUDIO_GENERATE",
] as const;
export type CoreOperation = (typeof coreOperations)[number];
export const capabilityCatalog: {
  operation?: CoreOperation;
  id: string;
  title: string;
  detail: string;
}[] = [
  {
    operation: "COGNITION",
    id: "TEXT_REASONING",
    title: "文本与推理",
    detail: "TEXT / REASONING · 原 CognitionSession",
  },
  {
    operation: "VISION",
    id: "VISION",
    title: "图片理解",
    detail: "VISION · 保留 H1 来源与语义契约",
  },
  {
    operation: "VIDEO_UNDERSTAND",
    id: "VIDEO",
    title: "视频理解",
    detail: "VIDEO_UNDERSTAND · 采样帧语义",
  },
  {
    operation: "STT",
    id: "STT_ASR",
    title: "语音转文字",
    detail: "STT / ASR · 不等于麦克风权限",
  },
  {
    operation: "TTS",
    id: "TTS",
    title: "文字转语音",
    detail: "TTS · 独立能力端口",
  },
  {
    operation: "EMBED",
    id: "EMBEDDING",
    title: "向量嵌入",
    detail: "EMBED · 可重建缓存，不是记忆真相",
  },
  {
    operation: "AUDIO_UNDERSTAND",
    id: "AUDIO",
    title: "音频理解",
    detail: "AUDIO_UNDERSTAND · 独立能力端口",
  },
  {
    operation: "IMAGE_GENERATE",
    id: "IMAGE_GENERATE",
    title: "图片生成",
    detail: "IMAGE_GENERATE · 独立能力端口",
  },
  {
    operation: "AUDIO_GENERATE",
    id: "AUDIO_GENERATE",
    title: "音频生成",
    detail: "AUDIO_GENERATE · 独立能力端口",
  },
  {
    id: "RERANK",
    title: "检索重排",
    detail: "未来扩展位 · 当前 Core 无对应 operation",
  },
  {
    id: "MULTIMODAL",
    title: "实时音视频",
    detail: "未来扩展位 · 不假定统一协议已经支持",
  },
];
export interface ProviderPreset {
  id: string;
  name: string;
  protocol: string;
  note: string;
  baseUrl?: string;
  suggestedModelId?: string;
}
export const providerPresets: readonly ProviderPreset[] = [
  {
    id: "openai",
    name: "OpenAI",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    baseUrl: "https://api.openai.com/v1",
    note: "Chat Completions 适配；Responses 需另行资格",
  },
  {
    id: "anthropic",
    name: "Anthropic",
    protocol: "ANTHROPIC",
    baseUrl: "https://api.anthropic.com/v1",
    note: "原生 Messages 文字认知与对话；流式和多模态尚未接通",
  },
  {
    id: "gemini",
    name: "Google Gemini",
    protocol: "GEMINI_NATIVE",
    note: "原生协议扩展位，不套用 OpenAI 请求",
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    baseUrl: "https://api.deepseek.com",
    suggestedModelId: "deepseek-chat",
    note: "历史文本资格不代表当前宿主已配置",
  },
  {
    id: "qwen",
    name: "阿里云百炼 / Qwen",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    note: "具体地域、模型和能力由官方配置确认",
  },
  {
    id: "siliconflow",
    name: "硅基流动",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    note: "预设而非兼容性资格",
  },
  {
    id: "doubao",
    name: "火山方舟 / 豆包",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    note: "endpoint/model ID 需宿主确认",
  },
  {
    id: "zhipu",
    name: "智谱",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    note: "具体模型和参数映射待资格",
  },
  {
    id: "groq",
    name: "Groq",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    note: "能力依实际模型及已验证协议",
  },
  {
    id: "ollama",
    name: "Ollama",
    protocol: "LOCAL",
    note: "本地运行需要显式本地适配，不能放宽 remote HTTPS",
  },
  {
    id: "compatible",
    name: "通用 OpenAI-Compatible",
    protocol: "OPENAI_COMPATIBLE_CHAT",
    note: "仅声明协议意向，不自动发现或启用模型",
  },
] as const;
/** Both editors use this registry. Unadapted protocols remain advanced drafts. */
export const modelSetupPresets = providerPresets.filter(preset =>
  preset.protocol === "OPENAI_COMPATIBLE_CHAT" || preset.protocol === "ANTHROPIC",
);
export interface ProviderView {
  id: string;
  name: string;
  protocol: string;
  baseUrl: string;
  enabled: boolean;
  secretState: "AVAILABLE" | "MISSING" | "UNCONFIGURED" | "UNKNOWN";
  privacy: string[];
  timeoutMs?: number;
  costCeiling?: number;
  revision?: number;
  locality?: string;
}
export interface ModelView {
  id: string;
  providerId: string;
  remoteModel: string;
  version: string;
  operations: CoreOperation[];
  inputModalities: string[];
  outputModalities: string[];
  contextLimit?: number;
  outputLimit?: number;
  enabled: boolean;
}
export interface RouteView {
  operation: CoreOperation;
  primary: string;
  fallbacks: string[];
  timeoutMs?: number;
  costCeiling?: number;
  enabled: boolean;
}
export interface ProviderSettingsView {
  state: "CURRENT" | "UNAVAILABLE" | "INVALID";
  revision?: number;
  providers: ProviderView[];
  models: ModelView[];
  routes: RouteView[];
}
const record = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
const string = (value: unknown, max = 192) =>
  typeof value === "string" ? value.slice(0, max) : "";
const strings = (value: unknown) =>
  Array.isArray(value)
    ? value
        .filter((x): x is string => typeof x === "string")
        .slice(0, 16)
        .map((x) => x.slice(0, 96))
    : [];
const number = (value: unknown) =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0
    ? value
    : undefined;
const protocols = [
  "OPENAI_COMPATIBLE_CHAT",
  "LOCAL",
  "SYNTHETIC_LOOPBACK",
  "OPENAI_RESPONSES",
  "ANTHROPIC",
  "GEMINI_NATIVE",
  "QWEN_NATIVE",
  "CUSTOM",
];
const profileId = /^[a-z][a-z0-9._-]{0,95}$/;
const operation = (value: unknown): value is CoreOperation =>
  coreOperations.includes(value as CoreOperation);
export function safeProviderUrl(value: unknown): string {
  if (typeof value !== "string" || value.length > 512 || /[\s%\\]/.test(value))
    return "";
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      !url.hostname.includes(".") ||
      (url.port && url.port !== "443")
    )
      return "";
    if (
      !/^(\/[A-Za-z0-9_-]+)*\/?$/.test(url.pathname) ||
      url.pathname.endsWith("/chat/completions")
    )
      return "";
    if (
      /^\d+(\.\d+){3}$/.test(url.hostname) ||
      /\.(local|localhost|internal)$/.test(url.hostname)
    )
      return "";
    return url.origin + url.pathname.replace(/\/$/, "");
  } catch {
    return "";
  }
}
/** Explicit allowlist: unexpected fields (including accidental credentials) never reach JSX. */
export function readProviderSettings(value: unknown): ProviderSettingsView {
  const raw = record(value);
  if (raw.state === "UNAVAILABLE" || !Object.keys(raw).length)
    return { state: "UNAVAILABLE", providers: [], models: [], routes: [] };
  if (
    raw.schema_version !== 1 ||
    raw.execution_authority !== false ||
    !Array.isArray(raw.providers) ||
    !Array.isArray(raw.models) ||
    !Array.isArray(raw.routes) ||
    number(raw.revision) === undefined
  )
    return { state: "INVALID", providers: [], models: [], routes: [] };
  const providers: ProviderView[] = raw.providers.slice(0, 64).map((value) => {
    const row = record(value);
    return {
      id: string(row.provider_profile_id, 96),
      name: string(row.display_name, 96),
      protocol: string(row.protocol, 48),
      baseUrl: safeProviderUrl(row.base_url),
      enabled: row.enabled === true,
      revision: number(row.revision),
      locality: string(row.locality, 32),
      secretState: ["AVAILABLE", "MISSING", "UNCONFIGURED"].includes(
        String(row.secret_state),
      )
        ? (row.secret_state as ProviderView["secretState"])
        : "UNKNOWN",
      privacy: strings(row.permitted_privacy).filter((x) =>
        ["PUBLIC", "PROJECT", "PERSONAL", "SECRET"].includes(x),
      ),
      timeoutMs: number(row.default_timeout_ms),
      costCeiling: number(row.default_cost_ceiling),
    };
  });
  const models: ModelView[] = raw.models.slice(0, 256).map((value) => {
    const row = record(value);
    return {
      id: string(row.model_profile_id, 96),
      providerId: string(row.provider_profile_id, 96),
      remoteModel: string(row.remote_model_id, 96),
      version: string(row.model_version, 96),
      operations: strings(row.operations).filter(operation),
      inputModalities: strings(row.input_modalities),
      outputModalities: strings(row.output_modalities),
      contextLimit: number(row.context_limit),
      outputLimit: number(row.output_limit),
      enabled: row.enabled === true,
    };
  });
  const routes: RouteView[] = raw.routes.slice(0, 9).map((value) => {
    const row = record(value);
    return {
      operation: row.operation as CoreOperation,
      primary: string(row.primary_model_profile_id, 96),
      fallbacks: strings(row.fallback_model_profile_ids),
      timeoutMs: number(row.timeout_ceiling_ms),
      costCeiling: number(row.cost_ceiling),
      enabled: row.enabled === true,
    };
  });
  const providerIds = providers.map((x) => x.id),
    modelIds = models.map((x) => x.id);
  if (
    new Set(providerIds).size !== providerIds.length ||
    new Set(modelIds).size !== modelIds.length ||
    providers.some(
      (x) =>
        !profileId.test(x.id) ||
        !x.name ||
        !protocols.includes(x.protocol) ||
        (x.protocol !== "LOCAL" &&
          x.protocol !== "SYNTHETIC_LOOPBACK" &&
          x.privacy.includes("SECRET")),
    ) ||
    models.some(
      (x) =>
        !profileId.test(x.id) ||
        !x.remoteModel ||
        !x.operations.length ||
        !providerIds.includes(x.providerId),
    ) ||
    routes.some(
      (x) =>
        !operation(x.operation) ||
        !modelIds.includes(x.primary) ||
        x.fallbacks.some((id) => !modelIds.includes(id)),
    ) ||
    new Set(routes.map((x) => x.operation)).size !== routes.length
  )
    return { state: "INVALID", providers: [], models: [], routes: [] };
  return {
    state: "CURRENT",
    revision: number(raw.revision),
    providers,
    models,
    routes,
  };
}
export function eligibleModels(
  view: ProviderSettingsView,
  op: CoreOperation,
): ModelView[] {
  return view.models.filter(
    (model) =>
      model.enabled &&
      model.operations.includes(op) &&
      view.providers.some(
        (provider) => provider.id === model.providerId && provider.enabled,
      ),
  );
}
export interface ProviderDraft {
  preset: string;
  displayName: string;
  protocol: string;
  baseUrl: string;
  modelId: string;
  alias: string;
  operation: CoreOperation;
  timeoutMs: number;
  contextLimit: number;
  outputLimit: number;
}
export function newProviderDraft(presetId = "compatible"): ProviderDraft {
  const preset =
    providerPresets.find((x) => x.id === presetId) ||
    providerPresets[providerPresets.length - 1];
  return {
    preset: preset.id,
    displayName: preset.name,
    protocol: preset.protocol,
    baseUrl: preset.baseUrl ?? "",
    modelId: preset.suggestedModelId ?? "",
    alias: "",
    operation: "COGNITION",
    timeoutMs: 120000,
    contextLimit: 8192,
    outputLimit: 1024,
  };
}
export function validateProviderDraft(draft: ProviderDraft, section: "ALL" | "PROVIDER" | "MODEL" = "ALL"): string[] {
  const errors: string[] = [];
  if (section !== "MODEL" && !draft.displayName.trim()) errors.push("请填写供应商显示名称。");
  if (section !== "MODEL") {
  if (draft.protocol === "LOCAL") {
    if (draft.baseUrl)
      errors.push("LOCAL 草稿不使用 remote Base URL；需宿主本地适配器。");
  } else if (!safeProviderUrl(draft.baseUrl))
    errors.push(
      "请使用已确认的 HTTPS Base URL；不能包含凭据、查询参数或 completion 路径。",
    );
  }
  if (section !== "PROVIDER" && !/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}$/.test(draft.modelId))
    errors.push("请填写明确的远端 Model ID（最多96字符）。");
  if (section !== "MODEL" && (
    !Number.isSafeInteger(draft.timeoutMs) ||
    draft.timeoutMs < 50 ||
    draft.timeoutMs > 600000
  ))
    errors.push("超时必须介于50与600000ms；实际仍与运行时上限求交。");
  if (section !== "PROVIDER" && (
    !Number.isSafeInteger(draft.contextLimit) ||
    !Number.isSafeInteger(draft.outputLimit) ||
    draft.contextLimit < 256 ||
    draft.contextLimit > 2000000 ||
    draft.outputLimit < 1 ||
    draft.outputLimit > 131072
  ))
    errors.push("上下文或输出上限超出 Core DTO 范围。");
  return errors;
}
/** A review proposal, deliberately not a Core command and with no secret/reference. */
export function providerDraftProposal(draft: ProviderDraft, revision?: number) {
  const errors = validateProviderDraft(draft);
  if (errors.length) throw new Error(errors[0]);
  return {
    kind: "NANA_SPACE_PROVIDER_REVIEW_DRAFT",
    state: "LOCAL_DRAFT_NOT_APPLIED",
    based_on_revision: revision ?? null,
    provider: {
      display_name: draft.displayName.trim(),
      protocol: draft.protocol,
      base_url: draft.baseUrl ? safeProviderUrl(draft.baseUrl) : null,
    },
    model: {
      remote_model_id: draft.modelId,
      alias: draft.alias.trim(),
      operation: draft.operation,
      context_limit: draft.contextLimit,
      output_limit: draft.outputLimit,
    },
    timeout_ms: draft.timeoutMs,
    secret_binding: "HOST_SECRET_RESOLVER_REQUIRED",
    no_network_request: true,
    execution_authority: false,
  } as const;
}
