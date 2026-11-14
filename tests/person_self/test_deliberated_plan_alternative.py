"""The adopted next step is sourced before C thinks, and remains a candidate."""
import json
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.agency import step_view
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue,LearningValue
from tests.open_autonomy.helpers import fresh,configure,objective,capture,cue,send


def ready(r,tmp_path,prohibited=(),*,grant=False):
    obj=objective();port=configure(r,tmp_path/'world.fixture.json',(obj,),grant=grant)
    port.seed_observation(obj.operators[0].resource,[1.2,2.3])
    send(r,'adopt-plan-alternative',(cue(r,obj),));r.step()
    ref=r.work.agency.next_reference();assert ref is not None
    view=step_view(r.store,ref,scope='lab',privacy_classes=('PERSONAL',))
    current=ConcernCue(cue_kind='OPEN_LOOP',topic_key='plan.alternative',motivation_source='CREATIVE_INTEREST',possible_behaviors=('CONTINUE_PROJECT','CREATE','LEARN','REST'),learning_value=LearningValue(goal_value='HIGH',future_reuse='HIGH',interest='HIGH'))
    mid=capture(r,'current-plan-alternative',current.model_dump_json(),predicate='concern.plan.alternative')
    mids=[mid]
    if prohibited:
        norm=ConcernCue(cue_kind='CONSTRAINT',topic_key=current.topic_key,motivation_source='NORM',prohibited_behaviors=prohibited)
        mids.append(capture(r,'plan-alternative-norm',norm.model_dump_json(),predicate='concern.constraint.plan-alternative'))
    event=SubjectInput(source_key='synthetic.deliberated-plan-alternative',kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope='lab',observed_at_us=r.clock.utc_now_us(),source_memory_ids=tuple(mids),realization_target=view.target,goal_step=ref)
    return view,event


@pytest.mark.parametrize('preference,prohibited,expected',[
    ('CREATE',(),'CREATE'),('LEARN',(),'LEARN'),('REST',(),'REST'),
    ('CONTINUE_PROJECT',(),'CONTINUE_PROJECT'),(None,(),'CONTINUE_PROJECT'),
    ('CREATE',('CREATE',),'CONTINUE_PROJECT'),
])
def test_c_considers_adopted_plan_and_can_choose_another_current_activity_without_advancing_it(tmp_path,preference,prohibited,expected):
    path=tmp_path/'s.db';seen=[]
    class Choosing:
        descriptor='synthetic-original-plan-alternative'
        def propose(self,request):
            seen.append(request);value=json.loads(AnalyticalFixturePort().propose(request))
            if preference:value['preferred_behavior']=preference
            return json.dumps(value)
    with fresh(path) as r:
        view,event=ready(r,tmp_path,prohibited)
        goal=dict(r.store.one('goals',view.goal_id));job=dict(r.store.one('jobs',view.reference.work_id));identity=r.identity_id
        policy=ContextPolicy(policy_id='plan-alternative',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        chosen=r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=policy)
        assert chosen.intention.behavior==expected
        frame=next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert frame['appraisal']['goal_relevance']=='RELEVANT'
        assert any(m['source']=='ADOPTED_GOAL' and view.goal_id in m['source_ids'] for m in frame['motivations'])
        assert view.record_id in frame['source_record_ids']
        assert chosen.realization_target==(view.target if expected=='CONTINUE_PROJECT' else None)
        assert r.store.one('goals',view.goal_id)==goal and r.store.one('jobs',view.reference.work_id)==job
        assert not r.store.all('grants') and not r.store.all('actions')
        assert r.subject.cognize(event,model=Choosing(),authority=r.authority,policy=policy).cycle_id==chosen.cycle_id and len(seen)==1
        cycle_id=chosen.cycle_id
    with fresh(path) as r:
        configure(r,tmp_path/'world.fixture.json',(objective(),),grant=False)
        assert r.identity_id==identity and r.subject.result(r.store.one('subject_cycles',cycle_id)).intention.behavior==expected
        assert r.store.one('goals',view.goal_id)==goal and r.store.one('jobs',view.reference.work_id)==job
        assert not r.store.all('actions') and not r.store.all('grants')


def test_stale_step_is_rejected_before_cognition_and_read_only_projection_keeps_original_target_binding(tmp_path):
    with fresh(tmp_path/'s.db') as r:
        view,event=ready(r,tmp_path);policy=ContextPolicy(policy_id='plan-alternative',allowed_scopes=('lab',),readable_privacy=('PERSONAL',));calls=[]
        class ShouldNotRun:
            descriptor='synthetic-stale-plan-must-not-think'
            def propose(self,request):calls.append(request);return AnalyticalFixturePort().propose(request)
        stale=event.model_copy(update={'goal_step':view.reference.model_copy(update={'revision':view.reference.revision+1})})
        with pytest.raises(CoreError,match='STALE_GOAL_STEP'):r.subject.cognize(stale,model=ShouldNotRun(),authority=r.authority,policy=policy)
        assert calls==[]
        source=r.subject.ingress.ingest(event.model_copy(update={'source_key':'synthetic.read-only-plan-projection'}))
        snapshot=r.store.snapshot();writes=r.store.db.total_changes
        situation=r.subject.situation(event,source)
        assert situation.plan_step==view
        assert r.store.snapshot()==snapshot and r.store.db.total_changes==writes
        wrong=event.model_copy(update={'source_key':'synthetic.wrong-plan-target','realization_target':view.target.model_copy(update={'resource':'synthetic://wrong'})})
        with pytest.raises(CoreError,match='GOAL_STEP_TARGET_MISMATCH'):r.subject.cognize(wrong,model=ShouldNotRun(),authority=r.authority,policy=policy)
        assert calls==[] and not r.store.all('actions') and not r.store.all('grants')


def test_other_choice_reaches_original_execution_consumer_without_using_step_grant_then_can_resume(tmp_path):
    from nana_core.continuity.agency_contracts import GoalReviewRef
    class Creative:
        descriptor='synthetic-current-creative-choice'
        def propose(self,request):
            value=json.loads(AnalyticalFixturePort().propose(request));value['preferred_behavior']='CREATE';return json.dumps(value)
    with fresh(tmp_path/'s.db') as r:
        view,event=ready(r,tmp_path,grant=True)
        assert r.store.all('grants') and not r.store.all('actions')
        original=dict(r.store.one('jobs',view.reference.work_id))
        policy=ContextPolicy(policy_id='plan-alternative',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        chosen=r.subject.cognize(event,model=Creative(),authority=r.authority,policy=policy)
        assert chosen.intention.behavior=='CREATE' and chosen.realization_target is None
        result=r.work.after_cycle(chosen,event)
        assert result['reason']=='SUBJECT_DEFERRED' and not r.store.all('actions')
        parked=r.store.one('jobs',view.reference.work_id);goal=r.store.one('goals',view.goal_id)
        assert parked['cursor']==original['cursor'] and goal['state']=='BLOCKED'
        # Only a fresh, sourced original C review returns the same goal to
        # availability. Neither the old choice nor an old effect is replayed.
        source=capture(r,'fresh-plan-return','SYNTHETIC later decision to reconsider the retained plan.')
        review=SubjectInput(source_key='synthetic.plan-alternative-return',kind='WAKE',origin='SELF_WAKE',entity_id=r.config.entity_id,scope='lab',observed_at_us=r.clock.utc_now_us(),source_memory_ids=(source,),goal_review=GoalReviewRef(goal_id=view.goal_id,version=goal['version'],cause_memory_id=source))
        reviewed=r.subject.run(review);r.work.after_cycle(reviewed,review)
        ref=r.work.agency.next_reference();assert ref is not None and ref.cursor==view.reference.cursor
        resumed=step_view(r.store,ref,scope='lab',privacy_classes=('PERSONAL',))
        assert resumed.goal_id==view.goal_id and len(r.store.all('goals'))==1 and not r.store.all('actions')
        current=ConcernCue(cue_kind='OPEN_LOOP',topic_key='plan.resume',motivation_source='LONG_TERM_GOAL',possible_behaviors=('CONTINUE_PROJECT','REST'))
        mid=capture(r,'current-plan-resume',current.model_dump_json(),predicate='concern.plan.resume')
        continuing=event.model_copy(update={'source_key':'synthetic.actual-plan-resume','goal_step':ref,'realization_target':resumed.target,'source_memory_ids':(mid,)})
        accepted=r.subject.run(continuing);assert accepted.intention.kind=='ACTION_PROPOSAL'
        r.work.after_cycle(accepted,continuing)
        assert len(r.store.all('actions'))==1 and r.store.all('actions')[0]['state']=='SUCCEEDED'
        assert r.store.one('jobs',ref.work_id)['cursor']==ref.cursor+1


@pytest.mark.parametrize('preference',['CREATE','CONTINUE_PROJECT'])
def test_actual_provider_sees_adopted_step_before_selecting_its_current_choice(tmp_path,preference):
    from nana_core.continuity.cognition import CognitiveProposal
    from nana_core.continuity.world_loop.cognition import CognitionSession,CognitionBudget,StructuredProposal
    from nana_core.continuity.world_loop.harness import provider_harness
    seen=[]
    def propose(request):
        seen.append(request);manifest=json.loads(request.context_json)['manifest']
        return StructuredProposal(interpretation='SYNTHETIC sourced plan competition',subject_cognition=CognitiveProposal(identity_id=manifest['identity_id'],identity_revision=manifest['identity_revision'],interpretation='SYNTHETIC choose between an adopted step and another current interest',preferred_behavior=preference,proposed_operations=('DRAFT',)))
    with provider_harness(proposer=propose) as (transport,state),fresh(tmp_path/'s.db',schema_target=13) as r:
        view,event=ready(r,tmp_path)
        policy=ContextPolicy(policy_id='plan-alternative',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        port=CognitionSession(r,transport,policy).subject_port(privacy_class='PERSONAL',budget=CognitionBudget(input_tokens=65536))
        result=r.subject.cognize(event,model=port,authority=r.authority,policy=policy)
        assert result.intention.behavior==preference
        frame=next(json.loads(b['data_json']) for b in json.loads(seen[0].context_json)['blocks'] if b['kind']=='SUBJECT_APPRAISAL')
        assert any(m['source']=='ADOPTED_GOAL' and view.goal_id in m['source_ids'] for m in frame['motivations'])
        assert result.realization_target==(view.target if preference=='CONTINUE_PROJECT' else None)
        assert state['calls']==1 and seen[0].budget.timeout_ms==120000
        assert len(r.store.all('cognitive_requests'))==1 and not r.store.all('runtime_cognition_calls')
        assert not r.store.all('actions') and not r.store.all('grants')


def test_wrong_step_target_is_rejected_before_a_model_call(tmp_path):
    with fresh(tmp_path/'s.db') as r:
        view,event=ready(r,tmp_path);calls=[]
        class Counting:
            descriptor='synthetic-wrong-step-target'
            def propose(self,request):calls.append(request);return AnalyticalFixturePort().propose(request)
        wrong=event.model_copy(update={'realization_target':view.target.model_copy(update={'resource':'synthetic://wrong'})})
        policy=ContextPolicy(policy_id='plan-alternative',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
        with pytest.raises(CoreError,match='GOAL_STEP_TARGET_MISMATCH'):r.subject.cognize(wrong,model=Counting(),authority=r.authority,policy=policy)
        assert calls==[] and not r.store.all('actions') and not r.store.all('grants')
