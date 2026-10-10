# Iris 记忆插件定制改动（D3）— 独立材料

> 隔离目录：本材料**单独存放**，不与 Nana Core 原创源码混合；随附上游 AGPL-3.0 许可证。
> 分级：【实测】【源码确认】【文档】【推断】【未知】

## 1. 上游锁定【源码确认】
| 项 | 值 |
|---|---|
| 上游仓库 | `Leafliber/astrbot_plugin_iris_chat_memory` |
| 版本 | `0.3.0`（metadata.yaml） |
| tag commit | `0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6` |
| 上游 blob 数 | 241（GitHub trees API `?recursive=1`） |
| LICENSE | **AGPL-3.0**（见 `LICENSE-AGPL-3.0.txt`） |

## 2. 定制改动全量清单（14 处 = 7 改 + 7 新增）【源码确认】
比对方式：对生产插件目录每个文件计算 **git blob SHA1**，与上游 tag `0.3.0` 的 241 个 blob 逐一比对。
结果：**234 文件逐字节相同，7 文件修改，7 文件新增，0 缺失**。

### 7 处修改（相对上游）
1. `_conf_schema.json`
2. `iris_memory/config/defaults.py`
3. `iris_memory/core/llm_request_hook.py`
4. `iris_memory/core/llm_response_hook.py`
5. `iris_memory/core/message_hook.py`
6. `iris_memory/l1_buffer/buffer.py`
7. `iris_memory/utils/__init__.py`

### 7 处新增（上游不存在）
1. `iris_memory/core/semantic_gate.py`   —— Semantic Gate
2. `iris_memory/core/action_ledger.py`   —— Action Ledger
3. `iris_memory/core/decision_log.py`
4. `iris_memory/core/conversation_flow.py`
5. `iris_memory/utils/timeutil.py`        —— 时间工具
6. `tests/core/test_semantic_gate.py`
7. `tests/core/test_gate_off_parity.py`

> 注：生产目录另有 `data/cmd_config.json` 与 `data/t2i_templates/*.html` 4 个文件不在上游——**属运行期数据/模板产物**，不计入定制改动，未纳入本补丁。

## 3. 覆盖的主题
- **Semantic Gate**（语义门控）：`semantic_gate.py`（新增）+ `llm_request_hook.py`/`message_hook.py`/`defaults.py`/`_conf_schema.json`（接入开关）。
- **Action Ledger**（动作账本）：`action_ledger.py`（新增）+ `decision_log.py`（新增）。
- **时间工具**：`utils/timeutil.py`（新增，UTC+8 北京时间口径）。
- **长消息处理**：`l1_buffer/buffer.py` + `config/defaults.py`。
- **测试**：`tests/core/test_semantic_gate.py`、`test_gate_off_parity.py`（新增）。

## 4. 复现 / 重建
```bash
git clone --branch 0.3.0 https://github.com/Leafliber/astrbot_plugin_iris_chat_memory iris_upstream
cd iris_upstream
git apply ../materials/iris_customizations/iris_customizations_v0.3.0.patch
# 得到与生产完全一致的 14 处文件（sha256 见 FINGERPRINTS.md）
```
【实测】补丁对 241 文件干净基线 `git apply --check` 通过；应用后 14 文件与生产**逐字节一致**。

## 5. 敏感信息
【实测】补丁与新增文件仅含代码；无密钥、无 Cookie、无用户数据、无日志。

## 6. 许可说明（依法判断，不简化）
- 上游 Iris 为 **AGPL-3.0**，本 14 处改动是 **AGPL 衍生作品**，因此**本目录内**材料适用 AGPL-3.0（附 `LICENSE-AGPL-3.0.txt`）。
- AGPL 的义务取决于**代码关系与使用方式**，**不能**简单认定"入库即整个仓库自动变 AGPL"。
- Nana Core 原创代码的许可证由**姐姐最终决定**；本目录为**隔离材料**，不影响其他部分。
