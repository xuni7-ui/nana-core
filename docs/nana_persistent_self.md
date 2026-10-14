# Nana C-V2 — Persistent Self offline candidate

This is an extension of Continuous Self/VNext-1, not a replacement runtime.
Design authority: [ADR-CV2-001](ADR/ADR-CV2-001-persistent-subject.md).
Evidence is synthetic/offline only. Real memory ingress remains code-disabled.

## One owner of the next intention

`continuity.subject.SubjectLoop` coordinates the single causal loop. No
background thread, daemon, scheduler, independent initiative engine, model
account, action executor or separate state database is created.

`SubjectLoop.run(input, expected_revision=...)` performs cheap deterministic
appraisal/motivation/attention/judgment. `cognize(..., model, authority, policy)`
optionally uses the existing frozen ModelPort/context protocol. A provider gets
serialized context, not a Store/service/authority handle. Source and identity
checks plus freshness validation surround inference. No DB transaction spans a
model call. Proposals and final Judgment are stored separately in a deletable
cycle record. Neither is Evidence or a success receipt.

The starting policy is ordinal and inspectable. It is not a learned general
reasoner: source adapters currently supply structured relevance/novelty/risk
facets. Natural-language appraisal quality requires later real semantic tests.
No model label, game name, simulation day or expected-test-answer flag determines
identity, interests or decisions.

## Persistent source → transition → projection

* `ingress.py`: source-key idempotency and memory admission before capture.
  Significant/new/relational/self-relevant occurrences may be kept without the
  user saying “remember”. Non-retention has priority over every other factor.
  TEMPORARY and FORGET_LATER retain no body in this version, rather than promising
  a future timer. Exact repeated occurrence is merged by persistent source key;
  changed retained payload under that key is rejected. No content hash of a
  deliberately unretained body is kept.
* `policy.py`: Situation/Appraisal/Motivation/Judgment/Intention contracts. Due
  adopted commitments beat optional exploration; sourced constraints can produce
  ALTERNATIVE/DISAGREE behavior. A quiet wake is legitimate autonomous behavior.
* `growth.py`: narrow evidence-supported preference/self-belief transition.
  Two independent direct observation roots can adopt an inclination. A model,
  reflection or repeated self-selected behavior cannot create independent support.
  Support/counter-evidence are recomputed from live sources. Equal opposing roots
  dispute a preference. Explicit supported replacement is terminal supersession.
* `state.py`, `projections.py`: read-only current views. A LivingSelfState is
  recomputed from accepted decisions/current sources/time; there is no saved
  authoritative living snapshot. Personality records explain provenance and
  limitations; mood activation is not stable character or canonical identity.
* `reflection.py`: only existing independently verified experiences can produce
  reflection. The first implemented rule is the existing reading-card locator
  rule, tested by existing PlanCompiler then explicitly locally reviewed before
  activation. Reflection cannot invent evidence, recursively reflect on itself,
  change identity, enable a capability or grant execution.
* `simulation.py`: input schedule/world/model fixtures around the real modules.
  This is a reproducible whole-subject acceptance experiment, not production.

## State and authority

Normalized development schema **v7**, 8 new tables: `subject_events`,
`subject_cycles`, `self_assertions`, `assertion_signals`, `relationship_events`,
`subject_intentions`, `subject_goal_candidates`, `subject_reflections`.
Private text is in existing artifacts/continuity_records and dependency chains;
immutable event changes contain IDs, enums, counts and timestamps. The generic
privacy erasure closure covers every new record kind. Rebuild never uses deleted
payloads or corrected stale sources to re-certify a preference.

One `core_meta` subject revision records accepted cycle order. The existing
single-writer lock and BEGIN IMMEDIATE transaction commit cycle + signals +
intention + candidate + revision atomically. Input admission is separately
idempotent, so a crash before acceptance leaves a safe resumable source. A stale
expected revision fails; terminal intentions cannot be reactivated. Duplicate
accepted events return the original decision (or explicit RATIONALE_NOT_RETAINED/
RATIONALE_RETIRED if no rationale was kept/deletion retired it), never a new cycle.

At most 8 live intentions across scopes; exact slot dedup, 7-day expiry. New
counter-evidence also drops an earlier optional exploration intention whose
motivation is no longer supported. Expired/deleted candidates are not shown as
live. Accepted clock rollback is blocked against persisted cycle high-water.
Occurrence time remains source time; it is not replaced by restart time.

CanonicalIdentity/charter are never edited by this subsystem. C candidates have
`adopted=false`, `execution_authority=false`, and terminate in SHADOW_BLOCKED or
NO_ACTION. StandingDelegation is a finite, scoped **contract only** with no
registration/activation operation. Available capabilities/devices are known
context, not authority. Existing ActionKernel remains behind the original offline
execution fence. Actions/Attempts/Grants/Budgets stay empty.

## Dependencies and migration

```
Clock / Store / revision stamp / DTO
  → Identity / Memory / deletable Records / Projects / Commitments / Experience
  → Subject contracts / source ingestion / read-only subject queries
  → pure policy + source-backed growth / reflection transitions
  → living/personality/relationship projections
  → existing ContextAssembler / ModelPort
  → SubjectLoop coordinator → explicit accepted transitions
```

Projections do not import the coordinator. Context does not invoke loop mutation.
Optional model cognition is a coordinator call through a typed frozen proposal;
all lower components remain independently read-only or explicit transition APIs.

v7 rebuilds existing parent CHECK constraints with FK disabled **before** BEGIN,
keeps parent names/rows and validates all FKs before commit. FK enforcement is
restored on failure. Populated-v6 data migration is tested. Default v1 Store stays
v1. Rollback: managed pre-upgrade snapshot, quarantine, no schema downgrade or
production upgrade. SQLite >=3.51.3 gate is unchanged. No new dependencies.

## Runtime contracts

```python
loop = SubjectLoop(store, scopes=("synthetic-life",),
                   privacy_classes=("PUBLIC", "PROJECT", "PERSONAL"))
result = loop.run(subject_input, expected_revision=loop.revision)
# result: typed appraisal, motives, attention, judgment, intention,
# source references, candidate ID, barrier and optional raw model proposal.
state, personality, relationship = project_self(
    store, entity_id="synthetic-sister", scope="synthetic-life",
    privacy_classes=("PUBLIC", "PROJECT", "PERSONAL"))
```

WakeCondition enumerates incoming/time/goal/anomaly/relationship/self/reflection/
device/environment events; an actual always-on scheduler is D work, not hidden
inside C. Wake carries no new lived experience or preference signal. Reflection
input must go through `loop.reflect(existing_experience_id, ...)`, never be
submitted as a fabricated external observation.

Qualitative state fields have source IDs and one view-wide source confidence.
No biological mood claim or 0–100 affection scale. Relationship events model
history/projects/jokes/norms/boundaries/conflict/repair/trust/commitment across
SELF/PERSON/GROUP/COMMUNITY/AGENT (existing PROJECT/OBJECT retained).
Source coverage remains explicit UNKNOWN unless a source actually reported it.

## Repeat the whole-subject experiment

```bash
.venv/bin/python -m nana_core.continuity.subject.simulation \
  --output .nana-experiment/persistent-self-new-run --days 60
.venv/bin/python -m pytest -q tests/continuous_self
.venv/bin/python -m pytest -q tests
```

Output directory must be new and private. No existing experiment data is reset.
The three matched worlds share the exact pre-day4 identity/memories/projects/
commitment snapshot. Only preference support signals or lesson application differ.
The failure experience exists in the no-lesson control. A false `success:true`
in the world fixture cannot pass independent field verification.

Actual process restart swaps AnalyticalFixturePort for CautiousFixturePort and
compares full subject state digest and derived projections. Separate actual
SIGKILL tests kill inside assertion/cycle transaction and after commit, reopen
in new interpreters, resume once and reject duplicate ingress. The 60-day soak
tracks live concerns, cold history, qualitative activation, independent roots,
reflection count and hot-state size. Cold event history is allowed to grow.

## Limits / next boundary

This candidate demonstrates causal engineering continuity, not subjective
consciousness, real-world independent judgment, emotional experience, natural
semantic preference inference or E12. Source independence is provenance-root
independence under trusted local adapters, not statistical independence against
an adversarial operator inventing different sources. Root/privileged whole-DB
clones and already-exported/RAM copies remain outside deletion guarantees.

There is no production integration in this task. Real memory/host/model/standing
autonomy and E/G action adoption need separate authorization/qualification. Real
B5-3/R045 facts remain owned by the other executor. No fixture result upgrades
FIRST_REAL_ASTRBOT_SHADOW, host_binding or real E12 status.
