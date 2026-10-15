"""Typed, bounded semantic contracts. No authority is serializable here."""
from typing import Literal
from pydantic import Field
from ...contracts import DTO

NormativeDisposition = Literal['ENDORSED','RESTRAINED','UNDECIDED']
DispositionCode = Literal['SUBJECT_ENDORSED','SUBJECT_RESTRAINED','SUBJECT_DEFERRED','SUBJECT_DROPPED','MANAGER_BLOCKED','MANAGER_UNKNOWN','REALIZATION_ELIGIBLE']
DisclosureMode = Literal['DISCLOSE_BEFORE','DISCLOSE_AFTER','DISCLOSE_WHEN_ASKED','WITHHOLD_UNTIL_REVEAL','DECLINE_TO_DISCLOSE','STAY_SILENT']
BehaviorPhase = Literal['PLANNED','MANAGER_BLOCKED','ACTION_BLOCKED','ATTEMPTED','UNKNOWN','VERIFIED_EFFECT']

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
