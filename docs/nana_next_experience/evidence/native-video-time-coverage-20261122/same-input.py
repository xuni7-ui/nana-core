import hashlib, importlib.util, json, subprocess, sys, time
from pathlib import Path
from nana_core.continuity.world_loop.perception import MediaDecoder

spec=importlib.util.spec_from_file_location('nana_core.continuity.world_loop._baseline_292', '/tmp/nana-292-original-perception.py')
original=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=original
spec.loader.exec_module(original)

def measure(cls,data):
    class Counted(cls):
        calls=0
        def _run(self,*args,**kwargs):
            self.calls+=1
            return super()._run(*args,**kwargs)
    d=Counted();start=time.perf_counter();cpu=time.process_time();result=d.decode(data,'VIDEO')
    samples=[f['sample_s'] for f in result['frames']]
    return result,{'native_processes':d.calls,'samples':samples,'wall_s':time.perf_counter()-start,'cpu_s':time.process_time()-cpu,
        'maximum_internal_gap_s':max(b-a for a,b in zip(samples,samples[1:]))}

regular=Path('/dev/shm/nq292-regular.mkv')
subprocess.run(['ffmpeg','-nostdin','-v','error','-threads','1','-filter_threads','1','-f','lavfi','-i',
    'testsrc=size=32x24:rate=30:duration=1','-c:v','ffv1','-threads','1',str(regular)],check=True,timeout=20)
logs={}
for name,path in [('dense_first',Path('/dev/shm/nq292old/test_video_skeleton_spans_wall0/synthetic-irregular.mkv')),
                  ('dense_last',Path('/dev/shm/nq292old/test_video_skeleton_spans_wall1/synthetic-irregular.mkv')),
                  ('regular',regular)]:
    data=path.read_bytes();old,a=measure(original.MediaDecoder,data);new,b=measure(MediaDecoder,data)
    assert len(old['frames'])==len(new['frames'])==8 and a['native_processes']==b['native_processes']==3
    logs[name]={'source_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'old':a,'new':b,'whole_observation_equal':old==new}
    assert old==new if name=='regular' else b['maximum_internal_gap_s']<a['maximum_internal_gap_s']
print(json.dumps(logs,indent=2))
