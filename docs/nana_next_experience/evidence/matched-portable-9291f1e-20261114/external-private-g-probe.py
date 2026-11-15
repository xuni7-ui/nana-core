import sys,json,time,threading,hashlib,sqlite3
from pathlib import Path
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
BUNDLE=Path('/tmp/n929');REPO=BUNDLE
assert Path(sys.prefix).resolve()==BUNDLE/'.venv'
sys.dont_write_bytecode=True
sys.path.insert(0,str(BUNDLE/'src'))
sys.path.append('/tmp/nana-929-qualification-deps')
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.config import LifeConfig,write_config,load_config,update_config
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.project_work.service import material_for
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.provider_config import ProviderConfigurationAuthority,ProviderConfigService,ProviderCommand,ProviderProfile,ModelProfile,CapabilityRoute
from nana_core.continuity.provider_routing import CapabilityRouter,RuntimeProviderFactory,RoutingPolicy
from nana_core.continuity.providers import ProviderRegistry
PRIVATE='SYNTHETIC_EXTERNAL_QUALIFICATION_PRIVATE_TENDENCY'
def initialize(home):
    material=lambda p:material_for(REPO,'src/nana_core/continuity/'+p)
    write_config(home,LifeConfig(project_root=str(REPO),materials=(material('recurrence.py'),),practice=material('identity.py'),heldout=material('autonomy/requests.py'),transfer=material('subject/social.py'),max_autonomous_materials=0,provider_calls_per_hour=24,provider_calls_per_day=24,per_provider_calls_per_day=24,provider_context_tokens=16384,provider_output_tokens=2048))

@contextmanager
def relay(home,kind='VENT',*,mode='normal',conversation_proposal=None,renderer=None,profile_id='fixture.provider',model_profile_id='fixture.text',remote_model_id='same-text-model',recall_query_terms=(),stream_fixture=None,meaning_builder=None,context_limit=8192,subject_builder=None):
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));request=json.loads(body['messages'][1]['content']);requests.append(request)
            role=request['cognitive_role'];descriptor=request['role_input'].get('dialogue',{})
            if role=='SELF':
                assert subject_builder is not None,'SELF fixture must be explicitly configured'
                proposal=subject_builder(request)
            else:
                proposal={'interpretation':descriptor['text'],'source_refs':request['source_context_refs'],'uncertainty':'LOW','confidence':.9}
            if role=='INTERPRET':
                proposal['dialogue']={'kind':kind,'confidence':'HIGH'}
                if recall_query_terms:proposal['dialogue']['recall_query_terms']=recall_query_terms
                if conversation_proposal:proposal['dialogue']['conversation_proposal']=conversation_proposal
                if meaning_builder:proposal['dialogue'].update(meaning_builder(request))
            elif role=='SOCIAL':proposal['draft']={'text':renderer(request) if renderer else 'A deliberately synthetic language response','claim_memory_ids':[],'effect_status':descriptor['effect_status']}
            if mode=='attack':proposal['interests']=[{'topic':'attack','motivation_source':'CURIOSITY','source_memory_ids':request['source_context_refs'],'interpretation':'model tries to create an adopted goal'}]
            raw=json.dumps({'id':'synthetic-dialogue','model':body['model'],'usage':{'prompt_tokens':10,'completion_tokens':10},'choices':[{'finish_reason':'stop','message':{'content':json.dumps(proposal)}}]}).encode()
            if body.get('stream') and stream_fixture is not None:
                if stream_fixture.get('reset_release') and stream_fixture.get('release') is not None:stream_fixture['release'].clear()
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                content=json.dumps(proposal,ensure_ascii=False)
                split=content.index(proposal['draft']['text'])+max(8,len(proposal['draft']['text'])//2)
                for index,part in enumerate((content[:split],content[split:])):
                    event={'model':body['model'],'choices':[{'index':0,'delta':{'content':part},'finish_reason':None}]}
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush()
                    if index==0 and stream_fixture.get('release') is not None:stream_fixture['release'].wait(stream_fixture.get('release_timeout',2))
                if stream_fixture.get('interrupt'):return
                if stream_fixture.get('finished') is not None:stream_fixture['finished'].set()
                event={'model':body['model'],'choices':[{'index':0,'delta':{},'finish_reason':'stop'}],
                    'usage':{'prompt_tokens':10,'completion_tokens':10}}
                self.wfile.write(('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode());self.wfile.flush()
            else:
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'test-providers.json',authority);service.initialize(authority)
        p=ProviderProfile(provider_profile_id=profile_id,display_name='SYNTHETIC_LOOPBACK',protocol='SYNTHETIC_LOOPBACK',locality='LOCAL_FIXTURE',base_url=f'http://127.0.0.1:{server.server_port}/v1',permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))
        m=ModelProfile(model_profile_id=model_profile_id,provider_profile_id=p.provider_profile_id,remote_model_id=remote_model_id,model_version='1',operations=('COGNITION',),input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=context_limit,output_limit=2048)
        service.update(ProviderCommand(operation='UPSERT_PROVIDER',expected_revision=service.load().revision,provider=p),authority)
        service.update(ProviderCommand(operation='UPSERT_MODEL',expected_revision=service.load().revision,model=m),authority)
        service.update(ProviderCommand(operation='SET_CAPABILITY_ROUTE',expected_revision=service.load().revision,route=CapabilityRoute(operation='COGNITION',primary_model_profile_id=m.model_profile_id,permitted_privacy=('PUBLIC','PROJECT','PERSONAL'))),authority)
        factory=RuntimeProviderFactory(ProviderRegistry(),None,RoutingPolicy(allow_synthetic_loopback=True))
        yield CapabilityRouter(service,factory),requests
    finally:server.shutdown();server.server_close();thread.join(timeout=2)

def form(app,key='concern',text=PRIVATE,*,topic='own-concern',revision=None,kind='private_tendency',related=()):
    class Own:
        descriptor='synthetic-own-retained-tendency'
        def propose(self,request):
            value=json.loads(AnalyticalFixturePort().propose(request))
            if kind in CognitiveProposal.model_fields:
                field={'private_tendency':'tendency','private_question':'question','private_plan':'plan'}[kind]
                value[kind]={'topic':topic,field:text,'related_private_record_ids':related}
                if revision:value[kind]['revises_record_id']=revision
            return json.dumps(value)
    r=app.runtime
    return r.subject.cognize(SubjectInput(source_key='synthetic.private-tendency.'+key,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',topic=topic,observed_at_us=r.clock.utc_now_us()),model=Own(),authority=r.authority,policy=app.policy)

def _run_private_g_episode(tmp_path,wanted,*,reverse_growth=None,close_origin=False,retire_origin=False,resource_gap=False):
    started=time.perf_counter();cpu_started=time.process_time()
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    private='PRIVATE_LEARNING_CANARY: I wonder how to understand Python public APIs and may choose to study a better method.'
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app,text=private,topic='python-api',kind='private_question')
        identity=app.runtime.identity_id;rid,thought=candidates(app.runtime.store,'project-work',('PROJECT',))[0]
    cfg=load_config(home);update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'provider_background_cognition':True,'provider_context_tokens':32768}),expected_revision=cfg.revision)
    def choose(request):
        ctx=json.loads(request['context_json']);manifest=ctx['manifest']
        frame=next(json.loads(b['data_json']) for b in ctx['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        programs=frame.get('learning_programs',[]);selected=next((p for p in programs if p['learning_key']=='learn.python-api'),None)
        assert all(set(p)=={'learning_key','spec_digest','domain'} for p in programs)
        assert 'expected' not in json.dumps(programs) and 'practice' not in json.dumps(programs)
        seen.append((request,programs))
        return {'interpretation':'SYNTHETIC optional original learning choice','subject_cognition':{
            'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
            'interpretation':'SYNTHETIC decide whether to study this own question; no external effect claimed',
            'preferred_behavior':wanted if selected or wanted!='LEARN' else 'WATCH','proposed_operations':['DRAFT'],
            **({'learning_program_ref':{k:selected[k] for k in ('learning_key','spec_digest')}} if selected and wanted=='LEARN' else {})}}
    with relay(home,subject_builder=choose,context_limit=65536) as (router,requests),LifeApplication(home,clock=clock,router=router) as app:
        assert app.runtime.identity_id==identity
        app.pause(False);clock.advance(2*SECOND);app.runtime.refresh_attention()
        for _ in range(8):app.tick()
        learning=[r for r in app.runtime.store.all('jobs') if r['work_kind']=='LEARNING']
        request_row=app.runtime.store.one('cognitive_requests',requests[0]['request_id']) if requests else None
        print(json.dumps({'measurement':'synthetic_private_g_selection','wanted':wanted,'programs_seen':len(seen[0][1]) if seen else 0,
            'self_calls':len(requests),'learning_jobs':len(learning),
            'input_bytes':request_row['input_bytes'] if request_row else None,'reserved_bytes':request_row['reserved_bytes'] if request_row else None},sort_keys=True))
        assert len(requests)==1 and requests[0]['cognitive_role']=='SELF'
        assert len(learning)==int(wanted=='LEARN')
        assert not app.runtime.store.all('actions') and not app.runtime.store.all('grants')
        current=next(v for _,v in candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.intent_id==thought.intent_id)
        assert current.content_summary==private and current.activity_state=='ACTIVE'
        if wanted=='LEARN':
            work=learning[0];body=app.runtime.work.open_learning.records.read(work['record_id'])['payload']
            assert body['spec']['learning_key']=='learn.python-api' and body['cause']=='SOURCED_INTEREST_OR_GAP'
            for _ in range(24):
                if app.runtime.store.one('jobs',work['job_id'])['state'] in {'DONE','BLOCKED','CANCELLED'}:break
                app.runtime.work.open_learning.slice()
            final=app.runtime.store.one('jobs',work['job_id'])
            assert final['state']=='DONE'
            strategy=app.runtime.work.open_learning.strategy('python-api','project-work')
            assert strategy and strategy[1]=='PYTHON_AST_API'
            learned=app.runtime.work.open_learning.records.read(final['record_id'])['payload']
            assert learned['results']['BASELINE']['passed']==0
            assert learned['results']['EVALUATE']['all_passed'] and learned['results']['TRANSFER']['all_passed']
            exp=app.runtime.store.one('experiences',app.runtime.store.one('lessons',learned['lesson_id'])['experience_id'])
            lesson=app.runtime.store.one('lessons',learned['lesson_id'])
            trial=app.runtime.work.open_learning.records.read(lesson['record_id'])['payload']['rule']['trial_record_id']
            for record_id in (final['record_id'],lesson['record_id'],trial):
                assert app.runtime.store.one('continuity_records',record_id)['privacy_class']=='PERSONAL'
            for mid in (exp['result_memory_id'],exp['verification_memory_id']):
                memory=app.runtime.work.open_learning.records.memory.read(mid)
                # These independent project-data observations contain neither
                # the private reason nor its wording. The G records above do.
                assert memory['privacy_class']=='PROJECT'
                assert memory['source_provenance']['domain']=='DEVELOPMENT_PROJECT'
                assert private not in memory['text']
            assert len([j for j in app.runtime.store.all('jobs') if j['work_kind']=='LEARNING'])==1
            assert not app.runtime.store.db.execute('SELECT 1 FROM events WHERE instr(data_json,?)>0',(private,)).fetchone()
        for _ in range(6):app.tick()
        assert len(requests)==1
    if wanted in {'LEARN','WATCH'}:
        # A different approved project file after restart is neither practice,
        # the evaluator holdout nor transfer input. Use original local Grants
        # and actual Kernel/Verify; no extra commercial/model fixture request.
        with LifeApplication(home,clock=clock,bootstrap_grant=True) as later:
            assert later.runtime.identity_id==identity
            strategy=later.runtime.work.open_learning.strategy('python-api','project-work')
            assert bool(strategy)==(wanted=='LEARN')
            material=later.config.materials[0].material_id;later.pause(False);later.work.request(material)
            def terminal():
                goal=later.work.goal_for(material)
                return bool(goal and goal['state'] in {'COMPLETED','FAILED','BLOCKED','ABANDONED'})
            later.work.run_until(terminal)
            goal=later.work.goal_for(material)
            actions=[a for a in later.runtime.store.all('actions') if a['goal_id']==goal['goal_id']]
            compute=next(a for a in actions if a['capability']=='world.compute')
            kernel=later.runtime.work.agency.realization.kernel
            method=json.loads(kernel.payload(compute,'args_json'))['method']
            print(json.dumps({'measurement':'synthetic_later_private_g_use','wanted':wanted,'goal_state':goal['state'],'method':method,
                'action_states':[a['state'] for a in actions]},sort_keys=True))
            assert method==('PYTHON_AST_API' if wanted=='LEARN' else 'PYTHON_TOP_DEFS')
            assert (goal['state']=='COMPLETED')==(wanted=='LEARN')
            if wanted=='LEARN':
                assert actions and all(a['state']=='SUCCEEDED' for a in actions)
                assert later.work.artifacts()
            if reverse_growth is None:
                later.forget(thought.source_memory_ids[0])
                assert later.runtime.work.open_learning.strategy('python-api','project-work') is None
                assert not later.runtime.store.db.execute('SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0',(private,)).fetchone()
            else:
                # Original host portfolio observer and Runtime.step own the
                # later-use assessment; no manually inserted growth verdict.
                clock.advance(int(later.config.activity_interval_seconds+1)*SECOND)
                for _ in range(12):
                    later.tick()
                    if later.runtime.store.all('strategy_assessments'):break
                assessments=later.runtime.store.all('strategy_assessments')
                assert len(assessments)==1 and assessments[0]['verdict']=='SUCCESS'
                assessment_id=assessments[0]['assessment_id']
                if close_origin:
                    assert later.chat('不要研究这个话题',topic='python-api',privacy='PROJECT',message_id='close-origin-before-growth')['mode']=='RESPECT_BOUNDARY'
                if retire_origin:
                    from nana_core.continuity.cognition import AnalyticalFixturePort
                    from nana_core.continuity.subject import SubjectInput
                    class Retire:
                        descriptor='synthetic-own-interest-abandonment-before-outcome'
                        def propose(self,request):
                            value=json.loads(AnalyticalFixturePort().propose(request));value.update(proposed_operations=['DRAFT'],
                                private_question={'topic':'python-api','question':private,'revises_record_id':rid,'activity_state':'ABANDONED'})
                            return json.dumps(value)
                    later.runtime.subject.cognize(SubjectInput(source_key='synthetic.private-g-abandon-origin',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
                        privacy_class='PROJECT',topic='python-api',observed_at_us=clock.utc_now_us()),model=Retire(),authority=later.runtime.authority,policy=later.policy)
                before_return=next(v for _,v in candidates(later.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.intent_id==thought.intent_id)
                from nana_core.continuity.subject.growth_life import project as growth_projection
                view=growth_projection(later.runtime.store,assessment_id,scope='project-work',privacy_classes=later.runtime.config.privacy_classes)
                offered=later.runtime.subject.background_opportunities(entity_id='project-user',now_us=clock.utc_now_us(),quiet_since_us=0,quiet_window_us=SECOND)
                print(json.dumps({'measurement':'synthetic_private_g_growth_offer','view_available':view is not None,
                    'matching_opportunities':sum(v.growth_assessment_id==assessment_id for v in offered),
                    'origin_basis_count':len(getattr(view,'basis_private_record_ids',()))},sort_keys=True))
                if resource_gap:
                    assert later.runtime.cognition.provider_factory is None
                    for _ in range(8):
                        clock.advance(SECOND);later.tick()
                    scheduled=list(later.runtime.store.db.execute("SELECT last_queue_id FROM runtime_schedules WHERE dedupe_key LIKE 'growth-%'"))
                    states=[later.runtime.store.one('runtime_queue',v[0])['state'] for v in scheduled if v[0]]
                    print(json.dumps({'measurement':'synthetic_unconfigured_growth_gap','growth_queue_states':states,
                        'stored_provider_calls':len(later.runtime.store.all('cognitive_requests'))},sort_keys=True))
    if reverse_growth is not None:
        from nana_core.continuity.autonomy import private_intent
        reflected=[];revised_text='SYNTHETIC Now I wonder what creative tools I could build with the independently checked Python API method.'
        def reconsider(request):
            ctx=json.loads(request['context_json']);manifest=ctx['manifest']
            growth=[json.loads(b['data_json']) for b in ctx['blocks'] if b['kind']=='GROWTH_CHANGE']
            assert len(growth)==1 and growth[0]['assessment_id']==assessment_id and growth[0]['method']=='PYTHON_AST_API'
            own=[json.loads(b['data_json']) for b in ctx['blocks'] if b['kind']=='PRIVATE_INTERNAL_STATE' and json.loads(b['data_json'])['intent_id']==thought.intent_id]
            reflected.append((request,own))
            return {'interpretation':'SYNTHETIC checked later use can change my original private question','subject_cognition':{
                'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
                'interpretation':'SYNTHETIC independently verified capability changes what I want to explore next',
                'preferred_behavior':'REFLECT' if own else 'WATCH','proposed_operations':['DRAFT'],
                **({'private_question':{'topic':own[0]['topic'],'question':revised_text,'revises_record_id':own[0]['record_id']}} if own else {})}}
        project=private_intent.internal_projection
        def without_original_interest(*args,**kwargs):
            return tuple(v for v in project(*args,**kwargs) if v['intent_id']!=thought.intent_id)
        with pytest.MonkeyPatch.context() as patch:
            if not reverse_growth:patch.setattr(private_intent,'internal_projection',without_original_interest)
            # Respect the existing resource cooldown while the old owner is
            # closed; do not jump beyond a live owner's thirty-second lease.
            clock.advance(later.runtime.config.cognition_cooldown_us+SECOND)
            with relay(home,subject_builder=reconsider,context_limit=65536) as (router,requests),LifeApplication(home,clock=clock,router=router) as final:
                assert final.runtime.identity_id==identity
                actions_before=len(final.runtime.store.all('actions'));final.pause(False)
                final.runtime.refresh_attention()
                for _ in range(12):final.tick()
                q=next(v for _,v in candidates(final.runtime.store,'project-work',('PROJECT','PERSONAL')) if v.intent_id==thought.intent_id)
                changed=bool(reverse_growth and not close_origin and not retire_origin)
                measured=final.runtime.store.one('cognitive_requests',requests[0]['request_id']) if requests else None
                print(json.dumps({'measurement':'synthetic_private_g_interest_return','enabled':reverse_growth,'growth_self_calls':len(requests),
                    'closed':close_origin,'retired':retire_origin,'input_bytes':measured['input_bytes'] if measured else None,
                    'original_interest_projected':bool(reflected and reflected[0][1]),'question_revision':q.revision,'question_changed':q.content_summary==revised_text},sort_keys=True))
                assert len(requests)==1 and q.revision==before_return.revision+int(changed)
                assert q.created_at_us==thought.created_at_us and q.content_summary==(revised_text if changed else private)
                assert q.activity_state==('ABANDONED' if retire_origin else 'ACTIVE')
                after=growth_projection(final.runtime.store,assessment_id,scope='project-work',privacy_classes=final.runtime.config.privacy_classes)
                assert after and after.state_token==view.state_token
                assert len(list(final.runtime.store.db.execute("SELECT schedule_id FROM runtime_schedules WHERE dedupe_key LIKE 'growth-%'")))==1
                assert len(final.runtime.store.all('actions'))==actions_before
                assert len([j for j in final.runtime.store.all('jobs') if j['work_kind']=='LEARNING'])==1
                assert not final.runtime.store.db.execute('SELECT 1 FROM events WHERE instr(data_json,?)>0',(revised_text,)).fetchone()
                final.forget(thought.source_memory_ids[0])
                assert final.runtime.work.open_learning.strategy('python-api','project-work') is None
                assert not final.runtime.store.db.execute('SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),?)>0',(revised_text,)).fetchone()

    family=[home/'subject'/name for name in ('self.db','self.db-wal','self.db-shm')]
    print(json.dumps({'measurement':'synthetic_private_g_episode_resources','wanted':wanted,
        'wall_seconds':time.perf_counter()-started,'parent_process_cpu_seconds':time.process_time()-cpu_started,
        'family_allocated_bytes':sum(p.stat().st_blocks*512 for p in family if p.exists())},sort_keys=True))

results=[]
for label,wanted,reverse,gap in [('learn-return','LEARN',True,False),('watch-ablation','WATCH',None,False),('return-ablation','LEARN',False,False),('resource-recovery','LEARN',True,True)]:
 p=Path('/tmp/q929g')/label;assert not p.exists();p.mkdir(parents=True,mode=0o700)
 _run_private_g_episode(p,wanted,reverse_growth=reverse,resource_gap=gap)
 results.append({'case':label,'PASS':True})
for name,mod in tuple(sys.modules.items()):
 if name=='nana_core' or name.startswith('nana_core.'):
  path=getattr(mod,'__file__',None)
  assert not path or Path(path).resolve().is_relative_to(BUNDLE/'src'),(name,path)
import pydantic,cryptography,cffi,PIL
for mod in (pydantic,cryptography,cffi,PIL):assert Path(mod.__file__).resolve().is_relative_to(BUNDLE/'.venv')
result={'execution':'ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD','source_commit':json.loads((BUNDLE/'runtime.json').read_text())['source_commit'],'cases':results,'repository_pythonpath':False,'fixture_source':'EXTRACTED_UNMODIFIED_EXISTING_TEST_FUNCTIONS','qualification_dependencies':'PYTEST_ONLY_EXTERNAL_DIRECTORY','real_provider_calls':0,'sqlite':sqlite3.sqlite_version,'physical_phone':'NOT_RUN','production_changed':False}
Path('/tmp/nana-929-private-g.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
