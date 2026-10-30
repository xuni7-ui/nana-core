import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  Check,
  ChevronRight,
  Clock3,
  FileText,
  Heart,
  Link2,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import {
  filterMemories,
  memoryCards,
  memoryDay,
  MEMORY_IMPORT_MAX_BYTES,
  parseMemoryImport,
  type ImportDraft,
  type MemoryCard,
} from "../../data/memory-center";

interface Props {
  memories: Record<string, unknown>[];
  available: boolean;
  privacyScope?: readonly string[];
  canWithdraw: boolean;
  busy: boolean;
  onWithdraw: (memoryId: string) => void;
  onNotice: (text: string) => void;
}
const kindNames: Record<string, string> = {
  FACT: "事实",
  EPISODIC: "经历",
  SEMANTIC: "语义记忆",
  PREFERENCE: "偏好",
  NOTE: "备注",
  EXPERIENCE: "经历",
  RAW_OBSERVATION: "原始观察",
  MODEL_DERIVATION: "模型推导",
  USER_PROVIDED: "用户提供",
  UNKNOWN: "未提供",
};
const label = (value: string) => kindNames[value] || value;

export function MemoryCenter({
  memories,
  available,
  privacyScope,
  canWithdraw,
  busy,
  onWithdraw,
  onNotice,
}: Props) {
  const cards = useMemo(
    () => memoryCards(available ? memories : [], privacyScope),
    [memories, available, privacyScope],
  );
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [source, setSource] = useState("");
  const [topic, setTopic] = useState("");
  const [relationship, setRelationship] = useState("");
  const [day, setDay] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftMode, setDraftMode] = useState<"NOTE" | "CORRECTION" | null>(
    null,
  );
  const [draft, setDraft] = useState("");
  const [preview, setPreview] = useState<ImportDraft[]>([]);
  const [fileName, setFileName] = useState("");
  const [importError, setImportError] = useState("");
  const [reading, setReading] = useState(false);
  const [importAcknowledged, setImportAcknowledged] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const fileReadVersion = useRef(0);
  const detailHeading = useRef<HTMLHeadingElement>(null);
  const selected = cards.find((card) => card.id === selectedId);
  const types = [...new Set(cards.map((card) => card.type))];
  const sources = [
    ...new Set(cards.flatMap((card) => (card.source ? [card.source] : []))),
  ];
  const topics = [...new Set(cards.flatMap((card) => card.topics))];
  const relationships = [
    ...new Set(cards.flatMap((card) => card.relationships)),
  ];
  const shown = filterMemories(cards, {
    query,
    type,
    source,
    topic,
    relationship,
    day,
  });
  const groups = new Map<string, MemoryCard[]>();
  for (const card of shown) {
    const day = memoryDay(card.createdAt);
    groups.set(day, [...(groups.get(day) || []), card]);
  }
  function clearPreview() {
    fileReadVersion.current++;
    setPreview([]);
    setFileName("");
    setImportError("");
    setReading(false);
    setImportAcknowledged(false);
    if (fileInput.current) fileInput.current.value = "";
  }
  useEffect(() => {
    if (!available) {
      clearPreview();
      setSelectedId(null);
      setDraftMode(null);
      setDraft("");
    }
  }, [available]);
  useEffect(
    () => () => {
      fileReadVersion.current++;
    },
    [],
  );
  useEffect(() => {
    if (selectedId) detailHeading.current?.focus();
  }, [selectedId]);
  useEffect(() => {
    if (selectedId && !selected) {
      setSelectedId(null);
      setDraftMode(null);
      setDraft("");
    }
  }, [selectedId, selected]);
  async function readFile(file?: File) {
    clearPreview();
    if (!file) return;
    const version = fileReadVersion.current;
    if (file.size > MEMORY_IMPORT_MAX_BYTES) {
      setImportError("文件不能超过 256 KB。");
      return;
    }
    setReading(true);
    try {
      const text = await file.text();
      if (version !== fileReadVersion.current) return;
      const parsed = parseMemoryImport(file.name, text, cards);
      setPreview(parsed);
      setFileName(file.name.slice(0, 160));
    } catch (error) {
      if (version === fileReadVersion.current)
        setImportError(
          error instanceof Error ? error.message : "文件无法预览。",
        );
    } finally {
      if (version === fileReadVersion.current) setReading(false);
    }
  }
  function openDetail(card: MemoryCard) {
    setSelectedId(card.id);
    setDraftMode(null);
    setDraft("");
  }
  return (
    <div className="v3-memory-center">
      <section className="v3-page-intro">
        <div>
          <span className="v3-eyebrow">OUR CONSTELLATION</span>
          <h2>记得的，都是有来处的。</h2>
          <p>把真实的片刻连起来，给修正和遗忘也留一个位置。</p>
        </div>
        <button
          className="button"
          onClick={() => {
            setDraftMode("NOTE");
            setDraft("");
            setSelectedId(null);
          }}
        >
          <FileText size={16} /> 写一条备注
        </button>
      </section>
      <section className="v3-card v3-memory-overview">
        <div className="v3-memory-mark">
          <Heart size={24} />
        </div>
        <div>
          <strong>
            {available ? `${cards.length} 条可见记忆` : "等待已授权的记忆"}
          </strong>
          <p>当前范围最多展示 32 条；不代表全部生活史。</p>
        </div>
        <span className="v3-chip">
          <ShieldCheck size={13} /> 来源可追溯
        </span>
      </section>
      <div className="v3-search-row">
        <label className="v3-search">
          <Search size={17} />
          <input
            aria-label="搜索记忆"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="找找某个片刻、主题或来源…"
          />
        </label>
        <label className="v3-filter-label">
          <span>类型</span>
          <select
            aria-label="记忆类型"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            <option value="">全部类型</option>
            {types.map((item) => (
              <option key={item} value={item}>
                {label(item)}
              </option>
            ))}
          </select>
        </label>
        <label className="v3-filter-label">
          <span>来源</span>
          <select
            aria-label="记忆来源"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="">全部来源</option>
            {sources.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="v3-memory-facets">
        <label>
          日期{" "}
          <input
            type="date"
            aria-label="记忆日期"
            value={day}
            onChange={(e) => setDay(e.target.value)}
          />
        </label>
        {day && (
          <button className="button" onClick={() => setDay("")}>
            清除日期
          </button>
        )}
        <label>
          主题{" "}
          <select
            aria-label="记忆主题"
            value={topic}
            disabled={!topics.length}
            onChange={(e) => setTopic(e.target.value)}
          >
            <option value="">
              {topics.length ? "全部主题" : "当前接口未提供主题标签"}
            </option>
            {topics.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          关系{" "}
          <select
            aria-label="记忆关系"
            value={relationship}
            disabled={!relationships.length}
            onChange={(e) => setRelationship(e.target.value)}
          >
            <option value="">
              {relationships.length ? "全部关系" : "当前接口未提供关系索引"}
            </option>
            {relationships.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="v3-memory-layout">
        <section className="v3-memory-timeline" aria-label="有来源的记忆时间线">
          {!shown.length && (
            <div className="v3-empty-state">
              <Sparkles size={28} />
              <h3>
                {query || type || source || day
                  ? "这里暂时没有匹配的片刻"
                  : "留一点空白，等真实经历到来"}
              </h3>
              <p>
                {available
                  ? "当前授权范围没有可展示的记忆；不据此推断完整生活史。"
                  : "连接后读取原 Core 的来源投影，不用故事填满空白。"}
              </p>
            </div>
          )}
          {[...groups].map(([day, group]) => (
            <div className="v3-memory-day" key={day}>
              <h3>
                <Clock3 size={14} /> {day}
              </h3>
              {group.map((card) => (
                <button
                  className="v3-card v3-memory-card"
                  key={card.id}
                  onClick={() => openDetail(card)}
                >
                  <div className="v3-card-meta">
                    <span className="v3-chip">{label(card.type)}</span>
                    <span>{card.privacy}</span>
                    <ChevronRight size={15} />
                  </div>
                  <p>{card.text || "当前来源未提供可显示的正文。"}</p>
                  <div className="v3-card-meta">
                    <Link2 size={13} />
                    <span>{card.source || "来源未提供"}</span>
                    <span className="v3-muted">
                      {label(card.epistemicKind)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          ))}
        </section>
        <aside className="v3-memory-sidebar">
          <section className="v3-card">
            <span className="v3-eyebrow">LEGACY CONTINUITY</span>
            <h3>旧时光，慢慢接回来</h3>
            <p>
              当前接口未提供 Iris / AstrBot
              迁移进度。私人历史须经过核账和单独授权后关联，不补写不存在的经历。
            </p>
            <span className="v3-chip">迁移进度 · 需要后端支持</span>
          </section>
          <section className="v3-card">
            <ArrowDownToLine size={20} />
            <h3>记忆与备份</h3>
            <p>
              本机副本不等于异机灾难恢复。当前接口未提供 B1
              接收与恢复回执，不能据此宣称异机资格。
            </p>
            <span className="v3-chip">LOCAL_ONLY_NOT_DR</span>
          </section>
        </aside>
      </div>
      <section className="v3-card v3-memory-import">
        <div className="v3-section-heading">
          <div>
            <span className="v3-eyebrow">BRING A NOTE</span>
            <h3>先看看，再决定要不要留下</h3>
          </div>
          <Upload size={20} />
        </div>
        <p>
          仅在当前页面内预览你选择的文件，不上传、不自动写入记忆。内容标记为「用户提供」，不会冒充奈奈亲历。
        </p>
        <input
          ref={fileInput}
          className="v3-file-input"
          type="file"
          accept=".txt,.md,.json"
          aria-label="选择记忆预览文件"
          onChange={(e) => void readFile(e.target.files?.[0])}
        />
        <small>
          TXT / Markdown / JSON，最多 256 KB、100
          条。私人文件需要另行授权；本轮请只使用公开或项目内容。
        </small>
        {reading && <p role="status">正在本机读取预览…</p>}
        {importError && (
          <p className="v3-inline-error" role="alert">
            {importError}
          </p>
        )}
        {preview.length > 0 && (
          <div className="v3-import-preview">
            <div className="v3-section-heading">
              <h4>
                {fileName} · {preview.length} 条
              </h4>
              <button
                className="v3-icon-button"
                aria-label="清除文件预览"
                onClick={clearPreview}
              >
                <X size={17} />
              </button>
            </div>
            <p>
              {preview.filter((item) => !item.duplicate).length} 条新草稿 ·{" "}
              {preview.filter((item) => item.duplicate).length}{" "}
              条文本重复（含文件内与当前投影，非全库核账）
            </p>
            <div className="v3-import-rows">
              {preview.map((item, index) => (
                <article key={index}>
                  <span className="v3-chip">
                    {item.duplicate ? "重复，默认排除" : "用户提供 · 本地草稿"}
                  </span>
                  <p>{item.text}</p>
                  <small>{item.source}</small>
                </article>
              ))}
            </div>
            <label className="v3-check-row">
              <input
                type="checkbox"
                checked={importAcknowledged}
                onChange={(e) => setImportAcknowledged(e.target.checked)}
              />{" "}
              我理解此预览不是已经写入的记忆
            </label>
            <button
              className="button"
              disabled
              title="当前 V2 未提供记忆导入写入端点"
            >
              需要后端支持 · 暂不能提交
            </button>
            {importAcknowledged && (
              <small>
                <Check size={12} /> 已确认预览边界；草稿离开页面即清除。
              </small>
            )}
          </div>
        )}
      </section>
      {selected && (
        <section className="v3-card v3-memory-detail" aria-label="记忆详情">
          <div className="v3-section-heading">
            <h3 ref={detailHeading} tabIndex={-1}>
              这个片刻的来处
            </h3>
            <button
              className="v3-icon-button"
              aria-label="关闭记忆详情"
              onClick={() => {
                setSelectedId(null);
                setDraftMode(null);
                setDraft("");
              }}
            >
              <X size={18} />
            </button>
          </div>
          <p className="v3-memory-body">{selected.text}</p>
          <dl className="v3-detail-grid">
            <div>
              <dt>记录时间（本机时区）</dt>
              <dd>{memoryDay(selected.createdAt)}</dd>
            </div>
            <div>
              <dt>来源引用</dt>
              <dd>{selected.source || "未提供"}</dd>
            </div>
            <div>
              <dt>证据类型</dt>
              <dd>{label(selected.epistemicKind)}</dd>
            </div>
            <div>
              <dt>原始可信度评估</dt>
              <dd>{selected.assessment}</dd>
            </div>
            <div>
              <dt>隐私范围</dt>
              <dd>{selected.privacy}</dd>
            </div>
            <div>
              <dt>记忆 ID</dt>
              <dd>{selected.id}</dd>
            </div>
          </dl>
          <div className="v3-actions">
            <button
              className="button"
              onClick={() => {
                setDraftMode("CORRECTION");
                setDraft("");
              }}
            >
              写一条纠错草稿
            </button>
            <button
              className="button danger"
              disabled={!canWithdraw || busy}
              onClick={() => {
                if (
                  confirm(
                    "申请撤回这条来源记忆？原 Core 将检查 Manager、来源与隐私传播。",
                  )
                )
                  onWithdraw(selected.id);
              }}
            >
              申请撤回此来源记忆
            </button>
          </div>
          {!canWithdraw && (
            <small>
              撤回需要当前会话的 Manager 权限；关系重要性不会自动授予权限。
            </small>
          )}
        </section>
      )}
      {draftMode && (
        <section
          className="v3-card v3-note-draft"
          aria-label="用户提供的记忆草稿"
        >
          <div className="v3-section-heading">
            <h3>{draftMode === "CORRECTION" ? "纠错草稿" : "写一条备注"}</h3>
            <button
              className="v3-icon-button"
              aria-label="丢弃记忆草稿"
              onClick={() => {
                setDraftMode(null);
                setDraft("");
              }}
            >
              <X size={17} />
            </button>
          </div>
          <span className="v3-chip">USER_PROVIDED · 仅当前页面内存</span>
          <textarea
            aria-label="记忆草稿内容"
            rows={4}
            maxLength={4000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="这是你提供的备注或纠正，不是奈奈自己的经历…"
          />
          <p>
            当前 V2
            仅支持来源撤回，没有新增备注或纠错写入端点。草稿不会发送给模型，也不会保存到设备。
          </p>
          <div className="v3-actions">
            <button className="button" disabled>
              需要后端支持 · 暂不能提交
            </button>
            <button
              className="button"
              onClick={() =>
                onNotice(
                  "草稿仅保留在当前页面内存；离开页面后清除，没有写入云端。",
                )
              }
            >
              查看保存范围
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
