# NANA_MEMORY_VNEXT_CONCEPT — DESIGN_ONLY / 非migration授权

## 需要什么

| 候选 | 结论/理由 | 与当前资产关系 |
|---|---|---|
| TemporalFactView | BORROW_PATTERN，高价值 | Memories+Evidence+correction revisions之上，非新truth |
| bi-temporal validity | 值得下一Memory ADR | event/observed/ingested已有，不能冒充valid interval+known interval |
| temperature placement | 借Letta组织，先做策略对照 | same ContextAssembler，tier不等于authority/privacy |
| MMR-like diversity | 实验值得，先benchmark | 全部scope/privacy/contradiction过滤后才rerank |
| consolidation window | 借YuriOS分片，让C准入 | summary=candidate，原Evidence保留，删除闭包 |
| contradiction graph | OPTIONAL投影 | 用现有dependency/family links，不先装Neo4j |
| temporal relationship edges | FUTURE扩现有source-view | trustdomain/breach/targetrepair，不搞affection |
| readable export | BORROW_PATTERN，隐私成本需控 | read-only derived，非可无审查import的权威包 |
| Living Journal | derivedactivity/episode索引 | planned/attempted/unknown/verified分开 |
| synthesis | 必须带source+coverage+contradiction+freshness | 通过MemoryCandidate/admission，不是dream事实 |
| benchmark suite | BENCHMARK_ONLY先行 | Mem0/Graphiti比较，不提前宣称更强 |

## 时间查询合同

Assertion identity按entity/scope/predicate/epistemic kind稳定，value/revision另存；事实修改≠authority升级。
valid_from/until允许unknown/uncertain bounds；reference_time是statement anchor；observed、ingested保持现义；recorded interval来自revision日志。
`as_of_valid=t, as_of_known=k`回答“在k时系统知道t时什么”；要保留当时uncertainty/contradiction，不从今天结论反填过去。
计划/承诺/adoption/履行必须四分。deadline到来不会把未来claim变事实。关系boundary未撤销不能按recency自动失效。

## 检索合同

1. privacy journal freshness / destination / entity / scope / support / lifecycle是硬门；不可先向外embed再过滤。
2. canonical/header/current commitments/conflicts等构成必要语义，不按vector score删去。
3. bounded candidates由关键词/可选embedding得来；embedding cache持久键含source revision/model version，删除可定位到cache。
4. 同一factroot的改述先去重；合法diversity只能在候选集里选，不能把冲突包拆散，不为多样性拉入别的人的事实。
5. ContextManifest标注coverage/omissions/tokenizer/schema/source IDs，发模型前再freshness校验。

## Consolidation lifecycle

eligible finished sources→candidate with evidence backlinks→semantic review/assessment→正式Memory；所有更新经现有Memory/RecordService transaction，source-erased/stale候选拒绝。
merge建议不能抹掉distinct independent roots；同source重复summary不增加confidence/support count。
删除请求穿透raw、summary、index、journal/export/context引用、managedbackup。历史asof不能绕过删除。自动retrievaldecay不物理清除；retention需要独立明确policy/authority。
反思不能发明事件，dreaminsight可只留为hypothesis，不允许CanonicalIdentity或value自动overwrite。

## 两个反例与迁移纪律

“我以前喜欢A”被晚上summary写回“喜欢A”，后来已经纠正成B：source revision stale→拒绝；不能让较新summary时间覆盖真正较新fact。
“删掉某私人经历”之后旧archive导入：PrivacyJournal先执行，再replay；已删root不得复活，连derived叙述也要撤掉。不能复制YuriOS Git保留旧值作为彻底删除。

真正施工需独立implementation ADR说明validity字段/indices与旧source保留策略。现有schema10/default7/8不动，本研究没有创建表或migration。
