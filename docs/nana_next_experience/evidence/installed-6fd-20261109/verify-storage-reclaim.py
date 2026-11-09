"""Explicit installed DEV experiment, not an automatic production maintenance API.

Reuse the existing stopped owned Subject, original deletion/managed backup and
original Store lock. VACUUM only already reusable pages; never delete history.
"""
import argparse,hashlib,json,os,sqlite3,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--case-id',required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
bundle=a.bundle.resolve();home=a.work.resolve()/'life';report=json.loads(a.prior.read_text())
if a.output.exists() or Path(sys.prefix).resolve()!=bundle/'.venv':raise ValueError('INSTALLED_FRESH_RESULT_REQUIRED')
if report.get('execution')!='ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD' or report.get('source_commit')!=json.loads((bundle/'runtime.json').read_text())['source_commit']:raise ValueError('PRIOR_BINDING_REQUIRED')
if json.loads((home/'nana-space-development.json').read_text())!={'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':report['subject_id']}:raise ValueError('OWNED_DEV_ONLY')
sys.path.insert(0,str(bundle/'src'));sys.dont_write_bytecode=True
from nana_core.life.application import LifeApplication
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.life.portable_runtime import owner_alive,status
from nana_core.continuity import ContinuityStore
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.cold_history import ColdHistoryService,_check_dependencies
from nana_core.actions import OperatorAuthority
from nana_core.contracts import CoreError
from nana_core.life.durability import size_view
if owner_alive(status(home/'subject/self.db')):raise ValueError('STOPPED_OWNED_WRITER_REQUIRED')
identity,lineage,_=existing_identity(home)
if (identity,lineage)!=(report['subject_id'],report['lineage_binding']):raise ValueError('SAME_SUBJECT_REQUIRED')
if a.case_id not in {'canonical2'}:raise ValueError('FROZEN_SYNTHETIC_CASE_REQUIRED')
paths=home/('reclaim-experiment-'+a.case_id);paths.mkdir(mode=0o700)
count=240;ids=[]
with LifeApplication(home) as app:
 app.pause();store=app.runtime.store;calls=store.db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]
 memory=MemoryService(store)
 for index in range(count):
  text='SYNTHETIC_CAPACITY_'+str(index)+' '+'retained source detail. '*1100
  eid=memory.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.capacity.owned',source_reference=a.case_id+'-capacity-'+str(index),source_kind='DIRECT_OBSERVATION'),text=text,privacy_class='PROJECT',observed_time_us=store.clock.utc_now_us()))
  ids.append(memory.add(MemoryCandidate(entity_id='project-user',scope='project-work',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=eid,text=text)))
 store.backup(paths/'before-withdrawal.db')
 for mid in ids[:180]:app.forget(mid)
 # Original backup privacy propagation already erases the retired source body.
 with sqlite3.connect((paths/'before-withdrawal.db').as_uri()+'?mode=ro',uri=True) as copy:
  assert copy.execute('SELECT lifecycle FROM memories WHERE memory_id=?',(ids[0],)).fetchone()[0]=='DELETED'
with ContinuityStore(home/'subject/self.db',schema_target=13) as store:
 assert not getattr(store,'_runtime_guard',None)
 lease=store.db.execute('SELECT state FROM runtime_lease').fetchone();assert lease[0]=='STOPPED'
 operator=OperatorAuthority();cold=ColdHistoryService(store,operator);cold_path=paths/'post-withdrawal-cold.db';cold.create(cold_path,authority=operator)
 def logical_digest():
  # iterdump has no table-row ORDER BY and may choose another covering index
  # after VACUUM changes physical page counts. Canonicalize schema separately,
  # and preserve each table's explicit rowid order without treating rowid values
  # as entity IDs. No SQL, payload or private text is written to the report.
  result={}
  schema=tuple(tuple(row) for row in store.db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name"))
  result['schema']=hashlib.sha256(json.dumps(schema,ensure_ascii=False).encode()).hexdigest()
  for (table,) in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
   h=hashlib.sha256();n=0
   for row in store.db.execute('SELECT * FROM "'+table+'" ORDER BY rowid'):
    values=tuple({'binary_hex':value.hex()} if isinstance(value,bytes) else value for value in row)
    h.update(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode());h.update(b'\n');n+=1
   result[table]={'rows':n,'sha256':h.hexdigest()}
  return result
 def footprint():
  values=size_view(store);files={}
  for name in ('before-withdrawal.db','post-withdrawal-cold.db'):
   info=(paths/name).stat();files[name]={'file_bytes':info.st_size,'allocated_bytes':info.st_blocks*512}
  return {'original_store':values,'managed_copies':files,'total_allocated_with_managed_copies':values['allocated_family_bytes']+sum(v['allocated_bytes'] for v in files.values())}
 raw_dump_before=hashlib.sha256('\n'.join(store.db.iterdump()).encode()).hexdigest()
 before=footprint();privacy=hashlib.sha256(store.privacy.path.read_bytes()).hexdigest();logical=logical_digest()
 assert before['original_store']['reusable_page_bytes']>1024*1024
 started=time.monotonic();assert store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]==0
 checkpointed=footprint();store.db.execute('VACUUM');assert store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]==0
 elapsed=time.monotonic()-started
 assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 assert not store.db.execute('PRAGMA foreign_key_check').fetchone();_check_dependencies(store.db)
 after_logical=logical_digest()
 (a.output.parent/(a.output.stem+'-logical.json')).write_text(json.dumps({'before':logical,'after':after_logical},indent=2)+'\n')
 assert after_logical==logical
 assert hashlib.sha256(store.privacy.path.read_bytes()).hexdigest()==privacy
 after=footprint();assert after['original_store']['allocated_file_bytes']['database']<checkpointed['original_store']['allocated_file_bytes']['database']
 raw_dump_after=hashlib.sha256('\n'.join(store.db.iterdump()).encode()).hexdigest()
 view=cold.open(cold_path,scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',))
 assert view.memory(ids[-1])['text'].startswith('SYNTHETIC_CAPACITY_239 ')
 try:view.memory(ids[0])
 except CoreError as exc:assert exc.code=='COLD_HISTORY_SOURCE_UNAVAILABLE'
 else:raise AssertionError('WITHDRAWN_SOURCE_MUST_STAY_UNAVAILABLE')
with LifeApplication(home) as app:
 app.pause();assert app.runtime.identity_id==identity
 assert app.runtime.store.db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]==calls
 assert MemoryService(app.runtime.store).read(ids[-1])['text'].startswith('SYNTHETIC_CAPACITY_239 ')
 app.forget(ids[-1])
 cold=ColdHistoryService(app.runtime.store,app.runtime.authority)
 try:cold.open(cold_path,scopes=('project-work',),privacy_classes=('PROJECT',),entity_ids=('project-user',))
 except CoreError as exc:assert exc.code=='COLD_HISTORY_CHANGED_RECREATE_REQUIRED'
 else:raise AssertionError('MUTATED_OLD_COLD_SEAL_MUST_NOT_BE_REUSED')
result={'execution':'EXPLICIT_INSTALLED_DEV_PHYSICAL_REUSE_EXPERIMENT_NOT_PRODUCTION_API','source_commit':report['source_commit'],'subject_id':identity,'lineage_binding':lineage,'synthetic_sources':count,'explicitly_withdrawn_before_reclaim':180,'before':before,'after_checkpoint_before_vacuum':checkpointed,'after':after,'sqlite_vacuum_seconds':elapsed,'all_canonical_schema_and_row_order_digests_unchanged':True,'raw_sql_dump_before':raw_dump_before,'raw_sql_dump_after':raw_dump_after,'privacy_anchor_unchanged_during_reclaim':privacy,'same_subject_restart':True,'old_and_later_withdrawal_remain_effective':True,'active_history_evicted':False,'automatic_reclaim_implemented':False,'additional_model_calls':0,'real_account_sends':0,'physical_phone':'NOT_RUN','production_changed':False}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
