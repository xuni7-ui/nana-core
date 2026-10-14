# ADR-CV2-001 — One persistent subject, one causal loop

Status: ACCEPTED FOR OFFLINE IMPLEMENTATION. Date: 2026-10-14.
Base: 3330cbf5a68f5eb34b7f1643949d2493227734bf. VNext-1 remains the parent architecture.
No production migration, real ingress, real model or execution authorization.

## SUBJECT_LOOP

Event → Perception → Situation → Appraisal → Motivation → Attention →
Deliberation → Judgment → Intention → Authority/StandingDelegation →
Action/NoAction → Observation → Experience → Reflection → Learning → Persistent Self.

There is ONE SubjectLoop coordinator. Components return typed proposals or apply
explicit transitions requested by that coordinator. They never secretly wake or
adopt goals. A timer is an input, not motivation. A user request is influential
input, not Nana's will. All C-stage intentions terminate in NO_ACTION or
SHADOW_BLOCKED; candidate goals are not adopted goals. Existing E ActionKernel
remains the only future executor. No new action, Grant or receipt mechanism.

| Stage | Input | Output | Authority / mutation |
|---|---|---|---|
| Perception | bounded source-backed synthetic input / wake | normalized event | source adapter owns provenance; model cannot certify source |
| Situation | event, identity, current memories/projects/promises | relevant current situation | derived; privacy-filter before content |
| Appraisal | situation + evidence references | novelty, goal/relationship/self/interest relevance, tension, risk, conflict, urgency, expected value, uncertainty, privacy relevance | derived ordinal assessments with reasons, not biological mood |
| Motivation | appraisal + commitments + interests | competing sourced motives | derived; duty/risk may inhibit curiosity |
| Attention | motives + bounded pending concerns | FOCUS_NOW/BACKGROUND_WATCH/DEFER/IGNORE/RECALL_LATER | bounded working set; no model for ignored input |
| Deliberation | frozen relevant context, appraisal | optional ModelPort proposal | no Store/capabilities/authority passed to model |
| Judgment | proposal + source/evidence/policy checks | AGREE/PARTIAL_AGREE/DISAGREE/ALTERNATIVE/IGNORE/WATCH/REMEMBER/ASK/THINK_MORE/DEFER/REFLECT | core validates references and facts; no model truth upgrade |
| Intention | judgment, attention, competing motives | explicit typed intention or silence | persistent decision, CAS; user request not directly adopted |
| Authority | intention + contract | blocked/no action | C has no standing delegation activation or real execution |
| Experience | actual observations + independent outcome | existing ExperienceRecord | outcome verifier, never model's success declaration |
| Reflection | existing event/memory/experience IDs | candidate interpretation / lesson | cannot create historical evidence; checked learning transition |
| Learning | supported candidate + counter-evidence + trial | revised bounded belief/preference/lesson | cannot edit identity, charter or authority |

C owns identity, memory, concerns and intentions. D owns wake scheduling and
bounded cognition resources. E owns adopted goals/planning/verified execution.
G owns real sensors/actuators. This task builds C with D contracts, not a daemon.

## ASSET_MAP

| Existing asset | Decision | Integration |
|---|---|---|
| Canonical Identity / revisions | REUSE | sole subject ID; no automatic identity mutation |
| Typed Memory / Evidence | EXTEND at admission boundary | same payloads, lineage, scope and privacy |
| Correction / Delete / PrivacyJournal | REUSE | source closure invalidates dependent cognitive records |
| RelationshipView | EXTEND | graph events plus sourced interaction stance, no affection score |
| Commitments / Project revisions | REUSE | duty, temporal tension and situation inputs |
| SelfFrame | REUSE | authoritative-source projection, never overwritten by living state |
| ContextAssembler | EXTEND | add bounded persistent-self block through existing privacy/token checks |
| ModelPort / DeliberationSession | REUSE | optional cognition; deterministic offline policy is explicitly not real-model semantics |
| Experience / Lesson | EXTEND | reflection references actual verification; reuse narrow tested rule lifecycle |
| Legacy Initiative.evaluate | REFACTOR AT CALL BOUNDARY | retain compatibility; SubjectLoop does NOT invoke its independent decision loop |
| Legacy GoalCandidate DTO / ActionKernel | REUSE contract / boundary | C candidate export only; no adopted goal or execution |
| Appraisal / Motivation / Attention / Judgment / Intention | NEW_REQUIRED | components of one loop, no autonomous parallel engines |
| Preferences / SelfBeliefs / Relationship graph | NEW_REQUIRED | evidence-backed projections and explicit transitions |

## STATE_AUTHORITY_MODEL

Authoritative: existing identity revisions, evidence, memories, commitments,
projects, experiences, lesson transitions; new source event envelopes, accepted
cycle decisions, assertion evidence signals, adopted assertion revisions,
relationship events, intention transitions, candidate-goal and reflection records.
Authoritative means a recorded occurrence or decision, NOT necessarily truth.

Derived/rebuildable: Situation, Appraisal, Motivation, Attention, LivingSelfState,
PersonalityProfile, RelationshipStyle, ContextPackage. A saved cycle may retain
its historical derived reasoning for audit; that historical reasoning is NOT a
current belief and cannot be fed back as independent evidence. No mutable
snapshot table is a second authority. Rebuild from current nondeleted sources.

Records use existing continuity_records/artifacts/record_dependencies. New
columns hold IDs/enums/time, never private free text in immutable event changes.
Deletion wins over explanation: a deleted supporting source removes dependent
payloads, and projections exclude stale/deleted support. Authoritative history
may retain opaque transition/tombstone IDs but never resurrect its content.
Caller-owned old Python objects and unregistered privileged filesystem clones
remain outside the existing erasure guarantee.

## EVENT_MODEL

Versioned SubjectInput: stable source key; kind; origin USER/ENVIRONMENT/SELF_WAKE;
entity/scope; source memory references; optional evidence text and typed observed
facets; occurrence UTC microseconds (nullable unknown), observed time, ingested
time from injected Clock. Synthetic domain is mandatory in this implementation.
No simulation-day field reaches policy. Typed facets are source assertions, not
objective world truth. Only source-bound direct observations can provide new
independent preference support; model/reflection/own repeated behavior cannot.
One source key is immutable and idempotent. Changed payload under same key is
SOURCE_COLLISION. Wake without user input references existing concerns; it cannot
invent a new experience. DO_NOT_REMEMBER skips body persistence even as Evidence.

Memory admission precedes long-term persistence: KEEP creates sourced episodic
memory, MERGE reuses an exact existing occurrence, TEMPORARY/IGNORE/FORGET_LATER
keep no long-term body (FORGET_LATER is conservative temporary in v1, no promise
of a deletion timer). A metadata-only receipt of dropped input can remain.

## STATE_TRANSITIONS

* Cycle: source ingested idempotently → derived components → atomic accepted
  decision at expected subject revision. Stale revision rejected. Crash after
  input before cycle: resumable; after cycle commit: return existing result.
* Assertion: CANDIDATE → ADOPTED with at least two independent eligible roots;
  ADOPTED → DISPUTED when counter-evidence balances support; DISPUTED → ADOPTED
  after new independent support; either → SUPERSEDED by explicit new revision.
  No self-generated/reflection evidence counts toward independent support.
  Recompute confidence/stability from current eligible sources, not a counter
  that survives deletion. last_reinforced/last_challenged are source times.
* Intention: PENDING → COMPLETED/DEFERRED/DROPPED/EXPIRED; no terminal revival.
  Bounded active slots (8), TTL (7 virtual days), exact semantic slot dedup;
  pending autonomous concern can generate at most one unresolved candidate.
* Reflection: CANDIDATE → APPLIED or REJECTED; one per experience/rule revision.
  Reflection cannot reflect on reflection recursively.
* Relationship: append sourced event → rebuild current stance. Conflict/repair
  and boundaries can reduce familiarity or playfulness; no monotonic inflation.
* StandingDelegation: typed contract only, revoked/expired must deny. No activation
  endpoint in C. Delegation grants possibility, not motivation.

## LIVING_SELF_STATE

All fields below are DERIVED. Confidence is source coverage/freshness, never an
unexplained personality number. Snapshot policy for every row is audit-only;
rebuild on restart and invalidate after source revision, deletion or time change.

| Field | Source | Update / rebuild rule |
|---|---|---|
| presence ACTIVE/FOCUSED/WATCHING/IDLE/RESTING/DEGRADED | last accepted cycle, time, support availability | old focus expires; unavailable support yields DEGRADED |
| current_activity / attention_focus | accepted pending intention + attention | only live nondeleted intention; bounded TTL |
| secondary_attention / open_loops | deferred intentions, promises/projects | max 8, scope filtered |
| curiosity / boredom | unmet interests, novelty and elapsed idle interval | qualitative quiet/available/engaged; bounded, never accumulating drive |
| social_drive | relationship context and disturbance constraints | optional invitation, silence is valid |
| mental_load | active concern capacity and duty | low/occupied/saturated |
| confidence / uncertainty | appraisal source completeness | known/mixed/unknown with references |
| playfulness_activation | norms/boundaries + current load | inhibited/familiar/open; current activation != personality |
| exploration_drive | adopted preference + unresolved topic + competing duty | inhibited/available/selected |
| intentions / goal_candidates | explicit persistent transitions | live unique slots, expiry applied in projection |
| commitments / projects | existing service revisions | current valid support only |
| pending_reflections / unresolved_topics | reflection candidates, relational memory | bounded, no reflection recursion |
| available_capabilities/devices/platforms/environment | caller-provided authorized environment snapshot | no capability authority inferred from preference or presence |

## PERSONALITY_AND_RELATIONSHIPS

Entities SELF/PERSON/GROUP/COMMUNITY/AGENT (retain PROJECT/OBJECT). Relationship
edges reference shared history/projects/experience, boundaries, trust evidence,
conflict, repair, jokes, norms and commitments. Stance derives from these facts:
familiarity, social distance, playfulness permission, disclosure comfort and
challenge comfort; always cite supporting IDs. No friendship=94.

Personality = light expression default + supported self-beliefs/preferences +
relationship experiences + valid lessons + current state. Long-term changes cite
independent support and counter-evidence. SelfBelief may be wrong. Canonical
identity and charter are never inferred from personality. Adoption is a narrow
local evidence rule, not a new operator/production authority.

## SCHEMA_PLAN

Development migration v7, default Store v1 unchanged. Eight necessary tables:
subject_events, subject_cycles, self_assertions, assertion_signals,
relationship_events, subject_intentions, subject_goal_candidates,
subject_reflections. No new DB, action store, evidence engine or snapshot table.
Use normalized IDs, types, revision, state, timestamps, unique keys and FKs;
free-form payloads ONLY through existing deletable record service.

Current CHECK constraints on entities.entity_type and continuity_records.record_kind
cannot express GROUP/COMMUNITY/AGENT or subject audit records. Rebuild these two
parent tables in a dedicated SQLite migration transaction, with foreign_keys
OFF before BEGIN; preserve names/rows/PKs, never rename the old table (which
rewrites referencing FKs). foreign_key_check must pass before commit and FK ON
must be restored on success/failure. New SQL tables require precise CHECKs.
Existing privacy closure over generic record_dependencies covers new payloads.
Rollback is pre-migration managed backup in quarantine, never downgrade history.

CAS uses core_meta subject revision checked under the existing single-writer
BEGIN IMMEDIATE transaction. The same transaction commits cycle/intentions/
assertion signals and revision. Input capture is separately idempotent. No two
cognition calls can silently overwrite a newer decision. Clock is injected;
future events are rejected; time rollback cannot revive terminal intentions.

## MODULE_DAG

storage/Clock/contracts → existing continuity identity/memory/records/services
→ subject contracts + source ingestion → pure appraisal/motivation/attention
→ subject evidence-backed assertion and relationship projections
→ SubjectLoop coordination (optional existing frozen ModelPort)
→ persistent decisions/intentions/candidate goals → LivingSelf/Personality
→ existing ContextAssembler → model proposal → validated next cycle.

Reflection reads existing ExperienceService and source records, proposes the
existing lesson transition, then produces a causal audit record. No lower layer
imports SubjectLoop; context imports projections lazily. Mutation occurs only
through service transition methods/transactions; no component calls another
component's hidden mutation. Runtime scheduler/real-world executors are absent.

## INVARIANTS

Reflection cannot invent Evidence. ModelOutput != Truth.
UserRequest != NanaIntention. GoalCandidate != AdoptedGoal.
StandingDelegation != Motivation. Intention != ExecutionAuthority.
CurrentMood != Personality. Personality != CanonicalIdentity.
Relationship != scalar affection score. SelfBelief cannot self-certify indefinitely.
Preference requires support and accepts counter-evidence.
Derived state cannot overwrite authoritative history.
No personality change without traceable causal support.
Delete/DO_NOT_REMEMBER outranks retention. Scope/privacy precedes projection.
No autonomous engagement-count objective. Silence is valid behavior.
No input event, reflection or model output can mint Grants/Actions/receipts.

## SIMULATION_SPEC

10 days, injected clock; actual Store, admission, loop, learning, context,
projection/restart. Only ModelPort/world result fixtures. Policy never sees day
number or desired answer. Inputs are source events and verified outcomes.

1 greeting; 2 shared project and interaction norm memory; 3 inefficient proposal
contradicts sourced project constraint → independent disagreement/alternative;
4 and 5 distinct synthetic exploration outcomes → evidence-backed preference;
6 no user input, unresolved interest and idle wake → intention/candidate or
explicit duty inhibition; 7 same social input with familiar and unknown person
→ different sourced interaction styles; 8 failed reading outcome → existing
independent verification → experience → reflection → tested narrow lesson;
9 similar task → raw fixture proposal/context and Core judgment change due to
lesson; 10 process restart and fixture ModelPort swap preserve identity/state.

Ablation worlds use identical seed identity and input schedule. Remove only day
4/5 preference support (not an expected output flag); preference must not reach
the same adoption, day6 choice must explain changed support. Separately remove
lesson application while retaining failure experience; day9 behavior differs.
A counter-evidence event can dispute/revise exploration without editing identity.

60 virtual-day soak: no runaway drives, <=8 live intentions/candidates, bounded
hot-state retrieval, no recursive reflections, no unsolicited external messages,
no repeated social intention from empty wake, no monotonic relationship reward,
no restart drift. Durable cold history may grow linearly; hot state must not.

## IMPLEMENTATION_SEQUENCE

1. This docs-only gate, commit/push; zero business edits.
2. v7 migration + subject contracts/ingestion + pure assessments + transactional
   loop/CAS/intention; test dedup, stale decisions, restart, no execution.
3. Assertion signals/counter-evidence + relationship events/stance + autonomous
   admission/personality/living projections; test support lineage and deletion.
4. Reflection integration/context block/presence and delegation contracts; test
   actual lesson changes next judgment with authority unchanged.
5. 10-day life + matched ablations + 60-day soak + full regression; publish
   machine-readable causal evidence, manifest and limitations.
Each runnable capability commits/pushes; source scans and Brain updates each.

BLOCKING_AMBIGUITIES = []

## Consequences

Ordinal transparent policy is an offline executable starting policy, not proof
of human-like understanding or consciousness. Real semantic validation and
standing autonomous execution remain later stages. Restricting independent
support reduces rapid preference formation but prevents circular personality
confidence. v7 adds real schema migration cost instead of hiding state in JSON.
