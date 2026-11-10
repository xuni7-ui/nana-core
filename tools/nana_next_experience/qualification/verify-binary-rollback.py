"""Stopped existing DEV binary rollback/return only, never database rollback."""
import argparse,json,sqlite3,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--previous-bundle',type=Path);p.add_argument('--work',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--single',action='store_true');a=p.parse_args()
report=json.loads(a.prior.read_text());home=a.work.resolve()/'life';bundle=a.bundle.resolve()
if a.output.exists() or report['execution']!='ACTUAL_INSTALLED_DEV_CORE_NOT_CLOUD':raise ValueError('FRESH_OWNED_DEV_BINDING_REQUIRED')
if json.loads((home/'nana-space-development.json').read_text())!={'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':report['subject_id']}:raise ValueError('OWNED_DEV_ONLY')
if a.single:
 if Path(sys.prefix).resolve()!=bundle/'.venv':raise ValueError('INSTALLED_INTERPRETER_REQUIRED')
 sys.path.insert(0,str(bundle/'src'));sys.dont_write_bytecode=True
 from nana_core.life.application import LifeApplication
 from nana_core.life.portable_runtime import owner_alive,status
 from nana_core.life.live_api.supervisor import existing_identity
 from nana_core.presence.authority import VirtualClock
 import nana_core.life.application as source
 assert Path(source.__file__).resolve().is_relative_to(bundle/'src')
 if owner_alive(status(home/'subject/self.db')):raise ValueError('STOPPED_OWNER_REQUIRED')
 with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
  high=db.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
  calls=db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]
  cycles=db.execute('SELECT count(*) FROM subject_cycles').fetchone()[0]
 before=existing_identity(home)
 assert before[:2]==(report['subject_id'],report['lineage_binding'])
 with LifeApplication(home,clock=VirtualClock(max(high,time.time_ns()//1000))) as app:
  app.pause();assert app.runtime.identity_id==report['subject_id']
  assert len(app.runtime.store.all('identities'))==1
  assert app.runtime.store.db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]==calls
  assert app.runtime.store.db.execute('SELECT count(*) FROM subject_cycles').fetchone()[0]==cycles
 assert existing_identity(home)==before
 result={'execution':'ACTUAL_INSTALLED_STOPPED_DEV_BINARY_ATTACH_NOT_DB_ROLLBACK','source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'subject_id':report['subject_id'],'lineage_binding':report['lineage_binding'],'single_identity':True,'same_subject_and_lineage':True,'additional_cognitive_requests':0,'additional_subject_cycles':0,'real_sends':0,'production_changed':False}
else:
 old=a.previous_bundle.resolve();previous=json.loads((old/'runtime.json').read_text());current=json.loads((bundle/'runtime.json').read_text())
 for key in ('schema_version','bundle_version','supported_platform','secret_binding_contract','archive_ingress_contract','bilibili_life_contract','platform_runtime_contract','private_context_contract'):assert previous.get(key)==current.get(key)
 assert current['source_commit']==report['source_commit']
 parts=[]
 for name,target in (('rollback',old),('return',bundle)):
  out=a.output.with_name(a.output.stem+'-'+name+'.json')
  subprocess.run([str(target/'.venv/bin/python'),'-I','-B',str(Path(__file__).resolve()),'--single','--bundle',str(target),'--work',str(a.work),'--prior',str(a.prior),'--output',str(out)],check=True,timeout=60)
  parts.append(json.loads(out.read_text()))
 result={'execution':'ACTUAL_STOPPED_DEV_BINARY_ROLLBACK_AND_RETURN','subject_id':report['subject_id'],'lineage_binding':report['lineage_binding'],'stages':parts,'database_rollback':False,'production_changed':False,'real_provider_calls':0,'physical_phone':'NOT_RUN','qualification':'NO_ACTIVE_PLAN_HOT_SWITCH_OR_PRODUCTION_HOST_QUALIFICATION'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
