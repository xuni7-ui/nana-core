# Iris Schema-Only Compatibility 核实（M4·R02）

- 时间：2026-10-11 (CST) · 执行者：奈奈（宿主侧执行者，只读）
- 方法：**只读 schema**（源码定义 + SQLite `sqlite_master` / `PRAGMA table_info`）
- **严格未读任何真实 memory / profile / conversation 的「值」**：所有查询只取结构元数据，不取行内容
- 只读连接：`sqlite3.connect("file:…?mode=ro", uri=True)`（不写、不加锁升级、不建 journal）

## 0. 结论

**`SCHEMA_COMPATIBLE`** —— Iris 0.3.0 的 11 类数据形态与 `nana-core` 迁移层 `FIELDS` 声明**逐字段一致**，
L2/L3 已用**真实库文件**的结构做了交叉验证。

---

## 1. 版本与路径

| 项 | 值 | 来源 |
|---|---|---|
| Iris 插件 | `astrbot_plugin_iris_chat_memory` | `metadata.yaml` |
| Iris version | **0.3.0** | `metadata.yaml` (`version: 0.3.0`) |
| 上游 | `https://github.com/Leafliber/astrbot_plugin_iris_chat_memory` | `metadata.yaml` |
| 插件根 | `/AstrBot/data/plugins/astrbot_plugin_iris_chat_memory` | 实测 |
| 数据根 | `/AstrBot/data/plugin_data/astrbot_plugin_iris_chat_memory` | `main.py:101` `StarTools.get_data_dir()` |

### 实现路径（只读枚举）

| 层 | 路径 |
|---|---|
| L1 缓冲 | `iris_memory/l1_buffer/{buffer,models,summarizer}.py` |
| L2 记忆 | `iris_memory/l2_memory/{adapter,io,models,retriever}.py` |
| L3 KG | `iris_memory/l3_kg/{adapter,extractor,models,retriever,related_retriever}.py` |
| 画像 | `iris_memory/profile/{storage,models,user_profile,group_profile,analyzer}.py` |
| KV 适配 | `iris_memory/core/storage.py` → `KVStorage` Protocol（AstrBot `get_kv_data/put_kv_data/delete_kv_data`） |
| 流水 | `iris_memory/core/conversation_flow.py`（`<workspace>/<umo>/对话流水/YYYYMMDD.jsonl`） |
| 台账 | `iris_memory/core/action_ledger.py`（`action_ledger/ledger.json` + `ledger.jsonl`） |
| 决策日志 | `iris_memory/core/decision_log.py`（`decision_log/YYYYMMDD.jsonl`） |

---

## 2. 物理存储（文件名+大小，不含内容）

```
plugin_data/astrbot_plugin_iris_chat_memory/
├── faiss/memory_default/{index.faiss, index_meta.json, metadata.db(+shm,wal)}
├── faiss/migration_backup/*.json
├── l3_graph/graph.db(+shm,wal)
├── action_ledger/{ledger.json, ledger.jsonl, backups/…}
├── decision_log/YYYYMMDD.jsonl
└── image_cache/…
```

---

## 3. L2 `metadata.db` — 真实库结构（`mode=ro`）

```
PRAGMA user_version = 0
journal_mode = wal
[table] memories
  columns: faiss_idx INTEGER | memory_id TEXT | content TEXT | metadata TEXT |
           group_id TEXT | user_id TEXT | timestamp TEXT | kg_processed INTEGER | persona_id TEXT
[index] sqlite_autoindex_memories_1 (idempotent UNIQUE memory_id)
[index] idx_memories_group_id / idx_memories_user_id / idx_memories_kg_processed
        idx_memories_timestamp / idx_memories_persona_id
```
源码定义：`iris_memory/l2_memory/adapter.py:727-760`（含 `persona_id` 向后兼容补列 `:741-745`）。
另：`index_meta.json` 实际键 = `["embedding_dimensions","embedding_model","free_list","persona_id","version"]`。

## 4. L3 `graph.db` — 真实库结构（`mode=ro`）

```
[table] nodes: id | label | name | content | confidence | access_count |
               last_access_time | created_time | source_memory_id | group_id | properties
[table] edges: source_id | target_id | relation_type | weight | confidence |
               access_count | last_access_time | created_time | source_memory_id | properties
[index] idx_nodes_label_name / idx_nodes_group / idx_nodes_source_mem /
        idx_edges_source / idx_edges_target + 两个 autoindex
```
源码定义：`iris_memory/l3_kg/adapter.py:73-110`。

---

## 5. 逐类对账（`nana_core.migration.iris.FIELDS` vs 实测）

| kind | nana-core 声明字段 | 实测 | 判定 |
|---|---|---|---|
| `l1` | role, content, timestamp, token_count, source, metadata, persona_id | `l1_buffer/models.py` `ContextMessage`(:25-55) 完全一致（含 `to_dict` :36-45） | ✅ |
| `l2` | id, content, metadata, persona_id, embedding | `l2_memory/models.py:53-57` 完全一致 | ✅ |
| `l2_row` | faiss_idx, memory_id, content, metadata, group_id, user_id, timestamp, kg_processed, persona_id | 真实 `memories` 表 9 列**逐一一致** | ✅ |
| `kg_node` | id, label, name, content, confidence, access_count, last_access_time, created_time, source_memory_id, group_id, properties | 真实 `nodes` 表 11 列**逐一一致** | ✅ |
| `kg_edge` | source_id, target_id, relation_type, weight, confidence, access_count, last_access_time, created_time, source_memory_id, properties | 真实 `edges` 表 10 列**逐一一致** | ✅ |
| `index_meta` | version, embedding_model, embedding_dimensions, persona_id, free_list | 真实 `index_meta.json` 键**逐一一致** | ✅ |
| `user_profile` | user_id, user_name, version, historical_names, personality_tags, interests, occupation, language_style, communication_style, emotional_baseline, favorability, bot_relationship, important_dates, taboo_topics, important_events, custom_fields, field_meta, update_tracker | `profile/models.py` `UserProfile` + `ProfileMetadataMixin`(:151-160) 一致 | ✅ |
| `group_profile` | group_id, group_name, version, interests, atmosphere_tags, long_term_tags, blacklist_topics, custom_fields, field_meta, update_tracker | `profile/models.py` `GroupProfile`(:238-274) 一致 | ✅ |
| `action_ledger` | key, state, updated_at, op, verify, note, actor, first_at, revision | `core/action_ledger.py:147-155` entry 键一致 | ✅ |
| `decision_log` | t, t_utc, tier, reason, query, top_k, hits, route, soft_confirm, window, ms, extra | `core/decision_log.py:152-160` 一致 | ✅ |
| `conversation_flow` | ts, ts_cst, umo, role, sender_id, sender_name, text, extra | `core/conversation_flow.py` 写入口径一致 | ✅ |

对账基准：`src/nana_core/migration/iris.py:11-35`（`KINDS` / `REQUIRED` / `FIELDS`）。

---

## 6. 值最小化声明

| 项 | 数量 |
|---|---|
| 读取的「真实记忆/画像/对话正文」条数 | **0** |
| 读取的行数据 | **0**（只用 `sqlite_master` + `PRAGMA table_info/user_version/journal_mode`） |
| 读取的索引/表名/列名 | 全量（结构元数据，非私人） |
| DB 写入 / 迁移 | **0** |

---

## 7. 判定与漂移记录

- **`SCHEMA_COMPATIBLE`**：11/11 类全部一致，无 `SCHEMA_DRIFT`，无 `UNKNOWN`。
- 边界声明：`user_version = 0`（Iris 未使用 SQLite user_version 做版本管理）→ nana-core **不得**依赖它做版本判断，应依赖 `PRAGMA table_info` 结构探测。
- L2 `metadata.db` 存在 `-wal` 残页：只读连接读取的是「WAL 合并视图」；若需逐字节快照，需先走 nana-core 的导入路径（**本轮不做**）。
