"""Stopped owned DEV only; explicit evidence counts, never roll back a Store."""
import argparse,json,sqlite3,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--previous-bundle',type=Path);p.add_argument('--work',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--single',action='store_true');a=p.parse_args()
assert __debug__ and not a.output.exists();bundle=a.bundle.resolve();home=a.work.resolve();prior=json.loads(a.prior.read_text())
assert prior['scope']=='ACTUAL_INSTALLED_CORE_OWNED_DEV_SYNTHETIC_HTTP' and prior['disable_restart'] and prior['source_withdrawal_closes_current_without_old_fallback']
assert 'provider_background_cognition' not in json.loads((home/'life.json').read_text())
if a.single:
 assert Path(sys.prefix).resolve()==bundle/'.venv';sys.dont_write_bytecode=True;sys.path.insert(0,str(bundle/'src'))
 from nana_core.life.application import LifeApplication
 from nana_core.life.portable_runtime import owner_alive,status
 from nana_core.life.live_api.supervisor import existing_identity
 from nana_core.presence.authority import VirtualClock
 from nana_core.continuity.autonomy.private_intent import candidates
 assert not owner_alive(status(home/'subject/self.db'));before=existing_identity(home)
 assert before[:2]==(prior['identity_id'],prior['lineage_binding']) and before[2]==0
 with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
  high=db.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
  counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('identities','cognitive_requests','subject_cycles','actions')}
  assert not db.execute("SELECT 1 FROM runtime_queue WHERE state IN ('READY','DEFERRED','PROCESSING')").fetchone()
 assert counts==prior['store_counts']
 assert counts['identities']==1 and counts['cognitive_requests']==8 and counts['actions']==0
 with LifeApplication(home,clock=VirtualClock(high)) as app:
  app.pause();assert app.runtime.identity_id==before[0] and not candidates(app.runtime.store,'project-work',('PROJECT','PERSONAL'))
  assert all(app.runtime.store.db.execute('SELECT count(*) FROM '+t).fetchone()[0]==n for t,n in counts.items())
 assert existing_identity(home)==before
 for name,module in sys.modules.items():
  if name=='nana_core' or name.startswith('nana_core.'):assert Path(module.__file__).resolve().is_relative_to(bundle/'src'),name
 result={'source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit'],'same_identity_and_lineage':True,'counts':counts,'additional_calls_cycles_actions':0,'withdrawn_tendency_not_revived':True,'all_core_imports_from_target':True}
else:
 stages=[]
 for name,target in [('rollback',a.previous_bundle.resolve()),('return',bundle)]:
  output=a.output.with_name(a.output.stem+'-'+name+'.json')
  subprocess.run([str(target/'.venv/bin/python'),'-I','-B',str(Path(__file__).resolve()),'--single','--bundle',str(target),'--work',str(home),'--prior',str(a.prior),'--output',str(output)],check=True,timeout=60)
  stages.append(json.loads(output.read_text()))
 result={'scope':'STOPPED_OWNED_DEV_AFTER_SOURCE_WITHDRAWAL_NO_PENDING_QUEUE_NO_ACTIVE_PLAN','stages':stages,'database_rollback':False,'production_changed':False,'real_provider_calls':0}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
