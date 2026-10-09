# C.5 第一阶段 · B站视频只读理解最小闭环

> 目标：**姐姐的 @ 落到某条视频上时，奈奈能顺着 BVID 读一眼这个视频，说出"它在讲什么"。**

## 链路（只这一条，不多走一步）

```
当前 @ 事件（bili_event_state.json，只读）
   ↓  取 BVID
video.get_info()          标题 / UP主 / 时长 / 分区 / 简介 / 播放量
   ↓  取 cid
video.get_player_info()   subtitle.subtitles 列表
   ↓  有则取 url
Api(subtitle_url).request(raw=True) → body → 拼接字幕正文（截断 4000 字）
   ↓
单次 LLM（deepseek，复用 bili_event_pump._real_llm_factory）
   ↓  {"summary": ..., "keywords": [...]}  ← 只认这 2 个白名单字段
打印结果，结束
```

## 文件

| 文件 | 作用 |
|---|---|
| `/root/.nana_secrets/bili_video_read.py` | C.5 第一阶段：事件 → 视频 → 信息/字幕 → 理解（只读单次） |

复用（一行都没复制）：`bili_send_core.load_cred()`（凭据同源）、
`bili_event_pump._real_llm_factory()`（LLM 配置同源）、`bilibili_api` 只读接口。

## 用法

```bash
python3 bili_video_read.py                      # 自动取「最新一条 @ 事件」的 BVID
python3 bili_video_read.py --bvid BV1xxxxxxxxx   # 指定视频
python3 bili_video_read.py --event-key at:1:123  # 指定去重表里的事件键
python3 bili_video_read.py --no-llm              # 只抓素材，不调 LLM（校验链路用）
python3 bili_video_read.py --json                # 机器可读输出
```

## 安全红线（代码里卡死）

1. **只读**：不写 `bili_event_state.json`、不写 `bili_comment_log.jsonl`、不写 Ledger
2. **不写 L2 / 不落记忆 / 不建新层 / 不碰发送与状态机**
3. **单视频、串行、一次性**：不循环、不爬取、不逐条探测评论（无请求放大）
4. **无字幕就说无字幕**：字幕列表为空 → 如实记 `该视频无字幕`，绝不编造字幕内容
5. **素材不足就说不足**：LLM 拿不到画面，只能依据标题/简介/字幕；不足时明说"素材不足"
6. **格式错就失败**：LLM 输出不合约 → 明确报错，不猜、不兜底成"看起来像对的"
7. **整体硬超时 90s**：超时即停，不重试

## 第一阶段不做（留给 C.5 后续）

写 L2 / 落记忆、回评闭环、批量视频、分 P 遍历、弹幕/评论辅助理解、任务调度常驻。
