# Nana Core V1 第一阶段实现与验收

> [实测] 2026-10-10；独立合成离线环境；严格限定 S0—S4。
> 基线：`18bc736d5e37fe3325e514a0e975403df2f97c9f`。
> 分支：`dev/nana-core-v1-s0-s4`。本报告不是生产运行验收。

## 结果

已经实际运行：Event → Memory → Goal → Plan → Authorization → Action → Verification → Feedback → Experience → 进程退出 → 新进程 → New Decision。

完整测试结果：**56 passed、0 failed、1 skipped**。E01—E20 有 **19 项离线 PASS**；E12 的真实双模型语义迁移 **NOT_RUN**，按本轮范围明确跳过。

验收原始结果：

- [逐项验收与测试节点](nana_core_v1_evidence/acceptance_results.json)
- [pytest 输出](nana_core_v1_test_output.txt)
- [JUnit](nana_core_v1_evidence/junit.xml)
- [独立进程实验](nana_core_v1_evidence/experiment_manifest.json)
- [崩溃恢复](nana_core_v1_evidence/action_recovery_trace.json)
- [经验消融](nana_core_v1_evidence/learning_ablation.json)
- [身份快照前](nana_core_v1_evidence/identity_snapshot_before.json) / [后](nana_core_v1_evidence/identity_snapshot_after.json)
- [事件轨迹](nana_core_v1_evidence/event_trace.json)
- [依赖与费用边界](nana_core_v1_evidence/dependency_manifest.json)

## 重现

需要 Python 3.12+、Linux/POSIX flock、实际链接的 SQLite >=3.51.3。开发环境实测 Python 3.12.14 / SQLite 3.53.1 / Pydantic 2.13.4。

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-core-dev.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pytest tests/offline_continuity --acceptance-report /tmp/nana-v1-acceptance
.venv/bin/nana-offline --output /tmp/nana-v1-new-run --seed 29
```

实验输出目录必须不存在。CLI 不读取凭据、不调用网络模型，也没有生产集成。pytest 的报告选项在实验目录 conftest 注册，命令需显式提供 `tests/offline_continuity`。最初省略该目录的报告命令在收集测试前报 usage 错误（exit 4）；修正调用后运行全部测试，不是隐藏测试失败。

普通 `.venv/bin/python -m pytest` 也能运行完整离线测试，只不生成 JSON 验收报告。

已实际构建 wheel，并确认只包含 `nana_core` 与其包元数据、包括 schema 文件；安装后的 `nana-offline` 在 `/tmp` 工作目录运行成功。

## 模块

| 文件 | 职责 |
|---|---|
| `contracts.py` | 严格 DTO、读卡片能力白名单、模型/反馈/策略契约 |
| `clock.py` | aware UTC 解析、原始发生时间、可注入时钟 |
| `storage/sqlite_store.py` | 单实例锁、单事务入口、追加事件、完整证据、投影回放、隔离备份 |
| `storage/schema_v1.sql` | 唯一 schema v1 定义 |
| `actions.py` | 本地授权入口、精确资源 Grant、预算、状态机、派发与恢复 |
| `fake_world.py` | 独立外部数据库、原子效果与幂等记录、查询核验 |
| `planning.py` | ContextBuilder、明确标识的工程 ModelPort、PlanCompiler |
| `runtime.py` | 一个 reading_card 目标、有限步骤、完成条件、自传片段、唤醒 |
| `experience.py` | 反馈关联、缺失字段归纳、策略测试/启用/撤回与证据失效 |
| `experiment.py` | 不同进程的完整实验、真实 SIGKILL、匹配快照消融与证据导出 |

## 数据库与事务

只建 15 个当前实验实际使用的领域表（不含 SQLite 自身的 sqlite_sequence）：

`core_meta, events, artifacts, identities, memory_items, goals, plans, decisions, grants, budgets, actions, attempts, budget_holds, strategies, jobs`。

字段、外键、CHECK、唯一索引和事件不可修改触发器均在 `src/nana_core/storage/schema_v1.sql`。

重要约束：来源事件键唯一；一个活跃目标；同一效果槽只允许一个可能生效的动作；幂等键唯一；预算 held+spent 不超过 limit；一个 attempt 对一个维度只有一条预留。

每个事务记录类型化事件及完整投影变更，事件与投影同库提交。原始 Artifact 是证据权威，不由模型重建。回放使用记录的变更，不重跑模型或能力。

事务分为：接收证据、接受目标/计划、授权与预算预留、派发资格复查与尝试记账、保存回执、核验结果、学习更新。模型/能力调用均在事务之外。SQL 设置 WAL / synchronous FULL / foreign_keys ON；恢复前 quick_check 与 foreign_key_check；身份丢失、损坏库或不认识的 schema 均拒绝运行，不静默生成新身份。

普通备份及回放生成的库带 `recovery_quarantine=true`，不自动重发。回放测试比较全部状态，只容许这一项已声明的本地恢复标记变化；没有跳过授权、预算等字段比较。当前不提供通用解除隔离或生产迁移功能。

## 崩溃证明

测试不只是 mock 异常：子进程使用 SIGKILL（返回码 -9）。

1. 派发记录已提交、调用前被杀：恢复先记 UNKNOWN，再完整查询；确认为 NOT_APPLIED；不重发。
2. fake_world 已提交卡片、回执保存前被杀：本地仍为 DISPATCHING；新进程通过独立读取恢复 SUCCEEDED；外部卡片数和写调用数均为 1。
3. 完整阅读目标在卡片提交后被杀：此前的读取和计划已持久化；恢复不用新的模型提议，目标最终完成；source/card 两次执行均未重复。

生产平台不一定具备这样的完整查询和幂等能力。本实现没有把 FakeWorld 的保证推广到 B站。

## 经验与消融证明

反馈原文保存为证据，结构化 `requested_fields=("locator",)` 来自本地认证 Operator 入口。引擎检查已验证卡片缺少哪个请求字段，从能力输出注册表选取生产该字段的读取能力，形成 ADD_READ_STEP 候选；通过正例、已有步骤、范围反例及写目标保持检查后启用。

规则没有测试事件 ID、指定页码或期望调用次数。PlanCompiler 使用持久化规则；页码来自实际 FakeWorld 查询。seed 1、8、23 的测试以及 seed 29 的独立交付运行使用不同合成内容和定位值。

匹配对照从已经完全解析的合成状态建立：同一个身份、授权、预算起点、来源资料和模型原始提议。唯一干预是对照分支停用经验。已有反馈仍在两组中。

| 观测 | 有经验 | 无经验 |
|---|---|---|
| 第二次计划 | read → locate → create | read → create |
| 定位执行次数 | 1 | 0 |
| 第二张卡片 locator | 由真实查询取得 | null |
| 卡片总数（含首次） | 2 | 2 |
| 授权变化 | 无 | 无 |

新计划及 Decision 显式引用策略 ID/revision，Episode 保留行为与核验证据。新增读取没有授权时，目标 BLOCKED，定位执行为 0；学习不能授予权限。支持撤回反馈、失效来源、停用策略。

实验分支复制只用于已解析的合成离线世界，不是通用备份恢复，也不解除备份/回放的隔离标记。

这证明了持久化经验对编译计划和实际行为的因果影响；不声称验证了真实 LLM 的语义泛化、人格质量或主观意识。

## E01—E20

| 编号 | 结果 | 实际依据 |
|---|---|---|
| E01 | PASS | 重复事件 100 次，目标、计划、卡片各一次 |
| E02 | PASS | 规范来源键跨渠道去重 |
| E03 | PASS | 外部提交后真实 SIGKILL，读取恢复成功 |
| E04 | PASS | 调用前真实 SIGKILL，禁止重发 |
| E05 | PASS | 可提出目标；缺 Grant 执行次数 0 |
| E06 | PASS | 预留后过期或撤销，派发被拦截 |
| E07 | PASS | 多维原子预留，竞争进程不能超额 |
| E08 | PASS | 未知不退款、不盲重试，核验尝试有预算 |
| E09 | PASS | UTC/偏移解析、未知时间、重启原始时间保持 |
| E10 | PASS | 模型伪造状态、成功和回执字段被拒绝；目标重定向被拒绝 |
| E11 | PASS | 独立进程重启，身份、历史与策略恢复 |
| E12 | NOT_RUN | 真实双模型语义迁移属 S5，本轮明确不执行 |
| E13 | PASS | 经验明确引用，新增读取真实发生 |
| E14 | PASS | 匹配快照与相同提议的行为消融 |
| E15 | PASS | 未授权新增读取被拦截；扩权规则拒绝 |
| E16 | PASS | 范围反例与无关事件不应用策略 |
| E17 | PASS | 反馈撤回和支持证据失效均暂停策略 |
| E18 | PASS | 旧备份隔离，不重复发送；通用恢复解锁未实现 |
| E19 | PASS | 完整投影回放、元数据仅指定恢复标记不同；外部调用 0 |
| E20 | PASS | 定时唤醒去重，不自动称为自主目标 |

逐项实际测试 nodeid、通过/跳过状态见 acceptance_results.json，不用本表替代测试执行。

## 最小实现修正与范围

- 写动作最多派发一次，NOT_APPLIED 不开放自动重试；保留安全状态，后续重试策略需单独实现。
- Attempt 增加 EXECUTE/VERIFY 类别；核验仍关联动作、授权和预算。
- 身份当前 revision 保存在 identities，历史版本可由追加事件恢复；暂不增加未使用的身份演进接口/表。
- 只有 reading 能力 v1 和本地 Operator 信任边界；动态能力安装、账号/宿主绑定及远端认证未实现。
- 策略只支持受限 ADD_READ_STEP/locator；自由文本经验语义归纳未实现。反馈原文与结构化意图严格区分。
- 预算成本是模拟整数单位；没有真实计费结算、付费 ModelPort 或时间周期自动续额。
- ContextBuilder 的 4000 字符裁剪只供工程夹具，标记 EXCERPT 并保存完整原文；真实模型 token 预算待 S5。
- 完整遗忘、复杂记忆冲突、通用检索和自动人格演进未实现；证据失效是撤回支持，不冒充删除所有私人数据。
- POSIX 单实例、一个活跃目标、顺序能力执行；未接入任何生产宿主或执行 Worker。
- Scheduler 只实现当前实验需要的持久化唤醒，不实现通用 cron 系统。

这些收缩没有改变身份保持、证据不伪造、授权不扩张、预算按尝试、UNKNOWN 不重发等关键不变量。

## 费用与下一阶段

付费模型调用 0；B站/QQ/AstrBot/Iris 生产调用 0；实验真实外部服务费用 0。开发只下载 pytest 等公开开发依赖，并本地构建包；fake cost_micro_units 是模拟额度。

S5 需要：明确授权的两个真实模型/端点或开发机离线权重；符合 ModelPort 的适配器；调用预算、超时和禁隐式重试；相同冻结连续性快照；用于评估身份、经验理解与计划质量的未见案例；顺序运行以避免双 Runtime 常驻。没有执行 S5，也没有执行 S6。


最终接口核对（C-024）：ModelRequest 同时携带 identity_id、identity_revision 和持久化 identity_snapshot。重启测试比较三者，身份内容不由模型重新生成；最新证据已重新生成。
