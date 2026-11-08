import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import {
  ArrowUp,
  ImagePlus,
  Paperclip,
  Mic,
  Sparkles,
  ChevronDown,
  Check,
  Copy,
  X,
  Volume2,
} from "lucide-react";
import { Avatar } from "../../avatar/Avatar";
import { Blank } from "./LifeViews";
import { readinessLabel } from "../../data/readiness";
import { transcribe, readAloud, stopSpeech } from "../../data/speech";
export type FeedbackTag = "TOO_VERBOSE" | "NATURAL" | "TOO_TERSE";
export interface Turn {
  id: string;
  input: string;
  state: string;
  reply?: string;
  provider?: string;
  error?: string;
  remembered?: boolean;
  model?: string;
  restored?: boolean;
  exchangeId?: string;
  pendingReceipt?: boolean;
  requestedAt?: number;
  provisional?: string;
  phase?: string;
}
/** Body text stays in React memory. Attachments are previews, never uploaded as text. */
export function ChatPane({
  turns,
  draft,
  onDraft,
  send,
  verify,
  busy,
  allowed,
  notice,
  readiness,
  configure,
  canRemember = false,
  canUsePersonal = false,
  personal = false,
  onPersonal,
  remember = false,
  onRemember,
  streaming = false,
  onStreaming,
  rememberConnection = false,
  onRememberConnection,
  onFeedback,
  onVerifyFeedback,
}: {
  onFeedback?: (turn: Turn, tag: FeedbackTag) => Promise<{id:string;state:string}>;
  onVerifyFeedback?: (id:string) => Promise<{id:string;state:string}>;
  turns: Turn[];
  draft: string;
  onDraft: (s: string) => void;
  send: (remember?: boolean, privacy?: "PROJECT" | "PERSONAL") => void;
  verify: (id: string) => void;
  busy: boolean;
  allowed: boolean;
  notice: (s: string) => void;
  readiness?: string;
  configure?: () => void;
  canRemember?: boolean;
  canUsePersonal?: boolean;
  personal?: boolean;
  onPersonal?: (personal: boolean) => void;
  remember?: boolean;
  onRemember?: (remember: boolean) => void;
  streaming?: boolean;
  onStreaming?: (value: boolean) => void;
  rememberConnection?: boolean;
  onRememberConnection?: (remember: boolean) => void;
}) {
  const [feedbackTurn, setFeedbackTurn] = useState<string>();
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [feedbackReceipts, setFeedbackReceipts] = useState<Record<string,{id:string;state:string}>>({});
  const review = async (turn:Turn, tag?:FeedbackTag) => {
    if (feedbackBusy) return;
    const receipt=feedbackReceipts[turn.id];
    if (tag && receipt && receipt.state!=="REJECTED") return;
    setFeedbackBusy(true);
    try {
      const result=tag && onFeedback ? await onFeedback(turn,tag)
        : receipt && onVerifyFeedback ? await onVerifyFeedback(receipt.id) : undefined;
      if(result)setFeedbackReceipts(old=>({...old,[turn.id]:result}));
    } catch { notice("这条评价尚未提交，请稍后检查连接。"); }
    finally { setFeedbackBusy(false); }
  };
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const visibleTurns = turns.filter(t => (t.input + " " + (t.reply || "")).toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const end = useRef<HTMLDivElement>(null),
    log = useRef<HTMLDivElement>(null);
  const atEnd = useRef(true),
    composing = useRef(false);
  const [attachment, setAttachment] = useState<{
    name: string;
    url?: string;
    size: number;
  }>();
  const file = useRef<HTMLInputElement>(null),
    image = useRef<HTMLInputElement>(null);
  const scopeAllowed = !personal || canUsePersonal;
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [waitingSeconds, setWaitingSeconds] = useState(0);
  const pending = [...turns].reverse().find(t => t.state === "REQUESTED");
  useEffect(() => {
    setWaitingSeconds(0);
    if (!pending) return;
    const started = pending.requestedAt ?? performance.now();
    const update = () => setWaitingSeconds(Math.max(0, Math.floor((performance.now() - started) / 1000)));
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [pending?.id, pending?.requestedAt]);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; stopSpeech(); };
  }, []);
  const voice = async (text?: string) => {
    if (voiceBusy) { stopSpeech(); return; }
    setVoiceBusy(true);
    try {
      if (text) await readAloud(text);
      else {
        const transcript = await transcribe();
        if (mounted.current) onDraft((draft + (draft ? " " : "") + transcript).slice(0, 2048));
      }
    } catch {
      if (mounted.current) notice("本地语音未完成或不可用；没有改用联网服务、没有自动发送。可使用手机键盘语音输入。");
    } finally { if (mounted.current) setVoiceBusy(false); }
  };
  useEffect(() => {
    if (atEnd.current)
      end.current?.scrollIntoView({ block: "end", behavior: "instant" });
  }, [turns]);
  useEffect(
    () => () => {
      if (attachment?.url) URL.revokeObjectURL(attachment.url);
    },
    [attachment],
  );
  const preview = async (f?: File) => {
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) {
      notice("附件预览上限为 5 MB。");
      return;
    }
    const photo = ["image/png", "image/jpeg", "image/webp"].includes(f.type);
    if (!photo && !/\.(txt|md|pdf)$/i.test(f.name)) {
      notice(
        "仅预览 PNG / JPEG / WebP / TXT / Markdown / PDF，不执行文件内容。",
      );
      return;
    }
    setAttachment({
      name: f.name.slice(0, 120),
      size: f.size,
      ...(photo ? { url: URL.createObjectURL(f) } : {}),
    });
    notice("仅本次页面预览；当前协议不支持附件上传，不会发送给模型。");
  };
  return (
    <section className="v3-chat live-chat">
      <div className="v3-chat-toolbar">
        <div>
          <Avatar size={36} />
          <span>
            <h1>奈奈</h1>
            <small>在这里，接着聊</small>
          </span>
        </div>
        <button
          className="v3-button ghost"
          onClick={() =>
            notice(
              "由服务器选择当前可用的对话模型。你可以在模型页查看和修改。",
            )
          }
        >
          当前模型 <ChevronDown size={14} />
        </button>
      </div>
      <div className="next-chat-tools">{onStreaming && <button type="button" className="next-search-toggle" aria-pressed={streaming} disabled={busy} onClick={() => onStreaming(!streaming)}>逐字回复{streaming ? " · 开" : " · 关"}</button>}
      <button className="next-search-toggle" onClick={() => {setSearchOpen(!searchOpen);setQuery("");}}>{searchOpen ? "收起搜索" : "搜索对话"}</button></div>
      {searchOpen && <label className="next-chat-search"><input aria-label="搜索当前对话" placeholder="在这段对话里找找…" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button type="button" onClick={() => setQuery("")}>清除</button>}</label>}
      {readiness && readiness !== "READY_LOCAL_GATES" && (
        <div className="v4-readiness" role="status">
          <span>{readinessLabel(readiness)}</span>
          {configure && <button type="button" onClick={configure}>查看模型设置</button>}
        </div>
      )}
      <div
        className="v3-chat-scroll live-chat-log"
        ref={log}
        role="log"
        aria-label="当前会话"
        aria-live="polite"
        onScroll={() => {
          const el = log.current;
          if (el)
            atEnd.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 90;
        }}
      >
        {!turns.length && (
          <div className="v3-chat-empty">
            <Avatar size={100} />
            <span className="v3-eyebrow">JUST A LITTLE MOMENT TOGETHER</span>
            <h2>想说什么，都可以慢慢说。</h2>
            <p>未选择保留的文字只留在当前窗口。明确保留的共同经历来自同一个奈奈；没有连接时不生成演示回复。</p>
            <div className="v3-suggestions">
              {["今天在关注什么？", "我们目前做到哪了？", "先陪我待一会儿"].map(
                (s) => (
                  <button key={s} onClick={() => onDraft(s)}>
                    {s}
                  </button>
                ),
              )}
            </div>
          </div>
        )}
        {visibleTurns.map((t) => (
          <article className="live-turn v3-turn" key={t.id}>
            {t.input && (
              <div className="v3-user-row">
                <p className="live-user">{t.input}</p>
                <span className="v3-user-initial">你</span>
              </div>
            )}
            <div className="v3-reply-row">
              <Avatar size={34} />
              <div className="live-reply">
                {t.reply ? (
                  <Markdown
                    components={{
                      img: () => <em>图片内容未自动加载</em>,
                      a: ({ href, children }) => (
                        <a
                          href={
                            href && /^https?:\/\//i.test(href)
                              ? href
                              : undefined
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {t.reply}
                  </Markdown>
                ) : (
                  <span>
                    {t.state === "REJECTED" ? (
                      readinessLabel(t.error)
                    ) : t.state === "UNKNOWN" ? (
                      "这条消息的结果还不能确认。先核验原回执，不重复发送。"
                    ) : t.state === "REQUESTED" ? (
                      <span className="v3-thinking">
                        {t.provisional && <span className="next-provisional" aria-label="生成中的临时回复" aria-live="off">{t.provisional}</span>}
                        <span role="status" aria-live="polite">{t.provisional ? "回复正在生成" : t.phase === "RENDERING" ? "奈奈正在组织回应" : "正在等奈奈回复"}<span aria-hidden="true"> · {waitingSeconds} 秒</span></span>
                        {t.provisional && <small>生成中，以完成后的回复为准。</small>}
                        {waitingSeconds >= 12 && <small>这次稍久一些，你可以先读读前面的对话。</small>}
                      </span>
                    ) : (
                      "这条回执尚无可展示的回复。"
                    )}
                  </span>
                )}
                <div className="v3-reply-meta">
                  <span>
                    <Check size={12} /> {({VERIFIED: "已收到", REQUESTED: "等待回复", REJECTED: "这次未提交", UNKNOWN: "等待核验"} as Record<string, string>)[t.state] || t.state}
                    {t.model ? ` · ${t.model}` : ""}
                  </span>
                  {onFeedback && t.state==="VERIFIED" && t.exchangeId && t.reply && t.reply.length<=2048 &&
                    <button aria-label="评价这条回复" onClick={()=>setFeedbackTurn(feedbackTurn===t.id?undefined:t.id)}>交流反馈</button>}
                  {t.reply && <button aria-label="引用这条回复" onClick={() => { onDraft(`引用：${t.reply!.slice(0, 500)}\n\n${draft}`); }}>引用</button>}
                  {t.reply && (
                    <button aria-label="朗读这条回复" onClick={() => void voice(t.reply)}><Volume2 size={14} /></button>
                  )}
                  {t.reply && (
                    <button
                      aria-label="复制这条回复"
                      onClick={() =>
                        void navigator.clipboard?.writeText(t.reply!).then(
                          () =>
                            notice("已复制到系统剪贴板；请注意共享设备隐私。"),
                          () => notice("当前环境不支持复制，请手动选择文本。"),
                        )
                      }
                    >
                      <Copy size={13} />
                    </button>
                  )}
                </div>
                {feedbackTurn===t.id && <div className="v3-feedback" aria-label="交流反馈">
                  <p>保存你的感受，帮助今后的交流；不会改写奈奈的身份或记忆事实。</p>
                  {(!feedbackReceipts[t.id] || feedbackReceipts[t.id].state==="REJECTED") && <div>
                    {([['TOO_VERBOSE','有点啰嗦'],['NATURAL','这样刚好'],['TOO_TERSE','想听多一点']] as const).map(([tag,label])=>
                      <button key={tag} disabled={busy||feedbackBusy} onClick={()=>void review(t,tag)}>保存：{label}</button>)}
                  </div>}
                  {feedbackReceipts[t.id] && <p role="status">{feedbackReceipts[t.id].state==="VERIFIED"?"评价已保存":feedbackReceipts[t.id].state==="REJECTED"?"这次未保存，可检查后重新提交":"保存结果待核验，不会重复提交"}</p>}
                  {feedbackReceipts[t.id]?.state==="UNKNOWN" && onVerifyFeedback &&
                    <button disabled={feedbackBusy} onClick={()=>void review(t)}>核验这条评价</button>}
                </div>}
                <small className="v3-muted">
                  {t.pendingReceipt ? t.state === "UNKNOWN" ? "只恢复原请求编号，原文没有缓存；请核验回执" : "已核验原请求；此窗口没有重发原文" : t.restored ? "从奈奈保留的共同经历恢复 · 来源仍有效" : t.remembered ? "已按本次选择保存，来源可查" : "本次文字未加入长期共同经历"}
                </small>
                {t.state === "UNKNOWN" && (
                  <button
                    className="v3-button soft"
                    onClick={() => verify(t.id)}
                  >
                    核验这条回执
                  </button>
                )}
              </div>
            </div>
          </article>
        ))}
        <div ref={end} />
      </div>
      <div className="v3-composer-wrap">
        {attachment && (
          <div className="v3-attachment">
            {attachment.url ? (
              <img src={attachment.url} alt="本地附件预览" />
            ) : (
              <Paperclip size={18} />
            )}
            <span>
              {attachment.name}
              <small>仅本地预览 · 不上传</small>
            </span>
            <button
              aria-label="移除附件预览"
              onClick={() => setAttachment(undefined)}
            >
              <X size={18} />
            </button>
          </div>
        )}
        <form
          className="live-composer v3-composer"
          onSubmit={(e) => {
            e.preventDefault();
            if (!scopeAllowed) return;
            send(remember, personal ? "PERSONAL" : "PROJECT");

          }}
        >
          <textarea
            aria-label="和奈奈说点什么"
            placeholder={
              allowed ? "把这一刻，说给奈奈听…" : "连接已有主体后，开始聊天"
            }
            value={draft}
            maxLength={2048}
            disabled={!allowed}
            onChange={(e) => onDraft(e.target.value)}
            onCompositionStart={() => {
              composing.current = true;
            }}
            onCompositionEnd={() => {
              composing.current = false;
            }}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                (e.ctrlKey || e.metaKey) &&
                !composing.current
              ) {
                e.preventDefault();
                if (!scopeAllowed) return;
                send(remember, personal ? "PERSONAL" : "PROJECT");

              }
            }}
          />
          <div className="v3-composer-tools">
            <div>
              <button
                type="button"
                aria-label="预览图片"
                onClick={() => image.current?.click()}
              >
                <ImagePlus size={19} />
              </button>
              <button
                type="button"
                aria-label="预览附件"
                onClick={() => file.current?.click()}
              >
                <Paperclip size={19} />
              </button>
              <button
                type="button"
                aria-label={voiceBusy ? "停止语音" : "本地语音输入"}
                aria-pressed={voiceBusy}
                disabled={!allowed}
                onClick={() => void voice()}
              >
                <Mic size={19} />
              </button>
            </div>
            <span className="v3-char-count">{draft.length}/2048</span>
            <button
              className="v3-send"
              aria-label="发送"
              disabled={busy || !allowed || !scopeAllowed || !draft.trim()}
            >
              <ArrowUp size={21} />
            </button>
          </div>
        </form>
        <details className="next-send-options">
          <summary>发送选项{personal ? " · 个人内容" : ""}{remember ? " · 会记住" : ""}</summary>
          <div className="next-options-panel">
        {(canUsePersonal || personal) && <label className="v4-remember">
          <input type="checkbox" checked={personal} disabled={busy} onChange={e => onPersonal?.(e.target.checked)} />
          本次包含个人内容
          <small>{scopeAllowed ? "仅获准设备可用；模型与保存仍受各自授权限制" : "个人范围授权已变化，请重新核对；不会自动改成项目内容发送"}</small>
        </label>}
        {canRemember && <label className="v4-remember">
          <input type="checkbox" checked={remember} disabled={busy} onChange={e => onRemember?.(e.target.checked)} />
          记住这次共同经历
          <small>{rememberConnection && !personal ? "本次连接已开启连续保存；可随时取消" : "仅本次提交 · 带来源保存，可在记忆中撤回"}</small>
        </label>}
        {canRemember && <label className="v4-remember">
          <input type="checkbox" checked={rememberConnection && !personal} disabled={busy || personal} onChange={e => onRememberConnection?.(e.target.checked)} />
          记住后续对话（本次连接）
          <small>由你主动开启；退出或权限变化后关闭。个人内容仍需逐条选择。</small>
        </label>}
          <p>个人内容仅用于下一条消息。已保存的内容可在记忆页撤回。</p>
          </div>
        </details>
      </div>
      <input
        hidden
        ref={image}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={(e) => {
          void preview(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <input
        hidden
        ref={file}
        type="file"
        accept=".txt,.md,.pdf,image/png,image/jpeg,image/webp"
        onChange={(e) => {
          void preview(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {!allowed && (
        <span className="v3-sr-only">
          <Blank title="尚未获得会话权限">
            请先连接，或检查这台设备的聊天权限。
          </Blank>
        </span>
      )}
    </section>
  );
}
