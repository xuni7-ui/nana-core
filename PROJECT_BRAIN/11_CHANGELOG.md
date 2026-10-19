# PROJECT_BRAIN / 11 CHANGELOG（变更日志）

> 创建：2026-10-10 ｜ 状态：**新建（P2）**
> **规则**：每次改动**必须**三条齐全 —— **改了什么 / 为什么 / 怎么验证**。缺一条视为未记录。
> 编号格式：`C-0NN`。**只增不改**。

---

## C-001 · P1 事实口径修正 + 证据四档重构

- **改了什么**
  1. `01_architecture.md`：插件数 **25 → 23**；第三方插件 **20 → 19**；新增「P1 口径修正」小节与「进程可观测性受限」条目。
  2. `05_third_party_licenses.md`：标题 **25 → 23**，并附计数口径说明（24 条目 = 23 插件 + 1 个 `data/` 目录）。
  3. `docs/migration_report_20261010.md`：外挂脚本 **~2311 行 → 10 文件 / 2681 行**（注明 2311 为核心 5 文件之和）；复制文件数 25 → 22。
  4. `04_verification_status.md`：**全文重构**为「已实现 / 已测试 / 已运行验收 / 未知」四档，旧稿"已验证"措辞按降级规则作废。
- **为什么**：姐姐裁决第 4 条要求证据分档；实测发现原稿三处计数错误、一处证据链不严谨。
- **怎么验证**（全部只读，可复现）
  - `ls -1 /AstrBot/data/plugins/ | wc -l` → `24`（23 插件 + `data`）
  - `ls -1 /root/nana_dev/nana-core/src/bili_agent/*.py | wc -l` → `10`
  - `wc -l src/bili_agent/*.py | tail -1` → `2681`
  - 事件泵存活证据：`action_ledger/ledger.json` → `bili_event_pump_last_poll.state=OK`
- **影响文件**：4 个（+ 新增本文件）

---

## C-002 · P2 项目账本建设 + 本地版本控制

- **改了什么**
  1. 新增 `07_ROADMAP.md`（六条主线 + "不做"清单）
  2. 新增 `08_TASKS.md`（任务清单 + 6 项真正阻塞）
  3. 新增 `09_STATE.md`（当前快照 + 锚点哈希）
  4. 新增 `10_DECISIONS.md`（D-001 ~ D-019）
  5. 新增 `11_CHANGELOG.md`（本文件）
  6. `00_INDEX.md` / `README.md` / `AGENTS.md` / `upload_whitelist.md` 同步更新
  7. `git init` + 本地提交（**仅本地，无 push**）
- **为什么**：`06_open_risks.md` 曾登记"**账本缺失**"（无 ROADMAP/TASKS/STATE/DECISIONS/CHANGELOG）与 **B4 无版本追溯**；本条目补洞。
- **怎么验证**
  - `ls PROJECT_BRAIN/` → 12 个文件
  - `git log --oneline` → 本地提交存在
  - `git status` → 工作区干净
- **影响文件**：+5 新增，4 修改

---

## C-003 · 指纹自指问题处理

- **改了什么**：`manifests/fingerprints_20261010.md` 剔除**自身条目**（自指哈希不可满足），改为**外置锚点**：指纹表自身 SHA256 记录于 `09_STATE.md`。
- **为什么**：原表把自己也列入，导致"43 个文件仅 42 个一致"——**这是方法论缺陷，不是文件损坏**。文件无法包含自身的哈希。
- **怎么验证**
  - `sha256sum manifests/fingerprints_20261010.md` 与 `09_STATE.md` 记录值比对
  - 表内条目数 = 仓库文件数 − 1
- **影响文件**：1 个

---

## C-004 · 本地基线提交（anchor）

- **改了什么**：把 C-001 ~ C-003 的结果固化为本地 Git 提交。
- **提交 SHA**：`26ef7af520ed8ea88ba0270c4f384ebfcb0f145b`（提交 #1，49 文件）
- **为什么**：姐姐 D-015 授权范围内的"可恢复点"要求（L1 级）。
- **怎么验证**：`git log --oneline` / `git show --stat HEAD`
- **边界**：**无 remote、无 push、无上传**。

---

## C-005 · 锚点回填 + 指纹刷新

- **改了什么**
  1. `09_STATE.md` §七 回填基线提交 SHA + 记录"无 remote"
  2. `manifests/fingerprints_20261010.md` 重新采集（因 09/11 变更后需与工作区对齐）
- **为什么**：指纹是**采集时刻**快照；锚点回填改变了 `09`/`11`，故必须**重出指纹**，否则表与工作区不一致。
- **怎么验证**
  - `git status` → 干净
  - 表内条目数 = 仓库文件数 − 1
  - 生产侧 14 个 Iris 文件：与 01:5x 采集**逐条一致**（`[实测]` 本次复核，**零漂移**）
- **边界**：本提交后**不再改动**任何文件，指纹表即为最终基线。

---

## C-006 · 协作桥最小闭环（新增 `bridge/`）

- **改了什么**
  1. 新增 `bridge/codex_bridge.py`：`TaskSpec → 隔离克隆 → Runner → 边界校验 + 验收命令 → 回执 JSON`；
     硬黑名单在 `allow_paths` 之前生效；源仓只读（`git clone --no-hardlinks`）。
  2. 新增 `bridge/local_runner.py`：`LocalLLMRunner`（用**已装** openai SDK + 注入的兼容端点编码）；
     上下文采集**永不外发**硬黑名单文件；模型越界编辑**整体拒绝**。
  3. 新增 `bridge/test_codex_bridge.py`（T1–T9）、`bridge/test_local_runner.py`（T1–T6）、`bridge/README.md`。
  4. `.gitignore` 增加 `bridge/scratch/`、`bridge/receipts/`。
- **为什么**：D-020 要求"奈奈做统筹与验收、Runner 做编码"的真实链路；本轮把**机制**打通并证明。
- **怎么验证**
  - `python3 bridge/test_codex_bridge.py` → **9/9**
  - `python3 bridge/test_local_runner.py` → **6/6**（含 127.0.0.1 真实 HTTP 闭环）
  - `python3 bridge/codex_bridge.py --selftest` → happy=applied / violation=拒绝
  - 关键不变式：**源仓逐字节未变**（T6 哈希断言）
- **边界**：`codex` **未安装**（`codex_available=false`）；真实外部端点**未启用**（待 D-023 授权）。

---

## C-007 · C.5-V-1 视频视觉接线适配层

- **改了什么**
  1. 新增 `src/bili_agent/c5v_wiring.py`：BVID →（yt-dlp）本地视频 → c5v 抽帧+视觉 → 结构化事实 → 可注入文本；
     默认**关闭**；失败**逐字节还原**原文；预算含时长/帧数/超时/清理。
  2. 新增 `src/bili_agent/test_c5v_wiring.py`（T1–T9）；新增 `docs/c5v_wiring_design.md`（含 A/B/C/D 方案比较）。
- **为什么**：首个真实协作任务（D-023）；且需在无授权期先把"可验证、可回滚"的部分做完，不阻塞主线。
- **怎么验证**：`python3 src/bili_agent/test_c5v_wiring.py` → **11/11**；测试视频由 `ffmpeg lavfi` 现造，**全程零公网请求**。
- **边界**：**未接生产**；生产接线见 `docs/c5v_wiring_design.md` §5（L4，待授权）。

---

## 待记（本轮未做，登记备查）

| 项 | 为什么没做 |
|---|---|
| C.4 端到端验收 | 需姐姐按"跑验收"级授权 |
| `p0_coref_backtrace` 复核 | 待办 T-23，只读可做，未排入本轮 |
| 自制插件 LICENSE | 需姐姐决策（T-42） |
| Codex 桥 `@codex` 实测 | 只读验证范围，未实测 |

---

## C-008 · 首次真实协作跑测（R2）+ 修掉协作桥身份 bug

- **改了什么**
  1. `bridge/codex_bridge.py`：`main()` 新增 `--runner {codex,local_llm}`（默认仍 `codex`，未显式指定绝不联网）；
     新增 `sys.modules` 别名根修 + `execute_task` 类型转换纵深防御；回执新增 `endpoint{runner,model,base_url,calls,max_calls,prompt_bytes,usage,is_codex_cli}`。
  2. `bridge/local_runner.py`：新增 `max_calls` 请求次数**硬闸门**（超限拒绝外发）、`last_usage` 用量采证；
     `from_env()` 支持 `NANA_BRIDGE_MAX_CALLS/MAX_FILES/MAX_BYTES`。
  3. `bridge/test_local_runner.py`：新增 T7（CLI 子进程回归身份 bug）/ T8（请求上限闸门）/ T9（usage）。
  4. `bridge/tasks/c5v_real_01.json`：首个真实任务的 TaskSpec（`allow_paths` 收窄为精确两文件）。
  5. 新增 `PROJECT_BRAIN/12_REAL_COLLAB_RUN_01.md`：完整证据。
- **为什么**：姐姐一次性授权"首次真实模型端点协作测试"，需验证 奈奈派单 → 真实端点接收 → 返回代码 → 白名单校验 → 测试 → 验收 全链路。
- **怎么验证**
  - 离线：`test_codex_bridge.py` **9/9** + `test_local_runner.py` **9/9** + `--selftest` rc=0（合计 **18/18 全绿**）。
  - 真实：`--spec tasks/c5v_real_01.json --runner local_llm` → `ok=true, applied=true`，验收命令 **13/13**，
    `usage` 输入 5,953 / 输出 12,438；`violations=[]`。
  - 源仓零改动：两目标文件 `sha256` 与 `git HEAD` **逐字节一致**；源仓原测试独立复跑 **11/11**。
  - 独立行为探针：`cache_dir` 命中时间谍 fetcher **0** 次调用、未命中 1 次、不传参数旧行为保持。
- **抓到的真 bug**：脚本运行时 `__main__` 与 `codex_bridge` 存在**两份 RunnerResult** → `isinstance` 恒假 →
  模型结果被静默判否（离线测试因模块导入路径不同而漏检）。已根修 + 加回归 T7。
- **成本**：3 次请求（1 探针 + 1 实跑 + 1 修复后 bounded 重试）· 输入 11,940 / 输出 25,734 tokens ≈ **¥0.2~0.7**（单价未核实）。
- **边界**：生产改动 **0**；未装依赖、未加 remote、未 push、未重启；`receipts/`+`scratch/` 为可删运行时产物。
- **影响文件**：`bridge/` 4 个 + `PROJECT_BRAIN/12` + 本次账本更新

## C-009 · Codex CLI 真实执行验证（自定义 Provider · 单次最小任务）

- **改了什么**
  1. 新增 `PROJECT_BRAIN/14_CODEX_CLI_REAL_EXEC_01.md`（证据：版本核验 / 沙箱约束 / 真实执行记录 / 成本 / 缺口 / 可复现命令 / 回滚）。
  2. 新增 `bridge/probes/codex_cli_probe.py` 与 `codex_cli_probe_sandboxed_fail.py`（探针脚本，**不含任何明文凭据**）。
  3. 更新 `09_STATE.md`：新增「Codex CLI 真实执行」状态行与沙箱约束事实。
- **为什么**
  姐姐授权做 Codex CLI 自定义 Provider 最小真实验证；需把「协议可行性 + 沙箱约束 + 真实执行结果」固化为工程事实，避免以后重复踩坑。
- **怎么验证**
  - `--strict-config` 实跑证明 `wire_api="chat"` 已被移除、仅支持 `responses`（CLI 原文报错）。
  - `POST https://api.deepseek.com/v1/responses` → 200（真钥匙）/ 401（假钥匙），证明协议握手成立。
  - 降权（`nobody`）实跑一次：真实落盘 `calc.py`/`test_calc.py`，真实执行 `python3 test_calc.py` → rc=0 `all tests passed`；奈奈独立复跑一致。
  - 凭据落盘扫描：`CODEX_HOME` 内**无**凭据（只报结论，不输出内容）。
- **边界**：生产改动 0、无 push、无新密钥、无全局安装。

## C-010 · R5 · OpenAI 官方出口只读体检（结论：不可达）

- **改了什么**
  1. 新增 `PROJECT_BRAIN/15_OPENAI_EGRESS_PROBE.md`（DNS/裸 TCP/TLS-SNI/对照组/代理排查 全套只读证据 + 阻塞点定性 + Cloud 替代路径评估）。
  2. 更新 `09_STATE.md`：补 R5 结论与「官方 OpenAI 出口」状态行。
- **为什么**
  姐姐追加指令：先只读确认是否存在可靠 OpenAI 出口、官方 ChatGPT 登录能否完成；不通则停止、不反复重试、不擅自部署代理。
- **怎么验证**（全部只读、可复现）
  - `getent ahostsv4 chatgpt.com` → `199.59.150.40`（非 CF 边缘 = 污染）；`172.64.146.15` 真实边缘裸 TCP ✅ 可连，但 `--resolve` 强制走真实边缘后 HTTPS **0.079s 立刻失败** → SNI 阻断。
  - `curl -o /dev/null -w %{http_code} https://auth.openai.com/` → **403**（TLS1.3 握手成功、证书 CN 有效 → 边缘拒绝）。
  - 对照组 `baidu/github/api.github/npmjs/deepseek` 全 ✅ → 本机出网正常，**非**本机网络故障。
  - `ss -ltnp` 空 + 无 `*_proxy` 环境变量 → 无现成代理可用。
- **结论**：B1 `chatgpt.com` SNI 阻断 ／ B2 `api.openai.com` 污染 ／ B3 `auth.openai.com` 403 ／ B4 无本地代理。**两条官方登录路径（网页授权 + device-auth）在本机均无法完成**；与 R3 实测一致，**按指令停止，未重试登录**。
- **边界**：只读。未安装、未登录、未部署代理、未索取任何凭据、生产改动 0、无 push。

---

## C-011 · R9 GitHub 首次推送 + 官方 Codex `@codex` 派单实测

- **改了什么**
  1. 新增 `PROJECT_BRAIN/19_GITHUB_FIRST_PUSH_AND_CODEX_DISPATCH_01.md`（首次 push 全证据 + `@codex` 触发面实测）。
  2. 本地历史重写：从**全部提交**中移除 `manifests/nana_iris_changes.diff`（根提交即在），11 提交全保留。
  3. 合并远端 `origin/main`（无关历史），合并提交 `e406127`。
  4. 首次 `git push -u origin master:main` 成功（**fast-forward，无 force**）。
- **为什么**
  姐姐指令「A，动手」：在已授权范围内把「奈奈 → 官方 Codex → 奈奈」真实闭环优先跑通，先推送再验 `@codex` 派单。
- **怎么验证**（只读 / 可复现）
  - `git rev-list --all --objects | grep -i nana_iris_changes` → **0 命中**（diff 已不在任何提交/对象）。
  - `GET /repos/xuni7-ui/nana-core/commits/main` → `e406127`；tree blob 数 = **67**；含 diff = **False**。
  - Issue #1：正文 `@codex` **无反应**；**评论** `@codex` → `chatgpt-codex-connector[bot]` **5 秒回复**。
- **边界**：未改生产、未自动合并 PR、未启用付费 API、未 `--force`、`diff` 未上远端。
- **阻塞**：该仓库在 Codex Cloud **尚未建 environment**（bot 明确提示）→ 闭环**待姐姐一步人工**。

---

## C-012 · 授权变更记录：姐姐批准 Git 推送 + `@codex` 派单 + PR 读取/复测/验收

- **改了什么**：记录姐姐本轮一次性集中授权范围（不影响任何文件内容）。
- **为什么**：把「姐姐退出日常传话」的授权边界固化为可追溯记录。
- **授权内容**：①现有 PAT 安全配置（600）；②合并本地/远端无关历史并保留双方 README 与全部提交；③按白名单正常 push、排除 `nana_iris_changes.diff`、禁 force；④推送后验证官方 Codex `@codex` 派单；⑤若 Codex 产 PR，由奈奈读取/复测/验收；⑥全程不改生产、不自动合并、不启用付费 API。
- **怎么验证**：见 C-011 及 `PROJECT_BRAIN/19_*.md`。

---

## C-013 · R10 Codex Cloud environment 阻塞复测（两次真实触发）

- **改了什么**：新增 `PROJECT_BRAIN/20_CODEX_ENV_BLOCKER_01.md`（Issue #1 两次 `@codex` 触发实测 + 只读诊断 + 姐姐侧核对清单）。
- **为什么**：姐姐「环境已建好」→ 按已授权第 4 条真实验证 `@codex` 派单闭环。
- **怎么验证**
  - `POST /issues/1/comments`（id 6088873418 → bot 04:39:29 回复；id 6088919356 → bot 04:42:42 回复，间隔 ~120s 排除传播延迟）。
  - timeline 两次均出现 `mentioned(codex)`；bot 回复恒定 = `create an environment for this repo`。
  - `branches=['main']`、`pulls?state=all=[]` → **无分支、无 PR**。
- **结论**：触发链路 ✅ 正常；**卡点 = Codex Cloud 侧未把 `xuni7-ui/nana-core` 关联到 environment**。
- **补充结论**：阻塞**与「本机离线」无关**（Codex Cloud 执行在 OpenAI 云端；本机仅需只读 GitHub API，已通）。
- **边界**：生产零改动、代码零改动、无 PR、无 force、无付费 API。

---

## C-014 · R11 Codex Cloud 阻塞 · 第三次触发复测 + 三层故障切分

- **改了什么**：新增 `PROJECT_BRAIN/21_CODEX_ENV_BLOCKER_RECHECK_01.md`；本文件追加本条。
- **为什么**：姐姐「妹妹开跑」→ 在已授权范围内对 `@codex` 闭环做**第 3 次触发 + 只读复测**，并把故障切成三层固定口径。
- **怎么验证**（只读 / 可复现）
  - 第 3 次触发：Issue #1 评论 `6089144686`（`20:58:26Z`）→ bot `20:58:32Z`（6 秒）同句回复。
  - `branches=['main'@a9b1d36]`、`pulls?state=all=[]`、HEAD 自 R10 **未变**。
  - `GET /repos/.../installation` → 401；`GET /user/installations` → 403（细粒度 PAT 权限边界，**非异常**）。
- **新增判据**：bot 恒 4～6 秒回复 ⇒ App 已安装 / 事件已投递 / OpenAI 已受理 ⇒ **排除「App 未装」，收窄到「环境查找」**。
- **撤销**：①「私有环境只对创建者可见」推测（无官方证据，降级待核实）；②「草稿未发布即根因」（被新证据推翻）。
- **结论**：L-C 入口链路 ✅ / 环境发现 ❌；**唯一未闭环一步 = 姐姐侧 Codex 界面新任务**；**停止重复评论**，必要时打包交 OpenAI 支持。
- **边界**：生产零改动、代码零改动、无 PR、无 force、无付费 API、仓库侧零写入。

---

## C-015 · R12 T-001 三项只读前置核验 + 首个真实 Codex 任务卡出卡

- **改了什么**：新增 `PROJECT_BRAIN/22_PRE_T001_READONLY_RECON_01.md`、`docs/tasks/T-001-c5v1-wiring-increment.md`；本文件追加本条；`08_TASKS.md` 增 T-47 行。
- **为什么**：姐姐授权（口令「动手」）核验 T-001 前置三项，并在无新重大风险时**直接制定首个最小可验收的 C.5-V-1 开发任务卡**。
- **怎么验证**（只读命令，可复现）
  - ① `git merge-base --is-ancestor a314c4c a9b1d36` → **exit=0（是祖先）**；`git log --oneline a314c4c..a9b1d36 | wc -l` → **1**；无分叉，对齐 = 纯快进。
  - ② `git ls-tree -r --name-only a9b1d36` → **含** `src/bili_agent/c5v_wiring.py`、`src/bili_agent/test_c5v_wiring.py`、`src/c5v/bili_video_vision.py`；**无 `tests/` 目录**。
  - ③ 测试实测：`python -m pytest src/bili_agent/test_c5v_wiring.py -q` → **no tests ran**；`python3 src/bili_agent/test_c5v_wiring.py` → **11 通过 / 0 失败**。⇒ 正确测试命令为后者。
  - ④ 服务器凭据面：`gh`/`codex` 未装；`GITHUB_TOKEN`、`~/.git-credentials`、`~/.config/gh`、`~/.ssh` **全无**。
  - ⑤ `git ls-remote origin` → **超时（退出码 124）**；`github.com` git 端点 curl **rc=28**；`api.github.com` **200**。⇒ **git-over-HTTPS 端点本轮不通**，远端真身**未复核**（不猜）。
- **修正两条旧口径**：
  1. 「在 `a314c4c` 上开发会把 main 往回退」→ 精确化为「PR diff 会出现 a9b1d36 的**逆向差异**」；**处理结论不变：一律从 `origin/main` 起分支**。
  2. 任务卡的测试命令由 `python -m pytest tests/ -k c5v -q` **改为** `python3 src/bili_agent/test_c5v_wiring.py`（仓库无 `tests/`，且该文件是自跑脚本）。
- **结论**：`a314c4c`→`a9b1d36` 线性 1 提交、无冲突风险；**origin/main 已含 C.5-V-1 全部源码与测试**；Codex 有源可改。无新重大风险 ⇒ **按授权出卡 T-001**。
- **边界**：只读核验；生产零改动、代码零改动、无 push、无 PR、未建/改环境、未发 `@codex` 评论、未联网安装。仅新增两份文档并**本地**提交。

---

## C-016 · R13/R14 T-41 协作桥真实 Runner 启用 + 首个真实协作执行

- **改了什么**：`bridge/codex_bridge.py`（`CodexRunner` 重写、`wrap_test_command()`、`redact()`、`_first_key()`、`SCRATCH_ROOT` 可外置、`--dry-run`）；新增 `PROJECT_BRAIN/23_T41_REAL_RUNNER_01.md`；`08_TASKS.md` T-41/T-47 置 DONE、BL-7 解除；本文件追加本条。**生产代码零改动。**
- **为什么**：姐姐授权（口令「动手」）走 **A+B 接力**中的 B（主机 Codex CLI）。原桥的 `CodexRunner` 只调 PATH 上的 `codex`（不在 PATH）且无降权/无严格配置，实测不可用。
- **怎么验证**（可复现）
  1. 离线回归：`python3 test_codex_bridge.py` → **9/9**；`python3 test_local_runner.py` → **9/9**；`--selftest` 通过；`codex_available=true`。
  2. dry-run：`NANA_BRIDGE_SCRATCH_ROOT=/opt/nana_codex/sandbox/bridge python3 codex_bridge.py --spec tasks/c5v_real_01.json --dry-run` → 命令形状正确（`setpriv`→`nobody`→`env CODEX_HOME`→`node codex.js exec --strict-config --json …`），密钥 `key_present=true` 且**打码**。
  3. 真跑：`… --runner codex` → `ok=True / applied=True / test_ok=True / duration_s=52.395`，`changed_files` = `src/bili_agent/c5v_wiring.py`、`src/bili_agent/test_c5v_wiring.py`，`violations=[]`，`diff_stat` = **2 files changed, 70 insertions(+), 4 deletions(-)**。
  4. 独立验收（奈奈不信模型自述）：本机复跑 `python3 src/bili_agent/test_c5v_wiring.py` → **13 通过 / 0 失败**；顶层仅标准库；无硬编码密钥；源仓 HEAD 未变。
- **修掉的三个真实缺陷/漏洞（含两次失败留证）**
  1. **stdin 未关闭 → 300s 假超时**：codex 0.162 在 stdin 非 TTY 时读 stdin 到 EOF，继承永不关闭的管道即死等。探针：修前 `rc=124`、stdout 0 字节；修后 **0.27s** 明确报缺失环境变量。修法：`stdin=subprocess.DEVNULL`。
  2. **key 取错 → 401**：AstrBot `provider_sources[].key` 是**列表**，`str()` 得到 `"['sk-…']"`。端点回显 `****e8']` 暴露。修法：`_first_key()` 归一化。
  3. **验收阶段以 root 执行模型产物 → 沙箱被绕过**：新增 `wrap_test_command()`，验收同权限同隔离。
- **结论**：B 路线**已真正打通**，桥具备「隔离克隆 → 降权执行 → 边界校验 → 同权限验收 → 回执」的完整可用闭环。首个真实协作任务 M2：**通过**。
- **残留**：R-1 模型元数据缺失告警（上下文 fallback，`[未核实]`）；R-2 无逐次成本熔断台账；R-3 `/opt/nana_codex` 不在 git 内，容器重建需重做。
- **边界**：生产零改动、无 push、无 PR、零新依赖、零新密钥；密钥仅运行期内存注入，回执已脱敏自查（`sk-`/`****` 痕迹 = 0）。


---

## C-016 工程基线收口（2026-10-10（CST））

- **改了什么**：新增 AstrBot 补丁、Iris 隔离材料、B站纳入/排除、`requirements.txt`、`LICENSES_AND_PROVENANCE.md`、`docs/bridge_node_rebuild.md`、`PROJECT_BRAIN/24_*`，并更正 `00/02/03/04/05/06/08/10`。
- **为什么**：建立可审查、可复现的工程基线，供 GPT-6.1 Sol 全面盘点。
- **怎么验证**：两套补丁 `git apply --check` + 往返 sha256 一致；上游 blob 全量比对；敏感值级扫描；远端 HEAD 回验。
- **边界**：生产零改动、无重启、无部署、无付费任务、非强制推送。


## C-017 收口同步完成（2026-10-10）

- **远端完整 HEAD**：`86484be9d3cc9dd7ca850d804b13fbf10d67ff2e`（fast-forward：`ff1c870..86484be`，无 force）。
- **验证**：`git ls-remote` + 鉴权 `api.github.com/repos/xuni7-ui/nana-core/commits/main` 双路一致；根目录新增 `materials/ patches/ requirements.txt LICENSES_AND_PROVENANCE.md`。
- **推送文件**：34 个（+7198 行）。
- **敏感**：预提交全量扫描零真值凭据。
- **边界**：生产零改动、无重启、无部署、无付费任务。


## C-018 Nana Core V1 S0（独立开发分支）
- **改了什么**：[实测] 新建独立包、严格 DTO、受限模型/策略契约、UTC Clock、隔离测试入口。
- **为什么**：执行用户本轮 S0—S4 开发授权；不接入生产，先建立可运行契约。
- **怎么验证**：`.venv/bin/python -m pytest -m s0`：8 passed；Python 3.12.14 / SQLite 3.53.1 / Pydantic 2.13.4。
- **回滚点**：基线 `18bc736d5e37fe3325e514a0e975403df2f97c9f`，tree `e0dae642fc21b973a00e992054eb6d2e45230745`；开发分支 `dev/nana-core-v1-s0-s4`。
- **边界**：只安装开发 pytest；无付费模型、无生产调用。S1—S4 尚未完成。


## C-019 Nana Core V1 S1
- **改了什么**：[实测] 新建 schema v1、单实例锁、事务事件入口、完整证据、身份恢复、来源去重、纯投影回放及备份隔离标记。
- **为什么**：原始证据、时间与稳定身份必须独立于宿主和模型。仅建当前实验需要的表；事件内记录投影变更，回放不重跑模型。
- **怎么验证**：`.venv/bin/python -m pytest -m s1`：5 passed（时间/身份/去重、回滚、损坏库拒绝、纯回放）。
- **边界**：schema 中后续实验的动作表尚无执行逻辑；不声称 S2 完成。


## C-020 Nana Core V1 S2
- **改了什么**：[实测] 本地 Operator 授权入口、精确范围 Grant、预算预留、动作/尝试状态机、独立 fake_world、读取核验、未知恢复、备份隔离。
- **为什么**：外部提交与本地回执之间没有共同事务，必须保留未知并查询恢复，预算不能按成功退回。
- **怎么验证**：`.venv/bin/python -m pytest -m s2`：12 passed；两种真实子进程 SIGKILL（派发后调用前、外部提交后回执前）均通过恢复断言。
- **最小修正**：Attempt 增加 EXECUTE/VERIFY 类型，核验同样有动作关联、授权和请求/模拟成本预算。第一阶段写动作 max_attempts=1，确认未生效后也不自动重试。
- **边界**：所有资金仅为 fake 预算单位，不产生真实费用；真实模型及平台未接入。


## C-021 Nana Core V1 S3
- **改了什么**：[实测] 单 reading_card 目标、ModelPort 工程夹具、严格计划校验、顺序执行、独立核验完成条件、自传片段、持久化唤醒。
- **为什么**：先跑通事件→记忆→目标→计划→授权→行动→验证，模型不拥有动作状态写入权。
- **怎么验证**：`.venv/bin/python -m pytest -m s3`：6 passed；100 次重复输入只创建一张卡片；长消息上下文标记 EXCERPT 且原文完整；定时唤醒不自动记为目标。
- **边界**：夹具是规则式工程 ModelPort，不是 LLM；不声称跨模型语义验证。


## C-022 Nana Core V1 S4
- **改了什么**：[实测] 可信本地反馈入口、缺失字段到能力输出的候选归纳、受限策略验证/启用、计划前后差异、撤回与窄范围经验。
- **为什么**：经验必须影响后续真实读取，不能只是把反馈附到提示词；学习不能授予新增步骤的权限。
- **怎么验证**：`.venv/bin/python -m pytest -m s4`：10 passed；新增定位步骤实际执行；移除策略编译结果有差异；未授权定位时仍被拦截；反馈撤回停用经验。
- **边界**：使用结构化反馈 requested_fields；自由文本只保存证据，不声称已实现通用自然语言经验归纳。完整独立进程实验与统一 E01—E20 报告仍待生成。


## C-023 Nana Core V1 S0—S4 统一交付验收
- **改了什么**：[实测] 独立进程实验 CLI、匹配状态消融、SIGKILL 证据、实际测试驱动 E01—E20 矩阵、完整依赖锁与 source 指纹、独立包构建。
- **为什么**：验证持久化经验确实造成计划与行为差异，避免用夹具切换冒充 S5；补齐未知动作、旧备份/回放隔离及时间回退边界。
- **怎么验证**：`.venv/bin/python -m pytest tests/offline_continuity --acceptance-report docs/nana_core_v1_evidence --junitxml=docs/nana_core_v1_evidence/junit.xml`：56 passed / 0 failed / 1 skipped；`nana-offline --seed 29` 在独立工作目录运行；wheel 只含 Core 和 schema。
- **真实故障**：派发前、外部提交后、完整目标卡片阶段的 SIGKILL；恢复不重发，已有计划不重跑模型。
- **消融**：原身份/授权/预算/模型提议匹配，只停用策略；有经验定位调用=1，无经验=0，两组卡片总数=2。
- **修正记录**：回放/备份带本地恢复隔离标记；投影比较仅允许该标记差异，其他字段完整比较；授权时间采用高水位，回退不复活过期权限；证据失效暂停策略。
- **测试入口问题**：第一次报告命令未显式提供实验测试目录，pytest 在测试收集前 usage exit 4；修正命令后全量执行通过，没有把失败测试标为通过。
- **范围**：S0—S4 完成；E12/S5 明确跳过；S6 未实施；生产零调用、无付费模型、无部署或合并。


## C-024 最终 ModelPort 身份上下文核对
- **改了什么**：ModelRequest 增加 identity_snapshot，ContextBuilder 传递持久化人格/价值内容，而不只传身份 ID 和版本。
- **为什么**：补齐 Architecture V1 的身份快照契约；不能把状态恢复缩减为仅恢复名称或 UUID。
- **怎么验证**：重启测试直接比较请求中的身份内容与持久化身份；完整复验 56 passed / 0 failed / 1 skipped；独立进程/消融/SIGKILL 证据重新生成。
- **边界**：S0—S4 契约修正，不执行真实模型语义或 S5；指纹锚点同步更新。


## C-025 保存 S0—S4 到私有 GitHub（2026-10-10）
- 改了什么：[实测] 将用户指定的 `dev/nana-core-v1-s0-s4` 推送到 `xuni7-ui/nana-core`；未 force、未合并。
- 为什么：本轮用户明确授权保存阶段成果。
- 怎么验证：HEAD=`884db6a460c2803e8c89434c3fa8e36f7ffe90cf`，工作区干净；24 个指纹与 45 个增量白名单文件一致；逐个历史增量版本凭据模式扫描 0；56 pass/0 fail/1 skip 记录与 E12 NOT_RUN 一致；原创许可待定、未复制 AGPL 模块进入 Core。
- 远端回验：git ls-remote 开发分支完整 SHA 一致；main 保持 `18bc736d5e37fe3325e514a0e975403df2f97c9f`。

## C-026 S5 工程实现与语义阻塞报告（2026-10-10）
- 改了什么：[实测] 新增 semantic 包、严格开发端点配置、预算持久账本、兼容 HTTP ModelPort、冻结 S4 合成历史、4 个留出案例、顺序评估/消融与 CLI；新增测试/证据/报告；只更新旧 E12 跳过理由，未改断言。
- 为什么：真实双模型需要相同身份与历史以及独立语义/行为证据；没有端点也应交付可执行评估线路。
- 怎么验证：新增 42 pass；联合 98 pass / 0 fail / 1 skip；真实账本 SIGKILL 后不继续调用；16 个独立顺序工程进程，所有测试行为断言成立。
- 修复：首次联合运行发生 4 个收集错误（无命名空间 conftest 冲突），给 S5 测试加包/相对导入后完整重跑通过；初始错误留档。
- 当前环境：[实测] readiness 无配置模型绑定；没有复用历史生产 DeepSeek。nana-semantic 默认空配置实际执行，E12/semantic_gate=NOT_RUN，真实模型调用 0、费用 0。
- 边界：Core schema、旧生产源码、生产依赖未改；不调用生产、无私人夹具、不安装新依赖/买服务，不实现 S6。
- 证据：docs/nana_core_s5_implementation.md、docs/nana_core_s5_evidence/；指纹锚点见 09_STATE。


## C-027 S5 私有分支保存回验
- 改了什么：[实测] 推送 `dev/nana-core-v1-s5`，随后追加本条和合成工程保存回执，无源码改动。
- 为什么：交付可审查的 S5 工程，保留已保存 S0—S4 分支，不影响 main。
- 怎么验证：GitHub 元数据 visibility=private；git ls-remote S5=`881e48a863257971e29a49f48ab8ec403313c3fa`，S0—S4=`884db6a460c2803e8c89434c3fa8e36f7ffe90cf`，main=`18bc736d5e37fe3325e514a0e975403df2f97c9f`。
- 工程结果不变：42 个新增测试通过，联合 98 pass / 1 skip；真实模型 0，E12 NOT_RUN，费用 0。证据 docs/nana_core_s5_evidence/github_save_receipt.json。


## C-028 S6 合成旧记忆导入
- 改了什么：新增 migration.legacy 严格合成来源信封、显式时间单位、精确原文保存、逐记录事务导入/去重/冲突拒绝、恢复与回放测试；不新增 Core 表。
- 为什么：保留旧来源且不把推断、摘要或旧 VERIFIED 声明提升成可信事实/执行证据。
- 怎么验证：tests/migration 14 passed，包括真实 SIGKILL 部分导入后恢复、身份和来源保持、纯回放。首次 14 failed，原因是有限浮点约束误施于含字符串的时间联合类型；修正为只约束 float 后全部通过，未削弱断言。
- 边界：全合成，无生产导出/数据库读取、真实模型 0，E12 NOT_RUN。


## C-029 S6 影子与单一执行权闭环
- 改了什么：新增无执行接口的 ShadowObserver、闭合 CapabilityRouter、持久 owner epoch/路由幂等标记；复用 Core 授权/预算/恢复，直接路由也检查授权及已消耗尝试预算。ContextBuilder 新增只读校验选项，默认行为不变。
- 为什么：旧模拟执行方持续执行业务时，Core 影子只能记录差异；不允许双执行，未决禁止换主，旧绑定在 epoch 切换后失效。
- 怎么验证：S6 27 passed；影子零能力调用、重复观察不重复目标/副作用、竞争方与旧绑定拒绝、授权临界过期拒绝、预算证据检查、恢复隔离、真实 SIGKILL 路由恢复一张卡片/一次写调用。
- 修复：首次影子批次 2 failed；规范化首次/重复返回的 JSON 结构，未授权调用测试改为构造实际攻击输入（原辅助方法已在 DTO 层拒绝空 attempt），保持原安全断言。
- 边界：仅模拟执行方，不接生产；handoff 仅合成实验；不解除备份 quarantine，不消费真实模型额度。


## C-030 S6 纵向 CLI 与统一回归
- 改了什么：新增 nana-migration CLI 和跨进程实验，导入→影子→模拟旧执行→反馈经验→重启合成换主→新行动→实际崩溃→核验恢复→完整回放；合成声明改为必须显式提供。
- 为什么：验证与真实旧宿主无关的迁移准备机制，并保留非生产边界；不等真实端点。
- 怎么验证：29 个 S6 tests；联合 127 pass / 0 fail / 1 skip；CLI 13 条检查成立；三张卡片/八次执行/八次核验；SIGKILL -9，恢复只查询、不调用模型重新规划；证据 docs/nana_core_s6_evidence/。
- 未验证：真实导出/格式兼容/宿主对账/旧未决接管/E12；不修改生产，不解除备份隔离，无额外费用/依赖。

## C-031 — S6 私有开发分支保存回执
- [实测] 改了什么：追加 docs/nana_core_s6_evidence/github_save_receipt.json、更新指纹锚点/复核清单和当前状态；不改源码。
- 为什么：记录已实际发生的推送与远端验证，区分实现提交和后续账本提交。
- 怎么验证：git push 成功；git ls-remote 的 S6 为 `14e5f2e71d209a2378290d7b591d932131ab28ba`，main/S0—S4/S5 保持原 SHA；既有 127 passed / 1 skipped，账本修改不重复运行测试。生产和 E12 未执行。
# C-032 — 只读权限核实与开发真实文件/HTTP 验证
- 改了什么：新增 src/nana_core/development/ 与 tests/development/、nana-development CLI；S5 service_kind 分类及 E12/费用统计；报告/合成证据/白名单/来源/指纹和 PROJECT_BRAIN 追加。
- 为什么：复用统一状态、身份、授权、预算、单执行方/核验，验证实际文件读取和真实 HTTP 协议；没有模型端点仍推进工程，避免将 wire 模拟器算作真实模型。
- [实测] 怎么验证：31 新测试全通过；联合 158 passed / 0 failed / 1 skipped；CLI 源文件 hash 未变，两张卡片无重复，经验实际增加定位；真实进程 SIGKILL 后身份相同，零重新执行/一次核验重读。证据 docs/nana_core_development_evidence/。
- 早期结果：文件工具/受影响 S5 65 passed；默认沙箱 23 passed / 7 failed（socket 创建 PermissionError），开发 network grant 下七项 wire tests 通过；一次未指定测试目录的自定义报告参数命令在解析阶段 exit 4，明确目录后运行。只读复核修正累计定位冒充经验效应，新增否定测试，无断言削弱。
- [实测/未知] 权限核实：生产连接/命令/变更 0；当前就绪 secrets/vars/identities 0；Docker socket 请求 PermissionError、阶段未记录；GitHub repo/workflows GET 成功（私有/0），hooks GET 403，webhooks/外部轮询未知。
- 真实模型推理、生产、公网工具调用与模型费用 0；E12 NOT_RUN。实际成功专项与最终 wire 运行各 8 个 loopback 请求，共 16，均 protocol simulator/unverified；不能宣称真实模型已验收。

## C-033 — P0 保存与 P1 模型适配收尾
- [实测] P0 保存：b05468d63182c17644037be447688798fa5ce6b4 已推送，ls-remote 相同；main 未变。上次代码/HTTP 测试/访问边界报告完整保留，不依赖未提供的截图。
- 改动与原因：HTTP 4xx 明确拒绝 FAILED，408/5xx/断连/截断 UNKNOWN；配置加载错误只输出安全代码，拒绝 symlink/超限配置；Endpoint 重新严格校验；已知开发 binding 原样回显在存储前拒绝。预算不退款、未决不重发，不修改生产。
- [实测] 验证：受影响 S5 与开发测试合计 81 passed；开发 39 passed；新增 8 项覆盖状态/截断/配置/凭据回显/变造端点。真实推理 0，E12 NOT_RUN；本阶段 12 个 loopback 请求，均协议模拟器，模型费用 0。最终全量回归留待后续阶段完成。

## C-034 — 网页单工具闭环
- 改了什么：PublicHTTPTransport、WebSourcePort、受控 HTTP 服务与测试；路由可选 development_public scope。P1 提交 0d13ecc8ed84ee9c0cd3e28b19cf0cfed00fe5db 已推送且 ls-remote 一致。
- 为什么：通过现有授权/预算/动作/核验接入固定 GET/HEAD，避免网页指令越权、SSRF 与恢复重复访问；不扩建 Core 框架。
- [实测] 怎么验证：84 targeted passed（开发 55、S6 29），证据 web_single_tests.json/web_single_output.txt；默认私网拒绝、DNS 一致性、代理/TLS 目标、超限/截止时间/redirect、Grant/owner/shadow/预算、历史回执/定位来源均验证。
- [实测] 公开 GET 仅尝试一次，DNS 阶段 WEB_TIMEOUT，HTTP/代理连接尝试均 0，UNKNOWN 不重试；public_web_attempt.json。真实模型 0、费用 0、E12 NOT_RUN，生产调用 0。公开运行验收未完成；P3/P4 待执行。

## C-035 — 来源证据、跨进程多工具与经验消融
- 改了什么：web_lab 纵向 CLI（观察→授权 GET→独立核验→来源卡片/引用结果→反馈→冻结两库→重启→经验/消融），真实 SIGKILL 及缺授权恢复分支；新增 6 测试，HEAD 明确 HEAD_NO_BODY 并核验。单工具 ccad1a2b9811eec853b4ecc908649ac3cc532de9 已推送/远端一致。
- 为什么：复用既有模板与 PlanCompiler，证明下游真正使用上游证据、经验实际改变行为，不能用计划文本或虚拟重启替代。
- [实测] 怎么验证：CLI 18 检查成立，5 实际 loopback GET；专项20 passed /0failed，14 实控请求（13 GET/1 HEAD）。SIGKILL -9 后 DISPATCHING→核验恢复，恢复 GET/模型提案0，所有动作 SUCCEEDED；缺locator授权保留read SUCCEEDED，goal BLOCKED，重启无重复GET/卡片。frozen两库hash相同，with1定位/without0定位，前置提案相同，授权未变化。
- 首轮新增HEAD断言误判UNKNOWN，已有完整外部查询正确证明NOT_APPLIED；修正精确断言，不削弱门槛。HEAD顶层coverage实际缺口已改并受测试约束。报告 docs/nana_core_web_validation.md、web_continuity_report.json、web_multitool_proof.json。
- 边界：工程夹具、合成loopback、fake notebook；真实模型0、费用0、E12 NOT_RUN；公网先前尝试UNKNOWN且不重试。Core schema/依赖不变，无生产变更。全量回归待执行。

## C-036 — 持续开发最终全量回归
- 改了什么：保存最终JUnit/工程结果/实际崩溃与wire proof/交付汇总，更新状态与开发/网页报告；源码无新增改动。
- 为什么：统一历史阶段口径，防止模拟器/loopback或工程夹具冒充公网、模型语义或生产能力。
- [实测] 怎么验证：全量228 collected，227 passed /0failed /0errors /1skipped（E12）；S0—S4 56、S5 42、S6 29、开发100。最终回归26 loopback HTTP（12协议POST、8网页GET+1HEAD、5多工具GET），独立CLI另5GET；公开一次DNS超时HTTP0，真实模型0/费用0。final_junit.xml/final_regression_output.txt/final_integration_proof.json/final_delivery.json。
- [实测] P3/P4 已保存远端 fced7f8204b82da03e6fc9d60fe73e29727c3d0c，ls-remote一致；最终检查点随后独立提交/推送，不合并main。敏感pattern/白名单/许可证复核、指纹更新；零依赖/Core schema变动。
- [未知] E12、公开proxy/TLS真实wire、生产SSH鉴权/未知卷/容器关联及webhook/外部自动部署；未触碰生产/私人资料/密钥，不以未发现代替绝对无权限。

## C-037 — Phase III 基线与单次公网验收
- 改了什么：从已验证29872608b7b82fcca4a89a3be98fda8e8c65337f建立dev/nana-core-v1-phase3-entry，新增现有公网传输阶段标记、单次完整Core探针及证据。
- 为什么：精确定位公网阻塞，不因普通网络失败误报能力，也不盲重试UNKNOWN。
- [实测] 怎么验证：本地/远端原HEAD一致，工作区干净；旧227/0/1证据保持。新42 targeted passed；实际一次DNS_FIRST超时，HTTP0/proxy连接0/read UNKNOWN/goal BLOCKED，独立核验与Attempt持久。未改系统网络/TLS/生产。

## C-038 — M2 真实模型就绪门
- 改了什么：只新增脱敏环境就绪与S5正式readiness证据，无模型适配新框架。
- 为什么：没有显式授权开发端点不能借用历史生产DeepSeek，也不能把当前助手或协议模拟器当E12。
- [实测] 怎么验证：environment_status current/spec33，secrets/vars/identities0；既有prepare/evaluate实际运行，snapshot unchanged，E12 NOT_RUN、calls0、models[]、token不适用、费用0。M1已保存远端4f51b5a385ac9a4673e1ba093b782b1ff840c023。继续不依赖端点的记忆任务。

## C-039 — M3 Iris真实结构映射与适配
- 改了什么：锁定上游源码证据manifest、正式11类schema字段映射；IrisAdapter复用LegacyImporter，原始与canonical两事务可恢复，14条synthetic真实字段夹具；不新增Core表。
- 为什么：不能从补丁/文档想象L2/L3/profile字段，也不能把旧VERIFIED/summary/action变成Core事实/执行；实测源adapter为FAISS+SQLite/L3 SQLite而非旧注释Chroma/Kuzu。
- [实测] 怎么验证：36 targeted passed（新7+S6 29），重复14duplicate，真实SIGKILL -9后1duplicate+13imported，来源/时间/身份保持、无Action/Grant/Strategy；拒绝记录完整batch evidence保留。首轮35pass/1fail为测试epoch常量误写2025，修正正确2026固定值未降断言。M2远端820e688b809dad7b22049ab699b86f211b813135一致。

## C-040 — M4 记忆冲突与迁移/影子对账
- 改了什么：MemoryView有界纯检索、最小claim信念projection；跨进程迁移/重启/replay/context/ModelPort工程fixture decision演习；old Iris-style lexical surrogate对比与真实对账报告。
- 为什么：新陈述不能销毁旧证据，summary/inference/旧confidence不升级；影子不写Goal/Action/Grant/Strategy。
- [实测] 怎么验证：10 targeted passed；CLI14导入/0拒绝、重启14duplicate、1KGrelation、1冲突组、identity/time/source/replay一致；source raw逐字对账；导入和preview没有动作/权限/预算。query重要证据recall surrogate0/Core1，矛盾可见0/2，shadow前后snapshot一致；fixture原始proposal实际引用当前否定陈述及memory ID。
- [未知] 真实模型理解、Iris真实embedding retrieval parity；后者PARTIAL只测纯surrogate，不部署。零依赖/新Core表。映射M3已保存ef51373570363ed715cb6eb0732365d4e611e86b。

## C-041 — M5 主动候选与价值冲突工程夹具
- 改了什么：通用GoalCandidate/Initiative、复用Scheduler、六合成情境；待决候选重启、来源/identity/revision/charter/理由、接受与执行分离。
- 为什么：支持独立建议/反对/信息获取和不打扰，不构建联系/关怀专用系统，不以模型提案授予权限。
- [实测] 怎么验证：22 targeted passed；六场景6/6，低优先级DEFERRED，非紧急dialogue与先询问信息ACCEPTED，所有contact intent BLOCKED，消息0。ReadingCard显式activation仍不能越过card Grant，pending重启相同；GoalCandidate存入不执行Action。零新增Core表/依赖；真实判断语义未验证。
- M4已保存远端51c28cf29e5ac970d401f19b1ce2c7fa76534a81一致。

## C-042 — M6 模型选择与受控工程准备
- 改了什么：有界operator模型元数据/selection policy、Bridge契约复用的disabled EngineeringPreparationPort；默认pytest加入phase3；修复candidate wake两事务间崩溃重复job风险（persist due）；补同刻冲突/剪裁，以及实际Observation→ContextBuilder→memory-aware fixture preview。
- 为什么：选择不创建端点授权，工程任务不得借旧Bridge shell/credential或reading Grant越权；现在闭合注册表尚无engineering.*，明确PARTIAL。
- [实测] 怎么验证：51 targeted passed（新selection/engineering15、S5 28、memory4、initiative4）；真实SIGKILL后延时重启jobs1/Action0。首轮selection夹具漏开发binding名称，补独立名称后严格Endpoint保持，无真实key读取。所有六工程操作只prepare，execute拒绝、verify拒绝伪造，无workspace副作用。
- [未知] 真实模型能力/费用与真实工程执行；均未运行。模型0/E12 NOT_RUN，无新表/依赖、无生产变更。M5远端ba7c86211c6a409218284b872c63b4d9ed132476一致。

## C-043 — 最终前的公网分阶段诊断和影子公平口径
- 改了什么：批准的公开数字IP文本探针、URL封闭白名单及脱敏summary；被动TLS trust元数据；shadow surrogate采用与Core相同8000chars/8items，避免旧top1比较制造召回优越印象。
- 为什么：主机名DNS失败不等于TLS不可达；仍不重试UNKNOWN、不放宽SSRF/代理/TLS。公平比较比把Core写成优胜更重要。
- [实测] 怎么验证：公开数字IP一次独立Grant/Action试验达TLS后失败，proxy尝试1、HTTP0、read UNKNOWN；精确TLS底层原因未记录，标UNKNOWN。两目标总HTTP0，不无限重试，tls_metadata仅被动统计。43 network targeted pass；shadow matched4pass，rehearsal新CLI回放一致，recall双方1.0，矛盾标注0/2。原旧top1统计不作为改进结论。
- M6远端21464fcfb0c9071a23ebc1a779f1aa80ee4ac600一致；无生产/模型/付费调用。

## C-044 — 导入声明一致性与来源上下文补强
- 改了什么：每record完整mapping声明使用既有core_meta/Event/Artifact持久化，跨原始/映射事务冻结annotation；错误类型与DTO超限逐条REJECTED，batch8MiB写前上限；有源上下文按矛盾伙伴成对优先，引用简写仍保留source_kind/IDs/coverage，原证据不删。
- 为什么：发现原始已提交但mapping没提交时sidecar能变化，以及格式异常会终止批次两真实缺口；补来源后不能让预算把矛盾原话挤掉。
- [实测] 怎么验证：13 targeted passed，9adapter+4memory；相同声明恢复去重、不同行义冲突拒绝、错误2条+合法1条均有结果/留证，真实SIGKILL继续通过。补声明首轮2fail为来源体积挤出相反证据，改排序/引用表示后全部通过，未降低原断言或增加context预算。最新rehearsal CLI重新对账，原14/14、1relation/1conflict、replay不变；无Core schema/依赖变动。
- [实测] C-043已保存450dbb49eddf9c268e4bacce28eaa285b4d8a719；最终全量在本补强后运行。

## C-045 — 跨来源判断与旧映射连续性
- 改了什么：跨dataset同canonical subject统一claim key，检索source范围隔离；稳定legacy/time排序；version2 mapping/policy与同语义旧mapping1最小升级。
- 为什么：P5要求不同来源可对账，来源不能混入claim身份；单一source查询不能泄露其他证据。保存后的开发数据亦需能恢复，不能因补声明就拒绝合法旧projection。
- [实测] 怎么验证：15 targeted passed（memory5+adapter10），跨source1冲突组/范围外ID不泄露，旧mapping升级不改变original artifact/identity。首轮旧surrogate随机UUID tie造成1fail，修为稳定relevance/time/key且保留断言。最新版rehearsal14/14、KG1/冲突1/replay PASS，无新表/依赖。

## C-046 · Phase III 最终回归、证据冻结与交付

- **改了什么**：保存263pass/1skip完整JUnit/输出、SIGKILL/消融开发证据、逐P0—P11 final_delivery；统一明确公网/真实模型/真实Iris检索/工程执行未验收边界。实现源码为4048c3f2830911cbec9d238c3a25f8a2e992f660；本节点仅证据/文档/指纹。
- **为什么**：完成连续开发最终可复现交付，不能把fixture、surrogate或UNKNOWN写成真实能力成功；状态需与实际测试产物一致。
- **怎么验证**：完整264 collected→263 passed/0fail/0error/1skip(E12)，旧测试完整保留；14源记录/11schema、restart14duplicate、source/time/identity/replay PASS；6/6主动夹具、影子零写入。两次公网阻塞DNS/TLS、HTTP0；实际真实模型0。allowlist/敏感模式/许可证检查、独立开发commit/push/ls-remote回验；完整最终SHA以Git为准。

## C-047 · Cloud M1: strict host observation contracts and non-production AstrBot adapter; 2 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-048 · Cloud M2: frozen-snapshot read-only Iris exporter and metadata-only preflight; 4 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-049 · Cloud M3: disabled host ShadowBridge and restartable evidence reconciliation; 7 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-050 · Cloud M4: reuse owner epoch for fenced synthetic handoff and memory authority protocols; 30 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-051 · Cloud M5: host initiative barrier and operator-scoped engineering capabilities through original ActionKernel; 74 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-052 · Cloud M6: bounded shadow session, packaged barriers and reversible cloud runbook; 58 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-053 · Cloud FINAL: preserve 281 passing tests and honest shadow deployment and engineering boundaries
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-054 · Cloud save correction: stage obsolete host module deletion to match fully tested source tree
- 改了什么：本节点源码/测试/报告，详见docs/nana_cloud_integration_architecture.md及阶段证据。
- 为什么：用户授权云端接线准备，保留只读/Shadow/单执行权边界。
- 怎么验证：对应targeted命令和结果在docs/nana_cloud_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-055 · First Shadow M1: fixed approved Core bundle and probe-only launcher; 7 targeted passed, real host blocked
- 改了什么：本节点源码/测试/报告，详见docs/nana_first_cloud_shadow.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_first_shadow_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-056 · First Shadow M2: persisted memory context and restart reconciliation; 15 targeted passed, host and E12 NOT_RUN
- 改了什么：本节点源码/测试/报告，详见docs/nana_first_cloud_shadow.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_first_shadow_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-057 · First Shadow M3: exact rollback, metadata-only SQL authorizer and real SIGKILL recovery; 10 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_first_cloud_shadow.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_first_shadow_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-058 · First Shadow FINAL: 291 passed, one E12 skip; real host blocked, bounded package and rollback evidence saved
- 改了什么：本节点源码/测试/报告，详见docs/nana_first_cloud_shadow.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_first_shadow_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-059 · First Shadow FINAL save: normalize preserved failure-log whitespace; 291 passed and real host BLOCKED_NO_HOST_CHANNEL
- 改了什么：本节点源码/测试/报告，详见docs/nana_first_cloud_shadow.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_first_shadow_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-060 · Shadow Bootstrap M1: evidence-tagged host blockers and SQLite WAL-reset durability audit; 10 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-061 · Shadow Bootstrap M2: real host-version comparison and Pydantic 2.13.5 291-pass regression; SQLite durability gate retained
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-062 · Shadow Bootstrap M3: private fixed SQLite binding and Pydantic wheels, integrity-checked runtime; 22 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-063 · Shadow Bootstrap M4: one-file archive, interpreter-scoped preflight and real extracted-bundle SIGKILL validation PASS
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-064 · Shadow Bootstrap M5: source-backed Iris native-field wrappers and metadata-only hook probe; 16 targeted passed, hook UNKNOWN
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-065 · Shadow Bootstrap release hardening: private SQLite symbol binding, ABI guard and lossless wrapper JSON; 24 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-066 · Shadow Bootstrap startup isolation: disable global site hooks and fail closed before bundle access; 25 targeted passed
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-067 · Shadow Bootstrap FINAL: 306 passing regressions, isolated archive SIGKILL recovery, compatibility matrix and exact operator upload receipt
- 改了什么：本节点源码/测试/报告，详见docs/nana_shadow_bootstrap.md及阶段证据。
- 为什么：用户授权首次真实宿主只读Shadow；无宿主入口时完成固定源码接线包，保持真实验收阻塞。
- 怎么验证：对应targeted命令和结果在docs/nana_shadow_bootstrap_evidence；敏感模式/白名单检查、独立开发commit/push/ls-remote，最终SHA以Git为准。

## C-068 · Shadow host ABI: actual Ubuntu CPython3.12.3 verifies original runtime, classified preflight and ABI policy; 37 targeted passed
- 改了什么：实际Ubuntu24.04/CPython3.12.3兼容证据、support ABI门/失败分类/复用原runtime或交付归档，按本检查点文件清单与docs/nana_shadow_host_compat.md。
- 为什么：真实宿主被补丁版本字符串阻断；仅在开发侧闭合ABI与可下载包交付，不升级宿主/不改生产。
- 怎么验证：对应targeted/完整回归/实际解包与SIGKILL证据保留，逐文件白名单/凭据模式/许可证审查，独立开发commit/push/ls-remote；最终SHA以Git为准。

## C-069 · Shadow host package: dual actual Python full318 regressions and SIGKILL validation, fixed downloadable private-branch archive
- 改了什么：实际Ubuntu24.04/CPython3.12.3兼容证据、support ABI门/失败分类/复用原runtime或交付归档，按本检查点文件清单与docs/nana_shadow_host_compat.md。
- 为什么：真实宿主被补丁版本字符串阻断；仅在开发侧闭合ABI与可下载包交付，不升级宿主/不改生产。
- 怎么验证：对应targeted/完整回归/实际解包与SIGKILL证据保留，逐文件白名单/凭据模式/许可证审查，独立开发commit/push/ls-remote；最终SHA以Git为准。

## C-070 · Shadow host FINAL: verified remote downloadable archive bytes, actual dual-Python318 regressions and unchanged production scope
- 改了什么：实际Ubuntu24.04/CPython3.12.3兼容证据、support ABI门/失败分类/复用原runtime或交付归档，按本检查点文件清单与docs/nana_shadow_host_compat.md。
- 为什么：真实宿主被补丁版本字符串阻断；仅在开发侧闭合ABI与可下载包交付，不升级宿主/不改生产。
- 怎么验证：对应targeted/完整回归/实际解包与SIGKILL证据保留，逐文件白名单/凭据模式/许可证审查，独立开发commit/push/ls-remote；最终SHA以Git为准。


## C-071 · Shadow Bind R02: dispatcher/registry 源码审计 + observer 开发副本（未安装）+ 状态口径修正 + Iris schema-only 兼容

- 改了什么：
  - `docs/nana_shadow_astrbot_dispatcher_audit_20261011.md`（M1：P2 十问逐项带 `path + symbol + line`；dispatcher map；六硬问题直答）。
  - `src/plugins/astrbot_plugin_nana_shadow_observer/{main.py,metadata.yaml,nana_observe_core.py}`（M2：零正文 / fail-closed 生命周期观察器，**开发副本**）。
  - `tests/nana_shadow/test_observer_offline.py`（9 例离线）。
  - `manifests/nana_shadow_observer_fingerprints.json` + `artifacts/nana-shadow-observer/nana_shadow_observer-0.0.1-dev.tar.gz`（确定性打包）。
  - `docs/nana_shadow_registration_blocker_20261011.md`（M3）、`docs/nana_shadow_observer_dev_20261011.md`（M2+P14 runbook）、
    `docs/nana_shadow_iris_schema_20261011.md`（M4）。
  - PROJECT_BRAIN 03/04/09/10/11 同步。
- 为什么：任务书要求在**不重启、不读 JWT** 前提下，把「hook 是否真实可绑」从摘要推进到源码级结论，
  并产出可审计的 observer 开发副本与安装 runbook。
- 怎么验证：`python3 -m pytest tests/nana_shadow -q` → 9 passed；打包确定性复算一致；
  全量套件失败点全部为既有 `SQLITE_VERSION_UNSUPPORTED`（非回归）；逐文件指纹入 manifest；独立开发分支 commit/push/ls-remote。
- 关键结论：**生命周期 hook = plugin manager 直调 registry，不是真实 dispatcher** ⇒ `BLOCKED_NO_INTERNAL_PROBE`。

## C-M0 · AstrBot Shadow Codex development
- 改了什么：Baseline 318 passed, E12 skipped; source audit and API evidence gap recorded；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M1 · AstrBot Shadow Codex development
- 改了什么：Metadata sanitizer and no-response observer contract; 13 targeted passed, collection failure retained；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M2 · AstrBot Shadow Codex development
- 改了什么：Persistent Store alias dedup and reviewed-origin binding proof; 13 targeted passed; unchanged approved Core；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M3 · AstrBot Shadow Codex development
- 改了什么：Shadow barrier and bounded callback failure isolation; 9 targeted passed including actual SIGKILL gap recovery；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M4 · AstrBot Shadow Codex development
- 改了什么：Source-gated AstrBot registration block and exact neutral registry lifecycle; 3 targeted passed, shared audit still absent；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M5 · AstrBot Shadow Codex development
- 改了什么：Exact-query Iris schema inspector with authorizer and frozen-source comparison; 13 targeted passed, real compatibility UNKNOWN；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M6 · AstrBot Shadow Codex development
- 改了什么：Observer development kit builder, independent Core proof readback and operator rollback/runbook; 13 targeted passed, real shim blocked；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M4-SOURCE · AstrBot Shadow Codex development
- 改了什么：Nana audit652a72f absorbed by reference; source-backed 4.28 lifecycle shim and safe unload, 21 targeted passed; dispatcher still blocked；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M7-HARDEN · AstrBot Shadow Codex development
- 改了什么：Lifecycle shim and kit validated in two actual Python environments; fail-closed BaseException/deferred completion guards, 22 targeted passed；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## C-M7 · AstrBot Shadow Codex development
- 改了什么：Final full regression 372 passed one E12 skip; reviewed observer kit archive, approved55 unchanged and zero production actions；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。

## FINAL · AstrBot Shadow Codex development
- 改了什么：Remote archive bytes verified; ordered Nana development handoff, 372 pass one skip; real dispatcher remains unverified；文件见manifests/whitelist_astrbot_codex.json。
- 为什么：用户授权独立开发Observer/证据链，保留批准Core字节与现场事实边界。
- 怎么验证：docs/nana_astrbot_shadow_evidence的专项/回归记录；白名单/敏感与运行产物检查通过，不代表真实宿主验收。


## C-072 · Shadow Bind R03：双分支合流 + SAFE message observer + 免重启加载路径审计

- 改了什么：
  - **M0 合流**：`dev/nana-core-v1-astrbot-shadow-bind-r03`，`merge --no-ff` Codex 分支 `10581aea`（经离线 bundle 导入）；合并提交 `d3e8c81`。
  - **M1 审计**：`docs/nana_shadow_message_observer_audit_20261011.md`（dispatcher map、逐候选 SAFE/UNSAFE、`plugin_set` 前置条件、免重启路径）。
  - **M2 实现**：`src/plugins/astrbot_plugin_nana_shadow_observer/message_hook_adapter.py`（最薄层，复用 Codex `sanitize/observer/core_sink`）；
    `main.py` 增 `filter.on_decorating_result()` 接线，默认哑火。
  - **M2 测试**：`tests/nana_shadow/test_message_hook_adapter.py`（32 例）。
  - **M5**：PROJECT_BRAIN `03/04/09/10/11` 同步（`D-045` 新裁决）。
- 为什么：任务书要求在**不重启、不读 JWT、不碰生产**前提下，把「message 是否有可安全观察的 hook」
  从摘要推进到源码级结论，并产出可审计的最薄 observer；同时把 Codex 独立实现与奈奈现场账本合流为单一 SSOT。
- 怎么验证：
  - `git bundle verify` ok；`merge-base = c3ada9b0…`；合流提交 `d3e8c81`（双亲 `652a72f` + `10581aea`）。
  - `python3 -m pytest tests/nana_shadow -q` → **31 passed / 1 skipped**（skip = 宿主 SQLite 门）。
  - 三方回归对照：R02 `65F/171P/1S/82E`；Codex `71F/219P/1S/82E`；**R03 与 Codex 逐数一致 ⇒ 零回归**；
    全部 202 处失败签名 = `SQLITE_VERSION_UNSUPPORTED`（宿主 3.46.1，未绕过）。
- 关键结论：
  - `SAFE result-path observer = AVAILABLE`；`SAFE early all-message observer = NOT_AVAILABLE`；
    `AdapterMessageEvent` / `OnLLMRequestEvent` = **UNSAFE**。
  - `NEW_PLUGIN_NO_RESTART_MANUAL_PATH = YES`（人工 Dashboard 路径）。
  - message observer `IMPLEMENTED / TESTED`；`Observer registered = NO`、`host_binding = UNVERIFIED`、
    `FIRST_REAL_ASTRBOT_SHADOW = BLOCKED`、`E12 = NOT_RUN`。

## R04-C0 — independently verified R03 bundle and baseline
- 改了什么：追加R04 development scope/baseline evidence; no Core/source modification in this checkpoint.
- 为什么：uploaded bundle is sole source, old frozen Codex branch not an implementation base.
- 怎么验证：SHA256/list-heads/complete-history verify and approved-runtime404pass/1E12skip. Real host facts not promoted.

## R04-C1 — receipt contract and separated trust types
- 改了什么：one_shot DTO/provenance/source-empty production pins; fixture class cannot accept real/lifecycle provenance.
- 为什么：one observation permission must not become Grant or wildcard/private-body authorization.
- 怎么验证：14 contract tests pass; initial2 bool-Literal failures fixed in validator, assertions retained. Evidence contract_fixed.txt.

## R04-C2-C5
- 改了什么：Atomic receipt and D-045 ingress/proof; 42 targeted passed, five actual SIGKILL boundaries; R03 pre-existing preflight drift disclosed; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-C6-C7
- 改了什么：Failure-isolated real-metadata callback and read-only operator CLI; 53 targeted passed; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-C6-C8
- 改了什么：Fail-closed operator CLI, 65 targeted passes, dormant message-only plugin and gated package/runbook; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-C8-HARDEN
- 改了什么：Dormant plugin blocks fixture trust and empty pins; 62 R04 targeted passed; earlier 65 count corrected to62; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-C8-SEAL
- 改了什么：Exact UTC microseconds, non-remintable permit and single-writer rollback instructions; 63 targeted passed; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-C8-INTEGRITY
- 改了什么：Stdlib hash gate before package execution and fixed proof diagnostics; 64 targeted passed, full468 passed one E12 skip; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-RELEASE
- 改了什么：Reviewed downloadable archive and extracted-package validation; full468 passed, one E12 skip, zero production operations; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-FINAL-TYPE-SEAL
- 改了什么：Require actual ReceiptLedger at sanitizer permit gate; full469 passed, one E12 skip, 65 R04 cases; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-FINAL-DELIVERY
- 改了什么：Sealed support archive and extracted-package proof; JUnit469 passed one E12 skip, all65 R04 cases; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-FINAL-CLI-SEAL
- 改了什么：Redact invalid CLI arguments with fixed diagnostics; full470 passed one E12 skip, 66 R04 cases; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-FINAL-PACKAGE
- 改了什么：Final CLI-redacted asset verified, full470 passed one E12 skip, package55ddab exact, zero host operations; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R04-FINAL
- 改了什么：Remote final asset bytes independently verified; handoff and ordered commit range, no further source changes; files in manifests/fingerprints_r04.json.
- 为什么：one reviewed metadata observation, D-045 gates retained, approved Core unchanged.
- 怎么验证：targeted evidence in docs/nana_r04_evidence, staged diff/secret/private-artifact allowlist checks; development only.

## R041-M1
- 改了什么：Bounded stdlib UDS metadata channel, R04 single-writer ingress and foreground session fence; 106 targeted passed; manifests/fingerprints_r041.json.
- 为什么：host SQLite3.46.1 must stay untouched; bounded local metadata bridge, not second permanent Runtime.
- 怎么验证：development-only targeted/full evidence, diff/allowlist/secret-private-artifact scans; approvedCore unchanged.

## R041-M2
- 改了什么：Old-SQLite client isolation, three actual worker SIGKILLs, PID/socket-fenced stop cleanup and adversarial lifecycle; 126 targeted passed; manifests/fingerprints_r041.json.
- 为什么：host SQLite3.46.1 must stay untouched; bounded local metadata bridge, not second permanent Runtime.
- 怎么验证：development-only targeted/full evidence, diff/allowlist/secret-private-artifact scans; approvedCore unchanged.

## R041-M3
- 改了什么：Bridge package/runbook and safe operator session readback; 44 targeted passed, real statuses unchanged; manifests/fingerprints_r041.json.
- 为什么：host SQLite3.46.1 must stay untouched; bounded local metadata bridge, not second permanent Runtime.
- 怎么验证：development-only targeted/full evidence, diff/allowlist/secret-private-artifact scans; approvedCore unchanged.

## R041-M4-SEAL
- 改了什么：Bounded observation and isolated hard-exit grace, no late ingress; full510 passed one E12 skip; manifests/fingerprints_r041.json.
- 为什么：host SQLite3.46.1 must stay untouched; bounded local metadata bridge, not second permanent Runtime.
- 怎么验证：development-only targeted/full evidence, diff/allowlist/secret-private-artifact scans; approvedCore unchanged.

## R041-RELEASE
- 改了什么：Sealed-window package validated in fresh directory; full510 passed one E12 skip, no approvedCore or production changes; manifests/fingerprints_r041.json.
- 为什么：host SQLite3.46.1 must stay untouched; bounded local metadata bridge, not second permanent Runtime.
- 怎么验证：development-only targeted/full evidence, diff/allowlist/secret-private-artifact scans; approvedCore unchanged.

## R041-FINAL
- 改了什么：Remote asset bytes verified, handoff/minimal host sequence and ordered development commits; real bridge NOT_RUN; manifests/fingerprints_r041.json.
- 为什么：host SQLite3.46.1 must stay untouched; bounded local metadata bridge, not second permanent Runtime.
- 怎么验证：development-only targeted/full evidence, diff/allowlist/secret-private-artifact scans; approvedCore unchanged.


## C-073 · R042 Real Host Integration / Final Preflight（真实宿主合流 + 非生产 preflight）

- 改了什么：
  - **M0 合流**：新建 `dev/nana-core-v1-r042-real-host-preflight`，基于 R03 `89385e98`，
    `merge --no-ff` R041 `c7d87018`；合并提交 `ddcd848`（双亲 `89385e98` + `c7d87018`）。
    PROJECT_BRAIN 09/10/11 为 R041 纯新增 ⇒ **零冲突**。
  - **M1**：PROJECT_BRAIN `09/10/11` 写入本阶段真实宿主证据（新增 `D-046` 口径裁决）。
  - **M2/M3**：只读证明 PID1 未注入 private sqlite；same UID / same pid·mnt ns / same fs visibility 核验通过。
  - **M4**：R041 交付包 SHA256 = `fafe82ec…dc63` 独立复核 **PASS**。
  - **M5**：短命子进程加载 R041 packaged private runtime → SQLite **3.51.3**，退出即清。
- 为什么：把 R04 Host Readiness 的真实证据正式入账，并完成进入**人工 Dashboard 上传前**的最后一道非生产 preflight。
- 怎么验证：
  - `git rev-list --parents -n1 HEAD` = `ddcd848 89385e98 c7d87018`（--no-ff 双亲）。
  - 状态键见 `09_STATE.md` 本阶段表；`HOST_NATIVE_SQLITE_GATE = BLOCKED`，`SHORT_LIVED_SHADOW_WORKER_FEASIBLE = YES`。
  - 生产动作计数 **0**：未装 Observer / 未改 plugin_set / 未建 receipt / 未 pin trust / 未起正式 bridge / 未重启 / 未发消息。

### R042 C1 — close audited source-seal tooling gap (2026-10-12 UTC)
- Why: R041 ledger review/arm cannot proceed with correctly EMPTY source maps and had no reviewed-build onboarding tool.
- Change: EMPTY sealed source module, offline exact receipt preparation/review/seal, separately constrained VERIFY_ONLY proof package, operator runbook/D-048. Original approved Core untouched; no runtime pin setter or real authority.
- Validation: R04/R041/onboarding targeted tests executed on actual CPython3.12.14 + privateSQLite3.51.3 + Pydantic2.13.5; full evidence/count at FINAL. Fixed gate order after an old trust-domain test exposed diagnostic regression; old assertions preserved.

### R042 C2 — bound post-review export and test separate read-only proof seal
- Why: a build review must not accidentally archive extra nested Core/body/private fields.
- Change: exact metadata-only Core proof schema (UUID/hash/link refs/time/zero counts), immutable source read vs dirty worktree checks, review-document digest recomputation tests.
- Validation: new strict/adversarial tests; no existing test/expectation removed or weakened. Package/default-production and final regression evidence follows FINAL.

### R042 C3 — remove manual hash preparation from onboarding
- Why: exact receipt hashes must match initialized Store's HMAC domain; manually composing Python or guessing IDs is not an executable safe workflow.
- Change: metadata-only scope helper with transient explicitly authorized IDs and hashed-only output, no discovery/body/network; operator instructions updated.
- Validation:33 onboarding tests passed in approved privateSQLite3.51.3 runtime. C2 package verification14 operations and full542pass/1skip retained as checkpoints; final build/regression follows new committed support seal.

### R042 FINAL — audited EMPTY package and full regression
- Changes: deliver no-authority EMPTY kit, exact operator ordering/fields/stops, evidence and security fingerprints. Production one-shot/proof trust must still come from independently reviewed source builds; no real pin or host fact fabricated.
- Validation: full543pass/0fail/0error/1E12skip in original privateSQLite3.51.3 runtime; extracted kit15 operations PASS; exact55Core byte hashes; original tests unchanged. Secret/private/runtime DB checks PASS. No host/model/message/production operation; no new tables/dependencies.
- Delivery: support source c6eb7255d0d2d985ecf5e06cdf42cfa4a33040b6, artifacts/r042/nana-r042-empty-c6eb725-onboarding.tar.gz,3358013bytes,SHA256 fe9c4bc0ad6cdd11b8a491fb610cacdc43f9cb395bdc36730e1b58b27be8bca7. Final Git/remote verification recorded after saving. Scope: R042 operator/build closure only; next real one-shot requires Nana independent host review and Sister's exact authorization.


## C-074 · R043 First-Real-Shadow Candidate Integration（合流 + 静态验收）

- 改了什么：新建 `dev/nana-core-v1-r043-first-real-shadow-candidate`（基于 R042 preflight `7d8a481`），`merge --no-ff` Codex R042 onboarding `a436333`；合并提交双亲 `7d8a481` + `a436333`，共同基线 `c7d87018`。PROJECT_BRAIN 09/10/11 三处追加冲突**人工逐块合并**，两分支证据全保留；`10_DECISIONS.md` 追加 **D-049** 纠正 `D-046` 编号碰撞（原 D-046 = R04 One-Shot Receipt，D-047 = temporary Shadow bridge，D-048 = production trust onboarding）。
- 为什么：把真实宿主 readiness + Codex R042 trust-onboarding 合成**唯一** FIRST_REAL_ASTRBOT_SHADOW 候选基线，并消除历史编号歧义。
- 怎么验证：Codex onboarding 文件与 R041 bridge 文件同时存在；`src/`（Approved Core）合流零改动；无新增 SQL table / dependency；`git diff --check` PASS；conflict marker 0；secret/private 扫描 PASS；已批准 private runtime 下完整 regression **543 passed / 0 failed / 1 skipped(E12)**；EMPTY 包 SHA256 复核一致 + verify/preflight PASS（production pins 0）。
- 生产动作计数 **0**：未上传 Dashboard / 未装 plugin / 未改 plugin_set / 未建真实 authorization / 未 seal production / 未 arm receipt / 未起正式 bridge / 未发消息 / 未 reload·restart / 未做 Iris 私人读取 / 未调用模型。


## C-075 · R044 pre-production red-team / offline recovery qualification（Codex，吸收前事实）

- 改了什么：`dev/nana-core-v1-r044-preprod-redteam-codex`（base `a436333`，HEAD `1bdf1f0`）修复 **10** 个产品问题（critical **0** / high **1** / medium **4** / low **5**），新增 **219** 测试；未改 PROJECT_BRAIN 09/10/11、未改 Approved Core。
- 修复清单：result-write 失败不跳过 cleanup；IPC directory inode/FD fence；capability LAST 发布；package 拒绝 dangling symlink/FIFO/special entries；package 拒绝 group/world-writable code/manifest/dirs（**唯一 High**）；Git review source 拒绝 symlink blob；stale cleanup 校验完整 capability digest；atomic publication 不暴露 nlink=2；preflight 不对 expired/VERIFY_ONLY 报 READY；symlink 固定诊断契约保持。
- 怎么验证：真实 SIGKILL crash matrix 32 边界、race/filesystem/IPC/onboarding red-team、recovery qualification、supply-chain/package hardening；已批准 private runtime 下 **762 passed / 0 failed / 1 skipped(E12)**；证据 `docs/nana_r044_evidence/`。
- 边界：`OFFLINE_RECOVERY_QUALIFIED` 为 fixture/offline 结论，**不得**写成真实 host PASS；生产 pins **EMPTY**。

## C-076 · R045 First-Real-Shadow Release Candidate（R044 修复吸收 + 合流）

- 改了什么：新建 `dev/nana-core-v1-r045-first-real-shadow-release-candidate`（基于 R043 `2d83e6a`），`merge --no-ff` R044 `1bdf1f0`；合并提交双亲 `2d83e6a` + `1bdf1f0`，共同基线 `a436333`，**零冲突**。PROJECT_BRAIN 09/10/11 为 R043 现场事实，**逐字节保留**；追加 D-050 与 R044/R045 事实。
- 为什么：把 R044 的全部安全修复、测试与交付能力吸收到 R043，形成**唯一**可进入真实 one-shot 前准备的候选。
- 怎么验证：R044 10 项修复机械确认进入 R045（`docs/nana_r045_merge.md`）；`src/`（Approved Core）合流零改动；无新增 SQL table / dependency；conflict marker 0；已批准 private runtime（CPython 3.12.14 / private SQLite 3.51.3 / Pydantic 2.13.5）下完整 regression **762 passed / 0 failed / 1 skipped(E12)**（收集 763）；EMPTY 包从 final source **重新构建**、verify/preflight + 交付校验 **15 操作 PASS**、Core55 exact、dangerous entries 0、package permissions PASS、两次同 basename 构建 **byte reproducible**。
- 交付：`artifacts/r045/nana-r045-empty-760e5e8-onboarding.tar.gz`，3368374 bytes，SHA256 `05e9765c…bd68c`，support source `760e5e829aa67b622b508c3f2c4a4e617528933f`；生产 pins **EMPTY**。旧 R042/R043 包 **superseded**。
- 环境说明：本容器默认 `/tmp` 为 overlayfs，inode 复用使 `test_atomic_write_does_not_follow_symlink_or_overwrite_foreign_file` 期望的 ENTRY_DRIFT 无法触发；同用例在**未改动**的 R044 原树下**同样失败** ⇒ 环境特性、非产品回归；合格跑使用 tmpfs 临时目录。
- 生产动作计数 **0**：未上传 Dashboard / 未装 plugin / 未改 plugin_set / 未建真实 authorization / 未 seal production / 未 arm / 未起正式 worker / 未发真实测试消息 / 未 reload·restart / 未做 Iris 私人读取 / 未调用模型。


## FUTURE-ARCH-VNEXT1 · 持续主体架构设计（2026-10-12 UTC，设计分支）
- 改了什么：新增 `docs/nana_future_architecture_vnext1.md`、固定源码/证据索引、阅读边界与文档校验记录，及独立设计指纹清单；仅向09_STATE追加设计存在的事实，不把提案写成已实现或新授权。
- 为什么：依据当前R045源码及证据，为持续自我、可信长期记忆、有限目标经济、人格关系、可移植主体提供一年蓝图，继承五阶段总纲和当前one-shot→Small Memory Shadow→E12顺序。
- 怎么验证：43处source fingerprint及行号、34节/主题覆盖、本地链接、敏感模式和实现零diff检查通过；未重跑产品回归、未运行新架构实验。既有R045762/0/1与当前真实Shadow/E12未验证边界保留。所有新设计待后续实施授权/评审，未触及生产/私密数据/真实receipt/pin。

[设计文档校验补记] 初次staged diff检查发现来源索引末尾多余空行；已规范化并更新设计manifest/校验记录，最终diff检查在提交前通过。无代码或运行验收变化。

## NEXT-STAGE-M1 · 合成Memory / Phase A readiness
- 改了什么：新增tools/nana_next_stage严格合同与原Store上的合成投影、tests/next_stage及开发证据。
- 为什么：在真实Shadow等待期间提前完成Phase A可独立运行的合同/fixture准备，不改批准Core或现场主线。
- 怎么验证：52passed，实际SIGKILL导入恢复、backup/replay quarantine、scope/provenance/纠正/检索撤回。首次严格JSON边界失败记录保留后修复；真实数据、真实模型、生产操作0。

## NEXT-STAGE-M2 · E12 frozen supplement / one-command qualification
- 改了什么：在Core外复用S5 snapshot/execute_case/CompatibleModelPort/CallLedger，补关系/OFFERED承诺/偏好纠正/观察覆盖理解评分与CLI；原提案和Core行为分开留证。
- 为什么：提前准备真实模型语义门，fixture绝不升级real；补齐Phase A可离线验证的合同。
- 怎么验证：顺序双fixture/各case有无经验、原提案漏定位仍判语义失败、结构漂移/缺端点/模拟器配置不误报真实E12；原型撤回/历史时间/重算hash对抗用例保留后修复。实际真实模型/生产/私忆/receipt/bridge操作0。

## NEXT-STAGE-FINAL · qualification / regression / blocker handoff
- 改了什么：补实际进程承诺/SelfFrame/context恢复用例；实际CLI证据、N01–N06/N11–N13/E12逐门资格矩阵、九项最小实施提案与指纹。
- 为什么：真实Shadow一旦通过即可复用准备工作；保留正式成长/承诺/实体/真实删除等基础边界。
- 怎么验证：81新增pass；既有Core指定全套+新增453pass/0fail/1E12skip（18.364sec）；新CLI合成工程PASS、真实模型NOT_RUN；敏感模式/白名单/运行DB排除检查通过。未改Core/SQL/依赖/R045接线/生产，无私人内容与真实secret读取。

## NEXT-STAGE-COVERAGE-FINAL
- 改了什么：Coverage合同拒绝声明完整却有丢弃/断线；资格矩阵/指纹/最终报告更新至83新test、455pass+1skip。
- 为什么：观察覆盖不能把缺失事件当未发生；属于Core之外的局部合同修复。
- 怎么验证：先保留2failed反例，再修合同，83targeted和455/0/1全Core配置回归通过。四项原型语义修复均有失败证据；未改当前R045/R045.1源码或Approved Core。

[证据记录勘误] 09_STATE最后检查点的精确时长校正到JUnit17.582sec；产品代码、测试结果与manifest未变。

## 2026-10-14 UTC — C1 canonical identity
- 改动：独立 Core continuity 包、显式 v2 migration、沿用 Store UUID 的身份历史/CAS/来源合同。
- 原因：把身份从 readiness 原型推进为长期状态，避免 model/host/session 创建新主体；拒绝伪安全的旧正文原地迁移。
- 验证：2 identity tests PASS；现有默认372 PASS/1 E12 skip；无生产/真实模型操作。

## 2026-10-14 UTC — C2 permanent memory foundation
- 改动：正式 evidence/memory/实体/依赖/索引 schema v3 与严格synthetic DTO，7类记忆和独立认识层。
- 原因：替换仅core_meta原型；保持原始证据与总结分离，并为可删除payload提供基础。
- 验证：5 continuous-self tests PASS；纠正入口曾错误拒绝disputed旧项，已修正为显式family/authority检查；无放宽断言。真实入口保持关闭。

## 2026-10-14 UTC — C3/C4 correction and deletion
- 改动：纠正传播到派生总结；正式生命周期/置信变更；受authority保护的物理forget、fsync删除意图、备份清理/恢复锚和索引清理。
- 原因：用户隐私删除优先于保留正文审计，修正旧summary仍可能进入未来context的问题。
- 验证：9 C/D tests PASS，含真实SIGKILL、DB/WAL/backup/replay无canary、旧source不同revision仍不能复活；83 readiness tests保留通过。无真实数据或生产操作。

## 2026-10-14 UTC — C5–C7 persistent relationship / promises / projects
- 改动：RelationshipView、CommitmentCandidate/AdoptedCommitment/状态机、ProjectState显式revision；四个规范化状态/可删除记录/依赖表。
- 原因：主体需跨模型记住共同历史和正在做的事；用户提到与奈奈正式承诺不可混淆。
- 验证：11 C/D tests PASS；模型不能自行adopt/履约；关系/承诺/项目重启恢复及所有历史payload删除通过。

## 2026-10-14 UTC — D1/D2 SelfFrame / ContextAssembler
- 改动：正式派生SelfFrame、privacy-first动态context、完整来源manifest/state一致性、预算/冲突整组/coverage；continuity开发库固定Shadow执行屏障。
- 原因：换模型不靠巨型persona prompt，删除/纠正/权限变化后不得继续用旧context。
- 验证：13 C/D tests PASS；预算不足/私有远传/篡改/旧context与coverage伪FULL均拒绝；无真实外部调用。

## 2026-10-14 UTC — D3 model-independent proposal contract
- 改动：Context-based v2 ModelPort、DeliberationSession与两个不同fixture adapter；兼容原reading-only端口。
- 原因：主体状态属于Store，模型可更换且只能提案；不再把后续理解字段塞进rationale字符串。
- 验证：15 C/D tests PASS；相同冻结context换fixture不改状态，伪造receipt/authority/identity/source均拒绝；真实模型未运行。

## 2026-10-14 UTC — D4 experience → later context/proposal
- 改动：schema v5 experience/lesson记录、artifact绑定独立质量核验、复用现有rule/compiler的窄学习试验、显式激活/撤回和context引用。
- 原因：把经历与学到的规则分开，证明重启/换fixture后可观察的提案变化，而不是人格提示词。
- 验证：17 C/D +83 readiness =100 PASS；新进程、raw proposal消融、不相关scope、旧source/lesson删除、权限不扩大。另修索引对失效/superseded项的清理及重复同源memory commit幂等，保留旧断言。

## 2026-10-14 UTC — C/D integration regression fix
- 改动：Store.one/all兼容未初始化的历史只读view；跨恢复副本删除锚锁与origin登记、严格journal元数据；默认pytest纳入永久continuous-self tests。
- 原因：全仓检查暴露新registry对旧只读借用方式的破坏；删除必须覆盖活跃原库而非只清当前恢复副本。
- 验证：首次全仓835/27/1失败证据保留；兼容修复相关52 PASS，18 C/D PASS。旧SQLite client真实运行3.13.5/3.46.1且无private imports，未改系统/生产依赖。

## 2026-10-14 UTC — C/D bounded context and vertical restart
- 改动：SQL有界候选与manifest计数、隐私限制反证整组、SELF entity绑定、缺失authority拒绝、精确承诺核验；schema v6仅索引。
- 原因：避免长期记忆增长时先读全量再裁剪，防止只展示可见反证一侧，以及不相关核验证明履约。
- 验证：20 C/D tests PASS；全状态组合用真实新进程/另一fixture恢复且无主体状态变化；上一全仓864/0/1，最终source checkpoint后再全量。

## 2026-10-14 UTC — C/D current-task destination privacy
- 改动：任务输入默认PERSONAL并受同一context destination gate；补长期API使用/数据/迁移/删除限制文档与D-CS-001。
- 原因：隐私不能只保护长期记忆，当前task也可能含私人内容。
- 验证：20 C/D tests PASS；最终完整回归将在此source checkpoint之后运行。未触及任何真实宿主/消息/数据。

## 2026-10-14 UTC — C/D private local storage default
- 改动：开发continuity DB/backup/replay私有目录与文件权限门、symlink拒绝，示例使用独立0700目录。
- 原因：隐私边界也要覆盖本机落盘，不能只限制模型context。
- 验证：20 C/D tests PASS，不安全共享目录在写DB前fail-closed；未更改系统/生产目录权限。

## 2026-10-14 UTC — C/D full-suite fixture precondition
- 改动：权限拒绝测试显式chmod synthetic目录到0755后再断言拒绝。
- 原因：全仓legacy测试遗留umask077，使mkdir(mode0755)实际得到0700；一次全量因此864 PASS/1 FAIL/1 skip。产品正确允许0700，测试前置条件错误，未放宽拒绝断言。
- 验证：修正后20 C/D tests PASS；最终全仓复测继续。仅测试夹具改动。

## 2026-10-14 UTC — C/D final offline candidate delivery
- 改动：最终全量JUnit、20项永久能力证据、组合重启结果、安全/包检查、source manifest、API/架构/状态记录；CONTINUOUS_SELF_OFFLINE_CANDIDATE=READY。
- 原因：交付正式长期能力与可复现证据，严格区分离线fixture/本地真实进程/真实宿主/真实模型。
- 验证：865 passed /0 failed /1 E12 skip；Core源checkpoint579a0bd，最终tested checkpoint289a7a5；无旧测试删除/弱化，无生产/main/R045变化。密钥模式扫描0命中，无DB/WAL/SHM/binary入Git，production/proof pins仍EMPTY。详情见delivery和results.json。

## 2026-10-14 — C-V2 Phase 0 meta-architecture gate

Docs-only executable contract accepted for offline implementation: asset reuse,
one causal SubjectLoop, authority/derived distinction, v7 schema/CAS, privacy,
reflection constraints, independent preference support and counter-evidence,
ten-day life/ablation/60-day soak specification. No business implementation or
production changes in this gate. See ADR-CV2-001.

## 2026-10-14 — C-V2 Phase 1a subject transactions

Added the single SubjectLoop and v7 development migration. Reused existing
records/memory/privacy/event replay. Tested 24 continuity cases; no production,
real memory ingress, model call or execution authority changes. All generated
C goals remain proposed candidates; the barrier is NO_ACTION/SHADOW_BLOCKED.

## 2026-10-14 — C-V2 Phase 1b projections and reflection

Added deletable-source-backed living/personality/relationship views and context
integration. Independent root counts resist copied support; counter-evidence
can dispute and supported replacement can supersede without revival. Added
source-backed reflection to existing checked lesson mechanism. Privacy precedes
payload projection; ordinal internal activation does not overwrite personality
or identity. 27 continuity tests passed; ten-day/soak still pending.

## 2026-10-14 — C-V2 whole-subject causal verification

Added the reproducible ten-day synthetic life, matched preference/lesson controls
and 60-day soak using real continuity modules; only world outcomes/ModelPorts are
fixtures. Added actual SIGKILL transaction recovery and separate-process model
swap checks. Fixed terminal optional-intention inhibition after counter-evidence,
removed projection/coordinator dependency cycle, and supplied pre-model appraisal
through the existing context budget/privacy path. 32 continuity tests passed;
initial full suite 877/0/1, final source regression pending. Real gates unchanged.

## 2026-10-14 — C-V2 final offline qualification and freeze

Final product regression 877 passed / 0 failed / 1 skipped (E12 NOT_RUN), 32
continuity cases. Published 20-check life/ablation/60-day evidence, actual
SIGKILL/restart assertions, source privacy scan and 105-file fingerprint manifest.
Documented ordinal-policy/one-lesson/real-semantic limits and intermediate fixes.
No prior tests modified, no dependencies added, no production or external
execution. Persistent Self offline candidate READY; automatic real rollout denied.

## 2026-10-15 — D-V1 baseline and current-route reconciliation

Read actual C-V2 READY base ea65dab; created isolated Runtime development branch.
Updated 07 current C/D status, preserving historical records. Recorded executable
runtime/lease/queue/cognition/privacy/social boundaries and verification sequence.
No business source or production changes in this checkpoint.

## 2026-10-15 — D-V1 M1 authority/queue/scheduler

Implemented dev v8 on the existing Store: runtime lease, queue, schedules and
operational cognition-call table; local write lock plus epoch/lease commit fence,
clock high-water, source-linked admission/queue, periodic coalescing and quarantine.
35 targeted tests PASS. Clarification records S1–S10 as peer cases and keeps all
judgment/personality in C. No production, new dependency or real-world adapter.

## 2026-10-15 — D-V1 M2 standalone coordinator

Added NanaRuntime foreground event loop, injectable clock, resource-health CLI,
supervised frozen model fixture subprocess and attempt-based daily budget/
cooldown/backoff. Timeout fallback still runs C and preserves identity; repeated
idle polling does not append domain history or rewrite unchanged health. Five
runtime tests PASS; no real models or production integration.

## 2026-10-15 — D-V1 M3 open opportunities and C social learning

Extended C rather than adding behavior loops: open motivation labels, sourced
concerns/constraints, background check descriptions, semantic social/read proposals
and one verified interaction lesson with trial/review/suspension. D schedules
those checks; synthetic screen/file/presence/platform adapters read no devices.
39 combined tests PASS; 7 Runtime tests PASS after final resource-clock/health
changes. No raw body enters queue metadata; old C input JSON accepts new optional
default fields. No real action or standing-delegation activation.

## D-V1 M4 — 2026-10-15 — runtime system/recovery qualification

[实测·开发离线] Added S1–S10 matrix, 72h no-input, 30d mixed life and bounded
real local process qualification. Same C loop, generic source interpretation;
no per-scenario runtime policy. Fixed duplicate lease binding, restart clock
floor, backoff restoration and active-health semantics found during recovery
review. Added v7→v8/erasure/replay tests. Four actual SIGKILL cuts preserve
identity and one logical decision; unresolved model calls stay UNKNOWN.
Validation: 43 C+Runtime PASS /0 FAIL, 27.50s. No prior tests weakened; E12 NOT_RUN;
production untouched. Final full regression/evidence follows separately.

## D-V1 FINAL — 2026-10-15 — offline candidate delivery

[实测·开发离线] Full suite888 PASS /0 FAIL /1 SKIP (E12), 84.87s; system gates
32/32 PASS. Archived S1–S10, 72h/30d and actual local process100-sample/4-SIGKILL
measurements; documented standalone CLI/contracts/migration/rollback/limits.
Explicitv8 tables4/dependencies0; no old tests or production source changed.
Privacy/path/credential scan PASS; production pins EMPTY. Manifest128 files
anchored in09_STATE. D_V1_CONTINUOUS_RUNTIME_OFFLINE_CANDIDATE=READY, not real
host/model/E/G acceptance. Main/R045 untouched; no production or external action.

## L3-C-AFFECT-V1 M1 — normative/disclosure foundations
Implemented v9 opt-in, normative evaluation/erasable disposition history and
semantic disclosure with known-fact contradiction rejection on same subject.
Targeted9 PASS; fixed strict DTO JSON rehydration after first failing regression.
No new dependency/table or real-world operation. More phases pending.

## L3-C-AFFECT-V1 M2 — negative-only governance / governed fixture realization
[实测·开发离线] R2 implemented: OperatorAuthority-bound controller, exact finite
negative constraints in existing events/artifacts, revision/revoke, post-Judgment
PASS/BLOCK/UNKNOWN, erasable outcome/disposition and filtered next-cycle view.
No Model/Memory/Subject authority path. Old blocked intentions do not revive.
Governed handoff uses existing ActionKernel checks and pre/post-transaction fence.
Only exact OfflineEffectPort on explicitv9 may exercise synthetic fixture actions;
no subclass/arbitrary CapabilityPort gets this exception, ordinary Shadow fences
remain. Fixture JSON is world data, not another subject DB/Store. No real effect.
Targeted22 PASS (R1/R2 + existing action/runtime boundary); latest R2 four PASS.
Full qualification/recovery matrix pending; not READY. No production changes.

## L3-C-AFFECT-V1 M3 — relationship and privacy axes
[实测·开发离线] R3 pure bounded RelationshipInfluenceView with seven facets,
domain trust/counterevidence and target-specific repair. Existing RelationshipView
retained; v9 personality/style/context use the same projector. Social expectation
comes from direct sourced norms/boundaries, not model assignment. Private social
meaning can cause self-restraint without becoming Manager authority. Hard context
privacy/task/destination/deletion/conflict checks preserved; secret canary excluded.
16 targeted PASS (new + prior projection/context); final four R1/R3 PASS after
normalized-link/time tie refinements. v9 adds only3 normalized relationship
columns on existing table; partial unreleased v9 checkpoints finalized additively.
No new tables/Store/loop; R4/R5/system qualification remain pending.

## L3-C-AFFECT-V1 M4 — positive requests and calendar opportunities
[实测·开发离线] R4 typed positive request → Subject ACCEPT/NEGOTIATE/DECLINE.
ACCEPT only offers existing CommitmentCandidate; trusted controller materializes
idempotently, no auto-adopt/Grant/send. Reuses CommitmentService/CAS and due
attention. Stdlib zoneinfo daily recurrence handles IANA zones, fold choice, gap
next-valid-minute, missed-window coalescing and persistent occurrence keys on
existing Scheduler. Calendar only emits SELF_WAKE checks, not user experiences.
Targeted8 PASS (new calendar/requests + prior scheduler/promises), latest2 PASS.
Queue metadata scrub extended for new structured personal fields; body remains
in erasable records only. v9 extends runtime_schedules CHECK, tables still39.
R5 experience and final scenarios/recovery remain pending, candidate not READY.

## L3-C-AFFECT-V1 M5 — disposition experience gate and checked learning
[实测·开发离线] R5 meaningful candidate gate selects consequence-backed, repeated
distinct or explicitly reflected dispositions. Raw veto/read/restart is not
automatically Experience. Typed independent verifier proves non-execution fact
without claiming reasoning correctness; later observed consequences supply a
separate assessment. Existing ExperienceService/Reflection/lesson trial/review
lifecycle supports NON_EXECUTION and a narrow consequence-review rule. Replaying
one candidate cannot create duplicate experience. Source erasure purges candidate/
proof/experience support while independent Manager source survives.
Targeted9 PASS (new experience + prior learning/privacy), final2 PASS. No new
tables: existing experiences CHECK extended and records opaque target lookup
column/index added; same Store/privacy/replay. Manager facts no longer become
automatic transitive normative dependencies in every future cycle.
Major full regression and final system qualification pending; NOT_READY yet.


## L3-C-AFFECT-V1 M6 — system and recovery qualification (OFFLINE)
[实测·开发离线] S1–S15 and two independent generic Subjects PASS; 60 virtual days
PASS with bounded pending/candidates/hot state, one veto history, no social/model
spam. Six actual tracked local SIGKILL/reopen cuts PASS, including UNKNOWN effect
verification without re-execution. Explicit v7→v9/v8→v9 preserves IDs/history,
foreign_key_check clean, managed backup/replay quarantine and erasure honored.
Production pins/real memory ingress unchanged. v9 adds0 business tables; default
C7 and D8 unchanged. Major full at f513dcc:900 passed/0 failed/1 skipped(E12).
Targeted C/D/new qualification:65 passed. Final full regression still pending.
Hardening: definition-only governance changes do not rewrite normative context;
resource classification is pinned to sourced cue and denied at realization;
post-check races persist veto without Action; filtered constraint view includes
revision/source/effective window. Hidden relationship counterevidence yields
PARTIAL/UNKNOWN coverage without loading its body. Source-erased disclosure is
unavailable. No real world/production/host/model/private input used.


## L3-C-AFFECT-V1 M7 — cancelled-action disclosure correction
[实测·开发离线] Pre-freeze full910 PASS/0 FAIL/1 SKIP,90.45s. Subsequent
semantic audit found a medium-severity disclosure-only bug: an Action cancelled
by later Manager veto could be projected as PLANNED when queried by Action ID.
A failing regression was retained before repair. Cancellation now resolves the
exact indexed sourced outcome (privacy/support checked) to MANAGER_BLOCKED or
UNKNOWN; possible/verified effects are not rewritten. No authority escape or
duplicate ingress occurred. Related source deletion still blocks disclosure.
Targeted suite and final full are rerun after this fix. No production changes.


## L3-C-AFFECT-V1 FINAL — OFFLINE_CANDIDATE READY (2026-10-15)
Current result supersedes pending descriptions in the historical M1–M7 entries.
R1–R6 IMPLEMENTED / SYNTHETIC TESTED / OFFLINE-VERIFIED. Qualified source:
09f45244d3d146e5381efb110fc8a89867a0f82e; final containing documentation commit
provides evidence hashes and does not change business behavior. Full911 passed /
0 failed /1 skipped(E12),93.47s. New23 PASS; existing C32 and D11 PASS.
S1–S15, generic two-Subject contrast, six actual local SIGKILL cuts,60 virtual-day
soak, explicit7→9/8→9 and managed backup/replay/delete closure all PASS.
One SubjectLoop/Store/Runtime; D WHEN, C WHAT/WHY; negative-only Manager after
Judgment; Grant/Budget/privacy remain independent hard gates. NEW_TABLES=0;
explicit9 only, C default7/D default8. No unresolved core invariant issue.
Reference: docs/nana_affective_autonomy_v1_implementation.md and evidence/manifest.
Production/main/R045/FIRST_REAL_ASTRBOT_SHADOW changed=NO; real models/private
memory/external actions=0. Production review/proof pins remain EMPTY. Real-memory
ingress remains deny-by-default. E12=NOT_RUN. These fixtures upgrade no real-host
status. Next step is independent offline review/integration; do not auto-deploy.

### C6/C7 + B6–B10 development — asset reuse

[源码] Branch dev/nana-core-c6c7-portable-subject-v1-codex starts at exact e26288e.
Reuses 21 Relational source assets from 67326d1 rather than a second implementation.
Explicit primary-user role and neutral fresh Subject bootstrap are local extensions;
existing identity/history unchanged. Validation: focused portable_subject tests.
No production, D2 or push. Design contract: docs/ADR/ADR-C6-B6B10-portable-personal-subject.md.

### C6/C7 + B6–B10 development — Surface continuity

[离线实测] Three synthetic surfaces enter the same SubjectLoop and identity;
source replay is deduplicated. L0/L1/L2 expose bounded, scope/privacy-filtered
references over the same Store, not new truth stores. Open namespaced descriptors
cannot extend closed authority/provenance enums. Two focused tests pass.

### C6/C7 + B6–B10 development — provider and frontend boundary

[离线实测] Provider descriptors and deterministic cognition/media ports reuse the
existing ContextAssembler/DeliberationSession; registry metadata grants no authority.
Embedding cache invalidates on provider/model/version/dimension/source revision and
is excluded from portability. Frontend session exposes typed projections/commands,
not DB/controller handles; future capability review stays proposal-only.
Validation: three focused provider/media/frontend tests pass. Real calls = 0.

### C6/C7 + B6–B10 development — controlled offline Subject transfer

[离线实测] Source retirement, existing managed SQLite backup/quarantine, bounded
three-file SubjectPackage manifest/hash verification, clean import and explicit
activation implemented. Exact destination controller/root, fresh runtime epoch,
old-grant revocation/budget reset and deletion-intent relocation preserve one
supported active lineage. Unknown host metadata blocks export; no journal rewrite.
Raw privileged archive/DB clones remain out of scope. Adds no business table/DB.
Neutral instance bootstrap is typed initial data; existing identities cannot be
rebootstrapped. Source-backed willing deference can accept where an unanchored
same request is declined, while retaining desire and rejecting indefinite control.
Validation: 17 focused tests pass, including v7/8/9→10, two distinct packages,
privacy/official replay, old authority fencing, model/media and frontend boundary.
No D2, real data/model/action, production or push.


### C6/C7 + B6–B10 FINAL — offline implemented/tested (2026-10-16)

[实测·开发离线] Explicit full-repository command `.venv/bin/python -m pytest -q tests`:
928 passed /0 failed /1 skipped(E12),90.73s. Targeted17 PASS,1.07s. Configured-directory
run455/0/1,53.65s is not mislabeled full regression. No business changes after full.
Implementation report and concentrated ADR document API/use, schema and limits.
File fingerprints in manifests/nana_c6_c7_b6_b10_v1.json (no self/anchor cycle).
Explicit development10,39 existing business tables,0 new tables/dependencies;
C default7/D default8 unchanged. No second subject Store/Runtime/SubjectLoop.
No real model/private data/external action/production/main/R045 changes; real memory
ingress remains NO; E12 NOT_RUN. This task upgrades no real-host verification.
No automatic push. D2–D7 remains recommendation only; task stops at this milestone.

## D2–D7 Living Autonomy V1 — integration baseline (2026-10-16)

[源码/文档] Independent branch from local4ad273f (not remote). Bounded comparison
against Relational67326d1 confirms prior source assets retained. Historical
Relational implementation/evidence and OSS9a9f8fe design reports carried forward
without claiming fresh validation. Construction plan is in
 docs/nana_d2d7_living_autonomy_v1_implementation.md.
No production/main/R045/real input/model/action; no push.

### D2–D7 M1 — bounded preemptible cadence

[离线实测] Added owner-thread bounded mailbox (durable ACK only after queue commit),
condition-generation wait (no lost wake), deadline/heartbeat bounded adaptive idle,
and safe-point preemption of background fixture cognition. Child process reaped;
queue resumes without duplicating Subject cycle. Explicit11 extends existing
jobs/record/call CHECKs/columns; no new business table. Default8 unchanged.
Targeted cadence2 PASS. Historical docs/evidence from67326d1/9a9f8fe preserved
with original provenance, not treated as this milestone's qualification.

### D2–D7 M2 — sustained offline goal/plan/action/verify path

[离线实测] Finite application-owned OfflineGoalPolicy adopts only C-endorsed,
source-bound candidates. The existing C SubjectLoop independently considers every
plan step; GovernedRealization/ActionKernel retain Manager/Grant/Budget/Verify.
Explicit11 jobs preserve step cursor and deterministic ingress identity across
restart/ACK gaps. UNKNOWN retains original effect identity and bounded verification,
never blind redispatch. Program registry grants no execution permission.
V11 action arguments/results/receipt/verification payloads use existing deletable
records/dependencies rather than copying personal body into immutable action rows.
Source erasure cancels future work, removes these payloads, preserves opaque history.
Targeted cadence/agency and prior realization7 PASS; real external actions=0.

### D2–D7 M3 — living maintenance, learning and operational projections

[离线实测] Interruptible bounded source scans persist cursor in existing jobs;
summary candidates require the same C SubjectLoop admission and remain INFERRED.
Source correction/erasure invalidates candidates and derived summaries. Explicit
sourced validity distinguishes event/observed/record/reference/valid time; historical
query never undoes erasure. Existing reflection/lesson trials alter later plans;
reviewed bounded offline procedure extension uses same policy/registry, no code install.
Resource reservations now cover byte/cost estimates and background subquota;
actual fixture bytes/latency/cost remain separately labeled. B10 runtime, needs,
Primary User, goals, Manager outcome and Living Journal projections are filtered,
rebuildable and authority-free; frontend input enters same runtime mailbox/queue.
Targeted new10 PASS; combined existing C/D + new53 PASS (30.78s). No new table,
model SDK, second loop/Store or real-world operation. Final qualification pending.

### D2–D7 M4 — complete life and dangerous recovery qualification

[离线实测] Reproducible four-virtual-hour demo uses actual Runtime/Subject/Store:
Primary choice differs without Grant/social-satiation override; voluntary finite
commitment persists/reviews; rest/no-input project; Manager blocks wanted action;
revocation does not execute; fresh sourced reconsideration; observed quality failure
→ C-selected reflection/verified lesson → self-wake → revised plan succeeds;
reviewed offline procedure enabled without new Grant; two surfaces share identity;
maintenance yields/resumes; restart retains identity and takes fresh epoch.
Demo ends0 pending intentions/0 model calls; all causal checks true.
Actual SIGKILL after durable effect/before receipt reopens and verifies one Action,
one EXECUTE, no duplicate effect. Explicit7/8/9/10→11 preserves IDs/FKs/table39.
V11 package transfer preserves goal/history, strips transient owner and revokes
old authority; no agency/port is automatically reconstructed on new host.
18 focused tests PASS, including bounded real process heartbeat/shutdown. Final
full repository regression still pending; no production/real models/data/actions.

### D2–D7 pre-final correction — temporal support and reservation fence

[离线实测] First full946 PASS/1 SKIP. Final causal audit reproduced an old validity
annotation remaining WITHIN after its direct support was explicitly corrected.
Regression retained; temporal projection now invalidates support at known-time
without backdating the correction into earlier knowledge. Also rechecks call cap/
in-flight reservations inside the existing reservation transaction. Targeted20
PASS. No authority/privacy gate relaxed. Final full will validate this fix.


### D2–D7 FINAL — living autonomy offline delivery（2026-10-16）

[源码/离线实测] Qualified source48174cb81002251dceec5dd54a1719e9ed61cc3d。
最终20 focused PASS；full948 PASS/0 FAIL/1 SKIP(E12)，98.61s；修复后的 temporal support
纠正边界和原子 reservation regression 均包含于最终 full。此前946 是修复前记录。
D2 owner-thread cadence/抢占恢复，D3 sourced生活状态，D4有限目标逐步执行，D5分片维护/
时态/Journal/学习，D6资源及UNKNOWN恢复，D7既有B10投影交付；详见 implementation。
四虚拟小时demo全部因果检查通过；真实本地SIGKILL保持EXECUTE1/effect1；显式7/8/9/10→11
保持39表/FK clean/历史，default7/8不变。短wall-clock进程检查heartbeat/shutdown。
只恢复 Relational 历史证据与 OSS 设计输入，不将研究冒充实现。实际实现无第三方源码复制。
main/R045/生产不变；真实模型/真实私人数据/真实外部动作0；E12 NOT_RUN；本地提交未push。
文档：docs/nana_d2d7_living_autonomy_v1_implementation.md；证据同名evidence/；
完整性：manifests/nana_d2d7_living_autonomy_v1.json（无自指，09为外部锚点）。

### E1–E6 M0 — local baseline and bounded source map

[源码/实测] Local HEAD30f7e6f confirmed, tracked worktree clean; old untracked bundle
preserved. New independent E1–E6 branch inherits C6/C7/Relational/D2–D7. Map in
nana_e1e6_open_autonomy_v1_implementation.md: explicit12 multi-goal, bounded generic
planning, delivery admission, independent learning, sandboxed code skill lifecycle,
existing Runtime/Kernel/privacy/portable/frontend reuse. bwrap namespace probe PASS;
no credentials/real endpoint used, no push. Implementation not yet qualified.

### E1–E6 M1 — bounded open planning and independent delivery admission

[源码/离线实测] Explicit12 removes only opt-in one_live_goal and adds goal priority,
deadline, parent/dependency and service-time metadata; default7/8/11 preserved.
Bounded generic operator planner validates references/preconditions/schema, same
C per-step judgment and sealed world Registry through existing governed Kernel.
Two persistent numeric/language goals interleave and reopen; six fixture Actions
verified. Social intent can remain endorsed while recipient admission defers BUSY;
no Grant/action from desire. Targeted7 PASS (new4 + inherited agency3).
No real endpoint/model/data/production; no push. Learning/code qualification pending.

### E1–E6 M2 — executed learning, generated code and media integration

[源码/离线实测] Same jobs/ExperienceService/Lesson lifecycle now supports recoverable
OBSERVE→VALUE→HYPOTHESIZE→BASELINE→PRACTICE→EVALUATE→TRANSFER→CONSOLIDATE→MONITOR.
Independent numeric/language splits execute actual transforms; checked strategy
changes C selected_method and subsequent plan. Failure-triggered reflection offers
same-goal replanning via a fresh C cycle; old failure remains. Timeout leaves cursor.
Generated Python first fails, repaired source passes bwrap isolated CPython tests,
reviewed hashed local realm activation/package/retirement works, no new Grant.
Existing B9 MediaSession feeds source-linked INFERENCE interest candidates to C.
New10 + existing C32/D2–D7 20:62 PASS,26.73s. No real models/private data/effects.
Small reusable fix: RecordService does not insert duplicate REVISION edge when
same old record is already a SUPPORT parent; erase closure is still retained.
Recovery fixes retain stable observation time and resume partially consolidated
learning/observation without re-execution. Final full/recovery qualification pending.

### E1–E6 M3 — integrated life, recovery, privacy and live projections

[源码/离线实测] Full synthetic story uses one existing Runtime/Subject/Store:
Primary/voluntary restraint, preserved appetite, busy-recipient deferral, rest,
three persistent goals, failure+interest learning, same-goal C-approved replan,
Manager veto/revoke/fresh review, real generated Python isolated execution through
Kernel, retirement, two surfaces, source erasure and restart. All boolean checks
PASS. Contrast uses other motives/tasks with plan lengths2/4, six verified actions.
Actual two SIGKILL cuts PASS: effect-before-receipt and Lesson-active-before-cursor.
Explicit7/8/11→12, legacy11 goal/action official replay and12 package transfer PASS;
39 tables, defaults7/8 unchanged, old Grants revoked, no realm/agency auto-restored.
B10 typed goal/learning/skill/delivery views and L0/L1/L2 reflect real Store results.
Fixed completed-concern re-adoption, scope-first work selection and source privacy
label propagation through action args/receipt/result and derived observations.
Personal read results cannot be downgraded by a PUBLIC goal; source deletion purges
input-dependent payloads. SECRET fixture feed is rejected before Core capture.
Targeted23 PASS,5.64s. Final full regression next; no real endpoint/production/push.

### E1–E6 M4 — plan dataflow revision fence before final qualification

[源码/离线实测] First full at c811850:971 PASS/0 FAIL/1 SKIP(E12),99.09s.
Subsequent causal audit retained a failing regression: a plan could name an input
operator absent from its path. Validate now requires preceding, unambiguous outputs;
step input lookup is bound to exact current plan record, never an older revision.
Suspended/retired strategy or locally unreviewed code is fenced before new Action.
Added actual eligible-recipient fixture contact/NO_RESPONSE and admission payload/
intention binding proof; world-change replan uses fresh observed values; monitored
lesson suspension stops an already-compiled plan. Targeted26 PASS,5.87s.
No authority escape observed, no invariant weakened. Final full next; no real use.

### E1–E6 M5 — execution input support freshness

[源码/离线实测] Full at1f01b77:974 PASS/0 FAIL/1 SKIP,98.00s.
A retained failing suppression regression showed a persisted action payload could
still be read after its newly linked input memory became non-current. Explicit12
Kernel payload resolution now checks supporting memory currency before obtaining
arguments/results. It fails closed without rewriting historical effects or retrying
UNKNOWN. Legacy≤11 behavior unchanged; new26 + inherited agency3 =29 PASS,6.25s.
Business implementation frozen here; final full follows. No new authority/endpoint.


### E1–E6 FINAL — freeze qualified offline implementation and evidence（2026-10-17）

[源码/离线实测] Qualified business source `ac0d934cfc116c55f75a597653579fba7ffdca8a`，完整继承本地
D2–D7 `30f7e6f5e0b6e935f7d27a2847a5107d261c4ef5`。最终文档批次不再修改业务源码。
完成显式12 bounded multi-goal/typed planning/recipient admission/independent staged
learning/generated isolated code review-use-retire，接入原B9/B6/B10、Runtime、Kernel；
修复已保留failing test的跨plan输入及non-current source payload问题，未放松断言或执行门。
为何：消除one_live_goal/fixed reading-card/data-only skill能力上限，并保留同一主体
来源、意愿/权限与隐私删除闭包；不将fixture当真实模型/外部能力。
最终验证：974 passed /0 failed /1 skipped(E12)，97.54s；新增26，focused29/6.25s；
恢复sanity5/0.78s。主生活3完成目标10合成核验动作，两领域baseline0/1→transfer1/1；
跨领域对照2/4步6动作；两真实本地SIGKILL、显式7/8/11→12、legacy官方replay、B8迁移
保留历史不恢复授权。独立worker实际Python3.13.5/bwrap；Core3.12.14/SQLite3.53.1。
同步07/08/09/04当前状态、追加10裁决、完整报告/小型JSON证据/生成代码candidate；最终
acyclic指纹清单排除自身及09，在09留hash锚点。数据源均synthetic，无DB/凭据入库。
无新依赖/业务表，默认C7/D8不变。生产/main/R045/真实模型/私人数据/真实外部动作0；
E12 NOT_RUN；本地提交，不push。真实接线阻塞和导出/原始clone边界见报告limitations。

## World Loop V1 M0 — local source and environment anchor（2026-10-17）
[源码/实测] 新分支继承完整255ac99，无远端替代或旧成果丢失。有限检查既有C/D/E模块、
privacy/provenance/schema/port边界，记录实现地图；ffmpeg/ffprobe/Pillow/bwrap已存在，
managed provider配置为空。开始显式13开发，不升级生产，不push。业务代码尚未变更。

## World Loop V1 M1 — durable cognition, temporal beliefs and actual codecs
[源码/离线实测] 显式13新增4个索引化header表，正文仍在同一Record/Privacy体系；默认7/8不变。
实现HTTPS structured transport与本地HTTP harness、先写CALLING、超时/重复/过期/来源删除
语义；现有ContextAssembler支持必需来源但不绕预算/隐私。世界信念有event/valid/known时间、
冲突/显式纠错/无复活投影。真实PNG像素/音频PCM/视频多点解码；FFmpeg在无宿主数据/网络
namespace里运行，限制资源；不冒充ASR/语义视频理解。9项foundation测试通过（与后续
dynamic goal/learning合计11 targeted通过），真实provider未配置/NOT_RUN。无生产/push。

## World Loop V1 M2 — open concern selection, independent episodes and skill needs
[源码/离线实测] 动态Objective只在受限资源描述范围内成为候选，仍由原C采纳；关注/兴趣/
目标分层持久化、去重、复访、退出，并复用同一LivingWork。transport-backed planner/
learning/code proposer可替换；模型不接触Store/Grant/Manager。新world输入可来源化地
提供旧目标replan机会；world belief通过原ContextAssembler隐私过滤进入认知。
跨episode独立oracle核验、反例暂停/证据比例、未解决反例禁止重启用；两类纯JSON代码
技能从C capability-gap判断进入生成失败/诊断/修复/隔离测试/review，启用不等于Grant。
实际SIGKILL发现并修复：C/goal已提交而Concern ACK未提交时，queue已DONE不应反复
提交旧envelope；现在重放幂等post-commit处理，不生成第二decision/goal/effect。
同时避免managed concern被通用watch再次驱动；已形成Reflection候选的工作完成后不占
永久pending槽。Legacy<=12保留。20项新targeted与26既有open tests当前通过；最终soak/
全量仍待验。真实模型/外部动作0，未push。

## GLOBAL_STAGE E M3 — decoded world causality and bounded recovery（2026-10-17）
[源码/离线实测] 实际PNG/WAV/MP4文件解码的技术结果现在进入同一Store的world belief；
不是语义模型理解。视频使用真实frame PTS/索引/采样区间，公开导入拒绝link/FIFO。
补全model proposal→C candidate→plan/code/hypothesis的Record依赖，来源删除可闭包；
同时修复把全量transitive support强制塞进模型造成预算溢出：只pin有界相关来源，完整
provenance仍保留，Context预算/完整冲突/隐私不放宽。post-judgment provider/context
失败park，不无穷重试、不重写判断。统一原Runtime与model transport的调用/字节/成本
reservation，真实未知billing不伪装0。对用户GLOBAL E纠偏追加能力矩阵/路线口径。
51 targeted通过（含两个26h世界、两实际SIGKILL/迁移），额外public file边界5/0.76s。
完整回归与30min实际wall-clock进行中；真实模型/外部动作/生产/push仍0。

## GLOBAL E qualification follow-up — transparent accounting / stronger history proof
[源码/离线实测] 保留失败回归后修复：已成功PROPOSED但billing缺失时，成本未知计数不能
变成0。新增真实HTTP回包后world revision变化的stale测试；记录每个goal的已提交
candidate/intention/cycle/SELF_WAKE concern谱系。7/8/12→13迁移测试现在迁移非空C历史，
验证旧Memory、全部Record IDs与已提交Cycle保留，不只验证空Store身份。targeted boundary
7通过/0.96s，recovery7通过/1.42s，26h主/对照system2通过/16.41s。全仓库显式tests回归中。

## GLOBAL E temporal-expiry fence and actual transport role qualification
[源码/离线实测] 保留失败回归后修复：belief自然跨过valid_until而未新增revision时，旧认知
上下文仍可能被接受。world stamp现包含来源的当前有效区间状态；有效期跨界即STALE，
不因微秒正常流逝无故invalidate。新增实际HTTP LEARN proposer→原九阶段→独立核验/
Lesson的接线测试；REFLECT回包不自行创建Experience/Lesson。World suite30通过/21.72s，
含两个26h综合世界；初次全仓1002通过/1 E12跳过，最终新增测试后的全仓待重跑。
实现文档说明模块/数据/时态/迁移/边界/复现命令，未新增第二学习或技能系统。

### GLOBAL E closeout M6 — repair retained regressions and qualify durable boundaries
[源码/离线实测] Resume exact9e7ce710 after authorized two-ref history sync; preserve old
unrelated bundle and finish legitimate dirty tests/evidence on the same branch. Fixed
retained strict-schema wire mismatch, origin promotion and counterexample/suspension
commit gap; each reproduced failing before repair. Audio technical records preserve
source codec/rate/channels, never transcript or semantic claims. Existing world
SIGKILL worker now covers PREPARED/proposal/concern/C commit/world revision/strategy
commit/skill cursor/deletion anchor, alongside CALLING/adoption and inherited effect/
learning cuts. Same Store/SubjectLoop; all authority and privacy gates preserved.
Focused world + inherited recovery46 PASS before final added provenance assertion;
latest dangerous-boundary/learning/recovery27 PASS. Final whole repository regression,
updated scenarios and active30-minute wall-clock Runtime soak follow. Not READY yet.
No push/main/R045/production/private/live model operations in this task.

### GLOBAL E closeout M7 — epistemic and deletion-liveness closure
[源码/失败回归→修复] WorldModel previously checked raw evidence kind but not the
referencing Memory's derived status. A SUMMARY could therefore present a newly
invented RAW_OBSERVATION while citing a genuine original Evidence. Reproduced and
fixed locally: RAW/VERIFIED/USER claim admission requires direct, observation/
statement Memory too. Summary remains a summary; no base Memory semantics changed.
A second retained regression showed erased concern headers could permanently fill
hot attention capacity. Only ACTIVE source records now count against that budget;
opaque historical rows remain and deleted topics cannot revive. Added one compact
transient→revisit→independent interest→source erasure and restart→expiry lifecycle
qualification. No table/authority/SubjectLoop added. Current boundaries/life16 PASS;
earlier full1014/0/1 at M6 retained as historical, final full follows these repairs.

### GLOBAL E closeout M8 — populated D history and world portability proof
[离线实测] Strengthened existing migration tests with actual v8 Runtime queue/C
history before13 upgrade, and an actual sourced world belief before SubjectPackage
transfer. Four targeted checks PASS, IDs/queue content retained, FK clean and old
Grants revoked. No business code change. Latest full1017 PASS/0 FAIL/1 E12 SKIP,
125.41s; world43 PASS/34.36s. Full will be captured on this final test tree too.
Correction: M7's boundaries/life count was15, not16; raw command output is retained.
The final evidence uses executable outputs, not that transcription error.


### GLOBAL E FINAL — freeze source-backed offline qualification
[源码/实测] Final business07b736a / test55ce086; full1017 passed/
0 failed/1 skipped(E12), World43 passed. Updated implementation,
A–J capability matrix, compact evidence/actual fixture DB counts,12 local SIGKILL
cuts, explicit13 migration/portability and long world/contrast/wall process proof.
Actual wall Runtime 1800.131s, separate30s final-source smoke. No old interrupted
soak duration reused. Source chronology is explicit, no false hot-reload claim.
Five failing-before-fix defects repaired without weakening privacy/authority/C/D;
no new subsystem/table/dependency in closeout. Only historical Stage E headers add4
same-Store tables, total43. Fixed M7 transcription via explicit M8 correction.
Local final save only; no push/production/main/R045/private/live-model operations.
Why: complete existing World/Cognition/Concern integration and its causal recovery,
rather than build duplicate planner/learner/agent. Qualified offline readiness is
separate from live semantic-provider, ASR and device/social qualification (NOT_RUN).

### H1 M1 — typed media interpretations enter the existing world
[源码/离线测试] From frozen dcaf30fe on independent H1 branch. Added bounded media
DTO/packaging, image/audio/video wire adapter and same-session interpretation→model
belief materialization. Source-only ContextAssembler option excludes unrelated
memory without lowering privacy/token/conflict checks. No schema/table/default/
Runtime/SubjectLoop/authority change. Initial16 H1 tests PASS; actual generated
public codecs only, narrow SYNTHETIC semantic oracle; live semantic/ASR NOT_RUN.
Why: distinguish media meaning proposals from technical decode and verified truth.
No push or production/private/live side effects.

### H1 M2 — same-Subject priorities and recoverable semantic life
[源码/实测] Added finite decoded video/audio association, primary-source focus on
synthetic proposer, typed media→C priorities, actual5 SIGKILL cuts and portable
semantic history/recovery proof. Paired48h worlds exercise original F planning,
G9-stage learning and I skill lifecycle; no new planner/learner/Store/loop. A
transcript-shaped wrong fixture remains MODEL_DERIVATION, never a user command.
Known generated pixels supply independent later verification, not model echo.
Source-only privacy and unknown billing preserved. Updated report/default H1 test
path. Initial main48h causal checks pass; contrast uses different needs and REST.
Final full/frozen scenarios/wall qualification follow. No production or push.

[H1 M2 follow-up / failure→fix] Retained failing metadata-routing regression proved
media source-only context still carried full source Memory.text. Media requests
now project citation/epistemic metadata only; typed validated parts carry content.
Ordinary C/D ContextAssembler defaults remain unchanged. Final focused32 PASS.
No new privacy access, authority, table or worker. Final full/evidence next.

### GLOBAL H1 FINAL — freeze semantic grounding offline candidate
[源码/测试/离线运行] Business/test anchor20758ecec2ef02efc3459985051cfbc3036b4697,
base dcaf30fe. Same-session typed media proposal, provenance/confidence/span/coverage,
source-only metadata context, original world conflict/correction/UNKNOWN, delete
closure and C-owned attention. Why: give the same Subject revisable media meaning,
without a perception brain or new authority. F planning/replan/G9-stage formatting
learning/I generated skills actually reused; no new subsystem/table/worker.
Final focused32 PASS/23.726s; full1049 PASS/0 FAIL/1 E12 SKIP/147.227s JUnit
(147.32s CLI). Actual5 SIGKILL and portable semantic-history retention PASS.
Main48.0953h:3 goals/6 verified local synthetic actions/1 lesson; contrast48.1025h:
2/4/0, distinct source fields/priorities/REST and no invented learning claim.
Final-source Runtime wall301.344s, FD4→4, queue0, identity stable,6 local HTTP calls.
Media real-model quality/ASR/live capture NOT_RUN; narrow public synthetic oracle
and wrong transcript contract fixture explicitly not accuracy evidence.
Append current roadmap/task/state/decisions, A–J/runbook/evidence/final fingerprints.
Source-only prose routing regression retained then repaired. No dependencies/schema
migration/default/production/main/R045/private/live model/social/external action/push.

## H1-LIVE provider qualification — BLOCKED_NO_CONFIGURED_PROVIDER（2026-10-17）
[实测/当前配置观测 + 源码审计] 独立开发分支
`dev/nana-core-h1-live-semantic-provider-v1-codex`，base H1 `f6aabc3c8e8712b811540764a3937cc9283861af`。
managed spec204/current观测：capabilities/secrets/runtime_variables/outbound_identities均为空；
任务未提供exact provider/model/endpoint。未搜索secret/读取生产配置/调用provider。
按本轮附件§3/§30完成有界readiness audit后停止：真实调用0，预算0，
LIVE_PROVIDER_QUALIFICATION=BLOCKED_NO_CONFIGURED_PROVIDER；不是失败模型或语义PASS。
H1 OFFLINE_CANDIDATE_READY保持；历史1049/0/1、focused32、5 SIGKILL不重跑、不冒充LIVE证据。
发现后续live measurement需保留provider-native response/request ID及raw response digest，
现有typed reply digest不能冒充raw HTTP fingerprint；无provider时不做猜测性实现。
源码/schema13/43表/权限/Runtime/SubjectLoop不变。E12/real ASR/OCR/quality/capture/Hands
仍NOT_RUN；无生产/main/R045/私人数据/外部action/push。报告及证据见
`docs/nana_h1_live_semantic_provider_readiness.md`和同名evidence目录。

## H1-LIVE TianToken — PARTIAL_PROVIDER_QUALIFICATION（2026-10-17）
[实测/开发真实relay调用 + 本地核验] 当前分支dev/nana-core-h1-live-semantic-provider-v1-codex，
base c3cd0017。用户明确授权临时凭据及TianToken；公开/api/status链接到官方Apifox文档，
确认https://api.tiantoken.com/v1/chat/completions，Bearer；不是猜测endpoint。
请求/返回model=qwen3.8-flash；UPSTREAM_IDENTITY=RELAY_CLAIMED_UNVERIFIED，非永久默认。
实际9请求（models1/text1/image6/video-visual1），MEDIA3 PROPOSED/1 strict格式FAILED/
3 UNKNOWN超时，未知call key不重发。OCR同一生成字符串两次正确；shape结果有缺项。
视频/视觉注入无已接收响应，LIVE质量/攻击guard NOT_RUN，不升级为全面资格PASS。
已接收真实解释→MODEL_DERIVATION Memory→原WorldModel→有来源的本地实验review/Concern
→唯一原C，WATCH/BACKGROUND_WATCH/NO_ACTION；0 Action/Grant/adopted Goal。
本地真实payload变异关联/model/authority拒绝，stale/deleted为STALE；独立进程重开同identity，
不回调provider/不重复C，删除传播后不从audit复活正文。控制CALLING cut不是live SIGKILL。
同序号不同观察顺序导致实验调用方predicate冲突，Core保持CONFLICT；新调用方用request scope，
旧历史不改。独立像素定位来源补充一条缺region解释，未虚构错误OCR或强制truth winner。
HTTP观测新增允许字段DTO，旧reply缺字段时原digest不变；schema13/43表/新增0，依赖不变。
full1060/0/1(E12)，focused42 PASS；另一次focused出现1次既有FFmpeg sandbox非零退出，
原因UNKNOWN；不改decoder边界，单独2-case及focused42复核通过，失败记录保留。
relay usage已返回部分token/cost字段，实际费用单位/结算未知，ACTUAL_COST=UNKNOWN。
业务代码唯一改动为HTTP观测；其它仅qualification工具/测试/文档。临时凭据不写仓库/日志。
无H2/Hands/capture/生产/main/R045/私人数据/真实外部action/social send；E12 NOT_RUN。
报告：docs/nana_h1_live_semantic_provider_qualification.md；证据：同名provider_evidence目录。

[H1-LIVE collector follow-up / failure→fix] Timeout行不得引用上一条completed envelope的
usage/ID。修复实验收集器并保留回归，删除UNKNOWN行不相关metadata；Core没有复用/接收
旧响应。最终11新增guard PASS；完整1060 PASS/0 FAIL/1 SKIP(E12),151.84s。

### Provider routing P1 — host configuration foundation (2026-10-17)
[源码/离线测试] From verified remote ba798b2 on independent provider-capability-routing
branch. Typed host-local JSON schema1, private atomic/CAS persistence, dependency
checks and explicit memory-only SecretResolver contract. Existing ephemeral B9
Registry accepts stable profile keys and disambiguates same remote name by provider.
25 targeted/B9 tests PASS,2 actual local SIGKILL cuts. No Subject table/schema,
secret/provider call or H1 historical PARTIAL upgrade. Router/frontend still pending.

### Provider routing P2/P3 — pre-dispatch selection and existing session factory
[源码/离线测试] Typed intersections, exact-model, profile-specific fixture and explicit
OpenAI-compatible construction. Fallback exists only in resolution before call;
UNKNOWN/malformed never re-dispatch. Immutable route snapshot persists in original
CognitionRequest, optional absent field retains old hashes. Old PREPARED request
cannot dispatch using changed route/model. Native loopback Text/Vision/sampled Video
reuse same H1 path; generic fixture media/embedding retain old B9 interfaces.
43 routing/B9/open-media focused PASS;0 real provider calls. Frontend/transfer
qualification pending. No new Subject table/schema, Runtime or SubjectLoop.

## 2026-10-17 Provider routing P4/P5 — implemented/tested offline

B10 PROVIDER_SETTINGS typed application transitions, revision CAS, dependency-safe removal, native loopback and B8 transfer exclusion implemented. Retained routed media sessions reject changed config. Sanitized original Cognition journal projects route provenance without credentials. Combined focused/B9/B10/H1/open-autonomy: 103 passed; full regression pending. Subject schema13/tables43 unchanged; H1 historical PARTIAL unchanged; real provider calls0.

## 2026-10-17 — PROVIDER_CAPABILITY_ROUTING_V1 final offline delivery

[源码/离线实测] Configuration schema1; compatible Registry; capability routing and existing transport factory; B10 settings/CAS; B8 host-config exclusion; embedding rebuild; sanitized call provenance; retained session target/revision fences implemented. New focused42 PASS, combined focused114 PASS, final full1102 PASS/1 E12 skipped/0 failures. Initial full also1102 PASS/1skip. Two process SIGKILL config checkpoints PASS. Subject schema13/43 tables, new dependencies0. Real calls0, no key reuse or environment/history discovery. H1 historical PARTIAL unchanged. Report/evidence: docs/nana_provider_capability_routing_v1_implementation.md and matching evidence directory. Local normal commits; current branch push authorized by this task, verified separately at handoff. No main/R045/production/device/social changes.

## H2 P1 — source contracts/config, 2026-10-18
[源码/离线测试] Verified remote a4abd5ce anchor; independent h2 branch. Typed host-local source schema1 reuses existing private atomic JSON primitives; explicit injected resolver, no model/host discovery or capture permission from kind. Source/Provider config focused36 PASS. No schema/table/dependency change. Real devices/provider/private content0. Coordinator/H1 temporary payload/runtime qualification pending.

## H2 P2–P5 — bounded ingress / original Runtime / ephemeral H1, 2026-10-18
[源码/离线实测] Source and Provider config first-stage count correction: 34 PASS (not36 in P1 entry). Existing H1 accepts digest-only frozen media with validated memory-only attachment; original full-envelope legacy path retained. H2 technical capture, typed source provenance, private in-memory PCM, safe flat-file reads, exact/temporal dedupe, original Scheduler opportunities, C-source WATCH bounds, user preemption, host/Manager veto, B10 source settings and B8 exclusion implemented. 63 H2 tests PASS, six actual local SIGKILL cuts; combined pre-final focused146 PASS. Follow-up metadata decode/capture tests green. 24 virtual hours mixed sensors PASS. Wall soak/final fresh-process full regression pending. Schema13/43 tables unchanged, new dependencies0, real devices/provider/private data/actions0. H1 historical PARTIAL retained.

## H2 recovery/resource follow-up — 2026-10-18
[源码/针对性测试] Treat unavailable adapter health/metadata and OS capture failures as SOURCE_UNAVAILABLE, with zero bytes read for denied health. Exact-digest semantic debounce is scoped to current routing revision, so a model switch/recovery does not silently reuse an older interpretation. Targeted capture/boundary/runtime43 PASS; recovery/capture/runtime32 PASS. Initial full/180s soak were already running against prior committed source; they are preliminary only. Final fresh-process qualification will run from this fixed source, with failures preserved and investigated. No authority/privacy/source history weakening.

## H2 final source freeze — 2026-10-18
[源码/离线实测] Event-driven metadata producers now use original Runtime.post(), with exact volatile pull/expired samples. Source revisions use monotonically increasing config revision on recreation, preventing stale capture/WATCH identity reuse. Trusted descriptor privacy floor cannot be downgraded by settings; Manager binding digest veto covers profile aliases. One pending periodic tick per source under user pressure. H2 focused69 PASS. Prior source full1166 PASS/1 E12 skip, existing rechecks202 PASS,180.064s synthetic wall soak PASS; final source fresh-process rerun pending. First full failure was missing /tmp legacy SQLite launcher, retained. Restored only ephemeral launcher to actual /usr/bin/python3 (Python3.13.5/SQLite3.46.1), original isolation test PASS; no mocked version/source/production modification, no new dependency.

## H2 final offline delivery — 2026-10-18

[源码/离线实测] H2 source ingress and original Runtime integration complete.69 focused PASS;202 existing rechecks PASS; final fresh committed-source full1171 passed/0 failed/1 E12 skipped (158.02s). Six actual SIGKILL cases PASS,24 virtual hours/3 sources/queue max5/hot requests64/27 synthetic semantic calls,180.039439s actual wall/17 captures/17 semantic calls/FD4→4/threads1→1/RSS peak growth8832KiB. Source qualification at798cc33; final docs/evidence commit changes no business code. Preliminary missing /tmp legacy launcher failure retained, restored only local actual3.46.1 launcher and isolated test passed. New H2 records have no raw media; prior historical H1 full envelopes unchanged. Schema13/tables43/new0/dependencies0. Source config separate from Subject/B8. No real devices/provider/key/private data/main/R045/production/Hands/social action. H1-LIVE PARTIAL unchanged. Reports and small evidence under docs/nana_h2_perception_ingress_v1*. Final dev push authorized by attachment; verified separately at handoff.


## H2-LIVE P1 — explicit capture contracts/provenance, 2026-10-18
[源码/针对性测试] From verified remote06c80a9 on independent h2-live branch. Add controlled-screen backend/receipt contracts and default-deny host port, PUBLIC-only real ingress; exact pixel/time/size/binding verification, source revision recovery fence, RGB semantic debounce and bounded transitive source-backed WATCH. Existing H2/Router/H1 reused, no schema/table/dependency change. 87 H2+screen targeted tests passed before final compatible absent-field serialization adjustment; focused confirmation recorded by commit/run evidence. Actual controlled OS pixels proved feasible; final qualification/wall/full still pending. No private desktop/provider/Hands/production.


## H2-LIVE P2 — owned display runner/source freeze, 2026-10-18
[源码/实测] Optional stdlib ctypes X11 host harness creates its own private-auth dummy server/window, renders public test graphics and captures only that drawable using XGetImage. No ambient display/window listing, hardware input or desktop crop. Process parent-death cleanup; serialized harness ownership prevents displayfd startup contention; before-fix combined run171 PASS/1 failure (resume handshake), retained in final limitations. After-fix87 H2+screen PASS,18 focused PASS, final A–J smoke PASS. Runner has mandatory live flag, finite scenes/wall/virtual/crash/resume commands, source/session revision renewals, no provider credential. Source frozen by this commit; final fresh-process qualification, >=300s real wall soak and full regression must follow.


## H2-LIVE final source-qualified delivery — 2026-10-18
[实测/受控 OS] On frozen86b7d18:18 explicit focused PASS including six actual
SIGKILL real Xorg captures/recovery; full default1178 PASS/0fail/12skip (11 opt-in
live passed separately +1 E12),159.68s. A–J13 captures,24 virtual hours25 captures,
300.045719563s actual wall29 captures;FD4→4/threads1→1/RSS growth23176KiB,own server
cleanly stopped. No raw screenshots/auth cookie in three development Stores or
text evidence; clean foreign keys, schema13/43tables/new0/dependencies0, Actions/
Grants0. Actual B8 transfer/new host identity, Manager preserve WATCH, preemption,
backpressure, stale topology/rebind and pixel/time debounce verified. Docs/evidence/
manifest added, no business code after freeze. Final statusREAL_OS_SCREEN_QUALIFIED
only L1; no physical/user desktop, real provider/camera/mic/OCR/Hands/Iris/production.
H1-LIVE historicalPARTIAL unchanged. Old bundle left untracked and unread.


## VISION_FIRST_SHARED_GROWTH_V2 — implementation started
[远端/源码核验] Base9faaad5006159c4f69f5c4056f0c6b062cc7770b; current independent
dev/nana-core-vision-first-shared-growth-v2-codex. C6/C7 and E1–E6 ancestry confirmed.
Dual durable priorities: Self-Evolution + Shared Life; current B+C causal increment
with small context-fit A. Existing C/D/F/G/I/J reused. Scoped dialogue assessment,
heldout separation and verified-reuse-to-life projection are actual gaps; no new
brain/Store/Runtime/schema, no H2 feature continuation. ADR-VF2-001 records bounded
audit/contract. This entry is planning/started, not implemented/qualified. Real
AstrBot/QQ shadow requires later explicit host/privacy authorization; real dialogue,
production Core adoption, general deep self-modification remain NOT_RUN.


## VISION_FIRST_SHARED_GROWTH_V2 — implementation checkpoint
[源码/定向测试] Original C now owns optional sourced ContextFitAssessment; exact
entity/scope/topic refusal/reopen uses existing SUBJECT_EVENT target IDs and
privacy closure. Explicit context never becomes Manager/Grant. Unrelated activity
survives casual chat; focus yields through original reactive D priority. Temporary
conversation uses bounded process-local queue ingress envelope, not capture-all
Memory; metadata strips signal, finish/stop drops it, restart cannot recover body.
Existing G proposals now see LearningProblem(practice only), not evaluation/
transfer examples/answers. Old full LEARN input is sanitized before HTTP; accepted
history stays intact. Original nine stages/Kernel/Experience/EpisodeLearning reused.
Source-bound ongoing learning pauses on topic refusal; reopen alone does not resume;
new C endorsement required. Adopted plan steps/reviews follow original C binding
and recheck current boundary before further work.

Verified novel later reuse can project a current optional growth-life opportunity
through original D collector/C; existing due work has priority, no second loop or
new table. Busy/unknown means WATCH; explicit no-interest closes that topic. Missing/
deleted sources or suspended strategy remove support. Two model fixtures tolerate
method lessons without reading-specific keys; identity/authority unchanged.
Development demo actual local result4 vs4.75 before,10.75 vs10.75 later; independently
checked heldout/transfer, candidate sharing/silence, source-withdrawal arm and true
float counterexample pass. This is controlled local fixture computation/strategy
selection, not real dialogue or general algorithm invention.165 earlier related
tests passed;11 new focused passed. Final frozen-source full regression pending.


## VISION_FIRST_SHARED_GROWTH_V2 — final scoped delivery
[实测] Sourceadb4b5b;11 focused PASS; full1189/0/12 intentional skips,163.16s.
Original controlled local G/F path shows independent capability selection/reuse
improvement, while new derived C/D projection shows separate life-causality
change. Actual Memory deletion ablation, busy/refusal, counterexample suspension,
restart and fixture-model swap verified. No invented algorithm/general Core
self-edit or real dialogue claim. Context fit is source-bound host interpretation;
privacy/authority are independent. Practice-only proposer fixes heldout exposure.
Original due opportunities precede optional growth-sharing checks. No new table,
schema/dependency/Store/loop. First full missing temporary SQLite launcher failure
retained; restore used actual system3.46.1, no source/test/R045 modification.
Report/evidence under docs/nana_vision_first_shared_growth_v2*. Stop after normal
development push/remote verification; no production/private/live integration.


## VF2 evidence tracking closure
[只读Git核验/文档修正] Generic *secret* ignore rule excluded the sanitized
secret_scan.json result from the first handoff docs commit. Reviewed its fields
(count0, no credential values) and explicitly whitelisted that text evidence.
Manifest content/hash and qualified source remain unchanged. All manifest paths
must now exist in committed Git history. Normal follow-up commit/push, no amend,
force push or business/source/test change.


## REAL_LIFE_V1 M0
[只读核验/文档] Fetch verified94016fcb; clean tracked workspace, old bundle untouched.
Created one mission ledger/map and current PROJECT_BRAIN entry to drive practical
U/L/P/S increments. No business implementation/qualification claim yet.


## REAL_LIFE_V1 M1 — practical project work
[源码/开发实测] Added bounded explicit-source port, no-exec AST inventory/compiler
oracle, dev CLI and original C/F/G workflow. Produced recurrence/extensions real
source reports, kept original failure, selected tested AST method and reused it.
Fixed goal-step/review wake privacy to inherit source instead of default PERSONAL.
19 targeted PASS; no new schema/table/dependency/private/model/external effects.
P/S and final source qualification pending; original bundle untouched.
