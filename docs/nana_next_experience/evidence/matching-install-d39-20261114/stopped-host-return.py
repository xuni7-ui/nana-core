"""Stopped owned startup DEV only; no Store rollback or ticks, old then new."""
import argparse,json,sqlite3,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--previous-bundle',type=Path);p.add_argument('--work',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--single',action='store_true');a=p.parse_args()
assert __debug__ and not a.output.exists()
home=a.work.resolve();bundle=a.bundle.resolve();prior=json.loads(a.prior.read_text())
assert prior['execution']=='ACTUAL_INSTALLED_DEV_STARTUP_ORIGINAL_RUNTIME_LOOPBACK' and prior['disable_restart_and_legacy_field_omission']
assert 'provider_background_cognition' not in json.loads((home/'life.json').read_text())
if a.single:
 assert Path(sys.prefix).resolve()==bundle/'.venv'
 sys.dont_write_bytecode=True;sys.path.insert(0,str(bundle/'src'))
 from nana_core.life.application import LifeApplication
 from nana_core.life.portable_runtime import owner_alive,status
 from nana_core.life.live_api.supervisor import existing_identity
 from nana_core.presence.authority import VirtualClock
 assert not owner_alive(status(home/'subject/self.db'))
 before=existing_identity(home)
 with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
  high=db.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
  counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identities','cognitive_requests','subject_cycles','actions')}
 assert counts['identities']==1 and counts['cognitive_requests']==1 and counts['actions']==0
 with LifeApplication(home,clock=VirtualClock(high)) as app:
  app.pause();assert app.runtime.identity_id==before[0]
  assert all(app.runtime.store.db.execute('SELECT count(*) FROM '+t).fetchone()[0]==n for t,n in counts.items())
 assert existing_identity(home)==before
 result={'source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'same_subject_and_lineage':True,'same_counts':counts,'additional_calls_cycles_actions':0,'startup_option_omitted':True}
else:
 stages=[]
 for name,target in [('rollback',a.previous_bundle.resolve()),('return',bundle)]:
  output=a.output.with_name(a.output.stem+'-'+name+'.json')
  subprocess.run([str(target/'.venv/bin/python'),'-I','-B',str(Path(__file__).resolve()),'--single','--bundle',str(target),'--work',str(home),'--prior',str(a.prior),'--output',str(output)],check=True,timeout=60)
  stages.append(json.loads(output.read_text()))
 result={'execution':'ACTUAL_STOPPED_INSTALLED_HOST_OPTION_ENABLE_THEN_DISABLE_OLD_READER_RETURN','stages':stages,'database_rollback':False,'production_changed':False,'real_provider_calls':0,'scope':'STOPPED_SYNTHETIC_STARTUP_STORE_AFTER_SOURCE_WITHDRAWAL_NO_ACTIVE_PLAN_HOT_SWITCH'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
