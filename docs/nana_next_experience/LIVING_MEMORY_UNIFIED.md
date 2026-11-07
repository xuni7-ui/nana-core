# 同一主任务：生活／情感／梦境／记忆／遗忘／成本融合施工

输入见 task_inputs/LIVING_MEMORY_DREAM_STORAGE_TOKEN_2026_11_07.md；原项目坐标不变。409客户端已定版，后端适配不触发逐次APK重打。生产由原负责人管理，真实模型/手机/跨日资格与开发分开。

## 已有／部分／本次已确认缺口

| 路径 | 继承及真实差额 |
|---|---|
| 原C/G/S3/Fish | 原关注/衰减/独立兴趣/反例/休息、实际学习复用与来源撤回已实现。不能重造；需深化与梦境和未来真实选择因果 |
| 模型/409 | 流式、原owner控制、回执归档、字节结算、模型framing绑定及原Runtime额度转发已代码验证；真实商业Tokenizer/usage/模型/Human不由夹具替代 |
| 原Runtime/SCAN | 实测无输入虚拟1小时360永久事件，逻辑增长1171456字节、family文件长度增长1715248字节，0模型调用。60次空泛时间检查及59次空SCAN是大头，不是主体生活经历 |
| 已实施差额 | 仅原内建无来源review改为同Store、同owner可重建的运行检查点；原C maintain仍执行，pending跨重启。真实自定义/日历/来源事件仍完整审计。空SCAN只推进操作due，不改cursor/revision/学习job；原G维护钩子保留 |
| 同条件候选 | 同原Store/时钟/配置/3600step：1条首次SCAN创建事件，逻辑增长0、family文件长度增长313072字节，0模型调用。未删除旧历史、未压低权限。不是生产实测，也非真实1h驻留 |
| 磁盘测量 | 原st_size family保留并明确其文件长度语义；新增去重st_blocks×512分配占用；dbstat和事件JSON按UTF8 BLOB字节计。不能以逻辑过期称物理回收 |
| 梦境 | 现有Maintenance为固定行批次拼接摘要、C认可、来源撤回；缺价值/关系选择、日/周/重要事件节奏及未来检索利用，待继续代码实现 |
| 上下文 | 现有PersonSelf只选少量交流，pinned对话未自动利用所有可用巩固；48小时软候选与重要旧源选择仍待接入原Assembler |
| 容量/归档 | 当前固定256MiB guard仍存在；弹性磁盘预算与异常速率分离、验证后冷归档/回读仍待做；不能截断链或越权真实重整 |

原31项相关运行/维护/检索成长检查及3项新检查点验证通过。baseline及初始候选见evidence/living-memory-unified。后续新来源、恢复/重放/前台抢占及真实磁盘比较继续补验，不能把这一个修复写成整项任务完成。

## 后续实际代码：软48h和原始话语回忆

同Store PersonSelf按当前task query/48h软窗口/时间选取，明确同意保留的话语才入候选；最多96条可见header、4个source-backed交流、热context至多2段，重要旧源不被48h删除。384字符逐字片段带原文offset与来源、reported-speech而非事实。privacy/active在SQL LIMIT前过滤。实际原INTERPRET→C→RENDER验证暴露末尾omission元数据把整个PersonSelf丢弃，已加有来源的单段回忆→稳定self降级，不抬模型预算/不削弱来源。

70相关检查24.19s通过，含72h虚拟间隔/同主体重启/旧原文实际进入RENDER/撤回后消失/未选择保留的query不落库；初始预算失败保留在soft48-result。不是实际跨日相处或商业模型回忆质量资格。APK未重打。

## 后续同一后端批次：巩固可用性、条件变化、容量与usage

- 原Maintenance/SCAN job和cursor上增量处理；新增同job的每周有界回看cursor，和新来源交替，重启继续，不每wake全量重读。重要单条来源可形成候选，无需等夜间或凑两条。不保留的LOCAL_INTERACTION_METADATA回执不能冒充经历；不同privacy分别形成候选。按现有承诺/项目支持、importance/significance、原时间排序，不按正面情感刷值。
- SOURCE_EXCERPTS_V1保留原文逐字offset、事件/获知/记录时间、epistemic/source kind和全部原始来源，仍须原C认可。没有模型调用，不把它叫学会技能或语义理解。C在已有6项注意负荷时可以REST；DEFER落在原jobs，条件不变不重复C/永久事件；原意图/义务/关注来源变化后才重新提供，跨重启成立。纠错或撤回使旧候选/摘要失效。
- 原ContextAssembler的同意/范围/privacy/预算内增加CONSOLIDATED_RECALL；原memory_terms和memory_dependencies按原来源匹配，最多16个摘要、2个召回块，100ms查询/处理界限。逐字片段再次读取当前原源，保留派生与不确定性，不直接相信摘要。新可重建索引只加速既有Store，SubjectPackage仍剥离并在目标重建；每摘要单独claim family，避免共享predicate导致不断全读旧摘要。
- 同条件、同预算的受控查询，巩固前没有目标片段，原C认可后出现；72h虚拟间隔/同Subject重启后实际RENDER请求仍含目标原文；纠错后旧周五来源不可用，原C重新认可周六来源；撤回后派生和未来请求都不再使用。并非真实跨日陪伴、商业模型理解或人类自然度资格。
- 原StorageGuard增加FIXED/DISK_AWARE。旧/缺失配置仍FIXED，显式旧max_state_mb仍有效。仅新宿主factory无显式固定上限时选DISK_AWARE；读取实际非特权statvfs空闲，预留磁盘和2份一致性备份空间，独立可配置16GiB ceiling。异常速率保护、停止锁存/人工可信复核不变，不自动恢复、不删除链、不宣称已有备份或DR。当前生产配置未改。
- 原ResourceState从现有COGNITION_PROPOSAL的usage元数据聚合实际提供方上报input/output，和SYNTHETIC本地数据分列；缺失/矛盾/UNKNOWN不当0、不从bytes估Token，不退款或解锁权限。这个报告不是账单、商业tokenizer资格或节省Token的证据。

尚未完成：经完整性/跨引用/恢复/隐私验证后冷历史归档及其实际物理回收；更深入的S8对梦境/上下文错误的独立后续策略验证；安全绑定下商业tokenizer/真实模型消耗、实际云端/手机/跨日相处资格。当前仅代码与隔离验证，最终安装包内后端probe/交付尚待后端收口，不把旧522/b873包冒充新后端。409APK/Web完全不动，source tree和APK SHA仍与b873一致。

最终本批源码指纹前后相同，248相关检查62.90s通过（外层64.003s），覆盖原PersonSelf/Runtime/C/S3/Provider/流式/可移植身份及新维护/容量/usage；不是全仓回归。初次缺召回优先级、LOCAL元数据fixture错误、未推进增量due的fixture、周回看被原hour间隔延迟等失败均保留；修复及相同断言复验见本目录evidence/living-memory-unified。历史2006/12仍只属于37e46b5。
