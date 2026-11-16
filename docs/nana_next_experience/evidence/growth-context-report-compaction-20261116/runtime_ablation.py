"""Exact fixed literal assembler vs report compaction through original C."""
import ast,json,subprocess,sys,time
from pathlib import Path
from unittest.mock import patch
from nana_core.continuity import context as context_module
from nana_core.continuity.context import ContextAssembler
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.open_agency.fixtures import numeric_learning
from nana_core.continuity.subject import growth_life
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import source
from tests.person_self.test_growth_inner_choice import grown
from tests.person_self.test_private_method_continuation import bind
BASE='f419c01'
text=subprocess.check_output(['git','show',BASE+':src/nana_core/continuity/context.py'],text=True)
cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='ContextAssembler')
fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='assemble');ns=dict(vars(context_module))
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<fixed-'+BASE+'-assemble>','exec'),ns)
literal=ns['assemble'];current=ContextAssembler.assemble
root=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/nana-growth-report-ablation');root.mkdir(exist_ok=False)
outputs=[]
for mode,assemble in [('literal',literal),('compacted',current)]:
 clock=VirtualClock();received=[];mids=[]
 def propose(request):
  data=json.loads(request.context_json);received.append(request)
  assert any(b['kind']=='GROWTH_CHANGE' for b in data['blocks'])
  return StructuredProposal(interpretation='SYNTHETIC verified growth can inform own choice',subject_cognition=CognitiveProposal(
   identity_id=data['manifest']['identity_id'],identity_revision=data['manifest']['identity_revision'],
   interpretation='SYNTHETIC I choose an own question after this checked method',preferred_behavior='REFLECT',proposed_operations=('DRAFT',),
   private_question={'topic':'own-compact-growth','question':'SYNTHETIC Could this verified method help an own creative experiment?'}))
 with grown(root/mode,clock) as (r,view,origin,reuse,lesson),provider_harness(proposer=propose) as (transport,state):
  review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
  for i in range(32):
   mid=source(r,'repeat-report-'+str(i),{'strategy_episode':{'episode_key':'repeat-report-'+str(i),'lesson_id':lesson,
     'case':numeric_learning().practice[0].model_dump(mode='json')}},kind='SYSTEM_VERIFICATION')
   review.assess(lesson,mid,authority=r.authority);mids.append(mid)
  before={t:len(r.store.all(t)) for t in ('actions','goals','grants')}
  bind(r,transport,context_policy());clock.advance(3*SECOND);r.lease.heartbeat();r.refresh_attention()
  start=time.perf_counter();cpu=time.process_time()
  with patch.object(ContextAssembler,'assemble',assemble):
   for _ in range(12):r.step()
   for _ in range(3):r.refresh_attention();r.step()
  elapsed=(time.perf_counter()-start)*1000;used=(time.process_time()-cpu)*1000
  assert state['calls']==1 and len(received)==1
  own=[v for _,v in candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL')) if v.topic=='own-compact-growth']
  assert len(own)==1 and before=={t:len(r.store.all(t)) for t in before}
  req=received[0];pkg=json.loads(req.context_json)
  blocks=[b for b in pkg['blocks'] if b['kind']=='MEMORY' and set(b['source_memory_ids'])&set(mids)]
  assert len(blocks)==(32 if mode=='literal' else 1)
  assert set(mids)<={mid for b in blocks for mid in b['source_memory_ids']}
  row=r.store.one('cognitive_requests',req.request_id)
  assert set(mids)<=set(RecordService(r.store).support(row['record_id']))
  outputs.append({'mode':mode,'self_calls':state['calls'],'own_questions':len(own),'report_bodies':len(blocks),
    'all_32_source_refs_retained':True,'context_json_bytes':len(req.context_json.encode()),'input_bytes':row['input_bytes'],
    'reserved_bytes':row['reserved_bytes'],'budget':RecordService(r.store).read(row['record_id'])['payload']['request']['budget'],
    'runtime_wall_ms':elapsed,'runtime_cpu_ms':used,'new_goals_actions_grants':False,'real_provider_calls':0})
print(json.dumps({'scope':'CONTROLLED_C_MEMORY_REQUEST_ABLATION_NOT_REAL_PROVIDER_TOKENS',
 'base':subprocess.check_output(['git','rev-parse',BASE],text=True).strip(),'outputs':outputs,
 'input_byte_reduction':outputs[0]['input_bytes']-outputs[1]['input_bytes'],
 'ratio_reduction':1-outputs[1]['input_bytes']/outputs[0]['input_bytes']},indent=2))
