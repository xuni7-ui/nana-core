import shutil
import subprocess
import pytest
from tools.nana_next_experience.experiments.video_audio_probe import measure

pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),
                               reason='optional FFmpeg unavailable')


def test_silence_is_measured_but_never_asserts_speech(tmp_path):
    path=tmp_path/'audio.mkv'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=3',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=1',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=2',
        '-filter_complex','[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]',
        '-map','[a]','-c:a','pcm_s16le','-y',str(path)],check=True,timeout=20)
    result=measure(path)
    assert result['state']=='MEASURED' and len(result['silence_intervals'])==2
    first,last=result['silence_intervals']
    assert first[0]==0 and 2.9<=first[1]<=3.1
    assert 3.9<=last[0]<=4.1 and 5.9<=last[1]<=6.0
    assert 'not speech' in result['meaning']


def test_no_audio_is_not_a_silence_observation(tmp_path):
    path=tmp_path/'video.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=black:s=32x32:r=2:d=2','-an','-c:v','mpeg4','-y',str(path)],check=True,timeout=20)
    result=measure(path)
    assert result['state']=='NO_AUDIO' and result['silence_intervals']==[]
    assert 'unknown' in result['meaning']
    window=measure(path,start_seconds=.5,end_seconds=1)
    assert window['state']=='NO_AUDIO' and window['requested_window']==(.5,1)


def test_unclosed_silence_is_unknown_instead_of_extending_to_end(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_audio_probe as module
    path=tmp_path/'input.mkv';path.write_bytes(b'fixture')
    responses=iter([SimpleNamespace(stdout=b'{"format":{"duration":"6"},"streams":[{"codec_type":"audio"}]}',stderr=b''),
                    SimpleNamespace(stdout=b'',stderr=b'[silencedetect] silence_start: 2.5\n')])
    monkeypatch.setattr(module,'_run_bounded',lambda *args,**kwargs:next(responses))
    result=measure(path)
    assert result['state']=='INCOMPLETE' and result['open_silence_start']==2.5
    assert result['silence_intervals']==[]
    assert result['coverage_state']=='UNKNOWN'


def test_unclosed_silence_cannot_hide_bad_frame_timing(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_audio_probe as module
    path=tmp_path/'input.mkv';path.write_bytes(b'fixture')
    responses=iter([SimpleNamespace(stdout=b'{"format":{"duration":"6"},"streams":[{"codec_type":"audio"}]}',stderr=b''),
                    SimpleNamespace(stdout=b'',stderr=(
                        b'[Parsed_ashowinfo_1 @ 0x1] n:0 pts:0 pts_time:0 rate:1 nb_samples:6\n'
                        b'[Parsed_ashowinfo_1 @ 0x1] n:2 pts:1 pts_time:1 rate:1 nb_samples:1\n'
                        b'[silencedetect] silence_start: 2.5\n'))])
    monkeypatch.setattr(module,'_run_bounded',lambda *args,**kwargs:next(responses))
    result=measure(path)
    assert result['state']=='INCOMPLETE' and result['open_silence_start']==2.5
    assert result['measured_intervals']==[(0.0,6.0)] and result['coverage_state']=='UNKNOWN'


def test_delayed_audio_has_explicit_coverage_and_outside_subtitles_unknown(tmp_path):
    from tools.nana_next_experience.experiments.video_caption_acoustic import review
    audio=tmp_path/'audio.mkv';video=tmp_path/'delayed.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=3',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=1',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=2',
        '-filter_complex','[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]',
        '-map','[a]','-c:a','pcm_s16le','-y',str(audio)],check=True,timeout=20)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','color=black:s=160x90:r=4:d=8','-itsoffset','1','-i',str(audio),
        '-map','0:v','-map','1:a','-c:v','mpeg4','-c:a','aac','-t','8','-threads','1',
        '-y',str(video)],check=True,timeout=20)
    acoustic=measure(video)
    assert acoustic['state']=='MEASURED' and acoustic['coverage_state']=='PARTIAL'
    a,b=acoustic['measured_intervals'][0]
    assert .8<a<1.1 and 6.9<b<7.2
    cues=[{'cue_id':str(i),'source_id':'source.fixture','start':start,'end':end}
          for i,(start,end) in enumerate([(.1,.5),(2,2.5),(7.5,7.8)])]
    result=review(cues,acoustic,acoustic_source_id='source.fixture',timeline_aligned=True)
    assert [x['status'] for x in result]==['UNKNOWN','REVIEW_SILENCE_OVERLAP','UNKNOWN']


def test_audio_timestamp_gap_is_not_filled_in_as_observed(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_audio_probe as module
    path=tmp_path/'input.mkv';path.write_bytes(b'fixture')
    meta=b'{"format":{"duration":"4"},"streams":[{"codec_type":"audio"}]}'
    log=(b'[Parsed_ashowinfo_2 @ 0x1] n:0 pts:0 pts_time:0 fmt:s16 channels:1 rate:10 nb_samples:10\n'
         b'[Parsed_ashowinfo_2 @ 0x1] n:1 pts:30 pts_time:3 fmt:s16 channels:1 rate:10 nb_samples:10\n')
    responses=iter([SimpleNamespace(stdout=meta,stderr=b''),SimpleNamespace(stdout=b'',stderr=log)])
    monkeypatch.setattr(module,'_run_bounded',lambda *args,**kwargs:next(responses))
    result=measure(path)
    assert result['state']=='MEASURED' and result['coverage_state']=='PARTIAL'
    assert result['measured_intervals']==[(0.0,1.0),(3.0,4.0)]


def test_nonzero_matroska_origin_does_not_expand_audio_coverage(tmp_path):
    from tools.nana_next_experience.experiments.video_caption_acoustic import review
    original=tmp_path/'tone.mkv';offset=tmp_path/'offset.mkv'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'sine=frequency=440:sample_rate=16000:duration=6','-c:a','pcm_s16le','-y',str(original)],
        check=True,timeout=20)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),
        '-c','copy','-output_ts_offset','5','-y',str(offset)],check=True,timeout=20)
    acoustic=measure(offset)
    assert acoustic['duration']==pytest.approx(11) and acoustic['coverage_state']=='PARTIAL'
    assert acoustic['measured_intervals'][0][1]==pytest.approx(6,abs=.01)
    window=measure(offset,start_seconds=1,end_seconds=3)
    assert window['state']=='MEASURED' and window['measured_intervals'][0]==pytest.approx((1,3),abs=.02)
    assert window['coverage_state']=='PARTIAL' and window['requested_window']==(1,3)
    cue={'cue_id':'outside','source_id':'fixture','start':7,'end':8}
    result=review([cue],acoustic,acoustic_source_id='fixture',timeline_aligned=True)
    assert result[0]['status']=='UNKNOWN'


def test_long_audio_window_keeps_global_time_and_unread_regions_unknown(tmp_path):
    from tools.nana_next_experience.experiments.video_caption_acoustic import review
    path=tmp_path/'long.flac'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=8000:duration=618',
        '-f','lavfi','-i','anullsrc=r=8000:cl=mono:d=2',
        '-filter_complex','[0:a][1:a]concat=n=2:v=0:a=1[a]',
        '-map','[a]','-c:a','flac','-y',str(path)],check=True,timeout=30)
    with pytest.raises(ValueError,match='duration'):measure(path)
    for start,end in ((None,3),(-1,3),(1,602),(619,621),(float('nan'),3)):
        with pytest.raises(ValueError,match='window'):measure(path,start_seconds=start,end_seconds=end)
    acoustic=measure(path,start_seconds=617,end_seconds=620)
    assert acoustic['requested_window']==(617,620) and acoustic['coverage_state']=='PARTIAL'
    assert acoustic['state']=='MEASURED' and acoustic['measured_intervals'][0][0]==pytest.approx(617,abs=.02)
    assert acoustic['measured_intervals'][-1][1]==pytest.approx(620,abs=.02)
    assert acoustic['silence_intervals'][0][0]==pytest.approx(618,abs=.03)
    cues=[{'cue_id':'outside','source_id':'source.fixture','start':20,'end':21},
          {'cue_id':'inside','source_id':'source.fixture','start':618.5,'end':619.5}]
    checked=review(cues,acoustic,acoustic_source_id='source.fixture',timeline_aligned=True)
    assert [row['status'] for row in checked]==['UNKNOWN','REVIEW_SILENCE_OVERLAP']
    assert all('not speech' in row['meaning'] for row in checked)
    # Reuse the existing window planner; planning itself is not observation.
    from tools.nana_next_experience.experiments.video_segment_windows import windows
    plan=windows('source.fixture',620,window_seconds=600,overlap_seconds=1)
    assert plan['status']=='REQUESTS_ONLY_NOT_OBSERVED' and len(plan['windows'])==2
    samples=[measure(path,start_seconds=w['start_seconds'],end_seconds=w['end_seconds']) for w in plan['windows']]
    assert samples[0]['measured_intervals'][0][0]==pytest.approx(0,abs=.02)
    assert samples[0]['measured_intervals'][-1][1]==pytest.approx(600,abs=.02)
    assert samples[1]['measured_intervals'][0][0]==pytest.approx(599,abs=.02)
    assert samples[1]['measured_intervals'][-1][1]==pytest.approx(620,abs=.02)
    assert all(s['state']=='MEASURED' and s['coverage_state']=='PARTIAL' for s in samples)


def test_audio_window_preserves_delayed_stream_gap(tmp_path):
    from tools.nana_next_experience.experiments.video_caption_acoustic import review
    path=tmp_path/'delayed.mkv'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','color=black:s=32x32:r=2:d=4',
        '-itsoffset','1','-f','lavfi','-i','anullsrc=r=8000:cl=mono:d=2',
        '-map','0:v','-map','1:a','-c:v','mpeg4','-c:a','pcm_s16le','-t','4','-threads','1',
        '-y',str(path)],check=True,timeout=20)
    result=measure(path,start_seconds=.5,end_seconds=3.5)
    assert result['state']=='MEASURED' and result['coverage_state']=='PARTIAL'
    assert result['measured_intervals'][0][0]==pytest.approx(1,abs=.02)
    assert result['measured_intervals'][-1][1]==pytest.approx(3,abs=.03)
    empty=measure(path,start_seconds=3.2,end_seconds=3.8)
    assert empty['state']=='INCOMPLETE' and empty['coverage_state']=='UNKNOWN'
    assert empty['measured_intervals']==[] and empty['requested_window']==(3.2,3.8)
    cues=[{'cue_id':'unread','source_id':'source.fixture','start':.6,'end':.9},
          {'cue_id':'silent','source_id':'source.fixture','start':1.5,'end':2.5},
          {'cue_id':'after','source_id':'source.fixture','start':3.1,'end':3.4}]
    assert [x['status'] for x in review(cues,result,acoustic_source_id='source.fixture',timeline_aligned=True)]==\
        ['UNKNOWN','REVIEW_SILENCE_OVERLAP','UNKNOWN']


def test_fractional_window_silence_boundaries_use_exact_decimal_offset(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_audio_probe as module
    path=tmp_path/'fixture.mkv';path.write_bytes(b'fixture')
    meta=b'{"format":{"duration":"1"},"streams":[{"codec_type":"audio"}]}'
    log=(b'[Parsed_ashowinfo_2 @ 0x1] n:0 pts:0 pts_time:0 fmt:s16 channels:1 rate:10 nb_samples:8\n'
         b'[silencedetect] silence_start: 0.1\n[silencedetect] silence_end: 0.3\n')
    responses=iter([SimpleNamespace(stdout=meta,stderr=b''),SimpleNamespace(stdout=b'',stderr=log)])
    monkeypatch.setattr(module,'_run_bounded',lambda *args,**kwargs:next(responses))
    result=measure(path,start_seconds=.2,end_seconds=1)
    assert result['silence_intervals']==[(.3,.5)]
    assert result['measured_intervals']==[(.2,1.0)] and result['coverage_state']=='PARTIAL'


def test_audio_subprocess_bounds_output_before_child_can_finish(tmp_path):
    import sys
    from tools.nana_next_experience.experiments.video_audio_probe import _run_bounded,AudioProbeOutputBound,AudioProbeUnavailable
    marker=tmp_path/'finished'
    for stream in ('stdout','stderr'):
        script=("import sys,pathlib;out=getattr(sys,"+repr(stream)+").buffer;"
                "out.write(b'x'*(1024*1024));out.flush();pathlib.Path(sys.argv[1]).write_text('done')")
        with pytest.raises(AudioProbeOutputBound):
            _run_bounded([sys.executable,'-c',script,str(marker)],timeout=5,stdout_limit=1024,stderr_limit=1024)
        assert not marker.exists()
    result=_run_bounded([sys.executable,'-c',"import sys;print('ok');print('warn',file=sys.stderr)"],
                        timeout=5,stdout_limit=1024,stderr_limit=1024)
    assert result.stdout==b'ok\n' and result.stderr==b'warn\n'
    script=("import sys;"
            "[(sys.stdout.buffer.write(b'o'*32768),sys.stdout.flush(),"
            "sys.stderr.buffer.write(b'e'*32768),sys.stderr.flush()) for _ in range(4)]")
    result=_run_bounded([sys.executable,'-c',script],timeout=5,stdout_limit=131072,stderr_limit=131072)
    assert result.stdout==b'o'*131072 and result.stderr==b'e'*131072
    with pytest.raises(AudioProbeUnavailable):
        _run_bounded([sys.executable,'-c','raise SystemExit(3)'],timeout=5,stdout_limit=1024,stderr_limit=1024)
    with pytest.raises(AudioProbeUnavailable):
        _run_bounded([sys.executable,'-c','import time;time.sleep(2)'],timeout=.1,stdout_limit=1024,stderr_limit=1024)


def test_audio_many_small_packets_stops_at_output_bound(tmp_path):
    from tools.nana_next_experience.experiments.video_audio_probe import AudioProbeOutputBound
    path=tmp_path/'tiny-packets.nut'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'anullsrc=r=8000:cl=mono:d=5','-af','asetnsamples=n=1:p=0',
        '-c:a','pcm_s16le','-y',str(path)],check=True,timeout=20)
    assert path.stat().st_size < 200000
    with pytest.raises(AudioProbeOutputBound):measure(path)


def test_bounded_runner_matches_original_runner_on_valid_audio(tmp_path,monkeypatch):
    from tools.nana_next_experience.experiments import video_audio_probe as module
    path=tmp_path/'valid.mkv'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'anullsrc=r=8000:cl=mono:d=3','-f','lavfi','-i','sine=frequency=440:sample_rate=8000:duration=1',
        '-filter_complex','[0:a][1:a]concat=n=2:v=0:a=1[a]','-map','[a]',
        '-c:a','pcm_s16le','-y',str(path)],check=True,timeout=20)
    def old_runner(command,*,timeout,stdout_limit,stderr_limit):
        return subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,timeout=timeout,check=True)
    for kwargs in ({},{'start_seconds':1,'end_seconds':4}):
        with monkeypatch.context() as patch:
            patch.setattr(module,'_run_bounded',old_runner)
            baseline=measure(path,**kwargs)
        assert measure(path,**kwargs)==baseline


@pytest.mark.parametrize('audio_order,first_is_silent',[(('1:a','2:a'),False),(('2:a','1:a'),True)])
def test_audio_probe_measures_only_the_original_first_audio_stream(tmp_path,audio_order,first_is_silent):
    path=tmp_path/'multitrack.mkv'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=black:s=32x32:r=2:d=2','-f','lavfi','-i','sine=frequency=440:sample_rate=8000:duration=2',
        '-f','lavfi','-i','anullsrc=r=8000:cl=mono:d=2',
        '-map','0:v','-map',audio_order[0],'-map',audio_order[1],
        '-c:v','mpeg4','-c:a','pcm_s16le','-threads','1','-y',str(path)],check=True,timeout=20)
    result=measure(path)
    assert result['state']=='MEASURED' and result['coverage_state']=='FULL'
    if first_is_silent:
        assert result['silence_intervals'][0][0]==0 and result['silence_intervals'][0][1]==pytest.approx(2,abs=.02)
    else:assert result['silence_intervals']==[]
