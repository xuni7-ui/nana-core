"""Fixed original versus current module, same byte input and three replays."""
import argparse,hashlib,importlib,importlib.util,json,resource,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--variant',choices=('original','current'),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=Path('/workspace/nana-next-refinement-work');sys.dont_write_bytecode=True;sys.path[:0]=[str(repo/'src'),str(repo)]
fixed='e5969b0363e825a51b56a9f24a655bfa590c6887';name='nana_core.continuity.world_loop.perception'
if a.variant=='original':
 raw=subprocess.check_output(['git','show',fixed+':src/nana_core/continuity/world_loop/perception.py'],cwd=repo);path=Path('/dev/shm/nana-282-original-perception.py');path.write_bytes(raw);importlib.import_module(name.rpartition('.')[0]);spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
else:module=importlib.import_module(name)
from tests.world_loop.helpers import fresh,providers,policy
from nana_core.presence.runtime import NanaRuntime
from nana_core.continuity.records import RecordService
from nana_core.continuity.memory import MemoryService
source=Path('/dev/shm/nana-282-fixture-video.bin');data=source.read_bytes();root=Path('/dev/shm/nana-282-benchmark-'+a.variant);assert not root.exists();root.mkdir();path=root/'self.db';calls=[]
class Counted(module.MediaDecoder):
 def _run(self,args,**kw):calls.append(args[0]);return super()._run(args,**kw)
with fresh(path) as r:
 desc=module.PublicMediaSource(source_id='same-owned-video',modality='VIDEO',origin='SYNTHETIC',event_time_us=r.clock.utc_now_us(),observed_time_us=r.clock.utc_now_us());ids=module.PerceptionService(r.store,providers(),policy(),decoder=Counted()).ingest(data,desc,entity_id='observer',scope='world');initial=len(calls);config,clock,identity=r.config,r.clock,r.identity_id;body=MemoryService(r.store).read(ids[0])['text'];record=RecordService(r.store).read(ids[1])
with NanaRuntime(path,config,clock=clock) as r:
 assert r.identity_id==identity;service=module.PerceptionService(r.store,providers(),policy(),decoder=Counted());writes=r.store.db.total_changes;before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter();cpu=time.process_time();samples=[]
 for _ in range(3):
  t=time.perf_counter();assert service.ingest(data,desc,entity_id='observer',scope='world')==ids;samples.append(time.perf_counter()-t)
 elapsed=time.perf_counter()-start;parent_cpu=time.process_time()-cpu;after=resource.getrusage(resource.RUSAGE_CHILDREN);assert r.store.db.total_changes==writes
 assert MemoryService(r.store).read(ids[0])['text']==body and RecordService(r.store).read(ids[1])==record
 report={'variant':a.variant,'original_fixed_source':fixed,'module_sha256':hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'same_subject_after_restart':True,'replays':3,'first_decode_processes':initial,'additional_replay_native_processes':len(calls)-initial,'replay_wall_seconds':elapsed,'replay_parent_cpu_seconds':parent_cpu,'replay_child_user_system_cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,'individual_wall_seconds':samples,'original_memory_and_record_unchanged':True,'sqlite_write_rows':r.store.db.total_changes-writes,'real_provider_calls':0,'byte_accounting_not_tokens':True}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
