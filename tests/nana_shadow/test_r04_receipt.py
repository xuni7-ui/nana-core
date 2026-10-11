import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from tools.nana_astrbot_shadow.one_shot import *

NOW=datetime(2026,10,11,12,tzinfo=timezone.utc)

def receipt(binding='a'*64, provenance=Provenance.FIXTURE, **changes):
    body=dict(receipt_id='r04-'+uuid4().hex,issued_at=NOW.isoformat(),expires_at=(NOW+timedelta(minutes=5)).isoformat(),
        platform_scope='aiocqhttp',conversation_hash='b'*64,sender_hash='c'*64,event_type_scope='FakeEvent',
        review_provenance=provenance,review_receipt_digest='0'*64,store_binding=binding,hash_scope='r04-test')
    body.update(changes)
    r=OneShotReceipt(**body)
    return r.model_copy(update={'review_receipt_digest':digest(review_document(r))})

def test_contract_roundtrip_and_frozen():
    r=receipt();assert parse_receipt(r.canonical())==r
    assert digest(json.loads(r.canonical()))==r.receipt_digest
    with pytest.raises(Exception):r.max_uses=2
    with pytest.raises(ValueError):parse_receipt(r.canonical()+' ')

@pytest.mark.parametrize('changes',[{'max_uses':2},{'max_uses':True},{'sender_hash':'*'},{'conversation_hash':'*'},
    {'issued_at':'2026-10-11T12:00:00'}, {'expires_at':(NOW+timedelta(hours=1)).isoformat()},
    {'purpose':'secret'}, {'platform_scope':'平台'}, {'sender_hash':None}, {'event_type_scope':'x'*10000},
    {'unknown':'PRIVATE-BODY-CANARY'}, {'schema_version':True}])
def test_invalid_contract(changes):
    with pytest.raises(ValueError):receipt(**changes)

def test_fixture_cannot_claim_real_or_lifecycle():
    for origin in (Provenance.ASTRBOT_REAL_MESSAGE,Provenance.ASTRBOT_LIFECYCLE,Provenance.LOCAL_SYNTHETIC):
        r=receipt(provenance=origin)
        assert not FixtureTrustStore().validates(r,review_document(r))
        assert not ProductionTrustStore().validates(r,review_document(r))
    assert len(PRODUCTION_REVIEW_PINS)==0

from tools.nana_astrbot_shadow.one_shot_ingress import OneShotCoreSink,OneShotSanitizer,OneShotObserver,OneShotPermit
from nana_core.clock import ManualClock,parse_utc
from concurrent.futures import ThreadPoolExecutor

RAW=dict(platform='aiocqhttp',type='FakeEvent',event_id='synthetic-r04-event',timestamp=NOW.isoformat(),
    conversation_id='synthetic-conversation',sender_id='synthetic-sender',event_source=REAL_SOURCE,synthetic=False,probe_id='')

def setup(path,*,rid=None,trust=None):
    path.mkdir(exist_ok=True,mode=0o700)
    rid=rid or 'r04-'+uuid4().hex
    sanitizer=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=rid)
    sink=OneShotCoreSink(path,sanitizer,rid,trust=trust or FixtureTrustStore())
    ledger=sink.ledger();ledger.store.clock=ManualClock(parse_utc(NOW.isoformat()))
    r=receipt(binding=ledger.binding,receipt_id=rid,
              sender_hash=sanitizer.scoped_hash('sender_id',RAW['sender_id']),
              conversation_hash=sanitizer.scoped_hash('conversation_id',RAW['conversation_id']))
    ledger.create(r);return sink,ledger,r

def arm(ledger,r):ledger.review(r.receipt_id,review_document(r));ledger.arm(r.receipt_id)

def test_create_arm_restart_and_terminal_state(tmp_path):
    sink,ledger,r=setup(tmp_path/'shadow');arm(ledger,r);identity=ledger.store.identity
    sink.close()
    san=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id)
    sink=OneShotCoreSink(tmp_path/'shadow',san,r.receipt_id,trust=FixtureTrustStore())
    ledger=sink.ledger();ledger.store.clock=ManualClock(parse_utc(NOW.isoformat()))
    assert ledger.store.identity==identity and ledger.status(r.receipt_id)['state']=='ARMED'
    out=sink.accept(dict(RAW));assert out['core']['barrier_result']=='SHADOW_BLOCKED'
    assert ledger.status(r.receipt_id)['uses']==1
    with pytest.raises(ValueError,match='ALREADY_CONSUMED'):sink.accept(dict(RAW))
    with pytest.raises(ValueError):ledger.arm(r.receipt_id)
    with pytest.raises(ValueError):ledger.disarm(r.receipt_id)
    assert len([e for e in ledger.store.all('events') if e['kind']=='observation.received'])==1
    sink.close()

@pytest.mark.parametrize('key,value',[('platform','different'),('sender_id','different'),('conversation_id','different'),
    ('type','OtherEvent'),('synthetic',True),('event_source','operator_probe'),('event_id',None),('timestamp',None),
    ('timestamp','2026-10-11T11:00:00+00:00'),('platform','x'*10000),('platform','秘密')])
def test_wrong_scope_never_consumes_or_writes_evidence(tmp_path,key,value):
    sink,ledger,r=setup(tmp_path/'shadow');arm(ledger,r)
    raw=dict(RAW);raw[key]=value
    with pytest.raises(ValueError):sink.accept(raw)
    assert ledger.status(r.receipt_id)['uses']==0
    assert not [e for e in ledger.store.all('events') if e['kind']=='observation.received']
    sink.close()

def test_expired_and_clock_rollback_does_not_revive(tmp_path):
    sink,ledger,r=setup(tmp_path/'shadow');arm(ledger,r)
    ledger.store.clock.advance(300_000_000)
    with pytest.raises(ValueError,match='EXPIRED'):sink.accept(dict(RAW))
    assert ledger.status(r.receipt_id)['state']=='EXPIRED'
    ledger.store.clock.advance(-300_000_000)
    with pytest.raises(ValueError):sink.accept(dict(RAW))
    with pytest.raises(ValueError):ledger.arm(r.receipt_id)
    sink.close()

@pytest.mark.parametrize('seconds,allowed',[(2,True),(2.000001,False)])
def test_future_issue_skew_fixed_boundary(tmp_path,seconds,allowed):
    sink,ledger,r=setup(tmp_path/'shadow')
    r=receipt(binding=ledger.binding,issued_at=(NOW+timedelta(seconds=seconds)).isoformat())
    ledger.create(r);ledger.review(r.receipt_id,review_document(r))
    if allowed:assert ledger.arm(r.receipt_id)['state']=='ARMED'
    else:
        with pytest.raises(ValueError,match='FUTURE'):ledger.arm(r.receipt_id)
    sink.close()

def test_duplicate_id_copied_receipt_reused_review_and_domain(tmp_path):
    sink,l,r=setup(tmp_path/'a')
    with pytest.raises(ValueError,match='DUPLICATE'):l.create(r)
    other,ol,orr=setup(tmp_path/'b')
    with pytest.raises(ValueError,match='STORE_MISMATCH'):ol.create(r)
    with pytest.raises(ValueError,match='UNTRUSTED'):ol.review(orr.receipt_id,review_document(r))
    with pytest.raises(ValueError,match='UNTRUSTED'):l.review(r.receipt_id,{**review_document(r),'extra':'private'})
    arm(l,r);sink.close();other.close()
    other=OneShotCoreSink(tmp_path/'a',OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id),r.receipt_id)
    with pytest.raises(ValueError,match='TRUST_DOMAIN_BLOCKED'):other.ledger().arm(r.receipt_id)
    other.close()

@pytest.mark.parametrize('count',[2,10,100])
def test_concurrent_events_have_one_atomic_accept(tmp_path,count):
    sink,ledger,r=setup(tmp_path/'shadow');arm(ledger,r);sink.close()
    # Exactly the same single-writer FIFO topology as host Observer, many competing
    # submitted events. No list dedup: SQLite receipt and event reservation decide.
    holder={}
    def attempt(i):
        if not holder:
            s=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id)
            holder['sink']=OneShotCoreSink(tmp_path/'shadow',s,r.receipt_id,trust=FixtureTrustStore())
            holder['sink'].ledger().store.clock=ManualClock(parse_utc(NOW.isoformat()))
        raw=dict(RAW);raw['event_id']='synthetic-event-'+str(i)
        try:holder['sink'].accept(raw);return 'ACCEPT'
        except ValueError as e:return str(e)
    with ThreadPoolExecutor(max_workers=1) as writer:
        futures=[writer.submit(attempt,i) for i in range(count)]
        results=[f.result() for f in futures]
        uses=writer.submit(lambda:holder['sink'].ledger().status(r.receipt_id)['uses']).result()
        writer.submit(holder['sink'].close).result()
    assert results.count('ACCEPT')==1 and results.count('ALREADY_CONSUMED')==count-1 and uses==1

def test_permit_and_sanitizer_are_independent_gates(tmp_path):
    sink,l,r=setup(tmp_path/'shadow');arm(l,r);m=sink.sanitizer.project(dict(RAW))
    # Neither forged opaque object nor synthetic ProbePermit passes real sanitizer.
    fake=OneShotPermit(r.receipt_id,r.receipt_digest,digest(m.public()),l.binding,'FIXTURE')
    assert sink.sanitizer.sanitize_real(m,permit=fake).status=='DROP_ONE_SHOT_PERMIT'
    with pytest.raises(ValueError,match='UNCONSUMED'):sink.sanitizer.issue_consumed_permit(l,m)
    assert sink.sanitizer.sanitize(dict(RAW)).status=='DROP_PROBE_SCOPE'
    l.consume(r.receipt_id,m)
    p=sink.sanitizer.issue_consumed_permit(l,m)
    assert sink.sanitizer.sanitize_real(m,permit=p).status=='ACCEPT'
    assert sink.sanitizer.sanitize_real(m,permit=p).status=='DROP_ONE_SHOT_PERMIT'
    sink.close()

from tools.nana_astrbot_shadow.one_shot_proof import collect,verify_first_real_message_shadow,mark_verified,ZERO_KEYS,REAL_RUNTIME_PROOF_PINS

def test_independent_persistent_proof_and_fixture_forgery(tmp_path):
    sink,l,r=setup(tmp_path/'shadow');arm(l,r);sink.accept(dict(RAW))
    report=collect(l,r.receipt_id,observer_callback_received=True,sanitizer_accepted=True,
                   noncore_zero={k:0 for k in ZERO_KEYS})
    assert verify_first_real_message_shadow(report,l)['status']=='SIMULATED_REAL_SHADOW_PROOF_PASS'
    assert mark_verified(report,l)['host_binding']=='UNVERIFIED'
    assert l.status(r.receipt_id)['state']=='VERIFIED'
    for patch in ({'source_provenance':'ASTRBOT_REAL_MESSAGE'},{'trust_domain':'PRODUCTION'},
                  {'observer_callback_received':False},{'sanitizer_accepted':False},
                  {'receipt_digest':'0'*64},{'body':'PRIVATE-CANARY'}, {'noncore_zero':{k:1 for k in ZERO_KEYS}}):
        altered={**report,**patch}
        assert verify_first_real_message_shadow(altered,l)['status']=='INCOMPLETE'
    assert len(REAL_RUNTIME_PROOF_PINS)==0
    report['core']={**report['core'],'observation_id':'00000000-0000-0000-0000-000000000000'}
    assert verify_first_real_message_shadow(report,l)['status']=='INCOMPLETE'
    sink.close()

def test_tampered_artifact_cannot_be_declared_verified(tmp_path):
    sink,l,r=setup(tmp_path/'shadow');arm(l,r);core=sink.accept(dict(RAW))['core']
    report=collect(l,r.receipt_id,observer_callback_received=True,sanitizer_accepted=True,noncore_zero={k:0 for k in ZERO_KEYS})
    l.store.db.execute('UPDATE artifacts SET payload=? WHERE artifact_id=?',(b'corrupt',core['core_evidence_id']))
    assert verify_first_real_message_shadow(report,l)['status']=='INCOMPLETE'
    with pytest.raises(ValueError):mark_verified(report,l)
    sink.close()
