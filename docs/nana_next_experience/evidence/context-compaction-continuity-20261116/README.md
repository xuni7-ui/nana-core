# 长期自主活动：原上下文压缩与主体连续性

基线337fdb56915885d66fabc9bf2f9d4866ad162c6e / Brain255，A，唯一NEXT_EXPERIENCE_AND_TEN_DOMAIN_REFINEMENT；S1/S2/S3/S4/S7/S8 Advanced及三横轴的局部验收，不重定义基础63标准。该需求已有task_inputs/CONTEXT_COMPACTION_AND_SUBJECT_CONTINUITY_2026_11_16.md，复用原任务，不新建主任务、服务或记忆库。

## 核对结论

| 用户验收项 | 现役机制及消费者 | 本次证据 / 剩余 |
|---|---|---|
| 重要经历在压缩前持久化 | SubjectIngress.admission/ingest只保留获准且有持久价值输入；LifeApplication.chat opt-in retain_input先提交，PrivateActivity/Experience走原Record/Memory依赖 | 原用户输入已有；本次修复已获准交流记录晚于临时历史裁剪的真实顺序缺口。默认普通聊天/DO_NOT_REMEMBER继续不保存正文，不因“重要”推断绕过同意。 |
| 压缩/重启后恢复重要事件、兴趣和未完意图 | person_self.project/compact、private_intent.candidates/internal_projection、原SubjectLoop/Runtime调度持久引用与版本 | 新断点2场景；既有49虚拟h倾向/平台历史、原私人计划未来LEARN、quiet窗口跨重启换model场景复验。不是实际跨日/任意模型语义资格。 |
| B站、QQ、手机同一记忆与去重 | PrivateDynamicBridge→原Memory；原QQ surface/Kernel、手机BFF→IPC→同LifeApplication/Store | 原private_source、phone_http_continuity和platform_context_population复验：同identity/同source，重复平台事件同Memory、原来源撤回后各投影失效。手机是实际本机HTTP/UDS合成客户端，不是真机；用户原始消息的跨平台文本相同不自动合并，不混淆不同发生。 |
| 经历改变后续自主选择 | 原C读取获准私人倾向和当前有效来源，CommunicationPurpose→SOCIAL；原计划进入后续学习候选 | 既有49虚拟h重启LISTEN，去私念投影消融CHAT；短状态可退、长期兴趣仍保留；来源撤回不冒用。原C私人计划通过原G相关LEARN选择而非仅被动检索。fixture约定的语义/选择，不是真实模型情感质量。 |
| 有界上下文/成本 | ContextAssembler完整包预算；person_self.compact最多两交流摘录、每方384字及准确范围；LifeApplication最近6条/1024字，原私人状态按条件选择 | 新断点后原文完整落原Record，后续只投影384字/准确full_characters，原输入8192/输出2048/120000ms预算，每正常轮仍INTERPRET+SOCIAL。字节/保守计数非真实Provider Token；完整模型特定计量与长期资源仍待。 |

## 真实缺口和最小修复

原LifeApplication.chat先替换/截断_recent，之后才retain_exchange。合成在那个裁剪边界抛异常：正常两次loopback HTTP认知已完成，获准保留的用户输入已提交，但CONVERSATION_EXCHANGE不存在。original2.txt旧1fail1pass1.48s，默认不保留控制本来通过。

只把原retain_exchange提交前移到临时历史改写之前；同一原Record及依赖、相同隐私/保留/64来源界限，无表/版本迁移、新总结、第二Store或额外模型阶段。保留的是生成的语言候选/说话记录，不证明送达、阅读或其内容为世界事实；外部Delivery/UNKNOWN权威不变。

current2.txt：获准保留和默认不保留两场景通过。裁剪异常后关闭owner、重开同identity，重复message_id返回ALREADY_REVIEWED_NO_REPLAY、模型增量0；获准记录完整保存两方原文，下一正常交流恢复准确384字摘录；撤回原user Memory后两个标记均退出上下文。默认不保留在所有Artifact中均无两方正文标记。无actions/grants，不重放未确认外部效果。

最初新断言错误要求整个长原文进Prompt，而原设计有界384字；incorrect-full-prompt-expectation-first保留。修正为更严格的“重启后Record完整原文 + Prompt精确摘录/范围/原始长度 + 全文不注入”，未放大窗口或绕过实际来源，旧缺记录失败仍成立。

related51.txt：51passed35.05s，包含新2/原dialogue/80段历史/49h短长倾向/平台群过滤/实际手机HTTP/QQ假平台/原私人计划/调度quiet重启换model/Context预算与撤回/DO_NOT_REMEMBER。http25.txt另25passed25.78s，原HTTP连续输入/父回执/延期草稿与隐私；不相加冒充全仓。最后只强化默认不保留的正文标记检测并重跑新2，51/25按实际运行源码范围记录，不声称最后全量重跑。

## 成本、反例和边界

新2每正常轮仍2 HTTP，重复0。旧新断点前保留侧request bytes均12761/11171，非保留11869/10279，同预算8192/2048/120000；恢复后上下文摘录如current2，bytes不是Token。正常成功路径只是原有一次Record提交换顺序，未增加持久条目/索引/模型阶段；未测生产CPU、WAL或实际费用，新增维护复杂度为一处顺序调整和两边界用例。

这是可控Python异常/正常关闭重开，不是新SIGKILL、断电/fsync或真实长期生活资格。原SQLite/进程恢复证据沿原范围复用，不把本次异常说成断电实测。不保证撤回前已对外送达的字节能收回。默认无保留授权的普通文本跨重启不恢复，属隐私设计，不为连续性偷偷存全文。

PR14/17/18已合；新PR19固定86d1edb是覆盖时间原型未现役，PR20固定3d6475c是视频依赖/账号兼容候选，已读交接，不将其未合代码写成本批具备。下一由A集成PR20实际来源缺口/原S5调用再吸收B合格原型，继续内心情感/多动机/G广迁移/物理隐私/真实Token与原A–H。c1d候选不含本修复，保留历史资格，不重复打包APK/CURRENT；真实模型、手机、QQ/B站账号、自然度/实际长期/生产未新增。
