"""UTC/high-water, copied receipt, source/digest mutation and privacy boundaries."""
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import random
import pytest
from test_r04_receipt import setup,arm,RAW,NOW,OneShotCoreSink,OneShotSanitizer,FixtureTrustStore,ManualClock,parse_utc,receipt
from tools.nana_astrbot_shadow.one_shot import utc,parse_receipt,review_document,ProductionTrustStore,Provenance
from tools.nana_astrbot_shadow.onboarding import validate_review,render_seal
from test_r042_onboarding import review as review_fixture
from tools.nana_host_shadow.safety import canonical,digest
from tools.nana_astrbot_shadow import sealed_trust

@pytest.mark.parametrize('offset',[-1,0,1])
def test_expiry_microsecond_commit_boundary(tmp_path,offset):
    sink,l,r=setup(tmp_path/'shadow');arm(l,r)
    l.store.clock=ManualClock(parse_utc(r.expires_at)+offset)
    try:
        if offset<0:
            sink.accept({**RAW,'timestamp':r.expires_at.replace('12:05:00','12:04:59.999999')})
            assert l.status(r.receipt_id)['uses']==1
        else:
            with pytest.raises(ValueError,match='EXPIRED'):sink.accept(dict(RAW))
            assert l.status(r.receipt_id)['state']=='EXPIRED'
    finally:sink.close()


def test_clock_highwater_survives_reopen_and_backward_clock(tmp_path):
    path=tmp_path/'shadow';sink,l,r=setup(path);arm(l,r)
    l.store.clock.advance(299_999_999)
    # Persist advanced high-water without consuming; then simulate restart clock rollback.
    l._now();sink.close()
    sink=OneShotCoreSink(path,OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id),r.receipt_id,trust=FixtureTrustStore())
    l=sink.ledger();l.store.clock=ManualClock(parse_utc(NOW.isoformat())-1_000_000)
    try:
        assert l._now()>=utc(r.expires_at)-timedelta(microseconds=1)
        l.store.clock=ManualClock(parse_utc(r.expires_at))
        with pytest.raises(ValueError):sink.accept(dict(RAW))
        l.store.clock=ManualClock(parse_utc(NOW.isoformat()))
        with pytest.raises(ValueError):l.arm(r.receipt_id)
        with pytest.raises(ValueError):sink.accept(dict(RAW))
        assert l.status(r.receipt_id)['uses']==0
    finally:sink.close()

@pytest.mark.parametrize('stamp',['2026-10-11T12:00:00Z','2026-10-11T12:00:00','2026-10-11T12:00:00+01:00',
    '10000-01-01T00:00:00+00:00','2026-10-11T12:00:00.000000+00:00','2026-10-11T12:00:00+00:00\n',None])
def test_noncanonical_or_unsupported_times_never_validate(stamp):
    with pytest.raises((ValueError,TypeError)):utc(stamp)

@pytest.mark.parametrize('field',['receipt_id','store_binding','authorization_digest','review_receipt_digest','sender_hash',
    'conversation_hash','platform_scope','event_type_scope','issued_at','expires_at','review_provenance','max_uses'])
def test_review_and_receipt_tampering_cannot_validate_or_promote(field):
    d=review_fixture();original=d['receipt'];body=json.loads(original)
    if field=='authorization_digest':d['review']['authorization_digest']='0'*64
    else:
        replacement={'receipt_id':'r04-'+'2'*32,'platform_scope':'other','event_type_scope':'Other',
            'issued_at':'2026-10-12T12:00:01+00:00','expires_at':'2026-10-12T12:08:00+00:00',
            'review_provenance':'FIXTURE','max_uses':2}.get(field,'0'*64)
        body[field]=replacement;d['receipt']=canonical(body)
    with pytest.raises(ValueError):validate_review(d,now=datetime(2026,10,12,12,tzinfo=timezone.utc))
    assert not sealed_trust.PRODUCTION_REVIEW_PINS and not sealed_trust.REAL_RUNTIME_PROOF_PINS


def test_renamed_fixture_provenance_still_cannot_authorize_runtime():
    r=receipt(provenance=Provenance.FIXTURE)
    body=json.loads(r.canonical());body['review_provenance']='ASTRBOT_REAL_MESSAGE'
    changed=parse_receipt(canonical(body))
    assert not FixtureTrustStore().validates(changed,review_document(changed))
    assert not ProductionTrustStore().validates(changed,review_document(changed))


def test_seal_literal_binds_review_receipt_store_source_without_executing_it():
    import ast
    r=receipt(provenance=Provenance.FIXTURE) # data-only renderer test, not production build
    source=render_seal(r,'VERIFY_ONLY',{},'1'*40)
    nodes=ast.parse(source).body
    values={n.targets[0].id:ast.literal_eval(n.value.args[0] if isinstance(n.value,ast.Call) else n.value)
            for n in nodes if isinstance(n,ast.Assign)}
    assert values['REVIEW_SOURCE_SHA']=='1'*40
    assert values['EXACT_STORE_BINDING']==r.store_binding and values['EXACT_RECEIPT_DIGEST']==r.receipt_digest
    assert values['PRODUCTION_REVIEW_PINS']=={r.review_receipt_digest:r.authorization_digest}
    assert not ProductionTrustStore().validates(r,review_document(r))
