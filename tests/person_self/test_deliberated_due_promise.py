"""A real due promise stays visible while C considers a new optional interest."""
import json
import pytest
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.commitments import CommitmentCandidate,CommitmentService
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue,LearningValue
from nana_core.continuity.project_work.service import capture
from .conftest import initialize


@pytest.mark.parametrize('preference,explicit_review,prohibited,risk,expected',[
    ('CREATE',False,(),'LOW','CREATE'),
    ('LEARN',False,(),'LOW','LEARN'),
    ('REST',False,(),'LOW','REST'),
    (None,False,(),'LOW',None),
    ('CREATE',True,(),'LOW',None),
    ('CREATE',False,('CREATE',),'LOW',None),
    ('LEARN',False,(),'HIGH','REST'),
],ids=['new-creative-choice','new-learning-choice','quiet-still-available','legacy-no-choice','explicit-promise-review','current-norm','learning-risk'])
def test_original_c_can_choose_new_interest_without_erasing_due_promise(tmp_path,preference,explicit_review,prohibited,risk,expected):
    home=tmp_path/'home';initialize(home);clock=VirtualClock();requests=[]
    class Choosing:
        descriptor='synthetic-due-promise-motivational-choice'
        def propose(self,request):
            requests.append(request)
            value=json.loads(AnalyticalFixturePort().propose(request))
            if preference:value['preferred_behavior']=preference
            return json.dumps(value)
    with LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime;identity=r.identity_id
        source=capture(r,'due-promise-evidence',{'source':'SYNTHETIC independently adopted promise'})
        service=CommitmentService(r.store,r.authority)
        cid=service.propose(CommitmentCandidate(entity_id='project-user',scope='project-work',description='SYNTHETIC real adopted due promise',support_memory_ids=(source,),due_at_us=clock.utc_now_us()-1))
        service.transition(cid,'ADOPTED',expected_revision=1,authority=r.authority)
        original=dict(r.store.one('commitments',cid))
        cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key='new-independent-interest',possible_behaviors=('CREATE','LEARN','REST'),learning_value=LearningValue(goal_value='HIGH',future_reuse='HIGH',interest='HIGH',risk=risk))
        mid=capture(r,'new-interest-with-due-promise',cue.model_dump(mode='json'),predicate='concern.new-independent-interest')
        if prohibited:
            norm=ConcernCue(cue_kind='CONSTRAINT',motivation_source='NORM',topic_key=cue.topic_key,prohibited_behaviors=prohibited)
            capture(r,'current-choice-norm',norm.model_dump(mode='json'),predicate='concern.constraint.current-choice-norm')
        event=SubjectInput(domain='DEVELOPMENT_MATERIAL',source_key='development.new-interest-with-due-promise',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,),commitment_check_id=cid if explicit_review else None)
        chosen=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy)
        assert len(requests)==1
        frame=next(json.loads(b['data_json']) for b in json.loads(requests[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert any(m['source']=='COMMITMENT' and m['strength']=='PRESSING' for m in frame['motivations'])
        assert chosen.intention.behavior==expected
        assert any(m.source=='COMMITMENT' and m.strength=='PRESSING' for m in chosen.motivations)
        assert dict(r.store.one('commitments',cid))==original and service.get(cid).overdue
        assert r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=app.policy).cycle_id==chosen.cycle_id and len(requests)==1
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
        if expected is None:assert chosen.intention.slot_key=='commitment-review'
        cycle_id=chosen.cycle_id
    with LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime;assert r.identity_id==identity
        assert r.subject.result(r.store.one('subject_cycles',cycle_id)).intention.behavior==expected
        assert dict(r.store.one('commitments',cid))==original
        if expected is not None:
            review=r.subject.run(event.model_copy(update={'source_key':'development.explicit-due-review','commitment_check_id':cid,'observed_at_us':clock.utc_now_us()}))
            assert review.intention.slot_key=='commitment-review' and review.intention.behavior is None
        assert dict(r.store.one('commitments',cid))==original


@pytest.mark.parametrize('preference',['CREATE','LEARN'])
def test_same_choice_uses_original_provider_self_budget_and_one_ledger_without_erasing_promise(tmp_path,preference):
    from nana_core.continuity.cognition import CognitiveProposal
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    home=tmp_path/'home';initialize(home);clock=VirtualClock();seen=[]
    def propose(request):
        seen.append(request);context=json.loads(request.context_json);identity=context['manifest']
        frame=next(json.loads(b['data_json']) for b in context['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert any(m['source']=='COMMITMENT' and m['strength']=='PRESSING' for m in frame['motivations'])
        return StructuredProposal(interpretation='SYNTHETIC bounded autonomous alternative',subject_cognition=CognitiveProposal(identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC choose an offered interest while leaving the promise outstanding',preferred_behavior=preference,proposed_operations=('DRAFT',)))
    with provider_harness(proposer=propose) as (transport,state),LifeApplication(home,clock=clock) as app:
        app.pause();r=app.runtime
        origin=capture(r,'provider-due-promise',{'source':'SYNTHETIC independently adopted due promise'})
        commitments=CommitmentService(r.store,r.authority)
        cid=commitments.propose(CommitmentCandidate(entity_id='project-user',scope='project-work',description='SYNTHETIC promise remains outstanding',support_memory_ids=(origin,),due_at_us=clock.utc_now_us()-1))
        commitments.transition(cid,'ADOPTED',expected_revision=1,authority=r.authority);promise=dict(r.store.one('commitments',cid))
        cue=ConcernCue(cue_kind='OPPORTUNITY',motivation_source='CREATIVE_INTEREST',topic_key='provider-new-interest',possible_behaviors=('CREATE','LEARN','REST'),learning_value=LearningValue(goal_value='HIGH',future_reuse='HIGH',interest='HIGH'))
        mid=capture(r,'provider-new-interest',cue.model_dump(mode='json'),predicate='concern.provider-new-interest')
        event=SubjectInput(source_key='development.provider-new-interest',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',observed_at_us=clock.utc_now_us(),source_memory_ids=(mid,))
        port=CognitionSession(r,transport,app.policy).subject_port(privacy_class='PROJECT',budget=CognitionBudget(input_tokens=65536))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy)
        assert result.intention.behavior==preference and dict(r.store.one('commitments',cid))==promise
        assert state['calls']==1 and len(seen)==1 and seen[0].cognitive_role=='SELF' and seen[0].budget.timeout_ms==120000
        assert len(r.store.all('cognitive_requests'))==1 and not r.store.all('runtime_cognition_calls')
        assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('goals')
        assert r.subject.cognize(event,model=port,authority=r.authority,policy=app.policy).cycle_id==result.cycle_id
        assert state['calls']==1
