# Nana cloud integration: current facts and wiring boundary

[文档/历史实测] PROJECT_BRAIN/09_STATE.md、01_architecture.md记录生产奈奈运行于AstrBot 4.28.0，Iris记忆插件及独立B站进程。**本轮没有观察生产当前运行态**；服务器hostname、容器、实时版本/路径必须由下一次授权preflight确认。GitHub仓库不是正在运行的云端Core。开发Core在Codex /workspace/nana-core，基线d79fa3eb72efd1907d314780a5c8677bbc361021，263pass/1skip，E12 NOT_RUN。

| Entity | Current authority / future boundary |
|---|---|
| Production Nana | 原AstrBot/Iris/B站继续真实业务；本轮未接线或改动 |
| Development Nana Core | 独立Store/Identity/ActionKernel与合成实验；非生产实例 |
| GitHub repository | 工程事实、可控副本与版本保存，不是runtime或memory DB |
| Model providers | 可替换ModelPort，只提案，不拥有身份/授权/receipt；当前真实开发端点0 |
| Platform adapters | AstrBot/QQ/NapCat/B站提供Observation、legacy来源和Capability，不是第二Core |
| State authority | 当前生产Iris/各账本；未来受控canonical Core Store，阶段式迁移 |
| Execution authority | 当前旧系统。Core shadow永远无现实执行权；owner epoch仍复用S6 |

```mermaid
flowchart LR
  Host[Production AstrBot/B站 event hook: future authorized] --> A[HostObservationAdapter]
  A --> E[Evidence + UNASSESSED Observation]
  Iris[Iris read-only export: future authorized] --> Bundle[Minimally exposed export bundle]
  Bundle --> Import[Reviewed canonical importer]
  E --> Shadow[Same host ShadowBridge + same Core Identity/Store]
  Import --> Shadow
  Shadow --> Draft[Goal / Plan / Decision draft]
  Draft --> Stop[SHADOW_BLOCKED]
  Legacy[Existing legacy executor] --> Business[Existing real business]
```

同宿主嵌入、单Store writer、串行有界任务；不长期运行两个完整自治Runtime。shadow DB独立于生产Iris DB，identity初始化/恢复由既有Store负责，不由模型重建。宿主只传递已筛选事件，不默认接所有私人聊天。出口STOP不可通过配置打开。

源码依据：src/nana_core/storage/sqlite_store.py Store.ingest/identity/transaction；actions.py ActionKernel；migration/routing.py OWNER_KEY/select_owner；migration/shadow.py ShadowObserver；migration/iris.py IrisAdapter；materials/iris_customizations/NEW_FILES/conversation_flow.py:297 append_event；src/bili_agent/bili_event_pump.py、bili_send_core.py。正式Iris字段依据docs/nana_core_phase3_iris_mapping.md及锁定source manifest；本次未复制AGPL执行代码。

契约：HostEvent保留platform/channel/sender/event/conversation/reply/附件reference/来源/原时间。Adapter只生成unrelated Observation，原envelope作为artifact；事件命名空间区分host/platform，稳定key包括conversation/event/revision。重复内容不是重复事件。缺失/坏时间UNKNOWN，不用接收时间补造发生时间；原事件聊天不是可信事实。附件不下载；raw_content_reference是opaque locator，不自动读文件。

## Read-only export and preflight (M2)
`integration/exporter.py`提供API/CLI `nana-iris-export`：必须显式选择已经一致备份的SQLite/JSON快照；SQLite `mode=ro&immutable=1`，拒绝未清理WAL/journal，固定memories/nodes/edges表。**不对活跃DB使用immutable，不运行Iris初始化代码**，不打开FAISS。L1/画像/流水/index_meta通过操作者提取的有界JSON envelope读取；不会假装自动理解所有原生磁盘wrapper。14类夹具中的11schema全可封装，实际磁盘reader仅上述固定表和JSON envelope。默认hash-only，redact逐字段最小白名单，include须未来明确授权且stdout敏感，不上传Git；弱口令/低熵文本hash不是匿名化保证。每条稳定legacy id/payload hash/source/version/type/time/relation/UNASSESSED，manifest有界8MiB/100条，无来源写。

`nana-cloud-preflight`只stat显式路径、读取包版本metadata/Python/SQLite、disk/当前进程和hostname hash。不会import插件、读配置、secret、聊天、DB，不安装/修复。当前Core要求Python>=3.12、SQLite>=3.51.3和Pydantic2.13.4；真实云端是否满足未知，若不满足BLOCKED，不擅自升级。未运行中的Iris版本/事件hook/快照一致性保留UNKNOWN；PASS不是自动获准部署。4 targeted passed，fixture DB逐字和目录列表未变化，dev预检UNKNOWN而不是宣称production ready。

## Shadow Bridge and reconciliation (M3)
`integration/shadow.py`复用Store/Artifact/Observation/CLAIM保存Goal/Plan/Decision **draft**。不创建活跃goal、不实例化Runtime/ActionKernel/可执行port，external_execute字段Literal[False]，任何execute恒SHADOW_BLOCKED；零现实预算、零Attempt/Grant/Strategy。直接调用ShadowCapabilityPort也拒绝。引用memory/evidence/experience必须在同一identity的Store真实存在。当前fixture decision可运行；real_model声明没有CallLedger绑定一律拒绝，不能伪造语义通过。真实ModelPort shadow wiring仍需授权端点后绑定账本，不影响纯shadow准备。

Export bundle manifest独立校验后以UNASSESSED Observation/Evidence接收；hash-only不变成原始正文或可采信事实。原synthetic IrisAdapter不放开production scope；真实include bundle canonical导入需未来显式数据范围核验，不在本轮偷改限制。

Reconciliation纯比较同一event的interpretation/memory/evidence/goal/decision/planned action，列重要历史遗漏、changed inputs与causal attribution UNKNOWN。差异不等于优劣；模型/经验/记忆改变仅列输入差异，因果需要既有matched ablation另证。当前legacy path是显式fixture，不冒充AstrBot真实判断。

[实测] 7 targeted passed；CLI实际Store关闭/重开、14条hash-only export→evidence→host observation→draft，重复source/event/decision幂等；identity一致、actions/attempts/budgets/grants/strategies/goals/plans均0。shadow_reconciliation.json/md。首次人类报告生成用了系统Python而无editable包，纠正为既有.venv Python；实现及测试未改断言。
