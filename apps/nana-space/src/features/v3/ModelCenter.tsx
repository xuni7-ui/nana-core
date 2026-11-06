import { useMemo, useState } from "react";
import {
  ArrowRight,
  Bot,
  Check,
  ChevronDown,
  CircleHelp,
  Layers3,
  Plus,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  X,
} from "lucide-react";
import {
  capabilityCatalog,
  eligibleModels,
  newProviderDraft,
  providerDraftProposal,
  providerPresets,
  readProviderSettings,
  validateProviderDraft,
  type CoreOperation,
  type ProviderDraft,
} from "../../data/provider-center";

import type { ProviderCommand } from "../../data/v2.generated";
import {
  providerCommand,
  modelCommand,
  routeCommand,
} from "../../data/provider-commands";
import { credentialProfiles, vaultMetadata } from "../../data/living";

interface Props {
  settings: unknown;
  available: boolean;
  onNotice: (text: string) => void;
  canConfigure?: boolean;
  busy?: boolean;
  onApply?: (command: ProviderCommand) => Promise<void>;
  onBindCredential?: (providerId: string, revision: number) => Promise<void>;
  onRevokeCredential?: (providerId: string, revision: number) => Promise<void>;
  credentialStatus?: unknown;
  onDiscover?: (providerId: string, revision: number) => Promise<string[]>;
}
const secretLabels = {
  AVAILABLE: "安全凭据可用",
  MISSING: "凭据缺失",
  UNCONFIGURED: "未绑定凭据",
  UNKNOWN: "凭据状态未知",
};
export function ModelCenter({
  settings,
  available,
  onNotice,
  canConfigure = false,
  busy = false,
  onApply,
  onBindCredential,
  onRevokeCredential,
  credentialStatus,
  onDiscover,
}: Props) {
  const view = useMemo(
    () => readProviderSettings(available ? settings : undefined),
    [settings, available],
  );
  const [tab, setTab] = useState<"routes" | "providers" | "models">("routes");
  const [search, setSearch] = useState("");
  const [editor, setEditor] = useState(false);
  const [draft, setDraft] = useState<ProviderDraft>(newProviderDraft);
  const [proposal, setProposal] = useState("");
  const vault = vaultMetadata(credentialStatus);
  const credentials = credentialProfiles(credentialStatus);
  const [providerId, setProviderId] = useState("");
  const [modelId, setModelId] = useState("");
  const [catalog, setCatalog] = useState<Record<string, string[]>>({});
  const [discovering, setDiscovering] = useState<string | null>(null);
  const discover = async (id: string, revision: number) => {
    if (!onDiscover || discovering) return;
    setDiscovering(id);
    try {
      const models = await onDiscover(id, revision);
      setCatalog(current => ({...current, [id]: models}));
      if (!models.length) onNotice("服务商返回的模型列表为空，也可以直接填写模型名称。");
    } catch (error) { onNotice(error instanceof Error ? error.message : "模型列表读取失败，请稍后手动重试。"); }
    finally { setDiscovering(null); }
  };
  const apply = async (make: () => ProviderCommand) => {
    if (!canConfigure || busy || !onApply) return;
    try {
      await onApply(make());
      setValidation([]);
    } catch (error) {
      setValidation([
        error instanceof Error ? error.message : "配置未确认，请查看回执。",
      ]);
    }
  };
  const [validation, setValidation] = useState<string[]>([]);
  const [routeDraft, setRouteDraft] = useState<
    Record<string, { revision?: number; primary: string; fallbacks: string[] }>
  >({});
  const change = <K extends keyof ProviderDraft>(
    key: K,
    value: ProviderDraft[K],
  ) => {
    setDraft((x) => ({ ...x, [key]: value }));
    setProposal("");
    setValidation([]);
  };
  const match = (value: string) =>
    value.toLocaleLowerCase().includes(search.toLocaleLowerCase().trim());
  const source =
    view.state === "CURRENT"
      ? `宿主配置 · revision ${view.revision}`
      : view.state === "INVALID"
        ? "配置投影不兼容，已拒绝展示"
        : "等待宿主配置投影";
  return (
    <div className="v3-model-center">
      <div className="v3-section-top">
        <div>
          <span className="v3-eyebrow">INTELLIGENCE, YOUR WAY</span>
          <h2>能力各有所长，奈奈始终是奈奈。</h2>
          <p>为每一种能力选择合适的资源。模型可替换，身份与经历持续。</p>
        </div>
        <button
          className="button primary"
          onClick={() => {
            setEditor(!editor);
            setProposal("");
          }}
        >
          <Plus size={17} />
          添加供应商草稿
        </button>
      </div>
      <div className="v3-inline-note">
        <ShieldCheck size={17} />
        <span>
          {source}。
          {canConfigure
            ? "宿主已开放配置，提交结果以真实回执为准；配置不会授权模型调用。"
            : "当前连接未开放配置写入；草稿只在本页内存中。"}
        </span>
      </div>
      {(onBindCredential || vault) && view.providers.length > 0 && (
        <section className="v3-card" aria-label="安全凭据绑定">
          <h3>在手机上安全连接模型</h3>
          <p className="v3-muted">凭据通过原生安全输入框直接交给可信宿主，网页不会接触密钥。绑定后需通过已有管理入口明确应用，付费授权与额度保持独立。</p>
          <p className="v3-inline-note" role="status">{vault?.persistent ? `宿主加密保险库 · revision ${vault.revision} · 正常服务重启可恢复绑定` : "尚未确认持久保险库；仅内存绑定在服务重启后需要重新录入"}</p>
          {view.providers.filter(p => p.locality === "REMOTE" && p.revision !== undefined).map(p => (
            <div className="v3-actions" key={p.id}>
            <span className="v3-chip">{p.name} · {secretLabels[credentials.find(x => x.id === p.id)?.state as keyof typeof secretLabels] || "凭据状态待核实"}</span>
            {onBindCredential && <button className="v3-button soft" disabled={busy}
              onClick={() => void onBindCredential(p.id, p.revision!)}>
              {credentials.find(x => x.id === p.id)?.state === "AVAILABLE" ? "轮换" : "绑定"} {p.name} 凭据
            </button>}{onRevokeCredential && <button className="v3-button ghost" disabled={busy}
              onClick={() => void onRevokeCredential(p.id, p.revision!)}>撤销 {p.name} 凭据</button>}</div>
          ))}
          {!onBindCredential && <small className="v3-muted">请使用已配对且具有宿主管理权限的手机绑定、轮换或撤销凭据。</small>}
        </section>
      )}
      {onDiscover && view.providers.length > 0 && <section className="v3-card" aria-label="读取服务商模型">
        <h3>从服务商读取模型</h3><p className="v3-muted">使用服务器已保存的凭据读取列表。不会生成回复或切换路由；列表中的模型仍需配置并验证。</p>
        {view.providers.filter(p => p.locality === "REMOTE" && p.revision !== undefined).map(p => <div key={p.id}>
          <button className="v3-button soft" disabled={busy || discovering !== null} onClick={() => void discover(p.id, p.revision!)}>
            {discovering === p.id ? "正在读取…" : `读取 ${p.name} 模型`}
          </button>
          {catalog[p.id] && <label>服务商返回的模型<select defaultValue="" onChange={e => {
            if (!e.target.value) return;
            setDraft(current => ({...current, modelId:e.target.value, alias:e.target.value}));
            setProviderId(p.id); setEditor(true); setProposal(""); setValidation([]);
          }}><option value="">选择后填入配置草稿</option>{catalog[p.id].map(id => <option key={id} value={id}>{id}</option>)}</select></label>}
        </div>)}
      </section>}
      <div className="v3-model-toolbar">
        <div className="v3-segmented" aria-label="模型中心分类">
          {(
            [
              ["routes", "能力路由"],
              ["providers", "供应商"],
              ["models", "模型库"],
            ] as const
          ).map(([id, title]) => (
            <button
              key={id}
              aria-pressed={tab === id}
              className={tab === id ? "active" : ""}
              onClick={() => setTab(id)}
            >
              {title}
            </button>
          ))}
        </div>
        <label className="v3-search">
          <Search size={17} />
          <input
            aria-label="搜索模型与能力"
            placeholder="搜索供应商、模型、能力…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      {editor && (
        <section
          className="v3-card v3-provider-editor"
          aria-label="供应商配置草稿"
        >
          <div className="v3-card-heading">
            <div>
              <span className="v3-eyebrow">LOCAL DRAFT</span>
              <h3>准备一个新的模型资源</h3>
            </div>
            <button
              className="icon-button"
              aria-label="关闭供应商草稿"
              onClick={() => {
                setEditor(false);
                setDraft(newProviderDraft());
                setProposal("");
                setValidation([]);
              }}
            >
              <X size={19} />
            </button>
          </div>
          <p className="v3-muted">
            不接收 API Key。后续由可信宿主 SecretResolver
            绑定；预设仅帮助填写协议意向。
          </p>
          <div className="v3-form-grid">
            <label>
              供应商配置 ID
              <input
                aria-label="供应商配置 ID"
                value={providerId}
                placeholder="provider.example"
                onChange={(e) => setProviderId(e.target.value)}
              />
            </label>
            <label>
              模型配置 ID
              <input
                aria-label="模型配置 ID"
                value={modelId}
                placeholder="model.example"
                onChange={(e) => setModelId(e.target.value)}
              />
            </label>
            <label>
              供应商预设
              <select
                value={draft.preset}
                onChange={(e) => {
                  setDraft(newProviderDraft(e.target.value));
                  setProposal("");
                  setValidation([]);
                }}
              >
                {providerPresets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              显示名称
              <input
                value={draft.displayName}
                maxLength={96}
                onChange={(e) => change("displayName", e.target.value)}
              />
            </label>
            <label className="v3-field-wide">
              已确认的 Base URL
              <input
                placeholder={
                  draft.protocol === "LOCAL"
                    ? "本地适配，不配置 remote URL"
                    : "https://官方确认的API地址"
                }
                value={draft.baseUrl}
                maxLength={512}
                onChange={(e) => change("baseUrl", e.target.value)}
                disabled={draft.protocol === "LOCAL"}
                autoComplete="off"
              />
            </label>
            <label>
              远端 Model ID
              <input
                value={draft.modelId}
                placeholder="填写准确的模型 ID"
                maxLength={96}
                onChange={(e) => change("modelId", e.target.value)}
              />
            </label>
            <label>
              模型别名（本地草稿）
              <input
                value={draft.alias}
                placeholder="例如：日常聊天"
                maxLength={96}
                onChange={(e) => change("alias", e.target.value)}
              />
            </label>
            <label>
              用途
              <select
                value={draft.operation}
                onChange={(e) =>
                  change("operation", e.target.value as CoreOperation)
                }
              >
                {capabilityCatalog
                  .filter((c) => c.operation)
                  .map((c) => (
                    <option key={c.id} value={c.operation}>
                      {c.title}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              超时上限 / ms
              <input
                type="number"
                min={50}
                max={600000}
                step={50}
                value={draft.timeoutMs}
                onChange={(e) => change("timeoutMs", Number(e.target.value))}
              />
            </label>
            <label>
              上下文上限
              <input
                type="number"
                min={256}
                max={2000000}
                value={draft.contextLimit}
                onChange={(e) => change("contextLimit", Number(e.target.value))}
              />
            </label>
            <label>
              输出上限
              <input
                type="number"
                min={1}
                max={131072}
                value={draft.outputLimit}
                onChange={(e) => change("outputLimit", Number(e.target.value))}
              />
            </label>
          </div>
          <div className="v3-inline-note">
            <CircleHelp size={17} />
            <span>
              {providerPresets.find((p) => p.id === draft.preset)?.note} · 协议{" "}
              {draft.protocol}。草稿尚未验证；已保存的供应商可在上方读取实际模型列表。
            </span>
          </div>
          <div className="v3-tag-row">
            <span className="v3-tag">PUBLIC / PROJECT 意向</span>
            <span className="v3-tag">费用与隐私仍受原 Core 求交限制</span>
            <span className="v3-tag">远程 SECRET 禁止</span>
          </div>
          {validation.length > 0 && (
            <div className="v3-form-errors" role="alert">
              {validation.map((error) => (
                <p key={error}>{error}</p>
              ))}
            </div>
          )}
          <div className="v3-actions">
            <button
              className="button primary"
              onClick={() => {
                const errors = validateProviderDraft(draft);
                setValidation(errors);
                if (!errors.length) {
                  setProposal(
                    JSON.stringify(
                      providerDraftProposal(draft, view.revision),
                      null,
                      2,
                    ),
                  );
                  onNotice(
                    "配置草稿已整理，仅留在本页；没有写入云端或发起模型请求。",
                  );
                }
              }}
            >
              <Check size={16} />
              整理配置草稿
            </button>
            <button
              className="button"
              disabled={
                !canConfigure ||
                busy ||
                !providerId ||
                view.revision === undefined ||
                view.providers.some((p) => p.id === providerId)
              }
              onClick={() =>
                void apply(() =>
                  providerCommand(draft, providerId, view.revision!),
                )
              }
            >
              应用新供应商
            </button>
            <button
              className="button"
              disabled={
                !canConfigure ||
                busy ||
                !modelId ||
                !view.providers.some((p) => p.id === providerId) ||
                view.revision === undefined
              }
              onClick={() =>
                void apply(() =>
                  modelCommand(draft, providerId, modelId, view.revision!),
                )
              }
            >
              注册模型配置
            </button>
            <button
              className="button"
              onClick={() => {
                setDraft(newProviderDraft());
                setProposal("");
                setValidation([]);
              }}
            >
              重置草稿
            </button>
            <button
              className="button"
              disabled
              title="需要后端支持：明确付费授权与专用测试端点"
            >
              测试模型 · 需要后端支持
            </button>
          </div>
          {proposal && (
            <details className="v3-draft-result">
              <summary>
                查看本地审阅草稿（不是应用成功回执）
                <ChevronDown size={15} />
              </summary>
              <pre>{proposal}</pre>
            </details>
          )}
        </section>
      )}
      {tab === "routes" && (
        <>
          <div className="v3-capability-grid">
            {capabilityCatalog
              .filter((c) => match(`${c.title} ${c.id} ${c.detail}`))
              .map((capability) => {
                const op = capability.operation;
                const route = view.routes.find((r) => r.operation === op);
                const primary = view.models.find(
                  (m) => m.id === route?.primary,
                );
                const provider = view.providers.find(
                  (p) => p.id === primary?.providerId,
                );
                const candidates = op ? eligibleModels(view, op) : [];
                const edited = op ? routeDraft[op] : undefined;
                const stale = Boolean(
                  edited && edited.revision !== view.revision,
                );
                return (
                  <section
                    className="v3-card v3-capability-card"
                    key={capability.id}
                  >
                    <div className="v3-card-heading">
                      <span className="v3-feature-icon">
                        <Layers3 size={19} />
                      </span>
                      <span
                        className={`v3-tag ${route?.enabled && primary?.enabled && provider?.enabled ? "good" : ""}`}
                      >
                        {!op
                          ? "未来扩展"
                          : route
                            ? route.enabled
                              ? "已配置路由"
                              : "路由已停用"
                            : "尚未配置"}
                      </span>
                    </div>
                    <h3>{capability.title}</h3>
                    <p className="v3-muted">{capability.detail}</p>
                    <div className="v3-model-target">
                      <Bot size={16} />
                      <div>
                        <strong>
                          {primary?.remoteModel || "等待明确配置"}
                        </strong>
                        <small>{provider?.name || "没有已配置的供应商"}</small>
                      </div>
                    </div>
                    {route && (
                      <div className="v3-route-meta">
                        <span>备用 {route.fallbacks.length} 个</span>
                        <span>超时上限 {route.timeoutMs ?? "未知"} ms</span>
                      </div>
                    )}
                    {op && (
                      <details className="v3-route-editor">
                        <summary>
                          <SlidersHorizontal size={15} />
                          准备路由调整
                          <ChevronDown size={15} />
                        </summary>
                        <label>
                          Primary
                          <select
                            aria-label={`${capability.title} Primary`}
                            value={edited?.primary ?? route?.primary ?? ""}
                            onChange={(e) =>
                              setRouteDraft((x) => ({
                                ...x,
                                [op]: {
                                  revision: view.revision,
                                  primary: e.target.value,
                                  fallbacks: [],
                                },
                              }))
                            }
                          >
                            <option value="">
                              选择已启用且支持此能力的模型
                            </option>
                            {candidates.map((m) => (
                              <option key={m.id} value={m.id}>
                                {
                                  view.providers.find(
                                    (p) => p.id === m.providerId,
                                  )?.name
                                }{" "}
                                / {m.remoteModel} · {m.id}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Fallbacks（按选择次序排序，最多8个）
                          <select
                            aria-label={`${capability.title} Fallbacks`}
                            value=""
                            onChange={(e) => {
                              const selected = e.target.value;
                              if (!selected) return;
                              setRouteDraft((x) => ({
                                ...x,
                                [op]: {
                                  revision: view.revision,
                                  primary:
                                    edited?.primary ?? route?.primary ?? "",
                                  fallbacks: [
                                    ...(edited?.fallbacks ??
                                      route?.fallbacks ??
                                      []),
                                    selected,
                                  ].slice(0, 8),
                                },
                              }));
                            }}
                          >
                            <option value="">添加备用模型…</option>
                            {candidates
                              .filter(
                                (m) =>
                                  m.id !==
                                    (edited?.primary ?? route?.primary) &&
                                  !(
                                    edited?.fallbacks ??
                                    route?.fallbacks ??
                                    []
                                  ).includes(m.id),
                              )
                              .map((m) => (
                                <option key={m.id} value={m.id}>
                                  {
                                    view.providers.find(
                                      (p) => p.id === m.providerId,
                                    )?.name
                                  }{" "}
                                  / {m.remoteModel} · {m.id}
                                </option>
                              ))}
                          </select>
                        </label>
                        <ol className="v3-fallback-list">
                          {(edited?.fallbacks ?? route?.fallbacks ?? []).map(
                            (id, index) => (
                              <li key={id}>
                                <span>
                                  {index + 1}.{" "}
                                  {view.models.find((m) => m.id === id)
                                    ?.remoteModel || id}{" "}
                                  · {id}
                                </span>
                                <button
                                  className="button"
                                  aria-label={`移除备用模型 ${id}`}
                                  onClick={() =>
                                    setRouteDraft((x) => ({
                                      ...x,
                                      [op]: {
                                        revision: view.revision,
                                        primary:
                                          edited?.primary ??
                                          route?.primary ??
                                          "",
                                        fallbacks: (
                                          edited?.fallbacks ??
                                          route?.fallbacks ??
                                          []
                                        ).filter((item) => item !== id),
                                      },
                                    }))
                                  }
                                >
                                  移除草稿项
                                </button>
                              </li>
                            ),
                          )}
                        </ol>
                        {stale && (
                          <p role="alert">
                            宿主 revision 已变化；请取消旧草稿后重新选择。
                          </p>
                        )}
                        <p className="v3-muted">
                          {candidates.length
                            ? "选择先留作草稿；仅显式提交后以云端回执为准。备用只在未 dispatch 前选择。"
                            : "当前没有符合此能力的已启用模型，不能凭供应商品牌推断支持。"}
                        </p>
                        {edited && (
                          <div className="v3-actions">
                            <span className="v3-tag">
                              本地草稿 · 未应用{stale ? " · 已过时" : ""}
                            </span>
                            <button
                              className="button primary"
                              disabled={
                                !canConfigure ||
                                busy ||
                                stale ||
                                !edited.primary ||
                                view.revision === undefined
                              }
                              onClick={() =>
                                void apply(() =>
                                  routeCommand(
                                    op,
                                    edited.primary,
                                    edited.fallbacks,
                                    view.revision!,
                                  ),
                                )
                              }
                            >
                              应用此路由
                            </button>
                            <button
                              className="button"
                              onClick={() =>
                                setRouteDraft((x) => {
                                  const next = { ...x };
                                  delete next[op];
                                  return next;
                                })
                              }
                            >
                              取消路由草稿
                            </button>
                          </div>
                        )}
                        {op === "EMBED" && (
                          <p className="v3-inline-note">
                            Embedding
                            模型、版本或维度改变可能要求重建索引；此处不会覆盖现有记忆向量。
                          </p>
                        )}
                      </details>
                    )}
                  </section>
                );
              })}
          </div>
          <div className="v3-inline-note">
            <ShieldCheck size={17} />
            <span>
              UNKNOWN 请求不会因切换路由而重发。已 dispatch
              的失败或无效响应不会在 V1 自动换模型。预算显示上限，不是实际账单。
            </span>
          </div>
        </>
      )}
      {tab === "providers" && (
        <div className="v3-provider-list">
          {view.providers
            .filter((p) => match(`${p.name} ${p.id} ${p.protocol}`))
            .map((provider) => (
              <section className="v3-card" key={provider.id}>
                <div className="v3-card-heading">
                  <div>
                    <span className="v3-eyebrow">{provider.id}</span>
                    <h3>{provider.name}</h3>
                  </div>
                  <span className={`v3-tag ${provider.enabled ? "good" : ""}`}>
                    {provider.enabled ? "已启用" : "已停用"}
                  </span>
                </div>
                <p>
                  {provider.baseUrl ||
                    (provider.protocol === "LOCAL"
                      ? "宿主本地资源"
                      : "地址未提供或不可安全展示")}
                </p>
                <div className="v3-tag-row">
                  <span className="v3-tag">{provider.protocol}</span>
                  <span className="v3-tag">
                    {secretLabels[provider.secretState]}
                  </span>
                  {provider.privacy.map((p) => (
                    <span className="v3-tag" key={p}>
                      {p}
                    </span>
                  ))}
                </div>
                <button
                  className="button"
                  disabled={
                    !canConfigure || busy || view.revision === undefined
                  }
                  onClick={() =>
                    void apply(() => ({
                      operation: provider.enabled
                        ? "DISABLE_PROVIDER"
                        : "ENABLE_PROVIDER",
                      target_id: provider.id,
                      expected_revision: view.revision!,
                    }))
                  }
                >
                  {provider.enabled ? "停用供应商" : "启用供应商"}
                </button>
                <div className="v3-route-meta">
                  <span>超时上限 {provider.timeoutMs ?? "未知"} ms</span>
                  <span>
                    费用 ceiling {provider.costCeiling ?? "未知"} · Core 单位
                  </span>
                </div>
              </section>
            ))}
          {view.providers.length === 0 && (
            <div className="v3-empty">
              <Sparkles size={25} />
              <h3>给每种能力，留一个合适的位置</h3>
              <p>
                宿主尚未返回供应商配置。你可以先整理草稿；没有默认供应商被自动选择。
              </p>
              <button className="button" onClick={() => setEditor(true)}>
                准备供应商草稿
                <ArrowRight size={16} />
              </button>
            </div>
          )}
          <section className="v3-card">
            <h3>供应商预设目录</h3>
            <p className="v3-muted">
              下列是可选填写模板，不是已发现模型、可用状态或兼容性验收结论。
            </p>
            <div className="v3-preset-grid">
              {providerPresets
                .filter((p) => match(`${p.name} ${p.protocol}`))
                .map((p) => (
                  <button
                    className="v3-preset"
                    key={p.id}
                    onClick={() => {
                      setDraft(newProviderDraft(p.id));
                      setEditor(true);
                      setProposal("");
                      setValidation([]);
                    }}
                  >
                    <Bot size={18} />
                    <span>
                      {p.name}
                      <small>{p.protocol}</small>
                    </span>
                    <Plus size={15} />
                  </button>
                ))}
            </div>
          </section>
        </div>
      )}
      {tab === "models" && (
        <div className="v3-provider-list">
          {view.models
            .filter((m) =>
              match(`${m.remoteModel} ${m.id} ${m.operations.join(" ")}`),
            )
            .map((model) => (
              <section className="v3-card" key={model.id}>
                <div className="v3-card-heading">
                  <div>
                    <span className="v3-eyebrow">
                      {view.providers.find((p) => p.id === model.providerId)
                        ?.name || model.providerId}
                    </span>
                    <h3>{model.remoteModel}</h3>
                  </div>
                  <span className={`v3-tag ${model.enabled ? "good" : ""}`}>
                    {model.enabled ? "配置启用" : "已停用"}
                  </span>
                </div>
                <p className="v3-muted">
                  {model.id} · 版本 {model.version}
                </p>
                <div className="v3-tag-row">
                  {model.operations.map((op) => (
                    <span className="v3-tag" key={op}>
                      {op}
                    </span>
                  ))}
                </div>
                <div className="v3-route-meta">
                  <span>
                    输入 {model.inputModalities.join(" / ") || "未提供"}
                  </span>
                  <span>
                    输出 {model.outputModalities.join(" / ") || "未提供"}
                  </span>
                  <span>Context {model.contextLimit ?? "未知"}</span>
                  <span>Output {model.outputLimit ?? "未知"}</span>
                </div>
                <p className="v3-muted">
                  这是宿主声明的模型能力，不能替代当前版本的实际 Provider 资格。
                </p>
              </section>
            ))}
          {view.models.length === 0 && (
            <div className="v3-empty">
              <Bot size={26} />
              <h3>还没有可展示的模型</h3>
              <p>
                只列出真实配置投影中的模型。不请求第三方模型目录，也不自动注册预设模型。
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
