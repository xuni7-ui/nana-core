"""Real local FFmpeg fixtures; no Nana Core, accounts or model calls."""
import json
import shutil
import subprocess

import pytest
from PIL import Image
import io
import os

from astrbot_plugin_nana_video.engine.video_perception import perceive_video

pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe')),
                              reason='FFmpeg and ffprobe required')


def test_short_video_scene_subtitle_audio_and_target_range(tmp_path):
    subtitle=tmp_path/'captions.srt'
    subtitle.write_text('1\n00:00:01,000 --> 00:00:02,500\nsynthetic caption\n\n'
                        '2\n00:00:04,000 --> 00:00:05,000\nselected caption\n',encoding='utf-8')
    video=tmp_path/'clip.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=160x90:r=2:d=8',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=8','-i',str(subtitle),
        '-filter_complex',"[0:v]drawbox=x=0:y=0:w=80:h=45:color=white:t=fill:enable='between(t,4,4.5)'[v]",
        '-map','[v]','-map','1:a','-map','2:s','-c:v','mpeg4','-c:a','aac','-c:s','mov_text',
        '-threads','1','-y',str(video)],check=True,timeout=30)
    result=perceive_video(video,time_range=(3.5,5),frame_budget=3,question='what changed?',
                          max_runtime_seconds=60,model_content=True)
    assert 1<=len(result['frames'])<=3
    assert any(4<=frame['time_seconds']<4.5 for frame in result['frames'])
    assert all(3.5<=f['time_seconds']<5 and Image.open(io.BytesIO(f['png'])).size==(160,90) for f in result['frames'])
    assert result['subtitles']['state']=='AVAILABLE_FULL_TRACK_NOT_RANGE_FILTERED'
    assert 'synthetic caption' in result['subtitles']['text']
    assert result['audio']['state']=='MEASURED' and result['transcript']['state']=='NOT_RUN_NO_TRANSCRIBER'
    context=json.loads(result['model_content']['items'][0]['text'].split('\n',1)[1])
    assert context['subtitle_model_scope']=='TARGET_WINDOW_UNVERIFIED'
    assert context['subtitles_full_track'] is None
    assert 'selected caption' in context['subtitles_target_window']
    assert 'synthetic caption' not in context['subtitles_target_window']
    assert context['audio_timeline']['requested_window']==[3.5,5]
    assert context['audio_timeline']['measured_intervals']
    assert context['audio_timeline']['timeline_basis']=='FFMPEG_NORMALIZED_CALLER_MUST_VERIFY'
    assert result['question']=='what changed?' and result['unobserved_intervals']
    assert result['outside_requested_intervals']==[(0.0,3.5),(5.0,8.0)]
    assert result['question_use']=='LITERAL_TEXT_OR_EXPLICIT_TIMESTAMP_ONLY'
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


def test_long_transcript_keeps_model_context_valid_and_status_visible(tmp_path):
    video=tmp_path/'long-text.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=32x32:r=2:d=2',
                    '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=20)
    transcript='START '+('quoted " text\n'*2000)+' END'
    result=perceive_video(video,frame_budget=1,max_runtime_seconds=30,
                          transcriber=lambda *_:transcript,model_content=True)
    content=result['model_content']
    payload=content['items'][0]['text'].split('\n',1)[1]
    context=json.loads(payload)
    assert content['context_truncated'] and len(payload)<=16000
    assert context['coverage']==result['coverage']
    assert context['unobserved_intervals']==[list(gap) for gap in result['unobserved_intervals']]
    assert context['transcript_state']=='CALLER_TRANSCRIBER_UNVERIFIED'
    assert context['audio_timeline']['state']=='NO_AUDIO'
    assert context['errors']==result['errors'] and context['warnings']==result['warnings']
    assert context['transcript_excerpt'].startswith('START ')
    assert context['transcript_excerpt'].endswith(' END')
    assert '[... omitted ...]' in context['transcript_excerpt']
    assert context['excerpt_omitted_characters']['transcript_excerpt']>0
    assert result['transcript']['text']==transcript


def test_long_subtitles_include_cue_for_selected_middle_frame(tmp_path):
    subtitle=tmp_path/'long.srt';video=tmp_path/'long-subtitle.mp4'
    def stamp(i):return f'00:{i//60:02}:{i%60:02},000'
    subtitle.write_text(''.join(f'{i+1}\n{stamp(i)} --> {stamp(i+1)}\n'+
        ('MIDDLE_CRITICAL ' if i==60 else '')+('filler '*30)+f'{i}\n\n' for i in range(120)),encoding='utf-8')
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=32x32:r=1:d=120',
        '-i',str(subtitle),'-map','0:v','-map','1:s','-c:v','mpeg4','-c:s','mov_text',
        '-threads','1','-y',str(video)],check=True,timeout=30)
    result=perceive_video(video,question='what occurs at 60 seconds?',frame_budget=1,
                          max_runtime_seconds=60,sampling='uniform',model_content=True)
    payload=result['model_content']['items'][0]['text'].split('\n',1)[1]
    context=json.loads(payload)
    assert result['model_content']['context_truncated'] and len(payload)<=16000
    assert result['frames'][0]['time_seconds']==60
    cues=context['subtitle_cues_overlapping_sampled_frames']
    assert any(c['start_seconds']==60 and 'MIDDLE_CRITICAL' in c['text'] for c in cues)
    assert context['subtitle_cue_alignment']=='TRACK_TIME_UNVERIFIED_NOT_CONTINUOUS_OBSERVATION'
    assert 'MIDDLE_CRITICAL' in result['subtitles']['text']


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


def test_chinese_seconds_question_guides_sampling(tmp_path):
    from astrbot_plugin_nana_video.engine.video_perception import _focus_candidates
    video=tmp_path/'chinese-timestamp.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=32x32:r=2:d=12',
                    '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=20)
    baseline=perceive_video(video,frame_budget=2,sampling='uniform',max_runtime_seconds=30)
    focused=perceive_video(video,question='在5秒时出现了什么？',frame_budget=2,
                           sampling='uniform',max_runtime_seconds=30)
    assert not any(5<=f['time_seconds']<6 for f in baseline['frames'])
    assert any(5<=f['time_seconds']<6 and f['selection_reason']=='QUESTION_TIMESTAMP'
               for f in focused['frames'])
    assert _focus_candidates('第5秒的画面',None,0,12)==[(5.0,'QUESTION_TIMESTAMP')]
    assert _focus_candidates('5secondsuffix',None,0,12)==[]


def test_minutes_seconds_question_uses_the_full_timestamp(tmp_path):
    from astrbot_plugin_nana_video.engine.video_perception import _focus_candidates
    video=tmp_path/'minute-second.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=32x32:r=1:d=100',
                    '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=20)
    for question in ('1分23秒发生了什么？','1分钟23秒时的画面','1:23秒发生了什么？'):
        assert _focus_candidates(question,None,0,100)==[(83.0,'QUESTION_TIMESTAMP')]
    assert _focus_candidates('1分75秒发生了什么？',None,0,100)==[]
    focused=perceive_video(video,question='1分23秒时的画面',frame_budget=1,
                           sampling='uniform',max_runtime_seconds=30)
    assert [f['time_seconds'] for f in focused['frames']]==[83.0]


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
                          max_runtime_seconds=60,ocr=True,asr='pocketsphinx',asr_max_seconds=2,model_content=True)
    assert result['focus_hints_applied']==1 and any(f['selection_reason']=='QUESTION_TIMESTAMP' for f in result['frames'])
    assert any('ALARM' in f['ocr'].get('text','') for f in result['frames'])
    assert result['transcript']['state']=='POCKETSPHINX_ENGLISH_UNVERIFIED'
    assert 'hello' in result['transcript']['text'] and result['transcript']['words']
    assert result['transcript']['timeline_basis']=='FFMPEG_NORMALIZED_CALLER_MUST_VERIFY'
    assert result['transcript']['processed_window']==(0.0,2.0) and result['transcript']['truncated'] is True
    content=result['model_content']
    assert content['format']=='OPENAI_COMPATIBLE_CHAT_CONTENT' and content['token_cost']=='UNKNOWN_NOT_MEASURED'
    assert len([x for x in content['items'] if x['type']=='image_url'])==len(result['frames'])
    assert any('ALARM' in x.get('text','') for x in content['items'] if x['type']=='text')
    assert '"transcript_truncated":true' in content['items'][0]['text']


def test_optional_chinese_tesseract_data_on_real_ffmpeg_video(tmp_path):
    from pathlib import Path
    data=os.environ.get('NANA_TEST_TESSDATA');font=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
    if not data or not (Path(data)/'chi_sim.traineddata').is_file() or not font.is_file() or not shutil.which('tesseract'):
        pytest.skip('optional Chinese Tesseract data and CJK font unavailable')
    video=tmp_path/'chinese.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=640x360:r=2:d=3',
        '-vf',f'drawtext=fontfile={font}:text=中文测试:fontcolor=white:fontsize=90:x=100:y=100',
        '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=30)
    result=perceive_video(video,frame_budget=1,max_runtime_seconds=30,ocr=True,
                          ocr_language='chi_sim',ocr_data_dir=data)
    assert result['frames'][0]['ocr']['state']=='TESSERACT_UNVERIFIED'
    assert '中文测试' in result['frames'][0]['ocr']['text'].replace(' ','')


def test_ocr_probes_find_question_word_at_same_output_frame_budget(tmp_path):
    from pathlib import Path
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    if not font.is_file() or not shutil.which('tesseract'):pytest.skip('optional OCR and font unavailable')
    video=tmp_path/'brief-text.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=640x360:r=2:d=12',
        '-vf',f"drawtext=fontfile={font}:text=ALARM:fontcolor=white:fontsize=100:x=100:y=100:enable='between(t,5,5.5)'",
        '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=30)
    baseline=perceive_video(video,frame_budget=4,max_runtime_seconds=60,sampling='uniform')
    result=perceive_video(video,question='find ALARM',frame_budget=4,max_runtime_seconds=90,
                          sampling='uniform',ocr=True,ocr_probe_budget=12)
    assert len(baseline['frames'])<=4 and len(result['frames'])<=4
    assert not any(5<=f['time_seconds']<6 for f in baseline['frames'])
    assert any(5<=f['time_seconds']<6 and f['selection_reason']=='QUESTION_OCR_MATCH' for f in result['frames'])
    assert 1<=len(result['ocr_probes'])<=12 and any(p.get('matched') for p in result['ocr_probes'])
    assert result['budget']['ocr_probe_limit']==12


def test_ocr_probe_retries_decimal_boundary_and_continues(tmp_path, monkeypatch):
    from astrbot_plugin_nana_video.engine import video_perception as module
    video=tmp_path/'boundary.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=32x32:r=10:d=8',
                    '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=30)
    original=module.decode
    failed=[]
    def decoder(*args, **kwargs):
        if kwargs['start_seconds']>0 and not failed:
            failed.append(kwargs['start_seconds'])
            raise ValueError('decoded frame outside requested window')
        return original(*args, **kwargs)
    monkeypatch.setattr(module,'decode',decoder)
    monkeypatch.setattr(module,'tesseract_ocr',lambda *args, **kwargs: '')
    result=module.perceive_video(video,question='find missing word',frame_budget=2,
                                max_runtime_seconds=60,sampling='uniform',ocr=True,ocr_probe_budget=3)
    assert len(result['ocr_probes'])==3
    retried=result['ocr_probes'][1]
    assert retried['state']=='TESSERACT_UNVERIFIED'
    assert retried['retry_start_seconds']>retried['requested_seconds']
    assert retried['time_seconds']>=retried['retry_start_seconds']


def test_larger_output_retains_small_text_without_changing_timestamp(tmp_path):
    from pathlib import Path
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    if not font.is_file() or not shutil.which('tesseract'):pytest.skip('optional OCR and font unavailable')
    video=tmp_path/'small-text.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=640x360:r=2:d=2',
        '-vf',f'drawtext=fontfile={font}:text=WARNING 4392:fontcolor=white:fontsize=14:x=25:y=30',
        '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=30)
    small=perceive_video(video,frame_budget=1,sampling='uniform',ocr=True,max_runtime_seconds=60)
    detail=perceive_video(video,frame_budget=1,sampling='uniform',ocr=True,max_runtime_seconds=60,
                          output_size=(640,360),model_content=True)
    assert small['frames'][0]['time_seconds']==detail['frames'][0]['time_seconds']
    assert Image.open(io.BytesIO(detail['frames'][0]['png'])).size==(640,360)
    assert detail['budget']['output_size']==(640,360)
    assert 'WARNING 4392' in detail['frames'][0]['ocr']['text']
    assert len(detail['frames'][0]['png'])>len(small['frames'][0]['png'])
    with pytest.raises(ValueError,match='invalid perception request'):
        perceive_video(video,output_size=(1024,1024))


def test_high_resolution_ocr_probe_finds_brief_small_text(tmp_path):
    from pathlib import Path
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    if not font.is_file() or not shutil.which('tesseract'):pytest.skip('optional OCR and font unavailable')
    video=tmp_path/'brief-small-text.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=640x360:r=2:d=8',
        '-vf',f"drawtext=fontfile={font}:text=WARNING 4392:fontcolor=white:fontsize=14:x=25:y=30:enable='between(t,3.5,4)'",
        '-c:v','mpeg4','-threads','1','-y',str(video)],check=True,timeout=30)
    common=dict(question='find WARNING',frame_budget=2,sampling='uniform',ocr=True,
                ocr_probe_budget=3,max_runtime_seconds=60)
    small=perceive_video(video,**common)
    detail=perceive_video(video,output_size=(640,360),**common)
    assert not any(p.get('matched') for p in small['ocr_probes'])
    assert any(p.get('matched') and 3.5<=p['time_seconds']<4.5 for p in detail['ocr_probes'])
    assert any(f['selection_reason']=='QUESTION_OCR_MATCH' and 3.5<=f['time_seconds']<4.5
               for f in detail['frames'])
    assert len(detail['frames'])<=2 and len(detail['ocr_probes'])<=3
