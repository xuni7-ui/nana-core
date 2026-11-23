"""Paired public-source snapshot comparison with synthetic local AV and original dsh."""
import argparse
import json
from pathlib import Path
import resource
import statistics
import subprocess
import tempfile
import time
from types import SimpleNamespace

from PIL import Image
from nana_core.clock import Clock
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh,policy,providers
from tools.nana_next_experience.experiments.video_guarded_audio import guarded_audio_window
from tools.nana_next_experience.experiments.video_guarded_batch import guarded_images
from tools.nana_next_experience.experiments.video_local_pairs import propose


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dsh',type=Path,required=True);args=parser.parse_args()
    upstream=args.dsh.resolve(strict=True)
    if subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()!=\
            '0b4bd110074b3e2cd043da8b078f7272589d50b0':raise ValueError('unexpected dsh revision')
    with tempfile.TemporaryDirectory(prefix='nana-shared-av-bench-') as directory:
        root=Path(directory);video=root/'source.mp4'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
            'testsrc2=s=320x180:r=10:d=15','-f','lavfi','-i',
            'sine=frequency=440:sample_rate=16000:duration=15','-map','0:v','-map','1:a',
            '-c:v','mpeg4','-c:a','aac','-threads','1','-t','15','-y',str(video)],check=True,timeout=30)
        data=video.read_bytes()
        with fresh(root/'subject.db',Clock()) as runtime:
            app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us()
            source=PublicMediaSource(source_id='synthetic-av-bench',modality='VIDEO',origin='SYNTHETIC',
                event_time_us=now,observed_time_us=now)
            mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,source,entity_id='observer',scope='world')
            cache=MediaCache(root/'cache',source_current=lambda _:True)
            try:
                handle=cache.put([data],source_ref=mid,media_type='video/mp4')
                def detector(decoded):
                    path=root/'frames.rgb';path.write_bytes(decoded.rgb24)
                    request={'source_ref':mid,'rgb_path':str(path),'width':64,'height':36,'fps':10,
                             'timestamps':decoded.timestamps,'max_frames_per_sheet':8}
                    script=Path(__file__).resolve().parent/'dsh_pipeline_adapter.mjs'
                    result=subprocess.run(['node',str(script),str(upstream)],input=json.dumps(request),
                                          text=True,capture_output=True,check=True,timeout=40)
                    size=64*36*3
                    frames=[(t,Image.frombytes('RGB',(64,36),decoded.rgb24[i*size:(i+1)*size]))
                            for i,t in enumerate(decoded.timestamps)]
                    return json.loads(result.stdout),propose(mid,frames)
                kwargs=dict(scope='world',windows=((0,7.5),(7.5,15)),detector=detector,
                            budget=4,max_gap=5,width=64,height=36,shared_snapshot=True)
                def baseline():
                    video_result=guarded_images(app,cache,mid,**kwargs)
                    audio_result=guarded_audio_window(app,cache,mid,scope='world',start_seconds=1,end_seconds=14)
                    return video_result,audio_result.acoustic,video_result.cache_bytes_hashed+audio_result.cache_bytes_hashed
                def candidate():
                    result=guarded_images(app,cache,mid,audio_window=(1,14),**kwargs)
                    return result,result.acoustic,result.cache_bytes_hashed
                functions={'separate':baseline,'shared':candidate};wall={k:[] for k in functions}
                parent_cpu={k:[] for k in functions};child_cpu={k:[] for k in functions};outputs={}
                for i in range(3):
                    for name in (('separate','shared') if i%2==0 else ('shared','separate')):
                        start=time.perf_counter();cpu=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
                        result=functions[name]();after=resource.getrusage(resource.RUSAGE_CHILDREN)
                        wall[name].append(time.perf_counter()-start);parent_cpu[name].append(time.process_time()-cpu)
                        child_cpu[name].append(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
                        outputs[name]=result
                a,b=outputs['separate'],outputs['shared']
                if a[0].images!=b[0].images or a[1]!=b[1] or a[0].source_sha256!=b[0].source_sha256:
                    raise RuntimeError('candidate outputs differ')
                print(json.dumps({'source_bytes':len(data),'source_sha256':handle.sha256,
                    'identical_images_and_acoustic':True,'image_candidates':len(b[0].images),
                    'logical_bytes_hashed_and_snapshotted':{'separate':a[2],'shared':b[2]},
                    'wall_seconds':wall,'wall_median_seconds':{k:statistics.median(v) for k,v in wall.items()},
                    'parent_cpu_seconds':parent_cpu,'child_cpu_seconds':child_cpu,'peak_memory':'NOT_MEASURED',
                    'scope':'one synthetic 15s source, 3 paired runs, original local dsh and original PUBLIC gate; no real provider, Token, bill, platform attestation or semantic accuracy'},indent=2))
            finally:cache.close()


if __name__=='__main__':main()
