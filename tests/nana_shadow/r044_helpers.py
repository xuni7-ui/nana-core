"""Offline synthetic helpers; no production trust pin or host binding."""
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
from uuid import uuid4
from nana_core.storage import Store
from tools.nana_astrbot_shadow.one_shot import ReceiptLedger, FixtureTrustStore, OneShotReceipt, Provenance, review_document
from tools.nana_astrbot_shadow.one_shot_cli import initialize, ReadOnlyStoreView
from tools.nana_astrbot_shadow.bridge_wire import scoped_hash
from tools.nana_host_shadow.safety import canonical,digest

ZERO_TABLES=('actions','attempts','grants','budgets','strategies')

def fixture(directory,*,window=600,armed=True):
    directory.mkdir(mode=0o700)
    root=directory/'data';root.mkdir(mode=0o700);initialize(root)
    ipc=directory/'ipc';ipc.mkdir(mode=0o700)
    with Store(root/'observer-shadow.db') as store:
        l=ReceiptLedger(store,FixtureTrustStore())
        key=bytes.fromhex(json.loads(store.one('core_meta','r04.hash_key')['value_json']))
        now=datetime.now(timezone.utc)
        raw={'platform':'development','type':'FakeEvent','event_id':'synthetic-r044-event',
             'timestamp':now.isoformat(),'sender_id':'synthetic-r044-sender','conversation_id':'synthetic-r044-conversation'}
        r=OneShotReceipt(receipt_id='r04-'+uuid4().hex,issued_at=now.isoformat(),
            expires_at=(now+timedelta(seconds=window)).isoformat(),platform_scope=raw['platform'],
            event_type_scope=raw['type'],sender_hash=scoped_hash('r04-host',key,'sender_id',raw['sender_id']),
            conversation_hash=scoped_hash('r04-host',key,'conversation_id',raw['conversation_id']),
            review_provenance=Provenance.FIXTURE,review_receipt_digest='0'*64,store_binding=l.binding,hash_scope='r04-host')
        r=r.model_copy(update={'review_receipt_digest':digest(review_document(r))})
        l.create(r)
        if armed:l.review(r.receipt_id,review_document(r));l.arm(r.receipt_id)
    return root,ipc,r,raw

@contextmanager
def fixture_view(directory):
    s=ReadOnlyStoreView(Path(directory)/'observer-shadow.db')
    try:yield ReceiptLedger(s,FixtureTrustStore())
    finally:s.close()


def readback(root,rid):
    with Store(root/'observer-shadow.db') as s:
        l=ReceiptLedger(s,FixtureTrustStore());status=l.status(rid)
        observations=[e for e in s.all('events') if e['kind']=='observation.received']
        assert all(not s.all(t) for t in ZERO_TABLES)
        assert len(observations)<=1 and status['uses']<=1
        return status,len(observations),s.identity
