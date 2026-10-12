"""Executable state-machine/sequence invariants, original R04 ledger only."""
import ast
import json
from pathlib import Path
import random
from datetime import datetime,timezone
import pytest
from test_r04_receipt import setup,arm,RAW,NOW,OneShotCoreSink,OneShotSanitizer,FixtureTrustStore,ManualClock,parse_utc
from tools.nana_astrbot_shadow.one_shot import ReceiptState,ProductionTrustStore,review_document
from tools.nana_astrbot_shadow.one_shot_proof import collect,mark_verified,ZERO_KEYS
from tools.nana_astrbot_shadow import sealed_trust
from tools.nana_host_shadow.safety import canonical

STATES=[s.value for s in ReceiptState]
OPS=('review','arm','consume','disarm')
LEGAL={'review':{'CREATED'},'arm':{'REVIEWED'},'consume':{'ARMED'},'disarm':{'CREATED','REVIEWED','ARMED'}}

def state_fixture(path,state):
    sink,l,r=setup(path)
    if state in ('REVIEWED','ARMED','CONSUMED','VERIFIED'):
        l.review(r.receipt_id,review_document(r))
    if state in ('ARMED','CONSUMED','VERIFIED'):l.arm(r.receipt_id)
    if state in ('CONSUMED','VERIFIED'):sink.accept(dict(RAW))
    if state=='VERIFIED':mark_verified(collect(l,r.receipt_id,observer_callback_received=True,
        sanitizer_accepted=True,noncore_zero={k:0 for k in ZERO_KEYS}),l)
    if state=='DISARMED':l.disarm(r.receipt_id)
    if state in ('EXPIRED','REJECTED','CORRUPT','UNKNOWN'):
        _,v=l.record(r.receipt_id);v.update(state=state,uses=1 if state=='UNKNOWN' else 0)
        with l.store.transaction('r04.fixture_state_constructed') as tx:l._write(tx,r,v)
    return sink,l,r

@pytest.mark.parametrize('state',STATES)
@pytest.mark.parametrize('op',OPS)
def test_complete_transition_matrix(tmp_path,state,op):
    sink,l,r=state_fixture(tmp_path/'shadow',state)
    call={'review':lambda:l.review(r.receipt_id,review_document(r)), 'arm':lambda:l.arm(r.receipt_id),
          'consume':lambda:sink.accept(dict(RAW)), 'disarm':lambda:l.disarm(r.receipt_id)}[op]
    try:
        if state in LEGAL[op]:call()
        else:
            old=l.status(r.receipt_id)
            with pytest.raises(ValueError):call()
            assert l.status(r.receipt_id)==old
        assert l.status(r.receipt_id)['uses']<=1
        assert all(not l.store.all(t) for t in ('actions','attempts','grants','budgets','strategies'))
    finally:sink.close()

@pytest.mark.parametrize('seed',range(24))
def test_deterministic_long_sequences_no_resurrection(tmp_path,seed):
    rng=random.Random(seed);path=tmp_path/'shadow';sink,l,r=setup(path)
    identity=l.store.identity;once=False;now=NOW
    try:
        for i in range(200):
            op=rng.choice(('review','arm','consume','disarm','restart','expire','verify','copy','tamper'))
            try:
                if op=='review':l.review(r.receipt_id,review_document(r))
                elif op=='arm':l.arm(r.receipt_id)
                elif op=='consume':sink.accept(dict(RAW))
                elif op=='disarm':l.disarm(r.receipt_id)
                elif op=='restart':
                    sink.close();sink=OneShotCoreSink(path,OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id),r.receipt_id,trust=FixtureTrustStore())
                    l=sink.ledger();l.store.clock=ManualClock(parse_utc(now.isoformat()))
                elif op=='expire':
                    l.store.clock.advance(301_000_000);now=datetime.fromtimestamp(l.store.clock.utc_now_us()/1_000_000,timezone.utc)
                elif op=='verify':mark_verified(collect(l,r.receipt_id,observer_callback_received=True,
                    sanitizer_accepted=True,noncore_zero={k:0 for k in ZERO_KEYS}),l)
                elif op=='copy':
                    other,ol,orr=setup(tmp_path/('copy-'+str(i)))
                    try:
                        with pytest.raises(ValueError):ol.create(r)
                    finally:other.close()
                else:
                    # Corrupt a caller's review, never repair state to manufacture success.
                    with pytest.raises(ValueError):l.review(r.receipt_id,{**review_document(r),'authorization_digest':'0'*64})
            except ValueError:pass
            status=l.status(r.receipt_id)
            assert status['uses'] in (0,1) and type(status['uses']) is int
            if once:assert status['uses']==1 and status['state'] not in ('CREATED','REVIEWED','ARMED')
            once|=status['uses']==1
            assert l.store.identity==identity
            assert len([e for e in l.store.all('events') if e['kind']=='observation.received'])<=1
        assert not ProductionTrustStore().validates(r,review_document(r))
    finally:sink.close()


def test_production_and_runtime_pin_separation_and_client_imports(monkeypatch):
    for name in ('TRUST_ALL','ALLOW_REAL','PRODUCTION_REVIEW_PINS','REAL_RUNTIME_PROOF_PINS'):
        monkeypatch.setenv(name,'ANY_FORGED_VALUE')
    assert sealed_trust.PRODUCTION_REVIEW_PINS is not sealed_trust.REAL_RUNTIME_PROOF_PINS
    assert not sealed_trust.PRODUCTION_REVIEW_PINS and not sealed_trust.REAL_RUNTIME_PROOF_PINS
    for source in ('bridge_client.py','bridge_wire.py','message_hook_adapter.py','r041_main.py'):
        path=Path('src/plugins/astrbot_plugin_nana_shadow_observer')/source
        tree=ast.parse(path.read_text())
        imports=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        imports += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
        assert not any(name.startswith(('nana_core','tools','pydantic','sqlite3','_sqlite3')) for name in imports)


def test_verify_only_blocks_production_arm_and_consume(monkeypatch):
    from tools.nana_astrbot_shadow.one_shot import ReceiptLedger
    l=object.__new__(ReceiptLedger);l.trust=ProductionTrustStore()
    monkeypatch.setattr(sealed_trust,'SEAL_MODE','VERIFY_ONLY') # no pin installed
    with pytest.raises(ValueError):l._execution_seal()
    assert not sealed_trust.PRODUCTION_REVIEW_PINS and not sealed_trust.REAL_RUNTIME_PROOF_PINS
