# 字幕/静音时间复查的有界区间索引

负责人B，A基线90a31b6，隔离实验，无现役主体消费者。上一版`ad4fdeb`对每条字幕扫描全部静音区间，输入均上限10000时可造成二次方计算。本版在原有已排序且不重叠的区间上构建一次前缀长度和两次二分；最多8个交叉区间时直接计算以降低极短字幕的浮点消减误差，其余用区间前缀并限制舍入范围。没有缓存字幕/音频/主体状态，返回的来源、UNKNOWN、复查阈值和原Memory撤回重读语义不变。

复现：`PYTHONPATH=src:. python tools/nana_next_experience/experiments/benchmark_caption_overlap.py`；单次3000条合成字幕×3000静音区间，直接逐项累加2.5872秒，索引版0.01546秒，最大重叠比例差0；前者仅测重叠运算，后者包含输入验证与结果构造，均为单本地运行，不代表真实视频端到端延迟。没有新增模型调用，Token/账单未测。随机300个区间与直接求和独立对照，短至微秒量级的区间边界、NanaLink原Memory来源撤回等相关14项通过：`PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_caption_acoustic.py tests/nanalink/test_bilibili_video_history.py -q`。

原video-caption-audio-crosscheck-20261116证据指向ad4fdeb当时源码，保留历史；本目录源码表指向后继索引实现。真实字幕/音频同步、跨时区/多音轨和持久撤回仍未资格；原调用链未接入，撤回实验文件即可，无迁移。B继续真实素材和算法对照，NanaLink负责媒体与来源，A负责唯一主体链。
