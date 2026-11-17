import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest
from PIL import Image

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.perception import MediaDecoder,PerceptionService,PublicMediaSource
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh,policy,providers
from tools.nana_next_experience.experiments.video_guarded_batch import guarded_images
from tools.nana_next_experience.experiments.video_local_pairs import propose
from tools.nana_next_experience.experiments.video_motion_onset import propose as motion_onsets


pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe','bwrap','node')),
                              reason='optional FFmpeg, sandbox and Node required')


def test_original_store_guard_wraps_real_dsh_batch_and_blocks_midflight_withdrawal(tmp_path,monkeypatch):
    upstream=os.environ.get('NANA_DSH_SOURCE')
    if not upstream:pytest.skip('trusted original dsh checkout required')
    assert subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()==\
        '0b4bd110074b3e2cd043da8b078f7272589d50b0'
    video=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=32x32:r=4:d=2','-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=20)
    data=video.read_bytes()
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us()
        source=PublicMediaSource(source_id='synthetic-video',modality='VIDEO',origin='SYNTHETIC',
                                 event_time_us=now,observed_time_us=now)
        mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,source,entity_id='observer',scope='world')
        cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            handle=cache.put([data],source_ref=mid,media_type='video/mp4')
            calls=[]
            def detector(decoded):
                raw=tmp_path/'frames.rgb';raw.write_bytes(decoded.rgb24);calls.append(len(decoded.timestamps))
                request={'source_ref':decoded.source_ref,'rgb_path':str(raw),'width':32,'height':32,'fps':4,
                         'timestamps':decoded.timestamps,'max_frames_per_sheet':4}
                script=Path(__file__).resolve().parents[2]/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'
                result=subprocess.run(['node',str(script),upstream],input=json.dumps(request),
                                      text=True,capture_output=True,check=True,timeout=40)
                pixels=32*32*3
                frames=[(t,Image.frombytes('RGB',(32,32),decoded.rgb24[i*pixels:(i+1)*pixels]))
                        for i,t in enumerate(decoded.timestamps)]
                return json.loads(result.stdout),propose(decoded.source_ref,frames),motion_onsets(decoded.source_ref,frames)
            batch=guarded_images(app,cache,mid,scope='world',windows=((0,1.5),(.5,2)),
                                 detector=detector,budget=3,max_gap=1,width=32,height=32)
            assert batch.source_ref==mid and batch.source_sha256==handle.sha256==hashlib.sha256(data).hexdigest()
            assert calls==[6,6] and 1<=len(batch.images)<=3
            assert batch.cache_bytes_hashed==2*len(data) and batch.window_count==2
            assert batch.decoded_rgb_bytes==12*32*32*3
            assert len({frame.pts_tick for frame in batch.images})==len(batch.images)
            assert all(MediaDecoder().decode(frame.png,'IMAGE')['pixel_digest']==frame.pixel_sha256
                       for frame in batch.images)
            assert batch.state=='CANDIDATES_NOT_INGESTED' and batch.source_lifetime=='RECHECK_REQUIRED_AT_USE'
            shared=guarded_images(app,cache,mid,scope='world',windows=((0,1.5),(.5,2)),
                                  detector=detector,budget=3,max_gap=1,width=32,height=32,shared_snapshot=True)
            assert shared.images==batch.images and shared.unrequested_intervals==batch.unrequested_intervals
            assert shared.sampling_gaps==batch.sampling_gaps and shared.source_sha256==batch.source_sha256
            assert shared.decoded_rgb_bytes==batch.decoded_rgb_bytes
            assert shared.cache_bytes_hashed==len(data) and batch.cache_bytes_hashed==2*len(data)
            from tools.nana_next_experience.experiments import video_guarded_batch as module
            from tools.nana_next_experience.experiments.video_pts_decode import FrameBoundExceeded
            actual_decode=module.decode_cached_window;limits=[]
            def bounded_decode(*args,**kwargs):
                limits.append(kwargs['max_frames']);return actual_decode(*args,**kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(module,'MAX_BATCH_RGB_BYTES',8*32*32*3)
                patch.setattr(module,'decode_cached_window',bounded_decode)
                with pytest.raises(FrameBoundExceeded):
                    guarded_images(app,cache,mid,scope='world',windows=((0,1.5),(.5,2)),
                                   detector=detector,budget=3,max_gap=1,width=32,height=32)
            assert limits==[8,2]
            current={'value':True}
            other_source=source.model_copy(update={'source_id':'synthetic-video-independent'})
            other_mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,other_source,entity_id='observer',scope='world')
            cache.put([data],source_ref=other_mid,media_type='video/mp4')
            def revoke_cache(decoded):
                result=detector(decoded);current['value']=False;return result
            with monkeypatch.context() as patch:
                patch.setattr(cache,'current',lambda ref: current['value'] if ref==other_mid else True)
                with pytest.raises(CoreError,match='MEDIA_SOURCE_RETIRED'):
                    guarded_images(app,cache,other_mid,scope='world',windows=((0,1),),detector=revoke_cache,
                                   budget=2,max_gap=1,width=32,height=32,shared_snapshot=True)
            def revoke(decoded):
                result=detector(decoded)
                MemoryService(runtime.store,runtime.authority).forget(mid,runtime.authority)
                return result
            previous_calls=len(calls)
            with pytest.raises(CoreError):
                guarded_images(app,cache,mid,scope='world',windows=((0,1),(1,2)),detector=revoke,
                               budget=2,max_gap=1,width=32,height=32,shared_snapshot=True)
            assert len(calls)==previous_calls+1
        finally:cache.close()
