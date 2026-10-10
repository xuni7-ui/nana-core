# B站 Agent 外挂源码（C 线）— 纳入材料

> 【实测】2026-10-10 比对生产 `/root/.nana_secrets/*.py` 与仓库 `src/bili_agent/`、`src/c5v/`。

## 1. 比对结论【实测】
- **已在仓库且一致**（仓库==生产，sha256 相等）：`bili_agent.py`、`bili_event_pump.py`、`bili_event_source.py`、`bili_refresh.py`、`bili_reply_comment.py`、`bili_send_comment.py`、`bili_send_core.py`、`bili_video_read.py`、`nana_bili_health_check.py`、`probe_msgfeed_readonly.py`。
- **本轮补入**：5 个登录辅助脚本 → 本目录 `login/`。
- **排除**：9 个测试脚本（见 `EXCLUSIONS.md`）。

## 2. 5 个登录辅助脚本（本轮入库）【实测】
| 文件 | 行数 | sha256(前16) |
|---|---|---|
| `bili_qr_login.py` | 67 | `46c0a0b7ad8486f9…` |
| `bili_qr_login_v2.py` | 123 | `5c9adbd49287b53d…` |
| `bili_qr_login_v3.py` | 142 | `dd2d2827db6c699f…` |
| `bili_qr_login_v4.py` | 158 | `82aad3e2bde8f178…` |
| `bili_qr_login_v5.py` | 171 | `43c81d1fc2498048…` |

- 内容：B站扫码登录，产物写入 `/root/.nana_secrets/bilibili_credential.json`（0600）。
- **敏感扫描**：无 Cookie/SESSDATA/Token **真值**、无长数字 ID、无个人信息；仅有凭据**路径**与字段**键名**。✅ 可入库。
- 依赖：`bilibili-api-python`、`qrcode`/`Pillow`（见仓库根 `requirements.txt`）。

## 3. C.5-V 状态
- 源码：`src/c5v/bili_video_vision.py`、`src/c5v/README_c5v.md`；接线层 `src/bili_agent/c5v_wiring.py`（默认关闭 `NANA_C5V_WIRING=0`，失败逐字节还原）。
- 状态：**离线骨架 + 已测试**（`test_c5v_wiring.py` 11/11）【实测】；**未接入生产事件泵**。
- 边界：**不擅自接入生产**（授权明确禁止）。

## 4. 脱离生产即可运行的说明
- 可独立运行：`c5v_wiring.py`、`test_c5v_wiring.py`、`bili_event_source.py`（离线部分）。
- 依赖生产环境：真实发送/评论/登录（需凭据与网络）、事件泵（常驻进程 + 状态文件）。
