import os
from pathlib import Path
import shutil
import subprocess
import json
import pytest

from tools.nana_next_experience.experiments.video_pts_decode import decode

pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='optional FFmpeg unavailable')


def make_vfr(path):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=160x90:r=4:d=3','-vf',"select='eq(n,0)+eq(n,2)+eq(n,7)+eq(n,8)'",
        '-fps_mode','vfr','-c:v','mpeg4','-threads','1','-y',str(path)],check=True,timeout=20)


def test_vfr_decode_uses_actual_pts_not_frame_index_rate(tmp_path):
    path=tmp_path/'vfr.mp4';make_vfr(path)
    result=decode('source.synthetic',path)
    assert result.timestamps==(0.0,0.5,1.75,2.0)
    assert tuple(t*result.time_base[0]/result.time_base[1] for t in result.pts_ticks)==result.timestamps
    assert result.timestamps!=tuple(i/4 for i in range(4))
    assert len(result.rgb24)==4*160*90*3 and result.count_consistent
    assert result.source_size==result.output_size==(160,90)
    assert result.source_attestation=='CALLER_SUPPLIED' and 'rgb24' not in repr(result)


def test_frame_limit_rejects_instead_of_silent_truncation(tmp_path):
    path=tmp_path/'vfr.mp4';make_vfr(path)
    with pytest.raises(ValueError,match='frame bound'):decode('source.synthetic',path,max_frames=3)


def test_nonzero_input_timeline_is_not_silently_shifted(tmp_path):
    original=tmp_path/'vfr.mp4';offset=tmp_path/'offset.mp4';make_vfr(original)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset','5','-y',str(offset)],check=True,timeout=20)
    with pytest.raises(ValueError,match='timing'):decode('source.synthetic',offset)


def test_decoded_pts_feed_original_dsh_without_inventing_times(tmp_path):
    upstream=os.environ.get('NANA_DSH_SOURCE')
    if not upstream or not shutil.which('node'):pytest.skip('trusted dsh checkout and Node required')
    assert subprocess.check_output(['git','-C',upstream,'rev-parse','HEAD'],text=True).strip()==\
        '0b4bd110074b3e2cd043da8b078f7272589d50b0'
    path=tmp_path/'vfr.mp4';make_vfr(path);decoded=decode('source.synthetic',path)
    raw=tmp_path/'frames.rgb';raw.write_bytes(decoded.rgb24)
    root=Path(__file__).resolve().parents[2]
    request={'source_ref':decoded.source_ref,'rgb_path':str(raw),'width':160,'height':90,
        'fps':4,'timestamps':decoded.timestamps,'max_frames_per_sheet':4}
    result=subprocess.run(['node',str(root/'tools/nana_next_experience/experiments/dsh_pipeline_adapter.mjs'),upstream],
        input=json.dumps(request),text=True,capture_output=True,check=True,timeout=40)
    selected=json.loads(result.stdout)['selected']
    assert selected and all(item['seconds'] in decoded.timestamps for item in selected)


def test_missing_or_duplicate_pts_are_rejected_not_reconstructed(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_pts_decode as module
    path=tmp_path/'fixture.mp4';path.write_bytes(b'synthetic')
    metadata=(b'{"format":{"duration":"2","start_time":"0"},"streams":'
              b'[{"width":2,"height":2,"start_time":"0","nb_frames":"2"}]}')
    config=b'[Parsed_showinfo_2 @ 0x1] config in time_base: 1/1000, frame_rate: 4/1\n'
    rows=(b'[Parsed_showinfo_2 @ 0x1] n: 0 pts: 0 pts_time:0\n'
          b'[Parsed_showinfo_2 @ 0x1] n: 1 pts: 0 pts_time:0\n')
    results=iter([SimpleNamespace(stdout=metadata,stderr=b''),
                  SimpleNamespace(stdout=bytes(24),stderr=config+rows)])
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:next(results))
    with pytest.raises(ValueError,match='timestamp sequence'):
        decode('source.synthetic',path,width=2,height=2)


def test_declared_frame_count_mismatch_never_qualifies_count(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_pts_decode as module
    path=tmp_path/'fixture.mp4';path.write_bytes(b'synthetic')
    metadata=(b'{"format":{"duration":"2","start_time":"0"},"streams":'
              b'[{"width":2,"height":2,"start_time":"0","nb_frames":"3"}]}')
    log=(b'[Parsed_showinfo_2 @ 0x1] config in time_base: 1/1000, frame_rate: 4/1\n'
         b'[Parsed_showinfo_2 @ 0x1] n: 0 pts: 0 pts_time:0\n'
         b'[Parsed_showinfo_2 @ 0x1] n: 1 pts: 500 pts_time:0.5\n')
    results=iter([SimpleNamespace(stdout=metadata,stderr=b''),SimpleNamespace(stdout=bytes(24),stderr=log)])
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:next(results))
    result=decode('source.synthetic',path,width=2,height=2)
    assert result.timestamps==(0.0,0.5) and result.declared_frames==3 and not result.count_consistent
