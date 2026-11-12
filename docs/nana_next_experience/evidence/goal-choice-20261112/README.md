# 原C目标取舍与内心生活优先级继承（S6/S3/S4，Advanced增量）

基线f7c3078。LIFECYCLE原C分支曾在HIGH load时无视有源紧急继续候选，机械REST；LOW load时又可在只有REST的候选里造CONTINUE。去除这两处E类固定取向，复用原ConcernCue urgency/选项/已采纳goal及norm过滤；没有继续选项不凭紧急性造继续，非紧急高负荷仍可休息，来源WITHDRAW原语义保持。明确prohibition同样有效，全受限时NO_ACTION不假冒暂停。Manager/Grant、原Planner、旧plan ID和主体不变，无新增执行权限/模型调用。

真实原Store/C/work.after_cycle、跨重启：原版2fail/3pass→修复后61相关6.01s→最终73相关8.64s含两项norm与Precision计划/恢复。检验原goal状态ACTIVE/SUSPENDED/ABANDONED，唯一goal/plan、既有grant集合不增加、0actions。开始的两次5fail分别是夹具本就有合法offline Grant，以及轻量Runtime未安装cognitive_requests表；改为真实前后grant集合和可选表实际计数，保留首错，不删除/放宽业务断言。

此处仅目标生命周期局部A–E取舍修复，不是整个自主性或持续内心机制完成。用户2026-11-12新13节优先级已归档并接入AGENTS/mission/08/09。最高优先级下一原C私念→动机→上下文/策略/学习因果；不另立内心Agent。生产/CURRENT266+409/真实模型/设备/长期资格未变。

f7基线独立CI43157054621已实读：135Core130.48s/93unit/148browser2.0m/Vite2.72s SUCCESS，basef7-ci.txt为原日志摘录；不是本批或全仓资格。
