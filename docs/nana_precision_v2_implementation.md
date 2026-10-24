# Precision V2 — implementation and qualification

Advanced Growth S2/S4/S5/S6/S7/S8/S9 and three axes, GLOBAL_STAGE H.
Base d695ed7d47a33cb3df62a144908df30b7d7c693d on the existing development branch.
Master and the fixed63 Foundation definitions are unchanged. Historical controlled
world residency stays PARTIAL_EXTERNAL_LIMIT, never reinterpreted as completed.

## P0 — frozen representative baseline, before runtime changes

`tools/nana_precision/benchmark.py` defines independent transition replay; the
planner subprocess receives only typed public operators/goals, not evaluator
answers. Twenty-four development cases vary chain widths/depths/costs/order,
alternative paths, irrelevant work, producer-specific dataflow, destructive
branches and impossible goals. Seed24102026. Evaluator and generator are frozen
in this commit before candidate changes. Final unseen seeds will be drawn only
after candidate freeze; no tuning on final instances or answers.

Baseline: `nana_precision_v2_evidence/baseline.json`:9/20 feasible completions,
13/24 correct including impossible cases,4 invalid proposals,0 accepted false
success,0 duplicate operators. Invalid proposals are wasted planning, not
successful Actions or falsely verified world effects. This is symbolic
ARCHITECTURE_PRECISION, not semantic intelligence. MODEL_ABLATION_NOT_RUN.

## Gap map and selected change

1. Uniform-cost enumeration expands independent step orders before reaching a
   multi-branch goal; its1024-expansion bound rejects feasible tasks.
2. Planner state tracks facts only, though validator also requires exact producer
   history and forbids repeated operator IDs. Cheap unrelated producers hide
   necessary dataflow paths.
3. Flat32-operator/step/cursor bounds prevent bounded larger decompositions.
4. Existing replan deliberately discards prior outputs and fences UNKNOWN effects.
   Reusing writes from symbolic facts alone would be unsafe; retain fresh-source/C
   review and do not introduce speculative write reuse.

Chosen: evolve the existing BoundedPlanner with causal relevance, explicit
producer history and finite heuristic search; add typed bounded hierarchical
groups using the original Goal/Plan/one-step C execution. Independent validation
and Manager/Grant/Budget/Verify remain. Satisficing search, not global cost-optimality.
No alternate will/planner/store/daemon. No schema change needed for typed plan data.

Pending: implementation, targeted/development comparison, candidate freeze,
unseen heldout comparison, original-runtime integrated lifecycle, compatibility,
recovery, portable install, full regression and layer-qualified final report.
