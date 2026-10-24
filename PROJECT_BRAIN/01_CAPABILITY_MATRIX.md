# Nana Core · Foundation Capability Matrix

版本：1.0 · 证据复核revision 4（固定63条criteria不变） · 首次冻结后Foundation收口 · 2026-10-21任务（Asia/Shanghai）
规范：[00_MASTER_FRAMEWORK.md](00_MASTER_FRAMEWORK.md) · 当前任务：[09_STATE.md](09_STATE.md)  
审计基线：`eece7a469a5af8a9df5731367e5b7db046039a23`，开发分支 `dev/nana-core-cloud-first-life-launch-v1-codex`。

本轮当前增量：CLOSURE。S3-C09和S6-C07已资格；S5-C06已完成单次新授权live组合，原S4实际24h最终结果已完整核验，S1–S9基础资格闭合，历史审计排序保留在下文。实现/测试范围详见收口报告，不再将本轮称为文档只读核账。

## 1. 口径与审计边界

[历史edda审计范围；本轮实施范围见CLOSURE] 初次af52371已冻结框架与63条criteria；本次快进继承并独立复核，不另立矩阵、不更改criteria分母。逐条结果可见[机器可读核账记录](../docs/nana_master_framework_foundation_audit_v1_evidence/audit.json)。初审未运行应用测试；独立复核实际执行21项当前tracked、18项历史测试快照对当前Core、6项边界测试及offline probe，并只读staging进度。不调用模型、不读取私人历史、不改运行配置或生产。

[历史实测证据复用] 既有真实进程/受控OS效果与虚拟/fixture资格按原范围保留；最近全仓记录为1300 passed /12 skipped，见REGRESSION。此数字不是本轮运行，不把E12或opt-in screen跳过项写成新通过。

`FOUNDATION_QUALIFIED` 在本表仅指固定criteria在指定开发范围内合格，不表示生产、通用智能、真人相处或开放终身成长资格。测试与资格材料不是外部独立认证。

所有criteria状态使用宪法七级词表。UNKNOWN表示证据不足；不得推成NOT_STARTED或必须重写。域汇总是对完整闭环的判断，不是行数平均；每条未知必须列明升级条件。`growth_status=ADVANCED_GROWTH` 表示未来扩展归属，不表示扩展已经实现。

## 2. 总览

| DOMAIN | STATUS | PASSED CRITERIA（资格） | OPEN FOUNDATION CRITERIA | ADVANCED FUTURE | FIRST-LIFE BLOCKER | PRIMARY EVIDENCE |
|---|---|---|---|---|---|---|
| S1 Subject / Identity | FOUNDATION_QUALIFIED | 5/5；C01,C02,C03,C04,C05 | 无 | 异构宿主广泛适配；深层自改后的身份连续性属S10。 | NO：当前限定基础达标；保留治理门。 | CDL,ID,MODEL_SWAP,PORT,PROVIDER,REGRESSION,REL,RUNTIME |
| S2 Memory / Experience | FOUNDATION_QUALIFIED | 6/6；C01,C02,C03,C04,C05,C06 | 无 | 长期生活史、多模态丰富记忆、更大规模检索；私人Iris迁移单独接线。 | NO：机制限定基础达标；真实数据接入仍独立授权。 | CDL,CONTEXT,HANDS,LEARN,LOOP,MEM,PORT,REGRESSION,WORLD |
| S3 Motivation / Affect / Relationship | FOUNDATION_QUALIFIED | 9/9；C01,C02,C03,C04,C05,C06,C07,C08,C09 | 无 | 复杂情绪、依恋/幽默/梦想细化和开放关系成长；不能全部变成Foundation前置。 | NO：S3-C09受控真实经历链已资格；更广情感开放成长属Advanced。 | CLOSURE及原证据 |
| S4 Runtime / Living Presence | FOUNDATION_QUALIFIED | 6/6；C01,C02,C03,C04,C05,C06 | 无 | 长期云端宿主、规模化长期生活、更多Presence接口。 | NO：原固定源码24h最终结果已完整核验；真人评审与First-Life组合资格另行完成。 | 24H,CDL,HANDS,LIFE,PORT,REGRESSION,RUNTIME |
| S5 World / Perception / Cognition | FOUNDATION_QUALIFIED | 6/6；C01,C02,C03,C04,C05,C06 | 无 | 广泛视频/音频语义、camera/mic、用户桌面OCR及开放世界；不要求全部传感器才基础完成。 | NO：S5基础组合已资格；S1–S9基础资格已闭合。 | CONTEXT,MEM,PROVIDER,REGRESSION,SCREEN,WORLD |
| S6 Independent Judgment / Problem Framing / Goal / Planning | FOUNDATION_QUALIFIED | 7/7；C01,C02,C03,C04,C05,C06,C07 | 无 | 开放长期复杂规划、研究发现未知方案；不把用户意图设为认知边界。 | NO：S6-C07已在有限有源候选空间受控资格；开放研究与任意问题发现为Advanced。 | CLOSURE及原证据 |
| S7 Hands / Action / Verification | FOUNDATION_QUALIFIED | 5/5；C01,C02,C03,C04,C05 | 无 | 浏览器、手机、桌面、游戏、真实平台动作及更复杂环境。 | NO：有限真实动作基础达标；扩环境另验，不扩权限。 | HANDS,RAE,SHARE |
| S8 Learning / Self-Evolution — Cross-Domain Growth Engine | FOUNDATION_QUALIFIED | 7/7；C01,C02,C03,C04,C05,C06,C07 | 无 | 长期开放学习、元学习、认知/规划/学习算法改变；深层改变进入S10。 | NO：受限成长引擎基础达标；S3倾向闭环仍由S3-C09独立核验。 | CDL,HANDS,LEARN,RAE,SHARE |
| S9 Self-Extension | FOUNDATION_QUALIFIED | 6/6；C01,C02,C03,C04,C05,C06 | 无 | 开放研究、任意复杂插件/适配器创造与安装、依赖管理。 | NO：受限自扩展基础达标；不授予安装或Core改写权。 | CDL,HANDS,PORT,RAE,SKILL |
| S10 Lineage / Deep Evolution | FOUNDATION_PARTIAL | 4/6；C01,C02,C03,C04 | C05:UNKNOWN_AUDIT_REQUIRED; C06:UNKNOWN_AUDIT_REQUIRED | 更开放Core/内部算法自修改、候选archive/canary、验证底座自身演化。 | NO：深层实现不阻塞当前First-Life；当前适用连续性/治理约束仍在S1/S7/S8/S9必验。 | CDL,HANDS,ID,LEARN,PORT,SKILL |

当前结论：S1–S9在明示受控范围全部Foundation Qualified；固定63项中61项已资格，S10-C05/C06两项高级深改仍未知且非First-Life基础前置。Foundation closure完成；First-Life组合资格、真人自然度及Beta仍未完成。

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

- **Existing Implementation：**IdentityService / ContinuityStore / SubjectPackageService / RuntimeLease；host config独立。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**真实本地顺序owner交接epochs2→3→4、同identity、旧writer拒绝；开发fresh-host transfer，非production迁移。
- **Missing Foundation：**限定受控身份/迁移Definition内无已确认缺失；分布式恶意clone不在当前资格。
- **对应源码：**[src/nana_core/continuity/identity.py](../src/nana_core/continuity/identity.py)；[src/nana_core/continuity/store.py](../src/nana_core/continuity/store.py)；[src/nana_core/continuity/portable.py](../src/nana_core/continuity/portable.py)；[src/nana_core/presence/authority.py](../src/nana_core/presence/authority.py)
- **对应当前tests：**[tests/continuous_self/test_identity.py](../tests/continuous_self/test_identity.py)；[tests/continuous_self/test_candidate.py](../tests/continuous_self/test_candidate.py)；[tests/portable_subject/test_package.py](../tests/portable_subject/test_package.py)；[tests/first_life/test_rehearsal.py](../tests/first_life/test_rehearsal.py)
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

- **Existing Implementation：**MemoryService/RecordService/PrivacyJournal/TemporalMemoryService/ExperienceService；Journal/context是派生视图。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**合成资料真实本地恢复、隐私journal和受控owned应用的实际Outcome→Experience；未读取Iris私人历史。
- **Missing Foundation：**限定来源/记忆闭包内无已确认缺失；真实私人历史接入、长期检索质量未资格，不推定机制缺失。
- **对应源码：**[src/nana_core/continuity/memory.py](../src/nana_core/continuity/memory.py)；[src/nana_core/continuity/records.py](../src/nana_core/continuity/records.py)；[src/nana_core/continuity/privacy.py](../src/nana_core/continuity/privacy.py)；[src/nana_core/continuity/temporal.py](../src/nana_core/continuity/temporal.py)；[src/nana_core/continuity/learning.py](../src/nana_core/continuity/learning.py)；[src/nana_core/continuity/context.py](../src/nana_core/continuity/context.py)
- **对应当前tests：**[tests/continuous_self/test_memory.py](../tests/continuous_self/test_memory.py)；[tests/continuous_self/test_privacy.py](../tests/continuous_self/test_privacy.py)；[tests/continuous_self/test_learning.py](../tests/continuous_self/test_learning.py)；[tests/living_autonomy/test_maintenance.py](../tests/living_autonomy/test_maintenance.py)；[tests/cloud_life/test_operations.py](../tests/cloud_life/test_operations.py)
- **当前blocker / First-Life：**NO：机制限定基础达标；真实数据接入仍独立授权。
- **下一次升级条件：**改来源、检索、删除或迁移机制时复核相应闭包。
- **Advanced Future：**长期生活史、多模态丰富记忆、更大规模检索；私人Iris迁移单独接线。
- **对应PROJECT_BRAIN决策：**`D-052`、`D-CS-001`、`D-WORLD-002`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S3 · Motivation / Affect / Relationship

**Foundation Definition：**持续需要、兴趣和关系参与取舍，经独立C判断形成行动或休息；经历可改变后来动机倾向且跨重启持续。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S3-C01 | 内部偏好/需要/关系有持续、可追源状态 | FOUNDATION_QUALIFIED | LOOP, REL, RECHECK | typed qualitative状态；不等于完整人类情绪。 独立复核：当前Core对历史Git测试快照18 PASS（含90虚拟天/7实际SIGKILL），另当前tracked因果目标测试21 PASS；仅上述范围，不填S3-C09。 |
| S3-C02 | 非用户命令可产生自主探索/社交等动机 | FOUNDATION_QUALIFIED | LOOP, LIFE, OLDREL, RECHECK | SELF_WAKE不等于无来源随机造欲望。 独立复核：当前Core对历史Git测试快照18 PASS（含90虚拟天/7实际SIGKILL），另当前tracked因果目标测试21 PASS；仅上述范围，不填S3-C09。 |
| S3-C03 | 多种需要可取舍；负荷高可REST，不强制学习 | FOUNDATION_QUALIFIED | REL, HANDS, RAE | 受控实测及测试含真实失败后选择REST。 |
| S3-C04 | 关系重要性影响选择，Primary User不是唯一兴趣源 | FOUNDATION_QUALIFIED | REL, OLDREL, RECHECK | anchor消融保留social appetite；自然语言思想开放性未普遍证明。 独立复核：当前Core对历史Git测试快照18 PASS（含90虚拟天/7实际SIGKILL），另当前tracked因果目标测试21 PASS；仅上述范围，不填S3-C09。 |
| S3-C05 | C拥有判断；Manager/Grant只限制实际动作且保留愿望 | FOUNDATION_QUALIFIED | AFFECT, HANDS, RAE | blocked与“不想做”分开。 |
| S3-C06 | 来源支持/反证可改变兴趣及后续SELF_WAKE选择 | FOUNDATION_QUALIFIED | LOOP, REL, RECHECK | 现有测试由typed环境PreferenceSignal输入，不能冒充开放自主体验提炼。 独立复核：当前Core对历史Git测试快照18 PASS（含90虚拟天/7实际SIGKILL），另当前tracked因果目标测试21 PASS；仅上述范围，不填S3-C09。 |
| S3-C07 | 真实受控Outcome/学习复用能改变后续分享或沉默 | FOUNDATION_QUALIFIED | SHARE, HANDS, RAE | 证明source-backed社会候选，不能直接等同基础情感倾向变化。 |
| S3-C08 | 偏好信号和主体判断可跨重启/真实SIGKILL恢复 | FOUNDATION_QUALIFIED | LOOP, OLDREL, RECHECK | 当前测试支持信号与事务恢复；历史关系专测部分路径已不在当前树。 独立复核：当前Core对历史Git测试快照18 PASS（含90虚拟天/7实际SIGKILL），另当前tracked因果目标测试21 PASS；仅上述范围，不填S3-C09。 |
| S3-C09 | 同一真实受控生活链：经历→后来需要/倾向变化→重启保留→自主再选择，含撤回/反例 | FOUNDATION_QUALIFIED | LOOP, REL, HANDS, 24H, CLOSURE | 实际owned app失败→Experience→OPEN/LEARN→独立真实复用→SETTLED/WATCH→SIGKILL/replay/再选择；受控反例→OPEN，实际来源撤回→UNKNOWN。无PreferenceSignal/affect分数/identity改写。 |

- **Existing Implementation：**Appraisal/Motivation/ConcernCue、social_appetite、relationship_influence、Growth、原C lexicographic policy与relational deliberate。motivate输出元组主要为审计描述；实际竞争由相同来源的Situation字段和C分支完成，不冒称通用motive优化器。 本轮闭环：受限competence need由实际失败Experience和独立后续复用派生，跨实际SIGKILL后再选择；反例/撤回改变未来需要，不人工注入偏好。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**原60/90虚拟天与7 SIGKILL历史资格保留；本轮增加真实owned失败/复用→需要改变、实际SIGKILL后同cycle再选择和撤回/反例，见CLOSURE。不是真人情感或真实社交资格。
- **Missing Foundation：**限定Foundation内无已确认待补机制；本轮CLOSURE关闭本域最后一条资格，不宣称Advanced完成。
- **对应源码：**[src/nana_core/continuity/subject/policy.py](../src/nana_core/continuity/subject/policy.py)；[src/nana_core/continuity/subject/loop.py](../src/nana_core/continuity/subject/loop.py)；[src/nana_core/continuity/subject/growth.py](../src/nana_core/continuity/subject/growth.py)；[src/nana_core/continuity/subject/projections.py](../src/nana_core/continuity/subject/projections.py)；[src/nana_core/continuity/relational/projections.py](../src/nana_core/continuity/relational/projections.py)；[src/nana_core/continuity/relational/deliberation.py](../src/nana_core/continuity/relational/deliberation.py)；[src/nana_core/continuity/autonomy/governance.py](../src/nana_core/continuity/autonomy/governance.py)
- **对应当前tests：**[tests/continuous_self/test_subject_life.py](../tests/continuous_self/test_subject_life.py)；[tests/continuous_runtime/test_generic_subject.py](../tests/continuous_runtime/test_generic_subject.py)；[tests/portable_subject/test_relational_reuse.py](../tests/portable_subject/test_relational_reuse.py)；[tests/affective_autonomy/test_governance.py](../tests/affective_autonomy/test_governance.py)
- **当前blocker / First-Life：**NO：S3-C09受控真实经历链已资格；更广情感开放成长属Advanced。
- **下一次升级条件：**按真实新增经历扩展需要类型；不新造第二affect系统。
- **Advanced Future：**复杂情绪、依恋/幽默/梦想细化和开放关系成长；不能全部变成Foundation前置。
- **对应PROJECT_BRAIN决策：**`D-CV2-001`、`D-AFFECT-003`、`D-AFFECT-005`、`D-AFFECT-006`、`D-C6B-001`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。
### S4 · Runtime / Living Presence

**Foundation Definition：**无输入也可活动和休息，用户可抢占；单writer持续运行并可恢复、控制资源。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S4-C01 | C WHAT/WHY与D WHEN职责分离，无第二意志loop | FOUNDATION_QUALIFIED | LIFE, RUNTIME, CDL | 调度只提供机会。 |
| S4-C02 | 无用户输入的有限活动、任务结束后休息/等待 | FOUNDATION_QUALIFIED | LIFE, CDL | 两小时finite workload，不是开放终身生活。 |
| S4-C03 | 输入抢占、暂停、恢复不丢目标或重复effect | FOUNDATION_QUALIFIED | RUNTIME, HANDS, CDL | 在明示安全点抢占。 |
| S4-C04 | 实际进程恢复、epoch fencing、UNKNOWN不盲重试 | FOUNDATION_QUALIFIED | RUNTIME, HANDS, PORT | 恢复与动作重新授权分离。 |
| S4-C05 | 资源/存储增长有测量、预算和停止边界 | FOUNDATION_QUALIFIED | CDL, 24H, REGRESSION | 冷历史仍可增长；guard不是无限存储已解决。 |
| S4-C06 | 固定源码实际24h durability与最终结果 | FOUNDATION_QUALIFIED | 24H, CLOSURE, S4_FINAL | 原固定645899b实际86405.272秒/exit0；源码205文件+supervisor、DB/FK、单owner、队列、幂等及SIGKILL恢复通过；不是当前代码24h或生产资格。 |

- **Existing Implementation：**原NanaRuntime/lease/queue/scheduler/cadence/cognition coordinator，host-local growth guard。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**原固定645899b实际86405.272秒开发驻留；最终退出0、源码/资源/DB/恢复/迁移与effect独立只读核验通过；非生产或当前最新源码24h资格。
- **Missing Foundation：**无当前已确认Foundation缺口；原24h实际结果与最终DB核验已通过。
- **对应源码：**[src/nana_core/presence/runtime.py](../src/nana_core/presence/runtime.py)；[src/nana_core/presence/authority.py](../src/nana_core/presence/authority.py)；[src/nana_core/presence/queue.py](../src/nana_core/presence/queue.py)；[src/nana_core/presence/scheduler.py](../src/nana_core/presence/scheduler.py)；[src/nana_core/presence/cadence.py](../src/nana_core/presence/cadence.py)；[src/nana_core/presence/resources.py](../src/nana_core/presence/resources.py)；[src/nana_core/life/durability.py](../src/nana_core/life/durability.py)
- **对应当前tests：**[tests/continuous_runtime/test_storage_runtime.py](../tests/continuous_runtime/test_storage_runtime.py)；[tests/living_autonomy/test_cadence.py](../tests/living_autonomy/test_cadence.py)；[tests/living_autonomy/test_recovery_migration.py](../tests/living_autonomy/test_recovery_migration.py)；[tests/first_life/test_durability.py](../tests/first_life/test_durability.py)
- **当前blocker / First-Life：**NO：原固定源码24h最终结果已完整核验；真人评审与First-Life组合资格另行完成。
- **下一次升级条件：**Foundation已资格；长期真实云宿主与真人Shared Life属于后续独立集成/高级资格。
- **Advanced Future：**长期云端宿主、规模化长期生活、更多Presence接口。
- **对应PROJECT_BRAIN决策：**`D-DV1-001`、`D-D2D7-001`、`D-D2D7-004`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S5 · World / Perception / Cognition

**Foundation Definition：**来源明确的观察经可替换认知资源形成可修正世界理解，再进入同一C；不把sensor/model当意志。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S5-C01 | 原始观察/模型推断、来源时间和不确定性区分 | FOUNDATION_QUALIFIED | WORLD, MEM | MODEL_DERIVATION不能升格RAW_OBSERVATION。 |
| S5-C02 | 世界信念冲突/修正/时间查询/删除因果正确 | FOUNDATION_QUALIFIED | WORLD, REGRESSION | 既有测试及结果复用。 |
| S5-C03 | 可替换Provider slots/routing，模型不授予authority | FOUNDATION_QUALIFIED | PROVIDER, WORLD | 离线路由资格不等于各slot均有live资格。 |
| S5-C04 | 真实文本INTERPRET+RENDER传输/解析功能成立 | FOUNDATION_QUALIFIED | PROVIDER, CONTEXT | 17次功能资格；后续总19次；自然度未评审、账单UNKNOWN。 |
| S5-C05 | 至少一个真实受控感知入口及源生命周期 | FOUNDATION_QUALIFIED | SCREEN | owned Xorg/XGetImage；当时语义为synthetic loopback。 |
| S5-C06 | 当前lineage真实输入→live语义→World/Concern→C完整组合及纠错 | FOUNDATION_QUALIFIED | WORLD, PROVIDER, CLOSURE, S5_LIVE | 同一原lineage实际PROJECT文本→live语义→World/Concern→C；实际source撤回令World UNKNOWN、C NO_ACTION；不推广全媒体/真人自然度，H1 PARTIAL保留。 |

- **Existing Implementation：**WorldModel/ConcernService/CognitionSession/MediaSemanticService、B9 router/factory与H2受控ingress；port永不拥有will。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**实际codecs/owned X11 L1与历史TianToken PARTIAL保留；新增S5_LIVE：同一原Subject一次DeepSeek PROJECT请求HTTP200→原C，再实际撤回来源→UNKNOWN/NO_ACTION。不得合称全live多模态。
- **Missing Foundation：**明示基础范围无已确认缺口；实际同一lineage单请求组合已留证，广泛媒体语义仍属后续。
- **对应源码：**[src/nana_core/continuity/world_loop/world.py](../src/nana_core/continuity/world_loop/world.py)；[src/nana_core/continuity/world_loop/attention.py](../src/nana_core/continuity/world_loop/attention.py)；[src/nana_core/continuity/world_loop/cognition.py](../src/nana_core/continuity/world_loop/cognition.py)；[src/nana_core/continuity/world_loop/semantics.py](../src/nana_core/continuity/world_loop/semantics.py)；[src/nana_core/continuity/sensors/coordinator.py](../src/nana_core/continuity/sensors/coordinator.py)；[src/nana_core/continuity/provider_routing.py](../src/nana_core/continuity/provider_routing.py)
- **对应当前tests：**[tests/world_loop/test_foundation.py](../tests/world_loop/test_foundation.py)；[tests/world_loop/test_boundaries.py](../tests/world_loop/test_boundaries.py)；[tests/h1_semantics/test_grounding.py](../tests/h1_semantics/test_grounding.py)；[tests/provider_routing/test_router.py](../tests/provider_routing/test_router.py)；[tests/first_life/test_project_status_context.py](../tests/first_life/test_project_status_context.py)
- **当前blocker / First-Life：**NO：S5基础组合已资格；S1–S9基础资格已闭合。
- **下一次升级条件：**本域基础已资格；更广媒体/语义、真人自然度须独立留证，不由一次HTTP成功推定。
- **Advanced Future：**广泛视频/音频语义、camera/mic、用户桌面OCR及开放世界；不要求全部传感器才基础完成。
- **对应PROJECT_BRAIN决策：**`D-WORLD-006`、`D-H1-001`、`D-H1-LIVE-003`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

### S6 · Independent Judgment / Problem Framing / Goal / Planning

**Foundation Definition：**C能形成自己的问题判断和目标，区分用户建议、问题与路径；有限规划可验证并按结果调整。
**STATUS = FOUNDATION_QUALIFIED**；growth_status = ADVANCED_GROWTH。

| Criterion | 固定必要条件 | 状态 | 实现/测试/证据索引 | 范围与未证明项 |
|---|---|---|---|---|
| S6-C01 | 输入/用户建议不直接变成已采纳目标或权限 | FOUNDATION_QUALIFIED | LOOP, AFFECT, PLAN | 候选、adoption、Grant分离。 |
| S6-C02 | 可提出与用户方法不同的有来源替代方案 | FOUNDATION_QUALIFIED | HANDS, LOOP | 真实owned任务历史支持HANDS_REPLACE替代APPEND；限定方法级。 |
| S6-C03 | 多目标、子目标依赖、有限路径与独立计划验证 | FOUNDATION_QUALIFIED | PLAN | 有界uniform-cost与typed operators；不是无限开放推理。 |
| S6-C04 | 实际执行/Verify/失败→Continue/Replan/Stop | FOUNDATION_QUALIFIED | PLAN, RAE, HANDS | 原失败保留。 |
| S6-C05 | 世界修正/学习/来源撤回可改变或暂停计划 | FOUNDATION_QUALIFIED | PLAN, LEARN, HANDS | 不能仅换解释而沿用旧输出。 |
| S6-C06 | 自主目标受Manager/资源约束但不由其生成意志 | FOUNDATION_QUALIFIED | LIFE, HANDS, RAE | REST/NO_ACTION也是有效选择。 |
| S6-C07 | 独立Problem Framing的当前最小因果资格 | FOUNDATION_QUALIFIED | HANDS, RAE, PLAN, SCOPE_PROBE, CLOSURE | 普通DECLINE_DELIVERY不阻同题内部LEARN；旧DECLINE_DEPTH保守处理禁令保持。C自身pending负荷可选择REST并重启后复审。同问题/不同实际IPC状态→保留原题或新问题→原Goal/Plan；无Grant为BLOCKED，不是仅替换方法。 |

- **Existing Implementation：**原C Judgment/ALTERNATIVE、typed Objective、BoundedPlanner与source/cursor-revision replan已在用；历史edda确认旧context_fit/learning范围混用；本轮已修复。 本轮闭环：对话投递、显式处理禁令、Subject自选休息及资源/权限分离；有源前提检验和问题级重定义、matched对照、原planner实际执行/无Grant阻断。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**历史方法级不同意见保留；本轮CLOSURE matched IPC状态证明问题级替代→原目标/规划→实际独立核验，含无Grant BLOCKED、source/model-only反例及范围分流/自主REST。
- **Missing Foundation：**限定Foundation内无已确认待补机制；本轮CLOSURE关闭本域最后一条资格，不宣称Advanced完成。
- **对应源码：**[src/nana_core/continuity/subject/policy.py](../src/nana_core/continuity/subject/policy.py)；[src/nana_core/continuity/subject/context_fit.py](../src/nana_core/continuity/subject/context_fit.py)；[src/nana_core/continuity/open_agency/contracts.py](../src/nana_core/continuity/open_agency/contracts.py)；[src/nana_core/continuity/open_agency/planning.py](../src/nana_core/continuity/open_agency/planning.py)；[src/nana_core/continuity/open_agency/service.py](../src/nana_core/continuity/open_agency/service.py)；[src/nana_core/continuity/open_agency/learning.py](../src/nana_core/continuity/open_agency/learning.py)；[src/nana_core/continuity/world_loop/attention.py](../src/nana_core/continuity/world_loop/attention.py)
- **对应当前tests：**[tests/open_autonomy/test_planning.py](../tests/open_autonomy/test_planning.py)；[tests/open_autonomy/test_learning.py](../tests/open_autonomy/test_learning.py)；[tests/controlled_hands/test_boundaries.py](../tests/controlled_hands/test_boundaries.py)；[tests/vision_first/test_context_fit.py](../tests/vision_first/test_context_fit.py)
- **当前blocker / First-Life：**NO：S6-C07已在有限有源候选空间受控资格；开放研究与任意问题发现为Advanced。
- **下一次升级条件：**新problem类型/更开放候选按实际证据扩展，沿原C/Goal/Planner；不另建brain。
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

- **Existing Implementation：**原ActionKernel/RealizationCoordinator与owned finite IPC adapter；document/form/files/content，不是任意OS。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**历史9tasks/36Actions/12effects真实owned进程；本审计目标测试有限临时owned应用复核，不接用户设备。
- **Missing Foundation：**有限owned开发应用Definition内无已确认缺失；通用GUI/用户设备和生产账号未在资格scope。
- **对应源码：**[src/nana_core/actions.py](../src/nana_core/actions.py)；[src/nana_core/continuity/autonomy/realization.py](../src/nana_core/continuity/autonomy/realization.py)；[src/nana_core/continuity/hands/service.py](../src/nana_core/continuity/hands/service.py)；[src/nana_core/continuity/hands/port.py](../src/nana_core/continuity/hands/port.py)；[src/nana_core/continuity/hands/server.py](../src/nana_core/continuity/hands/server.py)
- **对应当前tests：**[tests/controlled_hands/test_application.py](../tests/controlled_hands/test_application.py)；[tests/controlled_hands/test_boundaries.py](../tests/controlled_hands/test_boundaries.py)；[tests/controlled_hands/test_recovery.py](../tests/controlled_hands/test_recovery.py)
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

- **Existing Implementation：**统一权威Store/Experience→Reflection/typed lesson与LearningService九阶段；多个服务不是多个主体。当前方法/评价器仍有限且按领域审查。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**真实owned失败→before/after→heldout/不同任务transfer→counterexample suspension；社会学习和偏好/人格解释由独立来源支持的合成世界资格。
- **Missing Foundation：**受限跨域成长合同内无已确认缺失；不能由plan/action/share改善推定全部S2–S9算法学习成立，S3倾向整链另验。
- **对应源码：**[src/nana_core/continuity/learning.py](../src/nana_core/continuity/learning.py)；[src/nana_core/continuity/subject/reflection.py](../src/nana_core/continuity/subject/reflection.py)；[src/nana_core/continuity/subject/growth.py](../src/nana_core/continuity/subject/growth.py)；[src/nana_core/continuity/open_agency/learning.py](../src/nana_core/continuity/open_agency/learning.py)；[src/nana_core/continuity/world_loop/learning.py](../src/nana_core/continuity/world_loop/learning.py)；[src/nana_core/continuity/subject/growth_life.py](../src/nana_core/continuity/subject/growth_life.py)；[src/nana_core/presence/living.py](../src/nana_core/presence/living.py)
- **对应当前tests：**[tests/continuous_self/test_learning.py](../tests/continuous_self/test_learning.py)；[tests/continuous_runtime/test_generic_subject.py](../tests/continuous_runtime/test_generic_subject.py)；[tests/open_autonomy/test_learning.py](../tests/open_autonomy/test_learning.py)；[tests/world_loop/test_learning.py](../tests/world_loop/test_learning.py)；[tests/controlled_hands/test_application.py](../tests/controlled_hands/test_application.py)
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

- **Existing Implementation：**CodeSkillService/IsolatedSkillRunner/SelfExtensionWork，当前真实候选是deterministic bounded workflow composition，不是自主发明任意算法。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**真实form gap触发、独立bwrap qualification、2次后续Kernel受控实际复用、source删除撤销。
- **Missing Foundation：**受限纯数据workflow/skill realm内无已确认缺失；任意安装/host权限不是当前已有能力。
- **对应源码：**[src/nana_core/continuity/open_agency/code_skills.py](../src/nana_core/continuity/open_agency/code_skills.py)；[src/nana_core/continuity/world_loop/extension.py](../src/nana_core/continuity/world_loop/extension.py)；[src/nana_core/continuity/hands/skills.py](../src/nana_core/continuity/hands/skills.py)；[src/nana_core/life/skills.py](../src/nana_core/life/skills.py)
- **对应当前tests：**[tests/open_autonomy/test_code_skills.py](../tests/open_autonomy/test_code_skills.py)；[tests/world_loop/test_living.py](../tests/world_loop/test_living.py)；[tests/controlled_hands/test_application.py](../tests/controlled_hands/test_application.py)；[tests/cloud_life/test_daily_tasks.py](../tests/cloud_life/test_daily_tasks.py)
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

- **Existing Implementation：**已有lineage/受控迁移/版本化skill/禁用任意Core mutation；没有J式deep Core replacement执行系统。
- **Tested Evidence：**对应本域criteria索引及历史edda全仓1300/12skip；本轮变动以CLOSURE最终回归为准，不把历史同源码声明套到新实现。
- **Actually Run / Qualification Evidence：**实际B8退役迁移/顺序owner交接和fresh rollback；明确不是deep Core canary/rollback资格。
- **Missing Foundation：**S10-C05/C06深改和评测底座自演化未取得可执行资格；现有迁移/skill评测不代替它。
- **对应源码：**[src/nana_core/continuity/portable.py](../src/nana_core/continuity/portable.py)；[src/nana_core/continuity/identity.py](../src/nana_core/continuity/identity.py)；[src/nana_core/continuity/open_agency/code_skills.py](../src/nana_core/continuity/open_agency/code_skills.py)；[src/nana_core/life/cloud.py](../src/nana_core/life/cloud.py)
- **对应当前tests：**[tests/portable_subject/test_package.py](../tests/portable_subject/test_package.py)；[tests/portable_subject/test_schema_genericity.py](../tests/portable_subject/test_schema_genericity.py)；[tests/open_autonomy/test_code_skills.py](../tests/open_autonomy/test_code_skills.py)；[tests/first_life/test_rehearsal.py](../tests/first_life/test_rehearsal.py)
- **当前blocker / First-Life：**NO：深层实现不阻塞当前First-Life；当前适用连续性/治理约束仍在S1/S7/S8/S9必验。
- **下一次升级条件：**仅在确有深层变更任务时进入S10专门资格，不为当前封基础而先造大框架。
- **Advanced Future：**更开放Core/内部算法自修改、候选archive/canary、验证底座自身演化。
- **对应PROJECT_BRAIN决策：**`D-C6B-002`、`D-D2D7-006`、`D-E1E6-004`、`MASTER_FRAMEWORK_FREEZE_V1`，见[10_DECISIONS](10_DECISIONS.md)。按原阶段/范围继承，不将历史READY自动推广。

## 4. 三横轴的当前资格

| 轴 | 已有基础 | 待核验/未来 | 对当前Gate的影响 |
|---|---|---|---|
| Shared Life / Companionship | 关系影响、来源绑定分享/沉默、忙碌/拒绝与删除反例（REL/SHARE/HANDS） | 真正长期相处质量未评审；S3受限competence需要闭环已资格，不推广为全人类情感 | S1–S9基础门已齐；真人评审NOT_RUN，未自动启动。 |
| Platform / Surface / Embodied Presence | One Subject；Event-First L0/L1/L2与QQ/Bili开发shadow、受控Hands（CDL/PORT） | 实际账号统一接线、phone/desktop/game/voice/avatar等扩展 | 不要求所有设备前置；真实绑定和动作按具体范围另验。 |
| Manager / Authority / Privacy / Recovery | 愿望与权限分离、Grant撤销、来源删除、UNKNOWN、迁移恢复（AFFECT/HANDS/PORT） | 分布式敌对宿主与深层自改验证底座未合格 | 当前适用治理约束持续必验；S10远期能力不因此被提前宣称完成。 |

## 5. 有界缺口清单与下一任务

| ID | 归属 | 缺口类型 | 是否确认实现缺失 | 下一最小动作 / 完成条件 |
|---|---|---|---|---|
| FQ-01 | S3-C09 | CLOSED_CONTROLLED_QUALIFICATION | 最小派生需要桥接已实现并资格 | 已完成受控经历/复用/重启/反例/撤回，见CLOSURE；不重做。 |
| FQ-02 | S4-C06 | FOUNDATION_QUALIFIED | 否 | 原固定run实际86405.272秒，完整final/DB/恢复/源码核验PASS；无重跑或热更新。 |
| FQ-03 | S5-C06 | FOUNDATION_QUALIFIED | 否 | 单次新授权真实PROJECT组合已完成；source撤回修正已实测；不再调用、不启动真人评审。 |
| FQ-04 | S6-C07 | CLOSED_CONTROLLED_QUALIFICATION | 有界范围分流与问题重构已实现并资格 | 已完成问题级matched对照、原Planner实际效果及权限反例，见CLOSURE；不重做。 |
| AG-10 | S10-C05/C06 | ADVANCED_GROWTH | 当前不启动 | 深层自改触发时再做branch/evaluator/lineage专门资格；不阻塞当前基础封顶。 |

[历史edda审计建议，已由本轮执行完成] 独立复核后的唯一下一推荐：优先FQ-04 / S6-C07，在原C中补独立问题界定与认知范围分流。原因是已证实的语义缺口+当前Gate blocker，比S3-C09尚未知的资格差额更直接；不否定已有S3基础。FQ-01保留为后续有界资格，不自动实施。FQ-02保持原run独立等待；FQ-03先做资料差额对齐。不存在在核账之外新增一套情感引擎、第二记忆系统或大规模框架的授权。

**审计终点已达到：**十域均有固定criteria、状态、实现/测试/证据映射、未知和升级条件。本轮核账完成，不要求所有未知都在同一审计内变成PASS；后续仅关闭上述具体缺口。只有证实 `FOUNDATION_MISSING + CURRENT_GATE_BLOCKER` 才因新发现改变实施主线。

## 6. First-Life门与保留证据

- Foundation Gate：S1–S9均须FOUNDATION_QUALIFIED，当前未达到；本表不自动升级Beta。
- First-Life Integration Gate：之后验证同一实例的组合运行、恢复、长期驻留与适用的人机相处；已有技术证据保留，缺项按当时适用资格补齐。
- DeepSeek：功能资格文件记录17次；随后真人样本增加2次，当前累计19次，最后1次冻结；保守预留0.95USD不是账单。历史TianToken UNKNOWN保持PARKED。
- 当前真人样本因context/intent链路缺陷排除；修复只有OFFLINE/FIXTURE证据，不据此判用户表达、模型自然度或S3缺失。
- 历史edda审计已读快照：36953.176245105秒，RUNNING_NOT_QUALIFIED，provider0、social0；该文件不是live进程探测。
- 旧07/08/09中“下一步真人评审/新小额预算”等任务安排由本轮用户冻结指令暂缓；历史发生事实、预算消耗和原资格不改写。

## 7. 证据索引（路径均按审计基线检查）

索引中的源码/测试定义均为当前基线阅读对象；资格文件为历史运行结果。初次执行范围仅文档校验；独立复核新增RECHECK/SCOPE_PROBE，Core/test代码与初审同版本。

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

## 8. af52371独立复核 amendment（criteria版本1.0不变）

- 先验证本地eece7a4为远端af52371祖先；本地未提交草稿按10个文件的hash保存在仓库外，再fast-forward，无reset/rebase/force。Master文件逐字保留；63个criterion ID/文字/分母均与af52371完全相同。
- 新证据补足S3-C01/C02/C04/C06/C08受限合成/实际进程资格，8/9已资格；S3-C09真实经历→后来需要/倾向变化→重启→自主再选择仍UNKNOWN，域维持FOUNDATION_TESTED。不把来源typed偏好注入说成真实经历提炼。
- S6-C07从UNKNOWN改为FOUNDATION_PARTIAL：新PUBLIC probe、原6项测试与LearningService源码确认对话拒绝和同题内部认知暂停混用。普通来源并非Manager，其他topic仍独立、原motive来源未删除；需要有界语义修复，不是宣告整个Judgment/Goal/Planner不存在。缺少专用DTO本身不构成实现缺失证据，允许复用通用记录。
- S4-C06、S5-C06不升级，S10深层资格未知保留。现有候选/动作/学习/受控扩展PASS不回滚。
- 新复核：tracked21 PASS30.65s；历史Git测试快照对当前Core18 PASS106.06s，含90虚拟天/7实际SIGKILL；原topic边界6 PASS0.63s，PASS证明旧行为而非新宪法全部符合。历史全仓1300/12skip仍仅复用，未重复运行。
- 旧relational suite当前树缺失；确切Git来源、sha256与临时提取复核方法见relational_snapshot.json。pycache不算测试源码，历史a97a811不是当前分支祖先。
- S8仍为跨域成长引擎Foundation Qualified：实际plan/action/share与方法的后续变化可查；未来S2记忆策略、S4 cadence策略、S5认知方法、S6 framing、S3更广affect、S9新realm要分别验证，不能推定全S2–S9算法都会自动改写。学习不能覆盖S1身份与治理，深改进入S10。
- 独立复核只读staging进度并新增快照，不修改/重启固定源码run；没有新付费调用、human评分、社交或生产动作。

### RECHECK

- [docs/nana_master_framework_foundation_audit_v1_evidence/focused_tests.txt](../docs/nana_master_framework_foundation_audit_v1_evidence/focused_tests.txt)
- [docs/nana_master_framework_foundation_audit_v1_evidence/relational_current_core_tests.txt](../docs/nana_master_framework_foundation_audit_v1_evidence/relational_current_core_tests.txt)
- [docs/nana_master_framework_foundation_audit_v1_evidence/relational_snapshot.json](../docs/nana_master_framework_foundation_audit_v1_evidence/relational_snapshot.json)

### SCOPE_PROBE

- [src/nana_core/continuity/subject/context_fit.py](../src/nana_core/continuity/subject/context_fit.py)
- [src/nana_core/continuity/open_agency/learning.py](../src/nana_core/continuity/open_agency/learning.py)
- [tools/nana_foundation_audit/probe_topic_scope.py](../tools/nana_foundation_audit/probe_topic_scope.py)
- [docs/nana_master_framework_foundation_audit_v1_evidence/topic_scope_probe.json](../docs/nana_master_framework_foundation_audit_v1_evidence/topic_scope_probe.json)
- [docs/nana_master_framework_foundation_audit_v1_evidence/context_boundary_tests.txt](../docs/nana_master_framework_foundation_audit_v1_evidence/context_boundary_tests.txt)

## 9. Foundation Closure V1（当前，固定criteria不变）

- S3-C09 UNKNOWN→QUALIFIED，S3 TESTED→QUALIFIED：原Experience/策略复用支持重建competence need，真实owned失败及后续复用→OPEN/LEARN→SETTLED/WATCH→实际SIGKILL及同cycle重放/再选择；受控counterexample/实际来源撤回改变需要。不是人工PreferenceSignal注入，也不是全面人类affect资格。
- S6-C07 PARTIAL→QUALIFIED，S6 PARTIAL→QUALIFIED：普通投递停止与hard processing语义分流；自有pending负荷→REST→重启后复审；相同问题、不同真实IPC状态的前提检验与问题级替代→原Goal/Planner/Kernel，有Grant实际核验完成、无Grant BLOCKED。
- 回归发现并修复共享训练源删除后宿主重新capture导致SOURCE_DELETED的恢复缺陷；墓碑保留，共享training binding退役，不复活来源或技能。
- S4-C06 UNKNOWN保留：原固定24h run只读观察，实际final result尚未生成；S5-C06 UNKNOWN保留：当前组合仅SYNTHETIC_LOOPBACK通过，历史分项证据不拼接成live资格；新真实调用0，无安全凭据绑定/新付费授权。
- 63项：59 QUALIFIED、4 UNKNOWN；S1–S9仍缺S4/S5两条资格。S10-C05/C06保留UNKNOWN/非First-Life前置。未改变Master、criterion定义、ID或分母。
- 当前唯一剩余实施入口：S5-C06已准备的单次PROJECT新语义资格授权门，同时等待原S4实际结果；不新造模块、不重开24h、不进入First-Life评审。真人评审/生产继续暂停。

### CLOSURE

- [实现与限制](../docs/nana_foundation_closure_v1_implementation.md)
- [实际经历需要闭环](../docs/nana_foundation_closure_v1_evidence/experience_need.json)
- [问题重构与无Grant对照](../docs/nana_foundation_closure_v1_evidence/problem_framing.json)
- [当前语义组合，明确为合成](../docs/nana_foundation_closure_v1_evidence/semantic_chain_offline.json)
- [原staging只读观察](../docs/nana_foundation_closure_v1_evidence/staging_observation.json)

## S5-C06 LIVE FOLLOWUP — current delta

One new explicitly authorized DeepSeek PROJECT call, HTTP200, same original identity, strict MODEL_DERIVATION→World/Concern→C, followed by actual source withdrawal→UNKNOWN/NO_ACTION. 60/63 qualified, 3 unknown (S4-C06 and advanced S10-C05/C06). Only S4 blocks S1–S9 closure. Old current/reconciliation blocks above are historical.

### S5_LIVE

- [Live chain, source lifecycle and reopen metadata](../docs/nana_foundation_closure_v1_evidence/semantic_chain_live.json)
- [One-dispatch qualification tool](../tools/nana_foundation_closure/live_once.py)
- [Offline guard and integration tests](../tests/foundation_closure/test_live_once.py)

## CURRENT — 原S4-C06最终资格收口

原645899b开发run实际86405.272秒/exit0。1464资源采样、42唯一Action、14真实owned-dev effects、SIGKILL epoch2→3、独立DB quick/FK与fresh-host迁移均通过；原writer退役，恢复端Grant撤销，backup仅quarantine review。见S4_FINAL。S1–S9全部Foundation Qualified，63项61 qualified/2高级unknown。Master字节、criterion文字/ID/分母不变。上文历史CURRENT和运行中快照保留为历史；First-Life/Human/Beta未升级，未启动新任务。

## Advanced Growth evidence — Open Life Expansion V1 (2026-10-22)

No Foundation definition, criterion ID, denominator or status is changed.
S2/S3/S4/S5/S6/S7/S8/S9 + Shared Life/Surface/Governance gain an opt-in bounded
attention queue, explicit owned source intake/research, sealed browser/form Hand,
original C goal lifecycle review and original G practice-selection strategy.
See [implementation](../docs/nana_open_life_expansion_v1_implementation.md).
Current evidence is owned/dev + synthetic semantic interpretation; final growth
qualification is separate from Foundation and Human Review. S10 deep changes,
real cloud/social/devices and human First-Life/Beta remain outside this evidence.


## Advanced Growth evidence / Foundation criteria unchanged — 2026-10-22

Current result: OFFLINE_CANDIDATE_READY within OWNED_DEV_ONLY Advanced Growth.
Runtime source c4791d03edcabaf043118141ef20109bc0f28fda; final full1464/0fail/12skip
(409.31s), focused29/related159 from that same run. Actual120.168s residency and
60 virtual-day scenarios are distinct; no new24h/72h claim. Integrated evidence
records8 goals,30 Kernel actions,13 Experiences,3 Lessons,2 later skill uses;
automatic original Runtime research, busy deferral, retirement, withdrawal UNKNOWN,
quarantined backup and lawful same-identity transfer. All copies13/43/FK0.
Portable228-file release SHA256119a574ca4b2ee60673b6e054be51e3ffcb526f98b0f6bfe09a94fc7d214a636;
rebuild equal; clean offline installation and new features run without repository
or inherited PYTHONPATH. See status, quickstart and evidence manifest for exact scope.

One C/D/Store authority preserved; Master/63 criteria unchanged; no production,
main/R045, old web/current user Subject, private history or paid provider operation.
Human Review NOT_RUN, First-Life NOT_READY, Beta NO. FORM gestures do not qualify
real desktop/mobile/gameplay; fixed source/schema/method adapters do not qualify
general world comprehension/meta-learning. Track A no longer waits for Track B.


## Advanced Growth — Controlled World V1 / 2026-10-24

固定63条criteria、ID、定义和Foundation状态不变。S2–S9/三横轴增加五服务、结构化Browser、三源矛盾研究与9步多Hand项目、噪声G/I/技能退休、三surface与12实际进程切点、2000事件检索、官方B8迁移和更新便携包的受控证据。

本轮整体PARTIAL_EXTERNAL_LIMIT：原b6450e1只有3939.795642475秒最后健康快照，环境boot更换/owner消失且无final；不宣称5h。当前a47b672全仓与安装结果见[status](../docs/nana_real_world_controlled_expansion_v1_status.md)及[机器资格](../docs/nana_real_world_controlled_expansion_v1_evidence/qualification.json)。这是Advanced资格差额，不推翻既有S4原24h Foundation资格，不把S10高级项变成First-Life前置。Human/First-Life/Beta未升级。
