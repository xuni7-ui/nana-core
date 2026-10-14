# Continuous Self C–D development candidate

Authority: VNext-1 `45a0e0b`; implementation base `b3ff62a`. This independent
branch is authorized to extend Core. It is not the approved R045 host package,
not a production migration, and makes no claim about Nana's parallel B5-3 work.

## C1 — identity and explicit schema evolution (IMPLEMENTED / TESTED)

`ContinuityStore` opts into a versioned extension of the original SQLite Store.
It shares the same identity, artifact store, event log, transaction and writer
lock. Ordinary `Store` defaults to schema v1 and rejects higher versions.
SQLite >=3.51.3 is unchanged. No new dependency or second database service.

CanonicalIdentity is a projection of `identities` plus `identity_revisions`.
Bootstrap adopts the existing UUID. Reviewed expression changes use an expected
revision, operator object authority, provenance, supersedes and reason. There is
no model or learning API to change charter or authority. Stable preferences and
self beliefs belong in evidence-backed memory, not the identity prompt.

Development migration v1→v2 accepts empty/identity-only v1 state. A populated v1
contains immutable replicated plaintext, so it fails closed with
`LEGACY_PAYLOAD_MIGRATION_REQUIRED`. It requires a separately audited offline
conversion rather than an unsafe in-place relabel. Rollback means restoring the
pre-upgrade dev snapshot in quarantine, never silently downgrading new history.

Validation: `tests/continuous_self/test_identity.py`: 2 passed; identity revision,
CAS rejection, unauthorized update, restart, replay, another-host backup and
legacy migration rejection. Existing configured suite: 372 passed / 0 failed /
1 skipped (real E12). These are offline results, not real-model semantics.

## C2 — typed memory foundation (IMPLEMENTED / TESTED)

Explicit v3 adds entities, evidence, typed memories, dependency edges and a
rebuildable lexical term index. The seven memory facets are separate from the
epistemic layer (observation / statement / belief / summary / inference / lesson).
Memory has stable entity/scope, source reference and revision, occurrence,
observation and ingestion times, authority/confidence, importance/significance,
privacy, correction and assessment lifecycle. Text exists only in deletable
artifacts; append-only events carry IDs, typed metadata and references.

Only SYNTHETIC_ONLY source DTOs are admitted. RealMemoryIngress is code-level
closed even when every proposed qualification flag is true. Imported history
cannot create Grants, Actions, commitments or identity revisions. A summary must
have source memory backlinks, inherits the most restrictive source privacy, and
cannot be promoted to an original observation. Source-key collisions reject;
source time is never replaced by restart time. Query filters scopes/privacy
before reading payloads. There is no vector DB or new dependency.

Validation to date: 5 continuous-self tests (identity plus all seven facets,
source dedup/replay, correction/conflict, inference authority and real gate).
Correction exists but full descendant invalidation/deletion follows C3/C4;
this intermediate milestone does not claim physical deletion readiness.

## C3/C4 — correction and physical deletion (IMPLEMENTED / TESTED)

Correction requires a live claim in the same entity/predicate/scope family,
direct-source authority and proven non-older occurrence time. It records both
links, supersedes the old assessment and withdraws dependent summaries. Ambiguous
contradiction stays DISPUTED; ordinary retrieval excludes disputed, stale and
withdrawn claims. Confidence changes are separate reviewed transitions. Archive,
suppression and deletion have distinct APIs; only archive/suppression retain text.

`MemoryService.forget` requires its controller-owned operator object. It fsyncs an
opaque-ID deletion intent to a 0600 external privacy journal before the SQLite
transaction. It conservatively deletes the whole source-object dependency
closure, including summaries sharing that source, and clears payload/hash/index.
SQLite secure_delete + a checked WAL TRUNCATE checkpoint remove controlled DB/WAL
copies. Known backups are scrubbed; busy backups produce PENDING_BACKUP_PURGE,
not success. Opening any managed restore re-applies the current journal before
reads. Replay uses remaining artifacts and the deletion changes, then rebuilds
the lexical index. A deleted stable source cannot be reimported under a new
revision. All derivation requires live, current parents.

The journal must be retained independently of older snapshots. A missing anchor
on an existing continuity DB fails closed; managed backup links require the
current external anchor. Arbitrary privileged whole-filesystem rollback,
unregistered exports, model-provider retention, RAM held by an external caller,
and forensic SSD erasure are **not** controlled or certified. This is a synthetic
offline candidate, not permission to ingest real private data. Canonical identity
is not a deletable memory; private self beliefs stay outside the charter.

Validation: 9 cumulative continuous-self tests. Distinct synthetic erasure canary
absent from active DB/WAL, controlled backup and replay; source reimport,
consolidation from deleted input and lifecycle resurrection rejected. Actual
SIGKILL after fsynced intent/before purge recovers to deleted before retrieval.

## C5/C6/C7 — relationships, commitments and project continuity

IMPLEMENTED / TESTED. RelationshipView combines scoped current shared episodes,
preferences, norms, boundaries, unresolved topics, adopted promises and active
projects. It never owns an Identity update API or an affection score.

CommitmentCandidate → PROPOSED is distinct from reviewed ADOPTED → ACTIVE.
Only the controller's operator object adopts/transitions with expected revision.
FULFILLED requires a SYSTEM_VERIFICATION source, never model prose; terminal
states cannot return to ACTIVE. Past deadlines are visible as overdue, not
rewritten or automatically marked complete. No Grant is created by adoption.

ProjectState persists its goal, current state, typed milestones, decisions,
questions, blockers, progress and next actions. CAS revisions allow rebuilding
where we are without chat replay. State, scope, binding and revision are indexed
SQL columns; bounded typed narrative/list payloads live in artifacts so they can
be deleted. `continuity_records`/`record_dependencies` share that discipline for
all revision payloads. SUPPORT and REVISION edges are distinct: a new reviewed
revision need not believe an obsolete source, but erasure still follows history.

Schema v4 adds those four tables. There are no new services or dependencies.
Correction marks stale support for re-review; deleting source memory erases every
related record payload, including historical project revisions. Relationship
views omit stale/deleted support. Validation: 11 cumulative C/D tests, including
adoption rejection, terminal transition, independent fulfillment, overdue,
project CAS, backup/restart continuity and physical deletion of relation/promise/
all project revision payloads. No host or real semantic validation is claimed.

## D1/D2 — SelfFrame and context assembly (IMPLEMENTED / TESTED)

SelfFrame is rebuilt from current identity, relationship, adopted commitments,
projects, self-memory and supplied capability/limitation descriptors. It is not
stored as truth or allowed to write its sources. ContextAssembler applies scope
and destination privacy *before* payload loading, then ranks authority, query
relevance, importance/significance, recency, promises and project relevance.

ContextPackage contains identity/task/constraints, selected source-backed blocks,
coverage, omissions, unresolved conflict bundles, event cutoff/state token,
policy/request hashes and a whole-input budget. Disputed claims are all-or-nothing;
insufficient room produces INSUFFICIENT_CONTRADICTION_CONTEXT, not a one-sided
fact. Missing coverage stays UNKNOWN. A stale/deleted memory invalidates already
issued contexts before any model call; only 64 issued hashes are retained, no
persisted plaintext context cache. Every mandatory block and manifest overhead
counts against the budget. Small budgets block rather than silently drop identity.

Default counting is explicitly UTF8_BYTE_ESTIMATE, a conservative offline
engineering estimate, **not a real provider tokenizer**. Real model integration
must supply its actual framing/token counter. No remote call is made here.
ContinuityStore also sets the existing Shadow fence: ActionKernel grant/budget/
execution remains blocked. This candidate grants no new acting authority.

Validation: 13 cumulative C/D tests; frame reconstruction, provenance, source
coverage/loss validation, token cap, remote privacy exclusion, complete conflict
bundle, tamper/stale-context detection and deletion invalidation.
