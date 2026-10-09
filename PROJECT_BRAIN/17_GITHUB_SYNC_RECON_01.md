# 17 · GitHub 首次同步前置核验 + 官方 Codex 触发面实测（R7）

> 时间：2026-10-10 CST ｜ 作者：奈奈 ｜ 性质：**只读核验**（no push / 生产改动 0 / 无新凭据）
> 任务来源：姐姐 2026-10-10 指令——批准 GitHub + 官方 Codex Cloud 协作接入；采用「只限 nana-core 单仓库 Fine-grained PAT」最简方案；首次同步前排除不适合文件与历史、不得覆盖远端已有内容。

---

## 一、全量 Git 历史核验（不只当前文件）

| 项 | 实测 |
|---|---|
| 仓库 | `/root/nana_dev/nana-core` · 分支 `master`（唯一） · remote **无** |
| 提交数 | **9**（`26ef7af` → `d8976a8`） |
| 跟踪文件 | **66** |
| reflog / stash | 干净（无隐藏提交、无 stash） |
| **历史中被删除过的路径** | **0**（无「曾入库后删除」的残留文件） |
| **全历史所有 blob 真凭据值扫描** | **0 命中** ✅（`sk-` / `github_pat_` / `ghp_` / `AKIA` / PRIVATE KEY / `"sessdata": "…"` 长值 / `Bearer` 长值 全过） |
| 二进制 / 超大文件 | **无**（最大为 1590 行文本 diff） |

**结论**：拟推送历史中**不存在**任何「当前文件之外的隐藏敏感物」。9 个提交全部是文档 + 白名单源码，历史干净。

> 说明：扫描命中的 `SESSDATA`/`bili_jct`/`dedeuserid` 全部是**变量名、字典键、`.get()` 访问**，非字面量值；`test_bili_agent_semantic_retry.py`（唯一含硬编码值的文件）**从未进入本库**。

---

## 二、首发排除项与许可证

| 项 | 判定 | 处置 |
|---|---|---|
| `manifests/nana_iris_changes.diff`（1589 行，Iris `semantic_gate.py` 改动） | 含 **AGPL-3.0 衍生代码上下文** | **首发排除**（遵姐姐指令） |
| `src/plugins/*`（奈奈原创，**缺 LICENSE**） | 私有库暂可 | 公开前须指定许可；本次私有库不阻塞 |
| 信息暴露面 | `PROJECT_BRAIN/01,03,15` 含生产**目录拓扑**（路径名，非密钥） | 已报备：私有库连 Codex Cloud 后会随库可见于 OpenAI 侧 |

---

## 三、白名单口径缺口（需补登，非阻塞）

`manifests/upload_whitelist.md` 制于 P1 时刻（当时 49 文件），**未覆盖 R1–R6 新增**。按「白名单制=默认禁止」，以下当前**不在白名单**，须显式补登或排除：

- `bridge/**`（codex_bridge.py / local_runner.py / probes / tasks / tests / README）
- `docs/c5v_wiring_design.md`
- `PROJECT_BRAIN/12–16`（R1–R6 证据文档；文档类，应与 00–11 同权）

**奈奈建议**：以上均属「奈奈原创/证据文档」类别，**补入白名单后首发**（不含任何凭据、运行数据）。

---

## 四、远端真实状态（凭 PAT 前无法定论）

| 检查 | 结果 |
|---|---|
| `xuni7-ui` 用户 | HTTP 200（存在） |
| `xuni7-ui/nana-core` 匿名访问 | **404 / 要求认证** → **私有** |
| 本机 GitHub 凭据 | **零**（无 `~/.git-credentials`、无 `credential.helper`、无 `gh`） |
| 远端是否已有 README / 提交 | **未知**（需 PAT 后只读 `git ls-remote` + `fetch` 才能核实） |

> ⚠️ 姐姐此前反馈仓库「当前只有 README.md」。**该 README 属于远端已有内容，首发绝不覆盖。**
> 因此**目标分支策略待 fetch 后定**，不预先写死。

---

## 五、首发分支 / 策略（待 fetch 后最终确认）

1. **只读步**：持 PAT 先 `git ls-remote` + `fetch`（**只读，非 push**）→ 核实远端已有分支与 README 真实内容。
2. **推送步**（完成 1 后申请最终确认）：
   - 若远端与本地**无共同历史** → 推送到**新分支**（如 `nana/init-sync`），**不用 force、不碰远端默认分支、不动远端 README**；再开 PR 走 Codex 评审。
   - 绝不 `--force`、不 `--mirror`、不删远端引用。
3. 排除项：`manifests/nana_iris_changes.diff` 不入首发。

---

## 六、官方 Codex 触发面（官方文档原文 + 本机 CLI 实测）

**官方文档确认（learn.chatgpt.com/docs/third-party/github）**：

| 触发面 | 官方 | 奈奈可否无人值守发起 | 备注 |
|---|---|---|---|
| `@codex` 评论（PR） | ✅ | ✅（GitHub API 发评论） | 官方原文：非 `review` 的 @codex 会起一个**legacy cloud chat**，以该 PR 为上下文 |
| `@codex review` / `security review` / `fix the P1 issue` | ✅ | ✅ | PR-only；review 只报 P0/P1 |
| 自动 review（PR open 触发） | ✅ | ✅ | 需仓库设置开启 |
| **`codex cloud exec --env <ENV_ID>`** | ✅（experimental） | ✅ | **本机 CLI 0.162.0 实测存在**；`exec/list/status/apply/diff`；**需 OpenAI 出口** |
| `openai/codex-action@v1`（GitHub Actions） | ✅ | ✅ | 跑在 **GitHub 网络**，绕过本机封锁；走 **API key** 计费 |
| **公开 REST API 创建云任务** | ❌ **不存在** | — | 官方无；社区 feature request 仍开放 |

**本机 CLI 实测（`/opt/nana_codex`，@openai/codex 0.162.0）**：
- `codex cloud --help` → 有 `exec/status/list/apply/diff`（标 `[EXPERIMENTAL]`）。
- `codex doctor` → `✗ auth 无凭据` + `✗ reachability 端点不可达` + `⚠ websocket 超时`。
- **即：CLI 侧「提交云任务」的能力真实存在，但被本机 OpenAI 出口封锁挡住，不能用。**

**结论（不假设、不夸大）**：
- ❌ **不能**把「@codex Issue/PR 自动触发」当成可靠闭环——官方文档明列，但社区有确定性 bug：私有库非 review 的 @codex 评论会报 *"create an environment for this repo"*（openai/codex #20093）；短时间多条 @codex 会被忽略（#13701）。**须实测。**
- ✅ @codex **不是**唯一非 UI 方式。另有 **`codex cloud exec`（CLI）** 与 **`codex-action@v1`（GitHub Actions）**。
- ⚠️ 因本机 OpenAI 出口不可达，**唯一不依赖本机网络的确定性路径 = GitHub 侧事件**（@codex 评论 / codex-action）。两者都需先连仓库。

---

## 七、姐姐的一次性集中操作（仅两件）

| # | 姐姐操作 | 奈奈用途 |
|---|---|---|
| **A** | 创建**只限 `xuni7-ui/nana-core` 单仓库**的 Fine-grained PAT（Contents: RW · Issues: RW · Pull requests: RW · Metadata: R 自动），**放到服务器** `/root/.nana_secrets/github_nana_core_pat`（chmod 600，**不要发聊天**） | 只读 fetch + 首次 push + 发 @codex + 读 PR |
| **B** | 在 ChatGPT(Plus) → Codex 里**连接 GitHub 仓库 `nana-core`**，建一个 environment | 让 Codex Cloud 认识该库，@codex 才有效 |

> PAT 隔离：存 `/root/.nana_secrets/`（在仓库外），奈奈用**仅限该 repo 的 scoped credential helper** 读取；**不进源码、不进日志、不进回执**；可随时撤销。

---

## 八、授权后奈奈自动执行（不需再问）

1. 只读 `ls-remote`+`fetch` → 报远端真实内容与 README 归属。
2. 提交**首次 push 的精确清单 + 目标分支**，请姐姐最终确认一次（遵姐姐「完成检查后再申请」）。
3. 确认后 push → 发 `@codex` 最小任务 issue → 观察是否真触发（👀 反应 / 回复 / PR）。
4. 真实 Codex 执行 → 开 PR → 奈奈读 diff + **本地独立复跑测试** → 验收。
5. 若 @codex 不稳定 → 报阻塞，备选 `openai/codex-action@v1`（**不自研桥**）。

---

## 九、复现 / 元信息

- 采集方式：只读（`git log/ls-files/rev-list/grep`、`codex --help/doctor`、`curl`）。生产改动 0，未 push，无新凭据。
- 全历史扫描：`for c in $(git rev-list --all); do git grep -IE "$VALPAT" "$c"; done` → 0 命中。
- CLI：`/opt/nana_codex/node_modules/.bin/codex` v0.162.0（nobody 拥有，DeepSeek provider）。
