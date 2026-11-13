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
