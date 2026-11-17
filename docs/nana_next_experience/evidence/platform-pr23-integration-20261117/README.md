# A吸收C PR23：原来源、投影和订阅连续性

A原e148e5df / Brain272，C固定a159b7ddb7c60ffaf893f607585531dfde0e9499，原A共同基线d5。PR23虽draft，A已检查固定源码、原消费者和自己的受控证据后采用以下修复；新候选接口仍按候选记录，不把整个PR冒称真实平台/视频集成完成。不读取C/B不可见工作区，不重写其算法。

## 原消费者与行为变化

1. 原normalize_dynamic→Bili account poll→原私人来源：转发事件保留原动态/作者的独立opaque标识及parent，不把转发者当原作者；原帖内容不导入。已有变化hash/retire路径使转发归属变化撤回旧源。超2**63-1畸形作者ID跳过，避免坏单条中断同批事件。
2. 原storyboard_samples：返回前再次读每个原frame和父源，撤回中的引用不返回成有效候选。旧源撤回分支本来已过，只有末帧撤回竞态在本轮旧失败；不夸大成所有撤回都未实现。不是后续任意消费者期间的原子锁。
3. 原FeedAdapter.receive：有界解析页分最多32有效条继续，最后解析批完成才提交HTTP validator，避免原只取前32后条件304造成后续35页条目永久漏读。同实例pending/页游标在断连恢复保留；未持久化跨进程队列，自动owner/runtime安装未建立，送达/ACK/跨日不冒称。

A用固定C四个测试文件、原A源码做新增函数差分收集：有效旧4failed1passed1.88s；合并后完全同测试5passed1.78s。转发parent/畸形ID/Feed第33项/末frame撤回分别真实失败，源撤回旧已通过。初差分选择器变量名遮蔽生成不存在路径，selection-first原ERROR保留，不当作旧Core失败或放宽断言。随后原NanaLink全相关、原平台桥/Runtime、最小便携闭包、A新S5/H1媒体多流消费者158passed60.04s；未重跑全仓/发布、未调用真实模型或账号。

## 候选边界与主线职责

public_video_cache_handle/with_current_public_video采用为原NanaLink下属候选原语及其开发工具：查原Memory DIRECT/PUBLIC/VIDEO/允许scope+当前runtime entity、原MEDIA_OBSERVATION、cache source/digest，可信同步materialized回调前后复查，异源结果拒绝。测试缺原观察/私源/错entity/撤回/异步惰性结果等守住原边界。但它不验证回调内部任意效果，调用方仍须原C/Manager/Grant/Kernel；不能直接用于不受信任插件。

该候选当前只有受控test/tool消费者，不是正式B站原片获取/账号文件归因、B22原生S5、私人媒体或模型理解。B22固定d63c1ba仍draft，A没有执行其未经当前资格的新文件或把旧bbc工具pin冒充后继。真实视频字节/整数PTS/流与时间原点/沙箱/同预算融合仍由B/C/A各按职责衔接，现有30秒16MiB原S5约束保持。

## 集成兼容

正常双亲merge唯一dev；代码无冲突，11仅双方追加冲突，A/B/C内容全部保留。C原长交接插在09顶部会把CURRENT推过原12288B入口，原文移至CURRENT后，未删除其固定源码/证据；A typed当前账本继续唯一权威。

C固定清单原样存fixed-C-manifest.sha256；A首先检查报错，发现它只落后此前PR24的4个Web文件。未覆盖B源码，仅更新该4项摘要，其他C/原Core源码逐项匹配；manifest-verification.json记录新旧锚和具体文件。不是抹去历史固定C清单或为目录整齐迁移核心。来源/Store/schema/SubjectLoop/权限/投递不另造权威。

另原272独立CI run43931262291/job133524426222实际94passed39.65s，client SKIP；ci272-core94保留，本批273自身CI待实读。158项是本批受控证据，不是真实QQ/B站/手机/商业视觉/自然度或长期生活。程序新模型请求0；新增末尾来源复查增加读取，采用C已记录的小样本成本边界，不另称本批P95/Token收益。无新依赖/数据表/Store/后台模型循环/部署。

## 继续

PR24/23已接实际产品与平台消费者；23新缓存接口仅候选。A继续原S3多动机/可靠反馈/G未见迁移，私QQ父源/隐私byte handle、私Bili保留前C、B22正式原生消费者与原A–H。9a2旧Core/Web候选不含264后继及B24/C23；CURRENT266+409，未重建APK/474MiB V4，最终匹配发行仍待，不称上线。

回退固定C三个平台模块/对应测试工具与清单到A e148，无Store迁移；保留A媒体/Growth与B24源码。修复回退会恢复已证实的来源/漏页错误，不建议以此做生产升级。没有执行生产或真实账号操作。
