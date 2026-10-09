# PROJECT_BRAIN 指纹清单（采集时刻快照）

> 采集时间：2026-10-10 02:3x CST（第 2 次采集，锚点回填后刷新）｜ 方式：md5 ｜ **指纹仅证明采集时刻，不证明当前运行态**


## 〇、自指说明（P1 修正，2026-10-10）

**本表不包含自身条目。** 文件无法包含自身的哈希（自指悖论）——旧稿把本表自己列入，
导致"43 个文件仅 42 个一致"，那是**方法论缺陷，不是文件损坏**。

本表自身的完整性由 **Git 基线提交**（内容寻址）保证，提交 SHA 记录于
`PROJECT_BRAIN/09_STATE.md` §七 基线锚点。**若本表与 `git status` 不一致，以 git 为准。**

## 一、开发副本（nana-core）全量文件（**不含本表自身**）

| 相对路径 | 大小(B) | md5 |
|---|---|---|
| `.gitignore` | 498 | `87f3592d927098e8085655f61f930130` |
| `AGENTS.md` | 5990 | `ce2c70f4e6310e5db018c4b2ee2d9f7e` |
| `PROJECT_BRAIN/00_INDEX.md` | 4266 | `dc69d5717c09343760a4c7712b329550` |
| `PROJECT_BRAIN/01_architecture.md` | 5697 | `a22862358adc351c5240e78883992d68` |
| `PROJECT_BRAIN/02_source_inventory.md` | 3277 | `e3c371a1e25272b06b234ca2d6cd3d17` |
| `PROJECT_BRAIN/03_config_runtime.md` | 3011 | `76add8a1e5b3c05395037aa2f6eda0a6` |
| `PROJECT_BRAIN/04_verification_status.md` | 5934 | `43ed7533083d1b67c052e8e2f43f8c61` |
| `PROJECT_BRAIN/05_third_party_licenses.md` | 3828 | `68447327e7154cf11b5dd624291df885` |
| `PROJECT_BRAIN/06_open_risks.md` | 2491 | `2d93408a9c7407de6e40476a8774f55c` |
| `PROJECT_BRAIN/07_ROADMAP.md` | 4849 | `fd6c46b5b3914703ea4c0ba8fd5aaa83` |
| `PROJECT_BRAIN/08_TASKS.md` | 4232 | `dbb4b4eb73bdc582a63f8c8b050ae58c` |
| `PROJECT_BRAIN/09_STATE.md` | 3898 | `d5f2a467dd458bba6db9b2e76375999e` |
| `PROJECT_BRAIN/10_DECISIONS.md` | 5607 | `d522663245fb8f3a46bfe4803292fa5d` |
| `PROJECT_BRAIN/11_CHANGELOG.md` | 4395 | `0842a0077e6bebb972f1614fb00ce5a9` |
| `README.md` | 3138 | `39565e52462d8ea896de21467cb722aa` |
| `docs/external/README_bili_agent_c1.md` | 10458 | `5d173fc0fdfb0aa666008de36a689938` |
| `docs/external/README_bili_send_c2.md` | 3995 | `21fcdcfb9cb5b3d4047b816c8f50f325` |
| `docs/external/README_c4_events.md` | 3420 | `46d9b5150065e5f50256862bb33d81ed` |
| `docs/external/README_c5_read.md` | 2407 | `aeb1d9bcb1cbf042c6074f990fd52e3b` |
| `docs/migration_report_20261010.md` | 3274 | `727a3d5bc871c28bd3e04245793175f0` |
| `docs/verification_and_fingerprint.md` | 1981 | `f49075471152be03613e326f6661d088` |
| `manifests/nana_iris_changes.diff` | 66100 | `13828c7a254ad3dd4be93a0de929aa29` |
| `manifests/proposed_commit_manifest.md` | 3046 | `2d06a913d9ddc4eea8f50e84ace83d91` |
| `manifests/sensitive_scan_report_20261010.md` | 2700 | `0f8d1b6ba73525cacd47d25230c011ac` |
| `manifests/upload_whitelist.md` | 2472 | `c1f0accede014ce2a65c05486d23a399` |
| `src/bili_agent/bili_agent.py` | 47123 | `afcd69df7a8840d69b67c3ae6b2dcee0` |
| `src/bili_agent/bili_event_pump.py` | 19777 | `59f3e8ee50dff268622b85d1113830dd` |
| `src/bili_agent/bili_event_source.py` | 5186 | `e4b61749e5748d144200ea7e6bf4eec1` |
| `src/bili_agent/bili_refresh.py` | 2466 | `8604d8761b2b4645aa4da28bf7f85a4e` |
| `src/bili_agent/bili_reply_comment.py` | 934 | `93d24f6fba56dd240920a4cbda412db4` |
| `src/bili_agent/bili_send_comment.py` | 884 | `6cbc6665ed69511d21dc47ed3be08e22` |
| `src/bili_agent/bili_send_core.py` | 15058 | `b87ce89c5f208ac272080a4f9321d9fd` |
| `src/bili_agent/bili_video_read.py` | 17607 | `96fb021529228c752bc1c865f05021eb` |
| `src/bili_agent/nana_bili_health_check.py` | 8652 | `b4ed136bbe44e2b572c7a8ba8595b23f` |
| `src/bili_agent/notes/Agent与Harness_轩辕的编程宇宙_BV1t55v6DE2v_笔记.md` | 6852 | `8a60d5414a79ef916ff142dd7eedcac2` |
| `src/bili_agent/notes/C7_缺陷记录_OBSERVE吞靶子_20261007.md` | 2591 | `f4ff651a9527afbffa5f39e3e05fd38e` |
| `src/bili_agent/probe_msgfeed_readonly.py` | 1270 | `595e5a686f3ff1653da7ccbf5992c5c6` |
| `src/c5v/README_c5v.md` | 5900 | `4e1b04e44817b39a389be013493e78b9` |
| `src/c5v/bili_video_vision.py` | 21614 | `2a070086b11c24a989672f00584ff068` |
| `src/plugins/astrbot_plugin_linna_tmp/main.py` | 1580 | `acaee964ab6c18d664837faf54339d5b` |
| `src/plugins/astrbot_plugin_linna_tmp/metadata.yaml` | 153 | `a3e64bb7f1b13b9a7aaedf922960f5d7` |
| `src/plugins/astrbot_plugin_nana_admin_guard/main.py` | 1356 | `3a346144328bc8199439f737b3d2557e` |
| `src/plugins/astrbot_plugin_nana_admin_guard/metadata.yaml` | 243 | `ec9d46183ff1b8f305b5fd1bca8be5c6` |
| `src/plugins/astrbot_plugin_nana_anchor/main.py` | 4933 | `63222cf3a787f5666c977beff0d588a7` |
| `src/plugins/astrbot_plugin_nana_anchor/metadata.yaml` | 235 | `6471995a0ffa2156bd6e2398efc1c5d7` |
| `src/plugins/astrbot_plugin_nana_bilievent/main.py` | 5912 | `b7132f8da9b7011036797341c33c8c83` |
| `src/plugins/astrbot_plugin_nana_bilievent/metadata.yaml` | 274 | `d2dfa3bb0fd559050983417f931e4a8b` |
| `upstream/sources.md` | 1807 | `d20d81afbccfb0e98b93eceae66095f4` |

> 条目数：**48** ｜ 合计 **333,371 B（325.6 KB）** ｜ 仓库实际文件数 = 条目数 + 1（本表自身）

## 二、生产态：Iris 插件奈奈改动文件（14 个，只读采集）

| 文件 | md5 | mtime |
|---|---|---|
| `iris_memory/core/semantic_gate.py` | `9498f2ae4b88517da63fd69b50d0b68d` | 2026-10-05 18:27 |
| `iris_memory/core/decision_log.py` | `d2068660c55fb101c019acea0ee1aa95` | 2026-10-06 17:10 |
| `iris_memory/core/llm_response_hook.py` | `68e0bf2b11cf0118c5c363849bb5ec93` | 2026-10-06 10:03 |
| `iris_memory/core/message_hook.py` | `8897e087e0df61616e2b40f9ab0a7b8c` | 2026-10-06 11:39 |
| `iris_memory/core/conversation_flow.py` | `a3a9a759838eab2b5383dcdddadbe601` | 2026-10-06 17:04 |
| `iris_memory/core/llm_request_hook.py` | `95bc58088a8f769982d2fbe006a5ecea` | 2026-10-06 17:24 |
| `iris_memory/core/action_ledger.py` | `30bae5962575c9636383ef3748eff3ef` | 2026-10-06 17:13 |
| `iris_memory/l1_buffer/buffer.py` | `b28483496b79123c716a083f2a8f3100` | 2026-10-06 17:10 |
| `iris_memory/config/defaults.py` | `376653cc50ff5ee6db2e51e1851862b1` | 2026-10-06 17:11 |
| `iris_memory/utils/__init__.py` | `2bcf76bde55561a4753e345d173508b0` | 2026-10-06 17:04 |
| `iris_memory/utils/timeutil.py` | `da1a35176e852feafdd88d24ed57829a` | 2026-10-06 17:04 |
| `_conf_schema.json` | `96f98e457644c8161fa507d8997e73ff` | 2026-10-06 10:04 |
| `tests/core/test_gate_off_parity.py` | `447df8008ee2f0f698ec35123effed75` | 2026-10-05 19:11 |
| `tests/core/test_semantic_gate.py` | `19b79a861f5020a56410718d59bc0592` | 2026-10-05 19:13 |

> ✅ 与第 1 次采集（01:5x）**逐条一致**，生产文件未漂移。

## 三、采集边界

- 采集方式：`hashlib.md5` 逐文件只读
- 生产改动：**0**
- 未探测进程内存 → **源码态 ≠ 运行态**（见 `PROJECT_BRAIN/04` U3）