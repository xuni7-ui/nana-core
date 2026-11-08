# Nana Core 源码导航与真实性核对

核对基准：2026-11-08，开发分支 `dev/nana-core-next-experience-codex` 的 `9c33176d278c4c1e733c879868d2cf82433c777a`。这是一份按源码入口检查的导航快照，不是部署或长期体验验收；当前事实仍以 PROJECT_BRAIN 和实际运行回执为准。后续版本需重新核对，而非沿用此 SHA 作为永远最新。

## 先看哪里

1. [冻结总纲](../../PROJECT_BRAIN/00_MASTER_FRAMEWORK.md) 与 [固定能力标准](../../PROJECT_BRAIN/01_CAPABILITY_MATRIX.md)。
2. [当前状态](../../PROJECT_BRAIN/09_STATE.md)、[任务](../../PROJECT_BRAIN/08_TASKS.md)、[近期决策](../../PROJECT_BRAIN/10_DECISIONS.md) 和 [变更](../../PROJECT_BRAIN/11_CHANGELOG.md)。
3. [现有主任务进度与未完成事项](STATUS_AND_REMAINING.md) 与 [续办记录](ACTIVE_CHECKPOINT.md)。
4. 核对现场 `git status --short --branch`、`git rev-parse HEAD` 及远端，再沿下面调用链检查源码和对应测试。不要把某个发行包或旧记录直接认作当前生产。

## 实际运行链与归属

| 责任 | 实际入口及关系 | 证据与限制 |
|---|---|---|
| 独立 Core 进程 | `src/nana_core/life/__main__.py` 的 `run` → `life/application.py` 的 `LifeApplication` → `presence/runtime.py` 的 `NanaRuntime` | `LifeApplication.tick` 先处理已有入站，再调用原 runtime step；不是 README 早期目录图所描述的单纯 AstrBot 插件。 |
| 唯一持久主体及调度 | `presence/runtime.py` 创建 `continuity/store.py:ContinuityStore`、lease、`continuity/subject/loop.py:SubjectLoop`、队列和 scheduler | Store 的 SQLite 基础位于 `storage/sqlite_store.py`；具体实例的单写者/生产状态仍须现场核验。 |
| C 判断、情感与动机 | `continuity/subject/loop.py` 使用 `subject/policy.py` 的 appraisal、motivate、decide；关系投影在 `continuity/relationships.py` | 具体行为受现有规则限制，不能把类型存在等同自然生活已验收。 |
| 记忆、上下文、巩固 | `continuity/memory.py:MemoryService`、`continuity/context.py:ContextAssembler`、`continuity/maintenance.py:MaintenanceService`，`presence/living.py` 组装维护 | 48h、来源、撤回、记忆反馈与梦境按 STATUS 的各自证据核对；生产长期效果未由离线测试证明。 |
| 模型和世界认知 | `continuity/world_loop/cognition.py:CognitionSession` 使用 ContextAssembler；`world_loop/coordinator.py` 接入；`continuity/provider_routing.py` 路由 | 实际供应商、费用和使用量依赖运行配置及真实回执。 |
| 自主学习和扩展 | `presence/living.py` 接入 `continuity/open_agency/learning.py:LearningService`；其余增长在 `continuity/retrieval_growth.py` 和 `continuity/open_agency/` | 有受控测试；真实跨模型、跨日成长和技能宿主隔离不应由此推定。 |
| 权限和执行 | `continuity/autonomy/governance.py:ManagerConstraintGate`、`src/nana_core/actions.py`、`life/platform_runtime.py` | 意愿、权限、外部动作及回执不同；不能把内部兴趣直接视作发送授权。 |
| 私人意向 | `continuity/autonomy/private_intent.py` 使用原 Store 的记录和来源 | 已有对应机制，但跨模型、重启和自主表达的用户体验仍须实测；不要据名称假定已满足全部“隐私小本子”要求。 |
| API、Web、Android | `life/live_api/server.py`、`life/live_api/supervisor.py`，客户端 `apps/nana-space/`，宿主入口 `packaging/portable/host_gateway.py` | 源码存在不等于运行中 Gateway、Web 或手机已更新；真实绑定和签名分别核验。 |
| 发行 | `tools/nana_portable_cloud/build.py` 与 `packaging/portable/runtime-files.txt` | 核对实际 manifest、源提交、摘要和安装回执；源码开发 HEAD 不是自动发行版本。 |

相关测试入口包括 `tests/continuous_self/`、`tests/living_autonomy/`、`tests/open_autonomy/`、`tests/person_self/`、`tests/living_release_v4/`；选与改动相关的测试，先确认其 fixture 与执行环境。最近已有完整回归对应旧版本 b25，不能说 9c33176 已全仓通过。

## 分支与真实性

- 本次只读核对时远端开发 HEAD 为 `9c33176`，与本地一致；远端 `main` 为 `18bc736`，是该开发 HEAD 的祖先。`main` 与开发主线不可视为同一源码状态。
- 后续已正常 fetch 交付分支并实际读取 `5b4f589`：`CURRENT-DELIVERY.json` 仍选择 runtime `266272a92b5837b2458c107163bd95ea8e0d7fe4`、客户端409/frontend `b873a4af4b2c2731fe2c796b845364ab758a5f22`。新4205中断恢复候选随交付分支存在，但不是 CURRENT 选择。最新开发修复也没有自动进入该选择；不能把“文件在分支里”当成“选中/部署/在运行”。本次不改交付选择或生产。
- 现场 Core、Gateway、APK 和主体由用户转述的操作员回执描述；本次没有访问生产或独立验证。发布物应分别核对 source commit、封签、进程和 Store；开发代码存在不等于已部署。
- `a917c03` 的记忆使用反馈为开发源码和本地夹具验证；实际送达归因、C/S3/S8 后续行为、真人自然度及云端安装均未凭此证明。

## 明确的混乱及处理

| 项目 | 实际观察 | 判断与处理 |
|---|---|---|
| README 和 AGENTS 早期叙述 | README 将 2026-10-10 旧 P1/P2、未 push、旧目录图称为当前；AGENTS 顶部称 Foundation 核账为本轮任务并将 AstrBot 描述为现役唯一宿主 | 历史材料保留但不可当现状；以新导航和 09 状态提示为入口，后续按需逐项更新。 |
| `src/nana_core/runtime.py`、`memory.py` 与 `continuity/`、`presence/` 同名职责 | 同一仓库内确有不同代的实现及实验入口；正式独立 life 链使用上述 `continuity` 与 `presence` | 名称重复不等于可安全删除或全部未引用；在证明调用闭包和兼容性之前保留。 |
| `presence/*demo.py`、`qualification.py`、`controlled_world/lab.py` | 示例、受控验证或实验入口与运行代码并存 | 用途需要明确；不能凭文件名判定无依赖并删除。是否入包以实际白名单和构建产物核对。 |
| `pyproject.toml` 中 `nana-core-offline` 与多种 console script | 开发/实验入口存在；正式独立进程还通过 `python -m nana_core.life` 使用 | 名称不证明其为当前生产版本；检查实际部署入口与源码提交。 |
| 旧交付目录与历史文档 | 不同发布成果、环境、摘要可能不同 | 保留历史证据；任何新部署都应独立核对实际产物，不用目录名字冒充最新版。 |
| 开源依赖、孤立和跨分支实现 | 本次未完成全面静态/动态依赖闭包或所有远端分支逐对象审计 | 状态为未核验，不称无效依赖、孤儿代码或不存在；后续以导入、调用、测试和构建证明。 |

## 自主性审计首批可定位点（未作行为修改）

`continuity/subject/policy.py` 对高负荷、低价值/重复刺激、可替代学习方式等存在确定性早返回；尤其 `value.alternative == 'AVAILABLE'` 可直接拒绝学习。`life/application.py:PortfolioOpportunities` 也限制可用材料及活动时段。它们是待验证的过度约束候选，不能仅凭代码名称将所有限制判为错误；应区分现实权限、资源、接收者边界与主体选择，使用反例和消融比较后最小修改。真实 QQ 是否由旧插件拆句，本次无宿主证据，保持未知。

## 整理建议与回退

近期保留原模块和公开接口：入口是 README → Brain → 本导航 → 真实代码/测试；原始文档留作历史。P1 日用真实体验仍优先，不立即开展大规模目录迁移、依赖删除、旧分支合并或新 CI 治理项目。等 P1 有真实验收回执，再基于实际调用图提出明确归属和轻量检查；任何源码迁移需先评估引用、发布清单、序列化、身份、数据和回退。文档改动可通过其独立 Git 提交回退；本审计不移动或改写 Core。

## 2026-11-09 · Issue#2/#4的现役源码与隔离安装复核

GitHub连接器只读取得原Issue及评论（原文快照见evidence/resumed-20261109/issues-2-4-snapshot.json），没有发评论/关闭Issue。原61aebf3已是70c70d0祖先，不能按旧Issue“尚未修复”从零开发。源码在独立完整历史验证副本核对；主工作树未物化文件不当作仓库不存在。

| 原要求 | 实际入口/继承事实 | 本次资格与剩余 |
|---|---|---|
| Docker29双digest | tools/nana_living_release_v4/deploy.py:resolve及oci_identity.py从实际OCI绑定config/manifest，404才切合法manifest，并比diff_ids/架构/UID | SOURCE_FIXED；原正反例在70全仓执行，整体仅2个旧C预期失败，不冒充真实Docker29现场或新镜像构建 |
| 私有SSL库 | 同目录Dockerfile把libssl/libcrypto复制到私有runtime/lib，以UID999核对实际映射路径；不是改系统库 | SOURCE_FIXED；既有冷启动证据继承。本次安装用现有CPython3.12.14/SQLite3.53.1，未重建474MB旧V4、未验云端3.51.3 |
| life.json权限迁移 | config_permissions.py:prepare在既有独占锁/精确摘要下只fchmod0600，不改内容/所有者，拒绝活动owner及链接 | SOURCE_FIXED；原正反例被本次70全仓覆盖；没有应用到生产文件 |
| Gateway与Core版本入口 | live_api/__main__.py启动先follow_gateway_release；原私有Supervisor快照覆盖旧baked选择，注册和封签验证后exec目标 | 额外ACTUAL_INSTALLED_DEV检查：旧d2入口→70入口同PID两次成功exec，read-only检查通过，DB/配置/host状态hash不变；不是现役进程热切换/生产部署 |
| 120s/UNKNOWN/绑定 | 原可配置120–600s、两段独立等待、UNKNOWN保留与新独立前台额度、默认nana.space及旧配置不暗改已有实现 | 源码和既有HTTP/安装资格复用；真实账单/现场config仍UNKNOWN，不盲重试/清账 |
| 历史导入 | life/application.py接原ArchiveImportService；control.py的显式legacy-import/withdraw入口，migration/archive_ingress.py核身份/lineage/审批/来源/隐私；generic入口继续disabled | 源码可达及原合成拒绝路径被全仓覆盖，没读/导入8105条私人源；私人批准、源过滤、活Core/Iris索引和真实批次仍归云端负责人 |

Issue仍OPEN，不把操作者旧报告当最新现场，不自动关闭或切换现役。全部分支/孤立模块/依赖/长期运行闭包的完整审计仍未完成。上述是原任务H的有界继承核对，没有另建治理工程。
