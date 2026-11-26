# 本地视频感知最小入口

入口 `tools.nana_next_experience.experiments.video_perception.perceive_video` 处理调用方有权使用的本地文件，不依赖 Nana Core、Store、模型服务或账号，也不写主体记忆。基础依赖 Python 3.10+、Pillow、PATH 中的 FFmpeg/ffprobe；可选 OCR 依赖 Tesseract 和语言数据，可选离线 ASR 依赖 `pocketsphinx==5.1.1`。当前子进程管道按 Linux/POSIX 验证；不自动下载任何模型或调用云服务。

```python
from pathlib import Path
from tools.nana_next_experience.experiments.video_perception import perceive_video

result = perceive_video(Path('local-video.mp4'), question='23 seconds 时发生了什么？',
                        frame_budget=8, max_runtime_seconds=90,
                        ocr=True, asr='pocketsphinx', model_content=True)
for frame in result['frames']:
    print(frame['time_seconds'], frame['pts_tick'], frame['time_base'], len(frame['png']))
print(result['subtitles']['state'], result['transcript']['state'])
print(result['unobserved_intervals'], result['elapsed_seconds'], result['output_sizes'])
content = result['model_content']['items']  # 调用方可传给兼容的视觉模型；本模块不发送
```

`time_range=(start, end)` 可限定容器相对秒区间；帧为内存 PNG 字节，不是已投递消息。时间保留真实解码 PTS、time_base 和容器起点；调用方要自行确定与外部平台时间轴的对应。`question` 中明确的秒数/分秒或与现有字幕的字面词匹配，可在同一个帧预算内替换少量取帧点；`focus_times` 允许调用方提供回看时间。简单词匹配不是自然语言/视觉理解，没有时间或字幕命中时不会凭空判断画面。

`ocr=True` 调用本机 Tesseract（默认 `eng`，可通过 `ocr_language` 指定已安装语言）；使用缩小画面再放大，细字可能漏读。`asr='pocketsphinx'` 调用已安装 PocketSphinx 的默认英文模型，最多处理目标区间起始30秒并返回词级时间，余段显式标记截断；FFmpeg 归一时间与源轨道对齐须由调用方核验。二者为未核实线索，非语义真相。可选 `transcriber(path, start_seconds, end_seconds)` 可替代内置 ASR，调用方须负责线程/超时、隐私和费用；二者不得同时指定。默认不运行转录。第一个内嵌文本字幕轨可转换为 WebVTT，返回完整轨且明确未按目标区间过滤；位图字幕或不支持的编码返回不可用。

`model_content=True` 额外生成 OpenAI-compatible 多模态 content 数组，包含带来源时间的图像、OCR、字幕/转录、问题及未观察范围；长文本会标记截断，字节数与真实 Token/账单分开。此字段仅组装材料，不调用模型，格式是否被具体视觉 Provider 支持需调用方确认；本地未进行真实视觉模型理解对照。

短于等于 30 秒且起点接近零的文件使用已有 FFmpeg scdet 与覆盖规划；其他文件在全目标时间范围均匀请求有限窗口。窗口、帧数和1秒最大单次取帧窗口有界；长片不做全片场景扫描，可能漏掉窗口以外的事件。`unobserved_intervals` 表示采样点之间未连续观察的范围，`outside_requested_intervals` 标出目标区间之外，`requested_windows` 不代表该窗口被完整理解。相邻采样的灰度差和局部变化仅是稀疏视觉线索，不能判断连续运动或语义重要性。声学结果是静音阈值与实际覆盖，不是语音识别；有音轨但超过600秒的目标范围不运行声学扫描，无音轨单独标记。

`frame_budget` 为 1–32，`max_runtime_seconds` 为 1–300 秒。FFmpeg 子进程按剩余时间限时；总耗时是尽力预算，不是硬实时保证，尤其是调用方 transcriber。文件大小上限 256 MiB、时长上限 24 小时；无法解析的输入抛出异常，单个采样/字幕/声学失败则在结果中标记。此实验直接运行本地 FFmpeg，**不是原 S5 的沙箱或来源授权入口**，仅处理受信任文件；A 负责真实来源、权限与原 S5 融合。

## 继承与验证

复用 PR #22 固定 `8a1fd6c` 的有界 FFmpeg 源帧解码、声学测量、scdet、局部变化；复用主线已有 `video_coverage.plan`，不替换 A 已吸收的 PTS/VFR、缓存或核心实现。不引入 dsh 的 Node 宿主与实验性运动评分，也不把 video-watch-plus 声音类型阈值当作转录或语义事实；上游许可及完整对照见原 PR #22。

`PYTHONPATH=. python -m pytest -q tests/nana_next_experience/test_video_perception_standalone.py`：5项本地合成测试通过，覆盖白块变化、字幕导向的同4帧补采样、620秒长片、回调、实际 Tesseract 和 PocketSphinx。flite 合成语音 `hello world this is a test` 被识别为 `hello well this is a test`，保留此反例；OCR 在单一合成片识别出 `ALARM`。普通 Python 导入未加载 `nana_core`。

同4帧真实本地样本：OpenCV `tree.avi` SHA-256 `4666099d0f704e310047b2f0a5ec9f936cb76a7271de9a2e70a0c57f82ac82dc`，均匀取 `0/9.800/19.467/28.667` 秒，指定23秒取 `7.400/23.133/25.933/28.667` 秒；前者未落入此前目视标记的23–24.5秒手进入时段，后者落入。目标时间已事先知道，此例不证明系统自主发现事件。另一 OpenCV `vtest.avi` SHA-256 `45cddc9490be69345cbdab64ca583be65987e864ca408038e648db99e10516cf`，均匀取 `0/26.2/52.4/78.5` 秒，指定23秒取 `0/23/52.4/78.5` 秒；无独立事件真值，不计算召回。两段的单独作者/许可尚未核实，不随仓库分发。第二段曾因FFmpeg边界舍入少取一帧，保守向后重试后4帧并返回告警。结果仅为各一轮本地材料对照，无真实 Provider/视觉模型、实际 Token/账单、用户媒体或生产资格。

`tree.avi` 开启 OCR 与视觉材料的一次调用返回4帧、9条 content 项，PNG 116,255 字节、序列化内容 157,807 字节、约2.88秒。Tesseract 在这些自然画面上还输出了无意义字符，因此不能把识别文本当作事实；材料中明确提示 OCR/ASR 未经核实。输入图像已缩小，细节和字幕识别能力需真实模型/人工评价，字节数不代表 Token。OCR 临时图像和 ASR 临时音频在正常退出时清理，进程异常终止后的临时文件清理尚未验证。
