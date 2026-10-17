# GLOBAL_STAGE E — World Model / Real Cognition

## Coordinate, source and outcome

Base: `255ac99593219295b7126725bf6d51e1890051de`.
Branch: `dev/nana-core-real-cognition-world-loop-v1-codex`.
HEAD at finalization start: `9e7ce7101146ee5a7440bba806bdb00eef366df0`.
Qualified business anchor: `07b736a`; final test anchor: `55ce086`. The final
delivery commit adds evidence/documentation/fingerprints only. Final delivery HEAD
is the last local commit on this branch; this document does not embed its own hash.
The previous task's E1–E6 identifiers are not global stage E. See the current
[capability reconciliation](nana_global_stage_e_capability_reconciliation.md).

**GLOBAL_STAGE = E — World Model / Real Cognition.** Implemented/offline tested;
final measured gate and commands are in `nana_real_cognition_world_loop_v1_evidence/`.
LIVE_MODEL_EXECUTION remains **NOT_RUN**. No available provider credentials were
configured or searched for. HTTP evidence is explicitly a local synthetic provider.
Real image/audio/video byte decoding ran; semantic-model media understanding did not.

## What changed, and what was deliberately reused

| Module | Input → result | Authority/storage/failure |
|---|---|---|
| `continuity/world_loop/cognition.py` | frozen ContextPackage + typed role → correlated proposal | existing RecordService + indexed request header; expired/stale/unknown never commits a Subject decision |
| `world_loop/world.py` | sourced typed claim → temporal belief/alternatives | same Store, erasable value and evidence backlink; contradiction/hidden source/deletion → CONFLICT or UNKNOWN |
| `world_loop/perception.py` | bounded public files/bytes → actual decoded technical observation → world belief | original B9 provider/media contract; no semantic truth invented, fail closed on malformed/unsupported |
| `world_loop/attention.py` | interpreted observation → concern → interest → ordinary C opportunity | persistent indexed lifecycle, source/epoch/revision checks; C owns judgment/adoption |
| `world_loop/coordinator.py` | original LivingWork hooks → one bounded slice | no new event loop/brain; durable existing jobs, failures parked |
| `world_loop/ports.py` | original Planner/Learning/Code proposer requests → transport proposals | original planners/independent validation/lifecycle remain responsible for acceptance |
| `world_loop/learning.py` | independently checked later episode → strategy support/counterexample | original Experience/Lesson, no second learning pipeline; counterexample suspends, no self-certification |
| `world_loop/extension.py` | C-selected capability need → original CodeSkillService | original generate/test/repair/review/use/retire; no autonomous installation authority |
| `presence/resources.py` | original runtime calls + transport headers → one resource projection | bounded daily calls/bytes/cost reservations, known charge sum and explicit unknown count |
| `continuity/context.py` | privacy/scope-valid sources + world views → original ContextPackage | same assembler, budget/conflict completeness unchanged |
| `continuity/application.py` | existing frontend session → WORLD_LOOP projection | read-only filtered view, no added authority |
| `presence/world_demo.py` | environmental inputs/time/governance changes → integrated experiment | same Runtime/SubjectLoop/Store, loopback provider, local synthetic effect port |

F planning: existing multi-goal/dependency/priority/deadline/step/replan machinery.
G learning: existing nine stages, independent baseline/held-out/transfer, Lesson.
I extension: existing code isolation/review/use/retire. These were not rebuilt.
A role name does not imply every future modality/model provider has been qualified.

## Formal cognition transport and lifecycle

`OpenAIJSONTransport(endpoint, model_id, credential=..., harness=False)` implements
non-streaming JSON-object chat completions with Python stdlib HTTPS, system TLS
verification, bounded JSON and no redirect/retry. Trusted application construction
supplies the endpoint, exact returned model ID and optional credential. No credential
is fetched from environment, placed in the Store, shipped to a model, or logged.
HTTP is accepted only for explicit credential-free `127.0.0.1` synthetic harness.
There is no configured real endpoint in the demo.

Supported roles: INTERPRET, GOALS, PLAN, REPLAN, REFLECT, LEARN, SKILL, SOCIAL,
SELF, RETRIEVE, SUMMARIZE. They share one proposal-only DTO. PLAN uses the original
PlannerInput/BoundedPlanner validation; LEARN uses the original LearningSpec and
independent trials; SKILL uses the original CodeSpec, sandbox and review. Direct
HTTP-hypothesis qualification runs all original nine learning stages; REFLECT
returns a proposal and cannot manufacture Experience/Lesson. Provider-native strict
JSON Schema is not advertised for extensible operator argument maps. The expected
schema remains in the frozen request; exact local DTO validation rejects extra
authority fields. Reply origin must match trusted transport construction, so a
loopback reply cannot upgrade itself to REAL_PROVIDER. Other interpretation
roles share the same frozen context/citation/uncertainty contract.

Each durable request binds request key/ID, actual model/provider, identity revision,
Subject revision, runtime epoch, scoped world-header stamp, active goal versions,
context digest/refs, typed role input, creation/deadline, token and cost reservations.
PREPARED → CALLING is committed before the call; only a current correlated response
may become PROPOSED. A provider thread receives immutable DTO/transport only, never
Store/Core handles. The owner checks heartbeat and reactive ingress while waiting.
Only two outstanding transport threads are permitted; late results have no callback
into the Store. Response duplicate keys/nonfinite values/unknown proposal fields,
partial completion, refusal, rate limit and oversized response are rejected.

- timeout/preemption/interrupted CALLING: UNKNOWN, no blind retry;
- malformed/refusal/context overflow/rate limit: FAILED, no empty success;
- changed Subject/world/goal/identity/epoch/deadline/source: STALE or unavailable;
- duplicate request key/completion: existing result, no extra provider call;
- successful reply without billing: actual cost NULL and unknown count retained;
- source deletion: request/proposal payloads retire through original dependencies.

The full transitive provenance graph remains attached to downstream plans, hypotheses
and generated code. It is **not** copied wholesale as mandatory model prose. Planner
and code adapters pin at most two concise relevant sources; the one ContextAssembler
chooses optional views within budget and requires complete contradiction bundles.
Unselected evidence is not presented as model-visible and cannot be cited.

Calls share the original D resource pool. Reservations conservatively count the
request envelope/schema and bounded output; measured wire byte counts are recorded
only when known. `actual_cost_micro` is a sum of known charges, not an assertion that
missing charges were zero. No real-provider billing/pricing/latency was qualified.
A nonzero explicit cost ceiling is required for remote preparation. Provider-side
billing enforcement is outside this offline qualification.

## Persistent temporal world understanding

`SourcedClaim` identifies a bound entity, predicate, bounded value, epistemic kind,
confidence, valid interval, optional exact correction target and affected resources.
Kinds distinguish RAW_OBSERVATION, USER_CLAIM, VERIFIED_RESULT, INTERPRETED,
MODEL_BELIEF, INFERENCE and HISTORICAL. UNKNOWN is a projection state, not fabricated
evidence. User statements cannot become raw observations; model-derived inputs cannot
be promoted to direct verified facts or issue authoritative corrections. A derived
SUMMARY/INFERENCE cannot claim RAW_OBSERVATION merely by citing genuine original
Evidence: Memory authority and epistemic type are also checked. Technical
verification proves a codec result, never the semantic meaning of an image or event.

Event time, valid time and known/recorded time remain separate. Late correction does
not change the original event timestamp. Explicit correction adds a new revision;
other incompatible overlapping claims coexist as CONFLICT. Views can query valid and
known time independently. Deleted/hidden contrary support yields UNKNOWN rather than
silently showing the surviving half or resurrecting a superseded claim.

People/conversations/projects/activities/expected events can be expressed with bound
entities + sourced predicates and linked to existing Memory/Relationship/Commitment
records; this is not a new graph database or a complete semantic ontology. Unknown
future events remain beliefs. Confidence is supplied evidence confidence, not a
calibrated probability inferred from model fluency.

World changes can enter original ContextAssembler world blocks and offer an existing
goal review for exact related resources. They do not directly rewrite/adopt goals.
A new C decision must endorse replan; original plan versions and observations remain
traceable. Actual tests verify the revised plan reads fresh input rather than using
an old observation, and the integrated run records the correction as replan cause.

## Actual media ingestion

Only explicit public, nonpersonal development sources are accepted. The flat public
root is trusted application construction, not a model-selected path. File import
uses dirfd/O_NOFOLLOW/O_NONBLOCK, regular single-link checks and a 16 MiB bound;
symlinks/hardlinks/FIFO are rejected. No source path is persisted. Raw file bytes are
not sent to a remote model by this technical decoder.

- Image: real PNG/JPEG/WEBP pixel decode, dimensions/format/RGB statistics/digest,
  bounded four million pixels. Technical FULL_PIXEL_DECODE ≠ scene understanding.
- Audio: FFmpeg preserves source codec/original rate/channels separately from
  normalized mono 16 kHz PCM, duration/sample count,
  half-second RMS/activity segments and digest. Speech is UNKNOWN, transcript absent,
  NOT_RUN_NO_ASR. Energy is not claimed to be speech.
- Video: FFprobe reads actual frame PTS; up to eight source-frame indices are sampled
  across the bounded clip, decoded with FFmpeg, source time intervals retained.
  Frame differences are technical observations. Unobserved intervals remain explicit;
  TEMPORAL_SAMPLES_NOT_FULL_SEMANTIC_COVERAGE. Audio track presence is reported; its
  semantic content is not inferred from the video frames.

FFmpeg/FFprobe run in bwrap network/namespace isolation with read-only system libraries
and exact input-only mount, CPU/memory/output/timeout bounds and no Store/home mount.
Pillow is a bounded in-process image decoder; it is not claimed to have the same
process isolation. The exact existing local codec processor returns allowlisted
technical fields through B9 MediaSession. Malformed processor output is rejected.

Each item creates sourced Evidence/Memory, technical MEDIA_OBSERVATION and an indexed
VERIFIED_RESULT world belief. Deletion of the source cascades to the derived claim,
world support, model context/proposal and dependent records. Test sources are actual
synthetically generated PNG/WAV/MP4 files, not live camera/audio/private data. A separate
RECORDED_PUBLIC ingress test checks the domain boundary using generated public bytes.
**DECODED_REAL / SEMANTIC_MODEL_NOT_RUN** is the only media capability claim.

## Concerns, interests and living selection

An accepted proposal can offer a concern only with selected, valid source citations,
scope/privacy and exact finite resource descriptors. A transient low-support concern
is deferred; high value or a second independent encounter can form persistent interest.
Topic/entity/scope keys deduplicate/merge; source sets/hot interests/reviews/age are
bounded. Erased source records do not occupy live concern capacity; opaque history
remains without reviving erased topics. Low value can produce an IGNORE opportunity and original goal abandonment;
a C deferral does not falsely claim abandonment. Source withdrawal invalidates support.

An interest creates an ordinary sourced ConcernCue/RuntimeEvent. Original C appraisal,
motivation, attention, normative judgment and Manager separation apply. Only an endorsed
C GoalCandidate reaches original OpenAgencyService adoption and planning. For every
demo goal the evidence records its candidate, intention, committed C cycle and
SELF_WAKE concern. No final Objective/Goal is inserted by the experiment setup.
The loopback proposer compiles finite candidate descriptions from environment data;
it is explicitly an interpreter harness, not evidence of general LLM quality.

D only schedules safe opportunities/one maintenance slice. No second social/goal/
reflection/personality loop was introduced. World concerns are not driven twice by a
parallel generic watch. Recovery completes an already-committed C cycle's idempotent
post-commit ACK; context/provider realization failure is parked rather than repeatedly
creating cycles/candidates or endlessly retrying a failed provider key.

## Necessary G/I integration, not replacement

Original learning failure and checked result lead through original C reflection/
learning opportunities and nine-stage LearningService. Later independent typed
strategy episodes are recomputed with the existing evaluator; distinct context
support/counterexamples are indexed. The displayed fraction is labeled support
fraction, not calibrated confidence. Replayed episodes are not independent evidence.
An independently executed counterexample and ACTIVE→SUSPENDED transition commit
atomically; a crash cannot leave the durable disproof with an ACTIVE strategy.
The suspended original Lesson fences compiled dependent plans.
Two unrelated successes cannot erase a still-valid negative case. Revalidation must
resolve/retest contrary evidence or explicitly withdraw its invalid source.

A sourced capability gap can become C SEEK_CAPABILITY. Original CodeSkillService then
really generates Python, fails independent cases, records diagnostic, repairs, tests
inside bwrap, hashes/reviews, uses the pure local skill through Kernel and retires it.
Both bounded-data text transformation and bounded-analysis composition are qualified.
No pip/install/plugin/source-edit authority was added. Package import/history alone
never reconstitutes sandbox review or executable skill handles.

## Qualification, recovery and migration

`presence.world_demo` runs two distinct 26-hour accelerated worlds. They share the
same Core/Runtime/Store mechanisms, not final actions. Environmental inputs include
project/data problems, three actual media files, social BUSY, REST opportunity,
capability gap, world contradiction/correction, Manager veto/revocation, revoked Grant,
foreground surfaces, malformed/timeout provider, stale result and source deletion.

Main: precision/Unicode failures lead to original learning, later replan and reuse;
a later counterexample suspends a strategy. The contrast uses different domains,
operators, motives and analysis-workflow code; it produces no failed-goal Lesson and
reports that as NOT_APPLICABLE, rather than forcing a false learning narrative.
No-user periods include genuine silence/rest. Foreground ingress preempts maintenance
without losing its cursor. Actions are real executions of the *local synthetic*
effect port and isolated pure code, not real-world/social actions.

Twelve actual subprocess SIGKILL/reopen cuts cover PREPARED, CALLING, persisted
proposal, concern commit, C commit, goal adoption before ACK, world revision, checked
strategy episode, skill cursor, fsynced deletion intent, inherited effect-before-
receipt and learning consolidation. Reopen yields UNKNOWN/no call replay or one
original goal/decision/effect; a durable counterexample remains SUSPENDED.
A separate post-judgment context-failure test demonstrates parked realization.
Actual HTTP reply after Subject or world change is rejected. Restart keeps identity,
world history and goals but requires fresh runtime epoch and trusted controllers.

Explicit schema13 uses four new indexed header tables in the **existing Store**:
`cognitive_requests`, `world_beliefs`, `open_concerns`, `strategy_assessments`.
Total business tables43 (base39). All values/interpretations remain original deletable
artifacts/records. New kinds are six bounded Record kinds, not snapshot truth stores.
Forward migration7/8/12→13 preserves populated Memory/Record/C-cycle IDs/history
and actual v8 Runtime queue history,
FK check is clean, official replay is quarantined. SubjectPackage13 transfer retains
an actual world belief ID/history, revokes Grants, creates no model/sandbox/controller authority; pending calls
from the old epoch become UNKNOWN. No lossy downgrade and no production migration.
Default ContinuityStore7 and Runtime8 are unchanged. No dependency was installed or
new third-party source copied. The dev environment already has Python3.12.14,
SQLite3.53.1, Pillow, FFmpeg and bwrap; SQLite≥3.51.3 gate remains unchanged.

## Reproduce without external data or models

From repository root, using the approved development runtime:

```sh
.venv/bin/python -m nana_core.presence.world_demo --output /tmp/world-main.json
.venv/bin/python -m nana_core.presence.world_demo --contrast --output /tmp/world-contrast.json
.venv/bin/python -m nana_core.presence.world_demo --wall-seconds 1800 --output /tmp/world-wall.json
.venv/bin/python -m pytest -q tests/world_loop tests/open_autonomy
.venv/bin/python -m pytest -q tests
```

Default demo data directories are temporary and cleaned. `--directory` allows an
explicit fresh development directory for inspection; an existing demo Store is
rejected. Do not point it at production or private paths. No production install,
AstrBot, JWT, social account, real provider credential or private memory is needed.
The explicit `tests` command is necessary for all historical suites; default pytest
uses the narrower pre-existing testpaths. One E12 real-model skip must remain.

## Limitations and next gap

LIVE model quality/cost/provider-specific JSON compatibility, ASR, image/video
semantics and live device/screen/social adapters remain NOT_RUN. Exact model aliases
must match the returned provider model ID; alternate APIs/streaming need separate
reviewed transports. Remote execution needs independent approved configuration and
cost controls. API construction is ready; this is not production qualification.

World families are fail-closed/bounded to64 recent revisions per query (overflow
UNKNOWN); high-volume temporal compaction/index policy needs later measured work.
Context/Record lineage is deliberately conservative: a selected irrelevant source can
cause broad deletion invalidation. Large contexts may be rejected rather than silently
hide contradictions. Concern/provider failures parked at PROPOSED/UNKNOWN require new
reviewed evidence; there is no automatic “eventually retry everything” mechanism.
The narrow independent methods/pure-data code realm is not general skill mastery.

Subject privacy deletion covers controlled Store artifacts/dependencies, not arbitrary
already-exported report/package copies or privileged raw filesystem snapshots. Demo
reports contain only public synthetic source data and opaque generated IDs. No
production pins, secrets, private memory, main, R045 or host state were touched.
E12 and all real host statuses remain unchanged.

Next: assess the residual E gaps (approved minimal live-provider qualification and
reviewed semantic-perception input) against H real-adapter safety. F/G/I are existing
foundations to reuse; do not restart F from zero. A/B labels are not invented by this
delivery, and VNext's older Phase A–F labels are a different coordinate system.


## Finalization audit and repaired defects

Every listed defect has a retained regression that failed before its repair.

| Defect | Impact | Repair / regression |
|---|---|---|
| Open DTO schema advertised as native strict schema | Medium: compatible endpoint could reject a valid request | JSON-object wire, exact local validation; `test_generic_proposals_use_json_object_wire_and_local_schema_validation` also rejects a forged grant over actual HTTP |
| Loopback origin self-promotion | High evidence-integrity risk; no real authority was created | Reply origin bound to trusted transport; `test_loopback_reply_cannot_promote_itself_to_real_provider_evidence` |
| Counterexample persisted before suspension | High strategy-integrity risk after crash | Same original transaction commits both; `test_episode_reuse_counterexample_and_independent_revalidation` plus actual strategy SIGKILL cut |
| Derived summary relabeled as raw world fact | High epistemic-integrity risk; no Grant bypass | Direct Memory/type check; `test_derived_summary_cannot_relabel_direct_evidence_as_raw_world_fact` |
| Deleted headers exhausted concern capacity | Medium liveness risk | Count only ACTIVE source records; `test_deleted_concern_history_does_not_exhaust_hot_attention_capacity` |

No new subsystem, table or dependency was needed for these repairs. The only new
media detail retains original audio codec/rate/channels instead of conflating them
with normalized PCM. Current development schema remains13, total43 business tables,
Stage E adds4. Default C7/D8 and production schemas remain unchanged.

## Architecture simplification / authority review

The machine-readable authority matrix reviews WorldLoopWork, ConcernService,
CognitionSession, WorldModel, EpisodeLearning, SelfExtensionWork, OpenAgencyService,
SubjectLoop and NanaRuntime. Only SubjectLoop produces final normative Judgment /
Intention. OpenAgencyService mechanically commits an eligible C-endorsed candidate;
its adoption method is not an independent will. Skill development holds trusted
application review handles for the bounded realm; model DTOs never receive them.
Neither activation nor Manager PASS creates a Grant. Synthetic world JSON describes
external fixture effects, not another Subject database. No meta-agent was added.

## Evidence index and operational limits

`qualification.json` records scoped model/media counts, source anchors and gates;
`store_state.json` captures counts/FK/state from the two actual fixture Stores;
`recovery_matrix.json` and `migration_matrix.json` map successful executable tests;
`architecture_authority_matrix.json` documents the source-level authority review.
`living_soak.json` / `contrast_soak.json` retain actual goal/cycle/concern lineage,
technical media, learning, code execution and contrast results. `wall_soak.json`,
`wall_observations.json` and `wall_final_source_smoke.json` separate long-lived
Runtime evidence from final-source smoke. `test_summary.txt` and `limitations.txt`
are concise entry points; no DB is committed.

The long wall-clock process began on9e7ce710 plus the JSON-object wire correction.
Subsequent closeout fixes do not change Runtime/scheduler code; they address negative
provenance/summary inputs, counterexample transaction, deleted capacity and audio
metadata. This process did not hot-reload those changes. Full regression, final
virtual worlds and a separate final-source wall-clock smoke qualify the final code.
No old interrupted soak is counted toward this run's duration.

C/D wake envelopes remain development SYNTHETIC_ONLY. Public recorded input and
provider proposal provenance do not promote an experiment into production authority.
Real private-memory ingress remains disabled. Descriptor/candidate realms remain
finite: at most64 dynamic objective descriptions and bounded concern/revision windows;
this is not a claim of unlimited three-year production operation. Full historical
compaction and independently approved live semantic provider/media qualification
remain future work. Primary User influence, independent Social Appetite, voluntary
accommodation, negative-only Manager, hard data privacy and UNKNOWN semantics are
inherited and covered by the full regression, not replaced by this audit.


## Final measured delivery

GLOBAL_STAGE_E_WORLD_MODEL_REAL_COGNITION = OFFLINE_CANDIDATE_READY.
Full repository: 1017 passed /0 failed /1 skipped(E12),
121.108s JUnit suite time. Focused World Loop:43 passed.
Virtual worlds:26.08h main,26.069444h contrast, all applicable gates PASS.
Actual wall process:1800.131s; final-source smoke30.087s. Exact resource ranges,
source chronology and all12 SIGKILL cuts are in machine-readable evidence.
Live model/semantic perception/E12 remain NOT_RUN; real external actions/social
sends/private reads/production/main/R045 changes/pushes this task are all0.
Final local HEAD/parent are obtained from Git; evidence anchor is 55ce08679091ffb0efa0a15b74bc4f8edb025b23.
