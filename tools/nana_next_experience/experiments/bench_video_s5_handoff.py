"""Compare technical decode with/without candidate source checks on synthetic media.

The two paths do not offer equivalent source guarantees; this measures the
additional local work, not a performance improvement or production cost.
"""
import json
from pathlib import Path
import resource
import statistics
import subprocess
import tempfile
import time

from nana_core.clock import Clock
from nana_core.continuity.world_loop.perception import MediaDecoder
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh
from tests.nana_next_experience.test_video_shared_audio_snapshot import source
from tests.nana_next_experience.test_video_s5_handoff import make_batch
from tools.nana_next_experience.experiments.video_s5_handoff import s5_decode_handoff


def main():
    with tempfile.TemporaryDirectory(prefix='nana-s5-bench-') as directory:
        root=Path(directory);video=root/'source.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=320x180:r=10:d=15',
                        '-c:v','mpeg4','-q:v','2','-threads','1','-y',str(video)],check=True,timeout=60)
        data=video.read_bytes()
        with fresh(root/'subject.db',Clock()) as runtime:
            app,mid=source(runtime,data);cache=MediaCache(root/'cache',source_current=lambda _:True)
            try:
                cache.put((data[i:i+65536] for i in range(0,len(data),65536)),source_ref=mid,media_type='video/mp4')
                batch=make_batch(app,cache,mid);times={'decode_only':[],'source_checked':[],'frame_verified':[]};cpu={k:[] for k in times};child_cpu={k:[] for k in times}
                results={}
                for i in range(3):
                    names=('decode_only','source_checked','frame_verified')
                    for name in (names if i%2==0 else tuple(reversed(names))):
                        start=time.perf_counter();start_cpu=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
                        if name=='decode_only':result=[MediaDecoder().decode(f.png,'IMAGE') for f in batch.images]
                        else:result=[f.decoded for f in s5_decode_handoff(app,cache,batch,scope='world',verify_source_frames=name=='frame_verified').frames]
                        after=resource.getrusage(resource.RUSAGE_CHILDREN)
                        times[name].append(time.perf_counter()-start);cpu[name].append(time.process_time()-start_cpu)
                        child_cpu[name].append(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
                        results[name]=result
                if not results['decode_only']==results['source_checked']==results['frame_verified']:raise RuntimeError('technical image output differs')
                print(json.dumps({'source_bytes':len(data),'frame_count':len(batch.images),
                    'source_checked_extra_bytes_hashed_and_written':len(data),
                    'wall_seconds':times,'wall_median_seconds':{k:statistics.median(v) for k,v in times.items()},
                    'parent_cpu_seconds':cpu,'child_cpu_seconds':child_cpu,'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'rss_scope':'whole benchmark, all paths; not per-path incremental memory',
                    'scope':'one synthetic video; direct decode, source hash and source frame verification have different guarantees; no provider or tokens'},indent=2))
            finally:cache.close()


if __name__=='__main__':main()
