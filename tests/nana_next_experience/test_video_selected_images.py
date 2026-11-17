import shutil
import subprocess

import pytest

from nana_core.contracts import CoreError
from nana_core.continuity.world_loop.perception import MediaDecoder
from tools.nana_next_experience.experiments.video_pts_decode import decode
from tools.nana_next_experience.experiments.video_window_fusion import fuse_window
from tools.nana_next_experience.experiments.video_selected_images import selected_images


pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe','bwrap')),
                              reason='optional local FFmpeg and Core sandbox required')


def selection(decoded):
    dsh={'source_ref':decoded.source_ref,'input_size':decoded.output_size,
         'input_frames':len(decoded.timestamps),'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY',
         'selected':[],'dropped_sheets':0}
    pairs={'schema_version':1,'source_ref':decoded.source_ref,'input_size':decoded.output_size,
           'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]}
    return fuse_window(decoded,dsh,pairs,budget=3,max_gap=1)


@pytest.mark.parametrize('duration,offset,expected',[(2,5,'MEDIA_FRAME_TIME_INVALID'),
                                                       (31,0,'MEDIA_DURATION_BOUND')])
def test_real_core_image_decoder_accepts_candidate_pixels_with_original_pts(tmp_path,duration,offset,expected):
    original=tmp_path/'video.mp4';source=tmp_path/'source.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        f'testsrc2=s=32x32:r=4:d={duration}','-c:v','mpeg4','-threads','1',
        '-y',str(original)],check=True,timeout=20)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset',str(offset),'-y',str(source)],check=True,timeout=20)
    with pytest.raises(CoreError,match=expected):MediaDecoder().decode(source.read_bytes(),'VIDEO')
    decoded=decode('synthetic.source',source,width=32,height=32,start_seconds=0,end_seconds=2)
    chosen=selection(decoded);images=list(selected_images(decoded,chosen))
    assert images and len(images)<=3 and chosen['whole_window_observed'] is False
    assert decoded.timeline_origin==f'{offset}.000000'
    for candidate in images:
        observed=MediaDecoder().decode(candidate.png,'IMAGE')
        assert observed['pixel_digest']==candidate.pixel_sha256
        assert (observed['width'],observed['height'])==candidate.output_size==(32,32)
        assert (candidate.source_seconds,candidate.pts_tick) in zip(decoded.timestamps,decoded.pts_ticks)
        assert candidate.timeline_origin==decoded.timeline_origin
        assert candidate.source_attestation=='CALLER_SUPPLIED_UNVERIFIED'
        assert candidate.state=='CANDIDATE_NOT_INGESTED'
        assert candidate.png.hex() not in repr(candidate)


def test_cross_source_or_changed_pts_cannot_project_a_frame(tmp_path):
    source=tmp_path/'video.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=32x32:r=4:d=2','-c:v','mpeg4','-threads','1','-y',str(source)],check=True,timeout=20)
    decoded=decode('synthetic.source',source,width=32,height=32,start_seconds=0,end_seconds=2)
    chosen=selection(decoded)
    with pytest.raises(ValueError,match='incompatible'):
        list(selected_images(decoded,{**chosen,'source_ref':'different.source'}))
    frames=[dict(x) for x in chosen['selected_frames']];frames[-1]['pts_tick']+=1
    with pytest.raises(ValueError,match='selected frame'):
        next(selected_images(decoded,{**chosen,'selected_frames':frames}))
    stream=selected_images(decoded,chosen);first=next(stream)
    assert len(chosen['selected_frames'])>1
    expected=chosen['selected_frames'][1]['pts_tick']
    chosen['selected_frames'][1]['pts_tick']+=1
    assert next(stream).pts_tick==expected and first.state=='CANDIDATE_NOT_INGESTED'
