# Parallel Hardening & First-Life Readiness V1

Base `14e66be0b9562207997d76a68734ddba9ba89235`, original development branch
`dev/nana-core-cloud-first-life-launch-v1-codex`. Work was isolated in
`/workspace/nana-hardening` and disposable dev homes. Final source identity is the
normal commit containing this report, identified by the evidence manifest without
self-referential hashes. This is waiting-period hardening, not a new Foundation
capability or authorization to start First-Life.

## Findings and changes

- **P1 H01 / TYPE B — fixed:** storage monitor could block startup on a FIFO.
  Baseline subprocess exceeded the finite probe and was killed; no staging was
  involved. Storage and privacy loaders now use NOFOLLOW/NONBLOCK, validate the
  opened FD is a regular file and bound the read. Invalid input fails closed;
  no empty default or privacy state reset. No schema or journal-format change.
- **P1 H02 / TYPE B — fixed:** owned IPC limited each receive, allowing a slow
  peer to extend a logical exchange. A single monotonic deadline now covers the
  frame. The deterministic dribble test fails if the deadline renews per byte.
  Original peer PID/UID, inode, ownership, Kernel and independent Verify remain.
- **P2 H03 / TYPE B — fixed:** duplicate JSON keys, missing newline, multiple
  frames and invalid success envelopes are rejected. Completion ambiguity remains
  UNKNOWN, with no retry/fallback. RecursionError containment is defensive: the
  nested-input probe did **not** reproduce a crash in this environment and is not
  presented as a confirmed P1 vulnerability.
- **P2 H04 / TYPE A — implemented/tested:** independent local read-only Inspector.
  It opens the original SQLite database with quoted URI `mode=ro`, query_only and
  a finite query/time budget; it never constructs Store/Runtime or acquires authority.
  Existing relationship, social-appetite and ExperienceNeed projectors are reused
  through read primitives. No second state database/cache, prompt or decision loop.

`src/nana_core/life/inspector.py` supplies a versioned strict DTO and standalone
CLI. Existing record metadata provides activity, dispositions, judgment/WHAT/WHY
codes, concerns, Experience, interests, provenance, execution blockers and provider
attempts. Active goals are joined to their original adopted-goal record. Runtime
owner epoch/state, queue aggregates and ambiguity counts are operational metadata.
Process RSS/threads are read only when process-start/boot identity matches the lease.
Unavailable data is UNKNOWN; limited coverage is never a claim of completeness.

Only PUBLIC/PROJECT source support is visible in V1. Raw purpose/reason, model
proposal, governance configuration, provider secret/endpoint, source prose and
surprise content are omitted. Trust domains are hashed references, not free text.
A visible record is not a recipient delivery grant. Private intent remains design
only; `UNKNOWN_CONTENT_NOT_EXPOSED` does not assert no private thoughts exist.

Read-only tests compare Subject DB and nonempty WAL bytes, event counts, journal,
logs and configuration before/after, with an active writer and after stop. SQLite
readers may update transient SHM read marks or create an empty WAL: these are not
Subject history/authority mutations. Do not claim bit-identical shared-memory files.
Pending privacy intents fail closed without repairing a restored database. Actual
source erasure removes derived activity support on the next projection.

## Recovery, authority and learning

New real SIGKILL tests stop a disposable child after temp fsync/before replace and
after replace: reopening sees a complete old or new guard, never partial JSON or
an unlatched reset. ENOSPC replacement failure preserves old state and removes the
temporary file. This is process-crash testing, not physical power-loss qualification.
Seeded finite JSON roundtrips supplement malformed, incomplete and dribble cases.

Related existing suites verify live quarantined backup, deletion propagation,
transfer/no inherited authority, stale writer fencing, UNKNOWN effect mismatch,
real owned-process SIGKILL, relationship/privacy separation, provider reservation
persistence and isolated exact-digest skills. No P0 bypass was confirmed in this
bounded review; this is not an exhaustive security certification. Learning, C
motivation/judgment semantics, Manager/Grant and self-extension realm are unchanged.

## Preparation artifacts

- `nana_first_life_hardening_v1_runbook.md`: gated dev initialization/health/chat/
  Inspector/stop/restart/backup/transfer/rollback, same-identity checks and emergency
  handling. Prepared only; no real First-Life or review session launched.
- `..._private_intent_contract.md`: selective-disclosure design, disabled by default;
  no private-plan implementation or retained chain-of-thought.
- `..._acceptance.md`: integration checklist, all **NOT_RUN_AS_FIRST_LIFE_REVIEW**.
- `..._regression.md`, `tools/nana_first_life_hardening/regression.py`: explicit FAST
  and FULL selections plus changed-path/domain mappings. FULL names `tests`, not
  the older narrower default testpaths. Live opt-ins remain disabled.
- `tools/nana_first_life_hardening/preflight.py`: read-only current Matrix gate;
  OPEN exits 2, never launches or upgrades a Subject.
- Evidence `failure_matrix.json`: 21 engineering failure cases with expected state,
  retry/UNKNOWN, visibility/effect, rollback and evidence targets. Referenced suites
  do not imply every hardware/network failure was newly injected.

## Boundaries and limitations

Master bytes, fixed 63 criterion definitions/denominators and Matrix statuses are
unchanged. S4-C06 still needs the original frozen 24h final artifact. No new soak,
restart, hot update, injection or configuration changes were made to that run.
Foundation closure/integration readiness remain NO; human naturalness NOT_RUN;
First-Life/Beta NOT_READY. Historical S5 live chain and TianToken UNKNOWN remain
unchanged. No new paid provider, real social, private data, user devices or production.
Schema13 /43 business tables; new tables/dependencies0. No scanner was installed.
`pip check` verifies installed consistency, not a CVE audit.

Inspector V1 is local/controller metadata only; not a general remote frontend,
complete snapshot, private-content API or model context builder. Large/unavailable
projection horizons and concurrent privacy changes fail closed. Physical DB
corruption recovery, remounted readonly filesystem, host power loss and production
restart were not newly exercised. Same-UID arbitrary host compromise is outside
owned-private-socket isolation. Future work must preserve these explicit limits.

## Verification

Exact focused/FAST/related/FULL results and staging read-only observation are in
`nana_first_life_hardening_v1_evidence/qualification.json` and `test_summary.json`.
Only completed commands are PASS; final regression outcomes are filled from actual
JUnit artifacts. Test quantities are evidence, not the completion criterion. Final
completion is one bounded high-value hardening round plus Inspector/runbook/failure
matrix/regression readiness; it does not wait by inventing low-value cleanup.
