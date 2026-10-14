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
