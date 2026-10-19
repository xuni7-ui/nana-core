import json,os,signal,subprocess,sys,time
from pathlib import Path
import pytest
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from tools.nana_controlled_hands.qualification import snapshot
from .conftest import initialize,until,REPO

@pytest.mark.parametrize('mode',['BEFORE_PREPARE','BEFORE_EFFECT','AFTER_EFFECT','DURING_VERIFY','DURING_LEARNING','DURING_SKILL_TEST'])
def test_actual_process_sigkill_preserves_identity_effects_and_original_cursor(tmp_path,mode):
    tasks=None if mode in {'DURING_LEARNING','DURING_SKILL_TEST'} else (ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='safe content'),)
    with OwnedApplication(tmp_path/'target',tasks=tasks) as host:
        home=tmp_path/'life';initialize(home,host.profile)
        with LifeApplication(home,bootstrap_grant=True) as app:identity=app.runtime.identity_id
        marker=tmp_path/'cut';log=tmp_path/'worker.log'
        with log.open('w') as stream:
            p=subprocess.Popen([sys.executable,'-m','tools.nana_controlled_hands.crash_worker','--home',str(home),'--mode',mode,'--marker',str(marker)],cwd=REPO,stdout=stream,stderr=stream)
            try:
                start=time.monotonic()
                while not marker.exists():
                    assert p.poll() is None,log.read_text()
                    assert time.monotonic()-start<40,'cut not reached'
                    time.sleep(.02)
                before=snapshot(home);external=json.loads((Path(host.target.workspace)/'application-state.json').read_text())
                os.kill(p.pid,signal.SIGKILL);p.wait(timeout=4);assert p.returncode==-signal.SIGKILL
            finally:
                if p.poll() is None:p.kill();p.wait(timeout=4)
        with LifeApplication(home) as app:
            r=app.runtime;assert r.identity_id==identity and len(r.store.all('grants'))==1
            if mode=='BEFORE_EFFECT':
                for _ in range(15):app.tick();time.sleep(.025)
                effects=json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects']
                assert not effects and not external['effects']
                assert r.store.one('actions',marker.read_text())['state']=='UNKNOWN'
            elif mode in {'AFTER_EFFECT','DURING_VERIFY','BEFORE_PREPARE'}:
                until(app,lambda:bool(r.store.db.execute("SELECT 1 FROM goals WHERE state='COMPLETED'").fetchone()))
                effects=json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects']
                assert len(effects)==1
                assert r.store.one('actions',marker.read_text())['state']=='SUCCEEDED'
                assert len(r.store.all('actions'))==len(before['actions'])
            else:
                until(app,lambda:len(r.store.all('goals'))==8 and all(g['state'] in {'COMPLETED','FAILED'} for g in r.store.all('goals')),seconds=40)
                after=json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects']
                assert set(external['effects'])<=set(after) and len(after)==10
            assert len({a['idempotency_key'] for a in r.store.all('actions')})==len(r.store.all('actions'))
            assert not list(r.store.db.execute('PRAGMA foreign_key_check'))


def test_real_file_ipc_disagreement_remains_unknown_without_retry(tmp_path):
    task=ApplicationTask(task_id='doc',kind='DOCUMENT',wanted='safe content')
    with OwnedApplication(tmp_path/'target',tasks=(task,)) as host:
        home=tmp_path/'life';initialize(home,host.profile,skills=False)
        with LifeApplication(home,bootstrap_grant=True) as app:
            original=app.work.port.execute;calls=[]
            def changed(inv):
                reply=original(inv)
                if inv.capability=='world.publish':
                    calls.append(inv.action_id)
                    (Path(host.target.workspace)/'doc.txt').write_text('Concurrent approved test actor changed actual file')
                return reply
            app.work.port.execute=changed
            until(app,lambda:bool(calls))
            for _ in range(8):app.tick();time.sleep(.03)
            assert len(calls)==1 and app.runtime.store.one('actions',calls[0])['state']=='UNKNOWN'
            identity=app.runtime.identity_id
        with LifeApplication(home) as app:
            for _ in range(8):app.tick();time.sleep(.03)
            assert app.runtime.identity_id==identity and app.runtime.store.one('actions',calls[0])['state']=='UNKNOWN'
            assert len(json.loads((Path(host.target.workspace)/'application-state.json').read_text())['effects'])==1
