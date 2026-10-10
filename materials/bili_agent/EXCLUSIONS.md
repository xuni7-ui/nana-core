# 排除清单（未入库文件及原因）

> 【实测】2026-10-10。被排除文件**仍保留在生产目录**，仅在仓库侧不纳入。

| 文件 | 排除原因 | 可替代方案 |
|---|---|---|
| `test_bili_agent.py` | 含真实事件/消息 ID | 用合成 ID 夹具重写 |
| `test_bili_agent_observe_real.py` | 含真实事件 ID | 合成事件 JSON 回放 |
| `test_bili_agent_semantic_real.py` | 含真实事件 ID | 合成夹具 |
| `test_bili_agent_semantic_retry.py` | 含**真实事件 ID/UID 143666765** + 假 `SESSDATA=abcdef…` 夹具 | 脱敏为 `SESSDATA=DUMMY` |
| `test_bili_agent_semantic_retry_real.py` | 含真实事件 ID | 合成夹具 |
| `test_c2_real_verify.py` | 含真实事件 ID | 合成状态机夹具 |
| `test_c2_state_machine.py` | 含真实事件 ID | 可脱敏后入库 |
| `test_c4_events.py` | 含真实事件 ID/UID | 合成事件流 |
| `test_c7p1_replay.py` | 含真实事件 ID/UID | 合成回放集 |

## 说明
- 排除依据：授权"含有真实凭据、私有数据或无法安全脱敏的脚本不得上传"。
- 上述文件**无真实 Cookie/Token 真值**（扫描通过），但含**真实事件 ID 与 1 个疑似真实 UID**，属私有数据，故排除。
- 后续可提供**合成夹具版**测试集（不依赖生产 ID）。
