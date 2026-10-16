# Mem0 — BENCHMARK_FIRST

固定 `0724291bd864cf807e88ee8981c8226644e8fb42`；Python/TS，Apache-2.0。只评这个OSS snapshot，不把Cloud/platform功能算进来。

## 实际source path

[mem0/memory/main.py](https://github.com/mem0ai/mem0/blob/0724291bd864cf807e88ee8981c8226644e8fb42/mem0/memory/main.py#L881) infer=False逐消息embedding+persist，不调用fact-extraction LLM，但仍可能调用embed provider。infer=True的当前主路径是V3 phased batch：context gathering→extraction→batch embedding→hash dedup→vector insert→history→entity linking。不是旧博客里的逐条ADD/UPDATE/DELETE decision循环。
extraction错误重抛让调用者能区分no facts与model unavailable；JSON解析失败仍可能空列表。async版本同文件2455+，异步IO不等于无需模型。

[mem0/memory/main.py](https://github.com/mem0ai/mem0/blob/0724291bd864cf807e88ee8981c8226644e8fb42/mem0/memory/main.py#L2052) update保留created、改updated/hash/vector，再写history/entity cleanup。delete:2114先删vector后把old_memory写入DELETE history；这可审计，但不等于彻底清除内容。entity cleanup是non-fatal；多存储不是一个事务，需对partial failure/retry单独测试。
filters以user_id/agent_id/run_id建立scope，metadata身份键会被剥离，防止freeform metadata搬到别的tenant；这值得作为对照，但不是Nana authority/隐私域的全套模型。

## 平台边界而非宣传功能

search reference_date明确raise ValueError，tests/memory/test_temporal_feature_notice.py对应；project.update(decay=True)在OSS拒绝，test_decay_feature_notice.py有断言。
expiration_date以UTC日界`date < today`过滤，是retention visibility，不是事实有效时间；无time-of-day精度，bad stored date路径可返回not expired，不适合照搬hard privacy。
在本次`mem0/memory/`树中没有graph_memory实现；Dream/Synthesis/Merge/Supersede状态机未在所读OSS路径验证，记UNKNOWN/NOT_PRESENT_IN_SELECTED_TREE。不能因为API营销名假定存在。
rerank可配置，search explain有score_details。rank不是source truth。

## 未来公平benchmark（未执行）

同一纯synthetic 90-day transcript、固定版本/provider/mock与真实模型分轨、固定冻结eval questions，不把自己的summary作为gold。
两个track：A typed facts→storage/retrieval（不比抽取）；B相同authorized模型做candidate extraction→各自准入（未来另行授权）；Nana不被迫放松到LLM事实即authority。

| 指标 | 合成gold/主要失败 |
|---|---|
| exact fact recall | exact支持引用；编造答案计错 |
| preference/temporal update | 新值current，旧值historical；晚到旧消息不复活 |
| contradiction | 未解决冲突显式完整，不挑看似顺耳一边 |
| entity/relationship | 同名不同entity/scope不串；Anchor≠全部关系 |
| long-term recall | 跨月相关source仍可找，不奖励recent重复 |
| irrelevant retrieval | 空query/无关问能返回empty/unknown |
| delete closure | raw/derived/index/history/export/restore分别检验 |
| stale resurrection | checkpoint restore+reconsolidation不能重造删除事实 |
| provenance | source root/path/time/authority能重建，不只memory UUID |
| cost/latency | capture+embed+extract+search+rerank总tokens/calls/bytes/p50/p95 |

每次上游batch成功、本地history失败，及delete完成、link cleanup失败都注入故障。benchmark结果不得预填Nana胜；当前无准确率/成本赢家。
VERDICT：BENCHMARK_ONLY；不集成作第二记忆系统，不复制其delete history语义。
