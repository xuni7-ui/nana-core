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
