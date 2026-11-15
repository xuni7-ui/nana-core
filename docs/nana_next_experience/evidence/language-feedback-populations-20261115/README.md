# 反馈证据群不被合成数量挤占，已资格方法不被别域经验遮住

[实测 Advanced S2/S3/S6/S7/S8，原主任务/原186消费者] 起点383a51aa99a110219aab5733451ef1c6ef4abeba（业务源aebb02a），精确298旧运行文件从git show单独取得，未重新开发原G或把16/32笔记范围调大。

已证实三个因果断点。learnable先取全局32样本，再区分USER_PROVIDED_REVIEW/PROJECT_SYNTHETIC，40个新合成评论可挤掉旧用户意见；一条尚不足采用的用户意见因此被合成群替代并错误取得资格，明确反例也可能被挤走，或反过来让合成反例否决已支持的用户证据。分群之后，如果未评价样本也占32窗口，40个UNREVIEWED仍会遮住有效意见。expression_policy另有全局16 ACTIVE lesson截断，再过滤scope/隐私，16个别域或PERSONAL经验就会漏掉合法PROJECT经验。最后正常context会给已采纳USER方法混入最新PROJECT示例，即使它们属于相反证据群。

最小修正复用原person_self.rows的可选sample_provenance条件：仅LIVED_LANGUAGE_SAMPLE、只认原两种来源标签，在原scope/privacy/lifecycle header约束与原Artifact关联下，按证据群与已评价状态过滤，再各取原32窗口；learnable仍用原独立话轮去重/阈值/反例与来源逻辑。不把32放大成更高阈值，也不因为UNREVIEWED或沉默建立正评。表达lesson先按scope/current/privacy筛选，再取原16；当前支持/来源群仍复查。已采纳策略的示例只从同一来源群选原最多2个；没有策略时原带标签示例行为保持。

无新表/index/Store/模型/依赖/Prompt/schema/调度、无来源等级升级、人格写入或执行权限。通用CASUAL ExpressionRule仍是原有界假设，不变成独立沟通评价器；原G练习/held-out/迁移和16/32笔记资格不变。分群窗口最多64个候选头并仍只投影2示例，未全量注入评论。特定联系人/话题/收件范围的原通信方法与反馈保持原绑定；本批不声称通用表达假设已完成跨联系人或长期人格泛化。

精确旧383同17场景7fail10pass3.83s→新17pass4.20s；168相关55.68s覆盖正常对话、原有界方法/私人反馈、四模式记忆反馈、学习/隐私与旧schema genericity。随后只补一个正常LifeApplication→INTERPRET→原C→SOCIAL/RENDER真实本地HTTP场景，旧1fail1.19s，新1pass1.20s；两者C仍CHAT/两次PROPOSED调用，原模式/权限不改。新LIVED_LANGUAGE仍USER方法，LANGUAGE_EXAMPLES实际2个同群示例；fixture renderer按实际policy体现输出差异，不冒充商业模型语义或真人自然度。相关168之后未改Core代码，只新增此独立验证，不反复全仓重跑。

首次较小窗口1fail1pass0.59s、分群后11pass1.58s及15pass3.19s保留；UNREVIEWED挤占与示例错群各自首次失败保留，之后才修正相应连接。未删除/跳过/放宽原断言。所有USER_PROVIDED_REVIEW也是测试中显式标记的样本，不是本轮访问真实用户历史或收集真人反馈。

成本：同40新评论的只读资格查询旧约5.026ms/new5.336ms（单样本CPU相同数量级），两边写0/Provider请求0，不称P95或全局性能改善。正常两阶段预算均16384input/2048output/120000ms；旧完整输入25283+22335，新26872+24009bytes，合计+3263bytes，原预留亦分别增加1589/1674。新增的是应有策略/同群证据，源数量与阶段预算受原ContextAssembler控制；没有额外往返，也不把字节、fixture usage、单例延迟当真实Token/费用或缓存收益。

同一来源群内更长历史、许多别名/纠错/独立发生采样的更广资格仍待，当前没有无限扫描或宣称最近32永远代表全部长期反馈。SQL沿原头/Artifact索引和scope/privacy筛选，无未经测量的新派生index。主链物理回收、实际Token、自然交流长期效果及其他A–H继续。

前继383独立CI run43697928396/job132762634327实际69pass59.28s，仅归前继；client/full/portable SKIP。现有CI已按lived_language/person_self消费者选择原回归，不新增验证工程。本批无新包/Web/APK/手机安装、真实模型/费用、账号发送、生产、真人自然度或跨日长期资格；CURRENT266+409保持，固定929候选仍只归它自己的源码，不能称包含225/227。

工作树/workspace/nana-next-refinement-work，磁盘20万合成库/workspace/nana-preserved-200k-20261114保留，旧18bc保护。下一原S3情感短长/多动机，以及同群独立经历与通信方法的更广后续评价/反例迁移；复用原G与当前反馈接线。跨topic/存储隐私闭包/模型Token费用超时/多端产品/最终匹配发行和全部原A–H仍未完成。两个续办已按北京时间2026-11-15 22:25及11-16 05:00创建，不冻结当前工作；定时承诺仅为任务配置成功，非平台永久运行保证。
