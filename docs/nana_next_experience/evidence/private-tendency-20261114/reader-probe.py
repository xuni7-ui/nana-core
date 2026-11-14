import argparse,json,sys,sqlite3,runpy
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--home',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--installed-old',action='store_true');a=p.parse_args()
assert __debug__ and not a.output.exists()
sys.dont_write_bytecode=True;source=a.source_root.resolve();home=a.home.resolve();prior=json.loads(a.prior.read_text())
assert json.loads((home/'nana-space-development.json').read_text())=={'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':prior['identity_id']}
if a.installed_old:
 assert Path(sys.prefix).resolve()==source/'.venv'
 runpy.run_path(str(source/'bootstrap.py'),run_name='verify_old')['verify'](source)
sys.path.insert(0,str(source/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.life.portable_runtime import owner_alive,status
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.presence.authority import VirtualClock
assert not owner_alive(status(home/'subject/self.db'))
before=existing_identity(home)
assert before[0]==prior['identity_id']
with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:
 high=db.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
 original=db.execute("SELECT count(*) FROM continuity_records r JOIN artifacts a ON a.artifact_id=r.payload_artifact_id WHERE r.lifecycle='ACTIVE' AND json_extract(CAST(a.payload AS TEXT),'$.contract')='PRIVATE_TENDENCY_V4'").fetchone()[0]
 calls=db.execute('SELECT count(*) FROM cognitive_requests').fetchone()[0]
assert original==1 and calls==0
with LifeApplication(home,clock=VirtualClock(high)) as app:
 app.pause();assert app.runtime.identity_id==prior['identity_id']
 own=[v for _,v in candidates(app.runtime.store,'project-work',('PROJECT',)) if v.category=='PRIVATE_TENDENCY']
 if a.installed_old:assert not own
 else:assert len(own)==1 and own[0].content_summary==prior['private_fixture_value']
 assert 'PRIVATE_TENDENCY_CANARY' not in json.dumps(app.status())
 assert len(app.runtime.store.all('cognitive_requests'))==calls and not app.runtime.store.all('actions')
assert existing_identity(home)==before
if a.installed_old:runpy.run_path(str(source/'bootstrap.py'),run_name='verify_old')['verify'](source)
result={'source':json.loads((source/'runtime.json').read_text())['source_commit'] if a.installed_old else 'CURRENT_WORKSPACE_NOT_INSTALLED','reader':'INSTALLED_OLD' if a.installed_old else 'CURRENT_SOURCE_RETURN','single_identity_and_lineage':True,'old_unknown_contract_hidden':a.installed_old,'returned_tendency_preserved':not a.installed_old,'additional_model_calls':0,'actual_actions':0,'production_changed':False}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
