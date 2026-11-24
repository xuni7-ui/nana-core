"""Real local FFmpeg rotation fixture; no model, platform, or semantic claim."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from PIL import Image

from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_global_budget import select_windows,project_window
from tools.nana_next_experience.experiments.video_selected_images import selected_images
from tests.nana_next_experience.test_video_selected_images import selection


pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),
                              reason='optional FFmpeg unavailable')


def make_rotated(path):
    help_text=subprocess.check_output(['ffmpeg','-hide_banner','-h','full'],stderr=subprocess.STDOUT,text=True)
    if '-display_rotation' not in help_text:pytest.skip('FFmpeg display rotation fixture unsupported')
    raw=path.parent/'raw.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=64x32:r=2:d=1','-c:v','mpeg4','-threads','1','-y',str(raw)],check=True,timeout=20)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-display_rotation','90','-i',str(raw),
        '-c','copy','-y',str(path)],check=True,timeout=20)
    probe=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'stream_side_data=rotation','-of','default=nw=1:nk=1',str(path)],text=True)
    assert probe.strip()=='90'


def test_explicit_display_orientation_preserves_pixels_pts_and_source_space(tmp_path):
    video=tmp_path/'rotated.mp4';make_rotated(video)
    raw=decode('synthetic.rotation',video,width=64,height=32,start_seconds=0,end_seconds=1)
    oriented=decode('synthetic.rotation',video,width=32,height=64,start_seconds=0,end_seconds=1,orientation='display')
    assert raw.coordinate_space=='decoded_scaled_pixels_no_rotation'
    assert oriented.coordinate_space=='ffmpeg_autorotate_scaled_pixels'
    assert raw.source_size==oriented.source_size==(64,32)
    assert raw.timestamps==oriented.timestamps and raw.pts_ticks==oriented.pts_ticks
    size=64*32*3
    for i in range(len(raw.timestamps)):
        image=Image.frombytes('RGB',(64,32),raw.rgb24[i*size:(i+1)*size])
        assert image.transpose(Image.Transpose.ROTATE_90).tobytes()==oriented.rgb24[i*size:(i+1)*size]
    selected=selection(oriented)
    global_result=select_windows(oriented.source_ref,oriented.duration_seconds,[selected],budget=2,max_gap=1)
    images=list(selected_images(oriented,project_window(global_result,selected,0)))
    assert images and all(i.coordinate_space=='ffmpeg_autorotate_scaled_pixels' and i.output_size==(32,64) for i in images)
    assert all(i.pts_tick in oriented.pts_ticks for i in images)
    # A cue selected in one coordinate space cannot be projected in another.
    forged={**selected,'coordinate_space':'decoded_scaled_pixels_no_rotation'}
    with pytest.raises(ValueError,match='global window projection'):
        project_window(global_result,forged,0)
    with pytest.raises(ValueError,match='incompatible decoded selection'):
        list(selected_images(oriented,forged))
    with pytest.raises(ValueError,match='incompatible window'):
        select_windows(oriented.source_ref,oriented.duration_seconds,[selected,forged],budget=2,max_gap=1)
    with pytest.raises(ValueError,match='bounds'):
        decode('synthetic.rotation',video,orientation='unknown')


@pytest.mark.parametrize('detector_kind',['bounded-substitute','original-dsh'])
def test_rotated_video_flows_through_original_public_source_gate(tmp_path,detector_kind):
    if not shutil.which('bwrap'):pytest.skip('original Core sandbox unavailable')
    upstream=os.environ.get('NANA_DSH_SOURCE')
    if detector_kind=='original-dsh':
        if not upstream or not shutil.which('node'):pytest.skip('trusted dsh checkout and Node required')
        assert subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()==\
            '0b4bd110074b3e2cd043da8b078f7272589d50b0'
    from types import SimpleNamespace
    from nana_core.clock import Clock
    from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
    from nana_core.nanalink.media import MediaCache
    from tests.world_loop.helpers import fresh,policy,providers
    from tools.nana_next_experience.experiments.video_guarded_batch import guarded_images
    from tools.nana_next_experience.experiments.video_s5_handoff import s5_decode_handoff

    video=tmp_path/'rotated.mp4';make_rotated(video);data=video.read_bytes()
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us()
        source=PublicMediaSource(source_id='synthetic-rotation',modality='VIDEO',origin='SYNTHETIC',
                                 event_time_us=now,observed_time_us=now)
        mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,source,entity_id='observer',scope='world')
        cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            handle=cache.put([data],source_ref=mid,media_type='video/mp4')
            calls=[]
            def detector(decoded):
                calls.append(decoded.coordinate_space)
                if detector_kind=='original-dsh':
                    from tools.nana_next_experience.experiments.video_local_pairs import propose
                    raw=tmp_path/'frames.rgb';raw.write_bytes(decoded.rgb24)
                    request={'source_ref':decoded.source_ref,'rgb_path':str(raw),'width':32,'height':64,
                             'fps':2,'timestamps':decoded.timestamps,'max_frames_per_sheet':2}
                    script=Path(__file__).resolve().parents[2]/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'
                    result=subprocess.run(['node',str(script),upstream],input=json.dumps(request),
                                          text=True,capture_output=True,check=True,timeout=40)
                    size=32*64*3
                    frames=[(t,Image.frombytes('RGB',(32,64),decoded.rgb24[i*size:(i+1)*size]))
                            for i,t in enumerate(decoded.timestamps)]
                    return json.loads(result.stdout),propose(decoded.source_ref,frames)
                return ({'source_ref':decoded.source_ref,'input_size':decoded.output_size,
                    'input_frames':len(decoded.timestamps),'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY',
                    'selected':[],'dropped_sheets':0},
                    {'schema_version':1,'source_ref':decoded.source_ref,'input_size':decoded.output_size,
                     'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]})
            kwargs=dict(scope='world',windows=((0,1),),detector=detector,budget=2,max_gap=1,
                        width=32,height=64,orientation='display')
            regular=guarded_images(app,cache,mid,**kwargs)
            shared=guarded_images(app,cache,mid,shared_snapshot=True,**kwargs)
            assert regular.source_sha256==handle.sha256==shared.source_sha256
            assert regular.images==shared.images and regular.images
            assert calls==['ffmpeg_autorotate_scaled_pixels']*2
            assert all(image.coordinate_space=='ffmpeg_autorotate_scaled_pixels' for image in regular.images)
            verified=s5_decode_handoff(app,cache,shared,scope='world',verify_source_frames=True)
            assert [f.decoded['pixel_digest'] for f in verified.frames]==[f.pixel_sha256 for f in shared.images]
            assert all(f.coordinate_space=='ffmpeg_autorotate_scaled_pixels' for f in verified.frames)
            assert not runtime.store.all('actions') and not runtime.store.all('grants')
        finally:cache.close()
