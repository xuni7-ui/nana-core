import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
  useId,
  type ReactNode,
} from "react";
import {
  Home,
  MessageCircle,
  Heart,
  Compass,
  BookOpen,
  Sparkles,
  Monitor,
  Settings,
  Activity,
  Search,
  Bell,
  PanelLeftClose,
  ChevronDown,
  ArrowUpRight,
  Menu,
  X,
  Moon,
  Sun,
  ArrowRight,
  WifiOff,
  RefreshCw,
  ShieldCheck,
  Orbit,
  Command,
  Leaf,
} from "lucide-react";
import type {
  Route,
  Scenario,
  SpaceSnapshot,
  Message,
  MessageAttachment,
  InspectorSnapshot,
} from "../data/contracts";
import { scenarioLabels } from "../data/contracts";
import { demoAdapter } from "../data/demo";
import { parseInspectorSnapshot } from "../data/inspector";
import { usePreferences } from "./preferences";
import { Avatar } from "../avatar/Avatar";
import { Badge } from "../components/ui";
import { HomePage } from "../features/HomePage";
const Explore = () => import("../features/ExplorePages");
const MemoriesPage = lazy(() =>
  Explore().then((m) => ({ default: m.MemoriesPage })),
);
const GoalsPage = lazy(() => Explore().then((m) => ({ default: m.GoalsPage })));
const JournalPage = lazy(() =>
  Explore().then((m) => ({ default: m.JournalPage })),
);
const WorldPage = lazy(() => Explore().then((m) => ({ default: m.WorldPage })));
const GrowthPage = lazy(() =>
  Explore().then((m) => ({ default: m.GrowthPage })),
);
const DevicesPage = lazy(() =>
  Explore().then((m) => ({ default: m.DevicesPage })),
);
const ChatPage = lazy(() =>
  import("../features/ChatPage").then((m) => ({ default: m.ChatPage })),
);
const RuntimePage = lazy(() =>
  import("../features/RuntimePage").then((m) => ({ default: m.RuntimePage })),
);
const SettingsPage = lazy(() =>
  import("../features/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);
const navigation: [Route, string, typeof Home, string][] = [
  ["home", "生活空间", Home, "SPACE"],
  ["chat", "和奈奈聊聊", MessageCircle, "TOGETHER"],
  ["memories", "共同记忆", Heart, "TOGETHER"],
  ["goals", "小小计划", Compass, "TOGETHER"],
  ["journal", "生活手记", BookOpen, "TOGETHER"],
  ["world", "世界与发现", Orbit, "HER WORLD"],
  ["growth", "成长轨迹", Leaf, "HER WORLD"],
  ["devices", "连接的世界", Monitor, "HER WORLD"],
  ["runtime", "运行与边界", Activity, "SYSTEM"],
  ["settings", "空间设置", Settings, "SYSTEM"],
];
function readRoute(): Route {
  const x = location.hash.slice(1).split("?")[0];
  return navigation.some((n) => n[0] === x) ? (x as Route) : "home";
}
function Loading() {
  return (
    <div className="loading-state" role="status">
      <span className="loading-star">✧</span>
      <p>正在轻轻推开小房间的门…</p>
      <div className="loading-bars">
        <i />
        <i />
        <i />
      </div>
    </div>
  );
}
function Dialog({
  title,
  onClose,
  children,
  className = "",
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  const labelId = useId();
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const opener = document.activeElement;
    const el = ref.current;
    el?.showModal();
    el?.querySelector<HTMLElement>("[data-dialog-focus]")?.focus();
    return () => {
      el?.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);
  return (
    <dialog
      aria-labelledby={labelId}
      ref={ref}
      className={`space-dialog ${className}`}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-heading">
        <h2 id={labelId}>{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="关闭窗口">
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
// These IDs only correlate browser Demo messages, never subjects or execution grants.
let localMessageSequence = 0;
function newMessageId() {
  return (
    globalThis.crypto?.randomUUID?.() ??
    `demo-message-${Date.now()}-${++localMessageSequence}`
  );
}
function DemoApp({ onCore }: { onCore: () => void }) {
  const [route, setRoute] = useState<Route>(readRoute);
  const [scenario, setScenario] = useState<Scenario>("evening");
  const [data, setData] = useState<SpaceSnapshot | null>(null);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [preferences, setPreferences] = usePreferences();
  const [menu, setMenu] = useState(false);
  const [modal, setModal] = useState<"search" | "notifications" | null>(null);
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState("");
  const [toast, setToast] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [inspector, setInspector] = useState<InspectorSnapshot | null>(null);
  const sendController = useRef<AbortController | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const content = useRef<HTMLElement>(null);
  const navFocus = useRef<HTMLButtonElement>(null);
  const sendingLock = useRef(false);
  const inspectorRef = useRef<InspectorSnapshot | null>(null);
  const importSequence = useRef(0);
  const quietRef = useRef(preferences.quiet);
  quietRef.current = preferences.quiet;
  const notify = useCallback((s: string, optional = false) => {
    if (optional && quietRef.current) return;
    setToast(s);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 5000);
  }, []);
  const navigate = useCallback((r: Route) => {
    location.hash = r;
    setRoute(r);
    setMenu(false);
  }, []);
  useEffect(() => {
    const onHash = () => {
      setRoute(readRoute());
      setMenu(false);
    };
    addEventListener("hashchange", onHash);
    return () => removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    content.current?.scrollTo({ top: 0 });
    if (!menu) content.current?.focus({ preventScroll: true });
  }, [route]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setModal((m) => (m === "search" ? null : "search"));
      }
      if (e.key === "Escape") setMenu(false);
    };
    addEventListener("keydown", handler);
    return () => removeEventListener("keydown", handler);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    sendController.current?.abort();
    sendingLock.current = false;
    setSending(false);
    setData(null);
    setMessages([]);
    setError("");
    demoAdapter
      .load(scenario, controller.signal)
      .then((s) => {
        if (!controller.signal.aborted) {
          setData(s);
          setMessages(s.messages);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "数据暂时不可用");
      });
    return () => controller.abort();
  }, [scenario, reload]);
  useEffect(
    () => () => {
      sendController.current?.abort();
      if (toastTimer.current) clearTimeout(toastTimer.current);
    },
    [],
  );
  useEffect(() => {
    const online = () => notify("网络已恢复。当前仍为本地 Demo 数据源。", true);
    const offline = () =>
      notify("设备已离线；本地演示可继续浏览，Core 不会在浏览器运行。");
    addEventListener("online", online);
    addEventListener("offline", offline);
    return () => {
      removeEventListener("online", online);
      removeEventListener("offline", offline);
    };
  }, [notify]);
  const onChat = (t: string) => {
    setTopic(t);
    navigate("chat");
  };
  async function performSend(
    text: string,
    attachments: MessageAttachment[],
    retryId?: string,
  ) {
    if (sendingLock.current) return;
    if (!text.trim() || text.length > 8000) {
      notify("请输入 1–8000 个字符。");
      return;
    }
    sendingLock.current = true;
    const controller = new AbortController();
    sendController.current = controller;
    setSending(true);
    const time = new Intl.DateTimeFormat("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date());
    const uid = retryId || newMessageId();
    const rid = newMessageId();
    setMessages((old) => [
      ...(retryId
        ? old.map((m) =>
            m.id === uid ? { ...m, status: "SENDING" as const } : m,
          )
        : [
            ...old,
            {
              id: uid,
              role: "user" as const,
              text,
              time,
              status: "SENDING" as const,
              attachments,
            },
          ]),
      { id: rid, role: "nana", text: "", time, status: "SENDING" },
    ]);
    try {
      const result = await demoAdapter.send(
        text,
        scenario,
        (chunk) => {
          if (!controller.signal.aborted)
            setMessages((old) =>
              old.map((m) => (m.id === rid ? { ...m, text: chunk } : m)),
            );
        },
        controller.signal,
      );
      if (!controller.signal.aborted)
        setMessages((old) =>
          old.map((m) =>
            m.id === rid
              ? { ...m, text: result, status: "SENT" }
              : m.id === uid
                ? { ...m, status: "SENT" }
                : m,
          ),
        );
    } catch (e) {
      if (controller.signal.aborted) return;
      const code = (e as { code?: string }).code;
      const unknown = code === "UNKNOWN";
      setMessages((old) =>
        old
          .filter((m) => m.id !== rid)
          .map((m) =>
            m.id === uid ? { ...m, status: unknown ? "UNKNOWN" : "FAILED" } : m,
          ),
      );
      notify(
        unknown
          ? "状态未知，未自动重试。请先核验原消息。"
          : "演示消息发送失败，可以手动重试。",
      );
    } finally {
      if (!controller.signal.aborted) {
        sendingLock.current = false;
        setSending(false);
      }
    }
  }
  const retry = (id: string) => {
    const m = messages.find((x) => x.id === id);
    if (m?.status === "FAILED")
      void performSend(m.text, m.attachments || [], id);
  };
  async function onImport(file: File) {
    const sequence = ++importSequence.current;
    if (file.size > 2 * 1024 * 1024) throw new Error("快照不能大于 2 MB。");
    const text = await file.text();
    if (sequence !== importSequence.current)
      throw new Error("该快照导入已被取消。");
    const imported = parseInspectorSnapshot(
      text,
      inspectorRef.current?.identity_id,
    );
    inspectorRef.current = imported;
    setInspector(imported);
  }
  function clearInspector() {
    ++importSequence.current;
    inspectorRef.current = null;
    setInspector(null);
  }
  const sharedMessage = data?.messages.find((m) => m.proactive);

  const activeLabel = navigation.find((n) => n[0] === route)?.[1] || "生活空间";
  function navItems() {
    return navigation.map(([id, label, Icon, group], i) => (
      <div key={id}>
        {(i === 0 || navigation[i - 1][3] !== group) && (
          <span className="nav-section">
            {group === "SPACE"
              ? "我的小宇宙"
              : group === "TOGETHER"
                ? "我们之间"
                : group === "HER WORLD"
                  ? "奈奈的世界"
                  : "空间管理"}
          </span>
        )}
        <button
          className={`nav-item ${route === id ? "active" : ""}`}
          onClick={() => navigate(id)}
          aria-current={route === id ? "page" : undefined}
        >
          <Icon size={18} strokeWidth={1.65} />
          <span>{label}</span>
          {id === "chat" && sharedMessage && !preferences.quiet && (
            <span className="nav-new-dot" />
          )}
          {route === id && <span className="nav-active-spark">✧</span>}
        </button>
      </div>
    ));
  }
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          content.current?.focus();
        }}
      >
        跳到主要内容
      </a>
      <aside className="sidebar">
        <button
          className="brand"
          onClick={() => navigate("home")}
          aria-label="Nana Space 首页"
        >
          <span className="brand-symbol">✧</span>
          <span>
            Nana Space<small>奈奈的小房间</small>
          </span>
        </button>
        <nav aria-label="主要导航">{navItems()}</nav>
        <div className="sidebar-bottom">
          <div className="sidebar-little-note">
            <span>✦</span>
            <p>
              世界再大，
              <br />
              也有一起发光的角落。
            </p>
            <small>A LITTLE SPACE FOR US</small>
          </div>
          <button
            className="sidebar-profile"
            onClick={() => navigate("settings")}
          >
            <span className="user-avatar">U</span>
            <span>
              Primary User<small>这个空间的共同生活者</small>
            </span>
            <Settings size={15} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              ref={navFocus}
              className="icon-button mobile-menu-button"
              onClick={() => setMenu(true)}
              aria-label="打开导航菜单"
            >
              <Menu size={20} />
            </button>
            <span className="breadcrumb-brand">Nana Space</span>
            <span className="breadcrumb-slash">/</span>
            <span>{activeLabel}</span>
          </div>
          <div className="topbar-right">
            <button className="button secondary" onClick={onCore}>
              接入 Core
            </button>
            <button
              className="search-launch"
              onClick={() => {
                setQuery("");
                setModal("search");
              }}
            >
              <Search size={16} />
              <span>在小宇宙里找找…</span>
              <kbd>⌘ K</kbd>
            </button>
            <button className="mode-pill" onClick={() => navigate("settings")}>
              <span />
              DEMO <span className="mode-long">演示空间</span>
              <ChevronDown size={12} />
            </button>
            <span className="topbar-divider" />
            <button
              className="icon-button notification-button"
              onClick={() => setModal("notifications")}
              aria-label="打开分享与通知"
            >
              <Bell size={18} />
              {sharedMessage && !preferences.quiet && <i />}
            </button>
            <button
              className="icon-button"
              aria-label="切换深浅主题"
              onClick={() =>
                setPreferences((p) => ({
                  ...p,
                  theme:
                    document.documentElement.dataset.theme === "dark"
                      ? "light"
                      : "dark",
                }))
              }
            >
              {preferences.theme === "light" ? (
                <Sun size={18} />
              ) : (
                <Moon size={18} />
              )}
            </button>
            <Avatar size={30} />
          </div>
        </header>
        {scenario !== "evening" && (
          <div
            className={`scenario-banner ${scenario === "offline" ? "warning" : ""}`}
            role="status"
          >
            {scenario === "offline" ? (
              <WifiOff size={16} />
            ) : (
              <Orbit size={16} />
            )}
            <span>
              演示场景：{scenarioLabels[scenario]}
              {data && data.partial.length > 0
                ? ` · ${data.partial.join("、")}`
                : ""}
            </span>
            <button onClick={() => setScenario("evening")}>返回日常</button>
          </div>
        )}
        <main
          className={`page-content ${route === "chat" ? "is-chat" : ""}`}
          id="main-content"
          ref={content}
          tabIndex={-1}
        >
          {error ? (
            <div className="error-state">
              <span>☁</span>
              <h1>暂时没能打开这个片刻</h1>
              <p>{error}</p>
              <p>演示适配器加载失败，尚未连接 Nana Core。</p>
              <button
                className="button secondary"
                onClick={() => setReload((v) => v + 1)}
              >
                <RefreshCw size={16} />
                重试当前场景
              </button>
              <button
                className="button primary"
                onClick={() => setScenario("evening")}
              >
                恢复日常演示
              </button>
            </div>
          ) : !data ? (
            <Loading />
          ) : (
            <Suspense fallback={<Loading />}>
              {route === "home" ? (
                <HomePage
                  data={data}
                  navigate={navigate}
                  onChat={onChat}
                  avatar={preferences.avatar}
                />
              ) : route === "chat" ? (
                <ChatPage
                  data={data}
                  messages={messages}
                  sending={sending}
                  onSend={(t, a) => void performSend(t, a)}
                  onRetry={retry}
                  topic={topic}
                  notify={notify}
                  avatar={preferences.avatar}
                />
              ) : route === "memories" ? (
                <MemoriesPage data={data} notify={notify} onChat={onChat} />
              ) : route === "goals" ? (
                <GoalsPage data={data} notify={notify} onChat={onChat} />
              ) : route === "journal" ? (
                <JournalPage data={data} notify={notify} onChat={onChat} />
              ) : route === "world" ? (
                <WorldPage data={data} notify={notify} onChat={onChat} />
              ) : route === "growth" ? (
                <GrowthPage data={data} notify={notify} onChat={onChat} />
              ) : route === "devices" ? (
                <DevicesPage data={data} notify={notify} onChat={onChat} />
              ) : route === "runtime" ? (
                <RuntimePage
                  data={data}
                  inspector={inspector}
                  onImport={onImport}
                  onClear={clearInspector}
                  notify={notify}
                />
              ) : (
                <SettingsPage
                  data={data}
                  preferences={preferences}
                  setPreferences={setPreferences}
                  scenario={scenario}
                  setScenario={setScenario}
                  notify={notify}
                />
              )}
            </Suspense>
          )}
        </main>
        <nav className="bottom-nav" aria-label="移动端导航">
          {[navigation[0], navigation[1], navigation[2], navigation[5]].map(
            ([id, label, Icon]) => (
              <button
                key={id}
                className={route === id ? "active" : ""}
                onClick={() => navigate(id)}
                aria-current={route === id ? "page" : undefined}
              >
                <Icon size={20} />
                <span>
                  {id === "home"
                    ? "空间"
                    : id === "chat"
                      ? "聊天"
                      : id === "memories"
                        ? "记忆"
                        : "发现"}
                </span>
              </button>
            ),
          )}
          <button onClick={() => setMenu(true)} aria-label="打开更多导航">
            <Menu size={20} />
            <span>更多</span>
          </button>
        </nav>
      </div>
      {menu && (
        <Dialog
          title="奈奈的小宇宙"
          className="navigation-dialog"
          onClose={() => setMenu(false)}
        >
          <nav aria-label="全部页面">{navItems()}</nav>
          <span className="drawer-footnote">
            DEMO · 同一个主体，很多种相遇。
          </span>
        </Dialog>
      )}
      {modal === "search" && (
        <Dialog title="在小宇宙里找找" onClose={() => setModal(null)}>
          <label className="palette-search">
            <Search size={18} />
            <input
              data-dialog-focus
              aria-label="搜索页面、记忆或计划"
              placeholder="页面、记忆、计划、关注的主题…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <kbd>ESC</kbd>
          </label>
          <div className="palette-results">
            {navigation
              .filter((n) => !query || n[1].includes(query))
              .map(([id, label, Icon]) => (
                <button
                  key={id}
                  onClick={() => {
                    navigate(id);
                    setModal(null);
                  }}
                >
                  <Icon size={18} />
                  <span>
                    {label}
                    <small>前往页面</small>
                  </span>
                  <ArrowUpRight size={15} />
                </button>
              ))}
            {data &&
              [
                ...data.memories.map((m) => ({
                  id: m.id,
                  title: m.title,
                  route: "memories" as Route,
                  type: "演示记忆",
                })),
                ...data.goals.map((g) => ({
                  id: g.id,
                  title: g.title,
                  route: "goals" as Route,
                  type: "演示计划",
                })),
                ...data.research.map((r) => ({
                  id: r.id,
                  title: r.title,
                  route: "world" as Route,
                  type: "演示研究",
                })),
              ]
                .filter((x) => query && x.title.includes(query))
                .map((x) => (
                  <button
                    key={x.id}
                    onClick={() => {
                      navigate(x.route);
                      setModal(null);
                    }}
                  >
                    <Sparkles size={18} />
                    <span>
                      {x.title}
                      <small>{x.type}</small>
                    </span>
                    <ArrowRight size={16} />
                  </button>
                ))}
          </div>
          <small className="palette-footnote">
            仅检索当前演示投影和页面，不搜索私人记忆。
          </small>
        </Dialog>
      )}
      {modal === "notifications" && (
        <Dialog title="想和你分享的片刻" onClose={() => setModal(null)}>
          <div className="notification-note">
            <Avatar size={42} />
            <div>
              <Badge tone="pink">演示分享</Badge>
              <h3>
                {sharedMessage ? "奈奈留下一则分享" : "此刻，没有新的分享"}
              </h3>
              <p>
                {sharedMessage?.text ||
                  "安静也是生活的一部分。已有话题可以等你有空时再继续。"}
              </p>
              {sharedMessage && (
                <button
                  className="text-link"
                  onClick={() => {
                    onChat("继续聊聊这则分享");
                    setModal(null);
                  }}
                >
                  打开示例话题
                  <ArrowUpRight size={15} />
                </button>
              )}
            </div>
          </div>
          <div className="notification-boundary">
            <ShieldCheck size={18} />
            <p>
              真实主动交流由 Core
              的分享意愿、权限和投递策略决定。当前没有真实推送。
            </p>
          </div>
          <button
            className="button secondary full-width"
            onClick={() => {
              navigate("settings");
              setModal(null);
            }}
          >
            管理本地打扰偏好
          </button>
        </Dialog>
      )}
      {toast && (
        <div className="toast" role="status">
          <Sparkles size={16} />
          <span>{toast}</span>
          <button aria-label="关闭提示" onClick={() => setToast("")}>
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}

const CoreApp = lazy(() =>
  import("../features/CoreApp").then((m) => ({ default: m.CoreApp })),
);
const LiveSpace = lazy(() =>
  import("../features/LiveSpace").then((m) => ({ default: m.LiveSpace })),
);
export function App() {
  const live =
    import.meta.env.VITE_NANA_DELIVERY === "live" ||
    new URLSearchParams(location.search).get("source") === "live" ||
    Boolean(
      (
        window as unknown as {
          Capacitor?: { isNativePlatform?: () => boolean };
        }
      ).Capacitor?.isNativePlatform?.(),
    );
  if (live)
    return (
      <Suspense fallback={<Loading />}>
        <LiveSpace />
      </Suspense>
    );
  return <LegacyEntry />;
}
function LegacyEntry() {
  const [source, setSource] = useState<"demo" | "core">(() =>
    new URLSearchParams(location.search).get("source") === "core"
      ? "core"
      : "demo",
  );
  const select = (value: "demo" | "core") => {
    const url = new URL(location.href);
    if (value === "core") url.searchParams.set("source", "core");
    else url.searchParams.delete("source");
    history.replaceState(null, "", url);
    setSource(value);
  };
  return source === "core" ? (
    <Suspense fallback={<Loading />}>
      <CoreApp onDemo={() => select("demo")} />
    </Suspense>
  ) : (
    <DemoApp onCore={() => select("core")} />
  );
}
