# 视觉扫描完整性反例与修正

负责人B；A后继基线b5481b5。先前版本只检查首末帧距边界一秒内，不能证明中间帧有被测量；例如12秒标称48帧只读取首尾两帧也可能错误标complete。现读取原视频流声明帧数、平均帧率和开始时间；要求所读帧数=有变化分数的帧数=声明帧数、严格递增时间戳、零起点及合理边界，才报告`scan_complete`。缺元数据、帧数不符、重复时间戳、缺分数、非零源开始或边界异常一律False，不改变候选选帧或调用模型。

该标记仅说明FFprobe声明数和观测解码/时间/计数相符：不证明源文件未损坏、不证明语义理解、不证明任意VFR文件的全部原始帧。声明数不可靠、VFR尾帧间隔大、容器无nb_frames或视频时间偏移可保守误报不完整；绝不能把False当用户视频失败或触发自动重试。真实源/混合时轴由NanaLink和A共同核验，输出仍为无持久化的隔离候选。

定向证据：`PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_coverage_prototype.py tests/nana_next_experience/test_video_ffmpeg_probe.py tests/nana_next_experience/test_video_coverage_refine.py tests/nana_next_experience/test_video_short_detail.py tests/nana_next_experience/test_video_local_change.py tests/nana_next_experience/test_video_audio_probe.py tests/nana_next_experience/test_video_caption_acoustic.py tests/nanalink/test_bilibili_video_history.py -q`，43通过；含48帧生成片、首尾有帧但中间缺帧、重复PTS、缺分数、原Memory来源撤回。此前`video-short-detail-20261116`指纹对应7d58dfe旧probe，本目录指向本版；保留历史。无真实视频/长片/跨端/模型/Token/生产资格。删除隔离更改可回退，无数据迁移。
