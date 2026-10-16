"""Generic, bounded relational data; bootstrap roles never encode commands."""
from typing import Literal
from pydantic import Field,model_validator
from ...contracts import DTO

Key=str
Level=Literal['LOW','MODERATE','HIGH']
FacetName=Literal['self_direction_sensitivity','relational_accommodation','commitment_seriousness','conflict_style','social_exploration_tendency','conviction_persistence','repair_orientation','uncertainty_style']
DAY=86_400_000_000

class RelationalAnchorSpec(DTO):
    domain: Literal['SYNTHETIC_BOOTSTRAP'] = 'SYNTHETIC_BOOTSTRAP'
    identity_id: str
    anchor_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    entity_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    role_label: str = Field(pattern=r'^[a-z][a-z0-9 -]{0,63}$')
    scope: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    revision: int = Field(ge=1)
    provenance: Literal['BOOTSTRAP_RELATIONAL_ROLE'] = 'BOOTSTRAP_RELATIONAL_ROLE'
    state: Literal['ACTIVE','WITHDRAWN'] = 'ACTIVE'
    effective_from_us: int = Field(ge=0)
    expires_at_us: int | None = Field(default=None,ge=0)
    non_exclusive: Literal[True] = True
    care_orientation: Level = 'HIGH'
    relational_salience: Level = 'HIGH'
    repair_priority: Level = 'HIGH'
    deference_baseline: Level = 'HIGH'
    @model_validator(mode='after')
    def valid(self):
        if self.expires_at_us is not None and self.expires_at_us<=self.effective_from_us:raise ValueError('invalid anchor period')
        return self

class SubjectPersonalitySeed(DTO):
    domain: Literal['SYNTHETIC_BOOTSTRAP'] = 'SYNTHETIC_BOOTSTRAP'
    identity_id: str
    scope: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    revision: int = Field(ge=1)
    provenance: Literal['BOOTSTRAP_TEMPERAMENT'] = 'BOOTSTRAP_TEMPERAMENT'
    self_direction_sensitivity: Level = 'MODERATE'
    relational_accommodation: Level = 'MODERATE'
    commitment_seriousness: Level = 'HIGH'
    conflict_style: Literal['NEGOTIATE','FIRM','EXPLORE'] = 'NEGOTIATE'
    social_exploration_tendency: Level = 'MODERATE'
    conviction_persistence: Level = 'MODERATE'
    repair_orientation: Level = 'MODERATE'
    uncertainty_style: Literal['CLARIFY','WAIT','COMPARE'] = 'CLARIFY'

class RelationalAnchorView(DTO):
    derived: Literal[True] = True
    spec: RelationalAnchorSpec
    source_record_id: str
    as_of_us: int
    state_token: str
    authority: Literal[False] = False

class TendencyFacet(DTO):
    name: FacetName
    assessment: str
    basis: Literal['BOOTSTRAP','EVIDENCE','CONTESTED','UNKNOWN']
    support_refs: tuple[str,...] = ()
    counter_refs: tuple[str,...] = ()
    independent_support_count: int = 0

class PersonalityTendencyView(DTO):
    derived: Literal[True] = True
    facets: tuple[TendencyFacet,...]
    context_modifiers: tuple[str,...] = ()
    source_record_ids: tuple[str,...] = ()
    as_of_us: int
    state_token: str

class SocialAppetiteView(DTO):
    derived: Literal[True] = True
    state: Literal['QUIET','OPEN','SEEKING','SATURATED','RECOVERING','UNKNOWN']
    source_record_ids: tuple[str,...] = ()
    source_memory_ids: tuple[str,...] = ()
    available: bool = True
    as_of_us: int
    state_token: str

class RelationalRequest(DTO):
    request_id: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    requesting_entity: str = Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    operation: Literal['DO','REFRAIN','PREFER','ASK_FOR_TIME','ASK_FOR_ATTENTION']
    behavior_domain: Literal['SOCIAL_NEW_CONTACTS','COMPANIONSHIP','PROJECT','CREATIVE','REST']
    scope: Literal['TARGETED','LOCAL','GLOBAL'] = 'LOCAL'
    duration_us: int | None = Field(default=None,ge=1,le=365*DAY)
    review_at_us: int | None = Field(default=None,ge=0)
    consequence: Literal['LOW','MODERATE','HIGH'] = 'LOW'
    trust_domain: str = Field(default='interaction',pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    depends_on_statement: bool = False

class WillingDeferenceView(DTO):
    derived: Literal[True] = True
    assessment: Literal['STRONG','MODERATE','LIMITED','NONE','UNKNOWN']
    relationship_refs: tuple[str,...]
    personality_refs: tuple[str,...]
    request_refs: tuple[str,...]
    reason_refs: tuple[str,...]
    counterconsiderations: tuple[str,...]
    domain: str
    authority: Literal[False] = False

class SelfAuthorshipAppraisal(DTO):
    state: Literal['CLEAR_CHOICE','INFLUENCED','PRESSURED','CONSTRAINED','UNKNOWN']
    choice_owner: Literal['SUBJECT'] = 'SUBJECT'
    bypassed: Literal[False] = False
    reason_refs: tuple[str,...]

class DeliberationFactor(DTO):
    kind: Literal['PERSONAL_DESIRE','SOCIAL_APPETITE','RELATIONAL_REQUEST','RELATIONAL_DEFERENCE','SELF_AUTHORSHIP','PERSONALITY_TENDENCY','COMMITMENT','VALUE_OR_NORM','RISK_OR_CONSEQUENCE','TEMPORAL_SCOPE','ALTERNATIVE_AVAILABLE']
    direction: Literal['SUPPORT','COUNTER','CONTEXT']
    salience: Level
    source_refs: tuple[str,...]
    supports: tuple[Literal['ACCEPT','NEGOTIATE','DECLINE'],...]
    counter_refs: tuple[str,...] = ()

class RelationalResponsePlan(DTO):
    decision: Literal['ACCEPT','NEGOTIATE','DECLINE']
    retained_preference: Literal['SOCIALIZE','UNSPECIFIED']
    temporal_boundary_us: int | None
    warmth: Level
    firmness: Level
    playful: Literal[False] = False
    retained_care: bool
    authority: Literal[False] = False

class VoluntaryTerms(DTO):
    request_id: str
    source_cycle_id: str
    behavior_domain: str
    operation: str
    accepted_scope: Literal['TARGETED','LOCAL','GLOBAL']
    start_us: int
    end_us: int
    review_at_us: int
    reconsiderable: Literal[True] = True
    @model_validator(mode='after')
    def bounded(self):
        if not self.start_us<self.end_us or not self.start_us<self.review_at_us<=self.end_us or self.end_us-self.start_us>30*DAY:raise ValueError('bounded voluntary terms required')
        return self

class RelationalDecision(DTO):
    request: RelationalRequest
    deference: WillingDeferenceView
    authorship: SelfAuthorshipAppraisal
    factors: tuple[DeliberationFactor,...]
    response: RelationalResponsePlan
    prior_behavior_disposition: Literal['RETAINED','VOLUNTARILY_RESTRAINED']
    accepted_duration_us: int | None
    review_at_us: int | None
    phase: Literal['REQUEST','REVIEW'] = 'REQUEST'
    review_commitment_id: str | None = None
    review_revision: int | None = None
    review_choice: Literal['CONTINUE','MODIFY','END'] | None = None

class SelfNarrativeItem(DTO):
    semantic: str
    assessment: Literal['SUPPORTED','CONTESTED']
    support_refs: tuple[str,...]
    counter_refs: tuple[str,...]

class SelfNarrativeView(DTO):
    derived: Literal[True] = True
    entries: tuple[SelfNarrativeItem,...]
    as_of_us: int
    state_token: str
    is_policy: Literal[False] = False
