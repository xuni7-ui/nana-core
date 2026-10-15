"""C-stage subject contracts. No executable authority and no real ingress switch."""
from typing import Literal
from pydantic import Field, model_validator
from ...contracts import DTO
from .social import SocialInteractionProposal
from .opportunities import Behavior,SyntheticActionProposal

Key = str
Level = Literal['NONE', 'LOW', 'RELEVANT', 'HIGH']
DAY_US = 86_400_000_000
MAX_PENDING = 8
INTENTION_TTL_US = 7 * DAY_US


class PreferenceSignal(DTO):
    kind: Literal['PREFERENCE', 'SELF_BELIEF'] = 'PREFERENCE'
    topic: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    direction: Literal['SUPPORT', 'COUNTER']
    interpretation: str = Field(min_length=1, max_length=512)


class SubjectInput(DTO):
    schema_version: Literal[1] = 1
    domain: Literal['SYNTHETIC_ONLY'] = 'SYNTHETIC_ONLY'
    source_key: str = Field(pattern=r'^synthetic[.:_-][A-Za-z0-9._:-]{1,128}$')
    kind: Literal['INTERACTION', 'PROJECT', 'PLAY', 'OUTCOME', 'WAKE', 'RELATIONSHIP', 'REFLECTION']
    origin: Literal['USER', 'ENVIRONMENT', 'SELF_WAKE']
    entity_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    scope: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    occurred_at_us: int | None = Field(default=None, ge=0)
    observed_at_us: int = Field(ge=0)
    text: str | None = Field(default=None, max_length=8192)
    privacy_class: Literal['PUBLIC', 'PROJECT', 'PERSONAL', 'SECRET'] = 'PERSONAL'
    retention: Literal['MAY_REMEMBER', 'DO_NOT_REMEMBER'] = 'MAY_REMEMBER'
    source_memory_ids: tuple[str, ...] = Field(default=(), max_length=32)
    topic: str | None = Field(default=None, pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    novelty: Level = 'LOW'
    significance: Level = 'LOW'
    risk: Level = 'NONE'
    urgency: Level = 'NONE'
    uncertainty: Level = 'LOW'
    proposed_method: str | None = Field(default=None, max_length=128)
    constraint_memory_ids: tuple[str, ...] = Field(default=(), max_length=16)
    preference_signal: PreferenceSignal | None = None
    relationship_kind: Literal['SHARED_HISTORY', 'SHARED_PROJECT', 'SHARED_JOKE', 'NORM', 'BOUNDARY', 'CONFLICT', 'REPAIR', 'TRUST', 'COMMITMENT'] | None = None
    task_class: str | None = Field(default=None, pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    reflection_experience_id: str | None = None
    result_for_intention_id: str | None = None
    observed_availability: Literal['AVAILABLE','BUSY','UNKNOWN'] | None = None

    @model_validator(mode='after')
    def provenance(self):
        if self.kind == 'WAKE':
            if self.origin != 'SELF_WAKE' or self.text or self.preference_signal or self.relationship_kind:
                raise ValueError('wake cannot manufacture experience')
        elif self.origin == 'SELF_WAKE':
            raise ValueError('self wake cannot claim external occurrence')
        if self.result_for_intention_id and (self.origin!='ENVIRONMENT' or self.kind!='OUTCOME' or not self.text):
            raise ValueError('synthetic intention outcome requires an observed world result')
        if self.preference_signal and not self.text:
            raise ValueError('preference signal requires an observed occurrence')
        if self.kind == 'REFLECTION':
            raise ValueError('reflection must reference an existing experience via SubjectLoop.reflect')
        if self.relationship_kind and not self.text:
            raise ValueError('relationship update requires a sourced occurrence')
        if self.relationship_kind and self.kind not in {'RELATIONSHIP', 'PROJECT', 'INTERACTION'}:
            raise ValueError('relationship occurrence kind mismatch')
        return self


class Appraisal(DTO):
    novelty: Level
    goal_relevance: Level
    relationship_relevance: Level
    self_relevance: Level
    unfinished_tension: Level
    interest_relevance: Level
    risk: Level
    conflict: Level
    urgency: Level
    expected_value: Level
    uncertainty: Level
    privacy_relevance: Level
    source_ids: tuple[str, ...]
    reasons: tuple[str, ...]


class Motivation(DTO):
    source: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    strength: Literal['AVAILABLE','RELEVANT','PRESSING']
    source_ids: tuple[str, ...]
    inhibited_by: tuple[str, ...] = ()


class Judgment(DTO):
    stance: Literal['AGREE','PARTIAL_AGREE','DISAGREE','ALTERNATIVE','IGNORE','WATCH','REMEMBER','ASK','THINK_MORE','DEFER','REFLECT']
    reason: str = Field(min_length=1, max_length=1024)
    source_ids: tuple[str, ...]
    selected_method: str | None = None
    lesson_ids: tuple[str, ...] = ()


class Intention(DTO):
    kind: Literal['NO_ACTION','SOCIAL_INTERACTION','MEMORY_CANDIDATE','REFLECTION','GOAL_CANDIDATE','ACTION_PROPOSAL','WAIT','EXPLORE','DISAGREE']
    purpose: str = Field(min_length=1, max_length=512)
    slot_key: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    source_ids: tuple[str, ...]
    self_generated: bool
    behavior: Behavior | None = None


class DeliberationFrame(DTO):
    """Pre-model appraisal/attention, not model truth or an adopted intention."""
    derived: Literal[True] = True
    subject_event_id: str
    scope: str
    appraisal: Appraisal
    motivations: tuple[Motivation, ...]
    attention: Literal['FOCUS_NOW','BACKGROUND_WATCH','DEFER','IGNORE','RECALL_LATER']
    source_memory_ids: tuple[str, ...]
    source_record_ids: tuple[str, ...]


class DeliberationTrace(DTO):
    model_descriptor: str = Field(min_length=1, max_length=128)
    context_digest: str
    raw_proposal_json: str = Field(max_length=32768)
    source_kind: Literal['MODEL_PROPOSAL_NOT_TRUTH'] = 'MODEL_PROPOSAL_NOT_TRUTH'


class CycleResult(DTO):
    cycle_id: str
    event_id: str
    revision: int
    admission: Literal['KEEP','MERGE','TEMPORARY','IGNORE','FORGET_LATER']
    appraisal: Appraisal
    motivations: tuple[Motivation, ...]
    attention: Literal['FOCUS_NOW','BACKGROUND_WATCH','DEFER','IGNORE','RECALL_LATER']
    judgment: Judgment
    intention: Intention
    intention_id: str | None
    goal_candidate_id: str | None
    barrier: Literal['NO_ACTION','SHADOW_BLOCKED']
    record_id: str | None
    replayed: bool = False
    deliberation: DeliberationTrace | None = None
    social_proposal: SocialInteractionProposal | None = None
    action_proposal: SyntheticActionProposal | None = None


class WakeCondition(DTO):
    kind: Literal['INCOMING_EVENT','TIME_TRIGGER','GOAL_TRIGGER','ANOMALY','RELATIONSHIP_TRIGGER','SELF_TRIGGER','REFLECTION_TRIGGER','DEVICE_TRIGGER','ENVIRONMENT_CHANGE']
    due_at_us: int = Field(ge=0)
    source_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    dedupe_key: str = Field(min_length=1, max_length=128)


class StandingDelegation(DTO):
    """Future E contract; C never registers or activates one."""
    delegation_id: str
    subject: str
    capability: str = Field(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9._:-]+$')
    resource_scope: tuple[str, ...] = Field(min_length=1, max_length=16)
    operations: tuple[str, ...] = Field(min_length=1, max_length=16)
    risk_ceiling: Literal['READ_ONLY','REVERSIBLE','EXPLICIT_ONLY']
    privacy_scope: tuple[Literal['PUBLIC','PROJECT','PERSONAL'], ...]
    issued_at_us: int = Field(ge=0)
    expires_at_us: int = Field(ge=0)
    revoked: bool = False
    provenance: str = Field(min_length=1, max_length=256)

    @model_validator(mode='after')
    def exact(self):
        if self.expires_at_us <= self.issued_at_us or any('*' in s for s in (*self.resource_scope, *self.operations)):
            raise ValueError('exact, finite delegation required')
        return self
