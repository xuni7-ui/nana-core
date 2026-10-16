# YuriOS — two cadence 与生活表面，不替换 Nana 主体

固定 SHA `cd4d1f16ae095f0f694dbbe7b1aac8e33db25367`；Apache-2.0。Python，最近 commit 时间见 manifest；不是24h实机可靠性认证。
必读清单已逐文件定位/读取关键段；`yurios/mind/dreamjobs.py` 在该 SHA 不存在，实际为 `dreamjobs/{runner,builtins,context,filedsl,research}.py` package。不补造旧路径。

## 1. 两种 cadence 的实际链

[yurios/world/turns.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/world/turns.py#L260)：post user message→post signal→park_gate.wait→turn_started→brain.stream_reply。没有等待 mind.tick。
turn_started 直接将 activity preempt ENGAGED；turn_ended 后才 persist exchange，并将 structured tool outcomes 放入 turn_committed signal（turns:347–361）。所以快回复先可见，memory extraction 在可见回复之后，但 persist 仍在该 turn coroutine 内 await：不能说所有 post-turn 工作都已独立成 durable background job。
[yurios/mind/loop.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/loop.py#L356) 记录 in-flight count，bus wake 打断 cadence sleep；不等于无条件取消已在飞的模型/工具。[yurios/mind/loop.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/loop.py#L1028) 的 `wake.clear()` 与 sleep 并不能独自证明任意竞态零延迟。

后台自治不会把 cadence 周期放到聊天前面；仍会竞争同一 event loop、provider/VRAM/IO。arecall/to_thread、off-thread embed bootstrap、ParkGate 是重要配套，不是“天然互不影响”。tests/test_embed_off_loop.py 用慢 embed+heartbeat 验证调度不被同步 embedding 卡住；test_runtime_build.py 验证导入顺序与 ready 状态。

同一 soul/world/goals 接到 ToolBrain，可减少 talking/thinking 文本漂移；SPEC §15.3 还明确统一 reply-by-ACT 是未来 rung。因此不把现状包装为 Nana 所要求的一个 authority SubjectLoop。Nana 借 D 双 cadence；所有正式 Judgment/Intention 仍只有现有 C loop+CAS。

## 2. 六阶段源码表

| 阶段 | 输入→输出 | 模型 | 持久化/权限/no-op/crash |
|---|---|---|---|
| SENSE | bus batch+timer+wakeup+gap→world updates/actionable/review backlog | 主体扫描不调用；处理中会有状态修改 | engine/world多文件，不是整 tick 事务；仅 bookkeeping，不新增权限 |
| APPRAISE | signal/goal/dream/hand offer→有分数候选 | heuristic零模型 | transient；已混合 tool availability，不照搬到 Nana normative 判断前 |
| DECIDE | 排序+threshold→一个 chosen 或 REST | 不调用 | trace后写；“one”是调度与解释边界，不是exactly-once transaction |
| ACT | selected kind→noted/research/work/reach-out/dream | 按分支可调用 | 可触及真实host surfaces；REST不用模型；effect-before-state 有失败窗口 |
| REFLECT | act notes→journal、goal decision、trace | journal可embedding；不可泛称零模型成本 | 不等于 Nana 的正式 Experience/Reflection gate；partial多写可发生 |
| REGULATE | budget/backlog/user time→activity/cadence/state/ack | 状态决策无模型 | engine持久后ack，最后off-thread Git；不是跨外部effect原子commit |

主依据 [yurios/mind/loop.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/loop.py#L393)、[yurios/mind/loop.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/loop.py#L636)、[yurios/mind/loop.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/loop.py#L665)。
one intention per tick 有防 fan-out、预算和逐条解释三重价值；一个 goal_work 内仍可有多次tool/model step，不可误说一tick最多一外部调用。
Nana 每wake≤1 committed intention，多个长期project/commitment/candidate并存；不能无审查删除旧kernel `one_live_goal` index。

## 3. Activity / cost

[yurios/mind/policy.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/policy.py#L26)：ENGAGED→IDLE（engaged timeout）→DORMANT（idle timeout）；有backlog且处于dream window才DREAM；backlog清空返DORMANT；budget pressure≥1 把IDLE降级。user preempt来自任意状态。state影响cadence与候选工作，不等于人格或“她只喜欢聊天”。
`cadence()` 有backlog可缩到5s，否则min(state delay, due goal, wakeup, review retry)，run sleep可被bus唤醒。suspend gap只合并一次，不补几十次问候。
[yurios/mind/budget.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/budget.py#L22) 用chars/4估算daily spend，debit后读pressure；不是provider账单，也不是与call原子绑定的预留。quiet REST不调用chat/utility，可能仍有IO和状态维护，journaling可调用embed。
goal work、自语、research、dream是按候选触发，不是每tick一个LLM。但dream job多轮成本应单独计，不拿daily cap解释所有未知支出。

## 4. SignalBus vs Nana

[yurios/mind/signals.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/signals.py#L80) 是in-memory绝对offset+base+epoch+ack；MAX_HELD1000，溢出从前端丢，arrival JSONL仅记录**不回放**。重建same bus恢复offset，new bus从0，tests/test_mind_loop.py:648–714覆盖历史跳信号bug。
这适合低价值感知通知，不适合Nana authority ingress。Nana queue durable、owner epoch、已commit cycle恢复ack、provider RESERVED→UNKNOWN较强；保留后者。可借release unread window的有界思想，不能借丢消息语义替换receipt/commitment处理。

## 5. 四面可观测

[yurios/mind/journal.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/journal.py#L60) 写每日episodic `[she]`，publish先于embedding；index失败不毁文件。[yurios/mind/trace.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/trace.py#L19) 是sensed/appraised/runner-up/acted/interrupt；[yurios/mind/promptlog.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/promptlog.py#L44) correlate tick/turn/model，chat prompt只pointer避免双写；tool calls共享audit但标background origin。
Nana借关联UX而不借全文prompt默认留存：ActivityJournal从已提交records派生；DeliberationTrace只合法因素/source refs；ActionAudit以Attempt/Verify为准；ContextTrace默认manifest/ref/hash/omission而非隐藏思维或私人正文。删除source须撤掉journal/context body；journal读取不能再变独立Evidence。

## 6. Goals / promise

[yurios/mind/goals.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/goals.py#L295) goals.md解析/read-modify-write，pending/active/waiting/done/abandoned，text/provenance去重；dated与stale不同。[yurios/mind/goals.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/goals.py#L774) review schema严格，检查candidate indexes/词汇grounding；explicit提醒与assistant promise分开，timer_id避免重复早提醒。
有用：task work与tell/report分开；完成工作≠已经告知；FIFO review持久化/invalid backoff；timer join。
不可借：语言提取或semantic review直接变Nana正式承诺。Nana request→Judgment→proposal→独立adoption authority→commitment CAS更清晰；timer只是重新考虑机会。

## 7. Memory authority / retrieval

[yurios/app/memory/store.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/app/memory/store.py#L103)：SOUL/USER partner model、episodic day files、facts.md、forgotten.md是文件层；vector index是可重建cache；knowledge shelf另有原文/curated区分。assemble总注入小SOUL/USER，recall按需；summary不是原始经历。
remember先append raw exchange→embedding worker→extract ops→quarantine/merge USER.md。低confidence待corroboration；可更正slot但不是Nana结构化Evidence authority。evolve_partner await后重新读取当前文件以免覆盖forget，值得借“慢工作返回后重检source”的纪律。
recall过滤similarity floor/tombstone，similarity×salience×recency后MMR，先逐字规范化去重；测试证明只排序不把blend传MMR会失效。knowledge是0.65semantic+0.35keyword、每doc cap，与事实source/curated区分。

**关键不兼容**：forget:473明确 supersede-not-delete，旧值保留git；tombstone含selector，episodic原文未物理清除；DREAM汇总源也应再检查。不能满足Nana彻底删除规则，不能把“未来prompt不见”当“已删除”。纯字符串匹配也不保证改述/derived闭包。

## 8. DREAM / self-edit / hands

[yurios/mind/dream.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/dream.py#L145) oldest finished day、not today、progress+chunk budget；首项超预算仍尝试以免饥饿，Nana应改为严格bounded slice，不能用此理由穿透hard cap。facts被utility summary追加高salience，不能原样借为可信记忆。
[yurios/mind/dreamjobs/runner.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/dreamjobs/runner.py#L386) jobs priority、progress ledger、own research budget、process-global night lock；不是新生物睡眠，也不是durable跨进程exactly-once runner。
[yurios/mind/selfedit.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/selfedit.py#L75) constitution拒绝，soul high-risk review；memory/world/goals等低risk可autoapply。借proposal diff/review UX，不借自由文件重写Nana identity/growth。
[yurios/mind/hands.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/hands.py#L523) kill switch/allowlist/cap/pressure、conversation独立buckets、fingerprint cooldown、dispatch recheck、audit。ledger spend先于call但持久engine snapshot在后，不能证明crash后副作用只一次；Nana ActionKernel+receipt/UNKNOWN/Verify保留。

## 9. Reach-out

[yurios/mind/policy.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/policy.py#L184) salience-to-interrupt与act不同。quiet hours22–9、dailycap即使decided也veto；no recent contact/waiting credit可提高score。[yurios/mind/acts.py](https://github.com/yuri-os/YuriOS/blob/cd4d1f16ae095f0f694dbbe7b1aac8e33db25367/yurios/mind/acts.py#L744) 被quiet/cap挡住后park到next_open，不每小时刷日志；同reason/day不重复。
可借窗口/去重/延后机制；不借“安静越久越有打扰license”作为默认社会规范。Nana不能从沉默推断亲密下降、寂寞或同意；Primary Anchor也不意味着必须联系。

## 10. 追加源码反例：DREAM错误不等于空日

`dream.py:214–230` generic utility exception（非InferenceBusy）log后返回[]；`consolidate:169–194`无failed discriminator，仍把该日放入done_days/progress。注释称failed night保留backlog，但这个路径实际把失败当空日处理。reviewed AST隔离实测：synthetic provider RuntimeError→facts0、days_processed含该日、backlog空。只确认固定SHA该分支，不声称跑过完整服务或所有异常。
Nana维护协议必须EMPTY_SUCCESS / FAILED / INTERRUPTED / STALE分开；失败不能推进成功cursor，也不盲目重试已发生外部effect。此处仅记录研究发现，未改上游或Nana源码。

VERDICT：BORROW_PATTERN；authority/recovery/deletion/identity边界 NANA_ALREADY_STRONGER。没有复制上游代码。
