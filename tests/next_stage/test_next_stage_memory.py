import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from pydantic import ValidationError
from nana_core.clock import ManualClock
from nana_core.contracts import CoreError
from nana_core.storage import Store, canonical
from tools.nana_next_stage.contracts import Claim, SyntheticCapture, Commitment
from tools.nana_next_stage.fixtures import DATASET, capture, seed_phase_a
from tools.nana_next_stage.memory import PhaseAPrototype, ZERO


def test_import_preserves_provenance_time_types_and_never_executes(seeded):
    store, proto, report, ids = seeded
    assert report['input_count'] == len(ids) == 6
    assert all(r['status'] == 'IMPORTED' for r in report['results'])
    for m in proto.memories():
        b = json.loads(m['body_json']); iris = b['iris']
        assert iris['assessment'] == 'UNASSESSED'
        assert all(store.artifact(r['artifact_id']) for r in b['source_refs'])
        assert store.event(m['created_event_id'])['identity_id'] == store.identity['identity_id']
        if iris['origin']['legacy_kind'] in {'kg_edge','user_profile','action_ledger','l2'}:
            assert iris['time']['underlying_event_time_us'] is None
    assert json.loads(store.one('memory_items', ids['old-action'])['body_json'])['epistemic_kind'] == 'ACTION_CLAIM'
    assert all(not store.all(t) for t in ZERO)


def test_duplicate_import_and_reopen_preserve_identity_and_original_times(seeded):
    store, proto, _, _ = seeded
    identity, events = store.identity, store.all('events')
    original = {e['event_id']:e['occurred_at_us'] for e in events}
    report = proto.import_capture(capture())
    assert len(proto.memories()) == 6
    assert all(r['status'] == 'DUPLICATE' for r in report['results'])
    assert store.identity == identity
    assert all(store.event(eid)['occurred_at_us'] == time for eid,time in original.items())


def test_correction_is_temporal_and_keeps_both_evidence(seeded):
    store, proto, _, ids = seeded
    old = proto.assessments(DATASET, as_of='2026-09-02T10:00:00+00:00')[0]
    new = proto.assessments(DATASET, as_of='2026-09-04T10:00:00+00:00')[0]
    assert old['current_claim_ids'] == ['synthetic:old-preference']
    assert new['current_claim_ids'] == ['synthetic:new-preference']
    assert new['contradicting_claim_ids'] == ['synthetic:old-preference']
    assert new['verified_fact'] is False
    assert all(store.one('memory_items',mid)['status'] == 'ACTIVE' for mid in ids.values())
    before = proto.context(scope=DATASET, as_of='2026-09-02T10:00:00+00:00', max_chars=16000)
    assert ids['new-preference'] not in before['manifest']['selected_memory_ids']


def test_unknown_time_conflict_is_disputed_not_arbitrary_latest(seeded):
    _, proto, _, ids = seeded
    proto.claim(Claim(claim_id='synthetic:undated', subject='synthetic:sister', predicate='reading.preference',
        value='unknown-other', scope=DATASET, epistemic_kind='USER_STATEMENT',
        supporting_memory_ids=(ids['old-preference'],)))
    result = proto.assessments(DATASET, as_of='2026-09-04T10:00:00+00:00')[0]
    assert result['status'] == 'DISPUTED' and not result['current_claim_ids']

@pytest.mark.parametrize('key,kind', [('summary','USER_STATEMENT'), ('old-action','USER_STATEMENT'), ('profile','USER_STATEMENT')])
def test_summary_inference_and_action_cannot_be_promoted(seeded,key,kind):
    _, proto, _, ids = seeded
    with pytest.raises(CoreError, match='EPISTEMIC_PROMOTION_BLOCKED'):
        proto.claim(Claim(claim_id='synthetic:bad',subject='synthetic:sister',predicate='reading.preference',
            value='long',scope=DATASET,epistemic_kind=kind,supporting_memory_ids=(ids[key],)))


def test_source_key_collision_does_not_overwrite(seeded):
    store, proto, _, ids = seeded
    d = capture().model_dump(mode='json')
    d['records'][0]['raw_json'] = d['records'][0]['raw_json'].replace('long reading', 'changed reading')
    report = proto.import_capture(SyntheticCapture.model_validate_json(canonical(d)))
    assert report['results'][0]['status'] == 'REJECTED'
    assert report['results'][0]['error'] == 'LEGACY_SOURCE_KEY_COLLISION'
    assert 'long reading' in json.loads(store.one('memory_items',ids['old-preference'])['body_json'])['content']


def test_bad_record_is_reported_without_losing_valid_records(tmp_path):
    d = capture().model_dump(mode='json'); d['records'][0]['raw_json'] = '{"role":"user"}'
    with Store(tmp_path/'partial.db') as store:
        proto=PhaseAPrototype(store)
        report=proto.import_capture(SyntheticCapture.model_validate_json(canonical(d)))
        assert report['results'][0]['status']=='REJECTED'
        assert len(proto.memories())==5 and len(report['results'])==6

@pytest.mark.parametrize('raw', ['{"a":1,"a":2}', '{"password":"synthetic-secret-canary"}', '{"a":{"token":"synthetic-secret-canary"}}'])
def test_prewrite_json_and_secret_rejection(tmp_path,raw):
    d=capture().model_dump(mode='json'); d['records'][0]['raw_json']=raw
    with Store(tmp_path/'reject.db') as store:
        proto=PhaseAPrototype(store); before=store.snapshot()
        with pytest.raises(CoreError):
            proto.import_capture(SyntheticCapture.model_validate_json(canonical(d)))
        assert store.snapshot()==before


def test_commitment_offer_persists_but_cannot_self_declare_acceptance(seeded):
    _,proto,_,ids=seeded
    frame=proto.self_frame(); assert frame['commitments'][0]['status']=='OFFERED'
    assert frame['identity_growth_applied'] is False
    with pytest.raises(CoreError,match='COMMITMENT_AUTHORITY_NOT_IMPLEMENTED'):
        proto.commitment(Commitment(commitment_id='synthetic:forged',beneficiary_id='synthetic:sister',
            outcome='Synthetic proposal',due_at='2026-09-05T10:00:00+00:00',status='FULFILLED',
            supporting_memory_ids=(ids['new-preference'],)))


def test_context_manifest_coverage_and_tampering(seeded):
    _,proto,_,_=seeded
    c=proto.context(scope=DATASET,as_of='2026-09-04T10:00:00+00:00',max_chars=16000)
    assert c['manifest']['status']=='READY'; assert proto.verify_context(c)
    assert c['manifest']['observation_coverage'][0]['completeness']=='PARTIAL'
    assert c['manifest']['semantic_quality']=='NOT_RUN_REAL_DEPENDENCY'
    c['payload']['self']['identity_id']='fictional-forgery'
    with pytest.raises(CoreError,match='STALE_OR_TAMPERED_CONTEXT'):proto.verify_context(c)


def test_context_budget_keeps_conflict_bundle_or_refuses(seeded):
    _,proto,_,_=seeded
    c=proto.context(scope=DATASET,as_of='2026-09-04T10:00:00+00:00',max_chars=512)
    assert c['manifest']['status']=='INSUFFICIENT_CONTEXT'
    assert len(c['manifest']['dropped_memory_ids'])==6
    assert not c['payload']['memories'] and not c['payload']['assessments']
    with pytest.raises(CoreError,match='CONTEXT_DESTINATION_BLOCKED'):
        proto.context(scope=DATASET,as_of='2026-09-04T10:00:00+00:00',destination='remote')


def test_withdrawal_invalidates_context_and_dependent_candidates(seeded):
    _,proto,_,ids=seeded
    old=proto.context(scope=DATASET,as_of='2026-09-04T10:00:00+00:00',max_chars=16000)
    proto.withdraw(ids['new-preference'])
    with pytest.raises(CoreError,match='STALE_OR_TAMPERED_CONTEXT'):proto.verify_context(old)
    assert not proto.self_frame()['commitments'] and not proto.self_frame()['self_change_candidates']
    assert proto.assessments(DATASET,as_of='2026-09-04T10:00:00+00:00')[0]['current_claim_ids']==['synthetic:old-preference']
    assert proto.import_capture(capture())['results'][1]['status']=='DUPLICATE'
    assert ids['new-preference'] not in proto.context(scope=DATASET,as_of='2026-09-04T10:00:00+00:00',max_chars=16000)['manifest']['selected_memory_ids']


def test_restart_backup_replay_and_stale_backup_with_checkpoint(tmp_path):
    path=tmp_path/'original.db'
    with Store(path,ManualClock()) as store:
        p=PhaseAPrototype(store); _,ids=seed_phase_a(p); identity=store.identity; frame=p.self_frame()
        store.backup(tmp_path/'stale.db')
        checkpoint=p.withdraw(ids['new-preference'])
        store.backup(tmp_path/'backup.db');store.replay(tmp_path/'replay.db')
        projected=store.snapshot()
    with Store(path,ManualClock()) as store:
        p=PhaseAPrototype(store);assert store.identity==identity
        assert p.self_frame()['relationships']==frame['relationships']
        assert not p.self_frame()['commitments']
    for name in ('backup.db','replay.db','stale.db'):
        with Store(tmp_path/name) as store:
            p=PhaseAPrototype(store);p.apply_withdrawal_checkpoint(checkpoint)
            assert store.one('core_meta','recovery_quarantine')['value_json']=='true'
            assert store.identity==identity and not p.self_frame()['commitments']
            assert store.one('memory_items',ids['new-preference'])['status']=='RETRACTED'
            # Original artifacts remain: this is suppression, not deletion.
            assert store.artifact(store.event(ids['new-preference'])['artifact_id'])
            assert all(not store.all(t) for t in ZERO)


def test_actual_sigkill_partial_import_resume(tmp_path):
    path=tmp_path/'kill.db'
    code='''
import os,signal,sys
from nana_core.storage import Store
from tools.nana_next_stage.memory import PhaseAPrototype
from tools.nana_next_stage.fixtures import capture
with Store(sys.argv[1]) as s:
 p=PhaseAPrototype(s)
 p.import_capture(capture(),fault=lambda point,key: os.kill(os.getpid(),signal.SIGKILL))
'''
    env={**os.environ,'PYTHONPATH':str(Path.cwd())+os.pathsep+str(Path.cwd()/'src')}
    child=subprocess.run([sys.executable,'-c',code,str(path)],env=env,capture_output=True,timeout=20)
    assert child.returncode==-9
    with Store(path) as store:
        identity=store.identity;proto=PhaseAPrototype(store);report=proto.import_capture(capture())
        assert len(proto.memories())==6
        assert report['results'][0]['status']=='DUPLICATE'
        assert sum(r['status']=='IMPORTED' for r in report['results'])==5
        assert store.identity==identity and all(not store.all(t) for t in ZERO)


def test_foreign_scope_does_not_leak_self_relationship_or_commitment(seeded):
    _,proto,_,_=seeded
    context=proto.context(scope='synthetic:foreign',as_of='2026-09-04T10:00:00+00:00',max_chars=16000)
    assert not context['payload']['memories']
    assert not context['payload']['self']['relationships'] and not context['payload']['self']['commitments']


def test_nonfixture_store_cannot_be_adopted(tmp_path):
    with Store(tmp_path/'other.db') as store:
        with store.transaction('unrelated.existing'):
            pass
        with pytest.raises(CoreError,match='FRESH_FIXTURE_STORE_REQUIRED'):PhaseAPrototype(store)


def test_checkpoint_tamper_wrong_identity_and_no_authority_release(seeded):
    store,proto,_,ids=seeded
    checkpoint=proto.withdraw(ids['new-preference'])
    for field,value in [('identity_id','another-fixture'),('provenance','PRODUCTION'),('digest','0'*64)]:
        bad={**checkpoint,field:value}
        with pytest.raises(CoreError,match='WITHDRAWAL_CHECKPOINT_REJECTED'):proto.apply_withdrawal_checkpoint(bad)
    assert all(not store.all(t) for t in ZERO)
