"""Real local FFmpeg and original Store/MediaCache; no model or platform account."""
import hashlib
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh,policy,providers
from tools.nana_next_experience.experiments.video_guarded_audio import guarded_audio_window


pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe','bwrap')),
                              reason='optional FFmpeg and original Core sandbox required')


def video_bytes(tmp_path):
    path=tmp_path/'synthetic.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
        'color=black:s=32x32:r=2:d=4','-f','lavfi','-i','anullsrc=r=8000:cl=mono:d=4',
        '-map','0:v','-map','1:a','-c:v','mpeg4','-c:a','aac','-threads','1','-t','4',
        '-y',str(path)],check=True,timeout=20)
    return path.read_bytes()


def test_guarded_audio_uses_original_hash_and_does_not_create_observation(tmp_path):
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us()
        source=PublicMediaSource(source_id='synthetic-audio-video',modality='VIDEO',origin='SYNTHETIC',
                                 event_time_us=now,observed_time_us=now)
        mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,source,entity_id='observer',scope='world')
        cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            handle=cache.put([data],source_ref=mid,media_type='video/mp4')
            records_before=len(runtime.store.all('continuity_records'))
            from tools.nana_next_experience.experiments import video_guarded_audio as module
            from unittest.mock import patch
            with patch.object(module,'measure',side_effect=AssertionError('denied source must not decode')):
                with pytest.raises(CoreError):
                    guarded_audio_window(app,cache,mid,scope='not-allowed',start_seconds=1,end_seconds=3)
            result=guarded_audio_window(app,cache,mid,scope='world',start_seconds=1,end_seconds=3)
            assert result.source_ref==mid and result.source_sha256==handle.sha256==hashlib.sha256(data).hexdigest()
            assert result.acoustic['state']=='MEASURED' and result.acoustic['requested_window']==(1,3)
            assert result.acoustic['coverage_state']=='PARTIAL' and result.acoustic['silence_intervals']
            assert result.state=='MEASUREMENT_NOT_INGESTED' and result.timeline_alignment=='CALLER_MUST_VERIFY'
            assert result.source_lifetime=='RECHECK_REQUIRED_AT_USE' and result.cache_bytes_hashed==len(data)
            assert len(runtime.store.all('continuity_records'))==records_before
            assert not runtime.store.all('actions') and not runtime.store.all('grants')
        finally:cache.close()


@pytest.mark.parametrize('withdrawal',['store','cache'])
def test_guarded_audio_rejects_withdrawal_during_measurement(tmp_path,monkeypatch,withdrawal):
    from tools.nana_next_experience.experiments import video_guarded_audio as module
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us()
        source=PublicMediaSource(source_id='synthetic-audio-video',modality='VIDEO',origin='SYNTHETIC',
                                 event_time_us=now,observed_time_us=now)
        mid,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,source,entity_id='observer',scope='world')
        cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4');original=module.measure
            def withdraw(path,**kwargs):
                result=original(path,**kwargs)
                if withdrawal=='store':MemoryService(runtime.store,runtime.authority).forget(mid,runtime.authority)
                else:monkeypatch.setattr(cache,'current',lambda _:False)
                return result
            monkeypatch.setattr(module,'measure',withdraw)
            with pytest.raises(CoreError):
                guarded_audio_window(app,cache,mid,scope='world',start_seconds=1,end_seconds=3)
            with pytest.raises(CoreError):
                guarded_audio_window(app,cache,mid,scope='world',start_seconds=1,end_seconds=3)
        finally:cache.close()
