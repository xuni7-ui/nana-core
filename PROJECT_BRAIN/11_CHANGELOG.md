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
