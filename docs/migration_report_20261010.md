# 奈奈 Codex 工程迁移勘探报告（第二阶段：独立开发副本）

**执行时间**：2026-10-10 01:5x CST
**执行人**：奈奈（Nana）
**权限级别**：姐姐批准的「独立开发副本准备」
**生产改动**：**0** —— 未修改/移动/覆盖任何生产文件；未重启；未安装依赖；未运行不可信脚本；未 commit/push/上传/部署。

---

## 一、执行摘要

| 项 | 结果 |
|---|---|
| 独立开发副本 | ✅ `/root/nana_dev/nana-core/`（独立于 `/AstrBot` 生产树） |
| PROJECT_BRAIN/ | ✅ **新建**（原文件确认不存在） |
| AGENTS.md | ✅ 新建奈奈工程专用版（**未**复制 AstrBot 官方版） |
| 源码/架构映射 | ✅ 已建立（宿主 + 23 插件 + B站 Agent 外挂） |
| 第三方许可核对 | ✅ 23 个插件 + 宿主，已核版本/作者/LICENSE |
| 敏感扫描 | ✅ 逐文件；**1 个硬编码密钥文件被阻断** |
| 拟提交清单 | ✅ 白名单制，已列 |
| 未解决风险 | ✅ 登记于 `PROJECT_BRAIN/06` |

## 二、交付物索引

| 交付要求 | 位置 |
|---|---|
| 独立开发副本路径 | `/root/nana_dev/nana-core/` |
| PROJECT_BRAIN/ 文件清单及来源 | `PROJECT_BRAIN/00_INDEX.md` |
| AGENTS.md | `/root/nana_dev/nana-core/AGENTS.md` |
| 源码和架构映射 | `PROJECT_BRAIN/01`、`02`、`03` |
| 第三方许可证检查结果 | `PROJECT_BRAIN/05`、`upstream/sources.md` |
| 敏感信息扫描结果 | `manifests/sensitive_scan_report_20261010.md` |
| 拟提交文件清单 | `manifests/proposed_commit_manifest.md` |
| 尚未解决的风险 | `PROJECT_BRAIN/06_open_risks.md` |
| 指纹 | `manifests/fingerprints_20261010.md` |
| Iris 改动 diff | `manifests/nana_iris_changes.diff` |

## 三、关键发现

1. **原始 PROJECT_BRAIN 确实不存在**（`/AstrBot`、`/root` 内 `*brain*` 零命中）→ 已按裁决**新建**并注记。
2. **`/AstrBot/AGENTS.md` 是 AstrBot 官方规范**（uv/pnpm/pre-commit），与奈奈工程无关 → 已**另建**专用版。
3. **源码主体构成**：
   - 宿主 AstrBot 4.28.0（无 `.git`）
   - Iris 插件 v0.3.0（AGPL-3.0，奈奈改动 14 个文件）
   - 奈奈自制插件 4 个
   - B站 Agent 外挂脚本 **10 个文件 / 2681 行**（其中核心 5 个 = 2311 行；原稿"~2311 行"为**部分求和**，已按 P1 口径修正）
4. **Iris 奈奈改动规模**（改前备份↔现行）：`llm_request_hook.py` +447、`semantic_gate.py` +182、`conversation_flow.py` +122、`defaults.py` +102、`message_hook.py` +92、`buffer.py` +88，其余小改。
5. **安全**：唯一真实硬编码密钥在 `test_bili_agent_semantic_retry.py`（已阻断，未复制）。

## 四、本阶段实际执行的动作

1. 只读勘探（find/ls/grep/md5sum/difflib）—— 生产零改动
2. 新建独立目录 `/root/nana_dev/nana-core/`
3. **逐文件扫描后**复制非敏感奈奈原创文件（22 个）
4. 撰写 PROJECT_BRAIN/（7 文件）、AGENTS.md、README、manifests、docs
5. 生成 Iris 改动 diff（66 KB）
6. 生成指纹清单

## 五、下一步等待

⏸ **就地停止**，等待姐姐与小 GPT 共同验收。验收通过后，再决定是否：
- `git init` + `git add`（逐文件）
- 或进一步提交/push（**须另行明确批准**）
