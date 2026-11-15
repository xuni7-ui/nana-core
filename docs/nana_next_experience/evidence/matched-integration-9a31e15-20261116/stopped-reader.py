"""Explicit DEV stopped-reader compatibility, no model or platform operations."""
import argparse,json,hashlib,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--home',type=Path,required=True);a=p.parse_args()
sys.dont_write_bytecode=True;sys.path.insert(0,str(a.bundle/'src'))
from nana_core.life.application import LifeApplication
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.memory import MemoryService
from nana_core.contracts import CoreError
from nana_core.life.live_api.supervisor import existing_identity
metadata=json.loads((a.home.parent/'seed.json').read_text())
with LifeApplication(a.home) as app:
 app.pause();store=app.runtime.store
 assert app.runtime.identity_id==metadata['identity']
 row=store.one('memories',metadata['source']);assert row['lifecycle']=='DELETED'
 try:MemoryService(store).read(metadata['source'])
 except CoreError as exc:assert exc.code=='MEMORY_UNAVAILABLE'
 else:raise AssertionError('WITHDRAWN_SOURCE_REAPPEARED')
 private=[(rid,item) for rid,item in candidates(store,'project-work',('PROJECT','PERSONAL')) if item.category=='PRIVATE_TENDENCY']
 assert len(private)==1
 rid,item=private[0]
 _,lineage,_=existing_identity(a.home)
 value={'identity':app.runtime.identity_id,'lineage':lineage,'source_state':row['lifecycle'],
        'private_record':rid,'private_revision':item.revision,'private_state':item.activity_state,
        'private_text_sha256':hashlib.sha256(item.content_summary.encode()).hexdigest(),
        'counts':{table:len(store.all(table)) for table in ('subject_cycles','cognitive_requests','actions','jobs')}}
 print(json.dumps(value))
