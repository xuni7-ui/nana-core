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


def test_truncated_explanation_cannot_declassify_hidden_personality_support(tmp_path,monkeypatch):
 from nana_core.continuity.subject import SubjectLoop
 import nana_core.continuity.memory as memory_module
 from itertools import count
 with fresh(tmp_path/'self.db') as r:
  bootstrap(r)
  for i in range(17):signal(r,'public-trait'+str(i),'personality.relational_accommodation','PERSONALITY_TENDENCY')
  # Deterministic adversarial IDs place this genuine new source beyond the
  # bounded explanatory reference subset; no expected judgment enters policy.
  ids=count();monkeypatch.setattr(memory_module,'uid',lambda:'zz-synthetic-private-'+str(next(ids)))
  wide=SubjectLoop(r.store,scopes=('lab',),privacy_classes=('PERSONAL','SECRET'))
  from nana_core.continuity.subject import PreferenceSignal
  wide.run(event(r,'hidden-trait',kind='OUTCOME',origin='ENVIRONMENT',privacy_class='SECRET',preference_signal=PreferenceSignal(kind='PERSONALITY_TENDENCY',topic='personality.relational_accommodation',direction='SUPPORT',interpretation='A fictional secret observation')))
  hidden=r.store.db.execute("SELECT payload_artifact_id FROM memories WHERE source_evidence_id LIKE 'zz-synthetic-private-%'").fetchall()
  hidden_ids={x[0] for x in hidden};original=r.store.artifact
  def guarded(aid):
   assert aid not in hidden_ids,'projector read SECRET body'
   return original(aid)
  r.store.artifact=guarded
  view=personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',))
  facet=next(x for x in view.facets if x.name=='relational_accommodation')
  assert facet.independent_support_count<=17,'private source included in unprivileged aggregate'


import pytest
@pytest.mark.parametrize('version',(7,9))
def test_existing_development_schema_privacy_closure_uses_all_roots(tmp_path,monkeypatch,version):
 from types import SimpleNamespace
 from itertools import count
 from nana_core.actions import OperatorAuthority
 from nana_core.continuity import ContinuityStore,IdentityService
 from nana_core.continuity.subject import SubjectLoop,PreferenceSignal
 from nana_core.presence.authority import VirtualClock
 import nana_core.continuity.memory as memory_module
 with ContinuityStore(tmp_path/'self.db',VirtualClock(),schema_target=version) as store:
  authority=OperatorAuthority();IdentityService(store,authority);MemoryService(store).entity('anchor-person','PERSON')
  r=SimpleNamespace(store=store,clock=store.clock,subject=SubjectLoop(store,scopes=('lab',)))
  for i in range(17):signal(r,'public'+str(i),'social_exploration')
  ids=count();monkeypatch.setattr(memory_module,'uid',lambda:'zz-synthetic-hidden-'+str(next(ids)))
  wide=SubjectLoop(store,scopes=('lab',),privacy_classes=('PERSONAL','SECRET'))
  wide.run(event(r,'private',kind='OUTCOME',origin='ENVIRONMENT',privacy_class='SECRET',preference_signal=PreferenceSignal(topic='social_exploration',direction='SUPPORT',interpretation='Fictional hidden observation')))
  hidden={x[0] for x in store.db.execute("SELECT payload_artifact_id FROM memories WHERE source_evidence_id LIKE 'zz-synthetic-hidden-%'")};original=store.artifact
  def guard(aid):
   assert aid not in hidden,'SECRET body read via bounded assertion summary'
   return original(aid)
  store.artifact=guard
  view=project_self(store,entity_id='anchor-person',scope='lab',privacy_classes=('PERSONAL',))
  assert not view[1].stable_preferences
  assert store.db.execute('PRAGMA user_version').fetchone()[0]==version
