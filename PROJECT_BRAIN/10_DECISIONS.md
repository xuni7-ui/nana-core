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

## A7 — SUPERSEDES previous next-integration priority only
[任务边界] Independent local experience and replaceable semantic provider are now
critical path. Earlier mission's QQ shadow next-step remains historical, not an A7
prerequisite. Do not read/modify production or use QQ permission to fake standalone
readiness. A7 offline integration and independent-process soak may pass while real
provider/naturalness/first-life gates remain explicitly NOT_RUN/NOT_READY.


## A7/D8/C9 — qualification levels remain separate
[实测] Frozen source324b80d:16 focused PASS; full1218/0/12,214.25s. Actual30.0835s
process journey with SIGKILL/restart, zero-input real work/finite learning/reuse and
local controls verified. OFFLINE_INTEGRATED and bounded INDEPENDENT_RUNTIME_SOAK
PASS do not imply REAL_PROVIDER_QUALIFIED or FIRST_LIFE_EXPERIENCE_READY. Actual
provider/quality and voluntary human review remain next gated dependency; QQ is
not required. Window controls new opportunity admission, not a Manager-style veto
on adopted work; explicit pause/Grant/Manager still independently fence execution.
No general autonomous curriculum or algorithm-invention claim. Dev subject identity
is not imported production Nana. No new schema/dependency or private import.


## LIVED_GROWTH_V2 — scope and independent document work
[授权/施工] Preserve GLOBAL_STAGE H; mission E5/C9/D8/F6/G6/I3 labels do not
renumber phases. Add sealed Markdown document navigation/audit beside Python API
work in original ProjectWork/Kernel. Independent checking must trigger learning,
not host-injected failure. Skill code only via existing isolated CodeSkillService.
Real provider/human quality remains separately unauthorized/unreviewed; no old keys.


## LIVED_GROWTH_V2 — document grammar and skill adaptation boundary
[源码/定向实测] Reuse exact-manifest ProjectMaterialPort for .md using explicit
task_type; .py remains the default contract. Column-zero ATX/triple-backtick
grammar is intentionally bounded, not CommonMark completeness. Independent regex
oracle computes expectations; G proposer receives practice only and synthesizes
minimal sufficient depth within a host-reviewed finite recipe family. Existing I
CodeSkillService compiles that parameter into pure-data code, tests in mandatory
bwrap realm, then original F/Kernel calls world.skill on a later real material.
No second engine/Store/table. Fresh realm revalidation preserves exact historical
skill identity/tests and never creates Grants. Optional I slices participate in
original D safe points, C alone selects skill need. Offline success is workflow
adaptation, not model training/Core self-modification/general algorithm invention.
Bounded volatile conversational turns pass original ContextAssembler/Session source
and privacy checks; never persist raw turns, model wording, or replay after exit.


## LIVED_GROWTH_V2 — adopted I work is not an unresolved duplicate wish
[实际进程发现/修复] A skill-need cue was recalled after its work was already selected,
leaving a pending goal candidate despite completed tasks. Original I work now carries
source_program_id; original C recognizes current supported I work as representing
that program. Original candidate adoption stays explicit; no runtime suppression of
Subject judgment and no rewriting wishes. This fixes state continuity rather than
hiding an incorrect FOCUSED display. Human/live semantic qualification still NOT_RUN.


## LIVED_GROWTH_V2 — idle review is low-frequency, source attention stays responsive
[真实驻留证据/修复] Original application one-second periodic review generated128
scheduled occurrences in112s journey and~2MiB extra idle history. This is avoidable
operational cost, not autonomy. Default host-local idle_review_seconds=60 (10–3600),
with existing Scheduler CAS rescheduling for older initialized homes; preserve
occurrence identity/history and coalesce missed review time. Source/goal/commitment/
reactive attention still uses original independent wake mechanisms; no personality
policy change, no slower user ingress, no new grant or schema. Before/after actual
journeys must be reported distinctly; final source must be requalified.


## LIVED_GROWTH_V2 — failed novel use is counterevidence, not invisible learning
[定向因果测试/修复] ProjectWork later-use assessment previously considered only
COMPLETED goals. A genuinely new material failing independent verification could
leave the adopted strategy ACTIVE. Include FAILED goals only when the actual
SUCCEEDED compute result is source-backed and no baseline exposure occurred.
Original EpisodeLearning independently recomputes expectation and atomically suspends
the lesson on COUNTEREXAMPLE. No fake failure/learning grade, new authority or retry.
Synthetic unseen depth-three document now fails, pauses depth-two lesson, produces
no erroneous report and no repeated effects. Positive real-source journeys unchanged.

## LIVED_GROWTH_V2 — clarify idle-byte interpretation
[实测澄清] Before/after filesystem-byte snapshots include SQLite WAL and operational
lease writes; do not extrapolate their growth into a daily authoritative-history
rate. Robust actual change: periodic review occurrences109→1 and queue events164→56
for comparable bounded journeys. These are not controlled CPU benchmarks.


## LIVED_GROWTH_V2 — limited real cognition permission, credential gate remains
[用户明确授权/环境核验] TianToken https://api.tiantoken.com/v1; exact qwen3.8-flash;
PUBLIC/PROJECT only (PERSONAL/SECRET denied), <=20 calls/$1 equivalent,3s timeout.
No old key reuse/ambient environment/file/repository credential discovery. Current
managed environment reports no secret/runtime variable bindings; no explicit FD was
provided. Supersedes only earlier M1 BLOCKED_BY_AUTHORIZATION: now authorized but
BLOCKED_NO_SAFE_CREDENTIAL_SOURCE, actual calls0. Continue other development.
A model success cannot imply natural human quality or alter historical H1 PARTIAL.
CLI PERSONAL default must not silently become PROJECT; any future controlled live
qualification uses explicitly approved content/privacy and original ports/budgets.
Unknown currency mapping is not billing truth; no blind retry or expansion after
unknown completion/cost. Secret delivery must use host safe binding, never chat.


## LIVED_GROWTH_V2 — no unsupported model-wording replay across source erasure
[删除闭包审查/实测] A rendered reply can depend on facts later erased; associating
it only with message metadata would not preserve its full causal support. Minimal
V1 contract now retains only bounded USER turns in volatile history, never replays
model wording as conversation evidence. Fresh rendering cites current Core facts.
This avoids assistant self-confirmation and deleted-fact resurrection without a
second transcript authority. Renderer pins at most one current artifact to keep
bounded context usable after source withdrawal; no budget enlargement or hidden
provider retry. New actual loopback after-delete conversation test PASS.


## LIVED_GROWTH_V2 — authorized transient FD live attempt and UNKNOWN stop
[用户本轮显式授权/实测，2026-10-19] Supersedes only prior no-source gate: current
user supplied a one-run credential, admitted through no-echo stdin FD and existing
ExplicitFDResolver, never source/config/env/file/log persistence or historic key
search. Python core dumps disabled; resolver cleared, owning process exited.
No promise to erase an already submitted chat message; audit scope is engineering
files, diff, dev-home DB/config/WAL and generated logs/evidence, excluding old bundle.
One PROJECT-only TianToken/qwen3.8-flash request under3000ms deadline yielded UNKNOWN
without any HTTP response. This is not authentication failure or model semantic
failure; their truth remains unverified. No new call/timeout enlargement/fallback
may be disguised as the same request after UNKNOWN. Public model/group price ratios
are not account billing; estimated reservation1000 does not prove a dollar charge.
Keep remaining19-call allowance unused while completion/cost are unresolved. Later
explicit provider/operator evidence, not deleting DB/resetting the budget/new identity,
is needed before further live dispatch. Existing C ASK/WAIT and runtime continuation
are valid; neither grants a semantic-quality or human-naturalness PASS. No second
Subject/loop/Store, source/Grant/Manager/privacy/primary-role change or production access.


## LIVED_GROWTH_V2 — UNKNOWN reconciliation precedes longer-timeout dispatch
[2026-10-19用户约束/公开Provider接口实测] A confirmed log-list path is not a public
per-inference status API. Official frontend source uses logged-in account user.token;
no source establishes inference-key authentication for this API. Bounded unauthenticated
GET canonical /api/log/self returned401 without data. Do not repurpose a model key as
account session, log in, fetch broad account history, guess status endpoints or infer
no charge from an empty/unauthorized search. Preserve original UNKNOWN regardless.
User explicitly predicates a new10000–15000ms development request on confirmation that
it will not duplicate unknown billing. Prerequisite unmet: do not change active timeout,
clear/reset the request, change home/identity/day, retry the old message, or submit a new
live probe. Current host timeout3000ms; production untouched. The narrow followup uses
zero model calls and no credential. Need one sanitized operator/provider record with
correlation/finality/usage/charge currency; absence is not non-dispatch evidence. HTTP401
for log authentication says nothing about original inference authentication or quality.


## RAE-00 — strategic lock / controlled application Hands
[2026-10-19T17:22:20.804339+00:00，用户新长期任务/基线核验] Self-Evolution + Companionship are permanent axes.
Real outcome→prediction error→should learn/value/cost→baseline/trial/transfer/counterexample→
adoption/rollback; learning does not replace motivation. Primary User significance remains
high and configurable, never authority. User intent is influential input, not a cognitive
ceiling. No second Subject/Store/Runtime/will/planner. C WHAT/WHY; D WHEN; adapters execute;
Verify checks. Provider UNKNOWN parked unchanged, model calls0 new; no credential searches.
Minimum target is an explicitly owned independent local application child, typed finite
operations, PID/start-time/uid/socket-inode/session binding, effect-time recheck, exact
Kernel resources and Grants, separate read-only/file verification. No generic shell,
global desktop scope, account login or arbitrary filesystem. GUI is optional; a real
application process/state is sufficient only when independent real effects are proven.
Existing closed registry/realization may admit exactly this sealed opted-in development
port; no general removal of shadow fence or exemptions for production hosts. New methods
prepare bounded data; only original governed Kernel may commit external effects. Learning
candidate gets practice only; final heldout/transfer are distinct real process tasks.
Development authorization is not production readiness. Current implementation PENDING.


## RAE-01..13 — owned application action and outcome learning foundation
[源码/真实子进程实测，2026-10-19 UTC] 有限DOCUMENT/FORM应用进程在独立私有目录中运行，
两个Unix IPC channel与实际文档/应用状态文件；PID/start/UID/socket inode绑定，每次发送前
TOCTOU复查。新增hands://精确资源和四个纯数据命令准备方法，原C/有限F/Manager/Kernel/
Grant/Budget执行与独立Verify不替换。明确适配器是自有应用IPC，非GUI点击/用户桌面。
Kernel/GovernedRealization仅将exact opted-in OwnedApplicationPort纳入已有sealed开发例外；
不删除cloud shadow fence、不开放任意adapter，生产路径不变。Hands请求附完整action/subject/
goal/plan/effect-slot、target binding、Grant与budget hold、deadline和idempotency元数据；这些
是审计引用，不替代Kernel实时权限判断。独立核验执行事实后，目标质量另行比较，保留
SUCCEEDED effect != successful task，失败进入原Experience/G。实践选择只见practice，G评估
为命令准备的独立纯数据试验；后续独立真实应用任务另证外部迁移，不混称G试验为OS动作。
真实多字段失败揭示first-field-only workflow缺口，原I SelfExtensionWork生成有限batch
pure-data组合并在bwrap中独立测试/当前realm审核；后来两个新目标经原world.skill+publish
实际复用，不创建新权限。反例暂停原method lesson，不自动否定独立测试过的新workflow。
修正原OpenAgency _plan只为真正strategy-selectable compute绑定method lesson；显式skill
计划不应无关依赖一个已被反例暂停的旧method。此为依赖收窄，不绕skill/Memory来源有效性。
首轮2聚焦PASS14.96s（真实进程、学习/迁移/反例/I复用、delete/restart、pause/revoke/owner）；
权限/多切点恢复/30min驻留/full回归尚PENDING。Schema13/43表/new0、依赖0；新模型0。


## RAE hardening — real crash cuts, sharing and no resurrection
[源码/实际进程实测，2026-10-19 UTC] 新增6个实际SIGKILL切点before prepare/before effect/
after external effect before Core commit/during Verify/during G/during isolated I test；
原identity/Grant/action id保留，已发生效果可只核验，不明效果不重发。真实文件/IPC冲突
保持UNKNOWN。共享生活actual source→candidate→AVAILABLE/BUSY/explicit refusal→delete
source gating已通过；高负载C可REST而不强制学习。当前完整focused16 PASS59.16s（最后
no-resurrection加固后的复核随后记录），不是人类自然度。
将Owned端口scope/command/stale-revision preflight放在原Grant检查之后、READY之前，
effect时server仍复查revision/deadline；写入用原私有目录FD的openat/renameat/fsync，
避免路径替换逃逸。不改变旧ports或Grant/Manager/UNKNOWN语义。
长驻留02发现真实developer defect：删除技能支持后，完成的skill-only任务被当成未做过的
base task重新提供，30→33Actions/8→9Goals。已保留失败快照，不称Nana学习或合格soak。
修复以既有source evidence（包括tombstones）标识base/batch任务已提供；source删除/
skill撤退不会创建降级新目标。补删除后继续tick及重启继续tick的反回生断言；同一来源
缺失时不再生成gap。新30min实际进程run03正在进行，未提前PASS。无新模型/生产权限。


## RAE hardening checkpoint — latest targeted evidence
[2026-10-19 UTC] Final focused after FD pin/preflight and source-withdrawal fix:
16 PASS62.48s (six real SIGKILL cuts plus real file/IPC disagreement; no duplicated
external effects). Additional real heldout application journey35.3194s:9 distinct
tasks/10 goals/36 Kernel actions/12 actual application effects; same identity/one
Grant,goal quality counts finalized from actual verification events, not estimated. G pure-preparation
heldout remains separate from actual owned document/form heldout + transfer.
Source withdrawal did not create another action in this corrected short run;
source_fingerprints start/end equal.30min run03 underway, full regression underway.


## RAE final executable guard / typed problem reframing
[2026-10-19 UTC] First complete regression1246 PASS/0fail/12skip306.12s; then closed
an owned-mode CLI mismatch: project /work command now explicitly rejects replay,
rather than calling absent ProjectWork API. Source-backed typed user suggestion
HANDS_APPEND is independently answered ALTERNATIVE/HANDS_REPLACE after real failure
and evaluated method, with unchanged Grant. The test keeps the required separate
user occurrence text; it does not weaken SubjectInput provenance or pretend NLP.
Latest boundary+CLI9 PASS10.08s. Final full regression follows this executable guard.
No provider/new permissions. Hands execution files remain frozen533a1dd; current
30min run03 watches those same bytes (CLI /work rejection is outside commands used
in that residency). Final source SHA is recorded by git history, not guessed here.


## RAE final validation checkpoint [2026-10-19T18:01:43.171802+00:00]
[实测/开发进程] Executable freeze c2732b0fd67da74634ac41eba782fcc9011c3a9a。
最终全仓库1246 PASS/0fail/12skip296.88s（11历史opt-in live-screen + E12；均未伪称通过）；
新focused16 PASS62.48s，最后CLI/typed reframing9 PASS10.08s，related23 PASS8.72s。
实际CLI init/run及/life /actions /outcomes /pause /quit通过；全程无Provider。
实际扩展旅程9tasks/10goals/36KernelActions/12真实应用effects：8质量成功、4真实失败保留；
document/form baseline均0→1，独立real heldout/transfer均成功；multi-field真实失败触发
原I有限workflow与两次实际复用；两条旧method反例后SUSPENDED。G评估仍明确为纯准备
试验，实际OS留出/迁移另证。源删除撤掉skill/share支持，不恢复正文/退化重放。
原C可REST，typed narrow user plan可有来源地ALTERNATIVE；不是live自然语言真人评审。
6实际SIGKILL切点+1实际file/IPC冲突保持identity/Grant/action/UNKNOWN，无重复效果。
保留long02源删除重放developer defect失败快照；修复不计作Nana学习。run03仍在计时，
>=30min资格尚PENDING，不能拿35s旅程替代。Schema实测13/43表/新增0，依赖0，FK干净。
选定10个执行文件实际hash与最终freeze相同；未冒称覆盖整个import tree。
证据目录docs/nana_real_action_experience_evolution_v1_evidence/，report/quickstart新建。
Provider历史1 UNKNOWN PARKED、新增0、不访问凭据；自然聊天NOT_RUN、FIRST_LIFE NOT_READY。
main/R045/production/私人数据/真实社交/用户桌面变化0，旧bundle未读未动。


## RAE exact source identity hardening / actual residency complete
[实测2026-10-19 UTC] corrected run03实际驻留1805.221705515s，10真实effects/30Actions，
源撤回后无新增动作，pending/queue0，NanaCPU17.341583222s/峰RSS42488KiB，targetCPU0.70s，
77真实采样点，选定源码hash全程未变。不是生产或GUI资格。
随后实际边界断言发现doc/doc-next机会source前缀误关联；按inspect resource精确task绑定，
拒绝doc/doc-batch派生objective ID碰撞。保留初始失败；非Nana学习。此修复在驻留结束
封存后应用，最终18 targeted PASS62.48s（仍含六SIGKILL）。最终新full正在运行。
Selected residency source c2732b0；新exact-binding以本提交为准，不混称同一源码驻留。
Provider新增0/历史UNKNOWN PARKED；main/R045/production/旧bundle未改，权限未扩大。


## RAE final qualification decision [2026-10-19T18:21:07.717528+00:00]
[实测/设计裁决] RAE00–30在有限owned application范围完成，不等于通用桌面或完整共同生活。
选择真实独立应用IPC/文档/表单双结构核验，而非安装GUI输入栈：任务明确允许真实进程
surface，scope/PID/start/inode/peer绑定更有限，真实效果/独立核验/六切点恢复已有证据。
最终exact task/resource绑定和派生ID碰撞拒绝保护来源一致性，不扩展执行权。
Finite G method search与bounded I workflow模板如实命名；非任意研究/算法发明/Core自改。
源删除不得退化重放；source tombstones保留非正文阻止回生；独立治理来源不随个人记忆撤销。
实际驻留与最终hardening分开版本记录；最终1248/0/12skip、18focused及60s最终源码实跑。
下一步只按真实最大缺口选择更广owned应用/自然交流，不自动接用户桌面/设备或重试Provider。


## CURRENT — CLOUD DAILY LIFE & SHARED PRESENCE V1 / DEVELOPMENT
[源码/远端核验2026-10-19T21:28:23.247688+00:00] Base d7886ba9b49cf2fbb52cebcbce9525394c938d3c，
branch dev/nana-core-cloud-daily-life-shared-presence-v1-codex；GLOBAL_STAGE H。
继承RAE真实owned app/Verify/G/I资格，不重新施工已有PASS；One Subject/Store/Runtime/Loop，
C WHAT/WHY、D WHEN，Self-Evolution + Shared Life两主轴。
本轮补应用运行/操作面、B8迁移恢复、统一surface近期上下文、共享经历和日常任务组合。
已有ProviderRegistry/Router、SurfaceEnvelope/ContinuityViews、SubjectPackage与Kernel必须复用。
Provider历史1 UNKNOWN PARKED；环境无安全凭据，新调用0；真实Provider/真人评审/生产canary
为独立门，不能以离线测试升级Beta/FirstLife。main/R045/production/真实社交/私密数据不授权。
现阶段已核验基线，新增能力PENDING。以下当前块作为历史保留。
原因：把CDL登记为原路线延续，不建立第二系统。验证：本地/远端HEAD匹配，仅旧bundle未跟踪。

## CDL checkpoint 1 — implemented / targeted-tested, not Beta
[实测/源码] 独立headless Runtime私有IPC控制、health/磁盘guard/轮转日志、host CAS；
B8停机迁移/显式pending UNKNOWN保留/旧Grant撤销；三shadow入口Event-First L0/L1/L2，
显式PROJECT摘要与删除闭包；真实owned CONTENT/FILES任务；来源绑定shared candidate回原C与DeliveryAdmission，发送0。
集成短驻留90秒：12 goals/42 Kernel actions/14 owned effects；不是两小时资格。
首次组合暴露REFLECTION已完成但未结算挤占pending，已以原C反思结算+幂等D follow-up修复，
GOAL/REFLECTION提交后SIGKILL两切点通过；启动旧socket交错以当前lease PID的peer就绪验证修复。
验证：cloud+runtime+hands初次46pass/1启动race失败；修复后实际进程/两切点3pass8.41s；
先前相关45pass、Hands/B8 22pass。完整回归/两小时资格仍PENDING。
新增业务表/依赖0；历史Provider UNKNOWN不重试，新真实Provider调用0，真人评审/生产NOT_RUN。

## CDL checkpoint 2 — tested / actual residency running, not Beta
[实测] 冻结Core fc0fa46506a360a81a10e14f9d967a734d338141，7205秒真实驻留已启动；
未完成前不得写两小时PASS。首轮完整回归1266 passed /12 skipped /0 failed；
新增focused20 passed16.40s，另13项实际进程/替换模型/平台映射/对话兼容通过。
模型替换仅SYNTHETIC_LOOPBACK，来源/身份/旧路由provenance保持；错误返回旧model被correlation拒绝。
Bili仅复用纯normalize，QQ仅显式合成fixture→统一surface，未启动旧agent/pump，真实发送0。
停机前/实际SIGKILL后的backup均隔离；fresh-host激活仍走原B8源退休与旧Grant撤销，
无法证明旧host fenced的灾难备份不自动提升writer。新schema/表/依赖0。
已提供运行quickstart、未安装的development service样例、单一推荐cutover计划与真人空评审表。
Provider新调用0；历史UNKNOWN parked；真人review/24h staging/production/canary/72h NOT_RUN。

## CURRENT — CDL V1 / TECHNICAL DEV PROCESS QUALIFIED / BETA NOT_READY
[实测 2026-10-20T00:01:27.142666+00:00] Branch dev/nana-core-cloud-daily-life-shared-presence-v1-codex；
base d7886ba9b49cf2fbb52cebcbce9525394c938d3c；GLOBAL_STAGE H。可执行冻结
fc0fa46506a360a81a10e14f9d967a734d338141，203个Core/驻留driver Python文件起止SHA256一致。
真实驻留7205.177143084002秒（2h00m05s，非虚拟）；11个finite任务/12个goals（10完成、2反例失败保留）、
42 Kernel actions/14 owned physical effect receipts；4类DOCUMENT/FORM/CONTENT/FILES。
原G两条方法later-use SUCCESS后各被COUNTEREXAMPLE停用；原I 4独立测试、2次真实world.skill复用，
随后source withdrawal使技能支持失效；Codex代码修复不算主体学习。
实际SIGKILL恢复epoch2→3，同identity、Grant数1且无重放；fresh-host原B8源退休→同identity恢复，旧Grant全撤。
在线及crash-consistent backup隔离、delete传播通过；UNKNOWN显式迁移保留且无预算返还/重新授权。
RSS峰值49988KiB，steady约45248KiB；postrestart观测idle CPU约0.525%单核；
线程峰值1，FD峰值11/steady8；queue峰值2/final0，pending峰值5/final4。
self.db* family从688331→13382261 bytes（含WAL/privacy sidecars）；约651s后growth1967568 bytes，历史可线性增长。
新focused20 passed；最终full1268 passed /12 skipped /0 failed（298.46s）；11 live-screen+E12门保留NOT_RUN。
One Subject/Store/Loop/Runtime；C WHAT/WHY、D WHEN；schema13/43表，新表0/新依赖0。
QQ/Bili/CLI统一Event-First L0/L1/L2仅DEV SHADOW；Bili复用纯normalize，不运行旧Agent/pump。
真实Provider新调用0，历史1 UNKNOWN PARKED retry0/fallback0；无安全新凭据/付费资格，真人自然度NOT_RUN。
2h dev rehearsal不冒充24h staging/72h；生产inventory/cutover/canary、真实社交/private history NOT_RUN。
FIRST_LIFE_EXPERIENCE_READY=NOT_READY；CLOUD_DAILY_LIFE_BETA_CANDIDATE=NOT_READY；BETA_READY=NO。
main/R045/production/legacy live系统不变；旧bundle保持untracked/untouched/not-input。
报告/quickstart/cutover计划与小型文本证据见docs/nana_cloud_daily_life_shared_presence_v1_*。
下一最小门：显式安全FD/Resolver的新Provider有限付费资格，其后用户本人自然交流/shared-life评审；不搜索旧key。
下方CURRENT块均为保留的历史检查点，不覆盖本块。

## CURRENT — CLOUD FIRST-LIFE LAUNCH V1 / DEVELOPMENT
[源码/远端实测2026-10-20] Base b06e1e72f63a481ba349c23043c4027f137b9876 本地/远端一致；
新分支dev/nana-core-cloud-first-life-launch-v1-codex。GLOBAL_STAGE H不变，继承CDL/RAE，不重做PASS。
Phase A先定位增长：post-handoff开发库DB约12.6MB；events约6.8MB，artifacts约1.68MB；
queue full-row replay audit是可解释增长，不能以删除audit/provenance/UNKNOWN/隐私journal降数字。
实现host-local size/rate guard + PASSIVE checkpoint + 分类型numeric profile；超限停止writer，不改原愿望；
host guard窗口跨重启保留，corrupt fail closed，不新增Store/SubjectLoop/schema。资格尚在进行。
环境当前ready但secret/variable/identity bindings为空；Phase B等待新的安全FD/Resolver与有限付费批准；
历史Provider UNKNOWN仍PARKED retry0/fallback0。Human review/production inventory/production切换仍未授权/未运行。
继续可独立的人工评审入口、单writer dev rehearsal与24h隔离staging准备；无真实社交/private data/production。
旧bundle untracked/untouched/not-input。下方CURRENT为历史保留。

First-Life checkpoint [源码/实测]：size/rate guard、restart latch、PASSIVE checkpoint、numeric storage view、
同Runtime私有chat client、immutable结构化human-declared review、实际3进程writer交接/回滚工具均已实现。
新focused6 passed2.54s；相关first-life/cloud25 passed16.64s（该次尚未加入最后client case）；
真人review NOT_RUN，测试评分不作为human证据，不自动升级readiness。下一步actual bounded soak与24h dev runner。

## CURRENT CHECKPOINT — FIRST-LIFE / TECHNICAL DEV QUALIFIED, EXTERNAL GATES PENDING
[实测2026-10-20] Base b06e1e72f63a481ba349c23043c4027f137b9876；GLOBAL_STAGE H。
Frozen executable645899b32220e66a702e75d59a279a3a9685693f；branch dev/nana-core-cloud-first-life-launch-v1-codex。
已实现/测试：host-local DB family/rate guard、跨重启STOP latch、PASSIVE checkpoint、只读numeric storage profile；
原Runtime私有chat client与不可变human-declared评分入口，测试评分不冒充真人评审。
Focused6 passed2.72s；最终full1274 passed/12 skipped/0 failed280.58s（11 live-screen+E12保持门）。
实际三顺序进程交接/新B8回滚epochs2→3→4、同identity、旧writer fence；不是实际production rehearsal。
90.1745秒有界运行42actions/14owned effects、SIGKILL恢复/backup-delete/B8迁移均通过；短run不是24h。
独立24h staging已真实启动，固定detached worktree645899b；根/workspace/nana-staging/first-life-24h-01；
progress.json为实时运维投影；目标86405秒，尚未完成时必须RUNNING_NOT_QUALIFIED，不升级24h或Beta。
managed dev host长期存续未attest；源码冻结，停止/失败不自动重启，不重复effects。
Provider新调用0；当前无新安全FD/Resolver/付费范围，历史one UNKNOWN parked retry0/fallback0；不使用旧聊天key。
Human naturalness/shared-life NOT_RUN；production inventory需新授权，cutover approval尚未到请求门；canary/72h NOT_RUN。
FIRST_LIFE_EXPERIENCE_READY=NOT_READY；CLOUD_DAILY_LIFE_BETA_READY=NO。
One original Subject/Store/Loop/Runtime owner；schema13/43表，新表0/依赖0；main/R045/production/private data不变。
下一入口：安全新provider绑定及有限付费批准；继续观察真实24h结果后另行收口，不能把后台启动称任务全完成。
报告/status/quickstart/production_preparation及小型证据见docs/nana_cloud_first_life_launch_v1_*。
下方CURRENT为保留历史检查点。

### Provider authorization update — credential binding still blocked
[用户显式授权 + 环境实测2026-10-20] 新资格目标DeepSeek / https://api.deepseek.com / deepseek-flash，
OpenAI-compatible，PUBLIC/PROJECT only，最多20真实调用、$1等值上限；PERSONAL/SECRET不授权。
用户声明Secret已在个人保险库，名称DEEPSEEK_API_KEY。环境实时observations_current=true/revision281，
secrets=[]、runtime_variables=[]：尚未绑定到当前任务。工具仅支持environment_status，无配置修改工具。
因此BLOCKED_NO_CURRENT_ENVIRONMENT_SECRET_BINDING；新真实调用0；模型/endpoint尚未live验证。
不搜索环境/历史key，不读个人保险库原文，不用明文文件；已请求用户通过环境配置绑定并审核。
绑定ready后仅从显式宿主安全源→内存pipe/FD→现有ExplicitFDResolver，沿原预算/Privacy/UNKNOWN合同。
历史TianToken UNKNOWN仍PARKED，禁止重放或fallback。此前“未获付费范围”在本时点被上述有限授权取代。

## CURRENT — FIRST-LIFE / DEEPSEEK FIRST LIVE REQUEST / PARTIAL
[实测2026-10-20] 当前开发分支dev/nana-core-cloud-first-life-launch-v1-codex；GLOBAL_STAGE H。
用户本轮显式提供新凭据并要求执行，走关闭echo的进程stdin→内存pipe→原ExplicitFDResolver；非保险库绑定成功。
凭据不入argv/env/config/evidence/Store，resolver已清理、临时调用进程结束；资格home/result exact scan0。
DeepSeek https://api.deepseek.com / requested+returned deepseek-flash；新真实调用1，HTTP200，3688.587ms，
usage5790 input/565 output/6355 total；严格解析、CognitionSession PROPOSED、原C WATCH/SOCIAL_INTERACTION。
未创建Actions/Grants/Goals；retry0/fallback0；历史TianToken UNKNOWN仍PARKED，不重放。
首batch硬限1次，RENDER被PROVIDER_HOURLY_BUDGET挡住：语义传输成功不等于自然对话通过。
真实费用UNKNOWN，公开文档当前未取得可核对适用费率；扩大调用暂停在cost-bound门（总授权20次/$1）。
REAL_TEXT_PROVIDER=PARTIAL_TRANSPORT_INTERPRET_PASS；human naturalness/shared-life NOT_RUN；FIRST_LIFE/BETA不升级。
修复“已配置provider却因render预算阻断显示未配置”的误导fallback，保留原测量结果，targeted12 passed8.01s。
24h staging独立固定645899b持续运行，已实际恢复epoch2→3，仍RUNNING_NOT_QUALIFIED；不接本次凭据。
生产盘点/切换/canary/72h仍NOT_RUN，main/R045/production/private data/real social不变。
下方CURRENT为保留历史；前述“新调用0/当前完全无凭据”的事实由此本轮显式输入与实测更新，不改历史UNKNOWN。

[实测 post-live final] provider-budget/dialogue targeted12 passed8.01s；最终full1274 passed/12 skipped/0 failed286.16s。
DeepSeek资格home无transport重新打开：同identity、同1条PROPOSED记录，无自动发送/重放、新调用0。
24h dev growth guard真实window600.914192s，logical growth167936bytes（约0.96MiB/hour观测速率），
低于32MiB/hour configured fence，状态OBSERVING；未裁剪history。仅有界窗口，不冒充24h。
新Provider总调用1，usage已知、actual billing/cost UNKNOWN，等待可核对费率；真人自然度/Shared-Life NOT_RUN。
Source/staging与live/fix证据分别登记；新Source修复不覆盖固定645899b驻留进程。

## CURRENT — FIRST-LIFE / DEEPSEEK FUNCTIONAL TEXT QUALIFIED / HUMAN REVIEW PENDING
[实测2026-10-20] 同一主线/分支，GLOBAL_STAGE H。累计17次DeepSeek / deepseek-flash；独立request IDs17，
无automatic retry/fallback/UNKNOWN；旧TianToken UNKNOWN PARKED，不重放。14 PROPOSED、1 REJECTED、2 FAILED保留。
真实功能场景：natural(v3)、source-grounded/correction(v4)、disagreement wording/unknown(v5)、shared(v6)
均INTERPRET+RENDER；拒绝topic与重启后仍关闭均0模型调用。原C judgment逐项保留，不把模型“不同意”措辞伪装Core DISAGREE。
Shared引用的是实际开发资格HTTP200及源码观察，不是私人共同历史/production经历，不能冒充真人Shared-Life评审。
累计保守reservation850000 nominal USD micro/$0.85，上限1000000/$1；累计calls硬限20，余3；
小时/日20，仅资格home CAS；跨重启/跨日期累计限制复用原cognitive_requests，失败/拒绝/UNKNOWN不退款。
实际billing UNKNOWN，16/17次可见usage总计80350 input/12320 output（非完整总量），provider-side硬扣费cap未attest。
修复对话wire schema角色范围与无关$defs，不弱化Core authority/schema gate；保留partial finish_reason/model/usage观测。
可选host profile chat_thinking_mode=DISABLED（官方公开文档已核实；默认PROVIDER_DEFAULT不变），
资格context16384/output2048/timeout15000ms继续与Model/Route/Runtime求交；生产默认8192/1024不变。
私有IPC评审入口已实际启动，same reference identity b5864db1-ecfe-4278-9bc2-76db0e096311、PID59982，
/workspace/nana-staging/first-life-deepseek-01/life；最多7200秒，当前余3calls通常仅1完整轮；不持久化真人对话原文。
Human naturalness/Shared-Life review NOT_RUN；FIRST_LIFE_EXPERIENCE_READY=NOT_READY，BETA_READY=NO。
24h staging根/workspace/nana-staging/first-life-24h-01固定645899b独立继续，约1h时ACTIVE/epoch3/q0/RSS44708KiB，
该进程provider calls0，未重启/污染，不冒充24h PASS。生产inventory/cutover/canary/72h仍NOT_RUN。
One original C/Store/Runtime owner per reference lineage；schema13/43表，新表0/新依赖0；main/R045/production/private/social不变。
下方CURRENT是保留历史；DeepSeek新functional qualification不把历史H1 TianToken/Qwen PARTIAL改成FULL。

[实测 continuation final checkpoint] focused70 passed13.81s；最终full1279 passed/12 skipped/0 failed294.18s。
当前凭据exact-match审计：1520个受控文件约49.7MB+git diff，matches0/oversized skip0，包含tracked/evidence/资格home+logs；
不搜索历史凭据、不读取旧bundle，不声称审计平台工具日志或所有宿主存储。当前人工入口凭据仅在有界进程内存持有，
不是“所有进程已清空”；早期资格进程已退出，新入口停止后Resolver clear，无自动credential恢复。
剩余3次模型调用通常仅1完整轮；未收到真人消息/评审则Human NOT_RUN，不把开发者候选检查当Human通过。
主线继续门是当前私有开发入口人工体验；24h真实驻留另行等待结果，不提前production inventory/cutover。

[实测 First-Life真人输入样本1，尚非真人评审通过] 原7200秒私有入口已graceful STOP/socket移除，首次IPC失败在dispatch前0调用。
确认same home17条请求均terminal、无CALLING/UNKNOWN后，同identity新epoch内存FD恢复，仅处理本轮真实用户PROJECT输入。
INTERPRET+RENDER成功，累计19/20、reservation950000/$0.95（非actual bill），余1不足完整下一轮，不扩额度/不盲重试。
本轮context_mode UNCLEAR、原C ASK/WAIT，候选未获取最新PROJECT_BRAIN主线状态；不把这解释为用户表达有问题。
诊断线索：初始Local input metadata的UNCLEAR占位也会进context，可能影响解释；尚未验证根因，不改写本轮候选。
不入库真人原文/候选原文，仅结构化结果元数据。Human verdict PENDING，评分未记录，First-Life/Beta不升级。

## FIRST-LIFE — bounded SSOT context / explicit project inquiry / invalid review sample
[决策2026-10-20] 用户确认review chain缺口不是语言质量结论。保留原样本输出历史，但不纳入正式Human Naturalness评分。
不新建评审记忆：唯一当前状态摘要内嵌09_STATE typed header；宿主显式选择源/path/scope，
通过原ContextAssembler投影，最多12KiB前缀/8KiB JSON、时间有效、有限条目、hash/revision/source。
来源是external engineering status，不是Subject个人经历、execution authority或开发者日志记忆。
PROJECT_STATUS是原context-fit认知意图，仍由原SubjectLoop决定WATCH/SOCIAL_INTERACTION，不新建表达循环。
Neutral receipt仅是“已收输入，解释待定”的DIRECT_OBSERVATION；不能预先宣告UNCLEAR，也不能借此存入任意原文。
旧记录不反写，缺失/过期/变化/删除源不允许旧context继续采纳；既有privacy/token/权限边界保留。
新付费评审必须在离线修复与可审查提交后请求新的小额授权；余1次不使用，staging不更改。

## MASTER_FRAMEWORK_FREEZE_V1 — 用户正式冻结总宪法与Foundation核账

- 日期：2026-10-20（Asia/Shanghai）；来源：[用户明确指令]「好，现在正式冻结」「接下来不再改宪法，开始核账」。
- SUPERSEDES：旧账本中“下一步继续DeepSeek真人评审/新增小额复评预算”的近期任务安排，以及只靠GLOBAL_STAGE描述整体完成度的口径。保留全部既有发生事实、Provider资格与失败/UNKNOWN证据；不推翻历史实现。
- 冻结：`00_MASTER_FRAMEWORK.md` 的Ultimate Vision、S1–S10正式定义、三横向轴及最高原则；S8工程投入可极高但不是最高人生目的；Independent Life与Shared Life同时成立，Primary User不是认知/学习/思想边界。
- 总框架仅因逻辑矛盾、已确认终极目标不可表达或真实证据证明不可行而修订；新想法先归域、区分基础/扩展、核证据和Gate。因新建议改变近期实施主线须FOUNDATION_MISSING + CURRENT_GATE_BLOCKER。
- 首轮criteria版本1.0，10域63项；限定开发范围S1/S2/S7/S8/S9 Qualified，S3/S4/S5/S6 Tested并留关键未知，S10 Partial且深层实现非基础First-Life前置。UNKNOWN不自动等于缺失。
- 新主任务：`MASTER_FRAMEWORK_FREEZE_AND_FOUNDATION_CAPABILITY_AUDIT_V1`。审计产物为Master+Matrix及机器可读账；核账结束后只关闭Matrix列出的有界资格差额，不无限审计或重写系统。
- Gate：S1–S9基础资格齐全后再作First-Life Integration Qualification；已有集成试验/驻留/Provider成果保留。24h固定源码run继续独立，本轮未读运行宿主、不重启、不污染；真人评审暂停，付费范围未扩大。
- 权限：本轮用户已明确要求写入仓库；仅提交文档/审计元数据及入口对齐，不修改业务源码、测试、运行配置、Store、生产、main/R045或真实社交。
- 证据：[01_CAPABILITY_MATRIX.md](01_CAPABILITY_MATRIX.md) 逐条实现/测试/范围/未知；`docs/nana_master_framework_foundation_audit_v1_evidence/` 为本次阅读清单、校验与指纹。

## MASTER_FRAMEWORK_V1 — independent review of af52371, no refreeze

[实测/决定2026-10-20] SUPERSEDES初审近期FQ-01优先排序；不改变总框架或63条criteria。
先保留本地10个草稿文件及hash，再fast-forward到af52371；拒绝用未提交80条草稿覆盖已冻结标准。Master逐字保留；criterion ID/定义/分母版本1.0逐字比对。
新18项历史测试快照对当前Core复核只补S3-C01/C02/C04/C06/C08受限资格，不填S3-C09真实倾向整链；S3域仍Tested，S4/S5未知门不提高。
依据PUBLIC topic_scope_probe、现有6项topic测试与context_fit/LearningService源码，确认对话拒绝和同题内部认知暂停语义混合；映射现有S6-C07，记Partial，并非断言整套Problem Framing不存在。
这是FOUNDATION_MISSING（仅有界语义区分）+CURRENT_GATE_BLOCKER，故唯一下一主线优先FQ-04：原C独立问题界定与认知范围分流，允许复用通用记录，不强制特定DTO/模块。不在本审计实施；不删guard、不扩权限、不新建脑。
S3已有主体基础但真实闭环资格仍缺，不能借此启动第二affect系统；S10深改保持禁用。S1–S9全部资格前Human/First-Life/production推进继续暂停。
本次只读staging进度，不重启或写其目录；原初审“未访问宿主”按初审时点保留，当前新增只读观察另有证据。模型调用0，私有数据0，生产/main/R045不变。

## FOUNDATION-CLOSURE-001 — bounded scope, framing and experiential need in original C

[用户任务授权+实现证据] 本轮在原分支关闭明确S6/S3差额，不修订Master或63定义。普通DECLINE_DELIVERY仅停止对外深入/投递，不能自动阻断同题内部认知；旧DECLINE_DEPTH保留processing限制，无法从旧规范化记录猜测新含义。显式hard privacy、Manager、资源和Grant继续独立。
选择最小typed framing hypothesis/evaluator：C从有源可见direct observation核查前提与alternative need，原Goal registry/planner做后续；不是第二自主planner，不宣称开放任意问题发现。相同问题/不同实际状态的对照和无Grant BLOCK证明收益及权限保留。
复用原Experience/lesson/independent reuse assessment派生competence need OPEN/SETTLED/UNKNOWN，不新增人格表或人工PreferenceSignal；匹配来源祖先而非仅domain标签，已满足的gap可不再重复学习，反例/撤回撤去支持。
全仓暴露旧共享training source删除后的重绑capture缺陷，选择退役整个共同支持bundle/specs，避免SOURCE_DELETED阻断恢复或重新构造被删来源；不以删guard修复。
S3/S6有限Foundation Qualified；S4/S5资格仍开放，S10深改不启动。旧审计source hash是edda历史快照，不再要求当前业务源码永久不动；校验器保留冻结标准逐字检查及历史快照完整性，新实现由本轮manifest和应用测试检验。
本轮无新付费调用，S5 live新授权门不使用旧key/冻结余1；S4固定驻留只读，不凭时间推断。First-Life/Human/production不升级。

[本轮压力反例补充] 34次delivery记录曾触发33条horizon fail-closed而暂停内部认知，普通“可以再讨论”也曾复用processing REOPEN；两项测试先真实失败后修复。用原target_id索引分开两条ledger，无新增表；REOPEN_DELIVERY不解除processing，旧REOPEN保留原显式语义，边界转换commit前不发模型请求。反例与最终测试留证。

## FOUNDATION-CLOSURE-002 — one live request authorized; safe binding remains mandatory

[用户明确授权] 允许仅S5-C06最多1次DeepSeek PROJECT请求，15秒、0retry/0fallback、保守预留≤$0.05；不复用旧请求，不扩大真人/生产/私人/社交范围。用户允许此前Key使用，但凭据通道仍必须是安全FD/Resolver，不能把聊天凭据写进工具命令/argv/env/文件或日志来模拟绑定。环境320当前没有绑定；额度未消耗，单项等待安全绑定，不再重复询问调用许可。S4固定run只读继续，不因缺凭据重启或终止；未获最终结果不升级。

## S5-C06 LIVE FOLLOWUP — latest current amendment

新授权1次DeepSeek PROJECT调用完成，HTTP200，输入6849/输出290 tokens，timeout15000ms、实际2565ms、retry0/fallback0、保守预留$0.05。原identity b5864db1-ecfe-4278-9bc2-76db0e096311保持，累计20次/保守预留$1；实际billing UNKNOWN。
真实项目源→strict MODEL_DERIVATION→World SUPPORTED_BELIEF→Concern→原C EXPLORE；真实source撤回→World UNKNOWN→C NO_ACTION；无Action/Grant/Goal新增。重开原home后request20且本次request/cycle各1，无再次dispatch。
用户明确豁免宿主保险箱绑定，本次仅stdin内存→既有ExplicitFDResolver→Authorization；无argv/env/file凭据，exact-match扫描0，进程已结束。未搜索历史凭据。
S5-C06/S5升级FOUNDATION_QUALIFIED，固定63项60资格/3未知。S4最终24h仍待实测；S10两项高级门不阻塞First-Life基础。Master/criteria不变。
S1_TO_S9_FOUNDATION_QUALIFIED=NO；FOUNDATION_CLOSURE_COMPLETE=NO；READY_FOR_FIRST_LIFE_INTEGRATION_QUALIFICATION=NO。真人评审NOT_RUN、First-Life/Beta不升级、main/R045/production/private/social不变。

## PARALLEL HARDENING / FIRST-LIFE READINESS V1 — current side-work

[已实现/已测试/owned dev process，2026-10-21任务，UTC实测2026-10-20] 继承14e66be，同一Foundation Closure主线旁路加固；隔离worktree/dev homes，不重做已资格S3/S5/S6、不开始First-Life。
TYPE B：已复现FIFO storage guard启动卡住；storage/privacy打开FD后regular+NOFOLLOW/NONBLOCK+bounded读取。owned IPC使用单调时钟总frame deadline、拒绝重复JSON key/不完整帧/错误envelope，原PID/UID/inode/Grant/Manager/Verify不变。深嵌套JSON未复现crash，明确仅防御性异常处理，不虚报P1。
TYPE A：新增独立只读Inspector DTO/CLI，mode=ro/query_only/有界读取，复用既有need/appetite/relationship投影。只输出PUBLIC/PROJECT metadata/WHAT-WHY codes/source refs，不输出purpose/模型文本/治理正文/secret；pending privacy journal fail closed，不修复或初始化Store。SHM read mark为SQLite临时协调状态，不声称逐字节完全无读标记。
实际2个SIGKILL atomic cut + ENOSPC replace + malformed owned IPC + delete/pending-journal + seeded frame cases；新focused16（纳入FAST61），相关37、组合26通过；最终显式tests/全仓1339 passed /0 failed /12 skipped，323.52s。5个现有JUnit格式warning保留；后续runner仅将报告格式设xunit1，未改业务语义。
准备只读preflight、First-Life启停/恢复/备份/回滚runbook、21项Failure Matrix、domain→suite映射与验收清单；Private Intent仅设计/disabled，无新C语义或第二脑。pip check通过，CVE联网扫描NOT_RUN。
原固定645899b staging只读仍RUNNING_NOT_QUALIFIED，无actual final；不重启/写入/推算24h PASS。Master/Matrix固定63条及状态均不变，S4-C06仍唯一S1–S9基础资格门。Foundation/Integration readiness均NO，human NOT_RUN、First-Life/Beta NOT_READY。
本任务新付费0、private/social/device/production/main/R045改动0；schema13/43表/新依赖0。历史DeepSeek/S5与TianToken UNKNOWN保留；旧bundle不读不动。
详见docs/nana_first_life_hardening_v1_implementation.md及同名evidence目录。加固不构成生产或真人评审许可。

## CURRENT — S4-C06 ORIGINAL FINAL / FOUNDATION CLOSURE COMPLETE

原固定645899b实际86405.272秒，exit0；源码205文件+supervisor、1464资源采样、42唯一Action/14 owned-dev effects、SIGKILL、DB/FK/queue及迁移权限完整核验PASS。原run未被重启/停止/修改；raw结果低界标签不代替实际时长。
S4-C06/S4 FOUNDATION_QUALIFIED；S1–S9逐项已资格，固定63项61 qualified/2 advanced unknown；Master/criteria定义/ID/分母不变。
S1_TO_S9_FOUNDATION_QUALIFIED=YES；FOUNDATION_CLOSURE_COMPLETE=YES；READY_FOR_FIRST_LIFE_INTEGRATION_QUALIFICATION=YES。S10高级项非基础前置。
这是原冻结owned-dev进程资格，不是最新代码24h/生产云宿主/真人体验资格。Human naturalness NOT_RUN；FIRST_LIFE_EXPERIENCE_READY/Beta NOT_READY；不自动启动First-Life或新任务。本次Provider0、私人/社交/生产/main/R045改动0。
证据：docs/nana_foundation_closure_v1_evidence/staging_final_verification.json；独立只读工具tools/nana_foundation_closure/staging_verify.py。历史运行中CURRENT块不再代表当前状态。

## CURRENT — FIRST_LIFE_INTEGRATION_QUALIFICATION_V1 / IMPLEMENTATION

用户已授权本次First-Life组合资格，SUPERSEDES先前“Foundation未齐/不得启动First-Life”的任务暂停；不修改Master或63条Foundation标准。继承8a1e2cf与全部S1–S9资格，S10高级项不重开。
复用原LifeApplication/Runtime/Store/C/World/Concern/Hands/Growth/skill路径；新增源支持、原C事务内结构化私人意图与metadata-only Inspector，复用INTENTION typed envelope，schema13/43表不变。普通chat不自动取得私人内容；私人≠隐瞒Action/Grant/预算。
开发入口与预检已实现，真实同一Subject组合与进程资格进行中。真人评审NOT_RUN；First-Life Integration尚未资格、First-Life Experience/Beta不升级。历史Provider额度已用尽，本任务新调用0，安全FD/Resolver及新小额授权门独立等待；不使用历史key。原24h staging与bundle不读写/重启。
实现/复现入口：docs/nana_first_life_integration_v1_implementation.md、docs/nana_first_life_integration_v1_quickstart.md。生产/main/R045/真实社交/私人数据/用户设备不触碰。

## 2026-10-21 — First-Life integration observations / no constitutional change

1. B8 correctly excludes host current-state bindings; review host explicitly
   rebinds the approved bounded PROJECT header. No second memory, no full brain
   document injection, no Codex logs as Subject personal experience.
2. Scope-specific semantic interpretation may pin sources through original
   ContextAssembler. Backward-compatible prepare(pinned_only=True) excludes
   unrelated conflicts; required disputed/deleted/private sources retain all
   rejection/complete-conflict/privacy guards. Defaults unchanged. This fixes a
   proven before-dispatch integration block, not model/authority semantics.
3. Before-dispatch continuation requires observer0 and unchanged original
   reservation ledger; no reset/replay/renewal. After the one actual HTTP200
   strict-invalid reply, stop; retain failure/budget, no fallback.
4. Operational provider failure metadata may survive source deletion; it is not
   semantic evidence or permission to resurrect content. Typed outcome/lesson
   projections replace misleading generic UNKNOWN, still read-only.
5. Synthetic PRIMARY_USER role expresses high relation importance in C without
   Grant. PERSONAL anchor is not declassified for PUBLIC/PROJECT model use.
6.30min pin is629d2da/211files; subsequent Inspector/context-selection deltas have
   their own targeted/regression evidence. Do not call the final delta30min-qualified.
7. HTTP200/model/usage is not semantic or human quality qualification. Current
   live malformed reply root cause transport-vs-model unconfirmed; user opener
   not sent, so no adverse human naturalness conclusion. First-Life PARTIAL/NO.

## 2026-10-21 — First-Life ONE_SHOT live response closure checkpoint

Latest ONE_SHOT user instruction supersedes prior one-new-call/old-specific-root gate: up to7 unspent original slots may verify a fixed/reproduced/explicit compatibility hypothesis, at most1 new validation per iteration, no retry/fallback, no budget reset. Unknown old field stays UNKNOWN: safe diagnostic loss is proven, synthetic text-array mismatch independently reproduced, not claimed as old body. Reasoning/vendor metadata stays infrastructure-only; bounded text blocks still pass original strict semantic contract. Latest task defines EXPERIENCE_READY as a technically usable live entry; real HumanReview is separately necessary for INTEGRATION_QUALIFIED. This delivery-state distinction changes no Master/criteria. Missing current memory-only credential is an external binding gate; do not retrieve historical chat keys or weaken credential persistence policy.

## 2026-10-21 — ONE_SHOT technical handoff / explicit citations and C continuity

Current explicit user credential input may feed echo-disabled TTY→memory pipe→FD
resolver; this is not authority to discover unrelated secrets or expand provider,
privacy or budget. No persistent key, env/argv credential or vault success claim.
Actual C already supported PROJECT_STATUS; add it only to finite metadata ingress
allowlists, preserving raw-text exclusion. Dialogue wire citation enums mirror
existing Core source_context_refs: never normalize/drop an unsupported returned
citation. A fresh rendering qualification may use a still-supported existing
committed C via its idempotent result without re-INTERPRET, new judgment or reissue
of rejected provider requests. Current typed project state is external engineering
provenance, never personal Nana experience. EXPERIENCE_READY is technical delivery;
HUMAN_REVIEW/INTEGRATION_QUALIFIED remain actual-user gates. Stop feature work now.

## 2026-10-21 — Portable Cloud Runtime V1 host boundary

The runtime distribution is code+hashed dependency wheels, not Subject data. Fresh
init is explicit/new identity. Same-Subject migration only uses existing lawful B8
retirement/import/activation and revokes old Grants. Ordinary backups remain
quarantined; they never become a second writer. Host config/provider credentials
are separately bound, runtime starts paused, no copied old socket/owned-app Grant.
Private remote entry is authenticated SSH to the original CLI/Unix IPC; no new
HTTP service, public listener or second brain. Standard-library packaging and
original services preferred; no new dependency or business table. Supported V1 is
CPython3.12 Linux x86_64; other platforms require explicit future qualification.

## 2026-10-21 — Portable qualification scope and stop

Ship only exact committed runtime families+owned public materials+hashed existing
dependency wheels, not repository/private snapshots or current Subject package.
Archive source4bc4c05 is distinct from later evidence handoff commit. Reproducible
archive uses source commit timestamp; actual clean installs/processes qualify it.
Source retirement/B8/local lock are trusted offline single-operator fencing, not
new distributed anti-copy authority. Ordinary backups stay quarantined; executable
restore uses lawful SubjectPackage. Remote experience is existing authenticated
SSH/CLI, not a new HTTP listener or automatic server login. Platform result is
Debian13/x86_64/CPython3.12, other actual cloud hosts remain NOT_RUN. No live calls,
credential reuse, current Subject retirement or First-Life human/Beta upgrade.

## CURRENT — portable release final pin / supersedes candidate4bc4c05

Final runtime source `bfea92cc205b91ad7a3ca8dca4eb7c955b6d57a0`, archive SHA256 `228ef80e53ef961a409a651746a207a11a8bc72affe1940998e5c108fec9119a`.
Total decompression ceiling includes hidden tar metadata; final artifact clean-installed/
A→B process-qualified and deterministic rebuild equal. Focused28, full1407/0fail/12skip;
post-collection changes are unpacker-only, no shipped Core delta. NewProvider0, no actual
current Subject migration, private history or production; same declared dev scope. STOP.


## CURRENT — Persistent Person-Self / Lived Language V1 · 2026-10-22

Explicit social convention is not biological fact or execution authority. Retention is opt-in per turn; reported assistant speech is not truth. Source-aware context must include stable self or fail before paid dispatch. Use existing record kinds/tables and original Experience/Lesson, no schema migration. Human reports and project synthetic contrasts cannot manufacture each other’s qualification. Additional work selected from the observed contradictions: trusted generic instance profile, context-budget visibility, and finite unfinished-topic opportunity; not a second emotional brain.


## HANDOFF — Persistent Person-Self / Lived Language V1 · 2026-10-22

Optional speech ancestry is bounded without severing stored privacy edges; stable Self stays separate. Bound feedback inherits privacy and stores copied text atomically with dependencies; current report source must be exact. External review study material is not own lived history. Historical release manifests are checked at their committed release, while the new manifest attests this workstream.


## Open Life V1 — construction/experience separation and owned growth boundary

New user mission explicitly continues Track A while Track B awaits actual human review. This supersedes previous task-specific developer STOP, not Master/criteria or human PASS requirements. Add attention as original jobs and C cues; research is evidence comparison, not learning; exact owned Browser port joins sealed development allowlist, without accepting arbitrary subclasses/network. Form gestures are simulator proposals, not user-device permission. Meta-strategy projections do not modify the evaluator.

### Open Life — research is original D work after original C, not a demo controller

ResearchService is advanced by original maintenance slices only after a committed
C EXPLORE/ENDORSED. Existing jobs/records retain state; bounded reconciliation
closes acknowledgment/scheduling gaps. Same source cannot generate a new research
wish each wake. Unknown intake forbids later poll-bucket retries. Research remains
belief comparison, not skill acquisition, independent world truth or authority.
Historical release manifests bind their historical code; new growth is separately
attested. No frozen Master/criterion definitions or S10 verifier rules change.


## Open Life final scope and release separation — 2026-10-22

Runtime/research/learning remain within original C/D/Store/G/I. LOW/repeated
value inhibition belongs to original C, while queue admission only handles
privacy/current source/expiry/idempotency. Automatic research has bounded durable
slices and original C endorsement; HTTP dispatch UNKNOWN cannot become a new-poll
retry. Meta lessons select practice hypotheses, never replace heldout/evaluation.
The portable archive pins clean runtime c4791d0; final documentation commit records
its hash rather than rebuilding business code for a self-referential commit.
Scope-qualified dev PASS does not promote human/First-Life/Beta or device authority.

## Controlled World — one delivery owner and active temporal bounds / 2026-10-23

[源码及owned运行证据] 专用opportunity/shared cue不能再被generic watcher重复投递；这是source delivery dedup，不删除愿望/原判断。Experience attention必须链接原Experience走原reflection/G，无适用学习的review不制造Lesson。World候选64上限作用于当前有效候选，不能因过期历史增长永久UNKNOWN；correction仍挡旧claim复活，withdraw保守性保持。两个可重建索引只服务查询，不新增业务表/schema/authority。默认pytest覆盖整个tests，旧588子集不冒充全仓。原Master/63定义不变。


## Decision — Controlled World V1 / explicit evidence scope after host replacement

采用独立per-source seed让真正combined life形成三源CONTRADICTION，不向driver写研究答案。HTTP202仅volatile admission；仅三个输入前置拒绝可收口为REJECTED_INPUT，lease/privacy/integrity仍传播。资源成本为host estimate，绝不提权或伪造账单。

实际boot更换且原final缺失时只能PARTIAL_EXTERNAL_LIMIT；保留旧run/unknown exit，不以日历时间、重建run或进度文件代替>=5h原始结果。只读checker的partial一致性PASS不表示驻留PASS，固定27个task gate不能省略；Master/63不改变。新验证receipt保存在/workspace而非依赖/tmp。


## Precision V2 P1 — source candidate / 2026-10-24

采用有限AND group + 原operator替代路径/显式dataflow/1024 expansions与8192 frontier，不建第二planner。原1024 UCS组合爆炸及fact-only来源混淆由frozen baseline复现。独立Kernel reobserve是有Grant/预算的读，不改旧Action成功，不等于dispatch；仅当前MATCH且expected digest吻合的完整group前缀可复用，UNKNOWN/未对账成功禁止重规划。修复旧pending step占槽和replan commit→ack幂等gap。每个op携带可选task_domain，让真实失败进入适用G方法，不全局跨Hand套用同一lesson。practice竞争只看public practice，heldout/evaluator/authoritative Core无自改。


## Precision V2 P2 — bounded current-state recovery / 2026-10-24

P2 code review: a changed checkpoint is an expected boundary, so original LivingWork records exact CURRENT_STATE_REVIEW_REQUIRED and defers only that review; replay cannot repeatedly reserve/check it, and lease/privacy/unrecognized failures still propagate. TaskCheckpoint/Output/Check DTOs version/correlate new persistent metadata. Kernel reobservation never mutates historical Action outcome. Benchmark selection/planning/learning bytes remain frozen in0092cae; final wrapper guard does not use heldout answers.


## Precision V2 P3 — measured redundant anchor reads / 2026-10-24

Profile of the actual eight-task owned life found69641 anchor JSON loads and13.725s in ensure_current. A volatile validated-file signature cache still lstat-checks inode/dev/size/mtime/ctime/mode/uid/gid every read, reloads/revalidates on any change, and fails closed under replacement race. Same-size corruption with restored mtime and another trusted publisher durable delete both invalidate; original backup/delete/SIGKILL/privacy related12 PASS. Profile after:618 loads/2.052s in ensure_current; overall wall32.17→34.77s under different concurrent load, so NO end-to-end speedup claim and no invented lease-failure root cause. Bound actual planner heap as well as unique state keys at8192. Two old process failures isolated unchanged:2 PASS25.61s; earlier1170.94s diagnostic full1521pass/2fail/12skip retained, final full must rerun at frozen new bytes. Foundation checker only adds this authorized workstream to its entry allowlist; Master/fixed63 definitions unchanged. No protected staging/credentials/production/main operation.


## Precision V2 FINAL — scoped engineering qualification / 2026-10-24

Advanced Growth S2/S4/S5/S6/S7/S8/S9 +three axes; GLOBAL_STAGE H/current original branch.
Source 0a509a8650735b57f540720f310d480fb2ccd9aa; baseline d695ed7. Original C/D/F/Kernel/G evolved, no second
Subject/Store/Runtime/planner/will. Actual owned9-step failure→G→C→6 checked-prefix
operators retained→3-step completion, file move once; two actual SIGKILL cuts plus
installed restart/official transfer preserve identity/checkpoint and fence old grants.
Frozen dev9/20→20/20,finalunseen6/20→20/20,novelgraph9/13→13/13; acceptedfalse0→0.
Full1528pass/0fail/12skip862.499s,18new allpass; prior failure receipts retained.
Schema13/43tables/newtables0/deps0/runtimeprocesses0; Master/fixed63 unchanged.
Portable240 files,doublebuild SHA256 bcb3560c831014e014b8ff05121f96418b5d0003ba434f47220809db45ba7497; two offline installs +new probepass.
SCOPED_ENGINEERING_UPGRADE_QUALIFIED_EXTERNAL_GATES_PENDING. Semantic/LLM ablation/human
NOT_RUN; historical5h PARTIAL_EXTERNAL_LIMIT unchanged,new longresidency pending.
First-Life NOT_READY/Beta NO; newpaid/private/social/userdevice/production/main/R045/S10=0.
Report docs/nana_precision_v2_status.md; manifest SHA256 4f6c2a5ec0a41b495268dc2f90527f8009bc67d858c112c56cd83d02d1d539e6.

Selected bounded causal/history search over adding a new planning framework; finite
AND groups and primitive OR alternatives,not arbitrary recursive HTN. Original
independent validator retained. Partial work reuse requires original Kernel
fresh Verify authority/budget and matching expected effect; symbolic fact alone
cannot certify old writes. Current uncertainty parks C review without changing
judgment or retrying UNKNOWN. Optional practice competition sees only practice;
evaluation/transfer remain independent. Host cold-start readiness15/max30 is
explicit and separate from unchanged execution/lease/stop-reap invariants.
Privacy cache is volatile file-signature validation with lstat every access,
not a memory/authority cache; no end-to-end speedup inferred from parse counters.
No architecture change required for already-tested original Manager/Grant,
typed owned ports or runtime ownership; this is scoped reuse,not a claim all
future capability/semantic cases are solved.


## Engineering Quality Portable Runtime V2 — active / 2026-10-25

GLOBAL_STAGE H / Advanced Growth S1/S2/S4/S7/S8/S9、三横轴；非Foundation新Stage。87f73d2独立worktree/branch，不改另一AI Nana Space分支。Q1/Q2修复与定向证据见implementation：SQLite官方WAL修复门槛不降低，共享实际绑定检查；沙箱真实资格不是which；明确字节Socket路径与-O关键检查；精确发行清单及独立资格工具。静态/可读性、便携新包和全仓仍待，旧1528和bcb包仅历史基线。原Master/fixed63/S1–S9资格与S10 Partial不变。新paid/private/social/production/main/R045=0。


## Engineering Quality Portable Runtime V2 FINAL / 2026-10-25

GLOBAL_STAGE H / Advanced Growth; 原Master字节/固定63/61qualified/S1–S9Qualified、S10Partial不变。
独立dev/nana-core-engineering-quality-portable-v2-codex，base87f73d2；runtimee322f01、full源码9e67c83，Core/打包/Builder/Addon字节一致。
共享SQLite>=3.51.3 WAL修复门槛+JSON/FTS5/native实际绑定；installer与实际venv均检查，伪venv在pip前拒绝。
实际非root private libffi+SQLite3.51.3+CPython3.12.14双独立离线安装、完整运行/Chat/Inspect/Stop/Restart、SIGKILL、官方B8迁移/旧owner与Grant fence通过。
exact197源码assets/231归档files，184 installed imports闭包；demo/lab/qualification独立5文件addon，G/I/Hands/checkpoint保留。
bwrap实际11隔离checks与可选能力拒绝、最终107字节Socket前置、prctl/backup/47资格guard在-O保持。29热点纯format AST一致；全库复杂度债务仍在，新增检查有实测开销，不称加速。
当前实际full 1542 passed / 0 failed / 0 errors / 12 skipped / 656.233s；旧初败/中断/缺ctypes/夹具试验保留，不删测试/不新skip。Precision published/fresh oracle零false，原9→6保留+3repair/moveonce实际安装通过。
归档SHA25625ad9723cc9d4ac31eea6b67f8661b332fc53fb6bff298d540c038fb5ada10de；addonbb572d22159966c95b206aba783162b1556bd185bf890161b293d5f73af622c4，两者各自双构建一致。
范围为OWNED_DEV Linuxx86_64工程资格，非生产/跨平台全资格。B10/versioned frontend contract不变；host preflight增加诊断字段。
旧5h PARTIAL_EXTERNAL_LIMIT、新long PENDING_EXTERNAL_STABLE_ENV、human/semantic/ablation NOT_RUN、First-Life NOT_READY/Beta NO保持。
main/R045/production/private/device/social/paidProvider0。报告与证据：docs/nana_engineering_quality_portable_v2_status.md、implementation/quickstart及同名前缀evidence/manifest。


## First-Life Android APK Integration V2 — active / 2026-10-25

用户授权一个开发者统一Core/Android/前端职责；GLOBAL_STAGE H/Advanced Growth，Master/fixed63不变。d207质量线与b899UI线共同base87f，显式合并仅apps新增，旧v1开发guard保持。新v2契约/认证/Host Supervisor/React十页/原生Keystore HTTPS/APK在独立分支施工；云端inventory/生产canonical、真实私人Iris/QQ/模型费用/实机/release key/后台push/72h仍分别BLOCKED/NOT_RUN，不冒称已上线。SDK/构建位于独立开发宿主，无生产系统修改。依据附件8正文已完整读取并核SHA。详见docs/nana_first_life_android_v2/IMPLEMENTATION.md。


## First-Life V2 — injection compatibility / user addendum

外部网页/B站/AI内容不能仅凭文本成为system/Manager/Primary User/Grant；复用原Provenance/epistemic/privacy/Memory source lifecycle/Capability/Manager/Grant/Verify边界，不新增防护Brain或改变Single Subject/Store/Loop。v2认证角色由可信宿主绑定，消息只是SurfaceObservation，APK无Core/高权限服务端密钥或DB handle。仅修当前接入可复现的接口/权限绕过；未来开放自主网页、社交、自主安装技能前另做专项攻击资格。不得借防护关闭已有自主目标/兴趣/长期学习/主动交流/工具/合格自扩展，不把每步判断交Primary User审批；区分主体自愿目标、外部信息建议和正式执行授权。终极愿景/fixed63不变，优先首次真实长期使用。


### First-Life Android V2 — original Core integration checkpoint (2026-10-25)
[开发实测，S1/S2/S4/S5/S7＋Surface/Governance横轴；Advanced] 同一v2 BFF连接原Runtime/Store/SubjectLoop，认证角色不来自关系或消息声明。Host stop latch、固定release/同home重启与SIGKILL、source-aware投影/撤回、UNKNOWN不重发。真实Core Web三尺寸联合通过；原生APK构建/lint通过，模拟器/真机分别报告。Cloud inventory已收，未做生产/私人/真实模型/QQ发送。保留旧v1 guard、Master字节、固定63标准和历史资格；No second authority。后续按部署门收口，不把工程实现冒充First-Life/云端72h资格。证据见docs/nana_first_life_android_v2/。


### FL-A follow-up — independent hosting and durable storage (2026-10-25)
[用户确认/待最终host只读核验] 容器内private Python3.12.14/SQLite3.51.3与nonroot准备接受，不重做；/opt/nana-core宿主Mount持久化、最终环境ABI及systemd仍待真实证据。优先独立Ubuntu非root systemd，不可用才独立非rootDocker；不能依赖AstrBot/nohup/旧cron。正式Store/身份/备份不能只在容器可写层。bwrap保持BLOCKED，不改AstrBot cap/seccomp、不重启QQ、不退化exec；S9保留，其余合法自主能力继续。bz2/lzma当前非必要，不新增编译。只读host_probe已提供，无生产操作。genesis/私人导入/旧写者关停/QQ投递/生产流量仍独立批准。


### FL-A storage/hosting final user selection (2026-10-25)
[用户决定＋两份只读审计，S4/S1/Governance横轴Advanced] 固定host /srv/nana-core/{runtime,data,logs,backups} →container /opt/nana-core同四目录，独立nonroot Debian13 Docker，UID/GID999；不再等待systemd选型。后份证据撤回host PID1推断；旧/opt和/root备份仍在overlay，不能放行持久化。既有private runtime prefix=/opt/nana-core/runtime，Debian OpenSSL3.5.7依赖不能直接搬Ubuntu3.0.13。已有SDK通过不重做，待实际非敏感runtime归档在独立容器验证；镜像基础准备不冒充该资格。handoff=/AstrBot/data/_nana_core_handoff仅运行时/说明/哈希/结果，禁止Subject/identity/私人DB/密钥/生产备份。当前无云端安全访问，未假称复制或创建/srv。genesis/私人导入/旧写者关停/真实QQ/生产切流仍未批准。bwrap二进制已装但namespace拒绝，保持BLOCKED、不扩旧容器cap/seccomp、不重启QQ；S9不删除，bz2/lzma不补装。Master/fixed63/原主体机制不变。


### Supplied cloud SDK / isolated Docker closure — 2026-10-26
[实测，S1/S4/S5＋Platform/Governance，Advanced] 四分片/整包SHA/CRC/13封条/4766文件＋10软链通过；先读CODEX_HANDOFF，原脚本隔离执行7PASS。实际云端SDK在独立Debian13 UID999验证Python3.12.14/SQLite3.51.3/OpenSSL3.5.7、固定prefix、TLS证书校验HTTP200。修复umask权限、BFF发布端口不可达、首次密码stdin FD、Core unpack父目录并将同APK LIVE Web入镜像。实际四卷/只读、十页/原C离线对话/备份、杀BFF自动恢复、容器重建同ID epochs2→3→4、B8恢复及旧源fence/Grant撤销通过；39 focused PASS。新全仓回归在稳定源码检查点后执行，不能复制旧数字。原失败证据保留。正式cloud部署/genesis/private import/旧写者/QQ/生产尚未执行，无Provider调用；bwrap仍BLOCKED，Master/Matrix/fixed63不变。原始材料与复现见docs/nana_first_life_android_v2/CLOUD_RUNTIME_VALIDATION.md。


### First-Life Android V2 — final supplied-runtime seal and regression
[实测2026-10-26，Advanced] 完整固定源码4ec0dfc回归1581 PASS/0 FAIL/12 SKIP，368.62s；11 live screen＋E12未运行，5 JUnit metadata warnings保留。后续只修部署提取mtime/构建-B，避免原SDK 61个pyc重写；并加强WAL返回及精确PORTABLE_SOURCE_RETIRED断言。最终39 focused和实际新镜像再次通过，安装/导出后4766文件＋10软链与原包全等；Core/API/Web/Native业务字节不变，不冒称后续又全仓重跑。最终镜像0d8426762cef4bc19b12a7930361fbc9a9c4096628ffb0ee4024407ec5a1a5ee；PID杀/自动重启1、重建同ID epoch2→3→4、B8恢复/旧源fence通过。genesis计划/切换回滚材料已准备但没有批准或执行。所有失败原证据保留；bwrap云端BLOCKED，Provider0/private NO/social0/production NO，First-Life NOT_READY/Beta NO。


### First-Life V2 — APK delivery and single cloud approval draft (2026-10-26)
[用户确认99b93d4后，仅交付/准备；S4＋Platform/Governance Advanced] 已核现有debug APK SHA75e7576c...、固定私有GitHub直链；当前无二进制聊天附件上传接口，不冒称已上传附件。生成非敏感operator ZIP（含原APK/Web/Core与部署材料；不含SDK重复包/身份/私人DB/凭据），两次构建相同、CRC/清单/原APK字节/敏感模式检查通过。单一PRODUCTION_APPROVAL_V1草案覆盖/srv四目录、独立UID999 Docker、拟tailnet8443、genesis/fence/切换影响/回滚与拒绝门；实际宿主安全通道、Serve精确差异及旧writer恢复命令仍需宿主元数据补齐，不能称已具备生产执行条件。当前不请求逐项审批、不执行genesis/私人迁移/旧服务更改/QQ切流/付费。正式D阶段会造成旧QQ回复空窗须最终审批知情；bwrap仍BLOCKED。继承所有已验收结果，不重跑旧环境或业务测试。First-Life NOT_READY/Beta NO，main/R045/生产不变。


### First-Life rev3 — A/B preparation, C/D/E deferred (2026-10-26)
[实际文件/本地新增部署验证＋云端操作者四报告；S4/Platform/Governance Advanced] 65c49aa本地远端一致、干净起点，4份rev3已全文读并登记哈希，不复制QQ账户ID/私人正文。原合格镜像0d842676通过docker save导出，原tar589073920bytes/SHA4ef8918a75db986c5c4dd63b8e9c9fc585308be9a8414159aaa8f92c855dae17，linux/amd64/999:999；gzip9片≤28MiB，重组及docker load同ID通过，未build。空runtime0555遮挡重现、完整6565条文件树安全提取/权限修复/只读挂载UID999通过，非空重装拒绝；只属新增本地落地测试，云端尚无安全访问绑定，未假称/srv已填。原plan文件SHA41c343...为字节摘要；Core DTO摘要e3e2...e7ae5...另名绑定，保留原语义、不执行genesis。B1脚本用公钥OpenPGP、显式SSH agent/host key及独立宿主tailscaled socket，合成加解密/隔离恢复/离线UNKNOWN测试通过；真实PC未绑定，异机DR未资格，PC私钥不出PC。9项新工具测试通过，不重复旧SDK/全仓资格。明确新版无/ws/SSE、entry无genesis CLI；新宿主AuthURL只能由云端针对实际独立daemon生成，不碰nanadocker。C仅准备、D/E继续暂缓，Provider0/production NO/private NO/social0，bwrap BLOCKED、Master/63/原主体不变。


### H / First-Life Real Living Integration / 2026-10-27
[Advanced S1/S2/S3/S4/S5/S7/S8及Surface/Shared Life/Governance；实现+离线实测] 独立a07e906后继分支，不改CotEX apps或Host Operator。复用Supervisor/原C/D/G/I/V2/B1；新现有身份只读schema/完整性预检，显式host opt-in＋HOST_ADMIN ProviderCommand HTTP/CAS/idempotency接线，默认关且零模型调用；缺provider config不冒充主体缺失。Home沿用affect来源元数据，backup/status只投影调用者原回执，不伪造PC资格。新hash-only历史计划绑定身份/lineage/输入摘要，去重以source隔离；私人正文/旧Grant/实际事件不导入。5新/134相关离线通过，完整回归进行中；原Master/63不改，正式genesis/production/model/private/social0，First-Life/Beta不升级。见docs/nana_real_living_integration。


### First-Life Real Living Integration · OFFLINE final / 2026-10-27
源码995731b；实际全仓1595 passed/0failed/12skipped(11live screen＋E12)371.63s，5新/134相关通过，首次provider config缺失两处失败保留并安全修复。新Core244files/209sourceassets双构建一致SHA a9b750c09350b1b9857a62d071677d331a059e09939cd28454fccdca863f4b5d，qualified本地Python3.12.14/SQLite3.53.1隔离安装新模块导入通过；不重编或冒充旧Docker镜像。独立工具包含预检/hash计划/原B1；新API/native接线说明与真实体验清单齐。仅OFFLINE_PASS，REAL_PROVIDER/HOST/ANDROID/FIRST_LIFE不升级，正式genesis/私人导入/社交/生产0，CotEX/apps和HostOperator保持独立。下一主线依真实operator回执与明确激活授权，用同一canonical home完成手机＋一次PROJECT模型＋真人连续体验；不再重造架构。


### EXECUTION_CONTEXT_V1 — paths, UIDs and authority are namespace-scoped (2026-10-27)
[用户任务＋实际源码缺口，S4/S5/S7 Advanced] 明确ExecutionContext来自受信任执行层的内核metadata，TargetBinding为可信宿主显式配置，标签/UID0/用户名不构成HOST或执行权限。相同路径必须以context/dev/inode与时间区分；UID999只在其user namespace内解释，父层map不自动等于物理host。mountinfo不证明跨容器持久化或自动路径翻译。
复用原Kernel/Store/Grant/Manager/Verify，prepare原子绑定action目标，dispatch先claim再效果；UNKNOWN不换channel/不重发。只有已授权且尚未dispatch的通道选择可按HOST_OPERATOR→SSH；不建通用shell/第二planner/权限系统。原C继续原Hands，增强其namespace/dev与peer检查；不放宽sealed realization。Host Operator/SSH由已有可信认证adapter显式注入，本轮无真实绑定不虚称可用。source metadata新鲜度5s，不扩Action/Grant/Lease时限。
First-Life继续优先，不改Master/63、既有合法自主能力或现有生产。新host_probe需要同版安装Core，旧镜像不自动热更。


### Execution Context V1 · offline qualification final (2026-10-27)
[实测，runtime9bc301c/operator CLI7c842f4] 原Kernel/Hands/Manager/First-Life/Precision保留；50focused、118相关通过，完整1645passed/0failed/12skipped、378.07s（11live screen＋E12）；full后仅CLI拒绝来源metadata补齐，实际subprocess1PASS0.26s，运行时源码不变。249files包双构建相同SHA9bf5e4433c957fbf055b546cc1d4500c879a208b6629665bfdd480b6b97f3740；实际离线安装/隔离-I导入/本地metadata通过，无身份创建。仅OFFLINE_COMPONENT资格，跨namespace/host通道为合成fixture，实际宿主通道/部署未运行，unbound请求明确NO_TARGET_CHECK_PERFORMED，不冒充宿主文件缺失。失败记录保留；Master/Matrix/fixed63逐字不变，schema13/43表、前端不变，production/provider/private/social0。First-Life原主线继续，非新增Genesis/手机前置门。见docs/nana_execution_context_v1及artifacts/execution-context-v1。


### First-Life Unified Release (2026-10-27)
[H Advanced/既有First-Life发行延续，不新造Core] 核对无已开始的重复release后，从9217e3f完整继承RealLiving7a1bce9、ExecutionContext；不重复开发业务。原合格Debian13 image上离线安装新Core，实际SQLite3.51.3/Python3.12.14/OpenSSL3.5.7 UID999验证；新统一image de899852...。实际四卷、只读SDK、API十页/原C离线chat、杀BFF自动恢复、容器重建同ID epochs2→3→4、backup/B8restore/旧source fence通过。不是正式Genesis/生产部署；新Provider与context import通过，不访问模型/私史/旧QQ。完整镜像导出交接及部署说明见docs/nana_first_life_unified_release；初次磁盘不足失败保留，不降低门槛。原1645/12skip按相同runtime源码继承，不冒称新全仓运行；Master/63不改。


### Unified Release expanded user mission / checkpoint (2026-10-28 CST)
[同一First-Life Unified Release，不新开竞争版本] Core-only afb24ba实际推送完成，已有image/SDK/恢复资格保留；用户现明确将ea1e225完整V3、Provider/backup native API及Host Operator OpenSSL/Genesis入口修复合入唯一交付目标。云端12/13、OPENSSL_3.3.0错误与PID/CapEff为用户报告，尚未本地核验，不能将镜像导入PASS冒充真实Operator13/13。当前Core-only+V2Web不是最终V3产物。详细用户任务及未完成项见docs/nana_first_life_unified_release/UNIFIED_MISSION.md；计划北京时间10月28日07:00回顾后继续同分支独立开发，实际automation创建结果以工具确认为准。Master/63不变，正式C-only Genesis授权不扩张，本会话不执行生产/私史/旧writer/付费。


<!-- Imported additive V3 branch history ea1e225; current release status stays at unified header. -->


### Nana Space V3 · independent frontend extension / 2026-10-26
[实测/Advanced，S2/S3/S4/S5展示＋Platform/Shared Life/Governance横轴] 最新First-Life a07e906本地远端一致后创建独立dev/nana-space-v3-cotex；不覆盖部署分支。真实V2 surface重做为生活首页/小房间、聊天、模型和记忆中心、设备/备份/设置；复用原投影/Memory WITHDRAW/Manager/Host/配对撤销，不新Subject/Store/Loop。11预设≠协议资格，模型编辑/偏好/纠错导入仅内存草稿，B1无PC回执不称DR。修异步路由/配对码/注销/隐私晚回包；UNKNOWN仅原receipt GET。41单测/36合成浏览器及4视口120%字号、实际Core浏览器三尺寸和39相关回归通过，原始失败保留。APK同包名/原debug签名升级300，最终交付收口；无production/paid/private/social/genesis，bwrap BLOCKED，Master/63/First-Life NOT_READY/Beta NO不变。见docs/nana_space_v3/。


### Nana Space V3 · delivery sealed / 2026-10-26
[实测/Advanced frontend，非生产] source fde9074；APK4790932bytes/SHA02d85e568195d478de2b515ac45bf6278b3a399c262bf80841091ff30d8d0160、life.nana.space.dev/300，原V2证书完全一致，v1/v2签名与41份Web assets逐字核对通过；Web608679bytes/SHA60a15bb9e27e5288991666ce3e31adb037c1bc594ccc59998d6e287453917ca8双构建相同。最终41unit/36synthetic-browser/3actual-Core-browser/39related/1native-unit全过，lint0error15warnings，首次失败记录保留、不称新全仓。32截图区分synthetic与原Core，source manifest109文件。云端部署分支a07e906不变，Master/Matrix/原Core/API/Keystore字节不变；模型/记忆写入与B1状态待接线，实机/human/正式Cloud未升级，genesis/C-D-E边界原样保留。交付与最小集成见docs/nana_space_v3/HANDOFF.md；无新授权请求或生产操作。


### Unified First-Life V3 final deploy handoff · 2026-10-28 CST

SUPERSEDES仅此前Core-only部署指引，不覆写历史资格：发布唯一最终Core3665+V3；Genesis检查与Core使用相同Debian匹配库/私有前缀，在container执行，host标准库adapter不加载私有_ssl。原checker及批准参数保留，互斥flag最小修复，不发明13门。新slot/8149封条与原runtime/6565并存；host config只输出新提案且保留身份/lineage/角色/原审批；默认Compose不激活。角色/UI配置不产生模型付费权限，UNKNOWN不重发。Master/Matrix及C/D/Store/Loop不变。

证据：docs/nana_first_life_unified_release/evidence/final/qualification.json；交接：CLOUD_DEPLOY_HANDOFF/README.md。


### S2 长期保持度并入 First-Life · 2026-10-28

保存≠检索≠准确回忆；未开展评审≠无法回忆。重要共同经历需原合法保留路径的真实来源及以后实际影响。采样不读正文、不checkpoint/修剪/建Store/开第二Runtime；物理WAL收缩不等于遗忘。虚拟时间/离线测试不冒充长期陪伴，原固定发行物不为本验收增项重建。
证据：docs/nana_first_life_unified_release/s2/；工具：tools/nana_first_life_unified_release/memory_retention.py。


### Android 配对按钮修复 · 2026-10-28

配对协议的24–128长度及原生/服务端检查不放宽。去掉按钮的无提示内容禁用，改为点击后的明确四字段错误；trim边界空白，提交中禁用防重复，保留UNKNOWN不重放/Keystore/身份检查。
证据：docs/nana_first_life_unified_release/pairing-fix/qualification.json。


### 配对协议一致性紧急核验 · 2026-10-28

配对码须由同一运行BFF登记，外部随机生成或padding均无效。保持256bit CSPRNG/TTL/单次/手机名称/角色/CSRF/Keystore，签发不做blind retry。原代码一致时不为兼容19码改安全合同/正式Subject或Genesis。
证据：docs/nana_first_life_unified_release/pairing-protocol/。


### Living Release V4 — unified continuation / 2026-10-28

[用户完整任务/源码核对，H Advanced] 从本地远端77a09e2一致、干净工作树创建dev/nana-core-living-release-v4-codex，继承9217/7a1b/ea1e225/3665及302配对修复。统一V4不重复造Core，任务快照及真实缺口见docs/nana_living_release_v4/。Master/63标准和历史资格不改。30845fb未在仓库取得、无真实宿主访问，用户报告正式Genesis/现场状态不以旧文档否定。后续以原C/D/Memory/Provider接线及实际发行安装为主，不以审计替代施工；私史/付费/外发/正式切换单独授权，bwrap仍BLOCKED，First-Life/Beta不预先升级。


### Living V4 — actual integration checkpoint

修复：原Router无dispatch inspect/当前运行Resolver readiness；双阶段原预算前检与精确REJECTED；手机显式共同经历保存直通原Person-Self；原生安全凭据输入→host内存Resolver→sealed memfd→原child，独立角色/配置/付费边界保留。补本地设备语音入口及可见来源节奏，原appId/Keystore不改。117相关Python实际通过21.81s；44前端单元通过，最终Web/APK及新镜像继续构建，手机/模型/生产未验收。只读Docker API工具实际可用，无Docker CLI也可核既有服务；本地旧镜像受限verify exit0，非云端。保留首次夹具/绑定常量失败。无新Provider调用/私人导入/生产切换；不以此升级First-Life。


### 2026-10-28 — Living Release V4 integration checkpoint

V4: distinguish absent config, bound credentials, local readiness and real model qualification. Bilibili metadata is not watched experience. Operator ABI verification is a second phase; no staged tree may falsely become READY_FOR_SWITCH.


### 2026-10-28 — Living V4 verified development delivery

V4发行与产品资格分开。独立9737条新封条；新镜像SHA相同Python别名改为同venv符号链接，实测全部三版本ABI/prefix，旧镜像/封条不改。内存凭据不冒称vault；公共视频元数据不冒称观看；readiness不冒称真实认知。


## 2026-10-29 — Living V4 final integration checkpoint

D-V4-FINAL-20261029：保持同一V4与唯一Subject；Provider配置/密钥均宿主本地，AESGCM只防误泄漏及其他UID，不宣称抗root或同时盗取key+cipher。新投影必须求交binding scope/entity/privacy。关注来源按完整支持保守标记；外部模型/平台文本不授Grant。平台执行仍由原Manager/Grant/Kernel、原canonical激活与独立Verify约束，不改旧审批摘要。


## 2026-10-29 — V4 final credential/version hardening

D-V4-FD2：撤销/轮换必须让旧运行实例的后续选择失效，不能只删父进程key而允许重新启用profile复用旧凭据。匿名FD显式绑定宿主vault epoch/cipher digest；旧loader不降级为无守卫明文映射。旧二进制回滚须在停止健康Core前检查FD合同，空vault可离线兼容。


## 2026-10-29 — V4 delivery checkpoint

D-V4-DELIVERY-TRUTH：分别绑定运行源码c8、UI/Native源码af、实际安装6935项封条、不同测试源码和原失败。保留旧13/af精确归档与独立新SDK封条；兼容性不足先于停止健康服务拒绝，不修改旧审批、Store或历史资格。


## 2026-10-29 — Living V4 continuous 402 checkpoint

D-V4-402：旧档案只作为限时审批下的UNASSESSED SEMANTIC legacy claims进入原Memory，不成为EPISODIC/身份/Grant；旧解码器pre-stop拒绝。B站每个搜索/选择仍需原C+Kernel，后台为用户显式订阅的无正文动态提示，不冒充Nana已投递语言或即时推送。


## 2026-10-30 · Living V4 原owner平台链收口检查点

继承e8ff61d，原C/Manager/Grant/Kernel/Verify接通QQ和B站有限绑定回复；签名入站只传message ID，独立读取核对，不授予权限。手机CAS通道与原生安全凭据入口已实现；397相关回归通过，402 APK构建通过。初始失败、UNKNOWN停止记录及边界见 `docs/nana_living_release_v4/evidence/platform-402/`。未做真实provider/账号/私史/生产；私密前端授权路径和最终匹配发行继续，未宣称CODE_COMPLETE/First-Life/Beta。Master/63条/One Subject不变。


### V4 closure item 1 — actual installed image / recovery

f944e9e image607890d: actual install, repeat zero persistent changes, six mounted private SDK imports asUID999 and actual Pillow PNG decode PASS. Missing clock.py in owned test slot rejected with exact path/hash and no repair. Original same DEV Subject actual SIGKILL/recreate epochs2→3→4, B8 restoration/old-source fence/old-Grant revoke PASS. No production, actual Provider or real phone qualification. Temporary harness input/permission errors retained in evidence/closure-402 summary. Continue item2 explicit private-context scope, then item3 final matched export/delivery; no unrelated business regression repeated.


### V4 closure item 2 — explicit personal context

Additive PRIVATE_CONTEXT application role intersects host binding; no implicit scope gain for old paired devices, no Core Grant. Original Surface consent/provider/privacy/budget still required, SECRET denied. Original Memory/history/Inspector read and withdrawal are per-device; source/scope changes withhold cached receipts. Compatible runtime marker rejects unsafe downgrade before stop. Actual synthetic original-Core retention/restart/withdrawal and narrow-device denial PASS; related32, frontend56, actualTLS browser4 widths PASS (separate overlapping scopes, not summed). Browser first failures found draft checkbox state reset on ChatPane remount; choices now belong to the same ephemeral parent draft. Evidence private-403; actual personal data/provider/production0. Android403 follows original appId/signer; final build/export next.


### V4 403 development delivery
三项工程工作已在隔离开发环境完成：安装恢复、显式个人范围、匹配发行包。最终源码 ffa24b7；实际安装/重复/损坏拒绝与 DEV 同主体恢复通过。真实宿主、付费 Provider、私人历史、真实社交、手机及真人/正式24h仍未验收；First-Life NOT_READY，Beta NO。详见 docs/nana_living_release_v4/qualification.json。

### V4.0.3 daily-use and deployment follow-up — 2026-11-01

Issues #2/#4 remain OPEN: this development checkpoint is partial, not a production installation or release qualification. New configuration defaults use a 120000 ms per-model timeout (configurable up to 600000 ms); existing host/route values are not silently rewritten. The conversation control and web/native clients allow two sequential calls. A dispatched UNKNOWN remains reserved and cannot be replayed; a distinct request may proceed within existing cost/privacy limits and a two-live-worker bound. Background/media paths still have their existing conservative fences. No billing reconciliation was implemented or implied.

New hosts obtain the existing shadow-only Nana Space binding; existing host configurations need a separately reviewed migration. Private life.json reports owner/mode errors rather than silently changing permissions; migration remains outstanding. Future release tooling checks a separately pinned OCI manifest, config, descriptor sizes, all layer hashes and uncompressed diff_ids before accepting the daemon's alternate image ID. The original 4.0.3 ZIP is unchanged. Isolated uid-999 Debian testing loaded OpenSSL 3.5.7 and SQLite 3.51.3 from the private runtime; this is not a rebuilt image or host validation.

Open: Gateway may still run its baked release when Supervisor changes the active release; no automatic rollout/host fix was made. Existing ArchiveImportService is a separately approved identity/lineage/privacy-bound ingress, not the generic RealMemoryIngress flag; no private archive was imported or sent to a model. No real Provider calls, private history, production configuration, current Subject/Store/Vault, or QQ/Bilibili operations were changed. Android native timeout source changed, but a new APK and real-phone test have not been produced. Cloud T2–T4 is user-reported and was not independently checked here. Follow up with gateway version selection, safe config migration and actual deployment validation before closing the issues.


### Next Experience development — 2026-11-05
Advanced Growth / Platform + Shared Life. Original architecture and 63 criteria unchanged. Current work: App-native password login, existing device identity/Keystore, model quick setup via original CAS commands, authorized projection explorer, chat search/quote and original static art. Web/auth/browser tests passed within documented scope; no host/public-HTTPS/real-phone qualification. Full task remains IN_PROGRESS, not First-Life READY. See docs/nana_next_experience/STATUS.md for implementation and remaining gaps.


### 2026-11-06 · Next Experience / continuous ten-domain refinement
Continue the same product task; uploaded V1.3 design retained in docs/nana_next_experience/task_inputs. First fix actual phone chat layout and plain-language UI, then remaining original product flow, then highest-value original Core cross-domain refinements. No duplicate total plan or migration owner; cloud memory migration untouched. Mobile browser layout >45% message-area checks passed at four sizes; live phone result pending. No frozen framework/criteria/authority change.


### 2026-11-06 · long-term context/memory/latency addendum
Accepted as a supplement to the existing ten-domain refinement mission. Baseline → bounded implementation → same-condition quality/resource comparison. Reuse ContextAssembler/MemoryService/MaintenanceService/Router/S8; retain emotional/autonomous/learning quality, provenance and privacy. Synthetic 1k/10k/100k/larger benchmarks and authoritative live Store/index mapping are separate evidence. Initial code search does not prove a live FAISS binding; host mapping remains unverified and cloud migration untouched. Details and measurement distinctions: docs/nana_next_experience/task_inputs/LONG_TERM_CONTEXT_MEMORY_ADDENDUM.md. No performance gain, live audit or total completion is claimed.


### 2026-11-06 · measured long-lived memory refinement
Original-Core synthetic corpora measured at1k/10k/100k/200k. Fixed SELF selection before bound, added rebuildable physical lookups, and adopted rare-term ranking with dense/small-scope fallback. Alternating same-Store200001-row comparison: exact context equality; retrieval P50 508.46→133.85ms, P95 526.23→146.02ms; assembly P50 678.06→298.79ms, P95 777.85→316.84ms. These are local English lexical fixtures, not live FAISS/semantic/human qualification. Context units remain UTF8 byte estimate; provider calls0. Preservation of private-source withdrawal, original dialogue and strict portable schema is tested; initial schema-drift failure retained and fixed by stripping exact known physical indexes only from export copies. Source digests/evidence in docs/nana_next_experience/evidence/context-memory. S8 policies/production not auto-replaced; cloud migration untouched. Next Experience and ten-domain mission remain IN_PROGRESS, not complete.


### 2026-11-06 · continuous product/refinement / renewed S8 learning

Use new original C-endorsed work for later checked gaps, never replay old UNKNOWN or override ACTIVE lessons. No second learner/affect authority. All outstanding software work remains part of the same mission. Evidence: `docs/nana_next_experience/evidence/growth-renewal/`.


### 2026-11-06 · Next Experience product406 continuation

Keep catalog GET separate from inference/paid qualification, and memory POST search separate from context/semantic retrieval. Gateway follows registered sealed source only at process start; no hot code update, second process or web artifact rewrite. Keep independent phone/host review gates.


### 2026-11-06 · S8 material novelty boundary

A failure may reopen a need, but it is not itself new training material. Re-running unchanged practice/holdouts after suspension is prohibited; candidate-visible new material plus original C endorsement and a distinct later checked failure are required. Do not use final-answer edits to authorize an experiment. No new learner or production strategy adoption.


### 2026-11-06 · complete batch regression / continuing native affect integration

Reuse Fish Heart design ideas only after mapping to current native Appraisal/Concern/Runtime/Learning. No nine-value affection system, punitive silence, adult functions, second Store or privileged prompt authority. Full-regression source6f2a491 and APK client source480d45f are explicit ancestors; do not confuse artifact and production status.


### 2026-11-06 · continuous native affect / product integration

Fish Heart只借鉴设计思想并保留MIT归属，增强原S3/S4/S2/S6/S8，不造第二情绪/Store/Loop。重复解释不算独立经历，短期念头淡出不删除关系或历史；明确休息只写delivery边界，源于模型的提案不能安装它。状态更新走原Memory纠正及真实事件时间，旧无时间来源不补造。


### 2026-11-07 · resume matched406 / same continuous mission

406只交付精确cc3dc33匹配APK/Web/Core及候选隔离说明，不改既有474MB V4.0.3包、不覆盖生产。Docker校验替换entrypoint、限定新槽和scratch、不挂载canonical数据。旧全回归与新受影响资格按实际源码分别记载。


### 2026-11-07 · real original-Store notes / ongoing refinement

用户备注属于明确保留的USER_STATEMENT，不是Nana亲历、世界核验或身份/权限修改。只允许更正这类备注；来源/经历/Archive/SELF不能被此接口重写。沿用原Store/MemoryService/correction/Privacy/Manager/Surface/ledger；未确定写入结果不可再次POST。


## 2026-11-07 — 同一主任务407回归修正

同一raw source的语义修订可因原session验证的world_stamp变化重交原C，但不能增加独立encounter；只有纯关注且无待决UNKNOWN/效果/技能/目标时允许。原兴趣来源去重和全部执行权限不变。


## 2026-11-07 — 匹配407实际发行收口

工程状态摘要遵守原ProjectCurrentState固定上限8证据；改为7个代表入口，全部历史留在原账本，禁止为容纳增长而提高上限。部署交付新增独立只读组件一致性工具，不赋予生产权限，不将手写frontend_source当作独立源码证明。


## 2026-11-07 — S2有来源备注进入真实Core对话链

理解资源可提出至多8个瞬时检索词，不持久化未授权聊天/查询，不能给权限；原MemoryService只查既有当前用户备注，最多4条/默认100ms，超时只记检索缺口。模型表达数据按本次对话隐私封顶，不改变主体自身可思考范围。原C、人格关系、S8和授权全部保留。


## 2026-11-07 — S2实际冷连接瓶颈修正

新增memory_user_note_lookup仅为原Store可重建物理索引，无新表/Schema13/主体语义变化；沿用已知DDL导出清除/导入重建及替换拒绝。保留100ms、原隐私/来源校验，索引失配只让可选召回标记缺口，不升级执行权限。


## 2026-11-07 — 原上下文丢弃候选的实际开销优化

Pinned-only对话直接读取明确来源与合格备注，其余Self/关系/承诺/经验/语言投影走原路径；不把将丢弃的128条泛化候选先读入。性能比较只声明证据字节相同与装配延迟，不虚构模型token节省。


## 2026-11-07 — 兼容407的S2服务端实际交付

本批明确作为兼容既有407客户端的服务端补丁，不伪造frontend_source==新Core，保留原407三组件及其清单不变。无须为这一服务端改进重装APK；真实激活仍走原授权/封签/Supervisor路径。


## 2026-11-07 · Next Experience relationship continuity under growth

Relationship projection reserves bounded original-source retrieval for existing preference/norm/boundary/open families and episodic/relational rows; it does not rank all arbitrary semantic facts as relationship history. Max128 distinct IDs; exact privacy/current/source rules and original C remain unchanged.


## 2026-11-07 · Next Experience408 explicit connection retention

Kept original retain_shared_life per-message contract. Added opt-in PROJECT retention for current authenticated connection only, no device persistence; PERSONAL still separately consented. Parent handles one-shot clearing; removed duplicate child reset. Logout/run/privacy/role/error/capability loss clears mode, original UNKNOWN GET-only behavior retained. Frontend59 tests passed3.51s; responsive request-body/lifecycle checks and APK receipts in docs/nana_next_experience/evidence/chat408. Android408 same appId/signature,42Web assets equal; real physical phone/model/cloud remains unrun. See CHAT_MEMORY_FLOW.md.


### 2026-11-07 · Actual408 candidate published without production activation

Core/frontend f712136, delivery ced522e. Three remote downloads SHA matched; final279-file archive extracted/offline installed, original BFF/chat/notes/backup/sameDEV restart plus2local fixture context calls passed.17 original G/growth tests also passed. Same signed APK408 and42matchingWeb files; no physical phone/cloud/model/human/cross-day qualification or new full-suite pass. Original task remains active. HANDOFF_408.md/evidence/chat408/qualification.json are current receipts; next continue full wire/model-aware context budget, originalS8 retrieval feedback and remaining product integration, with real-host/provider/human gates separately pending.


## 2026-11-07 · Original model byte ledger uses exact outbound body

Same Next Experience S4/S5 refinement. Reuse one pure OpenAI body serializer for exact preflight input+unchanged bounded response+overflow probe reservation; preserve cost/call/UNKNOWN/no-retry, privacy and all non-OpenAI transport bounds. Recheck before dispatch, legacy reservations not refunded. Wire contents unchanged; actual tests and tradeoff in WIRE_RESERVATION.md/evidence/wire-reservation. CPU overhead measured, no token/billing savings claim.408client unchanged; server patch awaits final installed artifact qualification.


## 2026-11-07 · Explicit current delivery compatibility check

Existing verify_delivery.py retains strict same-source APK/Web/Core verification for each original artifact set. Added explicit CURRENT selector verification for a separately qualified server-only patch: pinned manifest hashes, all file hashes/paths, actual Core source, declared API/client version, identical runtime/schema/host-binding contracts and optional-feature superset.12positive/negative tests passed; actual missing API contract declaration correctly rejected before metadata completion. No runtime, phone or semantic qualification inferred from consistency. No Core/APK rebuilt for this external tool. Prevents ambiguous old/new package selection while retaining rollback files.


### 2026-11-07 ·408-compatible server byte refinement delivered

Source de08f8f, delivery9c54efb, Core279files/14993379bytes/SHAfbfe1399…6741f; two builds equal, actual extracted/install/original BFF/note/backup/sameDEV+lineage recovery and2local fixture phases passed. Actual HTTP request lengths and pre-reservations independently agreed. Same408 client, no second phone download. Current selector checker verifies actual sources, original client set, runtime contracts and retained optional features;12positive/negative checks passed. Actual remote Core SHA matched. No fee/token/production qualification upgrade. Original task continues; S8 retrieval-feedback learning/full model-token budgeting/streaming and real-host/human gates remain open.


### 2026-11-07 · Daily defaults / readable quota code continuation

New-host-only128daily/64hour/128provider preset stays within original128-call ceiling, cost0/no credential/host/privacy authorization; old/missing/explicit host settings stay unchanged. Readiness exposes original counts/ceilings/reasons without writes; server operational notices use plain Chinese while exact codes and UNKNOWN reservations remain.27 related checks14.47s and CLI help passed. This batch is code-tested, not yet a new installed candidate; current published client408/Corede08 remain unchanged. See DAILY_DEFAULTS.md. Continue originalS8/S3/S2 work rather than requalifying old G/Fish mechanisms.


### 2026-11-07 · Original S8 retrieval practice in the same Next Experience task

Source-backed retained-note lookup failure now offers an optional original-C opportunity, original-G practice-only competition/independent evaluation/transfer, source-bound method reuse and counterexample suspension. Original S3 need can settle after checked later reuse; no new learner/memory/emotion authority. Ten focused checks2.73s pass; initial faults/resource exit137 retained. Related/installed artifact qualification pending, no live-model/phone/production claim. See RETRIEVAL_GROWTH.md/evidence/retrieval-growth. Existing408 APK/signature and original framework/63criteria unchanged; remaining whole mission stays active.


### 2026-11-07 · Installed original S8/S2/S3 candidate delivered, same408 client

Runtimef03fcbb, tool edfd685, artifactc8d5934.139related checks passed;280-file archive15001321bytes SHAce518a23e3ec431b22f1b2a4e7441c84f57770ea2f65a133d9ac100c738ff25e, two builds equal. Actual extracted/offline BFF/ten views/notes/backup/sameDEV identity+lineage restart plus original-G study/later different-note RENDER/source withdrawal passed with6loopback calls/real0. Initial source/fixture/resource failures preserved; external checker6-call option leaves Runtime limits unchanged. Daily defaults391ab0d included, old settings not rewritten.408APK unchanged, directNana-408.apk link restored; current selector pins new server patch. See HANDOFF_RETRIEVAL_GROWTH.md and evidence/retrieval-growth. Model-specific full token framing/streaming/product remainder and live host/phone/human/cross-day/vector gates stay open. No production change or total-mission completion.


## 2026-11-07 · Same-task409 runtime/product continuation, not completion

Original owner/C streaming, responsive existing restrictive management, absolute JSON/SSE attempt deadlines, same-model full-request tokenizer binding and confirmed-byte admission settlement implemented; commercial tokenizer/real model/phone/human/long-life qualification remains unrun. Original256receipt hot set can privately archive body-free terminal/UNKNOWN keys without lifetime chat exhaustion; same-host restore retains root AND whole archive, old binaries fail closed. No production/Iris/identity/Framework/criteria changes. STREAMING_AND_RUNTIME_409.md and evidence/streaming409 record code/tests/failures; final artifacts/full regression/installed409 remain pending actual execution. Continue all original software and ten-domain work.


### 2026-11-07 · Same409 final quota propagation, current runtime authority retained

The routed session still inherited24 despite the host's explicit larger allowance. Pass exactly original Runtime.max_calls_per_day (0denied;2/26bounded;no model calls); no fee/hour/privacy/refund changes.62router/budget/stream/framing and20daily/media/source-growth/network checks pass. Full2006/12 remains tied to37e46b5, before this narrow delta. Clientb873a4a/409same signature and42asset equality retained, native code unchanged; final artifact source will attest identical frontend tree rather than rebuild unchanged APK. Framework/criteria/production/Iris untouched; same entire mission continues.


### 2026-11-07 · User living/dream/storage/token supplement merged, same mission

原任务和软件继续，409是4.0.9修复件，用户明确禁止因后端适配逐次重打APK；后端全完成后仅一次性处理必要客户端改动。新要求输入摘要和当前差额见 LIVING_MEMORY_UNIFIED.md/task_inputs。首先实测原无输入虚拟1h360永久事件/1171456逻辑增长/1715248family文件长度增长，候选原C检查点与空SCAN操作计时1事件/0逻辑增长/313072family增长，模型0；31原相关及4新增验证通过。并非真实1h驻留或生产改善，不删旧链/经历/动作审计，不新建主体/Store/循环。梦境价值选择/未来回忆、48h候选、弹性容量与冷档完整性、真实usage账本继续施工；真实云/模型/人/手机/跨日资格分列。


### 2026-11-07 · Same task soft recent window and actual rendered source selection

原PersonSelf/Assembler增加task相关软48h候选和逐字excerpt/offset，重要旧源可优先、SQL privacy/active过滤先于LIMIT。真实原C/本地传输请求验证发现并修复最终omission元数据挤掉全Self的预算bug，保留source-backed单段与稳定self降级，不抬预算。70相关检查24.19s通过，含72h虚拟重启、实际RENDER和撤回；初次失败留证。不是生产/真人/长期资格；409APK保留不重打。继续梦境/存储/成本原任务。


### 2026-11-07 · Same backend task: original-C consolidation, capacity and usage

原Maintenance jobs增加可重启增量/有界周回看、带时间和offset的来源片段；原C可以REST，条件未变不重复判断，条件变化后恢复；实际后续RENDER、纠错/撤回验证。原Store派生索引支持原源检索，单摘要claim family避免规模退化。StorageGuard新宿主可选实际磁盘/备份余量规划，旧FIXED/显式限额/异常速率/停止锁存不变；原资源账本从已接受usage分列真实提供方/fixture/缺失，bytes不冒充Token。248相关检查62.90s通过，源码指纹运行前后相同；全部初次失败保留，不称全仓/云端/手机/真人/商业Token资格。409APK/Web源码与b873同tree，完全未重打；最终后端包仍待整个后端收口。LIVING_MEMORY_UNIFIED.md及evidence/living-memory-unified记录实现与剩余冷归档/实际物理回收/S8反馈/真实绑定门；主任务继续，Master/63criteria不变。


### 2026-11-07 · Cold history uses existing managed backup, no history eviction

原Store.backup/PrivacyJournal新增可校验冷回读维护适配，停止态原CLI backup --cold可用；副本仅压缩已登记可重建索引，原链和主体不动、隔离标志不变，当前原源/权限/纠错/撤回始终优先。20项相关检查3.66s通过，真实分配占用/首次连接fixture失败留证。总磁盘不因多一副本而减少，未声称主库回收、生产恢复或DR；源码白名单已含新模块，后续同一Core安装验证继续，APK不重打。用户要求减少重复审核，本批只检查直接变更范围，不重跑无关全仓。
