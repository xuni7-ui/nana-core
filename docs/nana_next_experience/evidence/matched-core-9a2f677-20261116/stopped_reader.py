"""Stopped DEV owner only; do not execute pending choices or call any model."""
import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--home',type=Path,required=True);a=p.parse_args()
sys.dont_write_bytecode=True;sys.path.insert(0,str(a.bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.presence.authority import VirtualClock
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.lived_language import expression_policy
seed=json.loads((a.home.parent/'seed.json').read_text())
with LifeApplication(a.home,clock=VirtualClock(seed['clock_us'])) as app:
 app.pause();r=app.runtime;assert r.identity_id==seed['identity']
 _,lineage,_=existing_identity(a.home)
 private=[{'record_id':rid,'category':item.category,'revision':item.revision,'state':item.activity_state,
   'content_sha256':hashlib.sha256(item.content_summary.encode()).hexdigest()} for rid,item in candidates(r.store,'project-work',('PROJECT','PERSONAL'))]
 assert len(private)==1 and private[0]['category']=='PRIVATE_PLAN'
 assert r.subject.result(r.store.one('subject_cycles',seed['social_cycle'])).intention.behavior=='SOCIALIZE'
 assert seed['social_intention'] in {row['intention_id'] for row in r.subject.pending('project-work')}
 method=expression_policy(r.store,scope='project-work',privacy=('PROJECT',),mode='CASUAL')
 value={'identity':r.identity_id,'lineage':lineage,'private':private,
  'pending_social':seed['social_intention'],'lessons':[(row['lesson_id'],row['state']) for row in r.store.all('lessons')],
  'counts':{table:len(r.store.all(table)) for table in ('subject_cycles','cognitive_requests','actions','jobs','goals')},
  'method_available':method.get('lesson_id')==seed['lesson_id']}
 print(json.dumps(value))
