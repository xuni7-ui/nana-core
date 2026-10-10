# PROJECT_BRAIN / 09 STATE（当前状态快照）

> 创建：2026-10-10 ｜ 状态：**新建（P2）**
> **规则**：这是**状态唯一入口**。动手前先读本文件；**不要**凭聊天记忆判断当前状态。
> 快照时间：**2026-10-10 02:2x CST** ｜ 快照人：奈奈

---

## 一、一句话状态

**生产处于冻结观察期，B站事件泵正常常驻；`nana-core` 独立副本已完成 P1+P2，并新增「协作桥最小闭环」「C.5-V-1 接线适配层」与「**真 Codex CLI 执行入口**」（2026-10-10 03:2x 实测成功）。**Codex CLI 已可真实执行代码任务，模型为 DeepSeek（非 OpenAI）；生产接线仍默认关闭、未启用。** 未 push、未上传、未改生产。**

**R5（2026-10-10 03:3x）只读体检结论：官方 OpenAI 出口在本机 **不可达** —— `chatgpt.com` SNI 阻断 ／ `api.openai.com` DNS 污染 ／ `auth.openai.com` 403 ／ 本机无代理。** 官方 ChatGPT 登录（网页授权与 device-auth 两条路径）**均无法完成**，与 R3 结论一致。详见 `15_OPENAI_EGRESS_PROBE.md`。**

---

## 二、生产侧（`[实测]` + `[账本]`）

| 项 | 值 | 证据 |
|---|---|---|
| 生产改动 | **0**（01:40 后 `/AstrBot` 无新变动） | `[实测]` `find -newermt` 空结果 |
| AstrBot 版本 | 4.28.0 | `[实测]` pyproject.toml |
| 插件数 | **23**（22 `astrbot_plugin_*` + `meme_manager`） | `[实测]` `ls` |
| Iris 版本 | 0.3.0 / AGPL-3.0 | `[实测]` metadata.yaml |
| 核数 | **4**（非"八核"） | `[实测]` `nproc` |
| 磁盘 | 40G 总 / **21G 可用**（45% 已用） | `[实测]` `df -h` |
| 内存 | **未知**（本命名空间无 `free`） | `[未知]` |
| B站事件泵 | **运行中** · `revision=3709` · `state=OK` · 心跳 **2026-10-10 02:20:00** | `[账本]` `bili_event_pump_last_poll` |
| 最近真实发送 | `DONE` / `VERIFIED`（rpid=316556442641，BV1W7TM6JEFX） | `[账本]` 2026-10-09 19:31:09 |
| 观察期 | 72h，**进行中**；**开始时刻无实测锚点** | `[聊天记忆]` + `[未知]` |

> ⚠️ **进程可观测性**：本 shell 命名空间 `ps -e` 返回 **0 行** → **无法**用 `ps` 证实/证伪进程。泵存活结论**只**建立在**账本心跳**上。

---

## 三、副本侧（`/root/nana_dev/nana-core/`）

| 项 | 值 |
|---|---|
| 文件数 | **65**（含 `.gitignore`；`git ls-files` 64 + 未跟踪 1） |
| PROJECT_BRAIN | **16 文件**（事实层 00–06 + 账本层 07–11 + 证据层 12–15） |
| src | 24 文件（B站外挂 10 / 自制插件 8 / C5V 2 / 接线 2 / notes 2） |
| bridge | **7 文件**（编排 1 / Runner 1 / 测试 2 / README 1 / 任务书 2；scratch+receipts 不入库） |
| manifests | 6 文件 |
| 版本控制 | ✅ 本地 `git`（**无 remote**） |
| git 提交 | 见「基线锚点」 |

---

## 四、本轮完成（P1 + P2 + R1）

- ✅ **P1**：事实口径修正（25→23、2311→2681、证据四档重构、进程可观测性登记）
- ✅ **P1**：指纹自指问题处理（剔除自身条目 + 外置锚点）
- ✅ **P2**：账本建设（07 ROADMAP / 08 TASKS / 09 STATE / 10 DECISIONS / 11 CHANGELOG）
- ✅ **P2**：本地 git 版本控制（可恢复点）
- ✅ **R1**：协作桥最小闭环（`bridge/`）—— 隔离克隆 + 边界白名单 + 验收命令 + 回执；**离线 15/15 通过**
- ✅ **R1**：C.5-V-1 接线适配层（`src/bili_agent/c5v_wiring.py`）—— 默认关闭、失败逐字节还原、绝不编造；**离线 11/11 通过**
- ✅ **R2**：**首次真实模型端点协作跑测通过** —— 派单→真实端点(`api.deepseek.com/v1` / `deepseek-flash`)接收→返回代码→白名单校验→验收 13/13→奈奈独立探针复核；
  源仓逐字节零改动；并**抓到并修复**协作桥 `RunnerResult` 身份 bug（离线回归 18/18）。详见 `12_REAL_COLLAB_RUN_01.md`
  > ⚠️ 该 Runner 是 `LocalLLMRunner`（复用已在用兼容端点），**不等于 Codex**；`codex` CLI 仍未安装。

## 五·补、R2 之后的下一步（提案，未执行）

| # | 事项 | 级别 | 说明 |
|---|---|---|---|
| 1 | 接入**真 Codex Runner**（装 `@openai/codex` + device-code 登录） | **L3，须姐姐一次性审批** | 唯一必须姐姐点头的事 |
| 2 | 协作桥自动化：任务队列 / 触发 / 去重 / 自修复次数上限 | L1，奈奈自决 | 消除"手工派单" |
| 3 | 成本台账 + 阈值熔断（累计 token/费用） | L1 + 需姐姐给单价口径 | 端点无账单接口 |
| 4 | 回执归档策略（`receipts/` 属 gitignore 运行时产物） | 决策 | 长期留证需要 |


## 五、未知项（Top 6，一律按未达标处理）

| # | 未知 | 后果 |
|---|---|---|
| U1 | C.4 事件端到端是否达标 | L1 主线**不能**宣称完成 |
| U2 | 运行态 vs 源码态一致性 | 所有"已实现"仅到文件层 |
| U3 | 72h 观察开始时刻 | 卡住 Stage-0 → M1 |
| U4 | C.7 OBSERVE 吞靶子是否已修 | 潜在功能缺陷未收敛 |
| U5 | 真实 Runner 能否在本机端点跑通 | 桥**机制**已验证，**能力**未验证（`codex` 未安装） |
| U6 | C.5-V-1 真实 BVID 端到端表现 | 适配层只到"已测试"档，未上生产 |
| U7 | 官方 OpenAI Codex 能否在本机落地 | **R5 已定性：不能**（网络出口不可达，非软件问题）——除非姐姐侧提供合规出口 |

---

## 六、红线（姐姐保留，未授权）

- ❌ GitHub 首次上传 / push / 扩大同步范围
- ❌ 新建或使用 PAT / 修改仓库权限
- ❌ 安装依赖 / 启动常驻 Bridge / 消耗新付费额度
- ❌ 修改生产 / 重启服务 / 迁移数据库 / 操作密钥
- ❌ 自动合并 PR / 生产部署
- ❌ **向外部端点发送代码片段**（协作桥真实 Runner 的前置条件）

> 授权分级见 `AGENTS.md` §4.0 与 `10_DECISIONS.md` D-015。

## 六·B、本轮唯一审批项（合并为一次）

> **请求**：允许协作桥的 `LocalLLMRunner` 把 **隔离副本内、白名单内**的代码片段，
> 发往**已在用的 OpenAI 兼容端点**，跑通首个真实协作任务（C.5-V-1 接线增量）。
> **不做**：不装新依赖、不建新凭据、不改生产、不 push。
> **风险**：代码片段外发；模型可能给出坏改动 → 边界白名单 + 验收命令兜底，只落 scratch。
> **回滚**：删除 `bridge/scratch` 与 `bridge/receipts`；不设环境变量即完全关闭。

---

## 七、基线锚点（Anchor）

| 项 | 值 |
|---|---|
| 指纹表 | `manifests/fingerprints_20261010.md`（**不含自身条目**；覆盖 **P1+P2 的 49 文件基线**，见下方口径说明） |
| 基线提交 SHA（P1+P2） | `26ef7af520ed8ea88ba0270c4f384ebfcb0f145b`（提交 #1：P1+P2 全部内容） |
| 基线提交 SHA（R1） | `e896574` ← **本轮内容提交**（协作桥 + C.5-V-1 适配层 + 账本更新） |
| 提交后状态 | 工作区**零残留**（`git status --porcelain` = 0 行） |
| remote | **无**（未配置任何远端 → 物理上不可能 push） |

> **指纹口径说明**：`fingerprints_20261010.md` 只覆盖 P1+P2 那一刻的 49 个文件，
> **不覆盖** R1 新增的 `bridge/`、`c5v_wiring.py`、`docs/c5v_wiring_design.md`。
> 因此**当前完整基线的权威值是 `e896574`（Git 内容寻址）**，指纹表仅作 P1 时刻的历史快照。
> 若指纹表与 `git status` 不一致 → **以 git 为准**。
>
> **自指说明**：文件无法包含自身的哈希。故指纹表**剔除自身**，其完整性由**上述提交**（Git 内容寻址）保证。

---

## 七、Codex CLI 真实执行入口（C-009 · `[实测]` 2026-10-10 03:2x）

| 项 | 值 |
|---|---|
| 执行框架 | **Codex CLI 0.162.0**（官方 npm + 官方 linux-x64 二进制） |
| 模型 | **DeepSeek `deepseek-flash`** @ `api.deepseek.com/v1`（**非** OpenAI 模型，二者不得混淆） |
| 协议 | `wire_api = "responses"` —— 该版本 **已移除 `wire_api="chat"`** |
| 地址 | 入口 `/opt/nana_codex/`（home + node_modules + sandbox），探针 `/root/nana_dev/codex_probe/` |
| 隔离方式 | **OS 级外部沙箱**：进程降权为 `nobody(65534)` + `--dangerously-bypass-approvals-and-sandbox` |
| 为何不用自带沙箱 | 容器**禁止创建 namespace**（`unshare -U`→EPERM），bwrap 与 Landlock 均不可用 `[实测]` |
| 实测结果 | ✅ 真实写入文件 + 真实执行命令 + 测试 rc=0（模型自述与奈奈独立复跑一致） |
| 成本 | 两次会话共 input 95,583 / output 2,274 tokens；估算 **≈¥0.03**（单价口径 `[未核实]`，量级 <¥0.5） |
| 已知缺口 | ①沙箱靠外部降权，容器重建需重做；②模型元数据缺失告警；③桥 Runner 尚未切 `codex_cli`；④无成本熔断 |
| 降级风险 | 降权进程可读**世界可读**文件（如 644 的 `data_v4.db`）→ **非结构性隔离**，待姐姐决策是否加固 |
| 回滚 | `rm -rf /opt/nana_codex` 即彻底移除，生产与 `~/.codex` 未动 |

**证据**：`14_CODEX_CLI_REAL_EXEC_01.md` ｜ **脚本**：`bridge/probes/codex_cli_probe.py`


---

## P3 收口快照（2026-10-10（CST））

- 【实测】远端 `main`（同步前）= `ff1c8704a056c6ebe82594a24f2ecba48ae02e69`。
- 【实测】本轮推送后远端完整 HEAD = **`86484be9d3cc9dd7ca850d804b13fbf10d67ff2e`**（R15，2026-10-10T12:10:59Z，34 文件）。已由 `git ls-remote` + 鉴权 `api.github.com` **双路独立回验**。
- 【实测】本地分支 `master`，远端 `origin/main`，fast-forward 推送（无 force）。
- 【实测】AstrBot v4.28.0 上游 commit `a412146401426c0cdff8bbefb8627a03da519da8`；Iris 0.3.0 commit `0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6`。


## Nana Core V1 第一阶段开发（C-018）
[实测] 用户正式授权 S0—S4 独立开发、提交与离线测试；旧 T-31 对 T-22 的依赖不作为本次合成离线实验的阻塞，不改变生产迁移依赖。
基线 `18bc736d5e37fe3325e514a0e975403df2f97c9f`；本地分支 `dev/nana-core-v1-s0-s4`。S0 已测试（8 passed），后续未实现。

[实测] C-019：S1 已测试，5 passed；S2—S4 尚未完成。

[实测] C-020：S2 已测试，12 passed，包含真实 SIGKILL；S3—S4 尚未完成。

[实测] C-021：S3 已测试，6 passed；S4 尚未完成；S5 不在本轮范围。

[实测] C-022：S4 已测试，10 passed；S0—S4 阶段测试累计 41 项；统一实验与交付核验进行中。


## Nana Core V1 S0—S4 最终离线验收（C-023）

- **[实测] 基线**：`18bc736d5e37fe3325e514a0e975403df2f97c9f`；本地开发分支 `dev/nana-core-v1-s0-s4`。
- **[实测] 实现**：`src/nana_core/` 独立包；schema v1（15 领域表）；没有 AstrBot/Iris/B站导入或生产路径。
- **[实测] 验收**：56 passed / 0 failed / 1 skipped；E01—E20 中 19 离线 PASS，E12 真实双模型语义迁移 NOT_RUN。
- **[实测] 连续性**：不同进程保持相同身份与历史；反馈形成受限经验；下一次 read→locate→create，对照 read→create。
- **[实测] 恢复**：真实 SIGKILL -9，外部提交后本地 DISPATCHING 经查询恢复 SUCCEEDED；副作用与写调用均为 1。
- **[实测] 工程环境**：Python 3.12.14 / SQLite 3.53.1 / Pydantic 2.13.4 / pytest 9.1.1。
- **报告**：`docs/nana_core_v1_implementation.md`；原始证据 `docs/nana_core_v1_evidence/`（全为合成资料，不包含 DB）。
- **源/测试指纹锚点**：`manifests/fingerprints_nana_core_v1.json` SHA256 = `4e2426a09ae9fb8896ca585aee17f00c48940daebbb8aedfc59c38035debcb9d`；不包含自文件和引用锚点的账本，避免自指。
- **状态边界**：S0—S4 已离线运行验收；通用自然语言学习、真实模型、生产运行、迁移 S5/S6 未实现或未执行。旧 T-31—T-33 生产里程碑不因此宣称 DONE。
- **费用与权限**：真实外部模型及生产调用 0；模拟预算单位不是真实费用。未部署、未合并 main。

[实测] C-024：ModelRequest 补齐持久化 identity_snapshot；重启后 ID、版本和身份内容一同恢复。最终复验仍为 56 passed / 0 failed / 1 skipped，S5 未执行。


## S0—S4 远端保存与 S5 当前状态（C-025/C-026，2026-10-10）
[实测] 本轮用户明确授权推送开发分支并继续 S5；该授权更新历史 D-019 中本次开发分支上传边界，未授权生产或 main 合并。
- S0—S4 远端分支：`dev/nana-core-v1-s0-s4`，完整 SHA `884db6a460c2803e8c89434c3fa8e36f7ffe90cf`；git push + git ls-remote 一致。
- main：`18bc736d5e37fe3325e514a0e975403df2f97c9f`，未改。S5 从已保存提交创建 `dev/nana-core-v1-s5`。
- S5 工程：③已离线运行验收；42 个新增测试通过，联合回归 98 passed / 0 failed / 1 skipped。
- S5 真实语义 / E12：④未知（NOT_RUN）；实际模型无，调用 0，费用 0；当前环境没有就绪开发端点。历史 DeepSeek 记录不作为本环境能力。
- 身份与行为：16 个顺序子进程的工程夹具恢复同一身份；新增定位实际发生，权限缺失则 BLOCKED。不得称为真实双模型。
- 数据：全合成；未读取密钥文件/私人记忆，未使用生产账号；新增模型账本两表独立于 Core，Core schema 未变。
- 证据：`docs/nana_core_s5_implementation.md` 与 `docs/nana_core_s5_evidence/`；S6 未实施。
- S0—S4 指纹保留为历史快照；S5 修改 pyproject 和 E12 跳过理由，新指纹覆盖当前相关文件，不回写历史指纹。

[实测] S5 指纹锚点：`manifests/fingerprints_nana_core_s5.json` SHA256 `b228d79c6a192a9b0ebd30f1b88a91f147e6fc3faabb746e7fc1b632e23c9962`。只证明本次采集文件，不证明生产运行。

[实测] C-027：S5 实现提交 `881e48a863257971e29a49f48ab8ec403313c3fa` 已推送私有远端 `dev/nana-core-v1-s5`；git ls-remote 一致。此后仅追加保存回执/账本，最终 HEAD 以 Git 为准。原 S0—S4 分支和 main 均保持原 SHA。

[实测] C-027 指纹锚点更新（新增保存回执，代码 hash 不变）：`34805e92a62c1ae9b4f331c1a431e2d4ddd03769f4a34644b562c46ae48402f9`。


## S6 非生产准备启动（C-028，2026-10-10）
[实测] 本轮用户直接授权 S6 合成导入/影子观察/能力统一/单一执行权开发、测试、提交与 GitHub 开发分支交付；不扩展生产。基线 `6491aa6ddadd63e23035f69dd18a218b70ccf650`，分支 `dev/nana-core-v1-s6`。旧记忆导入纵向闭环 14 passed；影子/执行权尚未完成。E12 仍 NOT_RUN。

[实测] C-028 指纹锚点 1d01dc300189565fce3d279af71bbfb2091ec61d5012ba14dbe0883dfd01db72。

[实测] C-029：影子观察与统一 CapabilityPort 单一执行方完成；S6 累计 27 passed。影子不改目标/行动/授权/预算/策略；模拟旧执行方与 Core 执行方只有当前 epoch 可到达 FakeWorld，未决禁止换主。生产迁移与 E12 均未验证。

[实测] C-029 指纹锚点 ce2b9a8943512c036ca2e9a35e9388efbca842c1b9ee6643ebfc3d3f171ce39c。


## S6 当前统一验收（C-030）
[实测] 29 个 S6 测试通过，联合 127 passed / 0 failed / 1 skipped；CLI 已运行，13 条实际闭环检查均成立，真实 SIGKILL -9，三张卡片无重复副作用，恢复时模型调用 0。
[实测] 四条旧来源记录精确保留来源、覆盖范围和时间，推断/摘要/旧 VERIFIED 均 UNASSESSED；影子无执行能力，单执行方持久 epoch，未决禁止换主。
[未知] 真实宿主/真实数据映射与对账、生产执行权迁移、E12；均未执行。实验真实模型/生产调用/费用均为 0。报告 docs/nana_core_s6_implementation.md。

[实测] C-030 最终指纹锚点：manifests/fingerprints_nana_core_s6.json SHA256 `bc52a0627ec3b82c8f2f5d4fcd983efd1ffa2f48cb3ea200de351e6e62f16ae6`。只证明本次采集的合成源码/测试/证据；排除自身与账本，不证明生产运行。

[实测] C-031：S6 实现提交 `14e5f2e71d209a2378290d7b591d932131ab28ba` 已推送并核验私有开发分支 dev/nana-core-v1-s6；main/S0—S4/S5 SHA 未变。之后仅追加保存回执与账本，最终 HEAD 以 Git 为准；工作区无运行 DB 入库。指纹锚点更新 `fa081fdc74255b54197fd376f6125bc18591b41666f3dc6ec4ae647254c514ed`；源码/测试 hash 不变，新增合成保存回执。
