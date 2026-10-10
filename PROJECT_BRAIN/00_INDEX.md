# PROJECT_BRAIN / 00 索引

> **创建日期**：2026-10-10（CST）
> **创建人**：奈奈（Nana）
> **状态**：**新建**。原始 PROJECT_BRAIN **未找到**，本目录为 2026-10-10 依据现有事实文件与实测证据**重新建立**，**不是**原始文件的恢复或复制。
> **权威性声明**：本目录是奈奈工程事实的**唯一权威来源（Single Source of Truth）**。任何与聊天记忆、口头描述冲突之处，以本目录中标注 `[实测]` 的条目为准。

---

## 一、来源分级定义（全文通用）

| 标记 | 含义 | 可信度 |
|---|---|---|
| `[实测]` | 2026-10-10 由本机只读命令直接采集（find/ls/grep/md5sum/wc） | 高 |
| `[文档]` | 服务器上既有的、由奈奈此前生成的报告/说明文件 | 中（可能有滞后） |
| `[聊天记忆]` | 来自对话记忆，**未经本机复核** | 低，不得当作已验证事实 |
| `[未知]` | 无证据支撑 | — |

## 二、本目录文件清单（14 文件）

### 事实层（01–06）

| 文件 | 内容 | 主要来源 |
|---|---|---|
| `00_INDEX.md` | 索引、来源分级、权威声明 | 本文件 |
| `01_architecture.md` | 整体架构与模块边界 | `[实测]` 目录结构 |
| `02_source_inventory.md` | 源码清单（宿主/插件/外挂） | `[实测]` find/ls |
| `03_config_runtime.md` | 配置与运行数据职责/位置（不含内容） | `[实测]` ls/stat |
| `04_verification_status.md` | **证据四档**：已实现/已测试/已运行验收/未知 | `[实测]`+`[账本]` |
| `05_third_party_licenses.md` | 第三方来源、版本、LICENSE（23 插件） | `[实测]` metadata/LICENSE |
| `06_open_risks.md` | 未解决风险与未知项 | 综合 |

### 账本层（07–11，2026-10-10 P2 新建）

| 文件 | 内容 | 维护规则 |
|---|---|---|
| `07_ROADMAP.md` | 六条主线路线图（L1–L5 + LX） | 里程碑变更时更新 |
| `08_TASKS.md` | 任务清单 + 阻塞册 | 任务状态变更时更新 |
| `09_STATE.md` | **当前快照** + 指纹锚点 | 每次动手后**必更** |
| `10_DECISIONS.md` | 决策日志（D-001~） | **只增不改** |
| `11_CHANGELOG.md` | 变更日志（C-001~） | 每次改动**必须**三条齐全 |

### 证据层（12，2026-10-10 R2 新增）

| 文件 | 内容 |
|---|---|
| `12_REAL_COLLAB_RUN_01.md` | **首次真实模型端点协作跑测**的完整证据：授权逐条对照、任务书、两次运行、独立验收、成本披露、距无人值守的缺口、复现命令、回滚 |

---

## 二·补、P1 修正摘要（2026-10-10）

| 原稿 | 修正为 | 依据 |
|---|---|---|
| 插件"25 个" | **23 个** | `[实测]` `ls -1 /AstrBot/data/plugins/` |
| 外挂脚本"~2311 行" | **10 文件 / 2681 行** | `[实测]` `wc -l` |
| "已验证"（来源为聊天记忆） | 降级为 **①已实现 / ②已测试 / ④未知** | D-018 证据四档制 |
| 指纹表含自身条目 | 剔除 + 外置锚点 | 自指哈希不可满足 |

> 详细见 `11_CHANGELOG.md` C-001 ~ C-003。

## 三、全局未知项（显式登记）

1. **原始 PROJECT_BRAIN 不存在**：全盘轻量搜索 `/AstrBot`、`/root` 内 `*brain*`（maxdepth≤4）**零命中** `[实测 2026-10-10]`。
2. **上游 v0.3.0 原始文件未获取**：Iris 插件本地无 `.git`，故 `02`/diff 中的"改动"是**奈奈改前备份 ↔ 现行**的对比，**不等于**"上游官方 ↔ 现行"的差异。
3. **运行态 ≠ 源码态**：所有指纹（见 `manifests/fingerprints_20261010.md`）**仅证明采集时刻**的文件状态，**不自动证明**当前进程实际加载的内容。
4. **生产进程加载版本未知**：未重启、未探测进程内存，无法证明运行中的模块与磁盘文件一致。

## 四、采集元信息

- 采集方式：**只读**（find / ls / grep / head / md5sum / wc / difflib）
- 生产改动：**0**（未修改、未新建于生产树、未删除、未重启、未 push）
- 采集时间：2026-10-10 01:5x CST
- 环境：Debian 13 (trixie) / 4 核 / 磁盘可用 21G / AstrBot 4.28.0

## 五、维护节奏（2026-10-10 P2 起生效）

1. **动手前**：读 `09_STATE.md` 确认当前基线；读 `08_TASKS.md` 确认任务序号。
2. **动手后**：**必更** `09_STATE.md` + `11_CHANGELOG.md`（改了什么/为什么/怎么验证）。
3. **决策产生**：追加 `10_DECISIONS.md`，**不覆盖历史**。
4. **里程碑变化**：更新 `07_ROADMAP.md`。
5. **每次更新后**：重算 `manifests/fingerprints_20261010.md`，并把指纹表自身 SHA256 写回 `09_STATE.md`。

### 证据层（12–14）

| 文件 | 内容 |
|---|---|
| `12_REAL_COLLAB_RUN_01.md` | 首次真实模型端点协作跑测（LocalLLMRunner，**非** Codex） |
| `13_CODEX_CLI_INSTALL_PROBE.md` | Codex CLI 安装/登录探针（登录被外网阻断） |
| `14_CODEX_CLI_REAL_EXEC_01.md` | **Codex CLI 真实执行验证**（自定义 Provider + 外部降权沙箱，成功） |


---

## 六、P3 工程基线收口增补（2026-10-10（CST））

### 新增文件
- `24_BASELINE_CLOSURE_20261010.md`：本阶段 A–G 总证据文件。
- 仓库根：`requirements.txt`、`LICENSES_AND_PROVENANCE.md`
- 仓库目录：`patches/astrbot/`、`materials/iris_customizations/`、`materials/bili_agent/`
- 仓库文档：`docs/bridge_node_rebuild.md`

### 关键更正（覆盖旧描述）
- 【实测】Codex CLI **已安装**（`/opt/nana_codex`，`@openai/codex` 0.162.0），非"未安装"。旧 `13_*` 中"登录被阻断"仅指**官方 OpenAI 端点**；经自定义 Provider，**真实 exec 已成功**。
- 【源码确认】Iris 上游 **v0.3.0 已获取**（tag `0.3.0`，241 blob，逐字节校验）。旧"上游未获取"作废。
- 【实测】本地 Bridge Runner **真实闭环成功**（≠ Codex Cloud 成功；Cloud environment 仍未创建）。


## Nana Core V1 第一阶段实现（新建，2026-10-10）
- `src/nana_core/`：S0—S4 独立离线 Core。
- `docs/nana_core_v1_implementation.md`：实现、schema、E01—E20、边界和重现命令。
- `docs/nana_core_v1_evidence/`：全合成验收证据，不包含运行 DB 或私人资料。
- `manifests/fingerprints_nana_core_v1.json`：本阶段源/测试指纹，锚点见 09_STATE。

## Nana Core V1 S5（2026-10-10，本轮新增）
- `src/nana_core/semantic/`：真实兼容 ModelPort 与冻结状态顺序评估。
- `docs/nana_core_s5_implementation.md` / `docs/nana_core_s5_evidence/`：工程 PASS、真实语义 NOT_RUN 的分离证据。
- `manifests/fingerprints_nana_core_s5.json`：S5 采集时刻代码/测试/报告指纹；不覆盖生产运行。


## S6 非生产迁移准备（2026-10-10）
- src/nana_core/migration/：合成旧来源保留、影子观察、统一能力单执行方及 CLI。
- docs/nana_core_s6_implementation.md / docs/nana_core_s6_evidence/：工程、来源、真实进程故障证据。
- S5 E12 仍 NOT_RUN；生产迁移未运行，不把模拟执行方误称实际宿主。
