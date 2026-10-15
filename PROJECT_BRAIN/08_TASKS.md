# PROJECT_BRAIN / 08 TASKS（任务清单）

> 创建：2026-10-10 ｜ 状态：**新建（P2）**
> **规则**：任务状态只用四档 + `BLOCKED` / `DONE`。**没有证据的不得写 DONE**。
> 每次状态变更**必须**同步 `11_CHANGELOG.md` 与 `09_STATE.md`。

---

## 一、本轮完成（P1 + P2）

| ID | 任务 | 状态 | 证据 |
|---|---|---|---|
| T-01 | P1 事实口径修正（插件 25→23 / 外挂行数 2311→2681 / 证据四档重构 / 进程可观测性登记） | ✅ DONE | `11_CHANGELOG.md` C-001 |
| T-02 | P1 指纹自指问题处理（自指条目剔除 + 外置锚点） | ✅ DONE | `manifests/fingerprints_20261010.md` 首注 + `09_STATE.md` 锚点 |
| T-03 | P2 项目账本建设（ROADMAP/TASKS/STATE/DECISIONS/CHANGELOG） | ✅ DONE | 本目录 07–11 |
| T-04 | 本地 git 版本控制建立（仅本地，无 push） | ✅ DONE | `11_CHANGELOG.md` C-002 |

---

## 二、待办 · 按主线

### L1 · B站 Agent

| ID | 任务 | 状态 | 依赖 / 阻塞 | 需姐姐？ |
|---|---|---|---|---|
| T-11 | **C.4 事件接收与去重端到端验收**（下一核心问题） | TODO | 无硬阻塞；需设计"确定性优先"的验收方案 | 需批准"跑验收" |
| T-12 | C.7 "OBSERVE 吞靶子"缺陷复核 + 确认是否已修 | TODO | 只读复核即可 | 否（只读） |
| T-15 | C.5-V-1 生产接线（把适配层接进 `_understand`） | **待授权（L4）** | 改生产代码 + 更新封板指纹；回滚=改一个环境变量 | **是（可并入 T-41 一次审批）** |
| T-13 | `test_bili_agent_semantic_retry.py` 硬编码 SESSDATA 去毒（改读 `bili_credential` 或环境变量） | BLOCKED | **改生产文件** → 需"动手"级授权 | **是** |
| T-14 | `bili_send_comment.py` 补 precheck（对齐 reply 版） | TODO | 低风险，但属生产改动 | **是** |

### L2 · Iris 记忆系统

| ID | 任务 | 状态 | 依赖 / 阻塞 | 需姐姐？ |
|---|---|---|---|---|
| T-21 | **72h 观察期结束确认**（缺开始时刻实测锚点） | BLOCKED | 需姐姐给出观察开始时刻 | **是** |
| T-22 | **Stage-0 Memory Audit**（观察期后第一件事） | TODO | 依赖 T-21 | 是 |
| T-23 | `p0_coref_backtrace` 账本 `state=pending` 复核 | TODO | 只读 | 否（只读） |

### L3 · Nana Core

| ID | 任务 | 状态 | 依赖 / 阻塞 | 需姐姐？ |
|---|---|---|---|---|
| T-31 | M1（记忆地基 + NanaState） | TODO | 依赖 T-22 | 是 |
| T-32 | M2（Core API + Capability） | TODO | 依赖 T-31 | 是 |
| T-33 | M3（Goal + Agency + Learning） | TODO | 依赖 T-32 | 是 |
| T-34 | Portable | **不排期** | 依赖 T-33 | 是 |

### LX · 工程基建

| ID | 任务 | 状态 | 依赖 / 阻塞 | 需姐姐？ |
|---|---|---|---|---|
| T-41 | **协作桥真实 Runner 启用 + 首个真实协作执行**（C.5-V-1 接线增量） | ✅ **DONE** | `23_T41_REAL_RUNNER_01.md`：`applied=True`、13 通过 / 0 失败、边界 0 违规 | — |
| T-45 | 协作桥最小闭环实现 + 离线验证（`bridge/codex_bridge.py` / `local_runner.py`） | ✅ DONE | `test_codex_bridge.py` 9/9 + `test_local_runner.py` 6/6 |
| T-46 | C.5-V-1 接线适配层（`src/bili_agent/c5v_wiring.py` + 测试） | ✅ DONE | `test_c5v_wiring.py` 11/11 |
| T-47 | **T-001 任务卡出卡 + 执行**（首个真实 Codex 协作任务 = c5v_wiring 最小增量） | ✅ **DONE（B 路线执行）** | `docs/tasks/T-001-c5v1-wiring-increment.md` + `22_PRE_T001_READONLY_RECON_01.md` + `23_T41_REAL_RUNNER_01.md` | — |
| T-48 | T-001 三项只读前置核验（祖先关系 / 远端源码 / 环境归属） | ✅ DONE（③部分未知，如实标记） | `22_PRE_T001_READONLY_RECON_01.md` |
| T-42 | 自制插件 LICENSE 决策（4 个） | BLOCKED | 需姐姐指定许可 | **是** |
| T-43 | Iris 改动 diff 的整体许可策略（AGPL 传染确认） | BLOCKED | 需姐姐决策 | **是** |
| T-44 | GitHub 首次上传 / push | **未授权** | 姐姐明确保留 | **是** |

---

## 三、真正的阻塞项（Blockers，按严重度）

| # | 阻塞项 | 影响 | 可否自行解除 |
|---|---|---|---|
| **BL-1** | 上游 v0.3.0 原始文件缺失 | 无法证明"上游↔现行"边界 | 需联网拉取 → **不可**（禁止联网安装） |
| **BL-2** | `test_bili_agent_semantic_retry.py` 硬编码密钥 | 该文件永远不得入库；生产侧仍在 | 需生产改权限 → **不可** |
| **BL-3** | 自制插件无 LICENSE | 公开分发有权利瑕疵 | 需姐姐决策 → **不可** |
| **BL-4** | 72h 观察期缺开始锚点 | 卡住 T-22 → T-31 全线 | 需姐姐给时刻 → **不可** |
| **BL-5** | 进程不可观测（`ps` 空） | 无法做进程级存活/内存证据 | **不可**（命名空间限制） |
| ~~BL-6~~ | ~~无本地版本控制~~ | — | ✅ **本轮已解除** |
| ~~BL-7~~ | ~~协作桥无可用真实 Runner~~ | — | ✅ **本轮已解除**（R13/R14 打通，`applied=True`） |

---

## 四、任务优先级（姐姐裁决：不因 Codex 改变）

1. **先收尾既有能力** → T-21 / T-11（验收与审计）
2. **再做 Core 抽离** → T-31 → T-33
3. **Coex/Sync 类基建最后** → T-41、T-44

> ⚠️ 本清单**不是**执行授权。除标注"否（只读）"外，任何条目都需要姐姐按**操作范围 / 风险等级 / 资源预算**另行授权。


---

## P3 任务收口（2026-10-10（CST））

| 任务 | 状态 |
|---|---|
| T-A AstrBot 补丁 D2 | ✅ 完成（可复现补丁 + 双源基线） |
| T-B Iris 定制 D3 | ✅ 完成（14 处清单 + 隔离材料 + 可复现补丁） |
| T-C B站 Agent / C.5-V | ✅ 完成（纳入 5 / 排除 9 / C.5-V 状态记录） |
| T-D 依赖与重建 | ✅ 完成（requirements.txt + node 重建） |
| T-E 许可证与来源 | ✅ 完成（三类划分 + 待决策） |
| T-F PROJECT_BRAIN 收口 | ✅ 完成（含更正） |
| T-G GitHub 安全同步 | ✅ 完成（非强制增量 + 远端回验） |
| T-C.5V-生产接线 | ⛔ 未做（授权禁止） |
| T-Cloud-env | ⛔ 阻塞（待姐姐） |


## Nana Core V1 独立离线任务（用户本轮直接授权）

| ID | 内容 | 状态 | 证据 |
|---|---|---|---|
| NC-S0 | 包、DTO、schema、测试入口 | ③已离线运行验收 | C-018/C-023、contracts tests |
| NC-S1 | 身份、时间、事件、证据、事务 | ③已离线运行验收 | C-019/C-023、storage tests |
| NC-S2 | 授权/预算/动作/核验/SIGKILL恢复 | ③已离线运行验收 | C-020/C-023、action_recovery_trace.json |
| NC-S3 | 单 reading_card 完整目标循环 | ③已离线运行验收 | C-021/C-023、runtime tests |
| NC-S4 | 受限经验与重启行为消融 | ③已离线运行验收 | C-022/C-023、learning_ablation.json |
| NC-S5 | 真实双模型语义迁移 | 未执行（本轮排除） | E12 NOT_RUN |
| NC-S6 | 旧系统/生产迁移 | 未执行（本轮排除） | 没有生产调用 |

不将旧 T-31—T-33 或生产事项改为 DONE。


## S5 本轮更新（C-026；上方 S5“排除”是 S0—S4 历史状态）
| ID | 内容 | 当前状态 | 证据/阻塞 |
|---|---|---|---|
| NC-S0-S4-SAVE | 私有开发分支上传与远端回验 | ③已运行验收 | `884db6a…`，git push/ls-remote 一致，main 未变 |
| NC-S5-ENGINEERING | 真实 ModelPort/冻结/顺序评估/脚本 | ③已离线运行验收 | 新增 42 pass；联合 98 pass / 1 skip |
| NC-S5-SEMANTICS | 两真实模型身份/经验/计划语义 | ④未知 / NOT_RUN | 当前零就绪开发端点；不获取生产密钥，不购买服务 |
| NC-S6 | 生产影子对账与迁移 | 未实施 | 本轮授权禁止 |


## S6 本轮范围更新（C-030；覆盖此前“未实施”的非生产部分）
| ID | 当前档位 | 证据/边界 |
|---|---|---|
| NC-S6-IMPORT | ③合成离线运行验收 | 来源/时间/覆盖范围/去重/部分崩溃恢复；旧声明不授信 |
| NC-S6-SHADOW | ③合成离线运行验收 | 同进程纯比较、零执行/预算变更 |
| NC-S6-ROUTER | ③合成离线运行验收 | 单 owner epoch、授权/尝试预算、路由幂等/恢复 |
| NC-S6-PRODUCTION | ④未验证/未执行 | 无真实导出/接线/接管，旧未决未对账 |
| NC-S5-E12 | ④未验证 / NOT_RUN | 不以 S6 夹具替代真实模型 |
# 本轮开发验证（C-032）
| 任务 | 档位 | 证据/边界 |
|---|---|---|
| NC-DEV-BOUNDARY | ③已运行验收（可见元信息） | access_boundary.json；未知路径、webhooks/外部轮询保留 UNKNOWN，未登录生产 |
| NC-DEV-READONLY | ③已运行验收 | 实际合成文件读取/独立核验、单执行方、预算、SIGKILL 与身份恢复 |
| NC-DEV-HTTP | ③已运行验收（协议） | 7 wire tests，均明确 loopback simulator；不计真实模型 |
| NC-S5-E12 | ④未知 / NOT_RUN | 当前开发端点 0、真实调用 0；需两个授权 real_model 端点 |

## L3-C-AFFECT-V1 — implementation tracker
R1 normative/disclosure/disposition: IMPLEMENTED / targeted offline TESTED.
R2–R6 and system qualification: pending. No real models/data/actions.
Evidence: docs/nana_affective_autonomy_v1_implementation.md.

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

## L3-C-AFFECT-V1 M4 — positive requests and calendar opportunities
[实测·开发离线] R4 typed positive request → Subject ACCEPT/NEGOTIATE/DECLINE.
ACCEPT only offers existing CommitmentCandidate; trusted controller materializes
idempotently, no auto-adopt/Grant/send. Reuses CommitmentService/CAS and due
attention. Stdlib zoneinfo daily recurrence handles IANA zones, fold choice, gap
next-valid-minute, missed-window coalescing and persistent occurrence keys on
existing Scheduler. Calendar only emits SELF_WAKE checks, not user experiences.
Targeted8 PASS (new calendar/requests + prior scheduler/promises), latest2 PASS.
Queue metadata scrub extended for new structured personal fields; body remains
in erasable records only. v9 extends runtime_schedules CHECK, tables still39.
R5 experience and final scenarios/recovery remain pending, candidate not READY.

## L3-C-AFFECT-V1 M5 — disposition experience gate and checked learning
[实测·开发离线] R5 meaningful candidate gate selects consequence-backed, repeated
distinct or explicitly reflected dispositions. Raw veto/read/restart is not
automatically Experience. Typed independent verifier proves non-execution fact
without claiming reasoning correctness; later observed consequences supply a
separate assessment. Existing ExperienceService/Reflection/lesson trial/review
lifecycle supports NON_EXECUTION and a narrow consequence-review rule. Replaying
one candidate cannot create duplicate experience. Source erasure purges candidate/
proof/experience support while independent Manager source survives.
Targeted9 PASS (new experience + prior learning/privacy), final2 PASS. No new
tables: existing experiences CHECK extended and records opaque target lookup
column/index added; same Store/privacy/replay. Manager facts no longer become
automatic transitive normative dependencies in every future cycle.
Major full regression and final system qualification pending; NOT_READY yet.


## L3-C-AFFECT-V1 M6 — system and recovery qualification (OFFLINE)
[实测·开发离线] S1–S15 and two independent generic Subjects PASS; 60 virtual days
PASS with bounded pending/candidates/hot state, one veto history, no social/model
spam. Six actual tracked local SIGKILL/reopen cuts PASS, including UNKNOWN effect
verification without re-execution. Explicit v7→v9/v8→v9 preserves IDs/history,
foreign_key_check clean, managed backup/replay quarantine and erasure honored.
Production pins/real memory ingress unchanged. v9 adds0 business tables; default
C7 and D8 unchanged. Major full at f513dcc:900 passed/0 failed/1 skipped(E12).
Targeted C/D/new qualification:65 passed. Final full regression still pending.
Hardening: definition-only governance changes do not rewrite normative context;
resource classification is pinned to sourced cue and denied at realization;
post-check races persist veto without Action; filtered constraint view includes
revision/source/effective window. Hidden relationship counterevidence yields
PARTIAL/UNKNOWN coverage without loading its body. Source-erased disclosure is
unavailable. No real world/production/host/model/private input used.
