# 新的当前社交愿望参与原C选择

基线cfd11be158a3f0fa36abf93f42d5e4fde1f55bf0/Brain251；S3/S6/S7 Advanced局部A–E审查。写死的“先有保留私人愿望/SEEKING记录才算有社交兴趣”是E，低价值/重复机会仍保留为默认判断D；实际规范、接收者拒绝、近期重复投递、执行授权不变。

## 以前与现在

原C可以明确选择学习/创作而不先有保留兴趣；SOCIALIZE还必须带旧私人兴趣或有记录支持的SEEKING。original9.txt旧3fail6pass：无旧兴趣、已有RECOVERING、当前HIGH负荷三场景，即使当次C明确选择SOCIALIZE，仍被一般机会门判IGNORE或REST。默认不选、明确休息、对方拒绝、近期重复投递、规范与来源撤回控制本来通过。

新代码只让原当前已绑定且合法的SOCIALIZE选择也参与原interested_social判断；继续要求现役separate_delivery架构。没有新的情绪分数、愿望Agent、兴趣真相库或额外Planner。原当前cue导致的OPEN但C未选择仍不足以成为独立旧倾向；没有机械默认联系。原S3 QUIET/RECOVERING保留并继续给C，新的想法可以与它竞争，不通过写成SEEKING或删除旧倾向取得资格。

final10.txt：10passed.81s，新8组合（新愿望/安静倾向/高负荷/默认/休息/明确拒绝/近期重复投递/规范）、当前来源撤回模型0，以及原正常SELF→C→DeliveryAdmission。无预存private activity的当前愿望选择SOCIALIZE；原收件BUSY准入返回DEFER_BUSY、重复准入同record，无动作/Grant/Goal。关闭重开同身份，原SOCIAL_INTERACTION cycle及pending intention仍在、旧RECOVERING仍在、private activity仍0、cognitive_requests不增；不是重启后自动发送或所有意向永不结束。

related85.txt：85passed16.94s，原社交多倾向/虚拟49h、行为约束范围、私念资源准入、原投递/fixture Kernel和关系复用；随后仅给上述正常SELF追加同身份重启/pending不丢失断言，重跑final10，未重复整组85。当前44为前一相交范围，不相加成更大总数。

## 旧测试的行为意图与隐私

原social_tendency_competition的withdrawn案例旧期望IGNORE，体现“没有旧私念就不能联系”的旧准入规则。该案例的新cue由独立Memory来源创建，未从已撤回私念派生；本批改变期望为允许新C当前SOCIALIZE，并增加更强约束：旧private activity仍不再current，旧content_summary不在模型上下文，撤回root Memory已DELETED且不在Frame source IDs，新cue确实在Frame。不是恢复旧私文或沿用被撤回事实。另新测试直接撤回当前cue，原MEMORY_UNAVAILABLE在C前拒绝、模型0；这条真实来源边界未放宽。

原DECLINED、近期REPEATED+HIGH投递频率、当前规范继续约束实际表达；选择SOCIALIZE不是权限或送达，BUSY只延后投递而不强行改写内部愿望。真实联系人、QQ/B站账号与用户设备未接触。

## 同输入原C消融与成本

run_old_decision.py从固定cfd取原纯decide AST，复用同一SubjectLoop/SELF/Context/S3/Store。ablation-proof.json验证只有该Core文件改变，非decide AST完全相同；不是另一主体实现。旧1SELF返回IGNORE→新1SELF返回SOCIALIZE，同内层request JSON42992bytes、同input65536/output2048/timeout120000/cost0；当前阶段不增模型调用、Prompt/新索引/持久缓存。新原投递准入则按真实BUSY延后。后续若允许正式表达，仍可能按原RENDER和投递流程消耗预算，本批不宣称完整生活的调用永不增加。字节不是实际Provider Token，usage/账单/CPU/P95未实测。

## 首错、回退与剩余

最初norm夹具predicate没用原concern.constraint.入口，随后改成真实命名后才作3fail6pass基线；没改规范代码。新隐私断言先误用proposal字段private_text/tendency，实际persisted PrivateTendency是content_summary；普通SELF测试误从subject包导入未导出的RealizationTarget，均按真实类型修正、原失败保留。准入读权限使用原runtime允许的privacy_classes以读取PROJECT合成收件状态，DeliveryPolicy发送隐私仍PERSONAL；无运行权限扩大或守卫放宽。

回退本锚policy.py，无schema/数据迁移；新意向仍属原Store并受原过期/来源/重新判断机制。原9a固定候选不含245–252，CURRENT266+409未动，不重打包/APK。新远端CI待实际；真实模型、自然度、手机、账号/生产、实际跨日/长期成长未新增资格。

下一原C情感/策略与可靠反馈/G独立后续迁移仍继续；新的当前愿望不是新的稳定人格或已成功社交。B视觉固定算法交接、多帧覆盖与共享预算、存储/隐私/真实Token/产品及所有原A–H继续，原13/19节继承。
