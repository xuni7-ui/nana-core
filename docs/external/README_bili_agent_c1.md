# BiliAgent · C.1 第一版（离线骨架）

> 一句话验收目标：
> **给妹妹一个明确的 B 站任务，她能够自己组织已有能力完成它，并且只有经过 Verify 后，才允许向姐姐报告「完成」。**

## 一、定位

`bili_agent.py` 是**编排层，不是第二套 B 站业务内核**。

```
BiliTask（明确指定对象）
   ↓
Observe   读取目标评论（只读，按 rpid 定位）
   ↓
Understand LLM：**1 次调用**，产出最小语义结构（严格校验后才可用）
           {"intent":str, "worth_replying":bool, "reason":str, "reply":str}
   ↓
Decide     代码：把已校验语义**确定性翻译**成决策（不再问 LLM）
   ↓
Act        复用 bili_send_core.run_send（precheck → send → result → verify → record）
   ↓
Verify     以内核 Verify 为唯一真相源
   ↓
Record     Action Ledger（复用，不另造）
```

确定性逻辑（ID 校验 / precheck / 去重 / 状态转换 / send / verify / 禁重试 / Ledger）
**全部复用 `bili_send_core`，一行都不复制**（静态自检：编排层内无 `send_comment`、无 precheck/verify 复制）。

## 二、职责边界（铁律）

| 层 | 负责 |
|---|---|
| 代码（确定性） | 读哪个评论、按什么状态机发、发没发成功、记什么账、**校验语义输出、决定要不要发** |
| LLM（语义层） | 理解评论、判断意图、判断值不值得回、生成回复内容（**只写 4 个白名单字段**） |

### 语义层最小契约（C.1 Semantic Layer）

LLM 只能输出：

```json
{"intent": "question", "worth_replying": true, "reason": "对方明确提出问题，需要回应", "reply": "可以呀……"}
```

代码侧 `parse_semantic()` **严格校验**（任一不满足 → `SEMANTIC_ERROR`，绝不发送）：

- 不是合法 JSON 对象 → `SEMANTIC_ERROR`
- 缺任一必需字段（intent / worth_replying / reason / reply）→ `SEMANTIC_ERROR`
- 类型不对（尤其 `worth_replying` 不是布尔值）→ `SEMANTIC_ERROR`
- `worth_replying=true` 但 `reply` 为空 → `SEMANTIC_ERROR`

**安全边界**：语义层返回体只含 4 个白名单键；LLM 若伪造 `sent/status/done/reported_done/rpid/code`
等"已发送/成功"字段，一律丢进 `ignored_claims`（仅审计），**绝不参与任何状态判定**。
LLM 也无法调用发送函数（它只是一个 `(system,user)->str` 的纯函数），
更无法改 Action Ledger（记账只在 Act 之后、由代码执行）。

核心原则：**LLM 只负责"理解和建议"，代码负责"接受、检查、执行"。**

**★★ LLM 永远不能决定「已经发送成功」。** Agent 对外只暴露一个结论字段
`reported_done`，它**只有经内核 Verify 确认（VERIFIED / PRE_EXIST）后才为 True**。
代码里加了不变式断言：`reported_done == (status == DONE)`，任何路径都跑不掉。

## 三、Agent 状态词汇表（与内核词汇表分开）

| Agent 状态 | 含义 | reported_done |
|---|---|---|
| `DONE` | 内核 VERIFIED / PRE_EXIST | ✅ True |
| `SKIPPED` | 语义层判定不值得回 / 目标是自己 | ❌ |
| `DRY_RUN` | 空跑，未发送 | ❌ |
| `PENDING_VERIFY` | 内核未决（禁重试） | ❌ |
| `RETRYABLE` | 内核明确失败无副作用（v1 不自动重试） | ❌ |
| `SEMANTIC_ERROR` | LLM 输出异常/格式错误 → 安全兜底不发送 | ❌ |
| `OBSERVE_FAILED` | 读不到目标评论 → 不发送 | ❌ |
| `BAD_TASK` | 缺 bvid / comment_id | ❌ |

退出码：`0`=DONE · `1`=RETRYABLE · `2`=PENDING_VERIFY · `3`=DRY_RUN · `4`=未执行

## 四、第一版红线（未触碰）

❌ 自动 @ 轮询 · ❌ 自动发现事件 · ❌ 自动回复所有评论 · ❌ 后台自主社交
❌ 新 Agent 框架 · ❌ 新记忆系统 · ❌ L2/L3 重构 · ❌ 复制新的 send/verify 状态机

只有**明确传入 `comment_id`** 时 Agent 才会动；它不会自己去找评论、扫事件、主动社交。

## 五、用法

```bash
# 离线自测（全程 mock，不碰真站、不写账本）
python3 test_bili_agent.py

# 单任务（默认空跑，安全）
python3 bili_agent.py BV1duuQ68Eqe 316307987585 --instruction "用轻松语气"

# 真正执行需 --real 且注入 LLM（未注入会明确报错，不会瞎发）
```

代码内调用：

```python
from bili_agent import BiliAgent, BiliTask
agent = BiliAgent(llm=my_llm, observer=my_obs)   # 离线注入 mock
res = await agent.run(BiliTask(bvid="BV...", comment_id=316307987585))
if res["reported_done"]:
    ...   # 只有这里才敢说"完成了"
```

## 六、测试结果（离线 mock）

`test_bili_agent.py` —— **S1–S14 + S2b + A–H 全绿**（覆盖姐姐点名 7 项 + 边界 + 语义层专项）：

| # | 场景 | 期望 |
|---|---|---|
| S1 | 正常决定回复 | DONE，发 1 次 |
| S2/S2b | 判断不值得回复 | SKIPPED，零发送，且**不写 Action Ledger** |
| S3 | precheck 已存在 | DONE(PRE_EXIST)，零发送 |
| S4 | 回包异常但 verify 找到 | DONE(VERIFIED)，仍只发 1 次 |
| S5 | UNKNOWN(code=None) | PENDING_VERIFY |
| S6 | Verify 查询失败 | PENDING_VERIFY |
| S7/S7b | LLM 输出非 JSON / 阶段坏 | SEMANTIC_ERROR，零发送 |
| S8 | 缺 comment_id | BAD_TASK |
| S9 | Observe 失败 | OBSERVE_FAILED |
| S10 | 目标是自己发的评论 | SKIPPED，零发送 |
| S11 | 决定回复但正文空 | SEMANTIC_ERROR，零发送 |
| S12 | --dry 空跑 | DRY_RUN，零发送 |
| S13 | 不变式 `reported_done ⇔ DONE` | 恒成立 |
| S14 | markdown 围栏 JSON | 可解析 → DONE |
| **A** | 明确问题 | worth_replying=true → 走完整闭环 |
| **B** | 普通无意义评论 | worth_replying=false → SKIPPED 零发送 |
| **C** | 明确要求回复 | worth_replying=true |
| **D** | 恶意/无关内容 | false → 安全拒绝（不发送） |
| **E** | malformed JSON | SEMANTIC_ERROR |
| **F** | 缺字段 | SEMANTIC_ERROR |
| **G** | 错误类型（str/int 冒充 bool 等 3 种） | SEMANTIC_ERROR |
| **H/H2/H3** | LLM 假称"已发送"（伪造 sent/status/done/rpid…） | 不能进 DONE；伪造字段被隔离进 ignored_claims |

**副作用核查**：`bili_comment_log.jsonl` / `ledger.json` / `ledger.jsonl` 全程 MD5 前后不变；写侧熔断器零触发。

## 七、语义层真实·只读验证（2026-10-07）

`test_bili_agent_semantic_real.py` —— 真站 Observe + 真实 LLM，**止步于 Decide**：

```
真实 B站 → Observe(只读) → 真实评论内容 → 真实 LLM → Understand(严格校验) → Decide → 输出
到此停下（绝不 Act/Send/Reply/写账）
```

- 真实样本：`BV1t55v6DE2v` / `rpid=316308591393`（`@涟奈子也_ 妹妹可以这样吗？`，他人顶层）
- **身份注入后 4 次独立进程结果**（2026-10-07 修复复验）：
  - `worth_replying=true`、`decision` **4/4 完全一致**（`canon_decision_sha` 全等）
  - `intent`=`question`、`reason`/`reply` 措辞每次自然波动 → **判定稳定，但 LLM 存在自然随机性**
  - `reason` 每次均正确表述为"**@了本账号 / 指向自己**"，**0 次**命中原误判词
    （"另一位用户 / 不是我们 / 第三方用户 / 非本账号"等）
- 硬证据：`hard 21/21` 全绿；写侧熔断器零触发；账本/流水 MD5 前后不变；Act 从未调用
- ✅ **身份误判已修复并复验**：`_understand()` 提示词注入 `my_uname=涟奈子也_` /
  `my_mid=3706929700408150`，并明示"@本账号=自己、不当第三方、是否回复仍按内容判断"。
  修复前 4/4 误判为"@了另一位用户"；修复后 4/4 正确识别为本账号自己。

## 八、Observe 真实只读验证后的边界 / 状态（2026-10-07 更新）

- **Observer 真站只读已验证**（`test_bili_agent_observe_real.py` v3，47/47 hard 全绿）：
  - 顶层评论：按 rpid 扫顶层前 5 页命中 ✅
  - 楼中楼：**`task.root` 显式给出时**走楼中楼只读接口逐页定位（≤3 页）✅
  - 跨视频 t_op 定位 ✅；不存在 rpid → 明确 `OBSERVE_FAILED`（`reason=NOT_FOUND`）✅
- **Observe 失败区分两类**（姐姐重点要求）：
  - `reason=NOT_FOUND` —— 接口正常、扫描范围内确实没有该 rpid（真·找不到）
  - `reason=IFACE_ERROR` —— 接口/网络读取失败（**取法导致观察不到，≠ 不存在**）
- **不做请求放大**：**绝不会**为 `rcount>0` 的顶层评论逐条探测楼中楼；
  楼中楼路径仅由显式 `task.root` 触发。
- **mid 类型规范**：标准结构中 `mid` 统一归一为 `int`（比较/使用一致），
  原始 API 值保留在 `mid_raw`（真站为 `str`）——杜绝 C.2 同款 str/int 坑。
- **楼中楼精度**：回复时 `root` = 目标评论的顶层祖先；内核 `send_comment` 以
  `parent=None` 发送，**不直接挂在子评论下**（回复落在该顶层线程）。本版边界。
- **Agent 默认不接 LLM**：需注入 `llm=(system,user)->str`；未注入时语义层明确抛 `SemanticError`。
  （真实 LLM 适配器仅存在于测试脚本 `test_bili_agent_semantic_real.py` 内。）
- **v1 不自动重试**：`RETRYABLE` 只回报，不自动重发。

## 九、C.1 状态（2026-10-07）

| 环节 | 状态 |
|---|---|
| 源码 | ✅ `bili_agent.py` 新建（编排层，复用内核） |
| 离线测试 | ✅ `test_bili_agent.py` **S1–S14 + A–H 全绿**（mock） |
| **Observe 真站只读验证** | ✅ `test_bili_agent_observe_real.py` v3 **47/47 hard 全绿**（含楼中楼 + mid 规范） |
| Observe 只读硬证据 | ✅ 两次独立进程 `canon_sha` 一致；账本/流水 MD5 前后不变；写侧熔断器零触发 |
| **Understand / Decide 语义层** | ✅ 离线 S1–S14 + A–H + **身份专项 I1–I4 全绿** + **真站只读 4 次独立运行**（`test_bili_agent_semantic_real.py`，hard 21/21） |
| **身份上下文注入** | ✅ `_understand()` 注入 `my_uname`/`my_mid`（`self._agent_identity()`，与凭据同源）；`@本账号` 正确识别为"@自己" |
| 语义层真实发送次数 | ✅ **0**（Act 从未调用；写侧熔断器零触发；账本/流水 MD5 不变） |
| 已知语义增强点 | ✅ 已闭环（原缺陷 = 提示词缺"我是谁" → 已注入并 4/4 复验通过） |
| Act → 真发送 | ⬜ 未做（届时复用 C.2 内核，不在本步范围） |
| 内核/账本/插件改动 | ✅ 零改动（未动 `bili_send_core.py`、`action_ledger.py`、任何插件、主聊天链） |
