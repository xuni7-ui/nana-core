# 高负荷下原C的明确兴趣选择，不被固定REST覆盖

[实测 Advanced S3/S4/S6，原A–E自主性续审] 起点85a038b7c4e180209f3e99b8a3b828b2a81507d2。复用已存在Appraisal/Motivation/C判断和正常Runtime/Provider，不建立情绪总分、第二Planner/Store或生活优先级表。

旧机制已有light兴趣例外，但当前cue.cognitive_load=HIGH且attention_demand=HEAVY时，即使原C模型已明确选择有源私人兴趣的REFLECT/CREATE/LEARN，策略仍强制REST。正常LifeApplication→原Runtime.step→SELF HTTP→同C真实对照3fail2pass3.58s：三种明确活动都被REST替代，自主REST和明确REFLECT禁止保持。初始较小3场景1fail2pass2.19s也保留。负荷估计没有证明现实容量不足，不能反过来等同主体只想休息。

最小修正保留原支持兴趣判断，并允许“当前C明确选择+原有独立兴趣支持”在高负荷时继续竞争。未明确选择的重型默认仍保留原轻量决策；无支持、高风险、明确禁止、原接收者边界、资源/预算/并发、执行Grant/Kernel都未更改。REST仍以同样来源/RELEVANT强度出现在实际模型前的motivations，主体可以选择它；并未移除条件或把工作改为强制优先。这里只形成原意图候选或内部思考，不创建执行权限，也不证明重型研究已实际执行。

A现实权限与B实际容量保持，C接收者边界保持；本批定位的E是“负荷估计→在C已明确判断后永久覆盖所选重型兴趣”的开发者硬编码，D自主休息/取舍仍由原C可选。本结论只覆盖有依据且明确考虑的方向，不宣称全部A–E审计完成，也没有把所有新生未保留兴趣、社交节奏和人格取舍都资格。

新15pass10.20s，最终199相关52.93s，含原OPEN_LIFE高负荷默认/来源撤回/注意、到期承诺/明确复查、实际Provider预览成本/上下文/每日预算、原G独立评价与后续私问、关系自主性、Precision原规划/生命周期。没有削弱旧断言。各HEAVY受控场景均1次SELF/53288inputbytes/65577reservedbytes（明确禁止55701/67990），旧新相同，预算32768/2048/120000ms不变；没有新Prompt、schema、模型阶段、配置或按秒唤醒。这是wire bytes不是实际Provider Token或费用。

环境首错完整区分：首次回归命令把Precision路径写成不存在tests/precision_v2，0 tests；改实际路径后，精确旧对照及相关回归同时因8GiB cgroup上限被kill137，memory.events显示2次OOM。/tmp和/dev/shm都是tmpfs，约8GB不可换出shmem；这不是Core用量断言失败。当前根盘实际有7.5GB可用，与历史ENOSPC不同。确认20万合成库无进程持有后，将13个文件含DB/WAL/SHM/锁与privacy旁文件复制到/workspace/nana-preserved-200k-20261114，逐文件SHA/字节相同再移走旧tmpfs副本，原路径保留symlink；无数据内容丢失、不触碰正式Store/Git/未知文件。释放的是环境tmpfs副本空间，未做Core主链归档/逻辑删除/容量治理。严格无symlink入口后续应使用实际磁盘路径。

迁后串行重跑：精确85旧3fail2pass，当前199pass；OOM kill计数仍2。库字节保留不代表迁移后性能相同，20万P95仍只归先前RAM样本，没有重跑或改写成磁盘性能。空的被kill日志没有pytest结果；tool实际exit137和cgroup观测见environment-termination.json，不能假造通过。该环境事件不升级为重复治理工程。

前继85独立CI run43630443137/job132555800111实际323pass1warning118.97s仅归前继；client/full/portable SKIP，不外推本批或全仓。固定929候选的两次构建/真实GitHub下载/两槽离线安装、静止929→d141→929仍可下载，当前后继不在其中，不为此局部修改重打APK或每次重构建。

没有新真实模型、手机、生产、真人自然度、真实跨日长期成长、正式genesis或私史操作，CURRENT266+409保持。下一继续原INTERPRET可靠情境意义→同C当前评价/私人倾向/持续交流方法→真实收件范围明确反馈→原Experience/S8反例的因果链，先读现有communication方法/反馈消费者，复用已完成187–223，不塞字段绕过INTERPRET/SELF角色；重点让短状态与长关系分开，不以沉默当效果。其余原A–H、多动机与情感、广G独立迁移、跨topic当前思想、物理存储隐私、完整真实Token/模型协议/多端产品与最终匹配发行都仍未完成。
