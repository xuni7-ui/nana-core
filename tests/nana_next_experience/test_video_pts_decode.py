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
    assert result.duration_qualification=='CONTAINER_DECLARED_UNVERIFIED'


def test_frame_limit_rejects_instead_of_silent_truncation(tmp_path):
    path=tmp_path/'vfr.mp4';make_vfr(path)
    with pytest.raises(ValueError,match='frame bound'):decode('source.synthetic',path,max_frames=3)


def test_nonzero_timeline_origin_is_explicit_and_keeps_original_pts(tmp_path):
    original=tmp_path/'vfr.mp4';offset=tmp_path/'offset.mp4';make_vfr(original)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset','5','-y',str(offset)],check=True,timeout=20)
    normal=decode('source.synthetic',original);shifted=decode('source.synthetic',offset)
    assert shifted.timeline_origin=='5.000000' and shifted.video_start=='5.000000'
    assert shifted.timestamps==normal.timestamps==(0.0,0.5,1.75,2.0)
    assert shifted.pts_ticks[0]*shifted.time_base[0]/shifted.time_base[1]==5.0
    assert shifted.rgb24==normal.rgb24 and shifted.timestamp_basis=='container_relative'


def test_video_offset_from_audio_start_is_preserved_in_container_timeline(tmp_path):
    original=tmp_path/'vfr.mp4';mixed=tmp_path/'mixed.mp4';make_vfr(original)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=4','-itsoffset','1','-i',str(original),
        '-map','1:v','-map','0:a','-c:v','copy','-c:a','aac','-t','3.25','-y',str(mixed)],check=True,timeout=20)
    result=decode('source.synthetic',mixed)
    assert result.timeline_origin=='0.000000' and result.video_start=='1.000000'
    assert result.timestamps==(1.0,1.5,2.75,3.0)
    assert result.pts_ticks[0]*result.time_base[0]/result.time_base[1]==1.0


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


def test_mixed_audio_and_delayed_video_keep_common_container_timeline(tmp_path):
    from tools.nana_next_experience.experiments.video_audio_probe import measure
    original=tmp_path/'vfr.mp4';mixed=tmp_path/'mixed.mp4';make_vfr(original)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=4','-itsoffset','1','-i',str(original),
        '-map','1:v','-map','0:a','-c:v','copy','-c:a','aac','-t','3.25','-y',str(mixed)],check=True,timeout=20)
    video=decode('source.synthetic',mixed);audio=measure(mixed)
    assert video.timestamps[0]==1.0 and audio['state']=='MEASURED'
    assert len(audio['silence_intervals'])==1
    start,end=audio['silence_intervals'][0]
    assert start==pytest.approx(0,abs=.01) and end==pytest.approx(3.25,abs=.1)


def test_video_start_before_container_origin_is_not_guessed(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_pts_decode as module
    path=tmp_path/'fixture.mp4';path.write_bytes(b'synthetic')
    metadata=(b'{"format":{"duration":"2","start_time":"5"},"streams":'
              b'[{"width":2,"height":2,"start_time":"4","nb_frames":"2"}]}')
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=metadata,stderr=b''))
    with pytest.raises(ValueError,match='timing'):decode('source.synthetic',path,width=2,height=2)


def test_nonzero_matroska_container_duration_is_not_qualified_as_video_length(tmp_path):
    original=tmp_path/'vfr.mp4';offset=tmp_path/'offset.mkv';make_vfr(original)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset','5','-y',str(offset)],check=True,timeout=20)
    result=decode('source.synthetic',offset)
    assert result.timeline_origin=='5.000000'
    assert result.timestamps==(0.0,0.5,1.75,2.0)
    # Some Matroska muxers report end PTS (7.25), not necessarily the actual media duration.
    assert result.duration_qualification=='CONTAINER_DECLARED_UNVERIFIED'
    assert result.declared_frames is None and not result.count_consistent


def test_seeked_vfr_window_preserves_original_pts_with_nonzero_origin(tmp_path):
    original=tmp_path/'vfr.mp4';offset=tmp_path/'offset.mp4';make_vfr(original)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset','5','-y',str(offset)],check=True,timeout=20)
    full=decode('source.synthetic',offset)
    part=decode('source.synthetic',offset,start_seconds=.6,end_seconds=2.1)
    assert part.timestamps==(1.75,2.0) and part.pts_ticks==full.pts_ticks[-2:]
    assert part.rgb24==full.rgb24[-2*160*90*3:]
    assert part.timeline_origin=='5.000000' and part.requested_window==(.6,2.1)
    assert part.window_state=='FRAMES_DECODED_NOT_COVERAGE' and not part.count_consistent


def test_empty_vfr_window_does_not_claim_blank_or_observed_content(tmp_path):
    path=tmp_path/'vfr.mp4';make_vfr(path)
    part=decode('source.synthetic',path,start_seconds=.6,end_seconds=1.6)
    assert part.timestamps==() and part.rgb24==b''
    assert part.window_state=='NO_NEW_FRAME_DECODED_NOT_OBSERVED'


def test_adjacent_vfr_windows_preserve_all_decoded_frame_identity(tmp_path):
    path=tmp_path/'vfr.mp4';make_vfr(path);full=decode('source.synthetic',path)
    first=decode('source.synthetic',path,start_seconds=0,end_seconds=.5)
    second=decode('source.synthetic',path,start_seconds=.5,end_seconds=2.25)
    assert first.timestamps+second.timestamps==full.timestamps
    assert first.pts_ticks+second.pts_ticks==full.pts_ticks
    assert first.rgb24+second.rgb24==full.rgb24


def test_long_gop_b_frames_window_matches_full_decode_with_offset(tmp_path):
    encoders=subprocess.check_output(['ffmpeg','-hide_banner','-encoders'],stderr=subprocess.STDOUT,text=True)
    if 'libx264 ' not in encoders:
        pytest.skip('optional libx264 encoder unavailable')
    original=tmp_path/'long-gop.mp4';offset=tmp_path/'offset.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'testsrc2=s=160x90:r=10:d=20','-c:v','libx264','-g','120','-bf','3',
        '-threads','1','-y',str(original)],check=True,timeout=30)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset','5','-y',str(offset)],check=True,timeout=20)
    full=decode('source.synthetic',offset)
    frame_bytes=160*90*3
    for start,end in ((5,12),(12,17)):
        part=decode('source.synthetic',offset,start_seconds=start,end_seconds=end)
        indexes=[i for i,t in enumerate(full.timestamps) if start<=t<end]
        assert part.pts_ticks==tuple(full.pts_ticks[i] for i in indexes)
        assert part.rgb24==b''.join(full.rgb24[i*frame_bytes:(i+1)*frame_bytes] for i in indexes)


def test_long_video_uses_bounded_window_without_claiming_full_watch(tmp_path):
    path=tmp_path/'long.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=black:s=32x32:r=1:d=601','-c:v','mpeg4','-g','1','-threads','1',
        '-y',str(path)],check=True,timeout=30)
    with pytest.raises(ValueError,match='timing'):decode('source.synthetic',path,width=32,height=32)
    from tools.nana_next_experience.experiments.video_segment_windows import windows
    plan=windows('source.synthetic',601,window_seconds=600,overlap_seconds=1)
    batches=[decode('source.synthetic',path,width=32,height=32,
        start_seconds=w['start_seconds'],end_seconds=w['end_seconds']) for w in plan['windows']]
    first,part=batches
    assert [len(x.timestamps) for x in batches]==[600,2]
    assert set(first.timestamps)|set(part.timestamps)==set(range(601))
    assert set(first.timestamps)&set(part.timestamps)=={599.0}
    assert part.timestamps==(599.0,600.0)
    assert part.requested_window==(599,601) and part.window_state=='FRAMES_DECODED_NOT_COVERAGE'
    assert not part.count_consistent and plan['status']=='REQUESTS_ONLY_NOT_OBSERVED'
    with pytest.raises(ValueError,match='bounds'):
        decode('source.synthetic',path,width=32,height=32,start_seconds=0)
    with pytest.raises(ValueError,match='window'):
        decode('source.synthetic',path,width=32,height=32,start_seconds=0,end_seconds=601)
