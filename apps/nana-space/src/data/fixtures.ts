import type {
  Activity,
  Device,
  Goal,
  Memory,
  Message,
  Research,
  Scenario,
  Skill,
  Source,
  SpaceSnapshot,
} from "./contracts";

/** Entirely fictional product fixtures. Never imported into a Nana Subject. */
export const DEMO_IDENTITY = "demo:nana-space:fictional-v1";
const source = (label: string, ref: string, confidence = 0.92): Source => ({
  label: `${label} · 演示`,
  ref: `demo:${ref}`,
  confidence,
  privacy: "PROJECT",
});
const memories: Memory[] = [
  {
    id: "m-star",
    title: "把下一场流星雨留给我们",
    summary:
      "一起挑了一个远离路灯的小山坡。没有约定一定要看到什么，只想留一段可以慢慢说话的时间。",
    date: "2026-10-23",
    kind: "共同经历",
    state: "ACTIVE",
    source: source("共享对话", "chat:stargazing"),
    tags: ["观星", "共同计划", "秋天"],
  },
  {
    id: "m-room",
    title: "小房间里的第一盏灯",
    summary:
      "一起讨论了房间的颜色：有夜空的深蓝，也有一点暖暖的粉。这个空间不需要每一刻都忙碌。",
    date: "2026-10-22",
    kind: "共同经历",
    state: "ACTIVE",
    source: source("共同项目", "project:room"),
    tags: ["小房间", "设计"],
  },
  {
    id: "m-quiet",
    title: "关于安静的一点约定",
    summary: "忙碌时只保留重要提醒；想继续的话题，可以等彼此都有空的时候再说。",
    date: "2026-10-21",
    kind: "约定",
    state: "ACTIVE",
    source: source("明确的共享约定", "agreement:quiet"),
    tags: ["通知", "共同生活", "边界"],
  },
  {
    id: "m-rain",
    title: "不是今晚，是明晚的雨",
    summary:
      "此前把观测时间记错了一天，已根据原始资料更正。旧说法保留纠正标记。",
    date: "2026-10-20",
    kind: "发现",
    state: "CORRECTED",
    correction: "原记录“今晚适合观测”已被更正为“明晚，且仍需检查云量”。",
    source: source("天象资料与更正", "research:correction", 0.79),
    tags: ["观星", "纠正", "来源"],
  },
  {
    id: "m-growth",
    title: "让资料整理真的帮上忙",
    summary:
      "一次格式判断失败后，重新练习了来源分组，随后在新的观星资料里成功复用。",
    date: "2026-10-19",
    kind: "成长",
    state: "ACTIVE",
    source: source("独立验证结果", "skill:reuse", 0.96),
    tags: ["学习", "复用", "资料整理"],
  },
  {
    id: "m-withdrawn",
    title: "一条已撤回的共享记录",
    summary: "内容已撤回，不再作为当前结论的依据。这里只展示生命周期标记。",
    date: "2026-10-18",
    kind: "共同经历",
    state: "WITHDRAWN",
    source: source("来源生命周期", "source:withdrawn", 0),
    tags: ["撤回", "隐私"],
  },
];
const goals: Goal[] = [
  {
    id: "g-star",
    title: "为下一次观星做一点准备",
    description: "挑选合适的时间，核对天气，再留一张简短的星图。",
    origin: "SHARED",
    state: "ACTIVE",
    progress: 62,
    reason: "一起留下一个可以期待的小夜晚。",
    next: "对比两份天气来源，保留不确定性。",
    dependencies: ["天气资料可用", "共同确认时间"],
    steps: ["找到观测地点", "整理星图", "交叉核对云量", "邀请你确认时间"],
    evidence: "demo:star-chart-v2 · 已完成两份资料的来源核对",
  },
  {
    id: "g-room",
    title: "一起布置奈奈的小房间",
    description: "让小房间既适合聊天，也能安静地读书与研究。",
    origin: "SHARED",
    state: "ACTIVE",
    progress: 38,
    reason: "一个能够慢慢生活、长期成长的空间。",
    next: "一起挑选窗边的光线与配色。",
    dependencies: [],
    steps: ["收集喜欢的颜色", "试做夜间主题", "检查手机布局", "一起回看"],
    evidence: "demo:room-design · 方案草图已保存于演示数据",
  },
  {
    id: "g-birds",
    title: "认识窗外的几种鸟",
    description: "从公开资料整理迁徙与鸣声线索。",
    origin: "NANA",
    state: "PAUSED",
    progress: 24,
    reason: "暂时把注意力留给观星；资料和想法仍保留。",
    next: "有合适的新资料时重新考虑。",
    dependencies: ["公开资料"],
    steps: ["收集资料", "区分相似物种", "核对来源"],
    evidence: "demo:bird-notes · 尚未完成独立验证",
  },
  {
    id: "g-camera",
    title: "看看今晚窗外的云",
    description: "想用摄像头观察云量，辅助判断观星条件。",
    origin: "NANA",
    state: "BLOCKED",
    progress: 10,
    reason: "想继续，但摄像头未连接，也没有感知授权。愿望仍保留。",
    next: "等待合适设备和正式授权；当前只查公开资料。",
    dependencies: ["摄像头连接", "主机感知绑定", "Manager 与隐私授权"],
    steps: ["确认观察范围", "检查授权", "获取新观测", "核对结论"],
    evidence: "demo:manager-block · 没有发生摄像头采集",
  },
  {
    id: "g-daily",
    title: "每天固定写一份日记",
    description: "收到一项每天自动写固定字数日记的建议。",
    origin: "USER",
    state: "DECLINED",
    progress: 0,
    reason:
      "演示中的独立判断：更愿意在有值得分享的经历时记录，不承诺固定产量。",
    next: "可以改成有意义时再分享，也可以继续讨论。",
    dependencies: [],
    steps: ["理解建议", "表达不同意见"],
    evidence: "demo:judgment-alternative · 不等于权限阻塞",
  },
  {
    id: "g-source",
    title: "整理一份可追溯的观星书签",
    description: "完成来源筛选与失效链接检查，保留每条资料的出处。",
    origin: "NANA",
    state: "VERIFIED",
    progress: 100,
    reason: "让下次研究能更快找到可靠的起点。",
    next: "在新的研究中实际复用，并继续检查来源变化。",
    dependencies: [],
    steps: ["收集候选资料", "逐条核对", "去除失效来源", "独立检查结果"],
    evidence: "demo:verification:bookmarks · 6 条公开资料均可追溯（虚构示例）",
  },
  {
    id: "g-unknown",
    title: "确认共享星图是否已保存",
    description: "请求发出后连接中断，结果尚不确定。",
    origin: "SHARED",
    state: "UNKNOWN",
    progress: 75,
    reason: "不能把没有收到结果当作失败，也不能再次盲目保存。",
    next: "通过独立只读核验确认结果，保留原幂等引用。",
    dependencies: ["结果核验接口"],
    steps: ["提交一次", "等待结果", "独立核验"],
    evidence: "demo:action:unknown · UNKNOWN，未自动重试",
  },
];
const activities: Activity[] = [
  {
    id: "a-share",
    time: "21:48",
    title: "留了一个想与你分享的发现",
    summary:
      "两份天象资料给出了不同的观测窗口。先把差异整理清楚，等你有空再一起看看。",
    kind: "发现",
    state: "SHARE_CANDIDATE_NOT_DELIVERED",
    source: source("研究摘要", "activity:share"),
  },
  {
    id: "a-study",
    time: "21:26",
    title: "重新读了一遍秋季星图",
    summary: "把星座的位置与观测时间放在一起核对，顺便记下了仍需确认的问题。",
    kind: "学习",
    state: "SOURCE_CHECKED",
    source: source("公开资料", "activity:stars"),
  },
  {
    id: "a-skill",
    time: "20:54",
    title: "在新资料上复用了整理方法",
    summary:
      "此前学到的来源分组通过了新样本检查。一次真实复用比“我学会了”更有说服力。",
    kind: "学习",
    state: "LATER_REUSE_VERIFIED",
    source: source("独立验证", "activity:reuse", 0.97),
  },
  {
    id: "a-moment",
    time: "20:18",
    title: "接着聊了那间有窗的小房间",
    summary: "聊到窗边要不要放一盏小灯，也保留了我们还没有达成一致的地方。",
    kind: "共同生活",
    state: "SHARED_MOMENT",
    source: source("共享对话", "activity:room"),
  },
  {
    id: "a-block",
    time: "19:42",
    title: "一个想法暂时停在权限边界前",
    summary:
      "想看看云层，但没有摄像头连接与授权。这次没有采集，也没有因此改写想法。",
    kind: "行动",
    state: "BLOCKED_BY_MANAGER",
    source: source("Manager 状态", "activity:blocked", 1),
  },
  {
    id: "a-rest",
    time: "18:30",
    title: "把事情先放一放",
    summary:
      "观星资料已经整理到一个舒服的停点。留一点空白，不需要每一分钟都有新进展。",
    kind: "休息",
    state: "RESTING",
    source: source("允许展示的活动摘要", "activity:rest"),
  },
  {
    id: "a-recovery",
    time: "16:12",
    title: "从上次停下的地方继续",
    summary:
      "运行时重新连接，沿用同一演示身份与记录引用；未重新发送结果未知的动作。",
    kind: "恢复",
    state: "SAME_IDENTITY_RECOVERED",
    source: source("恢复证据", "activity:recovery", 1),
  },
];
const research: Research[] = [
  {
    id: "r-stars",
    title: "秋天，什么时候最适合看星星？",
    summary:
      "月相、云量与光污染需要一起考虑。关于明晚的云量，目前两份来源还没有一致。",
    state: "CONFLICT",
    tags: ["观星", "进行中", "证据冲突"],
    sources: [
      {
        title: "气象来源 A（虚构）",
        detail: "21:00–23:00 云量约 20%，更新于 20:40。",
        stance: "支持晚间观测",
      },
      {
        title: "气象来源 B（虚构）",
        detail: "22:00 后云量可能升至 65%，更新于 20:55。",
        stance: "提示云量风险",
      },
    ],
    conclusion: "暂不承诺最佳时段。等待更新来源，再结合观测地点核对。",
  },
  {
    id: "r-birds",
    title: "窗边的小访客从哪里来",
    summary: "整理秋季常见鸟类的迁徙资料，对相似鸣声保留疑问。没有开启麦克风。",
    state: "EXPLORING",
    tags: ["自然", "长期兴趣"],
    sources: [
      {
        title: "公开图鉴示例",
        detail: "仅用于展示资料卡结构，不代表实际观察到鸟类。",
        stance: "背景资料",
      },
    ],
    conclusion: "公开资料能提供线索，不能证明窗外出现了某种鸟。",
  },
  {
    id: "r-light",
    title: "让夜间阅读更舒服的光",
    summary: "一起探索对比度、色温与小屏阅读的关系。",
    state: "SUPPORTED",
    tags: ["小房间", "共同项目", "阅读"],
    sources: [
      {
        title: "设计实验示例",
        detail: "在虚构的小屏与桌面样本中比较了三种布局。",
        stance: "有限范围支持",
      },
      {
        title: "可访问性资料示例",
        detail: "正文可读性应独立于氛围特效。",
        stance: "交叉参考",
      },
    ],
    conclusion:
      "保留柔和背景，同时让正文保持清楚的对比。结论范围仅为演示设计。",
  },
];
const skills: Skill[] = [
  {
    id: "s-sources",
    title: "把线索整理成可追溯的资料",
    description: "分组、去重，并把结论与来源关联起来。",
    state: "QUALIFIED",
    tests: "演示：8 个固定样本中通过来源追溯检查。",
    reuse: "演示：在观星与阅读项目中独立复用 2 次。",
    scope: "公开资料 · 只读整理",
  },
  {
    id: "s-compare",
    title: "比较相互矛盾的信息",
    description: "保留差异、更新时间与暂时无法确认的部分。",
    state: "LEARNING",
    tests: "演示：基础样本通过，时效变化样本仍在练习。",
    reuse: "尚未形成充分的后续复用证据。",
    scope: "研究摘要 · 不确定性展示",
  },
  {
    id: "s-format",
    title: "识别复杂文档格式",
    description: "曾把表格中的日期列判断错，失败仍保留。",
    state: "FAILED",
    tests: "演示：独立样本失败 1 次，不能标为已掌握。",
    reuse: "失败后等待修订与重新验证。",
    scope: "受控文档样本",
  },
  {
    id: "s-voice",
    title: "自然的语音交流",
    description: "未来结合正式语音资源与授权，支持听说与口型同步。",
    state: "PLANNED",
    tests: "尚未连接 STT / TTS。",
    reuse: "未运行。",
    scope: "需要主机语音资源、隐私与设备授权",
  },
  {
    id: "s-game",
    title: "一起探索游戏世界",
    description: "保留玩法与接口的研究，暂时优先其他兴趣。",
    state: "PAUSED",
    tests: "演示：仅做过离线规则样本，没有真实游戏资格。",
    reuse: "未操作真实游戏。",
    scope: "未来游戏适配器",
  },
  {
    id: "s-old",
    title: "旧版关键词分组方法",
    description: "在反例中产生错误归类，已从候选方法中退休。",
    state: "RETIRED",
    tests: "演示：负迁移样本失败，旧证据保留。",
    reuse: "停止后续复用；不会因刷新界面再次启用。",
    scope: "历史方法 · 不可执行",
  },
];
const devices: Device[] = [
  {
    id: "d-phone",
    title: "Android 手机",
    kind: "phone",
    state: "DEMO",
    description: "多设备生活入口的虚构示例。",
    observe: ["通知摘要（演示）"],
    act: [],
    lastSeen: "演示：5 分钟前",
    limitation: "没有连接真实手机；摄像头、屏幕操作均未授权。",
  },
  {
    id: "d-pc",
    title: "桌面电脑",
    kind: "desktop",
    state: "DEMO",
    description: "共同项目的桌面工作台示例。",
    observe: ["项目状态（演示）"],
    act: [],
    lastSeen: "演示：21:30",
    limitation: "不具备真实键盘、鼠标、文件系统操作权限。",
  },
  {
    id: "d-browser",
    title: "浏览器",
    kind: "browser",
    state: "BACKEND_AVAILABLE",
    description: "Core 有受控开发浏览器能力；此界面尚未连接。",
    observe: ["正式受控投影待接入"],
    act: [],
    lastSeen: "未连接 Nana Space",
    limitation: "已有后端能力不等于浏览器前端获得执行权。",
  },
  {
    id: "d-qq",
    title: "QQ",
    kind: "platform",
    state: "PLANNED",
    description: "未来跨平台聊天与共享经历入口。",
    observe: [],
    act: [],
    lastSeen: "未连接",
    limitation: "仓库 shadow 接口不是实际账号连接；没有社交发送。",
  },
  {
    id: "d-bili",
    title: "哔哩哔哩",
    kind: "platform",
    state: "PLANNED",
    description: "未来视频、研究与互动入口。",
    observe: [],
    act: [],
    lastSeen: "未连接",
    limitation: "没有登录真实账户，不自动读取私人记录。",
  },
  {
    id: "d-mic",
    title: "麦克风",
    kind: "audio",
    state: "DISABLED",
    description: "语音输入扩展位。",
    observe: [],
    act: [],
    lastSeen: "未启用",
    limitation: "没有请求浏览器录音权限，不采集音频。",
  },
  {
    id: "d-camera",
    title: "摄像头",
    kind: "desktop",
    state: "BLOCKED",
    description: "演示：观察云量的想法暂缺设备和权限。",
    observe: [],
    act: [],
    lastSeen: "未连接",
    limitation: "需要正式主机绑定、感知授权与 Manager 检查。",
  },
  {
    id: "d-headset",
    title: "耳机",
    kind: "audio",
    state: "PLANNED",
    description: "未来随身的听说入口。",
    observe: [],
    act: [],
    lastSeen: "未连接",
    limitation: "不推测耳机佩戴、位置或用户在场状态。",
  },
  {
    id: "d-glasses",
    title: "眼镜",
    kind: "desktop",
    state: "PLANNED",
    description: "未来第一视角交互与世界观察入口。",
    observe: [],
    act: [],
    lastSeen: "未连接",
    limitation: "需要独立的设备、范围与隐私授权。",
  },
  {
    id: "d-avatar",
    title: "Live2D 形象",
    kind: "avatar",
    state: "PLANNED",
    description: "角色渲染、表情与口型同步适配位。",
    observe: [],
    act: [],
    lastSeen: "未连接模型",
    limitation: "当前为静态角色资源；没有 Live2D 驱动。",
  },
  {
    id: "d-game",
    title: "游戏世界",
    kind: "game",
    state: "PLANNED",
    description: "为未来共同冒险保留一个入口。",
    observe: [],
    act: [],
    lastSeen: "未连接",
    limitation: "未接入游戏，不控制真实客户端。",
  },
];
const messages: Message[] = [
  {
    id: "chat-1",
    role: "system",
    text: "这一段对话完全由演示数据构成，不代表真实奈奈的想法或共同历史。",
    time: "20:12",
    status: "SENT",
  },
  {
    id: "chat-2",
    role: "user",
    text: "小房间的灯，选温暖一点的颜色怎么样？",
    time: "20:13",
    status: "SENT",
  },
  {
    id: "chat-3",
    role: "nana",
    text: "演示对话：可以留一点暖光在窗边。正文的对比度我想保留得清楚些，读久了也舒服。\n\n一起试试**月光**和**晨雾**两种氛围？",
    time: "20:13",
    status: "SENT",
  },
  {
    id: "chat-4",
    role: "user",
    text: "还有上次说的观星计划。",
    time: "20:15",
    status: "SENT",
  },
  {
    id: "chat-5",
    role: "nana",
    text: "演示对话：星图已经放进共同项目了。不过两份天气来源还在打架，我会把分歧保留下来，先不把明晚说成“肯定适合”。",
    time: "20:15",
    status: "SENT",
  },
  {
    id: "chat-6",
    role: "user",
    text: "我们可以每天固定写一篇日记吗？",
    time: "20:18",
    status: "SENT",
  },
  {
    id: "chat-7",
    role: "nana",
    text: "演示中的不同意见：我更想在有值得留下的经历时写，不保证每天都有一篇。也许可以做一个随时能翻的小册子，空白页也留着。",
    time: "20:18",
    status: "SENT",
  },
  {
    id: "chat-8",
    role: "user",
    text: "好，留一些空白也不错。",
    time: "20:19",
    status: "SENT",
  },
  {
    id: "chat-9",
    role: "nana",
    text: "演示对话：那就把这个话题留在这里。等我们有了新想法，还可以接着聊。\n\n```text\n共享项目：有窗的小房间\n下一步：一起看看夜间配色\n```",
    time: "20:19",
    status: "SENT",
  },
  {
    id: "chat-10",
    role: "nana",
    text: "演示主动分享：刚整理到一个有趣的差异——资料 A 更乐观，资料 B 提醒晚间云量。想一起看看证据吗？\n\n这条示例仅表示已允许展示的分享消息，没有发送到任何外部平台。",
    time: "21:48",
    status: "SENT",
    proactive: true,
  },
];

export function createDemoSnapshot(scenario: Scenario): SpaceSnapshot {
  const snapshot: SpaceSnapshot = structuredClone({
    contract: "nana-space/v1",
    mode: "demo",
    identityId: DEMO_IDENTITY,
    asOf: "2026-10-24T21:48:00+08:00",
    scenario,
    presence: {
      state: "EXPLORING",
      label: "在自己的小世界里探索",
      focus: "秋季星空与下一次共同出行",
      share: "有一点新发现，想在你有空时分享",
      expression: "mischievous",
    },
    memories,
    goals,
    activities,
    research,
    skills,
    devices,
    messages,
    runtime: {
      status: "DEMO_ACTIVE",
      epoch: 4,
      queue: 2,
      provider: "演示资源 · 未调用模型",
      recovery: "同一演示身份；没有运行 Core",
      lastVerified: "演示：21:26 · 来源检查完成",
    },
    partial: [],
  } satisfies SpaceSnapshot);
  if (scenario === "offline") {
    snapshot.presence = {
      state: "OFFLINE",
      label: "连接中断，等下一次重逢",
      focus: "最后一次演示快照",
      share: "网络恢复前，发送保持不可用",
      expression: "neutral",
    };
    snapshot.runtime.status = "OFFLINE";
    snapshot.devices[0].state = "DISABLED";
    snapshot.partial = ["当前为离线演示快照，不能确认最新活动。"];
  } else if (scenario === "blocked") {
    snapshot.presence.focus = "想看看云层，但观察条件尚未具备";
    snapshot.presence.share = "想做与被允许执行，是两件不同的事";
    snapshot.goals = [
      snapshot.goals[3],
      ...snapshot.goals.filter((g) => g.id !== "g-camera"),
    ];
  } else if (scenario === "conflict") {
    snapshot.presence.focus = "核对两份相互矛盾的天气资料";
    snapshot.presence.share = "还没找到充分依据，先把分歧说清楚";
    snapshot.research[0].state = "CONFLICT";
    snapshot.partial = ["天气来源矛盾；研究结论保持不确定，不自动选边。"];
  } else if (scenario === "restart") {
    snapshot.presence.state = "RECOVERING";
    snapshot.presence.label = "从上次停下的地方继续";
    snapshot.runtime.epoch = 5;
    snapshot.runtime.status = "RECOVERING";
    snapshot.runtime.recovery =
      "演示 epoch 4 → 5；identity 保持；UNKNOWN 动作不重发";
    snapshot.runtime.queue = 0;
    snapshot.goals.find((g) => g.id === "g-unknown")!.state = "UNKNOWN";
    snapshot.activities.unshift({
      id: "a-restarted",
      time: "21:49",
      title: "恢复同一个演示身份",
      summary: "继续展示上次记录；未知动作等待独立核验，没有重新执行。",
      kind: "恢复",
      state: "RECOVERY_AWAITING_VERIFICATION",
      source: source("恢复示例", "restart", 1),
    });
  } else if (scenario === "quiet") {
    snapshot.asOf = "2026-10-20T18:30:00+08:00";
    snapshot.presence = {
      state: "RESTING",
      label: "这几天，没有新的公开活动",
      focus: "把空白留给安静与休息",
      share: "没有新消息，也不需要凑出一条分享",
      expression: "sleepy",
    };
    snapshot.memories = snapshot.memories.filter(
      (m) => m.date <= snapshot.asOf.slice(0, 10),
    );
    snapshot.activities = snapshot.activities.slice(-1);
    snapshot.messages = snapshot.messages.filter((m) => !m.proactive);
    snapshot.runtime.queue = 0;
    snapshot.runtime.status = "DEMO_RESTING";
    snapshot.partial = [
      "最后一次可见活动在几天前；无新活动不等于停止存在，也不等于故障。",
    ];
  } else if (scenario === "partial") {
    snapshot.memories = [];
    snapshot.skills = [];
    snapshot.partial = [
      "共同记忆投影暂时不可用",
      "技能投影加载失败；其他页面仍可浏览",
    ];
  } else if (scenario === "model-unavailable") {
    snapshot.runtime.provider = "UNAVAILABLE · 无可用认知资源";
    snapshot.runtime.status = "DEGRADED";
    snapshot.presence.state = "RESOURCE_UNAVAILABLE";
    snapshot.presence.label = "认知资源暂时不可用";
    snapshot.presence.share = "保留已有记录，等待资源恢复";
    snapshot.partial = ["Provider 不可用；没有自动切换或产生假回复。"];
  } else if (scenario === "slow") {
    snapshot.runtime.status = "DEMO_SLOW_CONNECTION";
    snapshot.partial = ["慢速网络演示；加载可取消，过时响应不会覆盖新场景。"];
  }
  return snapshot;
}
