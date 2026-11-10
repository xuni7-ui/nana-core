# 源码归属与治理补充

[实测] 审计基线 `b75ba7f8c74bfa98fefb518d8e028d731bd6c483`，2026-11-08；本页补充而不取代 [既有源码导航](SOURCE_NAVIGATION_AUDIT.md)、[冻结总纲](../../PROJECT_BRAIN/00_MASTER_FRAMEWORK.md) 和 [当前状态](../../PROJECT_BRAIN/09_STATE.md)。以下为源码存在与调用关系，不证明当前部署、真实体验或整体资格。能力状态按固定 Matrix 和对应证据核验；后续集成先检查基线差异。

| 职责及新代码归属 | 入口、依赖与证据 | 状态边界 |
|---|---|---|
| 独立主体/调度 | [life 命令](../../src/nana_core/life/__main__.py) → [LifeApplication](../../src/nana_core/life/application.py) → [NanaRuntime](../../src/nana_core/presence/runtime.py) → [SubjectLoop](../../src/nana_core/continuity/subject/loop.py)；Runtime 创建 Store、lease、queue、scheduler | 基线源码接线；实际单写者与运行版本须现场核验。 |
| 单 Store、记忆、经历、上下文 | [ContinuityStore](../../src/nana_core/continuity/store.py) 继承 [SQLite Store](../../src/nana_core/storage/sqlite_store.py)；[MemoryService](../../src/nana_core/continuity/memory.py)、[ExperienceService](../../src/nana_core/continuity/learning.py)、[ContextAssembler](../../src/nana_core/continuity/context.py)、[MaintenanceService](../../src/nana_core/continuity/maintenance.py) | 数据持久化、撤回及恢复以具体测试和运行回执为准。 |
| 判断、动机、情感、关系、规划 | SubjectLoop 使用 [policy](../../src/nana_core/continuity/subject/policy.py) 的 appraise/motivate/decide；[relationships](../../src/nana_core/continuity/relationships.py)；[OpenAgencyService](../../src/nana_core/continuity/open_agency/service.py) 使用 [BoundedPlanner](../../src/nana_core/continuity/open_agency/planning.py) | 不以类型或源码存在推定真实生活表现。C 的 WHAT/WHY 与 D 的 WHEN 边界见冻结总纲。 |
| 世界与认知 | [WorldLoopWork](../../src/nana_core/continuity/world_loop/coordinator.py) 使用 [CognitionSession](../../src/nana_core/continuity/world_loop/cognition.py)、WorldModel、ConcernService；[provider routing](../../src/nana_core/continuity/provider_routing.py) | 实际模型及费用依赖配置和回执。 |
| 学习、自扩展、深层演化 | [LivingWork](../../src/nana_core/presence/living.py) 配置 [LearningService](../../src/nana_core/continuity/open_agency/learning.py)；另有 [retrieval growth](../../src/nana_core/continuity/retrieval_growth.py)、[技能执行](../../src/nana_core/continuity/open_agency/skill_runner.py)、[主体包与迁移](../../src/nana_core/continuity/portable.py) | 深层演化不能从迁移接口推定完成；S10 按 Matrix 和独立验证/回退证据判断。 |
| Manager、Grant、动作 | [ManagerConstraintGate](../../src/nana_core/continuity/autonomy/governance.py) → [GovernedRealization](../../src/nana_core/continuity/autonomy/realization.py) → [ActionKernel](../../src/nana_core/actions.py)；[GrantSpec](../../src/nana_core/contracts.py) 定义能力、资源与有效时间，Kernel 的 grant/revoke/_grant_for 管授权记录与检查 | Manager PASS 不等于 Grant；dispatch 在调用端口前重查授权，verify 使用对应验证能力的 Grant。意愿不等于授权；UNKNOWN 不盲重试，外部动作及送达须独立核验。 |
| CapabilityPort 与执行上下文 | [CapabilityPort](../../src/nana_core/ports.py) 定义 execute/verify；Kernel 调用注入端口。原 [ContextBoundPort](../../src/nana_core/execution_context/port.py) 复用 Kernel 授权检查并绑定执行上下文；[ExecutionChannel](../../src/nana_core/execution_context/routing.py) 持有该协议端口 | 接口实现或上下文/通道元数据不授予权限，也不成为第二执行权威。端口与宿主的实际绑定须另验。 |
| 手机/Web 与 API | [Nana Space](../../apps/nana-space/README.md)、[API 服务](../../src/nana_core/life/live_api/server.py)、[supervisor](../../src/nana_core/life/live_api/supervisor.py)、[host gateway](../../packaging/portable/host_gateway.py) | 代码不证明客户端、网关、手机实际已更新。 |
| QQ/B站 | [PlatformRuntime](../../src/nana_core/life/platform_runtime.py) 的 qq/bilibili 入口分别调用 [QQ bridge](../../src/nana_core/life/platform_bridge.py) 与 [Bilibili workflow](../../src/nana_core/life/bilibili_runtime.py)；[shadow](../../tools/nana_cloud_surfaces/shadow.py) 是受控入口，复用旧 B站 normalize | 旧 [B站 Agent](../../src/bili_agent/bili_agent.py) 及事件泵是历史独立链，不能仅凭名称断定其是否在真实宿主运行。 |
| 构建、测试、交付 | [portable build](../../tools/nana_portable_cloud/build.py)、[runtime 白名单](../../packaging/portable/runtime-files.txt)、[测试](../../tests/)、[Next Experience selector 检查](../../tools/nana_next_experience/verify_delivery.py) 的 `--current` 与[历史 handoff 检查](../../tools/nana_first_life_unified_release/check_delivery.py)；[selector 测试](../../tests/first_life_android_v2/test_delivery_consistency.py) | 前者核对复合 selector、产物及声明契约；后者校验独立 SHA256SUMS 锚定的 handoff，适用范围不同。分别核对源码 SHA、清单、摘要、selector、安装与运行回执。 |

## 交付选择的核验入口

[实测：GitHub 只读文件，2026-11-08] 交付分支提交 `5b4f589fec8ecf5deb4dc5fafd2f4193c96569b8` 的 [CURRENT-DELIVERY.json](https://github.com/xuni7-ui/nana-core/blob/5b4f589fec8ecf5deb4dc5fafd2f4193c96569b8/deliveries/nana-space-next/CURRENT-DELIVERY.json) 指向 runtime `266272a` 和 frontend `b873a4a`；对应 [server manifest](https://github.com/xuni7-ui/nana-core/blob/5b4f589fec8ecf5deb4dc5fafd2f4193c96569b8/deliveries/nana-space-next/server-409-living-266/MANIFEST.json) 与 [client manifest](https://github.com/xuni7-ui/nana-core/blob/5b4f589fec8ecf5deb4dc5fafd2f4193c96569b8/deliveries/nana-space-next/MANIFEST-409.json) 的源码字段一致。同目录的 `CURRENT-DELIVERY-409-CANDIDATE.json` 选择旧 runtime `6a32cae`，不能按名称将其当作 CURRENT。两个 manifest 的 SHA-256 与 selector 一致；从该固定 Git 提交提取 selector 所列文件后，复用 `verify_delivery.py --root <目录> --current CURRENT-DELIVERY.json` 通过复合一致性检查，APK 与 Web 的 42 个文件相同。GitHub compare 显示上述 runtime 和 frontend 提交均为当时 A HEAD `58418b4e39c7003280fc4fcb2da352ea1dc9a7bf` 的祖先，分别相距 37 和 45 个提交；这不证明后续改动已进入交付。以上是该提交的文件快照；已对该 Git 快照所列二进制产物进行校验，但未证明主机、手机或生产实际运行。后续以当时的分支 HEAD、selector、manifest、产物摘要及现场回执重新核对。

## 审计分支的继承关系

[实测：GitHub compare 与 blob，2026-11-08] 审计分支 `50a842a0250726271ec1c1248e9cfd00087b7a5f` 与当时的 A HEAD `58418b4e39c7003280fc4fcb2da352ea1dc9a7bf` 共同祖先为 `9c33176d278c4c1e733c879868d2cf82433c777a`，分别有 2 与 12 个独有提交；审计分支不是 A 的祖先。两头的原 SOURCE_NAVIGATION_AUDIT、AGENTS 和 README blob 相同，CHANGELOG blob 不同。不能由导航文件已复用推断整个分支已合并或可删除；归档前仍须核对独有提交及账本，并协调负责人。该关系只覆盖上述固定提交。

## 定向测试入口

下列是定位入口，不代表本次运行或完整覆盖；按改动与 fixture 选择执行：

- 主体循环与运行：[SubjectLoop](../../tests/continuous_self/test_subject_loop.py)、[runtime](../../tests/continuous_runtime/test_storage_runtime.py)。
- 记忆与上下文：[memory](../../tests/continuous_self/test_memory.py)、[context](../../tests/continuous_self/test_context.py)、[memory-use feedback](../../tests/person_self/test_memory_use_feedback.py)。
- 认知与学习：[world loop](../../tests/world_loop/test_system.py)、[open autonomy learning](../../tests/open_autonomy/test_learning.py)。
- 治理、平台与迁移：[Manager governance](../../tests/affective_autonomy/test_governance.py)、[QQ platform](../../tests/living_release_v4/test_platform_runtime.py)、[B站 runtime](../../tests/living_release_v4/test_bilibili_runtime.py)、[portable subject](../../tests/portable_subject/test_package.py)。

## 同名模块的实际边界（基线 b75ba7f8）

- [旧 Runtime](../../src/nana_core/runtime.py) 自述为同步离线 driver；[development lab](../../src/nana_core/development/lab.py) 使用它，[离线 Runtime 测试](../../tests/offline_continuity/test_runtime.py)直接导入它。独立 life 主链使用上表的 `NanaRuntime`。这证明旧入口仍有源码消费者，不能按名字删除；不据此推定它在生产运行。
- [旧 MemoryView](../../src/nana_core/memory.py) 的 `entries` 要求显式 `synthetic:` 数据集；[迁移演练](../../src/nana_core/phase3/memory_rehearsal.py) 与 [phase3 测试](../../tests/phase3/test_memory.py)使用它。它与 `continuity/memory.py` 的 MemoryService 有不同的入口和范围，不能仅因同名合并。
- [便携包清单](../../packaging/portable/runtime-files.txt)同时列出新旧 runtime 和 memory 文件。对该基线 245 个清单条目运行 [构建器已有静态闭包检查](../../tools/nana_portable_cloud/build.py)通过；清单内 [initiative](../../src/nana_core/initiative.py) 静态引用旧 Runtime，而清单内未发现对旧 MemoryView 模块的静态导入。静态扫描不覆盖所有动态/外部消费者，也不证明每个实例的调用情况。若拟移除，先查外部入口、实际构建/安装、兼容测试与回退路径，再与负责人协调。

## Grant 与 CapabilityPort 的复用边界（2026-11-11，基线 cdc0132）

[源码核对] `ports.py` 的历史 offline 说明不能据以认定协议已废弃：[宿主集成契约](../../src/nana_core/integration/contracts.py)仍将 `HostCapabilityAdapter` 直接别名到原 `CapabilityPort`，上表执行通道也直接引用它。扩展适配器应沿用原 execute/verify 与 Kernel，不能因为旧注释另建权限或端口框架。

原 [QQReplyWorkflow](../../src/nana_core/life/platform_runtime.py) 构造 QQCapabilityPort，再由 [QQGovernedDelivery](../../src/nana_core/life/platform_bridge.py)复用原 ManagerConstraintGate 和 ActionKernel；它不走仅接纳指定离线/owned端口的普通 GovernedRealization 构造器。此处是现有源码的不同绑定路径，不是新增主体或授权来源，也不证明真实QQ已启用。

已有测试定位：[Manager PASS 不等于 Grant及直接Kernel不可绕过治理](../../tests/affective_autonomy/test_realization.py)、[动作Grant/过期/UNKNOWN](../../tests/offline_continuity/test_actions.py)、[QQ绑定与效果核验](../../tests/living_release_v4/test_platform_bridge.py)。这些链接提供现有验证入口，本次仅补导航，不重跑或升级它们的行为资格。


## 便携构建检查的限定修复（治理分支待集成）

[实测] 原 [静态闭包检查](../../tools/nana_portable_cloud/build.py)对 `import nana_core.not_present_anywhere` 的合成输入未拒绝：原逻辑只在目标已存在于 Git 树但未入清单时报告缺失。治理分支新增对显式绝对内部 `import` 的目标存在性检查；[定向测试](../../tests/engineering_quality/test_portable_missing_import.py)覆盖不存在、存在但未选入、正确选入、命名空间包及属性导入。修复后的检查对 `b75ba7f8` 与 `58418b4` 的各 245 个清单条目通过。对 `fb828cad077ba1bf2915eccb55496cddc12f3fd5`，复用 SHA-256 已核对的 266 交付包 wheel，在独立目录两次构建得到相同归档 SHA-256 `c6c7229c74e5732e0d2c7d428646f0f48a0085bb5cb1a964588b8a6d262be8c0`；已有 unpack 工具验证归档，279 个清单文件摘要及 source commit 一致。构建成功与产物校验不代表安装或运行成功，这两项均未执行。`from ... import name` 可能表示属性，仍沿用原有判断；动态注入模块、外部环境和安装运行仍需各自验证。该修复不证明任何当前交付产物有缺失。若需回退，单独撤销构建器新增检查与对应测试，不修改清单或运行数据；集成前重新对目标源码和实际打包验证。

## 开发与分支纪律

1. 先读总纲、Matrix、09 和当前任务；固定基线、查已有调用与测试，记录复用/扩展理由。实现、测试、接线、安装、生产及真实体验分开报告。
2. 按上表现有职责扩展；不引入第二 Subject、Store、Loop 或判断权威。实验、示例、兼容层注明入口和验证范围；同名不等于重复或可删除。
3. 分支记录起点 SHA、责任和范围；交付记录源提交、构建清单、摘要、selector 和安装回执。归档前检查共同祖先、独有提交、未集成差异和负责人；不因年龄直接删除。
4. 准备集成时重新核对 A 的已确认 HEAD、共同祖先及文件差异；仅移植治理改动，解决账本冲突时保留双方事实。结构迁移先列调用、数据/接口、依赖、验证与回退，协调后执行。
5. 导航改动运行 `python3 tools/nana_next_experience/check_governance_links.py`。此检查只验证本页相对 Markdown 链接目标存在；链接存在不证明功能或运行状态。历史/外部/暂缺目标应在文字中说明理由，不放入受检相对链接；补齐目标后再加链接。

## 2026-11-11 · 交付归档歧义的限定治理修复

现有 Next Experience 验证器增加 APK public 资源同名条目拒绝与 Core `runtime.json` 唯一性检查；普通 manifest 和 CURRENT 原入口复用，未改变交付选择。五个重算摘要的合成反例从误通过改为拒绝，固定 `5b4f589` CURRENT 快照仍通过42文件一致性检查。范围、回退与实测记录见[治理证据](evidence/governance-archive-ambiguity-20261111/README.md)；不代表生产、签名、安装或整体归档安全资格。
