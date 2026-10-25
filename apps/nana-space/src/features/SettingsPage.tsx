import type {Dispatch, SetStateAction} from 'react';
import {BellOff, Check, ChevronDown, Eye, Globe2, Moon, Palette, ShieldCheck, SlidersHorizontal, Sparkles, Sun} from 'lucide-react';
import type {Preferences} from '../app/preferences';
import {AvatarStage} from '../avatar/Avatar';
import {Badge, PageHeading, Panel, SectionHeading} from '../components/ui';
import {scenarioLabels, type Scenario, type SpaceSnapshot} from '../data/contracts';
import './settings.css';

interface SettingsProps {
  preferences:Preferences;
  setPreferences:Dispatch<SetStateAction<Preferences>>;
  scenario:Scenario;
  setScenario:(scenario:Scenario)=>void;
  notify:(message:string)=>void;
  data:SpaceSnapshot;
}

function LocalSwitch({label,description,checked,onChange}:{label:string;description:string;checked:boolean;onChange:()=>void}) {
  return <div className="settings-row"><div><strong>{label}</strong><p>{description}</p></div><button className={`settings-switch ${checked?'is-on':''}`} role="switch" aria-checked={checked} aria-label={label} onClick={onChange}><span/></button></div>;
}

const coreConfiguration = [
  {title:'AI Providers / Models',status:'BACKEND_AVAILABLE',description:'Core 已有 Provider Settings V1 应用契约。浏览器尚未接入授权会话。',detail:'正式接入需 VIEW_PROVIDER_SETTINGS / CONFIGURE_PROVIDERS；仅展示 secret_state，凭据由宿主 SecretResolver 持有。此处不收集 API Key。'},
  {title:'Capability Routing',status:'BACKEND_AVAILABLE',description:'认知、视觉、语音等路由由 Core 的能力路由配置管理。',detail:'路由更新使用 expected_revision；冲突后重新读取。UNKNOWN 或已经 dispatch 的请求不得通过切换模型自动重试。路由上限不能扩大 Runtime 预算。'},
  {title:'隐私 / Manager / Authority',status:'PLANNED',description:'Surface 的本地偏好不会改变隐私、Grant 或主体意愿。',detail:'展示和执行权限必须由正式授权投影与命令边界提供。关系重要性不等于执行权限。忘记、撤回和导出操作须由 Core 完成并返回明确回执。'},
  {title:'设备 / Perception',status:'BACKEND_AVAILABLE',description:'Core 已有感知配置与状态投影；真实设备尚未接入。',detail:'VIEW_PERCEPTION / CONFIGURE_PERCEPTION / REQUEST_CAPTURE 分别授权。启用源不等于获得传感器权限；没有连接时不启动摄像头或麦克风。'},
  {title:'资源预算',status:'BACKEND_AVAILABLE',description:'Provider 与路由预算属于宿主权威配置。',detail:'本页不修改真实调用次数、费用、超时和运行预算。未来适配层需使用版本校验、正式权限以及 Core 返回的错误码。'},
  {title:'备份与恢复',status:'PLANNED',description:'前端偏好与主体备份具有独立的生命周期。',detail:'恢复主体需要 Core 的 lineage / fencing / rollback 流程；浏览器缓存或角色图片不是主体备份，也不会携带旧设备与 Provider 的执行权限。'},
];

export function SettingsPage({preferences,setPreferences,scenario,setScenario,notify,data}:SettingsProps) {
  const update=<K extends keyof Preferences>(key:K,value:Preferences[K])=>setPreferences(previous=>({...previous,[key]:value}));
  return <div className="settings-page">
    <PageHeading eyebrow="MAKE YOURSELF AT HOME" title="把空间，调成喜欢的样子" description="一点月光，一点偏爱。这里的设置，只改变你看到的 Nana Space。"/>
    <div className="settings-local-note"><ShieldCheck size={19}/><p><strong>本地界面偏好</strong><span> 保存在此浏览器，不会修改奈奈的记忆、人格、愿望或 Core 权限。</span></p><Badge tone="muted">LOCAL ONLY</Badge></div>
    <div className="settings-layout">
      <div className="settings-stack">
        <Panel className="settings-card">
          <SectionHeading eyebrow="ATMOSPHERE" title="空间氛围"><Palette size={20}/></SectionHeading>
          <div className="settings-themes" role="group" aria-label="空间主题">
            {([{value:'dark',label:'月光深蓝',sub:'Moonlight',Icon:Moon},{value:'light',label:'晨间薄雾',sub:'Daydream',Icon:Sun},{value:'system',label:'跟随系统',sub:'Your rhythm',Icon:SlidersHorizontal}] as const).map(({value,label,sub,Icon})=><button key={value} aria-pressed={preferences.theme===value} onClick={()=>update('theme',value)} className={`settings-theme settings-theme-${value} ${preferences.theme===value?'selected':''}`}><span className="settings-theme-preview"><Icon size={20}/><i/><i/>{preferences.theme===value&&<Check size={15} className="settings-theme-check"/>}</span><strong>{label}</strong><small>{sub}</small></button>)}
          </div>
          <div className="settings-row"><div><strong>字体与界面缩放</strong><p>让长对话也读得轻松一点。</p></div><label className="settings-select-wrap"><select aria-label="字体与界面缩放" value={preferences.fontScale} onChange={event=>update('fontScale',Number(event.target.value))}>{[.9,1,1.1,1.2].map(value=><option key={value} value={value}>{Math.round(value*100)}%</option>)}</select><ChevronDown size={14}/></label></div>
          <LocalSwitch label="轻柔动效" description="关闭后减少页面过渡与角色装饰动画；也尊重系统减少动态效果。" checked={preferences.motion} onChange={()=>update('motion',!preferences.motion)}/>
          <div className="settings-row"><div><strong>界面语言</strong><p>当前提供简体中文；更多语言保留扩展。</p></div><span className="settings-language"><Globe2 size={15}/> 简体中文</span></div>
        </Panel>
        <Panel className="settings-card">
          <SectionHeading eyebrow="YOUR PACE" title="舒适地待在这里"><BellOff size={20}/></SectionHeading>
          <LocalSwitch label="显示角色形象" description="角色仅表达已允许的展示状态，不推断奈奈的内在情绪。" checked={preferences.avatar} onChange={()=>update('avatar',!preferences.avatar)}/>
          <LocalSwitch label="安静模式" description="减少界面提示。不会设定奈奈联系你的频率，也不更改 Core 通知授权。" checked={preferences.quiet} onChange={()=>{update('quiet',!preferences.quiet);notify(preferences.quiet?'界面提示已恢复':'已开启本地安静模式')}}/>
        </Panel>
        <Panel className="settings-card settings-demo-card">
          <SectionHeading eyebrow="A SMALL POSSIBLE WORLD" title="演示场景"><Badge tone="amber">DEMO</Badge></SectionHeading>
          <p className="settings-description">体验一个可能的生活切片，也看看连接中断、意见分歧和未知结果怎样被如实表达。所有内容均为模拟。</p>
          <label className="settings-scenario-label" htmlFor="demo-scenario">选择演示场景</label><div className="settings-select-wrap settings-scenario-select"><select id="demo-scenario" value={scenario} onChange={event=>setScenario(event.target.value as Scenario)}>{(Object.keys(scenarioLabels) as Scenario[]).map(key=><option key={key} value={key}>{scenarioLabels[key]}</option>)}</select><ChevronDown size={16}/></div>
          <div className="settings-demo-foot"><Sparkles size={15}/><span>场景切换不会操作设备、写入 Core 或制造真实生活史。</span></div>
        </Panel>
      </div>
      <div className="settings-stack">
        <Panel className="settings-avatar-card"><SectionHeading eyebrow="APPEARANCE STUDIO" title="形象小屋"><Eye size={20}/></SectionHeading><AvatarStage expression={data.presence.expression} enabled={preferences.avatar}/><p className="settings-avatar-note">内置头像来自用户提供的原型。图片预览只留在当前页面，不上传，不当作 Live2D 模型。</p></Panel>
        <Panel className="settings-core-note"><ShieldCheck size={24}/><h3>窗口可以改变，奈奈始终连续</h3><p>One Subject · One authoritative Store · One SubjectLoop · One active lineage</p><small>主体状态只由 Nana Core 管理。空间主题与角色外观不会创建第二个主体。</small></Panel>
      </div>
    </div>
    <Panel className="settings-card settings-core-card"><SectionHeading eyebrow="NANA CORE BOUNDARY" title="Core 配置与未来接入" description="下面记录真实契约与接入条件。尚未接入的配置不会显示为已修改。"><Badge tone="muted">只读说明</Badge></SectionHeading><div className="settings-core-grid">{coreConfiguration.map(item=><details key={item.title} className="settings-contract"><summary><span><strong>{item.title}</strong><small>{item.description}</small></span><Badge tone={item.status==='PLANNED'?'muted':'cyan'}>{item.status}</Badge></summary><p>{item.detail}</p></details>)}</div></Panel>
  </div>;
}
