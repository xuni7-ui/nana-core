"""Inspect only the existing stopped DEV; never tick or execute pending work."""
import argparse,json,sqlite3,sys,hashlib,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.dont_write_bytecode=True;sys.path.insert(0,str(a.bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.life.live_api.supervisor import existing_identity
from nana_core.presence.authority import VirtualClock
from nana_core.life.portable_runtime import owner_alive,status
from nana_core.continuity.autonomy.private_intent import candidates,eligible_content
from nana_core.continuity.subject.context_fit import depth_boundary
from nana_core.continuity.retrieval_growth import qualified_method
from nana_core.contracts import CoreError
home=Path('/tmp/pd277/life');gateway=json.loads(Path('/workspace/nana-277-second-gateway.json').read_text());setup=json.loads(Path('/workspace/nana-277-second-setup.json').read_text());private_id=setup['result']['private_intent']['intent_id'];assert not owner_alive(status(home/'subject/self.db'));assert existing_identity(home)[:2]==(gateway['subject_id'],gateway['lineage_binding'])
with sqlite3.connect((home/'subject/self.db').as_uri()+'?mode=ro',uri=True) as db:high=db.execute('select max(clock_high_water_us) from runtime_lease').fetchone()[0]
with LifeApplication(home,clock=VirtualClock(max(time.time_ns()//1000,high))) as app:
 app.pause();r=app.runtime;s=r.store;private=[(rid,v) for rid,v in candidates(s,'project-work',('PUBLIC','PROJECT')) if v.intent_id==private_id];assert len(private)==1;rid,v=private[0];assert rid==setup['result']['private_intent']['record_id'] and v.disclosure_policy=='PRIVATE_FOR_NOW'
 try:eligible_content(s,private_id,scope='project-work',privacy_classes=('PUBLIC','PROJECT'))
 except CoreError as exc:assert exc.code=='PRIVATE_INTENT_WITHHELD'
 else:raise AssertionError('PRIVATE_CONTENT_MUST_REMAIN_WITHHELD')
 assert depth_boundary(s,'project-user','project-work','creative-note',r.config.privacy_classes)[0]
 assert not depth_boundary(s,'project-user','project-work','creative-note',r.config.privacy_classes,purpose='COGNITION')[0]
 assert qualified_method(s,r.authority,'project-user','project-work',('PROJECT',)) is None
 counts={table:len(s.all(table)) for table in ('identities','subject_cycles','cognitive_requests','actions','goals')};assert counts['identities']==1 and counts['actions']==counts['goals']==0 and counts['cognitive_requests']==7
 report={'identity_id':r.identity_id,'lineage_binding':gateway['lineage_binding'],'private_record_id':rid,'private_intent_id':private_id,'private_content_sha256':hashlib.sha256(v.content_summary.encode()).hexdigest(),'private_content_withheld':True,'expression_boundary_preserved_cognition_still_allowed':True,'withdrawn_learning_method_still_fenced':True,'counts':counts,'clock_us':r.clock.utc_now_us()}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
