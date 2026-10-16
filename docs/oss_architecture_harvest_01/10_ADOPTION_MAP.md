# Adoption map — 没有实施任何采用

每项一个主要CLASS。BORROW_CODE=NONE；ADOPT_NOW不用于暗示已授权施工。完整要求字段在同目录 `adoption_map.json`，这里给人读的索引与逐项影响。

| # | Mechanism | Class | Layer / size / value | Recommendation |
|---|---|---|---|---|
| 1 | Reactive/living cadence | BORROW_PATTERN | D / MEDIUM / FOUNDATIONAL | D-V2 ONE next milestone; same C loop |
| 2 | Adaptive bounded idle wait | BORROW_PATTERN | D / SMALL / HIGH | combine with queue/deadline/lease; no emotion meter |
| 3 | Cheap appraisal before optional model | NANA_ALREADY_STRONGER | D / SMALL / HIGH | retain existing cognition choice and authority boundaries |
| 4 | One committed intention per cycle | NANA_ALREADY_STRONGER | C / SMALL / HIGH | preserve zero-action and multiple candidates |
| 5 | Four correlated observability surfaces | BORROW_PATTERN | UX / MEDIUM / HIGH | later standalone read-only journal milestone |
| 6 | Maintenance work slices | BORROW_PATTERN | D / MEDIUM / HIGH | after cadence milestone; candidate-only writes |
| 7 | Late result source revalidation | BORROW_PATTERN | Memory / MEDIUM / HIGH | return source-versioned candidate to existing writer, not Git memory authority |
| 8 | Act vs interruption worthiness | BORROW_PATTERN | Relationship / MEDIUM / HIGH | no actual sends; relationship is not authority |
| 9 | Background tool sub-budget | FUTURE_STAGE | E / MEDIUM / HIGH | subbudget never exceeds global hard cap |
| 10 | Dispatch kill switch UX | BORROW_PATTERN | Ops / SMALL / HIGH | project current blocker fact without rewriting judgment |
| 11 | Temporary tool fingerprint cooldown | BORROW_PATTERN | E / SMALL / MEDIUM | never substitute for effect receipt or durable dedup |
| 12 | Volatile SignalBus as authority queue | REJECT | D / LARGE / LOW | preserve Nana durable ingress |
| 13 | TemporalFactView | BORROW_PATTERN | Memory / MEDIUM / FOUNDATIONAL | separate Memory ADR; same DB; missing time UNKNOWN |
| 14 | Temporal relationship facts | BORROW_PATTERN | Relationship / MEDIUM / MEDIUM | no scalar affection, no time-only repair |
| 15 | MMR after privacy/conflict filtering | BORROW_PATTERN | Context / SMALL / HIGH | benchmark first; preserve full conflict bundles |
| 16 | Memory temperature map | BORROW_PATTERN | Context / MEDIUM / HIGH | HOT/WARM/COOL/COLD orthogonal to authority/privacy; PROCEDURAL is role |
| 17 | Mem0 synthetic long-life comparison | BENCHMARK_ONLY | Memory / MEDIUM / HIGH | do not install as production Memory backend |
| 18 | Model extraction as authoritative fact | REJECT | Memory / LARGE / LOW | only extraction proposals allowed |
| 19 | Checkpoint durability vocabulary | BORROW_PATTERN | Ops / SMALL / MEDIUM | borrow vocabulary, not graph runtime authority |
| 20 | Replace D with LangGraph | REJECT | D / LARGE / LOW | no replacement; no exactlyonce claim |
| 21 | Workflow vs activity/retry/timer separation | BORROW_PATTERN | Planning / MEDIUM / MEDIUM | unknown effects use Verify, never infinite retry |
| 22 | Deploy Temporal for current Nana | REJECT | D / LARGE / LOW | reconsider only proven distributed workflow need |
| 23 | Mark start / outcome ACK separation | BORROW_PATTERN | Ops / SMALL / HIGH | borrow classification and park UX, not re-enable blind rerun |
| 24 | File memory inspection UX | BORROW_PATTERN | UX / SMALL / MEDIUM | exports derived and erasable, no actual personal examples imported |
| 25 | Silent decay deletion and self-model rewrite | REJECT | Memory / LARGE / LOW | do not import lifecycle or selfrewrite |
| 26 | Hierarchical user profile organization | BORROW_PATTERN | Memory / MEDIUM / MEDIUM | do not equate user profile/model weights with Nana subject |
| 27 | One central subject with thin bodies | FUTURE_STAGE | G / LARGE / HIGH | reject independent local fallback authority |
| 28 | Session generation / passive device discovery | FUTURE_STAGE | G / LARGE / HIGH | pattern only; no AGPL code incorporation |
| 29 | Typed Action/Observation/confirmation surfaces | FUTURE_STAGE | E / LARGE / HIGH | risk labels never Grant; no current real tool execution |
| 30 | Canonical identity and source-backed growth | NANA_ALREADY_STRONGER | C / SMALL / HIGH | retain current Core, borrow review diff UX only |
| 31 | Delete closure vs Git tombstone | NANA_ALREADY_STRONGER | Memory / SMALL / FOUNDATIONAL | explicit erasure remains above history |
| 32 | Manager/Grant/Verify separation | NANA_ALREADY_STRONGER | E / SMALL / FOUNDATIONAL | preserve blocked/unknown provenance |

## M01 — Reactive/living cadence
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/world/turns.py; yurios/mind/loop.py
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: response does not wait for background cadence
- **NANA_CURRENT_STATE**: durable priority queue; synchronous step/fixed wait
- **GAP**: interruptible wait and safe-point arbitration
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: D
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: extend existing wait/dispatch, never second reply brain
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: preempt compute only; epoch/state-stamp revalidation
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: FOUNDATIONAL
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: D-V2 ONE next milestone; same C loop

## M02 — Adaptive bounded idle wait
- **SOURCE_PROJECT**: huodebing-alt/anima
- **SOURCE_FILE**: anima/agent.py:325-330,387-412
- **SOURCE_COMMIT**: ba215ce72bcaedd147d5d08de6e54555a62952c1
- **WHY_IT_WORKS**: quiet ticks back off, new input interrupts wait
- **NANA_CURRENT_STATE**: fixed poll_seconds
- **GAP**: deadline-aware sleep
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: D
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: avoid needless wake IO; no token claim unless model gate also holds
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: combine with queue/deadline/lease; no emotion meter

## M03 — Cheap appraisal before optional model
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/policy.py; yurios/mind/loop.py:563
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: heuristics nominate work before expensive call
- **NANA_CURRENT_STATE**: NO/LIGHT/FULL already present
- **GAP**: improve inspection/cost attribution, not new brain
- **CLASS**: NANA_ALREADY_STRONGER
- **PROPOSED_NANA_LAYER**: D
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: retain existing cognition choice and authority boundaries

## M04 — One committed intention per cycle
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/loop.py:636
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: bounds fanout and gives one explained decision
- **NANA_CURRENT_STATE**: CycleResult contains one intention
- **GAP**: document vs multi-goal distinction
- **CLASS**: NANA_ALREADY_STRONGER
- **PROPOSED_NANA_LAYER**: C
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: preserve zero-action and multiple candidates

## M05 — Four correlated observability surfaces
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/journal.py; trace.py; promptlog.py
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: join activity/reason/tool/context by IDs
- **NANA_CURRENT_STATE**: records/manifests exist; unified view absent
- **GAP**: derived reader with controlled privacy
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: UX
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: default context IDs/hashes, not full prompts; source deletion invalidates exports
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: later standalone read-only journal milestone

## M06 — Maintenance work slices
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/dreamjobs/runner.py; dream.py
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: resumable finished-day jobs with separate research budget
- **NANA_CURRENT_STATE**: reflection/admission/index services exist
- **GAP**: bounded interruptible job protocol
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: D
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: strict per-slice cap, no oversized-first bypass
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: after cadence milestone; candidate-only writes

## M07 — Late result source revalidation
- **SOURCE_PROJECT**: letta-ai/letta-code
- **SOURCE_FILE**: src/agent/subagents/memory-worker.ts; memory-worktree.ts
- **SOURCE_COMMIT**: 1297870b0aa6662d6c70729d273f5073c1bcbdea
- **WHY_IT_WORKS**: isolation and merge preserve concurrent edits
- **NANA_CURRENT_STATE**: CAS/state token already stronger
- **GAP**: background proposal integration ergonomics
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Memory
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: return source-versioned candidate to existing writer, not Git memory authority

## M08 — Act vs interruption worthiness
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/policy.py:184; yurios/mind/acts.py:744
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: valuable work can remain silent
- **NANA_CURRENT_STATE**: social proposals/disclosure exist, no real delivery
- **GAP**: separate explicit interruption interpretation
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Relationship
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: no actual sends; relationship is not authority

## M09 — Background tool sub-budget
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/hands.py:523-667
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: background cannot consume conversation rate buckets
- **NANA_CURRENT_STATE**: global grants/budget harder; no production background tools
- **GAP**: future allocation by resource class
- **CLASS**: FUTURE_STAGE
- **PROPOSED_NANA_LAYER**: E
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: subbudget never exceeds global hard cap

## M10 — Dispatch kill switch UX
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/hands.py:574
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: recheck current switch after proposal
- **NANA_CURRENT_STATE**: Manager/fence/stop exist
- **GAP**: operator visibility
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Ops
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: project current blocker fact without rewriting judgment

## M11 — Temporary tool fingerprint cooldown
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/hands.py:451-618
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: suppresses repeated expensive same request
- **NANA_CURRENT_STATE**: persistent action idempotency and UNKNOWN stronger
- **GAP**: bounded convenience cache only
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: E
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: MEDIUM
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: never substitute for effect receipt or durable dedup

## M12 — Volatile SignalBus as authority queue
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/signals.py:80-189
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: lightweight bounded notifications
- **NANA_CURRENT_STATE**: durable runtime_queue
- **GAP**: would lose restart work
- **CLASS**: REJECT
- **PROPOSED_NANA_LAYER**: D
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: LOW
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: preserve Nana durable ingress

## M13 — TemporalFactView
- **SOURCE_PROJECT**: getzep/graphiti
- **SOURCE_FILE**: graphiti_core/edges.py; utils/maintenance/temporal_edge_utils.py
- **SOURCE_COMMIT**: d50741d1bf463cbe3859eb73914cbff1b66839e6
- **WHY_IT_WORKS**: validity/reference/recording times distinct
- **NANA_CURRENT_STATE**: three clocks and correction chains
- **GAP**: valid interval and as-of knowledge view
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Memory
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: FOUNDATIONAL
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: separate Memory ADR; same DB; missing time UNKNOWN

## M14 — Temporal relationship facts
- **SOURCE_PROJECT**: getzep/graphiti
- **SOURCE_FILE**: graphiti_core/edges.py; utils/maintenance/edge_operations.py
- **SOURCE_COMMIT**: d50741d1bf463cbe3859eb73914cbff1b66839e6
- **WHY_IT_WORKS**: dated scoped edges retain old periods
- **NANA_CURRENT_STATE**: domain trust/target repair already sourced
- **GAP**: explicit validity query if necessary
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Relationship
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: MEDIUM
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: no scalar affection, no time-only repair

## M15 — MMR after privacy/conflict filtering
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/app/memory/store.py:351-443
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: blended relevance with redundancy penalty
- **NANA_CURRENT_STATE**: lexical bounded candidates/priority
- **GAP**: semantic retrieval diversity measurement
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Context
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: benchmark first; preserve full conflict bundles

## M16 — Memory temperature map
- **SOURCE_PROJECT**: letta-ai/letta-code
- **SOURCE_FILE**: src/agent/memory-filesystem.ts; src/agent/subagents/memory-worker.ts
- **SOURCE_COMMIT**: 1297870b0aa6662d6c70729d273f5073c1bcbdea
- **WHY_IT_WORKS**: system vs on-demand context saves prompt space
- **NANA_CURRENT_STATE**: mandatory/priority ContextAssembler
- **GAP**: explicit placement strategy/evaluation
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Context
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: HOT/WARM/COOL/COLD orthogonal to authority/privacy; PROCEDURAL is role

## M17 — Mem0 synthetic long-life comparison
- **SOURCE_PROJECT**: mem0ai/mem0
- **SOURCE_FILE**: mem0/memory/main.py; tests/memory/test_session_scope.py
- **SOURCE_COMMIT**: 0724291bd864cf807e88ee8981c8226644e8fb42
- **WHY_IT_WORKS**: same inputs reveal retrieval/update/delete tradeoffs
- **NANA_CURRENT_STATE**: no matched public baseline benchmark
- **GAP**: freeze independent gold/cost capture
- **CLASS**: BENCHMARK_ONLY
- **PROPOSED_NANA_LAYER**: Memory
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: do not install as production Memory backend

## M18 — Model extraction as authoritative fact
- **SOURCE_PROJECT**: mem0ai/mem0
- **SOURCE_FILE**: mem0/memory/main.py:924-1098
- **SOURCE_COMMIT**: 0724291bd864cf807e88ee8981c8226644e8fb42
- **WHY_IT_WORKS**: convenient batch extraction
- **NANA_CURRENT_STATE**: Evidence/Candidate/Assessment distinction
- **GAP**: would weaken truth boundary
- **CLASS**: REJECT
- **PROPOSED_NANA_LAYER**: Memory
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: LOW
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: only extraction proposals allowed

## M19 — Checkpoint durability vocabulary
- **SOURCE_PROJECT**: langchain-ai/langgraph
- **SOURCE_FILE**: libs/langgraph/langgraph/pregel/_loop.py
- **SOURCE_COMMIT**: 4e2dfe4a247abfc0d001f3ef8242cbbbba400d2c
- **WHY_IT_WORKS**: explicit sync/async/exit boundaries
- **NANA_CURRENT_STATE**: SQLite transactional commit/recovery already exists
- **GAP**: clear operator persistence contract
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Ops
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: MEDIUM
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: borrow vocabulary, not graph runtime authority

## M20 — Replace D with LangGraph
- **SOURCE_PROJECT**: langchain-ai/langgraph
- **SOURCE_FILE**: libs/langgraph/langgraph/pregel/main.py
- **SOURCE_COMMIT**: 4e2dfe4a247abfc0d001f3ef8242cbbbba400d2c
- **WHY_IT_WORKS**: durable graph task infrastructure
- **NANA_CURRENT_STATE**: already single D queue/C loop
- **GAP**: duplicate state/thread authority
- **CLASS**: REJECT
- **PROPOSED_NANA_LAYER**: D
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: LOW
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: no replacement; no exactlyonce claim

## M21 — Workflow vs activity/retry/timer separation
- **SOURCE_PROJECT**: temporalio/sdk-python
- **SOURCE_FILE**: temporalio/workflow/_activities.py; common.py; _workflow_ops.py
- **SOURCE_COMMIT**: 346d4dcd0863657c3a33283c952a296762059339
- **WHY_IT_WORKS**: deterministic control and retried work distinct
- **NANA_CURRENT_STATE**: C/D/E separation exists
- **GAP**: future long history archive semantics
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Planning
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: MEDIUM
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: unknown effects use Verify, never infinite retry

## M22 — Deploy Temporal for current Nana
- **SOURCE_PROJECT**: temporalio/sdk-python
- **SOURCE_FILE**: README.md; temporalio/worker
- **SOURCE_COMMIT**: 346d4dcd0863657c3a33283c952a296762059339
- **WHY_IT_WORKS**: durable distributed service ecosystem
- **NANA_CURRENT_STATE**: single local Store 4GB target
- **GAP**: adds unnecessary operational services
- **CLASS**: REJECT
- **PROPOSED_NANA_LAYER**: D
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: LOW
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: reconsider only proven distributed workflow need

## M23 — Mark start / outcome ACK separation
- **SOURCE_PROJECT**: shuaiyuan17/tomo
- **SOURCE_FILE**: src/cron/scheduler.ts:145-223
- **SOURCE_COMMIT**: a6ee1bec12bee2d59cd5015bf86208710aaf6915
- **WHY_IT_WORKS**: ACK failure is not execution failure
- **NANA_CURRENT_STATE**: reserved calls/UNKNOWN already protect
- **GAP**: operator incident labels
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Ops
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: borrow classification and park UX, not re-enable blind rerun

## M24 — File memory inspection UX
- **SOURCE_PROJECT**: shuaiyuan17/tomo
- **SOURCE_FILE**: src/people.ts; defaults/skills/lcm/DAILY.md
- **SOURCE_COMMIT**: a6ee1bec12bee2d59cd5015bf86208710aaf6915
- **WHY_IT_WORKS**: human can inspect audience/scoped memories
- **NANA_CURRENT_STATE**: typed records less convenient to read
- **GAP**: filtered read-only export
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: UX
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: MEDIUM
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: exports derived and erasable, no actual personal examples imported

## M25 — Silent decay deletion and self-model rewrite
- **SOURCE_PROJECT**: huodebing-alt/anima
- **SOURCE_FILE**: anima/store.py:247-299; anima/sleep.py:245
- **SOURCE_COMMIT**: ba215ce72bcaedd147d5d08de6e54555a62952c1
- **WHY_IT_WORKS**: simple growth/forgetting demo
- **NANA_CURRENT_STATE**: explicit privacy/admission/identity protection
- **GAP**: weakens source authority
- **CLASS**: REJECT
- **PROPOSED_NANA_LAYER**: Memory
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: LOW
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: do not import lifecycle or selfrewrite

## M26 — Hierarchical user profile organization
- **SOURCE_PROJECT**: mindverse/Second-Me
- **SOURCE_FILE**: lpm_kernel/L0/l0_generator.py; L1/l1_generator.py
- **SOURCE_COMMIT**: d0e40251d9de61b3340b8d0d7d83150669f1885a
- **WHY_IT_WORKS**: raw→abstractions grouped by topic
- **NANA_CURRENT_STATE**: typed self/relationship memory exists
- **GAP**: readability and cross-level source navigation
- **CLASS**: BORROW_PATTERN
- **PROPOSED_NANA_LAYER**: Memory
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: MEDIUM
- **EXPECTED_VALUE**: MEDIUM
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: do not equate user profile/model weights with Nana subject

## M27 — One central subject with thin bodies
- **SOURCE_PROJECT**: max286674-cpu/OpenWatari-Jarvis
- **SOURCE_FILE**: src/jarvis/edge/remote_brain.py; shared/protocol.py
- **SOURCE_COMMIT**: b6a1924bc35daaf9520ac6e9fc8ee8c7ef7b4c10
- **WHY_IT_WORKS**: central state with device-specific transport
- **NANA_CURRENT_STATE**: ports/synthetic perception only
- **GAP**: future device/session protocol
- **CLASS**: FUTURE_STAGE
- **PROPOSED_NANA_LAYER**: G
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: reject independent local fallback authority

## M28 — Session generation / passive device discovery
- **SOURCE_PROJECT**: AFK-surf/Comma
- **SOURCE_FILE**: systems/connector/salix-connect/connection_session.go; device_access.go
- **SOURCE_COMMIT**: ba4f55db1bf038a9246a9f71a7b5059cd91853f1
- **WHY_IT_WORKS**: transport-local reply state cannot cross reconnect
- **NANA_CURRENT_STATE**: local UDS/session fence already exists
- **GAP**: future network device bridge
- **CLASS**: FUTURE_STAGE
- **PROPOSED_NANA_LAYER**: G
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: AGPL-3.0-only; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: pattern only; no AGPL code incorporation

## M29 — Typed Action/Observation/confirmation surfaces
- **SOURCE_PROJECT**: OpenHands/software-agent-sdk
- **SOURCE_FILE**: openhands-sdk/openhands/sdk/event/llm_convertible/action.py; security/confirmation_policy.py
- **SOURCE_COMMIT**: 12e967664c2353f4cb85dd27da04ade035ff078c
- **WHY_IT_WORKS**: typed audit and explicit confirmation alternatives
- **NANA_CURRENT_STATE**: ActionKernel already harder authority
- **GAP**: future sandbox adapter/receipt UX
- **CLASS**: FUTURE_STAGE
- **PROPOSED_NANA_LAYER**: E
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: LARGE
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: MIT; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: risk labels never Grant; no current real tool execution

## M30 — Canonical identity and source-backed growth
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/selfedit.py
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: gated soul editing useful UI idea
- **NANA_CURRENT_STATE**: Nana immutable canonical/revisions/independent counters
- **GAP**: no replacement needed
- **CLASS**: NANA_ALREADY_STRONGER
- **PROPOSED_NANA_LAYER**: C
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: HIGH
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: retain current Core, borrow review diff UX only

## M31 — Delete closure vs Git tombstone
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/app/memory/store.py:473-512
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: inspectable audit but keeps old content
- **NANA_CURRENT_STATE**: Nana PrivacyJournal/delete propagation stronger
- **GAP**: do not regress
- **CLASS**: NANA_ALREADY_STRONGER
- **PROPOSED_NANA_LAYER**: Memory
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: FOUNDATIONAL
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: explicit erasure remains above history

## M32 — Manager/Grant/Verify separation
- **SOURCE_PROJECT**: yuri-os/YuriOS
- **SOURCE_FILE**: yurios/mind/hands.py; yurios/world/brain.py
- **SOURCE_COMMIT**: cd4d1f16ae095f0f694dbbe7b1aac8e33db25367
- **WHY_IT_WORKS**: guard/caps protect coarse tool usage
- **NANA_CURRENT_STATE**: Nana stronger typed realization boundary
- **GAP**: no permissive adoption
- **CLASS**: NANA_ALREADY_STRONGER
- **PROPOSED_NANA_LAYER**: E
- **AUTHORITY_IMPACT**: NONE; existing Subject/Manager/Grant gates remain
- **STORE_IMPACT**: same Store; derived view or existing lifecycle, no second authority
- **RUNTIME_IMPACT**: single Runtime and SubjectLoop unchanged
- **PRIVACY_IMPACT**: existing source/scope/destination/erasure filters remain hard
- **CRASH_IMPACT**: existing epoch/CAS/idempotency/UNKNOWN checks required
- **TOKEN_IMPACT**: no measured savings; bounded candidate computation only
- **IMPLEMENTATION_SIZE**: SMALL
- **EXPECTED_VALUE**: FOUNDATIONAL
- **DEPENDENCIES**: separate authorized implementation and targeted validation
- **LICENSE_NOTES**: Apache-2.0; pattern rewrite only, BORROW_CODE=NONE
- **RECOMMENDATION**: preserve blocked/unknown provenance
