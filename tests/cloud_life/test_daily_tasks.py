import json
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.hands.host import OwnedApplication,daily_tasks
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.life.application import LifeApplication
from .conftest import initialize,until

def test_daily_file_organization_and_content_processing_use_original_kernel(tmp_path):
 tasks=daily_tasks()[-4:]
 with OwnedApplication(tmp_path/'app',tasks=tasks) as target:
  home=tmp_path/'life';initialize(home,owned_application_profile=str(target.profile))
  with LifeApplication(home,bootstrap_grant=True) as app:
   identity=app.runtime.identity_id
   until(app,lambda:len(app.runtime.store.all('goals'))==4 and all(g['state']=='COMPLETED' for g in app.runtime.store.all('goals')))
   root=Path(target.target.workspace)
   assert (root/'reading-list.txt').read_text()=='map\nwind'
   assert (root/'index-topics.txt').read_text()=='alpha\nbeta'
   assert not (root/'archive-notes--draft.txt').exists()
   assert (root/'archive-notes--reviewed.txt').read_text()=='public project notes:draft'
   assert (root/'organize-export--processed.txt').read_text()=='synthetic export:incoming'
   assert len(json.loads((root/'application-state.json').read_text())['effects'])==4
   assert all(a['state']=='SUCCEEDED' for a in app.runtime.store.all('actions'))
   assert len(app.runtime.store.all('grants'))==1 and app.runtime.identity_id==identity
   assert not app.runtime.store.all('cognitive_requests')
   # Existing finite authority cannot authorize a different destination basename.
   key='hands://'+target.target.instance_id+'/archive-notes/effect'
   with pytest.raises(CoreError,match='EFFECT_SCOPE_DENIED'):
    app.work.port.preflight('world.publish',key,{'data_privacy':'PROJECT','data':{'task_id':'archive-notes','revision':2,'commands':[{'op':'MOVE','source':'draft','destination':'outside'}]}})

def test_file_mapping_rejects_overwrite_and_path_escape():
 for wanted in [{'draft':'../outside'},{'draft':'raw','raw':'done'},{'draft':'same','raw':'same'}]:
  with pytest.raises(ValueError):ApplicationTask(task_id='files',kind='FILES',fields=tuple(wanted),wanted=wanted)
