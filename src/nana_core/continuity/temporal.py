"""Source-backed validity annotations, distinct from event/observation/record time."""
import json
from typing import Literal
from pydantic import Field,model_validator
from ..contracts import DTO,CoreError
from ..actions import OperatorAuthority
from ..storage import canonical
from .records import RecordService

class FactValidity(DTO):
    memory_id: str
    valid_from_us: int | None = Field(default=None,ge=0)
    valid_until_us: int | None = Field(default=None,ge=0)
    reference_time_us: int | None = Field(default=None,ge=0)
    @model_validator(mode='after')
    def interval(self):
        if self.valid_from_us is not None and self.valid_until_us is not None and self.valid_until_us<=self.valid_from_us:raise ValueError('invalid validity interval')
        return self

class TemporalFactView(DTO):
    memory_id: str
    event_time_us: int | None
    observed_time_us: int
    ingested_time_us: int
    reference_time_us: int | None
    valid_from_us: int | None
    valid_until_us: int | None
    validity: Literal['WITHIN','OUTSIDE','UNKNOWN']
    belief_status: Literal['CURRENT_AT_KNOWN_TIME','SUPERSEDED_AT_KNOWN_TIME','UNCERTAIN']
    source_record_id: str | None
    as_of_valid_us: int
    as_of_known_us: int
    derived: Literal[True] = True

class TemporalMemoryService:
    def __init__(self,store,authority):
        if store.schema_target<11 or not isinstance(authority,OperatorAuthority):raise CoreError('TEMPORAL_CONTROLLER_REQUIRED')
        self.store,self._authority,self.records=store,authority,RecordService(store)
    def declare(self,validity:FactValidity,*,support_memory_id,expected_revision,authority):
        if authority is not self._authority:raise CoreError('UNAUTHENTICATED_OPERATOR')
        target=self.records.memory.read(validity.memory_id);support=self.records.memory.read(support_memory_id)
        if support['scope']!=target['scope'] or support['authority']!='DIRECT' or support['epistemic_kind'] not in {'STATEMENT','OBSERVATION'} or FactValidity.model_validate_json(support['text'])!=validity:
            raise CoreError('VALIDITY_DIRECT_SOURCE_REQUIRED')
        old=self.store.db.execute("SELECT * FROM events WHERE kind='memory.validity_revision' AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(validity.memory_id,)).fetchone()
        prior=json.loads(old['data_json'])['data'] if old else None
        if expected_revision!=(prior['revision'] if prior else 0):raise CoreError('STALE_VALIDITY_REVISION')
        data={'target_id':validity.memory_id,'revision':expected_revision+1}
        with self.store.transaction('memory.validity_revision',data) as tx:
            data['record_id']=self.records.create(tx,kind='MEMORY_VALIDITY',scope=target['scope'],payload=validity.model_dump(mode='json'),memories=(validity.memory_id,support_memory_id))
        return data['record_id']
    def view(self,memory_id,*,scopes,privacy_classes,as_of_valid_us,as_of_known_us):
        self.store.ensure_privacy_current();head=self.store.one('memories',memory_id)
        if not head or head['scope'] not in scopes or head['privacy_class'] not in privacy_classes or head['lifecycle']=='DELETED' or head['ingested_time_us']>as_of_known_us:
            raise CoreError('TEMPORAL_MEMORY_UNAVAILABLE')
        self.records.memory.read(memory_id,include_inactive=True)
        source_record=None;validity=None
        for event in self.store.db.execute("SELECT * FROM events WHERE kind='memory.validity_revision' AND recorded_at_us<=? AND json_extract(data_json,'$.data.target_id')=? ORDER BY seq DESC LIMIT 1",(as_of_known_us,memory_id)):
            rid=json.loads(event['data_json'])['data']['record_id'];row=self.store.one('continuity_records',rid)
            if row['privacy_class'] not in privacy_classes or row['lifecycle']=='DELETED':raise CoreError('TEMPORAL_MEMORY_UNAVAILABLE')
            validity=FactValidity.model_validate_json(canonical(self.records.read(rid,include_history=True)['payload']));source_record=rid
        state='UNKNOWN'
        if validity:
            if (validity.valid_from_us is not None and as_of_valid_us<validity.valid_from_us) or (validity.valid_until_us is not None and as_of_valid_us>=validity.valid_until_us):state='OUTSIDE'
            elif validity.valid_from_us is not None and validity.valid_until_us is not None:state='WITHIN'
        replacement=self.store.one('memories',head['superseded_by']) if head['superseded_by'] else None
        belief='SUPERSEDED_AT_KNOWN_TIME' if replacement and replacement['ingested_time_us']<=as_of_known_us else 'UNCERTAIN' if head['assessment'] in {'DISPUTED','WITHDRAWN'} else 'CURRENT_AT_KNOWN_TIME'
        return TemporalFactView(memory_id=memory_id,event_time_us=head['event_time_us'],observed_time_us=head['observed_time_us'],ingested_time_us=head['ingested_time_us'],
            reference_time_us=validity.reference_time_us if validity else None,valid_from_us=validity.valid_from_us if validity else None,valid_until_us=validity.valid_until_us if validity else None,
            validity=state,belief_status=belief,source_record_id=source_record,as_of_valid_us=as_of_valid_us,as_of_known_us=as_of_known_us)
