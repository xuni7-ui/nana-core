"""A demanding possible activity is not evidence that the Subject is tired."""
import json
import pytest
from nana_core.continuity.open_life.opportunities import OpportunityQueue, ActivityCost
from nana_core.continuity.subject.opportunities import ConcernCue, LearningValue
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.reference import capture, open_runtime
from .test_attention_research import runtime as runtime, candidate, judge
from .test_adopted_interest import adopt_interest


@pytest.mark.parametrize('behavior,demand',[
    ('EXPLORE','cost'),('CREATE','compute'),('CREATE','time'),('EXPLORE','interruption'),
    ('LEARN','learning-cost'),
])
def test_sourced_interest_can_consider_demanding_activity_without_claiming_fatigue(runtime,behavior,demand):
    r=runtime;adopt_interest(r)
    mid=capture(r,'demanding-personal-option',{'source':'SYNTHETIC demanding interest, not an executed activity'})
    item=candidate(r,mid,value='LOW',novelty='REPEATED')
    cue=item.cue.model_copy(update={'possible_behaviors':(behavior,'WATCH'),
        'learning_value':LearningValue(goal_value='LOW',future_reuse='LOW',interest='HIGH',time_compute_cost='HEAVY') if behavior=='LEARN' else None})
    estimate=ActivityCost(**({'compute':'HEAVY'} if demand=='compute' else {'time':'LONG'} if demand=='time'
        else {'interruption':'HEAVY'} if demand=='interruption' else {}))
    item=item.model_copy(update={'cue':cue,'cost':'HEAVY' if demand=='cost' else 'LIGHT','resource_estimate':estimate})
    q=OpportunityQueue(r);result=judge(r,q,q.offer(item))
    assert result['behavior']==behavior and result['normative']=='ENDORSED'
    snapshot=r.store.db.execute("SELECT memory_id FROM memories WHERE predicate_key='concern.world.question'").fetchall()
    actual=[json.loads(MemoryService(r.store).read(row[0])['text']) for row in snapshot]
    assert len(actual)==1 and actual[0]['cognitive_load']=='LOW'
    if demand!='learning-cost':assert actual[0]['attention_demand']=='HEAVY'
    assert q.view()[0]['resource_estimate']==estimate.model_dump(mode='json')
    assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


def test_demanding_interest_survives_restart_but_not_withdrawn_support(runtime):
    r=runtime;support=adopt_interest(r)
    path,clock,identity=r.store.path,r.clock.source,r.identity_id
    event_id=r.store.one('subject_cycles',support[0].cycle_id)['subject_event_id']
    support_mid=r.store.one('subject_events',event_id)['memory_id']
    r.stop()
    with open_runtime(path,clock) as current:
        assert current.identity_id==identity
        q=OpportunityQueue(current)
        mid=capture(current,'restart-heavy-option',{'source':'SYNTHETIC independent candidate'})
        item=candidate(current,mid,cost='HEAVY')
        assert judge(current,q,q.offer(item))['behavior']=='EXPLORE'
        MemoryService(current.store,current.authority).forget(support_mid,current.authority)
        other=capture(current,'after-withdraw-heavy-option',{'source':'SYNTHETIC later independent candidate'})
        assert judge(current,q,q.offer(item.model_copy(update={'source_memory_ids':(other,)})))['behavior']=='REST'
        assert not current.store.all('actions') and not current.store.all('grants')


def test_old_cue_wire_has_no_default_demand_field():
    old={'schema_version':1,'cue_kind':'OPPORTUNITY','motivation_source':'CURIOSITY','topic_key':'world.question'}
    cue=ConcernCue.model_validate_json(json.dumps(old))
    assert cue.attention_demand=='LIGHT' and 'attention_demand' not in json.loads(cue.model_dump_json())
