# 原C明确选择私人思想生命周期 — 2026-11-14

[实测 Advanced S1/S2/S3/S4/S6，原A–H同一主任务] 起点d1419869c4bb0952cbad5c71622fa4da2d848e60。原PrivateActivity V2/Question V3/Tendency V4已有ACTIVE/PAUSED/ABANDONED；原C的正常SELF提案却不能明确选择生命周期，且编辑暂置思想的文字会默默恢复ACTIVE并重新进入D候选。

沿原PrivateThoughtEdit增加可选activity_state，仅允许精确revises_record_id的现有思想修订。原C采纳、所选上下文引用、原私人Record和版本更新全部复用；省略字段则保持当前状态，明确ACTIVE才重新激活。新思想仍原默认ACTIVE，本批不声称新建即可暂置。暂停/结束关注不等于忘记或物理删除，不产生Goal/Action/Grant、披露权限或已完成效果。没有第二Store/Planner/情绪权威。

精确旧d141的298个运行源码文件逐字对照Git后，同一10场景/合法旧协议6fail4pass；新最终10pass3.51s，相关248pass79.12s。新字段是否存在由实际expected_schema决定，旧基线不会被强塞未知字段。正常LifeApplication→原D→owned HTTP SELF→原C→原V4，两种明确状态改变且同条件不重复调用；消融省略选择则原ACTIVE不变。重启同身份/同意图/创建时间及正文保留，撤回实际来源后依赖私文清除。Question/Plan/Tendency均可暂停→同状态无额外私人记录写入→主动恢复→放弃，另一思想不变；原D只在ACTIVE提供候选。未选中引用和非法状态不放宽，异常不含私文canary。正常路由更新的隐私为原PERSONAL下限，没有为测试降为PROJECT。

另一个反例先在新原型复现：不指定状态而仅编辑PAUSED正文，得到ACTIVE且offered_target=true。修正后保持PAUSED且不提供D机会。此为有意语义修正；旧省略状态的调用不能继续依赖隐式唤醒。序列化省略默认字段保持旧JSON，不宣称所有旧reader/热切换/安装回退均资格。

成本：四个HTTP场景旧每次48444input/60733reserved bytes，新49404/61693（+960），各1 SELF，没有额外模型阶段。SELF schema增加870规范JSON bytes；原非SELF schema11491bytes及默认提案JSON哈希完全相同，复用既有proposal_schema裁剪。字节不是Token，无实际Provider usage/费用或真实语义质量收益；10场景耗时仅合成受控耗时。正文/状态沿原Record，不新表/索引/后台循环；此处未量化长期DB增长或回收。

首次失败保留：旧基线初版3个夹具引用不在所选上下文，修正夹具后才有有效6fail4pass；新首轮2fail是测试只读PROJECT漏掉正常PERSONAL版本，扩大到主体已有授权读取并断言PERSONAL后通过，运行隐私机制未改。隐式重激活首次失败单独保留。247相关属于修正前，最终以248为准，不累加冒充全仓。

前继独立CI run43610804363：d141 Core job132495447271实际192pass140.77s；client job132495447255实际93单测/3Node/160浏览器通过。全仓/便携包/安装步骤SKIP，仅归前继；不是本批或Java/手机资格。本批workflow只把现有定向选择纳入新测试及原生SELF相关，没有再建发布流程。

原始文件见本目录；source.sha256只证明采集源码/证据，不证明运行现场。复跑采用现有pytest入口、TMPDIR=/dev/shm、PYTHONPATH=$PWD:$PWD/src，10场景文件tests/person_self/test_private_lifecycle_choice.py。原始旧/新输出保留断言和耗时，compatibility.json记录精确旧源及两个schema。

未新匹配Core/Web包、APK、安装、真实模型、手机、真人、生产、跨日或长期成长；CURRENT266+409保持。环境启动后已实核本工作副本/未提交改动完整、远端d141一致，无在途pytest/构建执行者。下一核对原D私念候选的WATCH/REFLECT/REST是否无必要限制自主探索/创作/学习：先沿原Work/Planner/执行消费者证明可用选项，不盲目扩大列表或把思想强制变任务。原情感/多动机/G未见迁移、存储隐私/Token/产品最终发行及全部A–H仍继续。
