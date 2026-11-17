# 原S5视觉覆盖→S2→同C私人疑问：不能把音轨尾部当已看见

A原631444986043bb3153a772983a20090126daee91 / Brain273，Advanced S5/S2/S6/S3原因果路径，冻结Foundation与63标准不改。B22 d63时轴/音视频覆盖反例作为核查线索，A没有复制B算法或另建视觉主体；本批直接修原MediaDecoder→PerceptionService→H1消费者。

## 旧行为的真实错误

本地生成同一Matroska，4帧video1秒+audio3秒。原S5最后帧source_interval_s无条件延伸到容器3秒；原H1 MEDIA fixture/ground结果unobserved_gaps=[]。original1.txt有效1failed1.27s，失败于原主链真实返回值，不是仅缺新字段。未说视频文件只有1秒：duration_s仍是3秒容器声明，错误在把最后图像当覆盖后续2秒。

现在既有ffprobe同一进程读取实际frame duration_time/旧版pkt_duration_time，最后帧只覆盖到min(容器时长,PTS+实际帧duration)。完全未知或N/A时仅有采样点，不按帧率、平均时长或容器尾部猜测；可用旧字段仍复用。非有限/负数/超原30秒span拒绝，原bwrap/CPU/16MiB/30秒/8帧限制、来源和画像UNKNOWN都不变。新frame interval .75–1秒，原H1保留[1,3]为未观察间隔；原source/part验证沿用，无新DTO字段、数据库、索引或模型阶段。

related62.txt 62passed20.51s覆盖原S5/H1/H2、音视频分离、实际音轨/多流、源撤回及语义资格。随后未知时长2项1.93s；再补旧字段可用兼容，仅最终3项2.29s，不称67项一次回归或再次全仓。N/A/缺duration是对真实ffprobe输出的有界元数据可用性消融，不冒称实际录制设备已遇到这些码流。

## 同一编码字节、同预算、同C行为消融

same_input_c_ablation.py从固定631原Git AST取decode，沿原_run/bwrap和原Store/H1调用，同一首次失败输入97261B/SHA a8dd42efda06fde8aa32055bb6eb4decb87b2b2d2f29879ceb849aff219b783e。不是两份约略同色视频。

两侧均4子进程（ingress3/package1）、1实际loopback MEDIA请求、1原C fixture认知；同budget、真实完整HTTP input各20219B、源Memory文本各1479B。变化仅ffprobe frame元数据321→485B(+164)，无新增模型请求；fixture usage数字不是实际Provider Token/费用。真实模型/付费0。单次含初始化与原C的wall652.25→591.49ms、parentCPU192.85→132.69ms不用于宣称P95/性能收益，未统计完整子进程CPU峰值。额外私人疑问是有意义原Record，不说Store零增长/物理回收。

同一原C消费者读取真实源覆盖元数据（固定受控规则，非生产硬编码/通用视觉模型）：旧误以为无尾部空档→原C WATCH/私人疑问0；新保留未知→原C REFLECT/PRIVATE_QUESTION1。没有先生成公开回复再补独白、无Goal/动作/Grant；新疑问依赖原源，撤回后current_support失效。这个证据展示可靠观察如何改变后续自主考虑，不声称学会一般视频理解、自动S8学习、情感成熟或长期人格成长。

初C消融夹具误把WATCH填入proposed_operations（原合法操作不含WATCH），c-operation-first保留；仅改回原合法DRAFT，preferred_behavior仍分别WATCH/REFLECT。未改C解析器/权限或放宽断言，原S5/H1旧失败独立成立。initial-codec-ablation保留早先不含C的同源结果，不挑选新跑结果替代首错。

## 当前整体验收节点

实读原273独立CI run43932489041/job133528712854：129passed35.24s，client SKIP；日志保留，本批274自身CI待实读。用户最新三方向原文已归现有task_inputs及08/mission，不创建任务体系。下一固定收口后的同源Core/BFF/Web候选，复用原安装/交付/综合探针，观察同主体私念/交流/记忆连续/G后续迁移，不再无止境做局部修饰；S3长期因果及S8/S10渐进闭环继续。

B22原片归因/正式适配/整数PTS/原点/旋转/长窗口仍未接；本批不改原容器时轴基准，不能把时长尾部修复说成完整视觉融合。私QQ父源、私Bili保留前C、冷历史物理隐私/DR、真实Token协议/产品及原A–H仍待开发/资格。9a2历史Core/Web不含264以后，CURRENT266+409，未重打APK/生产/实际手机/自然度/实际跨日长期。回退原perception.py到631，无DB迁移，不建议恢复已知错误覆盖作为生产修复。
