"""Open, source-backed attention cues. Data, not Nana's will or authority."""
from typing import Literal
from pydantic import Field
from ...contracts import DTO,CoreError
from ..memory import MemoryService
from ..records import RecordService

Behavior = Literal['ACT','DEFER','WATCH','REFLECT','LEARN','EXPLORE','CREATE','MAINTAIN','CONTINUE_PROJECT','HONOR_COMMITMENT','SEEK_CAPABILITY','EXPRESS_OPINION','DISAGREE','SOCIALIZE','REST','WITHDRAW','IGNORE','STAY_SILENT','DO_NOTHING']


class ConcernCue(DTO):
    schema_version: Literal[1] = 1
    cue_kind: Literal['OPEN_LOOP','OPPORTUNITY','DISCOVERY','CONSTRAINT','LOAD_STATE']
    motivation_source: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,63}$')
    topic_key: str = Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    possible_behaviors: tuple[Behavior, ...] = Field(default=('WATCH',),min_length=1,max_length=8)
    prohibited_behaviors: tuple[Behavior, ...] = Field(default=(),max_length=16)
    resource_ref: str | None = Field(default=None,pattern=r'^synthetic://[a-zA-Z0-9/._:-]{1,200}$')
    resource_class: Literal['ORDINARY','PASSWORD','CREDENTIAL','PAYMENT','OTHER_PERSON_SECRET','UNKNOWN'] = 'UNKNOWN'
    availability: Literal['AVAILABLE','BUSY','UNKNOWN'] = 'UNKNOWN'
    cognitive_load: Literal['LOW','OCCUPIED','HIGH'] = 'LOW'
    urgency: Literal['NONE','LOW','RELEVANT','HIGH'] = 'LOW'
    not_before_us: int = Field(default=0,ge=0)
    valid_until_us: int | None = Field(default=None,ge=0)


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
