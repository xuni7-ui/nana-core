# A采用NanaLink PR20固定增量

A原基线ecdb15c / Brain256；唯一负责人A做本次最终集成，原候选实现归NanaLink。固定PR20 3d6475c8ad03fad77f1f6b73c67db09f9537b02d，原基线46fa已是A祖先。正常非ff合并，不创建新开发分支、不重复平台/视觉算法或第二主体。09/11发生文字冲突，保留A最新typed CURRENT/全部记录，并附原C新增交接/日志；原A Core源与新压缩顺序不被旧快照覆盖。

## 采用的真实能力

- 原BilibiliReadPort在返回网络结果后重新核验原C/来源，再将原选择Memory作为VIDEO_READING父依赖。撤回选择来源沿原Memory闭包撤回视频、帧、Kernel可读结果及H1 MODEL_DERIVATION；原World信念回UNKNOWN，重启仍不可读。撤回发生在I/O期间则不保留结果、动作UNKNOWN，原请求不重取。不同来源的相同视频不误删。
- BilibiliSourceAdapter.history在原64上限前按scope/entity/privacy/current筛选，65条不可读私人视频不再挡住合法视频，不扩大上限/权限。原视频能力状态跟随当前实际消费者/授权/可选解码器，配置不当作在线或Grant。
- OneBot单个畸形帧/事件丢弃计数，账号错配/ID碰撞仍断开；在途RPC保持UNKNOWN/不重发，修复重连slot交接及迟到账号回执将断线误标ONLINE的竞态。全部由原适配器执行，没有第二投递器。
- 原Store的storyboard_samples v1只是已观察最多三帧及字幕范围的只读候选交接。保留时间/来源/隐私/撤回、明确缺时长或空档，不猜账号或未观看内容、不复制图像正文。当前消费者只有开发资格工具/tests，不是现役S5视频算法；未加入便携runtime名单，既有263模块闭包独立检查通过。后续真正进入现役链再按实际消费者收口，不把目录存在当正式能力。

## 旧/新及验证

original-lineage4.txt：ecdb原实际3fail1pass2.48s，精确候选测试源（从固定Git提取到隔离/tmp），上游withdraw后视频/帧或H1 World仍有效，以及I/O期间withdraw未阻止保留，独立不同来源控制原已通过。没有改旧源码/放宽来源断言。

integration106.txt：采用后106passed35.09s，原NanaLink全定向组、原B站读取/实际PNG帧/H1语义/UNKNOWN、当前社交判断及新压缩2项。closure-and-bridge30.txt：另30passed9.96s，最小Core静态闭包/缺可选依赖启动、原同主体可选媒体及平台桥。不是全仓/真实账号或手机；不合并历史测试数冒称当前完整资格。

B-handoff.json：A实际使用B PR19固定86d1edb的50行原型（SHA6b11af1e8ee253ef987e5cceb0284e2ba4427fa710411d930466a6f15ee201fd），经原VIDEO_READING/帧Memory投影0/5/10秒，输出按原Memory回映并报告空档，源withdraw后投影失效。100次本地投影中位0.2456ms/P95 0.3368ms/CPU0.02649s/峰RSS46412KiB，额外网络0/模型0；不是视频语义召回、全片覆盖、实际Token或生产性能。初次直接脚本PYTHONPATH只含src导致tests不可见，invocation-first保留；改用python -m tools.nanalink_video_handoff_qualification，未改代码/断言。

## 兼容、指纹与回退

无schema迁移、额外运行服务、强制模型调用、付费/账号或真实发送。manifests/nanalink-01.sha256原候选记录保留Git3d6475c；A当前集成只更新其中application.py摘要以匹配ecdb压缩修复，其余所有输入保持候选值。原始候选与现集成不混称，新的整体指纹另见source.sha256。

本批最小Core263模块静态/实际隔离启动闭包通过；候选只读交接模块不属于现役runtime消费者，不冒称已进入包。c1d交付历史候选不含此后修复，不重跑整套发行/重打APK；CURRENT仍266+409，未上线。

回退本次合并源码，不回滚或覆盖运行Store；已撤回来源不因旧版读取而恢复，旧reader另遵从原合同，不将无迁移当任意旧版资格。B PR19下一由A按收益决定保留实验并明确现役未接；B继续真实FFmpeg/两个原始算法对照，NanaLink继续平台来源，A继续原S5/S2/C/S8接线及情感多动机/G广迁移/物理隐私/真实Token/全部A–H。真实模型/QQ-B站账号/手机/生产/自然度/实际长期均未新增。

A集成NanaLink输入清单SHA256 `b203d234c7e49dbdf654cb7e498cef2c1e59833ab69315f99707d576eed601a1`。
