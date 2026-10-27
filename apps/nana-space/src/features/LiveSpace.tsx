import { useCallback, useEffect, useRef, useState } from "react";

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
  Sun,
  Moon,
  Bell,
  Smartphone,
  Search,
  ArrowUpRight,
  ChevronRight,
  Cloud,
  WifiOff,
  Sparkles,
} from "lucide-react";
import type {
  Envelope,
  CommandRequest,
  HostRequest,
  ProviderCommand,
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

import { usePreferences } from "../app/preferences";
import "./v3/v3.css";
import {
  destinations,
  destination,
  sourcePage,
  type Destination,
} from "./v3/navigation";
import {
  HomeView,
  V3Card,
  Blank,
  RecordCards,
  BackupView,
  ConnectionView,
} from "./v3/LifeViews";
import { ChatPane } from "./v3/ChatPane";
import { ModelCenter } from "./v3/ModelCenter";
import { MemoryCenter } from "./v3/MemoryCenter";
const v3Icons = {
  home: Home,
  chat: MessageCircle,
  memories: Heart,
  room: Moon,
  journal: BookOpen,
  goals: Compass,
  world: Orbit,
  growth: Leaf,
  models: Sparkles,
  notifications: Bell,
  devices: Monitor,
  backup: Cloud,
  runtime: Activity,
  settings: Settings,
};
const v3Descriptions: Partial<Record<Destination, string>> = {
  memories: "那些被记住的片刻，每一条都值得有来处。",
  models: "认知资源可以更换，奈奈始终是奈奈。",
  settings: "把窗口调得舒服一点，把边界看得清楚一点。",
  devices: "很多扇窗，通向同一个持续的主体。",
  backup: "可靠的备份，保护同一个奈奈的连续性。",
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
function route(): Destination {
  return destination(location.hash.slice(1));
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
  const routeVersion = useRef(0);
  const pageName = useRef<Destination>(route());
  const readVersion = useRef(0);
  const [page, setPage] = useState<Destination>(route);
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
  const offerVersion = useRef(0);
  const [offerBusy, setOfferBusy] = useState(false);
  const [pairManagement, setPairManagement] = useState(false);
  const [devices, setDevices] = useState<Record<string, unknown>[]>([]);
  const [backupStatus, setBackupStatus] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [receipt, setReceipt] = useState<Record<string, unknown> | null>(null);
  const [notifications, setNotifications] =
    useState("未请求系统通知权限；后台推送未资格");
  const [browsing, setBrowsing] = useState(false);
  const [notice, setNotice] = useState("");
  const [settingsSearch, setSettingsSearch] = useState("");
  const [styleDraft, setStyleDraft] = useState<string[]>([]);
  const [latency, setLatency] = useState<number | null>(null);
  const navRef = useRef<HTMLElement>(null),
    navButton = useRef<HTMLButtonElement>(null);
  const current = useRef<Envelope | null>(null);
  const privacy = useRef("");
  const bodyGeneration = useRef(0);
  const previousRun = useRef("");
  const [prefs, setPrefs] = usePreferences();
  const fail = useCallback((e: unknown) => {
    setError(explain(e));
    setSnapshot(null);
    setPairOffer("");
    offerVersion.current++;
    setOfferBusy(false);
    setDevices([]);
    setTurns([]);
    privacy.current = "";
    bodyGeneration.current++;
    setDraft("");
    setReceipt(null);
    setBackupStatus(null);
  }, []);
  const accept = useCallback((b: Envelope) => {
    if (previousRun.current && previousRun.current !== b.run_generation) {
      setTurns([]);
      setReceipt(null);
      setBackupStatus(null);
    }
    previousRun.current = b.run_generation;
    current.current = b;
    setBootstrap(b);
  }, []);
  const refresh = useCallback(async () => {
    const seq = ++readVersion.current;
    const version = sessionVersion.current;
    const pageVersion = routeVersion.current;
    const requestedPage = pageName.current;
    const started = performance.now();
    try {
      const b = await client.current.bootstrap();
      if (
        version !== sessionVersion.current ||
        seq !== readVersion.current ||
        pageVersion !== routeVersion.current
      )
        return;
      accept(b);
      const view = await client.current.view(sourcePage(requestedPage));
      if (
        version !== sessionVersion.current ||
        seq !== readVersion.current ||
        pageVersion !== routeVersion.current
      )
        return;
      const watermark = object(view.data).privacy_watermark;
      if (typeof watermark === "string") {
        if (privacy.current && privacy.current !== watermark) {
          setTurns([]);
          setDraft("");
          setReceipt(null);
          bodyGeneration.current++;
        }
        privacy.current = watermark;
      }
      if (requestedPage === "backup" && b.capabilities.backup_status === true) {
        const backup = await client.current.backupStatus();
        if (
          version !== sessionVersion.current ||
          pageVersion !== routeVersion.current ||
          seq !== readVersion.current
        )
          return;
        setBackupStatus(object(backup.data));
      } else setBackupStatus(null);
      current.current = view;
      setSnapshot(view);
      setLatency(Math.round(performance.now() - started));
      setError("");
    } catch (e) {
      if (
        version === sessionVersion.current &&
        seq === readVersion.current &&
        pageVersion === routeVersion.current
      ) {
        fail(e);
        throw e;
      }
    }
  }, [page, accept, fail]);
  useEffect(() => {
    const hash = () => {
      const next = route();
      if (next !== pageName.current) {
        pageName.current = next;
        routeVersion.current++;
        setPage(next);
        setSnapshot(null);
        setBackupStatus(null);
        setPairOffer("");
      }
    };
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
  useEffect(() => {
    setStyleDraft([]);
    setSettingsSearch("");
    setDevices([]);
    setPairOffer("");
    offerVersion.current++;
    setOfferBusy(false);
    setOfferBusy(false);
  }, [page]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 6500);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!nav) return;
    const aside = navRef.current;
    const previous = document.activeElement as HTMLElement | null;
    aside?.querySelector<HTMLButtonElement>("button")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setNav(false);
      }
      if (e.key === "Tab" && aside) {
        const entries = Array.from(
          aside.querySelectorAll<HTMLElement>("button:not(:disabled),a[href]"),
        );
        const first = entries[0],
          last = entries.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    const back = () => setNav(false);
    window.addEventListener("nana-android-back", back);
    document.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("nana-android-back", back);
      document.removeEventListener("keydown", key);
      (previous || navButton.current)?.focus();
    };
  }, [nav]);
  useEffect(() => {
    const viewport = window.visualViewport;
    const update = () =>
      document.documentElement.style.setProperty(
        "--v3-viewport",
        `${viewport?.height || innerHeight}px`,
      );
    update();
    viewport?.addEventListener("resize", update);
    return () => {
      viewport?.removeEventListener("resize", update);
      document.documentElement.style.removeProperty("--v3-viewport");
    };
  }, []);
  const login = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    const version = sessionVersion.current;
    try {
      const b = isNative()
        ? await client.current.pair(base, code, identity, deviceName)
        : await client.current.login(password, identity);
      if (version === sessionVersion.current) accept(b);
    } catch (e) {
      fail(e);
    } finally {
      setPassword("");
      setCode("");
      if (version === sessionVersion.current) setBusy(false);
    }
  };
  const fresh = async () => {
    const version = sessionVersion.current;
    const b = await client.current.bootstrap();
    if (version !== sessionVersion.current)
      throw new V2Error("SESSION_REVOKED");
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
    const version = sessionVersion.current,
      bodyVersion = bodyGeneration.current;
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
      if (
        version !== sessionVersion.current ||
        bodyVersion !== bodyGeneration.current
      )
        return;
      updateTurn(id, r);
      await refresh().catch(() => {});
    } catch (e) {
      if (version !== sessionVersion.current) return;
      fail(e);
      // Keep only the original receipt ID. Never retain/replay uncertain bodies.
      setTurns([{ id, input: "", state: "UNKNOWN" }]);
    } finally {
      if (version === sessionVersion.current) setBusy(false);
    }
  };
  const verify = async (id: string) => {
    const version = sessionVersion.current,
      bodyVersion = bodyGeneration.current;
    try {
      const result = await client.current.receipt(id);
      if (
        version === sessionVersion.current &&
        bodyVersion === bodyGeneration.current
      )
        updateTurn(id, result);
    } catch (e) {
      if (version === sessionVersion.current) {
        fail(e);
        setTurns([{ id, input: "", state: "UNKNOWN" }]);
      }
    }
  };
  const command = async (
    operation: CommandRequest["operation"],
    target?: string,
  ) => {
    if (busy) return;
    setBusy(true);
    const version = sessionVersion.current;
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
      if (version !== sessionVersion.current) return;
      setReceipt(object(r.data));
      await refresh();
    } catch (e) {
      if (version === sessionVersion.current) fail(e);
    } finally {
      if (version === sessionVersion.current) setBusy(false);
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
    const version = sessionVersion.current;
    try {
      const b = await fresh();
      const confirmation = await client.current.confirm({
        operation,
        expected_revision: b.revision,
      });
      if (version !== sessionVersion.current) return;
      const r = await client.current.write("host.operation", {
        ...writeBase(b),
        operation,
        confirmation_id: confirmation,
      });
      if (version !== sessionVersion.current) return;
      setReceipt(object(r.data));
      await refresh();
    } catch (e) {
      if (version === sessionVersion.current) fail(e);
    } finally {
      if (version === sessionVersion.current) setBusy(false);
    }
  };
  const applyProvider = async (command: ProviderCommand) => {
    if (busy) throw new V2Error("REQUEST_BUSY");
    const id = crypto.randomUUID(),
      version = sessionVersion.current;
    setBusy(true);
    try {
      const b = await fresh();
      const r = await client.current.write("providers.command", {
        ...writeBase(b, id),
        command,
      });
      if (version !== sessionVersion.current)
        throw new V2Error("SESSION_REVOKED");
      const d = object(r.data);
      setReceipt(d);
      if (d.state !== "VERIFIED")
        throw new V2Error(
          typeof d.error === "string" ? d.error : "UNKNOWN_VERIFY_ONLY",
        );
      const result = object(d.result);
      setNotice(
        `云端配置已保存 · revision ${String(result.configuration_revision)}；不代表模型调用授权或实时生效。`,
      );
      await refresh();
    } catch (e) {
      if (version === sessionVersion.current) {
        const code = e instanceof V2Error ? e.code : "UNKNOWN_VERIFY_ONLY";
        if (code === "UNKNOWN_VERIFY_ONLY")
          setReceipt({
            receipt_id: id,
            state: "UNKNOWN",
            dispatch_happened: "UNKNOWN",
            error: code,
          });
        setNotice(
          code === "PROVIDER_CONFIG_REVISION_CONFLICT"
            ? "配置版本已变化，请刷新后重新选择；旧请求不会自动重发。"
            : code,
        );
      }
      throw e;
    } finally {
      if (version === sessionVersion.current) setBusy(false);
    }
  };
  const verifyLatestReceipt = async () => {
    const id = text(receipt?.receipt_id),
      version = sessionVersion.current;
    if (!id || busy) return;
    try {
      const r = await client.current.receipt(id);
      if (version === sessionVersion.current) {
        setReceipt(object(r.data));
        await refresh();
      }
    } catch (e) {
      if (version === sessionVersion.current) setNotice(explain(e));
    }
  };
  const logout = async () => {
    sessionVersion.current++;
    offerVersion.current++;
    bodyGeneration.current++;
    setBusy(true);
    const pending = client.current.logout();
    client.current.clear();
    setBootstrap(null);
    setSnapshot(null);
    setTurns([]);
    setDevices([]);
    setPairOffer("");
    setDraft("");
    setReceipt(null);
    setBackupStatus(null);
    setBrowsing(false);
    setStyleDraft([]);
    setNotice("");
    setError("");
    current.current = null;
    privacy.current = "";
    previousRun.current = "";
    try {
      await pending;
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  };
  const listDevices = async () => {
    const version = sessionVersion.current,
      pv = routeVersion.current;
    try {
      const r = await client.current.devices();
      if (version === sessionVersion.current && pv === routeVersion.current)
        setDevices((object(r.data).devices as unknown[]).map(object));
    } catch (e) {
      if (version === sessionVersion.current) fail(e);
    }
  };
  const offer = async () => {
    if (offerBusy) return;
    const version = sessionVersion.current,
      pv = routeVersion.current,
      ov = ++offerVersion.current;
    setOfferBusy(true);
    setPairOffer("");
    try {
      const r = await client.current.offer(
        deviceName,
        pairManagement
          ? ["READER", "CONVERSATION", "MANAGER", "HOST_ADMIN"]
          : ["READER", "CONVERSATION"],
      );
      if (
        version === sessionVersion.current &&
        pv === routeVersion.current &&
        ov === offerVersion.current
      )
        setPairOffer(text(object(r.data).pairing_code));
    } catch (e) {
      if (version === sessionVersion.current) fail(e);
    } finally {
      if (ov === offerVersion.current) setOfferBusy(false);
    }
  };
  const revokeDevice = async (id: string) => {
    if (!window.confirm("撤销这台设备的会话权限？")) return;
    const version = sessionVersion.current;
    try {
      await client.current.revoke(id);
      if (version === sessionVersion.current) {
        setDevices([]);
        setNotice("服务端已接受设备撤销。");
      }
    } catch (e) {
      if (version === sessionVersion.current) fail(e);
    }
  };
  const roles =
    bootstrap && Array.isArray(object(bootstrap.data).roles)
      ? (object(bootstrap.data).roles as string[])
      : [];
  const manager = roles.includes("MANAGER"),
    admin = roles.includes("HOST_ADMIN");
  const data = snapshot ? object(snapshot.data) : {};
  const hostState = object(
    data.host || (bootstrap ? object(bootstrap.data).host : {}) || {},
  );
  const items = Array.isArray(data.items) ? data.items.map(object) : [];
  const memories = Array.isArray(data.memories)
    ? data.memories.map(object)
    : [];
  const healthy = Boolean(snapshot) && !error;
  const conversation = roles.includes("CONVERSATION") && healthy;
  const go = (p: Destination) => {
    if (p !== pageName.current) {
      pageName.current = p;
      routeVersion.current++;
    }
    location.hash = p;
    setPage(p);
    setNav(false);
    setSnapshot(null);
    setBackupStatus(null);
    setPairOffer("");
    setNotice("");
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  const notify = (message: string) => setNotice(message);
  const connected = Boolean(bootstrap);
  const themeButton = (
    <button
      className="v3-icon-button"
      aria-label="切换晨雾与月光"
      onClick={() =>
        setPrefs((p) => ({
          ...p,
          theme:
            document.documentElement.dataset.theme === "dark"
              ? "light"
              : "dark",
        }))
      }
    >
      {prefs.theme === "light" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
  const navGroups: [string, Destination[]][] = [
    ["日常相伴", ["home", "chat", "memories", "room"]],
    ["她的世界", ["journal", "world", "goals", "growth"]],
    ["空间管理", ["models", "devices", "backup", "runtime", "settings"]],
  ];
  const navLinks = navGroups.map(([name, pages]) => (
    <div className="v3-nav-group" key={name}>
      <span>{name}</span>
      {pages.map((p) => {
        const Icon = v3Icons[p];
        return (
          <button
            key={p}
            className={p === page ? "selected" : ""}
            onClick={() => go(p)}
            aria-current={p === page ? "page" : undefined}
          >
            <Icon size={19} />
            <span>{destinations[p][0]}</span>
            {p === page && <i />}
          </button>
        );
      })}
    </div>
  ));
  const controls = (
    <div className="v3-actions">
      {(["START", "STOP", "RESTART", "BACKUP"] as const).map((op) => (
        <button
          key={op}
          className="v3-button soft"
          disabled={busy || !admin || !healthy}
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
      ))}
    </div>
  );
  return (
    <div className="live-space v3-space">
      <a href="#v3-content" className="skip-link">
        跳到主要内容
      </a>
      {nav && (
        <button
          className="v3-nav-scrim"
          aria-label="关闭导航遮罩"
          onClick={() => setNav(false)}
        />
      )}
      <aside
        className={`live-nav v3-sidebar ${nav ? "open" : ""}`}
        aria-label="Nana Space 页面"
        ref={navRef}
      >
        <button className="v3-brand" onClick={() => go("home")}>
          <span className="v3-brand-mark">✧</span>
          <span>
            Nana Space<small>A LITTLE LIFE TOGETHER</small>
          </span>
        </button>
        <button
          className="v3-icon-button v3-nav-close"
          aria-label="关闭导航"
          onClick={() => setNav(false)}
        >
          <X size={20} />
        </button>
        <div className="v3-sidebar-companion">
          <Avatar size={50} />
          <span>
            <strong>奈奈的小宇宙</strong>
            <small>
              {connected ? "同一个主体，许多种相遇" : "等一个真实的连接"}
            </small>
          </span>
          <span
            className={`v3-dot ${hostState.process_ready && healthy ? "online" : ""}`}
          />
        </div>
        <nav>{navLinks}</nav>
        <div className="v3-sidebar-bottom">
          <span>✦</span>
          <p>
            一起看世界，
            <br />
            也拥有自己的光。
          </p>
          <small>ONE NANA · MANY WINDOWS</small>
        </div>
      </aside>
      <main
        className={`live-main v3-main ${page === "chat" ? "v3-main-chat" : ""}`}
        id="v3-content"
      >
        <header className="live-top v3-top">
          <div className="v3-top-title">
            <button
              className="v3-icon-button v3-mobile-menu"
              aria-label="打开导航"
              onClick={() => setNav(true)}
              ref={navButton}
            >
              <Menu size={22} />
            </button>
            <span className="v3-top-brand">
              Nana Space <span>/</span>
            </span>
            <span>{destinations[page][0]}</span>
          </div>
          <div className="v3-top-tools">
            <span className="v3-connection-label">
              <span className={`v3-dot ${healthy ? "online" : ""}`} />
              {connected
                ? healthy
                  ? bootstrap?.realm === "PRODUCTION_SINGLE_SUBJECT"
                    ? "已连接正式主体"
                    : "开发连接"
                  : "状态待确认"
                : "未连接"}
            </span>
            <button
              className="v3-icon-button"
              aria-label="打开通知信箱"
              onClick={() => go("notifications")}
            >
              <Bell size={18} />
            </button>
            {themeButton}
            {connected && (
              <button
                className="v3-icon-button"
                aria-label="退出并清除本机视图"
                title="退出并清除本机视图"
                onClick={() => void logout()}
              >
                <LogOut size={16} />
              </button>
            )}
            {connected && (
              <button
                className="v3-icon-button"
                aria-label="刷新真实状态"
                onClick={() => void refresh().catch(() => {})}
              >
                <RefreshCw size={17} />
              </button>
            )}
            <button
              className="v3-profile-button"
              aria-label="打开设置中心"
              onClick={() => go("settings")}
            >
              <Avatar size={31} />
            </button>
          </div>
        </header>
        {error && (
          <div className="v3-error" role="alert">
            <WifiOff size={17} />
            <span>{error}</span>
            {connected && (
              <button onClick={() => void refresh().catch(() => {})}>
                重新读取状态
              </button>
            )}
          </div>
        )}
        {connected && !snapshot && !error && (
          <div
            className="v3-skeleton"
            role="status"
            aria-label="正在读取当前来源投影"
          >
            <span />
            <span />
            <span />
          </div>
        )}
        {!connected && !browsing ? (
          <section className="v3-welcome">
            <div className="v3-welcome-visual">
              <div className="v3-welcome-orbit" />
              <Avatar size={240} />
              <span className="v3-eyebrow">NANA SPACE · V3</span>
              <h1>
                生活有了一个
                <br />
                <em>柔软的入口。</em>
              </h1>
              <p>
                同一个奈奈。属于她的世界，
                <br />
                和我们慢慢积累的日常。
              </p>
              <div className="v3-inline">
                <span className="v3-chip">持续的主体</span>
                <span className="v3-chip">真实的记忆</span>
                <span className="v3-chip">自由地生长</span>
              </div>
            </div>
            <V3Card
              title={
                isNative() ? "把奈奈的窗口带在身边" : "欢迎回到这个小小空间"
              }
              eyebrow={isNative() ? "PAIR YOUR DEVICE" : "CONNECT TO YOUR NANA"}
              className="v3-login-card"
            >
              <p>连接已有的云端主体。这里不会创建另一个奈奈。</p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void login();
                }}
              >
                {isNative() && (
                  <label>
                    私有 HTTPS 地址
                    <input
                      aria-label="私有 HTTPS 地址"
                      value={base}
                      onChange={(e) => setBase(e.target.value)}
                      placeholder="https://私有地址:8443"
                      autoComplete="off"
                    />
                  </label>
                )}
                <label>
                  Subject ID
                  <input
                    aria-label="Subject ID"
                    value={identity}
                    onChange={(e) => setIdentity(e.target.value)}
                    maxLength={96}
                    autoComplete="off"
                    placeholder="已核验的主体 ID"
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
                      placeholder="由可信宿主提供"
                    />
                  </label>
                )}
                <button
                  className="v3-button primary v3-full"
                  disabled={
                    busy ||
                    !identity ||
                    (isNative() ? code.length < 24 : password.length < 12)
                  }
                >
                  {busy ? "正在核验身份…" : "安全连接"}
                  <ArrowUpRight size={17} />
                </button>
              </form>
              <div className="v3-secure-note">
                <ShieldCheck size={17} />
                <span>
                  {isNative()
                    ? "配对凭据由原生 Keystore 保护，网页不可见。"
                    : "会话由 Secure / HttpOnly Cookie 保护。"}{" "}
                  不要输入 Provider API Key。
                </span>
              </div>
              <button
                className="v3-button ghost v3-full"
                onClick={() => setBrowsing(true)}
              >
                先看看空间 · 离线浏览 <ChevronRight size={15} />
              </button>
            </V3Card>
          </section>
        ) : (
          <>
            {!connected && (
              <div className="v3-offline-note">
                <Cloud size={16} />
                <span>离线浏览 · 所有生活记录留白，配置仅为本页草稿</span>
                <button
                  onClick={() => {
                    setBrowsing(false);
                    setDraft("");
                  }}
                >
                  连接奈奈
                </button>
              </div>
            )}
            {bootstrap && bootstrap.realm !== "PRODUCTION_SINGLE_SUBJECT" && (
              <div className="v3-dev-banner">
                <ShieldCheck size={13} />
                明确的开发主体 · 不是云端正式奈奈
              </div>
            )}
            {page !== "home" && page !== "room" && page !== "chat" && (
              <section className="v3-page-heading">
                <span className="v3-eyebrow">
                  {page === "models"
                    ? "AI RESOURCES & CAPABILITY ROUTING"
                    : page === "memories"
                      ? "EVERY MEMORY HAS A SOURCE"
                      : "A CONTINUOUS LIFE, MANY WAYS TO CONNECT"}
                </span>
                <h1>
                  {destinations[page][0]}
                  <span> ✧</span>
                </h1>
                <p>
                  {v3Descriptions[page] ||
                    "来自同一个 Core 的真实记录，保留来源和边界。"}
                </p>
              </section>
            )}
            {(page === "home" || page === "room") && (
              <HomeView
                items={items}
                ready={healthy && Boolean(hostState.process_ready)}
                connected={connected}
                room={page === "room"}
                go={go}
                avatar={prefs.avatar}
              />
            )}
            {page === "chat" && (
              <ChatPane
                key={`${bootstrap?.run_generation || "offline"}:${privacy.current}`}
                turns={turns}
                draft={draft}
                onDraft={setDraft}
                busy={busy}
                allowed={conversation}
                send={() => void send()}
                verify={(id) => void verify(id)}
                notice={notify}
              />
            )}
            {page === "memories" && (
              <MemoryCenter
                key={`${bootstrap?.run_generation || "offline"}:${privacy.current}`}
                memories={memories}
                available={healthy}
                busy={busy}
                canWithdraw={manager && healthy}
                onWithdraw={(id) => void command("WITHDRAW", id)}
                onNotice={notify}
              />
            )}
            {page === "models" && (
              <ModelCenter
                key={`${bootstrap?.run_generation || "offline"}:${privacy.current}:${healthy}`}
                settings={data.provider_settings}
                available={healthy}
                onNotice={notify}
                canConfigure={
                  admin &&
                  healthy &&
                  bootstrap?.capabilities.provider_configuration_write === true
                }
                busy={busy}
                onApply={applyProvider}
              />
            )}
            {page === "backup" && (
              <BackupView
                host={hostState}
                status={backupStatus}
                canBackup={admin && healthy}
                busy={busy}
                backup={() => void host("BACKUP")}
              />
            )}
            {["journal", "goals", "world", "growth", "notifications"].includes(
              page,
            ) && (
              <div className="v3-stack">
                <V3Card
                  title={
                    page === "notifications"
                      ? "值得被看见的消息"
                      : page === "growth"
                        ? "一步一步，真正学会"
                        : page === "world"
                          ? "她正在留意的世界"
                          : page === "goals"
                            ? "有自己的方向，也可以暂缓"
                            : "发生过，才写下来"
                  }
                  eyebrow={
                    page === "growth"
                      ? "LEARNING & QUALIFIED SKILLS"
                      : "SOURCED CORE PROJECTION"
                  }
                >
                  <RecordCards key={page} items={items} />
                </V3Card>
                {page === "growth" && (
                  <div className="v3-notice">
                    <ShieldCheck size={19} />
                    <span>
                      技能资格和执行权限分开。安装新技能需后端流程；当前不在前端运行代码。bwrap
                      未资格的 Code Skills 保持不可用，其余原有能力不因此关闭。
                    </span>
                  </div>
                )}
                {page === "notifications" && (
                  <p className="v3-muted">
                    当前 API
                    未提供独立通知信箱，仅展示同源生活记录。后台推送尚未接入，不声称
                    App 退出后仍会收到消息。
                  </p>
                )}
                {page !== "notifications" && (
                  <button className="v3-button soft" onClick={() => go("chat")}>
                    <MessageCircle size={17} />
                    和她聊聊这个方向
                  </button>
                )}
              </div>
            )}
            {page === "devices" && (
              <div className="v3-stack">
                <V3Card
                  title="同一个奈奈，许多生活入口"
                  eyebrow="ONE SUBJECT · MANY SURFACES"
                >
                  <div className="v3-device-grid">
                    {[
                      "这台手机",
                      "电脑 / 网页",
                      "QQ",
                      "哔哩哔哩",
                      "未来眼镜",
                    ].map((name, i) => (
                      <article key={name}>
                        <span className="v3-device-icon">
                          {i === 0 ? (
                            <Smartphone />
                          ) : i === 1 ? (
                            <Monitor />
                          ) : (
                            <Orbit />
                          )}
                        </span>
                        <h3>{name}</h3>
                        <small>
                          {i === 0 && isNative() && connected
                            ? "当前配对会话"
                            : i === 1 && connected && !isNative()
                              ? "当前网页会话"
                              : "未核验 / 未提供连接回执"}
                        </small>
                      </article>
                    ))}
                  </div>
                  <p className="v3-muted">
                    设备是入口，不拥有第二份长期记忆。这里不控制手机其他
                    App，也不自动接管 QQ / B站。
                  </p>
                  <div className="v3-tag-row">
                    {(Array.isArray(data.surfaces) ? data.surfaces : []).map(
                      (s, i) => {
                        const r = object(s);
                        return (
                          <span className="v3-chip" key={i}>
                            {text(r.platform)} · {text(r.state)}
                          </span>
                        );
                      },
                    )}
                  </div>
                </V3Card>
                <V3Card title="连接诊断">
                  <ConnectionView
                    host={hostState}
                    connected={healthy}
                    roles={roles}
                  />
                  <div className="v3-inline">
                    <span className="v3-chip">
                      最近读取 {latency === null ? "尚未测量" : `${latency} ms`}
                    </span>
                    <button
                      className="v3-button soft"
                      disabled={!connected}
                      onClick={() => void refresh().catch(() => {})}
                    >
                      重新读取
                    </button>
                  </div>
                </V3Card>
                <V3Card title="配对与设备权限" eyebrow="EXPLICIT DEVICE GRANTS">
                  {admin && healthy ? (
                    <>
                      <button
                        className="v3-button soft"
                        onClick={() => void listDevices()}
                      >
                        查看已绑定设备
                      </button>
                      <label>
                        新设备名称
                        <input
                          value={deviceName}
                          onChange={(e) => {
                            setDeviceName(e.target.value);
                            setPairOffer("");
                            offerVersion.current++;
                            setOfferBusy(false);
                          }}
                          maxLength={64}
                        />
                      </label>
                      <label className="v3-check">
                        <input
                          type="checkbox"
                          checked={pairManagement}
                          onChange={(e) => {
                            setPairManagement(e.target.checked);
                            setPairOffer("");
                            offerVersion.current++;
                            setOfferBusy(false);
                          }}
                        />
                        明确授权这台设备管理云端运行（Manager / Host Admin）
                      </label>
                      <button
                        className="v3-button primary"
                        disabled={offerBusy}
                        onClick={() => void offer()}
                      >
                        {pairManagement
                          ? "生成明确管理权限配对码"
                          : "生成最小权限一次性配对码"}
                      </button>
                      {pairOffer && (
                        <output className="live-pair-code">
                          {pairOffer}
                          <small>
                            120 秒单次使用；离开页面清除，不写日志。
                          </small>
                        </output>
                      )}
                      {devices.map((d) => (
                        <div
                          className="v3-device-binding"
                          key={text(d.device_id)}
                        >
                          <span>
                            {text(d.name)}
                            <small>{d.revoked ? "已撤销" : "已绑定"}</small>
                          </span>
                          {!d.revoked && (
                            <button
                              className="v3-button danger"
                              onClick={() =>
                                void revokeDevice(text(d.device_id))
                              }
                            >
                              撤销
                            </button>
                          )}
                        </div>
                      ))}
                    </>
                  ) : (
                    <Blank title="需要 Host Admin 的明确授权">
                      重要关系不会自动变成设备管理权。普通会话仍可在已获权限内使用。
                    </Blank>
                  )}
                </V3Card>
              </div>
            )}
            {page === "runtime" && (
              <div className="v3-stack">
                <V3Card
                  title="持续存在，可靠地休息"
                  eyebrow="RUNTIME & GOVERNANCE"
                >
                  <ConnectionView
                    host={hostState}
                    connected={healthy}
                    roles={roles}
                  />
                  <details className="v3-technical">
                    <summary>运行元数据与诊断</summary>
                    <dl className="v3-facts">
                      {Object.entries(hostState).map(([k, v]) => (
                        <div key={k}>
                          <dt>{k}</dt>
                          <dd>{text(v)}</dd>
                        </div>
                      ))}
                    </dl>
                  </details>
                  {controls}
                  <p className="v3-muted">
                    仅控制已绑定的原主体，需 Host Admin +
                    服务端单次确认。不会通过 APK 创建 genesis 或执行任意 Shell。
                  </p>
                </V3Card>
                <V3Card title="当前活动与未确认结果">
                  <RecordCards items={items} />
                </V3Card>
              </div>
            )}
            {page === "settings" && (
              <div className="v3-settings">
                <label className="v3-search">
                  <Search size={18} />
                  <input
                    aria-label="搜索设置"
                    placeholder="搜索外观、通知、连接…"
                    value={settingsSearch}
                    onChange={(e) => setSettingsSearch(e.target.value)}
                  />
                </label>
                {(!settingsSearch ||
                  "外观晨雾月光主题字号动画角色".includes(settingsSearch)) && (
                  <V3Card title="空间外观" eyebrow="MAKE YOURSELF AT HOME">
                    <div className="v3-theme-grid">
                      {(
                        [
                          ["light", "晨雾", "柔亮的薰衣草与微光"],
                          ["dark", "月光", "深蓝紫里的安静时刻"],
                          ["system", "跟随系统", "随你的设备一起变换"],
                        ] as const
                      ).map(([id, name, note]) => (
                        <button
                          aria-pressed={prefs.theme === id}
                          className={`v3-theme-option ${prefs.theme === id ? "selected" : ""}`}
                          key={id}
                          onClick={() => setPrefs((p) => ({ ...p, theme: id }))}
                        >
                          <span className={`v3-theme-swatch ${id}`}>
                            {id === "light" ? (
                              <Sun size={21} />
                            ) : id === "dark" ? (
                              <Moon size={21} />
                            ) : (
                              <Monitor size={21} />
                            )}
                          </span>
                          <strong>{name}</strong>
                          <small>{note}</small>
                        </button>
                      ))}
                    </div>
                    <div className="v3-setting-row">
                      <span>
                        <strong>文字大小</strong>
                        <small>只改变这台设备的阅读体验</small>
                      </span>
                      <select
                        aria-label="文字大小"
                        value={prefs.fontScale}
                        onChange={(e) =>
                          setPrefs((p) => ({
                            ...p,
                            fontScale: Number(e.target.value),
                          }))
                        }
                      >
                        {[0.9, 1, 1.1, 1.2].map((n) => (
                          <option key={n} value={n}>
                            {Math.round(n * 100)}%
                          </option>
                        ))}
                      </select>
                    </div>
                    <label className="v3-setting-row">
                      <span>
                        <strong>柔和动画</strong>
                        <small>同时尊重系统 reduced-motion</small>
                      </span>
                      <input
                        type="checkbox"
                        checked={prefs.motion}
                        onChange={(e) =>
                          setPrefs((p) => ({ ...p, motion: e.target.checked }))
                        }
                      />
                    </label>
                    <label className="v3-setting-row">
                      <span>
                        <strong>显示角色</strong>
                        <small>形象是表达层，不改写真实心情</small>
                      </span>
                      <input
                        type="checkbox"
                        checked={prefs.avatar}
                        onChange={(e) =>
                          setPrefs((p) => ({ ...p, avatar: e.target.checked }))
                        }
                      />
                    </label>
                  </V3Card>
                )}
                {(!settingsSearch ||
                  "交流风格人设偏好简短倾听玩笑".includes(settingsSearch)) && (
                  <V3Card
                    title="交流方式"
                    eyebrow="PREFERENCES, NOT A NEW IDENTITY"
                  >
                    <p className="v3-muted">
                      这是你的交流偏好草稿。不会改写奈奈的身份、共同历史或独立判断；当前没有服务端偏好写入接口。
                    </p>
                    <div className="v3-tag-row">
                      {["短一点", "多倾听", "轻松一点", "需要时直说"].map(
                        (s) => (
                          <button
                            className={`v3-chip ${styleDraft.includes(s) ? "selected" : ""}`}
                            aria-pressed={styleDraft.includes(s)}
                            key={s}
                            onClick={() =>
                              setStyleDraft((xs) =>
                                xs.includes(s)
                                  ? xs.filter((x) => x !== s)
                                  : [...xs, s],
                              )
                            }
                          >
                            {s}
                          </button>
                        ),
                      )}
                    </div>
                    <button
                      className="v3-button soft"
                      onClick={() =>
                        notify(
                          "交流偏好仅在本页草稿中选择；后端支持后才可授权同步。",
                        )
                      }
                      disabled={!styleDraft.length}
                    >
                      查看草稿状态
                    </button>
                    <small>离开设置即清除；未修改云端。</small>
                  </V3Card>
                )}
                {(!settingsSearch ||
                  "通知安静忙交流权限".includes(settingsSearch)) && (
                  <V3Card title="安静、通知与边界">
                    <label className="v3-setting-row">
                      <span>
                        <strong>本机安静偏好</strong>
                        <small>仅本地显示偏好，不冒充 Core BUSY 状态</small>
                      </span>
                      <input
                        type="checkbox"
                        checked={prefs.quiet}
                        onChange={(e) =>
                          setPrefs((p) => ({ ...p, quiet: e.target.checked }))
                        }
                      />
                    </label>
                    <p>{notifications}</p>
                    {isNative() ? (
                      <div className="v3-actions">
                        <button
                          className="v3-button soft"
                          onClick={() =>
                            void nativePort
                              .notificationPermission()
                              .then((r) =>
                                setNotifications(
                                  r.granted
                                    ? "前台通知权限已授权；后台推送尚未资格"
                                    : "系统通知权限未授权",
                                ),
                              )
                              .catch(fail)
                          }
                        >
                          请求系统通知权限
                        </button>
                        <button
                          className="v3-button soft"
                          onClick={() =>
                            void nativePort
                              .notifyForeground({
                                event_id: "local-test." + crypto.randomUUID(),
                                page: "chat",
                              })
                              .then(() =>
                                notify(
                                  "已请求本机测试通知；请在手机核对，不代表后台送达。",
                                ),
                              )
                              .catch(fail)
                          }
                        >
                          发送本机通知测试（无正文）
                        </button>
                      </div>
                    ) : (
                      <p className="v3-muted">
                        网页通知未接入，不会自动请求设备权限。
                      </p>
                    )}
                    <div className="v3-actions">
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
                          className="v3-button soft"
                          key={op}
                          disabled={!manager || !healthy || busy}
                          onClick={() => {
                            if (
                              op !== "REVOKE" ||
                              window.confirm(
                                "确认撤销当前本地执行授权？不会抹去她的判断。",
                              )
                            )
                              void command(op);
                          }}
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
                    <small>
                      这些云端动作需要 Manager
                      权限；本机偏好与正式执行授权分开。
                    </small>
                  </V3Card>
                )}
                {(!settingsSearch ||
                  "连接模型备份设备账号退出".includes(settingsSearch)) && (
                  <V3Card title="连接与管理">
                    <div className="v3-settings-links">
                      {(
                        [
                          ["models", "模型与能力路由"],
                          ["devices", "设备与会话权限"],
                          ["backup", "备份与恢复资格"],
                          ["runtime", "运行管理"],
                        ] as const
                      ).map(([p, s]) => (
                        <button key={p} onClick={() => go(p)}>
                          <span>{s}</span>
                          <ChevronRight size={17} />
                        </button>
                      ))}
                    </div>
                    {controls}
                    <p className="v3-muted">
                      运行管理始终由宿主确认；这里只是入口，没有第二套主体权限。
                    </p>
                  </V3Card>
                )}
              </div>
            )}
            {receipt && (
              <details className="live-receipt v3-technical">
                <summary>最近请求回执 · {text(receipt.state)}</summary>
                <button
                  className="button"
                  disabled={busy}
                  onClick={() => void verifyLatestReceipt()}
                >
                  核验当前回执
                </button>
                <dl className="v3-facts">
                  <div>
                    <dt>请求</dt>
                    <dd>{text(receipt.receipt_id)}</dd>
                  </div>
                  <div>
                    <dt>已 dispatch</dt>
                    <dd>{text(receipt.dispatch_happened)}</dd>
                  </div>
                  <div>
                    <dt>错误</dt>
                    <dd>{text(receipt.error || "以当前核验为准")}</dd>
                  </div>
                </dl>
                <small>不自动重试或 fallback，不代表外部投递成功。</small>
              </details>
            )}
            {page !== "chat" && (
              <footer className="v3-footer">
                <span>✧ 同一个奈奈 · 许多种相遇</span>
                {connected ? (
                  <button onClick={() => go("settings")}>
                    空间设置 <ChevronRight size={14} />
                  </button>
                ) : (
                  <button onClick={() => setBrowsing(false)}>
                    连接已有主体 <ArrowUpRight size={14} />
                  </button>
                )}
              </footer>
            )}
            {bootstrap && (
              <details className="live-identity v3-identity">
                <summary>身份与来源信息</summary>
                <span>{bootstrap.subject_id}</span>
                <small>
                  lineage {bootstrap.lineage_binding} ·{" "}
                  {snapshot?.coverage || "等待当前投影"}
                </small>
              </details>
            )}
          </>
        )}
      </main>
      {(connected || browsing) && (
        <nav className="v3-bottom-nav" aria-label="移动端导航">
          {(["home", "chat", "memories", "models"] as const).map((p) => {
            const Icon = v3Icons[p];
            return (
              <button
                key={p}
                aria-current={page === p ? "page" : undefined}
                className={page === p ? "selected" : ""}
                onClick={() => go(p)}
              >
                <Icon size={21} />
                <span>
                  {
                    {
                      home: "空间",
                      chat: "聊天",
                      memories: "记忆",
                      models: "模型",
                    }[p]
                  }
                </span>
              </button>
            );
          })}
          <button
            aria-label="打开更多导航"
            className={
              !["home", "chat", "memories", "models"].includes(page)
                ? "selected"
                : ""
            }
            onClick={() => setNav(true)}
          >
            <Menu size={21} />
            <span>更多</span>
          </button>
        </nav>
      )}
      {notice && (
        <div className="v3-toast" role="status">
          <Sparkles size={17} />
          <span>{notice}</span>
          <button aria-label="关闭提示" onClick={() => setNotice("")}>
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
