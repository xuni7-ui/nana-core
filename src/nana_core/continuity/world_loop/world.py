"""Persistent, temporal, evidence-dependent beliefs in the existing Store.

These are beliefs about the world, not another source of truth. Revision headers
are queryable; erasable values and supporting observations remain in RecordService.
"""
from typing import Literal,Any
from pydantic import Field,model_validator
from ...contracts import DTO,CoreError
from ...storage import canonical,digest,uid
from ..records import RecordService
from ..open_agency.world import bounded_data

class SourcedClaim(DTO):
    entity_id:str=Field(pattern=r'^[A-Za-z0-9._:-]{1,128}$')
    predicate:str=Field(pattern=r'^[a-z][a-z0-9._:-]{0,95}$')
    value:Any
    kind:Literal['RAW_OBSERVATION','INTERPRETED','INFERENCE','MODEL_BELIEF','VERIFIED_RESULT','USER_CLAIM','HISTORICAL']
    valid_from_us:int=Field(ge=0)
    valid_until_us:int|None=Field(default=None,ge=0)
    confidence:float=Field(default=0.,ge=0.,le=1.)
    corrects:str|None=None
    @model_validator(mode='after')
    def bounded(self):
        bounded_data(self.value)
        if self.valid_until_us is not None and self.valid_until_us<=self.valid_from_us:raise ValueError('invalid world interval')
        return self

class WorldBeliefView(DTO):
    entity_id:str
    predicate:str
    state:Literal['SUPPORTED_BELIEF','CONFLICT','UNKNOWN']
    alternatives:tuple[dict,...]
    support_records:tuple[str,...]
    as_of_valid_us:int
    as_of_known_us:int
    projection:Literal[True]=True

class WorldModel:
    def __init__(self,store,*,scopes,privacy_classes):
        if store.schema_target<13:raise CoreError('WORLD_SCHEMA_REQUIRED')
        self.store,self.scopes,self.privacy=store,tuple(scopes),tuple(privacy_classes);self.records=RecordService(store)
    def ingest(self,source_memory_id):
        memory=self.records.memory.read(source_memory_id)
        if memory['scope'] not in self.scopes or memory['privacy_class'] not in self.privacy:raise CoreError('WORLD_PRIVACY_DENIED')
        import json
        try:claim=SourcedClaim.model_validate_json(canonical(json.loads(memory['text'])['world_claim']))
        except (ValueError,KeyError,TypeError):raise CoreError('WORLD_SOURCED_CLAIM_REQUIRED') from None
        if not self.store.one('entities',claim.entity_id):raise CoreError('WORLD_ENTITY_UNBOUND')
        source_kind=memory['source_provenance']['source_kind']
        if (claim.kind=='VERIFIED_RESULT' and source_kind!='SYSTEM_VERIFICATION') or (claim.kind=='USER_CLAIM' and source_kind!='USER_STATEMENT') or (source_kind=='MODEL_DERIVATION' and claim.kind not in {'MODEL_BELIEF','INFERENCE','INTERPRETED'}):raise CoreError('WORLD_EPISTEMIC_ESCALATION')
        if claim.valid_from_us>self.store.clock.utc_now_us():
            # Expected future events are explicitly beliefs, not observations.
            if claim.kind in {'RAW_OBSERVATION','VERIFIED_RESULT'}:raise CoreError('WORLD_FUTURE_OBSERVATION')
        key=digest([source_memory_id,claim.model_dump(mode='json')])
        old=self.store.db.execute("SELECT b.belief_id FROM world_beliefs b JOIN continuity_records r ON b.record_id=r.record_id WHERE r.target_id=?",(key,)).fetchone()
        if old:return old[0]
        previous=self.store.db.execute('SELECT * FROM world_beliefs WHERE entity_id=? AND predicate_key=? ORDER BY revision DESC LIMIT 64',(claim.entity_id,claim.predicate)).fetchall()
        replaced=self.store.one('world_beliefs',claim.corrects) if claim.corrects else None
        if claim.corrects and (not replaced or replaced['entity_id']!=claim.entity_id or replaced['predicate_key']!=claim.predicate or source_kind=='MODEL_DERIVATION' or memory['authority']!='DIRECT'):raise CoreError('WORLD_CORRECTION_AUTHORITY_REQUIRED')
        state='CURRENT';conflicts=[]
        for p in previous:
            head=self.store.one('continuity_records',p['record_id'])
            if head['scope']!=memory['scope']:raise CoreError('WORLD_SCOPE_COLLISION')
            if p['state'] not in {'CURRENT','CONFLICT'} or p['belief_id']==claim.corrects:continue
            try:body=self.records.read(p['record_id'])['payload']['claim']
            except CoreError:continue
            overlaps=(p['valid_until_us'] is None or p['valid_until_us']>claim.valid_from_us) and (claim.valid_until_us is None or claim.valid_until_us>p['valid_from_us'])
            if overlaps and digest(body['value'])!=digest(claim.value):conflicts.append(p)
        if conflicts:state='CONFLICT'
        bid=uid();now=self.store.clock.utc_now_us()
        with self.store.transaction('world.belief_revision',{'belief_id':bid,'revision':previous[0]['revision']+1 if previous else 1}) as tx:
            # Corrections reference the opaque old ID, but erasure of old evidence
            # must not destroy independent new evidence or resurrect the old claim.
            rid=self.records.create(tx,kind='WORLD_BELIEF',scope=memory['scope'],payload={'claim':claim.model_dump(mode='json'),'source_memory_id':source_memory_id,'belief_not_truth':True},memories=(source_memory_id,),target_id=key)
            tx.put('world_beliefs',{'belief_id':bid,'record_id':rid,'entity_id':claim.entity_id,'predicate_key':claim.predicate,'revision':previous[0]['revision']+1 if previous else 1,'epistemic_kind':claim.kind,'state':state,'valid_from_us':claim.valid_from_us,'valid_until_us':claim.valid_until_us,'known_at_us':now,'replaces':claim.corrects})
            if replaced:tx.update('world_beliefs',replaced['belief_id'],state='SUPERSEDED')
            for p in conflicts:tx.update('world_beliefs',p['belief_id'],state='CONFLICT')
        return bid
    def view(self,entity_id,predicate,*,valid_at_us=None,known_at_us=None):
        now=self.store.clock.utc_now_us();valid=now if valid_at_us is None else valid_at_us;known=now if known_at_us is None else known_at_us
        rows=self.store.db.execute('SELECT * FROM world_beliefs WHERE entity_id=? AND predicate_key=? AND known_at_us<=? ORDER BY revision DESC LIMIT 65',(entity_id,predicate,known)).fetchall()
        alternatives=[];supports=[];unknown=len(rows)>64
        replaced={r['replaces'] for r in rows if r['replaces']}
        for row in rows:
            if row['belief_id'] in replaced or row['valid_from_us']>valid or (row['valid_until_us'] is not None and row['valid_until_us']<=valid):continue
            head=self.store.one('continuity_records',row['record_id'])
            if head['scope'] not in self.scopes or head['privacy_class'] not in self.privacy or head['lifecycle']!='ACTIVE' or not self.records.current_support(row['record_id']):unknown=True;continue
            payload=self.records.read(row['record_id'])['payload']
            alternatives.append({'belief_id':row['belief_id'],'revision':row['revision'],'kind':row['epistemic_kind'],'value':payload['claim']['value'],'confidence':payload['claim']['confidence'],'event_time_us':self.records.memory.read(payload['source_memory_id'])['event_time_us'],'valid_from_us':row['valid_from_us'],'known_at_us':row['known_at_us']});supports.append(row['record_id'])
        if unknown:alternatives=[];supports=[]
        state='UNKNOWN' if unknown or not alternatives else 'CONFLICT' if len({digest(a['value']) for a in alternatives})>1 else 'SUPPORTED_BELIEF'
        return WorldBeliefView(entity_id=entity_id,predicate=predicate,state=state,alternatives=tuple(alternatives),support_records=tuple(supports),as_of_valid_us=valid,as_of_known_us=known)
    def snapshot(self,limit=32):
        if not self.scopes or not self.privacy:return ()
        sp=','.join('?' for _ in self.scopes);pp=','.join('?' for _ in self.privacy)
        keys=self.store.db.execute(f"SELECT b.entity_id,b.predicate_key,max(b.known_at_us) t FROM world_beliefs b JOIN continuity_records r ON b.record_id=r.record_id WHERE r.scope IN ({sp}) AND r.privacy_class IN ({pp}) AND r.lifecycle='ACTIVE' GROUP BY b.entity_id,b.predicate_key ORDER BY t DESC LIMIT ?",(*self.scopes,*self.privacy,min(64,limit))).fetchall()
        return tuple(self.view(x['entity_id'],x['predicate_key']) for x in keys)
