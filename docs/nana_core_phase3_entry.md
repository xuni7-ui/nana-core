# Nana Core Phase III Entry 工程记录

基线 29872608b7b82fcca4a89a3be98fda8e8c65337f 与私有远端 dev/nana-core-v1-dev-validation 完全一致，原工作区干净。旧验收 final_junit.xml：227 pass/0fail/1skip，E12 NOT_RUN；main 18bc736d5e37fe3325e514a0e975403df2f97c9f。新分支 dev/nana-core-v1-phase3-entry；原生产/私有资料/凭据读取边界不变。

## M1 公网验收
[实测] 一次明确授权 https://example.com/ GET 经 Observation→ReadingCard Goal/Plan→Grant→ActionKernel→WebSourcePort→PublicHTTPTransport。新增 last_stage 可观察诊断，不放宽任何限制。DNS_FIRST / WEB_TIMEOUT，实际HTTP0、proxy连接0，read UNKNOWN、goal BLOCKED，未取得HTTP状态/正文/receipt。独立核验事件与Attempt持久存在；不自动重试。证据 public_probe.json。不是curl成功替代验收。未关闭TLS/绕过proxy/修改系统配置或使用生产代理。

[实测] 受影响公开传输41项及精确阶段测试1项共42 passed，协议夹具不算公网。当前DNS getaddrinfo 未能在5秒取得目标公共地址；代理TCP/TLS未运行，不能推断代理路径必然可用。

## M2 E12 就绪状态
待本节点核实与保存；不以fixture代替真实双模型。

[实测] M2 环境 spec33/current/enforced：就绪secrets/runtime_variables/outbound_identities均0，无显式开发模型配置。既有S5 prepare/evaluate创建合成冻结快照后运行readiness，E12 NOT_RUN、models[]、calls0、snapshot unchanged。token usage不适用、费用0（没有请求）；没有借用历史生产DeepSeek/当前助手/GitHub凭据。见model_readiness.json、semantic_report.json。真实端点出现后仍用既有顺序with/without和原始proposal评分，不重造评估器。

## M3 Iris 映射与适配
[源码确认/实测] 正式字段映射见nana_core_phase3_iris_mapping.md。14条真实schema合成夹具/11类型；源代码只读核对不复制AGPL实现。36 targeted passed，新7验证缺字段/冲突/错时/无源/summary/inference/KG/profile/ledger等；逐条原始事务+可恢复projection，真实SIGKILL间隙后补齐，无静默丢失或授权扩大。M3已推送ef51373570363ed715cb6eb0732365d4e611e86b。

## M4 最小冲突、迁移演习与影子检索
[实测] MemoryView复用memory_items JSON，无新表。operator语义sidecar只用于user原话（不是旧字段或模型提炼事实），claim key=(dataset,subject,predicate,value)，polarity冲突显式保留support/contradicting memory及原始evidence refs。已知发生时间的较新用户陈述为CURRENT_USER_STATEMENT，旧相反陈述SUPERSEDED；时间未知/并列相反DISPUTED，原始证据永不消失。旧confidence不决定新可信级别。

“事实”是某个供给的原始来源陈述存在；“当前相信”是可撤回、非VERIFIED的解释；“为什么”是来源链、原发生时间与policy1。自传/模型summary/inference不自动升级。MemoryView读取显式synthetic dataset及当前identity，Context裁剪报告dropped ids，保留原artifacts，不冒充完整历史。

实际CLI两子进程：14导入/0拒绝，重启14duplicate；source逐字匹配，原时间保存，KG1 relation两端解析；1冲突组，两陈述均可见；同身份/历史前缀/完整replay一致（仅replay quarantine预期差异）。导入/decision preview/影子均Goal/Action/Grant/Strategy/Budget0。

MemoryDecisionFixture明确接收selected memory context，在原始proposal中引用最新否定偏好及实际memory ID；没有模型推理、没有自动执行。10 targeted passed。memory_reconciliation.json为实际CLI对账。

P7为PARTIAL：old Iris-style lexical+legacy-confidence纯函数surrogate对比，不运行真实FAISS/embedding或生产Runtime。相同query以m1/m2为明确重要证据ground truth，surrogate top1 recall0、Core recall1，contradictions0对2；来源artifact可用率、已知时间数量、context chars、unsupported ID率、dropped重要项均报告。该unsupported率不是LLM幻觉语义评分；真实Iris检索一致性NOT_RUN。影子前后Store snapshot逐字相同，无Goal/Action/预算/Strategy写入。

## M5 主动候选与价值冲突
[实测] GoalCandidate/Initiative复用memory_items.CLAIM、Event、Identity charter、jobs/Scheduler和现有Runtime/ActionKernel，无新表/框架。strict proposal存purpose、intent、evidence refs、need/importance/urgency/confidence/disturbance、user discretion、required capability/resource；提出PROPOSED与评估ACCEPTED/DEFERRED/REJECTED/BLOCKED分离，接受不是执行授权。模型给出的数值是待核实判断，不冒充真实风险识别。

评估记录identity/revision/charter、why/priority/evidence与permission_source，不足优先级可不打扰；DEFERRED/ACCEPTED安排现有wake job但不创建Goal/Action。外部能力不可用则BLOCKED；ReadingCard显式activate再由Runtime/Core校验每一步授权预算，未授权card仍BLOCKED，不能借candidate前置接受扩大权限。Pending candidate/job重启保持；输入重复不重复candidate，冲突key拒绝。

[实测] 22 targeted passed（新3+已有Runtime/learning19）；实际合成场景6/6符合结果：普通情绪低落DEFERRED；非紧急不同意见ACCEPTED dialogue；潜在严重但证据不足ACCEPTED information，不提出外泄；高可信迫切风险、要求保密及无联系授权均允许存提出的external candidate但BLOCKED能力不可用。保密意愿进入记录，不能伪造Grant；contact不是此次可执行能力。所有场景Action/Goal/Grant0、第三方联系0，initiative_cases.json。

[未知] 真实模型的风险识别、价值判断语义和真实沟通能力未验收；没有联系模块/告状模块/场景专属框架。Fixture只证明结构能表达独立判断，不宣称数值可信。当前非reading intent只有候选/调度，不是可执行通用Plan模板。

## M6 模型选择与工程接口准备
[实测] ModelCapabilities描述model id/provider/service_kind/context/tools/privacy/cost/latency/tasks；纯ModelSelectionPolicy只在显式授权的既有Endpoint中选择，重新严格校验元数据绑定与scope。缺匹配BLOCKED，local-only排除remote，不因低成本扩大task/tools/权限，不读取凭据或创建额度，不调用模型。测试只用synthetic声明元数据，不是发现两个真实模型。

P11为PARTIAL：EngineeringPreparationPort遵守CapabilityPort execute/verify形状，复用bridge/codex_bridge.py的TaskSpec/check_boundaries，准备6类操作与固定test argv；仅隔离workspace、exact allow paths、dev branch，拒绝live Core/secret/symlink/越界/main/shell。不调用旧execute_task/CodexRunner/密钥加载。execute明确NOT_ENABLED，verify拒绝无执行证据。已有Core CAPABILITIES/DTO/Grant封闭于reading的3能力，engineering.*真实propose被UNKNOWN_CAPABILITY拒绝；当前不存在可合法授予工程权限的接口，不能套用reading Grant伪装。此次按“先接口+fixture”范围保留disabled，不提前扩建新Agent或绕过行动内核。下一步需要有界registry/args/budget/核验增量后才能真实patch/test/commit；本轮无工程能力自动自修改。

[实测] 51 targeted passed：selector/engineering15 + S5 ModelPort28 + memory4 + initiative4。首轮41pass/1fail为synthetic remote Endpoint夹具漏credential_env，补独立NANA_S5_DEV_SELECTION_FIXTURE名称后保留Endpoint严格校验（未读取/创建key，未放宽授权）。并修复initiative wake两事务间崩溃风险：due_at由candidate创建时持久化，旧candidate按原创建事件时间回推；真实SIGKILL在wake commit之后、状态commit之前，50秒后重启仍同occurrence/jobs1、无Action。最小记忆补充同时期相反陈述DISPUTED及context剪裁不得冒充完整证据的断言；decision preview改为实际Observation/ContextBuilder进入同ModelPort，未增Goal/Action。

M5已保存ba7c86211c6a409218284b872c63b4d9ed132476。新selector/preparation实测摘要model_engineering_preparation.json；源码/测试不含真实credentials或私人资料。

## 公网有限后续诊断
[实测] 主机名DNS阻塞后，为区分解析与连接问题，另一个独立、有新显式Grant的新实验对公开文本 https://1.1.1.1/cdn-cgi/trace 执行一次GET尝试。标准resolver对数字地址两次一致/全球可路由检查保持，既有代理数字CONNECT，TLS仍严格校验IP证书；不绕过代理/沙箱，不关闭校验、不改全局配置。这不是重新派发先前UNKNOWN动作。

该次DNS/代理CONNECT走到TLS阶段后失败，safe_error WEB_PROXY_REQUEST_FAILED，proxy连接尝试1、origin HTTP0、UNKNOWN，无HTTP正文/状态/receipt。具体TLS异常细节原先未记录，不能声称是证书/策略/源站中的哪一个；阶段确定TLS。被动TLS trust元数据tls_metadata.json说明CA store状态但不能据此证明公网握手。当前两个不同目标的有界尝试均无HTTP GET发出，停止公网实验，保留两条未决记录，不自动retry或变造成功。公开response正文/summary不上传Git（此次也未取得）；潜在后续成功只报hash/来源引用。

network_followup_tests.txt：43 passed，包含任意URL不能进入该操作者探针，未知地址被拒且不建workspace。

## Shadow 比较口径修正
初次M4 surrogate top1与Core limit8不适合做召回优劣结论。最终对账已改为相同max_chars8000/limit8、相同规范化输出字段，旧路径不读取Core belief；重要原话recall两边均1.0，旧路径不标注矛盾/Core显式2条。新增断言要求旧路径也保留两条重要证据和matched bounds，未弱化来源/权限/冲突不变量；历史top1数字只是早期实验，不代表真实检索改进。P7仍PARTIAL（没有真实FAISS/Iris parity），最新memory_reconciliation.json为准。
