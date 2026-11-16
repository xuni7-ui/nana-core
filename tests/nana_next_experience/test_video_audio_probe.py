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


def test_unclosed_silence_is_unknown_instead_of_extending_to_end(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from tools.nana_next_experience.experiments import video_audio_probe as module
    path=tmp_path/'input.mkv';path.write_bytes(b'fixture')
    responses=iter([SimpleNamespace(stdout=b'{"format":{"duration":"6"},"streams":[{"codec_type":"audio"}]}',stderr=b''),
                    SimpleNamespace(stdout=b'',stderr=b'[silencedetect] silence_start: 2.5\n')])
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:next(responses))
    result=measure(path)
    assert result['state']=='INCOMPLETE' and result['open_silence_start']==2.5
    assert result['silence_intervals']==[]
