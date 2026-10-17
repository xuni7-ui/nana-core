# E1–E6 Open Autonomy V1 — implementation ledger

Base: 30f7e6f5e0b6e935f7d27a2847a5107d261c4ef5 (available local D2–D7,
not a remote claim). Branch: dev/nana-core-e1e6-open-autonomy-self-extension-v1-codex.
Local commits only; no push/production/main/R045 operation.

## Bounded source map / construction sequence

- Reuse C source-backed appraisal/motivation/judgment, dispositions, relationship,
  Primary Anchor, independent social appetite, Context/Record/Privacy services.
- Extend existing goals/plans/jobs at explicit development12: remove one_live_goal
  index only here; bounded active goals, dependencies, priority/deadline, suspend/
  resume and versioned bounded operator planning. Keep C7/D8 defaults and11 tests.
- Reuse LivingWork opportunity/after_cycle and existing governed ActionKernel;
  extend exact sealed synthetic port with a finite typed cross-domain catalogue.
  No other decision loop or arbitrary capability callback in the offline realm.
- Add recipient admission distinct from social desire and no real social delivery.
- Persist learning stages/checks with independent baseline/held-out/transfer results
  in existing erasable records/jobs. Strategies remain supported proposals until
  tested/reviewed. Maintenance failure must not advance its cursor.
- Generated code uses isolated subprocess tests, not Python-private-object sandboxing.
  bwrap namespace/filesystem/network isolation probe succeeded on this dev machine.
  Static checks, bounded inputs/output/time, source/version hashes, review/rollback
  are separate; absence of sandbox blocks generated execution/activation.
- Extend existing B9 media ports, B10 projections and B8 controlled transfer with
  new history, never lease/provider instances/old Grants.
- Qualify with integrated story plus a different domain/motive; focused safety and
  recovery tests, then one final full regression. Real endpoints remain NOT_RUN.

No external source implementation copied. New generic mechanisms have no named
person/subject-specific behavior. Final results and honest limits follow below.

## Qualified implementation (OFFLINE / SYNTHETIC)

Business source: `ac0d934cfc116c55f75a597653579fba7ffdca8a`.
The final containing documentation commit records results/fingerprints without
changing business behavior. `git log 30f7e6f..HEAD` gives the local commit range.

| Stage | State | Source / working behavior |
|---|---|---|
| E1 | IMPLEMENTED / TESTED | continuity/open_agency/{contracts,planning,service}.py: multiple persistent goals, parent/dependency links, priority/deadline and bounded aging, pause/resume/abandon, finite cost search and validated dataflow, revised plans, one C-approved step at a time |
| E2 | IMPLEMENTED / TESTED, synthetic delivery | delivery.py + existing C policy: social desire survives BUSY; recipient/privacy/quiet-window/expiry/intent/payload admission is separate from Manager/Grant. Exact local contact fixture verifies NO_RESPONSE; no real social sender |
| E3 | IMPLEMENTED / TESTED | learning.py + existing ExperienceService/lessons: nine recoverable stages, executed baseline/practice/held-out/transfer, independent checks, reviewed method selection, monitoring/suspension and same-goal C reconsideration |
| E4 | IMPLEMENTED / TESTED, isolated local realm | code_skills.py / skill_runner.py: generated Python, failed test, repaired version, isolated CPython tests, review/hash/package, Kernel-routed local use, retire-to-disabled rollback. No arbitrary plugin install or production code execution |
| E5 | IMPLEMENTED / TESTED, fixture ports | replaceable PlannerPort/LearningProposerPort/evaluator/CodeProposerPort, sealed finite world capability catalogue, existing B9 MediaSession/ProviderRegistry, B6 Surface and B10 application. No SDK/real endpoint |
| E6 | IMPLEMENTED / TESTED | original Runtime/lease/queue/jobs, exact Action identity, C-approved revisions, resource budgets, B8 replay/transfer and typed source-filtered frontend/journal/L0/L1/L2 projections |

### Subject and planning lifecycle

D still supplies WHEN through `LivingWork.opportunity/after_cycle/maintenance_slice`.
C is still the only place committing appraisal, judgment and intention. There is
no new planning/social/learning agent loop, Runtime, Store or background database.

`runtime.work.configure_open_agency(OpenGoalPolicy(objectives), exactOfflinePort)`
and `configure_open_learning(specs)` are trusted application construction. Neither
policy carries a Grant. Catalogue registration, Subject endorsement, application
adoption, delivery eligibility, negative Manager and Kernel authority remain
separate. Frontends receive projections/proposals, never these controller handles.

A reviewed Objective describes symbolic conditions and typed operators. Uniform
cost search expands at most1024 states/32 operators/32 steps. Candidates can name
only supplied operators; schema/argument bounds, source/problem revision, ordered
preconditions and explicit earlier output bindings are checked. No `grant`/code/
arbitrary RPC in a planner candidate. `world_revision` identifies the frozen
planning problem (including supplied facts), not an omniscient world snapshot.
Fresh externally sourced observations can offer a C `GoalReviewRef`; C may defer,
or endorse a new plan. Every revised step observes/uses its own plan's verified
outputs, never accidental results from an earlier revision. These remain bounded
symbolic plans, not unconstrained natural-language planning or a complete world model.

Up to16 live goals per policy (default8), single writer and one cycle intention
continue. Parent/dependency links inherit source erasure. Priority/soft deadline,
last service and60-second bounded aging select *opportunities*; C can still rest
or decline. Dependencies wait for completion; suspension/resumption is versioned
and independently sourced. Completed concerns are deduplicated by objective/source;
new time ticks do not re-adopt the same finished problem. A resource/policy change
requires fresh sourced reconsideration; revocation never executes an old will.

### Learning and generated code

OBSERVE → VALUE → HYPOTHESIZE → BASELINE → PRACTICE → EVALUATE → TRANSFER →
CONSOLIDATE → MONITOR uses existing jobs and erasable records. Cursor advances only
after valid results commit. A timeout/malformed trial parks UNKNOWN without empty
success or background retry; explicit controller/source recovery can resume the
same stage. Process death simply reopens the last durable pure trial stage.

Practice/evaluation/transfer have disjoint case IDs/inputs, with transfer in a new
context. Actual candidate computation is compared with independent expected results.
Only improved held-out plus successful transfer can create a checked MethodStrategyRule
through the existing Lesson lifecycle. No identity/value/Manager/Grant changes.
A suspended lesson cannot silently remain usable by an already-compiled plan.
Repeated reflection of the same problem does not recursively create new training.

Actual examples: numeric precision failure (`NAIVE_SUM` truncates fractions) learns
`NUMERIC_SUM`; content-driven language interest learns Unicode normalization/token
handling. Both measured baseline0/1 versus held-out1/1 and transfer1/1. A later goal
actually uses the reviewed method; this is not semantic-quality proof for general
language or real video. Proposers/models are replaceable candidates, not truth.

CodeSpec is an open task descriptor over the bounded pure JSON transform contract.
The reference fixture proposer generates text, then changes it after an executed
failure diagnostic. Static checking is additional hygiene, not the sandbox.
`bwrap --unshare-all` provides separate process/user/network namespaces, read-only
system runtime, fresh tmpfs and no host workspace/home/Store/socket/credentials mounts.
The child has CPU1sec, address-space192MiB, bounded FDs/processes/files, parent timeout3sec,
input/output8KiB and closed pure builtins/AST. It receives only one JSON input and
code; no Store, Manager, Grant or Core import. Core runs Python3.12.14; this host's
isolated system Python is3.13.5, proving no private Core/SQLite dependency is needed
in the code worker. Missing/failing isolation blocks execution/activation.

Review is bound to current-object actual test results and exact source digest.
Enabled realm handles are ephemeral, not serialized authority. Re-instantiating a
service, restoring or moving an ACTIVE history record cannot automatically execute
it; current-realm testing/review is required. Actual local `world.skill` use still
passes the same governed Kernel/Grant/Budget/Verify route. Retirement disables it;
rollback here means return to no active version, not automatic re-enabling of an old
version. Generated candidate package is source + manifest, not an install script.
It is an explicitly exported copy; detached candidate copies/old archives require
operator retention/erasure handling, outside managed-Store deletion guarantees.

### Privacy, temporal meaning and source closure

Data privacy stays separate from social expectation, desire and authority. Seeded
synthetic resource classification cannot be downgraded by a PUBLIC goal. SECRET
content is rejected before Core capture. Input privacy and source dependencies flow
through args/receipt/result and downstream observations. V12 Kernel payload resolution
also rejects suppressed/corrected/non-current supporting memory. This does not rewrite
historical effect state; UNKNOWN still needs Verify, never a blind second execution.

Existing PrivacyJournal/record_dependencies cover learning, code, plans, Journal
and views. Erasing feed support removes its derived interest/lesson/view. Independent
Manager roots remain. Metadata-derived interests are INFERENCE/MODEL_DERIVATION with
backlinks; content credibility labels are not truth. Existing temporal memory separates
event/observed/ingested/reference/valid time; interpretation never backdates an event.

### Development schema and recovery

Explicit `schema_target=12`: remove `one_live_goal` only here; extend existing goals
with priority/deadline/parent/dependency/service fields and SUSPENDED; existing records
add five used kinds. Still39 business tables, no dependency added. Default C7/D8 and
explicit legacy11 do not acquire open-goal semantics. Forward migration is explicit;
rollback uses a prior isolated snapshot in quarantine, never a lossy downgrade or
production upgrade.

Actual tests preserve identity/history across7/8/11→12, old11 goal/Action official
replay, FK integrity and managed12 SubjectPackage transfer. Multi-goal and partial
learning history survive, old Grants are revoked, epoch advances, transient owners
are removed. No world port/provider/sandbox-review/agency authority is reconstructed.
Trusted single-destination/raw whole-database clone limits of B8 remain.

Two actual SIGKILL cuts: (1) durable fixture effect before receipt, then one original
Action verified with one EXECUTE/effect; (2) Lesson ACTIVE before learning cursor,
then resume with one Lesson/Experience and no duplicated consolidation. Existing
D2–D7 preemption/recovery/resource and C/Affective/Relational/Kernel regression remain.

### Reproduce

```sh
PYTHONPATH=src .venv/bin/python -m nana_core.presence.open_demo
PYTHONPATH=src .venv/bin/python -m nana_core.presence.open_demo --contrast
.venv/bin/python -m pytest -q tests/open_autonomy
```

Default demos create/remove private temporary synthetic Stores. `--directory` keeps
a fresh development fixture plus code candidate for inspection, refusing an existing
Store; `--output` writes report JSON. Do not point them at production data.

Main story: three persistent goals, ten actual verified local fixture actions, two
learning domains, busy contact deferral, rest, Primary/voluntary choice, foreground
preemption/resume, Manager veto and fresh C review, generated code fail/repair/use/
retire, two surfaces, deletion and restart. Contrast: different motive/history/task
with plans2/4 steps, six actual verified actions and no user input. Reports contain
actual calls/results; data and model proposers are explicitly synthetic fixtures.

Evidence lives in `docs/nana_e1e6_open_autonomy_v1_evidence/`. The generated source's
SHA256 is `61f9d9a7565e98221bb0ef994060f3a3addcdf18513cbd1ec802a2403954f4ad`.
Measured demo wall time, synthetic Kernel units, code test latency and fixture zero
provider charge are separate fields; none is represented as measured cloud billing.

### Remaining real integration boundaries

No real model/E12, decoded video/screen/device, QQ/Bilibili account, actual social
sender, production plugin installation or continuous production service was run.
For future integration: reviewed ProviderRegistry/ModelPort transport and destination
privacy/budget policy; sourced perception/media adapters with time/coverage; admitted
recipient-aware social CapabilityPort and real delivery verification; separately
reviewed capability/Grant/Manager/fence construction. These are actual absent adapters/
authorizations, not current production PASS. No self-writing general installer,
distributed authority, optimal general planner or hostile-kernel sandbox guarantee.
Long production soak/real media quality are NOT_RUN. No automatic push/deploy.


### Final qualification / delivery

[Measured offline] Full suite on qualified business source `ac0d934`:
**974 passed / 0 failed / 1 skipped in 97.54s**. The skip remains the E12 real-model
execution gate; no fixture result promotes it. Added26 open-autonomy cases; final
focused new + inherited agency29 passed/6.25s. Resume planning sanity5 passed/0.78s.
Final edits after that source are documentation, machine summaries and fingerprints only.

`qualification.json` records the stage matrix, counters, runtime versions, finite
scope and remaining dependencies; `recovery_matrix.json` records the two actual
SIGKILL cuts/migration/replay/transfer checks; `test_summary.txt` records measured
runs. `life_demo.json` and `contrast_demo.json` are actual service reports, not a
replacement for tests or external attestation. `skill_candidate/` includes the
actual generated source and review/test manifest; it carries no installation authority.

The final source/documentation fingerprint set is
`manifests/nana_e1e6_open_autonomy_v1.json`; it excludes itself and09_STATE to avoid
self-reference. Its SHA256 anchor is in09_STATE. Historical M0–M5 manifests retain
checkpoint semantics rather than claiming their old hashes match final edited docs.
All commits are local; no push, main/R045 change, production access, real model,
private-data read or real external action was performed. Final schema is opt-in12;
defaults remain7/8. READY is an offline candidate, not production qualification.
