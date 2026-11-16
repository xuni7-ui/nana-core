# 视频时间覆盖隔离原型

负责人 B；主线基线 `cfd11be158a3f0fa36abf93f42d5e4fde1f55bf0`，仅候选，无现役消费者或主体权威。输入：总时长、候选时间戳及可选非负镜头变化/运动分数、帧预算、最大间隔目标；输出：所选时间戳、超目标间隔及是否达到目标。单位秒，内存数据结构，无持久化/协议迁移。最多86400秒、10000候选、256帧；目标不能满足时如实返回空档。未采样片段不是已观察内容。

## 固定来源与实际调用路径

- [dsh-see-now](https://github.com/SAOS-3624/dsh-see-now) `0b4bd110074b3e2cd043da8b078f7272589d50b0`，Apache-2.0 + NOTICE。`src/pipeline.js` 调用 `cuts.js` 的亮度归一、背景、运动补偿与切点逻辑，随后选择/拼图；其阈值和实时管线尚未移植或实测。Node/FFmpeg，屏幕采集依平台环境。上游公开提交为2026年版本，持续维护状态需后续核验。
- [video-watch-plus](https://github.com/xinhailaopo/video-watch-plus) `8ca266f9cf9e5ffce7e9d424aa0e937a897b608d`，自身MIT，`NOTICE`明确为以下项目衍生。`vendor/vw.py` 的 `cmd_probe` 使用 FFmpeg scdet/freezedetect/tblend/signalstats 和音频 silencedetect，再以 `cmd_plan` 的分段、切点和运动峰值挑帧；脚本中并非所有语义判断自动化。依赖 FFmpeg、ImageMagick；ASR需独立依赖/模型。未经实际运行不可声称对照结果。
- [video-watch-skill](https://github.com/CFITCorporation/video-watch-skill) `a00ab16ef99717070f36ec2a5e8f5c7a5a8d7e35`，MIT，FFmpeg ≥5.1 且须相关滤镜，图版需要 ImageMagick，ASR 另需 faster-whisper。上游实际快照与 vendor 文件的精确来源提交关系尚未确认。

本原型独立编写，没有复制上游源码。借鉴时间覆盖优先、变化供补采的思想；尚未移植这两个项目的检测、视频解码、拼版、字幕、语音或时间一致性算法，也未测试真实视频。当前 B 站 `life/bilibili_frames.py::acquire_frames` 是最多三帧的发布方故事板，不能直接宣称全片覆盖。后续 B 继续完成 FFmpeg真实信号与同预算对照；NanaLink负责授权的媒体获取接口；A负责原 S5/S2/C/S8 消费及来源/撤回契约。

## 验证和反例

`PYTHONPATH=src:. python -m pytest tests/nana_next_experience/test_video_coverage_prototype.py -q`：7通过。120秒合成候选、8帧预算、变化只集中在前20秒：仅按变化最高选帧的最大时间间隔113秒，本原型15秒；这是构造数据的采样间距，不是关键事件召回、真实视频质量、Token或账单。稀疏输入及预算不足会明确报告空档；变化并不等于语义重要性。没有真实 Provider Token、CPU/内存/磁盘或端到端视频性能结果。

撤回只需丢弃实验模块和测试，无数据迁移或现役功能改变。下一步由B接入真实FFmpeg测量、覆盖与均匀/两原版同条件实验，记录亮暗场、运动、字幕/动作反例及资源成本；不足证据前保持候选。
