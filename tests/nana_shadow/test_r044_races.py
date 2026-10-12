"""Concurrent writer/UDS/readback and process-identity races; synthetic only."""
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import time
import pytest
from test_r041_bridge import fixture,ready,send
from tools.nana_astrbot_shadow.bridge_wire import project_raw,process_fingerprint
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore,ReceiptLedger
from tools.nana_astrbot_shadow.one_shot_cli import ReadOnlyStoreView
from tools.nana_astrbot_shadow.one_shot_proof import collect,verify_first_real_message_shadow
import tools.nana_astrbot_shadow.bridge_cli as cli
from tools.nana_host_shadow.safety import private_file
from nana_core.storage import Store
from nana_core.contracts import CoreError
from r044_helpers import fixture_view,readback

@pytest.mark.parametrize('count',[2,10,100,500])
@pytest.mark.parametrize('same',[True,False])
def test_concurrent_clients_at_most_one_persistent_ingress(tmp_path,count,same):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=4,trust=FixtureTrustStore())
        task,c=await ready(w);start=time.monotonic()
        frames=[project_raw({**raw,'event_id':raw['event_id'] if same else 'synthetic-'+str(i)},c) for i in range(count)]
        results=await asyncio.gather(*(send(c,m) for m in frames),return_exceptions=True)
        w.stop_event.set();await asyncio.wait_for(task,5)
        accepted=sum(type(x) is dict and x['status']=='SHADOW_BLOCKED' for x in results)
        if count<=100:assert accepted==1
        else:assert accepted<=1 # documented lifetime cap128 may fail closed under500 flood
        assert time.monotonic()-start<6
    asyncio.run(run());status,n,_=readback(root,r.receipt_id)
    assert status['uses']==n and n<=1
    assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()

@pytest.mark.parametrize('first',['consume','disarm'])
def test_disarm_vs_consume_serializes_in_original_writer(tmp_path,first):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w);loop=asyncio.get_running_loop();writer=w.observer._worker
        def disarm():return w._sink.ledger().disarm(r.receipt_id)
        def consume():return w._sink.accept_public(project_raw(raw,c))
        calls=[consume,disarm] if first=='consume' else [disarm,consume]
        results=await asyncio.gather(*(loop.run_in_executor(writer,f) for f in calls),return_exceptions=True)
        assert sum(isinstance(x,ValueError) for x in results)==1
        w.stop_event.set();await task
    asyncio.run(run());status,n,_=readback(root,r.receipt_id)
    assert n==int(first=='consume') and status['uses']==n
    assert status['state']==('CONSUMED' if first=='consume' else 'DISARMED')


def test_other_writer_is_blocked_while_readonly_views_stay_consistent(tmp_path):
    root,ipc,r,raw=fixture(tmp_path)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w)
        with pytest.raises(CoreError,match='RUNTIME_ALREADY_ACTIVE'):Store(root/'observer-shadow.db')
        observed=[]
        async def inspect():
            for _ in range(40):
                with fixture_view(root) as l:
                    status=l.status(r.receipt_id);observed.append(status['uses'])
                    report=collect(l,r.receipt_id)
                    verdict=verify_first_real_message_shadow(report,l)
                    assert verdict['host_binding']=='UNVERIFIED'
                    for e in l.store.all('events'):json.loads(e['data_json'])
                await asyncio.sleep(0)
        await asyncio.gather(inspect(),send(c,project_raw(raw,c)));await task
        assert set(observed)<= {0,1}
    asyncio.run(run())


def test_pid_reuse_fingerprint_change_never_signals_unrelated_process(tmp_path,monkeypatch):
    root,ipc,r,raw=fixture(tmp_path);monkeypatch.setattr(cli,'operator_ledger',fixture_view)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
        task,c=await ready(w);calls=[];count=0;original=cli.process_fingerprint
        def fingerprint(pid):
            nonlocal count
            count+=1
            return original(pid) if count==1 else '0'*64
        try:
            with monkeypatch.context() as m:
                m.setattr(cli,'process_fingerprint',fingerprint)
                m.setattr(os,'pidfd_open',lambda pid:os.open('/dev/null',os.O_RDONLY))
                m.setattr(signal,'pidfd_send_signal',lambda *a:calls.append(a))
                with pytest.raises(ValueError,match='PID_REUSED'):cli.stop(root,ipc)
                assert calls==[]
        finally:w.stop_event.set();await task
    asyncio.run(run())


def test_copied_directory_session_cannot_stop_or_cleanup(tmp_path,monkeypatch):
    import shutil
    root,ipc,r,raw=fixture(tmp_path);monkeypatch.setattr(cli,'operator_ledger',fixture_view)
    async def run():
        w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=.1,trust=FixtureTrustStore())
        task,c=await ready(w);await task
        clone=tmp_path/'clone';clone.mkdir(mode=0o700)
        row=json.loads((ipc/'session.json').read_text());row['socket_path']=str(clone/'bridge.sock')
        private_file(clone/'session.json',row)
        with pytest.raises(ValueError,match='DIRECTORY_FENCE_DRIFT'):cli.stop(root,clone)
        with pytest.raises(ValueError,match='DIRECTORY_FENCE_DRIFT'):cli.stale_cleanup(root,clone)
    asyncio.run(run())
