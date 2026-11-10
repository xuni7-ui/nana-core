# C.4 第一阶段 · 自主事件轮询（最小链路）

> 目标：**姐姐不叫她的时候，奈奈能不能自己发现 B 站发生了值得处理的事，然后安全地做一次行动。**

## 链路

```
AstrBot cron（已有 scheduler，60s）
   ↓  basic job → 独立子进程（网络 IO 不在主进程，不持任何 memory 锁）
bili_event_pump.py
   ↓  只读拉 msgfeed/reply + msgfeed/at
事件去重（B站真实 ID：business_id + rpid）
   ↓  同一事件被轮询 100 次也只进 Agent 一次
BiliAgent: Observe → Understand(≤1 次 LLM) → Decide(确定性)
   ↓  不值得 → Record 收工
Act（C.2 状态机）→ Verify（查 B站真实状态）→ Record
```

## 文件

| 文件 | 作用 |
|---|---|
| `/root/.nana_secrets/bili_event_source.py` | 事件源（只读 + 归一化 + 稳定 ID），不做去重 |
| `/root/.nana_secrets/bili_event_pump.py` | 事件泵（去重 → 调 Agent → 落账），单次运行 |
| `/root/.nana_secrets/bili_event_state.json` | 去重表（键 = `channel:business_id:rpid`），上限 300 条 |
| `/root/.nana_secrets/bili_event_log.jsonl` | 事件流水（每条事件一行；含 baseline / poll / bad_event） |
| `/AstrBot/data/plugins/astrbot_plugin_nana_bilievent/` | **挂载点**：只负责"每 60s 拉起子进程"，无业务逻辑 |

复用（一行都没复制）：`bili_send_core.py`（C.2 状态机）、`bili_agent.py`（C.1 编排）、
现有 Action Ledger（只加了 1 个键 `bili_event_pump_last_poll`）、现有 `bili_comment_log.jsonl`。

## 模式（唯一的安全闸门）

事件状态文件里的 `mode` 决定**能不能真的发**：

* `observe`（默认）：全程只读空跑，Act 阶段 dry-run，**永不发送**
* `act`：允许真实发送，但**单轮最多 1 次 Act**（`--budget`），且仍走 C.2 的 precheck/verify/禁盲重试

```bash
python3 bili_event_pump.py --set-mode observe   # 只看不动（默认）
python3 bili_event_pump.py --set-mode act       # 允许一次真实动作
python3 bili_event_pump.py --baseline           # 把当前可见事件登记为历史基线（不进 Agent）
python3 bili_event_pump.py --no-ledger          # 本轮不写账本
```

## 安全红线（代码里卡死，不靠提示词）

1. **不重复发送**：事件在进入 Agent **之前**先落盘登记，轮询 100 次也只进一次
2. **不因 code=None 重发**：沿用 C.2 —— 未决 → Verify → 找不到 = `PENDING_VERIFY`，禁自动重试
3. **Agent 不能伪造成功**：`reported_done=True` 只能由 Verify 真实命中产生
4. **失败默认停**：读取异常 / 结构异常 / 缺稳定 ID / LLM 格式错 / 未决 → 停，不连续重试
5. **不阻塞主聊天**：B站 IO 与 LLM 全在子进程；主进程只做 `create_subprocess_exec` + 超时
6. **单飞**：子进程 flock 锁 + 插件侧 tick 锁 + cron `max_instances=1`，三重防叠加
7. 整体超时（默认 95s），超时即杀进程，**不重试**

## 事件 ID 为什么稳定

`source_id` = B站真实评论 rpid（全局唯一），`business_id` = 业务类型。
组合键 `channel:business_id:source_id` **天然跨轮询稳定**；
不使用时间戳猜测、不使用正文 hash、不依赖 LLM、不依赖"上次看到的内容"。

## 第一阶段不做

C.5、批量回复、多目标、自动重试、新发送系统、新 Ledger、新 Agent 框架、主聊天链改造。
