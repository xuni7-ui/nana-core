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
