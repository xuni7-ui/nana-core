"""Typed, bounded semantic contracts. No authority is serializable here."""
from typing import Literal
from pydantic import Field
from ...contracts import DTO
from ..recurrence import RecurrenceSpec
from ..commitments import CommitmentCandidate

NormativeDisposition = Literal['ENDORSED','RESTRAINED','UNDECIDED']
DispositionCode = Literal['SUBJECT_ENDORSED','SUBJECT_RESTRAINED','SUBJECT_DEFERRED','SUBJECT_DROPPED','MANAGER_BLOCKED','MANAGER_UNKNOWN','REALIZATION_ELIGIBLE']
DisclosureMode = Literal['DISCLOSE_BEFORE','DISCLOSE_AFTER','DISCLOSE_WHEN_ASKED','WITHHOLD_UNTIL_REVEAL','DECLINE_TO_DISCLOSE','STAY_SILENT']
BehaviorPhase = Literal['PLANNED','MANAGER_BLOCKED','ACTION_BLOCKED','ATTEMPTED','UNKNOWN','VERIFIED_EFFECT']

class RealizationTarget(DTO):
    capability: str = Field(pattern=r'^[a-z][a-z0-9._-]{1,95}$')
    operation: Literal['READ','WRITE','DELETE','CONTACT']
    resource: str = Field(pattern=r'^(?:synthetic|project|hands)://[A-Za-z0-9/._:-]{1,160}$')
    resource_class: Literal['ORDINARY','PASSWORD','CREDENTIAL','PAYMENT','OTHER_PERSON_SECRET','UNKNOWN'] = 'UNKNOWN'

class DisclosureRequest(DTO):
    topic: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    asked: bool = False
    intention_id: str | None = None
    action_id: str | None = None

class DisclosureDecision(DTO):
    derived: Literal[True] = True
    mode: DisclosureMode
    phase: BehaviorPhase
    topic: str
    source_memory_ids: tuple[str,...] = ()
    source_record_ids: tuple[str,...] = ()
    source_event_ids: tuple[str,...] = ()
    reveal_at_us: int | None = None
    reason: str
    assertions: tuple[str,...] = ()
    delivery_authority: Literal[False] = False

class SubjectEvaluation(DTO):
    normative: NormativeDisposition
    disposition: DispositionCode
    considered: bool
    wanted: bool
    reason_refs: tuple[str,...]

class SocialExpectationSpec(DTO):
    topic: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    expectation: Literal['OPEN','ORDINARILY_VISIBLE','CONTEXT_SENSITIVE','EXPLICITLY_PRIVATE','EXPLICITLY_FORBIDDEN','UNKNOWN']
    domain: str = Field(default='interaction',pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    timing: Literal['BEFORE','AFTER','ON_REQUEST','DEFER_UNTIL'] = 'ON_REQUEST'
    reveal_at_us: int | None = Field(default=None,ge=0)
    resource_ref: str | None = Field(default=None,pattern=r'^(?:synthetic|project|hands)://[A-Za-z0-9/._:-]{1,160}$')

class DispositionView(DTO):
    record_id: str
    cycle_id: str
    intention_id: str | None
    intention_revision: int
    stage: Literal['SUBJECT','MANAGER','REALIZATION']
    code: DispositionCode
    normative: NormativeDisposition
    wanted: bool
    reason_refs: tuple[str,...]
    at_us: int

class RelationshipDetails(DTO):
    """Source interpretation metadata, never a direct facet assignment."""
    domain: str = Field(default='interaction',pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    target_event_id: str | None = None
    supersedes_event_id: str | None = None
    valid_until_us: int | None = Field(default=None,ge=0)
    trust_breach: bool = False
    boundary_state: Literal['ASSERTED','WITHDRAWN'] = 'ASSERTED'
    social_expectation: SocialExpectationSpec | None = None

class RelationshipFacet(DTO):
    domain: str
    assessment: str
    support_refs: tuple[str,...]
    counter_refs: tuple[str,...]
    coverage: Literal['FULL','PARTIAL','UNKNOWN']
    confidence: Literal['SOURCE_BACKED','CONTESTED','INSUFFICIENT']

class RelationshipInfluenceView(DTO):
    derived: Literal[True] = True
    entity_id: str
    scope: str
    as_of_us: int
    state_token: str
    familiarity: RelationshipFacet
    trust: tuple[RelationshipFacet,...]
    care_salience: RelationshipFacet
    boundary_salience: RelationshipFacet
    repair_tension: RelationshipFacet
    interaction_latitude: RelationshipFacet
    shared_commitment_relevance: RelationshipFacet
    source_record_ids: tuple[str,...]

class SocialPrivacyExpectation(DTO):
    derived: Literal[True] = True
    scope: str
    topic: str
    assessment: Literal['OPEN','ORDINARILY_VISIBLE','CONTEXT_SENSITIVE','EXPLICITLY_PRIVATE','EXPLICITLY_FORBIDDEN','UNKNOWN']
    support_refs: tuple[str,...]
    counter_refs: tuple[str,...] = ()
    as_of_us: int
    state_token: str

class PositiveRequest(DTO):
    task_class: Literal['REMINDER','PROJECT','CONTACT','MAINTENANCE']
    description: str = Field(min_length=1,max_length=1024)
    due_at_us: int | None = Field(default=None,ge=0)
    recurrence: RecurrenceSpec | None = None

class RequestDecision(DTO):
    decision: Literal['ACCEPT','NEGOTIATE','DECLINE']
    reason: str
    source_refs: tuple[str,...]
    candidate: CommitmentCandidate | None = None
