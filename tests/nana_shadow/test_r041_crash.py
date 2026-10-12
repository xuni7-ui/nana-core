"""Separate real worker process/SIGKILL; never production process operations."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from test_r041_bridge import fixture,send
from tools.nana_astrbot_shadow.bridge_wire import load_config,project_raw,process_fingerprint
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.bridge_cli import session_status
from tools.nana_astrbot_shadow.one_shot import ReceiptLedger,FixtureTrustStore
from nana_core.storage import Store

CODE='''import asyncio,sys,os,time,signal
from pathlib import Path
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore
root,ipc,rid,client,point,marker=sys.argv[1:]
def checkpoint(p):
 if p==point:
  Path(marker).write_text(p)
  while True:time.sleep(.01)
async def run():
 w=ShortLivedWorker(root,ipc,rid,client_pid=int(client),seconds=10,trust=FixtureTrustStore(),checkpoint=checkpoint)
 asyncio.get_running_loop().add_signal_handler(signal.SIGTERM,w.stop_event.set)
 await w.serve()
asyncio.run(run())
'''

def launch(root,ipc,rid,point,marker):
    env=dict(os.environ);env['PYTHONPATH']=str(Path('.').resolve())+os.pathsep+str(Path('src').resolve())
    return subprocess.Popen([sys.executable,'-c',CODE,str(root),str(ipc),rid,str(os.getpid()),point,str(marker)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def wait_file(p,path):
    end=time.monotonic()+5
    while not path.exists() and p.poll() is None and time.monotonic()<end:time.sleep(.01)
    assert path.exists()

@pytest.mark.parametrize('point,uses',[('before_consume',0),('after_consume_commit',1),('after_evidence',1)])
def test_real_worker_sigkill_no_reconnect_replay_or_permission_revive(tmp_path,point,uses):
    root,ipc,r,raw=fixture(tmp_path);marker=tmp_path/'checkpoint'
    p=launch(root,ipc,r.receipt_id,point,marker)
    wait_file(p,ipc/'client.json');c=load_config(ipc/'client.json')
    async def crash():
        task=asyncio.create_task(send(c,project_raw(raw,c)))
        end=time.monotonic()+5
        while not marker.exists() and time.monotonic()<end:await asyncio.sleep(.01)
        assert marker.exists();p.kill();assert await asyncio.to_thread(p.wait,5)==-9
        try:await task
        except (asyncio.IncompleteReadError,ConnectionError):pass
    try:asyncio.run(crash())
    finally:
        if p.poll() is None:p.kill();p.wait(5)
        p.communicate(timeout=5)
    assert session_status(ipc)['effective_state']=='UNKNOWN_WORKER_EXIT'
    with Store(root/'observer-shadow.db') as store:
        l=ReceiptLedger(store,FixtureTrustStore());assert l.status(r.receipt_id)['uses']==uses
        if uses:assert l.status(r.receipt_id)['completion']=='UNKNOWN'
        assert not any(store.all(t) for t in ('actions','attempts','grants','budgets'))
    next_ipc=tmp_path/'next';next_ipc.mkdir(mode=0o700)
    with pytest.raises(ValueError,match='SESSION_REPLAY'):
        asyncio.run(ShortLivedWorker(root,next_ipc,r.receipt_id,client_pid=os.getpid(),trust=FixtureTrustStore()).serve())


def test_foreground_deadline_and_sigterm_cleanup(tmp_path):
    root,ipc,r,raw=fixture(tmp_path);p=launch(root,ipc,r.receipt_id,'never',tmp_path/'none')
    try:
        wait_file(p,ipc/'client.json');p.terminate();assert p.wait(timeout=5)==0
        assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()
        assert session_status(ipc)['effective_state']=='CLOSED'
        assert json.loads((ipc/'result.json').read_text())['receipt']['uses']==0
    finally:
        if p.poll() is None:p.kill();p.wait(5)
        p.communicate(timeout=5)
