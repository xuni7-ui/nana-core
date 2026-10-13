# Nana Next-Stage Parallel Readiness

Base: VNext-1 design commit45a0e0b71f11b81f914141cfa139fc10ba6add9d (R045 source inherited).
Branch: dev/nana-core-next-stage-readiness-codex. Development fixture qualification only.

## Memory / Phase A checkpoint

`tools/nana_next_stage/` implements strict synthetic capture and metadata-only future
RealCapturePlan contracts. The latter cannot import/read real data. Original Store,
IrisAdapter, events/core_meta/memory_items are reused; no Core edits/tables/dependencies.

Implemented: exact scope/provenance, independent original/observed/import times,
per-record rejection, import idempotency/resume; typed claim family correction with
valid time and preserved opposing evidence; relationship view, OFFERED commitment,
SelfChange CANDIDATE, identity-stable SelfFrame, bounded all-or-nothing context with
coverage and stale/withdrawn support checks. None creates a Goal/Action/Grant/Strategy.

Withdrawal suppresses source lineage (including later revisions) and dependent views.
Fixture checkpoint reapplies suppression to an old quarantined backup. Original
append-only artifacts remain. **This is NOT physical privacy deletion and does not
provide an authenticated production revocation anchor.** N11 remains PARTIAL.
Commitment acceptance/fulfilment and identity growth are deliberately not implemented;
those architectural operations require the later Phase A Core contract review.

Evidence: memory_initial.xml43pass; memory_boundary_initial.xml7fail/31pass/14errors:
model-before validation converted JSON arrays into strict Python tuple boundaries.
Corrected with field validators plus exact synthetic-bool subclass; memory.xml52pass.
No old assertions removed or weakened. All inputs synthetic, no real endpoints/host.

## E12 / Phase A supplement

`tools/nana_next_stage/semantic.py` reuses original prepare_snapshot, execute_case,
CompatibleModelPort, HTTPTransport, CallLedger, PlanCompiler and independent behavior
rubric. No second model ledger or Core identity is created for a snapshot. Source-backed
synthetic Iris records and typed relationship/OFFERED promise/dated preference/coverage
are frozen in the same S5 Store; grants/budgets/actions/strategies stay byte-equivalent.
Heldout case answers are absent from supplement. Provider response, raw proposal,
compiled behavior and extra understanding checks remain distinct.

To avoid changing approved SemanticReply, the supplemental understanding JSON is
encoded as its existing bounded rationale string. This adapter convention is tested
with transport fixtures, not demonstrated with real models. A real model may fail
that contract; failure must not be hidden by compiler compensation. No extra calls.
Existing E12 gate is still required, with the additional Phase A checks conjoined.

Two fixture ModelPorts run sequentially across with/without arms of all4 cases. They
exercise native Core actions only against FakeWorld and always report transport_fixture;
no real model/network/production service. Simulator configs are refused by the real
entry; no config -> zero attempts and NOT_RUN. Future explicit authorized development
config can execute the same runner sequentially, retaining original budget/UNKNOWN
no-retry behavior. This task does not run that path with a real endpoint.

## Commands (from repository root, approved compatible Python)

```bash
PYTHONPATH=src .venv/bin/python -m tools.nana_next_stage qualify --output /tmp/nana-next-stage-fresh
PYTHONPATH=src .venv/bin/python -m tools.nana_next_stage e12 --output /tmp/nana-e12-fresh
PYTHONPATH=src .venv/bin/python -m tools.nana_next_stage plan-template --output /tmp/nana-real-plan.json
```

Outputs must not exist. First command runs synthetic Memory/Self/restore qualification
and creates a prepared E12 snapshot/report. Second currently records NOT_RUN without
network. Third writes metadata-only review input with reader_enabled=false; it cannot
read a host database. Later, under model execution authorization only, one command:

```bash
PYTHONPATH=src .venv/bin/python -m tools.nana_next_stage e12 --output /tmp/nana-e12-authorized-fresh --config /path/to/nonsecret-development-model-config.json
```

Config uses original RunConfig (max2 endpoints, development+existing_quota or real local
model; dedicated NANA_S5_DEV_* binding names only). No key values belong in JSON/Git.
Different aliases alone do not prove distinct models. Existing aggregate requires
actual provider metadata and successful complete cells. Fees UNKNOWN if not billed.
Before real execution operator must review available call/token/cost budget and
endpoint authorization; fixture success is not that authorization. No fresh receipt,
bridge, plugin/Dashboard interaction, host store or production trust introduced.

## Qualification honesty

N01/N02/N03/N12 have runnable offline engineering contracts. N04/N05/N06/N11/N13 are
PARTIAL because growth, entity binding, accepted commitment/Goal linkage, true purge
and token/semantic quality remain architectural work. Every real gate is
NOT_RUN_REAL_DEPENDENCY, including Small Real Memory Shadow and E12.

Three new-prototype failures were preserved and fixed: withdrawal could fall back to
an obsolete current belief; historical SelfFrame could include future-supported
candidates; a recomputed self-declared payload hash could pass context verification.
Fixes retain historical truth, filter support by as_of and reconstruct context from
Store instead of trusting caller hashes. The previous new-test assertion about old
belief now checks its historical date plus current uncertainty, strengthening temporal
correctness. No inherited test was edited/deleted. Initial failing XML is retained.

## Final actual development validation

83 new tests passed. Full configured Core S0–S6/development/phase3/integration suite
plus readiness: **455 passed / 0 failed / 0 errors / 1 skipped**,17.59seconds on actual
CPython3.12.14 / nativeSQLite3.53.1 / Pydantic2.13.4. The only skip is E12. No private
runtime injected into any host; this is a compatible development interpreter.
R04/R041 host-bridge test suite was not run this turn because receipt/bridge operations
are out of this task's scope; its code and all old tests are untouched. Do not compare
455 with R045's broader762 as if tests had been deleted.

Actual fresh CLI runs: qualify produced6imported/6duplicate, complete source/time
context, restart/backup/replay/checkpoint suppression and zero execution objects in
the memory prototype. e12 without config produced0calls/NOT_RUN. Same frozen-state
fixture cells exercise2ports×4cases×2arms=16cells, raw semantic vs Core behavior separate.
Actual source/model identity from real inference remains untested.

Qualification matrix: docs/nana_next_stage_evidence/qualification_matrix.json; every
real gate NOT_RUN_REAL_DEPENDENCY. Offline CLI evidence: offline_qualification.json;
real E12 absence: e12_not_run.json. Core blockers and minimal proposals:
docs/nana_next_stage_implementation_proposals.md. No production/real-memory/secret/
real-model/receipt/bridge operations; Approved Core semantics/schema/dependencies0diff.

Final coverage hardening: FULL_FOR_DECLARED_SCOPE plus drop/disconnection now rejects.
Two failing cases preserved in coverage_initial.xml;83 targeted pass and455+1E12skip
full configured regression after the fix. This is the fourth corrected prototype
semantic boundary; no Approved Core/R045 change.
