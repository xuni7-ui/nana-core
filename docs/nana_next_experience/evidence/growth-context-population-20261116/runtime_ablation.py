"""Fixed original selector vs grouped selector through the same Runtime/C/G."""
import ast,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.records import RecordService
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.subject import growth_life
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import source
from tests.person_self.test_growth_inner_choice import grown
from tests.person_self.test_private_method_continuation import bind
BASE='35740e7f2f518b9b2607bbd952759aa80683cf4c'
text=subprocess.check_output(['git','show',BASE+':src/nana_core/continuity/subject/growth_life.py'],text=True)
node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='opportunities')
ns=dict(vars(growth_life));exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed-'+BASE+'>','exec'),ns)
legacy=ns['opportunities'];current=growth_life.opportunities
root=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/nana-growth-context-ablation');root.mkdir(exist_ok=False)
outputs=[]
for mode,selector in [('original',legacy),('grouped',current)]:
 clock=VirtualClock();received=[]
 def propose(request):
  data=json.loads(request.context_json);has=any(b['kind']=='GROWTH_CHANGE' for b in data['blocks']);received.append(request.request_id)
  return StructuredProposal(interpretation='SYNTHETIC checked growth can inspire own choice',subject_cognition=CognitiveProposal(
   identity_id=data['manifest']['identity_id'],identity_revision=data['manifest']['identity_revision'],
   interpretation='SYNTHETIC I may pursue this own question without starting a task',preferred_behavior='REFLECT' if has else 'WATCH',
   proposed_operations=('DRAFT',) if has else ('READ_SOURCE',),
   private_question={'topic':'own-checked-context','question':'SYNTHETIC Could this checked method support my own playful experiment?'} if has else None))
 with grown(root/mode,clock) as (r,view,origin,reuse,lesson),provider_harness(proposer=propose) as (transport,state):
  review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
  for i in range(32):
   mid=source(r,'repeated-practice-'+str(i),{'strategy_episode':{'episode_key':'repeated-practice-'+str(i),
      'lesson_id':lesson,'case':numeric_learning().practice[0].model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
   review.assess(lesson,mid,authority=r.authority)
  before={k:len(r.store.all(k)) for k in ('goals','actions','grants')}
  bind(r,transport,context_policy());clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
  with patch.object(growth_life,'opportunities',selector):
   for _ in range(12):r.step()
   for _ in range(3):r.refresh_attention();r.step()
  own=[v for _,v in candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL')) if v.topic=='own-checked-context']
  assert before=={k:len(r.store.all(k)) for k in before}
  assert state['calls']==(1 if mode=='grouped' else 0),(mode,state)
  assert len(own)==(1 if mode=='grouped' else 0)
  calls=[dict(r.store.one('cognitive_requests',rid)) for rid in received]
  outputs.append({'mode':mode,'original_runtime_self_calls':state['calls'],'own_questions':len(own),
      'new_goals_actions_grants':False,'input_bytes':[c['input_bytes'] for c in calls],
      'reserved_bytes':[c['reserved_bytes'] for c in calls],
      'actual_request_budget':[RecordService(r.store).read(c['record_id'])['payload']['request']['budget'] for c in calls],
      'real_provider_calls':0})
print(json.dumps({'scope':'CONTROLLED_RUNTIME_ABLATION_NOT_REAL_MODEL','base':BASE,
 'same_configured_budget':outputs[1]['actual_request_budget'][0],
 'baseline_no_growth_request_allocated':not outputs[0]['actual_request_budget'],
 'baseline_uses_fixed_original_function_with_same_rebuildable_indexes':True,'outputs':outputs},indent=2))
