"""Lifecycle options are a menu, never an automatic instruction to abandon."""
import json
import pytest
from nana_core.continuity.agency_contracts import GoalReviewRef
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from tests.open_autonomy.helpers import fresh,configure,objective,capture,cue,send

ALL=('CONTINUE_PROJECT','REST','WITHDRAW')


def adopted(r,tmp_path):
    obj=objective().model_copy(update={'horizon':'ONGOING','review_after_us':1})
    port=configure(r,tmp_path/'world.fixture.json',(obj,));port.seed_observation(obj.operators[0].resource,[1.2,2.3])
    send(r,'adopt-current-lifecycle',(cue(r,obj),));r.step()
    return obj,r.store.all('goals')[0]


def review(r,goal,*,load,options,prohibited=()):
    current=ConcernCue(cue_kind='OPEN_LOOP',topic_key='ongoing.current-choice',motivation_source='LONG_TERM_GOAL',
                       possible_behaviors=options,cognitive_load=load,urgency='LOW')
    mid=capture(r,'current-goal-choice',current.model_dump_json(),predicate='concern.ongoing.current-choice')
    sources=[mid]
    if prohibited:
        norm=ConcernCue(cue_kind='CONSTRAINT',topic_key=current.topic_key,motivation_source='NORM',prohibited_behaviors=prohibited)
        sources.append(capture(r,'current-goal-norm',norm.model_dump_json(),predicate='concern.ongoing.current-norm'))
    return SubjectInput(source_key='synthetic.current-goal-lifecycle',kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,
        scope='lab',observed_at_us=r.clock.utc_now_us(),source_memory_ids=tuple(sources),
        goal_review=GoalReviewRef(goal_id=goal['goal_id'],version=goal['version'],cause_memory_id=mid,purpose='LIFECYCLE'))


@pytest.mark.parametrize('preference,load,options,prohibited,expected,state',[
    ('CONTINUE_PROJECT','HIGH',ALL,(),'CONTINUE_PROJECT','ACTIVE'),
    ('REST','LOW',ALL,(),'REST','SUSPENDED'),
    ('CONTINUE_PROJECT','HIGH',('CONTINUE_PROJECT','REST'),(),'CONTINUE_PROJECT','ACTIVE'),
    ('WITHDRAW','HIGH',ALL,(),'WITHDRAW','ABANDONED'),
    (None,'HIGH',('CONTINUE_PROJECT','REST'),(),'REST','SUSPENDED'),
    (None,'LOW',ALL,(),'CONTINUE_PROJECT','ACTIVE'),
    ('WITHDRAW','HIGH',ALL,('WITHDRAW',),'REST','SUSPENDED'),
    ('REST','LOW',ALL,('REST',),'CONTINUE_PROJECT','ACTIVE'),
])
def test_current_original_c_chooses_lifecycle_instead_of_menu_membership_or_load(tmp_path,preference,load,options,prohibited,expected,state):
    calls=[]
    class Choosing:
        descriptor='synthetic-current-goal-lifecycle'
        def propose(self,request):
            calls.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            if preference:value['preferred_behavior']=preference
            return json.dumps(value)
    path=tmp_path/'self.db'
    with fresh(path) as r:
        obj,goal=adopted(r,tmp_path);identity=r.identity_id;plan=json.loads(goal['body_json'])['plan_record_id']
        event=review(r,goal,load=load,options=options,prohibited=prohibited)
        policy=ContextPolicy(policy_id='current-lifecycle',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        grants={row['grant_id'] for row in r.store.all('grants')}
        result=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=policy)
        assert result.intention.behavior==expected
        r.work.after_cycle(result,event)
        updated=r.store.one('goals',goal['goal_id'])
        assert updated['state']==state
        assert json.loads(updated['body_json'])['plan_record_id']==plan
        assert len(r.store.all('goals'))==1 and len(calls)==1 and not r.store.all('actions')
        assert {row['grant_id'] for row in r.store.all('grants')}==grants
        frame=next(json.loads(b['data_json']) for b in json.loads(calls[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        if load=='HIGH':assert any(m['source']=='REST' for m in frame['motivations'])
    with fresh(path) as r:
        configure(r,tmp_path/'world.fixture.json',(obj,));assert r.identity_id==identity
        assert r.store.one('goals',goal['goal_id'])['state']==state
        assert json.loads(r.store.one('goals',goal['goal_id'])['body_json'])['plan_record_id']==plan
        assert len(r.store.all('goals'))==1 and not r.store.all('actions')


def test_actual_self_proposal_to_pause_does_not_become_abandonment(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    seen=[]
    def propose(request):
        seen.append(request);manifest=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC pause a continuing interest, do not abandon it',
            subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
                interpretation='SYNTHETIC choose rest from the currently offered lifecycle menu',preferred_behavior='REST',proposed_operations=('DRAFT',)))
    with provider_harness(proposer=propose) as (transport,metrics),fresh(tmp_path/'self.db',schema_target=13) as r:
        _,goal=adopted(r,tmp_path);event=review(r,goal,load='LOW',options=ALL)
        policy=ContextPolicy(policy_id='current-lifecycle',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        port=CognitionSession(r,transport,policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=65536))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=policy)
        r.work.after_cycle(result,event)
        print(json.dumps({'measurement':'original_provider_lifecycle','behavior':result.intention.behavior,
            'state':r.store.one('goals',goal['goal_id'])['state'],'http_calls':metrics['calls'],
            'request_json_bytes':len(seen[0].model_dump_json().encode()),'budget':seen[0].budget.model_dump(),'real_model_calls':0}))
        assert result.intention.behavior=='REST' and r.store.one('goals',goal['goal_id'])['state']=='SUSPENDED'
        assert metrics['calls']==1 and not r.store.all('actions')
