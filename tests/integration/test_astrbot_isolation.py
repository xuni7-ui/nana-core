import asyncio
import os
from pathlib import Path
import subprocess
import sys
import threading
import pytest
from tools.nana_astrbot_shadow.observer import ShadowObserver
from test_astrbot_sanitizer import sanitizer, event, PROBE, Sink
from test_astrbot_dedup import new_sink
from nana_core.actions import ActionKernel,OperatorAuthority
from nana_core.contracts import GrantSpec,CoreError

@pytest.mark.parametrize('failure',[RuntimeError,FileNotFoundError,PermissionError,KeyboardInterrupt])
def test_sink_failure_drops_without_exception_or_private_logging(failure):
    codes=[]
    class Broken(Sink):
        def accept(self,m): raise failure('synthetic-private-canary')
    async def run():
        o=ShadowObserver(sanitizer(),Broken(),logger=codes.append)
        assert await o.callback(event(),permit=o.issue_local_permit(PROBE)) is None
        assert o.last_result=={'status':'DROP_SHADOW_FAILURE'}
        await o.close()
    asyncio.run(run())
    assert codes==['DROP_SHADOW_FAILURE']

def test_timeout_busy_cancellation_and_late_exception_no_eventloop_leak():
    release=threading.Event();started=threading.Event();errors=[]
    class Slow(Sink):
        def accept(self,m):
            started.set();release.wait(1)
            raise RuntimeError('synthetic-private-canary')
    async def run():
        loop=asyncio.get_running_loop();loop.set_exception_handler(lambda l,c:errors.append(c))
        o=ShadowObserver(sanitizer(),Slow(),timeout=.01)
        p=o.issue_local_permit(PROBE)
        try:
            assert await o.callback(event(),permit=p) is None
            assert o.last_result=={'status':'UNKNOWN_LOCAL_STORE_COMPLETION'}
            assert await o.callback(event(),permit=p) is None and o.last_result['status']=='DROP_BUSY'
            release.set();await o.close();await asyncio.sleep(.01)
            assert not errors
        finally: release.set()
        release.clear();started.clear();o=ShadowObserver(sanitizer(),Slow(),timeout=1.)
        p=o.issue_local_permit(PROBE)
        task=asyncio.create_task(o.callback(event(),permit=p))
        while not started.is_set(): await asyncio.sleep(.001)
        task.cancel();assert await task is None and o.last_result['status']=='DROP_CANCELLED'
        release.set();await o.close();await asyncio.sleep(.01)
        assert not errors
    asyncio.run(run())

def test_real_core_worker_records_drafts_and_no_executor(tmp_path):
    s,sink=new_sink(tmp_path/'shadow')
    async def run():
        o=ShadowObserver(s,sink);p=o.issue_local_permit(PROBE)
        assert await o.callback(event(content='synthetic-private-canary'),permit=p) is None
        r=o.last_result['core'];assert r['barrier_result']=='SHADOW_BLOCKED' and not any(r['zero_execution_counts'].values())
        assert await o.callback(event(),permit=p) is None and o.last_result['core']['dedup_result']=='DUPLICATE'
        await o.close()
    asyncio.run(run())
    from nana_core.storage import Store
    with Store(tmp_path/'shadow'/'observer-shadow.db') as store:
        a=OperatorAuthority();k=ActionKernel(store,None,a)
        for f in [lambda:k.propose('reading.source.read','source://synthetic/probe',{'source_id':'source://synthetic/probe'}),
                  lambda:k.set_budgets({'write_attempts':1,'external_requests':1,'cost_micro_units':1},a),
                  lambda:k.grant(GrantSpec(capabilities=('reading.source.read',),resources=('source://synthetic/probe',),not_before_us=0,expires_at_us=2**62),a)]:
            with pytest.raises(CoreError,match='SHADOW_BLOCKED'):f()
        assert not any(store.all(t) for t in ('actions','attempts','grants','budgets','strategies'))
        assert all(b'synthetic-private-canary' not in store.artifact(x['artifact_id']) for x in store.all('events') if x['artifact_id'])

def test_actual_sigkill_after_observation_before_decision_recovers(tmp_path):
    code='''import os,signal,sys,json
from pathlib import Path
from tools.nana_astrbot_shadow.sanitize import MetadataSanitizer
from tools.nana_astrbot_shadow.core_sink import MetadataCoreSink
from nana_core.integration.host_observation import AstrBotObservationAdapter
p=Path(sys.argv[1]);p.mkdir(exist_ok=True,mode=0o700)
s=MetadataSanitizer(scope="dev-observer-v1",hash_key=b"D"*32,probe_ids=frozenset({"nana-probe-development-v1"}))
if sys.argv[2]=="crash":
 original=AstrBotObservationAdapter.ingest
 def crash(self,*args):
  result=original(self,*args);os.kill(os.getpid(),signal.SIGKILL);return result
 AstrBotObservationAdapter.ingest=crash
e={"event_id":"synthetic-event","event_source":"operator_probe","synthetic":True,"probe_id":"nana-probe-development-v1","timestamp":"2026-10-11T02:00:00+00:00"}
sink=MetadataCoreSink(p,s);r=sink.accept(s.sanitize(e).metadata);sink.close();print(json.dumps(r))'''
    env=dict(os.environ);env['PYTHONPATH']=str(Path('src').resolve())+os.pathsep+str(Path('.').resolve())
    argv=[sys.executable,'-c',code,str(tmp_path/'shadow')]
    crashed=subprocess.run(argv+['crash'],env=env,capture_output=True,text=True)
    assert crashed.returncode==-9
    import json
    restored=json.loads(subprocess.run(argv+['restore'],env=env,capture_output=True,text=True,check=True).stdout)
    again=json.loads(subprocess.run(argv+['restore'],env=env,capture_output=True,text=True,check=True).stdout)
    assert restored['dedup_result']==again['dedup_result']=='DUPLICATE'
    assert restored['identity_id']==again['identity_id'] and restored['observation_id']==again['observation_id']
    assert not any(again['zero_execution_counts'].values())
