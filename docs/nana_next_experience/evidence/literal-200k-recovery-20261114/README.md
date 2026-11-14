# 20万原合成记忆恢复与两查询诊断 — 2026-11-14

[实测/原S2-S8上下文质量，非新工程] 运行源f93bcfa，MemoryService源码未改变。旧/workspace/scratch/nana-memory-diverse-v3已随环境重建丢失，不假称复用其DB。仅用原tools/nana_next_experience/memory_diverse_compare.py恢复200k这一种规模，baseline-ref c9f7518e7ac61e469ec129ce3cc6e553fd1b094b；未重跑1k/10k/100k。FROZEN_SPEC的48个case/expected_refs与原final-FROZEN_SPEC解析内容一致，同limit4/repetitions3/100ms；新随机Store ID/布局不等于旧DB逐字节一致。

原旧记录memory-diverse-gram-covering-replay.json为142/144、2timeout，仍保留。此前next文字把预算写150ms并指initial-result文件，属于文档笔误：实际一直100ms，真正两超时在covering-replay。已纠正README，不修改原预算/失败或运行源码。

新恢复库同一个原Store交替比较：c9基线0/144、144timeout/P95100.42ms；当前144/144、0false/0timeout、P5017.23/P9520.34ms，生成+比较206.02s。是当前新恢复库warm/首样本混合、不是OS cold或生产SLO；不能冒称修好了历史随机超时。全部原expected source绑定实核，200k中仅一部分是可资格bench笔记，不称20万条都可召回；没有语义、2字符、真人或Core/Iris活库绑定资格。

仅原两次超时的astronomy0.absent、astronomy2.eligible，各3次/100ms，做同库交替SQL形态隔离对照。NOT EXISTS原型6/6但P9528.51ms vs原18.79ms；NOT IN原型6/6但P9531.02ms vs原20.57ms，均0false/0timeout。原SQL/原型source SHA及EXPLAIN QUERY PLAN在JSON，两个最小patch留档且均不集成。没有为了“修复”而增加更慢查询、索引、缓存、表、依赖或限时。原Store前后snapshot/total_changes均相同。

原诊断脚本为了只读验证做两次全Store snapshot，增加诊断前后内存/耗时而未计入每个查询；首轮已正常结束/exit0，非卡死或OOM。完成后将复跑助手改为PRAGMA query_only=ON+data_version/total_changes，避免未来大库全量快照。safer-replay-not-executed.py是未执行的后继助手，不充当首轮脚本指纹；实际执行的两个MemoryService SQL原型完整源SHA与归档patch核对一致，运行源码未边跑边改。

实际主DB2037067776bytes/分配2037063680bytes，4,770,998 terms；terms表305680384bytes，term lookup341385216bytes，覆盖头索引6070272bytes，WAL关闭后0。见physical-after-recovery.json，反映本合成库布局，非物理回收、256MiB上限、归档或DR资格。仅两个命名空间recorded.conversation.input/synthetic.diverse；无私人历史/真实模型/外部费用，未新Core包/APK/CURRENT/生产。

本次关闭的是同spec的新环境有限复测差额；保留旧两次超时并继续2字符/大批未索引/更广检索学习、真实绑定、长期/物理存储等原剩余项。下一回通用模型产品/实例与内心情感主链，不在没有新证据时反复跑这批大型数据。

复跑原工具：python tools/nana_next_experience/memory_diverse_compare.py --root <fresh-owned-synthetic-dir> --sizes 200000 --baseline-ref c9f7518e7ac61e469ec129ce3cc6e553fd1b094b；原TMPDIR=/dev/shm、PYTHONPATH=$PWD:$PWD/src。必须预留约2GB完成数据与过程余量；不在未知/真实Store目录执行。现用/dev/shm/nana-diverse-200k-20261114是易失研发路径，未上传整个DB，原源码/证据已保存。
