# Memory matrix — 先来源/删除，再召回质量

S/T/D/U含义同05；每格是该版本已读机制，不是完备安全认证。Nana当前Relational已存在，不能把其关系与personality projection当未来新增。

| 指标 | Nana | YuriOS | Graphiti | Letta/Code | Mem0 OSS | Second-Me | Anima | tomo |
|---|---|---|---|---|---|---|---|---|
| raw evidence | typed Evidence/artifact | rawday files | episode.content | transcript/files/blocks | message context+history | rawdocuments | episodictext+source | session/archive |
| episodic | typed/time/source | journal | episodicnodes | recall/transcript | extracted payload role | notes/timeline | kindepisodic | dailyjournal |
| semantic | assessed memory | facts/USER | entityedges | blocks/files | vector facts | L0/L1 abstractions | semantic gists | files/LCM |
| relationship | sourced facets/anchor非排他 | USER partner | entityrelation可表达 | memory/persona可表达，正式facetU | text facts，无subject关系authority | user profile facets | self/person记忆prompt | people files/owner路由 |
| temporal truth | 三时间+correction；validinterval缺口 | textday/recency | explicit valid/invalid/expired/reference | timestamps，双时间U | expiry date，asof参数拒绝 | datedtimeline | recencystrength | datedrollup |
| correction | explicit revision/supersession | slotmerge文本 | contradiction invalidation | blockedit/Gitmerge | updatepayload+history | profile rebuild | remember/dedup | files/rollup |
| contradiction | DISPUTED完整bundle | heuristic/extract reconcile | extraction+resolve | merge conflicts≠semantic conflict | additive main；当前语义U | modelmerge | U | U |
| provenance | evidence/dependency/sourcekind | file/span/quarantine | episodes+edge refs | file/git/transcript | metadata/history/attribution | noteIds/profile | source+links | archive/files/source annotations |
| deletion | PrivacyJournal+managedcopy closure | tombstone+Git旧原文保留 | delete node/edge，闭包U | Git/history/body closureU | vector删+old text history | status/file处理，模型unlearnU | archive/purge | files/archive closureU |
| retention | lifecycle与privacy分开 | recency retrievalfade | expiry≠delete | context/layout limits | expiration visibility | file/profile/training | scalar strength可archive/purge | summaries/archive |
| consolidation | admission/reflection边界已有；大规模window未测 | DREAM finished days | episode graph extraction | asyncreflection worker | extraction batch，dreamU | L0→L1→L2 | sleep gists/reflection/dream | LCMdaily/compact |
| retrieval | bounded lexical terms+priority | blendedvector/keyword | hybrid/BFS/RRF/MMR | files/read/search tools | vector/BM25+rerank | profile/query/train | vectorrecencyimportance | literal/LCM/archive |
| diversity | 无MMR实现证据 | blendedMMR/perdoccap | MMR selectable | filetree组织 | rerank，diversityU | facets组织 | cluster | summaries层次 |
| context tiers | mandatory/priority/source filters | soul/USER pinned+recall | query results | system hot/files cold | consumer负责 | profile/layers | self/working/recent | MEMORY.md+日记+archive |
| inspectability | records可查，统一readable面缺口 | humanfiles+innerlife | node/edge APIs | memoryFS/Git | CRUD/explain | localUI/files | UI/journal | Study/people/LCM |
| cache/source separation | explicit projections/state stamps | files authority/indexcache | driver graph authority | gitmemory authority+compile | vector与history双写 | raw/profile/training多层 | SQLite/self-model | files/transcript衍生 |
| self-belief | independent roots+counter | persona gated；partnerauto | 不是subject模型 | editableidentity blocks | 不是subject模型 | representsuser | LLM selfrewrite | prompt/files约定 |
| identity protection | canonicalrevision/authority | constitutionreadonly+soulreview | — | agentid+blocks非Nana等价 | — | learneduseralignment | versionedtextself | identityfiles |

## Nana当前具体实现与缺口

[`src/nana_core/continuity/memory.py:188`](https://github.com/xuni7-ui/nana-core/blob/67326d195edd0693d41eacc63fcc00e1c3205bd6/src/nana_core/continuity/memory.py#L188) 先entity/scope/privacy/lifecycle/assessment过滤，再bounded query_terms排名；[`src/nana_core/continuity/context.py:227`](https://github.com/xuni7-ui/nana-core/blob/67326d195edd0693d41eacc63fcc00e1c3205bd6/src/nana_core/continuity/context.py#L227) 以authority/relevance/importance/significance/recency排序。不是纯top-k embedding，也没有成熟semantic recall基准。
[`src/nana_core/continuity/context.py:248`](https://github.com/xuni7-ui/nana-core/blob/67326d195edd0693d41eacc63fcc00e1c3205bd6/src/nana_core/continuity/context.py#L248) 矛盾包整体注入，token不足不能只留一方。[`src/nana_core/continuity/records.py:13`](https://github.com/xuni7-ui/nana-core/blob/67326d195edd0693d41eacc63fcc00e1c3205bd6/src/nana_core/continuity/records.py#L13) privacy取支持最高敏感度，revision/dependency用于erasure；这些必须先于任何MMR/温度/压缩。

三个最大现实缺口：
1. 时间有效区间和recorded-asof表达；当前event/observed/ingested不自动等于完整bi-temporal。
2. 同义/跨月召回与diversity质量/成本没有统一公平测量；词汇匹配不够，不意味着马上装vectorDB。
3. source-linked synthesis的生命周期：候选、证据coverage、冲突、重算、删除和restore，还需要真实规模的离线测评；未授权realmemory。

推荐顺序：先冻结synthetic eval corpus→可重建TemporalFactView→检索多样性实验→维护window。三者分开里程碑，不为一次研究引入第二存储。
Privacy delete高于历史asof；temperature和retrievaldecay不能偷偷成为retention authority。
