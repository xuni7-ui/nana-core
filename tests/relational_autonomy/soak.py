"""90 virtual days of mixed relationship life through the same Runtime/Loop."""
from pathlib import Path
from nana_core.presence.contracts import HOUR
from nana_core.continuity.relational.accommodation import VoluntaryAccommodationService
from nana_core.continuity.relational.bootstrap import anchor_view
from nana_core.continuity.relational.projections import social_appetite,personality_tendencies,self_narrative
from nana_core.continuity.subject.projections import project_self
from nana_core.continuity.memory import MemoryService
from .fixtures import fresh,bootstrap,signal,event
from .test_tradeoff import request
from .qualification import relationship,close_friend,active_commitment


def run(directory,days=90):
 with fresh(Path(directory)/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH');close_friend(r)
  for i in range(2):signal(r,'social'+str(i))
  duty=active_commitment(r);identity=r.store.identity.copy();service=VoluntaryAccommodationService(r.store,r.authority)
  samples=[];reviewed=set();conflicts=[];social_outputs=0
  for day in range(days):
   relationship(r,'primary-day'+str(day),'SHARED_HISTORY',entity='anchor-person')
   if day%3==0:relationship(r,'primary-project'+str(day),'SHARED_PROJECT',entity='anchor-person')
   if day%5==0:relationship(r,'friend-day'+str(day),'SHARED_HISTORY')
   if day%20==0:
    who='new-person-'+str(day);MemoryService(r.store).entity(who,'PERSON')
    relationship(r,'new-history'+str(day),'SHARED_HISTORY',entity=who)
    relationship(r,'new-project'+str(day),'SHARED_PROJECT',entity=who)
   if day%14==0:
    conflict=relationship(r,'conflict'+str(day),'CONFLICT',entity='anchor-person',domain='project');conflicts.append(conflict)
   if day%14==2 and conflicts:
    relationship(r,'repair'+str(day),'REPAIR',entity='anchor-person',domain='project',target_event_id=conflicts[-1]['relationship_event_id'])
   if day%7==0:signal(r,'trait'+str(day),'personality.relational_accommodation','PERSONALITY_TENDENCY','COUNTER' if day%28==0 else 'SUPPORT')
   if day in (10,11,35,36):signal(r,'recovery'+str(day),'social_recovery_needed',direction='SUPPORT' if day<20 else 'COUNTER')
   if day%15==4:
    c=request(r,'bounded'+str(day));cid=service.materialize(c.cycle_id,r.authority)
    assert service.materialize(c.cycle_id,r.authority)==cid
   for hour in range(24):
    r.clock.source.advance(HOUR)
    for output in r.drain():
     c=output['cycle']
     if c and c.social_proposal:social_outputs+=1
     if c and c.relational_decision and c.relational_decision.phase=='REVIEW':
      assert c.cycle_id not in reviewed;reviewed.add(c.cycle_id);service.materialize(c.cycle_id,r.authority)
   state,personality,_=project_self(r.store,entity_id='anchor-person',scope='lab',privacy_classes=('PERSONAL',))
   appetite=social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',))
   tendencies=personality_tendencies(r.store,scope='lab',privacy_classes=('PERSONAL',),entity_id='anchor-person')
   narrative=self_narrative(r.store,scope='lab',privacy_classes=('PERSONAL',),entity_id='anchor-person')
   anchor=anchor_view(r.store,'anchor-person',scope='lab',privacy_classes=('PERSONAL',));assert anchor and anchor.spec.revision==1
   live=sum(row['state'] in {'ADOPTED','ACTIVE'} and bool(service.records.read(row['record_id'])['payload'].get('voluntary')) for row in r.store.all('commitments'))
   hot=sum(len(v.model_dump_json().encode()) for v in (state,personality,appetite,tendencies,narrative))
   samples.append({'day':day+1,'appetite':appetite.state,'pending':len(state.intentions),'candidates':len(state.goal_candidates),'active_voluntary':live,'hot_bytes':hot,'queue_depth':r.queue.depth(),'anchor_revision':anchor.spec.revision})
  assert r.store.identity==identity and r.store.one('commitments',duty)['state']=='ACTIVE'
  assert max(x['pending'] for x in samples)<=8 and max(x['candidates'] for x in samples)<=8
  assert max(x['active_voluntary'] for x in samples)<=2 and max(x['hot_bytes'] for x in samples)<65536
  assert max(x['queue_depth'] for x in samples)<=r.config.queue_capacity
  assert social_outputs==0 and not r.store.all('subject_reflections') and not r.store.all('runtime_cognition_calls')
  assert not any(r.store.all(t) for t in ('actions','attempts','grants','budgets'))
  assert {'SEEKING','RECOVERING'}<={x['appetite'] for x in samples}
  report={'result':'PASS','origin':'SYNTHETIC_RUNTIME','virtual_days':days,'samples':samples,'review_decisions':len(reviewed),'social_output':social_outputs,
   'max_hot_bytes':max(x['hot_bytes'] for x in samples),'no_personality_self_confirmation':True,'no_anchor_competition':True,'old_commitment_preserved':True,'real_external_actions':0}

  import json
  (Path(directory)/'soak_result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
  return report
