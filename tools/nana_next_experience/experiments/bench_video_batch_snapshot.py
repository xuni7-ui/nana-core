"""Compare per-window versus one-batch PUBLIC snapshots on fixed sample."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import statistics
import tempfile
import time
from types import SimpleNamespace

from nana_core.clock import Clock
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh,policy,providers
from tools.nana_next_experience.experiments.video_guarded_batch import guarded_images


VIDEO_SHA='4666099d0f704e310047b2f0a5ec9f936cb76a7271de9a2e70a0c57f82ac82dc'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--video',type=Path,required=True);args=parser.parse_args()
    path=args.video.resolve(strict=True)
    if path.stat().st_size!=1250680:raise ValueError('sample size mismatch')
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=VIDEO_SHA:raise ValueError('sample hash mismatch')
    with tempfile.TemporaryDirectory(prefix='nana-snapshot-bench-') as directory:
        root=Path(directory)
        with fresh(root/'subject.db',Clock()) as runtime:
            app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us()
            source=PublicMediaSource(source_id='opencv-tree',modality='VIDEO',origin='RECORDED',
                                     event_time_us=now,observed_time_us=now)
            mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,source,entity_id='observer',scope='world')
            cache=MediaCache(root/'cache',source_current=lambda _:True)
            try:
                cache.put((data[i:i+65536] for i in range(0,len(data),65536)),source_ref=mid,media_type='video/x-msvideo')
                def deterministic_empty_detector(decoded):
                    dsh={'source_ref':mid,'input_size':decoded.output_size,'input_frames':len(decoded.timestamps),
                         'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY','selected':[],'dropped_sheets':0}
                    pairs={'schema_version':1,'source_ref':mid,'input_size':decoded.output_size,
                           'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]}
                    return dsh,pairs
                timings={'per_window':[],'shared':[]};cpus={'per_window':[],'shared':[]};rows={};reference=None
                for mode in ('per_window','shared','shared','per_window','per_window','shared'):
                    started=time.perf_counter();cpu=time.process_time();children=resource.getrusage(resource.RUSAGE_CHILDREN)
                    batch=guarded_images(app,cache,mid,scope='world',windows=((0,8),(7,15),(14,22),(21,29.6)),
                        detector=deterministic_empty_detector,budget=4,max_gap=8,width=160,height=120,
                        shared_snapshot=mode=='shared')
                    after=resource.getrusage(resource.RUSAGE_CHILDREN)
                    timings[mode].append(time.perf_counter()-started)
                    cpus[mode].append({'parent':time.process_time()-cpu,
                                       'children':after.ru_utime+after.ru_stime-children.ru_utime-children.ru_stime})
                    signature=(batch.source_sha256,batch.images,batch.unrequested_intervals,batch.sampling_gaps,
                               batch.decoded_rgb_bytes,batch.window_count)
                    if reference is None:reference=signature
                    elif signature!=reference:raise RuntimeError('batch output changed')
                    rows[mode]={'cache_bytes_hashed':batch.cache_bytes_hashed,'window_count':batch.window_count,
                                'decoded_rgb_bytes':batch.decoded_rgb_bytes,'selected_frames':len(batch.images),
                                'timestamps':[image.source_seconds for image in batch.images]}
                print(json.dumps({'sample':{'repository':'https://github.com/opencv/opencv',
                    'commit':'5d0660acfed08650cafec4876b4792a369a20601','path':'samples/data/tree.avi',
                    'sha256':VIDEO_SHA,'bytes':len(data),
                    'license':'repository root Apache-2.0; individual video authorship/license unconfirmed'},
                    'modes':rows,'output_identical':True,'wall_seconds':timings,
                    'wall_median_seconds':{k:statistics.median(v) for k,v in timings.items()},'cpu_seconds':cpus,
                    'process_peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'rss_scope':'whole parent process including both modes, not child or per-mode RSS',
                    'limits':'one recorded clip, deterministic empty signal fixture, four FFmpeg decodes per mode; no model/Token or Bilibili attribution'},indent=2))
            finally:cache.close()


if __name__=='__main__':main()
