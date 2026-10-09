# 任务卡 T-001 · C.5-V-1 视觉接线适配层增量

> 出具：2026-10-10（奈奈）｜ 状态：**待执行**（姐姐在 Codex Cloud 界面起任务）
> 类型：最小、可离线验收、不触生产 ｜ 优先级：L1（首个真实 Codex 协作任务）

---

## 0. 执行环境与基准（第 0 步必须先做）

| 项 | 值 |
|---|---|
| 执行环境 | Codex Cloud，工作目录 `/workspace/nana-core` |
| 仓库 | `https://github.com/xuni7-ui/nana-core.git` |
| 运行时 | Python 3.12.14 ／ ffmpeg 7.1.5 ／ ffprobe 7.1.5 |
| 基准提交 | **`origin/main`**（服务器最后一次 fetch: 2026-10-09 20:48 UTC，HEAD = `a9b1d36`；**本轮未能联网复核**） |

**第 0 步（强制）**：

```bash
git fetch origin
git rev-parse origin/main          # 回报真实哈希
git checkout -B work origin/main   # 一律从 origin/main 起分支
```

> 若 `origin/main` ≠ `a9b1d36`，**以 fetch 到的为准**，并在 PR 描述里写明基准哈希。
> ⚠️ 云实例可能存在更旧的 `work` 分支快照（曾检出 `a314c4c`）。**禁止在旧快照上开发**：
> 从 `origin/main` 重新起分支，避免 PR 中出现「删掉 R10 提交内容」的假回退 diff。

---

## 1. 目标（只做这一件事）

在 `src/bili_agent/c5v_wiring.py` 上做**一次最小增量**，共两条：

1. **证据不足时二次补帧**：当首次视觉结果 `evidence_sufficient=false` 时，允许在**预算内**用 `fallback_uniform` 再抽一轮帧重试**一次**；仍失败 → 如实降级，**绝不编造**。
2. **视频文件复用**：`vision_brief` 接受可选 `cache_dir`；同名视频已存在则**不重复下载**。

## 2. 代码范围（硬边界）

| 允许改动 | 禁止改动 |
|---|---|
| `src/bili_agent/c5v_wiring.py` | `src/bili_agent/bili_agent.py`（生产主链） |
| `src/bili_agent/test_c5v_wiring.py` | `src/bili_agent/bili_send_*.py` / `bili_event_*.py` |
| （可选）`docs/c5v_wiring_design.md` 追加一节 | `src/bili_agent/notes/**`、`bridge/**`、`PROJECT_BRAIN/**`、`manifests/**` |

## 3. 验收标准（全中才算 DONE）

1. **默认关闭零变化**：`NANA_C5V_WIRING` 未设/为 `0` 时，`augment_material_brief` 返回值与现状**逐字节一致**。
2. **降级不编造**：任何失败路径（视频不可得、超预算、接口异常、非 JSON）→ 原素材块逐字节不变 + `reason` 字段。
3. **新增行为可证**：`cache_dir` 命中时**不调用**下载器（可用注入 fetcher 计数证明）；二次补帧**最多一次**，且受同一总预算约束（超预算则拒绝）。
4. **零新增依赖 / 零密钥**：不得引入第三方新依赖，不得硬编码任何 key、cookie、token；顶层只 import 标准库（沿用现有 AST 检查）。
5. **测试全绿**：原有 **11 条**用例继续通过，并**新增 ≥2 条**覆盖上述新行为。

## 4. 测试命令

```bash
python3 src/bili_agent/test_c5v_wiring.py
```

- 预期输出：`结果：13 通过 / 0 失败`（11 旧 + ≥2 新）。
- ⚠️ **不要用 `pytest tests/`**：本仓库没有 `tests/` 目录；`test_c5v_wiring.py` 是**自跑脚本**（`check()` + `__main__`），pytest 会收集到 0 条（已实测）。
- 测试用 `ffmpeg lavfi` 现造视频，**全程零公网请求**；耗时上限 300s。

## 5. 禁止事项

- ❌ 不改生产配置、不动 `bili_agent.py`、不碰 `_understand()`
- ❌ 不 `push` 到 `main`、不自动合并、不删分支以外的东西
- ❌ 不新建/重建 Codex 环境，不改环境配置
- ❌ 不启用付费 API、不发任何真实网络请求（视觉客户端只允许**注入**）
- ❌ 不扩大范围到 C.4/C.7/记忆系统
- ❌ 不写真实 BVID / 真实凭据进代码或测试

## 6. 交付物与回执

- 交付：**一个 PR**（分支 `work` 或 `codex/t001` → `main`），**保持未合并**，PR 描述含：基准哈希、改动文件、测试命令与结果、回滚方式（删分支即回滚）。
- 回执格式（三行即可）：
  1. `base=<origin/main 真实哈希>` ／ `head=<分支哈希>`
  2. `test=python3 src/bili_agent/test_c5v_wiring.py → N 通过 / M 失败`
  3. `changed=<文件列表>`

---

## 7. 回滚

纯新增分支改动，**删分支即完全回滚**；不涉及生产、不涉及环境、不涉及数据。
