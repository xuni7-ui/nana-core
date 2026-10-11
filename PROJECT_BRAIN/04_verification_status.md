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
| C.5-V-1 接线适配层（本轮新增） | `src/bili_agent/c5v_wiring.py` + `test_c5v_wiring.py`；`docs/c5v_wiring_design.md` |
| 协作桥最小闭环（本轮新增） | `bridge/codex_bridge.py` / `local_runner.py` / 2 个测试 / `README.md` |
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
| **C.5-V-1 接线适配层** | `test_c5v_wiring.py` **11/11**（含"失败逐字节还原""不编造""零公网"断言） | `[实测]` 2026-10-10 本副本 |
| **协作桥最小闭环** | `test_codex_bridge.py` **9/9** + `test_local_runner.py` **6/6**（含 127.0.0.1 真实 HTTP 闭环 + 源仓只读哈希断言） | `[实测]` 2026-10-10 本副本 |

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
| U5 | 真实 Runner 能否在本机端点跑通 | 桥**机制**已离线验证，**真实编码能力**未验证（`codex` 未安装；外部端点未启用） |
| U6 | 真实内存用量（MemTotal/MemFree） | 本命名空间**无 `free`**，无法实测 |
| U7 | 72h 观察期是否已完成 | `[聊天记忆：进行中]`，**无**开始时刻的实测锚点 |
| U8 | `astrbot_plugin_favour_ultra` 为何仅在 `plugin_data/` | 仅见残留目录，未见插件本体 |
| U9 | 上游 v0.3.0 ↔ 现行逐行差异 | 本地无 `.git`、未联网 |

---

## 五、明确"未实现 / 未做"

- **Nana Core 抽离（M1/M2/M3）**：仅方案，**零代码**。
- **Portable 运行环境**：仅方案，**零代码**。
- **协作桥的"真实编码能力"**：桥**机制**已实现并离线验证（见 §二），但 `codex` **未安装**、
  外部端点**未启用** → 「奈奈↔Codex 真实自主协作」**只能算"机制就绪"**，
  **不得**写作"已打通"（待 `10_DECISIONS.md` D-023 授权）。
- **C.5-V-1 生产接线**：适配层已实现+离线测试通过，**未接生产**。
- **本地版本控制**：本轮 P1/P2 前无 `.git`（本轮已补，见 `11_CHANGELOG.md`）。

---

*本文件由奈奈于 2026-10-10 按"证据四档制"重构；旧版"已验证"措辞已按降级规则作废。*


---

## P3 增补 · 本轮已验证（2026-10-10（CST））

| 项 | 证据 | 等级 |
|---|---|---|
| AstrBot 补丁对干净基线往返一致 | sha256 相等 | 【实测】 |
| Iris 补丁对 241 文件基线往返一致（14 文件） | sha256 相等 | 【实测】 |
| Iris 14 处改动权威性（7改+7增） | blob SHA1 全量比对 | 【源码确认】 |
| AstrBot 基线双源一致 | PyPI sdist == GitHub tag | 【源码确认】 |
| B站 5 登录脚本无真值凭据 | 值级扫描 | 【实测】 |
| Codex CLI 已安装 | 0.162.0 | 【实测】 |
| 本地 Bridge Runner 闭环 | applied=True/13-0 | 【实测】 |
| Codex **Cloud** 闭环 | **未达成**（environment 未建） | 【未知/待验证】 |


## Nana Core V1 S0—S4（2026-10-10，独立合成环境）
[实测] ③已离线运行验收：完整循环、真实进程重启、SIGKILL 恢复、受限经验/消融。56 passed / 0 failed / 1 skipped；E12/S5 真实模型语义未验证；生产运行未验证。
证据：`docs/nana_core_v1_implementation.md`、`docs/nana_core_v1_evidence/acceptance_results.json`。


## Nana Core V1 S5 增补（2026-10-10）
[实测] 工程③已离线运行验收：42 个 S5 测试；完整联合回归 98 passed / 0 failed / 1 skipped。实际测试节点见 `docs/nana_core_s5_evidence/engineering_results.json`，完整 JUnit 和命令输出同目录。
[实测] 16 个顺序工程子进程恢复相同身份和历史；经验组真实 FakeWorld 定位=1，对照=0；授权边界与范围反例通过。标记 transport_fixture，真实调用 0。
[未知] E12 真实双模型语义 NOT_RUN，当前无就绪开发端点；不能把该工程成功写成模型语义成功。
[实测] 初次联合运行 4 个收集错误，S5 测试命名空间修正后解决；保留初始错误记录，不削弱断言。


## S6 非生产准备验收（C-030）
[实测] 29 个新增 S6 测试通过；S0—S6 联合 127 passed / 0 failed / 1 skipped。来源和测试节点 docs/nana_core_s6_evidence/test_results.json，联合 JUnit 同目录。
[实测] 不同进程恢复相同身份、来源/原始时间、经验和唯一 owner；三张卡片/八次能力执行/八次核验；真实 SIGKILL -9 后恢复不重规划、不重发；全投影回放一致。
[未知] 真实旧数据格式映射、真实宿主对账与接管、跨真实模型 E12；未运行生产。
# 开发真实能力准备（C-032）
- [实测] ③已运行验收：受限合成文件只读端口，经原 ActionKernel/CapabilityRouter 授权、预算、单执行方、独立核验；跨重开身份一致，源文件未变，无重复卡片。
- [实测] ③已运行验收：31 个新增测试；联合 158 passed / 0 failed / 1 skipped。真实 SIGKILL 后零重执行/一次核验重读；7 个实际 loopback HTTP 协议测试通过。
- [实测] 协议成功不等于模型推理：新增 service_kind，未声明/模拟器调用不能计入 E12；首次自主定位没有学习效应时明确 NOT_DEMONSTRATED。
- [未知] ④未知：真实模型/E12、生产 SSH/容器与挂载来源、远端 webhooks 和外部轮询。Docker 默认沙箱 socket 请求 PermissionError；hooks API 403；未请求扩大生产权限。
- 证据：docs/nana_core_development_validation.md 与 docs/nana_core_development_evidence/。既有离线验收不替代真实双模型。

## Phase III Entry 最终（C-046）

- [实测] ②已测试：Iris正式适配、最小跨来源冲突与范围隔离、GoalCandidate/initiative结构6/6、模型metadata/选择；零新SQL表/依赖。全量263 passed/0failed/0errors/1skip。
- [实测] ③已非生产运行验收：14 synthetic真实schema记录跨进程导入/重启去重/源与时间/身份/replay；SIGKILL恢复不重复、工程经验消融保留。不是私人DB或生产迁移。
- [未知] ④：公网DNS/TLS阻塞，origin HTTP0；E12 NOT_RUN（真实模型0）；P7真实Iris FAISS parity NOT_RUN；P11工程execute禁用；主动风险判断真实语义未知。完整阶段与证据见docs/nana_core_phase3_entry.md及final_delivery.json。

## Cloud bridge C-053
[实测] ②宿主Adapter/只读snapshot exporter/preflight/authority协议/initiative/Persona fixtures；③两个synthetic shadow CLI进程及真实dev工程patch/test/commit/SIGKILL恢复；全量281pass/0fail/1skip。④生产runtime/hook/version/private migration/authority翻转/真实模型E12未验证；公网BLOCKED，工程任意代码执行未启用。证据docs/nana_cloud_evidence/final_delivery.json与final_junit.xml。


---

## Shadow Bind R02 · M1–M4（2026-10-11 CST）

### M1 = runtime topology + hook audit
- [实测] ①已实现：`docs/nana_shadow_astrbot_dispatcher_audit_20261011.md`（P2 十问 + dispatcher map，全部带 path+symbol+line）。
- [实测] ③已运行验收（只读）：AstrBot 4.28.0 / CONTAINER / `ASTRBOT_RELOAD` 未设 —— 均为宿主实测，非文档推断。
- [未知] ④：`host_binding` 仍 `UNVERIFIED`。

### M2 = observer 实现 + 离线测试
- [实测] ①已实现：`src/plugins/astrbot_plugin_nana_shadow_observer/`（3 文件，开发副本，**未安装**）。
- [实测] ②已测试：`python3 -m pytest tests/nana_shadow -q` → **9 passed**（zero-plaintext / fail-closed / 白名单 / handler 返回 None）。
- [实测] 打包：`artifacts/nana-shadow-observer/nana_shadow_observer-0.0.1-dev.tar.gz`
  sha256 `27fc75d98388d0890c4b7eeca67671b4b475f885c85938a958e0b1e9245e66fa`（确定性复算通过）。
- [未知] ④：未加载 / 未注册 / probe 未跑。

### M3 = real registration BLOCKED
- [实测] ①已实现：`docs/nana_shadow_registration_blocker_20261011.md`、`docs/nana_shadow_observer_dev_20261011.md`。
- [实测] 状态：`FIRST_REAL_ASTRBOT_SHADOW = BLOCKED`；`Permitted dynamic load channel = BLOCKED_AUTH_REQUIRED`；
  `Real dispatcher probe = BLOCKED_NO_INTERNAL_PROBE`（生命周期 hook 是 plugin manager 直调，**不构成**真实 dispatcher probe）。
- [未知] ④：无 `BLOCKED_RESTART_REQUIRED`（框架层动态加载能力已被源码证明存在）。

### M4 = Iris schema-only 兼容
- [实测] ①已实现：`docs/nana_shadow_iris_schema_20261011.md`。
- [实测] ③判定：**`SCHEMA_COMPATIBLE`** —— Iris 0.3.0 的 11 类形态与 `src/nana_core/migration/iris.py:11-35` 的 `FIELDS` 逐字段一致；
  L2 `metadata.db` / L3 `graph.db` 用 **`mode=ro`** 实读 `sqlite_master` 交叉验证；`index_meta.json` 实读键名。
- [实测] 私人值读取 = **0**（只取结构元数据）。

### 回归口径（重要）
- [实测] nana_core 全量套件在本宿主解释器下 `65 failed / 171 passed / 82 errors`，
  **全部**落点 = `SQLITE_VERSION_UNSUPPORTED`（`src/nana_core/storage/sqlite_store.py:78`，需 SQLite ≥3.51.3；宿主三解释器均 3.46.1）。
- [实测] 此为**既有环境门槛**，与 R02 观察器改动无因果；观察器 9/9 在宿主解释器独立通过。


---

## Shadow Bind R03 · M0–M6（2026-10-11 CST）

### M0 = 双分支合流（本地，未 push）
- [实测] 在开发副本 `/root/nana_dev/nana-core` 从 Codex 交付 **bundle** 离线合流（零网络依赖）：
  bundle sha256 `38b53b1598675cc81a12f376c11829bd0dd94e47c6cc817dc1c56f1d225439de`，
  `git bundle verify` = ok，`list-heads` = `10581aea4009add4e311bb0df843fbedffa7acfb refs/heads/dev/nana-core-v1-astrbot-shadow-bind-codex`。
- [实测] `merge-base HEAD bundle/codex` = `c3ada9b09faa8a2683f98d5c8bafec24779cfd71`（与任务书预期**逐字一致**）。
- [实测] 合流提交 **`d3e8c818e9c770c10555e8731d65ab5dab74b019`**（`--no-ff`，双亲 `652a72f` + `10581aea`）。
- [实测] 冲突仅 3 个 PROJECT_BRAIN 文件（`09/10/11`），**逐块并存**解决，**未**整文件 `ours/theirs`：
  奈奈 R02 现场账本（`BLOCKED_AUTH_REQUIRED` / `BLOCKED_NO_INTERNAL_PROBE` / `SCHEMA_COMPATIBLE` / D-044）
  与 Codex 交付记录（`C-M0…FINAL` / `372 pass` / `IMPLEMENTED/TESTED`）**同时保留**；残留冲突标记 = 0。

### M1 = message pipeline 安全观察点（只读源码审计）
- [实测] ①已实现：`docs/nana_shadow_message_observer_audit_20261011.md`（含 path/symbol/line 与逐候选 SAFE/UNSAFE 判定）。
- [实测] ②结论：`SAFE result-path observer = AVAILABLE`（`OnDecoratingResultEvent`）；
  `SAFE early all-message observer = NOT_AVAILABLE`；`AdapterMessageEvent` / `OnLLMRequestEvent` = **UNSAFE**。
- [未知] ④：`Real dispatcher traversal = NOT_VERIFIED`（无安全内部合成事件入口）。

### M2 = 最薄 message observer（开发副本，未安装）
- [实测] ①已实现：
  `src/plugins/astrbot_plugin_nana_shadow_observer/message_hook_adapter.py`（最薄层，复用 Codex `sanitize/observer/core_sink`，**未**另造第二套）；
  `main.py` 增加 `filter.on_decorating_result()` 接线，**默认哑火**（adapter 未绑定即 `return None`）。
- [实测] ②已测试：`python3 -m pytest tests/nana_shadow -q` → **31 passed / 1 skipped**。
  覆盖：正常 / 缺字段 / 超长 / Unicode / null / 恶意对象 / `__repr__`→`__str__`→`__format__` 禁调 /
  observer 异常 / sanitizer 异常 / Core 超时 / Core 异常 / 取消 / 重复 / 重启后重复 / 回调迟发异常；
  并断言 reply=0、event 变更=0、Action/Attempt/Grant/Budget=0、network=0、model=0、Iris 写=0。
- [实测] 状态仅标 **`IMPLEMENTED / TESTED`**，**不**升级为 real dispatcher `VERIFIED`。
- [未知] ④：`Observer registered = NO`；`host_binding = UNVERIFIED`；`FIRST_REAL_ASTRBOT_SHADOW = BLOCKED`。

### M3 = 全新插件免重启人工路径
- [实测] ①已实现：写入 `docs/nana_shadow_message_observer_audit_20261011.md` §5。
- [实测] ②结论：`NEW_PLUGIN_NO_RESTART_MANUAL_PATH = YES`（Dashboard 上传 → 进程内 `load()`）。
- [未知] ④本轮**不上传 / 不安装 / 不 reload / 不改 `plugin_set` / 不读 JWT / 不重启**；
  该动作需姐姐**届时单独授权**。

### M4 = 合流后回归（三方对照，同机同解释器）
| 版本 | 结果 |
|---|---|
| R02 基线 `652a72f` | `65 failed / 171 passed / 1 skipped / 82 errors` |
| Codex 基线 `10581aea` | `71 failed / 219 passed / 1 skipped / 82 errors` |
| **R03 合流 `d3e8c81`** | `71 failed / 219 passed / 1 skipped / 82 errors` |

- [实测] Codex 基线 ≡ R03 合流（**逐数一致**）⇒ 合流**零回归**。
- [实测] 全部失败/错误的 202 处签名均指向同一门：`SQLITE_VERSION_UNSUPPORTED`
  （`src/nana_core/storage/sqlite_store.py:78`，需 SQLite ≥3.51.3；宿主解释器 3.46.1）。
  因果已单独复现：真实 `MetadataCoreSink` 在宿主上 `observer_status = DROP_SHADOW_FAILURE`
  → `harness` 报 `HARNESS_CORE_UNAVAILABLE`。
- 口径：**`HOST_SYSTEM_SQLITE_GATE = BLOCKED`**；
  **`ISOLATED_APPROVED_RUNTIME_FULL_REGRESSION = NOT_RUN`**（本机当前无达标的隔离 runtime）。
  **未**绕过 SQLite 版本门。

### M5 / M6
- [实测] PROJECT_BRAIN 03/04/09/10/11 已同步（本文件即其一）。
- 见 `11_CHANGELOG.md` `C-072` 与 `10_DECISIONS.md` `D-045`。
