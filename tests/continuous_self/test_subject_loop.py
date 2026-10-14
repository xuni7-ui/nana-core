import json

import pytest

from nana_core.clock import ManualClock
from nana_core.contracts import CoreError
from nana_core.continuity.subject import SubjectInput, SubjectLoop, PreferenceSignal
from nana_core.continuity.subject.contracts import DAY_US
from nana_core.continuity.subject.growth import Growth


def event(store, key, **kw):
    now = store.clock.utc_now_us()
    fields = dict(source_key='synthetic.life.' + key, kind='INTERACTION', origin='USER',
        entity_id='synthetic-sister', scope='life', text='A synthetic shared experience',
        occurred_at_us=now, observed_at_us=now, significance='RELEVANT')
    fields.update(kw)
    return SubjectInput(**fields)


def test_loop_cas_persistent_dedup_and_authority(cognitive):
    store, memory, authority = cognitive
    loop = SubjectLoop(store, scopes=('life',))
    e = event(store, 'greeting', relationship_kind='SHARED_HISTORY')
    first = loop.run(e, expected_revision=0)
    assert first.judgment.stance == 'REMEMBER'
    assert loop.run(e).replayed and len(store.all('subject_cycles')) == 1
    with pytest.raises(CoreError, match='STALE_SUBJECT_REVISION'):
        loop.run(event(store, 'other'), expected_revision=0)
    assert loop.revision == 1
    assert not store.all('actions') and not store.all('attempts') and not store.all('grants') and not store.all('budgets')
    assert not store.db.execute('PRAGMA foreign_key_check').fetchall()
    assert store.db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
    # Complete dependency ancestry survives the actual replay implementation.
    copy = store.path.parent / 'replay' / 'self.db'
    store.replay(copy)
    from nana_core.continuity import ContinuityStore
    with ContinuityStore(copy, store.clock) as replay:
        assert replay.identity['identity_id'] == store.identity['identity_id']
        assert SubjectLoop(replay, scopes=('life',)).run(e).cycle_id == first.cycle_id


def test_preference_roots_counter_evidence_delete_and_idle(cognitive):
    store, memory, authority = cognitive
    loop = SubjectLoop(store, scopes=('life',))
    signal = PreferenceSignal(topic='exploration', direction='SUPPORT', interpretation='Enjoyed discovering a new route')
    events = [event(store, f'play-{i}', kind='PLAY', origin='ENVIRONMENT', preference_signal=signal) for i in range(2)]
    for e in events:
        loop.run(e)
    view = Growth(store).assertions('life')[0]
    assert view['state'] == 'ADOPTED' and view['independent_support_count'] == 2
    wake = event(store, 'idle', kind='WAKE', origin='SELF_WAKE', text=None, significance='LOW')
    result = loop.run(wake)
    assert result.intention.kind == 'EXPLORE' and result.intention.self_generated
    assert result.goal_candidate_id and result.barrier == 'SHADOW_BLOCKED'
    assert loop.run(event(store, 'idle-2', kind='WAKE', origin='SELF_WAKE', text=None)).intention.kind == 'NO_ACTION'
    # Support copied into a derived occurrence is not a fresh independent root.
    first = store.all('subject_events')[0]
    loop.run(event(store, 'copied', kind='PLAY', origin='ENVIRONMENT', preference_signal=signal,
        source_memory_ids=(first['memory_id'],)))
    assert Growth(store).assertions('life')[0]['independent_support_count'] == 2
    for i in range(2):
        loop.run(event(store, f'counter-{i}', kind='PLAY', origin='ENVIRONMENT',
            preference_signal=signal.model_copy(update={'direction':'COUNTER'})))
    challenged = Growth(store).assertions('life')[0]
    assert challenged['state'] == 'DISPUTED' and len(challenged['counter_evidence']) == 2
    assert not loop.pending('life')  # new evidence also inhibits old optional intent
    # Erasure reaches new subject records through existing dependency closure.
    memory.forget(first['memory_id'], authority)
    assert Growth(store).assertions('life')[0]['independent_support_count'] == 1
    assert not loop.pending('life')
    store.clock.advance(8 * DAY_US)
    loop.run(event(store, 'late', kind='WAKE', origin='SELF_WAKE', text=None))
    assert all(r['state'] in {'DROPPED','EXPIRED'} for r in store.all('subject_intentions'))


def test_admission_no_body_and_scope(cognitive):
    store, memory, authority = cognitive
    loop = SubjectLoop(store, scopes=('life',))
    marker = 'DO-NOT-PERSIST-SYNTHETIC-BODY'
    result = loop.run(event(store, 'nonretention', text=marker, retention='DO_NOT_REMEMBER'))
    assert result.admission == 'IGNORE' and result.intention.kind == 'NO_ACTION'
    assert not store.all('continuity_evidence') and not store.all('memories')
    assert marker not in json.dumps(store.snapshot(), default=str)
    with pytest.raises(CoreError, match='SUBJECT_CONTEXT_POLICY_BLOCKED'):
        loop.run(event(store, 'secret', privacy_class='SECRET'))
    with pytest.raises(CoreError, match='SUBJECT_CONTEXT_POLICY_BLOCKED'):
        loop.run(event(store, 'wrong-scope', scope='other'))


def test_real_v6_parent_rebuild_preserves_existing_records(tmp_path):
    from nana_core.storage.sqlite_store import Store
    from nana_core.continuity import ContinuityStore, IdentityService
    from nana_core.continuity.privacy import PrivacyJournal
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.contracts import EvidenceInput, Provenance, MemoryCandidate, MemoryType
    from nana_core.continuity.records import RecordService
    from nana_core.actions import OperatorAuthority
    authority, clock = OperatorAuthority(), ManualClock()
    path = tmp_path / 'old.db'
    with Store(path, clock, schema_target=6) as old:
        old.privacy = PrivacyJournal(old, new_database=True)
        old.ensure_privacy_current = old.privacy.ensure_current
        IdentityService(old, authority)
        memory = MemoryService(old)
        eid = memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.v6',
            source_reference='existing', source_kind='DIRECT_OBSERVATION'), text='Existing v6 source',
            privacy_class='PROJECT', observed_time_us=clock.utc_now_us()))
        mid = memory.add(MemoryCandidate(entity_id=old.identity['identity_id'], scope='life',
            memory_type=MemoryType.EPISODIC, epistemic_kind='OBSERVATION', source_evidence_id=eid,
            text='Existing v6 source'))
        with old.transaction('existing.project') as tx:
            rid = RecordService(old).create(tx, kind='PROJECT', scope='life', payload={'old':True}, memories=(mid,))
        identity = old.identity['identity_id']
    with ContinuityStore(path, clock) as new:
        assert new.identity['identity_id'] == identity
        assert RecordService(new).read(rid)['payload'] == {'old':True}
        assert MemoryService(new).read(mid)['text'] == 'Existing v6 source'
        assert new.db.execute('PRAGMA user_version').fetchone()[0] == 7
        assert not new.db.execute('PRAGMA foreign_key_check').fetchall()
        assert new.db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
