# 23 · T-41 真实 Runner 启用 + 首个真实协作任务执行（R13/R14）

> 时间：2026-10-10 04:5x–05:0x UTC（= 12:5x–13:0x CST）｜ 授权口令：姐姐「动手」
> 范围：`bridge/**`（非生产）＋隔离副本 `/opt/nana_codex/sandbox/bridge/**`
> 边界：**生产零改动、无 push、无 PR、零新依赖、零新密钥**

---

## 一、结论（一句话）

**B 路线（主机 Codex CLI）已真正打通**：桥以「外部沙箱 + 降权 nobody」形态驱动
`codex exec` 真实完成了一次「读源码 → 改代码 → 跑测试」闭环，**回执 `applied=True`**。
途中修掉 **2 个真实缺陷**（1 个致 300s 假超时、1 个致 401），并**补上 1 个安全洞**（验收阶段以 root 跑）。

---

## 二、执行事实链（三次运行，不掩盖失败）

| # | 现象 | 判定 | 根因 |
|---|---|---|---|
| 1 | `Runner 超时（300s）`，零输出零改动 | ❌ | **stdin 未关闭**：codex 0.162 在 stdin 非 TTY 时「读 stdin 到 EOF」，继承了永不关闭的管道 → 死等 |
| 2 | 7.04s 退出码 1，`401 Unauthorized` | ❌ | **key 取错**：`provider_sources[].key` 是**列表**，`str()` 后变成 `"['sk-…']"` 送出 |
| 3 | **`ok=True / applied=True / test_ok=True`，52.4s** | ✅ | 修完上述两项 |

**窄探针佐证（可复现）**：
- 修 stdin 前：`rc=124`（75s 超时），stdout **0 字节**，stderr 仅 `Reading additional input from stdin...`
- 修 stdin 后：`rc=1`，**0.27s** 内明确回报 `Missing environment variable: NANA_BRIDGE_API_KEY`（协议握手成立，只是缺钥匙）

---

## 三、本次代码改动（`bridge/codex_bridge.py`）

| 改动 | 内容 | 为什么 |
|---|---|---|
| `CodexRunner` 重写 | 对齐 0.162.0 真实形态：`setpriv --reuid/--regid --clear-groups` → `env HOME/CODEX_HOME/KEY` → `node codex.js exec --strict-config --json --dangerously-bypass-approvals-and-sandbox -C <dir> -m <model>` | 原实现只调 `codex`（不在 PATH）且缺降权，必失败 |
| **stdin=DEVNULL** | runner 与验收命令均显式关 stdin | 修缺陷 ①（300s 假超时） |
| **`_first_key()` 归一化** | `key` 为 list → 取首个非空元素 | 修缺陷 ②（401） |
| **验收命令降权** | 新增 `wrap_test_command()`，验收也在 nobody 沙箱内跑 | **补安全洞**：模型产物原以 root 执行，等于绕过外部沙箱 |
| `redact()` 全链路 | 出参、回执落盘前统一打码；追加 `****xx` 残片与 `sk-` 正则 | 防密钥以任何形式落盘 |
| `SCRATCH_ROOT` 可外置 | `NANA_BRIDGE_SCRATCH_ROOT`（默认不变） | `/root` 对 nobody 是 `0700`，不可穿越；沙箱工作区必须外置到 `/opt` |
| `--dry-run` | 只装配并打印最终命令（密钥打码），**不执行不出网** | 授权前可核验命令形状 |

**离线回归：18/18 全绿**（`test_codex_bridge.py` 9/9 + `test_local_runner.py` 9/9）+ `--selftest` 通过。

---

## 四、首个真实协作任务（`tasks/c5v_real_01.json`）

- **任务**：`src/bili_agent/c5v_wiring.py` 的 `vision_brief()` 增加可选 `cache_dir`，命中则复用本地视频、不调 fetcher；`cache_dir=None` 时逐字节等价；补离线用例。
- **环境**：Codex CLI 0.162.0 ｜ provider `nana_deepseek`（DeepSeek `deepseek-flash` @ `/v1/responses`）｜ 进程降权 `nobody(65534)` ｜ 工作区 `/opt/nana_codex/sandbox/bridge/c5v_real_01`
- **结果**：`ok=True` ｜ `applied=True` ｜ `duration_s=52.395`

| 采集项 | 值 |
|---|---|
| changed_files | `src/bili_agent/c5v_wiring.py`、`src/bili_agent/test_c5v_wiring.py` |
| violations | **0**（全落白名单内） |
| diff_stat | 2 files changed, **70 insertions(+), 4 deletions(-)** |
| 桥内验收 | **13 通过 / 0 失败**（11 旧 + T10/T11 新） |

### 奈奈的独立验收（不采信模型自述）

1. **本机复跑**（不经桥）：`python3 src/bili_agent/test_c5v_wiring.py` → **13 通过 / 0 失败** ✅
2. **边界**：`git diff --cached --stat` → 仅上述 2 文件，**无越界** ✅
3. **依赖**：顶层仅标准库（`os/shutil/subprocess/tempfile/time/dataclasses/typing`）✅
4. **密钥**：无硬编码 key/cookie/token 特征 ✅
5. **源仓未被碰**：源仓 HEAD 仍为 `9d31c28`，工作区仅本次桥改动 ✅
6. **回执脱敏**：`receipts/*.json` 内 `sk-` / `****` 痕迹自查 = 0 ✅

---

## 五、影响面与残留风险

- ✅ 生产（`/AstrBot`、`data_v4.db`、`cmd_config.json`、pl制品）**零改动**；源仓 `nana_dev/nana-core` 仅 `bridge/**` 变更。
- ⚠️ **R-1**：模型元数据告警 `Model metadata for deepseek-flash not found`（上下文窗口走 fallback）→ 长任务可能误判，仍属 `[未核实]`。
- ⚠️ **R-2**：桥内无逐次成本熔断台账（本次仅一次请求，规模可控）。
- ⚠️ **R-3**：`/opt/nana_codex` 不在 git 内，容器重建需重做（见 `14` §七-1）。
- 🔒 密钥仅在运行期从 `cmd_config.json` 读入内存 → 注入子进程环境 → **不落盘、不进回执**。

---

## 六、回滚

1. `git revert <R13/R14 提交>` —— 桥回到纯离线形态。
2. `rm -rf /opt/nana_codex/sandbox/bridge` —— 隔离副本整体消失。
3. 生产**无需回滚**（本轮未触）。
