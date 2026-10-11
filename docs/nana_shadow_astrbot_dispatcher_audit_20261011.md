# AstrBot v4.28.0 — Dispatcher / Registry / Lifecycle Hook 深度审计（M1·R02）

- 采集时间：2026-10-11 (CST)
- 执行者：奈奈（宿主侧执行者，in-container，只读）
- 证据等级：**源码级**，全部标注 `source path + symbol + line`
- 范围：只读、非敏感程序源码。**未读任何 secret / 私人文书 / 消息正文**
- 基线：`/AstrBot` @ AstrBot **4.28.0**，Python 3.12.14，CONTAINER runtime

> 本文是 R01 摘要 `docs/astrbot_hook_api_audit.md` 的**完整展开**：把 P2 十问逐项补齐到「路径+符号+行号」，
> 并回答任务书要求的六个硬问题（internal synthetic dispatch / 精确 dispatcher / 精确 registry /
> 生命周期 hook 是否同一 dispatcher / load() 是 manager 直调还是 dispatcher 派发 / unload 后 registry 移除链）。

---

## 0. 一句话结论

**AstrBot 4.28.0 里不存在「一个统一的 hook dispatcher」。**
唯一的 **真派发器** 是 `EventBus.dispatch()`，它**只服务消息事件**（`AstrMessageEvent`）。
所有生命周期 / 平台 / 结果装饰类 hook，都是**各自站点直接遍历同一个注册表**并 `await`，
即 **「共享 registry + 分站点直调」**，**不是**「共享 dispatcher」。

这条结论直接决定：**生命周期 hook 不能冒充 P6 的「真实 dispatcher probe」。**

---

## 1. 精确 Registry

| 项 | 值 |
|---|---|
| 类 | `StarHandlerRegistry` |
| source | `astrbot/core/star/star_handler.py:14` |
| 单例 | `star_handlers_registry = StarHandlerRegistry()` — `star_handler.py:216` |
| 存储 | `self.star_handlers_map: dict[str, StarHandlerMetadata]` + `self._handlers: list[...]` |
| 注册 | `StarHandlerRegistry.append()` — `star_handler.py:19`（按 `priority` 降序插入） |
| 查询 | `StarHandlerRegistry.get_handlers_by_event_type()` — `star_handler.py:150`（15 个 `@overload` 在 33–149 行） |
| 按模块查 | `get_handlers_by_module_name()` — `star_handler.py:191` |
| 删除单个 | `remove(handler)` — `star_handler.py:205` |
| 全清 | `clear()` — `star_handler.py:201` |
| 注册助手 | `get_handler_or_create()` — `astrbot/core/star/register/star_handler.py`（`handler_full_name = f"{__module__}_{__name__}"`） |
| 事件枚举 | `EventType` — `star_handler.py:219`（共 22 项，含 `OnPluginLoadedEvent` @240 / `OnPluginUnloadedEvent` @241） |

**注册发生在 import 期**：装饰器 `register_on_*` 在模块被 import 时调用 `get_handler_or_create()`
→ `star_handlers_registry.append(md)`。`handler_module_path = handler.__module__`。

---

## 2. 精确 Dispatcher（分站点全景）

| hook | 派发站点（source + line） | 派发形态 |
|---|---|---|
| **消息事件（唯一真 dispatcher）** | `astrbot/core/event_bus.py:39` `EventBus.dispatch()` → `:52` `scheduler.execute(event)` | 异步队列循环 → `PipelineScheduler` |
| 管道阶段机 | `astrbot/core/pipeline/scheduler.py:82` `execute()` → `:36` `_process_stages()` → `:47` `stage.process()` | 洋葱模型，9 段（`stage_order.py`） |
| 通用 pipeline hook（LLM 请求/响应、发送前、PluginError…） | `astrbot/core/pipeline/context_utils.py:78` `call_event_hook()` → `:91` `get_handlers_by_event_type()` → `:101` `await handler.handler(...)` | **函数级直调循环** |
| `AdapterMessageEvent` | `astrbot/core/pipeline/waking_check/stage.py:172` | 直调循环 |
| `OnDecoratingResultEvent` | `astrbot/core/pipeline/result_decorate/stage.py:159` | 直调循环 |
| `OnPluginErrorEvent` | `astrbot/core/pipeline/process_stage/method/star_request.py:59`（调 `call_event_hook`） | 走 `call_event_hook` |
| `OnAstrBotLoadedEvent` | `astrbot/core/core_lifecycle.py:367`（在 `start()` @358 内） | 直调循环 |
| `OnPlatformLoadedEvent` | `astrbot/core/platform/manager.py:228` | 直调循环 |
| **`OnPluginLoadedEvent`** | `astrbot/core/star/star_manager.py:1421` | **直调循环** |
| **`OnPluginUnloadedEvent`** | `astrbot/core/star/star_manager.py:2044` | **直调循环** |

> 关键事实：**除消息路径外，没有任何 hook 经过 `EventBus`。**

---

## 3. P2 十问逐项落盘（含路径/符号/行号）

### Q1 支持插件热加载吗？
**代码支持，当前运行配置下不可用。**
- 开关：`star_manager.py:220` `if os.getenv("ASTRBOT_RELOAD", "0") == "1": asyncio.create_task(self._watch_plugins_changes())`；模块级同判在 `:60`。
- watcher：`_watch_plugins_changes()` — `star_manager.py:223`，用 `watchfiles.awatch(..., PythonFilter(), recursive=True)`。
- 处理：`_handle_file_changes()` — `star_manager.py:240`；它**只遍历 `star_registry` 中 `activated` 的插件**（`:245-256`）→ **新目录不会被自动载入**。
- **实测**：`ASTRBOT_RELOAD` 未设置（宿主 shell `unset`；`/proc/1/environ` 无该键）→ **watcher 未运行**。

### Q2 支持插件热卸载吗？
**支持。** `PluginManager._unbind_plugin()` — `star_manager.py:1874`；`uninstall_plugin()` — `:1753`。

### Q3 动态加载是否需要 restart？
**`load()`/`reload()` 本身是进程内操作，不需要 restart；但到达它的通道受限。**
- `reload()` — `star_manager.py:1010`：若给了 `specified_plugin_name`，先 `_unbind_plugin`，再 `self.load(specified_module_path)`。
- `load()` — `star_manager.py:1068`：遍历 `self._get_plugin_modules()`（`:317`，扫盘 `:289 _get_modules`）。
  → **`load()` 无参调用会扫到新目录**；**但 `reload(name)` 只 `load(指定 module)`**，新目录不会进来。
- 非重启触发通道：
  1. 文件 watcher → **未开启**（Q1）。
  2. Dashboard `POST /api/plugin/reload` — `astrbot/dashboard/api/plugins.py:1391`（legacy）与 `:837`/`:1104`（新版）→ 依赖 `require_plugin_scope`（`plugins.py:59`）/`require_dashboard_user`（`plugins.py:52`）＝ **需要 Dashboard JWT**（secret，禁读）；服务侧 `PluginService.reload_plugin()` — `astrbot/dashboard/services/plugin_service.py:154` → `plugin_manager.reload(name)`。
  3. 其余服务侧调用点同样走 `reload(name)`（`plugin_service.py:141/1791`、`config_service.py:1017`）。
- ⇒ **在当前运行配置下，载入一个「全新」插件事实上需要 restart**；若要免重启，唯一通道是**已鉴权的 Dashboard reload**，且**仍只对已注册插件生效**（新插件需先让 `load()` 扫盘，即需一次全量 `load()`/重启）。

### Q4 卸载后 callback 是否真的从 registry 移除？
**是。** 真实调用链（`star_manager.py:1874-1917`）：
```
_unbind_plugin(plugin_name, plugin_module_path)
 ├─ del star_map[plugin_module_path]                        # :1886
 ├─ del star_registry[i]                                    # :1888-1893
 ├─ for h in star_handlers_registry.get_handlers_by_module_name(mp):  # :1894
 │     star_handlers_registry.remove(h)                     # :1902  → star_handler.py:205
 ├─ for k in star_handlers_map if k.startswith(mp): del ...  # :1907-1912
 ├─ llm_tools.func_list 移除该插件工具                        # :1914-1927
 ├─ unregister_platform_adapters_by_module(module_prefix)    # :1931-1937
 └─ _purge_modules(root_dir_name, reserved)                  # :1942 → :734
```
`remove()` 本体（`star_handler.py:205`）：`star_handlers_map.pop(full_name)` + `_handlers = [h for h in _handlers if h != handler]`。
⇒ **卸载后 registry 与 map 双双不含该 callback。**（另有 `reload()` 全量分支对 `star_handlers_registry.clear()` — `:1058`。）

### Q5 能否注册「只观察、不改 event」的 callback？
**能。** 见 §2 表：任何 hook 站点都是 `await handler.handler(...)`，返回值被忽略（生命周期 hook 的返回值直接丢弃，`star_manager.py:1430`）。
`call_event_hook` 只对 `event.stop_event()` 做特判（`context_utils.py:105`）。

### Q6 能否阻止 observer 修改 response？
**能。** 只有 **message 路径**才会 `event.set_result(ret)`（`astrbot/core/pipeline/context_utils.py:56`、`:72`，仅当返回 `MessageEventResult|CommandResult`）。
observer 若只挂 **生命周期 hook**，手上拿到的是 `StarMetadata` 而非 event，**结构上无法产生结果**。

### Q7 是否存在 before/after/generic hook？
**存在。** `EventType`（`star_handler.py:219-241`）含
`OnAstrBotLoadedEvent`(225)、`OnPlatformLoadedEvent`(226)、`AdapterMessageEvent`(228)、`OnDecoratingResultEvent`(234)、`OnPluginErrorEvent`(239)、`OnPluginLoadedEvent`(240)、`OnPluginUnloadedEvent`(241)，
以及 LLM 侧 `OnLLMRequestEvent`/`OnLLMResponseEvent`/`OnCallingFuncToolEvent`/`OnLLMToolRespondEvent`/`OnAfterMessageSentEvent`/`OnAgentBeginEvent`/`OnAgentDoneEvent` 等。
装饰器别名统一导出于 `astrbot/api/event/filter/__init__.py`（`on_plugin_loaded` @30、`on_plugin_unloaded` @31）。

### Q8 是否有内部 synthetic event dispatch API？
**没有安全的、隔离的内部 synthetic 入口。** 分三层说明：

| 层 | 存在性 | 证据 | 可用性 |
|---|---|---|---|
| **A. 真·internal synthetic event → 真 dispatcher** | 唯一入口存在但不安全 | `Context.get_event_queue()` — `astrbot/core/star/context.py:733`（`@deprecated`）→ 向队列 `put()` 即进 `EventBus.dispatch()`（`event_bus.py:41`）→ `PipelineScheduler.execute()` | ❌ 会跑**完整消息管道**（9 段，含 LLM 与 `RespondStage` 发送）→ 可能产生**真实外发回复**。本轮禁用。 |
| **B. framework development/test event** | **不存在** | `EventType` 全表（22 项）中没有任何 test/synthetic 专用类型 | ❌ |
| **C. plugin-local synthetic dispatch** | 可自造，但只是本插件内部函数调用 | 见 M2 observer（生命周期 hook）+ `tools/nana_host_shadow/observer.py`（`LocalProbe`/`ProbeObserver`） | ⚠️ **不等于**框架派发器 |

**可安全插入但无法取证的分支**：若构造的 `AstrMessageEvent` 的 `unified_msg_origin` 找不到 scheduler，
`EventBus.dispatch()` 会打日志并 `continue`（`event_bus.py:44-49`）→ 事件被丢弃、**不跑任何 stage**、也**不会触发任何 observer**。⇒ 它既证明不了 hook 派发，也没有观测价值。

**结论**：`Internal synthetic dispatch available = NO`（就「可安全使用的内部合成派发」而言）。

### Q9 能否区分 internal synthetic probe 与真实用户 message？
**框架无原生区分**（无专用 synthetic 事件类型 / 无 source 标签字段）。
只能由 observer 自带 metadata 自证（如 `source=astrbot_internal_lifecycle`、`synthetic=true`、`probe_id`）。本仓库 observer 已内建该标记（见 M2）。

### Q10 observer 异常会否阻塞主链？
- **生命周期 hook**：`star_manager.py:1421-1434` 与 `:2044-2056` 均逐 handler `try/except` → **吞异常、不断链**。
- **`call_event_hook`**：`context_utils.py:95-103` 逐 handler `try/except BaseException` → 吞异常、不断链。
- **消息路径 handler（star_request）**：`astrbot/core/pipeline/process_stage/method/star_request.py:47-69` 包了 `try/except`，
  且**默认会回一条报错提示**（`:59` 触发 `OnPluginErrorEvent`，无插件接管则报错回显）→ **违反 no-reply**。
⇒ observer **绝不可**接消息路径；若接，必须自身 fail-closed 且接管 `OnPluginErrorEvent` 屏蔽回显。本仓库策略：**只接生命周期 hook**。

---

## 4. 任务书六个硬问题（直答）

| # | 问题 | 答案 | 依据 |
|---|---|---|---|
| 1 | Internal synthetic dispatch available | **NO** | §3-Q8；`EventType` 无 synthetic 型；唯一真入口不安全 |
| 2 | exact dispatcher path（消息） | `event_queue.put` → `EventBus.dispatch()` (`event_bus.py:39`) → `PipelineScheduler.execute()` (`scheduler.py:82`) → `_process_stages()` (`scheduler.py:36`) → `stage.process()` (`scheduler.py:47`) | 源码 |
| 3 | exact registry | `star_handlers_registry`（`star_handler.py:216`，类 `StarHandlerRegistry` @14） | 源码 |
| 4 | 生命周期 hook 是否经过同一个 dispatcher | **NO**。生命周期是 **plugin manager / core_lifecycle / platform manager 各自的直调循环**，**不经过** `EventBus` | `star_manager.py:1421`、`:2044`、`core_lifecycle.py:367`、`platform/manager.py:228` |
| 5 | plugin `load()` callback 是 manager 直调还是 dispatcher 派发 | **plugin manager 直调**（在 `load()` 内联循环 `await handler.handler(metadata)`） | `star_manager.py:1421-1434` |
| 6 | unload 后 callback registry removal 的真实调用链 | 见 §3-Q4（`_unbind_plugin` → `get_handlers_by_module_name` → `remove()` → `_handlers`/`star_handlers_map` 双清） | `star_manager.py:1894-1912` + `star_handler.py:205` |

> 唯一「共享」的东西是 **registry**；**dispatcher 是分站点的**。
> 因此：**AstrBot runtime → real registry → observer callback 成立**；
> 但 **「真实 dispatcher（消息管道）派发到 observer」不成立** → 见 M3 的 `BLOCKED_NO_INTERNAL_PROBE`。

---

## 5. Pipeline 9 段（消息链，供风险界定）

`astrbot/core/pipeline/stage_order.py` `STAGES_ORDER`：
`WakingCheckStage` → `WhitelistCheckStage` → `SessionStatusCheckStage` → `RateLimitStage` →
`ContentSafetyCheckStage` → `PreProcessStage` → `ProcessStage`（插件/LLM） → `ResultDecorateStage` → `RespondStage`（**外发**）。

⇒ 任何进入 `event_queue` 的合成事件都可能走到 `RespondStage` ⇒ 这是 Q8-A 判为不可用的直接理由。
