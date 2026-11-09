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


@pytest.mark.parametrize('adopted,load,explicit_review,expected', [
    (True,'LOW',False,'CREATE'),
    (True,'HIGH',False,'REST'),
    (False,'LOW',False,None),
    (True,'LOW',True,None),
])
def test_due_commitment_is_considered_without_a_permanent_veto_on_owned_interest(
        runtime,adopted,load,explicit_review,expected):
    from nana_core.continuity.commitments import CommitmentCandidate,CommitmentService
    from nana_core.continuity.subject.opportunities import ConcernCue
    r=runtime
    interest_sources=adopt_interest(r) if adopted else ()
    source=capture(r,'due-promise-source',{'source':'SYNTHETIC adopted promise'})
    service=CommitmentService(r.store,r.authority)
    cid=service.propose(CommitmentCandidate(entity_id='observer',scope='world',
        description='SYNTHETIC due promise still requires a review',support_memory_ids=(source,),due_at_us=r.clock.utc_now_us()-1))
    service.transition(cid,'ADOPTED',expected_revision=1,authority=r.authority)
    cue=ConcernCue(cue_kind='DISCOVERY',motivation_source='CREATIVE_INTEREST',topic_key='world.question',
        possible_behaviors=('CREATE','WATCH'),resource_class='ORDINARY',cognitive_load=load)
    # Use original C ingress on the same original Store; no forced decision,
    # fake fulfillment, model, planner or permission is injected.
    from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
    memory=MemoryService(r.store)
    evidence=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.interest.choice',
        source_reference='due-choice',source_kind='DIRECT_OBSERVATION'),text=cue.model_dump_json(),privacy_class='PUBLIC',
        observed_time_us=r.clock.utc_now_us()))
    mid=memory.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.SEMANTIC,
        epistemic_kind='OBSERVATION',source_evidence_id=evidence,text=cue.model_dump_json(),predicate_key='concern.world.question'))
    choice=r.subject.run(SubjectInput(source_key='synthetic.due-interest.choice',kind='WAKE',origin='SELF_WAKE',
        entity_id='observer',scope='world',privacy_class='PUBLIC',observed_at_us=r.clock.utc_now_us(),
        source_memory_ids=(mid,),commitment_check_id=cid if explicit_review else None))
    assert choice.intention.behavior==expected
    assert any(m.source=='COMMITMENT' for m in choice.motivations)
    assert service.get(cid).state=='ADOPTED' and service.get(cid).overdue
    if expected is None:assert choice.intention.slot_key=='commitment-review'
    else:
        assert choice.intention.slot_key!='commitment-review'
        assert choice.evaluation.normative==('ENDORSED' if expected=='CREATE' else 'UNDECIDED')
    assert not r.store.all('actions') and not r.store.all('grants') and not r.store.all('cognitive_requests')
    if expected=='CREATE':
        event=r.store.one('subject_events',r.store.one('subject_cycles',interest_sources[0].cycle_id)['subject_event_id'])
        interest_mid=event['memory_id'];path,clock,identity=r.store.path,r.clock.source,r.identity_id
        r.stop()
        with open_runtime(path,clock) as current:
            assert current.identity_id==identity
            current.subject.run(SubjectInput(source_key='synthetic.due-interest.explicit-review',kind='WAKE',origin='SELF_WAKE',
                entity_id='observer',scope='world',privacy_class='PUBLIC',observed_at_us=current.clock.utc_now_us(),
                source_memory_ids=(mid,),commitment_check_id=cid))
            MemoryService(current.store,current.authority).forget(interest_mid,current.authority)
            later=current.subject.run(SubjectInput(source_key='synthetic.due-interest.withdrawn',kind='WAKE',origin='SELF_WAKE',
                entity_id='observer',scope='world',privacy_class='PUBLIC',observed_at_us=current.clock.utc_now_us(),source_memory_ids=(mid,)))
            # The independent promise is intact. Withdrawing the interest source
            # retires dependent earlier choices and removes the exception.
            assert later.intention.behavior is None
            assert later.intention.kind=='GOAL_CANDIDATE' and later.intention.slot_key=='commitment-review'
            assert any(m.source=='COMMITMENT' for m in later.motivations)
            assert CommitmentService(current.store,current.authority).get(cid).state=='ADOPTED'
            assert not current.store.all('actions') and not current.store.all('grants')
