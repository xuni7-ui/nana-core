"""Actual tracked local process crash checkpoints, synthetic Store/clock only."""
import json,signal,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relational_autonomy.fixtures import fresh,bootstrap,signal as observed,event
from relational_autonomy.test_tradeoff import request
from nana_core.presence.contracts import HOUR
from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
from nana_core.continuity.relational.bootstrap import anchor_view
from nana_core.continuity.relational.projections import self_narrative
from nana_core.continuity.memory import MemoryService
from nana_core.storage.sqlite_store import Transaction

path,marker,cut=sys.argv[1:]
with fresh(Path(path)) as r:
 service,authority=bootstrap(r,relational_accommodation='HIGH')
 report={'identity_id':r.store.identity['identity_id'],'epoch':r.lease.epoch,'config':r.config.model_dump(mode='json')}
 def pause():
  report['clock_us']=r.clock.utc_now_us()
  temp=Path(marker).with_suffix('.partial');temp.write_text(json.dumps(report));os.replace(temp,marker)
  while True:signal.pause()
 if cut=='C1':pause()
 if cut=='C5':
  old=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',))
  service.install(old.spec.model_copy(update={'revision':2,'entity_id':'friend-person','role_label':'companion-like'}),authority);pause()
 if cut in ('C4','C6'):
  for i in range(2):c=observed(r,'trait'+str(i),'personality.relational_accommodation','PERSONALITY_TENDENCY')
  row=r.store.one('subject_events',c.event_id)
  report['event']=r.subject.records.read(row['record_id'])['payload']['input']
  if cut=='C6':
   assert self_narrative(r.store,scope='lab',privacy_classes=('PERSONAL',)).entries
   first=r.store.db.execute("SELECT memory_id FROM subject_events WHERE source_key='synthetic.relational.trait0'").fetchone()[0]
   MemoryService(r.store,r.authority).forget(first,r.authority)
  pause()
 c=request(r,review_at_us=r.clock.utc_now_us()+24*HOUR);report['cycle_id']=c.cycle_id
 if cut=='C2':pause()
 s=VoluntaryAccommodationService(r.store,r.authority);cid=s.materialize(c.cycle_id,r.authority);report['commitment_id']=cid
 for i in range(24):r.clock.source.advance(HOUR);r.lease.heartbeat(force=True)
 review=event(r,'review',kind='WAKE',origin='SELF_WAKE',text=None,task_class='relational.accommodation.review',commitment_check_id=cid)
 report['event']=review.model_dump(mode='json')
 if cut=='C3_BEFORE':
  original=Transaction.put
  def put(tx,table,row):
   result=original(tx,table,row)
   if table=='subject_cycles':pause()
   return result
  Transaction.put=put
 reviewed=r.subject.run(review);report['review_cycle_id']=reviewed.cycle_id
 if cut=='C3_AFTER':pause()
 raise AssertionError('unknown checkpoint')
