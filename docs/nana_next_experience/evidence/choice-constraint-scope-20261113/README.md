# 原C约束按实际选择适用

同一NEXT_EXPERIENCE_AND_TEN_DOMAIN_REFINEMENT，S3/S6/Shared Life Advanced。基线269ea2e4ecdf0c2f78e2b7f1c3fc46c1c8783ab5；复用原C、private interest、关系/有限承诺及原机会评估，不新增偏好表/Agent/Planner/状态系统。

真实缺口：原policy已选options[0]，却用“候选列表是否还含SOCIALIZE/LEARN”决定是否套用对应边界/学习风险/学习成本。因此选CREATE时，尚未采用的社交建议被拒绝、社交相关性低或另一个学习方法风险高/成本重，会使本次私人创作变STAY_SILENT/REST。已采纳的有限社交约定也会因为候选里有SOCIALIZE抑制另一个私人活动。

最小修复：社交接收偏好/分享评估及有限社交自我约束只在选SOCIALIZE时参与；学习评估/风险及学习方法的time_compute_cost只在选LEARN/SEEK_CAPABILITY时参与。兴趣支持同样对应本次选择，不能借未选中的另一个方向规避本次约束。全局实际cognitive_load、该活动attention_demand、来源/norm/privacy、due commitment、原D资源/并发、Manager/Grant/Kernel保持原路径。没有删掉限制条件，也没有添加固定生活优先级。

A–E归类：真实来源/norm和执行权限属A，实际资源负荷属B，收件人明确拒绝属C，已经自主采纳且有限的关系让步属D；把这些范围扩大到未选择的另一个合法活动属E，本批修该扩大。内部创作不是发送联系人，不因解除连带否决就获得发送或执行权。

## 对照与验证

同输入/同预算：原源码4fail2pass→6pass；最终精确旧Git源码包269ea2e，在修正后的7个场景仍5fail2pass，含实际原关系决策ACCEPT→VoluntaryAccommodationService→ACTIVE承诺的连带抑制。新245相关33.55s通过，含7场景、open_life、affective_autonomy、原私念、ContextFit及Precision planning/recovery。两个反向控制：真正选SOCIALIZE仍遵守DECLINED；真正选高风险LEARN仍REST。实际有限承诺整行前后不变，选SOCIALIZE仍STAY_SILENT，而选CREATE不再被它禁止。非全仓、非商业模型/真人生活。

原始失败保留：关系夹具最初误写服务名、两项不同机会共用单值predicate造成MEMORY_NOT_CURRENT，以及误把原materialize终态ACTIVE写为ADOPTED。改为原VoluntaryAccommodationService、两项独立来源谓词、对照原源码明确ACTIVE后整行不变；没有放宽生产来源/冲突或承诺状态门。之后精确旧源仍在真正目标断言失败，避免拿夹具错误充旧版行为对照。

## 成本与边界

这些场景原模型调用0/新0、actions0/grants0；没有新字段/表/索引/依赖/模型阶段，正常原C评估复用既有输入。CREATE返回原GOAL_CANDIDATE而非真实执行，新增意向仍走原pending/重复/权限约束；不因通过选择测试就声称创作已完成。实际Provider Token、费用和真人延迟未测；没有物理存储或长期收益声明。新private/public DTO兼容没有扩大，既有choice/private-ref旧reader回退差额保留。

仍未完成：开放认知对多个动机的更深取舍、情感意义更新/预期和实际效果、跨日迁移与原A–H。当前options[0]仍是原初始policy的选择入口，本批没有将其包装为完成自主多动机机制；后续应让原C的已有认知在合法候选中形成有依据的选择，而不是另加固定权重表。CURRENT266+409，未安装/上线、真实模型/手机/自然度/长期未新增资格。
