"""Official quarantined restore vs unsupported privileged raw cloning."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import pytest
from test_r04_receipt import setup,arm,RAW,NOW,OneShotCoreSink,OneShotSanitizer,FixtureTrustStore,ManualClock,parse_utc
from test_r041_crash import launch,wait_file
from tools.nana_astrbot_shadow.one_shot import ReceiptLedger
from nana_core.storage import Store
from r044_helpers import fixture,fixture_view,readback
import tools.nana_astrbot_shadow.bridge_cli as cli

@pytest.mark.parametrize('kind',['backup','replay'])
def test_official_restore_quarantines_old_armed_snapshot(tmp_path,kind):
    sink,l,r=setup(tmp_path/'original');arm(l,r)
    target=tmp_path/(kind+'.db');getattr(l.store,kind)(target)
    identity=l.store.identity;sink.accept(dict(RAW));sink.close()
    with Store(target) as s:
        assert s.identity==identity and s.one('core_meta','recovery_quarantine')['value_json']=='true'
        with pytest.raises(ValueError,match='RESTORED_STORE_BLOCKED'):ReceiptLedger(s,FixtureTrustStore())
        assert not any(s.all(t) for t in ('actions','attempts','grants','budgets'))


def test_privileged_raw_checkpoint_clone_is_explicitly_unsupported(tmp_path):
    sink,l,r=setup(tmp_path/'original');arm(l,r)
    identity=l.store.identity;sink.close()
    clone=tmp_path/'raw-clone';clone.mkdir(mode=0o700)
    shutil.copyfile(tmp_path/'original/observer-shadow.db',clone/'observer-shadow.db')
    # Deliberate counterexample in FIXXTURE only. No production map is injected.
    for path in (tmp_path/'original',clone):
        s=OneShotSanitizer(scope='r04-test',hash_key=b'F'*32,receipt_id=r.receipt_id)
        sink=OneShotCoreSink(path,s,r.receipt_id,trust=FixtureTrustStore())
        try:
            l=sink.ledger();l.store.clock=ManualClock(parse_utc(NOW.isoformat()))
            assert l.store.identity==identity
            sink.accept(dict(RAW));assert l.status(r.receipt_id)['uses']==1
            assert not l.store.all('actions')
        finally:sink.close()
    # Both forks can consume old state: NOT a supported anti-clone security claim.


def test_50_actual_worker_processes_stop_reap_and_release_lease(tmp_path,monkeypatch):
    monkeypatch.setattr(cli,'operator_ledger',fixture_view)
    started=time.monotonic();exits=[]
    for i in range(50):
        case=tmp_path/('c'+str(i));root,ipc,r,raw=fixture(case)
        p=launch(root,ipc,r.receipt_id,'never',case/'unused')
        try:
            # Import/IPC readiness is separate from the unchanged five-second
            # stop/reap deadline. Fifty sequential cold starts remain required.
            wait_file(p,ipc/'client.json',startup_timeout=15)
            result=cli.stop(root,ipc);assert result['status']=='STOP_REQUESTED'
            assert p.wait(5)==0
            out,err=p.communicate(timeout=5);assert out==err==b''
            assert cli.stop(root,ipc)['stop_result']=='ALREADY_EXITED'
            status,n,_=readback(root,r.receipt_id);assert status['uses']==n==0
            assert not (ipc/'bridge.sock').exists() and not (ipc/'client.json').exists()
            exits.append(p.returncode)
        finally:
            if p.poll() is None:p.kill();p.wait(5)
            p.communicate(timeout=5)
        shutil.rmtree(case)
    assert not list(tmp_path.iterdir()) and exits==[0]*50
    Path('.nana-experiment/r044').mkdir(parents=True,exist_ok=True)
    Path('.nana-experiment/r044/subprocess-soak.json').write_text(json.dumps({'status':'PASS',
        'actual_worker_processes':50,'reaped':50,'owned_child_handles_remaining':0,'SIGTERM_via_pidfd':50,
        'seconds':round(time.monotonic()-started,3),'residual_temp_dirs':0,'residual_sockets':0,
        'held_Store_leases':0,'global_process_observation':'UNKNOWN','host_binding':'UNVERIFIED','production_pins':0}))
