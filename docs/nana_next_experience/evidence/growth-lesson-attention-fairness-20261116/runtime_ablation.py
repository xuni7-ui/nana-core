"""Fixed original selector vs distinct-method opportunity, same original G/C."""
import ast,contextlib,io,json,statistics,subprocess,time
from pathlib import Path
from unittest.mock import patch
from nana_core.continuity.subject import growth_life
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.cognition import CognitiveProposal
from nana_core.continuity.open_agency.fixtures import numeric_learning,language_learning
from nana_core.continuity.open_agency.learning import LearningCase
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.world_loop.learning import EpisodeLearning
from nana_core.continuity.world_loop.cognition import StructuredProposal
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.reference import context_policy
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.records import RecordService
from nana_core.presence.authority import VirtualClock
from nana_core.presence.contracts import SECOND
from tools.nana_vision_first.demo import source,cue,post,advance
from tests.person_self.test_growth_inner_choice import grown
from tests.person_self.test_private_method_continuation import bind
base='089256932c414bb5ab6acafdf23801ab67d1e295'
raw=subprocess.check_output(['git','show',base+':src/nana_core/continuity/subject/growth_life.py'],text=True)
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='opportunities');ns=dict(vars(growth_life));exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed-original-'+base+'>','exec'),ns)
old=ns['opportunities'];new=growth_life.opportunities
root=Path('/tmp/nana-growth-lesson-ablation-pruned');root.mkdir(exist_ok=False);outputs=[];profile=[]
for mode,selector in [('original',old),('distinct_lesson',new)]:
 clock=VirtualClock();seen=[];language_id=None
 def propose(request):
  package=json.loads(request.context_json);identity=package['manifest'];view=next(json.loads(b['data_json']) for b in package['blocks'] if b['kind']=='GROWTH_CHANGE');use=view['lesson_id']==language_id;seen.append(use)
  return StructuredProposal(interpretation='SYNTHETIC existing C considers actual checked capability',subject_cognition=CognitiveProposal(identity_id=identity['identity_id'],identity_revision=identity['identity_revision'],interpretation='SYNTHETIC choose own wordplay question' if use else 'SYNTHETIC leave numeric check alone',preferred_behavior='REFLECT' if use else 'WATCH',proposed_operations=('DRAFT',) if use else ('WAIT',),private_question={'topic':'own-language-play','question':'SYNTHETIC Could this checked text method support my own wordplay?'} if use else None))
 with grown(root/mode,clock) as (r,first,origin,reuse,math_id),provider_harness(proposer=propose) as (transport,state):
  r.work.configure_open_learning((numeric_learning(),language_learning()));mid=cue(r,'language-gap',ConcernCue(cue_kind='DISCOVERY',motivation_source='CURIOSITY',topic_key='own-language-gap',program_id='learn.language',possible_behaviors=('LEARN',)));post(r,'language-study',(mid,),task_class='language');advance(r,clock,30)
  jobs=[row for row in r.store.all('jobs') if row['work_kind']=='LEARNING' and row['state']=='DONE'];assert len(jobs)==2
  language_id=next(RecordService(r.store).read(row['record_id'])['payload']['lesson_id'] for row in jobs if RecordService(r.store).read(row['record_id'])['payload']['lesson_id']!=math_id)
  review=EpisodeLearning(r.store,r.authority,scopes=('world',),privacy_classes=('PUBLIC',))
  def check(key,lesson,case):
   mid=source(r,key,{'strategy_episode':{'episode_key':key,'lesson_id':lesson,'case':case.model_dump(mode='json')}},kind='SYSTEM_VERIFICATION');aid=review.assess(lesson,mid,authority=r.authority);assert growth_life.project(r.store,aid,scope='world',privacy_classes=('PUBLIC',))
  check('language-unseen',language_id,LearningCase(case_id='language-unseen',context='own-wordplay',data='Ｓky\tblue',expected=['Sky','blue']))
  for i in range(32):
   clock.advance(SECOND);r.lease.heartbeat();check('numeric-unseen-'+str(i),math_id,LearningCase(case_id='numeric-unseen-'+str(i),context='mathematical-check-'+str(i),data=[100+i,.25],expected=100.25+i))
  if mode=='distinct_lesson':
   read=MemoryService.read;writes=r.store.db.total_changes;model_rows=len(r.store.all('cognitive_requests'))
   for _ in range(5):
    for label,fn in [('original',old),('distinct_lesson',new)]:
     reads=[0];sql=[0]
     def measured(self,*args,**kwargs):reads[0]+=1;return read(self,*args,**kwargs)
     r.store.db.set_trace_callback(lambda _:sql.__setitem__(0,sql[0]+1));start=time.perf_counter();cpu=time.process_time()
     try:
      with patch.object(MemoryService,'read',measured):values=fn(r.store,scope='world',privacy_classes=('PUBLIC',))
     finally:r.store.db.set_trace_callback(None)
     profile.append({'mode':label,'wall_ms':(time.perf_counter()-start)*1000,'cpu_ms':(time.process_time()-cpu)*1000,'memory_reads':reads[0],'sql_statements':sql[0],'different_method_visible':language_id in {v.lesson_id for v in values}})
   assert r.store.db.total_changes==writes and len(r.store.all('cognitive_requests'))==model_rows
  bind(r,transport,context_policy());before={t:len(r.store.all(t)) for t in ('goals','actions','grants')};clock.advance(3*SECOND);r.lease.heartbeat()
  start=time.perf_counter();cpu=time.process_time()
  with patch.object(growth_life,'opportunities',selector):
   r.refresh_attention()
   for _ in range(20):clock.advance(r.config.cognition_cooldown_us+SECOND);r.lease.heartbeat();r.step()
  elapsed=(time.perf_counter()-start)*1000;used=(time.process_time()-cpu)*1000
  own=[v for _,v in candidates(r.store,'world',('PUBLIC','PROJECT','PERSONAL')) if v.category=='PRIVATE_QUESTION' and v.topic=='own-language-play'];assert before=={t:len(r.store.all(t)) for t in before}
  requests=r.store.all('cognitive_requests')
  outputs.append({'mode':mode,'source_newer_checks':32,'g_learning_jobs':2,'self_calls':state['calls'],'different_method_considered':any(seen),'own_questions':len(own),'input_bytes':[row['input_bytes'] for row in requests],'budgets':[RecordService(r.store).read(row['record_id'])['payload']['request']['budget'] for row in requests],'runtime_wall_ms':elapsed,'runtime_cpu_ms':used,'new_actions_goals_grants':False,'real_provider_calls':0})
assert outputs[0]['own_questions']==0 and outputs[1]['own_questions']==1
print(json.dumps({'base':base,'scope':'CONTROLLED_ORIGINAL_G_D_C_NOT_REAL_MODEL_LONGTERM','outputs':outputs,'same_store_read_cost_samples':profile,'profile_writes':0,'profile_model_calls':0,'bytes_are_provider_tokens':False},indent=2))
