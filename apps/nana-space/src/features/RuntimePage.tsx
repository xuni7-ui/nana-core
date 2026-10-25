import { useState } from "react";
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Database,
  FileJson,
  Fingerprint,
  HeartPulse,
  Layers3,
  LockKeyhole,
  Radio,
  RefreshCw,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import {
  Badge,
  Empty,
  PageHeading,
  Panel,
  SectionHeading,
} from "../components/ui";
import type { InspectorSnapshot, SpaceSnapshot } from "../data/contracts";
import { contractRegistry } from "../data/registry";
import "./settings.css";

interface RuntimeProps {
  data: SpaceSnapshot;
  inspector: InspectorSnapshot | null;
  onImport: (file: File) => Promise<void>;
  onClear: () => void;
  notify: (message: string) => void;
}

const sectionNames: Record<string, string> = {
  runtime: "生命周期",
  goals: "目标",
  activities: "活动",
  concerns: "关注事项",
  needs: "需要",
  affect: "状态投影",
  interests: "兴趣",
  suppressed_deferred: "暂缓事项",
  decisions: "决策元数据",
  experience: "经历元数据",
  provenance: "来源",
  authority: "权限边界",
  unknown: "未知结果",
  provider: "模型资源",
  queue: "观察队列",
  source_lifecycle: "来源生命周期",
  health: "健康检查",
  skills: "技能",
  world: "世界状态",
  learning: "学习",
};
const inspectedSections = Object.keys(sectionNames);
const shortDate = (microseconds: number) => {
  const date = new Date(microseconds / 1000);
  return Number.isFinite(date.getTime())
    ? date.toLocaleString("zh-CN", { hour12: false })
    : "UNKNOWN";
};

export function RuntimePage({
  data,
  inspector,
  onImport,
  onClear,
  notify,
}: RuntimeProps) {
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const activeGoals = data.goals.filter(
    (goal) => goal.state === "ACTIVE",
  ).length;
  const blockedGoals = data.goals.filter((goal) => goal.state === "BLOCKED");
  const unknownGoals = data.goals.filter((goal) => goal.state === "UNKNOWN");
  async function importFile(file: File | undefined) {
    if (!file) return;
    setImportError("");
    if (file.size > 2 * 1024 * 1024) {
      setImportError("文件超过 2 MB，请导出有界 Inspector Snapshot。");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".json")) {
      setImportError("请选择 Inspector 导出的 .json 文件。");
      return;
    }
    setImporting(true);
    try {
      await onImport(file);
      notify("已载入本地只读快照；演示空间保持独立");
    } catch (error) {
      setImportError(
        error instanceof Error
          ? error.message
          : "快照未通过校验，请检查版本与字段。",
      );
    } finally {
      setImporting(false);
    }
  }
  return (
    <div className="runtime-page">
      <PageHeading
        eyebrow="A WINDOW, NOT ANOTHER MIND"
        title="空间背后的脉动"
        description="让运行状态可理解，让每一份信息都有来处。主体与执行权始终留在 Nana Core。"
      />
      <div className="runtime-source-notice">
        <Radio size={18} />
        <p>
          <strong>当前生活空间使用演示数据</strong>
          <span>
            {" "}
            尚未连接真实 Runtime。连接状态与奈奈是否休息，是两件不同的事。
          </span>
        </p>
        <Badge tone="amber">DEMO</Badge>
      </div>
      <div className="runtime-overview-grid">
        <Panel className="runtime-overview-card">
          <span className="runtime-stat-icon">
            <HeartPulse size={21} />
          </span>
          <small>演示生命周期</small>
          <strong>{data.runtime.status}</strong>
          <span>{data.presence.label}</span>
        </Panel>
        <Panel className="runtime-overview-card">
          <span className="runtime-stat-icon pink">
            <Layers3 size={21} />
          </span>
          <small>演示中的持续目标</small>
          <strong>
            {activeGoals}
            <em> 项进行中</em>
          </strong>
          <span>
            {blockedGoals.length} 项被条件阻塞 · {unknownGoals.length}{" "}
            项结果未知
          </span>
        </Panel>
        <Panel className="runtime-overview-card">
          <span className="runtime-stat-icon cyan">
            <CheckCircle2 size={21} />
          </span>
          <small>最近的核验结果 · 演示</small>
          <strong className="runtime-stat-text">
            {data.runtime.lastVerified}
          </strong>
          <span>输出建议与已验证行动分别记录</span>
        </Panel>
      </div>
      <div className="runtime-main-grid">
        <Panel className="runtime-demo-panel">
          <SectionHeading eyebrow="DEMO SPACE" title="此刻的运行切片">
            <Badge tone="amber">模拟投影</Badge>
          </SectionHeading>
          <div className="runtime-focus">
            <span>
              <Activity size={19} />
            </span>
            <div>
              <strong>{data.presence.focus}</strong>
              <p>{data.presence.share}</p>
            </div>
          </div>
          <dl className="runtime-key-values">
            <div>
              <dt>模型资源</dt>
              <dd>{data.runtime.provider}</dd>
            </div>
            <div>
              <dt>观察队列</dt>
              <dd>{data.runtime.queue} 条 · 演示</dd>
            </div>
            <div>
              <dt>恢复状态</dt>
              <dd>{data.runtime.recovery}</dd>
            </div>
            <div>
              <dt>生命周期 epoch</dt>
              <dd>{data.runtime.epoch}</dd>
            </div>
          </dl>
          {blockedGoals.length > 0 && (
            <div className="runtime-blockers">
              <h3>
                <LockKeyhole size={15} /> 想做，但条件尚未满足
              </h3>
              {blockedGoals.map((goal) => (
                <div key={goal.id}>
                  <strong>{goal.title}</strong>
                  <p>{goal.reason}</p>
                </div>
              ))}
            </div>
          )}
          {data.partial.length > 0 && (
            <div className="runtime-partial">
              <strong>部分投影不可用</strong>
              <p>{data.partial.join(" · ")}</p>
              <small>缺失保持为未知，不以模拟成功填补。</small>
            </div>
          )}
          <details className="runtime-advanced">
            <summary>
              高级 Inspector · 演示技术信息 <ArrowUpRight size={15} />
            </summary>
            <dl className="runtime-key-values">
              <div>
                <dt>Surface contract</dt>
                <dd>nana-space/v1</dd>
              </div>
              <div>
                <dt>Demo identity</dt>
                <dd className="runtime-code">{data.identityId}</dd>
              </div>
              <div>
                <dt>Snapshot as of</dt>
                <dd>{data.asOf}</dd>
              </div>
              <div>
                <dt>Data adapter</dt>
                <dd>DemoAdapter · 非权威</dd>
              </div>
              <div>
                <dt>Execution authority</dt>
                <dd>false</dd>
              </div>
            </dl>
            <p>
              此标识属于模拟场景。它不会覆盖下方导入快照的真实
              identity_id，也不创建或启动 SubjectLoop。
            </p>
          </details>
        </Panel>
        <Panel className="runtime-import-panel">
          <SectionHeading eyebrow="LOCAL, READ-ONLY" title="打开一份 Core 快照">
            <FileJson size={21} />
          </SectionHeading>
          <div className="runtime-import-illustration">
            <Database size={30} />
            <span>→</span>
            <EyeMark />
          </div>
          <h3>只观察，保留原来的边界</h3>
          <p>
            载入你有权查看的 Inspector
            JSON，在浏览器内检查有限元数据。快照是导出时刻的记录，不代表 Core
            现在正在运行。
          </p>
          <label
            className={`button secondary file-button runtime-import-button ${importing ? "is-loading" : ""}`}
          >
            <Upload size={16} />
            {importing ? "正在校验快照…" : "选择本地 JSON"}
            <input
              type="file"
              accept=".json,application/json"
              disabled={importing}
              aria-label="导入只读 Inspector JSON"
              onChange={(event) => {
                void importFile(event.target.files?.[0]);
                event.target.value = "";
              }}
            />
          </label>
          <small>Inspector Snapshot V1 · ≤ 2 MB · 不上传 · 不持久化</small>
          <div className="runtime-privacy-note">
            <ShieldCheck size={16} />
            <span>
              只导入已获授权的脱敏元数据。不要选择原始私人记录、凭据或数据库；其他私密字段不会展示。
            </span>
          </div>
          {importError && (
            <div className="runtime-import-error" role="alert">
              <strong>快照未载入</strong>
              <p>{importError}</p>
            </div>
          )}
        </Panel>
      </div>
      <Panel className="runtime-inspector-panel">
        <SectionHeading
          eyebrow="IMPORTED SNAPSHOT · SEPARATE SOURCE"
          title="Core 快照观察窗"
          description="与上方演示数据分开呈现；导入不会把 Demo 变成真实生活史。"
        >
          {inspector ? (
            <button
              className="button secondary"
              onClick={() => {
                onClear();
                setImportError("");
                notify("已清除浏览器内的快照");
              }}
            >
              <X size={15} />
              清除快照
            </button>
          ) : (
            <Badge tone="muted">未载入</Badge>
          )}
        </SectionHeading>
        {!inspector ? (
          <Empty
            title="还没有载入快照"
            description="可以继续浏览演示；没有快照不等于奈奈没有活动。"
          />
        ) : (
          <>
            <div className="runtime-snapshot-heading">
              <Fingerprint size={22} />
              <div>
                <strong className="runtime-code">
                  {inspector.identity_id}
                </strong>
                <small>
                  导出时间 {shortDate(inspector.as_of_us)} ·
                  静态快照，非实时状态
                </small>
              </div>
              <Badge tone="cyan">只读元数据</Badge>
            </div>
            <div className="runtime-snapshot-facts">
              <span>
                <ShieldCheck size={15} /> execution_authority: false
              </span>
              <span>schema_version: 1</span>
              <span>coverage: BOUNDED_METADATA_ONLY</span>
            </div>
            <div className="runtime-section-grid">
              {inspectedSections
                .filter((key) => inspector.sections[key]?.length)
                .map((key) => (
                  <details className="runtime-section" key={key}>
                    <summary>
                      <strong>{sectionNames[key]}</strong>
                      <span>{inspector.sections[key].length} 条有限记录</span>
                    </summary>
                    <div className="runtime-items">
                      {inspector.sections[key].map((item, index) => (
                        <article key={`${item.reference}-${index}`}>
                          <div>
                            <strong>{item.category}</strong>
                            <Badge
                              tone={
                                item.state === "UNKNOWN" ? "amber" : "muted"
                              }
                            >
                              {item.state}
                            </Badge>
                          </div>
                          <dl>
                            <dt>Reference</dt>
                            <dd className="runtime-code">{item.reference}</dd>
                            {item.record_id && (
                              <>
                                <dt>Record ID</dt>
                                <dd className="runtime-code">
                                  {item.record_id}
                                </dd>
                              </>
                            )}
                            {item.as_of_us !== null && (
                              <>
                                <dt>As of</dt>
                                <dd>{shortDate(item.as_of_us)}</dd>
                              </>
                            )}
                            {item.source_memory_ids.length > 0 && (
                              <>
                                <dt>来源引用</dt>
                                <dd>{item.source_memory_ids.length} 个</dd>
                              </>
                            )}
                          </dl>
                        </article>
                      ))}
                    </div>
                  </details>
                ))}
            </div>
            {inspector.resources && (
              <details className="runtime-advanced">
                <summary>
                  <RefreshCw size={15} /> 导出时的资源观测
                </summary>
                <dl className="runtime-key-values">
                  {typeof inspector.resources.VmRSS === "number" && (
                    <div>
                      <dt>VmRSS</dt>
                      <dd>{inspector.resources.VmRSS} KiB</dd>
                    </div>
                  )}
                  {typeof inspector.resources.Threads === "number" && (
                    <div>
                      <dt>Threads</dt>
                      <dd>{inspector.resources.Threads}</dd>
                    </div>
                  )}
                </dl>
                <p>
                  仅显示 Inspector
                  定义的数值资源字段，不推断实时健康或执行能力。
                </p>
              </details>
            )}
            <p className="runtime-snapshot-foot">
              私人活动内容、内部推理、未知扩展字典均不展示。元数据可见性不构成向其他接收者披露的授权。
            </p>
          </>
        )}
      </Panel>
      <Panel className="runtime-contract-panel">
        <SectionHeading
          eyebrow="CONTRACT REGISTRY"
          title="接入的路，有清楚的名字"
          description="已有 Core 应用契约与未来浏览器传输分别标注。BACKEND_AVAILABLE 不等于此应用已连接。"
        />
        <div className="runtime-contract-grid">
          {contractRegistry.map((contract) => (
            <article key={contract.id}>
              <div>
                <h3>{contract.title}</h3>
                <Badge
                  tone={contract.maturity === "PLANNED" ? "muted" : "cyan"}
                >
                  {contract.maturity}
                </Badge>
              </div>
              <p>{contract.description}</p>
              <small className="runtime-contract-transport">
                {contract.version} · {contract.transport}
              </small>
              <code>{contract.source}</code>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
function EyeMark() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 36 36"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M3 18s5.5-9 15-9 15 9 15 9-5.5 9-15 9S3 18 3 18Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <circle cx="18" cy="18" r="4" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
