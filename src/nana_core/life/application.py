"""One independent application coordinates original Runtime safe points.

No parallel semantic loop: activity source only offers allowed materials; original
C judges, D queues, F executes, G learns. No automatic social delivery.
"""
import json,time
from pathlib import Path
from ..clock import Clock
from ..contracts import CoreError
from ..storage import canonical,digest,uid
from ..actions import OperatorAuthority
from ..continuity import ContinuityStore,IdentityService
from ..continuity.memory import MemoryService
from ..continuity.project_work.service import ProjectWork,learning_spec,capture
from ..continuity.project_work.port import read_material
from ..continuity.subject import SubjectInput
from ..continuity.subject.context_fit import InteractionSignal
from ..continuity.dialogue_shadow.bridge import LiteralSpanInterpreter
from ..continuity.context import ContextPolicy
from ..continuity.records import RecordService
from ..continuity.provider_routing import RouteRequest
from ..continuity.world_loop.cognition import CognitionBudget
from ..presence.runtime import NanaRuntime
from ..presence.contracts import RuntimeConfig,LivingRuntimeConfig,RuntimeEvent,Cause,SECOND,HOUR
from ..presence.projections import runtime_projection
from .config import home_path,load_config
from .dialogue_contracts import DialogueContext


def runtime_config(config):
    return RuntimeConfig(schema_target=13,scopes=('project-work',),entity_id='project-user',privacy_classes=('PUBLIC','PROJECT','PERSONAL'),model=None,
        heartbeat_us=SECOND,lease_us=30*SECOND,review_interval_us=SECOND,idle_recall_us=SECOND,queue_capacity=64,schedule_capacity=128,poll_seconds=.2,
        max_calls_per_day=config.provider_calls_per_day,living=LivingRuntimeConfig(maintenance_interval_us=60*SECOND,step_interval_us=200_000,max_idle_seconds=2,background_fraction_percent=50,max_model_bytes_per_day=4_000_000,max_estimated_cost_micro_per_day=max(1,config.provider_cost_ceiling_micro*config.provider_calls_per_day)))

class PortfolioOpportunities:
    """Finite host-approved material availability, not a wish/adoption engine."""
    def __init__(self,app):self.app=app;self.next_at=0
    def opportunity(self):
        a=self.app;r=a.runtime;now=r.clock.utc_now_us()
        if now<self.next_at:return None
        self.next_at=now+int(a.config.activity_interval_seconds*SECOND)
        hour=now//HOUR%24;start,end=a.config.active_start_utc,a.config.active_end_utc
        if start!=end and not (start<=hour<end if start<end else hour>=start or hour<end):return None
        checked=a.work.assess_later_use()
        if checked:return checked
        # Do not bypass an unresolved failure/unknown effect to manufacture activity.
        if r.store.db.execute("SELECT 1 FROM goals WHERE state IN ('FAILED','BLOCKED','ACTIVE','SUSPENDED') LIMIT 1").fetchone():return None
        if r.store.db.execute("SELECT 1 FROM jobs WHERE work_kind='LEARNING' AND state NOT IN ('DONE','CANCELLED') LIMIT 1").fetchone():return None
        for material in a.config.materials[:a.config.max_autonomous_materials]:
            if a.work.goal_for(material.material_id):continue
            # Source erasure tombstones remain authoritative after process restart.
            if r.store.db.execute("SELECT 1 FROM continuity_evidence WHERE source_namespace='recorded.project.material' AND source_reference=? AND state='DELETED'",('input:'+material.material_id,)).fetchone():continue
            try:
                source=a.work.request(material.material_id)
                return {'source':'APPROVED_PROJECT_MATERIAL_OPPORTUNITY','source_memory_id':source}
            except CoreError:return None
        return None

class LifeApplication:
    def __init__(self,home,*,clock=None,router=None,bootstrap_grant=False):
        self.home=home_path(home);self.config=load_config(home);self.router=router;self.session=None;self._chat={};self.closed=False
        self.clock=clock or Clock()
        with ContinuityStore(self.home/'subject/self.db',self.clock,schema_target=13) as s:
            IdentityService(s,OperatorAuthority());MemoryService(s).entity('project-user','PERSON')
        self.runtime=NanaRuntime(self.home/'subject/self.db',runtime_config(self.config),clock=self.clock)
        try:
            spec=learning_spec(*(read_material(self.config.project_root,m) for m in (self.config.practice,self.config.heldout,self.config.transfer)))
            self.work=ProjectWork(self.runtime,self.config.project_root,self.config.materials,self.home/'reports',spec,grant=bootstrap_grant,motivation_source='CREATIVE_INTEREST')
            self.runtime.work.activity_source=PortfolioOpportunities(self)
            old=self.runtime.store.one('core_meta','runtime.life_control');self.control=json.loads(old['value_json']) if old else {'paused':False,'messages':0}
            self.runtime.work.paused=self.control['paused']
            self.policy=ContextPolicy(policy_id='independent-life',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT','PERSONAL'),remote_privacy=self.config.remote_privacy)
        except BaseException:self.runtime.stop();raise

    def _save_control(self):
        r=self.runtime;r.lease.assert_current();r.store._put('core_meta',{'key':'runtime.life_control','value_json':canonical(self.control)})
    def pause(self,paused=True):
        self.control['paused']=paused;self.runtime.work.paused=paused;self._save_control();return {'autonomy':'PAUSED' if paused else 'RUNNING'}
    def tick(self):return self.runtime.step()
    def sources(self):
        r=self.runtime;out=[]
        for material in self.config.materials:
            row=r.store.db.execute("SELECT m.memory_id,m.lifecycle FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.material' AND e.source_reference=? ORDER BY m.rowid DESC LIMIT 1",('input:'+material.material_id,)).fetchone()
            out.append({'filename':material.relative_path,'material_id':material.material_id,'source_memory_id':row[0] if row else None,'support_state':row[1] if row else 'NOT_YET_OFFERED'})
        return {'approved_sources':out}
    def status(self):
        r=self.runtime
        return {'identity_id':r.identity_id,'autonomy':'PAUSED' if r.work.paused else 'RUNNING','provider':'OFFLINE_NO_PROVIDER' if self.router is None else 'CONFIGURED_NOT_QUALITY_QUALIFIED',
            'view':runtime_projection(r,'LIVING_RUNTIME',self.policy,scopes=('project-work',),entity_id='project-user'),
            'learning':[{'state':x['state'],'cursor':x['cursor']} for x in r.store.db.execute("SELECT state,cursor FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 4")],
            'reports':[p.name for p in (self.home/'reports').glob('*.md')], 'pending_authorization':['REAL_PROVIDER_BUDGET_AND_EXPLICIT_SECRET_RESOLVER'] if self.router is None else [],'external_social_delivery':'DISABLED'}
    def presence(self,state):
        from ..continuity.open_agency.delivery import RecipientState
        if state not in {'BUSY','AVAILABLE','UNKNOWN'}:raise CoreError('LOCAL_PRESENCE_INVALID')
        r=self.runtime
        value=RecipientState(resource='synthetic://recipient/project-user',entity_id='project-user',availability=state,observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+60*SECOND)
        mid=capture(r,'local-presence:'+uid(),value.model_dump(mode='json'),kind='USER_STATEMENT',predicate='recipient.'+digest(value.resource)[:32])
        r.refresh_attention();return {'declared_availability':state,'source_memory_id':mid,'not_inferred_from_contact_frequency':True}
    def _fact_sources(self):
        r=self.runtime;out=[]
        for row in r.store.db.execute("SELECT m.memory_id FROM actions a JOIN continuity_evidence e ON e.source_reference=a.action_id JOIN memories m ON m.source_evidence_id=e.evidence_id WHERE a.capability='world.publish' AND a.state='SUCCEEDED' AND e.source_namespace='recorded.project.local-action' AND m.lifecycle='ACTIVE' ORDER BY a.rowid DESC LIMIT 3"):
            try:MemoryService(r.store).read(row[0]);out.append(row[0])
            except CoreError:continue
        return tuple(out)
    def _session(self,privacy):
        if self.router is None:raise CoreError('LIVE_PROVIDER_NOT_RUN_OFFLINE_MODE')
        from ..presence.resources import resource_state
        if resource_state(self.runtime.store,self.runtime.config).unresolved_calls:raise CoreError('UNRESOLVED_PROVIDER_CALL_NO_RETRY')
        target=self.router.resolve(RouteRequest(operation='COGNITION',privacy_class=privacy,timeout_ms=self.config.provider_timeout_ms,cost_ceiling=self.config.provider_cost_ceiling_micro,context_limit=8192,output_limit=1024),self.policy)
        if self.session is None or self.session.route_snapshot!=target.snapshot:
            if self.session and any(w.is_alive() for w in self.session._workers):raise CoreError('PROVIDER_WORKER_UNRESOLVED')
            self.session=target.cognition_session(self.runtime)
            self.session.recover()
        from ..presence.resources import resource_state
        if resource_state(self.runtime.store,self.runtime.config).unresolved_calls:raise CoreError('UNRESOLVED_PROVIDER_CALL_NO_RETRY')
        return self.session
    def _model(self,key,phase,mid,text,topic,privacy,cycle=None):
        session=self._session(privacy)
        facts=self._fact_sources() if phase=='RENDER' else ()
        descriptor=DialogueContext(message_memory_id=mid,topic=topic,privacy_class=privacy,phase=phase,
            judgment=cycle.judgment.stance if cycle else None,intention=cycle.intention.kind if cycle else None,context_mode=cycle.context_fit.mode if cycle else None,effect_status='VERIFIED_EFFECT' if facts else 'NONE')
        data={'dialogue':descriptor.model_dump(mode='json')};volatile={'dialogue':descriptor.model_copy(update={'text':text}).model_dump(mode='json')}
        request=session.prepare(key, 'INTERPRET' if phase=='INTERPRET' else 'SOCIAL',(mid,*facts),role_input=data,volatile_input=volatile,
            budget=CognitionBudget(input_tokens=8192,output_tokens=1024,timeout_ms=self.config.provider_timeout_ms,cost_ceiling_micro=self.config.provider_cost_ceiling_micro))
        result=session.execute(request)
        if result['state']!='PROPOSED':raise CoreError(result.get('error_code','DIALOGUE_NOT_PROPOSED'))
        return session,result['record_id']

    def chat(self,text,*,topic='daily',privacy='PERSONAL',message_id=None):
        if type(text) is not str or not 1<=len(text)<=2048:raise CoreError('LOCAL_MESSAGE_BOUND')
        r=self.runtime;key=message_id or uid()
        if key in self._chat:return {'message_id':key,'state':'ALREADY_REVIEWED_NO_REPLAY'}
        if r.store.db.execute('SELECT 1 FROM subject_events WHERE source_key=?',('local.chat.'+key,)).fetchone():return {'message_id':key,'state':'ALREADY_REVIEWED_NO_REPLAY'}
        mid=capture(r,'local-message:'+key,{'local_message_id':key,'body_retained':False})
        literal=LiteralSpanInterpreter().interpret(text);kind=literal.kind if literal.basis=='LITERAL_SPAN' else 'UNCLEAR';basis='EXPLICIT' if literal.basis=='LITERAL_SPAN' else 'INTERPRETED';rid=None;provider_state='LIVE_PROVIDER_NOT_RUN'
        try:
            session,rid=self._model('life.interpret.'+key,'INTERPRET',mid,text,topic,privacy)
            meaning=session.proposal(rid).proposal.dialogue
            # Literal user boundary beats contradictory model interpretation.
            if kind not in {'DECLINE_DEPTH','REOPEN'}:
                kind=meaning.kind if meaning.confidence in {'RELEVANT','HIGH'} else 'UNCLEAR'
                basis='MODEL_PROPOSAL' if meaning.confidence in {'RELEVANT','HIGH'} else 'INTERPRETED'
            provider_state='MODEL_PROPOSAL_ACCEPTED_NOT_QUALITY_QUALIFIED'
        except CoreError as exc:provider_state=exc.code
        event=SubjectInput(domain='LOCAL_INTERACTION',source_key='local.chat.'+key,kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',observed_at_us=r.clock.utc_now_us(),privacy_class=privacy,
            text='Local input reviewed meaning: '+kind,source_memory_ids=(mid,),interaction_signal=InteractionSignal(kind=kind,topic_key=topic,basis=basis,proposal_record_id=rid))
        qid=r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=event,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us(),priority=3))
        outcome=r.step();queue=r.store.one('runtime_queue',qid)
        if not outcome or not outcome.get('cycle') or queue['state']!='DONE':raise CoreError('LOCAL_INTERACTION_PENDING')
        cycle=outcome['cycle'];draft=None;render_state='NOT_RUN'
        if cycle.context_fit.mode!='RESPECT_BOUNDARY' and self.router is not None and provider_state=='MODEL_PROPOSAL_ACCEPTED_NOT_QUALITY_QUALIFIED':
            try:
                session,render_rid=self._model('life.render.'+key,'RENDER',mid,text,topic,privacy,cycle)
                draft=session.take_dialogue_draft(render_rid);render_state='UNVERIFIED_MODEL_WORDING'
            except CoreError as exc:render_state=exc.code
        if not draft:
            draft={'VENT':'离线模式：我在听；这次不把倾诉变成研究。','HELP':'离线语义受限：可用 /work 选择已批准的源码材料。','SHARE':'离线模式：收到你的分享；没有另开任务。','CHAT':'离线模式：可以闲聊，真实语言模型尚未配置。',
                   'RESPECT_BOUNDARY':'这个话题先停在这里。','CORRECTION':'我会先澄清更正的内容，不直接改写历史。'}.get(cycle.context_fit.mode,'离线语义受限：你希望我听你说，还是一起处理具体问题？')
        if cycle.intention_id:
            current=r.store.one('subject_intentions',cycle.intention_id)
            if current['state']=='PENDING':r.subject.transition_intention(cycle.intention_id,expected_revision=current['revision'],state='DROPPED')
        self.control['messages']+=1;self._save_control();self._chat[key]=True
        if len(self._chat)>64:self._chat.pop(next(iter(self._chat)))
        return {'message_id':key,'message_memory_id':mid,'provider_state':provider_state,'render_state':render_state,'mode':cycle.context_fit.mode,'judgment':cycle.judgment.stance,'intention':cycle.intention.kind,'text':draft,'raw_body_persisted':False,'external_social_send':False}

    def forget(self,mid):MemoryService(self.runtime.store,self.runtime.authority).forget(mid,self.runtime.authority);return {'forgotten':mid}
    def revoke(self):
        k=self.runtime.work.agency.realization.kernel
        for row in self.runtime.store.all('grants'):
            if not row['revoked']:k.revoke(row['grant_id'],self.runtime.authority)
        return {'local_execution':'REVOKED_NO_REGRANT_ON_RESTART'}
    def close(self):
        if not self.closed:
            self.closed=True
            if self.session:
                self.session._volatile_inputs.clear();self.session._volatile_dialogue.clear()
                if hasattr(self.session.transport,'_credential'):self.session.transport._credential=None
            self.runtime.stop()
    def __enter__(self):return self
    def __exit__(self,*unused):self.close()
