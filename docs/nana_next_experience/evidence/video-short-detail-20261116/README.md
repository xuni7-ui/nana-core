# 短暂文字帧的候选保留反例

B负责，基线A 90a31b6，继承本分支 860e9ae 和 9fd98e8 的初始FFmpeg/换帧实验。12秒、4fps灰暗背景且周期亮度变化的FFmpeg合成素材中，仅3.0秒这一帧有文本CODE7，3.25秒已消失。旧每秒只取最高scdet得分，保留3.25而丢失真实有字的3.0帧；`before.txt`保留原失败。现改为每0.25秒桶的最高变化帧，使该输入的3.0秒成为候选；仍是有界600秒→最多2400桶，不新增模型调用。

同片4帧预算并用受控换帧：最大间隔3秒时实际选择3/4.5/7.5/9.25秒（包含有字帧），目标4秒时选择0.25/4.25/6.25/8.25秒（漏掉有字帧）。这是选择受其他变化影响的真实失败，候选保留不等于已选到或文字已读对，也不能保证0.25秒桶内更短事件。当前没有OCR、文字裁切/放大或语义重要性判断。

复现：`PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_coverage_prototype.py tests/nana_next_experience/test_video_ffmpeg_probe.py tests/nana_next_experience/test_video_coverage_refine.py tests/nana_next_experience/test_video_short_detail.py -q`，16通过；FFmpeg/ffprobe与DejaVu Sans不可用时对应测试按环境明确skip。`compare_video_fixture.py --dsh <fixed clone> --watch <fixed clone>`给同版四方法可重复对照，comparison.json为新粒度后原12秒场景实际数值；其实际4帧切点命中仍1/0/2/1，不能只看测试数。

**原始证据版本**：video-ffmpeg-comparison-20261116的源码表是本分支提交860e9ae当时的每秒版本，video-change-coverage-20261116是9fd98e8之前的实验；历史表和原对照保留。本表指纹仅覆盖新probe与回归文件。没有真实模型Token/账单、真实视频准确度或资源资格。下一B研究弱切、暗场、动态背景下短文本召回和局部裁切/文字路径并对照两个上游；NanaLink负责授权媒体与来源，A负责原主体集成。回退本批probe分桶及新增测试即可，无迁移。
