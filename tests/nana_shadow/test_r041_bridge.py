import asyncio
from datetime import datetime,timezone,timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import time
from uuid import uuid4
import pytest
from tools.nana_astrbot_shadow.bridge_wire import *
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot_cli import initialize
from tools.nana_astrbot_shadow.one_shot import ReceiptLedger,OneShotReceipt,Provenance,FixtureTrustStore,ProductionTrustStore,review_document,PRODUCTION_REVIEW_PINS
from tools.nana_host_shadow.safety import private_file,digest
from nana_core.storage import Store


def fixture(tmp_path):
    root=tmp_path/'data';root.mkdir(mode=0o700);info=initialize(root)
    ipc=tmp_path/'ipc';ipc.mkdir(mode=0o700)
    with Store(root/'observer-shadow.db') as store:
        l=ReceiptLedger(store,FixtureTrustStore())
        key=json.loads(store.one('core_meta','r04.hash_key')['value_json']);scope='r04-host'
        now=datetime.now(timezone.utc)
        raw={'platform':'development','type':'FakeEvent','event_id':'synthetic-event','timestamp':now.isoformat(),
            'sender_id':'synthetic-sender','conversation_id':'synthetic-conversation'}
        r=OneShotReceipt(receipt_id='r04-'+uuid4().hex,issued_at=now.isoformat(),expires_at=(now+timedelta(seconds=30)).isoformat(),
            platform_scope=raw['platform'],event_type_scope=raw['type'],sender_hash=scoped_hash(scope,bytes.fromhex(key),'sender_id',raw['sender_id']),
            conversation_hash=scoped_hash(scope,bytes.fromhex(key),'conversation_id',raw['conversation_id']),
            review_provenance=Provenance.FIXTURE,review_receipt_digest='0'*64,store_binding=l.binding,hash_scope=scope)
        review=review_document(r);r=r.model_copy(update={'review_receipt_digest':digest(review)})
        l.create(r);l.review(r.receipt_id,review);l.arm(r.receipt_id)
    return root,ipc,r,raw

async def ready(worker):
    task=asyncio.create_task(worker.serve())
    end=time.monotonic()+3
    while not (worker.ipc/'client.json').exists() and not task.done() and time.monotonic()<end:await asyncio.sleep(.01)
    if task.done():await task
    assert (worker.ipc/'client.json').exists()
    return task,load_config(worker.ipc/'client.json')

async def send(c,m=None,*,encoded=None):
    reader,writer=await asyncio.open_unix_connection(c['socket_path'])
    try:
        writer.write(encoded if encoded is not None else frame(envelope(m,c)));await writer.drain()
        return await read_frame(reader,.8)
    finally:
        writer.close();await writer.wait_closed()

@pytest.mark.parametrize('n',[2,10,100])
def test_concurrent_frames_one_receipt_and_zero_execution(tmp_path,n):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=3,trust=FixtureTrustStore())
        task,c=await ready(w);m=project_raw(raw,c)
        results=await asyncio.gather(*(send(c,m) for _ in range(n)),return_exceptions=True)
        await task
        accepted=[x for x in results if type(x) is dict and x['status']=='SHADOW_BLOCKED']
        assert len(accepted)==1
        report=json.loads((ipc/'result.json').read_text())
        assert report['receipt']['uses']==1 and report['status']=='SIMULATED_REAL_SHADOW_PROOF_PASS'
        assert report['host_binding']=='UNVERIFIED' and report['receipt']['trust_domain']=='FIXTURE'
        assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()
    asyncio.run(run())
    with Store(root/'observer-shadow.db') as store:
        assert len([e for e in store.all('events') if e['kind']=='observation.received'])==1
        assert not any(store.all(t) for t in ('actions','attempts','grants','budgets','strategies'))

@pytest.mark.parametrize('case',['malformed','oversize','partial','extra','body','session','nonce','store','receipt','mac','unicode','null'])
def test_adversarial_frame_drops_without_receipt_consumption(tmp_path,case):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w);m=project_raw(raw,c);obj=envelope(m,c)
        if case=='malformed':encoded=b'\0\0\0\x03xxx'
        elif case=='oversize':encoded=struct.pack('!I',MAX_FRAME+1)
        elif case=='partial':encoded=struct.pack('!I',100)+b'{}'
        else:
            if case=='extra':obj['command']='shell'
            if case=='body':obj['metadata']['body']='PRIVATE-CANARY'
            if case in ('session','nonce','store','receipt','mac'):
                key={'session':'session_id','nonce':'session_nonce','store':'store_binding','receipt':'receipt_id','mac':'mac'}[case];obj[key]='0'*64
            if case=='unicode':obj['metadata']['platform']='私人正文'
            if case=='null':obj['metadata']['timestamp']=None
            encoded=frame(obj)
        try:await send(c,encoded=encoded)
        except (asyncio.IncompleteReadError,ConnectionError):pass
        w.stop_event.set();await task
        out=json.loads((ipc/'result.json').read_text());assert out['receipt']['uses']==0
    asyncio.run(run())
    with Store(root/'observer-shadow.db') as store:assert not [e for e in store.all('events') if e['kind']=='observation.received']


def test_wire_exact_canonical_and_shared_plugin_protocol():
    assert Path('tools/nana_astrbot_shadow/bridge_wire.py').read_bytes()==Path('src/plugins/astrbot_plugin_nana_shadow_observer/bridge_wire.py').read_bytes()
    for data in (b'{} ',b'{"a":1,"a":1}',b'[]',b'NaN'):
        try:obj=decode(data)
        except (ValueError,TypeError):continue
        assert type(obj) is not dict or set(obj)!=ENVELOPE_KEYS
    assert len(PRODUCTION_REVIEW_PINS)==0


def test_production_worker_never_accepts_fixture_receipt(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    with pytest.raises(ValueError):asyncio.run(ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid()).serve())
    assert not list(ipc.iterdir())
