"""The original plan-review opportunity can be declined without erasing its goal."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.cognition import AnalyticalFixturePort,CognitiveProposal
from nana_core.continuity.context import ContextPolicy
from .test_deliberated_goal_review import adopted,review
from tests.open_autonomy.helpers import fresh,capture


def replan(r,goal,*,load='LOW',options=('LEARN','REST','CREATE'),prohibited=(),no_cue=False):
    event=review(r,goal,load=load,options=options,prohibited=prohibited)
    event=event.model_copy(update={'goal_review':event.goal_review.model_copy(update={'purpose':'REPLAN'})})
    if no_cue:
        mid=capture(r,'plain-replan-cause','SYNTHETIC newly retained information for the existing plan.')
        event=event.model_copy(update={'source_memory_ids':(mid,),
            'goal_review':event.goal_review.model_copy(update={'cause_memory_id':mid})})
    return event


@pytest.mark.parametrize('preference,load,prohibited,expected',[
    ('REST','LOW',(),'REST'),('CREATE','LOW',(),'CREATE'),('LEARN','HIGH',(),'LEARN'),
    (None,'LOW',(),'LEARN'),(None,'HIGH',(),'REST'),
    ('LEARN','LOW',('LEARN',),'REST'),('REST','LOW',('REST',),'LEARN'),
])
def test_original_replan_review_respects_current_choice_and_norms(tmp_path,preference,load,prohibited,expected):
    seen=[]
    class Current:
        descriptor='synthetic-replan-choice'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            if preference:value['preferred_behavior']=preference
            return json.dumps(value)
    path=tmp_path/'self.db'
    with fresh(path,schema_target=13) as r:
        _,goal=adopted(r,tmp_path);identity=r.identity_id
        event=replan(r,goal,load=load,prohibited=prohibited)
        policy=ContextPolicy(policy_id='synthetic-current-replan',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        plan_before=r.store.one('goals',goal['goal_id']);jobs_before=r.store.all('jobs');grants_before=r.store.all('grants')
        result=r.subject.cognize(event,model=Current(),authority=r.authority,policy=policy)
        assert result.intention.behavior==expected
        assert result.intention.kind==('NO_ACTION' if expected=='REST' else 'GOAL_CANDIDATE')
        assert len(seen)==1
        if expected!='LEARN':
            r.work.after_cycle(result,event)
            assert r.store.one('goals',goal['goal_id'])==plan_before and r.store.all('jobs')==jobs_before
        assert not r.store.all('actions') and r.store.all('grants')==grants_before
        cid=result.cycle_id
    with fresh(path,schema_target=13) as r:
        assert r.identity_id==identity and r.subject.result(r.store.one('subject_cycles',cid)).intention.behavior==expected
        assert r.store.one('goals',goal['goal_id'])==plan_before
        result=r.subject.cognize(event,model=Current(),authority=r.authority,policy=policy)
        assert result.cycle_id==cid and len(seen)==1 and not r.store.all('actions')


def test_original_self_can_decline_replan_without_a_second_cue_or_model_phase(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    seen=[]
    def propose(request):
        seen.append(request);manifest=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC optional supported plan review',
            subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],
                interpretation='SYNTHETIC keep the plan and rest instead of revising it now',preferred_behavior='REST',proposed_operations=('DRAFT',)))
    with fresh(tmp_path/'self.db',schema_target=13) as r,provider_harness(proposer=propose) as (transport,metrics):
        _,goal=adopted(r,tmp_path);event=replan(r,goal,no_cue=True)
        policy=ContextPolicy(policy_id='synthetic-native-replan',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        grants_before=r.store.all('grants')
        port=CognitionSession(r,transport,policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=65536))
        try:result=r.subject.cognize(event,model=port,authority=r.authority,policy=policy)
        finally:
            print(json.dumps({'measurement':'original-replan-self-attempt','http_calls':metrics['calls'],
                'request_json_bytes':len(seen[0].model_dump_json().encode()) if seen else None,
                'budget':seen[0].budget.model_dump() if seen else None,'real_model_calls':0}))
        assert result.intention.kind=='NO_ACTION' and result.intention.behavior=='REST'
        frame=next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert set(frame['behavior_options'])=={'LEARN','REST'}
        r.work.after_cycle(result,event)
        assert r.store.one('goals',goal['goal_id'])==goal and metrics['calls']==1
        assert not r.store.all('actions') and r.store.all('grants')==grants_before
        print(json.dumps({'measurement':'original-replan-self','http_calls':metrics['calls'],
            'request_json_bytes':len(seen[0].model_dump_json().encode()),'budget':seen[0].budget.model_dump(),
            'behavior':result.intention.behavior,'real_model_calls':0}))


def test_replan_projection_is_read_only_and_stale_goal_is_rejected_before_model(tmp_path):
    with fresh(tmp_path/'self.db',schema_target=13) as r:
        _,goal=adopted(r,tmp_path);event=replan(r,goal,no_cue=True)
        source=r.subject.ingress.ingest(event);writes=r.store.db.total_changes
        situation=r.subject.situation(event,source)
        assert situation.goal_review_id==goal['goal_id'] and situation.goal_review_purpose=='REPLAN'
        assert json.loads(goal['body_json'])['record_id'] in situation.support_record_ids
        assert r.store.db.total_changes==writes
        called=[]
        class MustNotThink:
            descriptor='synthetic-stale-replan'
            def propose(self,request):called.append(request);raise AssertionError('STALE_REPLAN_MODEL')
        stale=event.model_copy(update={'source_key':'synthetic.stale-replan',
            'goal_review':event.goal_review.model_copy(update={'version':event.goal_review.version+1})})
        policy=ContextPolicy(policy_id='synthetic-stale-replan',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        with pytest.raises(CoreError,match='STALE_GOAL_REVIEW'):
            r.subject.cognize(stale,model=MustNotThink(),authority=r.authority,policy=policy)
        assert called==[] and not r.store.all('actions')
