import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Markdown from "react-markdown";
import {
  Home,
  MessageCircle,
  Heart,
  Compass,
  BookOpen,
  Orbit,
  Leaf,
  Monitor,
  Activity,
  Settings,
  Menu,
  X,
  RefreshCw,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import type {
  Envelope,
  CommandRequest,
  HostRequest,
} from "../data/v2.generated";
import {
  V2Client,
  V2Error,
  livePages,
  object,
  writeBase,
  nativePort,
  isNative,
  type LivePage,
} from "../data/v2";
import { Avatar } from "../avatar/Avatar";
import { Panel as BasePanel, Empty, Badge } from "../components/ui";
import { usePreferences } from "../app/preferences";
import "./live-space.css";
function Panel({
  title,
  children,
  className,
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <BasePanel className={className}>
      <h2>{title}</h2>
      {children}
    </BasePanel>
  );
}
const titles: Record<LivePage, string> = {
  home: "生活空间",
  chat: "和奈奈聊聊",
  memories: "共同记忆",
  goals: "小小计划",
  journal: "生活手记",
  world: "世界与发现",
  growth: "成长轨迹",
  devices: "连接的世界",
  runtime: "运行与边界",
  settings: "空间设置",
};
const icons = {
  home: Home,
  chat: MessageCircle,
  memories: Heart,
  goals: Compass,
  journal: BookOpen,
  world: Orbit,
  growth: Leaf,
  devices: Monitor,
  runtime: Activity,
  settings: Settings,
};
const reasons: Record<string, string> = {
  INVALID_IDENTITY: "主体或谱系不匹配，已清除当前视图。",
  SESSION_REQUIRED: "请先登录。",
  SESSION_REVOKED: "会话已撤销或更新，请重新连接。",
  SESSION_DENIED: "登录未通过。",
  SCOPE_DENIED: "此会话没有这项权限。",
  ORIGIN_DENIED: "来源不匹配，连接已拒绝。",
  UNKNOWN_VERIFY_ONLY: "请求结果未知，请核验原回执，不要重复发送。",
  REVISION_CONFLICT: "状态已更新，请刷新后重新确认。",
  CORE_ALREADY_OWNED: "Core 已有运行 owner。",
  CORE_OWNER_PENDING_NO_RETRY: "已有启动进程尚待核验，不会重复启动。",
  CORE_UNAVAILABLE: "Core 暂不可用。",
  CONNECTION_LOST: "连接已断开，当前数据已清除。",
  STALE_EPOCH: "Core 运行代际已变化，请刷新。",
  STALE_RUN_NO_REPLAY: "网关已更新，旧请求不重放。",
  CAPABILITY_UNAVAILABLE: "此能力尚不可用。",
  AUTH_RATE_LIMIT: "尝试过于频繁，请稍后再试。",
  PAIRING_REQUIRED: "请先为这台手机配对。",
};
function explain(e: unknown) {
  const code =
    e instanceof V2Error
      ? e.code
      : e instanceof Error
        ? e.message
        : "REQUEST_UNKNOWN";
  return (
    reasons[code] ||
    `未完成：${/^[A-Z_]{1,96}$/.test(code) ? code : "连接或结果未知"}`
  );
}
function route(): LivePage {
  const p = location.hash.slice(1);
  return livePages.includes(p as LivePage) ? (p as LivePage) : "home";
}
function text(v: unknown) {
  return typeof v === "string"
    ? v
    : typeof v === "number" || typeof v === "boolean"
      ? String(v)
      : "UNKNOWN";
}
interface Turn {
  id: string;
  input: string;
  state: string;
  reply?: string;
  provider?: string;
}
export function LiveSpace() {
  const client = useRef(new V2Client());
  const sessionVersion = useRef(0);
  const refreshing = useRef(false);
  const [page, setPage] = useState<LivePage>(route);
  const [bootstrap, setBootstrap] = useState<Envelope | null>(null);
  const [snapshot, setSnapshot] = useState<Envelope | null>(null);
  const [identity, setIdentity] = useState("");
  const [password, setPassword] = useState("");
  const [base, setBase] = useState("");
  const [code, setCode] = useState("");
  const [deviceName, setDeviceName] = useState("这台安卓手机");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [nav, setNav] = useState(false);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pairOffer, setPairOffer] = useState("");
  const [pairManagement, setPairManagement] = useState(false);
  const [devices, setDevices] = useState<Record<string, unknown>[]>([]);
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null);
  const [notifications, setNotifications] =
    useState("未请求系统通知权限；后台推送未资格");
  const current = useRef<Envelope | null>(null);
  const privacy = useRef("");
  const previousRun = useRef("");
  const [prefs, setPrefs] = usePreferences();
  const fail = useCallback((e: unknown) => {
    setError(explain(e));
    setSnapshot(null);
    setPairOffer("");
    setDevices([]);
    setTurns([]);
    privacy.current = "";
  }, []);
  const accept = useCallback((b: Envelope) => {
    if (previousRun.current && previousRun.current !== b.run_generation) {
      setTurns([]);
      setReceipt(null);
    }
    previousRun.current = b.run_generation;
    current.current = b;
    setBootstrap(b);
  }, []);
  const refresh = useCallback(async () => {
    if (refreshing.current) return;
    refreshing.current = true;
    const version = sessionVersion.current;
    try {
      const b = await client.current.bootstrap();
      if (version !== sessionVersion.current) return;
      accept(b);
      const view = await client.current.view(page);
      if (version !== sessionVersion.current) return;
      const watermark = object(view.data).privacy_watermark;
      if (typeof watermark === "string") {
        if (privacy.current && privacy.current !== watermark) setTurns([]);
        privacy.current = watermark;
      }
      current.current = view;
      setSnapshot(view);
      setError("");
    } catch (e) {
      if (version === sessionVersion.current) {
        fail(e);
        throw e;
      }
    } finally {
      refreshing.current = false;
    }
  }, [page, accept, fail]);
  useEffect(() => {
    const hash = () => setPage(route());
    window.addEventListener("hashchange", hash);
    return () => window.removeEventListener("hashchange", hash);
  }, []);
  useEffect(() => {
    if (!bootstrap) return;
    let active = true;
    const poll = () => {
      if (active && !document.hidden) void refresh().catch(() => {});
    };
    poll();
    const timer = setInterval(poll, 10000);
    const visible = () => {
      if (!document.hidden) poll();
    };
    window.addEventListener("online", poll);
    document.addEventListener("visibilitychange", visible);
    return () => {
      active = false;
      clearInterval(timer);
      window.removeEventListener("online", poll);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [Boolean(bootstrap), refresh]);
  useEffect(() => {
    if (!isNative()) {
      let active = true;
      void client.current
        .bootstrap()
        .then((b) => {
          if (active) accept(b);
        })
        .catch(() => {});
      return () => {
        active = false;
      };
    }
    const open = () => {
      void nativePort.launchRoute().then(({ page }) => {
        if (livePages.includes(page)) {
          location.hash = page;
          setPage(page);
        }
      });
    };
    open();
    window.addEventListener("nana-native-route", open);
    void nativePort
      .status()
      .then(async (s) => {
        if (s.paired) {
          setIdentity(s.subject_id || "");
          const b = await client.current.bootstrap();
          accept(b);
        }
      })
      .catch(fail);
    return () => window.removeEventListener("nana-native-route", open);
  }, [accept, fail]);
  const login = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const b = isNative()
        ? await client.current.pair(base, code, identity, deviceName)
        : await client.current.login(password, identity);
      accept(b);
    } catch (e) {
      fail(e);
    } finally {
      setPassword("");
      setCode("");
      setBusy(false);
    }
  };
  const fresh = async () => {
    const b = await client.current.bootstrap();
    accept(b);
    return b;
  };
  const updateTurn = (id: string, r: Envelope) => {
    const d = object(r.data),
      result = object(d.result || {});
    setTurns((xs) =>
      xs.map((x) =>
        x.id === id
          ? {
              ...x,
              state: text(d.state),
              reply: typeof result.text === "string" ? result.text : undefined,
              provider:
                typeof result.provider_state === "string"
                  ? result.provider_state
                  : undefined,
            }
          : x,
      ),
    );
    setReceipt(d);
  };
  const send = async () => {
    if (busy || !draft.trim()) return;
    const input = draft.trim();
    const id = crypto.randomUUID();
    setBusy(true);
    setDraft("");
    setTurns((xs) => [...xs.slice(-31), { id, input, state: "REQUESTED" }]);
    try {
      const b = await fresh();
      const r = await client.current.write("message", {
        ...writeBase(b, id),
        text: input,
        topic: "daily",
        thread_id: "nana-space",
        privacy_class: "PROJECT",
      });
      updateTurn(id, r);
      await refresh().catch(() => {});
    } catch (e) {
      setError(explain(e));
      setTurns((xs) =>
        xs.map((x) => (x.id === id ? { ...x, state: "UNKNOWN" } : x)),
      );
      setSnapshot(null);
    } finally {
      setBusy(false);
    }
  };
  const verify = async (id: string) => {
    try {
      updateTurn(id, await client.current.receipt(id));
    } catch (e) {
      setError(explain(e));
    }
  };
  const command = async (
    operation: CommandRequest["operation"],
    target?: string,
  ) => {
    if (busy) return;
    setBusy(true);
    if (operation === "WITHDRAW") {
      setTurns([]);
      setSnapshot(null);
    }
    try {
      const b = await fresh();
      const r = await client.current.write("command", {
        ...writeBase(b),
        operation,
        ...(target ? { target_id: target } : {}),
      });
      setReceipt(object(r.data));
      await refresh();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };
  const host = async (operation: HostRequest["operation"]) => {
    if (
      busy ||
      !window.confirm(
        `确认请求云端 ${operation}？这不会创建新主体；最终状态以服务端核验为准。`,
      )
    )
      return;
    setBusy(true);
    try {
      const b = await fresh();
      const confirmation = await client.current.confirm({
        operation,
        expected_revision: b.revision,
      });
      const r = await client.current.write("host.operation", {
        ...writeBase(b),
        operation,
        confirmation_id: confirmation,
      });
      setReceipt(object(r.data));
      await refresh();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };
  const logout = async () => {
    sessionVersion.current++;
    try {
      await client.current.logout();
    } catch (e) {
      setError(explain(e));
    } finally {
      client.current.clear();
      setBootstrap(null);
      setSnapshot(null);
      setTurns([]);
      setDevices([]);
      setPairOffer("");
      current.current = null;
      privacy.current = "";
      previousRun.current = "";
    }
  };
  const roles =
    bootstrap && Array.isArray(object(bootstrap.data).roles)
      ? (object(bootstrap.data).roles as string[])
      : [];
  const manager = roles.includes("MANAGER"),
    admin = roles.includes("HOST_ADMIN"),
    conversation = roles.includes("CONVERSATION");
  const hostState = snapshot ? object(object(snapshot.data).host || {}) : {};
  const data = snapshot ? object(snapshot.data) : {};
  const items = Array.isArray(data.items) ? data.items.map(object) : [];
  const memories = Array.isArray(data.memories)
    ? data.memories.map(object)
    : [];
  const go = (p: LivePage) => {
    location.hash = p;
    setPage(p);
    setNav(false);
    setSnapshot(null);
    setPairOffer("");
  };
  return (
    <div className="live-space">
      <aside
        className={`live-nav ${nav ? "open" : ""}`}
        aria-label="Nana Space 页面"
      >
        <div className="live-brand">
          <Avatar expression="neutral" size={40} />
          <strong>
            Nana Space<small>同一个奈奈，许多生活入口</small>
          </strong>
          <button
            className="icon-button"
            onClick={() => setNav(false)}
            aria-label="关闭导航"
          >
            <X size={18} />
          </button>
        </div>
        <nav>
          {livePages.map((p) => {
            const Icon = icons[p];
            return (
              <button
                key={p}
                className={p === page ? "selected" : ""}
                onClick={() => go(p)}
              >
                <Icon size={18} />
                {titles[p]}
              </button>
            );
          })}
        </nav>
        <p className="live-nav-foot">
          网页与 APK 只是入口。手机关闭后，Core 的生活由云端 Runtime 延续。
        </p>
      </aside>
      <main className="live-main">
        <header className="live-top">
          <button
            className="icon-button live-menu"
            aria-label="打开导航"
            onClick={() => setNav(true)}
          >
            <Menu />
          </button>
          <span>✧ {titles[page]}</span>
          <div>
            <Badge
              tone={
                bootstrap?.realm === "PRODUCTION_SINGLE_SUBJECT"
                  ? "mint"
                  : "violet"
              }
            >
              {bootstrap?.realm === "PRODUCTION_SINGLE_SUBJECT"
                ? "已绑定正式主体"
                : bootstrap
                  ? "开发联合资格"
                  : "尚未连接"}
            </Badge>
            {bootstrap && (
              <button
                className="icon-button"
                aria-label="刷新真实状态"
                onClick={() => void refresh().catch(() => {})}
              >
                <RefreshCw size={17} />
              </button>
            )}
          </div>
        </header>
        {error && (
          <div className="live-alert" role="alert">
            {error}
          </div>
        )}
        {!bootstrap ? (
          <section className="live-login">
            <div className="live-welcome">
              <Avatar expression="neutral" size={140} />
              <span className="eyebrow">NANA · SAME SUBJECT</span>
              <h1>把生活的入口，放在身边。</h1>
              <p>
                连接已有的云端主体。这里不会生成另一个奈奈，也不会用演示回复补齐离线状态。
              </p>
            </div>
            <Panel
              title={isNative() ? "配对这台手机" : "登录私有生活空间"}
              className="live-login-panel"
            >
              {isNative() && (
                <label>
                  私有 HTTPS 地址
                  <input
                    aria-label="私有 HTTPS 地址"
                    value={base}
                    onChange={(e) => setBase(e.target.value)}
                    placeholder="https://已批准的私有地址:8443"
                    autoComplete="off"
                  />
                </label>
              )}
              <label>
                正式或明确的开发 Subject ID
                <input
                  aria-label="Subject ID"
                  value={identity}
                  onChange={(e) => setIdentity(e.target.value)}
                  maxLength={96}
                  autoComplete="off"
                />
              </label>
              {isNative() ? (
                <>
                  <label>
                    手机名称
                    <input
                      aria-label="手机名称"
                      value={deviceName}
                      onChange={(e) => setDeviceName(e.target.value)}
                      maxLength={64}
                    />
                  </label>
                  <label>
                    一次性配对码
                    <input
                      aria-label="一次性配对码"
                      type="password"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      maxLength={128}
                      autoComplete="off"
                    />
                  </label>
                </>
              ) : (
                <label>
                  会话口令
                  <input
                    aria-label="会话口令"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    maxLength={128}
                    autoComplete="current-password"
                  />
                </label>
              )}
              <button
                className="button primary"
                onClick={() => void login()}
                disabled={
                  busy ||
                  !identity ||
                  (isNative() ? code.length < 24 : password.length < 12)
                }
              >
                {busy ? "正在核对来源与身份…" : "安全连接"}
              </button>
              <p className="live-note">
                <ShieldCheck size={15} />{" "}
                {isNative()
                  ? "设备凭据只交给原生 Keystore 网络桥。"
                  : "会话由 Secure / HttpOnly Cookie 持有。"}{" "}
                不要输入 Provider API Key。
              </p>
              <p className="live-note">
                当前接入只接收 PUBLIC /
                PROJECT；真实私人历史、生产切换和模型额度需单独授权。
              </p>
            </Panel>
          </section>
        ) : (
          <>
            <section className="live-heading">
              <span className="eyebrow">PERSISTENT · SOURCED · CONNECTED</span>
              <h1>
                {titles[page]}
                <i> ✧</i>
              </h1>
              <p>
                {page === "chat"
                  ? "消息进入原 Core，由她判断。提交、模型措辞与真实投递分别核验。"
                  : "每条内容来自当前 Core 投影；没有数据就留白，不编造她的经历。"}
              </p>
            </section>
            <div className="live-identity">
              <span>{bootstrap.subject_id}</span>
              <Badge tone="violet">epoch {text(hostState.owner_epoch)}</Badge>
              <Badge tone={hostState.process_ready ? "mint" : "rose"}>
                {hostState.process_ready ? "Core 在线" : "Core 停止或未就绪"}
              </Badge>
              <small>{snapshot?.coverage || "等待当前投影"}</small>
            </div>
            {page === "chat" ? (
              <section className="live-chat">
                <div className="live-chat-log" aria-live="polite">
                  {!turns.length && (
                    <Empty
                      title="留一点空间，开始这一刻。"
                      description="只展示本页当前会话。重连不会重发旧消息，撤回后不恢复旧正文。"
                    />
                  )}
                  {turns.map((t) => (
                    <article className="live-turn" key={t.id}>
                      <p className="live-user">{t.input}</p>
                      <div className="live-reply">
                        {t.reply ? (
                          <Markdown>{t.reply}</Markdown>
                        ) : (
                          <span>
                            {t.state === "UNKNOWN"
                              ? "结果未知，请核验原回执。"
                              : t.state === "REQUESTED"
                                ? "请求正在处理中…"
                                : `回执：${t.state}；当前没有可展示的措辞。`}
                          </span>
                        )}
                        <small>
                          {t.state}
                          {t.provider ? ` · ${t.provider}` : ""} · 不代表 QQ
                          已发送
                        </small>
                        {t.state === "UNKNOWN" && (
                          <button
                            className="button"
                            onClick={() => void verify(t.id)}
                          >
                            核验这条回执
                          </button>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
                <form
                  className="live-composer"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void send();
                  }}
                >
                  <textarea
                    aria-label="和奈奈说点什么"
                    placeholder="只发送 PUBLIC / PROJECT 内容…"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    maxLength={2048}
                    disabled={!conversation}
                  />
                  <button
                    className="button primary"
                    disabled={busy || !conversation || !draft.trim()}
                  >
                    发送
                  </button>
                </form>
              </section>
            ) : (
              <div className="live-grid">
                {page === "home" && (
                  <Panel title="这一刻">
                    <div className="live-home-avatar">
                      <Avatar expression="neutral" size={140} />
                      <p>
                        {hostState.process_ready
                          ? "同一个主体正在云端运行。当前活动与关注见下方来源投影。"
                          : "主体数据仍在；运行状态以 Supervisor 的独立健康检查为准。"}
                      </p>
                    </div>
                  </Panel>
                )}
                {page === "memories" && (
                  <Panel title="有来源的记忆">
                    <div className="live-memory-list">
                      {memories.length ? (
                        memories.map((m) => (
                          <article key={text(m.memory_id)}>
                            <div>
                              <Badge tone="violet">
                                {text(m.privacy_class)}
                              </Badge>
                              <small>
                                {text(m.epistemic_kind)} · {text(m.assessment)}
                              </small>
                            </div>
                            <p>{text(m.text)}</p>
                            <small>来源 {text(m.source_evidence_id)}</small>
                            {manager && (
                              <button
                                className="button danger"
                                disabled={busy}
                                onClick={() =>
                                  void command("WITHDRAW", text(m.memory_id))
                                }
                              >
                                申请撤回此来源记忆
                              </button>
                            )}
                          </article>
                        ))
                      ) : (
                        <Empty
                          title="当前范围没有可展示记忆"
                          description="私人 Iris 尚未导入，未授权的内容不会被补齐。"
                        />
                      )}
                    </div>
                  </Panel>
                )}
                {page === "devices" && (
                  <Panel title="入口与设备">
                    <p>
                      此 APK 管理云端；没有手机 Device Agent，不控制其他 App。
                    </p>
                    <ul>
                      {(Array.isArray(data.surfaces) ? data.surfaces : []).map(
                        (x, i) => {
                          const r = object(x);
                          return (
                            <li key={i}>
                              {text(r.platform)} · {text(r.state)}
                            </li>
                          );
                        },
                      )}
                    </ul>
                    {admin && (
                      <>
                        <button
                          className="button"
                          onClick={() =>
                            void client.current
                              .devices()
                              .then((r) =>
                                setDevices(
                                  (object(r.data).devices as unknown[]).map(
                                    object,
                                  ),
                                ),
                              )
                              .catch((e) => setError(explain(e)))
                          }
                        >
                          查看已绑定设备
                        </button>
                        <label>
                          新设备名称
                          <input
                            value={deviceName}
                            onChange={(e) => setDeviceName(e.target.value)}
                          />
                        </label>
                        <label>
                          <input
                            type="checkbox"
                            checked={pairManagement}
                            onChange={(e) => {
                              setPairManagement(e.target.checked);
                              setPairOffer("");
                            }}
                          />
                          明确授权这台设备管理云端运行（Manager / Host Admin）
                        </label>
                        <button
                          className="button"
                          onClick={() =>
                            void client.current
                              .offer(
                                deviceName,
                                pairManagement
                                  ? [
                                      "READER",
                                      "CONVERSATION",
                                      "MANAGER",
                                      "HOST_ADMIN",
                                    ]
                                  : ["READER", "CONVERSATION"],
                              )
                              .then((r) =>
                                setPairOffer(text(object(r.data).pairing_code)),
                              )
                              .catch((e) => setError(explain(e)))
                          }
                        >
                          {pairManagement
                            ? "生成明确管理权限配对码"
                            : "生成最小权限一次性配对码"}
                        </button>
                        {pairOffer && (
                          <output className="live-pair-code">
                            {pairOffer}
                            <small>120秒内仅使用一次；离开本页即清除。</small>
                          </output>
                        )}
                        {devices.map((d) => (
                          <p key={text(d.device_id)}>
                            {text(d.name)} · {d.revoked ? "已撤销" : "已绑定"}{" "}
                            {!d.revoked && (
                              <button
                                className="button danger"
                                onClick={() =>
                                  void client.current
                                    .revoke(text(d.device_id))
                                    .then(() => setDevices([]))
                                    .catch((e) => setError(explain(e)))
                                }
                              >
                                撤销
                              </button>
                            )}
                          </p>
                        ))}
                      </>
                    )}
                  </Panel>
                )}
                {page === "settings" && (
                  <>
                    <Panel title="模型资源与能力路由">
                      <p>
                        配置属于宿主，不是奈奈的身份或记忆；这里不接收 API Key。
                      </p>
                      <pre className="live-config">
                        {JSON.stringify(
                          data.provider_settings || { state: "等待当前配置" },
                          null,
                          2,
                        )}
                      </pre>
                      <p>
                        修改沿用宿主 Provider Configuration CAS
                        服务，不会自动扩大费用、隐私或执行权限。
                      </p>
                    </Panel>
                    <Panel title="空间外观">
                      <button
                        className="button"
                        onClick={() =>
                          setPrefs((p) => ({
                            ...p,
                            theme: p.theme === "dark" ? "light" : "dark",
                          }))
                        }
                      >
                        切换明暗主题
                      </button>
                      <p>外观只在本机保存，不写入主体身份。</p>
                    </Panel>
                    <Panel title="安静与会话边界">
                      {manager ? (
                        <div className="live-actions">
                          {(
                            [
                              "BUSY",
                              "AVAILABLE",
                              "PAUSE",
                              "RESUME",
                              "REVOKE",
                            ] as const
                          ).map((op) => (
                            <button
                              className="button"
                              key={op}
                              disabled={busy}
                              onClick={() => void command(op)}
                            >
                              {
                                {
                                  BUSY: "我现在忙",
                                  AVAILABLE: "我有空了",
                                  PAUSE: "暂停自主调度",
                                  RESUME: "恢复调度",
                                  REVOKE: "撤销本地执行授权",
                                }[op]
                              }
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p>
                          当前没有 Manager
                          控制权限。关系重要性不自动成为执行权限。
                        </p>
                      )}
                    </Panel>
                    <Panel title="手机通知">
                      <p>{notifications}</p>
                      {isNative() && (
                        <button
                          className="button"
                          onClick={() =>
                            void nativePort
                              .notificationPermission()
                              .then((r) =>
                                setNotifications(
                                  r.granted
                                    ? "前台系统通知权限已授权；后台推送仍未资格"
                                    : "系统通知权限未授权，其他功能可正常使用。",
                                ),
                              )
                              .catch((e) => setError(explain(e)))
                          }
                        >
                          请求必要的系统通知权限
                        </button>
                      )}
                      {isNative() && (
                        <button
                          className="button"
                          onClick={() =>
                            void nativePort
                              .notifyForeground({
                                event_id: "local-test." + crypto.randomUUID(),
                                page: "chat",
                              })
                              .then(() =>
                                setNotifications(
                                  "已请求本机测试通知；请本人核对系统通知与点击入口。",
                                ),
                              )
                              .catch((e) => setError(explain(e)))
                          }
                        >
                          发送本机通知测试（无正文）
                        </button>
                      )}
                      <p>没有真实推送服务，不宣称 App 被杀后也能收到通知。</p>
                    </Panel>
                  </>
                )}
                {(page === "runtime" || page === "settings") && (
                  <Panel title="独立宿主管理">
                    <dl className="live-facts">
                      {Object.entries(hostState).map(([k, v]) => (
                        <div key={k}>
                          <dt>{k}</dt>
                          <dd>{text(v)}</dd>
                        </div>
                      ))}
                    </dl>
                    {admin ? (
                      <div className="live-actions">
                        {(["START", "STOP", "RESTART", "BACKUP"] as const).map(
                          (op) => (
                            <button
                              className="button"
                              key={op}
                              disabled={busy}
                              onClick={() => void host(op)}
                            >
                              {
                                {
                                  START: "启动原主体",
                                  STOP: "停止 Core",
                                  RESTART: "重启并核验同一身份",
                                  BACKUP: "一致性备份",
                                }[op]
                              }
                            </button>
                          ),
                        )}
                      </div>
                    ) : (
                      <p>Host 管理权限独立于 Manager 和关系角色。</p>
                    )}
                    <p>
                      升级只接受宿主登记、已验证的 release；没有任意 Shell
                      或文件路径入口。
                    </p>
                  </Panel>
                )}
                <Panel title="当前来源投影" className="live-projections">
                  {snapshot ? (
                    items.length ? (
                      <div className="live-records">
                        {items.map((r, i) => (
                          <article key={text(r.reference) + i}>
                            <div>
                              <span>{text(r.section)}</span>
                              <Badge tone="violet">{text(r.state)}</Badge>
                            </div>
                            <strong>{text(r.category)}</strong>
                            <small>{text(r.reference)}</small>
                            {Array.isArray(r.source_memory_ids) &&
                              r.source_memory_ids.length > 0 && (
                                <small>
                                  支持来源{" "}
                                  {r.source_memory_ids.map(text).join(" · ")}
                                </small>
                              )}
                          </article>
                        ))}
                      </div>
                    ) : (
                      <Empty
                        title="此范围当前没有数据"
                        description={
                          typeof data.reason === "string"
                            ? data.reason
                            : "不使用 Demo 填充，不把未知状态写成她不存在的经历。"
                        }
                      />
                    )
                  ) : (
                    <Empty
                      title="等待当前权威状态"
                      description="失联时不恢复旧正文；可以刷新或重新连接。"
                    />
                  )}
                </Panel>
                {(page === "goals" ||
                  page === "world" ||
                  page === "growth") && (
                  <Panel title="向她提出一个方向">
                    <p>
                      建议进入原 C 判断，不直接改写目标、世界事实或技能权限。
                    </p>
                    <button className="button" onClick={() => go("chat")}>
                      到对话里提出建议
                    </button>
                  </Panel>
                )}
              </div>
            )}
            {receipt && (
              <details className="live-receipt">
                <summary>最近请求的实际回执 · {text(receipt.state)}</summary>
                <dl>
                  <dt>请求</dt>
                  <dd>{text(receipt.receipt_id)}</dd>
                  <dt>已开始 dispatch</dt>
                  <dd>{text(receipt.dispatch_happened)}</dd>
                  <dt>重试</dt>
                  <dd>不自动重试</dd>
                  <dt>结果</dt>
                  <dd>
                    {text(
                      receipt.error || "以当前核验结果为准；不代表外部送达",
                    )}
                  </dd>
                </dl>
              </details>
            )}
            <footer className="live-footer">
              <span>同一身份 · 来源可追溯 · APK 不持有 Core 权威</span>
              <button className="button" onClick={() => void logout()}>
                <LogOut size={15} />
                退出并清除本机视图
              </button>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
