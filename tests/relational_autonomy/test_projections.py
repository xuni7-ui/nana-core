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


def test_own_choices_copies_and_subject_narrative_cannot_self_certify(tmp_path):
 from nana_core.continuity.subject import PreferenceSignal
 with fresh(tmp_path/'self.db') as r:
  bootstrap(r)
  original=signal(r,'external','personality.relational_accommodation','PERSONALITY_TENDENCY')
  source=r.store.one('subject_events',original.event_id)['memory_id']
  # Repeated derived descriptions of one root, including own words, are not
  # independent occurrences even if they have different external source keys.
  for i in range(5):
   r.subject.run(event(r,'copied'+str(i),kind='OUTCOME',origin='ENVIRONMENT',source_memory_ids=(source,),preference_signal=PreferenceSignal(kind='PERSONALITY_TENDENCY',topic='personality.relational_accommodation',direction='SUPPORT',interpretation='Repeated interpretation of the same root')))
  view=personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',))
  f=next(x for x in view.facets if x.name=='relational_accommodation')
  assert f.independent_support_count==1 and f.basis=='BOOTSTRAP'
  rev=r.subject.revision
  for _ in range(5):assert not self_narrative(r.store,scope='lab',privacy_classes=('PERSONAL',)).entries
  assert r.subject.revision==rev
