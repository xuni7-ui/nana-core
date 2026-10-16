from nana_core.continuity.relational.contracts import RelationalRequest,DAY
from nana_core.continuity.relational.projections import social_appetite
from .fixtures import fresh,bootstrap,signal,event


def request(r,key='request',duration=3*DAY,entity='anchor-person',**updates):
 data=dict(request_id=key,requesting_entity=entity,operation='REFRAIN',behavior_domain='SOCIAL_NEW_CONTACTS',duration_us=duration)
 data.update(updates)
 return r.subject.run(event(r,key,entity_id=entity,relational_request=RelationalRequest(**data)))


def test_same_context_personality_relation_and_duration_change_choice(tmp_path):
 results=[]
 for name,seed in [('accommodating',{'relational_accommodation':'HIGH'}),('self-directed',{'relational_accommodation':'HIGH','self_direction_sensitivity':'HIGH'})]:
  with fresh(tmp_path/name/'self.db') as r:
   bootstrap(r,**seed)
   for i in range(2):signal(r,'social'+str(i))
   c=request(r)
   expected='ACCEPT' if name=='accommodating' else 'NEGOTIATE'
   assert c.relational_decision.response.decision==expected
   assert c.evaluation.normative=='ENDORSED' and c.relational_decision.authorship.state=='INFLUENCED'
   assert c.relational_decision.response.retained_preference=='SOCIALIZE'
   assert social_appetite(r.store,scope='lab',privacy_classes=('PERSONAL',)).state=='SEEKING'
   indefinite=request(r,'indefinite',duration=None,scope='GLOBAL')
   assert indefinite.relational_decision.response.decision=='NEGOTIATE'
   stranger=request(r,'stranger',entity='stranger-person')
   assert stranger.relational_decision.response.decision=='NEGOTIATE'
   assert not r.store.all('grants') and not r.store.all('actions')
   results.append(expected)
 assert results==['ACCEPT','NEGOTIATE']


def test_filtered_context_and_model_cannot_supply_anchor_or_choice(tmp_path):
 import json,pytest
 from pydantic import ValidationError
 from nana_core.continuity.cognition import AnalyticalFixturePort
 from nana_core.continuity.context import ContextAssembler,ContextRequest,ContextPolicy
 with fresh(tmp_path/'self.db') as r:
  bootstrap(r,relational_accommodation='HIGH')
  for i in range(2):signal(r,'social'+str(i))
  c=request(r)
  assembler=ContextAssembler(r.store,r.authority)
  q=ContextRequest(entity_id='anchor-person',scopes=('lab',),task_class='subject',task='Fictional tradeoff',max_input_tokens=64000)
  p=ContextPolicy(policy_id='local',allowed_scopes=('lab',),readable_privacy=('PERSONAL',))
  ctx=assembler.assemble(q,p)
  block=next(b for b in ctx.blocks if b.kind=='RELATIONAL_SUBJECT')
  body=json.loads(block.data_json)
  assert body['anchor']['spec']['role_label']=='sibling-like' and body['social_appetite']['state']=='SEEKING'
  assert body['historical_tradeoff_not_current_policy']['response']['decision']=='ACCEPT'
  class Forged:
   descriptor='synthetic-forged-relational'
   def propose(self,envelope):
    b=json.loads(AnalyticalFixturePort().propose(envelope));b['anchor']={};b['deference']='STRONG';b['judgment']='AGREE';return json.dumps(b)
  rev=r.subject.revision
  with pytest.raises(ValidationError):r.subject.cognize(event(r,'forged',novelty='HIGH'),model=Forged(),authority=r.authority,policy=p)
  assert r.subject.revision==rev
  remote=q.model_copy(update={'task_privacy_class':'PUBLIC','destination':'DEVELOPMENT_REMOTE'})
  filtered=assembler.assemble(remote,ContextPolicy(policy_id='public',allowed_scopes=('lab',),readable_privacy=('PUBLIC','PERSONAL','SECRET'),remote_privacy=('PUBLIC',)))
  assert 'sibling-like' not in filtered.model_dump_json()
