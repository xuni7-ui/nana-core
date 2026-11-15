# 上传白名单（Upload Whitelist）

> 创建：2026-10-10 CST ｜ 原则：**白名单制**（默认禁止，仅列出的才允许）；**不依赖 `.gitignore`**。

## 一、允许入库（白名单）

### A. 文档与清单（安全）
- `AGENTS.md`
- `README.md`
- `PROJECT_BRAIN/*.md`（全部 **18 个**：事实层 00–06 + 账本层 07–11 + 核验层 12–18）
- `bridge/**`（**9 个**：协作桥最小闭环 + 探针 + 任务样本 + 测试）
- `docs/*.md`（含 `docs/c5v_wiring_design.md`、`docs/migration_report_20261010.md`、`docs/verification_and_fingerprint.md`）
- `manifests/upload_whitelist.md`、`sensitive_scan_report_20261010.md`、`proposed_commit_manifest.md`、`fingerprints_20261010.md`
- `upstream/*.md`（第三方来源登记，仅元数据）

### B. 奈奈原创源码（扫描通过）
- `src/plugins/astrbot_plugin_nana_admin_guard/{main.py,metadata.yaml}`
- `src/plugins/astrbot_plugin_nana_anchor/{main.py,metadata.yaml}`
- `src/plugins/astrbot_plugin_nana_bilievent/{main.py,metadata.yaml}`
- `src/plugins/astrbot_plugin_linna_tmp/{main.py,metadata.yaml}`
- `src/bili_agent/*.py`（**12 个**，已逐文件扫描通过）
- `src/bili_agent/notes/*.md`（笔记 + 缺陷记录）
- `src/c5v/{README_c5v.md,bili_video_vision.py}`

### C. 条件入库（需姐姐逐项批准）
- 🚫 **首发排除**：Iris 插件 **奈奈改动 diff** `manifests/nana_iris_changes.diff`
  - 含 AGPL-3.0 衍生代码上下文 → 若入库则**整体须 AGPL-3.0 并提供署名**；首次同步**不带它**（见 `18_GITHUB_REMOTE_VERIFY_01.md` §6）
- ⚠️ 奈奈自制插件**缺少 LICENSE** → 入库前须指定许可

## 二、明确禁止（黑名单）

| 类别 | 路径示例 | 原因 |
|---|---|---|
| 全局配置 | `data/cmd_config.json` | 含 API Key |
| 数据库 | `data/data_v4.db*` | 含会话/记忆 |
| 日志 | `data/logs/*`、`*.log` | 含运行信息 |
| 凭证 | `*credential*.json`、`*password*.txt` | 登录凭据 |
| 聊天记录 | `对话流水/*.jsonl`、`merged_memory.*` | 私人隐私 |
| 事件数据 | `bili_event_log.jsonl`、`bili_comment_log.jsonl`、`bili_event_state.json` | 运行态数据 |
| 秘密目录 | `/root/.nana_secrets/**` | 凭证+源码混合 |
| **硬编码密钥文件** | `test_bili_agent_semantic_retry.py` | **已阻断** |
| 第三方整包 | 各上游插件源码 | LICENSE/署名风险 |
| AstrBot 主体 | `/AstrBot/astrbot/**` | 体积+AGPL+非本项目 |
| 无关产品线 | `nana_dsh_whale_*` | 与 nana-core 无关 |
| 编译产物 | `__pycache__/`、`*.pyc` | 无用 |

## 三、入库前置检查（每次必做）

1. 文件在白名单内 ✅
2. 敏感扫描通过 ✅
3. 许可证核对通过 ✅
4. 无不可逆操作 ✅
5. 人类验收通过 ✅

## 四、口径备注

- 「**敏感扫描通过**」的精确含义 = **密钥值 0 命中**。`sessdata` 等**键名**出现在源码中属正常（读 cookie 必需），**不构成泄露**。
- 首次同步基线 = **66 文件**（本地 67 − 排除 `manifests/nana_iris_changes.diff`）。
- 远端 `xuni7-ui/nana-core` 首核结果：private、默认分支 `main`、仅 `Initial commit` 1 个文件 → 详见 `PROJECT_BRAIN/18_GITHUB_REMOTE_VERIFY_01.md`。


## Nana Core V1 S0—S4 增量白名单（用户授权，合成资料）
- `src/nana_core/**/*.py`、`src/nana_core/storage/schema_v1.sql`
- `tests/offline_continuity/*.py`
- `pyproject.toml`、`requirements-core-dev.lock`、`.gitignore`
- `docs/nana_core_v1_implementation.md`、`docs/nana_core_v1_test_output.txt`
- `docs/nana_core_v1_evidence/*.json`、`docs/nana_core_v1_evidence/junit.xml`（全合成，逐文件扫描）
- `manifests/fingerprints_nana_core_v1.json`、`manifests/nana_core_v1_review.json`
- `PROJECT_BRAIN/{00_INDEX,04_verification_status,08_TASKS,09_STATE,10_DECISIONS,11_CHANGELOG}.md`（本阶段追加）
- `LICENSES_AND_PROVENANCE.md`（仅新增来源登记）
不纳入 `.venv/`、DB/WAL/lock、wheel、运行目录或真实凭据。

## Nana Core V1 S5 增量（用户本轮开发与 GitHub 交付授权）
- `src/nana_core/semantic/*.py`、`tests/semantic_migration/*.py`
- `tests/offline_continuity/test_experiment.py`（仅 E12 跳过理由文字更新）
- `pyproject.toml`（CLI/测试入口，不新增依赖）
- `docs/nana_core_s5_implementation.md`、`docs/nana_core_s5_config.example.json`（空端点）
- `docs/nana_core_s5_test_output.txt`、`docs/nana_core_s5_evidence/{*.json,*.xml,initial_collection_failure.txt}`（全合成）
- `manifests/fingerprints_nana_core_s5.json`、`manifests/nana_core_s5_review.json`
- PROJECT_BRAIN 状态、任务、决策、变更与验证记录追加；`LICENSES_AND_PROVENANCE.md` 来源登记。
运行快照 DB、模型调用 DB、lock、开发绑定、真实服务配置不入库。


## S6 非生产准备增量（用户本轮 GitHub 交付授权）
- src/nana_core/migration/*.py、tests/migration/*.py、pyproject.toml
- src/nana_core/planning.py（仅新增影子观察的 suspend_invalid=False 选项；默认行为不变）
- docs/nana_core_s6_implementation.md、docs/nana_core_s6_test_output.txt、docs/nana_core_s6_evidence/*.json 与 junit.xml
- manifests/fingerprints_nana_core_s6.json、manifests/nana_core_s6_review.json
- PROJECT_BRAIN 工程状态/索引/任务/验证/决策/变更/路线追加，LICENSES_AND_PROVENANCE.md 来源登记。
- 排除运行 DB/WAL/lock、真实导出、真实凭据/记忆；不修改生产树或导入 AGPL 宿主。
# 本轮开发验证增量（用户明确授权）
- src/nana_core/development/*.py、tests/development/*.py、pyproject.toml
- src/nana_core/semantic/{contracts,evaluation,model_port,runner}.py（服务种类/真实模型计数，不改生产）
- tests/semantic_migration/test_evaluation.py（显式标注假设账本的 real_model 种类，原断言不变）
- docs/nana_core_development_validation.md、docs/nana_core_development_test_output.txt
- docs/nana_core_development_evidence/*.json、docs/nana_core_development_evidence/junit.xml（安全元信息和合成证据）
- manifests/fingerprints_nana_core_development.json、manifests/nana_core_development_review.json
- PROJECT_BRAIN/{00_INDEX,04_verification_status,08_TASKS,09_STATE,10_DECISIONS,11_CHANGELOG}.md 追加；LICENSES_AND_PROVENANCE.md 来源追加。
- 不上传源运行目录、DB/WAL/lock、真实模型配置/凭据/私人资料；不纳入生产目录或外部 secret 内容。

- C-033 增量：docs/nana_core_development_evidence/model_closeout_output.txt（实际合成测试 stdout）。

## C-034 网页工程白名单增补
- `src/nana_core/development/*.py` / `tests/development/*.py`：受控网页与公开只读传输。
- `src/nana_core/migration/routing.py`：仅可选 development_public scope，默认与生产边界保持。
- `docs/nana_core_web_validation.md` / `docs/nana_core_development_evidence/*.json` / `docs/nana_core_development_evidence/*_output.txt` / `docs/nana_core_development_evidence/*junit.xml`：合成工程与脱敏调用证据；不得包含运行 DB、密钥、真实私人资料或公开站点全文。

## Phase III 增量白名单
- src/nana_core/phase3/*.py、src/nana_core/migration/iris*.py、src/nana_core/memory*.py、src/nana_core/initiative*.py、src/nana_core/semantic/selection.py、semantic/contracts.py、development/public_http.py；仅独立Core增量，不改生产树。
- tests/phase3/*.py、docs/nana_core_phase3*.md、docs/nana_core_phase3_evidence/*.json/*.txt/*.xml、manifests/nana_core_phase3*.json、PROJECT_BRAIN、LICENSES_AND_PROVENANCE.md、pyproject.toml。
- 不含DB、JSONL私人资料、运行凭据、完整第三方源树；上游Iris只在临时目录只读核对，不入库。

Cloud bridge authorization: src/nana_core/integration/*.py, explicit ActionKernel/CapabilityRouter registry and fences, tests/integration/*.py, docs/nana_cloud*.md, docs/nana_cloud_evidence/{*.json,*.txt,*.xml,*.md}, manifests/nana_cloud*.json, pyproject.toml and PROJECT_BRAIN append records. No DB, credentials, private export or binary wheel in upload scope.

First real Shadow authorization: tools/nana_host_shadow/*.py, tests/integration/test_first_shadow.py, docs/nana_first_cloud_shadow.md, docs/nana_first_shadow_evidence/{*.json,*.txt,*.xml}, manifests/nana_first_shadow*.json, PROJECT_BRAIN append records, LICENSES_AND_PROVENANCE.md. Fixed Core package built only in temporary isolated directory; runtime DB and bundle binaries excluded.

Shadow Bootstrap: tools/nana_host_shadow/*.py, tests/integration/test_bootstrap.py, docs/nana_shadow_bootstrap.md, docs/nana_shadow_bootstrap_evidence/* (synthetic/version/hash/licensing/reproducer evidence), manifests/nana_shadow_bootstrap*.json, PROJECT_BRAIN append, LICENSES_AND_PROVENANCE.md, pyproject.toml and Core metadata preflight patch acceptance. No source runtime DB, binary or private snapshot upload.
# 2026-10-11 · Host ABI compatibility development delivery

- `tools/nana_host_shadow/bootstrap_entry.py`, `bootstrap.py`, `isolated_runtime.py`：ABI条件/报告及原runtime复用。
- `tests/integration/test_host_compat.py`：失败分类工程夹具，不冒充实际解释器运行。
- `docs/nana_shadow_host_compat.md`, `docs/nana_shadow_host_compat_evidence/*`：脱敏开发版本/测试/来源证据；不含DB/真实宿主数据。
- `manifests/nana_shadow_host_compat_*.json`：指纹/白名单/逐文件检查清单。
- `artifacts/shadow-bootstrap/nana-shadow-bootstrap-host3123-*.tar.gz`：仅当前批准Core+审核support+固定licensed runtime的单文件生成交付归档。逐archive entry/hash/license/credential扫描后允许保存私有开发分支，不能包含data/、DB、secret、生产配置或上游源码镜像。不是生产部署或第三方source vendoring目录。

## 2026-10-20 · Master Framework Freeze & Foundation Capability Audit V1

[用户明确要求正式写入仓库] 本次仅允许以下文档与无私人内容的审计元数据；不扩大运行、付费、生产或社交权限。

- `PROJECT_BRAIN/00_MASTER_FRAMEWORK.md`、`PROJECT_BRAIN/01_CAPABILITY_MATRIX.md`
- `PROJECT_BRAIN/00_INDEX.md`、`07_ROADMAP.md`、`08_TASKS.md`、`09_STATE.md`、`10_DECISIONS.md`、`11_CHANGELOG.md`（均在PROJECT_BRAIN内）
- `AGENTS.md`、`README.md`、`docs/nana_cloud_first_life_launch_v1_status.md`
- `docs/nana_master_framework_foundation_audit_v1_evidence/audit.json`、`validation.json`、`manifest.json`（仅源路径/hash、criteria与文档校验结果）
- `manifests/upload_whitelist.md`（本条）

逐文件检查后提交；不含DB/WAL、运行配置、凭据、聊天原文、第三方源码或二进制。

## Foundation audit independent recheck whitelist (parent af52371)

Only PROJECT_BRAIN/01_CAPABILITY_MATRIX.md,07_ROADMAP.md,08_TASKS.md,09_STATE.md,10_DECISIONS.md,11_CHANGELOG.md; docs/nana_cloud_first_life_launch_v1_status.md; docs/nana_master_framework_foundation_audit_v1_report.md; named JSON/txt/md evidence in docs/nana_master_framework_foundation_audit_v1_evidence/; tools/nana_foundation_audit/check.py and probe_topic_scope.py; this whitelist.
Master Framework, application source/tests, runtime configs/DBs, credentials, outside-repo preserved draft and old bundle are excluded. Exact staged names/hashes checked before commit.

## 2026-11-12 · Codex B 显式目录分页（用户持续开发/提交授权）

- 本批恰为 `docs/nana_next_experience/evidence/provider-catalog-pages-20261112/source-sha256.json` 中逐项登记的 12 份源码/测试文件；复用原 Core API、Web SDK 和 Android 有限映射，不复制第三方源码。
- `docs/nana_next_experience/evidence/provider-catalog-pages-20261112/{README.md,source-sha256.json,before-2fail.txt,browser-first.txt,related51.txt,catalog16.txt,client37.txt,browser16.txt,after-fast-forward.txt,after-a463.txt,after-a071.txt,after-bd48.txt,prerequisite-failures.txt}`：仅源码指纹/合成测试与已知环境失败记录。
- `docs/nana_next_experience/CODEX_B_QUEUE.md`、`PROJECT_BRAIN/{09_STATE.md,11_CHANGELOG.md}`（保留 A 原文，仅追加）及本白名单。
- 不含依赖目录、构建产物、数据库、运行配置、凭据、私人历史或 APK；保持原许可现状，逐文件扫描后本地提交/开发分支 push 与小范围 PR。


## 2026-11-12 · Codex B 供应商预设共用

持续开发/提交授权：apps/nana-space/src/{data/provider-center.ts,features/next/ModelSetup.tsx}，对应tests/{provider-center.test.ts,v3.spec.ts}；docs/nana_next_experience/evidence/provider-presets-20261112/{README.md,source-sha256.json,unit20.txt,browser36.txt,build.txt}；CODEX_B_QUEUE.md、PROJECT_BRAIN/{09_STATE.md,11_CHANGELOG.md}追加及本清单。仅原创代码、已知公开端点元数据与合成证据，无Key/DB/私史/依赖或二进制。


## 2026-11-13 · B 模型配置集成

沿用用户开发/提交/推送/PR持续授权；model-configuration-integration-20261113/{README.md,validation.json,source-sha256.json}及其逐项登记源码/测试，CODEX_B_QUEUE.md与09/11仅追加及本白名单。无第三方源码、凭据、数据或构建产物。


## 2026-11-13 · B 目录等待提示

持续授权范围：catalog-wait-20261113/{README.md,source-sha256.json}及指纹中6份源码/测试；CODEX_B_QUEUE.md、09/11追加、本清单。沿用原凭据/10秒节流，无真实Key/私史/依赖/构建产物。

## 2026-11-13 · B Provider配置解析复用候选

用户持续开发/提交/推送/PR授权：provider-config-parse-cache-20261113/{README.md,benchmark.json,cold-control-repeat.json,first-failures.txt,validation.txt,source-sha256.json}，其指纹3份原创源码/测试/本地实验；09/11仅追加及本白名单。无第三方复制/真实凭据/私史/依赖/构建产物。

## 2026-11-16 A采用PR17

B30459原12份文件正常合并，A保留当前09/双方11与既有白名单；另09/10/11、ACTIVE/STATUS/CODEX_B_QUEUE、本白名单及evidence/provider-parse-integration-20261115/内原创对照工具/原合成日志/指纹。无私有数据/凭据/第三方复制/二进制/运行配置。

## 2026-11-16 A采用PR18

正常合并固定6645的受控源码/配置示例/原创测试/公开工程资料/合成回执；A另改09/10/11、ACTIVE/STATUS、两个现有CI、portable/runtime-files、nanalink/login及其原测试、新最小包隔离测试、evidence/nanalink-core-integration-20261115/、原task_inputs主体连续性增补/08和本白名单。无DB/私史/真实账号或Key/新二进制，原许可/署名保留。

## 2026-11-16 A平台召回与主体连续性

memory.py/context.py、tests/nanalink/test_platform_context_population.py、原09/11/ACTIVE/STATUS及evidence/platform-context-population-20261116/的原合成日志/独立对照工具/指纹、本白名单；不含DB/运行配置/真实账户/凭据/二进制或上游复制。

## 2026-11-16 A匹配9a候选回执

09/11/ACTIVE/STATUS、本白名单及evidence/matched-integration-9a31e15-20261116/原公开合成安装/下载/回退/CI摘录/脚本和指纹。二进制仅原delivery固定efc候选，不重复放dev；无DB/私史/真实账号/密钥/新授权。

## 2026-11-16 A原视觉UNKNOWN范围

life/bilibili_frames.py两处field差额、新test_bilibili_frame_unknown.py、现有CI选择路径、09/11/ACTIVE/STATUS及evidence/visual-unknown-independent-request-20261116/原合成日志/指纹和本白名单。无Store/配置/真实账号/密钥/二进制/新收费授权，不重打9a包/APK。

## 2026-11-16 A原C已采纳步骤与负荷

subject/policy.py局部选择条件、test_deliberated_plan_load.py、原CI计划组选择、09/11/ACTIVE/STATUS及evidence/deliberated-plan-load-20261116/原受控日志/指纹、本白名单。无新权限/模型账单/Store/第三方源码/配置或二进制，不重打候选。

## 2026-11-16 A原C生命周期当前选择

policy.py生命周期局部、test_deliberated_goal_review.py、原CI计划组选择、09/11/ACTIVE/STATUS及evidence/deliberated-goal-review-20261116/原受控日志/指纹、本白名单。无私有数据/账户/配置/新授权/第三方复制或二进制。
