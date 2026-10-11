# AstrBot Hook API 源码审计 — 真实运行态 v4.28.0 (R01)

范围：只读、非敏感程序源码。目标：把 `真实 AstrBot hook = UNKNOWN` 推进为有源码依据的结论。
所有结论给出 **源码路径 + symbol + 证据**，不写“应该可以”。

## 一、核心符号地图

| 机制 | 位置 | symbol |
|---|---|---|
| 事件总线 | `astrbot/core/event_bus.py` | `EventBus.dispatch()` / `event_queue` |
| 管道调度 | `astrbot/core/pipeline/scheduler.py` | `PipelineScheduler.execute()` / `_process_stages()` |
| Handler 注册表 | `astrbot/core/star/star_handler.py` | `StarHandlerRegistry` / `star_handlers_registry` |
| 事件类型枚举 | 同上 `EventType` | 16 种（见下） |
| 插件管理 | `astrbot/core/star/star_manager.py` | `PluginManager.load/reload/_unbind_plugin` |
| 注册装饰器 | `astrbot/core/star/register/star_handler.py` | `register_on_plugin_loaded` 等 |
| 消息 handler 派发 | `astrbot/core/pipeline/process_stage/method/star_request.py` | `call_handler(...)` |
| 事件队列句柄 | `astrbot/core/star/context.py` | `Context.get_event_queue()` (L733) |

## 二、十问逐条回答

1. **支持插件热加载？** 代码支持：`star_manager.py:221` 当 `ASTRBOT_RELOAD=1` 时启动 `_watch_plugins_changes()`；用 `watchfiles.awatch(...PythonFilter(), recursive=True)` 监听插件目录，文件变化→`_handle_file_changes()`→`reload(plugin_name)`。**但**：`_handle_file_changes` 只遍历 **已在 star_registry 中且 activated** 的插件（L242-267），**新目录不会被自动加载**。实测本机 **`ASTRBOT_RELOAD` 未设置 → watcher 未运行**。

2. **支持插件热卸载？** 支持：`PluginManager._unbind_plugin()` (L1874) 会 `del star_map[...]`、从 `star_registry` 删除、`star_handlers_registry.remove(handler)`、清理 `star_handlers_map`、移除 `llm_tools`、`unregister_platform_adapters_by_module()`、`_purge_modules()`。`uninstall_plugin()` (L1753)。

3. **动态加载是否需要 restart？** 源码路径 `load()`/`reload()` 是 **进程内** 操作，本身不需要重启。**但到达它的触发通道受限**：
   - 文件 watcher（自动）→ 未开启（`ASTRBOT_RELOAD` 缺省）；
   - Dashboard API `POST /api/plugin/reload`（`dashboard/api/plugins.py:837,1104`）→ 需 **Dashboard JWT 鉴权**（`dashboard/server.py`，jwt HS256，secret 属敏感信息，禁止读取）；
   - `reload(name)` 只能重载 **已注册** 插件，新插件目录 **不会被它载入**。
   → 在当前运行配置下，**载入一个全新插件事实上需要 restart**。

4. **卸载后 callback 是否真的从 registry 移除？** 是：`star_handlers_registry.remove()`（`star_handler.py:205`）+ `star_handlers_map` 前缀清理（`star_manager.py:1897-1906`）。

5. **能否注册只观察、不修改 event 的 callback？** 能：可直接注册 `EventType.OnPluginLoadedEvent`/`OnPluginUnloadedEvent`/`OnLLMRequestEvent` 等，handler 返回 `None` 即不产生结果。

6. **能否阻止 observer 修改 response？** 能：pipeline 仅对 **yield 出的结果** 做 `set_result`；observer 不 yield、不调用 `event.set_result` 即零副作用。

7. **是否存在 before/after/generic hook？** 存在：`EventType` 含 `OnLLMRequestEvent`(请求前)/`OnLLMResponseEvent`(响应后)/`OnDecoratingResultEvent`(发送前)/`OnAfterMessageSentEvent`(发送后)/`OnAgentBeginEvent`/`OnAgentDoneEvent`/`OnCallingFuncToolEvent`/`OnLLMToolRespondEvent`/`OnPluginLoadedEvent`/`OnPluginUnloadedEvent`/`OnPluginErrorEvent` 等。

8. **是否有内部 synthetic event dispatch API？** 有间接通道：`Context.get_event_queue()`（`context.py:733`）暴露真实 `event_queue`；向其 `put(event)` 即进入 `EventBus.dispatch()`(真实 dispatcher)。**风险**：message 路径会跑完整 pipeline（含 LLM/respond），可能触发真实回复 → **不得用于本轮 probe**。另：无自带 “synthetic/test” `EventType`。

9. **能否区分 internal synthetic probe 与真实用户 message？** 框架 **无原生区分**（无专用 synthetic 事件类型）。只能由 observer 自带 metadata（`source=astrbot_internal_probe`、`probe_id`）自证。

10. **observer 异常是否会阻塞主消息链？**
    - 生命周期 hook（如 `OnPluginLoadedEvent`）：`star_manager.py:1428-1434 / 2049-2056` 逐 handler `try/except` → **吞异常、不断链**。
    - 消息链 handler：`process_stage/method/star_request.py:47-69` `try/except` 包裹 `call_handler`，**默认会回一条错误提示**（`:( 在调用插件...时出现异常`）→ **不满足 no-reply 要求**。结论：observer 若接消息路径，**必须自身 fail-closed、绝不抛异常**。

## 三、安全 observer 接法建议（P3）

- **方案 A（真实 internal synthetic event → 真实 dispatcher）**：可行但唯一入口 `event_queue` 会跑完整消息 pipeline → **风险高，本轮不用**。
- **方案 B（专用 dev/test 事件类型）**：**不存在**。
- **方案 C（独立临时 plugin 的 local dispatch）**：最安全——observer 注册 **生命周期 hook**（`OnPluginLoadedEvent` / `OnPluginUnloadedEvent`），由 AstrBot 真实 `load()` 内的 **真实 registry 查询 + await** 派发，全程 **不碰消息链、不触 LLM、不发消息**。

→ 推荐路径：**C（生命周期真实派发）作为 binding 证据主通道**；message 路径暂不接。

## 四、本轮结论

- `real AstrBot hook`：从 UNKNOWN → **CONFIRMED（源码级，v4.28.0）**
- 动态加载：**代码支持，但当前运行配置下触发受限 → 事实需 restart**
- 内部 synthetic dispatch：**无安全非重启路径**
