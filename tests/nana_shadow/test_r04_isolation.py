import asyncio
import json
import time
from pathlib import Path
import pytest
from test_r04_receipt import (setup,arm,RAW,NOW,FixtureTrustStore,OneShotCoreSink,OneShotSanitizer,ManualClock,parse_utc,OneShotObserver,receipt,Provenance,review_document)
from test_message_hook_adapter import FakeEvent,HostileRepr,CANARY
from message_hook_adapter import OneShotMessageHookAdapter


def make(path,**options):
    sink,l,r=setup(path);arm(l,r);sink.close()
    s=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id)
    sink=OneShotCoreSink(path,s,r.receipt_id,trust=FixtureTrustStore())
    # Worker owns Store. Injectable clock only for dev test (no host override).
    original=sink.ledger
    def ledger():
        v=original();v.store.clock=ManualClock(parse_utc(NOW.isoformat()));return v
    sink.ledger=ledger
    o=OneShotObserver(s,sink,timeout=2,**options)
    a=OneShotMessageHookAdapter(observer=o)
    return a,sink,r


def event():return FakeEvent(platform=RAW['platform'],sender=RAW['sender_id'],umo=RAW['conversation_id'],message_id=RAW['event_id'],timestamp=NOW.timestamp())


def test_full_adapter_no_body_no_mutation_network_model_and_no_reply(tmp_path,monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:(_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN')))
    monkeypatch.setattr(socket.socket,'connect_ex',lambda *a,**k:(_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN')))
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:(_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN')))
    a,s,r=make(tmp_path/'shadow');e=event();before=dict(vars(e));obj=dict(vars(e.message_obj))
    async def run():
        assert await a.on_decorating_result(e) is None
        assert a.observer.last_result['status']=='RECORDED'
        result=a.observer.last_result['receipt']
        assert result['trust_domain']=='FIXTURE' and result['core']['barrier_result']=='SHADOW_BLOCKED'
        assert await a.on_decorating_result(e) is None
        assert a.observer.last_result['status']=='DROP_ONE_SHOT_FAILURE'
        await a.close()
    asyncio.run(run())
    assert dict(vars(e))==before and dict(vars(e.message_obj))==obj
    assert CANARY.encode() not in (tmp_path/'shadow'/'observer-shadow.db').read_bytes()

@pytest.mark.parametrize('part',['sanitizer','core','ledger','logger','store','malformed'])
def test_failure_isolation_fixed_codes_and_no_exception_escape(tmp_path,part,capsys):
    a,s,r=make(tmp_path/'shadow',logger=lambda c:(_ for _ in ()).throw(RuntimeError(CANARY)))
    if part=='sanitizer':a.observer.sanitizer.project=lambda raw:(_ for _ in ()).throw(KeyboardInterrupt(CANARY))
    if part=='core':s.accept=lambda raw:(_ for _ in ()).throw(RuntimeError(CANARY))
    if part=='ledger':s.ledger=lambda:(_ for _ in ()).throw(RuntimeError(CANARY))
    if part=='store':s.directory=tmp_path/'absent'
    e=HostileRepr() if part=='malformed' else event()
    async def run():
        assert await a.on_decorating_result(e) is None
        await a.close()
    asyncio.run(run());captured=capsys.readouterr();assert CANARY not in captured.out+captured.err

@pytest.mark.parametrize('cancel',[False,True])
def test_timeout_cancellation_late_exception_never_reply_or_unhandled(tmp_path,cancel):
    a,s,r=make(tmp_path/'shadow');a.observer.timeout=.01
    def late(raw):time.sleep(.06);raise RuntimeError(CANARY)
    s.accept=late
    async def run():
        seen=[];asyncio.get_running_loop().set_exception_handler(lambda l,c:seen.append(c))
        task=asyncio.create_task(a.on_decorating_result(event()))
        await asyncio.sleep(.005)
        if cancel:task.cancel()
        assert await task is None
        assert a.observer.last_result['status'] in ('DROP_CANCELLED','UNKNOWN_LOCAL_STORE_COMPLETION')
        await asyncio.sleep(.08);await a.close();assert seen==[]
    asyncio.run(run())


def test_unknown_nested_hostile_values_dropped_before_worker(tmp_path):
    a,s,r=make(tmp_path/'shadow')
    raw=dict(RAW);raw.update(body=HostileRepr(),attachments={'private':HostileRepr()},history=[HostileRepr()])
    actual=s.accept
    def check(raw):
        assert set(raw)==set(RAW);return actual(raw)
    s.accept=check
    async def run():
        assert await a.observer.callback_real(raw) is None
        assert a.observer.last_result['status']=='RECORDED'
        await a.close()
    asyncio.run(run())


def test_readonly_cli_and_empty_real_trust(tmp_path,capsys):
    from tools.nana_astrbot_shadow.one_shot_cli import main,initialize,operator_ledger
    from nana_core.storage import Store
    path=tmp_path/'shadow';path.mkdir(mode=0o700)
    initial=initialize(path);assert not initial['real_arm_ready']
    with operator_ledger(path,write=True) as l:
        r=receipt(binding=l.binding,provenance=Provenance.ASTRBOT_REAL_MESSAGE)
        l.create(r)
    before=(path/'observer-shadow.db').read_bytes()
    for command in ('inspect','status','verify'):
        assert main(['receipt',command,'--directory',str(path),'--receipt-id',r.receipt_id])==0
    assert (path/'observer-shadow.db').read_bytes()==before
    assert main(['receipt','arm','--directory',str(path),'--receipt-id',r.receipt_id])==2
    with operator_ledger(path,write=True) as l:
        with pytest.raises(ValueError,match='UNTRUSTED'):l.review(r.receipt_id,review_document(r))
    for argv in (['receipt','arm','--directory',str(path),'--force'],['receipt','arm','--directory',str(path),'--trust-all']):
        with pytest.raises(SystemExit):main(argv)
    assert CANARY not in capsys.readouterr().out
