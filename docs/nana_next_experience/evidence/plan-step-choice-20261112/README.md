# 原C已采纳计划逐步选择的自主性修复

基线d3907d3（行为源码12fa8b9）。f583已修goal lifecycle review的负荷/继续取舍，但正常plan_step分支仍有独立缺口：HIGH负荷一律REST，LOW时REST-only仍CONTINUE，CONTINUE单项被prohibited但REST未禁止时仍继续，REST也被禁止时却虚构REST。冻结7场景4失败/3通过，原错保留。

A–E归属：真实权限/资源在原Manager/Grant/Kernel/Verify（A/B）；主体当前rest/watching取舍与source-backed norm/紧迫性属于D；开发者无条件HIGH→REST、忽略quiet choice/单项norm属于E误实现。本增量不删load或norm条件：当前quiet choice保留，CONTINUE单项规范明确检查，负荷与有源HIGH urgency竞争；无合法REST时不伪造REST。已采纳计划原CREATE/LEARN起源cue并非新步骤的穷尽白名单，默认继续行为保留，防止简单按CONTINUE是否在所有旧cue中就停掉创作计划。

测试通过真实已采纳原Goal/PlanStepRef/target，以原C判断而不执行step：HIGH/HIGH可ACTION_PROPOSAL；HIGH/LOW可REST；LOW/HIGH+REST-only仍REST；CONTINUE被禁→REST；CONTINUE和REST皆被禁→None/NO_ACTION；旧CREATE起源仍可继续。7例均configure(grant=False)，C选择不新增Grant/Action/model，原goal/job/cursor/plan row保持原样。没有将意愿当执行权限或把当前step withheld当整项goal已暂停/放弃。

初次测试错误查询schema12不存在的cognitive_requests，保留首次日志；改用原runtime_cognition_calls观测真实可用表后冻结4fail/3pass，不放宽行为断言。修后7通过0.75s；原open_life/open_autonomy/precision/affective182相关通过33.93s，包含Precision V2规划/检查点/恢复原断言。非全仓、实际账号/模型/手机/生产资格。

没有新Agent/Store/Planner/Grant机制或额外认知调用。只是原C当前选择与后继执行权限继续分离；更广动机竞争/商业内心/持续自然交流策略及全部原A–H继续，不据此称自主性全审计完成。普通CORRECTION源码早已WATCH，已复用，不重复改写。
