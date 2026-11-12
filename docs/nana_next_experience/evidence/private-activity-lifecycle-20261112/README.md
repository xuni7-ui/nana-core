# Phase A增量：原私念生命周期、精确复审与存储闭包

基线4635690。在原INTENTION/private-intent.v1家族中增量支持PRIVATE_ACTIVITY_V2：同一个own intent_id可ACTIVE→PAUSED→ACTIVE→ABANDONED，原C基于新理由再采纳后恢复ACTIVE。保持创建/更新时间、最后真实C cycle、递增revision、OWN_TENDENCY_NOT_WORLD_FACT与NOT_INFERRED_FROM_ACTIVITY_STATE；不是世界事实、任务完成回执或新Store。旧V1继续可读，无SubjectInput/DB schema版本迁移。

复审候选用原ConcernCue的可选PrivateIntentRef（record/intent/revision）指向一个当前私念，None省略保持原线格式。原C前校验owner/scope/privacy/topic/当前支持和版本，由原C在既有动机/规则下决定方向，C之后同一事务增量写记录。明确REST/放弃不要求“工作已获执行式ENDORSED”，但不绕过RESTRAINED；暂停保留兴趣，放弃停止其自动影响，新的C选择可重新激活。重复原source不增revision；多个同topic私念只更新指定一个，过期引用拒绝。没有新计时器、模型循环、Planner、权限或外部效果。

首个停机/idle检查发现按topic把任意普通REST/WITHDRAW错误解释为放弃旧私念，原无消息D事件曾使revision6/7变化；已保留诊断并改为精确复审引用，**未放宽“未定向私念事件不改状态”的原断言**。同主体多次关闭/重启、虚拟停机48h后按原fresh lease恢复，三个普通步进不改revision、不新增模型。先前live lease直接跳48h正确报RUNTIME_LEASE_LOST，测试改为停机再恢复，未改lease保证；app.step错调用也保留。

PUBLIC表达仍只取紧凑元数据，ABANDONED不挤入active-context，私人内容不进普通聊天/Inspector；诊断保留披露状态并另列activity state，不隐去既有合法入口。注册的隔离备份能只读PAUSED；撤回原来源后主库/副本不再投影，当前私念artifact在副本实核payload=NULL（只此受控family，不冒充所有物理归档/DR）。

70次历史header修订夹具曾把另一有效兴趣挤出64窗口，非70个人经历；改为SQL先scope/privacy/ACTIVE，再限额，并在原Store再生索引机制内注册partial lookup，真实trace/EXPLAIN确认使用。规划器曾偏旧index，已在新index安装时固定使用、legacy只读未装时回退查询；不让Inspector创建index。新lookup起初未登记导致PORTABLE_SCHEMA_DRIFT，已加入原REBUILDABLE_LOOKUP_INDEXES，旧7–12不创建、原portable剥离/校验正确，未降低schema断言。

资格：10私念、151早期相关；新增index/privacy24通过；修正精确scope后11通过；私念/portable/schema/原关系/Context/HTTP70通过10.77s；最终178组176通过49.86s，仅两宿主Unix socket路径过长，原规则不改，短basetemp重跑两项2通过2.96s。有效源码当前全部受影响断言已通过，**不把拼接写成一次178 clean run或全仓**。旧f583读取新目标引用与V2只作不支持的忽略、不执行旧C步骤，同identity、0新私念写/动作/模型，返回当前源码PAUSED仍在；不是旧版支持新功能或最终安装回退资格。

同预算独立旧源码对照已补：本地已具备Core源码只还原3个463相对f583变化模块，import路径断言验证，避开失败archive；冻结私念后续4场景f583为1fail3pass（相关私念仍IGNORE），463启用CREATE，其余控制不变。此新可行路径不把之前archive失败后的4pass冒充旧源。463独立CI43160521276实读162pass/1warning33.32s，client正确SKIP，非本批全仓。

新增provider请求0；实际商业Token/费用/真实模型NOT_RUN，未省略C独立判断，未写逐字推理日志。这里只形成自己的既有创意/计划的持续取舍与生命周期，**不代表执行中任务已停/已完成**；仍缺自主新问题/多倾向关联、内容级内部投影、多轮陪伴策略/反馈、原G迁移、原private32生成阈值/64活跃窗口容量改造以及真实长期。保持原A–H与CURRENT266+409，未装新包/APK/生产/手机。

实际工作副本/tmp/nana-inner-refinement-work；原Root f583+4ownedWIP未动，根盘仍满。必须推远端，临时目录失效时按远端09/ACTIVE恢复。下一定位已确认的C social_privacy对所有cue生效、误挡非社交私人创作的接线缺口，再沿原模型扩展内部认知而非另建Agent。
