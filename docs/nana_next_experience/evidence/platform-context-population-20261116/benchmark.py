import ast,json,statistics,subprocess,tempfile,time,types
from pathlib import Path
import nana_core.continuity.context as context
from nana_core.continuity.memory import MemoryService
from nana_core.life.application import LifeApplication
from nana_core.presence.authority import VirtualClock
from tests.nanalink.test_platform_context_population import prepare,populate,refs

old_source=subprocess.check_output(['git','show','486ed54626b27a4f2fac10c5fca6c37075b1ebb7:src/nana_core/continuity/context.py'],text=True)
cls=next(n for n in ast.parse(old_source).body if isinstance(n,ast.ClassDef) and n.name=='ContextAssembler')
node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='assemble')
namespace=dict(vars(context));exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<exact-486-assemble>','exec'),namespace)
with tempfile.TemporaryDirectory(prefix='nana-platform-population-',dir='/tmp') as folder:
 home=Path(folder)/'home';prepare(home);clock=VirtualClock()
 with LifeApplication(home,clock=clock) as app:
  app.pause();mid,event=populate(app,clock);store=app.runtime.store
  old=context.ContextAssembler(store,app.runtime.authority);old.assemble=types.MethodType(namespace['assemble'],old)
  new=context.ContextAssembler(store,app.runtime.authority)
  req=context.ContextRequest(entity_id='project-user',scopes=('project-work',),task_class='world.social',
       task='SYNTHETIC ORCHID follow-up',query_terms=('ORCHID',),task_privacy_class='PERSONAL',
       max_input_tokens=16384,output_reserve_tokens=2048)
  policy=context.ContextPolicy(policy_id='synthetic.population',allowed_scopes=('project-work',),readable_privacy=('PUBLIC','PROJECT','PERSONAL'))
  reads=[];original=MemoryService.read
  def counted(self,memory_id,*args,**kwargs):reads.append(memory_id);return original(self,memory_id,*args,**kwargs)
  MemoryService.read=counted
  results={'old':[],'new':[]};changes=store.db.total_changes
  try:
   for repeat in range(10):
    for label,assembler in ([('old',old),('new',new)] if repeat%2==0 else [('new',new),('old',old)]):
     reads.clear();cpu=time.process_time_ns();start=time.perf_counter_ns()
     result=assembler.assemble(req,policy,pinned_only=True,conversation_topic='orchid')
     wall=(time.perf_counter_ns()-start)/1e6;cpu=(time.process_time_ns()-cpu)/1e6
     results[label].append({'wall_ms':wall,'cpu_ms':cpu,'read_calls':len(reads),'has_source':mid in refs(result),'context_counter_estimate':result.manifest.input_tokens})
   assert all(not x['has_source'] for x in results['old']) and all(x['has_source'] for x in results['new'])
   assert store.db.total_changes==changes
   assert not store.all('actions') and not store.all('cognitive_requests')
  finally:MemoryService.read=original
  print(json.dumps({'baseline':'486ed54626b27a4f2fac10c5fca6c37075b1ebb7','same_input_memories':66,
      'same_input_limit':16384,'results':results,'summary':{label:{'median_wall_ms':statistics.median(x['wall_ms'] for x in samples),
      'median_cpu_ms':statistics.median(x['cpu_ms'] for x in samples),'memory_reads':sorted(set(x['read_calls'] for x in samples))} for label,samples in results.items()},
      'database_writes':0,'model_calls':0,'actual_provider_tokens':None},indent=2))
