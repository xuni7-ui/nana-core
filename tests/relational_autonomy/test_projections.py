from nana_core.continuity.relational.projections import social_appetite,personality_tendencies,self_narrative
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.subject.projections import project_self
from .fixtures import fresh,bootstrap,signal,event


def test_anchor_ablation_and_personality_growth_counter_erasure(tmp_path):
 worlds=[]
 for has_anchor in (False,True):
  with fresh(tmp_path/str(has_anchor)/'self.db') as r:
   bootstrap(r,anchor=has_anchor)
   for i in range(2):signal(r,'social'+str(i))
   view=social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',))
   assert view.state=='SEEKING'
   state,_,_=project_self(r.store,entity_id='anchor-person',scope='lab',privacy_classes=('PERSONAL',))
   assert state.internal['social_drive']=='SEEKING'
   worlds.append((view.state,view.available,len(view.source_record_ids)))
 assert worlds[0]==worlds[1]
 with fresh(tmp_path/'growth'/'self.db') as r:
  bootstrap(r)
  signal(r,'first','personality.relational_accommodation','PERSONALITY_TENDENCY')
  one=personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',))
  assert next(f for f in one.facets if f.name=='relational_accommodation').basis=='BOOTSTRAP'
  second=signal(r,'second','personality.relational_accommodation','PERSONALITY_TENDENCY')
  view=personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',))
  assert next(f for f in view.facets if f.name=='relational_accommodation').assessment=='HIGH'
  assert self_narrative(r.store,scope='lab',privacy_classes=('PERSONAL',)).entries
  for i in range(2):signal(r,'counter'+str(i),'personality.relational_accommodation','PERSONALITY_TENDENCY','COUNTER')
  challenged=personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',))
  assert next(f for f in challenged.facets if f.name=='relational_accommodation').basis=='CONTESTED'
  rows=r.store.db.execute("SELECT memory_id FROM subject_events WHERE source_key LIKE 'synthetic.relational.%'").fetchall()
  for row in rows:
   if row[0] and r.store.one('memories',row[0])['lifecycle']!='DELETED':MemoryService(r.store,r.authority).forget(row[0],r.authority)
  rebuilt=personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',))
  assert next(f for f in rebuilt.facets if f.name=='relational_accommodation').basis=='BOOTSTRAP'
  assert not self_narrative(r.store,scope='lab',privacy_classes=('PERSONAL',)).entries
