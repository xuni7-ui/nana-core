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
  PlayCircle,
} from "lucide-react";
import type {
  Envelope,
  CommandRequest,
  HostRequest,
  MessageRequest,
  ProviderCommand,
} from "../data/v2.generated";
import {
  V2Client,
  V2Error,
  noteFailureState,
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
import { ChatPane, type Turn } from "./v3/ChatPane";
import { ModelSetup, type ModelSetupPhase } from "./next/ModelSetup";
import { readModelCatalog } from "../data/model-catalog";
import { ProviderRuntimeSettings, type RuntimeBudgetInput } from "./next/ProviderRuntimeSettings";
import { DataConsole } from "./next/DataConsole";
import { readProviderSettings, type ProviderDraft } from "../data/provider-center";
import { providerCommand, modelCommand, routeCommand } from "../data/provider-commands";
import "./next/experience.css";
import { ModelCenter } from "./v3/ModelCenter";
import { MemoryCenter } from "./v3/MemoryCenter";
import { BilibiliView } from "./v3/BilibiliView";
import { PlatformPanel } from "./v3/PlatformPanel";
import { mergeRetainedTurns, retainedTurns, pendingReceiptTurns, sharedCandidates, vaultMetadata, sequenceTextWireBytes, sequenceReceiptTurns, messageReceiptTurns } from "../data/living";
import { languageFeedbackSample, languageFeedbackResponseBinding, reviewableResponse, type FeedbackChoice } from "../data/feedback";
const v3Icons = {
  home: Home,
  chat: MessageCircle,
  memories: Heart,
  room: Moon,
  journal: BookOpen,
  goals: Compass,
  world: Orbit,
  bilibili: PlayCircle,
  growth: Leaf,
  models: Sparkles,
  notifications: Bell,
  devices: Monitor,
  backup: Cloud,
  runtime: Activity,
  settings: Settings,
};
type ChatInput = {id: ReturnType<typeof crypto.randomUUID>; input: string; retain: boolean;
  privacyClass: "PROJECT" | "PERSONAL"; version: number; bodyVersion: number; expiresAt: number};
type ActiveChat = {owner: object; item: ChatInput; admitted: boolean; claimed: boolean;
  stopped: boolean; pending: Promise<void> | null; requireModel: boolean};
const v3Descriptions: Partial<Record<Destination, string>> = {
  memories: "那些被记住的片刻，每一条都值得有来处。",
  models: "认知资源可以更换，主体身份与经历保持连续。",
  settings: "把窗口调得舒服一点，把边界看得清楚一点。",
  devices: "很多扇窗，通向同一个持续的主体。",
  backup: "可靠的备份，保护同一个主体的连续性。",
};
const reasons: Record<string, string> = {
  INVALID_IDENTITY: "主体或谱系不匹配，已清除当前视图。",
  SESSION_REQUIRED: "请先登录。",
  SESSION_REVOKED: "会话已撤销或更新，请重新连接。",
  SESSION_DENIED: "登录未通过。",
  SCOPE_DENIED: "此会话没有这项权限。",
  ORIGIN_DENIED: "来源不匹配，连接已拒绝。",
  UNKNOWN_VERIFY_ONLY: "请求结果未知，请核验原回执，不要重复发送。",
  STREAM_INTERRUPTED_VERIFY_ONLY: "回复传输中断，请核验原回执；不会重复发送。",
  INVALID_STREAM: "这次回复传输未能核验，请查看原回执。",
  RECEIPT_ACTIVE_CAPACITY: "当前仍有多项操作处理中，请稍后查看原回执。",
  REVISION_CONFLICT: "状态已更新，请刷新后重新确认。",
  PROVIDER_CONFIG_REVISION_CONFLICT: "模型配置已更新，请刷新后重新确认。",
  PROVIDER_VAULT_REVISION_CONFLICT: "凭据状态已更新，请刷新后重新确认。",
  PROVIDER_VAULT_REVISION_REQUIRED: "尚未取得保险库的当前状态，请刷新后重新确认。",
  PROVIDER_HOST_NOT_AUTHORIZED: "该服务地址尚未得到宿主网络授权，请由运行负责人确认。",
  PROVIDER_CATALOG_AUTH: "服务商未接受凭据，请检查 API Key 和账户权限。",
  PROVIDER_CATALOG_HTTP: "服务商暂时无法返回模型列表，也可以手动填写模型名称。",
  PROVIDER_CATALOG_UNAVAILABLE: "模型列表读取未完成，请检查连接后手动重试。",
  PROVIDER_CATALOG_PROTOCOL_UNSUPPORTED: "该供应商暂不支持自动读取，请直接填写模型名称。",
  PROVIDER_CATALOG_WAIT: "刚刚已读取过模型列表，请稍等几秒。",
  PROVIDER_CATALOG_FORMAT: "服务商返回的列表格式不兼容，请直接填写模型名称。",
  PROVIDER_CATALOG_BOUND: "服务商列表超出单次读取范围，请手动填写模型名称。",
  PROVIDER_CATALOG_QUERY_REQUIRED: "模型分页信息无效，请重新读取列表。",
  PROVIDER_RUNTIME_CONFIGURATION_DISABLED: "宿主尚未开放运行预算设置。",
  LIFE_CONFIG_REVISION_CONFLICT: "运行配置已变化，请刷新核对后重新选择。",
  PROVIDER_RUNTIME_PROFILE_UNSUPPORTED: "请选择已启用且具有当前协议适配的远程服务商。",
  PROVIDER_CATALOG_MODEL_INVALID: "模型列表包含不兼容项目，已停止读取；可以手动填写模型名称。",
  SECRET_UNAVAILABLE: "尚未绑定可用的服务商凭据。",
  MEMORY_SEARCH_NARROW_QUERY: "这次查找范围太大，请换一个更具体的词句。",
  MEMORY_NOTE_REJECTED:"这条备注未获核验；请检查来源、保存范围和当前版本。不要重复提交原请求。",
  MEMORY_NOTE_TARGET_STALE:"这条备注已经变化或被撤回。请刷新后选择当前版本再更新，原请求未执行。",
  MEMORY_NOTE_TARGET_DENIED:"只能更新你保存的备注；原始经历和外部来源请通过原有纠错或撤回流程处理。",
  MEMORY_NOTE_PRIVACY_DOWNGRADE_DENIED:"更新不能降低原备注的隐私范围。",
  SURFACE_PERSONAL_RETENTION_NOT_AUTHORIZED:"当前入口尚未授权保存私人内容，请联系运行负责人确认，或选择已允许的保存范围。",
  SOURCE_CHANGED_REFRESH_REQUIRED: "记忆来源已更新，请刷新后重新查找。",
  PROVIDER_SETUP_CHANGED: "已保存的服务商或模型已被修改，请在下方核对后显式新建配置。",
  NATIVE_SECRET_INPUT_REQUIRED: "请在已配对的手机上管理安全凭据。",
  CORE_ALREADY_OWNED: "Core 已有运行 owner。",
  CORE_OWNER_PENDING_NO_RETRY: "已有启动进程尚待核验，不会重复启动。",
  CORE_UNAVAILABLE: "Core 暂不可用。",
  CONNECTION_LOST: "连接已断开，当前数据已清除。",
  STALE_EPOCH: "Core 运行代际已变化，请刷新。",
  STALE_RUN_NO_REPLAY: "网关已更新，旧请求不重放。",
  CAPABILITY_UNAVAILABLE: "此能力尚不可用。",
  AUTH_RATE_LIMIT: "尝试过于频繁，请稍后再试。",
  PAIRING_REQUIRED: "请先为这台手机配对。",
  NETWORK_OR_EXECUTION_UNKNOWN:
    "无法确认连接结果。请检查服务器 HTTPS 地址和网络是否可达；若已提交配对，请先在管理端核验设备状态，不要重复提交旧码。",
  HTTPS_ORIGIN_REQUIRED:
    "请输入完整 HTTPS 地址（域名和端口，不含路径、账号或参数）。",
  PAIRING_INPUT_INVALID:
    "请检查四个字段，并使用宿主生成的完整一次性设备配对码。",
  PAIRING_DENIED:
    "配对码无效、过期或已使用。请在管理端核验设备状态，必要时生成新码。",
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
type ModelSetupProgress = {
  draft: ProviderDraft; suffix: string; pid: string; mid: string; step: number;
  pendingId?: string; providerRevision?: number; credentialBound: boolean; bindingUncertain: boolean;
};
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
  const [usePairCode, setUsePairCode] = useState(false);
  const [deviceName, setDeviceName] = useState("这台安卓手机");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [priorityBusy, setPriorityBusy] = useState(false);
  const priorityPending = useRef(false);
  const writePending = useRef(false);
  useEffect(() => { writePending.current = busy; }, [busy]);
  const [nav, setNav] = useState(false);
  const [draft, setDraft] = useState("");
  const [personalDraft, setPersonalDraft] = useState(false);
  const [rememberDraft, setRememberDraft] = useState(false);
  // Opt-in for this authenticated connection only; never persisted on the device.
  const [rememberConnection, setRememberConnection] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [pairOffer, setPairOffer] = useState("");
  const offerVersion = useRef(0);
  const [offerBusy, setOfferBusy] = useState(false);
  const [pairManagement, setPairManagement] = useState(false);
  const [pairPrivate, setPairPrivate] = useState(false);
  const [devices, setDevices] = useState<Record<string, unknown>[]>([]);
  const [backupStatus, setBackupStatus] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [biliSnapshot, setBiliSnapshot] = useState<unknown>(null);
  const [sharedSnapshot, setSharedSnapshot] = useState<unknown>(null);
  const [credentialStatus, setCredentialStatus] = useState<unknown>(null);
  const [providerRuntime, setProviderRuntime] = useState<unknown>(null);
  const runtimeBudgetPending = useRef<number | null>(null);
  const modelSetupProgress = useRef<ModelSetupProgress | null>(null);
  const modelSetupPending = useRef<number | null>(null);
  const [modelSetupPhase,setModelSetupPhase] = useState<ModelSetupPhase>("NEW");
  const [modelSetupGeneration,setModelSetupGeneration] = useState(0);
  const clearModelSetup = useCallback(() => {
    modelSetupProgress.current=null;setModelSetupPhase("NEW");
    setModelSetupGeneration(value=>value+1);
  }, []);
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
  const chatInputs = useRef<ChatInput[]>([]);
  const chatDrain = useRef<object | null>(null);
  const activeChat = useRef<ActiveChat | null>(null);
  const [waitingInputs, setWaitingInputs] = useState(0);
  const clearQueuedInputs = useCallback((keepDrain = false) => {
    chatInputs.current = []; setWaitingInputs(0);
    setTurns(xs => xs.filter(turn => turn.state !== "WAITING_LOCAL"));
    if (!keepDrain && chatDrain.current) {
      activeChat.current = null;
      chatDrain.current = null; writePending.current = false; setBusy(false);
    }
  }, []);
  useEffect(() => {
    if (!chatInputs.current.length) return;
    const deadline = Math.min(...chatInputs.current.map(item => item.expiresAt));
    const timer = setTimeout(() => {
      const now = performance.now();
      const expired = new Set<string>(chatInputs.current.filter(item => item.expiresAt <= now).map(item => item.id));
      if (!expired.size) return;
      chatInputs.current = chatInputs.current.filter(item => !expired.has(item.id));
      setWaitingInputs(chatInputs.current.length);
      setTurns(xs => xs.map(turn => expired.has(turn.id) ? {id: turn.id, input: "", state: "LOCAL_EXPIRED"} : turn));
    }, Math.max(1, Math.ceil(deadline - performance.now())));
    return () => clearTimeout(timer);
  }, [waitingInputs]);
  useEffect(() => () => {
    chatInputs.current = []; chatDrain.current = null; activeChat.current = null; sessionVersion.current++;
  }, []);
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
    clearQueuedInputs();
    setDraft("");
    setPersonalDraft(false);
    setRememberDraft(false);
    setRememberConnection(false);
    setReceipt(null);
    setBackupStatus(null);
    setBiliSnapshot(null);
    setSharedSnapshot(null);
    setCredentialStatus(null);
    setProviderRuntime(null);
    if(e instanceof V2Error && /SESSION|IDENTITY|CONTRACT|SCOPE/.test(e.code))clearModelSetup();
  }, [clearQueuedInputs,clearModelSetup]);
  const accept = useCallback((b: Envelope) => {
    if (current.current?.capabilities.shared_life_retention === true && b.capabilities.shared_life_retention !== true) {
      setRememberDraft(false);
      setRememberConnection(false);
    }
    if (previousRun.current && (previousRun.current !== b.run_generation || current.current?.privacy_scope.join(",") !== b.privacy_scope.join(","))) {
      setSnapshot(null);
      setTurns([]);
      setReceipt(null);
      setBackupStatus(null);
      setBiliSnapshot(null);
      setSharedSnapshot(null);
      setCredentialStatus(null);
      setProviderRuntime(null);
      clearModelSetup();
      setDraft("");
      setPersonalDraft(false);
      setRememberDraft(false);
      setRememberConnection(false);
      bodyGeneration.current++;
    clearQueuedInputs();
    }
    previousRun.current = b.run_generation;
    current.current = b;
    setBootstrap(b);
  }, [clearQueuedInputs,clearModelSetup]);
  const acceptPrivacy = useCallback((data: Record<string, unknown>) => {
    const watermark = data.privacy_watermark;
    if (typeof watermark !== "string") return;
    if (privacy.current && privacy.current !== watermark) {
      setTurns([]);
      setDraft("");
      setPersonalDraft(false);
      setRememberDraft(false);
      setRememberConnection(false);
      setReceipt(null);
      setBiliSnapshot(null);
      setSharedSnapshot(null);
      clearModelSetup();
      bodyGeneration.current++;
    clearQueuedInputs();
    }
    privacy.current = watermark;
  }, [clearQueuedInputs,clearModelSetup]);
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
      const viewData = object(view.data);
      acceptPrivacy(viewData);
      const roles = object(b.data).roles;
      const canConverse = Array.isArray(roles) && roles.includes("CONVERSATION");
      if (!canConverse) {
        setTurns([]);
        setDraft("");
        setPersonalDraft(false);
        setRememberDraft(false);
        setRememberConnection(false);
        bodyGeneration.current++;
    clearQueuedInputs();
      }
      if (requestedPage === "chat" && canConverse && b.capabilities.conversation_history === true) {
        const history = await client.current.conversationHistory();
        if (version !== sessionVersion.current || pageVersion !== routeVersion.current || seq !== readVersion.current) return;
        acceptPrivacy(object(history.data));
        setTurns(current => mergeRetainedTurns([...retainedTurns(history.data), ...pendingReceiptTurns(history.data)], current));
      } else if (requestedPage === "chat") {
        setTurns(current => current.filter(turn => !turn.restored));
      }
      if ((requestedPage === "home" || requestedPage === "room") && b.capabilities.shared_life_candidates === true) {
        const candidates = await client.current.sharedLifeCandidates();
        if (version !== sessionVersion.current || pageVersion !== routeVersion.current || seq !== readVersion.current) return;
        acceptPrivacy(object(candidates.data));
        setSharedSnapshot(candidates.data);
      } else setSharedSnapshot(null);
      if (requestedPage === "bilibili" && b.capabilities.platform_bilibili_history === true) {
        const readings = await client.current.bilibiliHistory();
        if (version !== sessionVersion.current || pageVersion !== routeVersion.current || seq !== readVersion.current) return;
        setBiliSnapshot(readings.data);
      } else setBiliSnapshot(null);
      if (requestedPage === "models" && b.capabilities.durable_provider_binding === true
        && Array.isArray(object(b.data).roles) && (object(b.data).roles as unknown[]).includes("HOST_ADMIN")) {
        const credentials = await client.current.providerCredentials();
        if (version !== sessionVersion.current || pageVersion !== routeVersion.current || seq !== readVersion.current) return;
        setCredentialStatus(credentials.data);
      } else setCredentialStatus(null);
      if (requestedPage === "models" && b.capabilities.provider_runtime_configuration === true
        && Array.isArray(object(b.data).roles) && (object(b.data).roles as unknown[]).includes("HOST_ADMIN")) {
        const runtime=await client.current.providerRuntime();
        if(version!==sessionVersion.current || pageVersion!==routeVersion.current || seq!==readVersion.current)return;
        setProviderRuntime(runtime.data);
      } else setProviderRuntime(null);
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
      if (typeof viewData.privacy_watermark === "string" && viewData.privacy_watermark !== privacy.current) {
        // A newer auxiliary projection cannot make the older page current.
        setSnapshot(null);
        setLatency(Math.round(performance.now() - started));
        setError("");
        return;
      }
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
  }, [page, accept, acceptPrivacy, fail, clearQueuedInputs]);
  useEffect(() => {
    const hash = () => {
      const next = route();
      if (next !== pageName.current) {
        pageName.current = next;
        routeVersion.current++;
        setPage(next);
        setSnapshot(null);
        setBackupStatus(null);
        setBiliSnapshot(null);
        setSharedSnapshot(null);
        setCredentialStatus(null);
        setProviderRuntime(null);
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
      if (active && !document.hidden && !writePending.current) void refresh().catch(() => {});
    };
    // Explicit navigation must still load Manager/read views during a chat.
    // Only periodic background refresh yields to the pending write.
    void refresh().catch(() => {});
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
    const update = () => {
      const height=viewport?.height || innerHeight;
      document.documentElement.toggleAttribute("data-nana-short-viewport", innerWidth < 900 && height < 600);
      document.documentElement.style.setProperty("--v3-viewport", `${height}px`);
    };
    update();
    viewport?.addEventListener("resize", update);
    return () => {
      viewport?.removeEventListener("resize", update);
      document.documentElement.style.removeProperty("--v3-viewport");
      document.documentElement.removeAttribute("data-nana-short-viewport");
    };
  }, []);
  const login = async () => {
    if (busy) return;
    setError("");
    const subject = identity.trim();
    if ((!isNative() || usePairCode) && (!subject || subject.length > 96)) {
      setError("请填写已有主体的 Subject ID（最多 96 个字符）。");
      return;
    }
    const address = base.trim(),
      pairingCode = code.trim(),
      name = deviceName.trim();
    if (isNative()) {
      try {
        const url = new URL(address);
        if (
          url.protocol !== "https:" ||
          !url.hostname ||
          url.username ||
          url.password ||
          url.search ||
          url.hash ||
          url.pathname !== "/" ||
          address.includes("\\") ||
          address.length > 256 ||
          url.port === "0"
        )
          throw new Error();
      } catch {
        setError(reasons.HTTPS_ORIGIN_REQUIRED);
        return;
      }
      if (!name || name.length > 64) {
        setError("请填写手机名称（最多 64 个字符）。");
        return;
      }
      if (usePairCode && (pairingCode.length < 24 || pairingCode.length > 128)) {
        setError(
          "请粘贴完整的一次性设备配对码（24–128 个字符），不是短数字码、登录口令或 Provider API Key。",
        );
        return;
      }
    } else if (password.length < 12) {
      setError("请输入宿主提供的完整会话口令（至少 12 个字符）。");
      return;
    }
    clearModelSetup();
    setBusy(true);
    const version = sessionVersion.current;
    try {
      const b = isNative()
        ? usePairCode ? await client.current.pair(address, pairingCode, subject, name) : await client.current.loginDevice(address, name)
        : await client.current.login(password, subject);
      if (version === sessionVersion.current) {
        accept(b);
        if (isNative()) go("chat");
      }
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
    const d = object(r.data);
    setTurns((xs) =>
      sequenceReceiptTurns(id,d,xs) ?? messageReceiptTurns(id,d,xs),
    );
    setReceipt(d);
  };
  const cancelQueuedInput = (id: string) => {
    if (!chatInputs.current.some(item => item.id === id)) return;
    chatInputs.current = chatInputs.current.filter(item => item.id !== id);
    setWaitingInputs(chatInputs.current.length);
    setTurns(xs => xs.filter(turn => turn.id !== id));
  };
  const continueChat = () => {
    const active = activeChat.current, item = chatInputs.current[0];
    if (!active || !active.admitted || active.claimed || active.stopped || !item
        || chatDrain.current !== active.owner || item.retain || active.item.retain
        || item.privacyClass !== active.item.privacyClass || item.version !== active.item.version
        || item.bodyVersion !== active.item.bodyVersion || performance.now() >= item.expiresAt) return;
    active.claimed = true;
    chatInputs.current.shift(); setWaitingInputs(chatInputs.current.length);
    setTurns(xs => xs.map(t => t.id === item.id ? {...t,state:"REQUESTED",requestedAt:performance.now()}
      : t.id === active.item.id ? {...t,provisional:undefined} : t));
    const currentInput = () => item.version === sessionVersion.current && item.bodyVersion === bodyGeneration.current
      && chatDrain.current === active.owner;
    active.pending = (async () => {
      let dispatched = false;
      try {
        const b = await fresh();
        if (!currentInput()) return;
        if (performance.now() >= item.expiresAt) {
          setTurns(xs => xs.map(t => t.id === item.id ? {id:t.id,input:"",state:"LOCAL_EXPIRED"} : t));return;
        }
        if (!b.privacy_scope.includes(item.privacyClass)) throw new V2Error("SCOPE_DENIED");
        const request: MessageRequest = {...writeBase(b,item.id),text:item.input,topic:"daily",thread_id:"nana-space",
          privacy_class:item.privacyClass,require_model:active.requireModel,retain_shared_life:false,
          continuation_of:active.item.id};
        dispatched = true;
        const result = await client.current.write("message",request);
        if (!currentInput()) return;
        updateTurn(item.id,result);
        if (object(result.data).state !== "VERIFIED") {active.stopped=true;clearQueuedInputs(true);}
      } catch (e) {
        if (!currentInput()) return;
        if (e instanceof V2Error && ["CONTINUATION_WINDOW_CLOSED","REVISION_CONFLICT"].includes(e.code)) {
          // These exact server errors precede reservation/dispatch. Keep the
          // original ID and consent; no UNKNOWN request is automatically retried.
          chatInputs.current.unshift(item);setWaitingInputs(chatInputs.current.length);
          setTurns(xs => xs.map(t => t.id === item.id ? {...t,state:"WAITING_LOCAL"} : t));
          return;
        }
        active.stopped=true;
        if (e instanceof V2Error && /SESSION|IDENTITY|CONTRACT|SCOPE/.test(e.code)) {fail(e);return;}
        setError(explain(e));clearQueuedInputs(true);
        setTurns(xs => xs.map(t => t.id === item.id ? {id:t.id,input:"",state:dispatched?"UNKNOWN":"REJECTED"} : t));
      }
    })();
  };
  const send = async (retain = false, privacyClass: "PROJECT" | "PERSONAL" = "PROJECT") => {
    if (!draft.trim() || ((busy || writePending.current) && !chatDrain.current) || chatInputs.current.length >= 4) return;
    const owner = chatDrain.current || {};
    const queued = {id: crypto.randomUUID(), input: draft.trim(), retain, privacyClass,
      version: sessionVersion.current, bodyVersion: bodyGeneration.current,
      expiresAt: performance.now() + 20 * 60_000};
    chatInputs.current.push(queued);
    setWaitingInputs(chatInputs.current.length);
    setDraft(""); setPersonalDraft(false); setRememberDraft(false);
    setTurns(xs => [...xs.slice(-31), {id: queued.id, input: queued.input, state: "WAITING_LOCAL"}]);
    if (chatDrain.current) {continueChat();return;}
    chatDrain.current = owner; writePending.current = true; setBusy(true);
    try {
      while (chatDrain.current === owner && chatInputs.current.length) {
        const item = chatInputs.current.shift()!;
        setWaitingInputs(chatInputs.current.length);
        const {id, input, retain, privacyClass, version, bodyVersion} = item;
        if (version !== sessionVersion.current || bodyVersion !== bodyGeneration.current) break;
        if (performance.now() >= item.expiresAt) {
          setTurns(xs => xs.map(turn => turn.id === id ? {id, input: "", state: "LOCAL_EXPIRED"} : turn));
          continue;
        }
        let dispatched = false;
        let active: ActiveChat | null = null;
        let inFlight=[item],receiptId=id;
        setTurns(xs => xs.map(turn => turn.id === id ? {...turn, state: "REQUESTED", requestedAt: performance.now()} : turn));
        try {
          // Rebind before any dispatch; grouping consumes only already waiting
          // compatible bodies, with no batching timer or future-message promise.
          const b = await fresh();
          if (version !== sessionVersion.current || bodyVersion !== bodyGeneration.current) break;
          if (!b.privacy_scope.includes(privacyClass)) throw new V2Error("SCOPE_DENIED");
          if (retain && b.capabilities.shared_life_retention !== true) throw new V2Error("RETENTION_UNAVAILABLE");
          if(performance.now()>=item.expiresAt){
            setTurns(xs=>xs.map(t=>t.id===id?{id,input:"",state:"LOCAL_EXPIRED"}:t));continue;
          }
          if(b.capabilities.conversation_sequence===true && !retain){
            while(chatInputs.current.length && inFlight.length<4){
              const next=chatInputs.current[0];
              if(performance.now()>=next.expiresAt){
                chatInputs.current.shift();
                setTurns(xs=>xs.map(t=>t.id===next.id?{id:t.id,input:"",state:"LOCAL_EXPIRED"}:t));continue;
              }
              if(next.version!==version || next.bodyVersion!==bodyVersion || next.retain || next.privacyClass!==privacyClass
                || sequenceTextWireBytes([...inFlight.map(m=>m.input),next.input])>12288)break;
              inFlight.push(chatInputs.current.shift()!);
            }
          }
          setWaitingInputs(chatInputs.current.length);
          const grouped=inFlight.length>1;
          receiptId=inFlight.at(-1)!.id;
          if(grouped)setTurns(xs=>xs.map(t=>inFlight.some(m=>m.id===t.id)
            ? {...t,state:"REQUESTED",receiptId,requestedAt:performance.now()}:t));
          const request = {
            ...writeBase(b, receiptId), topic: "daily", thread_id: "nana-space", privacy_class: privacyClass,
            ...(b.capabilities.provider_readiness === true ? {require_model: true} : {}),
            ...(b.capabilities.shared_life_retention === true ? {retain_shared_life: retain} : {}),
          };
          const canContinue = !grouped && !retain && b.capabilities.conversation_continuation === true;
          if (canContinue) {
            active={owner,item,admitted:false,claimed:false,stopped:false,pending:null,
              requireModel:b.capabilities.provider_readiness===true};
            activeChat.current=active;
          }
          dispatched = true;
          const result = grouped
            ? await client.current.write("message.sequence",{...request,messages:inFlight.map(m=>({client_message_id:m.id,text:m.input}))})
            : b.capabilities.chat_streaming === true && (prefs.streamReplies || canContinue)
            ? await client.current.streamMessage({...request,text:input}, progress => {
                if (version === sessionVersion.current && bodyVersion === bodyGeneration.current) {
                  if (active) active.admitted=true;
                  setTurns(xs => xs.map(turn => turn.id === id ? {...turn, phase: progress.state,
                    ...(prefs.streamReplies && !active?.claimed && progress.text !== undefined ? {provisional: progress.text} : {})} : turn));
                  continueChat();
                }
              })
            : await client.current.write("message", {...request,text:input});
          if (version !== sessionVersion.current || bodyVersion !== bodyGeneration.current) break;
          updateTurn(receiptId, result);
          if (active) {active.admitted=false;await active.pending;}
          if (active?.stopped) break;
          // An uncertain/rejected original receipt never drains more waiting
          // bodies automatically. Only explicitly new input may start later.
          if (object(result.data).state !== "VERIFIED") { clearQueuedInputs(); break; }
          await refresh().catch(() => {});
        } catch (e) {
          if (active) {active.admitted=false;await active.pending;}
          if (version !== sessionVersion.current || bodyVersion !== bodyGeneration.current) break;
          if (e instanceof V2Error && /SESSION|IDENTITY|CONTRACT|SCOPE/.test(e.code)) {fail(e);break;}
          setError(explain(e));clearQueuedInputs(true);
          setTurns(xs=>xs.map(t=>inFlight.some(m=>m.id===t.id)
            ? {id:t.id,input:"",state:!dispatched?"REJECTED":t.id===receiptId?"UNKNOWN":"GROUP_PENDING",
              ...(inFlight.length>1?{receiptId}:{} )} : t));
          if (dispatched && e instanceof V2Error && ["UNKNOWN_VERIFY_ONLY", "STREAM_INTERRUPTED_VERIFY_ONLY",
              "INVALID_STREAM", "STREAM_RESPONSE_BOUND", "STREAM_FRAME_BOUND"].includes(e.code))
            await refresh().catch(() => {});
          break;
        } finally {
          if (activeChat.current === active) activeChat.current=null;
        }
      }
    } finally {
      if (chatDrain.current === owner) {
        chatDrain.current = null; writePending.current = false; setBusy(false);
      }
    }
  };
  const verify = async (id: string) => {
    const version = sessionVersion.current,
      bodyVersion = bodyGeneration.current;
    const parent=turns.find(t=>t.id===id)?.receiptId || id;
    try {
      const result = await client.current.receipt(parent);
      if (
        version === sessionVersion.current &&
        bodyVersion === bodyGeneration.current
      )
        updateTurn(parent, result);
    } catch (e) {
      if (version === sessionVersion.current) {
        fail(e);
        setTurns([{id:parent,input:"",state:"UNKNOWN",pendingReceipt:true}]);
      }
    }
  };
  const command = async (
    operation: CommandRequest["operation"],
    target?: string,
  ) => {
    const priority = ["PAUSE", "BUSY", "AVAILABLE", "REVOKE"].includes(operation);
    if ((busy && !priority) || priorityPending.current) return;
    if (priority) { priorityPending.current=true; setPriorityBusy(true); }
    else setBusy(true);
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
      if (priority) { priorityPending.current=false; setPriorityBusy(false); }
      else if (version === sessionVersion.current) setBusy(false);
    }
  };
  const saveLanguageFeedback=async(turn:Turn,choice:FeedbackChoice)=>{
    if(writePending.current || !turn.exchangeId || !turn.reply)throw new V2Error("REQUEST_BUSY");
    const id=crypto.randomUUID(),version=sessionVersion.current;
    let dispatched=false;
    writePending.current=true;setBusy(true);
    try{
      const b=await fresh();
      if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
      if(typeof choice!=="string" && b.capabilities.memory_use_feedback!==true)throw new V2Error("CAPABILITY_UNAVAILABLE");
      if(!reviewableResponse(turn.reply,b.capabilities.long_reply_feedback===true))throw new V2Error("CAPABILITY_UNAVAILABLE");
      const sample=languageFeedbackSample(turn,id,choice,Math.floor(Date.now()*1000));
      const responseBinding=await languageFeedbackResponseBinding(turn.reply);
      if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
      dispatched=true;
      const response=await client.current.write("conversation.feedback",{...writeBase(b,id),consent:true,
        exchange_record_id:turn.exchangeId,sample,...responseBinding});
      if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
      const result=object(response.data);setReceipt(result);
      return {id,state:String(result.state)};
    }catch(error){
      if(version!==sessionVersion.current)throw error;
      const state=noteFailureState(error,dispatched);
      setReceipt({receipt_id:id,state,operation:"LANGUAGE_FEEDBACK"});
      return {id,state};
    }finally{writePending.current=false;if(version===sessionVersion.current)setBusy(false);}
  };
  const verifyLanguageFeedback=async(id:string)=>{
    const version=sessionVersion.current;
    const response=await client.current.receipt(id);
    if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
    const result=object(response.data);setReceipt(result);
    return {id,state:String(result.state)};
  };
  const saveMemoryNote=async(text:string,privacy_class:"PUBLIC"|"PROJECT"|"PERSONAL",target_id?:string)=>{
    if(writePending.current)throw new V2Error("REQUEST_BUSY");
    const id=crypto.randomUUID(),version=sessionVersion.current;
    let dispatched=false;
    writePending.current=true;setBusy(true);
    try{
      const b=await fresh();
      if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
      dispatched=true;
      const response=await client.current.write("memories.note",{...writeBase(b,id),text,privacy_class,consent:true,...(target_id?{target_id}:{})});
      if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
      const receipt=object(response.data);setReceipt(receipt);
      setNotice(receipt.state==="VERIFIED"?"备注已保存；它是你提供的声明，不会冒充主体亲历。":typeof receipt.error==="string"?(reasons[receipt.error]||"保存结果待核验，请查看原回执。"):"保存结果待核验，不会重复提交。");
      await refresh();
      return {id,state:String(receipt.state)};
    }catch(error){
      if(version===sessionVersion.current){
        const state=noteFailureState(error,dispatched);
        setReceipt({receipt_id:id,state,operation:"MEMORY_NOTE",dispatch_happened:state==="REJECTED"?false:"UNKNOWN"});
        setNotice(explain(error));
        return {id,state};
      }
      throw error;
    }finally{writePending.current=false;if(version===sessionVersion.current)setBusy(false);}
  };
  const verifyMemoryNote=async(id:string)=>{
    const version=sessionVersion.current;
    const response=await client.current.receipt(id);
    if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
    const receipt=object(response.data);setReceipt(receipt);await refresh();
    return {id,state:String(receipt.state)};
  };
  const host = async (operation: HostRequest["operation"]) => {
    if (
      (busy && operation !== "STOP") || priorityPending.current ||
      !window.confirm(
        `确认请求云端 ${operation}？这不会创建新主体；最终状态以服务端核验为准。`,
      )
    )
      return;
    const priority = operation === "STOP";
    if (priority) clearQueuedInputs();
    if (priority) { priorityPending.current=true; setPriorityBusy(true); }
    else setBusy(true);
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
      if (priority) { priorityPending.current=false; setPriorityBusy(false); }
      else if (version === sessionVersion.current) setBusy(false);
    }
  };
  const bindProvider = async (providerId: string, revision: number) => {
    if (busy) return;
    const version = sessionVersion.current;
    setBusy(true);
    try {
      const b = await fresh();
      const credentials = b.capabilities.durable_provider_binding === true ? await client.current.providerCredentials() : null;
      if (version !== sessionVersion.current) return;
      const vault = vaultMetadata(credentials?.data);
      if (b.capabilities.durable_provider_binding === true && !vault) throw new V2Error("PROVIDER_VAULT_REVISION_REQUIRED");
      if (credentials && pageName.current === "models") setCredentialStatus(credentials.data);
      const r = await client.current.bindProviderCredential({
        ...writeBase(b), provider_profile_id: providerId, profile_revision: revision,
        ...(vault ? {expected_vault_revision: vault.revision} : {}),
      }, b.capabilities.durable_provider_binding === true);
      if (version !== sessionVersion.current) return;
      const result = object(r.data);
      if (!["BOUND_IN_HOST_MEMORY", "BOUND_IN_HOST_VAULT"].includes(String(result.state))) throw new V2Error("SECRET_BINDING_UNCONFIRMED");
      setNotice(result.state === "BOUND_IN_HOST_VAULT"
        ? "凭据已保存在宿主加密保险库，服务重启可恢复。请通过已有管理入口确认应用；没有调用模型或增加付费授权。"
        : "凭据仅绑定到服务器内存。请在管理页确认重启以应用；服务器重启后需要重新绑定。此操作没有调用模型。");
      await refresh();
    } catch (e) {
      if (version === sessionVersion.current) {
        setNotice(explain(e));
        await refresh().catch(() => {});
      }
    } finally {
      if (version === sessionVersion.current) setBusy(false);
    }
  };
  const revokeProvider = async (providerId: string, revision: number) => {
    if (busy || !window.confirm("撤销这个供应商的凭据并暂停其后续调用？已经发出的请求不会重放或被当作取消。")) return;
    const version = sessionVersion.current;
    setBusy(true);
    try {
      const b = await fresh();
      const credentials = await client.current.providerCredentials();
      if (version !== sessionVersion.current) return;
      const vault = vaultMetadata(credentials.data);
      if (!vault) throw new V2Error("PROVIDER_VAULT_REVISION_REQUIRED");
      if (pageName.current === "models") setCredentialStatus(credentials.data);
      const r = await client.current.revokeProviderCredential({
        ...writeBase(b), provider_profile_id: providerId, profile_revision: revision,
        ...(vault ? {expected_vault_revision: vault.revision} : {}),
      });
      if (version !== sessionVersion.current) return;
      const result = object(r.data);
      if (!["REVOKED", "CREDENTIAL_REVOKED", "REVOKED_AND_PROVIDER_DISABLED", "REVOKED_PROVIDER_DISABLED"].includes(String(result.state))) throw new V2Error("SECRET_REVOCATION_UNCONFIRMED");
      const affected = Array.isArray(result.disabled_provider_profile_ids) ? result.disabled_provider_profile_ids.length : 1;
      setNotice(`凭据已撤销，共暂停 ${affected} 个共用此凭据的供应商。已有请求仍以原回执为准；请通过管理入口明确重启以应用。`);
      await refresh();
    } catch (e) {
      if (version === sessionVersion.current) {
        setNotice(explain(e));
        await refresh().catch(() => {});
      }
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
  const setupModel = async (draft: ProviderDraft, setStatus: (s: string) => void) => {
    const version=sessionVersion.current;
    if(busy || writePending.current || modelSetupPending.current===version)return;
    modelSetupPending.current=version;writePending.current=true;setBusy(true);
    if(!modelSetupProgress.current){
      const suffix=crypto.randomUUID().replaceAll("-", "").slice(0,16);
      modelSetupProgress.current={draft:{...draft},suffix,pid:"provider.next-"+suffix,
        mid:"model.next-"+suffix,step:0,credentialBound:false,bindingUncertain:false};
    }
    const progress=modelSetupProgress.current;
    const currentStep=()=>{
      if(version!==sessionVersion.current || modelSetupProgress.current!==progress)
        throw new V2Error("SESSION_REVOKED");
    };
    setModelSetupPhase(progress.pendingId?"VERIFY":"RESUME");
    try {
      if(progress.bindingUncertain)throw new V2Error("SECRET_BINDING_UNCONFIRMED");
      while(progress.step<3){
        currentStep();
        if(progress.pendingId){
          setStatus("核验原请求；不会重复提交已派发步骤…");
          const pending=progress.pendingId;
          const response=await client.current.receipt(pending);currentStep();
          if(response.data.receipt_id!==pending)throw new V2Error("RESULT_UNVERIFIED");
          setReceipt(object(response.data));
          if(response.data.state==="REJECTED"){
            progress.pendingId=undefined;
            throw new V2Error(typeof response.data.error==="string"?response.data.error:"REQUEST_REJECTED");
          }
          if(response.data.state!=="VERIFIED")throw new V2Error("UNKNOWN_VERIFY_ONLY");
          progress.pendingId=undefined;progress.step++;continue;
        }
        const b=await fresh();currentStep();
        const settings=readProviderSettings((await client.current.view("settings")).data.provider_settings);currentStep();
        if(settings.state!=="CURRENT" || settings.revision===undefined)throw new V2Error("CONFIGURATION_UNAVAILABLE");
        const {pid,mid,suffix}=progress;
        const profile=settings.providers.find(p=>p.id===pid);
        if(progress.step>0){
          const expected=providerCommand(progress.draft,pid,settings.revision).provider!;
          if(!profile || !profile.enabled || profile.baseUrl!==expected.base_url || profile.protocol!==expected.protocol
            || profile.name!==expected.display_name || profile.timeoutMs!==expected.default_timeout_ms
            || (progress.providerRevision!==undefined && profile.revision!==progress.providerRevision))
            throw new V2Error("PROVIDER_SETUP_CHANGED");
          progress.providerRevision=profile.revision;
        }
        if(progress.step===2){
          const model=settings.models.find(m=>m.id===mid);
          if(!model || !model.enabled || model.providerId!==pid || model.remoteModel!==progress.draft.modelId
            || model.operations.length!==1 || model.operations[0]!==progress.draft.operation
            || model.contextLimit!==progress.draft.contextLimit || model.outputLimit!==progress.draft.outputLimit)throw new V2Error("PROVIDER_SETUP_CHANGED");
          if(!isNative() || b.capabilities.native_secret_binding!==true || profile?.revision===undefined){
            progress.step=3;setModelSetupPhase("SAVED");
            setStatus("供应商与模型已保存。请使用已授权手机绑定凭据，再手动选择默认模型；当前路由未变。");
            await refresh();return;
          }
          if(!progress.credentialBound){
            const credentials=b.capabilities.durable_provider_binding===true?await client.current.providerCredentials():null;currentStep();
            const vault=vaultMetadata(credentials?.data);
            if(b.capabilities.durable_provider_binding===true && !vault)throw new V2Error("PROVIDER_VAULT_REVISION_REQUIRED");
            setStatus("请在手机安全输入框中输入 API Key…");
            progress.bindingUncertain=true;
            try {
              const result=object((await client.current.bindProviderCredential({
                ...writeBase(b),provider_profile_id:pid,profile_revision:profile.revision,
                ...(vault?{expected_vault_revision:vault.revision}:{}),
              },b.capabilities.durable_provider_binding===true)).data);currentStep();
              if(!["BOUND_IN_HOST_MEMORY","BOUND_IN_HOST_VAULT"].includes(String(result.state)))throw new V2Error("SECRET_BINDING_UNCONFIRMED");
              progress.credentialBound=true;progress.bindingUncertain=false;
            } catch(e){
              if(e instanceof Error && e.message==="SECRET_INPUT_CANCELLED")progress.bindingUncertain=false;
              throw e;
            }
          }
        }
        const step=progress.step;
        setStatus(["保存供应商…","保存模型…","凭据已绑定，设置默认对话模型…"][step]);
        const command=step===0?providerCommand(progress.draft,pid,settings.revision)
          :step===1?modelCommand(progress.draft,pid,mid,settings.revision)
          :routeCommand("COGNITION",mid,[],settings.revision);
        if(command.provider)command.provider.secret_ref="next."+suffix;
        const id=crypto.randomUUID();progress.pendingId=id;
        const response=await client.current.write("providers.command",{...writeBase(b,id),command});currentStep();
        setReceipt(object(response.data));
        if(response.data.receipt_id!==id)throw new V2Error("RESULT_UNVERIFIED");
        if(response.data.state==="REJECTED")progress.pendingId=undefined;
        if(response.data.state!=="VERIFIED")throw new V2Error(
          typeof response.data.error==="string"?response.data.error:response.data.state==="UNKNOWN"?"UNKNOWN_VERIFY_ONLY":"REQUEST_REJECTED");
        progress.pendingId=undefined;progress.step++;
      }
      setModelSetupPhase("SAVED");
      setStatus("凭据已绑定，模型和路由已保存。实际可用性以服务器状态为准；配置可能需要重启才能生效。");
      await refresh();
    }catch(e){
      if(version!==sessionVersion.current || modelSetupProgress.current!==progress)return;
      setModelSetupPhase(progress.bindingUncertain?"BINDING_UNKNOWN":progress.pendingId?"VERIFY":"RESUME");
      if(progress.pendingId)setReceipt({receipt_id:progress.pendingId,state:"UNKNOWN",dispatch_happened:"UNKNOWN"});
      setStatus(progress.bindingUncertain?"凭据绑定结果尚待核验。请在下方凭据管理查看；不要重新提交密钥。"
        :explain(e)+" 已核验步骤保留在当前连接；继续时使用原配置 ID，待确认步骤只核验原回执。");
      await refresh().catch(()=>{});
    }finally{
      if(modelSetupPending.current===version)modelSetupPending.current=null;
      if(version===sessionVersion.current){setBusy(false);writePending.current=false;}
    }
  };
  const saveProviderRuntime = async (input: RuntimeBudgetInput) => {
    const version=sessionVersion.current;
    if (busy || writePending.current || runtimeBudgetPending.current===version) throw new V2Error("REQUEST_BUSY");
    runtimeBudgetPending.current=version;setBusy(true);
    const id=crypto.randomUUID();
    try {
      const b=await fresh();
      if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
      const response=await client.current.write("providers.runtime",{...writeBase(b,id),...input});
      if(version!==sessionVersion.current)throw new V2Error("SESSION_REVOKED");
      const result=object(response.data);setReceipt(result);
      if(result.state!=="VERIFIED")throw new V2Error(typeof result.error==="string"?result.error:"UNKNOWN_VERIFY_ONLY");
      setNotice("运行预算与连接域名已保存。请明确重启以应用；尚未调用模型。");
      await refresh();
    } catch(error) {
      if(version===sessionVersion.current){
        if(error instanceof V2Error && error.code==="UNKNOWN_VERIFY_ONLY")setReceipt({receipt_id:id,state:"UNKNOWN",dispatch_happened:"UNKNOWN"});
        setNotice(explain(error));await refresh().catch(()=>{});
      }
      throw error;
    } finally {
      if(runtimeBudgetPending.current===version)runtimeBudgetPending.current=null;
      if(version===sessionVersion.current)setBusy(false);
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
    clearQueuedInputs();
    setBusy(true);
    const pending = client.current.logout();
    client.current.clear();
    setBootstrap(null);
    setSnapshot(null);
    setTurns([]);
    setDevices([]);
    setPairOffer("");
    setDraft("");
    setPersonalDraft(false);
    setRememberDraft(false);
    setRememberConnection(false);
    setReceipt(null);
    setBackupStatus(null);
    setBiliSnapshot(null);
    setSharedSnapshot(null);
    setCredentialStatus(null);
    setProviderRuntime(null);
    clearModelSetup();
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
        [...(pairManagement
          ? ["READER", "CONVERSATION", "MANAGER", "HOST_ADMIN"]
          : ["READER", "CONVERSATION"]), ...(pairPrivate ? ["PRIVATE_CONTEXT"] : [])],
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
  const providerData = bootstrap ? object(object(bootstrap.data).provider || {}) : {};
  const rawReadiness = providerData.readiness;
  const providerReadyCode = rawReadiness && typeof rawReadiness === "object" && !Array.isArray(rawReadiness) && typeof object(rawReadiness).state === "string" ? String(object(rawReadiness).state) : undefined;
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
    setBiliSnapshot(null);
    setSharedSnapshot(null);
    setCredentialStatus(null);
    setProviderRuntime(null);
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
    ["她的世界", ["journal", "world", "bilibili", "goals", "growth"]],
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
          disabled={priorityBusy || (busy && op !== "STOP") || !admin || !healthy}
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
            <strong>生活的小宇宙</strong>
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
        data-subject-id={bootstrap?.subject_id}
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
                    ? "在线"
                    : "测试连接"
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
                持续的生活，独立的世界，
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
                isNative() ? "把生活的窗口带在身边" : "欢迎回到这个小小空间"
              }
              eyebrow="A LITTLE CLOSER, EVERY DAY"
              className="v3-login-card"
            >
              <p>连接已有的云端主体。你的手机，是通往她的新窗口。</p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void login();
                }}
              >
                {isNative() && (
                  <label>
                    服务器 HTTPS 地址
                    <input
                      aria-label="服务器 HTTPS 地址"
                      value={base}
                      onChange={(e) => setBase(e.target.value)}
                      placeholder="https://你的服务器"
                      inputMode="url"
                      autoCapitalize="none"
                      spellCheck={false}
                      autoComplete="off"
                    />
                  </label>
                )}
                {(!isNative() || usePairCode) && <label>
                  Subject ID
                  <input
                    aria-label="Subject ID"
                    value={identity}
                    onChange={(e) => setIdentity(e.target.value)}
                    maxLength={96}
                    autoComplete="off"
                    placeholder="已核验的主体 ID"
                  />
                </label>}
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
                    {usePairCode && <label>
                      一次性配对码
                      <input
                        aria-label="一次性配对码"
                        type="password"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        maxLength={128}
                        autoCapitalize="none"
                        spellCheck={false}
                        autoComplete="off"
                        aria-describedby="pair-code-help"
                      />
                      <small id="pair-code-help">
                        请粘贴宿主生成的完整设备配对码，仅在手机本地使用。当前{" "}
                        {code.trim().length} 个字符。
                      </small>
                    </label>}
                    <button type="button" className="v3-button ghost" onClick={() => setUsePairCode(!usePairCode)}>{usePairCode ? "使用服务器口令登录" : "已有配对码？"}</button>
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
                  type="submit"
                  disabled={busy}
                >
                  {busy ? "正在核验身份…" : isNative() && !usePairCode ? "登录并连接" : "安全连接"}
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
                    setPersonalDraft(false);
                    setRememberDraft(false);
                    setRememberConnection(false);
                  }}
                >
                  连接已有主体
                </button>
              </div>
            )}
            {bootstrap && bootstrap.realm !== "PRODUCTION_SINGLE_SUBJECT" && (
              <div className="v3-dev-banner">
                <ShieldCheck size={13} />
                隔离开发实例 · 非生产环境
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
                shares={healthy ? sharedCandidates(sharedSnapshot) : []}
              />
            )}
            {page === "chat" && (
              <ChatPane
                key={`${bootstrap?.run_generation || "offline"}:${privacy.current}`}
                turns={turns}
                onFeedback={manager && healthy && bootstrap?.capabilities.conversation_feedback===true ? saveLanguageFeedback : undefined}
                memoryFeedback={bootstrap?.capabilities.memory_use_feedback===true}
                longFeedback={bootstrap?.capabilities.long_reply_feedback===true}
                onVerifyFeedback={verifyLanguageFeedback}
                draft={draft}
                onDraft={setDraft}
                busy={busy}
                canQueue={chatDrain.current !== null && waitingInputs < 4}
                queuedCount={waitingInputs}
                cancelQueued={cancelQueuedInput}
                allowed={conversation}
                send={(retain, privacyClass) => void send(retain, privacyClass)}
                readiness={providerReadyCode}
                streaming={prefs.streamReplies}
                onStreaming={bootstrap?.capabilities.chat_streaming === true ? next => setPrefs({...prefs,streamReplies:next}) : undefined}
                configure={() => go("models")}
                canRemember={bootstrap?.capabilities.shared_life_retention === true}
                canUsePersonal={bootstrap?.privacy_scope.includes("PERSONAL") === true}
                personal={personalDraft}
                onPersonal={setPersonalDraft}
                remember={rememberDraft || (rememberConnection && !personalDraft)}
                onRemember={(next) => {
                  setRememberDraft(next);
                  if (!next) setRememberConnection(false);
                }}
                rememberConnection={rememberConnection}
                onRememberConnection={(next) => {
                  setRememberConnection(next);
                  setRememberDraft(false);
                }}
                verify={(id) => void verify(id)}
                notice={notify}
              />
            )}
            {page === "memories" && (
              <MemoryCenter
                key={`${bootstrap?.run_generation || "offline"}:${privacy.current}`}
                memories={memories}
                onSearch={healthy && bootstrap?.capabilities.memory_search === true ? async (query) => {
                  const version = sessionVersion.current, watermark = privacy.current;
                  try {
                    const result = await client.current.searchMemories(query);
                    if (version !== sessionVersion.current) throw new V2Error("SESSION_REVOKED");
                    if (watermark !== privacy.current || object(result.data).privacy_watermark !== watermark) {
                      await refresh(); throw new V2Error("SOURCE_CHANGED_REFRESH_REQUIRED");
                    }
                    const rows = object(result.data).memories;
                    if (!Array.isArray(rows)) throw new V2Error("SOURCE_CHANGED_REFRESH_REQUIRED");
                    return rows.map(object);
                  } catch (error) { throw new Error(explain(error)); }
                } : undefined}
                onSaveNote={manager && healthy && bootstrap?.capabilities.memory_notes===true?saveMemoryNote:undefined}
                onVerifyNote={verifyMemoryNote}
                privacyScope={snapshot?.privacy_scope}
                available={healthy}
                busy={busy}
                canWithdraw={manager && healthy}
                onWithdraw={(id) => void command("WITHDRAW", id)}
                onNotice={notify}
              />
            )}
            {page === "models" && (
              <><ModelSetup disabled={busy || !admin || !healthy || bootstrap?.capabilities.provider_configuration_write !== true} canBindCredential={isNative() && bootstrap?.capabilities.native_secret_binding===true} key={modelSetupGeneration} phase={modelSetupPhase} savedDraft={modelSetupProgress.current?.draft} onNew={clearModelSetup} onSetup={setupModel}/>
                {admin && bootstrap?.capabilities.provider_runtime_configuration===true && Boolean(providerRuntime) &&
                  <ProviderRuntimeSettings key={JSON.stringify([object(providerRuntime).configuration_revision,object(providerRuntime).profiles])} data={providerRuntime}
                    disabled={busy || !healthy} onSave={saveProviderRuntime}/>}
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
                credentialStatus={credentialStatus}
                onDiscover={admin && healthy && bootstrap?.capabilities.provider_model_discovery === true ? async (id, revision, afterId) => {
                  const version = sessionVersion.current;
                  try {
                    const result = await client.current.providerModels(id, revision, afterId);
                    if (version !== sessionVersion.current) throw new V2Error("SESSION_REVOKED");
                    const value = object(result.data);
                    if(value.provider_profile_id !== id || value.profile_revision !== revision)
                      throw new V2Error("PROVIDER_CONFIG_REVISION_CONFLICT");
                    return readModelCatalog(value);

                  } catch (error) { throw new Error(explain(error)); }
                } : undefined}
                onRevokeCredential={admin && isNative() && bootstrap?.capabilities.durable_provider_binding === true ? revokeProvider : undefined}
                onBindCredential={admin && isNative() && bootstrap?.capabilities.native_secret_binding === true ? bindProvider : undefined}
              /></>
            )}
            {page === "bilibili" && <BilibiliView data={biliSnapshot} available={healthy && bootstrap?.capabilities.platform_bilibili_history === true}/>}
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
                <PlatformPanel client={client.current} canManage={roles.includes('HOST_ADMIN') && bootstrap?.capabilities.platform_configuration_write === true}/>
                <V3Card
                  title="同一段生活，许多入口"
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
                      {roles.includes("PRIVATE_CONTEXT") && bootstrap?.privacy_scope.includes("PERSONAL") && <label className="v3-check">
                        <input type="checkbox" checked={pairPrivate} onChange={e => {
                          setPairPrivate(e.target.checked); setPairOffer(""); offerVersion.current++; setOfferBusy(false);
                        }} />
                        明确允许这台设备访问本主体已授权的个人内容
                      </label>}
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
                <DataConsole key={`${bootstrap?.run_generation}:${privacy.current}:${healthy}`} read={p => client.current.view(p)} connected={healthy}/>
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
                      这是你的交流偏好草稿。不会改写主体身份、共同历史或独立判断；当前没有服务端偏好写入接口。
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
                          { const quiet = e.target.checked;
                            setPrefs((p) => ({ ...p, quiet }));
                            if (isNative()) void nativePort.notificationQuiet({ quiet }).catch(fail);
                          }
                        }
                      />
                    </label>
                    <p>{notifications}</p>
                    {isNative() ? (
                      <div className="v3-actions">
                        <button className="v3-button soft" onClick={() =>
                          void nativePort.notificationPermission().then((r) => {
                            if (!r.granted) throw new V2Error('NOTIFICATION_PERMISSION_REQUIRED');
                            return nativePort.notificationQuiet({ quiet: prefs.quiet });
                          })
                            .then(() => nativePort.backgroundNotifications({ enabled: true }))
                            .then(() => setNotifications("后台动态提醒已安排：系统约每15分钟检查一次，可因省电而延迟；只提醒有来源的分享候选，不显示私人正文。实机送达尚待验证。"))
                            .catch(fail)
                        }>开启后台动态提醒</button>
                        <button className="v3-button soft" onClick={() =>
                          void nativePort.backgroundNotifications({ enabled: false })
                            .then(() => setNotifications("后台动态提醒已关闭。"))
                            .catch(fail)
                        }>关闭后台提醒</button>
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
                          disabled={!manager || !healthy || priorityBusy || (busy && op === "RESUME")}
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
            {receipt && page !== "chat" && (
              <details className="live-receipt v3-technical">
                <summary>最近操作 · {({VERIFIED:"已完成", UNKNOWN:"待确认", REJECTED:"未执行", REQUESTED:"处理中"} as Record<string,string>)[String(receipt.state)] || "查看详情"}</summary>
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
                    <dt>是否已提交</dt>
                    <dd>{text(receipt.dispatch_happened)}</dd>
                  </div>
                  <div>
                    <dt>错误</dt>
                    <dd>{text(receipt.error || "以当前核验为准")}</dd>
                  </div>
                </dl>
                <small>结果不明确时请先核验，不会重复提交。</small>
              </details>
            )}
            {page !== "chat" && (
              <footer className="v3-footer">
                <span>✧ 同一段生活 · 许多种相遇</span>
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
            {bootstrap && page !== "chat" && (
              <details className="live-identity v3-identity">
                <summary>身份与来源信息</summary>
                <span>{bootstrap.subject_id}</span>
                <small>
                  身份延续标识 {bootstrap.lineage_binding} ·{" "}
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
