"""Bounded standalone synthetic resource soak; never a production launcher."""
import asyncio
import gc
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import threading
import time
sys.path.insert(0,str(Path(__file__).parent))
from r044_helpers import fixture,readback
from tools.nana_astrbot_shadow.bridge_worker import ShortLivedWorker
from tools.nana_astrbot_shadow.one_shot import FixtureTrustStore,ReceiptLedger
from tools.nana_astrbot_shadow.bridge_wire import load_config,envelope,project_raw,frame,read_frame
from tools.nana_astrbot_shadow import sealed_trust
from nana_core.storage import Store


def snapshot():
    pages=int(Path('/proc/self/statm').read_text().split()[1])
    child_path=Path('/proc/self/task/'+str(os.getpid())+'/children')
    children=len(child_path.read_text().split()) if child_path.exists() else None
    return {'fds':len(list(Path('/proc/self/fd').iterdir())), 'threads':threading.active_count(),
        'children':children,'child_observation':'PROC_CHILDREN' if children is not None else 'UNAVAILABLE',
        'rss_bytes':pages*os.sysconf('SC_PAGE_SIZE')}

async def cycle(path,frames):
    root,ipc,r,raw=fixture(path)
    w=ShortLivedWorker(root,ipc,r.receipt_id,client_pid=os.getpid(),seconds=2,trust=FixtureTrustStore())
    task=asyncio.create_task(w.serve())
    for _ in range(500):
        if (ipc/'client.json').exists():break
        if task.done():await task
        await asyncio.sleep(.001)
    c=load_config(ipc/'client.json');obj=envelope(project_raw(raw,c),c);obj['mac']='0'*64
    data=frame(obj)
    for _ in range(frames):
        reader,writer=await asyncio.open_unix_connection(c['socket_path'])
        try:
            writer.write(data);await writer.drain()
            assert await asyncio.wait_for(reader.read(1),.5)==b''
        finally:
            writer.close()
            try:await writer.wait_closed()
            except ConnectionError:pass
    w.stop_event.set();await asyncio.wait_for(task,3)
    status,n,identity=readback(root,r.receipt_id)
    assert status['uses']==n==0
    with Store(root/'observer-shadow.db') as store:
        l=ReceiptLedger(store,FixtureTrustStore());assert l.disarm(r.receipt_id)['state']=='DISARMED'
    # Active resources vanish; original Store lock pathname is inert, not a lease.
    assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()
    assert w._ipc_fence.fd is None and not w.observer.active
    assert not sealed_trust.PRODUCTION_REVIEW_PINS and not sealed_trust.REAL_RUNTIME_PROOF_PINS
    # Do not retain/print wire/hash keys or nonce. Check sanitized result bytes.
    result=(ipc/'result.json').read_bytes()
    for k in ('wire_key','hash_key','session_nonce'):
        assert c[k].encode() not in result
    return {'worker_cycles':1,'rejected_frames':frames,'receipt_create_disarm':1,'active_sockets':0,'held_store_locks':0}


def run(cycles=1000,frames_per_cycle=10):
    if type(cycles) is not int or not 1<=cycles<=1000 or type(frames_per_cycle) is not int or not 0<=frames_per_cycle<=100:
        raise ValueError('BOUNDED_DEVELOPMENT_SOAK')
    start=time.monotonic();before=snapshot();samples=[]
    import shutil
    with tempfile.TemporaryDirectory(prefix='nana-r44-soak-') as td:
        base=Path(td);base.chmod(0o700)
        async def exercise():
            for i in range(cycles):
                path=base/('c'+str(i));await cycle(path,frames_per_cycle)
                shutil.rmtree(path) # own current synthetic fixture only
                if i%100==99 or i==cycles-1:
                    await asyncio.sleep(.01);gc.collect();sample={'cycle':i+1,**snapshot()};samples.append(sample)
                    print(json.dumps({'progress':i+1,'fds':sample['fds'],'threads':sample['threads'],'rss_bytes':sample['rss_bytes']}),flush=True)
            assert not list(base.iterdir())
        asyncio.run(exercise())
    gc.collect();after=snapshot()
    assert after['fds']<=before['fds']+1 and after['threads']<=before['threads']+1
    assert after['children']==before['children']
    if after['children'] is not None:assert after['children']==0
    assert after['rss_bytes']<=before['rss_bytes']+64*1024*1024
    return {'status':'PASS','origin':'OFFLINE_FIXTURE_API_WORKER_CYCLES',
        'worker_start_stop_cycles':cycles,'rejected_IPC_frames':cycles*frames_per_cycle,
        'receipt_create_disarm_cycles':cycles,'actual_subprocess_worker_cycles':0,
        'seconds':round(time.monotonic()-start,3),'before':before,'after':after,'samples':samples,
        'residual_sockets':0,'residual_capabilities':0,'held_store_locks':0,'residual_temp_dirs':0,
        'production_pins':0,'real_runtime_pins':0,'host_binding':'UNVERIFIED','E12':'NOT_RUN'}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cycles',type=int,default=1000)
    p.add_argument('--frames',type=int,default=10);p.add_argument('--output',required=True);a=p.parse_args()
    result=run(a.cycles,a.frames);Path(a.output).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cycles':result['worker_start_stop_cycles'],'frames':result['rejected_IPC_frames'],'seconds':result['seconds']}))
