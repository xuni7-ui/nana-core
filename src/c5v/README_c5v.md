# C.5-V-1 · 视频视觉理解（离线独立模块）

> 状态：**离线完成、未接线**。72h 基线观察期内**不接生产**。
> 阶段：C.5-V-1（Level 2 = 看懂主要画面与事件顺序，非逐帧理解）

---

## 1. 目标链路

```
视频文件
  → ① 视频结构分析（ffprobe）
  → ② 智能关键帧（ffmpeg 场景切换检测 + 配额选帧）
  → ③ 视觉模型（OpenAI 兼容 /chat/completions 多模态）
  → ④ 结构化视觉事实（schema = c5v.visual_facts.v1）
  → （未来）BiliAgent Understand → Decide
```

## 2. 文件清单

| 文件 | 作用 |
|---|---|
| `bili_video_vision.py` | 主模块（离线、独立、零生产依赖） |
| `test_bili_video_vision.py` | T1–T10 全离线测试（注入假视觉客户端） |
| `README_c5v.md` | 本文件 |

**位置说明**：本阶段放在工作区 `c5v_offline/`，**对 `/root/.nana_secrets/` 零足迹**。
接线阶段再决定是否移动到 Agent 同目录（那一步需要姐姐授权 + 更新封板指纹）。

## 3. 算法

### 3.1 结构分析
`ffprobe -select_streams v:0` → duration / width / height / avg_frame_rate / codec。

### 3.2 智能关键帧
1. **场景切换检测**：`ffmpeg -vf "select='gt(scene,θ)',showinfo" -f null -` 解析 stderr 的 `pts_time`，
   阈值 θ 默认 **0.30**。
2. **去重与间隔**：切换点升序、相邻最小间隔 0.5s、剔除首尾 0.05s 内的边界噪声。
3. **配额选帧**（硬上限 ≤8 张）：
   - 必取 **head**（0.2s 或 2% 处）与 **tail**（时长−0.2s）；
   - 中间配额 = 8 − 2：切换点 ≤ 配额 → 全取；切换点 > 配额 → 沿时间轴**均匀抽**配额个；
   - 截断到 ≤8，mode = `scene_cut`。
4. **降级**：一个切换点都没检测到 → 均匀采样 **4 帧**，mode 显式标记 `fallback_uniform`
   （**不假装**自己是场景检测结果）。

### 3.3 抽帧
`ffmpeg -ss t -i in -frames:v 1 -vf scale='min(640,iw)':-2 -q:v 3` → jpg（长边 ≤640，控 token）。

### 3.4 视觉调用
- 统一入口 `call_vision_model(images_b64, prompt, client=...)`；
- **client=None 时明确返回 `called=False`**，绝不偷偷联网；
- 默认客户端 `OpenAIVisionClient`：OpenAI 兼容 `chat/completions`，
  `image_url` 传 `data:image/jpeg;base64,...`；
- 默认模型 `deepseek-flash`（AstrBot 面板 `default_image_caption_provider_id`，`modalities` 含 `image`）。

## 4. JSON 输出格式（`c5v.visual_facts.v1`）

```json
{
  "schema": "c5v.visual_facts.v1",
  "module": {"name": "bili_video_vision", "stage": "C.5-V-1"},
  "video":  {"source": "...", "duration_s": 6.0, "width": 320, "height": 240, "fps": 15.0, "vcodec": "h264"},
  "keyframes": {"count": 4, "selection_mode": "scene_cut", "scene_cuts_detected": 2,
                "items": [{"i":0,"t":0.2,"reason":"head","bytes":674}, ...]},
  "model": {"name": "deepseek-flash", "called": true, "frames_sent": 4,
            "tokens": {...}, "elapsed_s": 17.0, "error": null},
  "facts": {"summary": "...", "scenes": [{"order":1,"start_s":0,"end_s":2,"description":"..."}],
            "entities": [...], "on_screen_text": [...], "actions": [...],
            "evidence_sufficient": true, "confidence": 0.9},
  "raw_text": "...",
  "errors": [],
  "ok": true
}
```

**关键约定**：`facts = null` 表示**没拿到可信画面事实**（缺帧 / 接口异常 / 回复非 JSON），
此时 `ok=false` 且 `errors` 非空 —— **绝不编造画面内容**。

## 5. 视觉结果如何进入 Understand（**本阶段未接线**）

备好但未启用：`facts_to_brief(facts)` 把事实压成一段纯文本，未来与现有
`_video_material_brief()` 并列注入 `bili_agent._understand()` 的 system 提示词。
接线需：① 72h 收尾后；② 姐姐授权；③ 同步更新 HC 封板指纹。

## 6. 离线测试 T1–T10（`python3 test_bili_video_vision.py`）

| # | 用例 | 断言 |
|---|---|---|
| T1 | 结构分析 | 6.00s / 320×240 / 15fps |
| T2 | 镜头切换检测 | 命中 2.0s、4.0s 两处切换 |
| T3 | 关键帧选择 | ≤8 张、含 head+tail、mode=scene_cut |
| T4 | 无切换降级 | mode=fallback_uniform、4 张 |
| T5 | 抽帧落盘 | 张数一致、JPEG 魔数、非空 |
| T6 | base64 | 编码可逆 |
| T7 | 视觉调用 | 注入客户端、图片数/提示词/usage 正确 |
| T8 | 结构化事实 | schema 校验通过、count 与 items 一致 |
| T9 | 异常路径 | 缺文件/接口炸/非 JSON → facts=null，不编造 |
| T10 | 隔离与确定性 | 结果可复现 + AST 扫描无生产模块依赖 |

**结果：10/10 通过。**

## 7. 真实调用记录（1 次，人工触发）

| 项 | 值 |
|---|---|
| 模型 | `deepseek-flash`（DeepSeek 官方直连） |
| 输入 | 4 张关键帧（320×240 jpg，红/蓝/绿/绿） |
| 输出 | 正确识别「红 → 蓝 → 绿」，`evidence_sufficient=false`（诚实自评） |
| tokens | prompt 977 + completion 3288（含 reasoning 3078）＝ 4265 |
| 耗时 | 17.0 s |
| 结论 | 视觉链路**真实可用**，非模拟 |

## 8. 风险

| 风险 | 级别 | 说明 / 对策 |
|---|---|---|
| 磁盘/临时帧堆积 | 低 | 默认 `workdir=None` 时落 `/tmp`，`cleanup=True` 可自动清；生产接线需绑定清理策略 |
| 长视频耗时 | 中 | scene 检测需完整解码一遍；接线时应加时长上限（建议 ≤10min）与总超时 |
| token 成本 | 中 | 8 帧 ≈ 1k prompt token；建议 ≤8 帧 + 640px 上限（已内置） |
| 模型不支持图 | 低 | 已实测 deepseek-flash 可收图；失败时 `called=True/error` 如实记录，不静默 |
| 关键帧漏拍关键内容 | 中 | 纯切换点会漏「无剪辑但画面变化」；已保留 `evidence_sufficient` 与未来补帧入口 |
| 生产污染 | **无** | 本阶段零接线、零生产依赖、零生产写入 |

---

_生成：2026-10-07 · 奈奈 · C.5-V-1 离线阶段_
