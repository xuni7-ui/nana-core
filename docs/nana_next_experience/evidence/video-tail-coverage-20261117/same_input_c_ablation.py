import ast,json,re,hashlib,time,subprocess
from pathlib import Path
from nana_core.storage import canonical
from nana_core.continuity.world_loop import perception as module
from nana_core.continuity.world_loop.perception import MediaDecoder,PerceptionService,PublicMediaSource
from nana_core.continuity.world_loop.semantic_harness import semantic_harness
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.cognition import AnalyticalFixturePort
from nana_core.continuity.subject import SubjectInput
from nana_core.continuity.subject.opportunities import ConcernCue
from nana_core.continuity.autonomy.private_intent import candidates
from nana_core.continuity.records import RecordService
from tools.nana_vision_first.demo import cue
from tests.world_loop.helpers import fresh,providers,policy
from tests.h1_semantics.test_grounding import setup
root=Path('/workspace/nana-next-refinement-work')
log=Path('/workspace/nana-video-tail-original.txt').read_text();p=re.search(r"tmp_path = PosixPath\('([^']+)'\)",log).group(1)
assert p.startswith('/dev/shm/pytest-of-agent/')
path=Path(p)/'short-video-long-audio.mkv';data=path.read_bytes()
source=subprocess.check_output(['git','show','631444986043bb3153a772983a20090126daee91:src/nana_core/continuity/world_loop/perception.py'],cwd=root,text=True)
cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='MediaDecoder');method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='decode');ns=dict(vars(module));exec(compile(ast.Module(body=[method],type_ignores=[]),'<fixed-63144498-decode>','exec'),ns)
class OriginalDecoder(MediaDecoder):decode=ns['decode']
run=MediaDecoder._run;calls=[]
def observed_run(self,args,**kwargs):
 output=run(self,args,**kwargs);calls.append({'tool':args[0],'output_bytes':len(output)});return output
MediaDecoder._run=observed_run
results=[]
try:
 for label,decoder in [('old',OriginalDecoder()),('new',MediaDecoder())]:
  begin=len(calls);wall=time.perf_counter_ns();cpu=time.process_time_ns()
  with fresh(Path('/dev/shm/nana-video-tail-ablation-c-2')/label/'subject.db') as r,semantic_harness() as (t,state):
   now=r.clock.utc_now_us();source=PublicMediaSource(source_id='synthetic-video-tail-ablation',modality='VIDEO',origin='SYNTHETIC',event_time_us=now,observed_time_us=now)
   mid,_=PerceptionService(r.store,providers(),policy(),decoder=decoder).ingest(data,source,entity_id='observer',scope='world')
   source_body=MemoryService(r.store).read(mid)['text'];decoded=json.loads(source_body)['decoded'];service=setup(r,t);cid=service.prepare('tail',mid,data)
   req=service.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request'];assert service.execute(cid)['state']=='PROPOSED';ground=service.ground(cid,entity_id='device');row=r.store.one('cognitive_requests',cid)
   cmid=cue(r,'tail-uncertainty',ConcernCue(cue_kind='DISCOVERY',motivation_source='CURIOSITY',topic_key='own-tail-gap',possible_behaviors=('WATCH','REFLECT')),parents=(mid,))
   class ConsiderCoverage:
    descriptor='SYNTHETIC_COVERAGE_CONSUMER_NOT_GENERAL_VIDEO_UNDERSTANDING'
    calls=0
    def propose(self,request):
     self.calls+=1
     values=[json.loads(json.loads(b['data_json'])['text']) for b in json.loads(request.context_json)['blocks'] if b['kind']=='MEMORY']
     meta=next(v['decoded'] for v in values if 'decoded' in v and v['decoded']['modality']=='VIDEO')
     gap=meta['frames'][-1]['source_interval_s'][1]<meta['duration_s']
     choice=json.loads(AnalyticalFixturePort().propose(request))
     choice.update(preferred_behavior='REFLECT' if gap else 'WATCH',proposed_operations=['DRAFT'])
     if gap:choice['private_question']={'topic':'own-tail-gap','question':'SYNTHETIC What is unknown about the unobserved tail?'}
     return json.dumps(choice)
   model=ConsiderCoverage();event=SubjectInput(source_key='synthetic.tail-coverage-consideration',kind='WAKE',origin='SELF_WAKE',entity_id='observer',scope='world',privacy_class='PUBLIC',observed_at_us=now,source_memory_ids=(cmid,))
   decision=r.subject.cognize(event,model=model,authority=r.authority,policy=policy())
   own=[(rid,value) for rid,value in candidates(r.store,'world',('PUBLIC',)) if value.category=='PRIVATE_QUESTION']
   assert len(own)==(1 if label=='new' else 0) and model.calls==1
   if own:assert RecordService(r.store).current_support(own[0][0])
   MemoryService(r.store,r.authority).forget(mid,r.authority)
   if own:assert not RecordService(r.store).current_support(own[0][0])
   assert not r.store.all('actions') and not r.store.all('goals') and not r.store.all('grants')
   results.append({'variant':label,'c_behavior':decision.intention.behavior,'private_questions':len(own),'c_fixture_calls':model.calls,'source_withdrawal_invalidates_question':True if own else None,'source_last_interval':decoded['frames'][-1]['source_interval_s'],'duration_s':decoded['duration_s'],'unobserved_gaps':ground['unobserved_gaps'],'covered_intervals':ground['covered_intervals'],'budget':req['budget'],'input_wire_bytes':row['input_bytes'],'output_wire_bytes':row['output_bytes'],'source_memory_text_bytes':len(source_body.encode()),'provider_fixture_calls':state['calls'],'subprocesses':calls[begin:],'wall_ms':(time.perf_counter_ns()-wall)/1e6,'parent_cpu_ms':(time.process_time_ns()-cpu)/1e6})
finally:MediaDecoder._run=run
assert results[0]['unobserved_gaps']==[] and results[1]['unobserved_gaps']==[[1.,3.]]
assert results[0]['budget']==results[1]['budget']
print(json.dumps({'old_source':'631444986043bb3153a772983a20090126daee91','input_sha256':hashlib.sha256(data).hexdigest(),'input_bytes':len(data),'results':results,'real_provider_calls':0,'paid_cost':0,'note':'Actual original sandbox/codec and HTTP fixture; fixture token numbers are not real Provider Token.'},indent=2))
