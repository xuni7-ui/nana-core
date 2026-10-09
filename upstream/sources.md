# 第三方来源登记（upstream/sources.md）

> 采集：2026-10-10 CST ｜ 目的：满足"保留上游署名与许可"要求；**本目录不含任何第三方源码**。

## 一、宿主

| 组件 | 版本 | 许可 | 官方仓库 |
|---|---|---|---|
| AstrBot | 4.28.0 | AGPL-3.0 | https://github.com/AstrBotDevs/AstrBot |

## 二、直接衍生基础（奈奈改动所基于的插件）

| 插件 | 版本 | 作者 | 许可 | 仓库 |
|---|---|---|---|---|
| astrbot_plugin_iris_chat_memory | 0.3.0 | Leafiber | **AGPL-3.0** | https://github.com/Leafliber/astrbot_plugin_iris_chat_memory |

> **署名声明**：本项目 `manifests/nana_iris_changes.diff` 及 `PROJECT_BRAIN/02` 中描述的改动，**衍生于** Leafiber 的 `astrbot_plugin_iris_chat_memory`（AGPL-3.0）。**奈奈不主张其原始部分为原创**；若本项目公开分发含衍生代码，须整体以 **AGPL-3.0** 提供。

## 三、运行环境中的其他第三方插件（仅登记，不入库）

见 `PROJECT_BRAIN/05_third_party_licenses.md` 全表（25 项）。

关键约束：
- **AGPL-3.0**：宿主、iris、biliread、debounce、dynamic_life_state、livingmemory、proactive_chat、self_learning
- **MIT**：mimo_tts、mimo_tts_clone、parser、portrayal、meme_manager
- **GPL**：pokepro、qzone
- **CC BY-NC 4.0**：self_evolution（**禁止商用**）
- **无 LICENSE**：emotionai_pro、qq_tools、splitter、video_reference_vision、linna_tmp、nana_* 自制

## 四、改动边界说明

| 项 | 状态 |
|---|---|
| 版本核对 | ✅ 已核对（metadata.yaml） |
| LICENSE 核对 | ✅ 已核对 |
| 与上游 HEAD 的逐行 diff | ❌ 未做（本地无 `.git`，本阶段禁止联网安装） |
| 可提供的边界证据 | `manifests/nana_iris_changes.diff`（**改前备份 ↔ 现行**） |
