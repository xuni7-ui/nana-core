"""Original-source-gated image/audio snapshot comparison using local synthetic media."""
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
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh,policy,providers
from tests.nana_next_experience.test_video_guarded_audio import video_bytes
from tools.nana_next_experience.experiments.video_guarded_audio import guarded_audio_window
from tools.nana_next_experience.experiments.video_guarded_batch import guarded_images
from tools.nana_next_experience.experiments.video_local_pairs import propose


pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe','bwrap','node')),
                              reason='optional FFmpeg, sandbox, and Node required')


def source(runtime,data):
    app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us()
    descriptor=PublicMediaSource(source_id='synthetic-audio-video',modality='VIDEO',origin='SYNTHETIC',
                                 event_time_us=now,observed_time_us=now)
    mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,descriptor,entity_id='observer',scope='world')
    return app,mid


def test_same_snapshot_matches_separate_source_gated_image_and_audio(tmp_path):
    upstream=os.environ.get('NANA_DSH_SOURCE')
    if not upstream:pytest.skip('trusted original dsh checkout required')
    assert subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()==\
        '0b4bd110074b3e2cd043da8b078f7272589d50b0'
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            handle=cache.put([data],source_ref=mid,media_type='video/mp4')
            def detector(decoded):
                raw=tmp_path/'frames.rgb';raw.write_bytes(decoded.rgb24)
                request={'source_ref':mid,'rgb_path':str(raw),'width':32,'height':32,'fps':2,
                         'timestamps':decoded.timestamps,'max_frames_per_sheet':4}
                script=Path(__file__).resolve().parents[2]/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'
                result=subprocess.run(['node',str(script),upstream],input=json.dumps(request),
                                      text=True,capture_output=True,check=True,timeout=40)
                size=32*32*3
                frames=[(t,Image.frombytes('RGB',(32,32),decoded.rgb24[i*size:(i+1)*size]))
                        for i,t in enumerate(decoded.timestamps)]
                return json.loads(result.stdout),propose(mid,frames)
            kwargs=dict(scope='world',windows=((0,4),),detector=detector,budget=3,max_gap=2,
                        width=32,height=32,shared_snapshot=True)
            images=guarded_images(app,cache,mid,**kwargs)
            audio=guarded_audio_window(app,cache,mid,scope='world',start_seconds=1,end_seconds=3)
            combined=guarded_images(app,cache,mid,audio_window=(1,3),**kwargs)
            assert combined.images==images.images and combined.acoustic==audio.acoustic
            assert combined.acoustic_status=='AVAILABLE_NOT_QUALIFIED'
            assert combined.source_ref==mid and combined.source_sha256==audio.source_sha256==handle.sha256
            assert combined.cache_bytes_hashed==len(data) and images.cache_bytes_hashed+audio.cache_bytes_hashed==2*len(data)
            assert combined.acoustic['timeline_basis']=='FFMPEG_NORMALIZED_CALLER_MUST_VERIFY'
            assert combined.source_lifetime=='RECHECK_REQUIRED_AT_USE' and not runtime.store.all('actions')
            with pytest.raises(ValueError,match='audio window'):
                guarded_images(app,cache,mid,**{**kwargs,'shared_snapshot':False},audio_window=(1,3))
        finally:cache.close()


@pytest.mark.parametrize('withdrawal',['store','cache'])
@pytest.mark.parametrize('probe_fails',[False,True])
def test_shared_audio_never_returns_if_source_withdrawn_during_probe(tmp_path,monkeypatch,withdrawal,probe_fails):
    from tools.nana_next_experience.experiments import video_guarded_batch as module
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4')
            def detector(decoded):
                return ({'source_ref':mid,'input_size':decoded.output_size,'input_frames':len(decoded.timestamps),
                         'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY','selected':[],'dropped_sheets':0},
                        {'schema_version':1,'source_ref':mid,'input_size':decoded.output_size,
                         'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]})
            original=module.measure
            def revoke(path,**kwargs):
                result=original(path,**kwargs)
                if withdrawal=='store':MemoryService(runtime.store,runtime.authority).forget(mid,runtime.authority)
                else:monkeypatch.setattr(cache,'current',lambda _:False)
                if probe_fails:
                    from tools.nana_next_experience.experiments.video_audio_probe import AudioProbeUnavailable
                    raise AudioProbeUnavailable('fixture')
                return result
            monkeypatch.setattr(module,'measure',revoke)
            with pytest.raises(CoreError):
                guarded_images(app,cache,mid,scope='world',windows=((0,4),),detector=detector,
                               budget=3,max_gap=2,width=32,height=32,shared_snapshot=True,audio_window=(1,3))
        finally:cache.close()


@pytest.mark.parametrize('failure,expected',[
    ('unavailable','PROBE_UNAVAILABLE'),('bound','OUTPUT_BOUND'),
])
def test_audio_probe_failure_keeps_valid_source_gated_image_candidates(tmp_path,monkeypatch,failure,expected):
    from tools.nana_next_experience.experiments import video_guarded_batch as module
    from tools.nana_next_experience.experiments.video_audio_probe import AudioProbeUnavailable,AudioProbeOutputBound
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4')
            def detector(decoded):
                return ({'source_ref':mid,'input_size':decoded.output_size,'input_frames':len(decoded.timestamps),
                         'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY','selected':[],'dropped_sheets':0},
                        {'schema_version':1,'source_ref':mid,'input_size':decoded.output_size,
                         'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]})
            kwargs=dict(scope='world',windows=((0,4),),detector=detector,budget=3,max_gap=2,
                        width=32,height=32,shared_snapshot=True)
            baseline=guarded_images(app,cache,mid,**kwargs)
            exception=AudioProbeUnavailable if failure=='unavailable' else AudioProbeOutputBound
            def fail(*args,**kwargs):raise exception('fixture')
            monkeypatch.setattr(module,'measure',fail)
            combined=guarded_images(app,cache,mid,audio_window=(1,3),**kwargs)
            assert combined.images==baseline.images and combined.images
            assert combined.acoustic is None and combined.acoustic_status==expected
            assert combined.source_lifetime=='RECHECK_REQUIRED_AT_USE'
        finally:cache.close()
