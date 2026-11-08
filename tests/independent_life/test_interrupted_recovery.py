"""Controlled stopped-owner recovery: no external provider or production data."""
import sqlite3
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
from nana_core.life.application import LifeApplication
from nana_core.life.interrupted_recovery import recover_interrupted
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.presence.authority import VirtualClock
from nana_core.storage.sqlite_store import Transaction
from tests.independent_life.conftest import initialize
from tests.independent_life.test_dialogue import relay


def test_stopped_owner_fenced_recovery_keeps_unknown_and_reservations(tmp_path, monkeypatch):
    home = tmp_path/'home'
    initialize(home, active=0)
    clock = VirtualClock()
    calls = []
    def timeout(self, request):
        calls.append(request.request_id)
        raise TimeoutError()
    monkeypatch.setattr(OpenAIJSONTransport, 'exchange', timeout)
    with relay(home) as (router, _), LifeApplication(home,clock=clock,router=router) as app:
        app.pause()
        app.chat('SYNTHETIC interrupted one', message_id='interrupted-1')
        app.chat('SYNTHETIC interrupted two', message_id='interrupted-2')
        rows=app.runtime.store.all('cognitive_requests')
        assert len(rows)==2 and len(calls)==2
        epoch=app.runtime.lease.epoch
        with app.runtime.store.transaction('synthetic.interrupted_fixture') as tx:
            tx.update('cognitive_requests',rows[0]['request_id'],state='PREPARED')
            tx.update('cognitive_requests',rows[1]['request_id'],state='CALLING')
        identity,lineage,_ = existing_identity(home)
        binding={'expected_epoch':epoch,'expected_subject':identity,'expected_lineage':lineage}
        with pytest.raises(CoreError,match='RUNTIME_ALREADY_ACTIVE'):
            recover_interrupted(home,**binding)
    # The test process still exists even after it released its lease.
    with pytest.raises(CoreError,match='INTERRUPTED_OWNER_STILL_ALIVE'):
        recover_interrupted(home,**binding)
    with monkeypatch.context() as unavailable:
        def denied(pid):raise PermissionError('synthetic /proc denial')
        unavailable.setattr('nana_core.life.interrupted_recovery.process_identity',denied)
        with pytest.raises(CoreError,match='INTERRUPTED_OWNER_UNVERIFIED'):
            recover_interrupted(home,**binding)
    # Fixture simulates the prior host process having exited, not a provider result.
    monkeypatch.setattr('nana_core.life.interrupted_recovery.process_identity',lambda pid: ('synthetic-other','other-boot'))
    with pytest.raises(CoreError,match='INTERRUPTED_RECOVERY_EPOCH_CHANGED'):
        recover_interrupted(home,**{**binding,'expected_epoch':epoch+1})
    with pytest.raises(CoreError,match='INTERRUPTED_RECOVERY_IDENTITY_MISMATCH'):
        recover_interrupted(home,**{**binding,'expected_lineage':'0'*64})
    original_update=Transaction.update
    seen=[]
    def fail_second(tx,table,key,**fields):
        if table=='cognitive_requests':
            seen.append(key)
            if len(seen)==2:raise RuntimeError('SYNTHETIC_INTERRUPTION')
        return original_update(tx,table,key,**fields)
    with monkeypatch.context() as interrupted:
        interrupted.setattr(Transaction,'update',fail_second)
        with pytest.raises(RuntimeError,match='SYNTHETIC_INTERRUPTION'):
            recover_interrupted(home,**binding)
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
        assert [r[0] for r in db.execute('SELECT state FROM cognitive_requests ORDER BY rowid')]==['PREPARED','CALLING']
        after_failed_epoch=db.execute('SELECT epoch FROM runtime_lease').fetchone()[0]
    assert after_failed_epoch==epoch+1
    result=recover_interrupted(home,**{**binding,'expected_epoch':after_failed_epoch})
    assert result['state']=='INTERRUPTED_ATTEMPTS_UNKNOWN' and result['changed']==2
    assert result['provider_calls']==result['retries']==0 and result['reservations_refunded'] is False
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
        after=db.execute('SELECT request_id,state,reserved_cost_micro,reserved_bytes FROM cognitive_requests ORDER BY rowid').fetchall()
        next_epoch=db.execute('SELECT epoch FROM runtime_lease').fetchone()[0]
        assert db.execute("SELECT count(*) FROM events WHERE kind='runtime.interrupted_attempts_quarantined'").fetchone()[0]==1
    assert [(x[0],x[1],x[2],x[3]) for x in after]==[(r['request_id'],'UNKNOWN',r['reserved_cost_micro'],r['reserved_bytes']) for r in rows]
    assert next_epoch==epoch+2 and len(calls)==2
    assert recover_interrupted(home,**{**binding,'expected_epoch':next_epoch})['state']=='NO_INTERRUPTED_ATTEMPTS'


def test_actual_process_crash_then_explicit_cli_recovery(tmp_path):
    root=Path(__file__).resolve().parents[2]
    home=tmp_path/'home'
    initialize(home,active=0)
    env={**os.environ,'PYTHONPATH':str(root/'src'),'PYTHONDONTWRITEBYTECODE':'1'}
    code='''
import json,os,sys
from pathlib import Path
from nana_core.life.application import LifeApplication
from nana_core.continuity.world_loop.cognition import OpenAIJSONTransport
from nana_core.presence.authority import VirtualClock
from tests.independent_life.test_dialogue import relay
def timeout(self,request): raise TimeoutError()
OpenAIJSONTransport.exchange=timeout
home=Path(sys.argv[1])
with relay(home) as (router,_):
 app=LifeApplication(home,clock=VirtualClock(),router=router)
 app.pause();app.chat('SYNTHETIC crash',message_id='crash-fixture')
 row=app.runtime.store.all('cognitive_requests')[0]
 with app.runtime.store.transaction('synthetic.pending_crash') as tx:
  tx.update('cognitive_requests',row['request_id'],state='CALLING')
 print(json.dumps({'epoch':app.runtime.lease.epoch,'id':row['request_id'],'reserved':row['reserved_cost_micro']}),flush=True)
 os._exit(0)
'''
    child=subprocess.run([sys.executable,'-c',code,str(home)],cwd=root,env=env,text=True,capture_output=True,timeout=20,check=True)
    prior=json.loads(child.stdout.strip().splitlines()[-1])
    subject,lineage,active=existing_identity(home)
    assert active==1
    command=[sys.executable,'-m','nana_core.life.portable_runtime','recover-interrupted','--home',str(home),
             '--expected-epoch',str(prior['epoch']),'--expected-subject',subject,'--expected-lineage',lineage]
    denied=subprocess.run(command,cwd=root,env=env,text=True,capture_output=True,timeout=15)
    assert denied.returncode!=0 and 'INTERRUPTED_RECOVERY_ACKNOWLEDGEMENT_REQUIRED' in denied.stdout
    completed=subprocess.run([*command,'--acknowledge-interruption'],cwd=root,env=env,text=True,capture_output=True,timeout=15,check=True)
    result=json.loads(completed.stdout)
    assert result['state']=='INTERRUPTED_ATTEMPTS_UNKNOWN' and result['changed']==1
    assert result['provider_calls']==result['retries']==0 and result['reservations_refunded'] is False
    with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT state,reserved_cost_micro FROM cognitive_requests WHERE request_id=?',(prior['id'],)).fetchone()
    assert row==('UNKNOWN',prior['reserved'])
    assert existing_identity(home)[2]==0
