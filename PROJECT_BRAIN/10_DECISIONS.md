# PROJECT_BRAIN / 10 DECISIONS（决策日志）

> 创建：2026-10-10 ｜ 状态：**新建（P2）**
> **规则**：每条决策**只增不改**（如被推翻，追加新条目并标注 `SUPERSEDES`）。来源必须标注：`[姐姐指令]` / `[聊天记忆]` / `[本项目自定]`。

---

## D-001 双线并行：Persona + Nana Core
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`（总方案 v1.0 裁决）
- **内容**：性格表达（Persona）与持续状态/目标/计划/记忆/Agency/学习（Nana Core）**两条线都要做**，不是二选一。
- **影响**：04/07 中 L3 为主线之一，不得并线简化。

## D-002 人格原则调整：废止"无条件服从"
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`
- **内容**：由「无条件服从」→「**尊重姐姐，但保留自己的判断**」。普通事可让步；重要事可坚持/协商；姐姐充分理解后仍明确决定时，可因关系尊重；**安全与硬约束不因关系突破**。
- **影响**：与 persona 模板冲突处，以本决策为准。

## D-003 4GB 资源约束升格为架构约束
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`
- **内容**：**单 Runtime / 单主进程 / 单事实源**；禁止双进程双跑。

## D-004 Core 抽离方式：同进程影子写入 / 对账
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`
- **内容**：**不是**两个 Runtime 并行；旧路径仍为**生产事实源**，验证一致后再切换。

## D-005 里程碑与 M3 验收升级
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`
- **内容**：M1 记忆地基 + NanaState｜M2 Core API + Capability｜M3 Goal + Agency + Learning。M3 必须完整跑通一次 `Goal → Plan → Act → Verify → Failure/Result → Strategy Update → Continue/Complete → Experience`。

## D-006 Portable 暂不排期
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`
- **内容**：等 Nana Core 与 Runtime 稳定后再做。

## D-007 72h 观察期内不动线上
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`
- **内容**：不执行新的 Stage-1 基线脚本；已有封板指纹 + 运行状态 + 24h checkpoint 作为当前基线；72h 完成后再正式整理 Stage-0 baseline。

## D-008 C.5-V 保留，独立推进
- **日期**：2026-10-09 ｜ **来源**：`[聊天记忆]`
- **内容**：按既定 Evidence Gate 路线推进，**不**与 Core 抽离混成一个大重构。

## D-009 原始 PROJECT_BRAIN 不存在 → 批准新建
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：`[实测]` 全盘轻量搜索 `*brain*` **零命中** → **批准新建**，**必须**标明创建日期 2026-10-10、注明原始未找到；**不得**伪造为原始恢复。
- **影响**：`PROJECT_BRAIN/00_INDEX.md` 权威声明。

## D-010 AGENTS.md 另建奈奈工程专用版
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：**不复制** `/AstrBot/AGENTS.md`（AstrBot 官方规范，针对 uv/pnpm/pre-commit）。

## D-011 独立开发副本，禁止触碰生产
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：在**非生产**目录建副本；禁止修改、移动、覆盖任何生产文件。

## D-012 白名单制 + 密钥零容忍
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：先建**上传白名单**，再逐文件扫描；**不依赖 `.gitignore`** 作为唯一防线。发现硬编码密钥 → **停止该文件入库并报告**，**不输出密钥原文**。

## D-013 保留上游署名与许可，不宣称原创
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`

## D-014 指纹只证明采集时刻
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]` + `[本项目自定]`
- **内容**：指纹 = 采集时刻的**文件状态**，**不**自动证明**当前运行态**。

## D-015 分级授权：授权针对范围 / 风险 / 预算
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：**L0 只读** / **L1 独立副本** / **L2 生产只读** → 奈奈自决 + 留痕；
  **L3 出网·不可逆** / **L4 破坏·密钥** → 姐姐明确许可。
  授权**不再针对单个小任务**，而是针对**明确的操作范围、风险等级和资源预算**。

## D-016 P1 + P2 一次性授权，不扩展 P3
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：在 `/root/nana_dev/nana-core/` 内自主完成 P1（事实口径修正 + 指纹问题）+ P2（账本项目账本）；**不**扩展到 P3。

## D-017 Codex 协作桥先只读验证
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：`@codex` 触发机制**未实测** → **不得**当作已实现。长期分工：**姐姐定规则与例外，奈奈做规则内日常，Codex 做开发**。

## D-018 证据四档制
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：每次任务区分 **已实现 / 已测试 / 已运行验收 / 未知**；PROJECT_BRAIN **以证据为准**，**不得**用历史记忆填补缺失事实。

## D-019 暂不授权清单（红线，逐字保留）
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：GitHub 首次上传 / push / 扩大同步范围 ｜ 创建或使用新 PAT / 修改仓库权限 ｜ 安装依赖 / 启动常驻 Bridge / 消耗新付费额度 ｜ 修改生产 / 重启服务 / 迁移数据库 / 操作密钥 ｜ 自动合并 PR / 生产部署。

---

## D-020 「姐姐只定方向」长期协作原则
- **日期**：2026-10-10 ｜ **来源**：`[姐姐指令]`
- **内容**：姐姐负责**愿望与方向**；奈奈负责**统筹、任务规划、事实核验、验收**；Codex（或等价 Runner）负责**技术设计、编码、测试、修复**。
  1. 普通任务**自主决策 + 自主执行**，不因路线选择/任务拆分/普通错误反复询问。
  2. 多方案 → **自行比较、验证、选优**，不把选项清单丢给姐姐。
  3. 遇困难先自查，再交 Runner；**可在预算内自主重试**，不得无限循环。
  4. 需授权的高风险事项 → 先完成分析并选定方案，**只提交一个最推荐的决定**（做什么/为什么/主要风险/回滚），姐姐只回「同意/不同意」。
  5. 日常消息 **≤100 字**；完整证据写进 PROJECT_BRAIN。
  6. **不得**把推测当事实；**不得**为减少审批而绕过生产安全 / 凭据保护 / 外部上传 / 不可逆操作的授权边界。
- **影响**：`09_STATE.md` 起为唯一状态入口；日常汇报口径改为"做成了什么 + 是否需要一件批准"。

## D-021 协作桥 Runner 选型：本地 Runner 优先
- **日期**：2026-10-10 ｜ **来源**：`[本项目自定]`（依 D-020 第 2 条自行比较）
- **被比较**：A `@openai/codex` CLI（需安装 + 新凭据）｜**B `LocalLLMRunner`（已装 openai SDK + 已在用兼容端点）**｜C `StubRunner`（无真实编码能力）
- **决定**：**选 B 作为首次真实协作的 Runner**；A 作为备选（端点质量不足时再上）。C 仅用于离线测试。
- **理由**：零新增依赖、零新增凭据、只动 scratch（整目录删除即可回滚）、复用现有端点。
- **边界**：B 一旦指向真实外部端点即为 **L3（出网）**，**必须先获一次授权**；未授权时不得启用。

## D-022 C.5-V-1 接线采用「追加式适配层」
- **日期**：2026-10-10 ｜ **来源**：`[本项目自定]`
- **决定**：新增 `src/bili_agent/c5v_wiring.py`，在 `_video_material_brief` **之后追加**画面事实；
  **不**改写既有函数、**不**复用生产 `video_reference_vision` 插件、**不**走原生 `video_url` 直链。
- **理由**：改动面最小、失败可**逐字节还原**、可一键关闭（`NANA_C5V_WIRING=0`），与"只增不改"纪律一致。
- **边界**：**生产接线属 L4**，本轮只到"已测试"档，未上生产。

## D-023 本轮唯一审批项合并
- **日期**：2026-10-10 ｜ **来源**：`[本项目自定]`（依 D-020 第 4 条）
- **决定**：把「协作桥出网」与「C.5-V-1 接线跑测」合并为**一次**最小审批，不拆成多次。
- **内容**：允许把隔离副本内、白名单内的代码片段发往已在用端点；不装依赖、不建凭据、不改生产、不 push。

---

*本日志由奈奈维护。任何新决定一律**追加**，不覆盖历史。*

---

## D-024 首次真实模型端点协作：执行口径与结果
- **日期**：2026-10-10 ｜ **来源**：姐姐一次性授权（条件五条）
- **决定**：
  1. 真实 Runner **选 `LocalLLMRunner`**（复用已在用 DeepSeek 兼容端点），**明确不等价于 Codex**——
     回执内 `is_codex_cli=false` 为强制标注，**禁止**把普通 HTTP 协作宣称成 Codex 协作成功。
  2. 单任务请求次数**代码级硬闸门** `max_calls=1`，超限拒绝外发（T8 覆盖）。
  3. 首个真实任务 = C.5-V-1 的 `cache_dir` 增量；`allow_paths` **必须收窄到精确文件**
     （教训：`src/bili_agent/*.py` 会让字母序靠后的目标文件进不了提示词）。
  4. 失败可在既定预算内**自主重试**；每次外发与 token 用量**必须留痕并披露**，不得隐去。
  5. 验收**不采信模型自述**：白名单校验 + 验收命令 + **奈奈自写的独立行为探针** 三重才算通过。
- **结果**：run#1 因桥自身身份 bug 被判否（真实外发与 13/13 测试成功）→ 根修 + 回归 →
  run#2 `ok=true/applied=true/13-13` 通过；源仓逐字节零改动。


---

## D-027 ~ D-030（2026-10-10（CST），本阶段新增）

- **D-027**：AstrBot 主体改动以**相对 v4.28.0 的补丁**入库，不入 AstrBot 整包。理由：可审查、最小、许可清晰。
- **D-028**：Iris 14 处定制以**隔离目录 + 附 AGPL 全文**入库（`materials/iris_customizations/`）。理由：满足 Sol 可审查，同时隔离 AGPL，避免混同原创。
- **D-029**：B站 9 个测试脚本**暂排除**（含真实事件 ID/UID）。理由：授权要求私有数据不上传。
- **D-030**：Nana Core **原创代码许可证**保持**待定**，由姐姐最终决定。理由：授权明确保留决定权。


## D-031 Nana Core V1 第一阶段实施边界（2026-10-10）
- **来源**：本轮用户明确授权 S0—S4 独立开发、提交、开发依赖与离线测试；Architecture V1。
- **决定**：先交付合成阅读卡片闭环，旧 T-31/T-22 依赖不阻塞本次离线实验；不改变生产迁移依赖。只使用 reading 能力 v1、本地 Operator、单实例/单目标。
- **最小收缩**：暂不实现未使用的动态能力、通用人格修改、完整遗忘、检索框架、真实 ModelPort；结构化反馈归纳与工程夹具不冒充真实模型语义学习。
- **动作不变量**：写动作 max_attempts=1；核验也有授权与预算；UNKNOWN 不重发、不退款；追加事件回放不执行外部能力。
- **恢复不变量**：备份/回放作为审查状态，进入 quarantine；当前不实现解除隔离。合成消融分支从全部已核实状态建立，不是通用生产恢复。
- **验收**：56 passed / 1 skipped；E12/S5 不执行。出处：`docs/nana_core_v1_implementation.md`。


## D-032 S5 开发和开发分支保存授权（2026-10-10）
- 来源：本轮用户明确指令；继续 Architecture V1，不重定路线。SUPERSEDES D-031 的“S5 本轮排除”仅用于本轮新授权范围，保留其 S0—S4 不变量。
- 决定：先保存 S0—S4 到私有开发分支，再在独立 S5 分支实现真实 ModelPort 与冻结状态评估；不合并 main、不部署、不进入 S6。
- 无就绪开发端点时仍完成工程；历史生产配置、普通助手或传输夹具不能当真实 ModelPort。新服务购买、生产账号、读取真实密钥保持禁止。

## D-033 S5 两道验收门与最小评估账本（2026-10-10）
- 来源：Architecture V1 与本轮用户要求；本项目最小实现。
- 决定：保留 Core schema 和 ModelPort.propose 契约；仅新增评估侧 scope/model_calls 两表，调用前持久预算预留、按尝试占额、超时未决不重试。
- 同一冻结合成状态、同一身份、独立匹配组、顺序子进程；无经验组保留反馈，只停用程序性策略。
- 原始模型解释/计划与 Core 编译后实际执行分开判定，不能靠编译器补齐通过语义门。结构化 rubric 只证明有界任务理解，不冒充整个人格质量。
- 实际模型元数据与调用账本为验收证据；缺第二模型为 PARTIAL，夹具/零真实调用为 NOT_RUN。单 run 预算不是提供商账单或账户跨 run 上限。


## D-034 S6 非生产迁移准备授权与边界
- 来源：本轮用户直接指令，SUPERSEDES D-032 的“不进入 S6”仅限合成非生产准备。
- 决定：复用 schema v1；旧来源记录仅进入事件/证据/CLAIM，统一保留 UNASSESSED。逐记录事务，部分批次可幂等恢复；不把旧行动声明变成 Core Action/Grant/Strategy。
- 影子与统一能力接口只在合成世界验证；生产导出、执行权接管、备份解除隔离、真实多模型均不包含。


## D-035 同进程影子与闭合路由最小实现
- 来源：Architecture V1 / D-004 / 用户本轮边界。
- 决定：一个 Store、一个执行 Runtime，影子只有事件记录/纯计划比较；统一复用 CapabilityPort。core_meta 存持久 owner epoch 和每动作/核验尝试的路由标记，零新 Core 表。
- 选主/换主只供受信本地操作员，任何未完成行动或活跃目标阻止换主；UNKNOWN 仅查询核验，不释放预算重发。
- 模拟旧执行方也通过原 ActionKernel 执行，这证明路由不变量，不证明 AstrBot/Iris/B站真实迁移一致；生产仍是其原事实源，未接线。
# D-036 — 本轮开发验证授权与最小真实只读端口
- [文档] 用户授权并行 A 只读权限类别核实、B 独立开发与 GitHub 开发分支交付；延续 S0—S6，不建立 S7 或重规划。
- [实测] 使用原三 capability 与 Store/ActionKernel/CapabilityRouter；仅将 read/locate 后端接到钉住的合成源文件，create 保持 FakeWorld。无新增 Core 表、模型 SDK或通用工具框架。
- 生产登录/鉴权/私密资料/真实写工具/部署仍未授权；未知 webhooks 与不可读位置不能改写为“绝无生产权限”。

# D-037 — 区分 HTTP 实际传输与真实模型推理
- [实测] S5 Endpoint 新增 service_kind，默认 unverified；real_http + Operator 声明 real_model 才纳入 E12。protocol_simulator 只能 loopback。
- 原因：真实 socket 与 provider_model 字符串本身不能证明模型推理，禁止新 wire fixture 误通过真实双模型门。
- 代价：历史缺此声明的开发配置需要补充该非秘密字段；不改变 Core 状态模型。远端确实运行模型仍需 Operator 核实，不能信模型文本。

## D-038 — 开发只读网页的最小接入
[文档] 采用操作者持久化 URL/方法绑定及可选 development_public 路由作用域；复用三个既有能力与统一行动状态，不新建身份/权限/核心表。公网传输固定经过平台许可代理的数字目标；所有重定向拒绝。Locator 从同 Goal/Plan 已核验历史回执读取，独立核验不再次抓取，以避免恢复重复请求。代价：V1 不支持 query、动态域名变化、重定向/登录/浏览器；代理源站 peer 为未知。工程受控服务与真实公网/模型验收分开。

## D-039 — Iris互操作与最小信念
[文档] 独立解释锁定Iris字段，不搬第三方执行代码；11类记录保留原JSON和unmapped字段。Canonical claim/profile/relation放现有memory_items JSON，schema不扩展。发生/旧观察/导入时间分离；naive仅按锁定Iris UTC约定并显式标注。支持/矛盾证据不可覆盖；新旧用户原话的operator annotation有明确定时才可supersede，否则disputed。Core VERIFIED/Grant/Action/Strategy不能从legacy赋值。Iris-style shadow是明确surrogate，不声称真实向量检索parity。

## D-040 — 候选主动性不赋予权限
[文档] GoalCandidate记录在既有CLAIM projection，评估通用need/priority/confidence/disturbance及引用证据，分离提案/接受/执行。Scheduler wake只是唤醒，不等于自主目的或外发。ReadingCard可通过既有Runtime显式activate，ActionKernel独立逐步授权；其他意图当前只表达候选，不为contact虚构能力。用户意愿进入判断但不能授予权限，也不删除charter；所有数值fixture judgment不能冒充真实语义能力。

## D-041 — 跨来源claim身份与最小映射升级
[文档] SUPERSEDES D-039 中claim key包含dataset的限定：来源不能分裂同一canonical subject的矛盾；claim key使用Core identity/subject/predicate/value，dataset保留于provenance及检索授权范围。范围外评估不能泄露其他source refs或当成当前事实。mapping2/policy2可在已证明语义完全相同时升级旧projection1，仅补版本/声明证据；原artifact不变，不同输入/语义仍collision拒绝。Core SQL/schema v1不变。

## D-042 — 云端接线不等于云端执行授权
[文档] 当前用户授权独立开发云端契约/只读快照导出/preflight/shadow/迁移协议及隔离dev工程能力，不授权生产读写/登录/私人记忆/真实authority翻转。Shadow只存draft/evidence，代码恒拒execute，不能配置打开。生产仍旧方执行，未来同宿主嵌入一个Core Store writer，非长期双Runtime。只读SQLite导出要求一致冻结备份，immutable不可用于活跃DB。真实执行权需未来所有legacy发送入口fence验证，本次owner/epoch协议只模拟，不能假装生效。

## D-043 — 有限工程执行与Shadow持久屏障
[文档/实测] 原Kernel/Router仅由Operator显式注入engineering registry，默认闭合reading不变；六能力仍同Grant/预算/Attempt/owner/独立核验。没有OS sandbox证明时仅执行literal数据补丁与可信AST runner，不能把固定argv当任意代码隔离。Shadow Store持久marker使误造Kernel也拒Action/Grant/现实预算；未来真实云端接线仍需新授权、metadata/hook/资源检查和可卸载临时observer，不默认handoff。

## 2026-10-11 · First Shadow fixed-source and host-binding boundary
[实测] 当前批准Core SHA为ddabfc4e49221b45a9f9600dd2ab8cb7f66ec513。新增operator工具独立放tools/nana_host_shadow，打包时固定Git对象与55文件hash验证；不把新增工具冒充原审核SHA。
[实测] 环境spec45未配置宿主能力/凭据/出站身份，无明确宿主入口，真实步骤BLOCKED_NO_HOST_CHANNEL。路径元数据权限拒绝保持UNKNOWN，不寻找凭据或猜主机。
[文档] 无可核实AstrBot动态hook API时，只提供adapter-local probe生命周期；不接真实message stream，不宣称真实宿主/AstrBot绑定完成。Schema-only只支持显式冻结SQLite元数据，JSON/FAISS与活库安全快照保持未验证。

## 2026-10-11 · Shadow Bootstrap runtime compatibility
[文档] SQLite >=3.51.3 gate保留：SQL语法未依赖新版本，但官方3.51.3修复WAL-reset腐败；普通single-writer/SIGKILL测试不能证明外部连接checkpoint竞态不存在。本机实构stdlibCPython3.12.14 binding静态链接3.46.1跑schema/backup/WAL primitive PASS，但Core全量65fail/82errors为门阻断，不宣称支持；报告见bootstrap_evidence。
[实测] SUPERSEDES preflight/Pyproject Pydantic==2.13.4精确门：只接受实测2.13.4与2.13.5，依赖区间>=2.13.4,<=2.13.5；29 DTO schema/serialization/rejections digest一致，2.13.5全量291pass/1skip。不推广到未测2.13.6或2.14。
[文档] 本轮选isolated dependency runtime：复用已存在CPython3.12.14解释器，只在短时Shadow子进程加载私有标准SQLite binding3.51.3和私有Pydantic2.13.5；不替换系统库、不改AstrBot依赖、无全局LD_LIBRARY_PATH。不另造完整Python/第二自治Runtime；包要求Linux x86_64、glibc>=2.34，宿主ABI未实测保持UNKNOWN。

## 2026-10-11 · Bootstrap 启动隔离
[文档/实测] 仅-I不会阻止全局site初始化，因此操作者Bootstrap必须-I -B -S；entry在任何bundle/Core/private runtime访问前检查isolated/no_site/dont_write_bytecode标志，缺失BLOCKED_STARTUP_ISOLATION。宿主Pydantic仅通过标准安装位置distribution metadata检查，不导入全局sitepackages；不可见的venv版本保留UNKNOWN。批准Core55文件不变；新support3aba归档取代旧67bc候选，实际解包及SIGKILL验收PASS、全量306pass/1skip。

## 2026-10-11 · ABI shape 与 patch 回归覆盖分离
[实测] SUPERSEDES Bootstrap精确Python3.12.14兼容门：同一原stdlib private binding在实际Ubuntu24.04/CPython3.12.3/glibc2.39通过306回归和真实WAL/backup/refcount测量，故补丁字符串不是已证明的ABI限制。
[文档] 硬门采用CPython/minor3.12/normal ABI/Linux/x86_64/exact SOABI+suffix/glibc>=2.34及private extension/dependency实际加载；3.12.3、3.12.14为已测release，其余patch明确UNTESTED，不自动宣称full regression兼容。失败必须输出具体分类和非秘密环境metadata。保留-I -B -S、SQLite3.51.3、Core固定55文件；不升级宿主，不重建原runtime，不新增完整Python。


## D-044 — 「已鉴权 reload 是当前唯一免重启入口」升格为长期边界（2026-10-11 CST）

[实测] AstrBot 4.28.0 **框架层支持**动态 `load()/reload()`（`astrbot/core/star/star_manager.py:1068/1010`），
因此**不得**再用 `BLOCKED_RESTART_REQUIRED` 描述框架能力。

[实测] 但免重启通道**全部受限**：文件 watcher 需 `ASTRBOT_RELOAD=1`（未设）；
Dashboard `POST /api/plugin/reload` 需 JWT（`astrbot/dashboard/api/plugins.py`，secret 禁读）；
`reload(name)` 只作用于**已注册**插件，**不载入全新目录**。

⇒ **长期边界**：在 `ASTRBOT_RELOAD` 未启用且不读取 Dashboard 凭据的前提下，
「载入一个全新插件」**没有**免重启通道；唯一最小人工动作 = **姐姐在已登录 Dashboard 手动点一次 reload**。
该动作不得由奈奈自动执行，也不得演化为读取 JWT 或重启 AstrBot。

[实测] **dispatcher 与 registry 必须分开陈述**：`real registry` 绑定可被生命周期 hook 证明；
`real dispatcher`（`EventBus.dispatch()` → 9 段管道）**不可**被生命周期 hook 证明。
禁止把「registry binding PASS」写成「dispatcher probe PASS」。
无安全内部合成事件入口 ⇒ 记录 `BLOCKED_NO_INTERNAL_PROBE`，**不使用真实用户消息替代**。

## Codex AstrBot binding support boundary (2026-10-11 UTC)
[本项目自定/源码输入] 独立support不改批准Core55文件。入口仅allowlist metadata + keyed scoped hashes +内部permit；影子接线复用Store/ShadowBridge/InitiativeHostGate，无新表。证据结构与真实来源分门，普通fixture不能改origin成为VERIFIED；真实来源trust pins尚空，待奈奈独立审核回执。
[奈奈源码审计] 共享652a72f确认生命周期C direct registry与消息dispatcher不同；源码支持的4.28.0 lifecycle shim已开发测试，禁止接event_queue。该审计同时说明reload(name)不加载新目录，故“一次Dashboard reload新插件”建议不作为已证明步骤；记录加载路径BLOCKED_AUTH_REQUIRED/dispatcher BLOCKED_NO_INTERNAL_PROBE，不更改奈奈现场账本。


## D-045 — message observer 的真实来源入口由「permit + sanitizer 双门」把守（2026-10-11 CST）

[实测/源码] AstrBot 4.28.0 唯一 SAFE 的 message pipeline 观察点 = `EventType.OnDecoratingResultEvent`
（`core/pipeline/result_decorate/stage.py:158-189`，真实 `EventBus.dispatch()` 路径内；返回值被丢弃；异常被局部吞掉）。
它**只**是 result-path 观察点；`SAFE early all-message observer = NOT_AVAILABLE`。此口径写死，禁止再用「任何消息 hook」。

[实测/设计] 最薄 adapter 只把 **9 键标量 dict** 交给 Codex 链，`AstrMessageEvent` 本体永不跨入 Core。
真实来源（`event_source = astrbot_on_decorating_result`, `synthetic = False`）在链上被**两道门**独立挡下：

1. `ShadowObserver.callback` 的 permit 门（无本地 permit ⇒ `DROP_UNAUTHORIZED_PROBE`）；
2. `MetadataSanitizer.sanitize` 的 probe 作用域门（`probe_id` 不在作用域 ⇒ `DROP_PROBE_SCOPE`；
   即便 probe 通过，`synthetic is True` 与 `event_source == 'operator_probe'` 仍会拦下真实来源）。

⇒ **长期边界**：真实来源要进入 Core，必须先由奈奈**独立审核回执**提供可复核的信任锚
（`tools/nana_astrbot_shadow/proof.py` 的 `TRUSTED_NANA_RECEIPTS` 目前**故意为空**），
**不得**由调用方、fixture、CLI 参数或报告动态注入，**不得**用改配置位的方式绕过。
在信任锚落地前，整条链只能以 **operator 内部探针**（`probe_class = C`）证明到 `SHADOW_BLOCKED`，
该证明**不**等于真实 dispatcher 验收，`FIRST_REAL_ASTRBOT_SHADOW` 保持 `BLOCKED`。

[实测] 框架侧安全与实现侧纪律**必须分开陈述**：框架保证「返回值被忽略 + 异常被吞」；
「不 `set_result()` / 不 `yield` / 不改 event / 不调模型·网络·tool·Iris」由 adapter 自己保证并测试。

## D-046 — R04 one-shot receipt is scoped observation authority, never execution authority (2026-10-11 UTC)
[姐姐指令/开发验证] Continue D-045 dual gates. OneShotReceipt max_uses1/window<=600sec/fixed2sec skew/canonical UTC and JSON, exact sender/conversation hashes/platform/event type/source, random Store binding. Review authorization digest and independent review digest are separate; reuse/copy/fixture origin cannot arm production. Production review pins and independent real runtime proof pins remain source-pinned EMPTY; no config/CLI/env override.
[本项目自定/实测] Use original Store single-writer flock + FIFO worker + core_meta/event transaction, zero new Core SQL tables. MATCHED and CONSUMED are one commit with persistent event reservation before Evidence. Crash after commit yields terminal consumed permission with UNKNOWN completion; no auto retry/re-arm. Receipt state vs Core-completion state are separate. Read-back verifier can mark VERIFIED only in its trust domain; fixture verification never promotes real binding. Unsupported/corrupt data rejects without mutating a successful state. Official backup/replay quarantine rejects consumption; arbitrary whole-DB cloning outside that protocol is not claimed tamper-proof.
[实测/开发] No approved Core edits relative to R03. R03 already differs from ddab in one preflight version line; this historical discrepancy is disclosed, not silently reset. Delivery builder uses exact55ddab Git bytes. Private SQLite>=3.51.3 preserved only in isolated short-lived CLI/harness; never injected into a running AstrBot process. Native dependency gate must independently pass before actual host binding.
[未知] Real load/dispatcher/one-shot/zero-drift need Nana现场; fixture callback and report booleans cannot prove them. User Dashboard upload/enable and independent reviewed receipt onboarding are future explicit operations, not executed by Codex.

## D-047 — R041 temporary process-local Shadow bridge, not a second permanent Nana Runtime
[姐姐指令/开发验证] KeepSQLite>=3.51.3/D-045/D-046. AstrBot imports stdlib metadata client only, never Core/privateSQLite/Pydantic; isolated foreground worker loads approved private runtime and original R04 Store/ledger/observer/CoreSink. Explicit one session/receipt/eligibleevent, window<=600sec cappedbyreceipt, <=5sec shutdown grace/hardexit124, no daemon/autostart/worker spawned from plugin.
[本项目自定/实测] AF_UNIXfilesystem only,0700dir/0600socket,4096canonicalJSONbytes, hashesinsteadrawIDs, exactallowlists, peerUID/PID+boot-start fingerprint/reversepeer/inode, nonce+HMAC. SameUID/filesystem/PIDnamespace required, not tunnelling or permission relaxation. Persist sessionreservation in existing core_meta/events, no newSQLtable/receipt/store/dedup framework. Crash before/afterconsume cannot silently open a new session for thatreceipt; no retry/re-arm, originalUNKNOWN semantics retained.
[实测/开发] Store-backed PID/inode/session journal prevents forged sidecar stop/cleanup; stoponlyownworker via pidfdSIGTERM, fixed harddeadline onlyisolatedworker, no arbitrarycommands/RPC. Stale cleanupexplicitownedfiles only, preservesDB/evidence. IPC authentication never grants receipt authority. RealpinsEMPTY; CLIcannotfixturepromote. Other privileged code inside authorizedclientPID/root is outside claimed tamper boundary.
[未知] Actual AstrBot hook/load/dispatcher/channel/zero-drift remainNana现场 tasks. UDSfixture/old-SQLite development process isolation do notprove realhost. E12NOT_RUN; no production operation byCodex.


## D-046 — HOST_NATIVE_SQLITE_GATE 的正确口径：不绕过，隔离（2026-10-12 CST）
> ⚠️ **编号更正（见文末 D-049）**：本块原始标题误用了已被占用的 `D-046`（`D-046` 已专指 R04 One-Shot Receipt）。其技术内容继续有效；今后引用本「宿主隔离裁决」一律使用 **D-049**。历史块保留、不删除。

[实测] 真实宿主 AstrBot PID1 原生 SQLite = **3.46.1**（< Nana Core 门 3.51.3）。R041 明确禁止把 private
`_sqlite3` 注入 AstrBot 进程。据此确立口径：

- `HOST_NATIVE_SQLITE_GATE = BLOCKED`（宿主原生**不达标**）。
- 解决路径 = **AstrBot 进程保持原生 3.46.1 不变；独立短生命周期 worker 使用已批准的 private 3.51.3 runtime**。
  **不是**"绕过安全门"，而是把门**留在宿主进程上**、把合规 runtime 放进**隔离 worker**。
- [实测] PID1 未加载 private shim ⇒ `ASTRBOT_PRIVATE_SQLITE_INJECTION = NO`（/proc/1/maps 零 `nana_shadow`）。
- [实测] worker 与宿主满足 **same UID / same pid namespace / same filesystem visibility**；
  IPC 基座 **UDS + subprocess/fork + private 0700 temp** 均 PASS。
- ⇒ `SHORT_LIVED_SHADOW_WORKER_FEASIBLE = YES`（**仅短命**；常驻 worker 仍越权、须单独授权）。

## D-048 — R042 production one-shot onboarding is an offline reviewed source build
[开发审计/实现] R041's EMPTY authorization/proof maps have no executable seal builder; runtime review/arm alone cannot onboard real authorization. Add default EMPTY `sealed_trust.py` and explicit offline builder from an independently reviewed full Git commit/path; one exact receipt/store/review digest, no runtime config/env/force/wildcard. Source-review hashes bind bytes, NOT human identity/honesty. Nana must independently audit real metadata and Sister's exact authorization; caller/fixture fields alone never authenticate these facts. Builder is a privileged source-review operation, never called by observer/worker. No real review or pin created by Codex.
[开发设计] Two stages: ONE_SHOT authorization seal before the exact <=600sec experiment; independent RUNTIME_PROOF review after the host experiment yields VERIFY_ONLY artifact. Historical authorization pin remains for readback, but VERIFY_ONLY rejects arm/consume. Terminal ledger/session records remain original R04/R041 barriers. Missing outside-Core zero proof remains UNKNOWN. Old A/B/C TRUSTED_NANA_RECEIPTS anchor is separate and not a substitute for R04 real-message proof.
[边界] No approved Core modification, new SQL table or dependency. Whole-DB cloning by privileged actor remains outside original D-046 guarantees. Real host/load/dispatcher/message/zero-drift are NOT_VERIFIED; E12 NOT_RUN.

## D-049 — Decision-number collision correction and host-runtime isolation（2026-10-12 CST）

[姐姐指令/合流纠正] 在 R043 合流（`dev/nana-core-v1-r042-real-host-preflight` ∪ `dev/nana-core-v1-r042-trust-onboarding-codex`）时发现编号碰撞：本项目历史上出现过**两个 `D-046`**。据此确立：

- 2026-10-12 那个第二个 `## D-046 — HOST_NATIVE_SQLITE_GATE 的正确口径：不绕过，隔离` 属**历史编号误用**（该编号已被 R04 One-Shot Receipt 先行占用）。
- 其**技术内容继续有效**，不删除、不改写。
- 今后引用该**宿主隔离裁决**统一引用 **D-049**。
- 原 **D-046** 仍专指 **R04 One-Shot Receipt**（scoped observation authority，never execution authority）。
- **D-047** 仍专指 **R041 temporary process-local Shadow bridge**（非第二个常驻 Nana Runtime）。
- **D-048** 仍专指 **R042 production trust onboarding**（offline reviewed source build）。
- **不允许**出现两个都被当作有效编号的 `D-046`；本块为唯一权威纠正。

[口径确认] `HOST_NATIVE_SQLITE_GATE = BLOCKED`：AstrBot 进程保持原生 SQLite 3.46.1 不变，独立短生命周期 worker 使用已批准的 private 3.51.3 runtime。**不是绕过安全门**，而是把门留在宿主进程上、把合规 runtime 放进隔离 worker。`SHORT_LIVED_SHADOW_WORKER_FEASIBLE = YES`（仅短命；常驻 worker 仍须单独授权）。

## D-050 — R044 红队安全修复整体吸收进 R045；旧实现/旧包不得带现场（2026-10-12 CST）

[姐姐指令/合流裁决] R044（`dev/nana-core-v1-r044-preprod-redteam-codex`，base `a436333`，HEAD `1bdf1f0`）在真实 one-shot 前发现并修复 **10** 个产品问题（critical **0** / high **1** / medium **4** / low **5**）。据此确立：

- R045（`dev/nana-core-v1-r045-first-real-shadow-release-candidate`）以 R043 `2d83e6a` 为起点，`--no-ff` **完整 merge** R044，**不做零散 cherry-pick**，以免拆散相互依赖的安全修复。
- R044 唯一 **High**（group/world-writable 的 package code/manifest/directory 被**旧 gate 接受**）**必须**确认已进入 R045；**不得**带旧实现上现场。
- R044 **未修改** PROJECT_BRAIN 09/10/11 ⇒ 合流**不得**用 R044 覆盖 R043 的宿主现场事实；D-049 编号纠正继续有效。
- R044 改过 bridge 实现 / session journal / integrity gate / package logic / onboarding safety ⇒ **旧 R042/R043 包全部 superseded**；**禁止**把旧 manifest/SHA 与新代码混用，必须从 R045 final source 重新构建 EMPTY 包。
- `OFFLINE_RECOVERY_QUALIFIED` 是 **fixture/offline** 结论，**不是**真实 host PASS；真实 load/dispatcher/bridge/one-shot 仍未运行。

[口径确认] 生产授权 pins 与 runtime-proof pins 保持 **EMPTY**；`seal_mode = EMPTY`；`FIRST_REAL_ASTRBOT_SHADOW = BLOCKED`，`E12 = NOT_RUN`。

## D-051 — Continuous Self uses explicit development schema on the same Store
[姐姐C–D授权/开发验证] VNext-1 后续能力在独立开发分支进入正式 Core；不把 readiness 的 core_meta prototype 当长期实现。同一个 Store/identity/transaction/lock，默认 v1 不变，开发显式 opt-in 版本迁移。存在业务正文的 v1 拒绝原地升级：旧 immutable event/projection 复制正文，新增字段无法保证删除；需另行审阅离线转换。回滚恢复旧隔离快照，不对新事件做有损 downgrade。此决定不改变 R045 包或生产 schema。

## D-052 — Privacy erasure outranks immutable content retention
[姐姐C4授权/VNext-1/开发验证] 新连续主体事件只保留typed metadata/opaque refs；正文只进可删除artifact。明确forget清除source对象的保守依赖闭包，不等同withdraw。删除意图在现行外部privacy journal先fsync，Store恢复/查询/受控备份与replay须应用tombstone；丢失现行锚则拒绝读旧continuity DB。可保留不含正文的删除审计，不能用append-only理由保留用户要求删除的payload。权限边界仍是可信应用controller持有operator，模型无Store引用。
[限制] 任意未经登记副本/root全盘回滚、已外发provider副本、SSD取证不在应用删除保证内；忙碌备份报告PENDING_BACKUP_PURGE并可恢复，绝不伪报完全擦除。不授权真实私人数据导入。

## D-CS-001 — Cognitive proposals and derived self never acquire write or execution authority
[姐姐C–D授权/VNext-1/开发验证] 永久SelfFrame/Context由Identity、当前assessment、关系、adopted承诺、项目和有限经验重建，不反写为原始事实。Context model port v2只给serialized data，模型输出只有proposal和来源引用；拒绝Grant/Receipt/success/换身份。承诺adoption与履约核验分开；lesson复用既有窄StrategyRule/PlanCompiler，经测试与operator激活，不改charter/权限。
[隐私/边界] 当前task本身默认PERSONAL，和检索记忆一起受目的地策略检查。候选检索有界，矛盾整组且隐私预过滤；不可用即BLOCKED。C/D开发库固定Shadow屏障，真实memory ingress硬关闭；E12与真实宿主事实不能由fixture升级。本条使用独立D-CS命名空间，避免与奈奈并行B5编号争用。

## D-CV2-001 — Unique subject loop and evidence-driven growth (2026-10-14)

Adopt `docs/ADR/ADR-CV2-001-persistent-subject.md` for offline C-V2 implementation.
Existing Core continuity remains authoritative; derived living/personality state
is rebuilt, not a second truth store. New preferences require independent
source roots and accept counter-evidence. Legacy initiative evaluation is not
another decision engine inside this loop. C intentions never grant execution.
Explicit development v7 migration is authorized only for dev Stores; deployed
v1/default Store, real ingress, production pins and R045 remain unchanged.

## D-DV1-001 — Runtime schedules C, local lease fences decisions (2026-10-15)

Adopt ADR-DV1-001 for standalone offline Runtime. Same Store/file lock plus
persisted epoch/lease and pre/post-transaction fence; no distributed consensus or
raw-clone protection claim. C remains sole judgment/intention authority. Wake is
not LLM/execution. Operational health/heartbeat is not Self Memory. Development
v8 only; real ingress/action/pins unchanged. Source-backed social/interaction
extensions use existing C and learning services, never a new SocialLoop.

## D-DV1-002 — Generative subject, not scenario-specific autonomy (2026-10-15)

User D-V1 clarification: folder curiosity is one fixture case, never personality,
default motive or runtime objective. C owns extensible MotivationSource and
judgment; D supplies time/event/cognition opportunities. Qualification covers
S1–S10 and legitimate non-action/rest/silence using one SubjectLoop. No social,
project, creative or curiosity agent loops. Persistent C+D is a foundation, not
all of Nana. No message frequency/engagement optimization or real permission gain.

## D-AFFECT-001 — opt-in generic subject semantics (2026-10-15)
[本轮正式授权/ADR2] v9 extends existing records/CHECKs, no new table/Store/loop.
Preserve v7/v8 defaults and old policy; normative/disclosure fields apply only
under v9. Source-backed restraint is distinct from lack of motive; disclosure
never creates authority. Model receives serialized proposals only.

## D-AFFECT-002 — trusted controller and sealed synthetic effect realm
[授权/ADR2/开发验证] Reuse exact application-held OperatorAuthority for installing/
revoking negative governance. Definitions never enter ordinary Memory/context;
subject reads only source-backed filtered outcome. Gate occurs after committed
judgment, cannot mint Grant. Synthetic action qualification uses exact final
OfflineEffectPort/v9, fixed reading-only capability family, synthetic resource
URIs and private fixture JSON; no callbacks/network/device interfaces/subclasses.
Production/default Shadow remains blocked. Kernel Grant/Budget/Verify/state graph
unchanged; governed admission and transaction fence cannot be bypassed by another
Kernel on same fixture Store. Root/hostile Python memory mutation is out of scope.

## D-AFFECT-003 — source facets and privacy remain separate
RelationshipView retained; bounded event projector derives domain-specific
trust/counterevidence/targeted repairs, familiarity and other facets. No total
score. Relation metadata is source interpretation, not a model's facet write.
Three nullable normalized v9 columns retain opaque revision links, preventing
erased later boundary versions from resurrecting old versions. No table added.
Social expectation acts only after Data Privacy; all ContextAssembler hard
checks remain. C oldv7/D oldv8 do not acquire new semantics.

## D-AFFECT-004 — request adoption and daily calendar semantics
Positive request decisions belong to the existing subject, never Manager.
Application-held authority materializes/adopts through CommitmentService; model
proposal cannot adopt. Daily calendar uses IANA zoneinfo, earliest/latest fold
and next-valid-minute gap, coalesces to the latest eligible local-day occurrence,
otherwise records missed metadata and advances. A calendar wake is only a source-
backed opportunity; SubjectLoop and future gates still decide. No new scheduler,
table, dependency or natural language time parser.

## D-AFFECT-005 — non-execution fact is not success or moral correctness
Disposition verifier reads committed subject/gate facts; only meaningful
ExperienceCandidate gate can admit them. NON_EXECUTION is a separate outcome,
not fake reading/interaction success. Independent later consequences can support
a narrow reviewed lesson, never automatic Manager obedience/hostility or identity
change. Same candidate is idempotent. Operational lookups use opaque indexed
record target IDs; no second authority or business table.


## D-AFFECT-006 — normative frame versus realization revision
On explicitv9, governance definition revisions have their own snapshot/fence;
they do not invalidate a frozen normative context merely by being installed.
Actual constraint outcomes remain observable facts for later Subject cycles.
Source resource classification cannot be downgraded by an input target. A hard
resource veto belongs to realization, not erasure of Subject desire. Oldv7/v8
retain conservative behavior. Every schema9 action mutation requires the same
post-Judgment governance transaction fence. Local fixture exception accepts only
the exact sealed offline port; no general external adapter is enabled.
Personal outcome body erasure wins over audit prose; opaque events and independent
constraint roots remain. A governance view exposes only id/revision/source event,
reason, scope and validity, never secret/resource operands. No new tables.
