# 授权来源在有界召回前筛选；压缩/重启连续性原链验证

基线486ed54626b27a4f2fac10c5fca6c37075b1ebb7/Brain242（已吸收PR14/17/18）。归S2-C01/C02/C04及原S1/S3/S7 Advanced协同，不改Foundation资格/冻结63条或新建主体任务。

## 真实缺口与最小实现

旧Context会先取所有来源排名前64，再判断是否为已同意保留的平台观察；同关键词的65个更高importance其他来源足以让一条合法B站观察缺席。该观察未删除，单纯扩大近期历史或全局召回窗口只会掩盖问题。

原MemoryService.query增加可选有界、精确匹配的source_namespaces，SQL原entity/scope/privacy/lifecycle筛选内、排名LIMIT前按既有evidence关联筛来源。现役Context明确传recorded.platform.bilibili.dynamic，之后原domain/kind/关键词/隐私及最多4项检查不变；通用LIMIT64/512均未放大。不新增表、索引、缓存、持久字段或模型阶段。默认省略参数走原查询。精确匹配中的%无通配权，PROJECT/异scope不能借来源过滤取得PERSONAL数据。回退486的memory/context两文件，无数据迁移。

## 原版→候选与因果边界

baseline-exact486-2.txt：固定486原Runtime allowlist263个文件逐一Git blob SHA一致、仅从该隔离目录导入Core；相同最终测试与输入实际2失败1.43s，不是候选模拟旧错。原版重启后原C仍LISTEN（私人倾向已保留），但SOCIAL SOURCE_UNAVAILABLE。最初整src archive触发部分克隆未用模块下载，停止该自有pipeline后改为已选263模块逐字核对，未取代旧失败/假称全仓归档。

final2.txt：2通过1.81s。明示保留平台观察在原Store只有1份，65其他有效观察仍在，不改变其importance；同上下文预算可选中相关来源，同主体关闭/重启后仍可用，PROJECT隔离/精确重复接纳/撤回生效，最多4个记忆块。

组合episode先由原C形成PRIVATE_TENDENCY，普通1200余字聊天只留1024临时摘录；关闭owner清空_recent，49虚拟小时后同identity重启。后续INTERPRET→同C→SOCIAL得到LISTEN+SOURCE_KNOWN；关闭既有dialogue_private_refs选择入口的投影消融得到CHAT+SOURCE_KNOWN；恢复投影并撤回B站观察得到LISTEN+SOURCE_UNAVAILABLE。原私人记录头保持，source撤回不错误删除独立私人倾向；私文不入SOCIAL或公开回复，普通临时CANARY不在任何持久artifact，不强制保存全部聊天。无Goal/动作/真实发送。

这证明已有私人状态在同一次正常对话中先参与C选择，原来源检索则影响后续可用知识；**不声称该视频观察已生成私人兴趣、验证安慰效果、形成S8新技能或实现新的压缩器。** 关闭机制只是测试投影消融，非第二C权威。模型为明示规则的本地HTTP夹具，非真实模型自主表现。

## 成本与范围

重启后同输入原/新各两次已有HTTP，input16384/output2048/timeout120000ms相同，无新付费阶段。INTERPRET请求JSON16918bytes两者相同；SOCIAL14489→16696（+2207bytes，包含补回真实来源）。它是内层request JSON字节，不是完整HTTP wire、更不是Token；fixture返回usage不作实际Provider账单。候选8次loopback包含额外消融/撤回两轮，不能与旧断言失败前4次累计简单比较。

benchmark.py从固定486 AST取原assemble，原/新在同66记忆/同预算/同Store交替各10次。旧来源缺席/新存在；每次MemoryService.read合计88→25（少读63个无关载荷），中位wall12.480993→9.4910405ms、CPU12.484167→9.4943375ms，原始每个样本保留。这里只是该合成热缓存本地装配；db.total_changes差0、模型0，非100k性能、真实Token或端到端延迟承诺。

related72.txt：72 passed24.02s，原Memory/Context/认知/隐私与隔离副本、平台撤权/BFF实际HTTP、私人倾向/原笔记召回/选择效率。首个夹具严格MemoryType错单列；消融首次错误移除已被选中的mandatory私投影，被PRIVATE_CONTEXT_REFERENCE_UNAVAILABLE正确拒绝，未改Core验证；改在原dialogue_private_refs候选选择入口关闭投影，保留原失败/诊断。未删断言/增加来源窗口/跳过测试。

## 本次用户五项验收映射

1. 原retain_input在认知前、原PrivateActivity/Record事务在后续投影前持久化；ContextAssembler只做预算选择，不破坏原经历。本episode私人关切和授权平台观察先持久化，普通聊天仍服从不保留。
2. 原PrivateActivity/Store/身份恢复沿用；本次临时摘录截短、进程重开（同进程关闭再开owner）及49虚拟小时验证，不冒称OS崩溃/真实49小时或任意语义摘要压缩合格。
3. PR18原同owner/Store的B站→QQ Kernel独立回读→NanaSpace HTTP/UDS资格直接复用（242 owned108），本次增加噪声人口/精确去重/重启回读，不再造跨端记忆。
4. 本episode私人投影消融改变C的LISTEN/CHAT，来源存在与撤回改变可用知识；原G独立未来迁移资格继承，不把本次开发修代码当主体成长。
5. 原有界Context/动态预算保持，两阶段对话不增加阶段；少读63载荷，补有价值来源确实增加2207请求JSON字节，真实模型Token仍未测。

剩余：更长多样经历经梦境摘要/原始细节竞争后，能否在不同topic/模型/多日维持合适注意仍需更广独立行为评价；有界64个同族候选仍不能声称完整语义召回。商业INTERPRET前按语义调用更广原平台背景及S3/S8因果迁移仍待，不把SOCIAL得到来源当原C已经形成兴趣。物理冷驱逐/恢复/隐私闭包/真实Token/多端/视觉算法与全部原A–H/最终匹配发行继续。CURRENT266+409不动，无新APK/真实模型/账号/手机/生产/自然度/实际长期资格。
