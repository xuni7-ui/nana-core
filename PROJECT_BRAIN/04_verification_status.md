# PROJECT_BRAIN / 04 实现与验证状态

> **证据四档制（2026-10-10 P1 重构）**。按姐姐裁决第 4 条：**每次任务都要区分「已实现 / 已测试 / 已运行验收 / 未知」**，四档**不可互相顶替**。
> 来源分级：`[实测]` 本机只读命令 ｜ `[账本]` 生产动作账本 `ledger.json`（只读） ｜ `[文档]` 服务器既有报告 ｜ `[聊天记忆]` 未复核线索。

---

## 〇、四档定义（判定标准）

| 档位 | 判定标准 | 能证明什么 |
|---|---|---|
| **① 已实现** | 代码/文件**存在**，有 md5 与行数 | 只证明"写了"，**不证明能跑** |
| **② 已测试** | 有**测试运行记录**（pytest/mock/离线用例） | 证明**当时**离线通过，**不证明**真实环境可用 |
| **③ 已运行验收** | 有**真实环境**的成功记录（真实发送/真实轮询/真实返回） | 证明**那次**真实跑通，**不证明**当前仍在跑 |
| **④ 未知** | 无证据，或证据不足 | 一律按未达标处理 |

> ⚠️ **降级规则**：原稿（旧版 04）中标注为"已验证"、但来源为 `[聊天记忆]` 的条目，本次**一律降级**至 ①/②/④，**不得**再写作"已验证"。

---

## 一、① 已实现（代码存在，`[实测]`）

| 能力 | 证据 |
|---|---|
| Iris 三层记忆（L1/L2/L3）+ 知识图谱 + 画像 | 生产 `iris_memory/{l1_buffer,l2_memory,l3_kg,profile,image}` 存在；一级子包 16 个 |
| 记忆检索纪律 v3.4（语义闸门） | `semantic_gate.py`、`decision_log.py` 存在于生产 |
| 动作账本 | `plugin_data/astrbot_plugin_iris_chat_memory/action_ledger/ledger.json` 存在，`version=1` |
| B站 Agent 骨架 | `bili_agent.py` **911 行**（副本 md5 = 生产） |
| B站事件泵 | `bili_event_pump.py` **466 行** + 自制插件 `nana_bilievent/main.py` 131 行 |
| B站发送核心 | `bili_send_core.py` **378 行**、`bili_send_comment.py` 31 行、`bili_reply_comment.py` 31 行 |
| B站保活/登录 | `bili_refresh.py` 75 行；登录工具（qr_login 系列，生产 `[实测]` 存在） |
| 健康巡检 + 封板指纹 | `nana_bili_health_check.py` **202 行** |
| C.5-V 视频理解离线骨架 | `c5v/bili_video_vision.py` **496 行** + `README_c5v.md` |
| 奈奈自制插件 4 个 | `nana_admin_guard` 39 行 / `nana_anchor` 121 行 / `nana_bilievent` 131 行 / `linna_tmp` 48 行 |

> 合计：副本 `src/` **22 个文件**；B站外挂 **10 文件 / 2681 行**。

---

## 二、② 已测试（有测试运行记录，离线/mock 级）

| 能力 | 测试证据 | 来源 |
|---|---|---|
| Agent 骨架编排层 | `test_bili_agent.py` **15/15 全绿(mock)** + 静态自检 | `[账本]` `bili_agent_skeleton_offline.verify` |
| 发送可靠性状态机 | **9/9 mock 全绿** + 真实 B站**只读** precheck 命中 | `[账本]` `bili_send_reliability_v1.verify` |
| C.2 收口（`code is None → PENDING_VERIFY`） | **T1–T11 离线全绿** + 静态穷举 RETRYABLE 仅 1 处带守卫 | `[账本]` `bili_send_c2_closure.verify` |
| 记忆检索纪律 v3.4 | **pytest 420 passed**（基线 406 + 新增 14） | `[账本]` `code_version.verify` |

> ⚠️ 全部为**离线/mock**级证据；**不构成**真实环境可用性证明。

---

## 三、③ 已运行验收（真实环境，有实据）

| 能力 | 真实证据 | 时刻 |
|---|---|---|
| **C.2 首次真实发送闭环** | `bili_comment_last_action.state=VERIFIED`，note 含真实 `rpid=316556442641`、`BV1W7TM6JEFX`；`bili_agent_last_task.state=DONE`（`op=BiliAgent:reply`，`revision=22`） | 2026-10-09 19:31:09 |
| **B站事件泵真实常驻** | `bili_event_pump_last_poll.state=OK`，`revision=3709`，`note=mode=act 新事件=0 处理=0 真实发送=0` | 心跳 **2026-10-10 02:20:00**（本次读取时刻仍在刷新） |
| 记忆持久化全链路 | `memory_persistence_v1.state=active`（写侧+回读侧+账本块） | 2026-10-06 22:14:36 |
| 对话流水回读（治断片 v1） | `flow_rehydrate_lines=12`、`ledger_inject_items=5`，自测命中 | 2026-10-06 19:39 |
| 数据库 WAL 回写 | `db_wal_checkpoint=done`，(busy,log页,已回写页)=(0,712,712) | 2026-10-06 22:14:36 |

> ✅ **结论**：C.2 真实闭环与事件泵常驻**有账本级硬证据**。
> ⚠️ 但所有"已运行验收"均**只证明对应时刻**；未重启、未复跑，**不代表当前仍通过**。

---

## 四、④ 未知（无证据 / 证据不足 → 一律按未达标）

| # | 项 | 为何未知 |
|---|---|---|
| U1 | **C.4 事件接收与去重是否端到端达标** | 有 `bili_event_pump.py` + `bili_event_state.json`，但**无端到端验收证据** |
| U2 | **C.7 缺陷"OBSERVE 吞靶子"是否修复** | 仅有缺陷记录文档，**无修复验证** |
| U3 | **运行态 vs 源码态是否一致** | `ps -e` 在本命名空间返回 **0 行**，**无法**探测进程；指纹只证明采集时刻 |
| U4 | `message_hook.py` 是否已有账本写侧分支 | 未复核（原判断仅来自 `[聊天记忆]`） |
| U5 | 上游 v0.3.0 ↔ 现行逐行差异 | 本地无 `.git`、未联网 |
| U6 | 真实内存用量（MemTotal/MemFree） | 本命名空间**无 `free`**，无法实测 |
| U7 | 72h 观察期是否已完成 | `[聊天记忆：进行中]`，**无**开始时刻的实测锚点 |
| U8 | `astrbot_plugin_favour_ultra` 为何仅在 `plugin_data/` | 仅见残留目录，未见插件本体 |

---

## 五、明确"未实现 / 未做"

- **Nana Core 抽离（M1/M2/M3）**：仅方案，**零代码**。
- **Portable 运行环境**：仅方案，**零代码**。
- **Codex 自动协作桥**：`@codex` 触发机制**未实测**，**不得**写作"已实现"（见 `07_ROADMAP.md` 与 `10_DECISIONS.md`）。
- **本地版本控制**：本轮 P1/P2 前无 `.git`（本轮已补，见 `11_CHANGELOG.md`）。

---

*本文件由奈奈于 2026-10-10 按"证据四档制"重构；旧版"已验证"措辞已按降级规则作废。*
