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


---

## P5 增补 · message pipeline 安全观察点（2026-10-11 CST · R03-M1，`[实测/源码]`）

被审源码：`/AstrBot/astrbot` @ **4.28.0**。详见 `docs/nana_shadow_message_observer_audit_20261011.md`。

- 【实测】真实消息调用链唯一入口：`EventBus.dispatch()`（`core/event_bus.py:39`）
  → `asyncio.create_task(scheduler.execute(event))`（`:52`）
  → `PipelineScheduler.execute()`（`core/pipeline/scheduler.py:82`）→ `_process_stages()`（`:36`）
  → `STAGES_ORDER`（`core/pipeline/stage_order.py:3-13`，共 9 段）。
- 【实测】**SAFE result-path observer = AVAILABLE**
  `EventType.OnDecoratingResultEvent`（enum `core/star/star_handler.py:234`；
  注册器 `core/star/register/star_handler.py:730`；调用点 `core/pipeline/result_decorate/stage.py:158-189`）。
  安全性三根支柱：
  1) `stage.py:173` `await handler.handler(event)` —— **返回值被丢弃**，返回 `None` 不改变消息结果；
  2) `stage.py:181-182` `except BaseException: logger.error(...)` —— **局部吞掉**，不 re-raise、不产生默认错误回复；
  3) `stage.py:184-189` 仅当 handler 自己 `stop_event()` 才 `return`。
  与 `pipeline/context_utils.py:54-75` 的 `call_handler()`（会 `event.set_result(ret)`）语义**完全不同**。
- 【实测】**SAFE early all-message observer = NOT_AVAILABLE**。
  `OnDecoratingResultEvent` 只在「本条消息产生了待发送结果」时触发（`stage.py:130-132` 早退；
  `:134-137` 流式分片早退），**不是**逐条消息观察点。**禁止**声称存在「每条消息到达即安全观察」的 hook。
- 【实测】第二候选：`OnAfterMessageSentEvent`（`core/pipeline/respond/stage.py:328`，经 `call_event_hook`），
  发生在**真正发送之后**，仅作备选。
- 【实测】**UNSAFE（禁止接）**：
  `AdapterMessageEvent` 是**指令 handler 的分组标签**（`register/star_handler.py:118/168/198/240/268/286/303/326`），
  由 `waking_check/stage.py:172-175` 收集、`process_stage/method/star_request.py:27-36` **当业务 handler 直接执行**
  —— 会 `set_result()` / `yield` / 发消息 / 调模型；
  `OnLLMRequestEvent` / `OnWaitingLLMRequestEvent`（`process_stage/.../internal.py:225/277`、`third_party.py:307`）
  既碰 prompt 本体，又有终止流程语义。
- 【实测】**`plugin_set` 是真实前置条件**：`pipeline/waking_check/stage.py:163-169`
  `plugin_set == ["*"] → event.plugins_name = None`（不过滤）；否则 `= 名单`；
  过滤点在 `core/star/star_handler.py:169-184`（名单外且非 `reserved` 的 handler 全部被剔除），
  另有 `:161-167` `only_activated=True`（插件须 `activated`）。
  ⇒ **「观察器被加载」≠「观察器一定收到 message hook」**。
- 【实测】**全新插件首次免重启加载（人工路径）= YES**：
  `POST /api/plugin/install-upload`（`dashboard/api/plugins.py:1272/584/371`）
  → `PluginService.install_plugin_upload_from_dashboard_form`（`dashboard/services/plugin_service.py:1726`）
  → `PluginManager.install_plugin_from_file`（`core/star/star_manager.py:2076`，`:2087` 解包 / `:2097` 落位 `data/plugins/<new>`）
  → `:2109` `await self.load(specified_dir_name=dir_name)`（`load()` 定义 `:1068`）。
  对比：`reload(name)`（`:1002/1010`）**只**作用于已注册 plugin/module，**不载入全新目录**。
- 【本轮零改动】未安装 / 未 reload / 未重启 / 未改 `plugin_set` / 未读 JWT / 未碰生产插件目录。
