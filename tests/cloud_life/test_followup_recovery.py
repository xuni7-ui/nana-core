import os,signal,subprocess,sys,time,json
from pathlib import Path
import pytest
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from .conftest import initialize,until,REPO

@pytest.mark.parametrize('cut',['GOAL','REFLECTION'])
def test_c_committed_decision_survives_sigkill_before_followup(tmp_path,cut):
 task=ApplicationTask(task_id='note',kind='DOCUMENT',initial='old ',wanted='new')
 with OwnedApplication(tmp_path/'app',tasks=(task,)) as target:
  home=tmp_path/'life';initialize(home,owned_application_profile=str(target.profile))
  with LifeApplication(home,bootstrap_grant=True) as app:identity=app.runtime.identity_id
  marker=tmp_path/'cut'
  with (tmp_path/'cut.log').open('w') as stream:
   p=subprocess.Popen([sys.executable,'-m','tools.nana_cloud_daily_life.crash_worker','--home',str(home),'--marker',str(marker),'--cut',cut],cwd=REPO,stdout=stream,stderr=stream)
   try:
    deadline=time.monotonic()+15
    while not marker.exists():
     assert p.poll() is None and time.monotonic()<deadline
     time.sleep(.02)
    p.kill();p.wait(4);assert p.returncode==-signal.SIGKILL
   finally:
    if p.poll() is None:p.kill();p.wait(4)
  with LifeApplication(home) as app:
   assert app.runtime.identity_id==identity
   until(app,lambda:bool(app.runtime.store.db.execute("SELECT 1 FROM goals WHERE state='COMPLETED'").fetchone()))
   assert app.runtime.store.one('subject_cycles',marker.read_text())
   assert app.runtime.store.db.execute("SELECT count(*) FROM events WHERE source_namespace='runtime.followup' AND json_extract(data_json,'$.data.cycle_id')=?",(marker.read_text(),)).fetchone()[0]==1
   assert len(app.runtime.store.all('goals'))==1 and len(app.runtime.store.all('grants'))==1
   assert not list(app.runtime.store.db.execute('PRAGMA foreign_key_check'))
  assert len(json.loads((Path(target.target.workspace)/'application-state.json').read_text())['effects'])==2
