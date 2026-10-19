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


## D-AFFECT-007 — offline acceptance does not adopt production authority
ADR2 R1–R6 are implemented on explicit development9 with no new business table.
Final911/0/1 and independent synthetic worlds qualify only the offline mechanism.
Local controller construction, fixture execution and verification do not create
real governance principal/trust pins, Model authority or production grants.
Historical block/cancel/UNKNOWN provenance is preserved; a later disclosure must
resolve the actual sourced veto instead of calling a cancelled Action PLANNED.
Any future real realization requires independently reviewed application wiring and
existing Grant/Budget/Capability/Fence checks; no implicit E/G advancement.


## D-C6B-001 — generic personal-subject continuity reuses authoritative sources

[文档/源码] C6/C7 reuses Relational source at 67326d1 on exact e26288e base.
Primary-user role is explicit, versioned, app-controller owned; not inferred from
model/conversation volume. Relational significance influences self-authored choice,
not Grant/Manager/privacy or exclusive social satiation. Personality/narrative
are sourced projections. Fresh identity bootstrap is neutral or explicit instance
data; an existing canonical identity cannot be rebootstrapped. Open Surface/device/
media descriptors do not open hard authority/lifecycle/privacy domains. L0/L1/L2
are access projections of the same Store, not three memory databases.

## D-C6B-002 — offline transfer retires source before destination activation

[文档/源码] This task authorizes development-only SubjectPackage migration using
existing managed backup/replay/quarantine, not production migration or a second
subject runtime. Source is retired before package publication. Exact destination
controller/root + clean import + explicit activation are required; old grants are
revoked, budgets closed and fresh epoch exceeds source high-water. Deletion intent
IDs move; host backup paths/lease/PID/health/provider objects do not. Unknown host
metadata blocks export rather than rewriting immutable history. Integrity hashes
are not malicious-packager signatures. Privileged raw copies, whole-disk rollback
or construction of a second independent destination controller are outside local
single-writer guarantees. Detached older archives need current deletion-journal
review; no cross-machine global erasure claim. Fork is unsupported contract only.

## D-C6B-003 — cognition resources and frontends are replaceable edges

[文档/源码] Providers/media ports reuse existing context/session contracts and
remain deterministic fixtures in this milestone. Embeddings are disposable caches,
not memory truth; descriptor/source change requires rebuild. Frontend sessions
receive typed projections and allowed service commands, never DB/authority handles.
Capability approval/revocation hook returns proposal only. No new dependencies or
business tables; explicit10, C default7/D default8. No D2 work or automatic push.


## D-D2D7-001 — owner-thread cadence and durable ingress acknowledgment

[源码/离线实测] 双节奏是同一 Runtime 的有界机会调度，不是两个主体。Adapter 线程
post 只拿 volatile receipt；现有 EventQueue commit 后才 ACK。唯一 owner 执行 SQLite
写入和 C decision；Condition generation 避免丢唤醒，安全点暂停后台 cognition/维护。
不得在 owner 上等待尚未 drain 的自身 receipt。已派发 effect 不因抢占被改写为 NONE。

## D-D2D7-002 — finite offline adoption does not create authority

[源码/离线实测] 受信应用可给出有限 OfflineGoalPolicy/OfflineProgram，由 C sourced
candidate 形成 adopted plan；每一步重新进入唯一 C SubjectLoop，现有 Manager/Kernel/
Grant/Budget/Verify 决定现实可行。维持 one_live_goal。UNKNOWN 保留同一 intention/
action，最多三次 verification 后停放；禁止新 effect ID 逃逸。revoke 不重跑旧愿望。
有限自愿迁就通过现有 CommitmentService，不覆盖原始 desire 或变成 Manager 正向命令。

## D-D2D7-003 — maintenance and journal are not truth authorities

[源码/离线实测] 同一 jobs 表持久化分片游标；SUMMARY/INFERRED 候选由 C admission，
不能写 Evidence/Identity，不能把摘要作为独立成长支持。已纠正/删除/隐藏 support 失效。
FactValidity 只接受有来源的显式声明；已知时间与事实有效时间分开，后续纠正不倒写旧认知。
Living Journal 是过滤投影。学习仍经既有 trial/verification/review，不自证、不自动提权。

## D-D2D7-004 — resource pressure is operational and estimates remain estimates

[源码/离线实测] 使用同一 cognition call reservation 原子预留次数/bytes/估算成本，后台
subquota 保留前台余量，总额度仍约束全部。UNKNOWN/in-flight 保守计费且不盲重试。
真实测量 bytes/latency 与估算 provider cost 分开；资源压力不是情绪或人格数值。

## D-D2D7-005 — explicit11 erasable payload lineage closes action privacy

[源码/离线实测] 无新业务表/依赖。仅显式 schema11 扩展现有 CHECK/columns/indexes；
默认 C7/D8 不变。V11 action args/result/receipt/verification 正文通过既有可删除
ACTION_PAYLOAD record/dependencies；不可变 action/attempt 行保留 opaque ref。
升级既有 governed action 只复用 exact action-link provenance。删除后核验 fail closed，
不能从 audit snapshot 复活正文；UNKNOWN 的真实效果不被改写。生产 migration未授权。

## D-D2D7-006 — portable history, rebuildable views and local execution are distinct

[源码/离线实测] 主体 goal/experience/memory 历史可随受控 B8 协议迁移；Journal/生活投影
可重建；worker/owner/lease/PID/socket/port/provider/本地 controller 不可当主体身份迁移。
恢复的 goal 不能自行重建 OfflineEffectPort/Grant/agency authority。沿用 trusted exact
single destination 和旧离线 archive/raw clone 边界，不声称跨机器全局共识或抹除保证。

## D-E1E6-001 — bounded multiple goals supersede the development11 single-goal cap

[附件授权/源码/实测] Supersedes only D-D2D7-002's one_live_goal *development capability
limit*. Explicit12 removes the index, keeps one writer/SubjectLoop/cycle intention,
with default8/max16 live goals, source-deduplicated adoption, typed finite operators,
soft deadlines, dependency/parent and bounded aging. A planner offers IDs, not facts/
Grant. Conditions/dataflow/source revision/schema validate before adoption; every step
returns to C. Default7/8/11 unchanged; no production migration or route reprioritization.

## D-E1E6-002 — desire, delivery admission and execution are three different decisions

[源码/实测] V12 social intention may remain endorsed with unavailable recipient.
Admission checks exact recipient/direct source, privacy, quiet window, expiry and
intention/payload binding; no message or Grant follows just from ELIGIBLE. Existing
negative-only Manager and Kernel Grant/Budget/Verify remain mandatory. Data privacy
classification propagates through observed inputs/action payloads/derived results;
PUBLIC purpose cannot downgrade PERSONAL data. Non-current input support blocks
payload resolution without changing historical wanted/effect facts or retrying UNKNOWN.

## D-E1E6-003 — learning advances only on independently executed comparable results

[源码/实测] Existing jobs/ExperienceService/lessons/RecordService implement staged
learning with disjoint practice/held-out/transfer and new-context transfer. Successful
summary/model assertion is not a trial. C selects the problem/reflection; application
policy bounds evaluation/review; only checked improvement may change method selection.
Monitoring may suspend the lesson, fencing existing compiled plans. Timeouts/errors
park UNKNOWN without cursor advancement; no blind retry. Reflection cannot mint
Evidence, Identity, Manager, Capability or Grant; repeated problem does not self-reinforce.

## D-E1E6-004 — generated code is a reviewed isolated capability realm, not an installer

[源码/实测] Code generation/AST compilation, actual isolated tests, source-hash review,
local activation, Kernel use and retirement are separate. bwrap isolation is required,
not Python private names. Only bounded pure JSON transform code; no host directories,
network, Store/controller or arbitrary install operation. Local tested/enabled handles
are ephemeral; historical ACTIVE record/package is not execution authority after
restart/import. Old Grants are not migrated. Exported candidate copies are explicit
operator artifacts, subject to detached-copy erasure limits; managed Store lineage
still propagates deletion. No real self-installation or production daemon authority.

## D-E1E6-005 — source-bound dataflow and projections stay in the one authoritative Store

[源码/实测] Current plan output bindings cannot resolve older plan revision results.
Old failures and Manager blocks remain historical; source-backed C reconsideration
creates a revised plan, not silent history rewrite. Existing B9 MediaSession proposes
source-linked interest INFERENCE and existing B10 exposes typed bounded goal/learning/
skill/delivery views. L0/L1/L2 are views, not duplicate selves. Existing39 tables suffice;
no new workflow service/framework/provider SDK. Migratable records/history, rebuildable
projections and machine-local execution are distinct. Main/R045/production untouched;
real memory ingress remains closed, E12 NOT_RUN, no automatic push.

## D-WORLD-001 — GLOBAL_STAGE E is not the previous task's local E1–E6 numbering
[用户纠偏/源码] GLOBAL_STAGE=E World Model/Real Cognition。此前E1–E6提前具备F/G/I及
迁移端口基础，不再新造goal/九阶段学习/code-skill lifecycle。当前新增能力优先为cognition
transport、持久world beliefs、真实媒体decode及其进入同一C/D链。仅因新输入需要增加
concern选择、episode反例和skill-need接线。A/B历史路线不被本轮重命名；不机械宣布NEXT=F。

## D-WORLD-002 — indexed headers, erasable sources, no second fact authority
[源码] 显式development13增加cognitive_requests/world_beliefs/open_concerns/
strategy_assessments四类可索引header，仍为原Store；内容与来源闭包复用Records/Memory/
PrivacyJournal，派生projection不是authority。默认C7/D8不变，生产migration未授权。
world belief显式区分source epistemics、event/valid/known time、revision、conflict/UNKNOWN；
模型引用不能自证事实，用户claim不能当raw observation。新媒体技术观察由实际解码器
核验后进入world，不把采样/statistics说成完整语义理解。

## D-WORLD-003 — explicit public media/transport construction and unknown billing
[源码/环境实测] 环境没有现成provider配置；不找secret，LIVE_MODEL_EXECUTION=NOT_RUN。
真实HTTPS transport实现完成，本地HTTP harness仍SYNTHETIC。模型只给proposal，先写
CALLING；超时/中断UNKNOWN不自动重发；epoch/source/subject/goal/world revision共同防陈旧。
现有ContextAssembler mandatory sources仍过hard privacy/budget；provider/cognition预算
并入原Runtime resource projection与前台保留份额，未知usage/cost保留未知，不伪造零账单。
允许development13 PUBLIC非私人录制媒体的typed provenance，RealMemoryIngress仍disabled。
FFmpeg仅只读系统运行库+单次输入sandbox，无宿主Store/private目录/网络；不新增真实执行权。

## D-WORLD-004 — bounded provenance/context and cost uncertainty
[2026-10-17 / GLOBAL E / implementation decision]
Full Record dependencies preserve causal deletion, but do not require every transitive
support memory to be copied as mandatory model input. The original ContextAssembler
pins at most two concise relevant sources for planner/code roles, retains complete
contradiction bundles and hard scope/privacy/token limits; role input's source record
remains a dependency. Model-visible citations are still limited to actual selected
context. Committed C judgment followed by failed context/provider realization is parked,
not silently retried on every Runtime step. No assertion of stronger model cognition.
Successful transport without billing remains cost UNKNOWN; known-charge sum plus the
explicit unknown counter is not total real billing. No live pricing qualification yet.

## D-WORLD-005 — provider JSON contract and atomic counterexample fencing
[2026-10-17 / GLOBAL E closeout / source and failing-before-fix tests]
Generic proposal DTOs contain open operator arguments and optional properties; their
ordinary Pydantic schema is not provider-native strict JSON Schema. The existing
HTTPS transport now requests JSON-object wire mode and retains the full expected
schema in the frozen request, with exact local DTO/citation/provenance validation.
This is protocol compatibility, not relaxed acceptance or a real-model qualification.
Reply origin must match trusted transport construction; a loopback reply cannot label
itself REAL_PROVIDER. An independently executed counterexample and ACTIVE→SUSPENDED
strategy transition now commit atomically in the original Store. Restart/replay cannot
leave the known-disproved strategy active between two transactions. No new table,
loop, authority, dependency or live provider. Actual source audio codec/rate/channels
are retained separately from normalized output PCM metadata.

## D-WORLD-006 — world epistemics and live-attention accounting follow source lifecycle
[2026-10-17 / GLOBAL E closeout / failing-before-fix regression]
A genuine Evidence backlink alone cannot certify the text of a derived Memory.
RAW_OBSERVATION / VERIFIED_RESULT / USER_CLAIM world admission additionally requires
DIRECT Memory with observation/statement epistemic type. Derived summaries retain
their interpretation status; the base Memory contract and historical evidence are
not rewritten. Erased concern records are historical metadata, not current hot
attention, so they no longer consume that capacity. Their old topic is not revived.
This is local source/lifecycle closure, no new subsystem/schema/authority and no
change to C-owned judgment or D-owned scheduling. Deliberately finite descriptive
realms and fail-closed revision overflow remain explicit limitations, not hidden
claims of unlimited production scalability.

## D-H1-001 — semantic observations reuse CognitionSession, not a perception brain
[源码/开发] H1 uses explicit13 existing cognitive_requests, RecordService/Memory
and WorldModel. No new tables or workers. MEDIA is a typed proposal role with an
exact transport-owned modality descriptor, source-only filtered context and
byte/pixel/PCM/temporal correlation. All interpretations/ASR are model-derived;
confidence never certifies truth. Historical accepted proposals can resume belief
materialization after restart with current source/deletion validation, never as
execution permission or permission to repeat provider calls. Source-linked summary
is separate and deletable; audio-track association requires independent same-byte
container ingress. Live provider absent: NOT_RUN, not an implementation blocker.

## D-H1-002 — media content travels only in typed parts, not arbitrary source prose
[失败回归→修复/实测] A retained regression demonstrated source-only media context
still sent Memory.text. Metadata-only citation blocks now preserve privacy,
required-source/conflict completeness and token checks; normalized typed media
parts are the only content channel. Normal C/D assembly defaults unchanged.
primary_source_refs names focus, not new evidence/authority. Model output/ASR/
OCR/captions remain model interpretations; knowingly wrong transcript fixture
proves only that transcripts cannot become user commands. Real ASR NOT_RUN.

## D-H1-003 — offline candidate is not semantic-model quality qualification
[实测] No configured managed provider/credential/identity available. H1 executes
actual generated public codecs and a narrow SYNTHETIC pixel/PCM oracle through
HTTP. Live recognition/ASR/scene-quality and E12 remain NOT_RUN. Existing worker
execute/recover, Runtime/Scheduler/SubjectLoop/Kernel unchanged; final-source301s
focused semantic Runtime.run meets the5-minute unchanged-worker qualification.
Video8 sampled frames/gaps and separately linked same-container audio, max98304
normalized semantic bytes, no silent broad capture/downsampling/auto retries.
Same explicit13/43 tables; no production migration/push or new execution authority.
Next live-provider public labelled qualification is separate; do not auto-enter H2.

## D-H1-LIVE-001 — absent provider stops qualification, not permission discovery
[2026-10-17 / 当前配置观测 / 任务§3/§30] Explicitly configured development semantic
provider absent; live calls/budget0. Stop after bounded source readiness audit.
Unrestricted network and existing synthetic harness are not configured provider
authority. Preserve offline H1; live controls/quality/ASR/E12 remain NOT_RUN.
No credential search, speculative integration, schema/source change or push.
Native provider IDs/raw response fingerprints and independent quality fixtures
remain required before a future explicitly configured live qualification.

## D-H1-LIVE-002 — capabilities route to replaceable ports, not one permanent model
[用户裁决/2026-10-17] Nana Core uses capability-specific ports for text/reasoning,
vision, audio understanding, ASR, TTS, embedding, image generation, video and future
capabilities. Each may configure primary/fallback providers/models. Future settings
include provider/protocol/base URL/secret reference/model/capability mapping,
primary/fallback/timeout/budget/privacy. This task freezes the decision only, not
new Provider Registry/UI. Existing B9 ports remain assets. TianToken and
qwen3.8-flash are qualification-only; permanent default=NO. Exact-model experiments
never silently switch to fallback. Audio/ASR deferred, no omni substitution.

## D-H1-LIVE-003 — real relay output remains revisable, and partial is not READY
[实测/2026-10-17] User configuration supersedes missing-provider configuration at
c3cd0017, not the original stop's historical validity. Official linked endpoint,
exact requested/returned alias and native IDs/digests are recorded. Upstream remains
RELAY_CLAIMED_UNVERIFIED.9 relay requests: MEDIA3 accepted,1 schema failure,
3 unknown; no unknown retry. Accepted sources remain MODEL_DERIVATION and C alone
judges. Local payload mutations/recovery are not live visual injection or SIGKILL.
Partial video/latency/schema quality cannot become H2/production/E12 readiness.
Provider usage.cost without confirmed units is not a known actual bill.
Ordinal model observations are not stable semantic identity: qualification caller
uses per-request predicates; existing conflicting history is retained. Optional
HTTP measurements preserve old absent-field canonical reply hashes, no migration.

## 2026-10-17 — Provider capability routing V1 implementation decisions

[源码/离线实测] GLOBAL_STAGE H, cross-cutting B9/B10 foundation, not another brain.

1. Nana/Subject is not a model. Changing provider never revises identity, relationships, memory authority, goals, Manager or Primary User.
2. Reuse B9 operation vocabulary, existing Registry/ports and original CognitionSession/H1 contracts; one SubjectLoop/Runtime/Store.
3. Provider configuration is host/application-local typed JSON schema1, not authoritative Subject data. No Subject migration: schema13/tables43.
4. Only opaque secret_ref is persisted in host configuration; explicit application resolver, no credential discovery. B8 excludes active config/endpoints/secret refs/handles; frontend omits secret_ref too.
5. Fallback is pre-dispatch only, with explicit reasons. Exact provider+profile mode never substitutes a model.
6. UNKNOWN/timeout/malformed after dispatch never fallback or blind retry. Terminal request replay never resends.
7. Privacy/timeout/cost/context/output limits intersect with existing policy and Runtime reservations; REMOTE SECRET remains denied. Application owns remote execution/host allowlist, not frontend configuration.
8. Settings changes affect future routing only; historical sanitized route snapshots remain. V1 conservatively stales all prepared requests tied to an older document revision, including retained media sessions.
9. B10 configuration commands use application-owned controller and CAS, not Primary User/relationship/Grant/Manager authority. No settings mutation creates Subject events or intentions.
10. Existing H1-LIVE historical status remains PARTIAL_PROVIDER_QUALIFICATION. All current routing qualification is offline SYNTHETIC_LOOPBACK/fixtures, real provider calls0.
11. No second Registry implementation, Store or HTTP stack: runtime Registry gained profile-qualified identity while unique legacy-name lookup remains compatible.
12. Atomic JSON is deliberately small host config, not a portable Subject snapshot. Corruption fails closed; ignored private temp residue is not a recovery authority. No automatic fallback after dispatch, no discovery/SDK/UI scope expansion.

## H2 ingress/runtime decisions — 2026-10-18

[源码/离线实测] Qualified source identified in H2 evidence; source code frozen before fresh-process final full/soak.

1. D owns WHEN; H2 observes/verifies source; H1 proposes uncertain interpretations; original C owns WHAT/WHY. No second Runtime/SubjectLoop/WorldModel/Store.
2. Sensor config is host/application local; source kind/name/device identity is not Subject identity, authority or permission. Host-injected ports and explicit allow policy default-deny. Source config never creates memory/goal/emotion/relationship/cycle.
3. Raw media defaults to memory-only ephemeral. New H2 requests persist only digests/spans/metadata in original CognitionSession; reserve the actual full temporary payload against existing D6 resources. Legacy H1 path/history remains compatible, not rewritten. Missing attachments expire; UNKNOWN never retry/fallback.
4. PublicMediaSource remains; MediaSourceDescriptor is a compatible separate capture descriptor. Exact private PCM/image paths are memory-only; unsupported private VIDEO fails closed. Real media/device provenance requires future explicit qualification, not relabeling synthetic data.
5. FILE_IMPORT securely reads through descriptor-scoped host port then original PerceptionService.ingest. Reusing ingest_file inside a port would improperly give the port Store mutation; the original public helper remains unchanged. No new decoder/semantic brain.
6. Trusted source descriptor privacy_floor cannot be lowered by frontend configuration. Manager veto supports canonical host binding digest across aliases, independent of host permission/privacy/Grant/Primary User. A block preserves original C desire and only reports infrastructure outcome.
7. Capture identity includes source revision/event/time/sequence/digest. Same bytes at another time are another temporal observation. Exact-digest semantic debounce retains observations and is scoped to route revision. Semantic predicates are capture-scoped.
8. Source profile mutation revision takes new config revision, preventing removed/recreated IDs from reusing stale capture/WATCH identity. CAS/atomic source persistence reuses existing host JSON primitives, no Subject migration.
9. Existing Scheduler handles periodic/coalesced opportunities; original Runtime.post handles event metadata without bytes. One pending periodic tick per source under user pressure. Exact volatile sample loss yields SOURCE_SAMPLE_EXPIRED. No H2 loop or curiosity metric.
10. Only a current source-backed C WATCH cycle may adjust cadence inside host min/base bounds and validity; H2 cannot configure itself or decide importance. Screen text/audio transcript is observation/model derivation, not user command or authenticated Primary User.
11. Disable/remove stops future access, preserves past facts. Only explicit Memory forget invalidates source/derived support. Source availability is infrastructure, not emotion or permanent world absence.
12. Living/Frontend projections are derived and privacy-filtered, no raw bytes/paths/resource refs/handles. B8 carries identity/history, never host source config or operational runtime health. New host explicitly binds devices.
13. First full failure was missing ephemeral legacy SQLite launcher. Restoring /tmp launcher to actual system Python3.13.5/SQLite3.46.1 allowed unchanged isolation test; no version spoof/test removal/R045 or production change. Final full1171/0/1.
14. H2 is OFFLINE/SYNTHETIC foundation. H1-LIVE stays historical PARTIAL; E12, live hardware/provider/ASR, Hands and production perception remain NOT_RUN. No new dependency/table/schema.


## 2026-10-18 — H2-LIVE controlled OS screen boundary

[源码/受控 OS 实测，最终资格待冻结重跑] Reuse PerceptionSourcePort, explicit resolver, original H2 Coordinator/Router/H1/WorldModel/Concern/C. No other loop/Store/table. V1 real screen accepts only PUBLIC pixels from an explicitly host-bound owned X11 dummy window; never ambient DISPLAY, full desktop then crop, physical GPU or input synthesis. Typed receipt records REAL_OS_CONTROLLED, window scope, source revision, session digest, times, geometry, encoded/pixel hashes. Existing SYNTHETIC history retains its origin and serialized shape; real controlled PUBLIC evidence uses existing RECORDED_PUBLIC storage domain with explicit source subtype, not synthetic provenance.

Source session/topology change invalidates the binding; only trusted host rebind creates a new revision. Pending old-revision work is fenced. Capture UNKNOWN is not retried. Exact RGB pixel debounce retains distinct temporal observations, respects route revision and time bounds; no fuzzy similarity. C WATCH can cite raw or semantic/world memory, following bounded existing dependency edges (128 nodes), never model-written source IDs alone. Host-local backend/active binding never enters B8; sanitized historical receipt may travel as evidence. No raw screenshot persistence or source authority from visible text. New API/OS calls do not grant action/Manager/Primary User authority.


## 2026-10-18 — H2-LIVE final qualification boundary
[实测] Source86b7d18 frozen before fresh-process tests/24h virtual/300s real wall.
REAL_OS_SCREEN_QUALIFIED means only L1 own OS window. H1 synthetic narrow pixel
oracle cannot qualify general OCR or real-provider semantic quality. Default
regression keeps capture off; explicit live18 PASS and default full1178 PASS/
12 skips (11 opt-in live +1 E12) are separate evidence. No widening of capture,
Privacy, Manager, Grant, Primary User or C authority. Source originREAL_OS_CONTROLLED
is retained separately from model derivation and old SYNTHETIC history. Future
user/physical desktops require separate host consent/backend qualification.
No new migration/dependency. Successful dev handoff grants no production/device/
Hands authority and does not upgrade historical H1-LIVE PARTIAL.


## VISION_FIRST_SHARED_GROWTH_V2 — implementation started
[远端/源码核验] Base9faaad5006159c4f69f5c4056f0c6b062cc7770b; current independent
dev/nana-core-vision-first-shared-growth-v2-codex. C6/C7 and E1–E6 ancestry confirmed.
Dual durable priorities: Self-Evolution + Shared Life; current B+C causal increment
with small context-fit A. Existing C/D/F/G/I/J reused. Scoped dialogue assessment,
heldout separation and verified-reuse-to-life projection are actual gaps; no new
brain/Store/Runtime/schema, no H2 feature continuation. ADR-VF2-001 records bounded
audit/contract. This entry is planning/started, not implemented/qualified. Real
AstrBot/QQ shadow requires later explicit host/privacy authorization; real dialogue,
production Core adoption, general deep self-modification remain NOT_RUN.


## VISION_FIRST_SHARED_GROWTH_V2 — implementation checkpoint
[源码/定向测试] Original C now owns optional sourced ContextFitAssessment; exact
entity/scope/topic refusal/reopen uses existing SUBJECT_EVENT target IDs and
privacy closure. Explicit context never becomes Manager/Grant. Unrelated activity
survives casual chat; focus yields through original reactive D priority. Temporary
conversation uses bounded process-local queue ingress envelope, not capture-all
Memory; metadata strips signal, finish/stop drops it, restart cannot recover body.
Existing G proposals now see LearningProblem(practice only), not evaluation/
transfer examples/answers. Old full LEARN input is sanitized before HTTP; accepted
history stays intact. Original nine stages/Kernel/Experience/EpisodeLearning reused.
Source-bound ongoing learning pauses on topic refusal; reopen alone does not resume;
new C endorsement required. Adopted plan steps/reviews follow original C binding
and recheck current boundary before further work.

Verified novel later reuse can project a current optional growth-life opportunity
through original D collector/C; existing due work has priority, no second loop or
new table. Busy/unknown means WATCH; explicit no-interest closes that topic. Missing/
deleted sources or suspended strategy remove support. Two model fixtures tolerate
method lessons without reading-specific keys; identity/authority unchanged.
Development demo actual local result4 vs4.75 before,10.75 vs10.75 later; independently
checked heldout/transfer, candidate sharing/silence, source-withdrawal arm and true
float counterexample pass. This is controlled local fixture computation/strategy
selection, not real dialogue or general algorithm invention.165 earlier related
tests passed;11 new focused passed. Final frozen-source full regression pending.


## VISION_FIRST_SHARED_GROWTH_V2 — final scoped delivery
[实测] Sourceadb4b5b;11 focused PASS; full1189/0/12 intentional skips,163.16s.
Original controlled local G/F path shows independent capability selection/reuse
improvement, while new derived C/D projection shows separate life-causality
change. Actual Memory deletion ablation, busy/refusal, counterexample suspension,
restart and fixture-model swap verified. No invented algorithm/general Core
self-edit or real dialogue claim. Context fit is source-bound host interpretation;
privacy/authority are independent. Practice-only proposer fixes heldout exposure.
Original due opportunities precede optional growth-sharing checks. No new table,
schema/dependency/Store/loop. First full missing temporary SQLite launcher failure
retained; restore used actual system3.46.1, no source/test/R045 modification.
Report/evidence under docs/nana_vision_first_shared_growth_v2*. Stop after normal
development push/remote verification; no production/private/live integration.


## REAL_LIFE_V1 — exact local project adapter, no second brain
[决策/未实现] Reuse original C/F/G/Kernel, extend sealed execution construction
only for exact host-approved no-exec source manifests and bounded dedicated report
outputs. Local artifact effects do not grant network/arbitrary filesystem/action
access. Input provenance must say DEVELOPMENT_PROJECT, not synthetic observation.
Independent compiler symtable oracle stays outside candidate-visible practice;
method selection is not algorithm invention. S defaults off and has no fetch/send.


## REAL_LIFE_V1 — implemented local evidence domain
[源码/定向实测] Explicit DEVELOPMENT_PROJECT provenance uses recorded.project.*,
PROJECT privacy, schema13 only. RealMemoryIngress remains permanently disabled;
no PERSONAL/SECRET import widening. Exact ProjectMaterialPort is accepted by
original governed/kernel offline fence solely for finite no-exec local artifacts;
synthetic port rejects project URIs. Original Grants/Manager/budgets still apply.
Compiler symtable evaluator is independent from AST candidate. Baseline misses
are real source findings, not arithmetic fixtures. Host installs finite methods;
Nana's actual improvement is source-supported method selection, not Core rewrite.


## REAL_LIFE_V1 — causal controls and shadow boundary
[源码/实测] Separate real-source withdrawal and strategy retirement interventions;
never demonstrate erasure only after an already suspended strategy. Source lookup
reads only current supported Kernel output and exact current file digest. Exported
reports are user-owned project artifacts, not context authority; source withdrawal
fences reuse/lookup even if a previously exported file is retained by its recipient.
Shadow is default-off, host-pushed, bounded32 reviews; no history/send/credentials.
Literal evidence validates a small anonymous language baseline; model-proposed
HUMAN_REVIEW never self-certifies. Live host path remains denied pending consent,
qualification and explicit privacy-domain integration, not silently synthetic.


## REAL_LIFE_V1 — final evidence boundary
[实测] Frozen sourcec39ba5c; fresh actual project processing, original-chain learning,
new-input reuse/navigation and separate causal interventions passed.13 focused;
full1202/0/12,170.99s. No new schema/dependency. Source variation/compile expectations
are actual repo materials, not toy numeric fixtures; finite method selection remains
a narrower claim than algorithm invention. Anonymous semantic drafts are not real
language/relationship quality evidence. Current live host path deliberately denied;
requires explicit limited consent plus host/privacy-domain qualification, not a
silent mapping of private live input into synthetic domain. Dev handoff is not
production/real companion/autonomous installer readiness.


## A7/D8/C9 — independent application, not a new subject loop
[决策/施工] A7 application wraps original single Runtime. Existing D schedules
source opportunities/real project work; C retains meaning/judgment. Local line
interface is independent from AstrBot/QQ. Provider slot reuses host-local Registry/
Router/JSON transport, off by default; no secret discovery or real calls in this
mission. Ephemeral local dialogue body must not become permanent raw Memory.
Number labels are mission targets; GLOBAL_STAGE H and historical priorities stay.
Resource detection: environment cgroup8GiB, CPU quota2; configure <=4-affinity CPUs,
512MiB process address-space ceiling, one foreground owner, no local model/capture.


## A7 — implementation constraints
[源码/定向实测] Local terminal is an input, not social send authority. Raw input/
provider free text remain volatile; only normalized LOCAL_INTERACTION_METADATA
(USER_STATEMENT tokens) may persist under privacy. Model meaning linked to current
correlated request/revision/epoch; model refusal is temporary, explicit literal
user refusal retains original scoped boundary. No model-certified goals/relations/
grants. Original ContextAssembler pinned-only mode carries verified report facts
and existing filtered relation/self facets; unrelated source corpus excluded.
Foreground dialogue uses shared total budget, not background subquota; UNKNOWN
blocks later dispatch and is never rendered/retried automatically. Runtime pause
is machine-local operational metadata, excluded by existing B8 transfer. Explicit
startup Grants installed once at init only; resume/restart never grants.
