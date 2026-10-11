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
