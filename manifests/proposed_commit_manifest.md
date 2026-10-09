# 拟提交文件清单（Proposed Commit Manifest）

> 生成：2026-10-10 CST ｜ 状态：**待姐姐与小 GPT 共同验收**，**未 commit、未 push**
> 路径根：`/root/nana_dev/nana-core/`

## 一、拟提交内容（= 白名单，共 3 组）

### 组 1：工程规范与事实源（必备）
```
AGENTS.md
README.md
PROJECT_BRAIN/00_INDEX.md
PROJECT_BRAIN/01_architecture.md
PROJECT_BRAIN/02_source_inventory.md
PROJECT_BRAIN/03_config_runtime.md
PROJECT_BRAIN/04_verification_status.md
PROJECT_BRAIN/05_third_party_licenses.md
PROJECT_BRAIN/06_open_risks.md
```

### 组 2：清单与证据
```
manifests/upload_whitelist.md
manifests/sensitive_scan_report_20261010.md
manifests/fingerprints_20261010.md
manifests/proposed_commit_manifest.md
manifests/nana_iris_changes.diff        ← ⚠️ AGPL 衍生，条件提交
docs/migration_report_20261010.md
docs/verification_and_fingerprint.md
upstream/sources.md
```

### 组 3：奈奈原创源码
```
src/plugins/astrbot_plugin_nana_admin_guard/main.py
src/plugins/astrbot_plugin_nana_admin_guard/metadata.yaml
src/plugins/astrbot_plugin_nana_anchor/main.py
src/plugins/astrbot_plugin_nana_anchor/metadata.yaml
src/plugins/astrbot_plugin_nana_bilievent/main.py
src/plugins/astrbot_plugin_nana_bilievent/metadata.yaml
src/plugins/astrbot_plugin_linna_tmp/main.py
src/plugins/astrbot_plugin_linna_tmp/metadata.yaml
src/bili_agent/bili_agent.py
src/bili_agent/bili_event_pump.py
src/bili_agent/bili_event_source.py
src/bili_agent/bili_send_core.py
src/bili_agent/bili_video_read.py
src/bili_agent/nana_bili_health_check.py
src/bili_agent/bili_refresh.py
src/bili_agent/bili_send_comment.py
src/bili_agent/bili_reply_comment.py
src/bili_agent/probe_msgfeed_readonly.py
src/bili_agent/notes/Agent与Harness_轩辕的编程宇宙_BV1t55v6DE2v_笔记.md
src/bili_agent/notes/C7_缺陷记录_OBSERVE吞靶子_20261007.md
src/c5v/README_c5v.md
src/c5v/bili_video_vision.py
```

## 二、明确排除（不入库）

| 排除项 | 原因 |
|---|---|
| `test_bili_agent_semantic_retry.py` | **硬编码 SESSDATA** |
| `/root/.nana_secrets/` 其余文件 | 凭证/日志/运行态 |
| `data/cmd_config.json`、`data_v4.db*`、`logs/` | 敏感运行数据 |
| `对话流水/*.jsonl`、`merged_memory.*` | 私人隐私 |
| 各第三方插件源码整包 | LICENSE/署名 |
| `nana_dsh_whale_*`、`gen_*.py` 等 | 无关/未鉴定 |
| `__pycache__/`、`*.bak*` | 编译产物/备份 |

## 三、提交前必须解决的阻塞项

1. **B1** 原始 PROJECT_BRAIN 不存在 → 需姐姐确认"以新建为准"。
2. **B3** 硬编码密钥文件 → 已阻断（本清单不含）。
3. **H5** 自制插件无 LICENSE → 需指定许可。
4. **H4** diff 含 AGPL 衍生 → 需确认整体许可策略。
5. **验收** → 姐姐 + 小 GPT 共同验收后才可 commit。

## 四、执行动作（获批后）

1. `git init`（本地，若姐姐批准）
2. 按本清单 `git add`（**逐文件**，不用 `git add -A`）
3. `git status` 复核
4. ⏸ **停下等待**，**不 commit、不 push**
