# Next-stage blockers and minimal implementation proposals

Design authority: VNext-1@45a0e0b. This file proposes changes only; no Approved Core
semantics, schema, dependencies, authority or production endpoint altered this turn.

| ID | Actual blocker / exact code | Minimal later implementation / acceptance |
|---|---|---|
| B01 | `src/nana_core/migration/legacy.py:LegacyRecord.synthetic_only/dataset_id`, `migration/iris.py:IrisRecord`, `memory.py:MemoryView.entries` reject real sources | Add separately reviewed authorized real-capture envelope and source registry/consent scope; do not relabel real records synthetic. Preserve stable source keys, original time, per-record results and retraction. Real importer remains NOT_RUN until firstShadowPASS plus specific data authorization. |
| B02 | `storage/sqlite_store.py:Store.ingest/transaction`, `runtime.py:Runtime.process`, `storage/schema_v1.sql:events_no_update/events_no_delete` replicate private plaintext in immutable logs/artifacts/projections/decisions | Before real plaintext, approve a new schema/protocol for referenced private payloads, dependency-aware withdrawal, purge/backup tombstones, authenticated external restore anchor. Test source/derived/index/context/controlled backup deletion. Current prototype only retrieval suppression, never claims physical erasure. |
| B03 | `storage/schema_v1.sql:one_live_goal`, goals.event_id UNIQUE, plans.goal_id UNIQUE; `runtime.py:ONE_ACTIVE_GOAL_LIMIT` | Phase B schema migration for finite admitted goals, pending promises and immutable plan revisions, keeping one effect owner. Phase A may first add explicit commitment acceptance/renegotiation/completion with evidence; model cannot self-accept or claim fulfilment. No index dropped now. |
| B04 | `memory.py:assess_claims` key includes value; only operator annotation of synthetic statements handled | Add typed subject/predicate/scope claim family, value comparison/valid time/UNKNOWN/withdrawn-support assessment. Prototype proves conservative semantics but does not replace Core memory policy. Preserve old evidence and avoid falling back to obsolete current belief after withdrawal. |
| B05 | `storage/sqlite_store.py:identity`, no identity-growth commit/CAS API; experimental Store UUID not mapped to production identity | Explicit identity continuity/adoption + expected revision SelfChange protocol; charter/permissions remain governance-only. Prototype persists candidate only and never changes identity. Need actual reviewed old-to-Core lineage. |
| B06 | `planning.py:ContextBuilder.build` reading-only/4000chars; Context manifest includes request data; general relation/commitment/token/privacy destination contract absent | Integrate existing strictly typed context manifest with source scope, as_of, withdrawal/cutoff version, complete contradiction bundles and actual model tokenizer budget. Production privacy gate before retrieval/send, not after. New prototype uses character bounds and all-or-nothing bundles only. |
| B07 | `semantic/contracts.py:SemanticReply` contains identity/experience/plan/rationale, no Phase A understanding field | Current readiness encodes strict PhaseAUnderstanding JSON into existing rationale and preserves raw evidence; real-model interoperability untested. Prefer a later explicitly versioned semantic reply field rather than keeping adapter encoding forever. Independent before-compiler and Core-behavior rubrics stay separate. |
| B08 | `integration/authority.py` and `migration/routing.py` owner/memory handoff are simulation-only | Actual writer stop/drain/fence/epoch and backup catch-up are future authorized work. A scope/descriptor or shadow report cannot certify physical single-owner enforcement. No handoff attempted now. |
| B09 | `integration/host_observation.py` / existing R03 result-path does not cover all messages; schema-only metadata does not prove L1/profile runtime extraction | Future scoped native snapshot/export adapter and measured source coverage; L1 volatile losses and missing originals explicitly UNKNOWN. Hash-only may still read private values; needs authorized input scope. No host/bridge operation in this task. |

## What is ready immediately after First Real Shadow PASS

- Run one-command synthetic qualification and inspect explicit N01–N06/N11–N13 matrix.
- Review metadata-only RealCapturePlan with exact source fingerprint/kinds/count/mode.
- Do schema/hash/redact small-memory preparation within a separately authorized scope;
  plaintext remains blocked by B01/B02. Do not remove synthetic gates as a shortcut.
- Use frozen E12 supplement/runner with independently authorized distinct development
  models and quota. This task has no ready model bindings; E12 NOT_RUN.
- Reuse fixtures/tests for later Phase A approved changes; do not replace current
  R045/R045.1 package or trust seal with this tools tree.

READY_TO_CONTINUE_AFTER_FIRST_REAL_SHADOW means engineering prep exists; it does not
mean all Core blockers are solved, real memory ingestion authorized, or E12 passed.
