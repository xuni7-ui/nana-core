"""Load remains a competing motive when C explicitly considers an adopted step."""
import json
import pytest
from nana_core.continuity.cognition import AnalyticalFixturePort, CognitiveProposal
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.subject.opportunities import ConcernCue
from tests.open_autonomy.helpers import fresh, configure, objective, capture
from .test_deliberated_plan_alternative import ready


def loaded(r,event):
    original=ConcernCue.model_validate_json(r.subject.records.memory.read(event.source_memory_ids[0])['text'])
    current=original.model_copy(update={'cognitive_load':'HIGH','urgency':'LOW'})
    mid=capture(r,'current-deliberated-heavy-plan',current.model_dump_json(),predicate='concern.plan.current-load')
    return event.model_copy(update={'source_key':'synthetic.deliberated-heavy-plan',
                                   'source_memory_ids':(mid,*event.source_memory_ids[1:])})


@pytest.mark.parametrize('preference,prohibited,expected',[
    ('CONTINUE_PROJECT',(),'CONTINUE_PROJECT'),
    ('REST',(),'REST'),(None,(),'REST'),('CREATE',(),'CREATE'),
    ('CONTINUE_PROJECT',('CONTINUE_PROJECT',),'REST'),
])
def test_explicit_plan_continuation_can_compete_with_rest_without_hiding_load_or_norms(tmp_path,preference,prohibited,expected):
    seen=[]
    class Choosing:
        descriptor='synthetic-deliberated-heavy-plan'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            if preference:value['preferred_behavior']=preference
            return json.dumps(value)
    path=tmp_path/'self.db'
    with fresh(path) as r:
        view,event=ready(r,tmp_path,prohibited);event=loaded(r,event)
        goal=dict(r.store.one('goals',view.goal_id));job=dict(r.store.one('jobs',view.reference.work_id));identity=r.identity_id
        policy=ContextPolicy(policy_id='deliberated-heavy-plan',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=policy)
        assert result.intention.behavior==expected
        frame=next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert any(m['source']=='REST' for m in frame['motivations'])
        assert any(m['source']=='ADOPTED_GOAL' and view.goal_id in m['source_ids'] for m in frame['motivations'])
        assert result.realization_target==(view.target if expected=='CONTINUE_PROJECT' else None)
        assert r.store.one('goals',view.goal_id)==goal and r.store.one('jobs',view.reference.work_id)==job
        assert not r.store.all('actions') and not r.store.all('grants')
        assert r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=policy).cycle_id==result.cycle_id
        assert len(seen)==1
        cycle=result.cycle_id
    with fresh(path) as r:
        configure(r,tmp_path/'world.fixture.json',(objective(),),grant=False)
        assert r.identity_id==identity
        assert r.subject.result(r.store.one('subject_cycles',cycle)).intention.behavior==expected
        assert r.store.one('goals',view.goal_id)==goal and r.store.one('jobs',view.reference.work_id)==job
        assert not r.store.all('actions')


def test_explicit_high_load_choice_reaches_original_step_consumer_only_with_existing_grant(tmp_path):
    class Continue:
        descriptor='synthetic-heavy-plan-continue'
        def propose(self,request):
            value=json.loads(AnalyticalFixturePort().propose(request));value['preferred_behavior']='CONTINUE_PROJECT'
            return json.dumps(value)
    with fresh(tmp_path/'self.db') as r:
        view,event=ready(r,tmp_path,grant=True);event=loaded(r,event)
        policy=ContextPolicy(policy_id='deliberated-heavy-plan',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        result=r.subject.cognize(event,model=Continue(),authority=r.authority,policy=policy)
        assert result.intention.behavior=='CONTINUE_PROJECT' and result.realization_target==view.target
        r.work.after_cycle(result,event)
        assert len(r.store.all('actions'))==1 and r.store.all('actions')[0]['state']=='SUCCEEDED'
        assert r.store.one('jobs',view.reference.work_id)['cursor']==view.reference.cursor+1
        assert len(r.store.all('goals'))==1


def test_same_original_provider_proposal_survives_high_load_before_original_c_choice(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    seen=[]
    def propose(request):
        seen.append(request);manifest=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC load is a competing motive',
            subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
                interpretation='SYNTHETIC choose one currently supported step while retaining rest as an option',
                preferred_behavior='CONTINUE_PROJECT',proposed_operations=('DRAFT',)))
    with provider_harness(proposer=propose) as (transport,metrics),fresh(tmp_path/'self.db',schema_target=13) as r:
        view,event=ready(r,tmp_path);event=loaded(r,event)
        policy=ContextPolicy(policy_id='deliberated-heavy-plan',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        port=CognitionSession(r,transport,policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=65536))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=policy)
        print(json.dumps({'measurement':'original_provider_heavy_plan','behavior':result.intention.behavior,
                          'http_calls':metrics['calls'],'request_json_bytes':len(seen[0].model_dump_json().encode()),
                          'budget':seen[0].budget.model_dump(),'real_model_calls':0}))
        assert result.intention.behavior=='CONTINUE_PROJECT' and result.realization_target==view.target
        assert metrics['calls']==1 and seen[0].budget.timeout_ms==120000
        assert not r.store.all('actions') and not r.store.all('grants')
