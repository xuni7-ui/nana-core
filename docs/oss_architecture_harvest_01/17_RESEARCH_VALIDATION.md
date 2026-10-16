# Research verification / delivery boundaries

## 实测

- Public repositories: 14；fixed snapshots: 15（Letta current entry+archive分开）。
- Deep-read projects: 7，定义是多个关键源码机制+相关test断言，不是读过每行/每个子系统。
- Directly inspected external source files: 75；test files: 19；其它spec/docs加上共98。精确range/hash在sources manifest；不把rg全树匹配当全文阅读。
- 11 isolated semantic/abstract checks PASS；selected AST only/no upstream package imports。Graphiti5、YuriOS中断gate4、抽象effect-before-checkpoint gap1、DREAM失败记账观察1。抽象gap项是反例预期，**不是LangGraph/Temporal运行故障测试**；DREAM项确认上游缺陷存在，不代表其维护正确性PASS。
- Anima `tests/test_store.py` **17 passed /0fail /0error /0skip**, CPython3.12.14，fakeclock/fakeembeddings/tempSQLite；socket connect/create_connection和urlopen强制拒绝，实际网络/LLM0。只测memory mechanics，不认证agent/sleep/effect safety。
- 其它上游完整suite NOT_RUN；真实模型/Graphiti drivers/Temporal server/Letta API/真实社交/perception均NOT_RUN。
- Nana完整regression本轮不重跑：业务/schema/tests/dependency不变。929/0/1是基线历史证据，不是本研究重新跑的结果。

## 重现

按sources_manifest把public repos clone到独立目录，目录名owner__repo。Letta archive目录用letta-ai__letta-archive，并checkout精确SHA；每个文件hash不符停止比较。不要下载latest来重跑这份报告。

```sh
python docs/oss_architecture_harvest_01/research_semantic_probe.py /path/to/public-checkouts
python docs/oss_architecture_harvest_01/research_anima_store_tests.py /path/to/public-checkouts
```

这两个是研究comparison脚本，不属于Nana产品测试，也不注册到pytest/config。它们仅使用std依赖/临时目录，输出到public-checkouts根；不读Nana生产Store或任何credential。执行前必须按manifest固定public源，不能把它当运行任意repo脚本的许可。

## 最终回报

TASK = OSS-ARCH-HARVEST-01
NANA_BASE_BRANCH = dev/nana-core-relational-autonomy-v1-codex
NANA_BASE_HEAD = 67326d195edd0693d41eacc63fcc00e1c3205bd6
REPOS_REVIEWED = 14 (15 snapshots)
REPOS_DEEP_READ = 7
SOURCE_FILES_READ = 75 selected source files
TEST_FILES_READ = 19 selected test files
TOP_5_BORROW_PATTERNS = dual cadence; separate interruption gate; adaptive cheap appraisal/cost regulation; interruptible maintenance; four correlated derived observability views
TOP_5_NANA_ALREADY_STRONGER = durable queue/epoch; authority gates; UNKNOWN+Verify; delete closure; sourced identity/growth/counters
TOP_MEMORY_FINDINGS = temporal validity; recall diversity; source-linked synthesis quality
TOP_RUNTIME_FINDINGS = fixedwait/synchronousstep gap; callcount != truecost; maintenance/operatorview gap
TOP_AUTONOMY_FINDINGS = single Subject authority; silence remains valid; timer/request != adopted will
TOP_RELATIONSHIP_FINDINGS = independent appetite already implemented; multidomain sources/counters stronger; interruption/delivery separate
YURIOS_VERDICT = BORROW_PATTERN
GRAPHITI_VERDICT = BORROW_PATTERN temporal semantics
LETTA_VERDICT = BORROW_PATTERN; current Code vs historical archive separated
MEM0_VERDICT = BENCHMARK_ONLY
LANGGRAPH_VERDICT = BORROW_PATTERN / REJECT runtime replacement
TEMPORAL_VERDICT = BORROW_PATTERN concepts / no install
ANIMA_VERDICT = BORROW_PATTERN cadence; REJECT self-model/dream truth/decay authority
TOMO_VERDICT = BORROW_PATTERN operations/inspection
SECOND_ME_VERDICT = BORROW_PATTERN organization; REJECT digital-twin identity substitution
NANA_DUAL_CADENCE = RECOMMENDED_DESIGN_ONLY
NANA_ADAPTIVE_HEARTBEAT = RECOMMENDED_DESIGN_ONLY
NANA_LIVING_JOURNAL = RECOMMENDED_DERIVED_VIEW_ONLY
NANA_TEMPORAL_FACT_VIEW = RECOMMENDED_FUTURE_MEMORY_ADR
NANA_MEMORY_TIERING = RECOMMENDED_PLACEMENT_PATTERN_ONLY
SECOND_STORE_RECOMMENDED = NO
REPLACE_D_RUNTIME = NO
REPLACE_SUBJECT_LOOP = NO
BEST_NEXT_IMPLEMENTATION_MILESTONE = D-V2 Bounded Preemptible Cadence
EXPECTED_BENEFIT = responsive incoming events + fewer idle wake/blocked foreground opportunities, not measured token percentage
EXPECTED_COST = MEDIUM within current queue/lease/loop; no new authority
ARCHITECTURE_RISKS = accidental second reply brain; stale async proposal; catchup/spam storm; false cancellation of effect
LICENSE_RISKS = no code copied; Comma AGPL and all asset/transitive licenses require future review
UNRESOLVED_QUESTIONS = see15; real endpoint behavior/performance and historical time migration unknown
IMPLEMENTATION_AUTHORIZED_BY_THIS_REPORT = NO
PRODUCTION_CHANGED = NO
REAL_MODELS = 0
PRIVATE_DATA_READS = 0
REAL_EXTERNAL_ACTIONS = 0

Research uses public GitHub reads; no new source upload or remote push. Existing development authorization from earlier implementation is not repurposed to push this new research branch. Docs delivered locally; main/R045/base unchanged.
