import json
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.open_agency.learning import LearningProblem
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.subject.context_fit import InteractionSignal
from nana_core.continuity.subject import SubjectInput
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND,RuntimeEvent,Cause
from tools.nana_vision_first.demo import run,source,cue,post,advance
from .test_context_fit import interaction


def test_controlled_capability_and_separate_life_causality_with_ablation(tmp_path):
    normal=run(tmp_path/'normal');ablation=run(tmp_path/'ablation',withdraw=True)
    assert normal['pre_intervention']==ablation['pre_intervention']
    assert normal['baseline_actual']!=normal['baseline_expected']
    assert normal['training']['EVALUATE']['all_passed'] and normal['training']['TRANSFER']['all_passed']
    assert normal['later_actual']==normal['later_expected'] and normal['later_method']=='NUMERIC_SUM'
    assert normal['social_available']=='REPORT_DISCOVERY' and normal['no_interest_intention']=='NO_ACTION'
    assert not ablation['life_opportunities'] and ablation['social_proposal'] is None
    assert normal['restart_identity_stable'] and normal['model_port_swap_identity_stable'] and normal['counterexample_suspended_strategy']


def test_learning_proposer_cannot_see_heldout_and_closed_topic_pauses_work(tmp_path):
    class Spy:
        problem=None
        def propose_method(self,problem):
            assert type(problem) is LearningProblem
            assert not hasattr(problem,'evaluation') and not hasattr(problem,'transfer')
            self.problem=problem;return problem.hypotheses[0]
    clock=VirtualClock()
    with open_runtime(tmp_path/'subject/self.db',clock) as r:
        spy=Spy();r.work.configure_open_learning((numeric_learning(),),proposer=spy)
        root=source(r,'gap',{'data':'A synthetic local measurement gap'})
        mid=cue(r,'want-learning',ConcernCue(cue_kind='OPEN_LOOP',topic_key='private-topic',motivation_source='CAPABILITY_GAP',possible_behaviors=('LEARN',),program_id='learn.numbers'),parents=(root,))
        post(r,'choose',(mid,));r.step()
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();assert job
        r.subject.run(interaction(r,'close','DECLINE_DEPTH','private-topic'))
        value=r.work.open_learning.slice();assert value['reason']=='CONTEXT_TOPIC_CLOSED' and spy.problem is None
        assert r.store.one('jobs',job['job_id'])['cursor']==job['cursor']
        r.subject.run(interaction(r,'reopen','REOPEN','private-topic'))
        # Reopen alone never starts/retries anything; a new C adoption is needed.
        assert r.store.one('jobs',job['job_id'])['state']=='BLOCKED'
        post(r,'reconsider',(mid,));advance(r,clock,20)
        assert r.store.one('jobs',job['job_id'])['state']=='DONE' and spy.problem is not None
        assert r.work.open_learning.strategy('numbers','world')


def test_focus_input_preempts_pending_learning_slice_without_dropping_it(tmp_path):
    clock=VirtualClock()
    with open_runtime(tmp_path/'subject/self.db',clock) as r:
        r.work.configure_open_learning((numeric_learning(),))
        root=source(r,'own-gap',{'data':'Independent synthetic precision interest'})
        mid=cue(r,'own-interest',ConcernCue(cue_kind='OPEN_LOOP',topic_key='own-measurement',motivation_source='CREATIVE_INTEREST',possible_behaviors=('LEARN',),program_id='learn.numbers'),parents=(root,))
        post(r,'own-cycle',(mid,));r.step()
        job=r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING'").fetchone();assert job
        e=interaction(r,'focus-now','FOCUS','urgent-help')
        r.submit(RuntimeEvent(event_type='USER_EVENT',trigger='INCOMING_EVENT',input=e,causes=(Cause(kind='CANONICAL_SELF',reference_id=r.identity_id),),due_at_us=clock.utc_now_us(),priority=3))
        value=r.step();assert value['cycle'].context_fit.mode=='FOCUS'
        assert r.store.one('jobs',job['job_id'])['cursor']==job['cursor'] and r.store.one('jobs',job['job_id'])['state']=='WAITING'
        advance(r,clock,20);assert r.store.one('jobs',job['job_id'])['state']=='DONE'

def test_legacy_learn_input_is_sanitized_before_existing_http_transport(tmp_path):
    from nana_core.continuity.world_loop.harness import provider_harness
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.continuity.world_loop.ports import CognitionLearningProposer
    from nana_core.continuity.world_loop.reference import context_policy
    from nana_core.continuity.records import RecordService
    with open_runtime(tmp_path/'subject/self.db',VirtualClock()) as r,provider_harness() as (transport,metrics):
        mid=source(r,'practice-source',{'data':'Public synthetic precision gap'})
        session=CognitionSession(r,transport,context_policy());port=CognitionLearningProposer(session,(mid,))
        assert port.propose_method(numeric_learning())=='NUMERIC_SUM' and metrics['calls']==1
        record=RecordService(r.store).read(port.last_record_id)
        # Follow the proposal's accepted request record, not a captured mock DTO.
        request=r.store.all('cognitive_requests')[0]
        inp=RecordService(r.store).read(request['record_id'])['payload']['request']['role_input']
        assert set(inp)=={'learning_key','domain','baseline_method','hypotheses','practice'}
        assert 'evaluation' not in inp and 'transfer' not in inp

def test_refusal_also_fences_an_already_adopted_private_plan(tmp_path):
    from tools.nana_vision_first.demo import configure,objective,offer
    clock=VirtualClock()
    with open_runtime(tmp_path/'subject/self.db',clock) as r:
        obj=objective('private-topic',[1.25,2.5]);world=configure(r,tmp_path,(obj,),grant=True)
        world.seed_observation(obj.operators[0].resource,[1.25,2.5]);offer(r,obj,'private-plan');r.step()
        assert r.store.all('goals')[0]['state']=='ACTIVE' and not r.store.all('actions')
        r.subject.run(interaction(r,'stop-private-plan','DECLINE_DEPTH',obj.objective_id))
        advance(r,clock,4)
        assert not r.store.all('actions') and r.store.all('goals')[0]['state']=='BLOCKED'
