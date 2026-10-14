# Continuous Self C–D: developer contract

This is a permanent Core **offline candidate**, not the approved R045 package.
Design: VNext-1@45a0e0b. All examples below use synthetic content. Do not open a
production Store, substitute real captures, or share a real operator/Store with a
model. The sole state authority remains one SQLite Store and writer lock.

## Entry points and ownership

| Module | Input → output | Durable authority / failure |
|---|---|---|
| `continuity.store.ContinuityStore` | dev path → same Store, explicit schema6 | v1 default unchanged; populated v1 refuses unsafe conversion; fixed Shadow fence |
| `identity.IdentityService` | operator + expected revision + reviewed expression → canonical revision | Original Store UUID; immutable charter; CAS rejects stale edits |
| `memory.MemoryService` | synthetic EvidenceInput / MemoryCandidate → stable IDs | artifact-only text, typed SQL metadata, source collision/dedup, live backlinks |
| `relationships.relationship_view` | entity + readable scopes/privacy → sourced view | No identity authority; no affection score |
| `commitments.CommitmentService` | candidate / reviewed transition → promise state | Candidate is not adopted; target-bound independent fulfillment check |
| `projects.ProjectService` | typed content + expected revision → current project | Narrative revisions are deletable records; SQL holds binding/state/revision |
| `context.self_frame` | current sources → derived SelfFrame | Rebuildable; not a truth database |
| `context.ContextAssembler` | situation + trusted policy + counter → ContextPackage/Manifest | Privacy first; bounded retrieval/context; unresolved conflict all-or-block |
| `cognition.ContinuityModelPort` | FrozenModelInput v2 → strict raw JSON proposal | No Store, operator, Grant, Receipt or success authority |
| `learning.ExperienceService` | checked outcome → experience → scoped trial lesson | Existing StrategyRule/PlanCompiler; explicit activation; cannot enlarge permission |
| `contracts.RealMemoryIngress` | proposed qualification → DENY | Always REAL_MEMORY_IMPORT_DISABLED in this candidate |

## Minimal use

```python
from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.context import ContextAssembler, ContextPolicy, ContextRequest
from nana_core.continuity.cognition import AnalyticalFixturePort, DeliberationSession

# This path is a fresh DEVELOPMENT database, never an AstrBot/Iris path.
with ContinuityStore(".nana-experiment/continuous-self/example.db") as store:
    authority = OperatorAuthority("synthetic-dev-controller")
    identity = IdentityService(store, authority).current()
    memory = MemoryService(store, authority)
    memory.entity("synthetic-person", "PERSON")
    now = store.clock.utc_now_us()
    evidence_id = memory.capture(EvidenceInput(
        provenance=Provenance(source_namespace="synthetic.example",
            source_reference="statement-1", source_kind="USER_STATEMENT"),
        text="Use concise synthetic notes", privacy_class="PERSONAL",
        event_time_us=now, observed_time_us=now))
    memory_id = memory.add(MemoryCandidate(entity_id="synthetic-person",
        scope="synthetic-example", memory_type=MemoryType.RELATIONAL,
        epistemic_kind="STATEMENT", source_evidence_id=evidence_id,
        text="Use concise synthetic notes", predicate_key="preference.notes"))
    policy = ContextPolicy(policy_id="local-only-v1",
        allowed_scopes=("synthetic-example",), readable_privacy=("PERSONAL",))
    request = ContextRequest(entity_id="synthetic-person", scopes=("synthetic-example",),
        task_class="reading_card", task="Prepare a fictional reading card")
    assembler = ContextAssembler(store, authority)
    context = assembler.assemble(request, policy,
        limitations=("OFFLINE_ONLY", "NO_EXECUTION_AUTHORITY"))
    result = DeliberationSession(assembler).run(AnalyticalFixturePort(), context, request, policy)
    assert result.execution == "NOT_EXECUTED"
    # No proposed operation is sent to a capability by this API.
```

An explicit new process can reopen that development DB and call the same services.
It recovers the identity; it does not generate a persona from the chosen model.
Self memory must use `identity.identity_id`, whose entity type is SELF.

## Memory, assessment and time

Each memory has: memory_id, entity_id, scope, seven-valued memory_type,
epistemic_kind, source_evidence_id, payload_artifact_id, predicate_key,
event_time_us, observed_time_us, ingested_time_us, confidence, authority,
importance, significance, privacy_class, lifecycle, assessment, correction_of,
superseded_by, created_at_us, updated_at_us and commit event_id.
`read()` adds source_provenance including the original source reference/revision.
All times are integer UTC epoch microseconds; unknown event time is NULL. No
restart/import timestamp substitutes for original occurrence time.

Evidence is an original source assertion, not automatically true. A belief's
current assessment is Nana's current supported interpretation; source/backlinks
explain why. Summaries/inferences cannot become observations; their privacy is
at least as restrictive as all parents. Context preserves epistemic kind,
confidence, authority and unknowns. PRIVATE meaning is not inferred by an LLM.

- Explicit correction: commit a new evidence source and MemoryCandidate with the
  same subject/predicate/scope and `correction_of=old_id`. Direct/non-older source
  required. Old belief becomes SUPERSEDED; dependent summaries become WITHDRAWN.
- Ambiguous conflicting statements remain DISPUTED. Normal query does not inject
  either as current fact. Context requires a complete authorized bundle or blocks.
- Confidence is a reviewed assessment, not an evidence rewrite.
- SUPPRESSED and ARCHIVED retain payload; explicit restoration is possible only
  for non-retired assessment. Neither means erased.
- `memory.forget(id, authority)` erases the conservative source/dependency closure.
  Deleted or superseded facts do not silently become current again when their
  replacement disappears. Deleted stable source keys/revisions remain blocked.

## Commitments and projects

Legal promise transitions:

```text
PROPOSED → ADOPTED → ACTIVE → FULFILLED | FAILED | CANCELLED | SUPERSEDED
PROPOSED → CANCELLED
ADOPTED → CANCELLED | SUPERSEDED
```

Operator object authority and expected revision are mandatory. SUPERSEDED needs
an adopted replacement for the same entity. FULFILLED needs an original
SYSTEM_VERIFICATION observation with `FulfillmentCheck`: exact commitment_id,
commitment_revision, satisfied=true and result_reference. Source kind alone or an
unrelated successful check is insufficient. Domain-specific verification remains
the trusted checker's responsibility; the model cannot create checker authority.

ProjectContent has bounded typed milestones/decisions/questions/blockers/progress/
next actions. `save(expected_revision=0)` creates; later revisions use CAS. A
project's COMPLETED state is a reviewed project assessment, not an Action receipt.
Deleted support erases payload; corrected support causes explicit REQUIRES_REVIEW.

## Privacy, context and evidence coverage

ContextPolicy is held by the trusted application controller, not chosen by the
model. Requested scopes must be allowed. Remote context uses only the
intersection of readable_privacy and remote_privacy; SECRET can never enter the
remote set. **The current task itself defaults PERSONAL** and is subject to the
same destination gate, not just retrieved memories. Explicit PUBLIC classification
in tests describes synthetic instructions only.

Retrieval loads at most128 candidates by default, with explicit maximum512. A
manifest reports visible total/candidate count, dropped block IDs and coverage.
Conflict families reload as a whole up to64; hidden or oversized counterevidence
blocks context. No private payload is read simply to explain why it was omitted.

Identity/task/constraints are mandatory. Whole serialized input plus manifest
counts against max_input_tokens-output_reserve_tokens. Default UTF8 byte counting
is an offline estimate, not a certified real-model tokenizer. A real adapter must
supply its framing/token counter and independently authorized endpoint/ledger.

Issued contexts are hashed snapshots; after correction/deletion/state change,
validation rejects them. Only64 issued hashes are kept, not persisted plaintext.
Rebuild a context after process restart. Coverage defaults UNKNOWN; source reports
may mark FULL only without known loss/disconnection. Lack of events is not proof
that nothing happened. Models are supplied serialized data and a strict v2 schema;
raw proposal, validation and any future compilation must remain distinguishable.

## Physical erasure, backup and rollback

The DB owns 12 additional development tables across schema2–5; schema6 adds only
an index. v1 tables and execution state machines remain unchanged. Structured
state/binding/revision/index metadata is in SQL, bounded narrative/list payloads
in artifacts. `core_meta` holds only small operating markers.

Before erase, a locked external `.privacy.json` journal fsyncs opaque tombstones.
This includes the original DB and managed backups. Purge clears raw/derived/
record/revision payloads and hashes, removes lexical terms, uses secure_delete
and checks WAL truncation. A busy backup returns PENDING_BACKUP_PURGE and stays
pending until scrubbed. A live restored copy shares the current anchor; it cannot
ignore deletion because its DB snapshot is older. Startup re-applies tombstones
before reads, including after actual SIGKILL. Replay keeps remaining artifacts,
applies event projections/deletion intent, rebuilds the index and stays quarantined.

Keep the current privacy journal independently of old DB snapshots. Existing
continuity DB without that anchor is blocked. A move to a new physical host needs
an explicitly reviewed relocation of the **current** anchor and managed paths;
blindly copying an old directory is not a supported restore protocol. This release
tests offline managed copies, not real host migration or production identity
adoption. There is no destructive automatic downgrade. Retain a pre-upgrade dev
snapshot and use a compatible version in quarantine if rollback is needed.

No claim covers unregistered exports, privileged whole-disk rollback, provider
retention, arbitrary caller RAM or forensic SSD erasure. Journal capacity16MiB is
bounded; future scalable compaction must preserve the deletion frontier. Real
private ingress remains forbidden until privacy/restore/conversion review.

## Learning and remaining boundary

Reading result verification inspects actual locator content and binds the result
artifact digest. Experience and proposed lesson are separate. Current learning
supports only the registered missing-locator read rule; it is not free-form RL.
Tests check idempotent compilation, exact task scope, unchanged write target and
no authority fields. Reviewed activation is separate; stale/deleted support,
suspension and retirement prevent selection. No identity revision or permission
is learned. Fixture ablation changes the raw planned operation, not a secretly
patched response. General semantic transfer still requires real E12.

The candidate does not admit multiple live Goals, dispatch Actions, schedule
messages, import real memories, hand off owners or replace AstrBot. Existing
one_live_goal remains a later Phase B blocker, not something silently removed.
