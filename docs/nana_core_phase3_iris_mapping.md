# Iris 0.3.0 → Nana Core schema mapping V1

[源码确认] 仓库只保存上游来源登记和14处定制补丁，不保存完整241文件。此次只读取得公开上游 tag0.3.0，核对 commit **0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6**，checkout在/tmp/nana-iris-phase3-upstream；未运行上游、未读取任何生产DB。精确文件hash见iris_source_manifest.json。下文“upstream:path:行号”指该锁定提交，公开永久链接基址为 https://github.com/Leafliber/astrbot_plugin_iris_chat_memory/blob/0557a4c1de1969bdccdb5a5de4b3724dc94aa6f6/ 。定制材料路径为本仓库真实文件。

## 承载方式
现有15表足够，无新增Core schema。原始supplied JSON逐字保存在LegacyRecord.source_payload及import artifact，Event记录稳定dataset/kind/legacy_key/revision，memory_items.CLAIM.body_json.iris承载规范化结构，原始body的UNASSESSED不提升。Relation/profile/summary/index是带epistemic标签的claim对象，不冒充新已验证事实。源文件不修改，canonical projection可重建。所有dataset必须synthetic:*；当前适配器不接受生产数据。

| Iris结构和真实字段 | Canonical destination与语义 | 代码证据 |
|---|---|---|
| L1 ContextMessage: role,content,timestamp,token_count,source,metadata,persona_id | 原JSON artifact；role=user→USER_STATEMENT、assistant→MODEL_INFERENCE、system→OBSERVATION；time记录发生时间，source/message_id→未解析来源；token_count只是旧估算；persona_id仅legacy namespace，不替换Nana身份 | upstream:iris_memory/l1_buffer/models.py:15–83 |
| L1 segmented queues: group_id,segment_1/2/3,total_tokens,lengths | 只导出实际消息；段位/长度为队列运行态，不是持久经历或证据；L1删除并不产生tombstone | upstream:iris_memory/l1_buffer/models.py:86–129 |
| L2 MemoryEntry: id,content,metadata,persona_id,embedding | artifact保留全部输入；metadata.source=l1_summary/summary→SUMMARY，否则MODEL_INFERENCE（tool不等于用户原话）；id/persona和producer保存；embedding不用于Core MemoryIndex | upstream:iris_memory/l2_memory/models.py:17–147 |
| L2 SQLite memories: faiss_idx,memory_id,content,metadata(JSON),group_id,user_id,timestamp,kg_processed,persona_id | 稳定来源key和字段精确保留；冗余列与metadata冲突则REJECT，不选择一方；faiss_idx/kg_processed为旧索引/流水状态，不是可信度 | upstream:iris_memory/l2_memory/adapter.py:721–765 |
| L2 metadata: access_count,last_access_time,confidence,confidence_level,source,group/user/name,timestamp | 时间语义分离；confidence原值保留不转Core assessment；访问量不等于事实可信；source一般仅producer而无原始对话定位，不补造 | upstream:iris_memory/l2_memory/models.py:26–37,95–147；iris_memory/l1_buffer/buffer.py:970–1008 |
| L2 index_meta: version,embedding_model,embedding_dimensions,persona_id,free_list | opaque OBSERVATION artifact，不载入FAISS、不跨模型复用向量；重新embedding需要另阶段授权与验证 | upstream:iris_memory/l2_memory/adapter.py:777–788 |
| L3 GraphNode: id,label,name,content,confidence,access_count,last_access_time,created_time,source_memory_id,group_id,properties | MODEL_INFERENCE；Person/实体type/别名只保留，source_memory_id以legacy ref链接，不能无证据升级人物关系 | upstream:iris_memory/l3_kg/models.py:75–134；adapter.py:75–87 |
| L3 GraphEdge: source_id,target_id,relation_type,weight,confidence,access_count,last_access_time,created_time,source_memory_id,properties | Relation={subject,predicate,object} + inference claim；weight不等于事实；保留两端与source refs，缺端标未解析，不静默删边 | upstream:iris_memory/l3_kg/models.py:137–192；adapter.py:89–103 |
| UserProfile: user_id,user_name,version,historical_names,personality_tags,interests,occupation,language_style,communication_style,emotional_baseline,favorability,bot_relationship,important_dates,taboo_topics,important_events,custom_fields,field_meta,update_tracker | 完整画像为MODEL_INFERENCE；favorability不是Core preference或信任等级；custom_fields未知语义opaque保存，不自动生成人格/权限/经验 | upstream:iris_memory/profile/models.py:327–385,394–415；storage.py:187,247 |
| GroupProfile: group_id,group_name,version,interests,atmosphere_tags,long_term_tags,blacklist_topics,custom_fields,field_meta,update_tracker | 同上，群profile不能当用户事实 | upstream:iris_memory/profile/models.py:237–274 |
| FieldMeta: confidence,last_updated,update_count,source(rule/llm/manual)；update_tracker | 保留per-field原值；manual旧标志仍UNASSESSED；无原始时间链不能强行给整个profile发生时间 | upstream:iris_memory/profile/models.py:27–72,74–148 |
| ActionLedger key,state,updated_at,op,verify,note,actor,first_at,revision | ACTION_CLAIM；旧verify/state=VERIFIED保留原字面，不写actions/attempts/receipt，不认为Core曾执行；现状态与journal需分别带legacy_key/revision | materials/iris_customizations/NEW_FILES/action_ledger.py:141–157 |
| DecisionLog t,t_utc,tier,reason,query,top_k,hits,route,soft_confirm,window,ms,extra | OBSERVATION of legacy decision；不写Core decisions（有goal FK），不是Core新计划；UTC和CST镜像矛盾REJECT | materials/iris_customizations/NEW_FILES/decision_log.py:151–174 |
| ConversationFlow ts,ts_cst,umo,role,sender_id,sender_name,text,extra | 原始supplied行artifact；user→USER_STATEMENT，assistant→MODEL_INFERENCE；ts为来源发生时间，ts_cst镜像校验；4000字符clip意味着“完整导出行”不等于完整未裁剪对话 | materials/iris_customizations/NEW_FILES/conversation_flow.py:221–237；常量47–53 |

[源码确认] 文档注释写Chroma/Kuzu，但锁定实现实际是 **L2 FAISS+SQLite、L3 SQLite**；以 adapter 实际建表为准。不能照旧注释设计读库器。

## 来源/时间/可信语义
IrisRecord envelope.dataset_id=稳定来源实例身份，kind+legacy_key+revision=稳定旧key；原有id/群/user/persona始终保留。没有native id的L1/流水必须由导出方给稳定file+line/message locator，不能每次导入生成UUID当legacy key。annotation是操作者语义sidecar，不是Iris原有字段；仅user原话允许，并保持非VERIFIED。

legacy_record_time_us是Iris行创建/更新/消息时间；underlying_event_time_us仅L1/流水可沿用，summary/KG/profile未知。legacy_observed_at由导出方显式提供，否则UNKNOWN；Core observed/recorded是本次导入时钟，绝不伪装旧发生时间。naive时间按锁定定制timeutil的历史UTC约定处理且标LEGACY_NAIVE_UTC_ASSUMPTION；不是通用猜测。错误/缺失时间UNKNOWN、保留原值；明确镜像矛盾REJECT。

源码对删除采用DELETE（L2 adapter.py:1808,2037,2142；L3 adapter.py:986,1271；profile storage.py:529–704），原样本不存在的记录不能恢复，也不能推断撤回理由。absence≠retraction；显式Core撤回将保留artifact。Dream contradiction/pruning会覆盖/删旧结构，不能恢复被删除内容或把最新模型总结当完整历史。无法恢复项在manifest/报告披露，不静默补造。

## 导入协议和边界
LegacyMemorySource提供有界typed synthetic records；IrisAdapter→既有LegacyImporter，每条原始证据原子提交，随后iris projection事务。两事务之间崩溃重启用相同key补齐projection，原始记录不会重复。不同raw/annotation沿用key时拒绝collision，不覆盖；batch最多100条。manifest固定input hash、source identities、逐条import/duplicate/rejected/unmapped/warnings；完整raw batch artifact包含被拒绝记录，支持恢复和无静默丢失。

任何导入都不建Goal/Action/Grant/Budget/Strategy/Identity，不自动产生可执行experience。经验候选不是此次迁移输出；旧偏好只能作为待评估记忆输入。scope、profile、关系链接与向量重新索引需要明确评估，不能借导入扩大权限。

[实测] 14条合成真实schema夹具覆盖11种结构；36 targeted passed（新7+S6 29）。重复导入14duplicate；真实SIGKILL -9在首条原始证据落盘和projection之前，恢复1duplicate+13imported；身份和前缀相同。missing字段/镜像冲突/冗余字段冲突/未知kind拒绝，错时间/无source/未知字段保存并告警。首轮1fail因测试把2026-09-01误写为2025的epoch常量，改为正确2026固定期望后36pass，未降低断言。
