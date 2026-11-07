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
        heartbeat_us=SECOND,lease_us=30*SECOND,review_interval_us=config.idle_review_seconds*SECOND,idle_recall_us=SECOND,queue_capacity=64,schedule_capacity=128,poll_seconds=.2,
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
        extension=r.work.skill_development
        if extension:
            pending=extension.opportunity()
            if pending:return pending
            if r.store.db.execute("SELECT 1 FROM jobs WHERE work_kind='CODE_DEVELOPMENT' AND state NOT IN ('DONE','CANCELLED') LIMIT 1").fetchone():return None
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
    def __init__(self,home,*,clock=None,router=None,bootstrap_grant=False,platform_resolver=None):
        self.home=home_path(home);self.config=load_config(home);self.router=router;self.session=None;self._chat={};self._recent=[];self.closed=False
        from ..continuity.current_state import ProjectStateSource
        self.current_project_state=ProjectStateSource(self.config.project_root,self.config.current_project_state) if self.config.current_project_state else None
        self.clock=clock or Clock()
        with ContinuityStore(self.home/'subject/self.db',self.clock,schema_target=13) as s:
            IdentityService(s,OperatorAuthority());MemoryService(s).entity('project-user','PERSON')
        self.runtime=NanaRuntime(self.home/'subject/self.db',runtime_config(self.config),clock=self.clock)
        try:
            # Upgrade only this application's machine-local review timer. Source,
            # goal, commitment and reactive opportunities retain their own cadence.
            schedule=self.runtime.store.db.execute('SELECT * FROM runtime_schedules WHERE dedupe_key=?',('runtime-review-'+digest('project-work')[:24],)).fetchone()
            interval=self.config.idle_review_seconds*SECOND
            if schedule and schedule['interval_us']!=interval:
                self.runtime.scheduler.reschedule_periodic(schedule['schedule_id'],expected_interval_us=schedule['interval_us'],interval_us=interval)
            if self.config.owned_application_profile:
                from ..continuity.hands.service import HandsWork
                self.work=HandsWork(self.runtime,self.config.owned_application_profile,grant=bootstrap_grant,allow_skills=self.config.allow_local_skills,browser_endpoint=self.config.owned_browser_endpoint)
            else:
                spec=learning_spec(*(read_material(self.config.project_root,m) for m in (self.config.practice,self.config.heldout,self.config.transfer)))
                specs=[spec]
                if self.config.document_learning:
                    if len(self.config.document_learning)!=3:raise CoreError('DOCUMENT_THREE_SPLITS_REQUIRED')
                    from ..continuity.project_work.documents import document_learning_spec
                    specs.append(document_learning_spec(*(read_material(self.config.project_root,m) for m in self.config.document_learning)))
                self.work=ProjectWork(self.runtime,self.config.project_root,self.config.materials,self.home/'reports',tuple(specs),grant=bootstrap_grant,allow_skills=self.config.allow_local_skills,motivation_source='CREATIVE_INTEREST')
                if self.config.allow_local_skills and self.config.document_learning:
                    from .skills import DocumentSkills
                    self.runtime.work.skill_development=DocumentSkills(self, specs[-1])
                self.runtime.work.activity_source=PortfolioOpportunities(self)
            old=self.runtime.store.one('core_meta','runtime.life_control');self.control=json.loads(old['value_json']) if old else {'paused':False,'messages':0}
            self.runtime.work.paused=self.control['paused']
            self.policy=ContextPolicy(policy_id='independent-life',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT','PERSONAL'),remote_privacy=self.config.remote_privacy)
            from .surfaces import SurfaceSession
            self.surfaces=SurfaceSession(self,self.config.surface_bindings)
            from .ingress import SurfaceIngress
            self.ingress=SurfaceIngress(self)
            from .shared import SharedPresence,LifeOpportunities
            self.shared=SharedPresence(self)
            if self.config.shared_presence:self.runtime.work.activity_source=LifeOpportunities(self.runtime.work.activity_source,self.shared)
            self.advanced=None
            if self.config.advanced_life:
                from .advanced import AdvancedLife
                self.advanced=AdvancedLife(self,self.runtime.work.activity_source)
                self.runtime.work.activity_source=self.advanced
            self.bilibili_life = None
            if self.config.bilibili_life and self.config.bilibili_life.enabled:
                from .bilibili_life import BilibiliLife
                self.bilibili_life = BilibiliLife(self, self.runtime.work.activity_source, self.config.bilibili_life)
                self.runtime.work.activity_source = self.bilibili_life
            from ..migration.archive_ingress import ArchiveImportService
            self.legacy_imports = ArchiveImportService(self)
            self.legacy_imports.reconcile()
            self._legacy_review_at = 0
            from .platform_runtime import PlatformRuntime
            self.platforms=PlatformRuntime(self,platform_resolver)
        except BaseException:self.runtime.stop();raise

    def _save_control(self):
        r=self.runtime;r.lease.assert_current();r.store._put('core_meta',{'key':'runtime.life_control','value_json':canonical(self.control)})
    def pause(self,paused=True):
        self.control['paused']=paused;self.runtime.work.paused=paused;self._save_control();return {'autonomy':'PAUSED' if paused else 'RUNNING'}
    def tick(self):
        now = self.runtime.clock.utc_now_us()
        if now >= self._legacy_review_at:
            self.legacy_imports.reconcile()
            self._legacy_review_at = now + 10_000_000
        incoming=self.ingress.drain()
        return {'surface_ingress':incoming} if incoming else self.runtime.step()
    def sources(self):
        r=self.runtime;out=[]
        if self.config.owned_application_profile:return {'owned_target':self.work.port.target.binding,'tasks':list(self.work.port.tasks),'scope':'OWNED_DEV_APPLICATION_ONLY'}
        for material in self.config.materials:
            row=r.store.db.execute("SELECT m.memory_id,m.lifecycle FROM memories m JOIN continuity_evidence e ON e.evidence_id=m.source_evidence_id WHERE e.source_namespace='recorded.project.material' AND e.source_reference=? ORDER BY m.rowid DESC LIMIT 1",('input:'+material.material_id,)).fetchone()
            out.append({'filename':material.relative_path,'material_id':material.material_id,'source_memory_id':row[0] if row else None,'support_state':row[1] if row else 'NOT_YET_OFFERED'})
        return {'approved_sources':out}
    def board(self):
        from .view import life_board
        if self.config.owned_application_profile:
            from ..continuity.hands.view import hands_board
            view=hands_board(self)
        else:view=life_board(self)
        view['shared_experiences']=self.shared.candidates()
        view['surfaces']=[{'binding_id':b.binding_id,'enabled':b.enabled,'mode':b.mode} for b in self.config.surface_bindings]
        view['human_review']='NOT_RUN'
        if self.advanced:view['advanced_life']=self.advanced.view()
        if self.bilibili_life:view['bilibili_life']=self.bilibili_life.view()
        view['platform_runtime']=self.platforms.view()
        return view
    def status(self):
        r=self.runtime
        return {'identity_id':r.identity_id,'autonomy':'PAUSED' if r.work.paused else 'RUNNING','provider':'OFFLINE_NO_PROVIDER' if self.router is None else 'CONFIGURED_NOT_QUALITY_QUALIFIED',
            'provider_readiness':self.provider_readiness(),
            'view':runtime_projection(r,'LIVING_RUNTIME',self.policy,scopes=('project-work',),entity_id='project-user'),
            'learning':[{'state':x['state'],'cursor':x['cursor']} for x in r.store.db.execute("SELECT state,cursor FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid DESC LIMIT 4")],
            'reports':[p.name for p in (self.home/'reports').glob('*.md')], 'pending_authorization':['REAL_PROVIDER_BUDGET_AND_EXPLICIT_SECRET_RESOLVER'] if self.router is None else [],'external_social_delivery':'DISABLED'}
    def provider_readiness(self, *, privacy='PROJECT', operation='COGNITION'):
        from .readiness import provider_readiness
        return provider_readiness(self, privacy=privacy, operation=operation)
    def presence(self,state,*,privacy_classes=('PUBLIC',)):
        from ..continuity.open_agency.delivery import RecipientState
        if state not in {'BUSY','AVAILABLE','UNKNOWN'}:raise CoreError('LOCAL_PRESENCE_INVALID')
        r=self.runtime
        value=RecipientState(resource='synthetic://recipient/project-user',entity_id='project-user',availability=state,observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+60*SECOND,permitted_privacy=privacy_classes)
        # Point-in-time declarations supersede earlier declarations through the
        # existing correction contract. They are not contradictory timeless
        # claims. A separate suffix preserves legacy undated/disputed evidence;
        # no past provenance is rewritten to invent an event time.
        predicate='recipient.'+digest(value.resource)[:32]+'.presence'
        previous=MemoryService(r.store).family('project-user','project-work',predicate)
        current=next((m for m in previous if m['assessment']=='CURRENT' and m['event_time_us'] is not None),None)
        mid=capture(r,'local-presence:'+uid(),value.model_dump(mode='json'),kind='USER_STATEMENT',predicate=predicate,
            event_time_us=value.observed_at_us,correction_of=current['memory_id'] if current else None)
        r.refresh_attention();return {'declared_availability':state,'source_memory_id':mid,'not_inferred_from_contact_frequency':True}
    def _fact_sources(self,privacy=None):
        r=self.runtime;out=[]
        for row in r.store.db.execute("SELECT m.memory_id FROM actions a JOIN continuity_evidence e ON e.source_reference=a.action_id JOIN memories m ON m.source_evidence_id=e.evidence_id WHERE a.capability='world.publish' AND a.state='SUCCEEDED' AND e.source_namespace IN ('recorded.project.local-action','recorded.project.owned-application-action') AND m.lifecycle='ACTIVE' ORDER BY a.rowid DESC LIMIT 3"):
            try:
                memory=MemoryService(r.store).read(row[0])
                from ..continuity.memory import PRIVACY_RANK
                if privacy is not None and PRIVACY_RANK[memory['privacy_class']]>PRIVACY_RANK[privacy]:continue
                out.append(row[0])
            except CoreError:continue
        return tuple(out)
    def _session(self,privacy):
        if self.router is None:raise CoreError('LIVE_PROVIDER_NOT_RUN_OFFLINE_MODE')
        target=self.router.resolve(RouteRequest(operation='COGNITION',privacy_class=privacy,timeout_ms=self.config.provider_timeout_ms,cost_ceiling=self.config.provider_cost_ceiling_micro,context_limit=self.config.provider_context_tokens,output_limit=self.config.provider_output_tokens),self.policy)
        # Additional host ceilings intersect the original Runtime reservations.
        # PREPARED/UNKNOWN attempts count too; absence of a bill is not a refund.
        from .readiness import budget
        budget(self,target.snapshot)
        if self.session is None or self.session.route_snapshot!=target.snapshot:
            if self.session and any(w.is_alive() for w in self.session._workers):raise CoreError('PROVIDER_WORKER_UNRESOLVED')
            self.session=target.cognition_session(self.runtime,project_state_source=self.current_project_state)
            self.session.recover()
        return self.session
    def _model(self,key,phase,mid,text,topic,privacy,cycle=None,retain_shared_life=False,recall_query_terms=()):
        if cycle and cycle.record_id:
            from ..continuity.memory import PRIVACY_RANK
            classification=self.runtime.store.one('continuity_records',cycle.record_id)['privacy_class']
            if PRIVACY_RANK[classification]>PRIVACY_RANK[privacy]:raise CoreError('DIALOGUE_JUDGMENT_PRIVACY_DENIED')
        session=self._session(privacy)
        facts=self._fact_sources(privacy)[:1] if phase=='RENDER' and cycle.context_fit.mode in {'CHAT','SHARE','HELP'} else ()
        from .surfaces import recent_sources
        continuity=recent_sources(self,topic,privacy)
        from ..continuity.memory import PRIVACY_RANK
        recent=[];history_sources=set()
        for turn in reversed(self._recent):
            if turn.topic!=topic or PRIVACY_RANK[turn.privacy_class]>PRIVACY_RANK[privacy]:continue
            try:
                for source in (turn.message_memory_id,*turn.support_memory_ids):
                    row=MemoryService(self.runtime.store).read(source)
                    if PRIVACY_RANK[row['privacy_class']]>PRIVACY_RANK[privacy]:raise CoreError('DIALOGUE_HISTORY_PRIVACY_DENIED')
            except CoreError:continue
            sources={turn.message_memory_id,*turn.support_memory_ids}
            if len(history_sources|sources)>16:continue
            history_sources.update(sources)
            recent.append(turn)
        recent.reverse()
        descriptor=DialogueContext(recent_history_truncated=len(recent)<len(self._recent),retain_shared_life=retain_shared_life,conversation_decision=cycle.conversation_decision if cycle else None,project_status_query=LiteralSpanInterpreter().interpret(text).kind=='PROJECT_STATUS' or bool(cycle and cycle.context_fit.mode=='PROJECT_STATUS'),message_memory_id=mid,topic=topic,privacy_class=privacy,phase=phase,
            judgment=cycle.judgment.stance if cycle else None,intention=cycle.intention.kind if cycle else None,context_mode=cycle.context_fit.mode if cycle else None,effect_status='VERIFIED_EFFECT' if facts else 'NONE')
        data={'dialogue':descriptor.model_dump(mode='json')};volatile={'dialogue':descriptor.model_copy(update={'text':text,'recent_turns':tuple(recent)}).model_dump(mode='json')}
        request=session.prepare(key, 'INTERPRET' if phase=='INTERPRET' else 'SOCIAL',tuple(dict.fromkeys((mid,*facts,*continuity,*(t.message_memory_id for t in recent)))),role_input=data,volatile_input=volatile,query_terms=recall_query_terms if phase=='RENDER' else (),
            budget=CognitionBudget(input_tokens=self.config.provider_context_tokens,output_tokens=self.config.provider_output_tokens,timeout_ms=self.config.provider_timeout_ms,cost_ceiling_micro=self.config.provider_cost_ceiling_micro))
        result=session.execute(request)
        if result['state']!='PROPOSED':raise CoreError(result.get('error_code','DIALOGUE_NOT_PROPOSED'))
        return session,result['record_id']

    def chat(self,text,*,topic='daily',privacy='PERSONAL',message_id=None,surface=None,support_memory_ids=(),source_key=None,retain_shared_life=False,reply_target=None):
        if type(text) is not str or not 1<=len(text)<=2048:raise CoreError('LOCAL_MESSAGE_BOUND')
        if type(retain_shared_life) is not bool:raise CoreError('CONVERSATION_RETENTION_INVALID')
        # An explicit whole rest/return declaration has a delivery-only scope.
        # Do not promote a model interpretation or third-party quotation to it.
        from ..continuity.dialogue_shadow.bridge import rest_delivery_signal
        rest=rest_delivery_signal(text)
        if rest:
            from ..continuity.subject.context_fit import REST_DELIVERY_TOPIC
            topic=REST_DELIVERY_TOPIC
        r=self.runtime;key=message_id or uid();event_key=source_key or 'local.chat.'+key
        if key in self._chat:return {'message_id':key,'state':'ALREADY_REVIEWED_NO_REPLAY'}
        if r.store.db.execute('SELECT 1 FROM subject_events WHERE source_key=?',(event_key,)).fetchone():return {'message_id':key,'state':'ALREADY_REVIEWED_NO_REPLAY'}
        # Metadata has the same classification as its source, and optional
        # approved summary parents participate in normal privacy/deletion closure.
        from ..continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
        memory=MemoryService(r.store);reference='message:'+digest(event_key)
        from ..continuity.contracts import PENDING_LOCAL_RECEIPT
        body=PENDING_LOCAL_RECEIPT
        old=r.store.db.execute("SELECT observed_time_us FROM continuity_evidence WHERE source_namespace='recorded.local.message' AND source_reference=?",(reference,)).fetchone()
        eid=memory.capture(EvidenceInput(provenance=Provenance(domain='LOCAL_INTERACTION_METADATA',source_namespace='recorded.local.message',source_reference=reference,source_kind='DIRECT_OBSERVATION'),text=body,privacy_class=privacy,observed_time_us=old[0] if old else r.clock.utc_now_us()))
        mid=memory.add(MemoryCandidate(entity_id=r.config.entity_id,scope=r.config.scopes[0],memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=body,derived_from=tuple(support_memory_ids)))
        if retain_shared_life:
            from ..continuity.person_self import retain_input
            mid=retain_input(r.store,entity_id=r.config.entity_id,scope=r.config.scopes[0],text=text,privacy=privacy,message_id=event_key)
        proposal=None;recall_query_terms=()
        literal=LiteralSpanInterpreter().interpret(text);kind=literal.kind if literal.basis=='LITERAL_SPAN' else 'UNCLEAR';basis='EXPLICIT' if literal.basis=='LITERAL_SPAN' else 'INTERPRETED';rid=None;provider_state='LIVE_PROVIDER_NOT_RUN'
        try:
            from ..continuity.subject.context_fit import depth_boundary
            closed,_,_=depth_boundary(r.store,'project-user','project-work',topic,r.config.privacy_classes)
            if closed or kind in {'DECLINE_DEPTH','DECLINE_DELIVERY','REOPEN','REOPEN_DELIVERY'}:raise CoreError('TOPIC_BOUNDARY_NO_MODEL_CALL')
            session,rid=self._model('life.interpret.'+key,'INTERPRET',mid,text,topic,privacy,retain_shared_life=retain_shared_life)
            meaning=session.proposal(rid).proposal.dialogue
            recall_query_terms=session.take_recall_terms(rid)
            proposal=meaning.conversation_proposal if retain_shared_life else None
            # Literal user boundary beats contradictory model interpretation.
            if kind not in {'DECLINE_DEPTH','DECLINE_DELIVERY','REOPEN','REOPEN_DELIVERY','PROJECT_STATUS'}:

                kind=meaning.kind if meaning.confidence in {'RELEVANT','HIGH'} else 'UNCLEAR'
                basis='MODEL_PROPOSAL' if meaning.confidence in {'RELEVANT','HIGH'} else 'INTERPRETED'
            provider_state='MODEL_PROPOSAL_ACCEPTED_NOT_QUALITY_QUALIFIED'
        except CoreError as exc:provider_state=exc.code
        event=SubjectInput(realization_target=reply_target,conversation_proposal=proposal,domain='LOCAL_INTERACTION',source_key=event_key,kind='INTERACTION',origin='USER',entity_id='project-user',scope='project-work',observed_at_us=surface.observed_at_us if surface else r.clock.utc_now_us(),occurred_at_us=surface.occurred_at_us if surface else None,privacy_class=privacy,surface=surface,
            text='Local input reviewed meaning: '+kind,source_memory_ids=(mid,),interaction_signal=InteractionSignal(kind=kind,topic_key=topic,basis=basis,proposal_record_id=rid))
        qid=r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=event,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us(),priority=3))
        outcome=r.step();queue=r.store.one('runtime_queue',qid)
        if not outcome or not outcome.get('cycle') or queue['state']!='DONE':raise CoreError('LOCAL_INTERACTION_PENDING')
        cycle=outcome['cycle'];draft=None;render_state='NOT_RUN';render_rid=None
        if cycle.context_fit.mode!='RESPECT_BOUNDARY' and self.router is not None and provider_state=='MODEL_PROPOSAL_ACCEPTED_NOT_QUALITY_QUALIFIED':
            try:
                session,render_rid=self._model('life.render.'+key,'RENDER',mid,text,topic,privacy,cycle,retain_shared_life=retain_shared_life,recall_query_terms=recall_query_terms)
                draft=session.take_dialogue_draft(render_rid);render_state='UNVERIFIED_MODEL_WORDING'
            except CoreError as exc:render_state=exc.code
        if not draft:
            draft={'VENT':'离线模式：我在听；这次不把倾诉变成研究。','HELP':'离线语义受限：可用 /work 选择已批准的源码材料。','SHARE':'离线模式：收到你的分享；没有另开任务。','CHAT':'离线模式：可以闲聊，真实语言模型尚未配置。',
                   'PROJECT_STATUS':'已识别为项目状态询问；当前未生成模型措辞。','RESPECT_BOUNDARY':'这个话题先停在这里。','CORRECTION':'我会先澄清更正的内容，不直接改写历史。'}.get(cycle.context_fit.mode,'离线语义受限：你希望我听你说，还是一起处理具体问题？')
        if self.router is not None and not render_state=='UNVERIFIED_MODEL_WORDING' and cycle.context_fit.mode!='RESPECT_BOUNDARY':
            # A configured provider can be budget-blocked after valid interpretation.
            # Do not falsely report that no model is configured or pretend this is generated speech.
            draft='本次没有生成模型回复（'+(render_state if render_state!='NOT_RUN' else provider_state)+'）。'
        if rest and render_state!='UNVERIFIED_MODEL_WORDING':
            draft='好，先休息吧。想聊时再来。' if rest=='DECLINE_DELIVERY' else '欢迎回来。'
            render_state='LOCAL_DELIVERY_BOUNDARY_ACKNOWLEDGEMENT'
        if cycle.intention_id and reply_target is None:
            current=r.store.one('subject_intentions',cycle.intention_id)
            if current['state']=='PENDING':r.subject.transition_intention(cycle.intention_id,expected_revision=current['revision'],state='DROPPED')
        from .dialogue_contracts import DialogueTurn
        # Both sides are transient by default, and every assistant turn retains
        # all source dependencies so forgetting cannot resurrect old wording.
        supports=RecordService(r.store).support(render_rid) if render_rid else ()
        exchange_id=None
        if render_state=='UNVERIFIED_MODEL_WORDING' and len(supports)<=64:
            self._recent.append(DialogueTurn(message_memory_id=mid,topic=topic,privacy_class=privacy,speaker='USER',text=text[:1024]))
            self._recent.append(DialogueTurn(message_memory_id=mid,topic=topic,privacy_class=privacy,speaker='ASSISTANT',text=draft[:1024],support_memory_ids=supports))
            self._recent=self._recent[-6:]
        # Explicit retention records what was actually said, including a local
        # boundary acknowledgement or a provider-unavailable explanation. It
        # does not certify model availability or the truth of the wording.
        if retain_shared_life and len(supports)<=64:
            from ..continuity.person_self import retain_exchange
            exchange_id=retain_exchange(r.store,entity_id=r.config.entity_id,scope=r.config.scopes[0],topic=topic,user_memory_id=mid,text=draft,cycle=cycle,source_memory_ids=supports)
        self.control['messages']+=1;self._save_control();self._chat[key]=True
        if len(self._chat)>64:self._chat.pop(next(iter(self._chat)))
        route=None
        if render_rid and render_state=='UNVERIFIED_MODEL_WORDING' and self.session.route_snapshot:
            route=self.session.route_snapshot.model_dump(mode='json')
            route['returned_model_id']=self.session.proposal(render_rid).model_id
        return {'message_id':key,'message_memory_id':mid,'provider_state':provider_state,'render_state':render_state,'route':route,'mode':cycle.context_fit.mode,'judgment':cycle.judgment.stance,'intention':cycle.intention.kind,'text':draft,'raw_body_persisted':retain_shared_life,'exchange_record_id':exchange_id,'conversation_decision':cycle.conversation_decision.model_dump(mode='json') if cycle.conversation_decision else None,'external_social_send':False,
            'cycle_id':cycle.cycle_id,'cycle_record_id':cycle.record_id,'intention_id':cycle.intention_id}

    def forget(self,mid):
        MemoryService(self.runtime.store,self.runtime.authority).forget(mid,self.runtime.authority)
        self._recent=[t for t in self._recent if t.message_memory_id!=mid]
        return {'forgotten':mid}
    def revoke(self):
        k=self.runtime.work.agency.realization.kernel
        for row in self.runtime.store.all('grants'):
            if not row['revoked']:k.revoke(row['grant_id'],self.runtime.authority)
        return {'local_execution':'REVOKED_NO_REGRANT_ON_RESTART'}
    def close(self):
        if not self.closed:
            self.closed=True;self._recent.clear();self.ingress.close()
            if self.session:
                self.session._volatile_inputs.clear();self.session._volatile_dialogue.clear()
                self.session._volatile_recall.clear()
                if hasattr(self.session.transport,'_credential'):self.session.transport._credential=None
            self.runtime.stop()
    def __enter__(self):return self
    def __exit__(self,*unused):self.close()
