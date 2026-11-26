"""Real local FFmpeg fixtures; no Nana Core, accounts or model calls."""
import shutil
import subprocess

import pytest
from PIL import Image
import io

from tools.nana_next_experience.experiments.video_perception import perceive_video

pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe')),
                              reason='FFmpeg and ffprobe required')


def test_short_video_scene_subtitle_audio_and_target_range(tmp_path):
    subtitle=tmp_path/'captions.srt'
    subtitle.write_text('1\n00:00:01,000 --> 00:00:02,500\nsynthetic caption\n',encoding='utf-8')
    video=tmp_path/'clip.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=160x90:r=2:d=8',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=8','-i',str(subtitle),
        '-filter_complex',"[0:v]drawbox=x=0:y=0:w=80:h=45:color=white:t=fill:enable='between(t,4,4.5)'[v]",
        '-map','[v]','-map','1:a','-map','2:s','-c:v','mpeg4','-c:a','aac','-c:s','mov_text',
        '-threads','1','-y',str(video)],check=True,timeout=30)
    result=perceive_video(video,time_range=(3.5,5),frame_budget=3,question='what changed?',max_runtime_seconds=60)
    assert 1<=len(result['frames'])<=3
    assert any(4<=frame['time_seconds']<4.5 for frame in result['frames'])
    assert all(3.5<=f['time_seconds']<5 and Image.open(io.BytesIO(f['png'])).size==(160,90) for f in result['frames'])
    assert result['subtitles']['state']=='AVAILABLE_FULL_TRACK_NOT_RANGE_FILTERED'
    assert 'synthetic caption' in result['subtitles']['text']
    assert result['audio']['state']=='MEASURED' and result['transcript']['state']=='NOT_RUN_NO_TRANSCRIBER'
    assert result['question']=='what changed?' and result['unobserved_intervals']
    assert result['outside_requested_intervals']==[(0.0,3.5),(5.0,8.0)]
    assert result['question_use']=='LITERAL_SUBTITLE_OR_EXPLICIT_TIMESTAMP_ONLY'
    assert all(c['qualification']=='SPARSE_FRAME_DIFFERENCE_NOT_CONTINUOUS_MOTION' for c in result['sparse_visual_changes'])
    assert result['output_png_bytes']==sum(len(f['png']) for f in result['frames'])
    assert result['output_sizes']['subtitle_utf8_bytes']==len(result['subtitles']['text'].encode('utf-8'))


def test_long_video_distributes_bounded_frames_and_reports_unobserved(tmp_path):
    video=tmp_path/'long.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=32x32:r=1:d=620',
                    '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=60)
    result=perceive_video(video,frame_budget=4,max_runtime_seconds=60)
    times=[f['time_seconds'] for f in result['frames']]
    assert 1<=len(times)<=4 and times==sorted(times)
    assert times[0]==0 and times[-1]>=619
    assert result['scene_scan']=='NOT_RUN_LONG_OR_OFFSET'
    assert result['audio']['state']=='NO_AUDIO'
    assert result['unobserved_intervals'] and result['coverage']=='POINT_SAMPLES_ONLY_NOT_CONTINUOUS_OBSERVATION'


def test_external_transcription_is_explicit_and_failure_is_visible(tmp_path):
    video=tmp_path/'clip.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=32x32:r=2:d=2',
                    '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=20)
    calls=[]
    def transcriber(path,start,end):calls.append((path,start,end));return 'synthetic transcript'
    result=perceive_video(video,frame_budget=1,max_runtime_seconds=30,transcriber=transcriber)
    assert result['transcript']=={'state':'CALLER_TRANSCRIBER_UNVERIFIED','text':'synthetic transcript'}
    assert len(calls)==1 and calls[0][1:]==(0,2)
    def fail(*_):raise RuntimeError('private detail should not appear')
    result=perceive_video(video,frame_budget=1,max_runtime_seconds=30,transcriber=fail)
    assert result['transcript']['state']=='TRANSCRIBER_FAILED' and 'TRANSCRIBER_FAILED' in result['errors']


def test_question_subtitle_guides_same_budget_to_relevant_window(tmp_path):
    subtitle=tmp_path/'captions.srt';subtitle.write_text('1\n00:00:05,000 --> 00:00:06,000\nFALCON arrives\n',encoding='utf-8')
    video=tmp_path/'subtitles.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=160x90:r=2:d=12',
                    '-i',str(subtitle),'-map','0:v','-map','1:s','-c:v','mpeg4','-c:s','mov_text',
                    '-threads','1','-y',str(video)],check=True,timeout=30)
    baseline=perceive_video(video,frame_budget=4,max_runtime_seconds=60,sampling='uniform')
    focused=perceive_video(video,question='When does FALCON arrive?',frame_budget=4,max_runtime_seconds=60)
    assert len(baseline['frames'])<=4 and len(focused['frames'])<=4
    assert not any(5<=f['time_seconds']<6 for f in baseline['frames'])
    assert any(5<=f['time_seconds']<6 and f['selection_reason']=='QUESTION_SUBTITLE_MATCH' for f in focused['frames'])
    assert focused['focus_hints_applied']==1


def test_real_local_ocr_and_offline_asr(tmp_path):
    pytest.importorskip('pocketsphinx')
    if not shutil.which('tesseract'):pytest.skip('optional Tesseract unavailable')
    filters=subprocess.check_output(['ffmpeg','-hide_banner','-filters'],text=True,stderr=subprocess.DEVNULL)
    if ' flite ' not in filters:pytest.skip('optional FFmpeg flite unavailable')
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if not __import__('pathlib').Path(font).is_file():pytest.skip('test font unavailable')
    video=tmp_path/'speech.mkv'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=640x360:r=2:d=4',
                    '-f','lavfi','-i',"flite=text='hello world this is a test':voice=slt",
                    '-vf',f'drawtext=fontfile={font}:text=ALARM:fontcolor=white:fontsize=100:x=100:y=100',
                    '-map','0:v','-map','1:a','-c:v','mpeg4','-c:a','pcm_s16le','-t','4',
                    '-threads','1','-y',str(video)],check=True,timeout=30)
    result=perceive_video(video,question='What is shown at 1 second?',frame_budget=2,
                          max_runtime_seconds=60,ocr=True,asr='pocketsphinx',model_content=True)
    assert result['focus_hints_applied']==1 and any(f['selection_reason']=='QUESTION_TIMESTAMP' for f in result['frames'])
    assert any('ALARM' in f['ocr'].get('text','') for f in result['frames'])
    assert result['transcript']['state']=='POCKETSPHINX_ENGLISH_UNVERIFIED'
    assert 'hello' in result['transcript']['text'] and result['transcript']['words']
    assert result['transcript']['timeline_basis']=='FFMPEG_NORMALIZED_CALLER_MUST_VERIFY'
    content=result['model_content']
    assert content['format']=='OPENAI_COMPATIBLE_CHAT_CONTENT' and content['token_cost']=='UNKNOWN_NOT_MEASURED'
    assert len([x for x in content['items'] if x['type']=='image_url'])==len(result['frames'])
    assert any('ALARM' in x.get('text','') for x in content['items'] if x['type']=='text')
