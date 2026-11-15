# 匹配9291f1e：双构建、真实仓库下载与两个离线安装槽

[实测，S1/S2/S3/S4/S6/S7/S8及原发行工具] 固定源码9291f1e5f76f799b8b4bda056418dd390d1a57ea，Brain221，普通开发授权内隔离DEV。现役原portable构建器复用，285包文件，两次同SHA256 `1b71be7c7527f30d5458e9e2bf8605740122ea7887c22665f51df815d70937ef`，15088074bytes。Web在同一干净源码执行TS/Vite，原web_archive两次同`cf6a1916709531f7dee909ad3c139f88f623d1588b96d1d03e977565297fd8e6`，628308bytes。未重建474MB原V4、未新APK或新Release。

现有交付分支从5b4f589正常后继到1d820c73423b197bbd979dfe647802fa1024780b，仅新增deliveries/nana-space-next/server-9291f1e-candidate和该分支changelog；原CURRENT/所有旧交付逐字不变。该候选是可下载受控成果，不是已选发行、生产或总工程完成。链接：https://github.com/xuni7-ui/nana-core/tree/delivery/nana-space-next-apk/deliveries/nana-space-next/server-9291f1e-candidate 。dev当前Brain继续做唯一任务入口，不以交付分支旧Brain覆盖新源码。

实际过程分开：第一次从本地构建归档安全解包到/tmp/n929，使用CPython3.12.14安装私有.venv，pip --isolated/--no-index/--require-hashes和pip check通过，SQLite实际3.53.1、原生依赖受检，不冒充云端3.51.3。第二次新建bare depth1/filter=blob:none的GitHub克隆，用远端git show下载Core/Web/安全解包器/清单/探针，下载摘要与原构建相同；完全使用这次下载的Core在/tmp/n929d新槽离线安装并实际BFF验证通过。不是Actions artifact下载，也不是云端/异机安装；已知403没有重试。两次安装均无需网络pip取依赖，不升级系统库、不改sealed runtime。

原BFF/反馈幂等/十视图/同DEV身份重启/笔记纠错与撤回/隔离备份通过；已安装原INTERPRET→C→RENDER的笔记召回、实际SSE早期prefix、G独立评价/后续新笔记RENDER/撤回通过，6个loopback调用，真实0。继续同DEV原C梦境巩固→后续context改变→虚拟72h重启/来源撤回及冷副本回读通过，新增模型0；不是主链物理冷驱逐、回收、真实三天或异机DR。此探针复用原已修复的维护候选驱动，旧历史assert summary首次失败不抹除。

已安装Core中的高级链亦实际执行：原自身私问→正常D/C选原G→独立练习/评价/transfer→同主体重启→新文件实际原Planner/Kernel/Verify→宿主独立评估→D/C修订原私问；WATCH消融未采用新方法，关闭兴趣投影保留相同独立G事实但不修订；缺模型期间不提前消费关注、恢复后仅一次考虑。4个episode执行现有测试函数原样提取，所有assert保留，Runtime源码和Pydantic/crypto/cffi/PIL路径检查来自已安装槽；pytest仅复制到独立资格目录、不是Runtime依赖，也没有仓库PYTHONPATH。首轮漏外部pytest自身的py.py导致ModuleNotFound，补测试依赖后通过，未修改Core/断言。

静止二进制回退：同一已学习的DEV DB再由原C形成Question/Plan/Tendency，并明确PAUSED一个问题；关闭owner后929→独立安装d141986→929，身份/lineage/三类私念正文状态版本及G job相同，认知请求/周期/动作计数2/16/3均不增。新G元数据和原已有私人V2/V3/V4都可读；这不是266旧版本或跨进程热切换资格。第一轮Python tuple与JSON list比较失败，实际数值一致；仅把观察结构JSON规范化后重读旧槽与返回槽，原严格整对象比较仍保留。首错存档，不把失败叫源码退化。

当前固定929独立CI run43629019266/job132551411147实际276pass1warning147.33s；full/portable/client SKIP，不能冒充最新全仓。之前d141客户端93单测/3Node/160浏览器只归其源码；本轮仅同Web源码重新编译，不重复整套客户端验证。Java目录有限映射尚未编译/手机安装，当前APK409未证明支持所有新SDK，必须收口后统一资格。

全部调用都是受控本地fixture，真实Provider/账号外发/手机/生产/真人自然度/真实跨日长期成长均0或NOT_RUN。未读取私人历史、未formal genesis、未改变CURRENT266+409。高级能力仍有真实剩余：当前已修订origin版本解析、多动机/多时间尺度情感、广G独立迁移、检索/主链物理存储隐私、完整模型Token/费用/超时、多端/向导及原A–H。后续源码会比此候选新，应保持它自己的精确资格，不能叫届时最新发行。

可复制构建/解包安装命令与包内依赖在交付HANDOFF；外部探针及原始日志同目录，路径易失不保证换环境仍有/tmp。下一直接继续原G结果回到已被合法修订思想的当前版本；先真实旧版行为对照，防64候选后筛选漏召回、跨主体/范围/私域/来源撤回误绑，不新增第二思想库或全表遍历。
