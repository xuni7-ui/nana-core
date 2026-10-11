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
# 当前开发能力验证（C-032，2026-10-10）
[实测] 本轮用户明确授权并行生产权限类别只读核实与独立开发验证、编码/测试/提交/推送；未授权生产登录、凭据/私人记忆读取、生产变更、main 合并或部署。基线 b2b5b99e69377d024bbb58c13d9f2564dccea9f5；开发分支 dev/nana-core-v1-dev-validation。
[实测] 31 个新测试，联合 158 passed / 0 failed / 1 skipped；真实源文件只读、独立重读、身份/Grant 连续、单执行方和真实 SIGKILL 恢复。实际 CLI 三次文件执行读取/三次核验重读、两张合成卡片；经验被引用并新增定位。
[实测] 真实 loopback 协议测试不是真实模型；当前开发端点 0、实际推理/公网工具/生产调用 0、模型费用 0，E12 NOT_RUN。service_kind 未声明默认 unverified，不能以 HTTP 成功通过 E12。
[实测/未知] 可见配置无生产访问绑定/生产命名挂载；Docker socket 请求在默认沙箱 PermissionError（拒绝阶段未记录），生产关联未知。GitHub 私有、Actions workflows 0、hooks GET 403；外部推送部署/轮询未知，未建立生产访问路径。
来源：docs/nana_core_development_validation.md、docs/nana_core_development_evidence/；未改变总体架构/生产树，零新增依赖和 Core 表。

[实测] C-032 指纹锚点 b175b377bf9f0536598811140953f24da795ff562b0b3801ec6a650429668975；只证明采集时刻的源码/测试/合成与元信息证据，不证明生产。

[实测] C-033：P0 已远端保存 b05468d63182c17644037be447688798fa5ce6b4；P1 模型适配收尾 81 targeted passed（开发 39）；配置/4xx/截断/回显边界保持，E12 NOT_RUN。当前继续只读网页开发，未建立生产访问。
[实测] C-033 指纹锚点 6dfcea0ce525ee517543c28cc2072a3a64d22251c22821daedc85aea1e3c9da3（当前开发源与历史/本阶段证据，不证明生产）。

[实测] C-034：网页单工具 84 targeted passed；新增开发 55，S6 29。公网一次授权尝试 UNKNOWN/WEB_TIMEOUT，实际 HTTP 0、代理连接 0；保留未决不重试。网页工程②已测试，公网④未知；模型 0、E12 NOT_RUN。P1 已保存远端 0d13ecc8ed84ee9c0cd3e28b19cf0cfed00fe5db。详见 docs/nana_core_web_validation.md；跨进程研究/经验消融待执行。

[实测] C-034 指纹锚点 2b0b52e766be9975632724ce957149e74d0cbee69cd0fb6b1319f3122422074c；只证明采集时刻的源码/测试/证据，不证明生产。

[实测] C-035：非生产研究/网页/定位/卡片跨进程闭环③已运行验收；CLI18检查成立，实际5 loopback GET。新专项20 passed，真实SIGKILL -9 恢复GET0/提案0；同冻结快照消融实际定位1对0，身份/时间/证据/Grant保持；缺定位授权目标BLOCKED，重启不重复已完成读取。公网/真实语义④未知，E12 NOT_RUN，模型0/费用0。P2已保存ccad1a2b9811eec853b4ecc908649ac3cc532de9。最终全量回归待执行。

[实测] C-035 指纹锚点 60133cef53d18640410da5469fa6218b7d42db923a19d92739bf40ac2607b91c；只证明采集时刻的源码/测试/证据，不证明生产。

## 持续开发最终工程状态（C-036）
[实测] 全量227 passed /0failed /0errors /1skip（E12），开发100项；真实SIGKILL/身份/时间/证据/授权/预算/幂等/影子/单执行方/经验消融均回归。网页研究卡片与3步多工具③已运行验收（合成loopback+确定性规划+fake notebook）；非真实自然语言研究语义。
[实测] 最终测试26 loopback HTTP，独立CLI5GET；公开尝试一次DNS超时HTTP0，UNKNOWN不盲重试；模型/生产调用0、费用0。公网/E12④未知（NOT_RUN或未验证）；生产路径未建立，未知卷/凭据候选/容器关联/webhook/外部轮询不假设不可访问。
[实测] 远端已保存P3/P4 fced7f8204b82da03e6fc9d60fe73e29727c3d0c，分支dev/nana-core-v1-dev-validation；最终HEAD以Git/ls-remote为准。报告docs/nana_core_web_validation.md、final_delivery.json；下一最短路径为开发DNS/代理适配的单次公网验收及两个既有额度真实开发ModelPort的E12。未更改总路线或生产树，零新增依赖/Core表。

[实测] C-036 指纹锚点 ea365a72aa241b6db3ae95c43cb53131c1beeda528f04b659186263848ab6dc3；只证明采集时刻的源码/测试/证据，不证明生产。

[实测] C-037：Phase III原基线29872608b7b82fcca4a89a3be98fda8e8c65337f本地/远端一致，新分支dev/nana-core-v1-phase3-entry。公网验收一次DNS_FIRST/WEB_TIMEOUT，HTTP0、proxy0，UNKNOWN保留；42 targeted passed。公网④未验证，其他独立任务继续，未动main/生产。

[实测] C-037 指纹锚点 503a533c70ed3635c34d7db0a02b4aa2bfb04f5dff9b1664621e0216d386bb77；仅本检查点文件状态，不证明生产。

[实测] C-038：M2 E12正式readiness已运行，冻结快照未变；开发端点0，真实模型0，E12 NOT_RUN、费用0，未读secret值。M1远端4f51b5a385ac9a4673e1ba093b782b1ff840c023一致。Iris上游完整源树不在仓库；本轮只读获取登记0.3.0 commit0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6到/tmp用于字段核对，不入库或运行上游。

[实测] C-038 指纹锚点 8be37a2e89c218faec3bb965572d8d2847aca8cf6930a71875a94d5036e6a42d；仅本检查点文件状态，不证明生产。

[实测] C-039：M3 Iris schema mapping+adapter②已测试，14 synthetic records/11结构，新7及S6 29共36pass；真实SIGKILL恢复、去重、拒绝/未知语义保留，无新Core表/权限。真实私人DB/生产迁移未运行；M2 E12仍NOT_RUN。映射docs/nana_core_phase3_iris_mapping.md与iris_source_manifest.json为锁定源证据。

[实测] C-039 指纹锚点 5fe2336a8d6382a5ef14bde304bd202494fac378ba027327d688eff65ce2c6ae；仅本检查点文件状态，不证明生产。

[实测] C-040：M4非生产迁移演习③已运行验收，14import/0reject→重启14duplicate，1relation/1conflict group，identity/time/source/replay保持，Goal/Action/Grant/Strategy/Budget0。10 targeted passed。MemoryView冲突及来源检索②已测试；P7影子PARTIAL（lexical surrogate，无真实Iris向量parity），E12 NOT_RUN。无新表/依赖。

[实测] C-040 指纹锚点 fa1ea7258bcc0b6a8c04262f77430923e1b80d0a89cced6dc11e08c9a391c94d；仅本检查点文件状态，不证明生产。

[实测] C-041：M5主动候选/价值冲突②已测试，22 targeted pass；fixture6/6，提出/接受/调度/执行隔离，contact BLOCKED、第三方联系0，pending重启保持。真实风险判断语义④未知；非reading计划模板未执行，无新表/依赖。M4远端51c28cf29e5ac970d401f19b1ce2c7fa76534a81。

[实测] C-041 指纹锚点 9522567d2a20492d3babd86f647a512bf84e07a96c3d2d1b2c443e6756b5dd3d；仅本检查点文件状态，不证明生产。

[实测] C-042：M6模型选择②已测试，显式Endpoint/privacy/task/context/tools/cost守门；工程能力PARTIAL（6操作preview，CapabilityPort disabled，Core registry拒绝），不自修改。51 targeted passed，initiative真实SIGKILL wake恢复jobs1；记忆同刻冲突/裁剪与真正ContextBuilder preview复验。E12 NOT_RUN/实际模型0，P11真实执行未启用；零新表/依赖。

[实测] C-042 指纹锚点 71576f64450feaa9eafac7e801dbd30c95db66b408dddb362de6e03a2132149c；仅本检查点文件状态，不证明生产。

[实测] C-043：公网两个不同目标各一次有界新授权实验，主机名DNS_FIRST超时；公开数字IP经proxy到TLS失败（底层原因UNKNOWN），HTTP总0/proxy尝试1，两个UNKNOWN保留无自动重试。43 targeted network pass。最终shadow采用matched8000chars/8items，recall两边1.0、矛盾标注0/2，原top1统计不作优劣证据；P7仍PARTIAL。真实公网/E12未验收。

[实测] C-043 指纹锚点 d83bd5dbb6265d75483dea11150e35dbe5a0c4e5bfa566ff078e7deebfd5200c；仅本检查点文件状态，不证明生产。

[实测] C-044：导入mapping声明跨崩溃冻结，异常逐条reject/继续，context矛盾原话优先但原证据不删；13 targeted pass，最新跨进程rehearsal仍14import/14duplicate与replay PASS。此前259pass/1skip为补强前回归，当前待最终完整复验。零新增Core表/依赖；公网/E12未验收。

[实测] C-044 指纹锚点 132d32602cea82e477a5554b4cce9f6d7d7d48899a44aeff8f5bac92837afc95；仅本检查点文件状态，不证明生产。

[实测] C-045：跨来源claim及source scope隔离、mapping1→2同语义升级②已测试，15 pass；源证据/身份不变，真实Iris检索仍PARTIAL；最新rehearsal14import/14duplicate、1relation/1conflict/replay PASS。最终全量待本补强后复验。

[实测] C-045 指纹锚点 74bc4b3cef7932a35d6404a0c2f405613bd1e7e019d9b0a54d2bff77d9ef353a；仅本检查点文件状态，不证明生产。

[实测] C-046：Phase III最终全量263 passed /0failed /0errors /1skip(E12)，36项新增不变量；最新14import/0reject/14duplicate、11真实结构、1conflict/1relation、replay/source/time/identity PASS。匹配shadow PARTIAL、6/6结构initiative、selection TESTED/engineering disabled PARTIAL。公网DNS/TLS阻塞，两Unknown/HTTP0/proxy CONNECT1，无真实模型。零新增SQL表/依赖/生产动作/私人记忆或secret值读取；main不动。最终报告docs/nana_core_phase3_entry.md与phase3_evidence/final_delivery.json，最终commit与远端相同状态以Git/ls-remote为准。

[实测] C-046 指纹锚点 848e1a6aa8160d067a6f39a1ad3639f963e3fd8f498b4c8833adab1ffffbcd57；仅本检查点文件状态，不证明生产。

[实测] C-047：Cloud M1: strict host observation contracts and non-production AstrBot adapter; 2 targeted passed；指纹锚点 0b960cb600a5718510d32888462ec0c240007c33f34f69b96a18ae79e8e5ec7e；仅本检查点文件状态，不证明生产。

[实测] C-048：Cloud M2: frozen-snapshot read-only Iris exporter and metadata-only preflight; 4 targeted passed；指纹锚点 3312c8a10d676599fcd508b0e18e8acda203f444e3206020f5bee6b145e08beb；仅本检查点文件状态，不证明生产。

[实测] C-049：Cloud M3: disabled host ShadowBridge and restartable evidence reconciliation; 7 targeted passed；指纹锚点 76b70ed24ab1abf03927b426667521e9eb8711952d666213e9091e732c38ae2d；仅本检查点文件状态，不证明生产。

[实测] C-050：Cloud M4: reuse owner epoch for fenced synthetic handoff and memory authority protocols; 30 targeted passed；指纹锚点 0db2a5bfbb7dfb116d1e453669f5edd21c7384c9cd829d2ab71c625c1a0fb49e；仅本检查点文件状态，不证明生产。

[实测] C-051：Cloud M5: host initiative barrier and operator-scoped engineering capabilities through original ActionKernel; 74 targeted passed；指纹锚点 a7fda377f0db0c4f731f28f4e3b43bf772347f39c9999bbea6de14e6f77903c0；仅本检查点文件状态，不证明生产。

[实测] C-052：Cloud M6: bounded shadow session, packaged barriers and reversible cloud runbook; 58 targeted passed；指纹锚点 e530a771426f2734a2830ddfd904cbc073f7df6c2871af3b396e523eb29fa808；仅本检查点文件状态，不证明生产。

[实测] C-053 FINAL：Cloud bridge独立开发全量281 passed/0failed/0errors/1skip(E12)。宿主Observation/导出/metadata preflight/Shadow/session/协议/initiative完成对应fixture工程门；两个真实开发进程Shadow恢复，engineering实际patch/test/verify/dev commit与SIGKILL核验恢复。生产接入未运行、真实handoff/memory翻转0，Iris native wrapper/热加载API/兼容版本待现场授权确认；工程仅literal数据与固定可信AST测试，不是任意代码sandbox。真实模型0/E12 NOT_RUN、公网本轮0仍BLOCKED、SQL新表0、依赖0、生产/secret值/私忆/外部消息0。报告docs/nana_cloud_integration_architecture.md、nana_cloud_shadow_runbook.md、nana_cloud_evidence/final_delivery.json；最终SHA以Git/远端回验为准。

[实测] C-053：Cloud FINAL: preserve 281 passing tests and honest shadow deployment and engineering boundaries；指纹锚点 fe66d10d5dae2176b867e1192ccc0f71171dcc41610647c7c660ff1e9ddbd735；仅本检查点文件状态，不证明生产。

[实测] C-054：Cloud save correction: stage obsolete host module deletion to match fully tested source tree；指纹锚点 2e0a18b78f8fae427520606f2c7c41e7b1602f6f7661f7680d3b3c6d079606b7；仅本检查点文件状态，不证明生产。

[实测] C-055：First Shadow M1: fixed approved Core bundle and probe-only launcher; 7 targeted passed, real host blocked；指纹锚点 6372a997357cddb33717c15b7e970a7bfcee43c77fa4b399a9c8140546717a64；仅本检查点文件状态，不证明生产。

[实测] C-056：First Shadow M2: persisted memory context and restart reconciliation; 15 targeted passed, host and E12 NOT_RUN；指纹锚点 e4533088583b9a7a2b1cce27b36fd7c4ec3cc4ef7c5dd6845d59de42858a12cf；仅本检查点文件状态，不证明生产。

[实测] C-057：First Shadow M3: exact rollback, metadata-only SQL authorizer and real SIGKILL recovery; 10 targeted passed；指纹锚点 f6620ccea15b6b20b9f60d3043825e4ac45e17f8202c8841dbcce9f18a1d19e2；仅本检查点文件状态，不证明生产。

[实测] C-058：First Shadow FINAL: 291 passed, one E12 skip; real host blocked, bounded package and rollback evidence saved；指纹锚点 93bc78fad82744034001ace1610c3afac2eb1c438814b9f28d153dd404fb84a2；仅本检查点文件状态，不证明生产。

[实测] C-059：First Shadow FINAL save: normalize preserved failure-log whitespace; 291 passed and real host BLOCKED_NO_HOST_CHANNEL；指纹锚点 6eccc6e70d6232253941f85cb61465a93a35619488edb0fdab16a535e528d0f8；仅本检查点文件状态，不证明生产。

[实测] C-060：Shadow Bootstrap M1: evidence-tagged host blockers and SQLite WAL-reset durability audit; 10 targeted passed；指纹锚点 82ef88ea168846e9fed09b8af14d6cd80afbedfb616722648d2c4e62fcb35772；仅本检查点文件状态，不证明生产。

[实测] C-061：Shadow Bootstrap M2: real host-version comparison and Pydantic 2.13.5 291-pass regression; SQLite durability gate retained；指纹锚点 4a6e813b05d710b8ecd7ce8a180a8311ae9ceae8ff3f8bfa987ddce8de359048；仅本检查点文件状态，不证明生产。

[实测] C-062：Shadow Bootstrap M3: private fixed SQLite binding and Pydantic wheels, integrity-checked runtime; 22 targeted passed；指纹锚点 55c9b46177ba7db1c096b699f1ec9b6ef98ebf5d4366c9cb37c93331ec70fd1f；仅本检查点文件状态，不证明生产。

[实测] C-063：Shadow Bootstrap M4: one-file archive, interpreter-scoped preflight and real extracted-bundle SIGKILL validation PASS；指纹锚点 3a2a859c90c3cb40932ee6de215659ce100026668611e4c1e797a705597d5706；仅本检查点文件状态，不证明生产。

[实测] C-064：Shadow Bootstrap M5: source-backed Iris native-field wrappers and metadata-only hook probe; 16 targeted passed, hook UNKNOWN；指纹锚点 a246f2194cd1012269050c88bf98725354d6e39e31e0b91d5f6e2f8280b67d5c；仅本检查点文件状态，不证明生产。

[实测] C-065：Shadow Bootstrap release hardening: private SQLite symbol binding, ABI guard and lossless wrapper JSON; 24 targeted passed；指纹锚点 29f4d02ac69f420bab21728a27b9a7c4a61369e5cba67a7163afedd98507331b；仅本检查点文件状态，不证明生产。

## 2026-10-11 UTC · Shadow Bootstrap 最终兼容性与交付

- [实测] 当前开发分支 dev/nana-core-v1-shadow-bootstrap，基线8ff57a3a227ee1c35ed34cf314866300e34d01f8；批准Core包55文件仍为ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513原字节；support固定67bc134045017763de989668d569c47b15ebfd74。最终报告提交SHA以Git/远端回验为准。
- [聊天记忆/用户输入] 宿主Python3.12.14/SQLite3.46.1/Pydantic2.13.5及未有Shadow目录/批准包是用户提供的阻塞事实；当前仓库未保存原始实机输出。本轮无宿主通道，不标成宿主实测。
- [文档/实测] SQLite语法本身不依赖3.51.3；官方WAL-reset corruption修复是保留>=3.51.3的可靠性依据。实际3.46.1的schema/backup/rollback/SIGKILL-WAL primitives PASS，原完整版本门对照144pass/65fail/82errors/1skip，未绕过门、未宣称重现corruption。完整矩阵docs/nana_shadow_bootstrap_evidence/compatibility_matrix.json。
- [实测] Pydantic2.13.5兼容：29 DTO合同与2.13.4摘要相同；只放宽到>=2.13.4,<=2.13.5，不推广未测版本。最终直接加载交付包SQLite binding（c18e64abba400c9c1ee91327680ce388dd51b4fb090b52ad829257ba19d82705）进行完整回归：305passed/0failed/0errors/1skipped(E12)。Python3.12.14/SQLite3.51.3/Pydantic2.13.5均是真实运行版本。
- [实测] 单包nana-shadow-bootstrap-67bc13404501.tar.gz，3,268,428bytes，SHA256=61574b2533cba222e58da24bf4d2e31b768b3811e2dd136b9244d0fcc07993b7。runtime含manifest8,537,017bytes；复用宿主CPython3.12.14，只在短期Shadow进程加载私有SQLite及5个固定wheel，不改系统/AstrBot。要求Linux x86_64/glibc>=2.34/正常cp312 ABI，宿主ABI仍未知。
- [实测] 新目录解包验证：全部脚本dry-run不写数据，preflight/一次探针/重启/真正SIGKILL(-9)/UNKNOWN回滚/恢复/二次回滚/collect通过；篡改BLOCKED_PACKAGE_INTEGRITY。唯一probe/Evidence/候选/Shadow draft/decision各1，Action/Attempt/Grant/现实预算均0。HOST_GLOBAL_ENV与SHADOW_RUNTIME_ENV分离，真正所选解释器决定探针兼容性；metadata整体UNKNOWN不被冒充AstrBot接线PASS。
- [实测/未知] HookCompatibilityProbe只读metadata/AST，无动态注册或真实消息流；真实hook UNKNOWN。Iris native L1 volatile queues/profile KV字段的synthetic冻结wrapper适配、schema/count/hash/redacted modes已测试；生产native KV/runtime extraction未启用，仍PARTIAL，不读取私人正文。
- [实测] 本轮生产登录/修改/调用/私人记忆/secret值读取/外部消息/owner和memory authority切换均0；Core新增SQL表0、全局依赖新增0，包内私有依赖5。真实模型调用0/E12 NOT_RUN；官方材料/构建输入下载是开发构建流量，不是公网Web Capability验收。
- [未知] FIRST_REAL_CLOUD_SHADOW仍BLOCKED_NO_HOST_CHANNEL。单文件上传仍由操作者完成；本轮未把包传到奈奈宿主。最短路径：人工上传归档、外部checksum验证、选定解释器preflight、adapter-local probe/restart-check/rollback/collect；准确命令及剩余授权边界见docs/nana_shadow_bootstrap.md。

[实测] 2026-10-11 startup isolation追加：bootstrap使用-I -B -S，缺任一标志在读取包前BLOCKED_STARTUP_ISOLATION；仅读全局安装metadata，不执行.pth/sitecustomize。25targeted passed。上条67bc归档/305回归作为历史实测保留；最终操作者包待本隔离修正commit后的新归档替换，不推给真实宿主。

### 当前交付（SUPERSEDES 上条67bc候选归档；历史证据保留）

- [实测] support固定3aba4eb4253cb30f27141831a4c983d714594e3a；批准Core仍ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513，55文件不变。最终归档nana-shadow-bootstrap-3aba4eb4253c.tar.gz，3,268,730bytes，SHA256=22ae38de7d2c751717a4ef351d0dc8f75491f2274a1bfea11e0a2e38c251b149。runtime含manifest8,537,017bytes，不含完整Python二进制；runtime内容图hash仍95c7215bc78d43cae809e99fcc65c1572cd611c87ae273afb80138b61c01e6ec。
- [实测] 使用最终归档binding重新完整回归：306passed/0failed/0errors/1skipped（仅E12）。全新目录解包的-I -B -S preflight/probe/restart-check/实际SIGKILL(-9)/UNKNOWN回滚/恢复/rollback/collect与tamper阻断PASS；25targeted包括全局site启用时在任何包访问之前拒绝启动。完整证据final_bundle_validation.json、final_runtime_junit.xml、final_delivery.json、compatibility_matrix.json。
- [未知] 实际宿主访问/上传/安装仍未运行，FIRST_REAL_CLOUD_SHADOW=BLOCKED_NO_HOST_CHANNEL；手工上传仍需要。宿主真实ABI/hook仍UNKNOWN，native Iris生产KV/runtime extraction未启用。真实模型0/E12 NOT_RUN、生产修改/调用/私忆/secret值/外部消息均0，新Core SQL表0。上条“待重建”已由本包开发验收闭合，不代表真实宿主验收闭合。

[实测] C-066：Shadow Bootstrap startup isolation: disable global site hooks and fail closed before bundle access; 25 targeted passed；指纹锚点 431dc2faf4e6ed582355fec6fc6a0d8efc62035709b3fb971b0230e9f7acd2cb；仅本检查点文件状态，不证明生产。

[实测] C-067：Shadow Bootstrap FINAL: 306 passing regressions, isolated archive SIGKILL recovery, compatibility matrix and exact operator upload receipt；指纹锚点 97639b5ec7269707930f1916cbaa6233bcfe5303a485d03b1ae36f4df743c702；仅本检查点文件状态，不证明生产。

## 2026-10-11 UTC · Real Host ABI fix 开发验证

- [用户提供] 新真实宿主preflight事实为Ubuntu24.04/x86_64/glibc2.39/Python3.12.3/SOABI cpython-312-x86_64-linux-gnu；旧包已到宿主，但BLOCKED_RUNTIME_ABI。本轮不登录宿主，不把用户提供的报告当成本轮实机采集。
- [实测] 旧入口在private extension load前精确要求3.12.14，actual Ubuntu3.12.3复现该拒绝；不能从patch字符串推导ABI不兼容。
- [实测] 独立Docker Ubuntu24.04/glibc2.39/真正CPython3.12.3（3.12.3-1ubuntu0.17），SOABI/EXT_SUFFIX匹配；使用原私有binding c18e64abba400c9c1ee91327680ce388dd51b4fb090b52ad829257ba19d82705，SQLite3.51.3/Pydantic2.13.5。原runtime全量306pass/0fail/0error/1skip(E12)，bounded205连接refcount53->53，WAL/backup PASS。首轮缺Git的4fail/6errors日志保留，补齐开发镜像后通过，未改断言。
- [实测] 修正ABI/失败分类及原Shadow回归targeted37pass。新包待固定support提交后生成；批准Core55文件仍ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513；仅改support ABI条件/metadata并复用旧runtime二进制，不降SQLite门、不携带完整Python。
- [未知] 新包真实宿主复测尚未运行；AstrBot实际hook UNKNOWN、E12 NOT_RUN、真实模型0。本轮生产修改/私忆/secret值/外部消息均0。

[实测] C-068：Shadow host ABI: actual Ubuntu CPython3.12.3 verifies original runtime, classified preflight and ABI policy; 37 targeted passed；指纹锚点 2c8834c8a290ae9c5efb3457f1a31c625feeef88620d06276a9979d66bb2a0bd；不证明生产运行。

### 2026-10-11 · Host ABI 最终包工程验收

- [实测] clean support cd2e8a302a6dc53ee1bb4449a04aa5a739d58cf7生成新包nana-shadow-bootstrap-host3123-cd2e8a302a6d.tar.gz；3,270,530bytes；SHA256 c793991badd5efeaaa4676730278c2cdf3f2e01ee5ccafd1626edc4819b49c88。Core仍ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513/55文件；原extension c18e64...和runtime内容图95c721...不变，只修support/metadata，runtime含metadata8,537,337bytes。
- [实测] actual Ubuntu24.04/Python3.12.3/glibc2.39/SOABI cpython-312-x86_64-linux-gnu完整318pass/0fail/0error/1skip；actual开发Python3.12.14/glibc2.41完整同为318pass/0fail/0error/1skip。每个环境新解包preflight/probe/restart-check/真正SIGKILL(-9)/UNKNOWN恢复/rollback/collect/tamper阻断PASS；身份/原始事件/候选/Shadow draft/decision连续，唯一probe1，Action/Grant/生产预算/外部消息0。
- [文档/实测] ABI门采用implementation/minor/normal build/SOABI/suffix/OS/arch/glibc及实际扩展加载，失败具体分类，HOST_GLOBAL_ENV与SHADOW_RUNTIME_ENV完整字段；3.12.3/3.12.14是实测coverage，其他3.12.x UNTESTED。无需完整隔离Python，不重建原extension，不修改服务器/系统Python/AstrBot。
- [实测] 单包保存为私有开发分支artifacts/shadow-bootstrap生成交付资产，白名单/每entry路径/凭据模式/许可证及hash审查后commit/push；remote字节核验将在下一检查点记录。不是正式部署、不触发Actions workflow（repo无.github workflow）。旧包22ae38...保留不覆盖。
- [未知] 新包真实宿主复测未执行，真实AstrBot hook UNKNOWN。E12 NOT_RUN/真实模型0；生产修改/调用、私人记忆/secret值/外部消息0，owner/memory authority未切换，Core新增SQL表0/runtime依赖新增0。

[实测] C-069：Shadow host package: dual actual Python full318 regressions and SIGKILL validation, fixed downloadable private-branch archive；指纹锚点 cc671ee53599461c64d33c998ca2b83ab71b8cd4a659dd572f89053c20b194d1；不证明生产运行。

[实测] Host ABI远端资产闭合：GitHub私有开发分支commit 659e3f55104363ab0b21fe0709b2ecc2e1792e95已保存单文件artifacts/shadow-bootstrap/nana-shadow-bootstrap-host3123-cd2e8a302a6d.tar.gz；新建独立bare repo实际fetch/read remote blob，3,270,530bytes及SHA256 c793991badd5efeaaa4676730278c2cdf3f2e01ee5ccafd1626edc4819b49c88完全一致。下载URL在final_delivery.json/remote_asset_verification.json/docs，非仅/workspace路径；本轮未操作真实宿主。最终报告提交以HEAD/ls-remote为准；318pass/0fail/1skip每解释器，无后续代码变更。

[实测] C-070：Shadow host FINAL: verified remote downloadable archive bytes, actual dual-Python318 regressions and unchanged production scope；指纹锚点 65e4a64556252313bd3ff2144e7ebf9ad0d011e3872cd1b5f31d93ace9f93c1d；不证明生产运行。


---

## 2026-10-11 (CST) · Shadow Bind R02：dispatcher 审计 + observer 开发副本（**状态口径修正**）

> SUPERSEDES 早前 `FIRST_REAL_ASTRBOT_SHADOW = BLOCKED_RESTART_REQUIRED` 的措辞。

| 状态键 | 值 |
|---|---|
| `AstrBot dynamic reload supported` | **YES**（源码级：`star_manager.py:1010/1068`） |
| `Restart required by framework` | **NO** |
| `Permitted dynamic load channel` | **BLOCKED_AUTH_REQUIRED** |
| `Observer registered` | **NO** |
| `host_binding` | **UNVERIFIED** |
| `FIRST_REAL_ASTRBOT_SHADOW` | **BLOCKED** |
| `Internal synthetic dispatch available` | **NO** |
| `Real dispatcher probe` | **BLOCKED_NO_INTERNAL_PROBE** |
| `AstrBot runtime` | 4.28.0 / Python 3.12.14 / CONTAINER / `ASTRBOT_RELOAD` 未设（`[实测]`） |
| `Iris schema compatibility` | **SCHEMA_COMPATIBLE**（11/11 类逐字段一致） |
| `observer dev copy` | 已实现 + 9/9 离线测试 + 已打包指纹（**未安装**） |

- [实测] 开发基线已切至 `dev/nana-core-v1-astrbot-shadow-bind` @ `c3ada9b09faa8a2683f98d5c8bafec24779cfd71`
  （本地旧 `master@18bc736` 不再作为实现基线；三个未提交证据文件已备份至 `/root/nana_dev/_evidence_backup_20261011/` 并随分支保留）。
- [实测] 本轮零漂移：重启 0 / secret 读取 0 / 认证绕过 0 / 生产源码改动 0 / 生产插件目录触碰 0 / 外发消息 0 / 私人正文读取 0。
- [未知] 最短路径：**姐姐在已登录 Dashboard 手动点一次插件 reload**（奈奈不读 JWT、不重启），奈奈随后只读取证 —— runbook 见
  `docs/nana_shadow_observer_dev_20261011.md` §6。
- [未知] 该路径只能证明 **registry binding**，**不证明** dispatcher traversal。

[实测/开发] C-M0: Baseline 318 passed, E12 skipped; source audit and API evidence gap recorded。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 c110b3d8b75d808fa6b37c9f18cf4feb97bf27e0581c96135b5882851c676481，不证明宿主运行。

[实测/开发] C-M1: Metadata sanitizer and no-response observer contract; 13 targeted passed, collection failure retained。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 233f0599cac2b1881e5ac5d76085ea1e95ce54cf56598b48aa405c34a0e4bbd5，不证明宿主运行。

[实测/开发] C-M2: Persistent Store alias dedup and reviewed-origin binding proof; 13 targeted passed; unchanged approved Core。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 a6043107ea733679ac8c955c645d6df16b753b408aecfc8b333fb4411e1e74c7，不证明宿主运行。

[实测/开发] C-M3: Shadow barrier and bounded callback failure isolation; 9 targeted passed including actual SIGKILL gap recovery。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 47348a1e5f3f9cdb24f4c27e4e3a7c24cd3c333db317856ac74144a0226a26bd，不证明宿主运行。

[实测/开发] C-M4: Source-gated AstrBot registration block and exact neutral registry lifecycle; 3 targeted passed, shared audit still absent。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 b5c722d274c41db1d8cc8487592a657221b0bac72c79c30e9934d9a68cb7b37e，不证明宿主运行。

[实测/开发] C-M5: Exact-query Iris schema inspector with authorizer and frozen-source comparison; 13 targeted passed, real compatibility UNKNOWN。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 34ff63403807bc52b0fc58216f3554f37785500debabfe7753f04215419b5213，不证明宿主运行。

[实测/开发] C-M6: Observer development kit builder, independent Core proof readback and operator rollback/runbook; 13 targeted passed, real shim blocked。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 9ce97c99cd96b90919fdb8ea0c14f03726abb1ab547e050c3f040b10be0c45fc，不证明宿主运行。

[实测/开发] C-M4-SOURCE: Nana audit652a72f absorbed by reference; source-backed 4.28 lifecycle shim and safe unload, 21 targeted passed; dispatcher still blocked。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 b414c713192561130f562b10c177f7cebbb18bbf1efed2a682e9bda578f54239，不证明宿主运行。

[实测/开发] C-M7-HARDEN: Lifecycle shim and kit validated in two actual Python environments; fail-closed BaseException/deferred completion guards, 22 targeted passed。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 1476c7707bc0b2a6b982ac96e692b13fb6123473aa39da3c803e78b10848c421，不证明宿主运行。

[实测/开发] C-M7: Final full regression 372 passed one E12 skip; reviewed observer kit archive, approved55 unchanged and zero production actions。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 e7e2042cc4c39806fcec6c3388b033f15f49cb2b6ab6fac0bad2d6c0b2f56676，不证明宿主运行。

[实测/开发] FINAL: Remote archive bytes verified; ordered Nana development handoff, 372 pass one skip; real dispatcher remains unverified。IMPLEMENTED/TESTED only；真实AstrBot binding UNVERIFIED、E12 NOT_RUN、Codex生产操作0。指纹锚点 b01f90794a4322dd405fc41fa1d1c5d427392a8fac618c18f8b2753169454a4f，不证明宿主运行。


---

## 2026-10-11 (CST) · Shadow Bind R03：双分支合流 + SAFE message observer + 免重启加载路径

> 在 R02 口径之上**追加**，不改写 R02 的现场账本。

| 状态键 | 值 |
|---|---|
| `SAFE early all-message observer` | **NOT_AVAILABLE**（源码级，R03-M1） |
| `SAFE result-path observer` | **AVAILABLE** — `EventType.OnDecoratingResultEvent` |
| `Second-candidate observer` | `OnAfterMessageSentEvent`（发送后） |
| `Unsafe hooks` | `AdapterMessageEvent` / `OnLLMRequestEvent` / `OnWaitingLLMRequestEvent` |
| `message observer` | **IMPLEMENTED / TESTED**（开发副本，未安装；31 pass / 1 skip） |
| `Observer registered` | **NO** |
| `host_binding` | **UNVERIFIED** |
| `Real dispatcher traversal` | **NOT_VERIFIED** |
| `FIRST_REAL_ASTRBOT_SHADOW` | **BLOCKED** |
| `Permitted dynamic load channel` | **BLOCKED_AUTH_REQUIRED**（不变） |
| `NEW_PLUGIN_NO_RESTART_MANUAL_PATH` | **YES**（人工 Dashboard 上传 → 进程内 `load()`） |
| `plugin_set is real precondition` | **YES**（`waking_check/stage.py:163-169` + `star_handler.py:169-184`） |
| `HOST_SYSTEM_SQLITE_GATE` | **BLOCKED**（宿主 3.46.1 < 3.51.3） |
| `ISOLATED_APPROVED_RUNTIME_FULL_REGRESSION` | **NOT_RUN**（本机无达标隔离 runtime） |
| `E12` | **NOT_RUN** |

- [实测] R03 合流提交 `d3e8c818e9c770c10555e8731d65ab5dab74b019`（双亲 `652a72f` + `10581aea`，`--no-ff`）。
- [实测] Codex bundle sha256 `38b53b1598675cc81a12f376c11829bd0dd94e47c6cc817dc1c56f1d225439de`；`merge-base = c3ada9b09faa8a2683f98d5c8bafec24779cfd71`。
- [实测] PROJECT_BRAIN 冲突 `09/10/11` **逐块并存**，双方证据块（R02 现场账本 + Codex `C-M0…FINAL`）**完整保留**。
- [实测] 三方回归对照（R02 / Codex / R03）中 Codex ≡ R03 **逐数一致** ⇒ 零回归。
- [实测] 本轮零漂移：生产源码改动 0 / 生产插件目录触碰 0 / 安装 0 / reload 0 / 重启 0 /
  JWT·secret 读取 0 / 真实消息 0 / 正文读取 0 / Iris 私人内容 0 / 外发 0 / authority 切换 0。
- [未知] 下一步唯一人工动作：姐姐在已登录 Dashboard **手动上传 observer 插件并纳入 `plugin_set`**（届时单独授权）。

## R04-C0 (2026-10-11 UTC) — development baseline only
[实测/开发] Uploaded R03 bundle independently hash/verify/list-heads checked; sole base89385e98118da81bae751311fb6149f048b772a8. New independent R04 branch. Approved isolated runtime full baseline404 passed/0failed/1skip (E12). Existing R039-key adapter/support reused; real message gates remain closed. Evidence docs/nana_r04_evidence/baseline.xml and docs/nana_r04_one_shot.md. No real host operations.

[实测/开发] R04-C1 strict receipt contract14passed; fixed Literal accepting bool-as1 via pre-validation, failure log retained. max_uses1/window<=600sec/UTC/scoped hashes/store binding/strict canonical JSON. Production trust pins empty; no Core changes.

[实测/开发] R04-C2-C5: Atomic receipt and D-045 ingress/proof; 42 targeted passed, five actual SIGKILL boundaries; R03 pre-existing preflight drift disclosed. Fingerprint anchor f6f9186edf890c1bc6c253dac74779ccaf37ca05430d4303266816109c83ea88; real load NOT_RUN/dispatcher NOT_VERIFIED/host_binding UNVERIFIED/E12 NOT_RUN.

[实测/开发] R04-C6-C7: Failure-isolated real-metadata callback and read-only operator CLI; 53 targeted passed. Fingerprint anchor 0ec78b45d7e7dcd9c01a8edbfff2b14c1d451d050d66d0b43d4bee122d42d124; real load NOT_RUN/dispatcher NOT_VERIFIED/host_binding UNVERIFIED/E12 NOT_RUN.

[实测/开发] R04-C6-C8: Fail-closed operator CLI, 65 targeted passes, dormant message-only plugin and gated package/runbook. Fingerprint anchor 783fe3d03faf4cbdaf71bc996aed0c05a1509480712b56cb744970c463f1b10b; real load NOT_RUN/dispatcher NOT_VERIFIED/host_binding UNVERIFIED/E12 NOT_RUN.

[实测/开发] R04-C8-HARDEN: Dormant plugin blocks fixture trust and empty pins; 62 R04 targeted passed; earlier 65 count corrected to62. Fingerprint anchor 6fe8ab2aee25643b7b51a2717e9534759f2ddcf9e153318c537c1bf21e2bd994; real load NOT_RUN/dispatcher NOT_VERIFIED/host_binding UNVERIFIED/E12 NOT_RUN.
