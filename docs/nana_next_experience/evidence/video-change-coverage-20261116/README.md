# 变化与覆盖之间的受控换帧

B负责；基线90a31b6及本分支既有FFmpeg实验。先调用原覆盖计划器，再尝试把低变化候选替换为高变化候选，仅当替换后的最大时间间隔不超过用户指定目标；如果初始候选本来无法满足目标，只允许间隔不恶化。最多尝试64个高变化候选，预算/输入上限复用原计划器。变化不等于语义重要性，缺帧和扫描不完整仍必须原样报告；此函数不授予观看/存储/投递权限，不提供新的主体权威。仅本地实验调用，尚无现役消费者。

复现：用同分支compare_video_fixture.py指定两固定上游，或用它的FFmpeg命令生成同一黑场→白场→运动12秒片，然后：

```sh
PYTHONPATH=src:. python tools/nana_next_experience/experiments/video_coverage_refine.py /path/to/video.mp4 --budget 4 --max-gap 4
PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_coverage_prototype.py tests/nana_next_experience/test_video_ffmpeg_probe.py tests/nana_next_experience/test_video_coverage_refine.py -q
```

FFmpeg 7.1.5生成片4帧预算：最大间隔3秒时选1/4/7/10秒，切点4/8秒仅命中1/2；最大间隔4秒时选4/8/10/11.5秒，两切点均命中，实际最大间隔4秒。2个切点之间间隔4秒，任何同时选中它们的方案都无法满足3秒间隔，因此不能把结果说成同约束改进；该实验展示不同允许覆盖缺口的取舍。15定向测试通过，包含实编解码素材、严格/放宽取舍和稀疏输入反例。无真实视频/字幕/语义理解/真实Token/账单资格。前述四方法对照及真实候选漏切结果保留，不覆盖。

接入：仅供B实验继续选择；NanaLink拥有平台采集/来源，A拥有原S5及主体的消费与撤回。下一B评估短暂文字、暗场、弱切、遮挡、跨时段动作和资源/缓存；当前方法局部贪心不保证全局最优，仅检查最多64项信号，不可宣称真实任务召回。撤回两个实验文件即可，无数据或协议迁移。
