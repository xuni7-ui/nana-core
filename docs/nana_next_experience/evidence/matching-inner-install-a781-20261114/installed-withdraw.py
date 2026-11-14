"""Validate active private-state return on the same installed owned DEV, then erase."""
import argparse,json,sys,sqlite3,runpy
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--home',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--return-report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert __debug__ and not a.output.exists()
sys.dont_write_bytecode=True;bundle=a.bundle.resolve();home=a.home.resolve();prior=json.loads(a.prior.read_text());returned=json.loads(a.return_report.read_text())
assert Path(sys.prefix).resolve()==bundle/'.venv'
assert prior['active_tendency_and_question_retained'] and not prior['withdrawal_closes_private_projection']
assert json.loads((home/'nana-space-development.json').read_text())=={'realm':'OWNED_DEVELOPMENT_ONLY','identity_id':prior['subject_id']}
source=json.loads((bundle/'runtime.json').read_text())['source_commit'];assert source==prior['source_commit']
assert returned['stages'][-1]['source_commit']==source and all(v['same_subject_and_lineage'] and v['additional_calls_cycles_actions']==0 for v in returned['stages'])
runpy.run_path(str(bundle/'bootstrap.py'),run_name='verify_installed')['verify'](bundle)
sys.path.insert(0,str(bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.life.portable_runtime import owner_alive,status
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.autonomy.private_intent import candidates
assert not owner_alive(status(home/'subject/self.db'))
before=existing_identity(home);assert before[:2]==(prior['subject_id'],prior['lineage_binding'])
with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:high=db.execute('SELECT coalesce(max(clock_high_water_us),0) FROM runtime_lease').fetchone()[0]
with LifeApplication(home,clock=VirtualClock(high)) as app:
 app.pause();store=app.runtime.store;items=candidates(store,'project-work',('PROJECT','PERSONAL'))
 assert {v.category for _,v in items}=={'PRIVATE_TENDENCY','PRIVATE_QUESTION'}
 assert all(prior['root_source_memory_id'] in v.source_memory_ids for _,v in items)
 assert len(store.all('identities'))==1 and len(store.all('cognitive_requests'))==1 and not store.all('actions')
 old_index=store.db.execute("SELECT sql FROM sqlite_master WHERE name='private_intent_topic_lookup_v1'").fetchone()[0]
 assert 'PRIVATE_TENDENCY_V4' not in old_index
 app.forget(prior['root_source_memory_id'])
 assert not candidates(store,'project-work',('PROJECT','PERSONAL'))
 assert len(store.all('cognitive_requests'))==1 and not store.all('actions')
assert existing_identity(home)==before
runpy.run_path(str(bundle/'bootstrap.py'),run_name='verify_installed')['verify'](bundle)
result={'execution':'ACTUAL_INSTALLED_ACTIVE_PRIVATE_TENDENCY_OLD_BINARY_RETURN_THEN_WITHDRAWAL','source_commit':source,'single_identity_and_lineage':True,'active_v4_tendency_and_v3_question_after_old_return':True,'source_withdrawal_closes_both':True,'additional_model_calls':0,'actual_actions':0,'bundle_seal_after_all_probes':'PASS','legacy_partial_predicate_preserved':True,'return_helper_scope_label':'Historical helper label AFTER_SOURCE_WITHDRAWAL is hardcoded; this probe validates the actual active-state fixture instead. No hot-plan or production qualification.','real_model_calls':0,'physical_phone':'NOT_RUN','production_changed':False}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
