# Real AstrBot Shadow — Registration Blocker 与状态口径修正（M3·R02）

- 时间：2026-10-11 (CST) · 执行者：奈奈（宿主侧执行者，只读）
- 依据：`docs/nana_shadow_astrbot_dispatcher_audit_20261011.md`（M1 源码级审计）+ 本轮真实实测
- 边界：**未重启 AstrBot / 未读 JWT / 未绕过认证 / 未改生产源码 / 未安装插件 / 未发消息**

---

## 一、状态口径修正（取代 R01 的 `BLOCKED_RESTART_REQUIRED`）

R01 曾写 `FIRST_REAL_ASTRBOT_SHADOW = BLOCKED_RESTART_REQUIRED`。
经 M1 源码审计，「框架层不存在无重启加载路径」**不成立** —— 框架**有**动态加载能力，
被挡住的是**通道鉴权**，不是**框架能力**。故口径修正为：

| 状态键 | 值 |
|---|---|
| `AstrBot dynamic reload supported` | **YES**（源码级：`star_manager.py:1010 reload()` / `:1068 load()`） |
| `Restart required by framework` | **NO**（`load()`/`reload()` 均为进程内操作） |
| `Permitted dynamic load channel` | **BLOCKED_AUTH_REQUIRED**（Dashboard JWT / 或 watcher 未启用） |
| `Observer registered` | **NO** |
| `host_binding` | **UNVERIFIED**（保持） |
| `FIRST_REAL_ASTRBOT_SHADOW` | **BLOCKED** |
| `Internal synthetic dispatch available` | **NO** |
| `Real dispatcher probe` | **BLOCKED_NO_INTERNAL_PROBE** |

> 只有在进一步证明「AstrBot 本身不存在任何无重启加载路径」时，才可再写 `BLOCKED_RESTART_REQUIRED`。
> **本轮未证明，故不写。**

---

## 二、BLOCKED 的精确构成

要完成 `FIRST_REAL_ASTRBOT_SHADOW`，需要两个正交条件同时成立：

| 条件 | 需要什么 | 现状 | Blocker |
|---|---|---|---|
| **C1 注册**：observer 被真实 runtime 加载并注册 | 一次把新插件目录送入 `load()` 的动作 | ❌ | `BLOCKED_AUTH_REQUIRED` |
| **C2 派发**：一条事件经**真实 dispatcher** 到达 observer | 内部合成事件入口 | ❌ | `BLOCKED_NO_INTERNAL_PROBE` |

### C1 的三个候选通道（全部受阻，逐个给证据）

1. **文件 watcher 自动加载** — `ASTRBOT_RELOAD` 未设置。
   实测：宿主 shell `$ASTRBOT_RELOAD` 为空；`/proc/1/environ` 无该键 ⇒ watcher 未启动（`star_manager.py:220`）。
   且即便启动，`_handle_file_changes()` 只重载**已注册且 activated** 的插件（`star_manager.py:245-256`）→ 新目录仍不会进来。
2. **Dashboard `POST /api/plugin/reload`** — 需 JWT（`require_plugin_scope` `plugins.py:59` / `require_dashboard_user` `plugins.py:52`）。
   **本轮禁止读取 secret ⇒ 不启用。**
3. **`reload(name)`** — 只 `load(指定 module)`（`star_manager.py:1052`），**新插件目录不会被载入**。

⇒ 结论：**当前配置下，"载入一个全新插件" 没有可用的免重启通道。**
最安全、最小、可审计的下一步动作 = **姐姐在已登录的 Dashboard 里手动点一次插件 reload / 重载**（或把目录放入后触发一次全量 load）。见 `docs/nana_shadow_observer_dev_20261011.md` §6 runbook。

### C2 为什么是 `BLOCKED_NO_INTERNAL_PROBE`

按任务书三件事分类逐条裁定：

| 类别 | 裁定 | 证据 |
|---|---|---|
| **A. 真正的 AstrBot internal synthetic event → dispatcher** | ❌ **不存在可信且安全的入口** | 唯一入口 `Context.get_event_queue()`（`context.py:733`）→ `EventBus.dispatch()`（`event_bus.py:41`）→ 全 9 段管道 → 可能 `RespondStage`（**外发**）。无 synthetic 专用 `EventType`。 |
| **B. framework development/test event → dispatcher** | ❌ **不存在** | `EventType`（`star_handler.py:219-241`）无 test/synthetic 型。 |
| **C. plugin-local synthetic dispatch** | ⚠️ **可实现，但不构成真实 dispatcher probe** | 生命周期 hook 由 `PluginManager` **直调**（`star_manager.py:1421-1434`），不经过 `EventBus`。 |

#### 对方案 C 的正式裁定

任务书要求：若把生命周期 `load()` hook 当方案 C 用，必须证明
`AstrBot runtime → real dispatcher/registry → observer callback`。

实测结论**分两半**：

- ✅ **`AstrBot runtime → real registry → observer callback` 成立**：注册表是真 `star_handlers_registry`（`star_handler.py:216`），
  派发方是真 `PluginManager.load()` 内联循环（`star_manager.py:1421`）。**这是可信的「注册表绑定」证据。**
- ❌ **但这不等于「真实 dispatcher probe」**：生命周期派发**不经过** `EventBus`/`PipelineScheduler`。
  它只证明「框架会调用挂在 registry 上的生命周期回调」，**不证明**「消息管道 dispatcher 能把事件送到 observer」。

⇒ 依任务书裁定：**「如果只是 plugin manager 直接调用生命周期函数，它不能冒充 P6 的真实 dispatcher probe。」**
⇒ 因此记录：**`BLOCKED_NO_INTERNAL_PROBE`**。
⇒ **不使用真实用户消息替代**（明令禁止，且会污染生产、不可回滚）。

---

## 三、如果要继续推进，只有两条合法出路

| 出路 | 内容 | 需要的授权 | 是否触碰生产 |
|---|---|---|---|
| **E1 注册表绑定验证（低风险，随时可做）** | 姐姐手动 reload 一次 → 触发 `OnPluginLoadedEvent` → 验证 `star_handlers_registry` 中出现 observer handler，且证据落盘 | 姐姐在 Dashboard 点一次 reload（奈奈不读 secret） | 只读 + 写入自有临时证据文件 |
| **E2 真实 dispatcher probe（高风险）** | 向 `event_queue` 注入合成事件 | 需要专门设计「无害化 event + 阻断 RespondStage」的方案并单独授权 | 触碰消息管道，**当前禁止** |

E2 在**未完成无害化设计**前不予推进；E1 可作为 `FIRST_REAL_ASTRBOT_SHADOW` 的**降级目标**（binding-only），
但**必须明确标注**：E1 证明的是 **registry binding**，**不是** dispatcher traversal。

---

## 四、本轮零漂移声明

| 项 | 值 |
|---|---|
| AstrBot restarted | **false** |
| secret / JWT read | **0** |
| auth bypass attempted | **0** |
| production source modified | **0** |
| production plugin dir touched (`/AstrBot/data/plugins`) | **0** |
| observer installed | **NO** |
| Dashboard reload called | **NO** |
| external message sent | **0** |
| real user message substituted | **0** |
| private plaintext read | **0** |
