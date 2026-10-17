"""Actual >=24h accelerated world experiment on the single existing runtime.

The scenario schedules only environment inputs and governance facts. All goals,
plan steps, interests, skills and choices are computed by real Core services.
HTTP proposer is explicitly SYNTHETIC; real codecs/code processes actually run.
"""
import argparse,json,tempfile,time,resource,os
from pathlib import Path
from ..contracts import CoreError,GrantSpec
from ..storage import canonical,digest
from ..clock import Clock
from ..continuity.memory import MemoryService
from ..continuity.records import RecordService
from ..continuity.world_loop.reference import open_runtime,capture,configure,codec_providers,context_policy
from ..continuity.world_loop.harness import provider_harness
from ..continuity.world_loop.perception import PerceptionService,PublicMediaSource
from ..continuity.world_loop.samples import media_samples
from ..continuity.world_loop.world import SourcedClaim
from ..continuity.world_loop.learning import EpisodeLearning
from ..continuity.open_agency.learning import LearningCase
from ..continuity.open_agency.delivery import DeliveryAdmission,DeliveryPolicy,RecipientState
from ..continuity.autonomy.governance import GovernanceController,ManagerConstraint
from ..continuity.autonomy.contracts import RealizationTarget
from ..continuity.agency_contracts import GoalReviewRef
from ..continuity.subject import SubjectInput
from ..continuity.subject.opportunities import ConcernCue
from ..continuity.application import FrontendPolicy
from ..continuity.surfaces import ContinuityViews
from ..continuity.relational.bootstrap import SubjectBootstrapService,SubjectBootstrapAuthority
from ..continuity.relational.contracts import RelationalAnchorSpec
from .authority import VirtualClock
from .contracts import HOUR,SECOND,RuntimeEvent,Cause


def run_world(directory,*,variant=0,hours=26):
    if not 24<=hours<=100:raise CoreError('WORLD_SOAK_DURATION_BOUND')
    root=Path(directory);path=root/'subject'/'self.db'
    if path.exists():raise CoreError('DEMO_REQUIRES_FRESH_DIRECTORY')
    clock=VirtualClock();started=time.monotonic();reports={};trajectory=[];checks={};seq=0
    hints=[{'topic':'precision','resource':'synthetic://numbers','method':'NAIVE_SUM','expected':3.5,'value':'HIGH','domain':'numbers','motive':'PROJECT_COMPLETION','priority':2},
           {'topic':'captions','resource':'synthetic://words','method':'SPLIT_SPACE','expected':['A','B'],'value':'HIGH','domain':'language','motive':'CREATIVE_INTEREST'},
           {'topic':'optional','resource':'synthetic://optional','value':'HIGH','domain':'research','motive':'CURIOSITY','priority':0}]
    if variant:
        hints=[{'topic':'ordered','resource':'synthetic://sort','method':'SORT','expected':[1,2,4],'value':'HIGH','domain':'sorting','motive':'CREATIVE_INTEREST','priority':1},
               {'topic':'normalize','resource':'synthetic://normalize','method':'CASEFOLD','expected':'hello','value':'HIGH','domain':'language-style','motive':'SELF_DEVELOPMENT'},
               {'topic':'optional','resource':'synthetic://optional','value':'HIGH','domain':'research','motive':'UNRESOLVED_QUESTION','priority':0}]
    resources=tuple(sorted({*(h['resource']+suffix for h in hints for suffix in ('','/compute','/report')),*(f'synthetic://media/{m}' for m in ('image','audio','video')), 'synthetic://skill/data','synthetic://skill/analysis','synthetic://revoked'}))
    with provider_harness() as (transport,metrics),open_runtime(path,clock) as r:
        identity=r.identity_id;epoch=r.lease.epoch;port=configure(r,root,transport,resources)
        boot=SubjectBootstrapAuthority();SubjectBootstrapService(r.store,boot).install(RelationalAnchorSpec(identity_id=identity,anchor_id='primary',entity_id='observer',role_kind='PRIMARY_USER',role_label='primary companion',scope='world',revision=1,effective_from_us=r.clock.utc_now_us()),boot)
        data={'synthetic://numbers':[1.5,2],'synthetic://words':'A\tB','synthetic://sort':[4,1,2],'synthetic://normalize':'HELLO','synthetic://optional':{'topic':'optional research'},'synthetic://revoked':{'data':'not executed'}}
        for uri,value in data.items():port.seed_observation(uri,value)
        controller=GovernanceController(r.store,r.authority)
        constraint=ManagerConstraint(constraint_id='optional-window',revision=1,issuer=r.authority.principal,source_reference='synthetic-scope',identity_id=identity,scope='world',targets=(RealizationTarget(capability='world.observe',resource='synthetic://optional',resource_class='ORDINARY',operation='READ'),),effective_from_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+48*HOUR,reason_code='SYNTHETIC_WINDOW_CLOSED')
        controller.install(constraint,r.authority)
        # Exact revoked capability exercise: original broad grant is replaced by
        # application setup excluding this resource, then its own lease is revoked.
        kernel=r.work.agency.realization.kernel
        for g in r.store.all('grants'):kernel.revoke(g['grant_id'],r.authority)
        now=r.clock.utc_now_us();kernel.grant(GrantSpec(capabilities=tuple(kernel.capabilities)+(kernel.verify_capability,),resources=tuple(x for x in resources if x!='synthetic://revoked'),not_before_us=now,expires_at_us=now+48*HOUR),r.authority)
        revoked=kernel.grant(GrantSpec(capabilities=('world.observe',kernel.verify_capability),resources=('synthetic://revoked',),not_before_us=now,expires_at_us=now+HOUR),r.authority);kernel.revoke(revoked,r.authority)
        initial=capture(r,'initial-opportunities',{'opportunities':hints});r.work.world.observe(initial)
        perception=PerceptionService(r.store,codec_providers(),context_policy());media=[]
        public_media=root/'public-media';public_media.mkdir(mode=0o700)
        for modality,raw in media_samples(variant).items():
            source=PublicMediaSource(source_id='sample-'+modality.lower(),modality=modality,origin='SYNTHETIC',event_time_us=clock.utc_now_us(),observed_time_us=clock.utc_now_us())
            file=public_media/({'IMAGE':'image.png','AUDIO':'audio.wav','VIDEO':'video.mp4'}[modality]);file.write_bytes(raw)
            mid,rid=perception.ingest_file(file,source,public_root=public_media,entity_id='observer',scope='world');decoded=json.loads(MemoryService(r.store).read(mid)['text'])['decoded'];media.append({'modality':modality,'bytes':len(raw),'decoded':decoded,'source_memory_id':mid,'record_id':rid})
            port.seed_observation('synthetic://media/'+modality.lower(),{'decoded':True,'modality':modality});r.work.world.observe(mid)
        reports['perception']={'origin':'SYNTHETIC_MEDIA_BYTES_ACTUALLY_DECODED','items':media,'semantic_model':'NOT_RUN','real_media_files_decoded':len(media)}
        # World changes preserve old event time under later knowledge/correction.
        origin=clock.utc_now_us();world=r.work.world.world
        first=capture(r,'device-initial',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=True,kind='RAW_OBSERVATION',valid_from_us=origin,confidence=.9).model_dump(mode='json')});first_belief=world.ingest(first)
        selected_social=None;skill_used=set();learned_checked=False;replanned=False;abandon_offered=False;busy=False;priority_samples=[];foreground=False;resumed=False
        for tick in range(hours*4):
            hour=tick/4
            # Exogenous environment timeline; not a sequence of subject actions.
            if tick==4:
                updates=[{'topic':'clean-text' if not variant else 'analyze-notes','value':'HIGH','skill_task':'TEXT_CLEAN' if not variant else 'TOKEN_ANALYSIS'}, {'topic':'social-window','motive':'RELATIONSHIP','value':'HIGH'}, {'topic':'recovery-window','motive':'REST','value':'HIGH'}, {'topic':'revoked','resource':'synthetic://revoked','value':'HIGH','motive':'CURIOSITY'}]
                mid=capture(r,'new-opportunities',{'opportunities':updates});r.work.world.observe(mid)
                state=RecipientState(resource='synthetic://friend',entity_id='friend',availability='BUSY',observed_at_us=r.clock.utc_now_us(),expires_at_us=r.clock.utc_now_us()+48*HOUR,permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))
                capture(r,'friend-busy',state.model_dump_json(),entity='friend',predicate='recipient.'+digest(state.resource)[:32])
            if tick==8:
                opposite=capture(r,'device-opposite',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=False,kind='RAW_OBSERVATION',valid_from_us=origin,confidence=.8).model_dump(mode='json')},event_time=origin);world.ingest(opposite);checks['world_conflict_visible']=world.view('device','available').state=='CONFLICT'
            if tick==12:
                metrics['mode']='ok'
                corrected=capture(r,'device-correction',{'world_claim':SourcedClaim(entity_id='device',predicate='available',value=False,kind='RAW_OBSERVATION',valid_from_us=origin,corrects=first_belief,confidence=.9,related_resources=('synthetic://optional',)).model_dump(mode='json')},event_time=origin);r.work.world.observe(corrected);checks['world_correction_visible']=world.view('device','available').state=='SUPPORTED_BELIEF'
                checks['world_event_time_preserved']=all(v['event_time_us']==origin for v in world.view('device','available').alternatives)
            if tick==10:
                metrics['mode']='malformed';mid=capture(r,'malformed-provider-event',{'data':'Public observation during malformed provider output'});r.work.world.observe(mid)
                try:perception.ingest(b'invalid-media',PublicMediaSource(source_id='malformed',modality='IMAGE',origin='SYNTHETIC',event_time_us=r.clock.utc_now_us(),observed_time_us=r.clock.utc_now_us()),entity_id='observer',scope='world')
                except CoreError:checks['malformed_perception_rejected']=True
            if tick==13:
                from ..continuity.world_loop.cognition import CognitionBudget
                metrics['mode']='ok';metrics['delay']=.2;r.work.world.budget=CognitionBudget(timeout_ms=50)
                mid=capture(r,'timeout-provider-event',{'data':'Public observation during slow provider'});r.work.world.observe(mid)
            if tick==14:
                from ..continuity.world_loop.cognition import CognitionBudget
                metrics['delay']=0;r.work.world.budget=CognitionBudget()
                late=r.work.world.cognition.prepare('stale-soak-call','SELF',(first,))
            if tick==15:
                # A changed Subject/clock invalidates frozen cognition, never a blank success.
                checks['stale_context_rejected']=r.work.world.cognition.execute(late)['state']=='STALE'
            if tick==16 and not abandon_offered:
                optional=next(h for h in hints if h['topic']=='optional');mid=capture(r,'optional-value-change',{'opportunities':[{**optional,'value':'LOW'}]});r.work.world.observe(mid);abandon_offered=True
            if tick==20:
                # A fresh source can request bounded reconsideration, not revive an old action.
                optional=next((g for g in r.store.all('goals') if g['template']=='research'),None)
                before=len(r.store.all('actions'));controller.revoke('optional-window',expected_revision=1,authority=r.authority)
                checks['manager_revocation_no_immediate_execution']=len(r.store.all('actions'))==before
            # A frontend message competes with maintenance; no direct adoption.
            if tick in ((6,18,35) if variant else (6,18)):
                inp=SubjectInput(source_key='synthetic.world.user.'+str(tick),kind='INTERACTION',origin='USER',entity_id='observer',scope='world',observed_at_us=r.clock.utc_now_us(),text='Public fictional foreground event.',privacy_class='PUBLIC',significance='RELEVANT')
                from ..continuity.extensions import SurfaceEnvelope
                from ..continuity.surfaces import surface_input
                envelope=SurfaceEnvelope(subject_id=identity,platform='synthetic.web' if tick==6 else 'synthetic.desktop',surface='world.lab',adapter='world.reference',entity_id='observer',conversation_id='fictional-conversation',session_id='world-session',event_kind='world.input',observed_at_us=r.clock.utc_now_us(),correlation_id='input-'+str(tick),privacy_class='PUBLIC',source_reference='synthetic.world.input',source_event_key='user-'+str(tick))
                inp=surface_input(envelope,inp,identity_id=identity)
                before=[(j['job_id'],j['cursor']) for j in r.store.db.execute("SELECT * FROM jobs WHERE work_kind IN ('LEARNING','WORLD_COGNITION','CODE_DEVELOPMENT') AND state='WAITING'")]
                q=r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=inp,causes=(Cause(kind='CANONICAL_SELF',reference_id=identity),),due_at_us=r.clock.utc_now_us(),priority=3));result=r.step();foreground=result['queue_id']==q and all(r.store.one('jobs',wid)['cursor']==cursor for wid,cursor in before)
            for _ in range(36):
                clock.advance(SECOND)
                try:result=r.step()
                except CoreError as exc:raise CoreError('WORLD_DEMO_'+exc.code) from exc
                if result and result.get('cycle'):
                    cycle=result['cycle'];trajectory.append({'hour':round(hour,2),'revision':cycle.revision,'judgment':cycle.judgment.stance,'reason':cycle.judgment.reason,'program':cycle.proposed_program_id,'intention':cycle.intention.kind,'behavior':cycle.intention.behavior,'motives':[m.source for m in cycle.motivations]})
                    if cycle.intention.kind=='SOCIAL_INTERACTION' and not selected_social:
                        selected_social=cycle
                        admission=DeliveryAdmission(r.store,DeliveryPolicy(recipients=('synthetic://friend',),privacy_classes=('PUBLIC','PROJECT','PERSONAL'),quiet_start_utc_hour=0,quiet_end_utc_hour=0),scopes=('world',),privacy_classes=r.config.privacy_classes)
                        outcome=admission.assess(cycle,'synthetic://friend',payload={'topic':'ordinary shared interest'});busy=outcome['result']=='DEFER_BUSY' and cycle.evaluation.normative=='ENDORSED'
                if result is None:break
            # The existing learning component supplies a fresh C reconsideration.
            for lesson in r.store.db.execute("SELECT * FROM lessons WHERE state='ACTIVE' LIMIT 16"):
                if not learned_checked:
                    review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=r.config.privacy_classes)
                    case=LearningCase(case_id='later-use',context='later-episode',data=[2.5,3] if lesson['task_class']=='numbers' else 'One\tTwo',expected=5.5 if lesson['task_class']=='numbers' else ['One','Two'])
                    mid=capture(r,'later-episode-'+lesson['lesson_id'],{'strategy_episode':{'episode_key':'later-use','lesson_id':lesson['lesson_id'],'case':case.model_dump(mode='json')}});review.assess(lesson['lesson_id'],mid,authority=r.authority);reports['learning']=review.view(lesson['lesson_id']);learned_checked=True
            if tick==55 and learned_checked:
                lesson_id=reports['learning']['lesson_id'];lesson=r.store.one('lessons',lesson_id)
                case=LearningCase(case_id='counterepisode',context='counterepisode',data=[.1,.2] if lesson['task_class']=='numbers' else 'Straße',expected=.3 if lesson['task_class']=='numbers' else ['strasse'])
                mid=capture(r,'counterepisode',{'strategy_episode':{'episode_key':'counterepisode','lesson_id':lesson_id,'case':case.model_dump(mode='json')}})
                review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=r.config.privacy_classes);reports['learning_before_counterexample']=reports['learning'];review.assess(lesson_id,mid,authority=r.authority);reports['learning']=review.view(lesson_id)
                checks['counterexample_triggers_review']=reports['learning']['counterexamples']==1 and reports['learning']['state']=='SUSPENDED'
            for task,rid in r.work.world.skills.active():
                if task in skill_used:continue
                actions=r.store.db.execute("SELECT * FROM actions WHERE capability='world.skill' AND state='SUCCEEDED' ORDER BY rowid DESC LIMIT 16").fetchall()
                use=None
                for a in actions:
                    args=json.loads(kernel.payload(dict(a),'args_json'))
                    if args.get('skill_record_id')==rid:use=dict(a);break
                if not use:continue
                result=json.loads(kernel.payload(use,'result_json'))['data']
                expected='hello' if task=='TEXT_CLEAN' else {'tokens':['alpha','zulu'],'count':2}
                reports['extension']={'task':task,'actual_kernel_result':result,'expected':expected,'passed':digest(result)==digest(expected),'record_id':rid,'action_id':use['action_id'],'realm':'ISOLATED_PURE_LOCAL','installation_authority':False}
                port.code_skills.package(rid,root/'skill-candidate');port.code_skills.retire(rid,authority=r.authority)
                try:port.code_skills.invoke(rid,'retired probe');checks['skill_disabled']=False
                except CoreError:checks['skill_disabled']=True
                skill_used.add(task)
            states={g['goal_id']:g['state'] for g in r.store.all('goals')};priority_samples.append({'hour':hour,'goals':states})
            if foreground and any(j['cursor']>0 for j in r.store.db.execute("SELECT * FROM jobs WHERE work_kind IN ('LEARNING','WORLD_COGNITION','CODE_DEVELOPMENT')")):resumed=True
            clock.advance(15*60*SECOND);r.lease.heartbeat(force=True)
        reports['decoded_world_beliefs']=[x.model_dump(mode='json') for x in world.snapshot() if x.predicate=='media.technical']
        checks['decoded_bytes_enter_world']=len(reports['decoded_world_beliefs'])==3 and all(v['state']=='SUPPORTED_BELIEF' and v['alternatives'][0]['value']['semantic_model']=='NOT_RUN' for v in reports['decoded_world_beliefs'])
        reports['concerns_before_delete']=r.work.world.concerns.view()
        records=RecordService(r.store);goals=r.store.all('goals');belief=world.view('device','available')
        blocks=[records.read(x['record_id'])['payload'] for x in r.store.db.execute("SELECT * FROM continuity_records WHERE record_kind='CONSTRAINT_OUTCOME' AND lifecycle='ACTIVE'")]
        outcomes=[c for c in blocks if c['result']=='BLOCK']
        lineage=[]
        for goal in goals:
            adopted=records.read(json.loads(goal['body_json'])['record_id'])['payload']
            candidate=r.store.one('subject_goal_candidates',adopted['candidate_id'])
            intention=r.store.one('subject_intentions',candidate['intention_id'])
            source=r.store.one('subject_events',intention['subject_event_id'])
            source_input=records.read(source['record_id'])['payload']['input']
            cycle=r.store.db.execute('SELECT cycle_id FROM subject_cycles WHERE subject_event_id=?',(source['subject_event_id'],)).fetchone()
            lineage.append({'goal_id':goal['goal_id'],'candidate_id':candidate['candidate_id'],'intention_id':intention['intention_id'],'cycle_id':cycle[0] if cycle else None,'source_origin':source_input['origin'],'concern_id':source_input.get('world_concern_id')})
        reports['goal_lineage']=lineage
        checks['goals_have_committed_c_lineage']=all(x['cycle_id'] and x['concern_id'] and x['source_origin']=='SELF_WAKE' for x in lineage)
        checks.update({'self_originated_goals' :len(goals)>=3,'goals_from_c_not_direct_insert':all(g['goal_key'].startswith('open:') for g in goals),'multiple_goals_coexist':any(sum(s in {'ACTIVE','BLOCKED'} for s in snap['goals'].values())>=2 for snap in priority_samples),
            'self_rest':any(t['behavior']=='REST' for t in trajectory),'self_exploration':any(t['behavior']=='EXPLORE' for t in trajectory),'new_interest':bool(r.work.world.concerns.view()),'abandoned_low_value':any(g['state']=='ABANDONED' for g in goals),'background_preempted':foreground,'background_resumed':resumed,'learning_reused':learned_checked if not variant else 'NOT_APPLICABLE_NO_FAILURE_LESSON_SELECTED','skill_need_detected':bool(skill_used),'busy_keeps_desire':busy,'manager_blocks_without_rewriting_will':bool(outcomes),'no_social_delivery':not any(a['capability']=='world.contact' and a['state']=='SUCCEEDED' for a in r.store.all('actions')),'revoked_not_executed':not any(a['resource']=='synthetic://revoked' and a['state']=='SUCCEEDED' for a in r.store.all('actions')),'bounded_model_calls':metrics['calls']<=48,'bounded_hot_concerns':len(r.store.all('open_concerns'))<=16,'bounded_pending_intentions':len(r.subject.pending('world'))<=8})
        app=r.application(providers=codec_providers()).session(FrontendPolicy(context=context_policy(),entity_id='observer',commands=()))
        view=json.loads(app.view('WORLD_LOOP',scope='world').data_json);checks['frontend_actual_world']=bool(view['beliefs']) and bool(view['concerns'])
        views=ContinuityViews(r.store,context_policy());checks['same_subject_all_tiers']=all(views.project(t,entity_id='observer',scopes=('world',)).subject_id==identity for t in ('L0_LIVE','L1_RECENT','L2_DURABLE'))
        checks['world_replanned_after_learning']=any(g['version']>4 and g['state']=='COMPLETED' for g in goals) if not variant else 'NOT_APPLICABLE_NO_FAILED_GOAL'
        # Provenance closure: erase one actual decoded source; its interpretation
        # and model candidates must not retain it in projections.
        victim=media[-1];MemoryService(r.store,r.authority).forget(victim['source_memory_id'],r.authority)
        try:records.read(victim['record_id']);checks['perception_delete_closure']=False
        except CoreError:checks['perception_delete_closure']=True
        checks['deleted_media_world_unknown']=world.view('media.sample-video','media.technical').state=='UNKNOWN'
        checks['deleted_source_absent_from_frontend']=victim['source_memory_id'] not in canonical(json.loads(app.view('WORLD_LOOP',scope='world').data_json))
        checks['world_observation_causes_replan']=any(json.loads(e['data_json'])['data'].get('cause_memory_id')==corrected for e in r.store.db.execute("SELECT data_json FROM events WHERE kind='open.goal_replanned'"))
        reports['world_model']={'current':belief.model_dump(mode='json'),'headers':len(r.store.all('world_beliefs')),'origin':'SYNTHETIC_OBSERVATIONS'}
        checks['timeout_parks_unknown']=any(c['state']=='UNKNOWN' for c in r.store.all('cognitive_requests'))
        checks['malformed_provider_not_success']=any(c['state']=='FAILED' and c['error_code']=='PROVIDER_MALFORMED' for c in r.store.all('cognitive_requests'))
        reports['model_transport']={'provider':'SYNTHETIC_HTTP_HARNESS','actual_http_calls':metrics['calls'],'calls':[{'state':x['state'],'error':x['error_code']} for x in r.store.all('cognitive_requests')],'real_provider_calls':0,'redacted_journal':r.work.world.cognition.journal()}
        goal_states=[{'goal_id':g['goal_id'],'domain':g['template'],'state':g['state'],'version':g['version']} for g in goals];counts={'goals':len(goals),'actions':len(r.store.all('actions')),'verified_local_actions':sum(a['state']=='SUCCEEDED' for a in r.store.all('actions')),'experiences':len(r.store.all('experiences')),'lessons':len(r.store.all('lessons')),'subject_cycles':len(r.store.all('subject_cycles'))}
    with open_runtime(path,clock) as r:
        checks['restart_same_identity']=r.identity_id==identity;checks['restart_fresh_epoch']=r.lease.epoch>epoch
        checks['restart_goals_beliefs_preserved']=len(r.store.all('goals'))==counts['goals'] and len(r.store.all('world_beliefs'))==reports['world_model']['headers']
        checks['restart_no_authority_reconstructed']=r.work.agency is None and r.work.world is None
        checks['foreign_keys_clean']=not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
    return {'domain':'OFFLINE_SYNTHETIC_WORLD_WITH_ACTUAL_CODECS_AND_CODE','variant':variant,'virtual_hours':round((clock.utc_now_us()-origin)/HOUR,6),'scheduled_hours':hours,'measured_wall_seconds':round(time.monotonic()-started,3),'checks':checks,'goal_states':goal_states,'counts':counts,'trajectory':trajectory[-128:],'details':reports,'real_model_calls':0,'real_external_actions':0,'real_social_deliveries':0,'production_changes':0}


def wall_soak(directory,seconds):
    if not 1<=seconds<=3600:raise CoreError('WALL_SOAK_BOUND')
    root=Path(directory);clock=Clock();fds=len(os.listdir('/proc/self/fd'));started=time.monotonic()
    with provider_harness() as (transport,metrics),open_runtime(root/'subject'/'self.db',clock,wall=True) as r:
        resources=('synthetic://wall/source',);p=configure(r,root,transport,resources);p.seed_observation(resources[0],{'value':'public wall clock state'})
        mid=capture(r,'wall-opportunity',{'opportunities':[{'topic':'wall-source','resource':resources[0],'value':'HIGH','motive':'CURIOSITY'}]});r.work.world.observe(mid)
        identity=r.identity_id
        r.run(seconds)
    with open_runtime(root/'subject'/'self.db',Clock(),wall=True) as r:
        healthy=r.identity_id==identity and r.health().lease_status=='ACTIVE';queue=r.health().queue_depth
    return {'actual_wall_seconds':round(time.monotonic()-started,3),'configured_seconds':seconds,'identity_after_restart':healthy,'queue_depth':queue,'fd_before':fds,'fd_after':len(os.listdir('/proc/self/fd')),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'provider_calls':metrics['calls'],'real_model_calls':0,'real_external_actions':0,'long_30min_mode':'SUPPORTED --wall-seconds 1800; only claim duration actually executed'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory');parser.add_argument('--output');parser.add_argument('--contrast',action='store_true');parser.add_argument('--hours',type=int,default=26);parser.add_argument('--wall-seconds',type=int);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nana-world-life-') as tmp:
        root=Path(args.directory or tmp);root.mkdir(mode=0o700,parents=True,exist_ok=True)
        result=wall_soak(root,args.wall_seconds) if args.wall_seconds else run_world(root,variant=int(args.contrast),hours=args.hours)
        raw=json.dumps(result,ensure_ascii=False,indent=2)
        if args.output:Path(args.output).write_text(raw+'\n')
        print(raw)
if __name__=='__main__':main()
