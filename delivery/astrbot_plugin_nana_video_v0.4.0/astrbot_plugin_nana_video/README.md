# Nana Video 0.4.0 / AstrBot 4.28.0
这是现役 AstrBot 专用独立插件，不依赖 Nana Core。保留 B 固定 66eb93b 的七个核心模块（六个原样，一个相对导入），原测试只改移植路径。上一版漏改的内部测试导入已修复。

## 入口归属：二选一
默认 coexist_bv：只处理明确 BV 号/链接及本插件的明确回看，QQ 直发、引用、含图片的混合消息全部让给其他插件；不抢优先级，不 stop_event。旧 Reference Vision 若需要直发请设 allow_direct_video=true；若只希望引用才观察，但不拦截普通聊天，设 intercept_direct_video_llm_request=false。建议关闭旧插件 video_caption_context_cache_rounds（设0），避免旧摘要污染；这些是旧插件独立配置，本插件不会修改它们。若旧插件继续处理直发，则它自己的额度单独管理，本插件上限不能限制它。
standalone：先在 AstrBot 停用 Reference Vision 及其他自动视频理解插件，再将 route_mode 设 standalone；此模式接受 QQ 直发和 BV，不支持引用/转发/分享卡片，不声称完成旧插件原生视频模型融合。
不自动识别或禁用其他插件，不调用旧插件私有函数。若上游已 stop_event，本插件无法恢复该轮。

## 模型与用量
vision_provider_id 填 AstrBot 中支持图片的 provider ID。默认群聊禁止，allowed_groups 填允许群号（逗号分隔）；群内默认需要明确观看请求。allowed_senders 可额外限制发送者。私聊默认可用。
每日 20 次潜在计费模型调用，全局与每发送者6次独立持久计数（UTC+8）；视觉与STT分别计次，失败不退；不是人民币或Token上限，也不涵盖宿主主对话和其他插件。每发送者30秒冷却，2路并发，无长队列；同会话并发新来源使旧来源退役。默认短片4帧，中片6帧，长片8帧，不超过 max_frames。OCR/STT默认关闭。源视频临时明文缓存默认600秒，按会话与发送者隔离，可设0。一般聊天绝不自动注入旧观察；明确“回看第23秒”“刚才的视频第23秒发生了什么”才重采样。缓存命中不再次调用视觉模型；新来源先检查预算，回看缓存不需要下载。新视频失败不延续旧源；含外部媒体的消息让权并退役缓存。
命令：/nana视频状态，/nana视频清除（仅本插件缓存，不改宿主聊天记录）。日志有阶段、异常类型、堆栈位置，避免泄露原始错误中的API凭证。
## 安装
Linux/POSIX、Python>=3.10、FFmpeg/ffprobe、Pillow、yt-dlp。替换整个旧 Nana Video 插件目录并重载；不要同时安装两个 Nana Video 版本。先私聊试用。旧插件设置由操作者决定。纯视频需要宿主先触发LLM。可选 OCR 依赖 Tesseract/语言包；STT 使用宿主STT。
## 限制
不支持原生整段视频模型、短链、分P、平台字幕、评论、引用视频和模型自主工具调用。B独立内核非Core沙箱；本地媒体需可信、更新FFmpeg。宿主QQ下载先于本插件检查；长片漏采样、OCR/ASR不确定，缓存异常退出可能残留。没有真实QQ、B站、真实Provider及生产验收。联合CI使用真实FFmpeg和模拟宿主/Provider，绝不调用付费模型。原B真实DeepSeek实验见 UPSTREAM_EVIDENCE.md，不等同于本插件真实运行。
