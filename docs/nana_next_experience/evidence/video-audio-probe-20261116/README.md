# 音频静音测量隔离实验

负责人B，A基线90a31b6。显式本地文件经过ffprobe检查时长及音轨；有音轨时FFmpeg以-35dB、1秒门槛测量静音时间，返回`MEASURED`/区间；无音轨返回`NO_AUDIO`，不等同静音；缺少结束标记返回`INCOMPLETE`，不擅自补全。最多600秒、256MiB、120秒命令超时；不调用ASR、外部模型、网络，不保存音频或建立状态权威。时间来自工具输出，复杂源起始时间/多音轨同步尚未资格；仅使用第一音轨。

真实FFmpeg合成六秒音轨：0–3秒静音、3–4秒纯音、4–6秒静音，输出区间[0,3.000125]、[4,6]；纯音不是人声证据。真实无音轨视频返回NO_AUDIO；模拟缺失结束标记返回INCOMPLETE。26项覆盖/视频/裁切/音频相关测试通过：`PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_coverage_prototype.py tests/nana_next_experience/test_video_ffmpeg_probe.py tests/nana_next_experience/test_video_coverage_refine.py tests/nana_next_experience/test_video_short_detail.py tests/nana_next_experience/test_video_local_change.py tests/nana_next_experience/test_video_audio_probe.py -q`。缺FFmpeg时有关用例明确skip。

静音门槛不能说明语音、背景音乐、说话人、字幕准确或含义；无ASR/VAD/字幕对齐或幻觉校验，真实素材/多音轨/资源与模型Token均未测。B后续用有独立标注的受控音视频验证和跨模态交叉校验；平台来源/账号由NanaLink，原S5/S2/C/S8及撤回由A负责。尚无现役消费者或生产资格；撤销此实验模块/测试即可，无迁移。
