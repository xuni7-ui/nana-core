"""Current load competes with a supported light interest, without commanding rest/work."""
import pytest
from nana_core.continuity.open_life.opportunities import OpportunityQueue
from nana_core.continuity.subject.opportunities import LearningValue
from nana_core.continuity.world_loop.reference import capture, open_runtime
from nana_core.continuity.memory import MemoryService
from .test_attention_research import runtime as runtime, candidate, judge
from .test_adopted_interest import adopt_interest


@pytest.mark.parametrize('behavior,cost,expected',[
    ('CREATE','LIGHT','CREATE'),('LEARN','LIGHT','LEARN'),
    ('CREATE','HEAVY','REST'),('LEARN','HEAVY','REST'),
])
def test_sourced_rest_motive_can_compete_with_light_personal_interest(runtime,behavior,cost,expected):
    r=runtime;adopt_interest(r)
    mid=capture(r,'loaded-interest-option',{'source':'SYNTHETIC supported interest during current load'})
    item=candidate(r,mid,cost=cost)
    item=item.model_copy(update={'cue':item.cue.model_copy(update={'possible_behaviors':(behavior,'REST'),
        'cognitive_load':'HIGH','learning_value':LearningValue(goal_value='LOW',future_reuse='LOW',interest='HIGH',
            time_compute_cost=cost) if behavior=='LEARN' else None})})
    q=OpportunityQueue(r);result=judge(r,q,q.offer(item))
    assert result['behavior']==expected
    cycle=r.subject.result(r.store.one('subject_cycles',result['cycle_id']))
    rest=[m for m in cycle.motivations if m.source=='REST']
    assert len(rest)==1 and rest[0].strength=='RELEVANT' and rest[0].source_ids
    assert any(m.source=='CURIOSITY' for m in cycle.motivations)
    assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


def test_light_choice_survives_restart_but_withdrawal_removes_its_support(runtime):
    r=runtime;support=adopt_interest(r)
    old_event=r.store.one('subject_cycles',support[0].cycle_id)['subject_event_id']
    support_mid=r.store.one('subject_events',old_event)['memory_id']
    path,clock,identity=r.store.path,r.clock.source,r.identity_id;r.stop()
    with open_runtime(path,clock) as current:
        assert current.identity_id==identity
        q=OpportunityQueue(current)
        def offer(key,behaviors):
            mid=capture(current,key,{'source':'SYNTHETIC current load with a private light option'})
            item=candidate(current,mid)
            return q.offer(item.model_copy(update={'cue':item.cue.model_copy(update={
                'possible_behaviors':behaviors,'cognitive_load':'HIGH'})}))
        assert judge(current,q,offer('quiet-first',('REST','CREATE')))['behavior']=='REST'
        assert judge(current,q,offer('private-light-choice',('CREATE','REST')))['behavior']=='CREATE'
        MemoryService(current.store,current.authority).forget(support_mid,current.authority)
        assert judge(current,q,offer('withdrawn-light-choice',('CREATE','REST')))['behavior']=='REST'
        assert not current.store.all('actions') and not current.store.all('grants') and not current.store.all('cognitive_requests')
