import { useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  MessageCircle,
  Sparkles,
  Moon,
  BookOpen,
  Heart,
  ShieldCheck,
  Cloud,
  HardDrive,
  Laptop,
  LockKeyhole,
  Link2,
  Fingerprint,
  ChevronRight,
  Leaf,
  CircleHelp,
} from "lucide-react";
import { Avatar } from "../../avatar/Avatar";
import type { Destination } from "./navigation";
import type { SharedCandidate } from "../../data/living";

export function label(value: unknown, fallback = "尚未提供") {
  return typeof value === "string"
    ? value
    : typeof value === "number" || typeof value === "boolean"
      ? String(value)
      : fallback;
}
const statusNames: Record<string, string> = {
  ACTIVE: "进行中",
  REST: "休息",
  WATCH: "观察",
  WAIT: "等待",
  UNKNOWN: "待核验",
  VERIFIED: "已核验",
  COMPLETE: "已完成",
  COMPLETED: "已完成",
  QUALIFIED: "已资格",
  SUSPENDED: "已暂停",
  RETIRED: "已退役",
  OPEN: "未完成",
  SETTLED: "已安定",
  NO_ACTION: "暂不行动",
  TRANSIENT: "刚浮现的念头",
  INTEREST: "想继续了解",
  DEFERRED: "先放一放",
  PROPOSED: "正在斟酌",
  ABANDONED: "已经放下",
  EXPIRED: "暂时淡出",
  SEEKING: "想找人聊聊",
  QUIET: "想安静一会儿",
  SATURATED: "交流暂时够了",
  RECOVERING: "先缓一缓",
};
const sectionNames: Record<string, string> = {
  activities:"正在做的事", experience:"经历", interests:"兴趣", concerns:"当前关注",
  needs:"此刻的需要", affect:"交流状态", relationship:"关系与牵挂", goals:"目标与计划",
  decisions:"自己的判断", learning:"学习与成长", skills:"学会的本领", world:"世界观察",
  source_lifecycle:"来源变化", provenance:"来源", runtime:"运行近况", health:"运行状况",
  provider:"认知资源", authority:"执行权限", queue:"待办机会", unknown:"待核验事项",
};
const categoryNames: Record<string, string> = {
  OPEN_CONCERN:"心里惦记着的事", WORLD_CONCERN:"心里惦记着的事", CONCERN:"当前关注",
  EXPERIENCE_NEED:"从经历中发现的需要", SOCIAL_APPETITE:"这会儿想怎样相处",
  VERIFIED_OUTCOME:"已经核验的经历", METHOD_LESSON:"从经历中学会的方法",
  WORLD_BELIEF:"对事情的理解", GOAL:"想推进的事", JUDGMENT:"这一次的判断",
  CODE_SKILL:"已有的能力", MEMORY:"记忆来源", COGNITION_ATTEMPT:"一次思考",
};
export const statusLabel = (x: unknown) => statusNames[label(x)] || label(x);
export function V3Card({
  title,
  eyebrow,
  children,
  className = "",
  action,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <section className={`v3-card ${className}`}>
      <div className="v3-card-title">
        <div>
          {eyebrow && <span className="v3-eyebrow">{eyebrow}</span>}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Blank({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="v3-blank">
      <span className="v3-blank-icon">
        <Sparkles size={22} />
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function RecordCards({
  items,
  empty = "这里还没有可展示的片刻",
}: {
  items: Record<string, unknown>[];
  empty?: string;
}) {
  const [limit, setLimit] = useState(12);
  if (!items.length)
    return (
      <Blank title={empty}>
        等待 Core 的有来源记录。留白也很好，不用故事填满它。
      </Blank>
    );
  return (
    <>
      <div className="v3-records">
        {items.slice(0, limit).map((r, i) => (
          <article className="v3-record" key={label(r.reference) + i}>
            <span className="v3-record-icon">
              <Leaf size={18} />
            </span>
            <div>
              <div className="v3-record-head">
                <span>{sectionNames[label(r.section)] || "近况记录"}</span>
                <span className="v3-chip">{statusLabel(r.state)}</span>
              </div>
              <h3>{categoryNames[label(r.category)] || "近况记录"}</h3>
              <details>
                <summary>
                  查看来源 <ChevronRight size={13} />
                </summary>
                <small>原始分类：{label(r.section)} / {label(r.category)}</small>
                <small>原始状态：{label(r.state)}</small>
                {typeof r.as_of_us === "number" && r.as_of_us > 0 && <small>记录时间：{new Date(r.as_of_us / 1000).toLocaleString()}</small>}
                <code>{label(r.reference)}</code>
                {Array.isArray(r.source_memory_ids) &&
                  r.source_memory_ids.map((s, n) => (
                    <small key={n}>{label(s)}</small>
                  ))}
              </details>
            </div>
          </article>
        ))}
      </div>
      {items.length > limit && (
        <button
          className="v3-button ghost"
          onClick={() => setLimit((n) => n + 12)}
        >
          再看一些（{items.length - limit}）
        </button>
      )}
    </>
  );
}
export function HomeView({
  items,
  ready,
  connected,
  room,
  go,
  avatar = true,
  shares = [],
}: {
  items: Record<string, unknown>[];
  ready: boolean;
  connected: boolean;
  room?: boolean;
  go: (p: Destination) => void;
  avatar?: boolean;
  shares?: SharedCandidate[];
}) {
  const activities = items.filter((x) =>
    /activit|experience|interest|concern/i.test(label(x.section)),
  );
  const appetite = ready ? items.find(x => x.section === "affect" && x.category === "SOCIAL_APPETITE") : undefined;
  const rhythm: Record<string, {text: string; expression: string}> = {
    OPEN: {text: "愿意聊聊天", expression: "neutral"},
    SEEKING: {text: "想找人聊聊", expression: "smile"},
    QUIET: {text: "这会儿想安静一会儿", expression: "neutral"},
    SATURATED: {text: "这会儿更想静一静", expression: "neutral"},
    RECOVERING: {text: "先缓一缓，等会儿再聊", expression: "sleepy"},
  };
  const tone = appetite ? rhythm[label(appetite.state)] : undefined;
  return (
    <div className={`v3-home ${room ? "v3-room-page" : ""}`}>
      <section className="v3-hero">
        <div className="v3-hero-copy">
          <span className="v3-eyebrow">
            {room
              ? "A LITTLE ROOM, A CONTINUOUS LIFE"
              : "YOUR LITTLE CORNER OF THE UNIVERSE"}
          </span>
          <h1>
            {room ? (
              <>
                小房间<span>安静相伴，也各自生长。</span>
              </>
            ) : (
              <>
                把日常，
                <br />
                慢慢过成<span className="v3-gradient-text">我们的故事。</span>
              </>
            )}
          </h1>
          <p>
            {connected
              ? ready
                ? "这个窗口连接着同一段持续的生活。近况与关心，都有来处。"
                : "已经连接，正在等待最新近况。"
              : "连接之后，真实的生活、记忆和共同经历会在这里慢慢出现。"}
          </p>
          <div className="v3-inline">
            <button className="v3-button primary" onClick={() => go("chat")}>
              <MessageCircle size={17} />
              开始聊天 <ArrowUpRight size={16} />
            </button>
            <button
              className="v3-button ghost"
              onClick={() => go(room ? "journal" : "room")}
            >
              {room ? "看生活动态" : "走进小房间"} <ChevronRight size={15} />
            </button>
          </div>
          <span className="v3-hero-note">
            <span className={`v3-dot ${ready ? "online" : ""}`} />
            {connected
              ? ready
                ? "入口在线 · 生活仍由她自己决定"
                : "已绑定 · 状态待确认"
              : "离线浏览 · 没有虚构的生活数据"}
          </span>
        </div>
        <div
          className="v3-room-scene"
          role="img"
          aria-label="小房间，静态角色展示，不代表实时心情"
        >
          <div className="v3-room-window" />
          <span className="v3-room-star one">✧</span>
          <span className="v3-room-star two">✦</span>
          <span className="v3-room-caption">
            A ROOM FOR NANA <span>✧</span>
          </span>
          {avatar ? <Avatar size={180} expression={tone?.expression || "neutral"} className="v4-room-avatar" /> : <Moon className="v3-room-moon" size={140} />}
          <span className="v3-room-plaque">
            <Moon size={15} />
            {tone ? tone.text : "安静留白，等待真实的近况"}
          </span>
        </div>
      </section>
      {shares.length > 0 && <V3Card title="她留待分享的片刻" eyebrow="FROM HER OWN JUDGMENT">
        <p className="v3-muted">这些候选来自当前主体已有的判断与来源。目前尚未送达，会等合适的时机与权限。</p>
        <div className="v3-records">{shares.map(item => <article className="v3-record" key={item.id}>
          <span className="v3-record-icon"><MessageCircle size={18}/></span>
          <div><div className="v3-record-head"><strong>有来源的分享候选</strong><span className="v3-chip">尚未送达</span></div>
            <p className="v3-muted">{item.state === "DEFER_BUSY" ? "知道你正忙，先留在这里。" : item.state === "SAVE_FOR_LATER_UNKNOWN_AVAILABILITY" ? "还不确定你是否方便，先留待以后。" : "留待适合的窗口。"}</p>
            <details><summary>查看来源与范围 <ChevronRight size={13}/></summary>
              {item.topic && <small>话题：{item.topic}</small>}
              <code>{item.id}</code><small>原判断：{item.cycleId}</small>
              {item.records.map(id => <small key={id}>支持记录：{id}</small>)}
              {item.memories.map(id => <small key={id}>来源：{id}</small>)}
              <small>当前状态：{item.state} · 尚无外部投递</small>
            </details>
          </div>
        </article>)}</div>
      </V3Card>}
      <section className="v3-card v4-living-tone" aria-label="有来源的生活节奏">
        <div>
          <span className="v3-eyebrow">HER OWN PACE</span>
          <h2>{tone ? tone.text : "此刻，不替她定义心情。"}</h2>
          <p>{tone ? "从她已有的经历与判断里，看看最近的交流节奏。" : "没有明确近况时，就留一点安静。"}</p>
        </div>
        {appetite && <details><summary>看看这份近况的来源</summary>
          <small>{appetite.as_of_us ? new Date(Number(appetite.as_of_us) / 1000).toLocaleString() : "时间尚未提供"}</small>
          <code>{label(appetite.record_id, "暂未提供支持记录")}</code>
        </details>}
      </section>
      <div className="v3-home-links">
        {(
          [
            [Heart, "共同记忆", "有来处的每一个片刻", "memories"],
            [Sparkles, "她的世界", "兴趣、发现与自己的生活", "world"],
            [BookOpen, "成长足迹", "真正学会，才留下脚印", "growth"],
          ] as const
        ).map(([Icon, title, subtitle, p]) => (
          <button key={p} className="v3-quick-card" onClick={() => go(p)}>
            <span className="v3-quick-icon">
              <Icon size={21} />
            </span>
            <span>
              <strong>{title}</strong>
              <small>{subtitle}</small>
            </span>
            <ArrowUpRight size={17} />
          </button>
        ))}
      </div>
      <div className="v3-two-column">
        <V3Card
          title="最近的生活"
          eyebrow="LITTLE MOMENTS"
          action={
            <button className="v3-text-button" onClick={() => go("journal")}>
              全部动态 <ArrowUpRight size={14} />
            </button>
          }
        >
          <RecordCards items={activities.slice(0, 4)} />
        </V3Card>
        <V3Card title="在一起，也留一点空间" eyebrow="SHARED & INDEPENDENT">
          <div className="v3-gentle-note">
            <Moon size={27} />
            <h3>不必每一刻都做些什么。</h3>
            <p>
              可以探索，也可以休息。你忙的时候，这里会留着一个不催促的入口。
            </p>
            <button className="v3-button soft" onClick={() => go("settings")}>
              安静与交流设置 <ChevronRight size={15} />
            </button>
          </div>
        </V3Card>
      </div>
      {room && (
        <V3Card title="房间里的未来" eyebrow="ROOM EXTENSIONS">
          <div className="v3-inline">
            {["Live2D 表情", "换装", "桌面小组件", "实时语音", "小游戏"].map(
              (s) => (
                <span className="v3-chip" key={s}>
                  {s} · 预留
                </span>
              ),
            )}
          </div>
          <p className="v3-muted">
            沿用 AvatarDriver
            表达接口；它们不会拥有独立记忆、情绪权威或第二个主体。
          </p>
        </V3Card>
      )}
    </div>
  );
}
export function BackupView({
  host,
  status,
  canBackup,
  busy,
  backup,
}: {
  host: Record<string, unknown>;
  status?: Record<string, unknown> | null;
  canBackup: boolean;
  busy: boolean;
  backup: () => void;
}) {
  return (
    <div className="v3-stack">
      <V3Card title="让连续性，有一份可靠的托付" eyebrow="BACKUP & CONTINUITY">
        <div className="v3-backup-path">
          <div>
            <Cloud />
            <strong>云端安全点</strong>
            <small>原 Core 一致性备份</small>
          </div>
          <span>···</span>
          <div>
            <LockKeyhole />
            <strong>加密交接</strong>
            <small>宿主 B1 工具</small>
          </div>
          <span>···</span>
          <div>
            <Laptop />
            <strong>你的电脑</strong>
            <small>私有 Tailscale</small>
          </div>
        </div>
        <div className="v3-notice">
          <ShieldCheck size={18} />
          <div>
            <strong>异机备份状态尚未接入</strong>
            <p>
              当前 API 没有 PC 接收与恢复回执。显示为
              LOCAL_ONLY_NOT_DR；不能据本机备份成功宣称异机灾难恢复通过。
            </p>
          </div>
        </div>
        <button
          className="v3-button primary"
          disabled={!canBackup || busy}
          onClick={backup}
        >
          <HardDrive size={17} />
          请求 Core 一致性备份
        </button>
        {status && (
          <div className="v3-inline-note">
            服务端回执投影：{label(status.scope)} · PC{" "}
            {label(status.pc_delivery)} · 恢复 {label(status.restore_check)}
            <ul>
              {Array.isArray(status.local_receipts) &&
                status.local_receipts.map((row, i) => {
                  const r = (
                    row && typeof row === "object" ? row : {}
                  ) as Record<string, unknown>;
                  return (
                    <li key={i}>
                      {label(r.receipt_id)} · {label(r.state)}
                    </li>
                  );
                })}
            </ul>
          </div>
        )}
        <p className="v3-muted">
          需要 Host Admin
          单次确认。手机不会打包数据库，也不会创建或恢复另一个主体。
        </p>
      </V3Card>
      <div className="v3-two-column">
        <V3Card title="备份计划">
          <dl className="v3-facts">
            <div>
              <dt>方案</dt>
              <dd>B1 · 加密备份到电脑</dd>
            </div>
            <div>
              <dt>最近真实异机结果</dt>
              <dd>未提供</dd>
            </div>
            <div>
              <dt>周期 / 保留策略</dt>
              <dd>等待宿主状态接口</dd>
            </div>
            <div>
              <dt>恢复检查</dt>
              <dd>NOT_RUN / 无当前回执</dd>
            </div>
            <div>
              <dt>当前 owner epoch</dt>
              <dd>{label(host.owner_epoch)}</dd>
            </div>
          </dl>
        </V3Card>
        <V3Card title="恢复是一项独立授权">
          <Blank title="不在手机上一键覆盖身份">
            恢复需要 lineage、隐私撤回和旧 owner fencing
            核验。当前界面仅查看与请求安全备份，不提供危险的直接数据库操作。
          </Blank>
        </V3Card>
      </div>
    </div>
  );
}
export function ConnectionView({
  host,
  connected,
  roles,
}: {
  host: Record<string, unknown>;
  connected: boolean;
  roles: string[];
}) {
  return (
    <div className="v3-diagnostics">
      {[
        [Link2, "网关连接", connected ? "已建立认证连接" : "未连接"],
        [
          Cloud,
          "Core Runtime",
          host.process_ready ? "当前已就绪" : "未就绪 / 未提供",
        ],
        [Fingerprint, "会话权限", roles.length ? roles.join(" · ") : "未授权"],
        [CircleHelp, "往返延迟", "按刷新请求实际测量，非 Provider 延迟"],
      ].map(([Icon, title, value]) => {
        const Glyph = Icon as typeof Link2;
        return (
          <div key={String(title)}>
            <Glyph size={19} />
            <span>
              <strong>{String(title)}</strong>
              <small>{String(value)}</small>
            </span>
          </div>
        );
      })}
    </div>
  );
}
