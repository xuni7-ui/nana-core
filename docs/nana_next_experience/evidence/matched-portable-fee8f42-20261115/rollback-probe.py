import argparse,json,sys,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--home',required=True);p.add_argument('--seed',action='store_true');a=p.parse_args()
bundle=Path(a.bundle).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.continuity.autonomy.private_intent import candidates
with LifeApplication(a.home) as app:
 app.pause();r=app.runtime
 if a.seed:
  from nana_core.continuity.cognition import AnalyticalFixturePort
  from nana_core.continuity.subject import SubjectInput
  class Own:
   descriptor='synthetic-rollback-retained-tendency'
   def propose(self,request):
    value=json.loads(AnalyticalFixturePort().propose(request));value['private_tendency']={'topic':'rollback-continuity','tendency':'SYNTHETIC retained private interest, no external action'}
    return json.dumps(value)
  r.subject.cognize(SubjectInput(source_key='synthetic.fee8-rollback-tendency',kind='WAKE',origin='SELF_WAKE',entity_id='project-user',scope='project-work',privacy_class='PROJECT',topic='rollback-continuity',observed_at_us=r.clock.utc_now_us()),model=Own(),authority=r.authority,policy=app.policy)
 thought=[dict(record_id=rid,intent_id=v.intent_id,revision=v.revision,state=getattr(v,'activity_state',None),content_sha256=hashlib.sha256(v.content_summary.encode()).hexdigest()) for rid,v in candidates(r.store,'project-work',('PUBLIC','PROJECT','PERSONAL'))]
 assert any(v['state']=='ACTIVE' for v in thought)
 values={table:[dict(row) for row in r.store.all(table)] for table in ('jobs','identity','surface_bindings') if table!='identity' and r.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()}
 result={'identity':r.identity_id,'thoughts':thought,'job_rows':values.get('jobs'),
  'counts':{table:len(r.store.all(table)) for table in ('subject_cycles','cognitive_requests','actions','jobs')},
  'source_commit':json.loads((bundle/'runtime.json').read_text())['source_commit']}
 print(json.dumps(result,sort_keys=True))
