import json,sqlite3
from uuid import uuid4
from pathlib import Path
import pytest
from nana_core.contracts import CoreError
from nana_core.life.application import LifeApplication
from nana_core.life.cloud import backup,transfer,receive,health,RotatingJSONLog
from nana_core.continuity import ContinuityStore
from nana_core.continuity.hands.host import OwnedApplication
from nana_core.continuity.hands.contracts import ApplicationTask
from nana_core.continuity.portable import SubjectPackageService,PortableTransferAuthority
from .conftest import initialize,config,until
BASE='d7886ba9b49cf2fbb52cebcbce9525394c938d3c'

def test_live_backup_is_consistent_quarantined_and_source_delete_propagates(tmp_path):
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
 with LifeApplication(home) as app:
  app.pause();reply=app.chat('这个话题先不要深入了',topic='project',privacy='PROJECT',message_id='one')
  mid=reply['message_memory_id'];path=tmp_path/'copies'/'review.db'
  info=backup(app.runtime.store,path);assert not info['runnable']
  with pytest.raises(CoreError):
   from nana_core.presence.runtime import NanaRuntime
   from nana_core.life.application import runtime_config
   NanaRuntime(path,runtime_config(app.config))
  app.forget(mid)
  with ContinuityStore(path,schema_target=13) as copy:
   assert copy.one('memories',mid)['lifecycle']=='DELETED'
   assert not list(copy.db.execute('pragma foreign_key_check'))
  assert health(home)['process_ready']
 assert not health(home)['process_ready']

def test_runtime_subject_transfer_preserves_history_and_excludes_host_config(tmp_path):
 home=tmp_path/'a';initialize(home,max_autonomous_materials=0,provider_background_cognition=True)
 with LifeApplication(home) as app:
  assert app.config.provider_background_cognition is True and app.runtime.cognition.provider_factory is None
  identity=app.runtime.identity_id;app.pause();app.chat('这个话题先不要深入了',topic='shared',privacy='PROJECT',message_id='decline')
 target_id=str(uuid4());package=tmp_path/'subject.zip';result=transfer(home,package,destination_id=target_id,source_commit=BASE)
 with pytest.raises(CoreError,match='PORTABLE_SOURCE_RETIRED'):
  LifeApplication(home)
 out=receive(package,tmp_path/'b',sha256=result['sha256'],destination_id=target_id,config=config(max_autonomous_materials=0))
 assert out['identity_id']==identity and not out['provider_config_transferred']
 with LifeApplication(tmp_path/'b') as app:
  assert app.runtime.identity_id==identity
  assert app.config.provider_background_cognition is False and app.runtime.cognition.provider_factory is None
  from nana_core.continuity.subject.context_fit import depth_boundary
  assert depth_boundary(app.runtime.store,'project-user','project-work','shared',app.policy.readable_privacy)[0]
  assert all(x['revoked'] for x in app.runtime.store.all('grants'))
  assert not list(app.runtime.store.db.execute('pragma foreign_key_check'))
 # The package contains only the original B8 three files, no life/provider paths.
 import zipfile
 with zipfile.ZipFile(package) as z:assert set(z.namelist())=={'subject.sqlite','privacy.json','manifest.json'}
 with pytest.raises(CoreError,match='CLOUD_FRESH_HOME_REQUIRED'):
  receive(package,tmp_path/'b',sha256=result['sha256'],destination_id=target_id,config=config())

def test_pending_effect_transfer_preserves_unknown_and_consumes_reservation(tmp_path):
 task=ApplicationTask(task_id='note',kind='DOCUMENT',wanted='finite')
 with OwnedApplication(tmp_path/'target',tasks=(task,)) as target:
  home=tmp_path/'a';initialize(home,owned_application_profile=str(target.profile))
  with LifeApplication(home,bootstrap_grant=True) as app:
   old=app.work.port.execute;seen=[]
   def changed(inv):
    r=old(inv)
    if inv.capability=='world.publish':
     seen.append(inv.action_id);(Path(target.target.workspace)/'note.txt').write_text('concurrent approved modification')
    return r
   app.work.port.execute=changed
   until(app,lambda:bool(seen));aid=seen[0];identity=app.runtime.identity_id
   assert app.runtime.store.one('actions',aid)['state']=='UNKNOWN'
  with pytest.raises(CoreError,match='PORTABLE_UNRESOLVED_EFFECT'):
   transfer(home,tmp_path/'strict.zip',destination_id=str(uuid4()),source_commit=BASE)
  dest=str(uuid4());package=tmp_path/'pending.zip';r=transfer(home,package,destination_id=dest,source_commit=BASE,pending_effects=True)
  receive(package,tmp_path/'b',sha256=r['sha256'],destination_id=dest,config=config(max_autonomous_materials=0))
  with LifeApplication(tmp_path/'b') as app:
   assert app.runtime.identity_id==identity and app.runtime.store.one('actions',aid)['state']=='UNKNOWN'
   assert all(x['revoked'] for x in app.runtime.store.all('grants'))
   assert not app.runtime.store.db.execute("SELECT 1 FROM budget_holds WHERE status='HELD'").fetchone()
   assert all(b['limit_value']==b['spent'] and not b['held'] for b in app.runtime.store.all('budgets'))
   for _ in range(5):app.tick()
   assert app.runtime.store.one('actions',aid)['state']=='UNKNOWN'
  assert len(json.loads((Path(target.target.workspace)/'application-state.json').read_text())['effects'])==1

def test_rotation_is_bounded_and_does_not_log_payloads(tmp_path):
 log=RotatingJSONLog(tmp_path,256)
 for n in range(30):log.write(state='WATCHING',clock_us=n,queue_depth=0)
 assert (tmp_path/'runtime.log').stat().st_size<256
 assert (tmp_path/'runtime.log.1').stat().st_size<256
 assert set(json.loads((tmp_path/'runtime.log').read_text().splitlines()[0]))=={'state','clock_us','queue_depth'}

def test_disk_guard_rejects_mutation_but_leaves_status_and_stop(tmp_path,monkeypatch):
 from nana_core.life.control import dispatch
 from collections import namedtuple
 home=tmp_path/'life';initialize(home,max_autonomous_materials=0)
 with LifeApplication(home) as app:
  usage=namedtuple('usage','total used free')(1000,1000,0)
  monkeypatch.setattr('nana_core.life.control.shutil.disk_usage',lambda _:usage)
  with pytest.raises(CoreError,match='DISK_GUARD'):dispatch(app,{'operation':'control','command':'resume'})
  assert dispatch(app,{'operation':'view','view':'status'})['identity_id']==app.runtime.identity_id
  assert dispatch(app,{'operation':'control','command':'stop'})['state']=='STOP_REQUESTED'
