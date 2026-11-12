# R1 研究结论：此两跳查询不推广通用图展开

**2026-11-12 续办实测结论：停止本窄候选的集成推进。** 下文第一阶段 12/24→24/24 只对近期快照成立；新增查询感知控制仅组合原 `WorldModel.view`，同样 24/24，且在无关分支反例中 2 次读取命中，通用展开 32 次耗尽仍未命中。证据与限制见本文末尾。原始结果和源指纹按历史版本保留，不用新结论改写旧数据。此结论不否定 Graphiti 的其他机制或未来真正需要通用多跳的场景。

[源码/实测，2026-11-12 Asia/Shanghai] Codex B，`UNIVERSAL_EXPERIENCE_AND_TECH_TRANSFER` / 原总任务。基线 A `f583f187152c452b9638ff2d6c96b91bd4fe68da`；独立工作树/研究分支，无 Core 源码改动。DOMAIN S2-C02/C03、S5-C02、S6-C02 / Advanced。候选只扩展可供原 C 使用的来源路径，不创造动机、决定学什么或授予操作权限。

## 固定来源与实际机制

上游 [getzep/graphiti@ebef986a0b2360211b65751c111cacb4a7d790eb](https://github.com/getzep/graphiti/tree/ebef986a0b2360211b65751c111cacb4a7d790eb)，声明 0.31.2 / Apache-2.0；实际读取文件指纹见 `upstream-source.json`。观察到 HEAD 提交时间 2026-11-11，不据单次快照推断完整维护健康。没有复制 SDK、查询文本或第三方源码，也没有安装/运行其依赖或宣称上游测试通过。

真实调用路径：`Graphiti.add_episode` → 节点/边提取与 `_extract_and_resolve_edges` → `extract_edges` / `resolve_extracted_edges` → `_process_episode_data` / `add_nodes_and_edges_bulk`。`EntityEdge` 的 `episodes` 保存来源，`valid_at/invalid_at/expired_at/reference_time` 区分时间；`remove_episode` 移除该 episode 支持，仍有其他 episode 的边保留。检索 `search.edge_search` 按配置组合全文、向量、BFS，随后 RRF/其他排序；`search_utils.edge_bfs_search` 由 origin UUID 和深度构造实际图查询，不只是宣传。

默认 Neo4jDriver、OpenAIClient、OpenAIEmbedder；核心依赖还含 pydantic、tenacity、numpy、posthog 等，可选其他图驱动/供应商。常规提取/嵌入需要模型与图数据库；未发现必须另接消息队列的基本路径。上游已有 edge/temporal/BFS/security 等测试文件；本轮仅审查入口，未运行依赖外部服务的上游集成测试。group_id、软时态失效和删除接口不直接等价于 Nana 的单主体命名空间、纠错与物理隐私闭包。

## Nana 差额与改造

直接搬入时态图或再建记忆服务的方案本轮**否定**：原 `TemporalMemoryService`、`WorldModel.view`、`RecordService` 已有有效/已知时间、来源、冲突、纠错与撤回语义。新增外部图权威只增加同步、凭据和恢复成本，未证明收益。

保留的窄缺口：现有 `WorldModel.snapshot(32)` 按最近 key 投影，不接受已知关注实体作为检索锚点；较早的“关注→主题→资料”路径会被近期无关 key 挤掉。原 `world_current(scope,entity_id,predicate_key,known_at_us)` 已有索引，足以试验有界关联展开，不需要图数据库或新索引。

`tools/nana_next_experience/association_probe.py:linked_recall` 从调用方提供的 canonical seed 和谓词集合出发，最多 32 次原 `WorldModel.view`、深度 1–3；只将明确 `{'entity_id': ...}` 值视为关联。每步仍由原时态/来源/隐私投影裁定；冲突/不确定不跨越，不把 BELIEF 变 RAW_OBSERVATION。返回实体路径、谓词和原 support record IDs，不返回新事实。候选需要单 scope，缓存仅单次查询，循环停止；已知时间、撤回、跨实例和同身份重启均独立验证。同步读之间检查 deadline，不能硬中断 SQLite；晚结果标记并扣留。原隐私检查及同连接写变化会扣留结果，尚不是跨进程变更订阅协议。

接口：`linked_recall(world, seed, predicates=..., max_views=32, max_depth=2, timeout_ms=100, valid_at_us=..., known_at_us=...) -> AssociationResult`。潜在接入位置是原 ContextAssembler/World 只读候选装配；原 C 决定锚点、关注与选择，原 G 独立评价后才可视为技能。当前没有接线、发布证书、持久化、后台循环或第二学习权威。

## 同预算对照与反例

固定合成语料 88 个 world keys、8 个根、24 条两跳路径；前半来源较旧、后半较近，并含 40 个无关 key。目标路径 SHA256 `daeb76c2b81ec955e0471e3ecc2e29c93523b8e800740841c7573081242bf982`，由语料定义在两种检索运行前固定。两者最多读 32 个原 World 视图；snapshot 实际 32，候选每根实际 6。交替顺序、各 40 次，原始 samples/cases 在 `results.json`，初次结果 `first-results.json` 保留。

| 同一台开发机、此语料 | 原 snapshot32 | 关联候选 linked32 |
|---|---:|---:|
| 可提供完整两跳支持的唯一目标 | 12/24 | 24/24 |
| 候选错误路径 | 不适用，快照不是分类器 | 0 |
| P50 / P95 | 5.228 / 8.466 ms | 1.174 / 2.009 ms |
| 40 样本合计 process CPU | 233.001 ms | 50.919 ms |
| 独立 tracemalloc pass peak | 90,461 B | 36,657 B |

这些数值不是 Graphiti runtime 比赛或全局提速：候选利用已有 seed，原快照不是最优 query-aware baseline；读取实际数量不同。Python allocation peak 不是 RSS。原 Store family 实际分配前后均 5,844,992 B，检索 SQL 写入/事件新增为 0；合成语料本身仍有正常存储成本。LLM 请求 0，真实 Token/账单未计量，不宣称 Token 节省。

`final6.txt`：5 个新实验测试加原时态冲突/纠错/撤回测试，共 6 passed / 8 deselected，2.37s；初次 4 passed 在 `first4.txt`。覆盖旧源召回、冲突、PERSONAL 尾边、过期、循环、32-view/超时、读中撤回、同身份重启、已知时间及两个独立 Store 无共享缓存。没有失败样本被删掉或改成通过。

```sh
PYTHONPATH=src:. python -m pytest -q tests/world_loop/test_association_research.py tests/world_loop/test_foundation.py -k 'association or temporal_conflict'
PYTHONPATH=src:. python -m tools.nana_next_experience.association_compare --output work/association-results.json
```

## 集成条件、收益与未证明项

可验证收益仅是此结构化语料的跨关联召回，能让原 S2 旧来源通过 S5 可读投影成为未来 S6 的可选材料；尚未证明 C 更自主、S8 真实学习/迁移或关系/情感改变。当前不应生产集成。A 若采纳，下一步以独立、更不利的真实形状语料和 query-aware 单跳/SQL 基线对照，再经原 C 的后续选择、撤回与消融证明因果收益；不要只把本数字当验收。

不支持普通自然语言/隐式关系提取、跨 scope、向量语义或 >32 视图的大规模查询；不证明长期遗忘、源恢复物理闭包或 Token 节省。无 schema/数据迁移，回退删除这组研究工具/测试即可，无运行态变化。源码表锚 `710359287620f161efa52955bc7ffc1c1a96d0de214ab5d1a21e11c30cc2c628`，不自指。产品 PR #14 独立；此候选提交给 A 评估，不能自动接入原 Store/MemoryService/C。


## 续办：查询感知基线和否定结论

正常合入 A `071669bd62a1a8f5fa812775ae8518c12b727ebc`；完整保留其私问/学习/原Store恢复成果与两份账本。新控制 `association_direct_baseline.direct_two_hop` 只按问题给定的有序谓词调用现有 WorldModel.view，不直接查图SQL、不写Core。所有方法面对同一根和问题，linked API内部仅接受谓词集合、忽略顺序；这项信息损失是当前候选的限制，不把额外节点当虚假事实。

`query-aware-results.json` 保留原88keys/8roots/24固定目标、同32视图上限和原目标SHA。轮换执行顺序，每方法40样本：原快照12/24，linked24/24，direct24/24；linked/direct均实际6视图。P50/P95分别为快照5.490/7.143ms、linked1.278/1.654ms、direct1.092/1.332ms；CPU合计224.326/51.199/43.840ms，独立tracemalloc peak 88562/39777/38000B。原Store无检索写入/事件新增，family分配前后不变。不同于首阶段的机器测量单列，不混成全局性能结论。

新增65key反例：固定旧interest→needs目标，添加较新的无关分支。同32视图上限，linked耗尽32次、匹配目标0、产生24条不符合此查询模式的原始关联路径；direct原API组合读2次、匹配1/1，无额外路径。两者均0模型/0Store写；结果不是自然语言问答或事实信任评分。调用方过滤关联路径虽可改善相关性，但在这个固定模式中，直接组合原查询更简单。

两个方法共用原有冲突、隐私、过期、循环、撤回、已知时间、重启、实例和预算反例。`query-aware-tests.txt`：12 passed/8 deselected，4.97s。源码表`query-aware-source-sha256.json`锚619377c23dc7de4cf7187390ead3e1cc1dd34d9f6595a28dcb1408ba73336f6b，原source-sha256.json仅代表第一阶段对应Git版本。没有Core集成/数据迁移/新增模型调用。

决策：撤回通用图展开的集成候选，保留独立分支和可执行对照，结束本窄主题。原API已有足够能力处理已知两跳模式；未来若原C实际提出更一般的关系检索缺口，再以独立查询语料重新评估，不能凭首阶段24/24直接上线。此为有证据的否定结论，不要求A为本候选新增图服务、接口或生产验证负担。
