# C.5-V-1「视频视觉接线」设计与选型

> 日期：2026-10-10 ｜ 作者：奈奈 ｜ 状态：**适配层已实现 + 离线验证通过；生产接线待授权**
> 上游文档：`src/c5v/README_c5v.md`（离线模块）、`PROJECT_BRAIN/07_ROADMAP.md`（L1）

---

## 1. 接线目标

让 B站 Agent 的 Understand 阶段，除现有「标题/简介/字幕/弹幕/热评」外，再多一路
**来自关键帧的画面事实**，且该路必须**可降级、可审计、绝不编造**。

```
BVID → yt-dlp 取本地视频 → ffprobe 结构 → scene-cut 关键帧 → 视觉模型
     → c5v.visual_facts.v1 → facts_to_brief() → 追加到 _video_material_brief 之后 → _understand
```

## 2. 方案比较（奈奈自行比较后选型）

| 方案 | 做法 | 优点 | 缺点 | 判定 |
|---|---|---|---|---|
| **A. 追加式适配层（已选）** | 新增 `c5v_wiring.py`，在 `_video_material_brief` **之后追加**一段画面事实 | 只增不改、可一键关闭、失败逐字节还原、改动面最小 | 需多一次下载 + 视觉调用 | ✅ **选它** |
| B. 改造 `_video_material_brief` 内部 | 把视觉逻辑写进原函数 | 少一个文件 | 侵入既有稳定语义，回归面大 | ❌ |
| C. 复用生产 `astrbot_plugin_video_reference_vision` | 走它已有的抽帧转述链路 | 不新增代码 | 它面向 QQ 引用视频、非 B站；跨插件耦合难测；会动生产 | ❌（作为未来参考） |
| D. 直接上 `video_url` 原生视频解析 | 把 B站视频 URL 直接交给支持 `video_url` 的模型 | 代码最少 | 需要可公网访问的视频直链（B站防盗链），不确定性高 | ❌ |

**选 A 的理由**：与 AGENTS.md「只增不改 / 可降级 / 有证据」最一致，且失败路径可证明地不改动原行为。

## 3. 关键设计

| 机制 | 取值 / 做法 |
|---|---|
| 开关 | `NANA_C5V_WIRING`（默认 `0` = 关闭，行为与现状**逐字节一致**） |
| 视频获取 | `YtDlpFetcher`（yt-dlp **已装** 2026.08.19）；可注入替换 |
| 分辨率/体积 | ≤480p、`--max-filesize 120M`、`--no-playlist` |
| 时长预算 | 默认 ≤600s，超限**直接拒绝**并说明 |
| 抽帧 | ≤8 张（沿用 c5v 模块）、长边 ≤640、`cleanup=True` |
| 视觉客户端 | 只能**注入**或读环境变量；缺则 `available=False`（离线，不联网） |
| 失败语义 | 任何失败 → 原素材块**逐字节不变** + `reason`；**绝不注入编造画面** |
| 凭据 | 本层零硬编码；真实 key 由姐姐注入环境变量，不入库 |

## 4. 验证证据（离线，`python3 test_c5v_wiring.py`）

| # | 用例 | 结果 |
|---|---|---|
| T1 | 未启用 → 素材块逐字节不变 | ✅ |
| T2 | 视频不可得 → 原文不变 + reason | ✅ |
| T3 | 本地视频 + 注入客户端 → 追加【画面事实】且含 summary | ✅ |
| T4 | 视觉接口异常 → 原文不变 | ✅ |
| T5 | 非 JSON 回复 → 不注入（不编造） | ✅ |
| T6 | 超时长预算 → 拒绝并说明 | ✅ |
| T7 | 无客户端 → 明确离线、不注入 | ✅ |
| T8 | AST 扫描：不 import 生产发送/事件/日志模块；无硬编码密钥 | ✅ |
| T9 | 不可用时 `render_block` 返回空串 | ✅ |

**11/11 通过。** 测试视频由 `ffmpeg lavfi` 现造，**全程零公网请求**。

## 5. 生产接线步骤（**待授权，L3/L4**）

1. 把 `src/c5v/bili_video_vision.py` 与 `src/bili_agent/c5v_wiring.py` 放到生产同目录（或加 path）。
2. 在 `bili_agent._understand()` 的 `material_block` 组装后加两行：

```python
from c5v_wiring import augment_material_brief
material_block, c5v_meta = await augment_material_brief(material_block, task.bvid)
```

3. 生产环境设置 `NANA_C5V_WIRING=1` 与 `NANA_C5V_VISION_BASE_URL/_API_KEY`。
4. 更新 HC 封板指纹；跑一次真实 BVID 端到端；失败则回滚为 `NANA_C5V_WIRING=0`（一行回滚）。

**回滚成本：改一个环境变量即可完全恢复现状。**

## 6. 未解风险

| 风险 | 级别 | 对策 |
|---|---|---|
| B站视频下载可能需登录 cookie（高清/部分稿件） | 中 | 先用 ≤480p 匿名；失败即降级，不阻塞主链 |
| 下载耗时/带宽（长视频） | 中 | 时长 + 体积双上限；总预算超时即丢弃 |
| 画面事实被模型过度解读 | 中 | 提示词明写"不是亲眼看过"；`evidence_sufficient` 如实透传 |
| 生产接线属 L4 | — | **本次不做**，只留待授权步骤 |
