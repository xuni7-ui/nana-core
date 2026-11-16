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

## 2026-11-16 A原巩固候选前置

subject/{loop,policy}.py原消费者接线、test_memory_review_choice.py、现有CI选择、09/11/ACTIVE/STATUS及evidence/memory-review-current-choice-20261116/原合成日志/指纹、本白名单。无DB/配置/私史/真实账号/凭据/二进制/新外部权限或第三方复制。

## 2026-11-16 A原暂停回看关切群

living.py局部元数据/单slice缓存、test_memory_review_condition.py、现有CI组、09/11/ACTIVE/STATUS和evidence/memory-review-condition-cohort-20261116/原公开合成脚本/日志/指纹及本白名单。无Store/配置/私史/账户/凭据/二进制/第三方复制/新权限。

## 2026-11-16 A原H1帧语义定位

world_loop/semantics.py原H1来源元数据、test_bilibili_frames.py原场景和两反例、既有CI选择与原codec资格、09/11/ACTIVE/STATUS及evidence/frame-semantic-source-locator-20261116/原公开合成日志/指纹、本白名单。无第三方复制/DB/私史/账号/配置/密钥/二进制/付费或新增执行权限。

## 2026-11-16 A原REPLAN当前选择

subject/{policy,loop}.py及presence/living.py原consumer局部、test_deliberated_replan_choice.py、现有CI组、09/11/ACTIVE/STATUS与evidence/deliberated-replan-choice-20261116/原受控日志/独立基线脚本/指纹、本白名单。无运行Store/配置/私史/账户/凭据/第三方复制/二进制/新执行权限或收费。

## 2026-11-16 A原C新社交选择

policy.py原interested_social局部、test_fresh_social_choice.py/原test_social_tendency_competition.py新语义与严格撤回断言、既有CI组、09/11/ACTIVE/STATUS及evidence/fresh-social-choice-20261116/原公开合成日志/纯C消融脚本/指纹、本白名单。无真实收件人/账户/私史/DB/配置/凭据/第三方复制/二进制/新执行或收费授权。

## 2026-11-16 A原表达课题来源群

lived_language.py原consumer局部、test_expression_lesson_population.py、既有CI组、09/11/ACTIVE/STATUS及evidence/expression-lesson-population-20261116/原公开合成日志/同库原函数对照脚本/指纹、本白名单。无真实反馈/私史/账户/DB/配置/凭据/第三方复制/二进制/新执行或付费权限。

## 2026-11-16 A统一Web输入闭包

package-lock.json三版本标签、tools/nana_first_life_android_v2/web_inputs.py、09/11/ACTIVE/STATUS及evidence/web-build-input-closure-20261116/原公开合成安装/回退/新npm/编译/单测/输入验证日志/指纹、本白名单。既有.env.live仅验证已提交公共开关、未新增密钥配置；无Store/签名Key/真实账号/用户数据/二进制/APK/新权限。

## 2026-11-16 A匹配c1d受控交付回执

09/11/ACTIVE/STATUS、本白名单及evidence/matched-integration-c1d345e-20261116/固定公开源码构建、合成安装/下载/停机回退回执/复现脚本/指纹。候选二进制仅既有delivery分支a274601，主开发分支不复制；无Store/Key/真实用户或账号/新权限。

## 2026-11-16 A原上下文压缩连续性

life/application.py现有保留顺序局部、test_compaction_durability.py、原CI组/路径、08/09/11/ACTIVE/STATUS、本白名单及evidence/context-compaction-continuity-20261116/公开合成原失败/定向回归/指纹。无私史/Store/Key/账号/新依赖/新系统/发行二进制/生产。

## 2026-11-16 A集成固定PR20

固定PR20的原NanaLink/B站源码/测试/只读交接及开发工具/原C交接日志、manifests/nanalink-01.sha256（A仅刷新application摘要），09/11/ACTIVE/STATUS、本白名单及evidence/platform-integration-pr20-20261116/公开合成原失败/定向检查/固定B投影回执/指纹。无Store/Key/真实用户/账号/新依赖/执行权限/发行二进制/生产。


<!-- PR19固定研究交接；A当前结论见09 -->


## 2026-11-16 B视频覆盖隔离候选

持续授权：tools/nana_next_experience/experiments/video_coverage.py、tests/nana_next_experience/test_video_coverage_prototype.py、docs/nana_next_experience/evidence/video-coverage-prototype-20261116/README.md、09/11追加及本清单；原创代码，引用上游思想和许可证，无第三方源码/真实视频/凭证。

## 2026-11-16 A采用固定PR19实验

固定PR19工具/原测试/原研究及原B交接文字、原CI两个精确路径/7项组，09/11/ACTIVE/STATUS、本白名单及evidence/vision-prototype-adoption-20261116/公开合成回执/指纹。无第三方源码复制/新依赖/Store/Key/账号/运行权威/发行/生产。

## 2026-11-16 A原G注意可见性群

subject/growth_life.py原SQL局部、test_growth_attention_visibility.py、原CI精确路径/组、09/11/ACTIVE/STATUS及evidence/growth-attention-visibility-20261116/公开合成原失败/夹具差额/定向回归/指纹、本白名单。无Store/Key/真实用户/账号/新依赖/执行权限/二进制/生产。

## 2026-11-16 A原G重放结果绑定

world_loop/learning.py原cache局部、test_growth_assessment_identity.py、原CI精确路径/组、09/11/ACTIVE/STATUS及evidence/growth-assessment-replay-binding-20261116/公开合成原失败/定向回归/指纹、本白名单。无Store/Key/真实用户/账号/新依赖/执行权限/二进制/生产。

## 2026-11-16 A原G情境注意

subject/growth_life.py、continuity/store.py两个可重建索引及旧schema guard、新test_growth_context_population.py、原CI精确组/路径、09/11/ACTIVE/STATUS及evidence/growth-context-population-20261116/公开合成失败/回归/旧函数消融/SQLite元数据与同库读成本脚本/日志/指纹、本白名单。原库与元数据实验DB不入库，无Key/用户史/账号/新依赖/执行权限/发行/生产。

## 2026-11-16 A原成长SELF等价体

continuity/context.py、test_growth_context_compaction.py、原CI精确路径/组、09/11/ACTIVE/STATUS、evidence/growth-context-report-compaction-20261116公开合成日志/受控消融/脚本/指纹、本白名单。无DB/私文/账号Key/新依赖/生产/发行修改。

## 2026-11-16 A固定9a2匹配安装

09/11/ACTIVE/STATUS、evidence/matched-core-9a2f677-20261116公开合成构建/安装/下载/源码指纹/固定夹具准备脚本和收据、本白名单。delivery ca765仅server-9a2f677-candidate/11件，保留CURRENT，无私史/Key/DB/生产变更；外部公开夹具不是Runtime源码。

## 2026-11-16 A集成PR21固定0f766c1

原C固定35路径普通merge、09/11/ACTIVE/STATUS、现役nanalink manifest两A后继SHA、evidence/platform-integration-pr21-20261116公开原反例/192回归/固定C指纹及本白名单；原上传无私史/Key/DB/新账号授权/生产/新打包。

## 2026-11-16 A公共Bili synthetic绑定

life/bilibili.py、新test_bilibili_synthetic_binding.py、原frame/unknown夹具显式local opener、原CI精确路径与组、nanalink manifest该源、09/11/ACTIVE/STATUS、evidence/bilibili-public-fixture-binding-20261116公开原错与回归/指纹、本白名单，无新依赖/账号/DB/私文/部署/打包。

## 2026-11-16 A原G不同能力候选

subject/growth_life.py、test_growth_lesson_attention.py、原CI精确路径/组、09/11/ACTIVE/STATUS、evidence/growth-lesson-attention-fairness-20261116公开失败/回归/原函数消融与读成本/指纹、本白名单。无DB/私史/Key/新增权限/框架/生产或打包，G16/32原资格不变。

## 2026-11-16 A成长目的上下文引用

continuity/context.py、test_growth_purpose_context.py、原CI精确路径/组、现役nanalink manifest该源、09/11/ACTIVE/STATUS、evidence/growth-purpose-context-20261116公开失败/回归/原函数消融/合成请求块统计/物理撤回/指纹、本白名单；无私史/Key/DB/新依赖/付费调用/生产/打包。

## 2026-11-16 A原S5源流/时长

world_loop/perception.py、新test_media_stream_binding.py、原CI精确路径/组、09/11/ACTIVE/STATUS、evidence/media-stream-binding-20261116公开合成原错/70及后8回归/同编码文件解码消融/指纹、本白名单。无媒体原件/DB/私史/Key/新依赖/模型或账号调用/生产/打包。

## 2026-11-16 A原CI native选择

.github/workflows/nana-next-qualification.yml、09/11/ACTIVE/STATUS、evidence/native-ci-routing-20261116公开CI原错/本地原错/分类检查/指纹、本白名单；无新Core代码/DB/私史/凭据/生产/发行。

## 2026-11-16 A原H1同轨/独立覆盖

world_loop/semantics.py、新tests/h1_semantics/test_media_stream_binding.py、09/11/ACTIVE/STATUS、evidence/media-semantic-track-20261116、269公开原CI log补正/source.sha256、本白名单；无DB/媒体原件/私史/Key/新依赖/真实模型或账号/发行生产。


## 2026-11-16 B FFmpeg时间覆盖研究

持续授权范围：video-ffmpeg-comparison-20261116/{README.md,comparison.json,source-sha256.json}，其指纹三份原创实验/测试文件，09/11追加及本清单。上游仅本地运行并引用固定SHA/许可证，不复制第三方源码或提交生成视频。


## 2026-11-16 B覆盖与变化换帧

持续授权：video-change-coverage-20261116/{README.md,source-sha256.json}及其中2个原创实验/测试文件、09/11追加、本清单；无第三方源码、真实视频或凭证。


## 2026-11-16 B短暂文字候选

持续授权：video-short-detail-20261116/{README.md,before.txt,comparison.json,source-sha256.json}、其中probe及新增测试、09/11追加与本清单；合成素材不入库、无真实视频或凭证。


## 2026-11-16 B局部变化与裁切实验

持续授权：video-local-change-20261116/{README.md,source-sha256.json}、其中原创实验及测试、09/11追加及本清单；无真实帧/凭据、第三方源码或二进制。


## 2026-11-16 B音轨静音测量

持续授权：video-audio-probe-20261116/{README.md,source-sha256.json}及其中原创实验、测试，09/11追加、本清单；不提交合成音视频或凭据。


## 2026-11-16 B字幕声学时间复查

持续授权：video-caption-audio-crosscheck-20261116/{README.md,source-sha256.json}及其中原创实验/测试、09/11追加和本清单；无真实字幕、音视频、凭据或第三方源码。


## 2026-11-16 B字幕声学区间索引

持续授权：video-caption-overlap-index-20261116/{README.md,benchmark.json,source-sha256.json}和指纹中3个原创源码/测试，09/11追加、本清单；合成输入、无真实字幕音频或凭据。


## 2026-11-16 B上游音频判型反例

持续授权：video-upstream-audio-counterexample-20261116/{README.md,comparison.json,source-sha256.json}、其中原创对照脚本、09/11追加和本清单；不复制上游源码/合成音频/真实字幕或凭据。


## 2026-11-16 B视觉扫描完整性

持续授权：video-scan-completeness-20261116/{README.md,source-sha256.json}和其中实验/测试，09/11追加、本清单；无真实视频、凭据或第三方源码。


## 2026-11-16 B原dsh管线适配

持续授权：dsh-pipeline-adapter-20261116/{README.md,source-sha256.json}及其中原创调用适配器与测试，09/11追加、本清单；不复制第三方代码、生成RGB/视频、账号或凭据。


## 2026-11-16 B三视觉场景对照

持续授权：video-three-scenarios-20261116/{README.md,results.json,source-sha256.json}及其中原创对照脚本、09/11追加、本清单；无真实视频/凭据或复制第三方源码。


## 2026-11-16 B局部变化前后帧

持续授权：video-local-pairs-20261116/{README.md,source-sha256.json}及其中原创实验/测试、09/11追加、本清单；无真实帧或凭据。


## 2026-11-16 B视觉线索融合候选

持续授权：video-fusion-candidates-20261116/{README.md,source-sha256.json}及其中原创实验/测试、09/11追加、本清单；无真实帧/凭据或上游源码复制。


## 2026-11-16 B视觉融合三场景

持续授权：video-fusion-scenarios-20261116/{README.md,results.json,source-sha256.json}及其中原创对照脚本、09/11追加、本清单；不提交真实视频/凭据或复制上游源码。


## 2026-11-16 B静态帧快速路径

持续授权：video-static-frame-fast-path-20261116/{README.md,benchmark.json,source-sha256.json}和其中3个原创源码/测试、09/11追加、本清单；不含真实画面/凭据或上游源码。


## 2026-11-16 B dsh背压状态

持续授权：dsh-backpressure-accounting-20261116/{README.md,source-sha256.json}及其中原创适配/融合/测试、09/11追加、本清单；不复制上游源码或提交视频/凭据。


## 2026-11-16 B本地消费者背压实验

持续授权：dsh-local-consumer-20261116/{README.md,source-sha256.json}及其中原创适配/测试、09/11追加、本清单；无上游源码/真实画面/凭据。


## 2026-11-16 B dsh恢复受控对照

持续授权：dsh-restore-fixture-20261116/{README.md,source-sha256.json}及其中原创驱动/测试、09/11追加、本清单；无真实媒体/凭据或复制上游源码。


## 2026-11-16 B dsh选帧时间精度

持续授权：dsh-selected-time-precision-20261116/{README.md,source-sha256.json}及其中原创适配/测试、09/11追加、本清单；无真实媒体/凭据或上游源码复制。


## 2026-11-16 B融合帧对引用

持续授权：video-fusion-pair-lineage-20261116.json及其中原创源码/测试，09/11追加、本清单；无真实帧/凭据。


## 2026-11-16 B变帧率PTS解码候选

持续授权：video-vfr-pts-decode-20261116.json及其中原创实验/测试、09/11追加、本清单；不提交真实视频、帧或凭据。


## 2026-11-16 B音视频起点与音频覆盖

持续授权：video-audio-coverage-and-offset-20261116.json及其中7个原创源码/测试，09/11追加、本清单；无真实音视频/字幕/凭据或上游源码复制。


## 2026-11-16 B有界分段与PTS

持续授权：video-bounded-windows-20261116.json及其中4个原创实验/测试，09/11追加、本清单；无真实媒体/凭据。


## 2026-11-16 B原PTS窗口融合

持续授权：video-window-fusion-20261116.json及其中6个原创实验/测试、09/11追加、本清单；无真实视频/凭据/上游源码复制。

## 2026-11-16 B帧数上限自适应分段

持续授权：video_adaptive_decode.py、video_pts_decode.py及对应测试、bench_video_adaptive_decode.py、CODEX_B_QUEUE.md和本清单；仅合成视频，无真实媒体、凭据或上游源码复制。
