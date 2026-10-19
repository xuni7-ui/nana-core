import json,os,signal,subprocess,sys,time
from pathlib import Path
from nana_core.life.control import request
from nana_core.life.cloud import health,backup
from nana_core.continuity import ContinuityStore
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from .conftest import initialize,REPO

def wait_ready(home,p):
 start=time.monotonic()
 while time.monotonic()-start<8:
  assert p.poll() is None
  if (home/'control.sock').exists() and health(home)['process_ready']:return
  time.sleep(.02)
 raise AssertionError('owned runtime did not become ready')

def test_headless_control_restart_dedup_and_quarantined_backup(tmp_path):
 task=ApplicationTask(task_id='note',kind='CONTENT',initial='b\na\nb',wanted='a\nb')
 with OwnedApplication(tmp_path/'app',tasks=(task,)) as target:
  home=tmp_path/'life';initialize(home,owned_application_profile=str(target.profile))
  with LifeApplication(home,bootstrap_grant=True) as app:
   identity=app.runtime.identity_id;app.pause()
  with (tmp_path/'process.log').open('w') as log:
   args=[sys.executable,'-m','nana_core.life','run','--home',str(home),'--seconds','30','--headless','--control','--json']
   p=subprocess.Popen(args,cwd=REPO,stdout=log,stderr=log)
   try:
    wait_ready(home,p)
    first=request(home,{'operation':'view','view':'status'})
    assert first['ok'] and first['result']['identity_id']==identity
    assert not request(home,{'operation':'grant','capability':'*'})['ok']
    bk=request(home,{'operation':'backup','name':'checkpoint'})
    assert bk['ok'] and not bk['result']['runnable']
    assert not request(home,{'operation':'backup','name':'../../escape'})['ok']
    os.kill(p.pid,signal.SIGKILL);p.wait(4);assert p.returncode==-signal.SIGKILL
    # Recover a crash-consistent review snapshot, never activate a duplicate.
    crash_copy=tmp_path/'crash-copy.db'
    with ContinuityStore(home/'subject/self.db',schema_target=13) as source:
     assert not backup(source,crash_copy)['runnable']
    with ContinuityStore(crash_copy,schema_target=13) as review:
     assert review.identity['identity_id']==identity
     assert review.one('core_meta','recovery_quarantine')['value_json']=='true'
     assert not list(review.db.execute('PRAGMA foreign_key_check'))
    p=subprocess.Popen(args,cwd=REPO,stdout=log,stderr=log);wait_ready(home,p)
    assert request(home,{'operation':'view','view':'status'})['result']['autonomy']=='PAUSED'
    request(home,{'operation':'control','command':'resume'})
    start=time.monotonic()
    while time.monotonic()-start<10:
     state=json.loads((Path(target.target.workspace)/'application-state.json').read_text())
     if state['effects']:break
     time.sleep(.05)
    assert len(state['effects'])==1
    request(home,{'operation':'control','command':'stop'});p.wait(4);assert p.returncode==0
   finally:
    if p.poll() is None:p.kill();p.wait(4)
  assert not (home/'control.sock').exists()
  with LifeApplication(home) as app:
   assert app.runtime.identity_id==identity and len(app.runtime.store.all('grants'))==1
   for _ in range(3):app.tick()
  assert len(json.loads((Path(target.target.workspace)/'application-state.json').read_text())['effects'])==1
  assert not health(home)['process_ready']
