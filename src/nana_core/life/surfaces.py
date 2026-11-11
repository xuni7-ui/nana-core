"""Host-bound development surfaces into the same LifeApplication/SubjectLoop.

Shadow adapters and explicit platform adapters enter the same SubjectLoop.
Personal retention requires a trusted binding and a named consent reference.
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
    mode:Literal['DEVELOPMENT_SHADOW_NO_SEND','PLATFORM_ADAPTER_NO_SEND']='DEVELOPMENT_SHADOW_NO_SEND'
    permitted_privacy:tuple[Literal['PUBLIC','PROJECT','PERSONAL'],...]=('PUBLIC','PROJECT')
    allow_personal_retention:bool=False
    personal_retention_consent_ref:str|None=Field(default=None,pattern=r'^[A-Za-z0-9._:-]{1,128}$')


class SurfaceObservation(DTO):
    binding_id:str=Field(pattern=NAME_PATTERN)
    event_id:str=Field(pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    thread_id:str=Field(default='daily',pattern=r'^[A-Za-z0-9._:-]{1,96}$')
    topic:str=Field(default='daily',pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    text:str=Field(min_length=1,max_length=2048)
    privacy_class:Literal['PUBLIC','PROJECT','PERSONAL']='PROJECT'
    origin:Literal['DEVELOPMENT_SHADOW','SYNTHETIC_LOOPBACK','AUTHENTICATED_PLATFORM','ACCOUNT_API_UNATTESTED']='DEVELOPMENT_SHADOW'
    occurred_at_us:int|None=Field(default=None,ge=0,le=9223372036854775807)
    retain_shared_life:bool=False
    approved_summary:str|None=Field(default=None,min_length=1,max_length=512)
    summary_authorization:Literal['NONE','EXPLICIT_PROJECT_SUMMARY','EXPLICIT_PERSONAL_SUMMARY']='NONE'


def recent_sources(app,topic,privacy,limit=8):
    """Bounded metadata/source refs, filtered before any payload is read."""
    s=app.runtime.store;memory=MemoryService(s);out=[]
    for row in s.db.execute("SELECT m.* FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE m.entity_id=? AND m.scope=? AND m.lifecycle='ACTIVE' AND e.source_namespace IN ('recorded.project.surface-summary','recorded.conversation.input') ORDER BY m.created_at_us DESC,m.rowid DESC LIMIT 32",(app.runtime.config.entity_id,app.runtime.config.scopes[0])):
        if row['privacy_class'] not in app.policy.readable_privacy or PRIVACY_RANK[row['privacy_class']]>PRIVACY_RANK[privacy]:continue
        try:
            current=memory.read(row['memory_id']);body=json.loads(current['text'])
        except (CoreError,ValueError):continue
        if type(body) is dict and body.get('topic')==topic and 'summary' in body:out.append(current['memory_id'])
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
    def validate_observation(self,observation,*,reply_target=None):
        if type(observation) is not SurfaceObservation:raise CoreError('SURFACE_TYPED_OBSERVATION_REQUIRED')
        o=SurfaceObservation.model_validate_json(observation.model_dump_json());b=self._binding(o.binding_id)
        if reply_target is not None:
            from ..continuity.autonomy.contracts import RealizationTarget
            if type(reply_target) is not RealizationTarget:raise CoreError('SURFACE_TRUSTED_REPLY_TARGET_REQUIRED')
            allowed = (b.platform=='qq.onebot' and reply_target.capability=='world.contact' and reply_target.operation=='CONTACT') or (
                b.platform=='bilibili.account' and reply_target.capability in {'bilibili.dm.send','bilibili.comment.send'} and reply_target.operation=='WRITE')
            if (b.mode!='PLATFORM_ADAPTER_NO_SEND'
                    or not allowed or reply_target.resource_class!='ORDINARY'):
                raise CoreError('SURFACE_TRUSTED_REPLY_TARGET_REQUIRED')
        if o.privacy_class not in b.permitted_privacy:raise CoreError('SURFACE_PRIVACY_NOT_BOUND')
        if o.privacy_class=='PERSONAL' and (o.retain_shared_life or o.approved_summary is not None) and (not b.allow_personal_retention or not b.personal_retention_consent_ref):raise CoreError('SURFACE_PERSONAL_RETENTION_NOT_AUTHORIZED')
        if b.mode=='DEVELOPMENT_SHADOW_NO_SEND' and o.origin!='DEVELOPMENT_SHADOW':raise CoreError('SURFACE_ORIGIN_BINDING_MISMATCH')
        if o.approved_summary is not None and o.summary_authorization!=('EXPLICIT_PERSONAL_SUMMARY' if o.privacy_class=='PERSONAL' else 'EXPLICIT_PROJECT_SUMMARY'):raise CoreError('SURFACE_SUMMARY_NOT_AUTHORIZED')
        return o,b
    def receive(self,observation,*,reply_target=None,observed_at_us=None,_defer_render=False,_respond_to=()):
        o,b=self.validate_observation(observation,reply_target=reply_target)
        app=self._app;r=app.runtime;key=digest([b.binding_id,o.event_id]);current=r.clock.utc_now_us()
        if observed_at_us is not None and (type(observed_at_us) is not int or not 0<=observed_at_us<=current):
            raise CoreError('SURFACE_OBSERVATION_TIME_INVALID')
        now=current if observed_at_us is None else observed_at_us
        envelope=SurfaceEnvelope(domain='LOCAL_INTERACTION',subject_id=r.identity_id,
            platform=b.platform,surface=b.surface,adapter=b.adapter,entity_id=b.entity_id,
            conversation_id=o.thread_id,session_id=b.binding_id,event_kind='conversation.message',
            occurred_at_us=o.occurred_at_us,observed_at_us=now,correlation_id=o.event_id,privacy_class=o.privacy_class,
            source_reference=('local:shadow:' if b.mode=='DEVELOPMENT_SHADOW_NO_SEND' else 'local:platform:')+key[:40],source_event_key=key)
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
                'binding_id':b.binding_id,'event_id':o.event_id,'epistemic':'EXPLICIT_USER_STATEMENT_NOT_WORLD_TRUTH',
                **({'retention_consent_ref':b.personal_retention_consent_ref} if o.privacy_class=='PERSONAL' else {})})
            reference=('input:surface-summary:' if o.privacy_class=='PERSONAL' else 'summary:')+key
            namespace='recorded.conversation.input' if o.privacy_class=='PERSONAL' else 'recorded.project.surface-summary'
            old=r.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace=? AND source_reference=?",(namespace,reference)).fetchone()
            eid=memory.capture(EvidenceInput(provenance=Provenance(domain='CONSENTED_INTERACTION' if o.privacy_class=='PERSONAL' else 'DEVELOPMENT_PROJECT' if o.privacy_class=='PROJECT' else 'RECORDED_PUBLIC',
                source_namespace=namespace,source_reference=reference,source_kind='USER_STATEMENT',coverage='SUMMARY'),
                retention_consent_ref=reference if o.privacy_class=='PERSONAL' else None,
                text=body,privacy_class=o.privacy_class,observed_time_us=old[0] if old else now))
            summary=(memory.add(MemoryCandidate(entity_id=b.entity_id,scope=b.scope,memory_type=MemoryType.EPISODIC,
                epistemic_kind='STATEMENT',source_evidence_id=eid,text=body,confidence=.8)),)
        result=app.chat(o.text,topic=o.topic,privacy=o.privacy_class,message_id=key,
            surface=envelope,support_memory_ids=summary,source_key=canonical_key,retain_shared_life=o.retain_shared_life,
            reply_target=reply_target,_defer_render=_defer_render,_respond_to=_respond_to)
        return {**result,'binding_id':b.binding_id,'source_key':canonical_key,'summary_memory_ids':summary,
            'state':'SHADOW_INPUT_REVIEWED_NO_REPLY' if result.get('render_state')=='DEFERRED_TO_CONTINUATION' else 'SHADOW_REPLY_CANDIDATE' if b.mode=='DEVELOPMENT_SHADOW_NO_SEND' else 'CORE_REPLY_CANDIDATE',
            'platform_origin':o.origin,'delivered':False,'execution_authority':False}

    def receive_sequence(self,observations):
        """Already received finite inputs; each enters original C exactly once.

        Retained conversations and explicit boundaries keep individual replies.
        No batch transport acknowledges delivery, persists transient bodies or
        authorizes replay of a partially judged sequence after interruption.
        """
        if type(observations) is not tuple or not 2<=len(observations)<=4:
            raise CoreError('SURFACE_SEQUENCE_BOUND')
        checked=[self.validate_observation(o) for o in observations]
        first,binding=checked[0]
        if binding.mode!='DEVELOPMENT_SHADOW_NO_SEND':raise CoreError('SURFACE_SEQUENCE_SHADOW_REQUIRED')
        coordinates=lambda o:(o.binding_id,o.thread_id,o.topic,o.privacy_class,o.origin,o.retain_shared_life)
        if (any(coordinates(o)!=coordinates(first) for o,_ in checked)
                or len({o.event_id for o,_ in checked})!=len(checked)):
            raise CoreError('SURFACE_SEQUENCE_SCOPE_REQUIRED')
        r=self._app.runtime
        seen=[]
        for o,b in checked:
            # Existing canonical event key: no parallel idempotency journal.
            key=digest([b.binding_id,o.event_id])
            reference=('local:shadow:' if b.mode=='DEVELOPMENT_SHADOW_NO_SEND' else 'local:platform:')+key[:40]
            envelope=SurfaceEnvelope(domain='LOCAL_INTERACTION',subject_id=r.identity_id,platform=b.platform,
                surface=b.surface,adapter=b.adapter,entity_id=b.entity_id,conversation_id=o.thread_id,
                session_id=b.binding_id,event_kind='conversation.message',observed_at_us=r.clock.utc_now_us(),
                correlation_id=o.event_id,privacy_class=o.privacy_class,source_reference=reference,source_event_key=key)
            seen.append(bool(r.store.db.execute('SELECT 1 FROM subject_events WHERE source_key=?',(source_key(envelope),)).fetchone()))
        if any(seen) and not all(seen):raise CoreError('SURFACE_SEQUENCE_PARTIAL_NO_REPLAY')
        from ..continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
        boundaries={'DECLINE_DEPTH','DECLINE_DELIVERY','REOPEN','REOPEN_DELIVERY'}
        # Preserve retained history/feedback semantics instead of dropping a
        # saved exchange or claiming one draft was sent for several contacts.
        coalesce=not any(seen) and not first.retain_shared_life and all(o.approved_summary is None
            and LiteralSpanInterpreter().interpret(o.text).kind not in boundaries for o,_ in checked)
        results=[];unanswered=();deferred_ids=set();completed=False;observed_at_us=r.clock.utc_now_us()
        try:
            for i,(o,_) in enumerate(checked):
                if r.stop_requested:raise CoreError('SURFACE_SEQUENCE_INTERRUPTED_NO_REPLAY')
                for mid in unanswered:
                    MemoryService(r.store).read(mid)  # Withdrawal wins before a later model call.
                result=self.receive(o,observed_at_us=observed_at_us,_defer_render=coalesce and i<len(checked)-1,
                    _respond_to=unanswered if coalesce else ())
                result={**result,'respond_to_memory_ids':list((*unanswered,result['message_memory_id']))
                    if result.get('text') and result.get('message_memory_id') else []}
                results.append(result)
                key=result.get('message_id','')
                if r.store.db.execute("SELECT 1 FROM cognitive_requests WHERE request_key IN (?,?) AND state='UNKNOWN'",
                        ('life.interpret.'+key,'life.render.'+key)).fetchone():
                    raise CoreError('SURFACE_SEQUENCE_INCOMPLETE_NO_REPLAY')
                if result.get('render_state')=='DEFERRED_TO_CONTINUATION':
                    unanswered=(*unanswered,result['message_memory_id']);deferred_ids.add(result['message_memory_id'])
                else:
                    if unanswered and result.get('render_state')!='UNVERIFIED_MODEL_WORDING' and result.get('mode')!='RESPECT_BOUNDARY':
                        raise CoreError('SURFACE_SEQUENCE_INCOMPLETE_NO_REPLAY')
                    unanswered=()
            completed=True
            return {'state':'SHADOW_SEQUENCE_REVIEWED','results':results,
                'coalesced':any(x.get('render_state')=='UNVERIFIED_MODEL_WORDING'
                    and len(x['respond_to_memory_ids'])>1 for x in results),
                'delivered':False,'execution_authority':False}
        finally:
            if not completed:
                self._app._recent=[turn for turn in self._app._recent if turn.message_memory_id not in deferred_ids]
