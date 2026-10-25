import {useEffect, useState} from 'react';
import {BookOpen, Bookmark, Brain, CheckCircle2, ChevronDown, CircleHelp, Clock3, Compass, Eye, FileCheck2, FlaskConical, Gamepad2, GitBranch, Heart, Headphones, Leaf, Lightbulb, Link2, LockKeyhole, Monitor, Pause, Play, Radio, ShieldCheck, Smartphone, Sparkles, Telescope, Unplug, Waves} from 'lucide-react';
import type {Activity, Device, Goal, Memory, Skill, SpaceSnapshot} from '../data/contracts';
import {Badge, Empty, PageHeading, Panel, Progress, SearchField, SectionHeading, TextLink} from '../components/ui';
import './explore.css';

export interface ExploreProps {data:SpaceSnapshot; notify:(message:string)=>void; onChat:(topic:string)=>void}
type FiltersProps = {items:string[]; selected:string; onSelect:(value:string)=>void; label:string};
function Filters({items,selected,onSelect,label}:FiltersProps){return <div className="exp-filters" role="group" aria-label={label}>{items.map(item=><button key={item} type="button" className={selected===item?'active':''} aria-pressed={selected===item} onClick={()=>onSelect(item)}>{item}</button>)}</div>}
function Provenance({source}:{source:Memory['source']}){return <div className="exp-source"><Link2 size={14}/><div><span>{source.label}</span><small>来源引用 <code>{source.ref}</code> · {source.privacy} · 置信度 {Math.round(source.confidence*100)}%</small></div></div>}
function DemoNote({children}:{children:string}){return <p className="exp-note"><Sparkles size={15}/>{children}</p>}
const memoryIcons = {'共同经历':Heart,'发现':Telescope,'约定':Bookmark,'成长':Leaf};

export function MemoriesPage({data,onChat}:ExploreProps){
  const [query,setQuery]=useState('');const [kind,setKind]=useState('全部');
  const memories=data.memories.filter(memory=>(kind==='全部'||memory.kind===kind)&&`${memory.title} ${memory.state==='WITHDRAWN'?'':memory.summary} ${memory.tags.join(' ')} ${memory.source.label}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  return <div className="exp-page"><PageHeading eyebrow="SHARED MEMORIES" title="那些被记住的时刻" description="有些经历成为故事，有些约定陪我们走得更远。"><Badge tone="pink">共同生活 · 演示</Badge></PageHeading>
    <div className="exp-toolbar"><SearchField value={query} onChange={setQuery} placeholder="搜索记忆、主题或来源…"/><Filters items={['全部','共同经历','发现','约定','成长']} selected={kind} onSelect={setKind} label="记忆类型"/></div>
    {memories.length?<div className="exp-grid">{memories.map(memory=>{const Icon=memoryIcons[memory.kind];return <Panel key={memory.id} className={`exp-card ${memory.state==='WITHDRAWN'?'exp-withdrawn':''}`}><div className="exp-card-head"><span className={`exp-card-icon ${memory.kind==='共同经历'?'pink':''}`}><Icon size={21}/></span><div className="exp-meta"><span>{memory.kind}</span><small>{memory.date}</small></div><Badge tone={memory.state==='WITHDRAWN'?'gray':memory.state==='CORRECTED'?'amber':'purple'}>{memory.state==='WITHDRAWN'?'已撤回':memory.state==='CORRECTED'?'已纠正':'有效记录'}</Badge></div><h3>{memory.title}</h3>
      {memory.state==='WITHDRAWN'?<p className="exp-privacy"><LockKeyhole size={16}/>来源已撤回，正文不再呈现。仅保留撤回状态供审查。</p>:<p>{memory.summary}</p>}
      {memory.correction&&memory.state!=='WITHDRAWN'&&<p className="exp-warning"><CircleHelp size={16}/>{memory.correction}</p>}
      <div className="exp-tags">{memory.tags.map(tag=><span key={tag}>#{tag}</span>)}</div><details className="exp-details"><summary>来源与可信度<ChevronDown size={16}/></summary><div className="exp-detail-body"><Provenance source={memory.source}/><p className="exp-small">这是演示记录。真实记忆只能由 Core 正式投影提供；更正和遗忘须经过原有权限与来源传播机制。</p><TextLink onClick={()=>onChat(`想回顾「${memory.title}」的来源和更正状态`)}>带着这个话题聊聊</TextLink></div></details></Panel>})}</div>:<Empty title="这里暂时没有匹配的记忆" description="换一个词或主题试试。投影缺失也可能使部分记录不可见。"/>}
    <DemoNote>这些故事仅用于界面演示，没有写入奈奈的记忆，也不会在正式接入时迁移。</DemoNote>
  </div>
}

const goalLabels:Record<Goal['state'],string>={ACTIVE:'正在继续',PAUSED:'暂时放下',BLOCKED:'等待条件',DECLINED:'选择不做',VERIFIED:'已核验完成',UNKNOWN:'结果待核验'};
const originLabels:Record<Goal['origin'],string>={NANA:'奈奈的想法',USER:'你的提议',SHARED:'共同计划'};
const goalTones:Record<Goal['state'],string>={ACTIVE:'purple',PAUSED:'gray',BLOCKED:'amber',DECLINED:'pink',VERIFIED:'green',UNKNOWN:'amber'};
export function GoalsPage({data,notify,onChat}:ExploreProps){
  const [filter,setFilter]=useState('全部');const [localStates,setLocalStates]=useState<Record<string,Goal['state']>>({});
  useEffect(()=>setLocalStates({}),[data]);
  const goals=data.goals.map(goal=>({...goal,state:localStates[goal.id]??goal.state}));
  const shown=goals.filter(goal=>filter==='全部'||filter==='进行中'&&goal.state==='ACTIVE'||filter==='等待与暂停'&&['PAUSED','BLOCKED','UNKNOWN'].includes(goal.state)||filter==='已有结论'&&['DECLINED','VERIFIED'].includes(goal.state));
  function change(goal:Goal,state:Goal['state']){setLocalStates(previous=>({...previous,[goal.id]:state}));notify(`演示目标「${goal.title}」${state==='PAUSED'?'已暂停':state==='ACTIVE'?'已恢复':'已放弃'}；未向 Core 发送命令。`)}
  return <div className="exp-page"><PageHeading eyebrow="GOALS & LITTLE DREAMS" title="想做的事，慢慢实现" description="有她自己的好奇，也有我们约好一起走的路。"><Badge tone="purple">意愿 ≠ 权限</Badge></PageHeading>
    <div className="exp-status-summary"><Panel className="exp-stat"><Sparkles size={19}/><strong>{goals.filter(goal=>goal.state==='ACTIVE').length}</strong><span>在继续的计划</span></Panel><Panel className="exp-stat"><Clock3 size={19}/><strong>{goals.filter(goal=>['PAUSED','BLOCKED','UNKNOWN'].includes(goal.state)).length}</strong><span>可以慢一点的事</span></Panel><Panel className="exp-stat"><CheckCircle2 size={19}/><strong>{goals.filter(goal=>goal.state==='VERIFIED').length}</strong><span>有结果证据的完成</span></Panel></div>
    <Filters items={['全部','进行中','等待与暂停','已有结论']} selected={filter} onSelect={setFilter} label="目标状态"/>
    {shown.length?<div className="exp-grid">{shown.map(goal=><Panel key={goal.id} className="exp-card"><div className="exp-card-head"><span className={`exp-card-icon ${goal.origin==='SHARED'?'pink':''}`}>{goal.origin==='SHARED'?<Heart size={20}/>:goal.origin==='NANA'?<Lightbulb size={20}/>:<Bookmark size={20}/>}</span><div className="exp-meta"><span>{originLabels[goal.origin]}</span><small>{goal.id}</small></div><Badge tone={goalTones[goal.state]}>{goalLabels[goal.state]}</Badge></div><h3>{goal.title}</h3><p>{goal.description}</p>
      <div className="exp-progress-head"><span>演示进度</span><b>{goal.progress}%</b></div><Progress value={goal.progress}/>
      <p className={['BLOCKED','UNKNOWN'].includes(goal.state)?'exp-warning':'exp-note'}>{goal.state==='BLOCKED'?<LockKeyhole size={16}/>:goal.state==='UNKNOWN'?<CircleHelp size={16}/>:<Compass size={16}/>}<span>{localStates[goal.id]?`本页演示已${goalLabels[goal.state]}，原 Core 意愿与权限未改变。`:goal.reason}</span></p>
      <details className="exp-details"><summary>计划、依赖与结果<ChevronDown size={16}/></summary><div className="exp-detail-body"><h4>接下来</h4><p>{goal.next}</p><ol className="exp-plan">{goal.steps.map((step,index)=><li key={`${index}-${step}`}><span>{String(index+1).padStart(2,'0')}</span>{step}</li>)}</ol><h4>所需条件</h4><div className="exp-tags">{goal.dependencies.length?goal.dependencies.map(dependency=><span key={dependency}><GitBranch size={12}/>{dependency}</span>):<span>当前无已知依赖</span>}</div><h4><FileCheck2 size={15}/>独立结果证据</h4><p className="exp-small">{goal.evidence}</p>{goal.state==='UNKNOWN'&&<p className="exp-warning">UNKNOWN 不等于失败。需要先核验实际结果，不能盲目重新执行。</p>}</div></details>
      <div className="exp-actions">{goal.state==='ACTIVE'&&<><button className="secondary" onClick={()=>change(goal,'PAUSED')}><Pause size={15}/>演示暂停</button><button className="exp-subtle-button" onClick={()=>change(goal,'DECLINED')}>演示放弃</button></>}{goal.state==='PAUSED'&&<button className="secondary" onClick={()=>change(goal,'ACTIVE')}><Play size={15}/>演示恢复</button>}{goal.state==='BLOCKED'&&<span className="exp-small"><LockKeyhole size={14}/>授权只能通过正式 Core 流程</span>}{goal.state==='DECLINED'&&<span className="exp-small">尊重这个判断；可以讨论新的提议。</span>}<TextLink onClick={()=>onChat(`继续聊聊「${goal.title}」，保留她的判断与实际权限边界`)}>聊聊这件事</TextLink></div>
    </Panel>)}</div>:<Empty title="这片空间还很安静" description="当前筛选中没有目标，不需要为了填满界面创造新任务。"/>}
    <DemoNote>暂停、恢复和放弃只改变本页演示。正式操作须由同一 Subject 接受、规划，并经过 Manager / Grant 与独立核验。</DemoNote>
  </div>
}

const activityIcons:Record<Activity['kind'],typeof Sparkles>={'发现':Telescope,'学习':BookOpen,'共同生活':Heart,'恢复':Waves,'休息':Leaf,'行动':Compass};
export function JournalPage({data,onChat}:ExploreProps){
  const [filter,setFilter]=useState('全部');const [day,setDay]=useState(24);const [view,setView]=useState('时间线');
  const activities=day===24?data.activities.filter(activity=>filter==='全部'||activity.kind===filter):[];
  return <div className="exp-page"><PageHeading eyebrow="NANA LIFE JOURNAL" title="日子，有自己的纹理" description="小小的发现、认真尝试的事，还有安静休息的空白。"><Filters items={['时间线','一周回看']} selected={view} onSelect={setView} label="日记视图"/></PageHeading>
    {view==='一周回看'&&<Panel className="exp-week-panel"><div className="exp-card-head"><span className="eyebrow">OCTOBER 2026</span><Badge tone="gray">固定演示周</Badge></div><div className="exp-week">{['一','二','三','四','五','六','日'].map((label,index)=><button className={day===index+19?'active':''} key={label} onClick={()=>setDay(index+19)} aria-pressed={day===index+19}><span>周{label}</span><b>{index+19}</b><i aria-label={index+19===24?'有演示活动':'没有演示样本'}>{index+19===24?'•':'·'}</i></button>)}</div></Panel>}
    <Filters items={['全部','发现','学习','共同生活','恢复','休息','行动']} selected={filter} onSelect={setFilter} label="活动类型"/>
    <SectionHeading title={view==='一周回看'?`10 月 ${day} 日`:'奈奈的最近一天'} description="精选的可分享活动摘要 · 演示时间线"/>
    {activities.length?<div className="exp-timeline">{activities.map(activity=>{const Icon=activityIcons[activity.kind];return <article key={activity.id} className="exp-timeline-entry"><time className="exp-time">{activity.time}</time><span className="exp-timeline-dot"><Icon size={16}/></span><Panel className="exp-timeline-card"><div className="exp-card-head"><Badge tone={activity.kind==='共同生活'?'pink':activity.kind==='恢复'?'cyan':'purple'}>{activity.kind}</Badge><span className="exp-small">{activity.state}</span></div><h3>{activity.title}</h3><p>{activity.summary}</p><details className="exp-details"><summary>看看这一刻的来源<ChevronDown size={16}/></summary><div className="exp-detail-body"><Provenance source={activity.source}/><TextLink onClick={()=>onChat(`聊聊日记里的「${activity.title}」`)}>继续这个话题</TextLink></div></details></Panel></article>})}</div>:<Empty title={day===24?'让日子安静一会儿':'这一天没有提供演示样本'} description="没有活动投影不代表停止生活。界面不会填造记录，也不要求固定的每日活动数量。"/>}
    <DemoNote>日记只呈现适合分享的经历摘要，不公开内部推理、私有内容或完整的底层事件流。</DemoNote>
  </div>
}

export function WorldPage({data,onChat}:ExploreProps){
  const [query,setQuery]=useState('');const [filter,setFilter]=useState('全部');
  const research=data.research.filter(item=>(filter==='全部'||filter==='继续探索'&&item.state==='EXPLORING'||filter==='证据有分歧'&&item.state==='CONFLICT'||filter==='已有支持'&&item.state==='SUPPORTED')&&`${item.title} ${item.summary} ${item.tags.join(' ')}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="exp-page"><PageHeading eyebrow="WORLD & WONDER" title="世界总有新鲜事" description="保持好奇，也给不确定的事情留一点空间。"><Badge tone="cyan">结论 · 证据 · 不确定性</Badge></PageHeading>
    <Panel className="exp-research-banner"><span className="exp-card-icon cyan"><Telescope size={27}/></span><div><span className="eyebrow">A WINDOW TO THE WORLD</span><h3>不是所有问题，都急着有一个答案。</h3><p>这里呈现可以公开的研究摘要和来源。意见不一致时，让证据保持可见。</p></div><Sparkles className="exp-banner-star" size={42}/></Panel>
    <div className="exp-toolbar"><SearchField value={query} onChange={setQuery} placeholder="寻找一个好奇的主题…"/><Filters items={['全部','继续探索','证据有分歧','已有支持']} selected={filter} onSelect={setFilter} label="研究状态"/></div>
    {research.length?<div className="exp-stacked">{research.map(item=><Panel className="exp-card" key={item.id}><div className="exp-card-head"><span className="exp-card-icon cyan"><FlaskConical size={20}/></span><div className="exp-meta"><span>探索札记</span><small>{item.id}</small></div><Badge tone={item.state==='CONFLICT'?'amber':item.state==='SUPPORTED'?'green':item.state==='UNKNOWN'?'gray':'cyan'}>{item.state==='CONFLICT'?'来源有分歧':item.state==='SUPPORTED'?'有证据支持':item.state==='UNKNOWN'?'尚不清楚':'正在探索'}</Badge></div><h3>{item.title}</h3><p>{item.summary}</p><div className="exp-tags">{item.tags.map(tag=><span key={tag}>#{tag}</span>)}</div><details className="exp-details"><summary>展开材料与当前结论<ChevronDown size={16}/></summary><div className="exp-detail-body"><div className="exp-evidence-grid">{item.sources.map((source,index)=><article key={`${source.title}-${index}`} className="exp-evidence"><div className="exp-card-head"><BookOpen size={17}/><Badge tone={item.state==='CONFLICT'?'amber':'gray'}>{source.stance}</Badge></div><h4>{source.title}</h4><p>{source.detail}</p></article>)}</div><h4>当前可以分享的结论</h4><p className={item.state==='CONFLICT'?'exp-warning':'exp-note'}>{item.conclusion}</p><TextLink onClick={()=>onChat(`一起看看「${item.title}」的证据和不确定性`)}>一起研究一下</TextLink></div></details></Panel>)}</div>:<Empty title="还没有找到这个主题" description="换一个关键词试试。未提供的资料不会被界面补成已知结论。"/>}
  </div>
}

const skillLabels:Record<Skill['state'],string>={QUALIFIED:'限定范围已验证',LEARNING:'正在学习',FAILED:'测试未通过',PAUSED:'已经暂停',RETIRED:'已经退休',PLANNED:'未来适配'};
const skillTones:Record<Skill['state'],string>={QUALIFIED:'green',LEARNING:'purple',FAILED:'amber',PAUSED:'gray',RETIRED:'gray',PLANNED:'cyan'};
export function GrowthPage({data,onChat}:ExploreProps){
  const [filter,setFilter]=useState('全部');
  const skills=data.skills.filter(skill=>filter==='全部'||filter==='已经会的'&&skill.state==='QUALIFIED'||filter==='正在尝试'&&['LEARNING','FAILED'].includes(skill.state)||filter==='暂停与未来'&&['PAUSED','RETIRED','PLANNED'].includes(skill.state));
  return <div className="exp-page"><PageHeading eyebrow="GROWTH JOURNEY" title="一点一点，成为自己" description="经历会留下改变。失败、复用和选择停下，也都是成长的一部分。"><Badge tone="pink">能力有范围，成长有证据</Badge></PageHeading>
    <Panel className="exp-research-banner"><span className="exp-card-icon pink"><Leaf size={28}/></span><div><span className="eyebrow">LEARN · TRY · USE AGAIN</span><h3>会一次，与以后也做得到，是两回事。</h3><p>从一次尝试到后来的实际复用，留下过程，也保留失效和退休的记录。</p></div><GitBranch className="exp-banner-star" size={42}/></Panel>
    <Filters items={['全部','已经会的','正在尝试','暂停与未来']} selected={filter} onSelect={setFilter} label="技能阶段"/>
    {skills.length?<div className="exp-grid">{skills.map((skill,index)=><Panel key={skill.id} className="exp-skill-card"><div className="exp-card-head"><span className={`exp-card-icon ${index%3===0?'pink':index%3===1?'cyan':''}`}>{skill.state==='QUALIFIED'?<ShieldCheck size={21}/>:skill.state==='FAILED'?<FlaskConical size={21}/>:skill.state==='RETIRED'?<Leaf size={21}/>:<Brain size={21}/>}</span><Badge tone={skillTones[skill.state]}>{skillLabels[skill.state]}</Badge></div><h3>{skill.title}</h3><p>{skill.description}</p><p className="exp-small"><LockKeyhole size={13}/>适用范围：{skill.scope}</p><details className="exp-details"><summary>资格、复用与失败记录<ChevronDown size={16}/></summary><div className="exp-detail-body"><div className="exp-skill-track"><div><span><FlaskConical size={15}/></span><h4>测试与资格</h4><p>{skill.tests}</p></div><div><span><GitBranch size={15}/></span><h4>后来的实际复用</h4><p>{skill.reuse}</p></div></div><p className="exp-small">资格只覆盖明确的版本、材料和范围。界面不会通过“启用技能”绕过执行授权。</p><TextLink onClick={()=>onChat(`看看「${skill.title}」最近的测试、复用与限制`)}>聊聊这段成长</TextLink></div></details></Panel>)}</div>:<Empty title="这个阶段暂时没有样本" description="学习不是必须持续上涨的进度条。这里会保留适合公开的真实过程。"/>}
    <DemoNote>这里的能力与成长记录均为演示。开发者改代码不代表奈奈自身学会了新能力。</DemoNote>
  </div>
}

const deviceIcons:Record<Device['kind'],typeof Smartphone>={phone:Smartphone,desktop:Monitor,browser:Compass,platform:Radio,audio:Headphones,avatar:Sparkles,game:Gamepad2};
const deviceLabels:Record<Device['state'],string>={DEMO:'演示连接',PLANNED:'尚未接入',BACKEND_AVAILABLE:'后端契约已有',CONNECTED:'演示 · 已连接',DISABLED:'未启用',BLOCKED:'等待授权',ERROR:'连接故障',UNKNOWN:'连接状态未知'};
export function DevicesPage({data,onChat}:ExploreProps){
  const [filter,setFilter]=useState('全部');
  const devices=data.devices.filter(device=>filter==='全部'||filter==='设备'&&['phone','desktop','browser'].includes(device.kind)||filter==='平台'&&device.kind==='platform'||filter==='感知与形象'&&['audio','avatar','game'].includes(device.kind));
  return <div className="exp-page"><PageHeading eyebrow="CONNECTED WORLD" title="同一个奈奈，更大的世界" description="每一个窗口，都通向同一个主体；连接带来可能，也保留清楚的边界。"><Badge tone="cyan">One subject · Many surfaces</Badge></PageHeading>
    <p className="exp-note"><Unplug size={17}/>当前为 Demo。没有连接真实手机、电脑或平台账户，也没有采集摄像头和麦克风。</p><Filters items={['全部','设备','平台','感知与形象']} selected={filter} onSelect={setFilter} label="连接类型"/>
    {devices.length?<div className="exp-device-grid">{devices.map(device=>{const Icon=deviceIcons[device.kind];return <Panel key={device.id} className="exp-device-card"><div className="exp-card-head"><span className={`exp-device-icon ${device.kind==='avatar'?'pink':device.kind==='audio'?'cyan':''}`}><Icon size={25}/></span><Badge tone={['ERROR','BLOCKED'].includes(device.state)?'amber':['DISABLED','UNKNOWN','PLANNED'].includes(device.state)?'gray':'cyan'}>{deviceLabels[device.state]}</Badge></div><h3>{device.title}</h3><p>{device.description}</p><span className="exp-small"><Clock3 size={13}/>{device.lastSeen}</span><details className="exp-details"><summary>能力与连接条件<ChevronDown size={16}/></summary><div className="exp-detail-body"><h4><Eye size={15}/>可以观察</h4><div className="exp-device-capabilities">{device.observe.length?device.observe.map(capability=><span key={capability}>{capability}</span>):<span>没有已接入的观察能力</span>}</div><h4><Compass size={15}/>可以执行</h4><div className="exp-device-capabilities">{device.act.length?device.act.map(capability=><span key={capability}>{capability}</span>):<span>没有已授权的执行能力</span>}</div><p className="exp-warning"><LockKeyhole size={15}/>{device.limitation}</p><p className="exp-small">以上是演示能力描述。真实连接、采集和动作需由主机适配器与 Core 权限共同确认。</p><TextLink onClick={()=>onChat(`了解「${device.title}」需要的适配器、权限与能力限制`)}>了解接入条件</TextLink></div></details></Panel>})}</div>:<Empty title="这个世界还可以慢慢扩展" description="当前分类没有设备投影。未连接不会显示为在线。"/>}
    <DemoNote>设备离线不等于奈奈休息；前端缓存不恢复设备授权。Live2D 与真实语音驱动仍需模型、运行器和正式接入。</DemoNote>
  </div>
}
