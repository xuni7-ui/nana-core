"""Own interests can select the original configured G, without a second learner."""
import json,time
import pytest
from nana_core.life.application import LifeApplication
from nana_core.life.config import load_config,update_config
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from nana_core.continuity.autonomy.private_intent import candidates
from tests.independent_life.test_dialogue import relay
from .conftest import initialize
from .test_private_tendency import form


@pytest.mark.parametrize('wanted',['LEARN','WATCH','REST'])
def test_normal_d_own_question_can_choose_original_g_or_keep_the_interest_without_learning(tmp_path,wanted):
    _run_private_g_episode(tmp_path,wanted)


def _run_private_g_episode(tmp_path,wanted,*,reverse_growth=None,close_origin=False,retire_origin=False):
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


@pytest.mark.parametrize('condition',['unknown-program','wrong-digest','missing-ref','disabled-after-read','changed-after-read','forbidden','wait'])
def test_learning_reference_is_bound_to_current_g_and_c_keeps_final_choice(tmp_path,condition):
    from nana_core.contracts import CoreError
    from nana_core.continuity.cognition import AnalyticalFixturePort
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.subject.opportunities import PrivateIntentRef,ConcernCue
    from nana_core.continuity.project_work.service import capture
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app,text='SYNTHETIC optional Python method curiosity',topic='python-api',kind='private_question')
        r=app.runtime;rid,item=candidates(r.store,'project-work',('PROJECT',))[0]
        ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision)
        if condition=='forbidden':
            norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key='python-api',prohibited_behaviors=('LEARN',))
            capture(r,'learning-norm',norm.model_dump(mode='json'),predicate='concern.constraint.private-learning')
        class Choice:
            descriptor='synthetic-exact-original-g-reference'
            def propose(self,request):
                context=json.loads(request.context_json)
                frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
                option=frame['learning_programs'][0];key=option['learning_key']
                value=json.loads(AnalyticalFixturePort().propose(request));value.update(preferred_behavior='LEARN',proposed_operations=['WAIT'] if condition=='wait' else ['DRAFT'])
                if condition!='missing-ref':
                    value['learning_program_ref']={'learning_key':'unoffered.program' if condition=='unknown-program' else key,
                        'spec_digest':'0'*64 if condition=='wrong-digest' else option['spec_digest']}
                if condition=='disabled-after-read':r.work.open_learning=None
                if condition=='changed-after-read':
                    spec=r.work.open_learning.specs[key]
                    r.work.open_learning.specs[key]=spec.model_copy(update={'baseline_method':'PYTHON_AST_API'})
                return json.dumps(value)
        event=SubjectInput(source_key='synthetic.exact-private-g.'+condition,kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
            privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),source_memory_ids=r.subject.records.support(rid),private_thought_ref=ref)
        if condition in {'forbidden','wait'}:
            result=r.subject.cognize(event,model=Choice(),authority=r.authority,policy=app.policy)
            assert not result.proposed_program_id and result.intention.kind=='NO_ACTION'
            assert result.intention.behavior==('WATCH' if condition=='forbidden' else 'DEFER')
            r.work.after_cycle(result,event)
        else:
            error='PRIVATE_LEARNING_SELECTION_REQUIRED' if condition=='missing-ref' else 'UNSUPPORTED_COGNITIVE_LEARNING_PROGRAM'
            with pytest.raises(CoreError,match=error):r.subject.cognize(event,model=Choice(),authority=r.authority,policy=app.policy)
        assert not any(j['work_kind']=='LEARNING' for j in r.store.all('jobs'))
        assert not r.store.all('goals') and not r.store.all('actions') and not r.store.all('grants')
        assert next(v for _,v in candidates(r.store,'project-work',('PROJECT',)) if v.intent_id==item.intent_id)==item


@pytest.mark.parametrize('condition',['active','unconfigured','withdrawn','wrong-scope','too-private'])
def test_g_catalog_is_read_only_and_never_exposes_evaluation_or_unavailable_data(tmp_path,condition):
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime;g=r.work.open_learning
        if condition=='unconfigured':r.work.open_learning=None
        if condition=='withdrawn':app.forget(g.source_memory_ids[0])
        snapshot=r.store.snapshot();writes=r.store.db.total_changes
        choices=r.subject.learning_program_catalog('unavailable-scope' if condition=='wrong-scope' else 'project-work',('PUBLIC',) if condition=='too-private' else ('PROJECT',))
        assert bool(choices)==(condition=='active')
        if choices:
            value=choices[0].model_dump();assert set(value)=={'learning_key','spec_digest','domain'}
            assert value['learning_key']=='learn.python-api' and len(value['spec_digest'])==64
        assert snapshot==r.store.snapshot() and writes==r.store.db.total_changes


def test_private_g_uses_original_topic_pause_and_default_wire_remains_omitted(tmp_path):
    from nana_core.continuity.cognition import CognitiveProposal,AnalyticalFixturePort
    from nana_core.continuity.world_loop.cognition import proposal_schema
    from nana_core.continuity.subject import SubjectInput
    from nana_core.continuity.subject.opportunities import PrivateIntentRef
    value=CognitiveProposal(identity_id='synthetic',identity_revision=1,interpretation='SYNTHETIC',proposed_operations=('WAIT',))
    assert 'learning_program_ref' not in value.model_dump_json()
    assert 'LearningProgramRef' not in proposal_schema().get('$defs',{})
    home=tmp_path/'home';initialize(home);clock=VirtualClock()
    with LifeApplication(home,clock=clock) as app:
        app.pause();form(app,topic='python-api',kind='private_question');r=app.runtime
        rid,item=candidates(r.store,'project-work',('PROJECT',))[0]
        class Select:
            descriptor='synthetic-original-g-topic-binding'
            def propose(self,request):
                frame=next(json.loads(b['data_json']) for b in json.loads(request.context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
                option=frame['learning_programs'][0];out=json.loads(AnalyticalFixturePort().propose(request))
                out.update(preferred_behavior='LEARN',proposed_operations=['DRAFT'],learning_program_ref={k:option[k] for k in ('learning_key','spec_digest')})
                return json.dumps(out)
        event=SubjectInput(source_key='synthetic.private-g-topic',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',
            observed_at_us=clock.utc_now_us(),source_memory_ids=r.subject.records.support(rid),private_thought_ref=PrivateIntentRef(record_id=rid,intent_id=item.intent_id,revision=item.revision))
        result=r.subject.cognize(event,model=Select(),authority=r.authority,policy=app.policy);r.work.after_cycle(result,event)
        g=r.work.open_learning;job=g.next_job();assert job
        body=g.records.read(job['record_id'])['payload'];assert body['context_binding']=={'entity_id':'project-user','topic':'python-api'}
        stopped=app.chat('不要研究这个话题',topic='python-api',privacy='PROJECT',message_id='stop-private-g')
        assert stopped['mode']=='RESPECT_BOUNDARY'
        assert g.slice()['reason']=='CONTEXT_TOPIC_CLOSED'
        paused=r.store.one('jobs',job['job_id']);assert paused['state']=='BLOCKED'
        assert g.records.read(paused['record_id'])['payload']['context_paused']
        assert not r.store.all('lessons') and not r.store.all('actions') and not r.store.all('grants')


def test_private_learning_does_not_open_arbitrary_project_private_ingress(tmp_path):
    from nana_core.contracts import CoreError
    from nana_core.continuity.contracts import EvidenceInput,Provenance
    from nana_core.continuity.subject import SubjectInput
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        r=app.runtime
        with pytest.raises(CoreError,match='PROJECT_DEVELOPMENT_INGRESS_ONLY'):
            r.subject.records.memory.capture(EvidenceInput(provenance=Provenance(domain='DEVELOPMENT_PROJECT',source_namespace='recorded.project.untrusted',source_reference='private-input',source_kind='USER_STATEMENT'),
                text='PRIVATE_UNTRUSTED_PROJECT_INPUT',privacy_class='PERSONAL',observed_time_us=r.clock.utc_now_us()))
        with pytest.raises(ValueError,match='development sources require explicit nonprivate namespace'):
            SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.untrusted-private-input',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us())
        assert not r.store.db.execute("SELECT 1 FROM artifacts WHERE instr(CAST(payload AS TEXT),'PRIVATE_UNTRUSTED_PROJECT_INPUT')>0").fetchone()


@pytest.mark.parametrize('enabled',[True,False])
def test_original_host_later_use_can_reconsider_the_interest_that_chose_learning(tmp_path,enabled):
    _run_private_g_episode(tmp_path,'LEARN',reverse_growth=enabled)


@pytest.mark.parametrize('condition',['closed','abandoned'])
def test_checked_learning_does_not_reopen_a_closed_context_or_revive_an_abandoned_interest(tmp_path,condition):
    _run_private_g_episode(tmp_path,'LEARN',reverse_growth=True,close_origin=condition=='closed',retire_origin=condition=='abandoned')
