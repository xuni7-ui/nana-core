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
- docs/nana_core_s6_implementation.md、docs/nana_core_s6_test_output.txt、docs/nana_core_s6_evidence/*.json 与 junit.xml
- manifests/fingerprints_nana_core_s6.json、manifests/nana_core_s6_review.json
- PROJECT_BRAIN 工程状态/索引/任务/验证/决策/变更/路线追加，LICENSES_AND_PROVENANCE.md 来源登记。
- 排除运行 DB/WAL/lock、真实导出、真实凭据/记忆；不修改生产树或导入 AGPL 宿主。
