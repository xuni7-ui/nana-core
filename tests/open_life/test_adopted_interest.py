"""Sourced personal interests may compete with generic opportunity scores.

These are original C/Growth/queue executions; no model, learning requirement,
real hobby experience or execution permission is implied by the fixtures.
"""
import pytest

from nana_core.continuity.subject import SubjectInput, PreferenceSignal
from nana_core.continuity.subject.growth import Growth
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.open_life.opportunities import OpportunityQueue
from nana_core.continuity.world_loop.reference import capture, open_runtime
from .test_attention_research import runtime as runtime, candidate, judge


def adopt_interest(r, topic='world.question'):
    results = []
    for index in range(2):
        results.append(r.subject.run(SubjectInput(source_key='synthetic.play-interest.' + str(index),
            kind='PLAY', origin='ENVIRONMENT', entity_id='observer', scope='world', privacy_class='PUBLIC',
            text='SYNTHETIC independent enjoyable experience ' + str(index), observed_at_us=r.clock.utc_now_us(),
            preference_signal=PreferenceSignal(topic=topic, direction='SUPPORT',
                                               interpretation='SYNTHETIC wants to explore or create for enjoyment'))))
    assert Growth(r.store).assertions('world', kind='PREFERENCE')[0]['state'] == 'ADOPTED'
    for old in r.subject.pending('world'):
        r.subject.transition_intention(old['intention_id'], expected_revision=old['revision'], state='DROPPED')
    return results


@pytest.mark.parametrize('behavior,value,novelty,topic,load,expected', [
    ('CREATE', 'LOW', 'NEW', 'world.question', 'LOW', 'CREATE'),
    ('EXPLORE', 'RELEVANT', 'REPEATED', 'world.question', 'LOW', 'EXPLORE'),
    ('CREATE', 'LOW', 'REPEATED', 'another.interest', 'LOW', 'IGNORE'),
    ('CREATE', 'LOW', 'REPEATED', 'world.question', 'HIGH', 'REST'),
])
def test_adopted_personal_interest_survives_generic_score(runtime, behavior, value, novelty, topic, load, expected):
    r = runtime
    adopt_interest(r, topic)
    mid = capture(r, 'leisure-opportunity', {'source': 'SYNTHETIC personal option'})
    item = candidate(r, mid, value=value, novelty=novelty)
    item = item.model_copy(update={'cue': item.cue.model_copy(update={
        'motivation_source': 'CREATIVE_INTEREST', 'possible_behaviors': (behavior, 'WATCH'),
        'cognitive_load': load})})
    queue = OpportunityQueue(r)
    jid = queue.offer(item)
    result = judge(r, queue, jid)
    assert result['behavior'] == expected
    cycles = len(r.store.all('subject_cycles'))
    assert queue.offer(item) == jid
    for _ in range(4):
        queue.opportunity()
    assert len(r.store.all('subject_cycles')) == cycles
    assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')


def test_interest_restart_and_source_withdrawal_remove_the_exception(runtime):
    r = runtime
    support = adopt_interest(r)
    path, clock, identity = r.store.path, r.clock.source, r.identity_id
    event_id = r.store.one('subject_cycles', support[0].cycle_id)['subject_event_id']
    support_mid = r.store.one('subject_events', event_id)['memory_id']
    r.stop()
    with open_runtime(path, clock) as current:
        assert current.identity_id == identity
        mid = capture(current, 'after-restart-option', {'source': 'SYNTHETIC repeat enjoyable option'})
        item = candidate(current, mid, value='LOW', novelty='REPEATED')
        queue = OpportunityQueue(current)
        result = judge(current, queue, queue.offer(item))
        assert result['behavior'] == 'EXPLORE'
        MemoryService(current.store, current.authority).forget(support_mid, current.authority)
        assert Growth(current.store).assertions('world', kind='PREFERENCE')[0]['state'] != 'ADOPTED'
        new_mid = capture(current, 'withdrawn-interest-option', {'source': 'SYNTHETIC separate occurrence'})
        after = item.model_copy(update={'source_memory_ids': (new_mid,)})
        assert judge(current, queue, queue.offer(after))['behavior'] == 'IGNORE'
        assert not current.store.all('actions') and not current.store.all('grants')


@pytest.mark.parametrize('external,compute,time_cost,storage,interruption,expected', [
    ('REQUIRES_RESERVATION', 'LIGHT', 'SHORT', 'SMALL', 'LIGHT', 'EXPLORE'),
    ('UNKNOWN', 'LIGHT', 'SHORT', 'SMALL', 'LIGHT', 'EXPLORE'),
    ('NONE', 'HEAVY', 'SHORT', 'SMALL', 'LIGHT', 'REST'),
    ('NONE', 'LIGHT', 'LONG', 'SMALL', 'LIGHT', 'REST'),
    ('REQUIRES_RESERVATION', 'LIGHT', 'SHORT', 'LARGE', 'LIGHT', 'REST'),
    ('UNKNOWN', 'LIGHT', 'SHORT', 'SMALL', 'HEAVY', 'REST'),
])
def test_external_admission_estimate_does_not_claim_cognitive_load(
        runtime, external, compute, time_cost, storage, interruption, expected):
    from nana_core.continuity.open_life.opportunities import ActivityCost
    r = runtime
    adopt_interest(r)
    mid = capture(r, 'cost-kind', {'source': 'SYNTHETIC independent enjoyable option'})
    item = candidate(r, mid, value='LOW', novelty='REPEATED').model_copy(update={
        'resource_estimate': ActivityCost(external=external, compute=compute,
            time=time_cost, storage=storage, interruption=interruption)})
    queue = OpportunityQueue(r)
    result = judge(r, queue, queue.offer(item))
    assert result['behavior'] == expected
    assert queue.view()[0]['resource_estimate']['external'] == external
    assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')
