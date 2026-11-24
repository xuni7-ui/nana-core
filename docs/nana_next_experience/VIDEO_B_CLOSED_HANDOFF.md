# B 视频专项收口：CLOSED_HANDOFF

> 2026-11-24 用户修正了专项自主执行权；本文件是当时的交接快照。A `02c01dc` 已接收该交接并负责原权威融合，新的 B 隔离技术解码候选见 `video_s5_handoff.py`，不代表原生持久化接线已完成。

> 后续候选提供 `verify_source_frames=True`：对相同已校验 PUBLIC 视频的所选窗口按相同输出尺寸/方向重新解码，逐帧核对 PTS 与像素；空批次明确 `NO_FRAMES_TO_VERIFY`。它不证明平台获取、视频来源归属或帧被原 C 选择；使用点须复查原授权，FFmpeg 本地实验未套用原 S5 沙箱。该选项有额外解码成本，A 自主决定是否吸收。

固定算法代码 `21de817f1537a85f59fb70510f7a102c98d1ba00`，A 基线 `6a483b3c48648ae9d093b0aed0d1a4242fbd2171`。本文件所在后续提交只补交接；[PR #22](https://github.com/xuni7-ui/nana-core/pull/22) 是隔离候选，尚未进入现役 S5 调用链。CLOSED_HANDOFF 表示 B 停止本专项，不表示功能全部集成或生产资格。A 是原 S5/S2/C/S8 最终接线负责人，NanaLink 负责平台获取和来源绑定。

## 采用建议

| 类别 | 具体内容 | 接入判断 |
| --- | --- | --- |
| 已由 A 采用 | 容器相对 PTS、变帧率和时间覆盖：A `e5969b0` 后续已在原 S5 实现 | 不重复移植 B 的时间解码器 |
| 可评估移植 | `video_coverage.py` 已对照的有界覆盖规划、空隙显式化；`video_local_pairs.py` 的局部变化前后帧；`video_global_budget.py` 的跨窗 PTS 去重/预算；`video_audio_probe.py` 与 `video_caption_acoustic.py` 的有界声学复核 | 先满足下述来源契约和预算；线索仅供原 S5/C 评估，不是事实或自动目标 |
| 保留作实验 | `video_guarded_batch.py` 同一 PUBLIC 快照、声画失败状态和撤回回查；`video_segment_windows.py` 请求分窗；原 dsh 适配与 motion onset | 当前实验须完整运行环境；不直接把工具目录整体带入 Core；长视频请求并非原 S5 已观察 |
| 不建议采用 | video-watch-plus 的声学类型阈值作为语音/音乐事实；把 dsh 切点、运动或字幕重叠当语义真值；未证实收益的大样本线索优先方案 | 保留反例，不为复杂度支付无证据成本 |

## 最小接口与接线差额

`guarded_images(app, cache, source_memory_id, scope=..., windows=..., detector=..., budget=..., max_gap=..., shared_snapshot=True, audio_window=...)` 返回物化 `GuardedImageBatch`：原 `source_ref`、`source_sha256`、内存 `images`、未请求区间、超间隔、声学状态及请求窗口。每帧 `ImageCandidate` 有 PNG、原容器相对秒、整数 PTS/time_base、坐标空间和像素摘要。请求窗口不等于观察；空窗/缺音轨/出错不是内容为空。声学测量不是 ASR/VAD，时间对齐须独立验证。

原 `MediaDecoder.decode(frame.png, 'IMAGE')` 可以直接消费 PNG，相关实测其 `pixel_digest` 与候选一致；这只是 S5 的技术图像解码，**不是**携原视频来源的 `PerceptionService.ingest` 接线。现役 S5 尚无把解码视频帧作为原视频派生证据安全写入、并维持来源依赖及撤回的公开契约；直接伪造 `PublicMediaSource` 或调用 `BilibiliFrameService.capture` 会错误记录独立来源或发布者故事板。此项是 A 原生接线的阻塞，不由 B 修改 Core 权威。

接入必须在实际消费前再次验证原 Store 当前来源、scope、缓存哈希和授权，并建立视频来源到派生帧/观察的可撤回依赖；NanaLink 须证明实际平台账号、bvid/cid、获取时间和字节摘要的绑定。现有门控仅允许原 PUBLIC 直接视频与最多 16 MiB 缓存，且现役原视频入口时长有上限；不是长视频或 B 站任意媒体已接通。公共临时快照异常崩溃清理、真实平台与模型使用点竞态仍未资格。

依赖按需：本地 FFmpeg/ffprobe、Python Pillow；原 dsh 对照需 Node 和可信固定 checkout；原 S5 视频解码依现有 bwrap 沙箱。检测回调是可信宿主代码，不是沙箱；不得把实验 FFmpeg 子进程当成现役安全沙箱。来源/身份由原 Store 与 NanaLink 提供，不新建 Store 或主体。回退为不接此工具或撤回所移植的外围代码；无数据迁移。

## 同预算结果与反例

- [三场景原四方法](evidence/video-three-scenarios-20261116/README.md) 和 [融合对照](evidence/video-fusion-scenarios-20261116/README.md)：每场景一条 8 秒合成片；四帧预算下弱切旧/新均选中，单帧文字旧候选漏、新候选选中；连续运动中 dsh 的假切会占用融合预算。原 watch 输出是请求偏移，原 dsh 输出有时不足四帧，不等于统一的已解码帧预算。无 OCR/语义准确率结论。
- [原 S5 对照](evidence/video-native-s5-comparison-20261117.json)：单段参与参数选择的实拍中各取八帧，B 选择进入动作时段，原 S5 取 25 秒手已进入画面；分辨率不同、没有真实模型计费，不能推断语义或 Token 收益。另一个独立样本没有逐帧真值，不能声称召回提高。
- [规划等价对照](evidence/video-coverage-index-20261117.json)：3000 组固定合成输入输出一致；10000 候选案例旧/新本地墙钟中位约 0.516/0.009 秒，80 候选差异小且波动大；只测选帧规划，不含解码、模型、账单或端到端成本。另一个 [全局预算方案](evidence/video-global-budget-20261116.json) 大样本更慢且同样只中 8 条线索，不建议按该结果推广复杂评分。
- 受控 A `6a483b3` 源码下共享声画/来源/音频相关 29 项，C `636eb88` 源码下 14 项通过；涉及真实本地 FFmpeg 和合成数据。更早真实 dsh 管线、取帧、撤回及差异证据见 PR。未进行真实 Provider Token/费用、真实 B 站账号、真机或生产测试。

固定上游：[dsh-see-now](https://github.com/SAOS-3624/dsh-see-now) `0b4bd110074b3e2cd043da8b078f7272589d50b0` Apache-2.0 + NOTICE；[video-watch-plus](https://github.com/xinhailaopo/video-watch-plus) `8ca266f9cf9e5ffce7e9d424aa0e937a897b608d` MIT，其 NOTICE 所列衍生上游也需核对；研究独立实现，未把上游整包复制进产品。实拍素材未入库且单独作者/许可未确认。
