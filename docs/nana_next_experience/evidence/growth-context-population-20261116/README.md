# 原G以情境分配注意窗口，重复练习不挡住真正复用

锚35740e7f2f518b9b2607bbd952759aa80683cf4c / Brain260，A；原S2/S3/S4/S6/S8 Advanced同一链路，不扩G16/32笔记资格或新建学习系统。

原实现仍以全体可见评价最新32条为候选，然后project独立查资格。原G对同一个练习case的32个重复校验都可算数学SUCCESS，但不算未见迁移；它们挤掉了原G练习后实际不同数据Kernel/Verify成功的旧一条。original2.txt旧1fail1pass1.31s；没有手插SUCCESS/ACTIVE、跳过练习或伪造32次实际成长。

## 实际修复与边界

复用EpisodeLearning.view已有lesson_id/context_digest语义，将原32候选窗口分配给不同可读情境。只读查每情境至多32评价，逐条原project资格；组头本身不等于有效资格。保留最新合格评价后再按实际时间/rowid排序，最后按lesson去重。已在原全局前32里的合格候选仍包含于新候选范围；没有合并、删除或改写任何Record/Memory/评价，也没有将同一练习算成独立经历。

每次读中，原project一旦确认该情境输入属于原trial训练集合，该context_digest已绑定context/data，剩余同组副本不用再次完整读取。仅局部set，跨调用不保留、不替代来源/隐私或独立裁判；新来源/其他情境继续资格检查。无新模型阶段/Planner/Store。

当前9项通过4.14s：0/32练习噪声都正常D→SELF/C形成自选私人问题，相同条件不重复调用、没有新Goal/动作/Grant；259的PUBLIC/私评价隔离及同身份重启保持。包含新组头只是未核验USER_STATEMENT时回查旧独立校验、跨组按实际最新合格结果取舍两反例。所有SOURCE/held-out/训练重叠不放宽。

新增两个普通可重建元数据索引：strategy_growth_order_lookup、strategy_growth_context_lookup，原owner自动建、无schema号变化/权威字段迁移或新依赖；查询不强制INDEXED BY，旧只读投影可无新索引但性能未资格。初稿漏旧schema guard导致7/12打开失败（legacy-index-first旧2fail1pass），已补13前跳过；7/12/13均能打开/重开。related57.txt：57passed22.58s，包含原G/反例/训练隔离/内心/来源/身份/上下文/隐私、portable包与schema通用性。不是全仓或生产升级资格。

## 原链路消融与成本

runtime-ablation.json：从固定357源AST提取精确旧opportunities函数，其他Runtime/G/C及两索引相同，同内容合成经历/同配置预算。原32练习副本→正常D期间SELF0/新疑问0；新分组→SELF1/新疑问1，Goal/动作/Grant均无新增。正常刷新重复条件不重调，真实Provider0。不是随机新Agent或一段预写的内心独白；现役C实际从原GROWTH_CHANGE生成原PRIVATE_QUESTION。

新调用实际账本budget为input65536/output2048/timeout120000ms/cost0（fixture），input_bytes108329/reserved_bytes120618，非实际Provider Token/费用。恢复有意义认知本来会花一次已有SELF预算，不以旧零调用更便宜当成功标准。首次ablation头部文字错标output1024，原JSON保留；后继从实际request Record读取budget2048，不能拿错标签证明预算比较。

read-cost.json：同一真实合成Core Store，5轮交替关/开本次局部训练重叠复用，候选结果全相同、db写0/额外模型0。project次数33→2、MemoryService.read238→21，wall中位15.456→1.703ms。非独占CPU/生产/P95或实际Token。

metadata-cost.json是1k/100k文件型SQLite元数据夹具，不是完整Core语义、真实活库或磁盘P95。原SQL/新SQL由实际函数捕获，SQLite3.53.1，每项3样本；索引计划实证global顺序与context/time/rowid两个范围。100k各情境不同：原索引旧头查询中位97.044ms，新两索引分组头.293ms、单组成员.010ms；仅加order时成员30.508ms，context索引有实际用途。100k/31重复情境/同钟：新两索引头303.943ms、成员.068ms；旧含order头.039ms但不进行独立分组，两者语义不同，不能宣称完整新方法更快。取不足32情境仍可能遍历大量元数据，前台延迟/更大稀疏学习史与调度分片仍需资格。

100k索引增加实际文件分配约12.7–12.9MB，明确空间成本；原100k无索引新范围查询未运行，不冒称PASS。/tmp存放的文件型库不是云端硬盘/旧20万库，不能改写旧P95。Source原文/体验未物理回收或截链。

## 继续主任务

每轮最多32情境×32历史资格检查，训练重叠常见副本可提前停止；多于32个不同不合格情境、组内32无效source后更老有效source、更多课题公平和已处理机会在quota前过滤仍未全部解决，不将本批说成任意长期规模资格。

下一已定位同一SELF路径会把很多重复数学评价正文放入一般Context，实际新请求108329bytes。先比较完整请求中的重复内容，保持所有原记录、次数、依赖与C判断，仅对当前growth认知做可验证的等价报告压缩，不隐藏真实不同经历/反例；随后继续原C情感/多动机/策略、G广迁移、B真实视觉/原S5、物理隐私/真实Token及A–H。原CURRENT266+409不动，c1d历史候选不含256/257/259–261，无新APK/真实模型/手机/生产/自然度/实际长期。
