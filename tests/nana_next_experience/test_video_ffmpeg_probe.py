import shutil
import subprocess

import pytest

from tools.nana_next_experience.experiments.video_ffmpeg_probe import probe
from tools.nana_next_experience.experiments.video_coverage import plan


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='optional FFmpeg unavailable')
def test_real_generated_video_scene_measurements_and_coverage(tmp_path):
    path=tmp_path/'three-scenes.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','color=black:s=160x90:r=4:d=4',
        '-f','lavfi','-i','color=white:s=160x90:r=4:d=4',
        '-f','lavfi','-i','testsrc2=s=160x90:r=4:d=4',
        '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0',
        '-c:v','mpeg4','-threads','1','-y',str(path)],check=True,timeout=20)
    result=probe(path)
    assert result['scan_complete'] and result['frames_measured']==48
    assert result['duration']==12
    assert {round(c.seconds) for c in result['candidates'] if c.cut>10}>={4,8}
    selection=plan(result['duration'],result['candidates'],8,max_gap=3)
    assert len(selection['timestamps'])==8 and selection['coverage_target_met']


def test_non_media_file_is_rejected(tmp_path):
    path=tmp_path/'invalid.mp4';path.write_bytes(b'not a video')
    with pytest.raises(ValueError,match='unavailable'):probe(path)


def test_early_termination_never_claims_full_video_coverage(tmp_path,monkeypatch):
    from tools.nana_next_experience.experiments import video_ffmpeg_probe as module
    path=tmp_path/'fixture.mp4';path.write_bytes(b'synthetic')
    replies=iter(['{"format":{"duration":"12"}}',
                  'frame:0 pts:0 pts_time:0\nlavfi.scd.score=0\nframe:1 pts:4 pts_time:4\nlavfi.scd.score=25\n'])
    monkeypatch.setattr(module,'_run',lambda *args,**kwargs:next(replies))
    result=module.probe(path)
    assert result['scanned_until']==4 and result['scan_complete'] is False


def test_missing_beginning_never_claims_full_video_coverage(tmp_path,monkeypatch):
    from tools.nana_next_experience.experiments import video_ffmpeg_probe as module
    path=tmp_path/'fixture.mp4';path.write_bytes(b'synthetic')
    replies=iter(['{"format":{"duration":"12"}}',
                  'frame:0 pts:4 pts_time:4\nlavfi.scd.score=0\nframe:1 pts:11 pts_time:11\nlavfi.scd.score=25\n'])
    monkeypatch.setattr(module,'_run',lambda *args,**kwargs:next(replies))
    assert module.probe(path)['scan_complete'] is False
