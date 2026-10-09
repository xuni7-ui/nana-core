# 奈奈 ↔ Codex 协作桥（bridge/）

> 创建：2026-10-10 ｜ 状态：**机制已离线验证，真实 Runner 待一次性授权**
> 定位：**奈奈负责统筹 / 事实核验 / 验收；Codex（或等价本地 Runner）负责技术设计、编码、测试与修复。**

---

## 1. 闭环（4 步）

```
TaskSpec  →  隔离克隆(git clone → bridge/scratch/<id>)  →  Runner 执行  →  边界校验 + 验收命令  →  回执 JSON
```

* **源仓永不被改**：`git clone --no-hardlinks` 到 scratch，源仓只读（有逐字节哈希测试 T6 守着）。
* **边界白名单**：改动落到 `allow_paths` 之外 → 判违规，`applied=False`，不并入结果。
* **硬黑名单优先**：`.env / *credential* / *secret* / *token* / *cookie* / *.key` 一律禁止改动，
  且**永不进入发给模型的提示词**（T2 有"金丝雀"断言）。
* **回执留痕**：`bridge/receipts/<task_id>.json`（含 changed_files / diff / 验收输出 / 判定）。

## 2. 文件

| 文件 | 作用 |
|---|---|
| `codex_bridge.py` | 编排 + 隔离 + 边界校验 + 回执（**零网络**） |
| `local_runner.py` | Runner 实现：用**已装 openai SDK + 已配置兼容端点**编码 |
| `test_codex_bridge.py` | 闭环离线测试 T1–T9 |
| `test_local_runner.py` | Runner 离线测试 T1–T6（含 127.0.0.1 真实 HTTP 链路） |
| `receipts/` | 回执行（运行时产物，不入库） |
| `scratch/` | 隔离克隆（运行时产物，不入库） |

## 3. Runner 选型（已自行比较，选 B）

| 方案 | 依赖 | 新授权 | 判定 |
|---|---|---|---|
| A. `@openai/codex` CLI | 需安装（npm）+ 登录/密钥 | 安装 + 新凭据 | 备选：端点质量不足时再上 |
| **B. `LocalLLMRunner`（已选）** | **无（openai SDK 已装）** | 仅"出网"一项 | **首次真实协作用它** |
| C. `StubRunner` | 无 | 无 | 仅供离线测试，无真实编码能力 |

**为什么选 B**：零新增依赖、零新增凭据、只动 scratch（可整目录删除回滚）、复用已在用的模型端点。
**风险**：代码片段会发往该端点（外部上传）；模型可能产出坏改动 → 由边界校验 + 验收命令兜底。

## 4. 用法

```bash
# 离线自检（不联网）
python3 codex_bridge.py --selftest
python3 test_codex_bridge.py && python3 test_local_runner.py

# 真实运行（需先授权出网）
export NANA_BRIDGE_BASE_URL=...   # 复用已在用的兼容端点
export NANA_BRIDGE_API_KEY=...    # 由姐姐注入，不入库
python3 codex_bridge.py --spec task.json
```

`task.json` = `TaskSpec` 的字段：`task_id / goal / repo / allow_paths / deny_paths / test_command / test_timeout_s / budget_s`。

## 5. 首个真实协作任务

**C.5-V-1 视频视觉接线**（`src/bili_agent/c5v_wiring.py`）。
接线层与其测试已由奈奈在隔离副本内先行落地（11/11 离线通过），
待桥开通后可作为「首个真实协作任务」交给 Runner 做增量（如真实端点下的端到端跑测）。
