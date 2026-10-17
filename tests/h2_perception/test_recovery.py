import json,os,signal,subprocess,sys
import pytest
from tests.world_loop.helpers import fresh
from .helpers import *
STAGES=['BEFORE_SOURCE_OPEN','AFTER_CAPTURE_BEFORE_INGEST','AFTER_TECHNICAL_INGEST','BEFORE_SEMANTIC_DISPATCH','AFTER_SEMANTIC_RESPONSE','BEFORE_CONCERN']
@pytest.mark.parametrize('stage',STAGES)
def test_actual_sigkill_six_safe_points(tmp_path,stage):
    child=subprocess.run([sys.executable,'-m','tests.h2_perception.process_worker','crash',str(tmp_path),'--stage',stage],capture_output=True,timeout=20)
    assert child.returncode==-signal.SIGKILL,child.stderr.decode()[-1000:]
    # Virtual time must advance past the dead owner's lease, explicitly no forced takeover.
    code='''from pathlib import Path
import json,sys
from nana_core.continuity.world_loop.reference import open_runtime
from nana_core.presence.authority import VirtualClock
from tests.h2_perception.helpers import setup_existing,SemanticFixture
from nana_core.continuity.world_loop.reference import configure
clock=VirtualClock();clock.advance(3*3600_000_000)
with open_runtime(Path(sys.argv[1])/'subject/self.db',clock) as r:
 configure(r,Path(sys.argv[1]),SemanticFixture('fixture.interpret','fixture-cognition'),('synthetic://public',),grant=False,planner=False)
 c,adapter,m,a=setup_existing(r,Path(sys.argv[1]),concern_callback=lambda result,cid:[r.work.world.observe(mid) for mid in result['semantic_memory_ids']])
 for _ in range(8):clock.advance(1000000);r.step()
 first={t:len(r.store.all(t)) for t in ['memories','cognitive_requests','subject_cycles','open_concerns']}
 c.recover();c.recover()
 assert first=={t:len(r.store.all(t)) for t in first}
 assert m.calls==0 and adapter.bytes_read==0
 assert all(x['state']!='CALLING' for x in r.store.all('cognitive_requests'))
 print(json.dumps(first))
'''
    resumed=subprocess.run([sys.executable,'-c',code,str(tmp_path)],capture_output=True,timeout=20)
    assert resumed.returncode==0,resumed.stderr.decode()[-1800:]

def test_ephemeral_prepared_request_cannot_dispatch_after_restart(tmp_path):
    from nana_core.continuity.world_loop.cognition import CognitionSession
    from nana_core.continuity.world_loop.semantics import MediaSemanticService
    db=tmp_path/'subject/self.db'
    with fresh(db) as r:
        c,adapter,m,a=setup(r,tmp_path);value=c.observe(c.request('screen.a',request_id='original',semantic=False))
        target=c.router.resolve(RouteRequest(operation='VISION',input_modalities=('IMAGE',)),c.policy)
        service=MediaSemanticService(target.cognition_session(r));cid=service.prepare('prepared-only',value['memory_id'],png(),ephemeral=True)
        assert service.session._volatile_inputs and m.calls==0
    with fresh(db) as r:
        c,adapter,m,a=setup_existing(r,tmp_path)
        target=c.router.resolve(RouteRequest(operation='VISION',input_modalities=('IMAGE',)),c.policy);session=target.cognition_session(r)
        outcome=session.execute(cid);assert outcome['state']=='STALE' and m.calls==0
