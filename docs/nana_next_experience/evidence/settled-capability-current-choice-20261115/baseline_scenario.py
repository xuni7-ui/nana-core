"""A checked capability need may settle without settling every personal interest."""
import json
from contextlib import ExitStack
import pytest
from nana_core.life.application import LifeApplication
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.continuity.project_work.service import capture
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue,LearningValue
from nana_core.continuity.subject.growth_life import opportunities
from nana_core.continuity.cognition import AnalyticalFixturePort
from tests.controlled_hands.conftest import initialize,until
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness


@pytest.fixture
def settled(tmp_path):
    tasks=(ApplicationTask(task_id='base',kind='DOCUMENT',initial='old ',wanted='new',context='notes'),
        ApplicationTask(task_id='later',kind='DOCUMENT',initial='draft ',wanted='different',context='research'))
    with OwnedApplication(tmp_path/'target',tasks=tasks) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            r=app.runtime
            until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM experiences WHERE outcome='FAILURE' AND task_class='owned-document'").fetchone()))
            app.pause();failure=r.store.db.execute("SELECT * FROM experiences WHERE outcome='FAILURE' AND task_class='owned-document' LIMIT 1").fetchone()
            cue=ConcernCue(cue_kind='OPEN_LOOP',topic_key='document-competence',motivation_source='CAPABILITY_GAP',program_id='learn.owned-document',
                possible_behaviors=('LEARN','REFLECT','REST','WATCH'),learning_value=LearningValue(goal_value='LOW',future_reuse='LOW',interest='LOW',alternative='AVAILABLE'))
            mid=capture(r,'settled-interest',cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(failure['result_memory_id'],),predicate='concern.document-competence')
            app.pause(False);until(app,lambda:bool(opportunities(r.store,scope='project-work',privacy_classes=r.config.privacy_classes)))
            app.pause();identity=r.identity_id
        # One owner at a time; competence history survives a genuine restart.
        with LifeApplication(home,bootstrap_grant=False) as app:
            app.pause();assert app.runtime.identity_id==identity
            yield app,mid,cue


@pytest.mark.parametrize('choice',[None,'LEARN','REST','REFLECT'])
@pytest.mark.parametrize('port',['fixture','provider'])
def test_settled_need_does_not_remove_an_explicit_current_direction(settled,choice,port):
    app,mid,cue=settled;r=app.runtime;seen=[]
    class Choosing:
        descriptor='synthetic-current-choice-after-checked-capability-use'
        def propose(self,request):
            frame=next(json.loads(b['data_json']) for b in json.loads(request.context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
            seen.append(frame);value=json.loads(AnalyticalFixturePort().propose(request))
            if choice:value['preferred_behavior']=choice if choice in frame['behavior_options'] else 'WATCH'
            return json.dumps(value)
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.settled-interest-choice',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',
        privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(mid,),task_class='owned-document')
    actions=len(r.store.all('actions'));jobs=[j['job_id'] for j in r.store.all('jobs') if j['work_kind']=='LEARNING']
    with ExitStack() as stack:
        model=Choosing();wire=[];state=None
        if port=='provider':
            def propose(request):
                wire.append(len(transport.request_body(request)))
                return StructuredProposal(interpretation='SYNTHETIC current choice',
                    subject_cognition=CognitiveProposal.model_validate_json(Choosing().propose(request)))
            transport,state=stack.enter_context(provider_harness(proposer=propose))
            model=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=32768))
        result=r.subject.cognize(event,model=model,authority=r.authority,policy=app.policy)
        print(json.dumps({'choice':choice,'port':port,'behavior':result.intention.behavior,'wire_bytes':wire,
            'calls':state['calls'] if state else len(seen),'need':result.experience_need.state}))
        assert r.subject.cognize(event,model=model,authority=r.authority,policy=app.policy).cycle_id==result.cycle_id
        assert not state or state['calls']==1
    assert result.experience_need.state=='SETTLED'
    assert result.intention.behavior==(choice or 'WATCH')
    assert len(seen)==1
    # Considering an interest does not invent a fresh failure or retrain an
    # already qualified course; original G still owns that independent decision.
    r.work.after_cycle(result,event)
    assert [j['job_id'] for j in r.store.all('jobs') if j['work_kind']=='LEARNING']==jobs
    assert len(r.store.all('actions'))==actions and not r.store.all('self_assertions')
    assert json.loads(r.subject.records.memory.read(mid)['text'])==cue.model_dump(mode='json')
    assert r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy).cycle_id==result.cycle_id and len(seen)==1


@pytest.mark.parametrize('condition',['norm','eight-options'])
def test_current_need_preserves_original_norm_and_full_candidate_bound(settled,condition):
    app,mid,original=settled;r=app.runtime;seen=[]
    options=('LEARN','REFLECT','REST','EXPLORE','CREATE','MAINTAIN','SEEK_CAPABILITY','SOCIALIZE') if condition=='eight-options' else original.possible_behaviors
    cue=original.model_copy(update={'possible_behaviors':options})
    current=capture(r,'settled-current-options',cue.model_dump(mode='json'),kind='MODEL_DERIVATION',parents=(mid,),predicate='concern.document-competence')
    if condition=='norm':
        norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=cue.topic_key,prohibited_behaviors=('LEARN',))
        capture(r,'settled-current-norm',norm.model_dump(mode='json'),predicate='concern.constraint.settled')
    class Choosing:
        descriptor='synthetic-current-settled-options'
        def propose(self,request):
            seen.append(next(json.loads(b['data_json']) for b in json.loads(request.context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL'))
            value=json.loads(AnalyticalFixturePort().propose(request));value['preferred_behavior']='LEARN'
            return json.dumps(value)
    event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.settled-options',kind='WAKE',origin='SELF_WAKE',
        entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(current,),task_class='owned-document')
    result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
    assert result.experience_need.state=='SETTLED'
    assert result.intention.behavior==('REFLECT' if condition=='norm' else 'LEARN')
    assert seen[0]['behavior_options']==list(options)
