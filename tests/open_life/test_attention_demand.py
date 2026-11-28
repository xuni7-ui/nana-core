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


def test_already_scheduled_experiences_leave_room_for_a_new_verified_outcome(tmp_path):
    from nana_core.continuity.learning import ExperienceInput, ExperienceService
    from nana_core.presence.runtime import NanaRuntime
    from nana_core.storage import canonical, digest
    from tests.open_autonomy.helpers import capture, fresh

    def observe(runtime, index):
        service=ExperienceService(runtime.store,runtime.authority)
        observed=capture(runtime,f'readback-{index}',canonical({'data':index}))
        check=service.verify_structured_result(observed,digest(index),runtime.authority)
        return service.record(ExperienceInput(context_memory_ids=(observed,),scope='lab',task_class='numbers',
            decision='Consider an independently checked result',result_memory_id=observed,verification_memory_id=check))

    path=tmp_path/'self.db'
    with fresh(path,schema_target=13) as runtime:
        older=[observe(runtime,i) for i in range(32)]
        runtime.refresh_attention()
        runtime.step()
        schedules=runtime.store.all('runtime_schedules')
        assert {row['dedupe_key'] for row in schedules if row['dedupe_key'].startswith('reflection-')} == {
            f'reflection-{identifier}' for identifier in older}
        assert not runtime.store.all('subject_reflections')
        newest=observe(runtime,32)
        config,clock,identity=runtime.config,runtime.clock.source,runtime.identity_id

    with NanaRuntime(path,config,clock=clock) as runtime:
        assert runtime.identity_id==identity
        runtime.refresh_attention()
        runtime.step()
        key=f'reflection-{newest}'
        schedule=runtime.store.db.execute('SELECT * FROM runtime_schedules WHERE dedupe_key=?',(key,)).fetchone()
        assert schedule and schedule['state']=='ACTIVE'

    clock.advance(config.idle_recall_us)
    with NanaRuntime(path,config,clock=clock) as runtime:
        assert runtime.identity_id==identity
        for _ in range(48):
            runtime.step()
            if runtime.store.db.execute('SELECT 1 FROM subject_reflections WHERE experience_id=?',(newest,)).fetchone():
                break
        else:
            raise AssertionError('Newly verified outcome never reached original C')
        reflected=runtime.store.db.execute('SELECT * FROM runtime_schedules WHERE dedupe_key=?',(key,)).fetchone()
        assert reflected['schedule_id']==schedule['schedule_id'] and reflected['occurrence']==1
        later=runtime.store.one('runtime_queue',reflected['last_queue_id'])
        assert later['state']=='DONE'
        result=runtime.subject.result(runtime.store.one('subject_cycles',later['cycle_id']))
        assert result.intention.kind=='REFLECTION' and not runtime.store.all('actions')

    with NanaRuntime(path,config,clock=clock) as runtime:
        runtime.refresh_attention()
        runtime.step()
        assert runtime.store.db.execute('SELECT occurrence FROM runtime_schedules WHERE dedupe_key=?',(key,)).fetchone()[0]==1
        assert not runtime.store.all('cognitive_requests')
