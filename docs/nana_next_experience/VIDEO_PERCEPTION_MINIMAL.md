# 本地视频感知最小入口

入口 `tools.nana_next_experience.experiments.video_perception.perceive_video` 处理调用方有权使用的本地文件，不依赖 Nana Core、Store、模型服务或账号，也不写主体记忆。依赖 Python 3.10+、Pillow、PATH 中的 FFmpeg/ffprobe；当前子进程管道实现按 Linux/POSIX 验证。模型、OCR、ASR、Node 均非必需，也不会自动下载或调用。

```python
from pathlib import Path
from tools.nana_next_experience.experiments.video_perception import perceive_video

result = perceive_video(Path('local-video.mp4'), question='发生了什么？',
                        frame_budget=8, max_runtime_seconds=90)
for frame in result['frames']:
    print(frame['time_seconds'], frame['pts_tick'], frame['time_base'], len(frame['png']))
print(result['subtitles']['state'], result['transcript']['state'])
print(result['unobserved_intervals'], result['elapsed_seconds'], result['output_sizes'])
```

`time_range=(start, end)` 可限定容器相对秒区间；帧为内存 PNG 字节，不是 JSON 文本或已投递消息。时间保留真实解码 PTS、time_base 和容器起点；调用方要自行确定与外部平台时间轴的对应。`question` 原样返回供上层使用，**不参与当前选帧或语义理解**。

可选 `transcriber(path, start_seconds, end_seconds)` 由调用方显式提供并返回字符串；不提供时返回 `NOT_RUN_NO_TRANSCRIBER`。其结果标记 `CALLER_TRANSCRIBER_UNVERIFIED`，调用方须负责线程/超时、隐私和费用；本模块不托管模型或中断任意外部回调。第一个内嵌文本字幕轨可转换为 WebVTT，返回完整轨且明确未按目标区间过滤；位图字幕或不支持的编码返回不可用，不会冒称识别成功。没有内建 OCR 或 ASR。

短于等于 30 秒且起点接近零的文件使用已有 FFmpeg scdet 与覆盖规划；其他文件在全目标时间范围均匀请求有限窗口。窗口、帧数和1秒最大单次取帧窗口有界；长片不做全片场景扫描，可能漏掉窗口以外的事件。`unobserved_intervals` 表示采样点之间未连续观察的范围，`outside_requested_intervals` 标出目标区间之外，`requested_windows` 不代表该窗口被完整理解。相邻采样的灰度差和局部变化仅是稀疏视觉线索，不能判断连续运动或语义重要性。声学结果是静音阈值与实际覆盖，不是语音识别；有音轨但超过600秒的目标范围不运行声学扫描，无音轨单独标记。

`frame_budget` 为 1–32，`max_runtime_seconds` 为 1–300 秒。FFmpeg 子进程按剩余时间限时；总耗时是尽力预算，不是硬实时保证，尤其是调用方 transcriber。文件大小上限 256 MiB、时长上限 24 小时；无法解析的输入抛出异常，单个采样/字幕/声学失败则在结果中标记。此实验直接运行本地 FFmpeg，**不是原 S5 的沙箱或来源授权入口**，仅处理受信任文件；A 负责真实来源、权限与原 S5 融合。

## 继承与验证

复用 PR #22 固定 `8a1fd6c` 的有界 FFmpeg 源帧解码、声学测量、scdet、局部变化；复用主线已有 `video_coverage.plan`，不替换 A 已吸收的 PTS/VFR、缓存或核心实现。不引入 dsh 的 Node 宿主与实验性运动评分，也不把 video-watch-plus 声音类型阈值当作转录或语义事实；上游许可及完整对照见原 PR #22。

`PYTHONPATH=. python -m pytest -q tests/nana_next_experience/test_video_perception_standalone.py` 使用本地生成视频：短片中的白块变化与字幕/声轨、620 秒长片有限帧与未观察区间、显式转录回调及失败状态。普通 Python 直接导入时未加载 `nana_core`。一次8秒合成片、4帧、无声轨/字幕的独立调用输出时间 0.5/2/5/6 秒、PNG 共 52,513 字节、本地墙钟 1.047 秒；仅一个样本，不代表普遍性能或真实模型 Token。无真实 Provider/模型、真实用户媒体或生产资格。
