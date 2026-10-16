"""Real development migrations and managed quarantine, never production DB."""
from pathlib import Path
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.subject import SubjectLoop
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.authority import VirtualClock,RuntimeLease
from .fixtures import fresh,bootstrap,event
from nana_core.continuity.relational.bootstrap import anchor_view


def run(directory):
 from types import SimpleNamespace
 checks=[]
 for version in (7,8,9):
  path=Path(directory)/str(version)/'self.db';clock=VirtualClock();auth=OperatorAuthority()
  with ContinuityStore(path,clock,schema_target=version) as old:
   IdentityService(old,auth);MemoryService(old).entity('anchor-person','PERSON')
   shell=SimpleNamespace(clock=clock)
   c=SubjectLoop(old,scopes=('lab',)).run(event(shell,'existing',relationship_kind='SHARED_HISTORY'))
   identity=old.identity.copy();payload=RecordService(old).read(c.record_id)['payload']
  runtime_ids=[]
  if version>=8:
   cfg=RuntimeConfig(schema_target=version,scopes=('lab',),entity_id='anchor-person')
   with NanaRuntime(path,cfg,clock=clock) as rt:runtime_ids=[s['schedule_id'] for s in rt.store.all('runtime_schedules')]
  cfg=RuntimeConfig(schema_target=10,scopes=('lab',),entity_id='anchor-person')
  with NanaRuntime(path,cfg,clock=clock) as rt:
   assert rt.store.identity==identity
   assert RecordService(rt.store).read(c.record_id)['payload']==payload
   assert rt.subject.run(event(SimpleNamespace(clock=clock),'existing',relationship_kind='SHARED_HISTORY')).cycle_id==c.cycle_id
   assert set(runtime_ids)<={s['schedule_id'] for s in rt.store.all('runtime_schedules')}
   assert not rt.store.db.execute('PRAGMA foreign_key_check').fetchall()
   count=rt.store.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0];assert count==39
   assert rt.store.db.execute('PRAGMA user_version').fetchone()[0]==10
   checks.append({'from':version,'to':10,'result':'PASS','table_count':count,'identity_ids_history_preserved':True,'runtime_history_preserved':True,'foreign_key_check':'clean'})
 with fresh(Path(directory)/'managed'/'self.db') as rt:
  service,authority=bootstrap(rt)
  old=anchor_view(rt.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',))
  backup=Path(directory)/'backup'/'self.db';replay=Path(directory)/'replay'/'self.db'
  rt.store.backup(backup)
  source=RecordService(rt.store).support(old.source_record_id)[0]
  MemoryService(rt.store,rt.authority).forget(source,rt.authority)
  assert anchor_view(rt.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)) is None
  rt.store.replay(replay)
  for path in (backup,replay):
   with ContinuityStore(path,rt.clock,schema_target=10) as copy:
    assert copy.identity['identity_id']==rt.store.identity['identity_id']
    assert anchor_view(copy,'anchor-person',scope='lab',privacy_classes=('PERSONAL',)) is None
    assert not copy.db.execute('PRAGMA foreign_key_check').fetchall()
    try:RuntimeLease(copy,rt.config).acquire();raise AssertionError('restored live authority enabled')
    except CoreError as e:assert e.code=='RUNTIME_RESTORE_QUARANTINED'
    checks.append({'restore':path.parent.name,'result':'PASS','quarantined':True,'no_deleted_anchor_resurrection':True})
 return {'result':'PASS','checks':checks,'new_business_tables':0,'defaults':{'C':7,'D':8,'AFFECT':9,'relational':'explicit10'}}
