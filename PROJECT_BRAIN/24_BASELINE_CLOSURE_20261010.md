# PROJECT_BRAIN / 24 工程基线收口（2026-10-10）

> 分级：**【实测】**本机命令直出 · **【源码确认】**与上游源码逐字节比对 · **【文档】**既有报告 · **【推断】** · **【未知/待验证】**
> 本文件是本次"Nana Core 工程基线收口"阶段（A–G）的**总证据文件**。

---

## A. AstrBot 主体补丁 D2
- **上游基线**：GitHub `AstrBotDevs/AstrBot` tag `v4.28.0`，commit `a412146401426c0cdff8bbefb8627a03da519da8`；PyPI sdist `astrbot-4.28.0.tar.gz` sha256 `ea48a4ba…c655`。双源交叉。**【源码确认】**
- **改动**：3 处 / +3 −3（`qqofficial_message_event.py` 加 `C2CMessage`；`qqofficial_platform_adapter.py` 两处移除主动推送 `msg_seq`）。**【源码确认】**
- **补丁**：`patches/astrbot/astrbot-4.28.0-qqofficial-proactive-send.patch`。**【实测】**`git apply --check` 通过；往返应用后与生产**逐字节一致**。
- **许可**：AGPL-3.0-or-later。**【实测】**
- **敏感**：无。**【实测】**

## B. Iris 定制 D3
- **上游**：`Leafliber/astrbot_plugin_iris_chat_memory` 0.3.0，tag commit `0557a4c1…aa6f6`，241 blob，AGPL-3.0。**【源码确认】**
- **14 处 = 7 改 + 7 新增**；`git blob SHA1` 全量比对：234 相同 / 7 改 / 7 增 / 0 缺失。**【源码确认】**
- **材料**：`materials/iris_customizations/`（补丁 + NEW_FILES + AGPL 全文 + 指纹 + 重建说明）。**【实测】**补丁往返应用后 14 文件与生产逐字节一致。
- **主题覆盖**：Semantic Gate、Action Ledger、时间工具、长消息处理、相关测试。**【源码确认】**
- **隔离**：独立目录，附 AGPL，不与原创混；许可决策留给姐姐。

## C. B站 Agent / C.5-V
- **比对**【实测】：10 个 .py 仓库==生产；**5 个登录脚本本轮补入** `materials/bili_agent/login/`（零真值凭据、零长 ID）。
- **排除 9 个测试脚本**：含真实事件 ID/疑似真实 UID → 见 `materials/bili_agent/EXCLUSIONS.md`。
- **C.5-V**：源码/依赖/测试/接入状态已记录；**未接入生产事件泵**（授权禁止）。**【实测】**

## D. 依赖与重建
- `requirements.txt`（精确版本，源自实测）。**【实测】**
- `docs/bridge_node_rebuild.md`：Node v24.20.0 / npm 11.19.0 / `@openai/codex` 0.162.0 + 重建步骤。**【实测】**
- 外部工具：FFmpeg/FFprobe 7.1.5。**【实测】**
- 配置示例：**不含真实密钥**（见 `requirements.txt` 注释与各 README）。

## E. 许可证与来源
- `LICENSES_AND_PROVENANCE.md`：原创（待姐姐定）/ 派生（AGPL，保原许可）/ 未改依赖（不分发）三类。【实测】
- **未**简化 AGPL 义务；**未**擅自更改项目整体许可证。

## F. PROJECT_BRAIN 更正（关键）
| 旧描述 | 更正为 | 依据 |
|---|---|---|
| "Codex CLI 未安装/登录被阻断" | **已安装**：`/opt/nana_codex`, `@openai/codex` 0.162.0，自定义 Provider 下**真实 exec 成功** | R14 实测 |
| "上游 v0.3.0 原始文件未获取" | **已获取**（tag `0.3.0`, 241 blob, 逐字节校验） | 本文件 B |
| "Runner 未验证" | **本地 Bridge Runner 真实闭环**（applied=True, 13-0） | 【实测】R14 |
| 本地 Runner 成功 ≠ Codex **Cloud** 成功 | Cloud environment 仍**未创建**（`work@a314c4c` 落后 main），仍需姐姐界面一步 | 【实测】 |

## G. GitHub 同步
- 远端 `main` 同步前 = `ff1c8704a056c6ebe82594a24f2ecba48ae02e69`（= 本地 HEAD）。**【实测】**
- 本轮为**纯增量、非强制**推送；推送后完整 HEAD 见 `09_STATE.md` 与 `11_CHANGELOG.md`。**【实测】**
- 生产零改动、无重启、无部署、无付费任务。**【实测】**

## 交付给 GPT-6.1 Sol 的审查入口
1. `patches/astrbot/` —— AstrBot 主体偏离（可复现）。
2. `materials/iris_customizations/` —— Iris 14 处定制（可复现，AGPL）。
3. `materials/bili_agent/` —— B站 Agent 纳入/排除。
4. `src/`、`bridge/`、`docs/`、`requirements.txt` —— 现有可开发源码与依赖。

## 尚未实现 / 仍需独立材料
- Iris 定制逻辑的**逐行语义说明**（当前为补丁+指纹，Sol 可直接读 diff）。
- 9 个测试脚本的**合成夹具版**（未提供）。
- 真实 Codex **Cloud** 闭环（阻塞于 environment，需姐姐）。
- `/opt/nana_codex` 未入 git（容器重建需重做，见重建说明）。
