"""One-command cross-domain synthetic life on the actual existing subject/runtime.

No real model, social account, video, private input, device or network endpoint.
"""
import argparse,json,tempfile,time
from pathlib import Path
from ..actions import OperatorAuthority
from ..contracts import CoreError,GrantSpec
from ..storage import canonical,digest
from ..continuity import ContinuityStore,IdentityService
from ..continuity.memory import MemoryService
from ..continuity.records import RecordService
from ..continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..continuity.subject import SubjectInput,PreferenceSignal
from ..continuity.subject.opportunities import ConcernCue
from ..continuity.agency_contracts import GoalReviewRef
from ..continuity.relational.bootstrap import SubjectBootstrapService,SubjectBootstrapAuthority
from ..continuity.relational.contracts import SubjectPersonalitySeed,RelationalAnchorSpec,RelationalRequest
from ..continuity.relational.projections import social_appetite
from ..continuity.relational.accommodation import OfflineAccommodationPolicy
from ..continuity.open_agency.service import OpenGoalPolicy
from ..continuity.open_agency.contracts import Objective,Operator
from ..continuity.open_agency.delivery import DeliveryPolicy,DeliveryAdmission,RecipientState
from ..continuity.open_agency.exploration import ExplorationService,FixtureContentUnderstandingPort,ContentFeed,ContentItem
from ..continuity.open_agency.code_skills import CodeSkillService,CodeSpec,FixtureCodeProposer
from ..continuity.open_agency.learning import LearningCase
from ..continuity.open_agency.fixtures import numeric_learning,language_learning,numeric_objective,feed_objective
from ..continuity.providers import ProviderRegistry,ProviderDescriptor
from ..continuity.context import ContextPolicy
from ..continuity.application import FrontendPolicy
from ..continuity.extensions import SurfaceEnvelope
from ..continuity.autonomy.fixture_effects import OfflineEffectPort
from ..continuity.autonomy.governance import GovernanceController,ManagerConstraint
from ..continuity.autonomy.contracts import RealizationTarget
from .runtime import NanaRuntime
from .contracts import RuntimeConfig,LivingRuntimeConfig,RuntimeEvent,Cause,SECOND,HOUR,DAY
from .authority import VirtualClock


def run_demo(directory):
    root=Path(directory);path=root/'subject'/'self.db';world=root/'world'/'life.fixture.json'
    if path.exists():raise CoreError('DEMO_REQUIRES_FRESH_DIRECTORY')
    started=time.monotonic_ns();clock=VirtualClock();report={'domain':'OFFLINE_SYNTHETIC_ONLY','real_models':0,'real_social_delivery':0,'real_private_data':0,'real_external_actions':0}
    config=RuntimeConfig(schema_target=12,living=LivingRuntimeConfig(maintenance_interval_us=SECOND),scopes=('life',),entity_id='synthetic-primary',idle_recall_us=SECOND,review_interval_us=HOUR,lease_us=HOUR,heartbeat_us=SECOND)
    with ContinuityStore(path,clock,schema_target=12) as s:
        IdentityService(s,OperatorAuthority())
        for e in ('synthetic-primary','synthetic-friend'):MemoryService(s).entity(e,'PERSON')
    seq=0
    with NanaRuntime(path,config,clock=clock) as r:
        identity=r.identity_id;records=RecordService(r.store)
        def memory(key,text,*,predicate=None,entity=config.entity_id,privacy='PERSONAL'):
            m=MemoryService(r.store)
            e=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.open-demo',source_reference=key,source_kind='DIRECT_OBSERVATION'),text=text,privacy_class=privacy,observed_time_us=r.clock.utc_now_us()))
            return m.add(MemoryCandidate(entity_id=entity,scope='life',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=e,text=text,predicate_key=predicate))
        def send(*,kind='WAKE',origin='SELF_WAKE',entity=config.entity_id,**kw):
            nonlocal seq
            seq+=1;inp=SubjectInput(source_key='synthetic.open-demo.'+str(seq),kind=kind,origin=origin,entity_id=entity,scope='life',observed_at_us=r.clock.utc_now_us(),**kw)
            q=r.submit(RuntimeEvent(event_type='USER_EVENT' if origin=='USER' else 'WORLD_EVENT' if origin=='ENVIRONMENT' else 'SELF_EVENT',trigger='INCOMING_EVENT' if origin!='SELF_WAKE' else 'SELF_TRIGGER',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=identity),),due_at_us=r.clock.utc_now_us(),priority=3 if origin=='USER' else 2))
            for _ in range(128):
                result=r.step()
                if result and result.get('queue_id')==q and result.get('cycle'):return result['cycle']
            raise CoreError('DEMO_EVENT_DID_NOT_COMPLETE')
        foreground_work=None
        def ticks(count):
            nonlocal seq,foreground_work
            for _ in range(count):
                clock.advance(SECOND);r.refresh_attention()
                for _ in range(96):
                    result=r.step()
                    if result is None:break
                    if not foreground_work:
                        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' AND state='WAITING' LIMIT 1").fetchone()
                        if job:
                            seq+=1;inp=SubjectInput(source_key='synthetic.open-demo.foreground.'+str(seq),kind='INTERACTION',origin='USER',entity_id=config.entity_id,scope='life',observed_at_us=r.clock.utc_now_us(),text='A fictional foreground input during learning.',significance='RELEVANT')
                            qid=r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=identity),),due_at_us=r.clock.utc_now_us(),priority=3))
                            first=r.step();report['user_preempts_background_learning']=first['queue_id']==qid and r.store.one('jobs',job['job_id'])['cursor']==job['cursor']
                            foreground_work=(job['job_id'],job['cursor'])
                if foreground_work:
                    j=r.store.one('jobs',foreground_work[0]);report['interrupted_learning_resumes']=j['cursor']>foreground_work[1]

        def concern(obj):
            cue=ConcernCue(cue_kind='OPEN_LOOP',motivation_source=obj.motivation_source,topic_key=obj.objective_id.replace('.','-'),program_id=obj.objective_id)
            return memory(obj.objective_id,cue.model_dump_json(),predicate='concern.'+obj.objective_id)
        boot=SubjectBootstrapAuthority();bootstrap=SubjectBootstrapService(r.store,boot)
        bootstrap.install(SubjectPersonalitySeed(identity_id=identity,scope='life',revision=1,relational_accommodation='HIGH',conviction_persistence='HIGH'),boot)
        bootstrap.install(RelationalAnchorSpec(identity_id=identity,anchor_id='primary',entity_id=config.entity_id,role_kind='PRIMARY_USER',role_label='companion',scope='life',revision=1,effective_from_us=r.clock.utc_now_us()),boot)
        r.work.accommodation_policy=OfflineAccommodationPolicy(max_duration_us=DAY)
        for _ in range(2):send(kind='OUTCOME',origin='ENVIRONMENT',text='An independent synthetic social experience was interesting.',significance='RELEVANT',preference_signal=PreferenceSignal(topic='social_exploration',direction='SUPPORT',interpretation='Sourced fictional social interest'))
        appetite=social_appetite(r.store,scope='life',privacy_classes=('PERSONAL',)).state
        request=RelationalRequest(request_id='ordinary',requesting_entity='synthetic-friend',operation='REFRAIN',behavior_domain='SOCIAL_NEW_CONTACTS',duration_us=SECOND)
        ordinary=send(kind='INTERACTION',origin='USER',entity='synthetic-friend',text='A finite fictional request for quiet company.',significance='RELEVANT',relational_request=request)
        primary=send(kind='INTERACTION',origin='USER',text='The same finite fictional request.',significance='RELEVANT',relational_request=request.model_copy(update={'request_id':'primary','requesting_entity':config.entity_id}))
        report['primary_user_influences_choice']=ordinary.relational_decision.response.decision=='DECLINE' and primary.relational_decision.response.decision=='ACCEPT'
        report['voluntary_accommodation_preserves_desire']=social_appetite(r.store,scope='life',privacy_classes=('PERSONAL',)).state==appetite=='SEEKING'
        report['relationship_does_not_grant']=not r.store.all('grants')
        ticks(2)
        rest=ConcernCue(cue_kind='LOAD_STATE',motivation_source='REST',topic_key='rest',cognitive_load='HIGH',possible_behaviors=('REST',),valid_until_us=r.clock.utc_now_us()+SECOND)
        rest_mid=memory('rest',rest.model_dump_json(),predicate='concern.rest')
        report['rest_is_valid']=send(source_memory_ids=(rest_mid,)).intention.behavior=='REST'
        ticks(2)
        contact='synthetic://contact/friend'
        social=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='RELATIONSHIP',topic_key='connection',possible_behaviors=('SOCIALIZE',),resource_ref=contact,resource_class='ORDINARY',availability='BUSY')
        social_mid=memory('social-wish',social.model_dump_json(),predicate='concern.connection')
        availability=RecipientState(resource=contact,entity_id='synthetic-friend',availability='BUSY',observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+HOUR,permitted_privacy=('PERSONAL',))
        memory('busy',availability.model_dump_json(),predicate='recipient.'+digest(contact)[:32],entity='synthetic-friend')
        delivery=DeliveryAdmission(r.store,DeliveryPolicy(recipients=(contact,),privacy_classes=('PERSONAL',),quiet_start_utc_hour=0,quiet_end_utc_hour=0),scopes=('life',),privacy_classes=config.privacy_classes)
        wish=send(source_memory_ids=(social_mid,),realization_target=RealizationTarget(capability='world.contact',operation='CONTACT',resource=contact,resource_class='ORDINARY'))
        assessed=delivery.assess(wish,contact)
        report['busy_defers_delivery_not_will']=wish.evaluation.normative=='ENDORSED' and assessed['result']=='DEFER_BUSY'
        report['no_contact_from_desire']=not r.store.all('actions')
        nums,feed=numeric_objective(),feed_objective();policy=OpenGoalPolicy((nums,feed));port=OfflineEffectPort(identity,world)
        r.work.configure_open_agency(policy,port);r.work.agency.delivery=delivery;port.delivery=delivery
        r.work.configure_open_learning((numeric_learning(),language_learning()))
        providers=ProviderRegistry();providers.register(ProviderDescriptor(provider_id='fixture.media',model_id='fixture.video',model_version='1',operations=('VIDEO_UNDERSTAND',),input_modalities=('TEXT','VIDEO'),output_modalities=('TEXT',),context_limit=16384,output_limit=4096,locality='LOCAL_FIXTURE',permitted_privacy=('PUBLIC','PERSONAL')),FixtureContentUnderstandingPort())
        context_policy=ContextPolicy(policy_id='local-reference',allowed_scopes=('life',),readable_privacy=('PUBLIC','PERSONAL'))
        r.work.exploration=ExplorationService(r.store,providers,context_policy,'fixture.video',('learn.language',))
        port.seed_observation(nums.operators[0].resource,[1.2,2.3])
        clips=ContentFeed(items=(ContentItem(content_id='clip',media_type='VIDEO',topic='language',learning_key='learn.language',source_reference='synthetic.clip',occurred_at_us=r.clock.utc_now_us(),privacy_class='PUBLIC'),))
        port.seed_observation(feed.operators[0].resource,clips.model_dump(mode='json'))
        gov=GovernanceController(r.store,r.authority);gov.initialize(r.authority);kernel=r.work.agency.realization.kernel
        resources=tuple({op.resource for o in (nums,feed) for op in o.operators}|{'synthetic://skill/input','synthetic://skill/output'})
        now=r.clock.utc_now_us();kernel.grant(GrantSpec(capabilities=tuple(kernel.capabilities)+(kernel.verify_capability,),resources=resources,not_before_us=now,expires_at_us=now+DAY),r.authority)
        kernel.set_budgets({'write_attempts':40,'external_requests':300,'cost_micro_units':300},r.authority)
        veto=ManagerConstraint(constraint_id='hold-report',revision=1,issuer=r.authority.principal,source_reference='synthetic.review',identity_id=identity,scope='life',targets=(nums.operators[-1].target(),),effective_from_us=now,expires_at_us=now+DAY,reason_code='HOLD_REPORT')
        gov.install(veto,r.authority)
        num_mid=concern(nums);feed_mid=concern(feed)
        send(source_memory_ids=(num_mid,));send(source_memory_ids=(feed_mid,))
        report['multiple_persistent_goals']=len(r.store.all('goals'))==2
        ticks(18)
        goal=next(g for g in r.store.all('goals') if g['template']=='numbers')
        report['failure_triggered_learning']=any(e['task_class']=='numbers' and e['outcome']=='FAILURE' for e in r.store.all('experiences')) and r.work.open_learning.strategy('numbers','life') is not None
        report['interest_triggered_learning']=r.work.open_learning.strategy('language','life') is not None
        report['wanted_but_manager_blocked']=goal['state']=='BLOCKED' and bool([i for i in r.store.all('subject_intentions') if i['state']=='MANAGER_BLOCKED'])
        count=len(r.store.all('actions'));gov.revoke(veto.constraint_id,expected_revision=1,authority=r.authority);r.drain(20)
        report['revocation_does_not_execute']=len(r.store.all('actions'))==count
        clock.advance(1);cause=memory('fresh-review','An independently observed synthetic policy change offers reconsideration.')
        goal=r.store.one('goals',goal['goal_id'])
        send(source_memory_ids=(cause,),goal_review=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=cause),task_class='numbers')
        ticks(8)
        report['same_goal_replanned_and_completed']=r.store.one('goals',goal['goal_id'])['state']=='COMPLETED'
        report['old_failure_preserved']=any(e['outcome']=='FAILURE' for e in r.store.all('experiences'))
        gap=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='CAPABILITY_GAP',topic_key='precision-skill',possible_behaviors=('SEEK_CAPABILITY',))
        gap_mid=memory('code-gap',gap.model_dump_json(),predicate='concern.precision-skill');need=send(source_memory_ids=(gap_mid,))
        skills=CodeSkillService(r.store,r.authority);port.code_skills=skills;spec=CodeSpec(name='fractional-total',revision=1,purpose='Retain numeric precision in a bounded local transform',task='FRACTIONAL_TOTAL');proposer=FixtureCodeProposer()
        tests=(LearningCase(case_id='case-a',context='test',data=[.25,.5],expected=.75),LearningCase(case_id='case-b',context='transfer',data=[1.5,3],expected=4.5))
        failed=skills.test(skills.propose(need,spec,proposer),tests)
        fixed=skills.test(skills.propose(need,spec.model_copy(update={'revision':2}),proposer,diagnostic='Fractional precision was lost in executed tests'),tests)
        sha=records.read(fixed)['payload']['source_digest'];before=len(r.store.all('grants'));active=skills.review(fixed,authority=r.authority,expected_digest=sha)
        report['generated_code_failed_then_repaired']=records.read(failed)['payload']['state']=='REJECTED' and records.read(active)['payload']['state']=='ACTIVE'
        report['skill_review_does_not_grant']=len(r.store.all('grants'))==before
        package=skills.package(active,root/'skill-candidate');report['skill_package']=package
        # C has processed the source need; close the selected development proposal,
        # not an external action, before offering use of its independently tested tool.
        if need.intention_id:r.subject.transition_intention(need.intention_id,expected_revision=1,state='COMPLETED')
        use=Objective(objective_id='project.skill-use',scope='life',motivation_source='SELF_DEVELOPMENT',task_domain='precision',desired=('evaluated',),operators=(
            Operator(operator_id='inspect',capability='world.observe',resource='synthetic://skill/input',produces=('input',),args={}),
            Operator(operator_id='use',capability='world.skill',resource='synthetic://skill/output',requires=('input',),produces=('evaluated',),args={'skill_record_id':active,'input_from':'inspect'},expected_digest=digest(6.25))))
        policy.objectives[use.objective_id]=use;port.seed_observation('synthetic://skill/input',[2.25,4])
        use_mid=concern(use);send(source_memory_ids=(use_mid,));ticks(4)
        report['generated_skill_executed_through_kernel']=any(a['capability']=='world.skill' and a['state']=='SUCCEEDED' for a in r.store.all('actions'))
        skills.retire(active,authority=r.authority)
        try:skills.invoke(active,[1,2]);report['skill_rollback_disables']=False
        except CoreError:report['skill_rollback_disables']=True
        app=r.application(providers=providers,bootstrap_authority=boot)
        client=app.session(FrontendPolicy(context=context_policy,entity_id=config.entity_id,commands=('SEND_INPUT',)))
        for platform in ('fixture.desktop','fixture.mobile'):
            env=SurfaceEnvelope(subject_id=identity,platform=platform,surface=platform+'.chat',adapter='fixture.adapter',entity_id=config.entity_id,conversation_id='synthetic-conversation',session_id='synthetic-session',event_kind='message.input',observed_at_us=r.clock.utc_now_us(),correlation_id=platform,privacy_class='PERSONAL',source_reference='synthetic.cross-surface',source_event_key=platform)
            inp=SubjectInput(source_key='synthetic.placeholder',kind='INTERACTION',origin='USER',entity_id=config.entity_id,scope='life',observed_at_us=r.clock.utc_now_us(),text='A fictional continuity check',significance='RELEVANT')
            receipt=client.send_input(env,inp);r.drain(32);receipt.wait(.1)
        views=[client.view('CONTINUITY',scope='life',tier=t) for t in ('L0_LIVE','L1_RECENT','L2_DURABLE')]
        report['two_surfaces_one_subject']=all(v.subject_id==identity and len(v.surfaces)==2 for v in views)
        open_view=json.loads(client.view('OPEN_AUTONOMY',scope='life').data_json)
        report['frontend_reads_actual_work']=len(open_view['goals'])==3 and len(open_view['learning'])==2 and len(open_view['skills'])>=1
        report['learning_comparison']=[{'domain':v['domain'],'cause':v['cause'],'baseline_passed':v['baseline_passed'],'transfer_passed':v['transfer_passed'],'stage':v['stage']} for v in open_view['learning']]
        # Demonstrate source erasure invalidates strategy and its derived views.
        MemoryService(r.store,r.authority).forget(feed_mid,r.authority)
        report['deleted_source_invalidates_learning']=r.work.open_learning.strategy('language','life') is None
        report['deleted_source_removed_from_view']=not any(v['domain']=='language' for v in json.loads(client.view('OPEN_AUTONOMY',scope='life').data_json)['learning'])
        clock.advance(SECOND);r.step()
        epoch=r.lease.epoch;report['goal_states']=[g['state'] for g in r.store.all('goals')]
        report['actions']=len(r.store.all('actions'));report['model_calls']=len(r.store.all('runtime_cognition_calls'))
        report['kernel_budget']=[{'dimension':b['dimension'],'held':b['held'],'spent':b['spent']} for b in r.store.all('budgets')]
        report['one_store_one_subject_loop']=r.subject.store is r.store and r.work.agency.store is r.store
    with NanaRuntime(path,config,clock=clock) as r:
        report['restart_same_identity']=r.identity_id==identity;report['restart_fresh_epoch']=r.lease.epoch>epoch
        report['restart_retains_goals_and_learning']=len(r.store.all('goals'))==3 and r.store.db.execute("SELECT count(*) FROM jobs WHERE work_kind='LEARNING'").fetchone()[0]==2
        report['no_local_authority_reconstructed']=r.work.agency is None and r.work.open_learning is None
    report['measured_wall_ms']=(time.monotonic_ns()-started)//1000000
    report['provider_cost']='FIXTURE_ZERO_REAL_COST; Kernel units are synthetic budgets, not provider billing'
    return report

def run_contrast(directory):
    """Same subject/runtime mechanism, different history/motives/plans/results."""
    root=Path(directory);path=root/'subject'/'self.db';clock=VirtualClock()
    if path.exists():raise CoreError('DEMO_REQUIRES_FRESH_DIRECTORY')
    with ContinuityStore(path,clock,schema_target=12) as s:
        IdentityService(s,OperatorAuthority());MemoryService(s).entity('synthetic-observer','PERSON')
    ordered=Objective(objective_id='create.arrangement',scope='life',motivation_source='CREATIVE_INTEREST',task_domain='arrangement',desired=('arranged',),operators=(
        Operator(operator_id='inspect',capability='world.observe',resource='synthetic://arrange/input',produces=('seen',),args={}),
        Operator(operator_id='sort',capability='world.compute',resource='synthetic://arrange/result',requires=('seen',),produces=('arranged',),args={'method':'SORT','input_from':'inspect'},expected_digest=digest([1,2,3]))))
    text=Objective(objective_id='project.format',scope='life',motivation_source='PROJECT_COMPLETION',task_domain='formatting',desired=('formatted',),priority=2,operators=(
        Operator(operator_id='inspect',capability='world.observe',resource='synthetic://format/input',produces=('seen',),args={}),
        Operator(operator_id='lower',capability='world.compute',resource='synthetic://format/lower',requires=('seen',),produces=('lowered',),args={'method':'CASEFOLD','input_from':'inspect'}),
        Operator(operator_id='words',capability='world.compute',resource='synthetic://format/words',requires=('lowered',),produces=('words',),args={'method':'UNICODE_WORDS','input_from':'lower'}),
        Operator(operator_id='join',capability='world.compute',resource='synthetic://format/join',requires=('words',),produces=('formatted',),args={'method':'JOIN','input_from':'words'},expected_digest=digest('hello world'))))
    config=RuntimeConfig(schema_target=12,living=LivingRuntimeConfig(),scopes=('life',),entity_id='synthetic-observer',idle_recall_us=HOUR)
    with NanaRuntime(path,config,clock=clock) as r:
        port=OfflineEffectPort(r.identity_id,root/'world'/'contrast.fixture.json');r.work.configure_open_agency(OpenGoalPolicy((ordered,text)),port)
        GovernanceController(r.store,r.authority).initialize(r.authority);k=r.work.agency.realization.kernel
        k.grant(GrantSpec(capabilities=tuple(k.capabilities)+(k.verify_capability,),resources=tuple({op.resource for obj in (ordered,text) for op in obj.operators}),not_before_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+DAY),r.authority)
        k.set_budgets({'write_attempts':16,'external_requests':64,'cost_micro_units':64},r.authority)
        for obj,data in ((ordered,[3,1,2]),(text,'Hello\tWORLD')):
            port.seed_observation(obj.operators[0].resource,data)
            cue=ConcernCue(cue_kind='OPEN_LOOP',motivation_source=obj.motivation_source,topic_key=obj.objective_id.replace('.','-'),program_id=obj.objective_id)
            memory=MemoryService(r.store);eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.contrast',source_reference=obj.objective_id,source_kind='DIRECT_OBSERVATION'),text=cue.model_dump_json(),observed_time_us=r.clock.utc_now_us(),privacy_class='PROJECT'))
            mid=memory.add(MemoryCandidate(entity_id=config.entity_id,scope='life',memory_type=MemoryType.PROJECT,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=cue.model_dump_json(),predicate_key='concern.'+obj.objective_id))
            inp=SubjectInput(source_key='synthetic.contrast.'+obj.objective_id,kind='WAKE',origin='SELF_WAKE',entity_id=config.entity_id,scope='life',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),privacy_class='PROJECT')
            r.submit(RuntimeEvent(event_type='SELF_EVENT',trigger='SELF_TRIGGER',input=inp,causes=(Cause(kind='MEMORY',reference_id=mid),),due_at_us=r.clock.utc_now_us(),priority=2));r.drain(8)
        for _ in range(8):clock.advance(SECOND);r.drain(16)
        goals=r.store.all('goals');records=RecordService(r.store)
        plans=[records.read(json.loads(g['body_json'])['plan_record_id'])['payload'] for g in goals]
        return {'domain':'OFFLINE_SYNTHETIC_CONTRAST','different_motives':{o.motivation_source for o in (ordered,text)}=={'CREATIVE_INTEREST','PROJECT_COMPLETION'},'plan_lengths':sorted(len(p['steps']) for p in plans),'both_goals_completed':len(goals)==2 and all(g['state']=='COMPLETED' for g in goals),'actual_verified_actions':len([a for a in r.store.all('actions') if a['state']=='SUCCEEDED']),'no_user_input':not r.store.db.execute("SELECT 1 FROM subject_events WHERE origin='USER'").fetchone(),'one_subject':r.subject.store is r.store,'real_models':0,'real_external_actions':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory');parser.add_argument('--output');parser.add_argument('--contrast',action='store_true');args=parser.parse_args()
    runner=run_contrast if args.contrast else run_demo
    if args.directory:report=runner(args.directory)
    else:
        with tempfile.TemporaryDirectory(prefix='open-subject-life-') as root:report=runner(root)
    raw=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:Path(args.output).write_text(raw)
    print(raw,end='')
    if any(type(v) is bool and not v for v in report.values()):raise SystemExit(1)
if __name__=='__main__':main()
