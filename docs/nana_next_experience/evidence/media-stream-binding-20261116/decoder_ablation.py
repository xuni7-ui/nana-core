"""One actual generated input, exact original decoder and current sandbox."""
import ast,hashlib,json,re,resource,subprocess,time,types
from pathlib import Path
from nana_core.continuity.world_loop import perception as module
from nana_core.continuity.world_loop.perception import MediaDecoder
base='7690ce94f63b27f48604d205ad5fbaf03fbd4895'
raw=subprocess.check_output(['git','show',base+':src/nana_core/continuity/world_loop/perception.py'],text=True)
cls=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='MediaDecoder');node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='decode');ns=dict(vars(module));exec(compile(ast.Module(body=[node],type_ignores=[]),'<fixed-'+base+'-decode>','exec'),ns)
report=Path('/workspace/nana-media-stream-original.txt').read_text();match=re.search(r"tmp_path = PosixPath\('(/dev/shm/pytest-of-agent/pytest-\d+)/",report);assert match
video=Path(match.group(1))/'native-media-tracks0/fixture.mkv';assert video.is_file();data=video.read_bytes();outputs=[]
for mode,decode in [('original',ns['decode']),('bound_first_stream',MediaDecoder.decode)]:
 for modality in ('VIDEO','AUDIO'):
  decoder=MediaDecoder();decoder.decode=types.MethodType(decode,decoder);run=decoder._run;calls=[]
  def measured(args,**kwargs):
   calls.append({'process':args[0],'mapped_stream':args[args.index('-map')+1] if '-map' in args else 'AUTOMATIC_SELECTION'})
   return run(args,**kwargs)
  decoder._run=measured;start=time.perf_counter();parent=time.process_time();children=resource.getrusage(resource.RUSAGE_CHILDREN);value=decoder.decode(data,modality);end=resource.getrusage(resource.RUSAGE_CHILDREN)
  result={'mode':mode,'modality':modality,'wall_ms':(time.perf_counter()-start)*1000,'parent_cpu_ms':(time.process_time()-parent)*1000,'completed_children_cpu_ms':(end.ru_utime+end.ru_stime-children.ru_utime-children.ru_stime)*1000,'processes':calls,'duration_s':value['duration_s'],'semantic_or_speech':'UNKNOWN'}
  if modality=='VIDEO':result.update(metadata_dimensions=[value['width'],value['height']],source_frame_count=value['source_frame_count'],sample_times=[f['sample_s'] for f in value['frames']],first_mean_rgb=value['frames'][0]['mean_rgb'])
  else:result.update(metadata_rate=value['source_sample_rate'],metadata_channels=value['source_channels'],samples=value['samples'],first_rms=value['segments'][0]['rms'])
  outputs.append(result)
assert outputs[0]['first_mean_rgb'][2]>200 and outputs[2]['first_mean_rgb'][0]>200
assert outputs[1]['first_rms']>0 and outputs[3]['first_rms']==0
assert len(outputs[0]['processes'])==len(outputs[2]['processes'])==3 and len(outputs[1]['processes'])==len(outputs[3]['processes'])==2
print(json.dumps({'scope':'SYNTHETIC_SAME_EXACT_ENCODED_FILE_NATIVE_SANDBOX_ONLY','base':base,'input_sha256':hashlib.sha256(data).hexdigest(),'input_bytes':len(data),'outputs':outputs,'all_same_existing_bwrap':True,'actual_provider_calls':0,'new_processes_added':0,'new_schema_or_dependencies':False,'cumulative_exited_child_maxrss_KiB':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'not_production_or_semantic_qualification':True},indent=2))
