# Nana Core Architecture V1 — S6 非生产迁移准备

> [实测] 2026-10-10；基线 `6491aa6ddadd63e23035f69dd18a218b70ccf650`。
> 本轮只交付合成导入、同进程影子、统一 CapabilityPort 和单一模拟执行方。
> 生产数据导出、真实宿主接线、生产执行权迁移和 S5 E12 **未验证/未执行**。

## 结果与证据

新增 **29 个 S6 测试全部通过**；S0—S6 联合回归 **127 passed / 0 failed / 1 skipped**。
CLI 实际运行不同进程：合成旧记忆导入 → 影子观察 → 模拟旧执行方完成卡片 → 反馈/经验 →
新进程 → 合成执行方换主 → 新卡片 → 提交后 SIGKILL → 新进程读取核验恢复 → 全状态回放。

实际结果：

- 稳定 identity_id、revision、身份内容和历史前缀一致；原始时间及未知时间保持。
- 四条旧来源记忆各导入一次，重复批次没有新增记录。
- 影子零能力调用；学习后捕获 read→create 与 read→locate→create 的步骤差异。
- 只有选中执行方可调用统一接口；未决禁止换主，旧 epoch 绑定不可复用。
- 三张卡片、八次能力执行（含读取），八次独立核验；定位读取两次；无重复副作用。
- 卡片提交后真实 SIGKILL `-9`；恢复没有模型重规划/重新执行，所有动作经核验完成。
- 追加事件完整回放与原投影一致，仅已声明的本地 quarantine 标记不同。
- 真实模型、生产服务调用、外部模型费用均为 0；E12 保持 NOT_RUN。

完整节点：[test_results.json](nana_core_s6_evidence/test_results.json)；
联合输出：[nana_core_s6_test_output.txt](nana_core_s6_test_output.txt)；
跨进程/崩溃/来源证据：[migration_report.json](nana_core_s6_evidence/migration_report.json)。

仓库未找到独立同名《奈奈工程总纲》文件；本轮使用用户明确边界、PROJECT_BRAIN 的
07_ROADMAP / 10_DECISIONS（尤其 D-003/D-004）及既有 Architecture V1 实现契约，不编造总纲条文。

## 实现位置与最小契约

| 文件 | 职责 |
|---|---|
| `src/nana_core/migration/legacy.py` | 严格 LegacyRecord、原文/来源/覆盖范围、时间转换、事务导入/去重、原始来源读取 |
| `shadow.py` | 同 Store 影子观察与纯计划差异；不持有 CapabilityPort 或 Runtime |
| `routing.py` | 实现现有 CapabilityPort；闭合三能力注册、持久执行方 epoch、尝试预算/授权与路由幂等 |
| `experiment.py` | 新进程连续性、换主、实际 SIGKILL、独立恢复和回放的 CLI |
| `tests/migration/` | 导入/影子/路由/故障与完整实验测试 |

**零新增 Core 表、零新增依赖、无宿主导入。** 使用原 15 表 schema v1。
`ContextBuilder.build(..., suspend_invalid=False)` 是唯一 Core 行为接口增量：
影子仍过滤失效经验，但不暂停/改写策略。默认路径保持原来的失效策略暂停行为。

LegacyRecord 要求显式 synthetic_only=true、synthetic: 数据集、源系统、记录 ID/修订、
认知类型、content 及覆盖范围、原始 source_payload 及覆盖范围、原始时间和明确时间单位。
没有数据库路径、凭据字段或自动生产导出入口。source_payload 保留包括空白的精确字符串；
完整 import envelope 的 FULL 标签不表示完整原始历史。摘要仍 SUMMARY，缺失原文仍 UNAVAILABLE，
跨旧系统的来源 ID 标为 UNRESOLVED_LEGACY_REF，不编造 Core 证据指向。

旧 USER_STATEMENT、MODEL_INFERENCE、SUMMARY、ACTION_CLAIM 进入 CLAIM/UNASSESSED，
不创建 identity/Grant/Action/Strategy；旧 VERIFIED 只是来源声明，不能证明执行成功。
同系统/数据集/记录 ID/修订唯一；同键内容不同拒绝，显式新修订保留另一条历史。
每记录事件、证据和记忆同事务提交；批次不伪装整体原子，已提交部分可去重恢复。

ISO 时间必须带偏移/时区；秒/毫秒由 time_format 明确指定；无效/无单位/无时区为 UNKNOWN，
不使用导入或重启时间补齐。发生/观察/记录时间沿用 Core 原字段。

## 影子和执行边界

ShadowObserver 只接收合成 Observation 和已生成的严格计划建议，记录观察/对照。
不调用模型，不请求授权、不创建目标/行动，不消耗预算。其结果是 advisory draft，
没有通过 Runtime 的目标完成条件就不会成为可执行计划。
相同事件/比较修订去重；同键输入改变拒绝，新比较需显式修订；初次/重启返回相同 JSON 结构。

CapabilityRouter 复用现有 Invocation/Receipt/Verification 和 ActionKernel：

- 本地受信 Operator 选定 `legacy_simulator` 或 `core_simulator`；shadow 永远无执行权。
- owner/epoch 写入 core_meta，并有追加事件；绑定携带 epoch，换主后旧绑定失效。
- 任何未完成 Action 或活跃 Goal 阻止换主；quarantine 保持禁止，不实现通用解除隔离。
- 派发要求 Core DISPATCHING、相同参数 hash/幂等键/尝试 ID、有效 Grant 与已记账预算。
- 每动作持久路由 claim 提交后才调用后端；同动作不得第二次派发；核验也按独立尝试 claim。
- UNKNOWN 不退款或盲重发；恢复通过原 ActionKernel + 真实 FakeWorld 读取核验。

这些是受信同进程接口边界，不是针对任意恶意 Python 插件的 OS 沙箱。
闭合注册表只覆盖当前三种 reading 能力，不提前开发动态工具/插件加载或多 Agent 框架。
多步骤 read/locate/create 经同一接口协作，不能据此宣称已经接入多个真实外部工具。

模拟旧执行方也使用原 ActionKernel；没有执行旧 AstrBot/Iris/B站的业务代码。
因此本轮证明迁移机制不变量，**不能证明真实旧系统与 Core 已对账一致**。
真实旧未决动作也未导入/核销，不能将本轮合成换主视作生产接管条件。

## 分阶段记录与修复

1. 导入闭环：14 tests，通过后提交；首次 14 failed 是浮点有限值约束误作用于时间的字符串分支，
   改为只约束 float 后通过，未削弱断言。
2. 影子/单执行权闭环：累计 27 tests，通过后提交。初次 2 failed：首次/重复返回的 tuple/list
   不一致，以及攻击测试在构造 Invocation 前已被严格 DTO 拒绝。规范化返回并构造实际攻击输入后通过。
3. 完整 CLI 与回归：最终 29 个 S6 测试及 127 联合测试通过；增加“缺少合成声明不能默认导入”检查。

所有这些错误及修复已记录于 C-028—C-030，不把早期失败改写为通过。
当前 stdout/JUnit 记录的是最终完整运行；早期节点结果取自实际 pytest 工具输出和变更账本。

## 复现与后续条件

```bash
.venv/bin/python -m pytest tests/offline_continuity tests/semantic_migration tests/migration \
  --s6-report /tmp/nana-s6-tests.json
.venv/bin/nana-migration --output /tmp/nana-s6-new-experiment
```

实验输出目录必须不存在；只在开发路径运行，固定生成全合成资料，零网络模型请求。
无需两个自治 Runtime 常驻；子进程顺序运行，每个进程只有一个实际执行 Runtime。
归档 JSON 不含 DB、WAL、lock、真实用户内容或凭据。

未实现/未验证：真实记忆导出与字段映射、真实来源对账和冲突裁决、生产执行权接线、
旧未决动作核验、实际平台幂等/核验能力、真实模型 E12、通用备份解除隔离与通用 MemoryIndex。
未来生产迁移需要单独授权、脱敏导出及真实 schema 映射、旧系统未决对账、全部副作用
入口统一接线与回滚证据；本轮不读取生产来提前解除这些条件。
原创许可仍由所有者决定；未复制第三方 AGPL 实现进入 Core。
