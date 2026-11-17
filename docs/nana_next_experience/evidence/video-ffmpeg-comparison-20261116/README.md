# FFmpeg 画面测量与四方法初步对照

负责人B，基线A `90a31b6d10118061c55bf7d3821920b22713463c`；原 #19 已合入但仍是隔离工具。本增量调用本机 ffprobe/FFmpeg，逐帧采集 `scdet` 分数并按秒保留每秒最高分，再调用已有时间覆盖计划器。输入是明确本地文件及帧预算，输出采样时间、实际扫描到的末帧、扫描是否完整和计划空档；限制600秒、36000帧、256MiB源文件及120秒子进程超时。它不生产语义观察、主体状态或持久化；60fps以上长片可能触及帧上限，返回未完成而非虚报全片扫描。秒级聚合会漏掉同一秒内多个切点、运动/弱切点也不保证识别，时间规划覆盖不等于理解。探测后按秒聚合，尚无字幕/音频/ASR、拼版或真实接入。

复现：固定[dsh-see-now](https://github.com/SAOS-3624/dsh-see-now) `0b4bd110074b3e2cd043da8b078f7272589d50b0` (Apache-2.0) 和 [video-watch-plus](https://github.com/xinhailaopo/video-watch-plus) `8ca266f9cf9e5ffce7e9d424aa0e937a897b608d` (MIT，衍生上游MIT)。

```sh
PYTHONPATH=src:. python tools/nana_next_experience/experiments/compare_video_fixture.py --dsh /path/to/dsh-see-now --watch /path/to/video-watch-plus
PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_coverage_prototype.py tests/nana_next_experience/test_video_ffmpeg_probe.py -q
```

测试片由FFmpeg现场生成：12秒、4fps、黑场→白场→运动图案，已知硬切4和8秒；所有方法实际输出4帧，以切点后0.5秒内存在所选帧作为非常窄的定位指标，并对完整12秒计算相邻样本最大间隔。dsh实际原始管线自然选4帧（maxFrames=8是每图上限，并非全片预算），video-watch原probe/plan用骨架2、max4、burst1恰输出4帧。只有本fixture可作同帧数对照，不推论其他视频相同。

|方法|切点命中/2|最大间隔秒|
|---|---:|---:|
|均匀|1|3|
|video-watch-plus原版|0|5.87|
|dsh原管线|2|4|
|候选|1|3|

结果表明候选在严格覆盖目标和4帧预算下漏掉8秒切点，dsh此例切点更好；不要推广为整体优于任何上游。video-watch工具timeline以最后帧11.75秒为时长，表中统一用真实12秒区间。第一次上游plan把目录误填为输出文件导致 IsADirectoryError，改为明确文件路径后运行成功；原始错误未视为算法失败。相关11项测试通过（含真实生成视频及提前终止不假称完整扫描），FFmpeg 7.1.5。

`comparison.json` 为单次测量，包含各方法时间戳及未经归一的wall时间：候选含ffprobe与FFmpeg进程、video-watch含probe/plan两个进程，dsh只计预解码RGB之后的Node管线，不可比较为端到端性能。独立候选一次运行wall 0.2048秒、子进程累计CPU 0.2082秒、最大单子进程RSS 35072 KiB，合成源文件92371字节；单次数值不是总体峰值、正式基准或真实视频资源预测。此次真实Provider调用0，图像Token与账单未测；字幕/细节准确率、真实关键事件理解、重复观看缓存收益和长期视频性能均未测。

**下一步负责人**：B需研究覆盖与切点的预算取舍，增加运动/弱切、暗场、相似画面、字幕及重复观看对照，并测资源；NanaLink提供授权媒体/时间来源，A负责原S5/S2/C/S8及撤回的真实消费者。此工具不改A或平台权威，A尚未接线；撤回实验文件即可，无迁移。
