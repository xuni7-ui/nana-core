"""Renewed, verified gaps can teach the same Subject after an earlier lesson.

All world effects here are explicitly synthetic. The numeric evaluator is the
existing application-owned oracle, not a model or a new learning subsystem.
"""

import json
import pytest

from nana_core.actions import OperatorAuthority
from nana_core.continuity import ContinuityStore, IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.open_agency.learning import LearningCase, LearningSpec
from nana_core.continuity.records import RecordService
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue, LearningValue
from nana_core.continuity.subject.experience_need import project_need
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
from nana_core.presence import NanaRuntime, RuntimeConfig
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import HOUR, LivingRuntimeConfig
from tests.open_autonomy.helpers import configure, objective, cue, send, advance, capture
from tests.open_autonomy.test_learning import number_learning, start_learning


def runtime(path, clock):
    with ContinuityStore(path, clock, schema_target=13) as store:
        IdentityService(store, OperatorAuthority())
        MemoryService(store).entity('synthetic-person', 'PERSON')
    return NanaRuntime(path, RuntimeConfig(schema_target=13, living=LivingRuntimeConfig(),
        scopes=('lab',), entity_id='synthetic-person', idle_recall_us=HOUR), clock=clock)


def jobs(r):
    return r.store.db.execute("SELECT * FROM jobs WHERE work_kind='LEARNING' ORDER BY rowid").fetchall()


def body(r, job):
    return RecordService(r.store).read(job['record_id'])['payload']


def ordering_spec():
    return LearningSpec(learning_key='learn.numbers', domain='numbers', baseline_method='NUMERIC_SUM',
        hypotheses=('NUMERIC_SUM', 'SORT'), hypothesis_policy='PRACTICE_COMPARE',
        practice=(LearningCase(case_id='order-practice', context='readings', data=[3, 1], expected=[1, 3]),),
        evaluation=(LearningCase(case_id='order-eval', context='readings', data=[9, 2, 4], expected=[2, 4, 9]),),
        transfer=(LearningCase(case_id='order-transfer', context='inventory', data=[7, 0, 5], expected=[0, 5, 7]),))


def reconsider(r, key, gap, *, load='LOW'):
    cue_value = ConcernCue(cue_kind='OPEN_LOOP', motivation_source='CAPABILITY_GAP',
        topic_key=key, program_id='learn.numbers', possible_behaviors=('LEARN', 'WATCH'), cognitive_load=load)
    mid = capture(r, key, cue_value.model_dump_json(), predicate='concern.'+key, derived=(gap,))
    cycle = r.subject.run(SubjectInput(source_key='synthetic.renewal.'+key, kind='WAKE', origin='SELF_WAKE',
        entity_id='synthetic-person', scope='lab', observed_at_us=r.clock.utc_now_us(),
        source_memory_ids=(mid,), task_class='numbers'))
    if cycle.intention_id and r.store.one('subject_intentions', cycle.intention_id)['state']=='PENDING':
        r.subject.transition_intention(cycle.intention_id, expected_revision=1, state='DROPPED')
    return cycle


@pytest.mark.parametrize('load,value,expected', [
    ('HIGH', None, 'REST'),
    ('LOW', LearningValue(goal_value='LOW', future_reuse='LOW'), 'WATCH'),
    ('LOW', LearningValue(goal_value='HIGH', future_reuse='HIGH', alternative='AVAILABLE'), 'WATCH'),
    ('LOW', LearningValue(goal_value='HIGH', future_reuse='HIGH', time_compute_cost='HEAVY'), 'REST'),
])
def test_c_declining_learning_does_not_start_background_practice(tmp_path, load, value, expected):
    with runtime(tmp_path/'subject.db', VirtualClock()) as r:
        r.work.configure_open_learning((number_learning(),))
        c = ConcernCue(cue_kind='OPEN_LOOP', motivation_source='CAPABILITY_GAP', topic_key='optional-study',
            program_id='learn.numbers', possible_behaviors=('LEARN', 'WATCH'), cognitive_load=load,
            learning_value=value)
        mid = capture(r, 'optional-study', c.model_dump_json(), predicate='concern.optional-study')
        send(r, 'consider-optional-study', (mid,), task_class='numbers')
        result = r.step()
        assert result['cycle'].intention.behavior==expected
        assert jobs(r)==[], 'Runtime must not turn a considered learning program into mandatory learning'
        advance(r, 12)
        assert not r.store.all('lessons') and not r.store.all('cognitive_requests')


def test_renewed_failure_relearns_once_then_transfers_after_restart(tmp_path, record_property):
    path = tmp_path/'subject.db'
    clock = VirtualClock()
    with runtime(path, clock) as r:
        r.work.configure_open_learning((number_learning(),))
        start_learning(r, number_learning())
        original = dict(jobs(r)[0])
        old_lesson = body(r, original)['lesson_id']
        identity = r.identity_id
        assert r.work.open_learning.strategy('numbers', 'lab')[1] == 'NUMERIC_SUM'
    # A new resource/proposer instance on restart does not own the learned state.
    with runtime(path, clock) as r:
        spec = ordering_spec()
        r.work.configure_open_learning((spec,))
        assert r.identity_id == identity
        assert r.work.open_learning.strategy('numbers', 'lab')[1] == 'NUMERIC_SUM'
        obj = objective('changed.ordering', method='NUMERIC_SUM', expected=[2, 4, 9])
        port = configure(r, tmp_path/'world'/'state.fixture.json', (obj,))
        port.seed_observation(obj.operators[0].resource, [9, 2, 4])
        source = cue(r, obj)
        send(r, 'new-task', (source,), task_class='numbers'); r.step(); advance(r, 4)
        failure = r.store.db.execute("SELECT * FROM experiences WHERE task_class='numbers' AND outcome='FAILURE' ORDER BY rowid DESC LIMIT 1").fetchone()
        assert failure is not None
        before = reconsider(r, 'reopened-gap', failure['result_memory_id'])
        assert before.experience_need.state=='OPEN' and before.intention.behavior=='LEARN'
        resting = reconsider(r, 'rest-before-learning', failure['result_memory_id'], load='HIGH')
        assert resting.intention.behavior=='REST'
        # An ordinary wake alone cannot restart completed learning.
        start_learning(r, spec, 'ordinary-wake')
        assert len(jobs(r)) == 1
        # Counterexample runs the old method; failure suspends it before adoption.
        check = r.work.open_learning.monitor(old_lesson, spec.practice, authority=r.authority)
        assert not check['all_passed'] and r.work.open_learning.strategy('numbers', 'lab') is None
        assert not r.work.open_learning._new_verified_gap(original, failure, number_learning(), 'lab')
        heldout_only = number_learning().model_copy(update={'evaluation':(
            number_learning().evaluation[0].model_copy(update={'expected':99}),)})
        assert not r.work.open_learning._new_verified_gap(original, failure, heldout_only, 'lab')
        for parked in ('WAITING', 'RUNNING', 'UNKNOWN', 'CANCELLED'):
            assert not r.work.open_learning._new_verified_gap(
                {**original, 'state':parked}, failure, spec, 'lab')
        # Self-originated reflection: no user command or provider call.
        send(r, 'checked-new-failure', (source,), reflection_experience_id=failure['experience_id'], task_class='numbers')
        r.drain(32)
        assert len(jobs(r)) == 2, 'A finished old learning job must not swallow a later checked gap'
        renewed = dict(jobs(r)[-1]); learned = body(r, renewed)
        assert renewed['state'] == 'DONE'
        assert not r.work.open_learning._new_verified_gap(renewed, failure, spec, 'lab')
        assert learned['previous_work_id'] == original['job_id']
        assert learned['reconsidered_experience_id'] == failure['experience_id']
        assert learned['selected_method'] == 'SORT'
        assert learned['results']['BASELINE']['passed'] == 0
        assert learned['results']['EVALUATE']['all_passed'] and learned['results']['TRANSFER']['all_passed']
        assert r.store.one('lessons', old_lesson)['state'] == 'SUSPENDED'
        # Repeated reflection and replay do not re-run a learning experiment.
        send(r, 'repeat-gap-review', (source,), reflection_experience_id=failure['experience_id'], task_class='numbers')
        r.drain(24)
        assert len(jobs(r)) == 2
        current_lesson = learned['lesson_id']
        # Qualification is not yet evidence that a later real task reused it.
        assert project_need(r.store, 'numbers', scope='lab', privacy_classes=('PERSONAL',)).state=='OPEN'
    with runtime(path, clock) as r:
        r.work.configure_open_learning((ordering_spec(),))
        assert r.identity_id == identity
        assert r.work.open_learning.strategy('numbers', 'lab')[1] == 'SORT'
        later = objective('unseen.later', method='NUMERIC_SUM', expected=[-2, 8, 11])
        port = configure(r, tmp_path/'later-world'/'state.fixture.json', (later,))
        port.seed_observation(later.operators[0].resource, [11, -2, 8])
        send(r, 'independent-later-task', (cue(r, later),), task_class='numbers'); result = r.step()
        assert result['cycle'].judgment.selected_method == 'SORT'
        advance(r, 6)
        assert port._load()['resources'][later.operators[-1].resource]['data'] == [-2, 8, 11]
        assert r.store.one('lessons', current_lesson)['state'] == 'ACTIVE'
        assert len(jobs(r)) == 2 and not r.store.all('cognitive_requests')
        latest = json.loads(r.store.db.execute("SELECT data_json FROM events WHERE kind='living.goal_step_completed' ORDER BY seq DESC LIMIT 1").fetchone()[0])['data']
        case = LearningCase(case_id='later-realization', context='different-sensor', data=[11, -2, 8], expected=[-2, 8, 11])
        text = json.dumps({'strategy_episode': {'episode_key':'later-realization', 'lesson_id':current_lesson,
            'case':case.model_dump(mode='json')}})
        memory = MemoryService(r.store)
        eid = memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.renewal',
            source_reference='verified-later-effect', source_kind='SYSTEM_VERIFICATION'), text=text,
            privacy_class='PERSONAL', observed_time_us=r.clock.utc_now_us()))
        observation = memory.add(MemoryCandidate(entity_id='synthetic-person', scope='lab',
            memory_type=MemoryType.EPISODIC, epistemic_kind='OBSERVATION', source_evidence_id=eid,
            text=text, derived_from=(latest['memory_id'],)))
        EpisodeLearning(r.store, r.authority, scopes=('lab',), privacy_classes=('PERSONAL',)).assess(
            current_lesson, observation, authority=r.authority)
        after = reconsider(r, 'settled-after-later-use', failure['result_memory_id'])
        assert after.experience_need.state=='SETTLED' and after.intention.behavior=='WATCH'
        # Privacy withdrawal removes support on restart as well as immediately.
        MemoryService(r.store, r.authority).forget(failure['result_memory_id'], r.authority)
        assert r.work.open_learning.strategy('numbers', 'lab') is None
    with runtime(path, clock) as r:
        r.work.configure_open_learning((ordering_spec(),))
        assert r.work.open_learning.strategy('numbers', 'lab') is None
        assert len(jobs(r)) == 2 and r.identity_id == identity
    record_property('growth_evidence', json.dumps({'before': 'sum cannot produce ordered readings',
        'experience': 'independently checked new task failure', 'after': 'heldout/transfer and new task sorted correctly',
        'restart_preserved': True, 'real_model_swap': 'NOT_RUN', 'provider_calls': 0,
        'scope': 'SYNTHETIC_WORLD_NOT_LIVE_COMPANIONSHIP', 'withdrawal': 'INVALIDATES_LESSON'}))
