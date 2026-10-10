# PROJECT_BRAIN / 02 源码清单

> 全部条目为 `[实测]` 2026-10-10 本机采集。**不在本清单中的源码，视为未核实。**

## 一、AstrBot 宿主

| 项目 | 值 | 来源 |
|---|---|---|
| 版本 | `4.28.0`（pyproject.toml `name/version`） | `[实测]` |
| 路径 | `/AstrBot`（主程序包 `/AstrBot/astrbot`） | `[实测]` |
| 许可证 | 仓库根 `LICENSE` 存在（AstrBot 官方） | `[实测]` |
| 本地 Git | **无 `.git`** → 无版本追溯能力 | `[实测]` |
| 官方 AGENTS.md | `/AstrBot/AGENTS.md`（6,502 B，内容为 uv/pnpm/pre-commit 规范） | `[实测]` |

> ⚠️ `/AstrBot/AGENTS.md` 是 **AstrBot 官方**的开发规范，**不是**奈奈工程的 AGENTS.md，**禁止**直接复用到本项目。

## 二、Iris 记忆插件（`astrbot_plugin_iris_chat_memory`）

- 上游：`Leafiber/astrbot_plugin_iris_chat_memory` v0.3.0，LICENSE=**AGPL-3.0**。`[实测]`
- 结构：`iris_memory/` 下 16 个子包（commands/config/core/dream/image/l1_buffer/l2_memory/l3_kg/llm/platform/profile/tasks/tools/utils/web），`.py` 文件 **187 个**。`[实测]`
- **奈奈改动文件清单（14 个）** `[实测]`：见 `manifests/fingerprints_20261010.md`
- 改动 diff：`manifests/nana_iris_changes.diff`（66 KB，**改前备份 ↔ 现行**）

## 三、奈奈自制插件（4 个）

| 插件 | 文件 | 行数 | 来源 |
|---|---|---|---|
| `astrbot_plugin_nana_admin_guard` | main.py | 39 | `[实测]` author=Linna |
| `astrbot_plugin_nana_anchor` | main.py | 121 | `[实测]` author=Nana |
| `astrbot_plugin_nana_bilievent` | main.py | 131 | `[实测]` author=Nana |
| `astrbot_plugin_linna_tmp` | main.py | 48 | `[实测]` author=Linna |

## 四、B站 Agent 外挂脚本（`/root/.nana_secrets/`）

| 文件 | 行数 | 职责 |
|---|---|---|
| `bili_agent.py` | 911 | Agent 骨架（observe→…→record） |
| `bili_event_pump.py` | 466 | 事件轮询泵（常驻） |
| `bili_event_source.py` | 142 | 事件源接口 |
| `bili_send_core.py` | 378 | 发送状态机核心 |
| `bili_video_read.py` | 414 | 视频/字幕读取 |
| `nana_bili_health_check.py` | — | 健康巡检（含封板指纹基线） |
| `bili_refresh.py` / `bili_send_comment.py` / `bili_reply_comment.py` | — | 保活/发评/回复 |
| `bili_qr_login*.py` / `probe_msgfeed_readonly.py` | — | 登录工具 / 只读探针 |
| `test_bili_agent*.py` / `test_c*.py` | — | 测试脚本 |

> ⚠️ **`test_bili_agent_semantic_retry.py` 含硬编码 SESSDATA 字面量 → 严禁入库**（见 `manifests/sensitive_scan_report_20261010.md`）。

## 五、事实文件（工作区，非生产源码）

位于 `.../workspaces/default_1905615275_.../`：

- `nana_notes/*.md`（笔记 + C7 缺陷记录）
- `c5v_offline/`（C.5-V 离线骨架 + README）
- `对话流水/2026100{6..0}.jsonl`（**含私人聊天 → 禁传**）
- `奈奈源码_运行版_20261007_施工前.zip`（施工前快照，1.6 MB）
- 各类 `*.md` 报告（P0B 实况包 / 运行态验证报告 等）

## 六、本轮新增（隔离副本 `src/` 与 `bridge/`）

| 文件 | 职责 | 状态 |
|---|---|---|
| `src/bili_agent/c5v_wiring.py` | C.5-V-1 接线适配层（默认关闭、失败逐字节还原） | ② 已测试（11/11） |
| `src/bili_agent/test_c5v_wiring.py` | 适配层离线测试 T1–T9 | `[实测]` |
| `bridge/codex_bridge.py` | 协作桥编排（隔离克隆 + 边界校验 + 回执） | ② 已测试（9/9） |
| `bridge/local_runner.py` | 本地 Runner（openai SDK + 注入端点） | ② 已测试（6/6） |
| `bridge/test_codex_bridge.py` / `test_local_runner.py` | 桥离线测试 | `[实测]` |
| `docs/c5v_wiring_design.md` | 接线方案比较与选型 | 文档 |

> ⚠️ 以上均为**隔离副本内**产物，**未**接入生产；`bridge/scratch|receipts` 为运行时产物，不入库。

## 七、尚未核实的源码位置（`[未知]`）

- 生图脚本（`gen_*.py`）散落于工作区根，**未逐一鉴定是否为工程组成部分**。
- `nana_dsh_whale_*`（桌面/Android 悬浮窗）与奈奈 Core **无关**，属另一条产品线。


---

## 八、P3 增补（2026-10-10（CST））

- 【源码确认】**Iris 上游已获取**：tag `0.3.0`（commit `0557a4c1…`），241 blob；以 `git blob SHA1` 全量比对生产插件目录 → **234 同 / 7 改 / 7 新增 / 0 缺失**。旧"上游未获取/改前↔现行"作废。
- 【实测】**AstrBot 上游基线**：GitHub tag `v4.28.0` commit `a4121464…`；补丁入 `patches/astrbot/`。
- 【实测】**B站外挂**：5 个登录脚本入 `materials/bili_agent/login/`（`bili_qr_login*.py`）；9 个测试脚本排除（见 `materials/bili_agent/EXCLUSIONS.md`）。
- 【实测】新增工程材料目录见 `00_INDEX` 第六节。
