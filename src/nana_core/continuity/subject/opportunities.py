"""Open, source-backed attention cues. Data, not Nana's will or authority."""
from typing import Literal
from pydantic import Field,model_serializer
from ...contracts import DTO,CoreError
from ..memory import MemoryService
from ..records import RecordService

Behavior = Literal['ACT','DEFER','WATCH','REFLECT','LEARN','EXPLORE','CREATE','MAINTAIN','CONTINUE_PROJECT','HONOR_COMMITMENT','SEEK_CAPABILITY','EXPRESS_OPINION','DISAGREE','SOCIALIZE','REST','WITHDRAW','IGNORE','STAY_SILENT','DO_NOTHING']


class LearningValue(DTO):
    """Sourced assessment factors, not a command or numeric reward."""
    goal_value: Literal['LOW','RELEVANT','HIGH']
    future_reuse: Literal['LOW','RELEVANT','HIGH']
    interest: Literal['LOW','RELEVANT','HIGH']='LOW'
    relationship_relevance: Literal['LOW','RELEVANT','HIGH']='LOW'
    alternative: Literal['AVAILABLE','UNAVAILABLE','UNKNOWN']='UNKNOWN'
    time_compute_cost: Literal['LIGHT','HEAVY']='LIGHT'
    risk: Literal['LOW','HIGH']='LOW'


class OpportunityAssessment(DTO):
    value: Literal['LOW','RELEVANT','HIGH']
    novelty: Literal['REPEATED','NEW']


class ShareAssessment(DTO):
    relational_relevance:Literal['LOW','RELEVANT','HIGH']='LOW'
    novelty:Literal['NEW','REPEATED']='NEW'
    affect_relevance:Literal['LOW','RELEVANT']='LOW'
    urgency:Literal['LOW','HIGH']='LOW'
    interruption_cost:Literal['LIGHT','HEAVY']='LIGHT'
    recent_delivery_frequency:Literal['LOW','HIGH','UNKNOWN']='UNKNOWN'
    user_preference:Literal['ALLOW','DECLINED','UNKNOWN']='UNKNOWN'
    desire:Literal['PRESENT']='PRESENT'


class ConcernCue(DTO):
    schema_version: Literal[1] = 1
    cue_kind: Literal['OPEN_LOOP','OPPORTUNITY','DISCOVERY','CONSTRAINT','LOAD_STATE']
    motivation_source: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    program_id: str | None = Field(default=None,pattern=r'^[a-z][a-z0-9_-]{0,31}\.[a-z][a-z0-9._-]{0,95}$')
    topic_key: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    possible_behaviors: tuple[Behavior, ...] = Field(default=(),max_length=8)
    required_preference_id: str | None = None
    prohibited_behaviors: tuple[Behavior, ...] = Field(default=(),max_length=16)
    resource_ref: str | None = Field(default=None,pattern=r'^synthetic://[a-zA-Z0-9/._:-]{1,200}$')
    resource_class: Literal['ORDINARY','PASSWORD','CREDENTIAL','PAYMENT','OTHER_PERSON_SECRET','UNKNOWN'] = 'UNKNOWN'
    availability: Literal['AVAILABLE','BUSY','UNKNOWN'] = 'UNKNOWN'
    behavior_domain: Literal['SOCIAL_NEW_CONTACTS','COMPANIONSHIP','PROJECT','CREATIVE','REST'] | None = None
    cognitive_load: Literal['LOW','OCCUPIED','HIGH'] = 'LOW'
    # Demand of a possible activity, not evidence of current fatigue/load.
    attention_demand: Literal['LIGHT','HEAVY'] = 'LIGHT'
    urgency: Literal['NONE','LOW','RELEVANT','HIGH'] = 'LOW'
    not_before_us: int = Field(default=0,ge=0)
    valid_until_us: int | None = Field(default=None,ge=0)
    learning_value: LearningValue | None = None
    share_assessment: ShareAssessment | None = None
    opportunity_assessment: OpportunityAssessment | None = None
    @model_serializer(mode='wrap')
    def compatible_wire(self,handler):
        value=handler(self)
        if self.learning_value is None:value.pop('learning_value',None)
        if self.share_assessment is None:value.pop('share_assessment',None)
        if self.opportunity_assessment is None:value.pop('opportunity_assessment',None)
        if self.attention_demand=='LIGHT':value.pop('attention_demand',None)
        return value


def cues_from(store,memory_ids,*,scope,privacy_classes):
    memory=MemoryService(store)
    out=[]
    for mid in dict.fromkeys(memory_ids):
        row=store.one('memories',mid)
        if not row or row['scope']!=scope or row['privacy_class'] not in privacy_classes:continue
        try:item=memory.read(mid)
        except CoreError:continue
        if item['predicate_key'] is None or not item['predicate_key'].startswith('concern.'):
            continue
        try:cue=ConcernCue.model_validate_json(item['text'])
        except ValueError:continue
        if cue.valid_until_us is not None and store.clock.utc_now_us()>=cue.valid_until_us:continue
        if store.clock.utc_now_us()<cue.not_before_us:continue
        # A model-derived cue remains a proposal/hypothesis with references. It
        # cannot be a self-certified norm or permission.
        if cue.cue_kind=='CONSTRAINT' and (item['authority']!='DIRECT' or item['epistemic_kind'] not in {'OBSERVATION','STATEMENT'}):continue
        out.append((mid,cue))
    return tuple(out)


class SyntheticActionProposal(DTO):
    domain: Literal['SYNTHETIC_ONLY'] = 'SYNTHETIC_ONLY'
    capability: Literal['synthetic.resource.read'] = 'synthetic.resource.read'
    operation: Literal['READ'] = 'READ'
    resource_ref: str = Field(pattern=r'^synthetic://[a-zA-Z0-9/._:-]{1,200}$')
    resource_class: Literal['ORDINARY','PASSWORD','CREDENTIAL','PAYMENT','OTHER_PERSON_SECRET','UNKNOWN']
    source_memory_ids: tuple[str,...]
    execution_authority: Literal[False] = False


# Initial C interpretation policy, not a Runtime registry or personality meter.
# Source proposals can add options; C still inhibits by norms/load/uncertainty.
DIRECTIONS = {
    'PROJECT_COMPLETION': ('CONTINUE_PROJECT',), 'COMMITMENT': ('HONOR_COMMITMENT',),
    'CAPABILITY_GAP': ('SEEK_CAPABILITY',), 'CREATIVE_INTEREST': ('CREATE',),
    'MAINTENANCE': ('MAINTAIN',), 'LONG_TERM_GOAL': ('MAINTAIN',),
    'SELF_DEVELOPMENT': ('LEARN',), 'REST': ('REST',),
    'CURIOSITY': ('EXPLORE','WATCH'), 'UNRESOLVED_QUESTION': ('EXPLORE','WATCH'),
    'OPPORTUNITY': ('EXPLORE','WATCH'),
    'RELATIONSHIP': ('SOCIALIZE','WATCH'), 'NOVELTY': ('WATCH',),
}


def directions(cue):
    if cue.possible_behaviors:return cue.possible_behaviors
    return DIRECTIONS.get(cue.motivation_source,('WATCH',))
