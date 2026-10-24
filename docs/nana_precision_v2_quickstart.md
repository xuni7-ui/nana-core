# Precision V2 — development entry points

Owned/dev only. No real model, private history, user-device, social or production
authorization follows from these commands. Start in a clean dev checkout with
the existing offline `.venv`; no credential or new dependency is required.

## Reproduce the comparison

```sh
git worktree add --detach /workspace/nana-staging/precision-baseline-d695ed7 d695ed7d47a33cb3df62a144908df30b7d7c693d
.venv/bin/python -m tools.nana_precision.benchmark --source /workspace/nana-staging/precision-baseline-d695ed7 --seed 24102026 --out /workspace/nana-staging/before.json
.venv/bin/python -m tools.nana_precision.benchmark --source /workspace/nana-core --seed 24102026 --out /workspace/nana-staging/after.json
.venv/bin/python -m pytest tests/precision -q
```

If the baseline worktree already exists, verify its HEAD and use it; do not
overwrite it. Recorded heldout seed3213777597 is now public regression material,
not a fresh hidden test. New optimization requires a new frozen candidate and a
new final seed. `heldout.py` adds independently solved random transition graphs.
`scenarios.py` runs twenty representative original Core/owned/fixture categories.
It explicitly does not qualify semantic comprehension or real mobile operation.

## Application configuration

Existing LifeConfig has `controlled_projects`. Set `learn_methods: true` on a
project to keep original imperfect primitive methods and allow original G's
per-operator lessons to change later plans. Default false preserves reviewed
method behavior. Example descriptor (task IDs must exist in the owned profile):

```json
{
  "project_id": "adaptive",
  "trigger_entity": "project-user",
  "trigger_predicate": "lab.project-status",
  "task_ids": ["document-transfer", "archive-notes", "form-transfer"],
  "learn_methods": true
}
```

LifeApplication's existing `advanced_life` opt-in and source binding are required.
No source descriptor is a command or Grant. `tests/precision/test_lifecycle.py`
provides a reproducible full configuration, actual five-process owned world and
independent file/IPC outcome checks. It uses the original foreground app/Runtime.

Programmatic Objective supports optional `task_groups` (32 groups/depth8) over
up to128 existing operators. Groups contain operator IDs or other group IDs;
`depends_on` requires the referenced group to finish first. Primitive operators
may offer alternative ways to produce the same fact. Only current C adoption
can create the original Goal/Plan. Every remaining step still gets original C.

Optional Operator.input_guard contains `observation_operator_id`, `max_age_us`,
and `expected_revision` (SHA256 of verified observation data). A stale observation
parks the step before new dispatch. This is a bounded observation contract, not
an atomic compare-and-swap of arbitrary external resources. Existing owned port
revision/DOM/ownership checks remain the dispatch fence.

LearningSpec can opt into `hypothesis_policy: PRACTICE_COMPARE`; otherwise the
existing proposer/meta-learning choice remains. Practice comparison can select
only a declared method, has no transfer/evaluator handles, and creates no Lesson
until the original independent stages and activation gates succeed.

## Inspect, recover, migrate

Use the existing `nana life`/board/health projections and original Store records.
`AUTONOMOUS_PLAN.payload.checkpoint` reports reused operator IDs, memory IDs and
fresh independent verification records. `action.reobserved` changes no old Action
outcome. `open.goal_replanned` has a durable exact source key; replay does not
repeat the committed revision. `open.plan_review_deferred` parks changed current
effects without rewriting C's endorsement or crashing the owner.

`tests/precision/test_recovery.py` exercises actual SIGKILL before/after plan commit,
independent effect change and original-C deferred review. UNKNOWN actions must be
verified with the original Kernel; no replan/checkpoint can redispatch them.

Schema remains13/43 business tables, no migration/new dependency. New optional
typed payload fields live in existing erasable records/artifacts and privacy
dependencies. Official B8/portable quarantine and fresh-host binding apply.
An old binary may reject new fields or a cursor>32: that is intentional fail-closed
compatibility, not permission to silently downgrade an active plan. Rollback uses
the official quarantined backup/lineage workflow, never a live stale Store copy.

## Portable verification

Build with `tools.nana_portable_cloud.build` at the final runtime pin and existing
local wheelhouse, verify its SHA256, then run `tools.nana_portable_cloud.rehearse`.
`tools/nana_precision/installed_probe.py` runs under installed Python `-I` with
only the explicit bundle/src inserted; it verifies actual learned multi-Hand
checkpoint repair, independent file moves and same-identity restart. It is an
external qualification driver, not shipped runtime or a second brain.

No deployment, provider call, automation or user-surface cutover is implied.
