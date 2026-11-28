# Nana Video 0.3.0 — 独立 AstrBot 适配版

面向现役、与 Nana Core 完全无关的 AstrBot 奈奈。目标宿主 AstrBot v4.28.0、Linux/POSIX。保留原人格、群聊发言闸、记忆插件与当前聊天模型；不需要安装 Core、数据库、BFF、主体循环或 NanaLink。

## 安装与使用

- 确保 AstrBot 所在的实际运行环境有 ffmpeg、ffprobe、Python 3.10+；requirements.txt 安装 Pillow 和 yt-dlp（Docker 容器内亦需可用）。
- 在 AstrBot 插件管理上传完整 ZIP；或解压到 AstrBot/data/plugins/astrbot_plugin_nana_video/。更新旧版请替换整个插件目录，避免残留；重载后检查 /nana视频状态。
- 配置支持图片的 AstrBot 聊天提供商 ID，并非 API key 或模型名称。原聊天模型不变。关闭其他自动视频插件的重复触发功能。
- 默认关闭 OCR 和 STT。OCR 需额外安装 Tesseract 和 chi_sim+eng 语言包；STT 复用 AstrBot 已配置的语音转写提供商，可能计费。
- 直接发送视频或带 BV 号的 B站公开视频链接。宿主须正常触发 LLM 请求（群里可 @ 奈奈，纯视频不触发时附文字）。默认十分钟内同一会话同一发送者可以问“第23秒发生了什么”或“回看视频里的某个文字”；明确回看会按问题重新采样，重复问题可复用结果。一般追问复用已有观察。
- /nana视频清除 清除当前发送者的插件源缓存，不会修改聊天记录。

## 原始内核

引自 B 分支固定提交 66eb93b594b2a4c520040e4b08d3efe98ff10e34，七个文件中六个逐字节相同，另一个仅将绝对 import 改为相对 import。UPSTREAM.json 附精确 blob 指纹和改动说明；UPSTREAM_EVIDENCE.md 保留 B 的原回执，tests/test_upstream_original.py 保留原测试并改包导入路径。B 的 PTS、取帧、OCR、字幕、声学、局部变化和模型材料算法不重写。B 保守记录未连续观察的时间；它不是 A 的完整帧覆盖、H1 语义校验或 Core 生命周期系统。

宿主适配只做媒体取得、缓存源和哈希、调用原引擎、转换模型材料到 AstrBot SDK、观察注入原对话。B 的真实 DeepSeek Flash 实测是原 B 的证据，不是新插件的真实模型验收。

## 边界

默认8张、长边640px、600秒、80MiB、4个源缓存、10分钟。源视频明文暂存于临时目录以便回看，按会话和发送者隔离，活动处理结束后每30秒清理过期项；异常退出可能残留。cache_seconds=0 不保留原视频。宿主聊天记录和模型服务中的数据不由本插件删除。正常追问复用缓存；明确回看可能增加一次视觉调用；首次视觉观察和原聊天回复分别调用模型。

B 独立原版没有 Core bwrap 沙箱；文件容器、大小、分辨率、时长和尽力处理预算受限，但只应在受信任的媒体来源及及时更新的 FFmpeg 环境试用。QQ 附件宿主下载发生于本插件检查前，B站下载限制不能确保过程中总磁盘绝不超限。暂不支持短链、分P、引用嵌套/转发视频或需登录视频。只做稀疏画面观察，不支持逐帧理解、原生整段视频模型或实时屏幕。内嵌字幕、OCR、STT 可能错误，长片可漏掉短暂事件；无平台字幕与评论采集。STT仅起始限定时长、对齐未核实。

## 证据

适配层本地 4 项 unittest 通过，使用真实合成 FFmpeg 文件、模拟 AstrBot 与引擎。原版 B 源码已按 Git blob 逐文件校验。因当前构建容器无法直接访问 GitHub，未在本地运行打包后 B 引擎与适配器的联合测试；原 B 的受控试验见原文档。真实 AstrBot 加载、QQ、B站、视觉 Provider 及实机体验尚未验收。先私聊短视频试用，确认后再扩大范围。

从插件目录的上级运行：python -m unittest discover -s astrbot_plugin_nana_video/tests -p test_adapter.py -v；如已安装 pytest 和 FFmpeg/Pillow，运行 python -m pytest -q astrbot_plugin_nana_video/tests/test_upstream_original.py（可选 OCR/ASR 依赖缺失时按原测试逻辑跳过）。
