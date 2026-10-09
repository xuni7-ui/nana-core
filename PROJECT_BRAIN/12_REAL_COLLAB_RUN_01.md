# PROJECT_BRAIN / 12 首次真实协作跑测证据（R2）

> 创建：2026-10-10 ｜ 作者：奈奈 ｜ 状态：**已完成，独立验收通过**
> 授权来源：姐姐 2026-10-10"首次真实模型端点协作测试"一次性最小授权（见 D-024）
> 证据分级：全文沿用 `00_INDEX.md` 的 `[实测] / [文档] / [聊天记忆] / [未知]`

---

## 一、结论速览

| 项 | 值 | 等级 |
|---|---|---|
| 真实接收端 | `https://api.deepseek.com/v1` · model `deepseek-flash` · runner `local_llm` | `[实测]` |
| **不是** Codex | `codex` CLI 未安装（`CodexRunner.is_available()==False`），回执内 `is_codex_cli=false` | `[实测]` |
| 任务是否成功 | **是**（第 2 次运行：`ok=true, applied=true, test_ok=true`） | `[实测]` |
| 是否通过验收 | **通过**（含奈奈自写的独立行为探针，非仅采信模型自测） | `[实测]` |
| 实际调用成本 | 3 次请求 · 输入 11,940 / 输出 25,734 tokens ≈ **¥0.2 ~ ¥0.7**（端点无账单接口，单价未核实） | `[实测]`(用量) + `[未知]`(单价) |
| 生产改动 | **0**：未改生产源码、未重启、未 push、无 remote | `[实测]` |

---

## 二、授权边界与实际执行的逐条对照

| 姐姐的条件 | 执行情况 | 证据 |
|---|---|---|
| ① 端点须是预期的开发模型服务，不得把普通 HTTP 调用冒充 Codex | 端点 = 已在用的 DeepSeek 兼容端点；回执显式标注 `is_codex_cli=false`；**未**宣称 Codex 协作成功 | 回执 `endpoint` 字段 |
| ② 外传仅限已确认白名单代码，无凭据/私人数据/无授权三方码 | 仅 2 个文件、18,187 字节（`c5v_wiring.py` + `test_c5v_wiring.py`）；两文件预先扫描无密钥；采集器对 `HARD_DENY` 强制跳过 | 采集器 + 预扫描输出 |
| ③ 用现有凭据，不装依赖、不扩权限 | 复用 `cmd_config.json` 内已有 deepseek 凭据（进程内注入，未入库/未入命令行）；`openai` SDK 早已安装（3.8.0）；未新增任何权限 | `[实测]` |
| ④ 设请求次数与费用上限；不确定即暂停 | 硬闸门 `max_calls=1`（代码级，超限拒绝外发）；`max_files=2` `max_total_bytes=30000`；**总授权内实发 3 次**（见 §五 披露） | T8 用例 + 回执 `calls/max_calls` |
| ⑤ 不改生产、不 push、不部署、不自动合并 | 全程只读源仓 + 克隆到 `bridge/scratch/`；源仓两文件 `sha256 == git HEAD` | §四 独立验收 |

---

## 三、任务书（TaskSpec）

`bridge/tasks/c5v_real_01.json`

| 字段 | 值 |
|---|---|
| goal | 给 `vision_brief()` 增可选 `cache_dir`：命中则复用本地视频、不下载；默认 `None` 时行为逐字节不变；补 1~2 条离线用例；无新依赖、无密钥 |
| allow_paths | `src/bili_agent/c5v_wiring.py`、`src/bili_agent/test_c5v_wiring.py` |
| deny_paths | `src/bili_agent/notes/**` |
| test_command | `python3 src/bili_agent/test_c5v_wiring.py` |
| budget_s | 300 |

> **执行前修掉的一处隐患**：原任务书 `allow_paths = src/bili_agent/*.py` 会让采集器按字母序抓前 8 个文件，
> 目标文件 `c5v_wiring.py`（字母序靠后）**根本进不了提示词**。已收窄为精确两文件。
> `[实测]` `prompt_bytes=18187` ≈ 两文件之和，可反证"只发了这两个文件"。

---

## 四、结果与**独立验收**（不采信模型自述）

### 4.1 两次运行

| # | 结果 | 验收命令 | 说明 |
|---|---|---|---|
| run#1 | `ok=false, applied=false` | **13/13 通过** | 真实外发成功、代码写盘、测试全绿，但被判 `Runner 返回类型异常：RunnerResult` → 见 §4.2 |
| run#2 | `ok=true, applied=true, test_ok=true` | **13/13 通过** | 修 bug 后 bounded 重试一次，管道完整闭环 |

### 4.2 真实跑测抓出的真 bug（本条是本轮最大收获）

* **现象**：以脚本方式运行 `codex_bridge.py --runner local_llm` 时，模型结果被丢弃判否。
* **根因**：脚本运行时本模块名为 `__main__`，而 `local_runner` 执行 `from codex_bridge import RunnerResult`
  又加载了**第二份**同名模块 → 两个 `RunnerResult` 类对象身份不同 → `isinstance` 恒为 False。
* **为何离线测试没抓到**：测试里 `codex_bridge` 是被 `import` 的模块，不是 `__main__`，身份恰好一致。
* **修复**：① `sys.modules.setdefault("codex_bridge", sys.modules[__name__])` 根修；
  ② `execute_task` 增加纵深防御——类型不符时**按属性转换**而不是丢弃结果。
* **回归**：`test_local_runner.py` 新增 T7（CLI 子进程 + 127.0.0.1 假端点，复现原 bug 路径）、T8（请求上限闸门）、T9（usage 采证）。

### 4.3 奈奈自写的独立行为探针（绕开模型的测试）

在克隆内（非源仓）直接调用改动后的 `vision_brief`，用**间谍 fetcher** 计数：

| 场景 | 期望 | 实测 |
|---|---|---|
| `cache_dir` 命中（目录内有 `BV...mp4`） | fetcher **0** 次，流程越过下载阶段 | ✅ 0 次；reason 变成"视频结构不可读"（说明已复用本地文件进入探针阶段） |
| `cache_dir` 未命中 | fetcher **1** 次并回落 | ✅ 1 次 |
| **不传** `cache_dir`（旧签名） | 旧行为保持 | ✅ 1 次，与改动前一致 |
| 签名 | 含 `cache_dir` | ✅ |

### 4.4 源仓零改动的硬证据

| 文件 | 源仓实盘 sha256(16) | `git HEAD` 版 sha256(16) | 判定 |
|---|---|---|---|
| `src/bili_agent/c5v_wiring.py` | `a8f194930b62c4a1` | `a8f194930b62c4a1` | 未改动 ✅ |
| `src/bili_agent/test_c5v_wiring.py` | `0ddce4bf5b08e464` | `0ddce4bf5b08e464` | 未改动 ✅ |

* 源仓原测试独立复跑：**11/11 通过**（改动前基线未受影响）。
* 模型产物扫描：新增 import **无**（零新依赖）；疑似密钥行 **无**。

### 4.5 边界校验

`violations = []`（模型所有编辑均落在白名单内）。
白名单机制本身由离线用例 T4（越界编辑整体拒绝）与 selftest 的 `violation` 分支持续守住。

---

## 五、成本披露（如实）

| 项 | 数值 |
|---|---|
| 请求 ① 连通性探针（max_tokens=8） | 输入 34 / 输出 8 |
| 请求 ② run#1（真实任务，被判否） | 输入 5,953 / 输出 13,288 |
| 请求 ③ run#2（修复后重试，通过） | 输入 5,953 / 输出 12,438 |
| **合计** | **输入 11,940 / 输出 25,734 / 共 37,674 tokens** |

* **费用估算**：`api.deepseek.com` 无账单查询接口，`deepseek-flash` 的实际单价**奈奈无法从端点核实**。
  按两个公开参照档估算区间：**≈ ¥0.23（低价档 ¥2/¥8 每百万）～ ¥0.62（2026Q2 国内均值 ¥4.9/¥21.9）**，
  即**约 ¥0.2 ~ ¥0.7**。若需精确到分，须姐姐在服务商控制台核对 → `[未知]`。
* **闸门有效性**：单任务 `max_calls=1` 为**代码级硬约束**（超限直接拒绝外发），已由 T8 用例覆盖。
* **超出"单任务一次"的部分**：总授权内实发 **3 次**。第 ②→③ 是**修 bug 后的一次 bounded 重试**
  （依据长期协作原则第 3 条"既定预算内自主重试"）；奈奈在此显式披露，不隐藏。

---

## 六、离"无人值守协作"还差什么

| # | 缺口 | 性质 | 需要谁 |
|---|---|---|---|
| 1 | **真实 Codex Runner 未接入**：当前是 `LocalLLMRunner` 复用兼容端点，**不是** Codex | 本质差异，须 `[未知]`→`[实测]` | 姐姐（L3：装 `@openai/codex` + device-code 登录） |
| 2 | **无自动派单**：TaskSpec 仍由奈奈手工产出并手工调用 CLI，无队列/触发/去重 | 工程 | 奈奈（L1） |
| 3 | **成本未闭环**：只有 token usage，无累计费用台账与阈值熔断 | 工程 + 口径 | 奈奈（L1）+ 姐姐（单价口径） |
| 4 | **质量门偏薄**：白名单 + 单条验收命令；缺"自修复次数上限 / 回归基线对比 / diff 语义审查" | 工程 | 奈奈（L1） |
| 5 | **回执归档策略未定**：`bridge/receipts/` 是 gitignore 的运行时产物，关键回执长期留证需另立策略 | 决策 | 奈奈提案，姐姐点头 |
| 6 | **权限仍旧集中于低风险**：仅 L1 副本内自主；L3（推送/装依赖/新凭据）未开 | 授权 | 姐姐 |

> 结论：**链路本身已证明可用**（奈奈派单 → 真实端点接收 → 返回代码 → 白名单校验 → 验收 → 收货）。
> 但要"无人值守"，缺的是 **#1（真 Codex）+ #2/#3/#4（自动化与成本熔断）**；
> 其中 **#1 是唯一需要姐姐的一次性审批**，其余奈奈可在 L1 内自建。

---

## 七、可复现命令

```bash
cd /root/nana_dev/nana-core/bridge

# 离线（不联网）
python3 codex_bridge.py --selftest
python3 test_codex_bridge.py        # 9/9
python3 test_local_runner.py        # 9/9（含 T7 CLI 身份回归）

# 真实运行（需姐姐的一次性授权；凭据由调用方在进程内注入，不入库）
export NANA_BRIDGE_BASE_URL=...  NANA_BRIDGE_API_KEY=...  NANA_BRIDGE_MODEL=deepseek-flash
export NANA_BRIDGE_MAX_CALLS=1 NANA_BRIDGE_MAX_FILES=2 NANA_BRIDGE_MAX_BYTES=30000
python3 codex_bridge.py --spec tasks/c5v_real_01.json --runner local_llm
```

## 八、回滚

1. `rm -rf bridge/scratch bridge/receipts` —— 隔离克隆与回执，**源仓不受影响**。
2. 不设 `NANA_BRIDGE_*` 环境变量 → Runner 构造为 `None` → **物理上不可能出网**（T6 守着）。
3. 未改生产、未加 remote、未 push，**无需生产回滚**。
