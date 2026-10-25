import { useCallback, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import {
  ArrowUp,
  ArrowUpRight,
  ChevronRight,
  Heart,
  Home,
  MessageCircle,
  Orbit,
  BookOpen,
  Compass,
  Leaf,
  Monitor,
  Activity,
  Settings,
  RefreshCw,
  ShieldCheck,
  Menu,
  X,
} from "lucide-react";
import { usePreferences } from "../app/preferences";
import { Avatar, AvatarStage } from "../avatar/Avatar";
import { Badge, Empty, Panel, PageHeading } from "../components/ui";
import {
  liveAdapter,
  LiveError,
  type CoreEnvelope,
  type CoreData,
  type CoreReceipt,
} from "../data/live";
import type { Route, InspectorItem } from "../data/contracts";
import "./core.css";
const routes: [Route, string, typeof Home][] = [
  ["home", "生活空间", Home],
  ["chat", "和奈奈聊聊", MessageCircle],
  ["memories", "共同记忆", Heart],
  ["goals", "小小计划", Compass],
  ["journal", "生活手记", BookOpen],
  ["world", "世界与发现", Orbit],
  ["growth", "成长轨迹", Leaf],
  ["devices", "连接的世界", Monitor],
  ["runtime", "运行与边界", Activity],
  ["settings", "空间设置", Settings],
];
const sectionNames: Record<string, string> = {
  runtime: "生命周期",
  goals: "目标",
  activities: "可见活动",
  concerns: "关注事项",
  needs: "需要",
  affect: "状态投影",
  interests: "兴趣",
  suppressed_deferred: "暂缓",
  decisions: "判断元数据",
  experience: "经历",
  provenance: "来源",
  authority: "权限",
  unknown: "未知结果",
  provider: "模型资源",
  queue: "队列",
  source_lifecycle: "来源生命周期",
  health: "健康",
  skills: "技能",
  world: "世界状态",
  learning: "学习",
};
const sectionsFor: Partial<Record<Route, string[]>> = {
  home: ["activities", "interests", "concerns", "goals"],
  memories: ["experience", "provenance", "source_lifecycle"],
  goals: ["goals", "suppressed_deferred", "unknown"],
  journal: ["activities", "experience", "decisions"],
  world: ["world", "concerns", "source_lifecycle"],
  growth: ["skills", "learning", "experience"],
  devices: ["provider", "authority"],
  runtime: Object.keys(sectionNames),
};
function initialRoute(): Route {
  return routes.find(([id]) => id === location.hash.slice(1))?.[0] || "home";
}
function explain(code: string) {
  return (
    (
      {
        SESSION_REQUIRED: "请用本机访问口令登录开发会话。",
        SESSION_EXPIRED: "开发会话已过期，请重新登录。",
        SESSION_DENIED: "口令或主体 ID 不匹配。",
        CORE_UNAVAILABLE: "原 Core owner 暂不可用；当前不展示旧状态。",
        CONNECTION_LOST: "连接中断；发送中的消息结果可能未知，请先核验。",
        SUBJECT_IDENTITY_MISMATCH: "主体身份不匹配，连接已拒绝。",
        SESSION_GENERATION_CHANGED_NO_REPLAY:
          "网关会话已更换，旧消息不可重新发送。",
      } as Record<string, string>
    )[code] || `接入被拒绝：${code}`
  );
}
interface Turn {
  id: string;
  text: string;
  state: "SENDING" | "REVIEWED" | "UNKNOWN" | "FAILED";
  reply?: CoreReceipt;
  runId: string;
}
function Records({ name, items }: { name: string; items: InspectorItem[] }) {
  return (
    <Panel className="core-records">
      <h2>
        {sectionNames[name] || name}
        <Badge tone="muted">{items.length} 条有限元数据</Badge>
      </h2>
      {items.length ? (
        items.map((item, i) => (
          <article key={`${item.reference}-${i}`}>
            <div>
              <strong>{item.category}</strong>
              <Badge tone={item.state === "UNKNOWN" ? "warning" : "purple"}>
                {item.state}
              </Badge>
            </div>
            <p>{item.reference}</p>
            {item.record_id && <small>记录：{item.record_id}</small>}
            {item.as_of_us !== null && (
              <small>
                来源时间：
                {new Date(item.as_of_us / 1000).toLocaleString("zh-CN")}
              </small>
            )}
            {item.source_memory_ids.length > 0 && (
              <details>
                <summary>来源引用</summary>
                {item.source_memory_ids.map((id) => (
                  <p key={id}>{id}</p>
                ))}
              </details>
            )}
          </article>
        ))
      ) : (
        <p>没有可展示的投影条目；不推断为没有生活或没有目标。</p>
      )}
    </Panel>
  );
}
export function CoreApp({ onDemo }: { onDemo: () => void }) {
  const [preferences, setPreferences] = usePreferences();
  const [route, setRoute] = useState<Route>(initialRoute);
  const [menu, setMenu] = useState(false);
  const [identity, setIdentity] = useState(() => {
    try {
      return sessionStorage.getItem("nana-space.expected-core") || "";
    } catch {
      return "";
    }
  });
  const [password, setPassword] = useState("");
  const [snapshot, setSnapshot] = useState<CoreEnvelope<CoreData> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const sendLock = useRef(false);
  const alive = useRef(true);
  const identityRef = useRef(identity);
  identityRef.current = identity;
  const thread = useRef<HTMLDivElement>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    const hash = () => {
      setRoute(initialRoute());
      setMenu(false);
    };
    addEventListener("hashchange", hash);
    return () => removeEventListener("hashchange", hash);
  }, []);
  const navigate = (value: Route) => {
    location.hash = value;
    setRoute(value);
    setMenu(false);
  };
  useEffect(() => {
    const ctrl = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let pending = false;
    async function poll() {
      if (!identity || pending) return;
      pending = true;
      try {
        const next = await liveAdapter.load(identity, ctrl.signal);
        if (!ctrl.signal.aborted) {
          setSnapshot(next);
          setError("");
        }
      } catch (e) {
        if (!ctrl.signal.aborted) {
          setSnapshot(null);
          setError(
            explain(e instanceof LiveError ? e.code : "CORE_UNAVAILABLE"),
          );
        }
      } finally {
        pending = false;
        if (!ctrl.signal.aborted) timer = setTimeout(poll, 10000);
      }
    }
    void poll();
    return () => {
      ctrl.abort();
      clearTimeout(timer);
    };
  }, [identity, refresh]);
  useEffect(() => {
    thread.current?.scrollTo({ top: thread.current.scrollHeight });
  }, [turns]);
  async function login() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await liveAdapter.login(password, identity);
      setPassword("");
      try {
        sessionStorage.setItem("nana-space.expected-core", identity);
      } catch {}
      setRefresh((n) => n + 1);
    } catch (e) {
      setError(explain(e instanceof LiveError ? e.code : "CONNECTION_LOST"));
    } finally {
      setPassword("");
      setBusy(false);
    }
  }
  const send = useCallback(async () => {
    if (sendLock.current || !snapshot || !draft.trim()) return;
    const text = draft.trim();
    if (text.length > 2048) return;
    const id = globalThis.crypto?.randomUUID?.() || `space-${Date.now()}`;
    const runId = snapshot.run_id;
    const subject = identity;
    sendLock.current = true;
    setDraft("");
    setTurns((old) =>
      [...old, { id, text, state: "SENDING" as const, runId }].slice(-32),
    );
    try {
      const result = await liveAdapter.send(subject, runId, id, text);
      if (alive.current && identityRef.current === subject)
        setTurns((old) =>
          old.map((t) =>
            t.id === id
              ? { ...t, state: result.data.state, reply: result.data }
              : t,
          ),
        );
      setRefresh((n) => n + 1);
    } catch (e) {
      if (alive.current && identityRef.current === subject)
        setTurns((old) =>
          old.map((t) =>
            t.id === id
              ? {
                  ...t,
                  state:
                    e instanceof LiveError &&
                    [
                      "SEND_INPUT_DENIED",
                      "MESSAGE_BOUND",
                      "MESSAGE_FIELDS_DENIED",
                      "SESSION_REQUIRED",
                      "SESSION_DENIED",
                    ].includes(e.code)
                      ? "FAILED"
                      : "UNKNOWN",
                }
              : t,
          ),
        );
    } finally {
      sendLock.current = false;
    }
  }, [draft, snapshot, identity]);
  async function verify(turn: Turn) {
    try {
      const result = await liveAdapter.receipt(identity, turn.id, turn.runId);
      if (alive.current)
        setTurns((old) =>
          old.map((t) =>
            t.id === turn.id
              ? { ...t, state: result.data.state, reply: result.data }
              : t,
          ),
        );
    } catch (e) {
      setError(explain(e instanceof LiveError ? e.code : "CONNECTION_LOST"));
    }
  }
  const currentTitle = routes.find(([id]) => id === route)?.[1] || "生活空间";
  const rows = (sectionsFor[route] || []).map(
    (key) => [key, snapshot?.data.inspector.sections[key] || []] as const,
  );

  return (
    <div className="app-shell core-app">
      <aside className="sidebar">
        <button className="brand" onClick={() => navigate("home")}>
          <span className="brand-symbol">✧</span>
          <span>
            Nana Space<small>同一主体 · 开发连接</small>
          </span>
        </button>
        <nav aria-label="Core 页面导航">
          {routes.map(([id, label, Icon]) => (
            <button
              key={id}
              className={`nav-item ${route === id ? "active" : ""}`}
              onClick={() => navigate(id)}
              aria-current={route === id ? "page" : undefined}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>
        <button className="button secondary core-back" onClick={onDemo}>
          退出 Core，返回演示
        </button>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu-button"
              aria-label="打开 Core 导航"
              onClick={() => setMenu(!menu)}
            >
              {menu ? <X size={20} /> : <Menu size={20} />}
            </button>
            {currentTitle}
          </div>
          <div className="topbar-right">
            <Badge tone={snapshot ? "green" : "warning"}>
              {snapshot ? "DEV CORE · CONNECTED" : "CORE · 未连接"}
            </Badge>
            <button
              className="icon-button"
              aria-label="刷新 Core 投影"
              onClick={() => setRefresh((n) => n + 1)}
            >
              <RefreshCw size={18} />
            </button>
            <button
              className="button secondary core-demo-mobile"
              onClick={onDemo}
            >
              演示
            </button>
          </div>
        </header>
        {menu && (
          <nav className="core-mobile-menu" aria-label="Core 全部页面">
            {routes.map(([id, label]) => (
              <button key={id} onClick={() => navigate(id)}>
                {label}
              </button>
            ))}
          </nav>
        )}
        <div className="core-boundary">
          <ShieldCheck size={16} />
          <span>
            真实 Core 协议 · 隔离开发实例 · 非生产奈奈 ·
            无付费模型、设备或社交权限
          </span>
        </div>
        <main
          className={`page-content ${route === "chat" && snapshot ? "is-chat" : ""}`}
        >
          {!snapshot ? (
            <div className="core-login">
              <PageHeading
                eyebrow="CONNECT TO THE SAME SUBJECT"
                title="打开通向 Core 的窗口"
                description="连接宿主启动的本机开发网关。口令只用于此会话，不存入浏览器偏好或主体记忆。"
              />
              <Panel>
                <label>
                  预期 Subject ID
                  <input
                    aria-label="预期 Subject ID"
                    value={identity}
                    onChange={(e) => {
                      setSnapshot(null);
                      setTurns([]);
                      setIdentity(e.target.value);
                    }}
                    maxLength={128}
                  />
                </label>
                <label>
                  本机开发会话口令
                  <input
                    aria-label="本机开发会话口令"
                    type="password"
                    autoComplete="off"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    maxLength={128}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void login();
                    }}
                  />
                </label>
                <button
                  className="button primary"
                  disabled={busy || !identity || password.length < 12}
                  onClick={() => void login()}
                >
                  {busy ? "正在核对身份…" : "验证并连接"}
                </button>
                {error && (
                  <p role="alert" className="warning-text">
                    {error}
                  </p>
                )}
                <p>
                  会话凭据由同源 HttpOnly Cookie 持有。此页面不能配置 Provider
                  Key、数据库路径或执行命令。
                </p>
                <button className="text-link" onClick={onDemo}>
                  返回独立 Demo
                </button>
              </Panel>
            </div>
          ) : (
            <>
              {error && (
                <p className="warning-text" role="alert">
                  {error}
                </p>
              )}
              <div className="core-identity">
                <span>
                  Subject <code>{snapshot.subject_id}</code>
                </span>
                <span>
                  投影于{" "}
                  {new Date(snapshot.as_of_us / 1000).toLocaleTimeString(
                    "zh-CN",
                  )}
                </span>
                <span>
                  {snapshot.data.runtime.autonomy} ·{" "}
                  {snapshot.data.runtime.provider}
                </span>
              </div>
              {route === "settings" ? (
                <div className="core-settings">
                  <PageHeading
                    eyebrow="LOCAL PRESENTATION"
                    title="窗口与连接"
                    description="界面偏好仍在浏览器；Core 权限、配置与记忆保持原有权威。"
                  />
                  <Panel>
                    <h2>主题</h2>
                    {(["dark", "light", "system"] as const).map((theme) => (
                      <button
                        className="button secondary"
                        key={theme}
                        onClick={() => setPreferences((p) => ({ ...p, theme }))}
                      >
                        {theme === "dark"
                          ? "月光深蓝"
                          : theme === "light"
                            ? "晨间薄雾"
                            : "跟随系统"}
                      </button>
                    ))}
                    <label>
                      字体缩放
                      <select
                        value={preferences.fontScale}
                        onChange={(e) =>
                          setPreferences((p) => ({
                            ...p,
                            fontScale: Number(e.target.value),
                          }))
                        }
                      >
                        {[0.9, 1, 1.1, 1.2].map((n) => (
                          <option key={n} value={n}>
                            {n * 100}%
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="button secondary"
                      onClick={() =>
                        setPreferences((p) => ({ ...p, motion: !p.motion }))
                      }
                    >
                      轻柔动效：{preferences.motion ? "开" : "关"}
                    </button>
                    <AvatarStage enabled={preferences.avatar} />
                  </Panel>
                  <Panel>
                    <h2>当前接入边界</h2>
                    <p>
                      PROJECT 输入 · 2048 字上限 · 原 Runtime owner 处理 ·
                      不保留对话正文
                    </p>
                    <p>
                      Provider 设置、Perception
                      Capture、设备动作、权限变更均未开放。当前未配置语言模型；回复会明确标记离线语义受限。
                    </p>
                  </Panel>
                </div>
              ) : route === "chat" ? (
                <div className="chat-page">
                  <header className="chat-heading">
                    <div className="chat-person">
                      <Avatar size={40} />
                      <div>
                        <h1>和 Core 里的奈奈聊聊</h1>
                        <p>本次开发会话 · 原主体判断 · 当前无语言模型</p>
                      </div>
                    </div>
                    <Badge tone="warning">PROJECT · ≤ 2048 字</Badge>
                  </header>
                  <div className="core-chat-thread" ref={thread}>
                    <p className="core-chat-notice">
                      回复来自原 Core，而非
                      DemoAdapter。界面不会把离线固定表达伪装为模型生成；发送不等于外部动作成功。
                    </p>
                    {turns.length === 0 && (
                      <Empty
                        title="从一个真实输入开始"
                        description="消息通过固定 SurfaceBinding 进入原 owner；不绕过 Grant / Manager。"
                      />
                    )}
                    {turns.map((turn) => (
                      <div key={turn.id}>
                        <article className="message message-user">
                          <div className="message-content">
                            <div className="message-bubble">
                              <p>{turn.text}</p>
                            </div>
                            <small>
                              {turn.state === "SENDING"
                                ? "已提交，等待原 Core 回执"
                                : turn.state === "REVIEWED"
                                  ? "原 Core 已审阅 · 非外部送达"
                                  : turn.state === "FAILED"
                                    ? "未获发送许可"
                                    : "结果 UNKNOWN · 不重发"}
                            </small>
                          </div>
                        </article>
                        {turn.reply?.text && (
                          <article className="message message-nana">
                            <Avatar size={30} />
                            <div className="message-content">
                              <div className="message-bubble">
                                <Markdown skipHtml>{turn.reply.text}</Markdown>
                              </div>
                              <div className="core-reply-meta">
                                <Badge tone="muted">
                                  Core 返回 · {turn.reply.render_state}
                                </Badge>
                                <span>
                                  判断 {turn.reply.judgment} · 意图{" "}
                                  {turn.reply.intention}
                                </span>
                                <small>
                                  消息元数据引用 {turn.reply.message_memory_id}
                                </small>
                              </div>
                            </div>
                          </article>
                        )}
                        {turn.state === "UNKNOWN" && (
                          <button
                            className="button secondary"
                            onClick={() => void verify(turn)}
                          >
                            核验原消息结果
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <form
                    className="chat-composer"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void send();
                    }}
                  >
                    <div className="composer-box">
                      <textarea
                        aria-label="发送给真实开发 Core"
                        placeholder="这条消息会进入原 Core 的开发实例…"
                        maxLength={2048}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        rows={2}
                      />
                      <div className="composer-tools">
                        <small>
                          仅 PROJECT · 正文保留在当前会话 · 刷新清空
                        </small>
                        <button
                          className="send-button"
                          aria-label="发送给 Core"
                          disabled={
                            sendLock.current ||
                            !draft.trim() ||
                            !snapshot.data.capabilities.send_input
                          }
                        >
                          <ArrowUp size={20} />
                        </button>
                      </div>
                    </div>
                  </form>
                </div>
              ) : (
                <>
                  <PageHeading
                    eyebrow={
                      route === "home"
                        ? "A REAL WINDOW, A CONTINUOUS SUBJECT"
                        : "SOURCE FILTERED CORE PROJECTION"
                    }
                    title={
                      route === "home" ? "同一个奈奈，在这里相遇" : currentTitle
                    }
                    description={
                      route === "home"
                        ? "这里呈现原 Core 允许公开的有限状态。此开发实例尚无长期共同生活史，空白不会由演示故事填补。"
                        : "当前接口提供有界元数据。完整标题、记忆正文或尚未提供的能力保持不可用，不从 Demo 数据推导。"
                    }
                  />
                  {route === "home" && (
                    <Panel className="core-presence">
                      <Avatar size={64} />
                      <div>
                        <h2>连接原 Runtime owner</h2>
                        <p>
                          {snapshot.data.runtime.autonomy} ·{" "}
                          {snapshot.data.runtime.provider}
                        </p>
                        <button
                          className="text-link"
                          onClick={() => navigate("chat")}
                        >
                          开始一次真实输入
                          <ArrowUpRight size={16} />
                        </button>
                      </div>
                      <Badge tone="muted">静态角色 · 不推断情绪</Badge>
                    </Panel>
                  )}
                  <div className="core-grid">
                    {rows.map(([name, items]) => (
                      <Records key={name} name={name} items={items} />
                    ))}
                  </div>
                  {route === "devices" && (
                    <Panel>
                      <h2>观察与执行能力</h2>
                      <p>
                        当前网关只开放有限投影与 PROJECT
                        消息。相机、麦克风、QQ、B站、PC/Android
                        控制均未连接；没有“启用”假按钮。
                      </p>
                    </Panel>
                  )}
                </>
              )}
            </>
          )}
        </main>
        <nav className="bottom-nav" aria-label="Core 移动导航">
          {[routes[0], routes[1], routes[2], routes[5]].map(
            ([id, label, Icon]) => (
              <button
                key={id}
                className={route === id ? "active" : ""}
                onClick={() => navigate(id)}
              >
                <Icon size={20} />
                <span>{label}</span>
              </button>
            ),
          )}
          <button onClick={() => setMenu(!menu)}>
            <Menu size={20} />
            <span>更多</span>
          </button>
        </nav>
      </div>
    </div>
  );
}
