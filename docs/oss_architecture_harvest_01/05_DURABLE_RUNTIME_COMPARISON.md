# Durable runtime matrix — 机制不是产品成熟度评分

证据标签：S=所读source支持；T=同时有已读test断言（本轮不等于已执行）；D=文档合同；U=UNKNOWN；—=不属于该项目责任。没有数字性能排名。
Nana source [`src/nana_core/presence/runtime.py:113`](https://github.com/xuni7-ui/nana-core/blob/67326d195edd0693d41eacc63fcc00e1c3205bd6/src/nana_core/presence/runtime.py#L113)、[`src/nana_core/presence/queue.py:104`](https://github.com/xuni7-ui/nana-core/blob/67326d195edd0693d41eacc63fcc00e1c3205bd6/src/nana_core/presence/queue.py#L104)、[`src/nana_core/presence/cognition.py:70`](https://github.com/xuni7-ui/nana-core/blob/67326d195edd0693d41eacc63fcc00e1c3205bd6/src/nana_core/presence/cognition.py#L70)。

| 指标 | Nana D-V1 +当前C | YuriOS | Letta Code | LangGraph | Temporal SDK | Anima | tomo |
|---|---|---|---|---|---|---|---|
| process persistence | S standalone dev | S asyncio host mind | S listener/server | S graph invocation, host负责常驻 | S worker+另需server | S sync Mind.run | S agent daemon/cron |
| wake | S durable event/schedule | S bus wake | S queue/cron | S invoke/resume | S signal/timer/taskqueue | S inbox/sliced wait | S cron/inbound |
| idle cost | noLLM，固定poll | noLLM REST+IO | runtime模式相关U | 未invoke无model | 等timer无需model，但服务有成本 | backoff后仍每tick think | 每cron可调用agent |
| model frequency | S NO/LIGHT/FULL+cap | S ACT-on-demand | S turn/worker trigger | 用户graph定义 | 用户workflow定义 | S think每tick | S due turn |
| adaptive cadence | 缺deadline-aware sleep | S ladder+due+backlog | cron扫描不等于自适应 | — | durable timers概念 | S bounded multiplicative backoff | 固定30s scan |
| user preemption | 当前同步step内不完整 | S activity抢占，非任意effect取消 | S queue/steering，读段未证明全局截止 | interrupt是暂停合同，非用户抢占 | signal不是强制安全取消 | slice可醒；同步model内不抢占 | session queue与steering，端到端U |
| timer durability | S coalescing+stablekey | S TimerBoard/engine notes | S crons.json lease | 需调用者scheduler | S server-backed timer | sleep状态部分持久，U | S markStarted/recover |
| crash recovery | T committed C ack+UNKNOWN | T bus epoch，非arrival replay | S worktree/conflict/lease | S checkpoint pending writes | D deterministic workflow replay | SQLite memory，tick-effect事务U | T interrupted run park/resume |
| duplicate suppression | persistent source/cycle/epoch | goal text/fingerprint/cooldown | pertask/worker token | cached finished task结果 | activity retries仍需idempotency | echo/dedup，effect级U | run token+one-shot stop |
| side-effect safety | S Grant/Budget/Verify/UNKNOWN | Guard/cap/audit，非同DB原子 | permission模型需逐tool审 | checkpoint≠external exactlyonce | retry≠external exactlyonce | booleans+cooldown | mark-before-run减少repeat，非verify |
| hot bound | activequeue/schedule/calls/context bound；历史增长 | MAX_HELD/rotated logs | bounded tree，全部runtimeU | graph dependent | history需continue-as-new | working window/config，长期U | boundedfiles/queues各自限制 |
| observability | structuredrecords，统一surface缺口 | trace/journal/audit/prompts较好 | memory tree/worker/cron logs | checkpoints/tasks/debug | history/query/UI ecosystem | journal/state UI | watch/study/logs |
| kill switch | dev stop+lease/无真实E/G | hands switch+dispatch recheck | stop/permission，逐path限定 | abort/interrupt非OS隔离 | cancellation非副作用回滚 | capabilities/config | stop/paused等，逐path限定 |

## LangGraph：BORROW_PATTERN；不换D

固定 4e2dfe4a247abfc0d001f3ef8242cbbbba400d2c，MIT。`Pregel`把channels/checkpoints/pending tasks作为graph execution state；thread是execution conversation key，Store是跨thread数据接口，不是天然Subject identity。
[libs/langgraph/langgraph/pregel/_loop.py](https://github.com/langchain-ai/langgraph/blob/4e2dfe4a247abfc0d001f3ef8242cbbbba400d2c/libs/langgraph/langgraph/pregel/_loop.py#L1226)：checkpoint与pending writes记录边界；exit模式在退出/interrupt保存，async可后台保存，sync等待checkpointer完成更强；持久性仍由saver负责，InMemorySaver不是磁盘持久化。
[libs/langgraph/langgraph/func/__init__.py](https://github.com/langchain-ai/langgraph/blob/4e2dfe4a247abfc0d001f3ef8242cbbbba400d2c/libs/langgraph/langgraph/func/__init__.py#L319) finished task缓存支持resume；interrupt后节点可从头运行，task分界与重放顺序需要稳定。图修改可能使旧checkpoint不兼容，不能当万能时间旅行。
external effect成功→task result checkpoint未落盘→crash→resume：仍可能再做一次。sync也不能使两个系统成为一个transaction。必须provider idempotency key/query/Verify/UNKNOWN。本轮抽象gap微实验有两次effect，不是运行LangGraph的故障证明。
cron/托管平台scheduler不在读过的core checkpoint机制中，不能从托管广告推导OSS本地自带cron。
适合借分阶段durability说明、暂停/恢复的operator表达；迁移D会重复state authority、引入graph thread≠subject的混淆，收益低于成本。

## Temporal：概念借用，不安装

固定SDK 346d4dcd0863657c3a33283c952a296762059339，MIT。只审SDK与合同，不声称审过Temporal server实现或运维成本实测。
Workflow=可确定性重放控制流；Activity=可能有外部effect的工作；signal=外部持久输入；query=读状态；durable timer/wait条件=时间机会；continue-as-new=截断当前run历史但保留业务连续性。
[temporalio/common.py](https://github.com/temporalio/sdk-python/blob/346d4dcd0863657c3a33283c952a296762059339/temporalio/common.py#L37) RetryPolicy maximum_attempts默认0表示无上限。不能照搬到UNKNOWN外部action；heartbeat用于进度/取消传递，不是Nana存在本身。

| Temporal概念 | Nana映射/禁止混同 |
|---|---|
| workflow deterministic replay | D schedule/control history概念；C判断不强制在历史重放时重新问LLM |
| activity | E/G capability attempt；必须现有Grant/Fence/Verify |
| signal | source-backed EventQueue ingress，不是trusted statement |
| query | RuntimeHealth/derived self projections，不修改memory |
| durable timer | Scheduler机会，不制造motivation/commitment |
| continue-as-new | cold-history archive/operational generation，identity不变，删除tombstone仍保留 |

4GB个人云机新增server/worker/持久服务与运维面大，没做RAM测量不报MB数字。未来多天分布式可靠workflow有需求时重新评估；现在替换D为REJECT，概念BORROW_PATTERN。Temporal也不替代Nana policy与local single-writer authority。

## tomo与Anima的版本特定判断

tomo当前scheduler比“简单mark-before-run”更细：先recoverInterrupted，markStarted持久run token，再调用agent；outcome ACK失败与执行失败分流，park而非重复执行。值得借错误分类和operational解释；不能把它升级为external exactlyonce。附件中poster/plan store/curator的独立对象未在当前读路径定位，标U，不按旧描述造类。
Anima backoff与interruptible maintenance便宜、易理解，但agent:255每tick仍think。sleep有dream随机采样与self-model直接rewrite，不能整体借。Nana的零模型wake、authority/clock可注入/恢复纪律已更强。
