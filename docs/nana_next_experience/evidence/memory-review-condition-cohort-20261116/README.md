# 暂停回看的关切群条件

基线9c8fe1e/Brain248，同一原C/原Store/原D；S2/S3/S4/S6 Advanced定向改进，不更改冻结标准或原Foundation资格。

## 真实差额

原条件摘要仅保留按ID排序的129个关切头部。原C明确REST后，新建第131条或撤回第130条，已保存的关切群发生变化，但摘要不变。original8.txt：真实旧3fail5pass（2个尾部变化、1个重复查询计数）；原probe的普通opportunity并不是maintenance_slice，单独调用它不会排队，因此candidate_probe.json虽显示摘要已变化，job仍PAUSED。不能把该探针当作正常D联调成功。

新代码在原精确scope/entity/privacy/current过滤下，复用memory_family索引的字面concern.前缀范围；保留129样本，补count/最大创建event.seq/最大updated元数据。仅符合条件的关切创建序号参与，无关的全局事件不会使其变化。既有候选验证/来源撤回/原C选择与资源门不改，既有普通回看仍可零模型。

final9.txt：9passed1.28s，最后增加正常Runtime.step入口复验。130条关切后，新增/撤回样本外尾部，停机重开同身份→原Runtime.step BOUNDED_MAINTENANCE_SLICE→原job WAITING/单次排队；重复maintenance_slice不重复排队，cognitive_requests/actions均0。scope/实体/配置外PERSONAL/非精确前缀反例不解除暂停；只读检查不写Store。另3候选同scope每slice条件只读一次、下一slice重新读；原candidate安全点真实withdraw来源会使本轮缓存失效。此安全点由测试包装控制发生次序，真实Forget/候选/Store未替代。

final52.txt：52passed17.64s，含前版本9用例/原8选择、梦境来源纠错撤回、维护、私念资源、进程与中断恢复。之后仅将尾部的直接maintenance_slice改为正常Runtime.step入口并重跑final9；不把重叠结果相加或称后续完整52重跑。原正常调度前台优先/暂停/资源门未修改。

## 成本与限制

没有新增Provider调用、阶段、Prompt字段、索引、表或持久缓存。每次至多16候选，在同一slice按scope复用一次聚合；候选隐私安全点写入及旧C周期恢复后清缓存，跨slice不保留。原PAUSED旧摘要第一次比较会有一次重新考虑机会，不是重派外部动作或自动采纳。

metadata_benchmark.json是隔离内存SQLite元数据夹具，不是实际Core/20万库/完整检索基准。7样本中位：100k头且131关切，旧样本query10.363ms、补充聚合0.105ms；100k全关切旧query13.598ms、聚合38.261ms。聚合成本额外存在，不能把两条查询当互相替代或宣称新完整方法更快；新样本也用了前缀索引，但未测其完整端到端收益。实际Provider Token/费用未知，模型0，无付费调用。

count/max不是任意变化的完整版本：在相同时间戳、不改变count/最大seq/最大updated且不在129样本内的原位改动仍可能遗漏。私人Record版本不在此条件群；未证明它必须让所有已暂缓摘要重判，不泛加全局私念游标。旧有限样本本来也不是完整变化版本，本批只资格新增/撤回尾部差额。若后续真实反例要求完整版本，沿原记录/索引最小扩展，不建第二状态权威。

## 首次失败及资格

fixture-first：陌生entity未原绑定、默认可读PERSONAL的假设错误，按MemoryService.entity与显式窄runtime配置修正。related-path-first仅测试文件名错误/未运行；safe-point-order-first因虚拟时钟相同timestamp不保证插入顺序，按实际消费者访问顺序断言第一PAUSED/第二WAITING。生产行为及边界未为这些夹具失败修改。

独立CI43769066695/job132980872350实读9c8：746passed3warnings346.75s，targeted；full/oldSQLite/portable/client均SKIP，非本批CI或全仓结果。回退本基线living.py，无schema迁移。CURRENT266+409和已下载离线安装的9a候选不变，该包不包含245–249；无新APK/真实模型/手机/QQ-B站账号/生产/自然度/实际长期资格。

下一继续原商业C内情感/多动机/原G迁移及B视觉固定交接；PRIVATE版本/策略因果先核对真实消费者，不把每个变化强制成Goal或重复模型。原A–H完整继承。
