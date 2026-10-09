# PROJECT_BRAIN / 05 第三方来源与许可证

> 全部 `[实测]` 2026-10-10，取自各插件 `metadata.yaml` 与 `LICENSE` 文件头部。

## 一、宿主

| 组件 | 版本 | 许可 |
|---|---|---|
| AstrBot | 4.28.0 | AGPL-3.0（仓库根 LICENSE） |

## 二、插件许可总表（23 个）

> **口径修正（2026-10-10 P1）**：本表原标"25 个"为**计数错误**。`[实测]` `ls -1 /AstrBot/data/plugins/` 共 **24 个条目** = **23 个插件目录**（22 个 `astrbot_plugin_*` + 1 个 `meme_manager`）**+ 1 个 `data/` 运行数据目录**（非插件）。表内 23 行与实测**逐条对齐**。

| 插件 | 版本 | 作者 | 仓库 | LICENSE |
|---|---|---|---|---|
| iris_chat_memory | 0.3.0 | Leafiber | Leafliber/astrbot_plugin_iris_chat_memory | **AGPL-3.0** |
| nana_admin_guard | v1.0.0 | Linna | — | **无 LICENSE（奈奈自制）** |
| nana_anchor | 1.0.0 | Nana | — | **无（奈奈自制）** |
| nana_bilievent | v1.0.0 | Nana | — | **无（奈奈自制）** |
| linna_tmp | v1.0.0 | Linna | — | **无（自制/临时）** |
| biliread | v1.2.0 | SodaCode 等 | SodaCodeSave/astrbot_plugin_biliread | AGPL-3.0 |
| debounce | 1.1.1 | Jason.Joestar | advent259141/astrbot_plugin_debounce | AGPL-3.0 |
| dynamic_life_state | v0.3.1 | Hola-Gracias | Hola-Gracias/astrbot_plugin_dynamic_life_state | AGPL-3.0 |
| emotionai_pro | v4.0.0 | asakiyoshi | — | **无** |
| livingmemory | 2.7.0-beta.1 | lxfight | lxfight-s-Astrbot-Plugins/… | AGPL-3.0 |
| mimo_tts | v2.3.2 | unsuited_ | SteveBaka/astrbot_plugin_mimo_tts | MIT |
| mimo_tts_clone | v0.7.2 | Justice-ocr | Justice-ocr/astrbot_plugin_mimo_tts_clone | MIT |
| parser | v1.5.7 | Zhalslar | Zhalslar/astrbot_plugin_parser | MIT |
| pokepro | v2.1.1 | Zhalslar | Zhalslar/astrbot_plugin_pokepro | GPL |
| portrayal | v1.1.7 | Zhalslar | Zhalslar/astrbot_plugin_portrayal | MIT |
| proactive_chat | v1.2.5 | DBJD-CR | Pancakes-Labs/astrbot_plugin_proactive_chat | AGPL-3.0 |
| qq_tools | v0.2.1 | YUMU1658 | YUMU1658/astrbot_plugin_qq_tools | **无** |
| qzone | v3.1.0 | Zhalslar | Zhalslar/astrbot_plugin_qzone | GPL |
| self_evolution | Ver 5.4.0 | renyus | Renyus/astrbot_plugin_self_evolution | **CC BY-NC 4.0（非商业）** |
| self_learning | 4.3.0 | NickMo, EterUltimate | NickCharlie/astrbot_plugin_self_learning | AGPL-3.0 |
| splitter | v1.4.8 | 糯米茨 | nuomicici/astrbot_plugin_splitter | **无** |
| video_reference_vision | v0.122 | C₂₂H₂₅NO₆ | Sisyphbaous-DT-Project/… | **无** |
| meme_manager | 5.0.2 | anka | anka-afk/astrbot_plugin_meme_manager | MIT |

## 三、许可证合规结论与要求

1. **AGPL-3.0（宿主 + Iris + 6 插件）**：
   - 若本项目**分发**（含上传公开仓库）包含其源码或其衍生代码，**整体须以 AGPL-3.0 提供**，并**保留原版权与署名**。
   - **禁止**将 Iris 的衍生代码宣称为奈奈原创。
2. **CC BY-NC 4.0（self_evolution）**：**禁止商业使用**，须署名。**建议本项目不纳入其源码**。
3. **MIT（4 个）**：可自由使用，保留许可声明即可。
4. **GPL（pokepro, qzone）**：传染性强，**建议不纳入源码分发**。
5. **无 LICENSE 文件者**：**默认保留全部权利**，**不得**复制其源码进入公开仓库。
6. **奈奈自制插件（4 个）**：本地无 LICENSE → **入库前必须由姐姐指定许可**（建议 MIT 或 AGPL 与宿主一致）。

## 四、上游核对状态

| 项 | 状态 |
|---|---|
| 版本号核对（metadata） | ✅ 已核对 |
| LICENSE 类型核对 | ✅ 已核对 |
| 与上游 commit 逐行 diff | ❌ **未做**（本地无 `.git`、未联网拉取；且本阶段禁止联网安装） |
| 改动边界 | ⚠️ **仅能给出"奈奈改前备份 ↔ 现行"边界**，见 `manifests/nana_iris_changes.diff` |
