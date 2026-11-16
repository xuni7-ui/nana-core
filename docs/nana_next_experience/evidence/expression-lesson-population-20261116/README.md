# 原G延迟资格在后续交流中持续生效

基线46fa16b/Brain252；S2/S8/S7 Advanced局部消费者连续性修复，继承原G评价，不把基础表结构或标签当作新成长。

## 原版与新行为

原learnable已对USER_PROVIDED_REVIEW/PROJECT_SYNTHETIC分别在32窗口前筛选，直接复用；expression_policy仍先取所有证据群最新16条ACTIVE lesson，随后才读来源。一个早提出、后评价的候选，activation不会改变lessons.rowid，因此另一群16条较新课题能永久挡住它，即使它刚通过原G评价/激活且支持来源完整。

original2.txt旧1fail1pass：正常G先从一个Human PARTIAL报告形成候选但不评价；原G从17个独立PROJECT_SYNTHETIC报告激活16个课题；之后两个新的Human REJECTED报告才使最初候选通过原test_lesson/activate。未手工插ACTIVE行，未改原评价或凑阈值；PARTIAL提议不是它自身的资格证据。原lesson ACTIVE、current_support为真、当下Human资格成立，但同主体重开后正常INTERPRET/C/SOCIAL给出baseline because method missing。控制0条其他lesson原本通过。

新查询沿原lessons→experience→反馈Memory/Evidence/Artifact，在原scope/privacy/current与来源命名空间约束下，按当前资格群在LIMIT16之前筛选。CROSS JOIN固定header在payload解析之前，保留严格current_support、sample_from_memory与origin再次检查；不提高16、不给另一来源群补分、不建表/索引/新学习引擎。

current2.txt新2passed2.51s；同主体重启后的普通交流重新读到原已资格方法，并沿既有LIVED_LANGUAGE/例子投影影响受控RENDER。同样两次HTTP、原C仍CHAT，没有新认知阶段；这是原方法重新进入现役路径，不是新算法学会自然交流。撤回原候选的PARTIAL支持来源后，另外两条Human资格仍成立，但原方法不再可用，后续普通交流回到baseline；不借新证据继续冒用已撤回的原课题。

related43.txt：43passed13.62s，原语言评价/群隔离/阈值/反例/模式、反馈四模式/长回复绑定、portable迁移/进程恢复、原G与隐私；不是全仓/真实模型/真人自然度。新目标fixture所称Human仅测试声明的报告来源，所有数据是受控合成，不冒充实际真人意见、阅读或送达。

## 资源与代价

相同16拥挤情景，原/新普通首轮均INTERPRET+SOCIAL各2HTTP；内层request JSON总量31194→34287bytes（+3093）是恢复规则与同群示例的上下文成本，不是实际Provider Token，也不宣称更少模型费用。配置/预算未改，真实Provider用量、自然度和账单未测。

profile.json用同一实际合成Core Store的17个ACTIVE lesson、精确46fa旧函数/新函数，5组交替只读调用：MemoryService.read197→63；wall中位23.942→9.953ms，db写0、测量内模型0。测量与定向回归并行，非独占CPU、P95、10万lesson或生产性能，不能外推。来源群在SQL筛选会解析对应候选反馈元数据；仍可能随当前scope活动课题增长扫描更多头部，本批未新增索引/缓存或宣称无界性能。

## 边界与回退

最初重开后错误使用旧LanguageService的已关闭连接，closed-helper-first保留；改为当前原RecordService，没有改变运行合同或放宽断言。原Memory.set_lifecycle会撤销派生，未把其当成无损归档恢复，本批没改该逻辑，也没有宣称物理归档/回收闭包完成。

所有来源/规范/Model Authority/G门保持。回退lived_language.py，无schema迁移。原9a历史候选不含245–253，CURRENT266+409不动，本批尚未匹配安装/新APK；真实模型/手机/QQ-B站账户/生产/自然度/实际长期未新增。独立46fa CI43775156209/job132999860363已实读638passed3warnings275.85s，仅targeted，full/oldSQLite/portable/client均SKIP；不是本批源码CI结果。

下一把已经连续完成的Core修复固定为同一便携候选，复用已验证Web输入/原构建器/wheelhouse完成一次匹配构建、离线安装、原主体/反馈/撤回与停机回退，不每个补丁重打APK。其后仍继续情感/原C持续策略/G更广迁移、B视觉固定交接及全部原A–H；高级长期总任务未完成。
