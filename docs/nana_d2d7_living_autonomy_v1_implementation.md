# D2–D7 Living Autonomy V1 — development implementation log

Base: 4ad273f540bf8ac2988854b68a689685333e8c67 (local, not pushed).
Branch: dev/nana-core-d2d7-living-autonomy-v1-codex. No automatic push.

## Bounded integration result

Relational 67326d1 and this base share e26288e. C6/C7 reused all 21 source
changes; the remaining source delta is additions and explicit bootstrap/primary/
portability extensions, not lost Relational behavior. Prior Relational reports
are retained from 67326d1 as historical evidence, not this task's validation.
OSS research documents are retained from 9a9f8fe, DESIGN_ONLY unless listed below.
No external source code is copied; pattern implementations remain project code.

## Construction sequence

1. Existing Runtime gets a bounded thread-safe ingress mailbox and condition wait;
only its owning thread writes SQLite. Pausable background cognition and maintenance
safe points use the same queue and C SubjectLoop, never a second reply brain.
2. Explicit development schema11 extends existing jobs/record/call lifecycles. No
second DB. C owns source-backed plan-step appraisal; a trusted finite offline goal
policy can adopt C candidates. Existing governed realization/Kernel own all effects.
3. Source-versioned maintenance slices produce candidates; existing C admission,
ExperienceService/Reflection/Growth remain authority. Living Journal is a projection.
4. Resource reservations, recoverable work and B10 read projections close the loop.
5. One synthetic life/skill demonstration and focused tests, then final full suite.

Default v7/v8/v10 paths remain compatible. Living mode requires explicit11;
production migration, real data/models/sends/devices and real plugin installation
are NOT authorized. Portable subject state, rebuildable projections and machine
execution state must stay distinct. Manager remains post-Judgment negative-only.

The construction notes above are retained; final qualified results follow.

## Implemented result (OFFLINE / SYNTHETIC)

Qualified business source: `48174cb` (full SHA in delivery manifest). Final containing
commit adds only documentation/evidence/test discovery. No automatic push.

| Stage | Result | Permanent modules / concrete behavior |
|---|---|---|
| D2 | IMPLEMENTED / TESTED | presence/cadence.py, runtime.py, queue.py, cognition.py: bounded mailbox, durable receipt, notification-generation wait, adaptive deadlines/heartbeats, user priority, cancellable background computation and replay-safe resume |
| D3 | IMPLEMENTED / TESTED | existing C appraisal/motivation/Growth/relationship plus source-backed living projections; open motivation sources; sourced rest, silence, project and relationship choices |
| D4 | IMPLEMENTED / TESTED, finite offline scope | continuity/agency*.py: C candidate → reviewed finite adoption → per-step C judgment → existing Manager/Kernel/Grant/Budget/Verify → durable cursor and checked outcome |
| D5 | IMPLEMENTED / TESTED | continuity/maintenance.py, temporal.py, skills.py, journal.py: sliced source scans, C admission of derived summaries, known/valid/reference time, checked reflection/lesson integration and reviewed offline procedure extension |
| D6 | IMPLEMENTED / TESTED | resources.py + existing lease/queue/Kernel: atomic call/byte/estimated-cost reservations, protected foreground capacity, measured bytes/latency, backoff, bounded UNKNOWN verification, fresh epoch and exact effect identity |
| D7 | IMPLEMENTED / TESTED, in-process | presence/projections.py and existing B10 application: living state, source motives, Primary User, work/goals, resources/health, Manager versus original will, filtered Living Journal and L0/L1/L2 |

No new business table or dependency. Explicit schema11 rebuilds existing record/
job/call/candidate CHECKs and adds progress/accounting columns. Existing defaults
C7/D8 remain; old v10 is still supported explicitly. Table count stays39. No
production migration. V11 action args/results/receipts/verification use the existing
deletable record graph; immutable rows keep opaque refs. V9/v10 governed actions
can reuse exact prior action-link provenance for verification after explicit upgrade.
Unlinked/erased sources fail closed. No default schema/privacy/Grant relaxation.

## Runtime semantics and useful application wiring

The owning Runtime thread alone reads/writes its SQLite connection. `post(event)`
is thread-safe and returns a volatile pending receipt; `receipt.wait()` only
succeeds after existing EventQueue commits. Do not block the owning thread waiting
for its own pending receipt: call step/run or wait from the adapter thread.
`post_surface` validates a B6 envelope using the immutable identity binding; B10
runtime sessions use this path rather than independently calling C.

D offers WHEN. C decides WHAT/WHY. Maintenance computation occurs only after the
reactive queue is served and advances at most configured slice_items (1–16).
New input interrupts idle waits and background fixture cognition; no transaction
is interrupted halfway. Already-dispatched effects are never called NONE merely
because processing stopped. Full cognition uses the existing supervised fixture
ModelPort and kills/reaps cancelled child processes. C commits remain serialized.

Optional application-owned wiring:

- `runtime.work.configure_agency(OfflineGoalPolicy(programs), OfflineEffectPort(...))`:
  finite reviewed procedure data, no Grant. Governance initialization/negative
  constraints and Kernel Grants/Budgets remain separate trusted construction.
- `runtime.work.learning_policy = OfflineLearningPolicy(tasks)` permits only
  existing narrow, independently checked lesson trials after C selects reflection.
- `runtime.work.accommodation_policy = OfflineAccommodationPolicy(...)` permits
  materializing C's finite voluntary choices through existing CommitmentService.
  It does not specify the choice and cannot remove the original social desire.
- `runtime.application(providers=..., bootstrap_authority=...)` reuses B10. New
  LIVING_RUNTIME/LIVING_JOURNAL/RESOURCE_STATE views obey scope/privacy/support;
  frontends receive neither Store nor controller handles.

C can autonomously produce a program proposal from a sourced concern; no raw user
request is silently adopted. Existing one_live_goal is retained; other proposals
remain candidates, bounded by existing C attention limits. Each plan step gets its
own supported C opportunity. Reconsidering a blocked goal needs a fresh direct
source and CAS. Constraint revocation alone never retries old will. UNKNOWN retains
the original intention/action, verifies at most three scheduled checks, then parks
for review. No new effect ID is manufactured to escape uncertainty.

## Memory, learning and privacy

Source scans persist only cursor/revision/opaque refs in existing jobs. Candidate
bodies live in RecordService, not a snapshot authority. C admits a valid bounded
excerpt bundle as SUMMARY/INFERRED with backlinks. Candidates with corrected,
erased or hidden support are rejected. Summaries are never independent growth
votes and are excluded as raw scan inputs, preventing summary/reflection recursion.

FactValidity requires an exact direct sourced declaration and reviewed transition.
Event, observed, ingested, reference, known and valid times stay separate. Missing
validity remains UNKNOWN. Later support correction invalidates current validity
without rewriting what was known before it. Deletion also removes past-time access.
This is a bounded temporal claim view, not a full temporal graph database.

Living Journal is a bounded filtered projection. It keeps planned/wanted, Manager
BLOCK, Action BLOCK, UNKNOWN, verified effect and independently verified quality
separate. It never includes source prose or governance operands by default.
Personality remains C's source-backed projection; runtime resource pressure is not
an emotion score, identity mutation or evidence of relationship deterioration.

Offline learning actually changes later planning: checked missing-locator failure
→ C reflection → existing lesson trial/review → source-backed self wake → C new
candidate → PlanCompiler inserts locator → independently checked success.
OfflineSkillService can package that tested procedure as data and enable it only
through trusted review in the same finite registry. No Python/plugin code is
written, installed, evaluated or granted external authority. General self-writing
and real plugin installation remain future work.

## Reproduce the complete demonstration

```sh
PYTHONPATH=src .venv/bin/python -m nana_core.presence.living_demo
# Optional: --directory /tmp/new-synthetic-life --output /tmp/life-evidence.json
```

Requires the approved dev Python/SQLite gate; this run used Python3.12.14,
SQLite3.53.1, Pydantic2.13.4. SQLite minimum≥3.51.3 is unchanged. Default demo uses a
fresh temporary Store and deletes it afterward; an explicit existing Store is refused.

Actual observed demonstration (four virtual hours; no real model/body): ordinary
request DECLINE versus Primary User ACCEPT without Grant; social desire retained;
rest selected; no-input project adopted; Manager blocks wanted output; revocation
does not execute; fresh supported reconsideration; quality failure; autonomous
checked learning and revised successful plan; reviewed offline skill; two surfaces;
maintenance yields and resumes; same identity/fresh lease epoch after restart.
All boolean checks true; final0 pending intentions,0 model calls, one FAILED goal
followed by one COMPLETED goal. These are actual calls to the offline fixture
capability and verifier, not claims of real-world access or subjective experience.

For a bare standalone dev process, supply RuntimeConfig JSON with explicit
schema_target11/living{} and synthetic entity/scopes, then use existing
`python -m nana_core.presence.cli init-synthetic|run|status|stop`. Run is foreground,
bounded by --max-seconds; there is no daemon install or production startup. A fresh
bare process has no preexisting interests, procedure port or Grant, so silence is valid.

## Qualification and honest limits

- New focused suite:20 PASS,4.02s. Combined earlier C/D + initial new suite53 PASS.
- First full946 PASS/1 SKIP; a reproduced temporal support bug was fixed afterward.
- Final `.venv/bin/python -m pytest -q tests`:948 PASS/0 FAIL/1 SKIP(E12),98.61s.
- Actual local SIGKILL after durable fixture effect/before Kernel receipt: same
  Action verified on restart, one EXECUTE and one effect; no duplicate C cycle.
- Explicit7/8/9/10→11: same identity/history, FK clean,39 tables.
- V11 portable transfer: goal/history retained, transient owner cleared, old Grants
  revoked, fresh epoch; no agency/port automatically re-created on destination.
- Real process smoke: actual wall-clock scheduler/heartbeat/graceful shutdown.
- Secret/private-artifact/identity-branch scans and final fingerprints: delivery manifest.

Limits: one adopted live goal and the existing narrow reading-card compiler/reference
procedure; general open-ended planning is not claimed. Social output remains
semantic proposals, with availability/approach and execution authority separate;
there is no actual sending adapter or tested real delivery. All model/media quality,
E12, real perception, real plugin building/install, real host operation and production
running are NOT_RUN. Cost reservations are estimates, not provider billing. Long
uninterrupted production uptime/latency is not proven by the short process smoke.
Older C projections can still need indexing at very large history sizes; new watches,
maintenance and journal have explicit bounded coverage. Migration retains the
trusted single-destination/raw-clone and detached-old-archive limits from B8.
Python private service objects are trusted application code, not a hostile-code sandbox.

Identity/relationship/privacy/negative-only Manager/Grant/Budget/Verify invariants
remain. REAL_MEMORY_IMPORT_ENABLED=NO; real models/private data/external actions=0.
main/R045/FIRST_REAL_ASTRBOT_SHADOW/production unchanged. No automatic push.
Next entry is controlled E capability/planning expansion and separately authorized
real ModelPort/perception qualification on this same subject, following PROJECT_BRAIN;
this task does not start them or change L1/L2/B5 priority.
