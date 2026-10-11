# Nana Core · R03-M1 — AstrBot 4.28.0 真实 message pipeline 安全观察点审计

- 分支：`dev/nana-core-v1-astrbot-shadow-bind-r03`
- 基线：merge `652a72f` (R02) × `10581aea` (Codex)
- 被审源码：`/AstrBot/astrbot`，`astrbot/__init__.py:3 → __version__ = "4.28.0"`
- 本轮性质：**只读源码审计**。零安装、零 reload、零重启、零 JWT、零真实消息、零生产改动。
- 证据等级：`[实测/源码]`。**不**构成真实 dispatcher 验收。

---

## 0. 状态口径（先纠偏，再展开）

| 状态键 | 值 | 依据 |
|---|---|---|
| `AstrBot dynamic reload supported` | **YES** | `star_manager.py:1010/1068` |
| `Restart required by framework` | **NO** | 同上 |
| `Permitted dynamic load channel` | **BLOCKED_AUTH_REQUIRED** | 见 R02 / D-044 |
| `SAFE early all-message observer` | **NOT_AVAILABLE** | 本文件 §3 |
| `SAFE result-path observer` | **AVAILABLE** | 本文件 §2.1 |
| `Observer registered` | **NO** | 本轮零注册 |
| `host_binding` | **UNVERIFIED** | 未接真实宿主 |
| `Real dispatcher traversal` | **NOT_VERIFIED** | 无内部合成事件入口 |
| `FIRST_REAL_ASTRBOT_SHADOW` | **BLOCKED** | 同上 |
| `E12` | **NOT_RUN** | — |

**禁止**再用 `BLOCKED_RESTART_REQUIRED` 描述框架能力；**禁止**把「registry binding PASS」写成「dispatcher probe PASS」。

---

## 1. 真实调用链（源码级）

```
platform adapter
  └─ event_queue.put(event)                       # 平台适配器入队
        ↓
EventBus.dispatch()                               # astrbot/core/event_bus.py:39
  ├─ conf = astrbot_config_mgr.get_conf_info(umo)  # :42
  ├─ scheduler = pipeline_scheduler_mapping[conf]  # :46
  └─ asyncio.create_task(scheduler.execute(event)) # :52   ← 唯一进入点
        ↓
PipelineScheduler.execute(event)                   # astrbot/core/pipeline/scheduler.py:82
  ├─ active_event_registry.register(event)         # :89
  └─ _process_stages(event)                        # :91 → :36
        ↓
STAGES_ORDER                                       # astrbot/core/pipeline/stage_order.py:3-13
  WakingCheckStage → WhitelistCheckStage → SessionStatusCheckStage → RateLimitStage
  → ContentSafetyCheckStage → PreProcessStage → ProcessStage
  → ResultDecorateStage → RespondStage
```

**结论**：只有经过 `ResultDecorateStage` / `RespondStage` 的 hook，才满足「只在真实 `EventBus.dispatch() → PipelineScheduler` 路径中触发」。

---

## 2. 候选 hook 逐项判定

### 2.1 `EventType.OnDecoratingResultEvent` — 结论 **SAFE**

| 项 | 事实 |
|---|---|
| enum | `astrbot/core/star/star_handler.py:234` `# 发送消息前` |
| 注册器 | `astrbot/core/star/register/star_handler.py:730-741` `register_on_decorating_result()` → `get_handler_or_create(..., EventType.OnDecoratingResultEvent)` |
| 调用点（唯一） | `astrbot/core/pipeline/result_decorate/stage.py:158-189` |
| 触发链 | `ResultDecorateStage.process()` 内部 —— 该类**仅**由 `PipelineScheduler` 实例化（`stage_order.py:11`），无第二调用方（全仓 grep 仅 stage 自身） |
| 前置守卫 | `stage.py:130-132`：`result = event.get_result()`；`if result is None or not result.chain: return` → **只有“真的有东西要回”时才触发** |
| 流式分支 | `stage.py:134-137`：`STREAMING_RESULT` 直接 return；`STREAMING_FINISH` 走 `is_stream=True` 分支 |
| 参数 | `await handler.handler(event)`（`stage.py:173`）—— **无 `*args`** |
| **返回值处理** | **被丢弃**。`stage.py:173` 只 `await`，不读取返回值；与 `context_utils.call_handler()`（会 `event.set_result(ret)`）**完全不同** |
| **异常处理** | `stage.py:164/173` 包在 `try:` 内，`stage.py:181-182` `except BaseException: logger.error(traceback.format_exc())` —— 只记日志，**不 re-raise，不产生默认错误回复** |
| 停止传播 | `stage.py:184-189`：仅当 handler 自己 `event.stop_event()` 才 `return` |
| 位于 dispatcher 后 | **是**（pipeline 第 8 段，`EventBus.dispatch` 之后） |
| event 变更风险 | 框架层不读返回值；变更风险**只**来自 handler 自己的实现纪律 |

**SAFE 判定**：满足 M1 十项条件中的框架侧部分 —— ①真实 dispatcher 路径内触发 ②返回 `None` 不改变结果（返回值被忽略）③异常被框架 `BaseException` 局部吞掉，不触发默认回复 ④无需读正文 ⑤无 `*args`。

**必须由实现侧自己保证**（框架不替我们保证）：不 `set_result()`、不 `yield`、不改 event、不调模型/网络/tool/Iris、fail-closed。→ 见 `docs/nana_shadow_observer_dev_20261011.md` 与 `message_hook_adapter.py`。

**限制（不可隐藏）**：它是 **result-path** observer，只在「本条消息产生了要发送的结果」时触发；**不是** all-message observer。任何消息（含未唤醒、被白名单挡下、无回复）都不会到它这里。

### 2.2 `EventType.OnAfterMessageSentEvent` — 结论 **SAFE（第二候选）**

| 项 | 事实 |
|---|---|
| enum | `astrbot/core/star/star_handler.py:238` |
| 注册器 | `register/star_handler.py:744-753` `register_after_message_sent()` |
| 调用点 | `astrbot/core/pipeline/respond/stage.py:328` `if await call_event_hook(event, EventType.OnAfterMessageSentEvent): return` |
| 返回值处理 | `call_event_hook`（`pipeline/context_utils.py:78-112`）**忽略 handler 返回值**（`:101 await handler.handler(...)`） |
| 异常处理 | `context_utils.py:102-103` `except BaseException: logger.error(traceback.format_exc())` → 不 re-raise |
| 位于 dispatcher 后 | **是**，但发生在**消息真正 `await event.send(chain)` 之后**（`respond/stage.py:276-326`） |
| 定位 | **第二候选**：晚于发送，观测窗口更靠后，无法在结果成形前拦截 |

### 2.3 `EventType.AdapterMessageEvent` — 结论 **UNSAFE**

| 项 | 事实 |
|---|---|
| 用途 | 它**不是** hook，是**指令 handler 的分组标签**：`register/star_handler.py:118/168/198/240/268/286/303/326`（`register_command` 等）|
| 收集点 | `pipeline/waking_check/stage.py:172-175` 按 filter 逐个匹配（AND 逻辑，`stage.py:184-237`）|
| **实际调用点** | `pipeline/process_stage/method/star_request.py:27-36`，把 `activated_handlers` **当业务 handler 直接执行** |
| 危险点 | 这些 handler 会 `set_result()` / `yield` / 发消息 / 调模型；接进去等于把自己变成指令 handler，**必然影响主链** |
| 判定 | **UNSAFE —— 不允许接** |

### 2.4 `OnLLMRequestEvent` / `OnWaitingLLMRequestEvent` — **UNSAFE（范围不符）**

| 项 | 事实 |
|---|---|
| 调用点 | `process_stage/method/agent_sub_stages/internal.py:225` / `:277`；`third_party.py:307` |
| 危险点 | 只在 LLM 请求路径触发；handler 拿到 `req`（prompt 本体）；`call_event_hook` 的停止语义会 `return`（`:225-226` 直接终止 LLM 分支） |
| 判定 | **UNSAFE**（既碰正文，又能改流程） |

### 2.5 `PreProcessStage` / `ProcessStage` / `RespondStage` 本身 — 非 hook，不适用

无 `call_event_hook` 入口；它们的定制点是插件指令与 LLM 端口，均会改变处理结果。

---

## 3. 结论汇总表

| 候选 | path | symbol | line | dispatcher 内 | 返回值语义 | 异常语义 | 默认回复风险 | 结论 |
|---|---|---|---|---|---|---|---|---|
| OnDecoratingResultEvent | `core/pipeline/result_decorate/stage.py` | `ResultDecorateStage.process` | 158-189（调用 173 / 吞异常 181-182） | ✅ | 忽略 | 局部 `except BaseException` → 仅日志 | 无 | **SAFE** |
| OnAfterMessageSentEvent | `core/pipeline/respond/stage.py` | `RespondStage.process` | 328 | ✅ | 忽略 | `call_event_hook` 吞 `BaseException` | 无 | **SAFE（第二）** |
| AdapterMessageEvent | `core/pipeline/waking_check/stage.py` → `process_stage/method/star_request.py` | 指令 handler 分组 | 172 / 27-36 | ⚠️ 经 WakingCheck 收集 | 业务 handler 语义 | 会外抛/发消息 | **有** | **UNSAFE** |
| OnLLMRequestEvent | `process_stage/.../internal.py` | `call_event_hook` | 277 | ✅ | 停止即 return | 吞 | 有（终止 LLM） | **UNSAFE** |
| OnWaitingLLMRequestEvent | 同上 | — | 225 | ✅ | 停止即 return | 吞 | 有 | **UNSAFE** |

### 最终口径（写死）

```
AstrBot 4.28.0:
SAFE early all-message observer  = NOT_AVAILABLE
SAFE result-path observer        = AVAILABLE   (OnDecoratingResultEvent)
SECOND-CANDIDATE observer        = AVAILABLE   (OnAfterMessageSentEvent, 发送后)
```

**禁止**声称存在「每条消息到达即安全观察」的 hook。

---

## 4. `plugin_set` 是真实前置条件（新增实证）

| 项 | 事实 |
|---|---|
| 写入点 | `pipeline/waking_check/stage.py:163-169` |
| 逻辑 | `enabled = ctx.astrbot_config.get("plugin_set", ["*"])`；`["*"] → event.plugins_name = None`；否则 `= enabled` |
| 过滤点 | `core/star/star_handler.py:169-184`：`plugins_name is not None and != ["*"]` 时，**只剩名单内（或 `reserved`）插件**的 handler 被返回 |
| 联动 | `core/pipeline/context_utils.py:93` 与 `result_decorate/stage.py:161` 均传 `plugins_name=event.plugins_name` |
| 另一道门 | `star_handler.py:161-167` `only_activated=True`（默认）→ 插件必须 `activated` |

**结论**：
```
新 observer 被加载  ≠  它一定能收到 message hook
```
要在 `plugin_set` 非 `["*"]` 的会话里收到 `OnDecoratingResultEvent`，observer 插件**必须在 `plugin_set` 名单内且 `activated`**。
本轮**不修改**真实 `cmd_config.json`、**不**改 `plugin_set`；仅写入 runbook（见 §6）。

---

## 5. 「全新插件首次免重启加载」路径（R03-M3 初查，已完成）

| 项 | 事实（含 line） |
|---|---|
| 入口 API | `POST /api/plugin/install-upload` — `dashboard/api/plugins.py:1272`（legacy）/ `:584`；服务调用 `:371` |
| 服务层 | `dashboard/services/plugin_service.py:1726` `install_plugin_upload_from_dashboard_form` |
| 管理器 | `core/star/star_manager.py:2076` `install_plugin_from_file` |
| 落盘 | `:2087` 解包 → `:2088` 读 metadata 目录名 → `:2097` `os.rename` 到 `data/plugins/<new plugin>` |
| 进程内加载 | `:2109` `await self.load(specified_dir_name=dir_name)` → `load()` 定义在 `:1068`，`:1120` 只载入指定目录名 |
| 结论 | `NEW_PLUGIN_NO_RESTART_MANUAL_PATH = YES`（**人工**路径；奈奈不读 JWT、不自动调用） |
| 对比 | `reload(name)`（`:1002/1010`）只作用于**已注册** plugin/module，**不**载入全新目录 |
| 本轮 | **不上传、不安装、不 reload、不改 plugin_set、不读 JWT** |

---

## 6. 未来唯一人工动作（需要姐姐**届时单独授权**）

> **在已登录的 Dashboard 里上传 observer 插件 ZIP → 系统在进程内 `load()` → 把该插件加入 `plugin_set`。**

- 性质：**一次、有限、可逆**的生产配置动作。
- 必须由姐姐手动完成；奈奈**不得**读取 JWT、**不得**绕过 Dashboard auth。
- 完整 pre-load / post-load / unregister / rollback / zero-drift 清单见 `docs/nana_shadow_observer_dev_20261011.md` §6 与 `docs/nana_shadow_registration_blocker_20261011.md`。

---

## 7. 本轮零漂移声明

| 项 | 计数 |
|---|---|
| 生产源码修改 | **0** |
| 生产插件目录触碰 | **0** |
| 安装 / reload / 重启 | **0** |
| JWT / secret 读取 | **0** |
| 真实消息发送 / 接收 | **0** |
| 消息正文读取 | **0** |
| Iris 私人内容读取 | **0** |
| 网络外发 | **0** |
| owner / authority 切换 | **0** |
