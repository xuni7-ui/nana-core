# Nana Core · Foundation Capability Matrix

版本：1.0 · 首次完整核账 · 2026-10-20（Asia/Shanghai）  
规范：[00_MASTER_FRAMEWORK.md](00_MASTER_FRAMEWORK.md) · 当前任务：[09_STATE.md](09_STATE.md)  
审计基线：`eece7a469a5af8a9df5731367e5b7db046039a23`，开发分支 `dev/nana-core-cloud-first-life-launch-v1-codex`。

## 1. 口径与审计边界

[源码核对] 本轮固定远端commit，逐域检查选定实现、测试定义及已提交资格材料；逐条结果可见[机器可读核账记录](../docs/nana_master_framework_foundation_audit_v1_evidence/audit.json)。本轮不重跑应用测试，不调用模型、不读取私人历史、不访问staging运行宿主、不改生产。

[历史实测证据复用] 既有真实进程/受控OS效果与虚拟/fixture资格按原范围保留；最近全仓记录为1300 passed /12 skipped，见REGRESSION。此数字不是本轮运行，不把E12或opt-in screen跳过项写成新通过。

`FOUNDATION_QUALIFIED` 在本表仅指固定criteria在指定开发范围内合格，不表示生产、通用智能、真人相处或开放终身成长资格。测试与资格材料不是外部独立认证。

所有criteria状态使用宪法七级词表。UNKNOWN表示证据不足；不得推成NOT_STARTED或必须重写。域汇总是对完整闭环的判断，不是行数平均；每条未知必须列明升级条件。`growth_status=ADVANCED_GROWTH` 表示未来扩展归属，不表示扩展已经实现。

## 2. 总览

| Domain | Foundation状态 | 是否阻塞基础First-Life | 当前范围/关键缺项 |
|---|---|---|---|
| S1 Subject / Identity | FOUNDATION_QUALIFIED | 否 | 受控开发实例；模型替换含合成端口，不等于所有真实模型/平台迁移。 |
| S2 Memory / Experience | FOUNDATION_QUALIFIED | 否 | 合成与受控开发材料；没有把私人历史内容不足当成机制未完成。 |
| S3 Motivation / Affect / Relationship | FOUNDATION_TESTED | 是 | 已有合成因果/实际进程恢复及真实受控任务→分享候选；完整内在倾向的真实持续闭环未核实。 |
| S4 Runtime / Living Presence | FOUNDATION_TESTED | 是 | 2h真实开发驻留已留证；24h仅有中途快照，非生产常驻资格。 |
| S5 World / Perception / Cognition | FOUNDATION_TESTED | 是 | 世界模型和认知协议已有测试；文本provider与受控视觉入口分别留证，组合真实语义资格有缺项。 |
| S6 Independent Judgment / Problem Framing / Goal / Planning | FOUNDATION_TESTED | 是 | 有限目标/方法替代、capability-gap重述与规划已成立；更广问题定义的最小资格待界定核实。 |
| S7 Hands / Action / Verification | FOUNDATION_QUALIFIED | 否 | OWNED_DEV_APPLICATION_PROCESS；DOCUMENT/FORM/CONTENT/FILES有限IPC与文件，非GUI/个人设备/生产。 |
| S8 Learning / Self-Evolution — Cross-Domain Growth Engine | FOUNDATION_QUALIFIED | 否 | 受控方法学习与纯数据工作流适配；跨任务域可用的成长合同，不等于已改善S2–S9每一域。 |
| S9 Self-Extension | FOUNDATION_QUALIFIED | 否 | 有限确定性纯数据workflow/code skill；实际bwrap和原Kernel复用。 |
| S10 Lineage / Deep Evolution | FOUNDATION_PARTIAL | 否 | 身份/迁移/受限skill谱系已有；深层Core/评测底座改变尚未资格化。 |

当前结论：S1/S2/S7/S8/S9在明示受控范围已有基础资格；S3/S4/S5/S6的必要资格尚有未知；S10深层实现部分完成且不作为当前基础Gate前置。**尚不能宣布S1–S9全部Foundation Qualified。**

这不是“发现四套系统必须重写”。本轮确认的是资格差额，尚未确认任何一项整体重写需求。代码缺失、资格缺失、范围窄、未来扩展必须分别处理。

## 3. 固定criteria与逐域账目

### S1 · Subject / Identity

**Foundation Definition：**同一主体身份与连续状态跨重启、模型资源替换、受控迁移保持；实例权威所有权清楚。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S1-C01 | 持久 canonical identity；表达修订有版本和来源 | FOUNDATION_QUALIFIED | ID | 身份ID不由模型文本决定。 |
| S1-C02 | 重启、replay、受控fresh-host迁移保持同identity和历史 | FOUNDATION_QUALIFIED | PORT, ID, CDL | 只认受控迁移；副本激活需fencing。 |
| S1-C03 | 单权威Store/SubjectLoop/Runtime owner，旧writer不能继续 | FOUNDATION_QUALIFIED | RUNTIME, CDL | 不声称分布式敌对宿主全局租约合格。 |
| S1-C04 | 模型资源更换不创建第二Subject或迁移旧执行权限 | FOUNDATION_QUALIFIED | PORT, PROVIDER, REGRESSION, MODEL_SWAP | 真实不同provider的广泛对照未完成。 |
| S1-C05 | 来源、关系和权限分离；新宿主撤销旧Grant | FOUNDATION_QUALIFIED | PORT, REL | 迁移包不是宿主凭据备份。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**NO：当前限定基础达标；保留治理门。
- **下一次升级条件：**改变身份/迁移协议时定向复核，不重做未受影响资格。
- **Advanced Future：**异构宿主广泛适配；深层自改后的身份连续性属S10。
- **对应PROJECT_BRAIN决策：**`D-051`、`D-C6B-001`、`D-C6B-002`、`D-C6B-003`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S2 · Memory / Experience

**Foundation Definition：**可信、持续、可追源和纠错的记忆/经历能进入判断，支持删除与迁移。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S2-C01 | 记忆类型、来源、事件时间/观察时间和不确定性可区分 | FOUNDATION_QUALIFIED | MEM | 推断不能冒充原始观察。 |
| S2-C02 | 去重、冲突、纠正、来源撤回有明确状态 | FOUNDATION_QUALIFIED | MEM, WORLD | 新事实不无痕覆盖旧来源。 |
| S2-C03 | 记忆/经历实际改变后续C判断与规划 | FOUNDATION_QUALIFIED | LOOP, LEARN, HANDS | 有反例/撤回对照；不是仅保存文本。 |
| S2-C04 | 隐私分类及删除传播到派生记录、技能、context和迁移 | FOUNDATION_QUALIFIED | MEM, PORT, HANDS, CDL | 本轮不读取私人数据。 |
| S2-C05 | 跨重启、backup/restore与受控迁移保持连续 | FOUNDATION_QUALIFIED | PORT, CDL | 恢复副本不自动取得执行权。 |
| S2-C06 | 工程状态是有来源的外部事实，不冒充个人经历 | FOUNDATION_QUALIFIED | CONTEXT, REGRESSION | 当前状态投影修复仅OFFLINE/FIXTURE资格。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**NO：机制限定基础达标；真实数据接入仍独立授权。
- **下一次升级条件：**改来源、检索、删除或迁移机制时复核相应闭包。
- **Advanced Future：**长期生活史、多模态丰富记忆、更大规模检索；私人Iris迁移单独接线。
- **对应PROJECT_BRAIN决策：**`D-052`、`D-CS-001`、`D-WORLD-002`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S3 · Motivation / Affect / Relationship

**Foundation Definition：**持续需要、兴趣和关系参与取舍，经独立C判断形成行动或休息；经历可改变后来动机倾向且跨重启持续。
**STATUS = FOUNDATION_TESTED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S3-C01 | 内部偏好/需要/关系有持续、可追源状态 | FOUNDATION_TESTED | LOOP, REL | typed qualitative状态；不等于完整人类情绪。 |
| S3-C02 | 非用户命令可产生自主探索/社交等动机 | FOUNDATION_TESTED | LOOP, LIFE, OLDREL | SELF_WAKE不等于无来源随机造欲望。 |
| S3-C03 | 多种需要可取舍；负荷高可REST，不强制学习 | FOUNDATION_QUALIFIED | REL, HANDS, RAE | 受控实测及测试含真实失败后选择REST。 |
| S3-C04 | 关系重要性影响选择，Primary User不是唯一兴趣源 | FOUNDATION_TESTED | REL, OLDREL | anchor消融保留social appetite；自然语言思想开放性未普遍证明。 |
| S3-C05 | C拥有判断；Manager/Grant只限制实际动作且保留愿望 | FOUNDATION_QUALIFIED | AFFECT, HANDS, RAE | blocked与“不想做”分开。 |
| S3-C06 | 来源支持/反证可改变兴趣及后续SELF_WAKE选择 | FOUNDATION_TESTED | LOOP, REL | 现有测试由typed环境PreferenceSignal输入，不能冒充开放自主体验提炼。 |
| S3-C07 | 真实受控Outcome/学习复用能改变后续分享或沉默 | FOUNDATION_QUALIFIED | SHARE, HANDS, RAE | 证明source-backed社会候选，不能直接等同基础情感倾向变化。 |
| S3-C08 | 偏好信号和主体判断可跨重启/真实SIGKILL恢复 | FOUNDATION_TESTED | LOOP, OLDREL | 当前测试支持信号与事务恢复；历史关系专测部分路径已不在当前树。 |
| S3-C09 | 同一真实受控生活链：经历→后来需要/倾向变化→重启保留→自主再选择，含撤回/反例 | UNKNOWN_AUDIT_REQUIRED | LOOP, REL, HANDS, 24H | 没有找到覆盖整条链的当前资格证据；不是宣告机制不存在。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**YES：S3-C09证据缺口阻止S3 Foundation资格；不是已确认重写需求。
- **下一次升级条件：**先复用现有Growth/relational/C/D，补同一lineage的最小非人工偏好注入因果证据；失败再定位实现差额。
- **Advanced Future：**复杂情绪、依恋/幽默/梦想细化和开放关系成长；不能全部变成Foundation前置。
- **对应PROJECT_BRAIN决策：**`D-CV2-001`、`D-AFFECT-003`、`D-AFFECT-005`、`D-AFFECT-006`、`D-C6B-001`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S4 · Runtime / Living Presence

**Foundation Definition：**无输入也可活动和休息，用户可抢占；单writer持续运行并可恢复、控制资源。
**STATUS = FOUNDATION_TESTED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S4-C01 | C WHAT/WHY与D WHEN职责分离，无第二意志loop | FOUNDATION_QUALIFIED | LIFE, RUNTIME, CDL | 调度只提供机会。 |
| S4-C02 | 无用户输入的有限活动、任务结束后休息/等待 | FOUNDATION_QUALIFIED | LIFE, CDL | 两小时finite workload，不是开放终身生活。 |
| S4-C03 | 输入抢占、暂停、恢复不丢目标或重复effect | FOUNDATION_QUALIFIED | RUNTIME, HANDS, CDL | 在明示安全点抢占。 |
| S4-C04 | 实际进程恢复、epoch fencing、UNKNOWN不盲重试 | FOUNDATION_QUALIFIED | RUNTIME, HANDS, PORT | 恢复与动作重新授权分离。 |
| S4-C05 | 资源/存储增长有测量、预算和停止边界 | FOUNDATION_QUALIFIED | CDL, 24H, REGRESSION | 冷历史仍可增长；guard不是无限存储已解决。 |
| S4-C06 | 固定源码实际24h durability与最终结果 | UNKNOWN_AUDIT_REQUIRED | 24H | 仓库快照elapsed36953.176秒、RUNNING_NOT_QUALIFIED；未访问运行宿主，不保证此刻仍存活。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**YES：S4-C06的24h durability资格未完成。
- **下一次升级条件：**等待原固定源码staging实际result；不新开重复soak，不从快照或时间推算PASS。
- **Advanced Future：**长期云端宿主、规模化长期生活、更多Presence接口。
- **对应PROJECT_BRAIN决策：**`D-DV1-001`、`D-D2D7-001`、`D-D2D7-004`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S5 · World / Perception / Cognition

**Foundation Definition：**来源明确的观察经可替换认知资源形成可修正世界理解，再进入同一C；不把sensor/model当意志。
**STATUS = FOUNDATION_TESTED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S5-C01 | 原始观察/模型推断、来源时间和不确定性区分 | FOUNDATION_QUALIFIED | WORLD, MEM | MODEL_DERIVATION不能升格RAW_OBSERVATION。 |
| S5-C02 | 世界信念冲突/修正/时间查询/删除因果正确 | FOUNDATION_QUALIFIED | WORLD, REGRESSION | 既有测试及结果复用。 |
| S5-C03 | 可替换Provider slots/routing，模型不授予authority | FOUNDATION_QUALIFIED | PROVIDER, WORLD | 离线路由资格不等于各slot均有live资格。 |
| S5-C04 | 真实文本INTERPRET+RENDER传输/解析功能成立 | FOUNDATION_QUALIFIED | PROVIDER, CONTEXT | 17次功能资格；后续总19次；自然度未评审、账单UNKNOWN。 |
| S5-C05 | 至少一个真实受控感知入口及源生命周期 | FOUNDATION_QUALIFIED | SCREEN | owned Xorg/XGetImage；当时语义为synthetic loopback。 |
| S5-C06 | 当前lineage真实输入→live语义→World/Concern→C完整组合及纠错 | UNKNOWN_AUDIT_REQUIRED | WORLD, SCREEN, PROVIDER | 不能把不同版本的分项PASS拼成未实际运行的整链；历史H1 PARTIAL保持。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**YES：S5-C06的真实源→真实语义→世界修正→C组合资格待对齐。
- **下一次升级条件：**先检查现有H1/文本/owned ingress能否复用到一个当前受控场景；不再横向堆传感器。
- **Advanced Future：**广泛视频/音频语义、camera/mic、用户桌面OCR及开放世界；不要求全部传感器才基础完成。
- **对应PROJECT_BRAIN决策：**`D-WORLD-006`、`D-H1-001`、`D-H1-LIVE-003`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S6 · Independent Judgment / Problem Framing / Goal / Planning

**Foundation Definition：**C能形成自己的问题判断和目标，区分用户建议、问题与路径；有限规划可验证并按结果调整。
**STATUS = FOUNDATION_TESTED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S6-C01 | 输入/用户建议不直接变成已采纳目标或权限 | FOUNDATION_QUALIFIED | LOOP, AFFECT, PLAN | 候选、adoption、Grant分离。 |
| S6-C02 | 可提出与用户方法不同的有来源替代方案 | FOUNDATION_QUALIFIED | HANDS, LOOP | 真实owned任务历史支持HANDS_REPLACE替代APPEND；限定方法级。 |
| S6-C03 | 多目标、子目标依赖、有限路径与独立计划验证 | FOUNDATION_QUALIFIED | PLAN | 有界uniform-cost与typed operators；不是无限开放推理。 |
| S6-C04 | 实际执行/Verify/失败→Continue/Replan/Stop | FOUNDATION_QUALIFIED | PLAN, RAE, HANDS | 原失败保留。 |
| S6-C05 | 世界修正/学习/来源撤回可改变或暂停计划 | FOUNDATION_QUALIFIED | PLAN, LEARN, HANDS | 不能仅换解释而沿用旧输出。 |
| S6-C06 | 自主目标受Manager/资源约束但不由其生成意志 | FOUNDATION_QUALIFIED | LIFE, HANDS, RAE | REST/NO_ACTION也是有效选择。 |
| S6-C07 | 独立Problem Framing的当前最小因果资格 | UNKNOWN_AUDIT_REQUIRED | HANDS, RAE, PLAN | 方法选择与预定义capability-gap分类已有；尚不能据此宣布问题定义能力完整过门。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**YES：S6-C07的问题定义资格仍不足；不是要求万能planner。
- **下一次升级条件：**沿原C/World/Goal记录补一例有来源的问题重定义、理由与对照；先查既有RAE gap证据，避免重造。
- **Advanced Future：**开放长期复杂规划、研究发现未知方案；不把用户意图设为认知边界。
- **对应PROJECT_BRAIN决策：**`D-E1E6-001`、`RAE final executable guard / typed problem reframing`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S7 · Hands / Action / Verification

**Foundation Definition：**在有限真实环境中，经授权产生可辨认效果，独立验证任务质量并处理失败和未知。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S7-C01 | 真实目标绑定与有限typed动作，不靠模型自述完成 | FOUNDATION_QUALIFIED | HANDS, RAE | 进程身份、scope、revision均受校验。 |
| S7-C02 | Manager/Grant/预算/撤权在effect前生效 | FOUNDATION_QUALIFIED | HANDS, RAE | 授权不由目标、关系或skill生成。 |
| S7-C03 | 真实文件/应用状态与只读Verify独立核对 | FOUNDATION_QUALIFIED | HANDS, RAE | 物理执行成功与任务质量成功分开。 |
| S7-C04 | SIGKILL/并发冲突/UNKNOWN保留，无重复effect | FOUNDATION_QUALIFIED | HANDS, RAE | 六切点及file/IPC不一致反例。 |
| S7-C05 | Outcome进入Experience/学习/后续决策 | FOUNDATION_QUALIFIED | HANDS, RAE, SHARE | 有实际失败、迁移任务和来源撤回。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**NO：有限真实动作基础达标；扩环境另验，不扩权限。
- **下一次升级条件：**新增动作域时增加目标绑定、权限和独立Verify资格。
- **Advanced Future：**浏览器、手机、桌面、游戏、真实平台动作及更复杂环境。
- **对应PROJECT_BRAIN决策：**`D-AFFECT-006`、`RAE-01..13`、`RAE final qualification decision`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S8 · Learning / Self-Evolution — Cross-Domain Growth Engine

**Foundation Definition：**有来源的经历引发可选择的学习，经过baseline/独立评估/迁移/后来复用/反例暂停，改变未来行为。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S8-C01 | 真实失败/能力缺口经C选择学习，也可选择不学/REST | FOUNDATION_QUALIFIED | RAE, HANDS, LEARN | 工程优先级不自动成为奈奈内部最高目的。 |
| S8-C02 | baseline、学习问题和候选变化有来源 | FOUNDATION_QUALIFIED | LEARN, RAE | 有限候选/预写方法，不宣称算法发明。 |
| S8-C03 | 训练/held-out/transfer分离，提议者看不到独立答案 | FOUNDATION_QUALIFIED | LEARN | 评测器当前由可信宿主提供；敌对root不在证明范围。 |
| S8-C04 | before/after和后来不同任务实际复用可核实 | FOUNDATION_QUALIFIED | HANDS, RAE | 开发者修复不计主体学习。 |
| S8-C05 | 负迁移/反例可停用，并阻止旧计划继续用错策略 | FOUNDATION_QUALIFIED | LEARN, HANDS, RAE | 两方法later-use后遭反例停用；不是只留成功。 |
| S8-C06 | 来源删除、重启、成本/资源和回滚合同保留 | FOUNDATION_QUALIFIED | LEARN, HANDS, CDL | 观察资源/预算不等于真实provider账单。 |
| S8-C07 | 成长能够进入其他域的后续行为而不是孤立lesson | FOUNDATION_QUALIFIED | SHARE, LEARN, RAE | 已覆盖规划/动作/分享；不由此推定全域或深层机制演化合格。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**NO：受限成长引擎基础达标；S3倾向闭环仍由S3-C09独立核验。
- **下一次升级条件：**按具体域缺口扩展同一G/I，不把学习设为永久最高动机。
- **Advanced Future：**长期开放学习、元学习、认知/规划/学习算法改变；深层改变进入S10。
- **对应PROJECT_BRAIN决策：**`D-E1E6-003`、`RAE-00`、`LIVED_GROWTH_V2 — failed novel use is counterevidence`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S9 · Self-Extension

**Foundation Definition：**能力不足经同一C形成扩展候选，在隔离环境测试、采用、真实复用，并可撤回。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S9-C01 | 实际能力缺口→C SEEK_CAPABILITY→原I工作 | FOUNDATION_QUALIFIED | RAE, SKILL | 缺口分类有限，不等于开放技术研究。 |
| S9-C02 | 候选实现/失败修复有版本与来源 | FOUNDATION_QUALIFIED | SKILL, RAE | FixtureCodeProposer/确定性编译器边界明确。 |
| S9-C03 | 真实sandbox、独立测试与digest-bound review | FOUNDATION_QUALIFIED | SKILL, RAE | 无网络、无任意宿主文件/安装权限。 |
| S9-C04 | 受限采用不创造新Grant，换realm需重新review | FOUNDATION_QUALIFIED | SKILL, PORT | portable skill record不等于可执行权限。 |
| S9-C05 | 原Kernel至少两次真实任务复用 | FOUNDATION_QUALIFIED | RAE, HANDS | 批量表单与不同context，非仅测试函数返回值。 |
| S9-C06 | 退役、来源撤回、恢复后不复活失效技能 | FOUNDATION_QUALIFIED | SKILL, HANDS, CDL | 不能由投影或缓存恢复权限。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**NO：受限自扩展基础达标；不授予安装或Core改写权。
- **下一次升级条件：**确有新能力缺口时沿原I逐步扩大候选空间与环境资格。
- **Advanced Future：**开放研究、任意复杂插件/适配器创造与安装、依赖管理。
- **对应PROJECT_BRAIN决策：**`D-E1E6-004`、`LIVED_GROWTH_V2 — document grammar and skill adaptation boundary`、`RAE-01..13`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S10 · Lineage / Deep Evolution

**Foundation Definition：**深层变化保留谁在改变、如何验证、如何退回的谱系；候选不能控制其唯一裁判。
**STATUS = FOUNDATION_PARTIAL**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S10-C01 | 现有identity/策略/技能修订有来源和版本 | FOUNDATION_QUALIFIED | ID, SKILL, PORT | 这是受限谱系，不是所有Core自改的archive。 |
| S10-C02 | 迁移前退役源、新epoch、旧Grant撤销 | FOUNDATION_QUALIFIED | PORT, CDL | 受控单活迁移，不声称敌对多宿主同步。 |
| S10-C03 | 恢复/回滚不清掉UNKNOWN或复活删除来源 | FOUNDATION_QUALIFIED | PORT, HANDS, CDL | 旧源未fenced时不能自动提升备份writer。 |
| S10-C04 | 候选学习/技能不接触自己的独立held-out评测答案 | FOUNDATION_QUALIFIED | LEARN, SKILL | 当前可信宿主隔离合同，非通用深层裁判自演化。 |
| S10-C05 | 深层Core候选Branch Before Replace及独立评测/回滚 | UNKNOWN_AUDIT_REQUIRED | PORT, SKILL | 受限skill机制不能自动证明Core深改；未来触发条件未运行。 |
| S10-C06 | 验证底座自身演化由旧可信版本验证新版本 | UNKNOWN_AUDIT_REQUIRED | ID, PORT | 规范已冻结，未取得深层实现资格；不冒称已完成。 |

- **已实现/已测/已运行：**按上表来源和范围；TESTED仅到测试，QUALIFIED仅到所列场景；UNKNOWN项不冒充已通过。
- **当前blocker / First-Life：**NO：深层实现不阻塞当前First-Life；当前适用连续性/治理约束仍在S1/S7/S8/S9必验。
- **下一次升级条件：**仅在确有深层变更任务时进入S10专门资格，不为当前封基础而先造大框架。
- **Advanced Future：**更开放Core/内部算法自修改、候选archive/canary、验证底座自身演化。
- **对应PROJECT_BRAIN决策：**`D-C6B-002`、`D-D2D7-006`、`D-E1E6-004`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

## 4. 三横轴的当前资格

| 轴 | 已有基础 | 待核验/未来 | 对当前Gate的影响 |
|---|---|---|---|
| Shared Life / Companionship | 关系影响、来源绑定分享/沉默、忙碌/拒绝与删除反例（REL/SHARE/HANDS） | 真正长期相处质量未评审；S3内在倾向的持续闭环未知 | S3-C09先补证；真人评审暂停，不能替代基础审计。 |
| Platform / Surface / Embodied Presence | One Subject；Event-First L0/L1/L2与QQ/Bili开发shadow、受控Hands（CDL/PORT） | 实际账号统一接线、phone/desktop/game/voice/avatar等扩展 | 不要求所有设备前置；真实绑定和动作按具体范围另验。 |
| Manager / Authority / Privacy / Recovery | 愿望与权限分离、Grant撤销、来源删除、UNKNOWN、迁移恢复（AFFECT/HANDS/PORT） | 分布式敌对宿主与深层自改验证底座未合格 | 当前适用治理约束持续必验；S10远期能力不因此被提前宣称完成。 |

## 5. 有界缺口清单与下一任务

| ID | 归属 | 缺口类型 | 是否确认实现缺失 | 下一最小动作 / 完成条件 |
|---|---|---|---|---|
| FQ-01 | S3-C09 | QUALIFICATION_GAP | 否；UNKNOWN | 对照现有Growth/relational/C/D与真实Outcome路径，验证同一lineage经历改变后来动机倾向、重启保留、再次自主选择；含撤回/反例。先核现有可用证据，有真实差额才补源码。 |
| FQ-02 | S4-C06 | DURATION_QUALIFICATION_PENDING | 否 | 等原24h固定源码run实际结果；不重跑/重启，不以36953秒快照或当前时间推算成功。 |
| FQ-03 | S5-C06 | INTEGRATED_SEMANTIC_EVIDENCE_GAP | 否；UNKNOWN | 先对齐历史H1、当前文本Provider与owned source的版本和路径；满足真实源→语义→世界修正→C的一例最小组合，保留错误/UNKNOWN。若需新增付费，仍按当时授权，不在本任务调用。 |
| FQ-04 | S6-C07 | PROBLEM_FRAMING_QUALIFICATION_GAP | 否；UNKNOWN | 检查原RAE capability-gap与typed reframe是否已有问题级证据；明确“问题改变”与“选另一个方法”的区别，只补缺失反例/归因。 |
| AG-10 | S10-C05/C06 | ADVANCED_GROWTH | 当前不启动 | 深层自改触发时再做branch/evaluator/lineage专门资格；不阻塞当前基础封顶。 |

下一有界工作以FQ-01为首项；FQ-04复用同一因果证据检查。FQ-02保持原run独立等待；FQ-03先做资料差额对齐。不存在在核账之外新增一套情感引擎、第二记忆系统或大规模框架的授权。

**审计终点已达到：**十域均有固定criteria、状态、实现/测试/证据映射、未知和升级条件。本轮核账完成，不要求所有未知都在同一审计内变成PASS；后续仅关闭上述具体缺口。只有证实 `FOUNDATION_MISSING + CURRENT_GATE_BLOCKER` 才因新发现改变实施主线。

## 6. First-Life门与保留证据

- Foundation Gate：S1–S9均须FOUNDATION_QUALIFIED，当前未达到；本表不自动升级Beta。
- First-Life Integration Gate：之后验证同一实例的组合运行、恢复、长期驻留与适用的人机相处；已有技术证据保留，缺项按当时适用资格补齐。
- DeepSeek：功能资格文件记录17次；随后真人样本增加2次，当前累计19次，最后1次冻结；保守预留0.95USD不是账单。历史TianToken UNKNOWN保持PARKED。
- 当前真人样本因context/intent链路缺陷排除；修复只有OFFLINE/FIXTURE证据，不据此判用户表达、模型自然度或S3缺失。
- 24h仓库最新已读快照：36953.176245105秒，RUNNING_NOT_QUALIFIED，provider0、social0；该文件不是live进程探测。
- 旧07/08/09中“下一步真人评审/新小额预算”等任务安排由本轮用户冻结指令暂缓；历史发生事实、预算消耗和原资格不改写。

## 7. 证据索引（路径均按审计基线检查）

索引中的源码/测试定义均为当前基线阅读对象；资格文件为历史运行结果。本轮执行范围仅文档校验。

### ID

- [src/nana_core/continuity/identity.py](../src/nana_core/continuity/identity.py)
- [tests/continuous_self/test_identity.py](../tests/continuous_self/test_identity.py)

### PORT

- [tests/portable_subject/test_package.py](../tests/portable_subject/test_package.py)
- [docs/nana_cloud_daily_life_shared_presence_v1_evidence/portability.json](../docs/nana_cloud_daily_life_shared_presence_v1_evidence/portability.json)

### MEM

- [src/nana_core/continuity/memory.py](../src/nana_core/continuity/memory.py)
- [src/nana_core/continuity/records.py](../src/nana_core/continuity/records.py)
- [tests/continuous_self/test_memory.py](../tests/continuous_self/test_memory.py)

### LOOP

- [src/nana_core/continuity/subject/policy.py](../src/nana_core/continuity/subject/policy.py)
- [tests/continuous_self/test_subject_loop.py](../tests/continuous_self/test_subject_loop.py)
- [tests/continuous_self/test_subject_life.py](../tests/continuous_self/test_subject_life.py)

### REL

- [src/nana_core/continuity/relational/projections.py](../src/nana_core/continuity/relational/projections.py)
- [src/nana_core/continuity/relational/deliberation.py](../src/nana_core/continuity/relational/deliberation.py)
- [tests/portable_subject/test_relational_reuse.py](../tests/portable_subject/test_relational_reuse.py)

### AFFECT

- [tests/affective_autonomy/test_dispositions.py](../tests/affective_autonomy/test_dispositions.py)
- [tests/affective_autonomy/test_experience.py](../tests/affective_autonomy/test_experience.py)
- [docs/nana_affective_autonomy_v1_evidence/scenario_matrix.json](../docs/nana_affective_autonomy_v1_evidence/scenario_matrix.json)

### OLDREL

- [docs/nana_relational_autonomy_v1_evidence/social_appetite_ablation.json](../docs/nana_relational_autonomy_v1_evidence/social_appetite_ablation.json)
- [docs/nana_relational_autonomy_v1_evidence/recovery_matrix.json](../docs/nana_relational_autonomy_v1_evidence/recovery_matrix.json)
- [docs/nana_relational_autonomy_v1_evidence/targeted_tests.xml](../docs/nana_relational_autonomy_v1_evidence/targeted_tests.xml)

### LIFE

- [src/nana_core/presence/living.py](../src/nana_core/presence/living.py)
- [tests/living_autonomy/test_agency.py](../tests/living_autonomy/test_agency.py)
- [tests/living_autonomy/test_recovery_migration.py](../tests/living_autonomy/test_recovery_migration.py)

### RUNTIME

- [src/nana_core/presence/authority.py](../src/nana_core/presence/authority.py)
- [src/nana_core/presence/cadence.py](../src/nana_core/presence/cadence.py)
- [tests/living_autonomy/test_cadence.py](../tests/living_autonomy/test_cadence.py)
- [tests/continuous_runtime/test_system_qualification.py](../tests/continuous_runtime/test_system_qualification.py)

### CDL

- [docs/nana_cloud_daily_life_shared_presence_v1_evidence/qualification.json](../docs/nana_cloud_daily_life_shared_presence_v1_evidence/qualification.json)
- [docs/nana_cloud_daily_life_shared_presence_v1_evidence/portability.json](../docs/nana_cloud_daily_life_shared_presence_v1_evidence/portability.json)

### 24H

- [docs/nana_cloud_first_life_launch_v1_evidence/context_repair_staging_observation.json](../docs/nana_cloud_first_life_launch_v1_evidence/context_repair_staging_observation.json)

### WORLD

- [src/nana_core/continuity/world_loop/world.py](../src/nana_core/continuity/world_loop/world.py)
- [tests/world_loop/test_foundation.py](../tests/world_loop/test_foundation.py)
- [docs/nana_real_cognition_world_loop_v1_evidence/qualification.json](../docs/nana_real_cognition_world_loop_v1_evidence/qualification.json)

### SCREEN

- [docs/nana_h2_live_real_screen_v1_evidence/qualification.json](../docs/nana_h2_live_real_screen_v1_evidence/qualification.json)

### PROVIDER

- [docs/nana_provider_capability_routing_v1_evidence/qualification.json](../docs/nana_provider_capability_routing_v1_evidence/qualification.json)
- [docs/nana_cloud_first_life_launch_v1_evidence/deepseek_functional_qualification.json](../docs/nana_cloud_first_life_launch_v1_evidence/deepseek_functional_qualification.json)

### CONTEXT

- [src/nana_core/continuity/current_state.py](../src/nana_core/continuity/current_state.py)
- [docs/nana_cloud_first_life_launch_v1_evidence/human_review_context_repair.json](../docs/nana_cloud_first_life_launch_v1_evidence/human_review_context_repair.json)

### PLAN

- [src/nana_core/continuity/open_agency/planning.py](../src/nana_core/continuity/open_agency/planning.py)
- [tests/open_autonomy/test_planning.py](../tests/open_autonomy/test_planning.py)

### HANDS

- [src/nana_core/continuity/hands/contracts.py](../src/nana_core/continuity/hands/contracts.py)
- [tests/controlled_hands/test_application.py](../tests/controlled_hands/test_application.py)
- [tests/controlled_hands/test_boundaries.py](../tests/controlled_hands/test_boundaries.py)
- [tests/controlled_hands/test_recovery.py](../tests/controlled_hands/test_recovery.py)

### RAE

- [docs/nana_real_action_experience_evolution_v1_evidence/qualification.json](../docs/nana_real_action_experience_evolution_v1_evidence/qualification.json)
- [docs/nana_real_action_experience_evolution_v1_evidence/self_extension.json](../docs/nana_real_action_experience_evolution_v1_evidence/self_extension.json)

### LEARN

- [src/nana_core/continuity/open_agency/learning.py](../src/nana_core/continuity/open_agency/learning.py)
- [tests/open_autonomy/test_learning.py](../tests/open_autonomy/test_learning.py)
- [tests/vision_first/test_growth.py](../tests/vision_first/test_growth.py)

### SKILL

- [src/nana_core/continuity/open_agency/code_skills.py](../src/nana_core/continuity/open_agency/code_skills.py)
- [tests/open_autonomy/test_code_skills.py](../tests/open_autonomy/test_code_skills.py)
- [docs/nana_e1e6_open_autonomy_v1_evidence/qualification.json](../docs/nana_e1e6_open_autonomy_v1_evidence/qualification.json)

### SHARE

- [src/nana_core/continuity/subject/growth_life.py](../src/nana_core/continuity/subject/growth_life.py)
- [tests/controlled_hands/test_boundaries.py](../tests/controlled_hands/test_boundaries.py)
- [docs/nana_vision_first_shared_growth_v2_evidence/life_causal_change.json](../docs/nana_vision_first_shared_growth_v2_evidence/life_causal_change.json)

### REGRESSION

- [docs/nana_cloud_first_life_launch_v1_evidence/context_repair_test_summary.txt](../docs/nana_cloud_first_life_launch_v1_evidence/context_repair_test_summary.txt)

### MODEL_SWAP

- [tests/cloud_life/test_model_swap.py](../tests/cloud_life/test_model_swap.py)
- [tests/portable_subject/test_providers_frontend.py](../tests/portable_subject/test_providers_frontend.py)

## 8. 历史覆盖与维护规则

历史 relational_autonomy XML 中部分 `tests/relational_autonomy/...` 路径已不在当前树；它们仍是历史证据，不伪装成当前可运行命令。当前复用测试包括 `tests/portable_subject/test_relational_reuse.py`、continuous_self 与affective_autonomy系列。S3更强的完整资格保留UNKNOWN，避免仅凭旧READY升级。

修改Matrix须列criterion ID、旧→新状态、对应源码/证据commit、环境/时长/数据范围、反例和下一条件。不得为通过Gate临时删criteria，不把一般Advanced功能塞回Foundation。

本表的Foundation criteria版本1.0是首次冻结愿景到可验证条件的操作化；以后若条件本身不合理，显式记录标准修订及原结果，而不是追改旧证据。宪法仍仅按三项Change-Control门槛修订。
