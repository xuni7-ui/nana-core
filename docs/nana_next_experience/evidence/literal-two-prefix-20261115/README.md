# 原Store两码点literal：复用L3/一个末尾键/来源先于正文

基线b6a9eaa（MemoryService原SHA2477b1772591b3368a82b4bfc5e818843bc869b5db1de10e50cf73a0d39a239b）。唯一主任务S2/S5/S8上下文质量增量，非语义检索、真人记忆或奈奈自主进化。原literal_notes允许两码点，但只有>=3个casefold码点能加速；10万笔记在原100ms内大批超时。

实现仅原MemoryService/原memory_terms：现有L3前缀覆盖短词中间位置，每个可索引的不可变笔记只补一个NOTE_END_PREFIX末尾键，覆盖最后两个码点。最多原4096原文字符的索引预算保持；更长、旧版未补项、缺索引均走精确校验回退，不假造空结果。不新建生产表/索引/Store/词向量/Agent，不改事实/事件/谱系、G16/32资格、模型阶段或Token预算。

先用最多65个去重且已符合来源/角色/范围/隐私的索引命中选择查询计划，不把65当召回/历史/兴趣上限。稀少候选只计算一次，并在读正文前重验完整条件；常见词按原rowid最新优先，SQLite CASE短路护栏确保正文标量子查询只在完整原授权/来源条件成立后执行。实际literal匹配/limit4/最终MemoryService.read/is_user_note均保留。co前缀显式绕开complete标记整段，不扫描每条笔记的相同覆盖标记。Unicode上界处理D7FF/最大码点，SQL参数绑定保留百分号等字面含义。

冻结v2协议16种请求×3次、同库/同limit4/同100ms、交替原版/候选；汉字中间/末端、emoji、百分号、Greek/Deseret、最高Unicode、casefold扩展、未索引新增、撤回、缺失、混合以及常见词。预期绑定由实际API写入返回的memory_id固定，private/其他实体/其他scope/伪来源/纠错排除。新普通Native实现实际结果：

|规模|原版正确/超时|新版正确/超时|原P50/P95 ms|新P50/P95 ms|
|---|---|---|---|---|
|1k|48/0|48/0|3.26/4.18|0.94/1.53|
|10k|48/0|48/0|24.34/26.79|3.45/3.95|
|100k|6/42|48/0|100.30/100.46|42.24/46.68|

全部误返回0。成功率分母每臂48，不是48种语义/人的体验；温度为同连接交替warm，非OS cold或生产SLO。每个结果含实际/预期Source ID、源码与驱动SHA，Native测量SHA071dd44f13d2a3e2584e07939edd6387ece1927ad7df80915410950c71666a97与当前业务文件一致。1k原冻结根的绑定后按精确note:short.N/noise/late引用只读重建，没有改其DB/期待标准。

物理代价与旧缓存边界：已有生成库在本隔离驱动只补派生End键，SQLite authorizer只准INSERT memory_terms；再禁止主库写入做比较，原主要表数量/identity保持，查询写0。1k补979键/0.030s/实际家族+159744bytes；10k9979/0.300s/+1589248；100k99979/2.489s/+16220160（约15.47MiB）。这是独立合成DEV原Store缓存维护，不是线上回填、物理回收、冷驱逐或DR。100k完整bigram需4381915行对比临时tail99978行，本轮没建bigram。新写入自然由原_index产生End键；现有大库在线增量补项尚未开发/资格，不自动重扫生产历史。

原生74相关27.32s通过，覆盖原记忆/隐私/注册副本增量撤回/上下文、原G16/32及TEXT独立评价和memory scale。正常LifeApplication新增两字“归途”通过原INTERPRET/C/RENDER、同identity重启/换fixture模型/纠错/撤回，保留完整wire账本断言。仪器化同方法common测试原版读70条合法正文，新版只读4；另外320条跨隐私/scope/实体或具SEMANTIC-DIRECT-user-note假头但无合法来源的干扰正文不被读取。旧源码此受控断言实际fail70!=4，未放宽原安全断言；最终原生14项阶段结果后增两字商业链/缓存删除断言进入74相关。旧Memory reader可读新End键，旧rebuild丢掉新键、新reader仍精确回退；只是Memory API资格，不是完整旧二进制回退/安装。

保留所有先前失败/拒绝：初版合成正文含controlled，意外也匹配co，期待集错误，两臂39/42、各12“假false”均是夹具真值错，不是源记忆错误；改输入生成器后冻结v2，原首次源与结果保存。只用range/tail的1k P95略差、10k P9527.56→43.37，不集成该方案。首次adaptive SQL留下CTE尾逗号语法错，保留。10万double-pass45/48三次da超时；复用小集合后仍45/48，定位是大posting先物化；早期已授权索引探针才48/48/P9556.06。Native持久End行版独立实测P9546.68，不把TEMP原型当已接线。一个Native fixture缺observed_time_us，原DTO正确拒绝，补实际101、未改契约。

原20万多样库/workspace/nana-preserved-200k-20261114未打开/改写；旧144/144与原两次超时历史各自保留，本次不是重跑它或宣称所有Memory统一。Core/Iris活索引绑定、更广语义/大批未索引/长期/跨存储恢复/物理隐私仍待。现100k开发根含新增End缓存，早期只读回放SHA只指当时状态；fact未改，当前物理SHA不能冒称仍等于早期值。

前继49d独立CI43709063393/job132796594466实际670pass1warning257.02s，client/full/portable SKIP，仅该源码的targeted。当前CI affected selector复用原组，memory.py也选已有note/G/context测试，不新增框架。没有新包/Web/APK/匹配安装、真实模型、账单、账号发送、手机、生产、真人自然度或真实跨日成长；Provider0/Token不测，CURRENT266+409不动。SQL字节/毫秒不冒充模型Token收益，原C独立判断与120s预算不改。

影响/回退：仅派生cache多一行/笔记及两码点查询计划；无格式/主表迁移，旧程序忽略新命名空间，缓存可按原路径再生。正式旧reader/便携安装回退仍待最终匹配发行。源码/未知文件/旧交付与两个保护工作树不删除，Corpus位置见corpora.json。

下一回原情感意义/多时间尺度和自然交流策略的可靠反证如何改未来取舍；并继续旧库有界补项、广语义/真实绑定、物理隐私/Token费用/多端产品及原A–H。此次短线索闭环只缩小该具体资格差额，不是总任务完成。
