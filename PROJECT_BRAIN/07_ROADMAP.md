# PROJECT_BRAIN / 07 ROADMAP（主线路线图）

> 创建：2026-10-10 ｜ 状态：**新建（P2）**
> **纪律**：Codex 是**工具**，不是新主线。规划项**不得**写成已实现。优先级**不因 Codex 接入而改变**。
> 档位沿用 `04` 的四档：① 已实现 ② 已测试 ③ 已运行验收 ④ 未知 / 规划。

---

## 一、主线总览

| 线 | 名称 | 当前档位 | 下一里程碑 |
|---|---|---|---|
| **L1** | B站 Agent（C 系列） | ①–③ 混合 | C.4 事件端到端验收 |
| **L2** | Iris 记忆系统 | ①–③ 混合 | Stage-0 Memory Audit |
| **L3** | Nana Core 独立化 / C Persistent Self | **OFFLINE_CANDIDATE READY** | C-V2 已实现/离线验证；真实接入另行验收 |
| **L4** | D Continuous Runtime & Persistent Presence | **OFFLINE_CANDIDATE READY** | 独立 Runtime 已实现/离线验证；真实接入另行授权，无生产部署 |
| **L5** | 插件与接口维护 | ① 已实现 | 变更即记录 |
| **LX** | 工程基建（事实源 / 版本 / 协作桥） | ①–② | 协作桥**机制已离线验证**，真实 Runner 待一次性授权 |

---

## 二、L1 · B站 Agent

**目标**：奈奈能自己 Observe → Understand → Decide → Act → Verify → Record，并对"这个事件值不值得行动"做判断。

| 子项 | 档位 | 证据 / 备注 |
|---|---|---|
| C.1 Observe / Understand-Decide | ② 已测试 | `[账本]` 15/15 mock 全绿 |
| C.2 发送状态机（首次真实闭环） | ③ 已运行验收 | `[账本]` 2026-10-09 19:31 VERIFIED |
| C.2 收口（PENDING_VERIFY 补洞） | ② 已测试 | `[账本]` T1–T11 离线全绿 |
| C.4 事件接收与去重 | ④ 未知 | 有代码有状态文件，**端到端未验收** ← **下一里程碑** |
| C.5-V 视频理解（Evidence Gate） | ② 已测试 | 离线骨架 done；**适配层 `c5v_wiring.py` 已实现 + 11/11 离线通过**；**生产接线未做**（待授权） |
| C.7 缺陷：OBSERVE 吞靶子 | ④ 未知 | 有缺陷记录，**修复未验证** |

**依赖**：无新增系统；复用 `TaskScheduler` 串行机制（**不要**用写锁锁 B站 IO）。
**阻塞**：无硬阻塞；缺"端到端验收"这一动作。

---

## 三、L2 · Iris 记忆系统

**目标**：现状可审计、遗留问题收敛、可靠性可证明。

| 子项 | 档位 | 证据 / 备注 |
|---|---|---|
| 三层记忆 L1/L2/L3 + KG + 画像 | ① 已实现 | 目录结构 `[实测]` |
| 检索纪律 v3.4（语义闸门 + 决策日志双门） | ② 已测试 | `[账本]` pytest 420 passed |
| 记忆持久化全链路（治断片 v1） | ③ 已运行验收 | `[账本]` 2026-10-06 |
| **Stage-0 Memory Audit** | 规划 | 需 72h 观察结束（`[聊天记忆]`） |
| Iris 上游 ↔ 现行差异 | ④ 未知 | 本地无 `.git`，未联网 |

**遗留问题**：`p0_coref_backtrace`（指代硬回溯）账本 `state=pending` `[账本]` — **未完成项，需复核是否仍有效**。
**依赖**：L3 的 M1 以本线审计结果为前提。

---

## 四、L3 · Nana Core 独立化（当前 C-V2 离线候选 READY）

当前入口（2026-10-15）：C = Persistent Self & Autonomous Personality Foundation，
OFFLINE_CANDIDATE READY，基线 ea65dab。以下 M1–M3 表保留原规划记录，
不再表示当前零代码状态；现行实测证据见 09_STATE 和 C-V2 delivery。

**目标**：身份 / 记忆 / 状态 / 目标 / 计划 / 行动 / 经验学习 七要素独立可控。

| 里程碑 | 内容 | 档位 |
|---|---|---|
| **M1** | 记忆地基 + NanaState | **规划，零代码** |
| **M2** | Core API + Capability | **规划，零代码** |
| **M3** | Goal + Agency + Learning | **规划，零代码** |

**硬约束（架构纪律）**：
1. **单 Runtime / 单主进程 / 单事实源** —— 4G 内存下禁止双跑。
2. Core 抽离走**同进程「影子写入 / 对账」**，**不是**两个 Runtime 并行。
3. 旧路径仍是**生产事实源**，验证一致后才切换。

**M3 验收标准（不可放宽）**：必须完整跑通一次
`Goal → Plan → Act → Verify → Failure/Result → Strategy Update → Continue/Complete → Experience`。

---

## 五、L4 · D Continuous Runtime & Persistent Presence（CURRENT DEVELOPMENT STAGE）

当前入口（2026-10-15）：独立开发 D-V1 Runtime，继承 C SubjectLoop。
以下“当前不动”为2026-10-10历史前置条件，现由 C-V2 READY 满足开发前置；
不授权生产常驻第二 Runtime、真实 G 感知或 E 执行。

- Portable 可移植运行环境；统一能力接口（Capability 抽象）。
- **前置**：L3 稳定之后。**当前不动**。

---

## 六、L5 · 插件与接口维护

- 生产插件 **23 个**（22 `astrbot_plugin_*` + `meme_manager`）。`[实测]`
- QQ 通道（NapCat）与 B站接口维持现状；**变更即入账**。
- 自制插件**无 LICENSE** → 分发前需姐姐指定（见 `08_TASKS.md` T-08）。

---

## 七、LX · 工程基建（本轮新建）

| 项 | 档位 | 备注 |
|---|---|---|
| PROJECT_BRAIN 事实源 | ① 已实现 | 本目录 12 文件 |
| 本地版本控制（git） | ① 已实现 | 本轮建立，**仅本地** |
| 项目账本（07–11） | ① 已实现 | 本轮建立 |
| **Codex 自动协作桥** | **② 已测试** | 闭环机制已实现并离线验证（`bridge/` 15 项用例全绿）；真实 Runner **未启用**（需授权 L3） |
| GitHub 同步 | **禁止** | 姐姐未授权 |

---

## 八、本路线图的"不做"清单

1. 不为小问题新增系统 / 记忆层 / Agent 框架。
2. 不重构 L2/L3 时间处理。
3. 不把 Codex 接入当作主线变更。
4. 不在授权外触碰生产、密钥、部署。


## 2026-10-10 独立 Core 工程增补（历史零代码口径不再描述当前副本）
[实测] S0—S4 离线连续性、S5 工程评估、S6 非生产准备已在开发副本实现与测试；E12 未验证。S6 仅合成旧来源/同进程影子/闭合 reading CapabilityPort/单模拟执行方，不代表 Portable 全框架、真实平台多工具或生产迁移完成。D-003/D-004 的小资源/单 Runtime/影子原则保持。

## L3-C-AFFECT-V1 — CURRENT DEVELOPMENT (2026-10-15)
Affective Drive, Autonomous Judgment & Governed Realization Foundation belongs
to L3 Persistent Self, inherits C-V2/D-V1 offline candidates. Own branch only;
no L1/L2/B5/R045 priority or production changes. Explicit v9, no new tables.

## L3-C-AFFECT-V1 M2 — negative-only governance / governed fixture realization
[实测·开发离线] R2 implemented: OperatorAuthority-bound controller, exact finite
negative constraints in existing events/artifacts, revision/revoke, post-Judgment
PASS/BLOCK/UNKNOWN, erasable outcome/disposition and filtered next-cycle view.
No Model/Memory/Subject authority path. Old blocked intentions do not revive.
Governed handoff uses existing ActionKernel checks and pre/post-transaction fence.
Only exact OfflineEffectPort on explicitv9 may exercise synthetic fixture actions;
no subclass/arbitrary CapabilityPort gets this exception, ordinary Shadow fences
remain. Fixture JSON is world data, not another subject DB/Store. No real effect.
Targeted22 PASS (R1/R2 + existing action/runtime boundary); latest R2 four PASS.
Full qualification/recovery matrix pending; not READY. No production changes.

## L3-C-AFFECT-V1 M3 — relationship and privacy axes
[实测·开发离线] R3 pure bounded RelationshipInfluenceView with seven facets,
domain trust/counterevidence and target-specific repair. Existing RelationshipView
retained; v9 personality/style/context use the same projector. Social expectation
comes from direct sourced norms/boundaries, not model assignment. Private social
meaning can cause self-restraint without becoming Manager authority. Hard context
privacy/task/destination/deletion/conflict checks preserved; secret canary excluded.
16 targeted PASS (new + prior projection/context); final four R1/R3 PASS after
normalized-link/time tie refinements. v9 adds only3 normalized relationship
columns on existing table; partial unreleased v9 checkpoints finalized additively.
No new tables/Store/loop; R4/R5/system qualification remain pending.
