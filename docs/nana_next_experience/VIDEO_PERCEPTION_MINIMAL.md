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

`time_range=(start, end)` 可限定容器相对秒区间；帧为内存 PNG 字节，不是已投递消息。时间保留真实解码 PTS、time_base 和容器起点；调用方要自行确定与外部平台时间轴的对应。`question` 中明确的秒数/分秒或与现有字幕的字面词匹配，可在同一个输出帧预算内替换少量取帧点；`focus_times` 允许调用方提供回看时间。设置 `ocr=True, ocr_probe_budget=12` 可在没有既有时间/字幕命中时额外扫描最多12个时间点，按问题中的字面词或显式 `focus_terms` 匹配文字并补采样。`ocr_probes` 和 `ocr_probe_status` 单独记录额外检查，不应把只比较输出帧数误当成总处理预算相同。简单词匹配不是自然语言/视觉理解，未命中时不会凭空判断画面。

OCR 探测的十进制时间边界若因解码时间基舍入落在窗口外，会向后重试至下一个 0.1 秒边界，实际重试起点由 `retry_start_seconds` 给出。单个取帧失败记录为 `FRAME_UNAVAILABLE` 并继续其他探测点；OCR 不可用记录为 `OCR_UNAVAILABLE` 并停止探测。真实 OpenCV vtest 视频前 30 秒的 8 点探测中，3 点发生上述重试，8 点均获得 OCR 结果但没有命中查询词，约 9.35 秒；没有标注真值，因此这不是文字召回率或理解效果证据。

输出图像默认为 `output_size=(160,90)`；需要画面细节时可传 `output_size=(640,360)`。每边最多 1024 像素，总像素最多 262144；FFmpeg 直接缩放到指定宽高，调用方应自行按源画面纵横比选择尺寸。OCR 候选探测和最终输出都采用该尺寸；较大尺寸会增加探测及输出的处理资源、传输量和潜在模型费用，高帧率窗口也可能触及原有 64 MiB 解码边界并明确报取帧失败。探测是稀疏采样，不保证找到短暂文字。

同一 640×360 合成画面中的 14 像素文字，160×90 输出 OCR 为 `wees «0`，640×360 输出为 `WARNING 4392`，单帧 PNG 分别为 445 和 3866 字节。另一真实 OpenCV tree 画面的同一时间点，160×90 与 640×360 的 PNG 分别为 29394 和 295919 字节，组装的模型材料分别为 40335 和 396013 字节，单次耗时 0.685 和 2.638 秒；自然画面 OCR 仍产生乱码。以上只是各一轮本地观察，不证明语义理解或实际 Token 成本。

另一个 8 秒合成片中，14 像素 `WARNING` 只在 3.5–4 秒出现；在均限制最多 3 次 OCR 探测和输出 2 帧时，160×90 探测 3 次未命中、输出 0/7 秒，640×360 探测 2 次后命中并输出 3.5/7 秒。单次耗时分别 1.50/1.97 秒，PNG 242/4614 字节；探测次数不同、计算成本也不同，不构成同计算预算或真实素材召回证明。

`ocr=True` 调用本机 Tesseract（默认 `eng`，可通过 `ocr_language` 指定已安装语言，或 `ocr_data_dir` 指定数据目录）；使用缩小画面再放大，细字可能漏读。可选中文数据为官方 [tessdata_fast 固定 8741641](https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd)，本地 `chi_sim.traineddata` SHA-256 `a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730`，不随仓库分发。`asr='pocketsphinx'` 调用已安装 PocketSphinx 的默认英文模型，默认处理目标区间起始30秒，`asr_max_seconds` 可设为1–120秒，返回词级时间并显式标记截断；FFmpeg 归一时间与源轨道对齐须由调用方核验。二者为未核实线索，非语义真相。可选 `transcriber(path, start_seconds, end_seconds)` 可替代内置 ASR，调用方须负责线程/超时、隐私和费用；二者不得同时指定。默认不运行转录。第一个内嵌文本字幕轨可转换为 WebVTT，返回完整轨且明确未按目标区间过滤；位图字幕或不支持的编码返回不可用。

`model_content=True` 额外生成 OpenAI-compatible 多模态 content 数组，包含带来源时间的图像、OCR、字幕/转录、问题及未观察范围；字节数与真实 Token/账单分开。上下文超过 16000 字符时，保留覆盖区间、错误、警告及字幕/转录状态，字幕和转录改为首尾节选，标记中间省略及省略字符数；当容器起点接近零时，另附最多 16 条与已选画面时间重叠的字幕轨短句，每条最多 100 字符，并提供匹配总数及截断标志。字幕轨与画面时间对齐仍须核验，非零起点不自动添加此项。逐词时间、探测详情和稀疏变化从模型上下文省略，调用方仍可从原始返回字段读取。节选可能漏掉中间重要内容，不能视作完整理解。此字段仅组装材料，不调用模型，格式是否被具体视觉 Provider 支持需调用方确认；本地未进行真实视觉模型理解对照。

一次本地 FFmpeg 合成对照使用 120 秒视频及约 2.9 万字符字幕，选择第 60 秒画面：原首尾节选漏掉该秒的 `MIDDLE_CRITICAL`，新材料包含对应时间字幕短句且上下文为有效 JSON；这只验证时间线材料完整性，不证明真实字幕对齐或模型理解。

模型材料中的 `audio_timeline` 保留音轨测量状态、目标窗口和时间基准。已测区间和静音区间各最多附前 12 条，并标明省略条数。长文本节选时仍保留这项信息，完整测量可从原返回的 `audio` 字段读取。静音只代表阈值测量，时间对齐仍须由调用方核验。

请求视频子区间时，模型材料仅附时间上与区间重叠的字幕条目，保留条目原时间和值，并标为 `TARGET_WINDOW_UNVERIFIED`。区间边界跨越的条目会完整保留，条目内没有逐字时间。容器起点偏移超过 1 毫秒时，模型材料标为 `OMITTED_UNVERIFIED_OFFSET` 并省略字幕，完整轨仍可从原始 `subtitles` 读取。全片请求继续提供整轨。

短于等于 30 秒且起点接近零的文件使用已有 FFmpeg scdet 与覆盖规划；其他文件在全目标时间范围均匀请求有限窗口。窗口、帧数和1秒最大单次取帧窗口有界；长片不做全片场景扫描，可能漏掉窗口以外的事件。`unobserved_intervals` 表示采样点之间未连续观察的范围，`outside_requested_intervals` 标出目标区间之外，`requested_windows` 不代表该窗口被完整理解。相邻采样的灰度差和局部变化仅是稀疏视觉线索，不能判断连续运动或语义重要性。声学结果是静音阈值与实际覆盖，不是语音识别；有音轨但超过600秒的目标范围不运行声学扫描，无音轨单独标记。

`frame_budget` 为 1–32，`max_runtime_seconds` 为 1–300 秒。FFmpeg 子进程按剩余时间限时；总耗时是尽力预算，不是硬实时保证，尤其是调用方 transcriber。文件大小上限 256 MiB、时长上限 24 小时；无法解析的输入抛出异常，单个采样/字幕/声学失败则在结果中标记。此实验直接运行本地 FFmpeg，**不是原 S5 的沙箱或来源授权入口**，仅处理受信任文件；A 负责真实来源、权限与原 S5 融合。

## 继承与验证

复用 PR #22 固定 `8a1fd6c` 的有界 FFmpeg 源帧解码、声学测量、scdet、局部变化；复用主线已有 `video_coverage.plan`，不替换 A 已吸收的 PTS/VFR、缓存或核心实现。不引入 dsh 的 Node 宿主与实验性运动评分，也不把 video-watch-plus 声音类型阈值当作转录或语义事实；上游许可及完整对照见原 PR #22。

`NANA_TEST_TESSDATA=/path/to/tessdata PYTHONPATH=. python -m pytest -q tests/nana_next_experience/test_video_perception_standalone.py`：该环境7项本地合成测试通过，覆盖白块变化、字幕和画面文字导向的同输出帧预算补采样、620秒长片、回调、实际 Tesseract 和 PocketSphinx；缺少可选工具/数据时相应测试会跳过。flite 合成语音 `hello world this is a test` 被识别为 `hello well this is a test`，保留此反例；OCR 在单一合成片识别出 `ALARM`，中文大字合成片识别出 `中文测试`。普通 Python 导入未加载 `nana_core`。

无字幕12秒合成片中，均匀4帧取0/4/7.5/11秒，漏掉5秒短暂的 `ALARM`；文字导向仍输出4帧，取0/5/7.5/11秒，命中短字。但它额外执行了6次OCR探测，单次墙钟0.874→3.510秒、输出PNG 484→2195字节；这是相同输出帧数、不同处理预算，不能声称免费或相同计算成本，模型Token亦未测。

同4帧真实本地样本：OpenCV `tree.avi` SHA-256 `4666099d0f704e310047b2f0a5ec9f936cb76a7271de9a2e70a0c57f82ac82dc`，均匀取 `0/9.800/19.467/28.667` 秒，指定23秒取 `7.400/23.133/25.933/28.667` 秒；前者未落入此前目视标记的23–24.5秒手进入时段，后者落入。目标时间已事先知道，此例不证明系统自主发现事件。另一 OpenCV `vtest.avi` SHA-256 `45cddc9490be69345cbdab64ca583be65987e864ca408038e648db99e10516cf`，均匀取 `0/26.2/52.4/78.5` 秒，指定23秒取 `0/23/52.4/78.5` 秒；无独立事件真值，不计算召回。两段的单独作者/许可尚未核实，不随仓库分发。第二段曾因FFmpeg边界舍入少取一帧，保守向后重试后4帧并返回告警。结果仅为各一轮本地材料对照，无真实 Provider/视觉模型、实际 Token/账单、用户媒体或生产资格。

中文数字秒数后接汉字的提问也支持时间引导，例如 `23秒时画面发生了什么？`。上述 tree 视频在同为均匀方案和4帧的单次对照中，无问题取 `0/9.800/19.467/28.667` 秒，中文问题取 `0/9.800/23.133/28.667` 秒；只有后者落入已预先标记的事件区间。这只验证已知时间的中文表达，不验证中文语义理解或自主发现事件。

数字格式的 `1分23秒`、`1分钟23秒` 和 `1:23秒` 均指向 83 秒，不再同时把后半段误作第 23 秒；`1分75秒` 等秒数超出范围的组合不会生成时间提示。本地 FFmpeg 100 秒合成视频以 1 帧预算验证了 83 秒取帧，不代表支持中文数字或所有时间表达。

无问题提示时，同一 tree 样本的自适应方案取 `7.400/22.267/25.933/28.667` 秒，也没有落入上述 23–24.5 秒人工标记区间；该次场景扫描结果为 `PARTIAL_OR_UNQUALIFIED`，不应称为全片语义发现或断言优于均匀采样。均匀和自适应该次单轮耗时约 0.88/0.82 秒，缺少多样样本及重复测量，不能据此评价速度。

`tree.avi` 开启 OCR 与视觉材料的一次调用返回4帧、9条 content 项，PNG 116,255 字节、序列化内容 157,807 字节、约2.88秒。Tesseract 在这些自然画面上还输出了无意义字符，因此不能把识别文本当作事实；材料中明确提示 OCR/ASR 未经核实。输入图像已缩小，细节和字幕识别能力需真实模型/人工评价，字节数不代表 Token。OCR 临时图像和 ASR 临时音频在正常退出时清理，进程异常终止后的临时文件清理尚未验证。
