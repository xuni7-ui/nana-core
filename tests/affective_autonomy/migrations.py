"""Actual versioned migrations, managed restore quarantine and erasure replay."""
from pathlib import Path
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.continuity import ContinuityStore,IdentityService
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject import SubjectLoop,SubjectInput
from nana_core.continuity.records import RecordService
from nana_core.presence import NanaRuntime,RuntimeConfig
from nana_core.presence.authority import VirtualClock,RuntimeLease
from .life import fresh,equip,propose,rule,familiar,influence


def run(directory):
 reports=[];clock=VirtualClock()
 for version in (7,8):
  path=Path(directory)/str(version)/'self.db';auth=OperatorAuthority()
  with ContinuityStore(path,clock,schema_target=version) as old:
   IdentityService(old,auth);MemoryService(old).entity('person-a','PERSON')
   event=SubjectInput(source_key='synthetic.migrate.existing',kind='INTERACTION',origin='USER',entity_id='person-a',scope='lab',text='An existing fictional relationship',observed_at_us=clock.utc_now_us(),relationship_kind='SHARED_HISTORY')
   original=SubjectLoop(old,scopes=('lab',)).run(event)
   identity=old.identity.copy();body=RecordService(old).read(original.record_id)['payload']
  config=RuntimeConfig(scopes=('lab',),entity_id='person-a')
  runtime_ids=[]
  if version==8:
   with NanaRuntime(path,config,clock=clock) as r:
    runtime_ids=[x['schedule_id'] for x in r.store.all('runtime_schedules')]
    old_epoch=r.lease.epoch
  with NanaRuntime(path,config.model_copy(update={'schema_target':9}),clock=clock) as r:
   assert r.store.identity==identity and r.store.db.execute('PRAGMA user_version').fetchone()[0]==9
   assert RecordService(r.store).read(original.record_id)['payload']==body
   assert r.subject.run(event).cycle_id==original.cycle_id
   if version==8:
    assert [x['schedule_id'] for x in r.store.all('runtime_schedules')]==runtime_ids
    assert r.lease.epoch==old_epoch+1
   assert not r.store.db.execute('PRAGMA foreign_key_check').fetchall()
   count=r.store.db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
   assert count==39
   reports.append({'from':version,'to':9,'result':'PASS','table_count':count,'identity_preserved':True,'history_ids_preserved':True,'runtime_history_preserved':True,'foreign_key_check':'clean'})
 with fresh(Path(directory)/'restore'/'self.db') as r:
  realizer,ctrl=equip(r);ctrl.install(rule(r),r.authority);familiar(r);c=propose(r)
  blocked=realizer.gate.gate(c.intention_id,expected_revision=1)
  source=r.store.db.execute("SELECT s.memory_id FROM subject_events s JOIN relationship_events e ON e.subject_event_id=s.subject_event_id WHERE e.relation_kind='SHARED_JOKE'").fetchone()
  backup=Path(directory)/'backup'/'self.db';replay=Path(directory)/'replay'/'self.db'
  r.store.backup(backup)
  MemoryService(r.store,r.authority).forget(source['memory_id'],r.authority)
  assert source['memory_id'] not in {m for rid in influence(r).source_record_ids for m in RecordService(r.store).support(rid)}
  r.store.replay(replay)
  identity=r.store.identity['identity_id']
  for target in (backup,replay):
   with ContinuityStore(target,r.clock,schema_target=9) as copy:
    assert copy.identity['identity_id']==identity
    assert copy.one('memories',source['memory_id'])['lifecycle']=='DELETED'
    assert not copy.db.execute('PRAGMA foreign_key_check').fetchall()
    try:RuntimeLease(copy,r.config).acquire();raise AssertionError('restored authority auto-enabled')
    except CoreError as e:assert e.code=='RUNTIME_RESTORE_QUARANTINED'
    assert copy.db.execute("SELECT count(*) FROM events WHERE kind='governance.constraint_revision'").fetchone()[0]==1
    # Personal lineage can erase outcome body; independent governance roots and
    # opaque historical event remain. Never resurrect prose for auditability.
    assert copy.db.execute("SELECT 1 FROM events WHERE kind='governance.outcome'").fetchone()
    assert copy.one('continuity_records',blocked.record_id)['lifecycle']=='DELETED'
    reports.append({'restore':target.parent.name,'result':'PASS','quarantined':True,'deleted_source_not_resurrected':True,'governance_history_preserved':True,'derived_views_not_authority':True})
 return {'result':'PASS','checks':reports,'v9_new_business_tables':0,'default_continuity_schema':7,'default_runtime_schema':8}
