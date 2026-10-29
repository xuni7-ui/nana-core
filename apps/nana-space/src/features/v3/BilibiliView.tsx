import { useMemo, useState } from "react";
import { ArrowUpRight, BookOpen, Eye, MessageCircle, Search, ShieldCheck } from "lucide-react";
import { bilibiliReadings } from "../../data/living";
import { Blank, V3Card } from "./LifeViews";

/** A view of original Core sources, never a parallel viewing/interest ledger. */
export function BilibiliView({ data, available }: { data: unknown; available: boolean }) {
  const all = useMemo(() => bilibiliReadings(data), [data]);
  const [query, setQuery] = useState("");
  const items = all.filter(item => (item.title + item.bvid).toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  return <div className="v3-stack">
    <V3Card title="一起看见更大的世界" eyebrow="BILIBILI · SOURCED LIFE">
      <p className="v3-muted">这里展示奈奈真正取得的资料和理解范围。标题、字幕、评论与采样画面分别标记，不能互相冒充。</p>
      <label className="v3-search"><Search size={17}/><input aria-label="搜索B站经历" value={query} onChange={e => setQuery(e.target.value)} placeholder="视频标题或 BV 号" maxLength={128}/></label>
    </V3Card>
    {!available ? <Blank title="这扇窗还没有接通">当前服务尚未提供B站来源投影。不会用演示观看记录代替真实经历。</Blank>
      : !items.length ? <Blank title={query ? "没有匹配的来源" : "还没有可展示的B站经历"}>只有已进入同一个 Core、仍有有效来源支持的资料才会出现在这里。</Blank>
      : items.map(item => <article className="v3-card v4-bili-card" key={item.id}>
        <div className="v3-card-heading"><span className="v3-eyebrow">{item.origin}</span><span className="v3-chip">{item.coverage}</span></div>
        <h3>{item.title || item.bvid}</h3>
        <p className="v3-muted">{item.interpreted ? "已有来源支持的理解记录" : "已取得资料，尚无可确认的语义理解记录"}</p>
        <div className="v4-evidence-counts" aria-label="资料覆盖">
          <span><BookOpen size={15}/>{item.subtitles} 段字幕</span>
          <span><MessageCircle size={15}/>{item.comments} 条评论 · {item.danmaku} 条弹幕</span>
          <span><Eye size={15}/>{item.frames} 帧画面</span>
        </div>
        {item.missing.length > 0 && <p className="v3-muted">未取得：{item.missing.join("、")}</p>}
        <div className="v4-bili-footer"><time dateTime={new Date(item.observedAt / 1000).toISOString()}>{new Date(item.observedAt / 1000).toLocaleString()}</time>
          <a href={`https://www.bilibili.com/video/${item.bvid}`} target="_blank" rel="noopener noreferrer">在B站打开 <ArrowUpRight size={14}/></a>
        </div>
        <details className="v3-technical"><summary>来源与范围</summary><small>{item.id}</small><p>这条记录不证明完整观看，也不代表已经评论、私信或获得任何执行权限。</p></details>
      </article>)}
    <p className="v3-inline-note"><ShieldCheck size={17}/>公开资料、私聊与平台动作保留各自权限；这里不会自动发表评论或发送私信。</p>
  </div>;
}
