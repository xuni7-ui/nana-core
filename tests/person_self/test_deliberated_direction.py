"""Existing C cognition can reconsider ordinary alternatives, without another planner."""
import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue,LearningValue
from nana_core.continuity.project_work.service import capture
from .conftest import initialize
from .test_inner_communication import seed


@pytest.mark.parametrize('preference,prohibited,risk,expected',[
    ('REST',(), 'LOW','REST'),
    ('LEARN',(), 'LOW','LEARN'),
    ('LEARN',('LEARN',), 'LOW','CREATE'),
    ('LEARN',(), 'HIGH','REST'),
],ids=['rest-not-first','learn-not-first','norm-still-applies','selected-learning-risk-still-applies'])
def test_existing_cognition_can_prefer_an_alternative_while_current_c_guards_and_replay_remain(tmp_path,preference,prohibited,risk,expected):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();calls=[]
    class Choosing:
        descriptor='synthetic-direction-choice'
        def propose(self,request):
            calls.append(request)
            value=json.loads(AnalyticalFixturePort().propose(request))
            value['interpretation']='SYNTHETIC prefer '+preference+' after considering the available motives.'
            if 'preferred_behavior' in CognitiveProposal.model_fields:value['preferred_behavior']=preference
            return json.dumps(value)
    with LifeApplication(home,clock=clock) as app:
        app.pause();seed(app);r=app.runtime
        cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key='own-curiosity',
            possible_behaviors=('CREATE','LEARN','REST'),
            learning_value=LearningValue(goal_value='HIGH',future_reuse='HIGH',interest='HIGH',risk=risk))
        mid=capture(r,'deliberated-direction',cue.model_dump(mode='json'),predicate='concern.deliberated-direction')
        if prohibited:
            norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=cue.topic_key,prohibited_behaviors=prohibited)
            capture(r,'deliberation-current-norm',norm.model_dump(mode='json'),predicate='concern.constraint.deliberation')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.deliberated-direction',kind='WAKE',origin='SELF_WAKE',
            entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,))
        cycle=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
        assert cycle.intention.behavior==expected
        assert r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy).cycle_id==cycle.cycle_id and len(calls)==1
        assert json.loads(r.subject.records.memory.read(mid)['text'])==cue.model_dump(mode='json')
        if 'preferred_behavior' in CognitiveProposal.model_fields:
            frame=next(json.loads(b['data_json']) for b in json.loads(calls[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
            assert set(frame['behavior_options'])==set(cue.possible_behaviors)
            assert 'SYNTHETIC prefer' not in cycle.deliberation.raw_proposal_json
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
        identity=r.identity_id;cycle_id=cycle.cycle_id
    with LifeApplication(home,clock=clock) as app:
        app.pause();assert app.runtime.identity_id==identity
        assert app.runtime.subject.result(app.runtime.store.one('subject_cycles',cycle_id)).intention.behavior==expected


def test_candidate_cannot_invent_a_direction_and_legacy_proposal_omits_new_field(tmp_path):
    from nana_core.contracts import CoreError
    home=tmp_path/'home';initialize(home)
    with LifeApplication(home,clock=VirtualClock()) as app:
        app.pause();r=app.runtime
        cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='REST',topic_key='quiet-choice',possible_behaviors=('REST',))
        mid=capture(r,'one-offered-direction',cue.model_dump(mode='json'),predicate='concern.one-offered-direction')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.unoffered-direction',kind='WAKE',origin='SELF_WAKE',
            entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
        class Unsupported:
            descriptor='synthetic-unsupported-direction'
            def __init__(self,preferred='SOCIALIZE'):self.preferred=preferred
            def propose(self,request):
                value=json.loads(AnalyticalFixturePort().propose(request))
                assert 'preferred_behavior' not in value
                value['preferred_behavior']=self.preferred
                value['interpretation']='PRIVATE_SYNTHETIC_DIRECTION_REASON_DO_NOT_LOG'
                return json.dumps(value)
        before=len(r.store.all('subject_cycles'))
        with pytest.raises(CoreError,match='UNSUPPORTED_COGNITIVE_BEHAVIOR'):
            r.subject.cognize(event,model=Unsupported(),authority=r.authority,policy=app.policy)
        assert len(r.store.all('subject_cycles'))==before and not r.store.all('subject_intentions')
        assert not r.store.all('actions') and not r.store.all('grants')
        # Even without a prior private record, own preference reasons stay out
        # of the ordinary cycle trace. The coarse selected direction may remain.
        quiet=r.subject.cognize(event,model=Unsupported('REST'),authority=r.authority,policy=app.policy)
        assert quiet.intention.kind=='NO_ACTION' and quiet.intention.behavior=='REST'
        assert 'PRIVATE_SYNTHETIC_DIRECTION_REASON_DO_NOT_LOG' not in quiet.deliberation.raw_proposal_json


@pytest.mark.parametrize('behavior',['EXPLORE','CREATE','REFLECT'])
@pytest.mark.parametrize('guard',['none','unconsidered','rest','norm','heavy-load','risk'])
def test_first_considered_noninstrumental_activity_does_not_require_a_stored_interest(app,behavior,guard):
    from nana_core.continuity.subject.opportunities import OpportunityAssessment
    from .test_private_tendency import current
    r=app.runtime;seen=[]
    cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='CREATIVE_INTEREST',topic_key='a-first-uncommitted-idea',
        possible_behaviors=(behavior,'REST'),resource_class='ORDINARY',cognitive_load='HIGH' if guard=='heavy-load' else 'LOW',
        attention_demand='HEAVY' if guard=='heavy-load' else 'LIGHT',opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'))
    mid=capture(r,'first-noninstrumental-idea',cue.model_dump(mode='json'),predicate='concern.first-noninstrumental-idea')
    assert not current(app) and not r.store.all('self_assertions')
    if guard=='norm':
        norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=cue.topic_key,prohibited_behaviors=(behavior,))
        capture(r,'first-idea-current-norm',norm.model_dump(mode='json'),predicate='concern.constraint.first-idea')
    class Choosing:
        descriptor='synthetic-a-first-considered-interest'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            value.update(preferred_behavior=None if guard=='unconsidered' else 'REST' if guard=='rest' else behavior,proposed_operations=['DRAFT']);return json.dumps(value)
    event=SubjectInput(source_key='synthetic.first-noninstrumental-choice',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
        scope='project-work',privacy_class='PERSONAL',risk='HIGH' if guard=='risk' else 'LOW',uncertainty='RELEVANT' if guard=='risk' else 'LOW',
        observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
    result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
    assert result.intention.behavior==(None if guard=='risk' else 'IGNORE' if guard=='unconsidered' else 'REST' if guard in {'rest','norm'} else behavior)
    assert r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy).cycle_id==result.cycle_id
    assert json.loads(r.subject.records.memory.read(mid)['text'])==cue.model_dump(mode='json')
    assert not current(app) and not r.store.all('self_assertions') and not r.store.all('goals')
    assert len(seen)==1 and not r.store.all('actions') and not r.store.all('grants')


def test_first_considered_activity_uses_existing_self_request_without_a_new_call_or_persistent_trait(tmp_path,monkeypatch):
    import itertools,uuid
    from nana_core.continuity.subject.opportunities import OpportunityAssessment
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    from .test_private_tendency import current
    ids=itertools.count(200000);monkeypatch.setattr('nana_core.storage.sqlite_store.uuid.uuid4',lambda:uuid.UUID(int=next(ids)))
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    def choose(request):
        context=json.loads(request.context_json);seen.append(request);manifest=context['manifest']
        return StructuredProposal(interpretation='SYNTHETIC a new activity need not be useful or permanently retained',subject_cognition=CognitiveProposal(
            identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],interpretation='SYNTHETIC I choose to consider an offered creative possibility for its own sake',
            preferred_behavior='CREATE',proposed_operations=('DRAFT',)))
    with provider_harness(proposer=choose) as (transport,state),LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='CREATIVE_INTEREST',topic_key='first-ordinary-creative-option',
            possible_behaviors=('REST','CREATE'),resource_class='ORDINARY',opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'))
        mid=capture(r,'first-creative-option',cue.model_dump(mode='json'),predicate='concern.first-creative-option')
        event=SubjectInput(source_key='synthetic.first-creative.structured-self',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
            scope='project-work',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,))
        port=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=16384))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        rows=r.store.all('cognitive_requests');assert len(rows)==1 and state['calls']==1
        print(json.dumps({'measurement':'synthetic_first_considered_activity','behavior':result.intention.behavior,
            'input_bytes':rows[0]['input_bytes'],'reserved_bytes':rows[0]['reserved_bytes'],'self_calls':state['calls'],
            'budget':seen[0].budget.model_dump(mode='json'),'retained_private_thoughts':len(current(app)),'real_provider_calls':0,'real_actions':0}))
        assert result.intention.behavior=='CREATE'
        assert r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy).cycle_id==result.cycle_id and state['calls']==1
        assert not r.store.all('goals') and not r.store.all('self_assertions') and not current(app)
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('runtime_cognition_calls')
        assert seen[0].budget.timeout_ms==120000 and seen[0].cognitive_role=='SELF'


@pytest.mark.parametrize('behavior',['LEARN','SEEK_CAPABILITY'])
@pytest.mark.parametrize('generic_value',['LOW','RELEVANT'])
@pytest.mark.parametrize('guard',['current','rest','unconsidered','norm','risk','heavy'])
def test_first_deliberated_learning_wish_can_reconsider_low_instrumental_value_and_an_available_alternative(app,behavior,generic_value,guard):
    from nana_core.continuity.subject.opportunities import OpportunityAssessment
    r=app.runtime;seen=[]
    cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='new-study-for-itself',
        possible_behaviors=(behavior,'REST'),resource_class='ORDINARY',cognitive_load='HIGH' if guard=='heavy' else 'LOW',
        opportunity_assessment=OpportunityAssessment(value=generic_value,novelty='NEW'),learning_value=LearningValue(goal_value='LOW',future_reuse='LOW',interest='LOW',alternative='AVAILABLE',
            risk='HIGH' if guard=='risk' else 'LOW',time_compute_cost='HEAVY' if guard=='heavy' else 'LIGHT'))
    mid=capture(r,'first-low-utility-learning',cue.model_dump(mode='json'),predicate='concern.first-low-utility-learning')
    if guard=='norm':
        norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=cue.topic_key,prohibited_behaviors=(behavior,))
        capture(r,'first-low-utility-norm',norm.model_dump(mode='json'),predicate='concern.constraint.first-low-utility')
    class Choosing:
        descriptor='synthetic-new-learning-choice'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request));value.update(preferred_behavior=None if guard=='unconsidered' else 'REST' if guard=='rest' else behavior,proposed_operations=['DRAFT']);return json.dumps(value)
    event=SubjectInput(source_key='synthetic.first-low-utility-learning',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
        privacy_class='PERSONAL',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,))
    result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
    expected=('IGNORE' if generic_value=='LOW' else 'WATCH') if guard=='unconsidered' else 'REST' if guard in {'rest','norm','risk'} else behavior
    assert result.intention.behavior==expected
    assert r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy).cycle_id==result.cycle_id
    assert len(seen)==1 and not r.store.all('goals') and not r.store.all('self_assertions') and not r.store.all('actions') and not r.store.all('grants')
    assert json.loads(r.subject.records.memory.read(mid)['text'])==cue.model_dump(mode='json')


@pytest.mark.parametrize('wanted',['LEARN','REST'])
def test_first_learning_choice_can_use_original_g_and_change_a_different_later_kernel_plan(tmp_path,monkeypatch,wanted):
    _run_first_learning_episode(tmp_path,monkeypatch,wanted)


def _run_first_learning_episode(tmp_path,monkeypatch,wanted,*,reconsider=None):
    from nana_core.continuity.autonomy.private_intent import candidates
    from nana_core.continuity.subject.opportunities import OpportunityAssessment,LearningProgramRef
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    import itertools,uuid,time
    wall_started=time.perf_counter();cpu_started=time.process_time()
    ids=itertools.count(300000);monkeypatch.setattr('nana_core.storage.sqlite_store.uuid.uuid4',lambda:uuid.UUID(int=next(ids)))
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    def choose(request):
        ctx=json.loads(request.context_json);manifest=ctx['manifest']
        frame=next(json.loads(b['data_json']) for b in ctx['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        programs=frame.get('learning_programs',[])
        offered=next((v for v in programs if v['learning_key']=='learn.python-api'),None)
        if offered:assert set(offered)=={'learning_key','spec_digest','domain'}
        assert 'practice' not in json.dumps(programs) and 'expected' not in json.dumps(programs)
        seen.append(request)
        return StructuredProposal(interpretation='SYNTHETIC new learning wish is optional, not a fixed task priority',subject_cognition=CognitiveProposal(
            identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],interpretation='SYNTHETIC choose learning or rest without creating a permanent interest',
            preferred_behavior=wanted,proposed_operations=('DRAFT',),learning_program_ref=LearningProgramRef(learning_key=offered['learning_key'],spec_digest=offered['spec_digest']) if wanted=='LEARN' and offered else None))
    with provider_harness(proposer=choose) as (transport,state),LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime;identity=r.identity_id
        cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='first-python-study',resource_class='ORDINARY',
            possible_behaviors=('LEARN','REST'),opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'),
            learning_value=LearningValue(goal_value='LOW',future_reuse='LOW',interest='LOW',alternative='AVAILABLE'))
        mid=capture(r,'first-python-study',cue.model_dump(mode='json'),predicate='concern.first-python-study')
        event=SubjectInput(source_key='synthetic.first-python-study',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
            privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,))
        port=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=32768))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        r.work.after_cycle(result,event)
        work=[j for j in r.store.all('jobs') if j['work_kind']=='LEARNING'];rows=r.store.all('cognitive_requests')
        print(json.dumps({'measurement':'synthetic_first_optional_g','wanted':wanted,'behavior':result.intention.behavior,
            'self_calls':state['calls'],'input_bytes':rows[0]['input_bytes'],'reserved_bytes':rows[0]['reserved_bytes'],
            'learning_jobs':len(work),'program_count':len(next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL').get('learning_programs',[])),'real_provider_calls':0}))
        assert result.intention.behavior==wanted and len(work)==int(wanted=='LEARN')
        assert len(rows)==1 and state['calls']==1 and not candidates(r.store,'project-work',('PROJECT','PERSONAL'))
        assert not r.store.all('actions') and not r.store.all('grants')
        if work:
            for _ in range(24):
                if r.store.one('jobs',work[0]['job_id'])['state'] in {'DONE','BLOCKED','CANCELLED'}:break
                r.work.open_learning.slice()
            final=r.store.one('jobs',work[0]['job_id']);assert final['state']=='DONE'
            learned=r.work.open_learning.records.read(final['record_id'])['payload']
            assert learned['results']['BASELINE']['passed']==0
            assert learned['results']['EVALUATE']['all_passed'] and learned['results']['TRANSFER']['all_passed']
    # Original explicit isolated DEV authority. The following approved recurrence
    # material is separate from G practice/heldout/transfer; use actual Kernel.
    with LifeApplication(home,clock=clock,bootstrap_grant=True) as later:
        assert later.runtime.identity_id==identity
        material=later.config.materials[0].material_id;later.pause(False);later.work.request(material)
        later.work.run_until(lambda:bool((g:=later.work.goal_for(material)) and g['state'] in {'COMPLETED','FAILED','BLOCKED','ABANDONED'}))
        goal=later.work.goal_for(material);actions=[a for a in later.runtime.store.all('actions') if a['goal_id']==goal['goal_id']]
        compute=next(a for a in actions if a['capability']=='world.compute');kernel=later.runtime.work.agency.realization.kernel
        method=json.loads(kernel.payload(compute,'args_json'))['method']
        print(json.dumps({'measurement':'synthetic_first_g_future','wanted':wanted,'method':method,'goal_state':goal['state'],
            'action_states':[a['state'] for a in actions],'later_model_calls':len(later.runtime.store.all('cognitive_requests'))-1}))
        assert method==('PYTHON_AST_API' if wanted=='LEARN' else 'PYTHON_TOP_DEFS')
        assert (goal['state']=='COMPLETED')==(wanted=='LEARN')
        assert all(a['state']=='SUCCEEDED' for a in actions) and len(later.runtime.store.all('cognitive_requests'))==1
        from pathlib import Path
        db=Path(later.runtime.store.db.execute('PRAGMA database_list').fetchone()[2])
        family=[Path(str(db)+suffix) for suffix in ('','-wal','-shm')]
        print(json.dumps({'measurement':'synthetic_first_g_resources','wanted':wanted,'wall_seconds':time.perf_counter()-wall_started,
            'parent_process_cpu_seconds':time.process_time()-cpu_started,'family_allocated_bytes':sum(p.stat().st_blocks*512 for p in family if p.exists())}))
        if reconsider is None and wanted=='LEARN':
            later.forget(mid)
            assert later.runtime.work.open_learning.strategy('python-api','project-work') is None
        if reconsider is not None:
            from nana_core.presence.contracts import SECOND
            clock.advance(int(later.config.activity_interval_seconds+1)*SECOND)
            for _ in range(12):
                later.tick()
                if later.runtime.store.all('strategy_assessments'):break
            assessments=later.runtime.store.all('strategy_assessments')
            assert len(assessments)==1 and assessments[0]['verdict']=='SUCCESS'
            assessment=assessments[0]['assessment_id']
            baseline_private={v.intent_id:(rid,v) for rid,v in candidates(later.runtime.store,'project-work',('PROJECT','PERSONAL'))}
            assert not any(v.category=='PRIVATE_QUESTION' for _,v in baseline_private.values())
            actions_before=len(later.runtime.store.all('actions'));later.pause()
    if reconsider is not None:
        from nana_core.life.config import load_config,update_config
        from nana_core.continuity.subject import growth_life
        from nana_core.presence.contracts import SECOND
        from tests.independent_life.test_dialogue import relay
        qtext='PRIVATE_NEW_G_QUESTION_CANARY: What playful creative tools could I make with this newly checked API method?'
        reflected=[]
        def grow(request):
            context=json.loads(request['context_json']);manifest=context['manifest']
            growth=[json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='GROWTH_CHANGE']
            assert not any(b['kind']=='PRIVATE_INTERNAL_STATE' for b in context['blocks'])
            if growth:
                assert growth[0]['assessment_id']==assessment and not growth[0].get('basis_private_record_ids')
            reflected.append((request,growth))
            return {'interpretation':'SYNTHETIC checked capability use can inspire a first own question', 'subject_cognition':{
                'identity_id':manifest['identity_id'],'identity_revision':manifest['identity_revision'],
                'interpretation':'SYNTHETIC a new question, not an observed fact or a compulsory goal',
                'preferred_behavior':'REFLECT' if growth else 'WATCH','proposed_operations':['DRAFT'],
                **({'private_question':{'topic':'new-api-play','question':qtext}} if growth else {})}}
        cfg=load_config(home);update_config(home,cfg.model_copy(update={'revision':cfg.revision+1,'provider_background_cognition':True,'provider_context_tokens':32768}),expected_revision=cfg.revision)
        clock.advance(601*SECOND)
        with pytest.MonkeyPatch.context() as patch:
            if not reconsider:patch.setattr(growth_life,'context_projection',lambda *a,**kw:None)
            with relay(home,subject_builder=grow,context_limit=65536) as (router,requests),LifeApplication(home,clock=clock,router=router) as final:
                assert final.runtime.identity_id==identity
                assert {v.intent_id:(rid,v) for rid,v in candidates(final.runtime.store,'project-work',('PROJECT','PERSONAL'))}==baseline_private
                final.pause(False);final.runtime.refresh_attention()
                for _ in range(12):final.tick()
                all_own=candidates(final.runtime.store,'project-work',('PROJECT','PERSONAL'))
                own=tuple((rid,v) for rid,v in all_own if v.intent_id not in baseline_private)
                assert {v.intent_id:(rid,v) for rid,v in all_own if v.intent_id in baseline_private}==baseline_private
                print(json.dumps({'measurement':'synthetic_first_g_new_question','projection_enabled':reconsider,'growth_self_calls':len(requests),
                    'new_questions':len(own),'qualified_growth_projected':bool(reflected and reflected[0][1]),
                    'input_bytes':final.runtime.store.one('cognitive_requests',requests[0]['request_id'])['input_bytes'] if requests else None}))
                assert len(requests)==1 and bool(own)==reconsider
                if reconsider:
                    assert len(own)==1 and own[0][1].category=='PRIVATE_QUESTION' and own[0][1].content_summary==qtext
                    assert own[0][1].owner_identity_id==identity and own[0][1].epistemic_status=='OWN_QUESTION_NOT_WORLD_FACT'
                assert len(final.runtime.store.all('actions'))==actions_before
                assert not final.runtime.store.db.execute('SELECT 1 FROM events WHERE instr(data_json,?)>0',(qtext,)).fetchone()
                calls=len(requests);clock.advance(2*SECOND);final.runtime.lease.heartbeat();final.runtime.refresh_attention()
                for _ in range(8):final.tick()
                assert len(requests)==calls
                final.pause()
        with LifeApplication(home,clock=clock) as reopened:
            all_own=candidates(reopened.runtime.store,'project-work',('PROJECT','PERSONAL'))
            own=tuple((rid,v) for rid,v in all_own if v.intent_id not in baseline_private)
            assert {v.intent_id:(rid,v) for rid,v in all_own if v.intent_id in baseline_private}==baseline_private
            assert reopened.runtime.identity_id==identity and bool(own)==reconsider
            r=reopened.runtime;calls_before=len(r.store.all('cognitive_requests'))
            cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='new-api-play',resource_class='ORDINARY',
                possible_behaviors=('LEARN','REST'),opportunity_assessment=OpportunityAssessment(value='LOW',novelty='REPEATED'),
                learning_value=LearningValue(goal_value='LOW',future_reuse='LOW',interest='LOW',alternative='AVAILABLE'))
            future_mid=capture(r,'later-new-question-choice',cue.model_dump(mode='json'),predicate='concern.later-new-question-choice')
            next_choice=r.subject.run(SubjectInput(source_key='synthetic.later-new-question-choice',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
                scope='project-work',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(future_mid,)))
            assert next_choice.intention.behavior==('LEARN' if reconsider else 'IGNORE')
            assert any(m.source=='PRIVATE_INTEREST' for m in next_choice.motivations)==reconsider
            assert len(r.store.all('cognitive_requests'))==calls_before and len(r.store.all('actions'))==actions_before
            assert len([j for j in r.store.all('jobs') if j['work_kind']=='LEARNING'])==1
            print(json.dumps({'measurement':'synthetic_new_question_later_choice','projection_enabled':reconsider,
                'behavior':next_choice.intention.behavior,'new_model_calls':len(r.store.all('cognitive_requests'))-calls_before}))
            # Original erasure must remove the G-dependent influence as well as
            # the method; it is not permission to rewrite an unrelated thought.
            reopened.forget(mid)
            assert r.work.open_learning.strategy('python-api','project-work') is None
            assert not any(v.content_summary==qtext for _,v in candidates(r.store,'project-work',('PROJECT','PERSONAL')))
            after_withdraw=r.subject.run(SubjectInput(source_key='synthetic.later-new-question-source-withdrawn',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',
                scope='project-work',privacy_class='PERSONAL',observed_at_us=clock.utc_now_us(),source_memory_ids=(future_mid,)))
            assert after_withdraw.intention.behavior=='IGNORE' and len(r.store.all('cognitive_requests'))==calls_before


@pytest.mark.parametrize('condition',['offered','norm','not-learning','unconfigured','no-retention'])
def test_first_learning_catalog_reuses_original_readonly_scope_and_current_options(app,condition):
    r=app.runtime
    if condition=='unconfigured':r.work.configure_open_learning(())
    cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='SELF_DEVELOPMENT',topic_key='first-catalog-option',
        possible_behaviors=('CREATE','REST') if condition=='not-learning' else ('LEARN','REST'),resource_class='ORDINARY')
    mid=capture(r,'first-catalog-option',cue.model_dump(mode='json'),predicate='concern.first-catalog-option')
    if condition=='norm':
        norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=cue.topic_key,prohibited_behaviors=('LEARN',))
        capture(r,'first-catalog-norm',norm.model_dump(mode='json'),predicate='concern.constraint.first-catalog')
    event=SubjectInput(source_key='synthetic.first-catalog-option',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PERSONAL',
        retention='DO_NOT_REMEMBER' if condition=='no-retention' else 'MAY_REMEMBER',observed_at_us=r.clock.utc_now_us(),source_memory_ids=() if condition=='no-retention' else (mid,))
    source=r.subject.ingress.ingest(event);changes=r.store.db.total_changes
    view=r.subject.situation(event,source)
    assert bool(view.learning_programs)==(condition=='offered')
    assert view.learning_selection_optional==bool(view.learning_programs)
    assert all(set(p.model_dump(mode='json'))=={'learning_key','spec_digest','domain'} for p in view.learning_programs)
    assert r.store.db.total_changes==changes and not r.store.all('cognitive_requests')


@pytest.mark.parametrize('reconsider',[True,False],ids=['verified-growth','growth-projection-ablated'])
def test_normal_d_checked_first_learning_use_can_form_a_new_private_question_without_an_old_private_origin(tmp_path,monkeypatch,reconsider):
    _run_first_learning_episode(tmp_path,monkeypatch,'LEARN',reconsider=reconsider)
