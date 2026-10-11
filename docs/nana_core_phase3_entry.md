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
