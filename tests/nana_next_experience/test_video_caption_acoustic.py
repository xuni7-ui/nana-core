import pytest
from tools.nana_next_experience.experiments.video_caption_acoustic import review


def cue(name,start,end):
    return {'cue_id':name,'source_id':'source.caption', 'start':start,'end':end}


def test_silent_caption_is_review_only_and_tone_is_not_speech_proof():
    audio={'state':'MEASURED','duration':6,'silence_intervals':[(0,3),(4,6)]}
    output=review([cue('silent',1,2),cue('tone',3.1,3.9)],audio,
                  acoustic_source_id='source.audio',timeline_aligned=True)
    assert [x['status'] for x in output]==['REVIEW_SILENCE_OVERLAP','BELOW_SILENCE_REVIEW_THRESHOLD']
    assert output[0]['caption_source_id']=='source.caption' and output[0]['acoustic_source_id']=='source.audio'
    assert all('not speech' in x['meaning'] for x in output)


def test_no_audio_incomplete_or_unaligned_time_never_claims_consistency():
    for state,aligned in [('NO_AUDIO',True),('INCOMPLETE',True),('MEASURED',False)]:
        result=review([cue('x',1,2)],{'state':state,'duration':6,'silence_intervals':[(0,3)]},
                      acoustic_source_id='source.audio',timeline_aligned=aligned)
        assert result[0]['status']=='UNKNOWN' and result[0]['silence_overlap_fraction'] is None


def test_rejects_unsafe_or_invalid_spans_without_silently_rewriting_sources():
    audio={'state':'MEASURED','duration':6,'silence_intervals':[(0,3),(2,4)]}
    with pytest.raises(ValueError):review([cue('x',1,2)],audio,acoustic_source_id='audio',timeline_aligned=True)
    audio['silence_intervals']=[]
    with pytest.raises(ValueError):review([{**cue('x',1,2),'text':'not accepted'}],audio,acoustic_source_id='audio')
    with pytest.raises(ValueError):review([cue('x',1,7)],audio,acoustic_source_id='audio')
    with pytest.raises(ValueError):review([cue('x',1,2),cue('x',2,3)],audio,acoustic_source_id='audio')


def test_real_measured_audio_intervals_feed_source_bound_timing_review(tmp_path):
    import shutil
    import subprocess
    from tools.nana_next_experience.experiments.video_audio_probe import measure
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('optional FFmpeg unavailable')
    path=tmp_path/'audio.mkv'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=3',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=1',
        '-f','lavfi','-i','anullsrc=r=16000:cl=mono:d=2',
        '-filter_complex','[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]',
        '-map','[a]','-c:a','pcm_s16le','-y',str(path)],check=True,timeout=20)
    result=review([cue('silent',1,2),cue('tone',3.1,3.9)],measure(path),
                  acoustic_source_id='source.fixture.audio',timeline_aligned=True)
    assert [x['status'] for x in result]==['REVIEW_SILENCE_OVERLAP','BELOW_SILENCE_REVIEW_THRESHOLD']


def test_zero_duration_caption_remains_unknown():
    audio={'state':'MEASURED','duration':6,'silence_intervals':[(0,3)]}
    result=review([cue('instant',1,1)],audio,acoustic_source_id='audio',timeline_aligned=True)
    assert result[0]['status']=='UNKNOWN' and result[0]['silence_overlap_fraction'] is None


def test_nanalink_projection_rechecks_original_source_after_withdrawal(tmp_path):
    from types import SimpleNamespace
    from nana_core.clock import Clock
    from nana_core.contracts import CoreError
    from nana_core.continuity.memory import MemoryService
    from nana_core.life.bilibili import BilibiliSourceAdapter, BilibiliPublicTransport
    from nana_core.life.bilibili_frames import BilibiliFrameService
    from tests.living_release_v4.bilibili_loopback import counterpart
    from tests.world_loop.helpers import fresh, policy
    from tools.nana_next_experience.experiments.video_caption_acoustic import review_storyboard
    with counterpart() as (opener,platform), fresh(tmp_path/'subject.db',Clock()) as runtime:
        platform['video_duration']=12
        transport=BilibiliPublicTransport(authorized=True,origin='SYNTHETIC_FIXTURE',request_limit=9)
        transport.opener=opener
        reading=transport.read_video('BV1t55v6DE2v',visual=True)
        app=SimpleNamespace(runtime=runtime,policy=policy())
        source=BilibiliSourceAdapter(app).ingest(reading)
        BilibiliFrameService(app).capture(source,reading.frames)
        acoustic={'state':'MEASURED','duration':12,'silence_intervals':[(0,3)]}
        result=review_storyboard(app,source,scope='world',privacy_classes=('PROJECT',),
            acoustic=acoustic,acoustic_source_id=source,timeline_aligned=True)
        assert result['scope']=='world' and result['privacy_class']=='PROJECT'
        assert result['account_binding']=='PUBLIC_SOURCE_NOT_ACCOUNT_ATTRIBUTED'
        assert result['timeline_alignment']=='CALLER_ATTESTED' and result['storage']=='NONE'
        assert len(result['reviews'])==1 and result['reviews'][0]['status']=='REVIEW_SILENCE_OVERLAP'
        assert result['reviews'][0]['caption_source_id']==result['reviews'][0]['acoustic_source_id']==source
        with pytest.raises(ValueError,match='unverified source'):
            review_storyboard(app,source,scope='world',privacy_classes=('PROJECT',),
                acoustic=acoustic,acoustic_source_id='other.source',timeline_aligned=True)
        MemoryService(runtime.store,runtime.authority).forget(source,runtime.authority)
        with pytest.raises(CoreError):
            review_storyboard(app,source,scope='world',privacy_classes=('PROJECT',),
                acoustic=acoustic,acoustic_source_id=source,timeline_aligned=True)
