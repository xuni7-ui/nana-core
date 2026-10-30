"""Admission is a separate realization consideration, never a social drive."""
import json
from typing import Literal
from pydantic import Field,model_validator,model_serializer
from ...contracts import DTO,CoreError
from ...storage import canonical,digest
from ..records import RecordService
from .world import URI

class RecipientState(DTO):
    resource: str = Field(pattern=URI)
    entity_id: str
    availability: Literal['AVAILABLE','BUSY','UNKNOWN']
    observed_at_us: int = Field(ge=0)
    expires_at_us: int = Field(ge=0)
    permitted_privacy: tuple[Literal['PUBLIC','PROJECT','PERSONAL'],...] = ('PUBLIC',)

class ReplyWindowBinding(DTO):
    resource:str=Field(pattern=URI)
    binding_id:str=Field(min_length=1,max_length=96)
    platform:Literal['qq.onebot','bilibili.account']
    thread_id:str=Field(min_length=1,max_length=128)

class DeliveryPolicy(DTO):
    recipients: tuple[str,...] = Field(max_length=16)
    privacy_classes: tuple[Literal['PUBLIC','PROJECT','PERSONAL'],...] = ('PUBLIC',)
    quiet_start_utc_hour: int = Field(default=23,ge=0,le=23)
    quiet_end_utc_hour: int = Field(default=7,ge=0,le=23)
    admission_us: int = Field(default=30000000,ge=100000,le=60000000)
    quiet_timezone:str='UTC'
    quiet_start_local_hour:int|None=Field(default=None,ge=0,le=23)
    quiet_end_local_hour:int|None=Field(default=None,ge=0,le=23)
    direct_reply_bindings:tuple[ReplyWindowBinding,...]=Field(default=(),max_length=16)
    direct_reply_window_us:int=Field(default=60000000,ge=1000000,le=120000000)
    @model_serializer(mode='wrap')
    def existing_policy_wire(self,handler):
        value=handler(self)
        if not self.direct_reply_bindings:
            value.pop('direct_reply_bindings',None);value.pop('direct_reply_window_us',None)
        return value
    @model_validator(mode='after')
    def quiet_spec(self):
        from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
        if (self.quiet_start_local_hour is None)!=(self.quiet_end_local_hour is None):raise ValueError('complete quiet window required')
        try:ZoneInfo(self.quiet_timezone)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('IANA timezone required') from None
        return self

class DeliveryAdmission:
    def __init__(self,store,policy,*,scopes,privacy_classes):
        self.store,self.policy=store,policy;self.scopes,self.privacy=tuple(scopes),tuple(privacy_classes);self.records=RecordService(store)
    def _recipient(self,resource,scope):
        for row in self.store.db.execute("SELECT * FROM memories WHERE scope=? AND predicate_key=? AND lifecycle='ACTIVE' AND assessment IN ('CURRENT','UNASSESSED') ORDER BY created_at_us DESC LIMIT 16",(scope,'recipient.'+digest(resource)[:32])):
            if row['privacy_class'] not in self.privacy:continue
            item=self.records.memory.read(row['memory_id'])
            if item['authority']!='DIRECT':continue
            try:state=RecipientState.model_validate_json(item['text'])
            except ValueError:continue
            if state.resource==resource and state.entity_id==item['entity_id']:return row['memory_id'],state
        return None,None
    def _quiet(self):
        from datetime import datetime,timezone
        from zoneinfo import ZoneInfo
        local=self.policy.quiet_start_local_hour is not None and self.policy.quiet_end_local_hour is not None
        hour=datetime.fromtimestamp(self.store.clock.utc_now_us()/1e6,tz=ZoneInfo(self.policy.quiet_timezone) if local else timezone.utc).hour
        start,end=(self.policy.quiet_start_local_hour,self.policy.quiet_end_local_hour) if local else (self.policy.quiet_start_utc_hour,self.policy.quiet_end_utc_hour)
        return start<=hour<end if start<end else hour>=start or hour<end if start>end else False
    def _reply_window(self, event_id, resource):
        """Conversation timing evidence, never execution permission/Grant.

        Only the independently fetched original platform event opens a bounded
        direct-reply window. It cannot authorize proactive or different-peer send.
        """
        event=self.store.one('subject_events',event_id)
        if not event or event['scope'] not in self.scopes or not self.records.current_support(event['record_id']):
            raise CoreError('DIRECT_REPLY_SOURCE_UNAVAILABLE')
        data=self.records.read(event['record_id'])['payload']['input']
        surface=data.get('surface')
        now=self.store.clock.utc_now_us()
        if (data['kind']!='INTERACTION' or data['origin']!='USER' or not surface
                or surface['event_kind']!='conversation.message' or not data['observed_at_us']<=now<data['observed_at_us']+self.policy.direct_reply_window_us):
            raise CoreError('DIRECT_REPLY_WINDOW_EXPIRED_OR_UNPROVEN')
        if not any((b.resource,b.binding_id,b.platform,b.thread_id)==(resource,surface['session_id'],surface['platform'],surface['conversation_id'])
                   for b in self.policy.direct_reply_bindings):
            raise CoreError('DIRECT_REPLY_PEER_UNBOUND')
        return data['observed_at_us']+self.policy.direct_reply_window_us
    def assess_reply(self, cycle, resource, *, payload=None, source_memory_ids=()):
        if (not cycle.intention_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED'
                or cycle.intention.kind not in {'SOCIAL_INTERACTION','DISAGREE','ACTION_PROPOSAL'}
                or not cycle.realization_target or cycle.realization_target.resource!=resource):
            raise CoreError('ENDORSED_DIRECT_REPLY_REQUIRED')
        expires=self._reply_window(cycle.event_id,resource)
        head=self.records.read(cycle.record_id)
        if (resource not in self.policy.recipients or head['privacy_class'] not in self.policy.privacy_classes
                or any(self.records.memory.read(mid)['privacy_class'] not in self.policy.privacy_classes for mid in source_memory_ids)):
            raise CoreError('DIRECT_REPLY_PRIVACY_DENIED')
        key=digest(['direct-reply',cycle.cycle_id,resource,digest(payload)])
        previous=self.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='DELIVERY_DECISION' AND target_id=?",(key,)).fetchone()
        if previous:return {'record_id':previous[0],**self.records.read(previous[0])['payload']}
        body={'intention_id':cycle.intention_id,'intention_revision':self.store.one('subject_intentions',cycle.intention_id)['revision'],
            'payload_digest':digest(payload),'resource':resource,'result':'ELIGIBLE','recipient_memory_id':None,
            'expires_at_us':min(expires,self.store.clock.utc_now_us()+self.policy.admission_us),
            'direct_reply_event_id':cycle.event_id,'authority_granted':False}
        with self.store.transaction('open.direct_reply_assessed',{'intention_id':cycle.intention_id}) as tx:
            rid=self.records.create(tx,kind='DELIVERY_DECISION',scope=head['scope'],payload=body,
                records=(cycle.record_id,),memories=tuple(source_memory_ids),target_id=key)
        return {'record_id':rid,**body}
    def assess(self,cycle,resource,*,payload=None,source_memory_ids=()):
        if not cycle.intention_id or not cycle.evaluation or cycle.evaluation.normative!='ENDORSED':raise CoreError('ENDORSED_SOCIAL_INTENTION_REQUIRED')
        event=self.store.one('subject_events',cycle.event_id);scope=event['scope']
        if scope not in self.scopes or cycle.intention.kind not in {'SOCIAL_INTERACTION','ACTION_PROPOSAL'}:raise CoreError('DELIVERY_SCOPE_DENIED')
        mid,state=self._recipient(resource,scope);now=self.store.clock.utc_now_us()
        code='ELIGIBLE'
        if resource not in self.policy.recipients:code='DENY_RECIPIENT'
        elif not mid or state.observed_at_us>now or state.expires_at_us<=now:code='UNKNOWN_AVAILABILITY'
        elif state.availability!='AVAILABLE':code='DEFER_BUSY' if state.availability=='BUSY' else 'UNKNOWN_AVAILABILITY'
        elif self._quiet():code='DEFER_QUIET_WINDOW'
        parent=self.records.read(cycle.record_id)
        from ..memory import PRIVACY_RANK
        classification=max((parent['privacy_class'],*(self.records.memory.read(m)['privacy_class'] for m in source_memory_ids)),key=PRIVACY_RANK.get)
        if classification not in self.policy.privacy_classes or (state and classification not in state.permitted_privacy):code='DENY_PRIVACY'
        key=digest([cycle.cycle_id,resource,mid,code,digest(payload)])
        old=self.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='DELIVERY_DECISION' AND target_id=?",(key,)).fetchone()
        if old:return {'record_id':old[0],**self.records.read(old[0])['payload']}
        body={'intention_id':cycle.intention_id,'intention_revision':self.store.one('subject_intentions',cycle.intention_id)['revision'],'payload_digest':digest(payload),'resource':resource,'result':code,'recipient_memory_id':mid,'expires_at_us':min(now+self.policy.admission_us,state.expires_at_us) if state else now,'authority_granted':False}
        with self.store.transaction('open.delivery_assessed',{'intention_id':cycle.intention_id,'result':code}) as tx:
            rid=self.records.create(tx,kind='DELIVERY_DECISION',scope=scope,payload=body,records=(cycle.record_id,),memories=tuple(dict.fromkeys((*((mid,) if mid else ()),*source_memory_ids))),target_id=key)
        return {'record_id':rid,**body}
    def require(self,rid,resource,*,invocation=None):
        if not rid:raise CoreError('DELIVERY_ADMISSION_REQUIRED')
        record=self.records.read(rid);body=record['payload'];now=self.store.clock.utc_now_us()
        if record['record_kind']!='DELIVERY_DECISION' or record['scope'] not in self.scopes or record['privacy_class'] not in self.privacy or not self.records.current_support(rid):raise CoreError('DELIVERY_ADMISSION_RETIRED')
        if body.get('direct_reply_event_id'):
            self._reply_window(body['direct_reply_event_id'],resource)
            if body['result']!='ELIGIBLE' or body['resource']!=resource or body['expires_at_us']<=now:
                raise CoreError('DELIVERY_ADMISSION_STALE')
        else:
            mid,state=self._recipient(resource,record['scope'])
            if body['result']!='ELIGIBLE' or body['resource']!=resource or body['expires_at_us']<=now or self._quiet() or mid!=body['recipient_memory_id'] or not state or state.availability!='AVAILABLE' or state.expires_at_us<=now:raise CoreError('DELIVERY_ADMISSION_STALE')
        if invocation is not None:
            action=self.store.one('actions',invocation.action_id);intention=self.store.one('subject_intentions',body['intention_id'])
            if not action or action['effect_slot']!='subject:'+body['intention_id'] or not intention or intention['revision']!=body['intention_revision'] or intention['state']!='PENDING' or digest(invocation.args.get('data'))!=body['payload_digest']:raise CoreError('DELIVERY_INTENTION_OR_PAYLOAD_MISMATCH')
        return True
