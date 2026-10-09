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
