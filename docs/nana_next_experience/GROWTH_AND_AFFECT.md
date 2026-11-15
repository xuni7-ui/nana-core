# 原生情感与独立念头增强 — 同一 Next Experience / 十域精修任务

## 实际缺口与行为变化

借鉴 Fish Heart 的设计思想，固定来源/许可见 FISH_HEART_GAP_MATRIX.md；没有复制插件执行代码或安装生产插件。

1. **原来源去重**：修复同一原始观察的多个派生 Memory ID 能刷高 encounters 的问题。复用原 S3 Growth 的证据根解析，最多128节点；来源不明或当前依赖超过32时暂缓，不伪装独立新经历。不同的新来源仍能形成兴趣。
2. **念头自然淡出与再关注**：原 C 已考虑的纯念头没有目标/技能时也按既有三天时间窗淡出，避免永久占用热关注。后续独立新事实可让同一关注重新接受 C 判断；旧来源别名不能重开。ABANDONED、实际目标/技能、UNKNOWN执行恢复栅栏保持。绝对时间跨重启重算，不补发停机期间动作，不清空长期关系。
3. **归因**：常见中文引用、第三方转述先留为语义提案，不把“他说先别聊”直接变成用户本人的持久拒绝。没有负面关键词扣关系机制。此为保守窄规则，不能冒充通用真实模型语义资格。
4. **晚安与返回**：完整、无引用的“晚安／我先休息了”等明确声明写入原有 delivery 边界的 presence.rest 话题。自主投递与通知提示在准备和执行前复查；已准备的旧投递也会失效。返回声明只重开投递，不发 Grant、不自动判定AVAILABLE、不解除处理禁令。新直接聊天仍可进行，原 C 的判断、独立兴趣和学习保留。回应是明确标识的本地边界确认，不伪装模型措辞。复杂晚安表达仍走原语义资源，未声称全部自然语言已覆盖。
5. **在线状态真实恢复**：实际测试发现反复 availability 更新被当成互相冲突的永久事实。新 presence 元数据带真实事件时间，通过原 MemoryService correction 链替代前次状态；保留旧无时间记录，不编写历史时间。35次切换后只有一条 CURRENT，删除当前来源不会复活旧状态；同时间戳以 rowid 稳定取最新。
6. **真实界面接线**：原 Inspector 从提案正文取 Concern 状态，实际返回UNKNOWN；现只投影 open_concerns 当前权威行，避免旧版本重复卡片。Nana Space 使用简洁中文状态，来源展开可核查原代码与时间；不提供人格分数编辑，不用假故事填充。

## 原 C 因果对照

同一公开合成观察 → 三个派生解释，旧机制可升为兴趣，现保持1次TRANSIENT且不产生机会；重启后独立新观察 → INTEREST → 原 C 自主EXPLORE → PROPOSED；无新事实不重复判断，跨重启/虚拟三天后纯念头EXPIRED；独立新来源再关注，旧别名仍无效；原来源撤回后整条派生关注不可展示。这是原 Store/Subject/C 的受控执行，不是模型自评。

S8 对应上一批6f2a491：原G从实际任务失败发现缺口，在新候选可见练习材料出现后再次实验，独立评价/迁移/后来合成世界实际复用；资格本身不冒充需要已满足，后续Verify才使原S3 competence OPEN→SETTLED；反例和来源撤回停用。原学习模型和人格资源没有重建。本轮进一步解决自主关注的重复、遗忘与再考虑问题。开发者改代码不等于奈奈自己学习。

## 证据与界限

本批受影响原Core233通过/0失败104.42秒，涵盖原world/实际SIGKILL/自主性/关系/学习/对话/边界；随后 Inspector 修复及只读投影/真实owned经历相关7通过2.20秒。桌面/360/390/412浏览器24通过31.6秒，含真实契约夹具中的状态展示、来源撤回、聊天大小、模型目录、旧记忆查找与UNKNOWN。旧Core6f2a491完整回归1905通过/12明确跳过572.94秒仍按原源码记载，不能冒充本次源码全仓回归。初始失败原样保留。

新增规则不增加模型调用或随机轮询；受控链使用本地合成 Provider/虚拟时钟，真实Provider调用0，成本0。233项整体时长含进程与夹具等待，不用作产品P95性能结论。沿用三天/小时复查/16热关注/有界来源；没有建立第二情绪数值、第二Store、第二循环或第二意志。

**真实模型语义/人类自然度/物理手机/跨日生活与长期资源稳定性未运行**。不能据此宣称“已在真实生活中更合理选择”、First-Life Ready或总工程完成。云端L0恢复、Iris迁移与生产激活仍由原负责人处理；本地未读取或修改其数据。

## 后续完整回归修正

73fc941全仓首次运行揭示真实边界：新的语义认识来自相同原始事件，仍应允许原C重评，不能只因证据根相同拦掉。现复用原WorldLoop的同一个CognitionSession验证当前提案及真实world_stamp变化；不加encounters、不自动行动、不复活过期关注，不重放UNKNOWN/目标/技能。重复模型措辞、同一世界快照别名依然无效。原H1测试已增强为两次独立C判断、一个原始encounter且不重复重放。完整新源码回归待验，初始失败未掩盖。


## Same-task S8 retrieval feedback continuation

Retained-note lookup failures now have an original C→G practice/independent validation→later ContextAssembler method path; checked counterexamples and S3 need modulation reuse existing services. Exact scope, tests, recovery and unrun real-life gates: RETRIEVAL_GROWTH.md. Developer implementation is not itself Nana learning; only actual original-G executed trials/later lookup count within the declared DEV scope.

## 2026-11-09 · 自主性A–E续审：成本与认知负荷分开

原OpportunityQueue把资源估计中的外部需预留/未知一律当HIGH认知负荷；相同已采纳兴趣、轻量短时低存储不打扰场景基线2失败4通过，修复后原兴趣/学习/注意/Hands/边界57通过15.38s。保留队列排序及完整估计，只将compute/time/storage/interruption或显式HEAVY映射负荷；真实pending负荷与Resource/Manager/Grant/Kernel继续约束执行，不因想探索创建权限。见evidence/resumed-20261109。

| 当前路径 | A–E归属与结论 | 下一步/证据限制 |
|---|---|---|
| Grant/Kernel、非普通资源披露 | A现实权限；执行门保留，不能反向擦掉兴趣 | 原受控Hands回归复用；真实账号未验 |
| pending>=4、compute/time/storage/interruption | B容量/注意；保留暂缓，不设永久兴趣禁令 | 57相关覆盖；不同长期负荷竞争待扩大 |
| 外部需预留/未知→HIGH认知负荷 | E错误归因，本批最小修复 | 2失败对照→6控制通过；不是收费额度已许可 |
| 明确休息/话题拒绝/隐私/投递准入 | C接收者边界，保持范围/撤回/UNKNOWN | 不等于内部念头必须消失 |
| due commitment优先、无足够价值学习则WATCH | D主体当前取舍，硬优先可能过宽 | 未整体资格；需紧急新事件/承诺可延期的因果对照，不简单删分支 |
| 高负荷一律REST、社交低相关/重复→沉默 | D/E待分辨；当前保留愿望记录 | 轻量替代/真实分享愿望及不同上下文独立评价尚待实现 |
| 通用低价值/重复压制匹配已采纳兴趣 | E已有58418b4修复，复用 | 不表示全部娱乐/社交分类已收口 |

本表是现有入口的增量核对，不宣称A–E全覆盖、自然度、真实生活或长期成长完成。

## 2026-11-14 · 明确考虑的重型兴趣与原REST动机共同竞争

原C明确选择、有独立私人兴趣支持时，HIGH负荷/HEAVY投入不再在后续策略强制替换为REST；REST仍在原动机，未考虑的重型默认与实际资源/权限/接收者门保留。这是A/B/C不变、修E并归还D取舍的窄范围修正。正常Runtime/SELF旧3fail2pass→15pass、199相关52.93s，同1次53288wirebytes非Token；不是重型活动已执行或全自主性资格。证据evidence/deliberated-heavy-interest-20261114/README.md。
