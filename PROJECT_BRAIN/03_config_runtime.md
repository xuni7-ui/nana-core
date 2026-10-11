# PROJECT_BRAIN / 03 配置与运行数据

> **纪律**：本文件**只记录职责、位置、接口**，**不复制实际内容**、**不记录任何密钥原文**。所有条目 `[实测]` 2026-10-10。

## 一、配置与运行数据映射

| 资产 | 路径 | 职责 | 敏感级别 | 入库 |
|---|---|---|---|---|
| 全局配置 | `/AstrBot/data/cmd_config.json` | 平台/模型/API Key 等全局配置 | 🔴 极高 | ❌ 禁 |
| 主数据库 | `/AstrBot/data/data_v4.db`(+shm/wal) | 会话/消息/记忆持久化 | 🔴 极高 | ❌ 禁 |
| 运行日志 | `/AstrBot/data/logs/` | 运行日志 | 🟠 高 | ❌ 禁 |
| 插件数据 | `/AstrBot/data/plugin_data/` | 各插件运行态数据 | 🟠 高 | ❌ 禁 |
| B站凭证 | `/root/.nana_secrets/bilibili_credential.json` | 登录凭证(sessdata 等) | 🔴 极高 | ❌ 禁 |
| 酒馆密码 | `/root/.nana_secrets/sillytavern_password.txt` | 第三方密码 | 🔴 极高 | ❌ 禁 |
| B站事件日志 | `/root/.nana_secrets/bili_event_log.jsonl`(432 KB) | 事件留档 | 🟠 高 | ❌ 禁 |
| B站评论日志 | `/root/.nana_secrets/bili_comment_log.jsonl` | 发送留档 | 🟠 高 | ❌ 禁 |
| 事件状态 | `/root/.nana_secrets/bili_event_state.json` | 去重/游标状态 | 🟡 中 | ❌ 禁（含运行态） |
| 对话流水 | `.../workspaces/.../对话流水/*.jsonl` | 私人聊天 | 🔴 极高 | ❌ 禁 |
| 记忆合并库 | `.../merged_memory.json/.md` | L2 记忆快照 | 🔴 极高 | ❌ 禁 |

## 二、接口说明（供 Codex 理解，不含凭证）

| 接口 | 形式 | 说明 |
|---|---|---|
| AstrBot 插件接口 | `Star` 基类 / FunctionTool | 插件通过此接口接入 |
| LLM 请求钩子 | `iris_memory/core/llm_request_hook.py` | 注入记忆上下文（奈奈改动重点） |
| 消息钩子 | `iris_memory/core/message_hook.py` | 处理用户消息（奈奈改动重点） |
| 动作账本 | `iris_memory/core/action_ledger.py` | 记录奈奈的对外动作 |
| B站事件泵 | `bili_event_pump.py` (cron/常驻) | 轮询 B站消息事件 |
| B站发送 | `bili_send_core.py` → `bili_send_comment.py` | 发布评论/回复 |

## 三、运行状态（`[实测]` 采集时快照）

| 项 | 值 | 来源 |
|---|---|---|
| B站事件泵 last_poll | `OK`（2026-10-10 01:53:00+08:00） | `[实测]` 事件泵锁定/日志 |
| B站 Agent last_task | `DONE`（2026-10-09 19:31:09） | `[聊天记忆/账本]` |
| 发评论 last_action | `VERIFIED`（2026-10-09 19:31:09） | `[聊天记忆/账本]` |

> ⚠️ 上表为**采集时刻快照**，不代表持续状态；**指纹 ≠ 当前运行态**。

## 四、密钥登记（掩码，仅本机可见，**不入库**）

| 凭证 | 位置 | 状态 |
|---|---|---|
| B站登录凭证 | `~/.nana_secrets/bilibili_credential.json` | ✅ 在册 |
| SillyTavern 密码 | `~/.nana_secrets/sillytavern_password.txt` | ✅ 在册 |
| API Key × 若干 | `data/cmd_config.json` | ✅ 掩码登记 |

> 本文件**刻意不记录**任何密钥的值、前缀或长度。


---

## P3 增补（2026-10-10（CST））

- 【实测】依赖清单入仓库根 `requirements.txt`（精确版本，无密钥）。
- 【实测】Codex Bridge Node 侧：Node `v24.20.0` / npm `11.19.0` / `@openai/codex` `0.162.0`，安装于 `/opt/nana_codex`（**不在 git**）；重建见 `docs/bridge_node_rebuild.md`。
- 【实测】外部工具：FFmpeg/FFprobe `7.1.5`。
- 配置示例均**不含真实密钥**。


---

## P4 增补 · 真实运行态 hook/registry 口径（2026-10-11 CST，`[实测]`）

- 【实测】AstrBot 运行位置 = **CONTAINER**（与奈奈同一容器；PID1=`python main.py`）；版本 **4.28.0**；Python 3.12.14。
- 【实测】插件目录 `/AstrBot/data/plugins`；保留插件目录 `/AstrBot/astrbot/builtin_stars`；插件数据 `/AstrBot/data/plugin_data`。
- 【实测】**不存在统一 hook dispatcher**。唯一真派发器 `EventBus.dispatch()`（`astrbot/core/event_bus.py:39`）**只服务消息事件**；
  生命周期/平台/结果装饰 hook 由各站点**直接遍历同一注册表**（`star_handlers_registry`，`astrbot/core/star/star_handler.py:216`）。
- 【实测】`OnPluginLoadedEvent` 派发点 = `astrbot/core/star/star_manager.py:1421`（**plugin manager 直调**，非 dispatcher）；
  `OnPluginUnloadedEvent` = `:2044`。卸载移除链 = `_unbind_plugin()`（`:1874`）→ `get_handlers_by_module_name`（`:1894`）→ `remove()`（`star_handler.py:205`）。
- 【实测】`ASTRBOT_RELOAD` **未设置**（宿主 shell + `/proc/1/environ` 均无）⇒ 文件 watcher 未启动。
- 【实测】无重启载入新插件的现存通道 = Dashboard `POST /api/plugin/reload`（`astrbot/dashboard/api/plugins.py:1391/837/1104`），**需 JWT**。
- 详见：`docs/nana_shadow_astrbot_dispatcher_audit_20261011.md`。
