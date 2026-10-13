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
