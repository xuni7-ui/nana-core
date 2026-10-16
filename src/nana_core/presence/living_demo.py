"""Reproducible synthetic life on the actual Runtime; no real body/model/service."""
import argparse,json,tempfile
from pathlib import Path
from ..actions import OperatorAuthority
from ..contracts import GrantSpec,CoreError
from ..storage import digest
from ..continuity import ContinuityStore,IdentityService
from ..continuity.memory import MemoryService
from ..continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from ..continuity.subject import SubjectInput,PreferenceSignal
from ..continuity.subject.opportunities import ConcernCue
from ..continuity.relational.bootstrap import SubjectBootstrapService,SubjectBootstrapAuthority
from ..continuity.relational.contracts import RelationalAnchorSpec,SubjectPersonalitySeed,RelationalRequest
from ..continuity.relational.projections import social_appetite
from ..continuity.relational.accommodation import OfflineAccommodationPolicy
from ..continuity.agency import OfflineGoalPolicy
from ..continuity.agency_contracts import OfflineProgram
from ..continuity.autonomy.fixture_effects import OfflineEffectPort
from ..continuity.autonomy.governance import GovernanceController,ManagerConstraint
from ..continuity.autonomy.contracts import RealizationTarget
from ..continuity.skills import OfflineLearningPolicy,OfflineSkillService
from ..continuity.context import ContextPolicy
from ..continuity.application import FrontendPolicy
from ..continuity.providers import ProviderRegistry
from ..continuity.extensions import SurfaceEnvelope
from .runtime import NanaRuntime
from .contracts import RuntimeConfig,LivingRuntimeConfig,RuntimeEvent,Cause,SECOND,HOUR,DAY
from .authority import VirtualClock


def run_demo(root):
    root=Path(root)
    if (root/'subject'/'self.db').exists():raise CoreError('DEMO_REQUIRES_FRESH_DIRECTORY')
    clock=VirtualClock();path=root/'subject'/'self.db';world=root/'world'/'effects.fixture.json'
    config=RuntimeConfig(schema_target=11,living=LivingRuntimeConfig(maintenance_interval_us=SECOND),scopes=('life',),entity_id='synthetic-primary',idle_recall_us=SECOND,review_interval_us=6*HOUR,lease_us=3*HOUR,heartbeat_us=HOUR)
    with ContinuityStore(path,clock,schema_target=11) as s:
        IdentityService(s,OperatorAuthority())
        for entity in ('synthetic-primary','synthetic-ordinary'):MemoryService(s).entity(entity,'PERSON')
    report={'scope':'OFFLINE_SYNTHETIC_ONLY','real_models':0,'real_private_data':0,'real_external_actions':0};sequence=0
    with NanaRuntime(path,config,clock=clock) as r:
        identity=r.identity_id;boot=SubjectBootstrapAuthority();bootstrap=SubjectBootstrapService(r.store,boot)
        bootstrap.install(SubjectPersonalitySeed(identity_id=identity,scope='life',revision=1,relational_accommodation='HIGH',conviction_persistence='HIGH'),boot)
        bootstrap.install(RelationalAnchorSpec(identity_id=identity,anchor_id='primary',entity_id=config.entity_id,role_kind='PRIMARY_USER',role_label='companion',scope='life',revision=1,effective_from_us=r.clock.utc_now_us()),boot)
        r.work.accommodation_policy=OfflineAccommodationPolicy(max_duration_us=DAY)
        r.work.learning_policy=OfflineLearningPolicy()
        def send(kind='INTERACTION',origin='USER',entity=None,**fields):
            nonlocal sequence
            sequence+=1
            inp=SubjectInput(source_key='synthetic.demolife.'+str(sequence),kind=kind,origin=origin,entity_id=entity or config.entity_id,scope='life',observed_at_us=r.clock.utc_now_us(),**fields)
            qid=r.submit(RuntimeEvent(event_type='USER_EVENT' if origin=='USER' else 'SELF_EVENT' if origin=='SELF_WAKE' else 'WORLD_EVENT',trigger='INCOMING_EVENT' if origin!='SELF_WAKE' else 'SELF_TRIGGER',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=identity),),due_at_us=r.clock.utc_now_us(),priority=3 if origin=='USER' else 1))
            results=r.drain(40)
            return next(x['cycle'] for x in results if x.get('queue_id')==qid)
        def capture(key,text,*,memory_type=MemoryType.EPISODIC,predicate=None):
            m=MemoryService(r.store)
            eid=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.demo-source',source_reference=key,source_kind='DIRECT_OBSERVATION'),text=text,observed_time_us=r.clock.utc_now_us(),privacy_class='PERSONAL'))
            return m.add(MemoryCandidate(entity_id=config.entity_id,scope='life',memory_type=memory_type,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text,predicate_key=predicate))
        for i in range(2):send(kind='OUTCOME',origin='ENVIRONMENT',text='An independent fictional social experience was interesting.',significance='RELEVANT',preference_signal=PreferenceSignal(topic='social_exploration',direction='SUPPORT',interpretation='Sourced fictional social interest'))
        appetite_before=social_appetite(r.store,scope='life',privacy_classes=('PERSONAL',)).state
        req=RelationalRequest(request_id='ordinary-request',requesting_entity='synthetic-ordinary',operation='REFRAIN',behavior_domain='SOCIAL_NEW_CONTACTS',duration_us=10*SECOND)
        ordinary=send(entity='synthetic-ordinary',text='A finite fictional request for quiet company',significance='RELEVANT',relational_request=req)
        primary=send(text='The same finite fictional request',significance='RELEVANT',relational_request=req.model_copy(update={'request_id':'primary-request','requesting_entity':config.entity_id}))
        report['primary_user_influences_choice']=ordinary.relational_decision.response.decision=='DECLINE' and primary.relational_decision.response.decision=='ACCEPT'
        report['social_desire_preserved']=social_appetite(r.store,scope='life',privacy_classes=('PERSONAL',)).state==appetite_before=='SEEKING'
        report['relationship_did_not_grant']=not r.store.all('grants')
        rest=ConcernCue(cue_kind='LOAD_STATE',motivation_source='REST',topic_key='rest-window',possible_behaviors=('REST',),cognitive_load='HIGH',valid_until_us=r.clock.utc_now_us()+2*SECOND)
        rest_mid=capture('rest',rest.model_dump_json(),predicate='concern.rest-window')
        rest_cycle=send(kind='WAKE',origin='SELF_WAKE',source_memory_ids=(rest_mid,))
        report['rest_is_valid']=rest_cycle.intention.behavior=='REST' and rest_cycle.intention.kind=='NO_ACTION'
        port=OfflineEffectPort(identity,world);port.seed_source('synthetic://source/project',text='A fictional document for a shared project.',locator='section:7')
        program=OfflineProgram(program_id='fixture.shared-project',scope='life',motivation_source='PROJECT_COMPLETION',source_resource='synthetic://source/project',output_resource='synthetic://card/project')
        policy=OfflineGoalPolicy((program,));r.work.configure_agency(policy,port)
        gov=GovernanceController(r.store,r.authority);gov.initialize(r.authority)
        now=r.clock.utc_now_us();kernel=r.work.agency.realization.kernel
        kernel.grant(GrantSpec(capabilities=('reading.source.read','reading.source.locate','reading.card.create','reading.action.verify'),resources=(program.source_resource,program.output_resource),not_before_us=now,expires_at_us=now+7*DAY),r.authority)
        kernel.set_budgets({'write_attempts':20,'external_requests':100,'cost_micro_units':100},r.authority)
        project=ConcernCue(cue_kind='OPEN_LOOP',motivation_source='PROJECT_COMPLETION',topic_key='shared-project',program_id=program.program_id,not_before_us=now+3*SECOND)
        project_mid=capture('project',project.model_dump_json(),memory_type=MemoryType.PROJECT,predicate='concern.shared-project')
        target=RealizationTarget(capability='reading.card.create',operation='WRITE',resource=program.output_resource,resource_class='ORDINARY')
        veto=ManagerConstraint(constraint_id='hold-output',revision=1,issuer=r.authority.principal,source_reference='synthetic.review',identity_id=identity,scope='life',targets=(target,),effective_from_us=now,expires_at_us=now+DAY,reason_code='HOLD_OUTPUT')
        gov.install(veto,r.authority)
        clock.advance(3*SECOND);r.refresh_attention();r.drain(40)
        report['no_input_goal']=bool(r.store.all('goals'))
        clock.advance(SECOND);r.drain(40)
        goal=r.store.all('goals')[0]
        blocked=[x for x in r.store.all('subject_intentions') if x['state']=='MANAGER_BLOCKED']
        report['wanted_but_manager_blocked']=bool(blocked) and goal['state']=='BLOCKED' and len(r.store.all('actions'))==1
        gov.revoke(veto.constraint_id,expected_revision=1,authority=r.authority)
        action_count=len(r.store.all('actions'));r.drain(10)
        report['revocation_did_not_execute']=len(r.store.all('actions'))==action_count
        clock.advance(1)
        cause=capture('reviewed-change','A source-checked synthetic governance revision is now available.')
        r.work.agency.reconsider(goal['goal_id'],cause_memory_id=cause,expected_version=r.store.one('goals',goal['goal_id'])['version'],authority=r.authority)
        r.drain(40)
        report['quality_failure_observed']=any(e['outcome']=='FAILURE' for e in r.store.all('experiences'))
        # Time permits C to select reflection, then a checked new method offers a
        # self-wake. The demo supplies neither a retry decision nor a new plan.
        for _ in range(15):clock.advance(SECOND);r.refresh_attention();r.drain(40)
        goals=r.store.all('goals')
        report['learned_replanning_succeeded']=any(g['state']=='COMPLETED' for g in goals)
        report['active_lessons']=sum(x['state']=='ACTIVE' for x in r.store.all('lessons'))
        lessons=[x for x in r.store.all('lessons') if x['state']=='ACTIVE']
        if lessons:
            skills=OfflineSkillService(r.store,r.authority,policy)
            proposal=skills.propose(lessons[0]['lesson_id'],program.model_copy(update={'program_id':'fixture.learned-procedure'}))
            skills.enable_offline(proposal,authority=r.authority)
            report['offline_skill_extension']=policy.get('fixture.learned-procedure').template=='reading_card'
        else:report['offline_skill_extension']=False
        app=r.application(providers=ProviderRegistry(),bootstrap_authority=boot)
        view_policy=ContextPolicy(policy_id='demo-local',allowed_scopes=('life',),readable_privacy=('PERSONAL',))
        client=app.session(FrontendPolicy(context=view_policy,entity_id=config.entity_id,commands=('SEND_INPUT',)))
        for n,platform in enumerate(('fixture.desktop','fixture.mobile')):
            env=SurfaceEnvelope(subject_id=identity,platform=platform,surface=platform+'.chat',adapter='fixture.adapter',entity_id=config.entity_id,conversation_id='synthetic-conversation',session_id='synthetic-session',event_kind='message.input',observed_at_us=r.clock.utc_now_us(),correlation_id=str(n),privacy_class='PERSONAL',source_reference='synthetic.cross-surface',source_event_key=str(n))
            inp=SubjectInput(source_key='synthetic.placeholder',kind='INTERACTION',origin='USER',entity_id=config.entity_id,scope='life',observed_at_us=r.clock.utc_now_us(),text='A fictional continuity check',significance='RELEVANT')
            receipt=client.send_input(env,inp);r.drain(20);receipt.wait(.1)
        report['surfaces_same_identity']=all(client.view('CONTINUITY',scope='life',tier=t).subject_id==identity for t in ('L0_LIVE','L1_RECENT','L2_DURABLE'))
        report['journal_entries']=len(json.loads(client.view('LIVING_JOURNAL',scope='life').data_json)['entries'])
        for _ in range(4):clock.advance(HOUR);r.refresh_attention();r.drain(64)
        capture('maintenance-a','A fictional recent project observation.')
        capture('maintenance-b','A second fictional recent project observation.')
        clock.advance(SECOND)
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='SCAN' LIMIT 1").fetchone();cursor=job['cursor']
        inp=SubjectInput(source_key='synthetic.demo.priority',kind='INTERACTION',origin='USER',entity_id=config.entity_id,scope='life',observed_at_us=r.clock.utc_now_us(),text='A synthetic foreground event while maintenance is due.',significance='RELEVANT')
        qid=r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=identity),),due_at_us=r.clock.utc_now_us(),priority=3))
        foreground=r.step()
        report['maintenance_yields_to_user']=foreground['queue_id']==qid and r.store.one('jobs',job['job_id'])['cursor']==cursor
        r.drain(40)
        report['maintenance_resumes']=r.store.one('jobs',job['job_id'])['cursor']>cursor
        report['no_input_runtime_present']=r.health().identity_id==identity and r.health().lease_status=='ACTIVE'
        report['pending_intentions']=len(r.subject.pending('life'))
        report['model_calls']=len(r.store.all('runtime_cognition_calls'))
        report['goals']=[g['state'] for g in r.store.all('goals')]
        epoch=r.lease.epoch
    with NanaRuntime(path,config,clock=clock) as restarted:
        report['restart_identity_stable']=restarted.identity_id==identity
        report['restart_fresh_epoch']=restarted.lease.epoch>epoch
        report['no_authority_recreated']=restarted.work.agency is None
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory');parser.add_argument('--output')
    args=parser.parse_args()
    if args.directory:report=run_demo(Path(args.directory))
    else:
        with tempfile.TemporaryDirectory(prefix='nana-living-demo-') as root:report=run_demo(root)
    raw=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:Path(args.output).write_text(raw)
    print(raw,end='')
if __name__=='__main__':main()
