# 完全相同画面的局部变化快速路径

B负责，A基线35740e7；仅影响隔离视频实验。局部区域检测此前即使前后灰度字节完全一致，也生成逐像素差、排序求中位数；现在在同样的尺寸/阈值检查与灰度转换后，只对字节完全相同的帧对直接返回原结果None。差异帧仍走原算法，不减少采样或自主认知；原有灰度方法本身可能漏掉同亮度色彩变化，此批未新增或解决该缺口。

可执行同条件对照：`PYTHONPATH=src:. python tools/nana_next_experience/experiments/benchmark_static_pairs.py`，读取本地Git提交84e79d6中真实上一版本，执行前校验源文件SHA256；两个版本交替各6次，比较相同48帧/47对完整输出相等。320×180合成静止背景+一帧局部变化：原中位272.691ms、新17.804ms，事件均2；持续局部运动：原275.595ms、新275.269ms，事件均47。CPU均值及原值见benchmark.json；单机器、每类一组合成素材，仅含已解码图像的灰度转换/区域判断，不含采集、FFmpeg解码、上传、模型、真实Token或账单，不推断实际硬件收益。

`NANA_DSH_SOURCE=/path/to/pinned/dsh-see-now PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_local_change.py tests/nana_next_experience/test_video_local_pairs.py tests/nana_next_experience/test_video_fusion_prototype.py -q`：19通过，包含真实dsh原管线/FFmpeg合成片、来源和预算、局部光标误报；无该可选checkout时对应项会skip。首次测试未传checkout变量时18通过/1 skip，补变量后19通过，不冒称首次完整。

此前video-local-change-20261116证据表固定fd12bc1旧代码；本表是后继候选。尚未接入现役平台/原主体或验证真实素材、图像Token和长片资源；A/NanaLink分别负责原链与来源。撤销两行快速路径即可回到原行为，无数据迁移。
