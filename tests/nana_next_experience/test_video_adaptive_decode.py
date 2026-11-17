import shutil
import subprocess

import pytest

from tools.nana_next_experience.experiments.video_adaptive_decode import iter_windows
from tools.nana_next_experience.experiments.video_pts_decode import decode, FrameBoundExceeded


pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),
                              reason='optional FFmpeg unavailable')


def make_video(path):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=32x32:r=10:d=8','-c:v','mpeg4','-g','40','-threads','1',
        '-y',str(path)],check=True,timeout=20)


def test_real_video_subdivides_at_frame_bound_and_preserves_pts_and_pixels(tmp_path):
    original=tmp_path/'original.mp4';path=tmp_path/'offset.mp4';make_video(original)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset','5','-y',str(path)],check=True,timeout=20)
    full=decode('synthetic',path,width=32,height=32)
    assert full.timeline_origin=='5.000000' and full.pts_ticks[0]>0
    with pytest.raises(FrameBoundExceeded):
        decode('synthetic',path,width=32,height=32,max_frames=12,start_seconds=0,end_seconds=8)
    records=list(iter_windows('synthetic',path,0,8,width=32,height=32,max_frames=12))
    chunks=[record['decoded'] for record in records[:-1]]
    assert len(chunks)==8 and all(len(chunk.timestamps)<=12 for chunk in chunks)
    assert sum((chunk.pts_ticks for chunk in chunks),())==full.pts_ticks
    assert b''.join(chunk.rgb24 for chunk in chunks)==full.rgb24
    assert records[-1]['complete_requests'] and not records[-1]['unprocessed_intervals']
    assert records[-1]['status']=='REQUESTS_ONLY_NOT_OBSERVED'


def test_attempt_limit_preserves_every_unprocessed_interval(tmp_path):
    path=tmp_path/'video.mp4';make_video(path)
    records=list(iter_windows('synthetic',path,0,8,width=32,height=32,max_frames=12,max_attempts=3))
    assert records==[{'status':'REQUESTS_ONLY_NOT_OBSERVED','attempts':3,
        'unprocessed_intervals':[(0,1.0),(1.0,2.0),(2.0,4.0),(4.0,8)],
        'complete_requests':False,'source_attestation':'CALLER_SUPPLIED'}]


def test_non_bound_failure_propagates_instead_of_becoming_empty_video(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(iter_windows('synthetic',tmp_path/'missing',0,8))
