# Graphiti — 时间语义值得借，图数据库不是前置条件

固定 `d50741d1bf463cbe3859eb73914cbff1b66839e6`，Python，Apache-2.0。解决多episode实体与关系事实的增量提取、检索、过期。
权威是配置driver持久节点/边；不是Nana subject authority。extraction/resolve调用LLM/embedding，不能称零token记忆。

## 时间字段逐项

[graphiti_core/edges.py](https://github.com/getzep/graphiti/blob/d50741d1bf463cbe3859eb73914cbff1b66839e6/graphiti_core/edges.py#L263)、[graphiti_core/nodes.py](https://github.com/getzep/graphiti/blob/d50741d1bf463cbe3859eb73914cbff1b66839e6/graphiti_core/nodes.py#L318)：

| 字段 | 此SHA实际意义 | Nana建议映射 |
|---|---|---|
| created_at | graph object进入系统的记录时间 | recorded/ingested time，不是fact开始时间 |
| Episode.valid_at | 原episode document/reference发生时间 | event_time，与observed/ingested分开 |
| EntityEdge.valid_at | fact开始成立 | valid_from，可未知 |
| EntityEdge.invalid_at | fact停止成立 | valid_until，通常半开区间 |
| expired_at | 系统将edge标成已失效/历史的时间 | invalidation recorded time；不是TTL/删除 |
| reference_time | 生成该edge的episode reference timestamp | statement/reference anchor，不是承诺履行 |

[graphiti_core/utils/maintenance/temporal_edge_utils.py](https://github.com/getzep/graphiti/blob/d50741d1bf463cbe3859eb73914cbff1b66839e6/graphiti_core/utils/maintenance/temporal_edge_utils.py#L39) 明确未来计划的valid_at不能直接用未来发生日；“计划明天去东京”现在成立的是**计划声明**，不是明天已到访。soft deadline不能自动invalid_at；持续不可用until才可作为结束界。
该归一化是英文regex heuristic，不是通用跨语言事实认证；ensure_utc接受naive并假定UTC，Nana应继续严格拒绝无timezone/非canonical来源，而非照抄。

## 更新、冲突与历史

[graphiti_core/utils/maintenance/edge_operations.py](https://github.com/getzep/graphiti/blob/d50741d1bf463cbe3859eb73914cbff1b66839e6/graphiti_core/utils/maintenance/edge_operations.py#L715)：先date再temporal invalidation；later candidate可结束earlier incoming edge；resolve_edge_contradictions只在时间相交且旧start<新start时截断旧edge，expired_at取系统now。旧edge保留，通常保存更新而非覆盖消失。
LLM提出duplicate/contradiction候选，时间逻辑不证明内容真实；同起点/时间缺失不能据此擅自挑一方为真。SOURCE→candidate→Core assessment/correction仍必须保留。

- 以前喜欢A、现在喜欢B：同entity/scope/predicate，statement evidence+correction；不要把两个值都当当前，也不要靠全局latest消息解决跨域。
- 以前住东京、现在大阪：valid interval变化与系统何时获知分开；晚到旧资料不能把当前改回东京。
- 计划明天去、明天真的去了：PLAN/COMMITMENT与OCCURRED两个不同claim；没有Observation不能提升。
- temporal relationship edge：信任某project domain的证据可有有效窗口，冲突repair必须target；不建“亲密度总分”。

## 检索与删除

[graphiti_core/search/search_config.py](https://github.com/getzep/graphiti/blob/d50741d1bf463cbe3859eb73914cbff1b66839e6/graphiti_core/search/search_config.py#L32) hybrid BM25/cosine/BFS，RRF/MMR/cross encoder可选；search_filters对valid/invalid/created/expired支持组合条件。driver-specific实现不应被一份filter DTO证明为全driver语义等价。
Episode→edge IDs给来源线索；delete node/edge不是Nana完整依赖/PrivacyJournal删除协议，备份/摘要/模型缓存闭包未由本研究证明。
无24h主体循环、承诺adoption、social gate、Grant/Manager；此类问题NOT_APPLICABLE，不是项目缺陷。

## NANA_TEMPORAL_FACT_VIEW_CONCEPT — DESIGN_ONLY

同一Store的Memories/Evidence/assessment revisions→可重建TemporalFactView：
`entity + scope + predicate + assertion_kind + evidence refs + valid_from/until(known/unknown) + recorded_from/to + reference_time + assessment + privacy/deletion state`。
query同时接受`as_of_valid`和`as_of_known`。recorded_to由superseding assessment历史推导，不能从当前覆盖行假装完整双时间。缺失时间UNKNOWN，不能默认从宇宙开始成立。
历史查询仍必须先执行今天的privacy deletion，旧快照不允许恢复已忘内容。时间关系不构成authority；跨scope不合并。
未来migration先单独ADR和fixtures，不能现在添加第二graph DB或重复事件authority。

11个隔离检查中5项实际执行了reviewed AST temporal函数；结果支持这些函数语义，不是Graphiti端到端/抽取准确率/driver qualification。
VERDICT：BORROW_PATTERN。最大价值是多时间轴与future assertion边界；最大风险是把抽取文本当事实或自动失效合法旧记录。
