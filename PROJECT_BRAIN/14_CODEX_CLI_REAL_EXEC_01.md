# 14 · Codex CLI 真实执行验证（自定义 Provider · 单次最小任务）

- 时间：2026-10-10 03:14–03:25 CST
- 授权：姐姐「同意进行一次 Codex CLI 自定义 Provider 的最小真实验证」（L3：出网 + 消耗既有端点额度）
- **执行框架**：`Codex CLI 0.162.0`（`@openai/codex` 官方 npm 包 + 官方 linux-x64 原生二进制）
- **模型**：`DeepSeek deepseek-flash` @ `https://api.deepseek.com/v1`（**不是** OpenAI 模型）
- 两者**严格区分**：`is_codex_cli = true`，`model_provider = deepseek`，`is_openai_model = false`
- 生产改动：**0** ｜ push：**无**（无 remote） ｜ 新密钥：**0**

---

## 一、结论（三句话）

1. **真 Codex CLI 执行成功**：CLI 真实完成「写文件 → 执行命令 → 观测测试输出」完整闭环，**不是**返回代码文本。
2. **协议可行但形态受限**：该版本**只支持 `wire_api = "responses"`**；DeepSeek `/v1/responses` 实测可用。
3. **沙箱在本容器不可用**：容器禁止创建 namespace（`unshare -U` → EPERM），bwrap 死路；改用 **OS 级降权外部沙箱**（`nobody`）替代，实测有效。

---

## 二、版本能力核验（不许假定"改一行就兼容"）

| 核验项 | 方法 | 结果 |
|---|---|---|
| CLI 版本 | `codex --version` | `codex-cli 0.162.0` `[实测]` |
| 是否支持自定义 Provider | 二进制 strings + `--strict-config` 实跑 | ✅ 支持 `[model_providers.*]`（`base_url` / `env_key` / `wire_api`）`[实测]` |
| `wire_api` 可选值 | 直接以 `wire_api="chat"` 启动 | ❌ **`wire_api = "chat"` is no longer supported** → 提示改 `responses` `[实测]` |
| 端点是否讲 Responses 协议 | `POST /v1/responses` | ✅ **HTTP 200**，返回标准 `response` 对象 `[实测]` |
| 配置是否被版本接受 | `codex exec --strict-config` | ✅ 无 unrecognized field 报错 `[实测]` |
| 原始 OpenAI 登录路径 | （R3 已测） | ❌ 403 / 超时，**本方案不依赖它** |

> 参考：`https://github.com/openai/codex/discussions/7782`（CLI 自身给出的迁移说明）

## 三、沙箱约束（关键环境事实）

| 事实 | 证据 |
|---|---|
| 容器禁止 namespace | `unshare -U true` → `Operation not permitted` `[实测]` |
| 内核开关本身是开的 | `kernel.unprivileged_userns_clone=1`、`max_user_namespaces=14566` `[实测]` → 说明是**容器 seccomp/Cap** 限制 |
| bwrap 无法替代 | `codex sandbox linux -- pwd` → `bwrap: No permissions to create a new namespace` `[实测]` |
| Landlock 亦不可用 | `/sys/kernel/security/lsm` 不存在 `[实测]` |
| Docker 不可用 | `docker/podman` 均 not found `[实测]` |

→ 结论：**Codex 自带沙箱在本机物理不可用**，唯一出路是「外部沙箱」。

## 四、采用的隔离方案（OS 级外部沙箱）

- 进程以 **`nobody(65534)`** 运行（`setpriv --reuid/--regid --clear-groups`）
- `--dangerously-bypass-approvals-and-sandbox`（官方为"已外部沙箱化环境"提供的入口）
- 工作区：`/opt/nana_codex/sandbox/run01`（独立空 git 仓，仅种子 README）
- 凭据：运行时从 `cmd_config.json` 读入**内存**，仅注入子进程环境变量（`env_key` 机制），**不落盘**
- 实测边界：nobody **读不到** `cmd_config.json`（0600）、**写不进** `/AstrBot` `[实测]`

## 五、真实执行记录（唯一一次任务）

任务：创建 `calc.py`(add) → 创建 `test_calc.py`(assert 正/负/零) → 运行 `python3 test_calc.py`。

| 项 | 结果 |
|---|---|
| 文件修改 | ✅ 真实写入 `calc.py` / `test_calc.py`（32B / 195B）`[实测]` |
| 命令执行 | ✅ `/usr/bin/bash -lc "…python3 test_calc.py"` → `exit_code=0` `[实测]` |
| 测试结果 | ✅ `all tests passed`（模型自述 **+** 奈奈独立复跑，rc=0）`[实测]` |
| 是否只是"返回代码文本" | ❌ **不是**，产物落盘且可独立复现 |
| git 状态 | `?? calc.py` `?? test_calc.py` `?? __pycache__/`（真实新增未跟踪文件）`[实测]` |

### 首次尝试为何失败（保留证据，不掩盖）
第一次以 `-s workspace-write` 运行：Codex **真实连上了** `https://api.deepseek.com/v1/responses`（假钥匙返回 401 证明协议握手成立），
但每条 shell 均被 bwrap 拒绝 → 模型诚实报告"环境沙箱起不来，任务无法执行"，**未伪造成功**。
→ 该次不计为验收通过，仅证明「协议通 + 沙箱不通」。

## 六、成本（口径标注）

| 轮次 | input | cached | output | 性质 |
|---|---|---|---|---|
| R4 第 1 次（沙箱失败） | 78,113 | 76,544 | 2,049 | `[实测]` 端点 usage |
| R4 第 2 次（成功） | 17,470 | 16,384 | 225 | `[实测]` 端点 usage |
| **合计** | **95,583** | **92,928** | **2,274** | — |

**估算费用：≈ ¥0.03**（按 deepseek-chat 档 ¥2/M 未命中、¥0.2/M 命中、¥3/M 输出估算）。
⚠️ 单价口径 `[未核实]`，故仅报**量级**：**肯定 < ¥0.5**。零成本探针（假钥匙/401/404）不产生费用。

## 七、现存缺口（距"无人值守开发"）

| # | 缺口 | 严重度 | 归属 |
|---|---|---|---|
| 1 | **沙箱依赖外部 OS 降权**，非 Codex 原生 bwrap；容器一旦重建需重做 `/opt/nana_codex` | 中 | 奈奈 L1 |
| 2 | 模型元数据缺失告警（`Model metadata for deepseek-flash not found`）→ 上下文窗口按 fallback，长任务可能误判 | 中 | 奈奈 L1 |
| 3 | 桥的 Runner 尚未切到 `codex_cli`（现仍为 `LocalLLMRunner`） | 中 | 奈奈 L1 |
| 4 | 无逐次成本熔断台账（仅能从 usage 事后核算） | 中 | 奈奈 L1 |
| 5 | 降权进程可读**世界可读**的生产文件（如 `data_v4.db` 644）——本轮未发生，但**不是结构性强隔离** | **低偏中** | 需姐姐决策是否加固 |

## 八、可复现命令

```bash
setpriv --reuid=65534 --regid=65534 --clear-groups \
  env HOME=/opt/nana_codex/home CODEX_HOME=/opt/nana_codex/home \
      NANA_BRIDGE_API_KEY=<运行期注入，不入库> \
  /usr/bin/node /opt/nana_codex/node_modules/@openai/codex/bin/codex.js exec \
      --strict-config --json --dangerously-bypass-approvals-and-sandbox \
      -C /opt/nana_codex/sandbox/<workdir> "<task>"
```

配置：`/opt/nana_codex/home/config.toml`（`model_providers.nana_deepseek`，`wire_api="responses"`）

## 九、回滚

1. `rm -rf /opt/nana_codex` —— 开发入口整体消失，**零残留**。
2. `/root/nana_dev/codex_probe`（探针 + 脚本）可整目录删除。
3. 生产、`~/.codex`、全局 npm **均未改动**；无 remote、无 push，**无需生产回滚**。
