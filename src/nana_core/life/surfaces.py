"""Host-bound development surfaces into the same LifeApplication/SubjectLoop.

QQ/Bili here are shadow adapters, not account connections. Only explicitly
supplied PUBLIC/PROJECT summaries persist; conversation bodies remain volatile.
There is no transport, controller token, Grant, or second conversation database.
"""
import json
from typing import Literal
from pydantic import Field
from ..contracts import DTO,CoreError
from ..storage import canonical,digest
from ..continuity.extensions import SurfaceEnvelope,NAME_PATTERN
from ..continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..continuity.memory import MemoryService,PRIVACY_RANK
from ..continuity.records import RecordService
from ..continuity.surfaces import ContinuityViews,source_key


class SurfaceBinding(DTO):
    binding_id:str=Field(pattern=NAME_PATTERN)
    platform:str=Field(pattern=NAME_PATTERN)
    surface:str=Field(pattern=NAME_PATTERN)
    adapter:str=Field(pattern=NAME_PATTERN)
    entity_id:str='project-user'
    scope:str='project-work'
    enabled:bool=True
    mode:Literal['DEVELOPMENT_SHADOW_NO_SEND']='DEVELOPMENT_SHADOW_NO_SEND'


class SurfaceObservation(DTO):
    binding_id:str=Field(pattern=NAME_PATTERN)
    event_id:str=Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    thread_id:str=Field(default='daily',pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    topic:str=Field(default='daily',pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    text:str=Field(min_length=1,max_length=2048)
    privacy_class:Literal['PUBLIC','PROJECT']='PROJECT'
    retain_shared_life:bool=False
    approved_summary:str|None=Field(default=None,min_length=1,max_length=512)
    summary_authorization:Literal['NONE','EXPLICIT_PROJECT_SUMMARY']='NONE'


def recent_sources(app,topic,privacy,limit=8):
    """Bounded metadata/source refs, filtered before any payload is read."""
    s=app.runtime.store;memory=MemoryService(s);out=[]
    for row in s.db.execute("SELECT m.* FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE m.entity_id=? AND m.scope=? AND m.lifecycle='ACTIVE' AND e.source_namespace='recorded.project.surface-summary' ORDER BY m.created_at_us DESC,m.rowid DESC LIMIT 32",(app.runtime.config.entity_id,app.runtime.config.scopes[0])):
        if row['privacy_class'] not in app.policy.readable_privacy or PRIVACY_RANK[row['privacy_class']]>PRIVACY_RANK[privacy]:continue
        try:
            current=memory.read(row['memory_id']);body=json.loads(current['text'])
        except (CoreError,ValueError):continue
        if body['topic']==topic:out.append(current['memory_id'])
        if len(out)>=limit:break
    return tuple(out)


class SurfaceSession:
    def __init__(self,app,bindings):
        self._app=app;self._bindings={x.binding_id:x for x in bindings}
        if len(self._bindings)!=len(bindings):raise CoreError('SURFACE_BINDING_DUPLICATE')
        if any(x.entity_id!=app.runtime.config.entity_id or x.scope not in app.runtime.config.scopes for x in bindings):raise CoreError('SURFACE_ENTITY_SCOPE_UNBOUND')
    def view(self,binding_id,*,tier='L1_RECENT'):
        b=self._binding(binding_id)
        return ContinuityViews(self._app.runtime.store,self._app.policy).project(tier,
            entity_id=b.entity_id,scopes=(b.scope,),limit=16)
    def _binding(self,key):
        b=self._bindings.get(key)
        if not b or not b.enabled:raise CoreError('SURFACE_DISABLED_OR_UNBOUND')
        return b
    def receive(self,observation):
        if type(observation) is not SurfaceObservation:raise CoreError('SURFACE_TYPED_OBSERVATION_REQUIRED')
        o=SurfaceObservation.model_validate_json(observation.model_dump_json());b=self._binding(o.binding_id)
        if o.approved_summary is not None and o.summary_authorization!='EXPLICIT_PROJECT_SUMMARY':raise CoreError('SURFACE_SUMMARY_NOT_AUTHORIZED')
        app=self._app;r=app.runtime;key=digest([b.binding_id,o.event_id]);now=r.clock.utc_now_us()
        envelope=SurfaceEnvelope(domain='LOCAL_INTERACTION',subject_id=r.identity_id,
            platform=b.platform,surface=b.surface,adapter=b.adapter,entity_id=b.entity_id,
            conversation_id=o.thread_id,session_id=b.binding_id,event_kind='conversation.message',
            observed_at_us=now,correlation_id=o.event_id,privacy_class=o.privacy_class,
            source_reference='local:shadow:'+key[:40],source_event_key=key)
        canonical_key=source_key(envelope)
        prior=r.store.db.execute('SELECT * FROM subject_events WHERE source_key=?',(canonical_key,)).fetchone()
        if prior:
            # No replay of private bodies or model wording. Source closure still
            # applies to any separately requested continuity view.
            if prior['record_id']:
                try:old=RecordService(r.store).read(prior['record_id'])['payload']['input']
                except CoreError:return {'state':'ALREADY_REVIEWED_SOURCE_RETIRED','external_delivery':False}
                if old['privacy_class']!=o.privacy_class or old['surface']['conversation_id']!=o.thread_id or old['interaction_signal']['topic_key']!=o.topic:raise CoreError('SURFACE_EVENT_COLLISION')
            return {'state':'ALREADY_REVIEWED_NO_REPLAY','source_key':canonical_key,'external_delivery':False}
        summary=()
        if o.approved_summary is not None:
            memory=MemoryService(r.store);body=canonical({'topic':o.topic,'summary':o.approved_summary,
                'binding_id':b.binding_id,'event_id':o.event_id,'epistemic':'EXPLICIT_USER_STATEMENT_NOT_WORLD_TRUTH'})
            reference='summary:'+key
            old=r.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace='recorded.project.surface-summary' AND source_reference=?",(reference,)).fetchone()
            eid=memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT' if o.privacy_class=='PROJECT' else 'RECORDED_PUBLIC',
                source_namespace='recorded.project.surface-summary',source_reference=reference,source_kind='USER_STATEMENT',coverage='SUMMARY'),
                text=body,privacy_class=o.privacy_class,observed_time_us=old[0] if old else now))
            summary=(memory.add(MemoryCandidate(entity_id=b.entity_id,scope=b.scope,memory_type=MemoryType.EPISODIC,
                epistemic_kind='STATEMENT',source_evidence_id=eid,text=body,confidence=.8)),)
        result=app.chat(o.text,topic=o.topic,privacy=o.privacy_class,message_id=key,
            surface=envelope,support_memory_ids=summary,source_key=canonical_key,retain_shared_life=o.retain_shared_life)
        return {**result,'binding_id':b.binding_id,'source_key':canonical_key,'summary_memory_ids':summary,
            'state':'SHADOW_REPLY_CANDIDATE','delivered':False,'execution_authority':False}
