"""Real FFmpeg and original Store/S5 technical-decoder handoff fixture."""
from dataclasses import replace
import hashlib
import io
import shutil

import pytest
from PIL import Image

from nana_core.clock import Clock
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.records import RecordService
from nana_core.continuity.world_loop.perception import PerceptionService,PublicMediaSource
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh,providers
from tests.nana_next_experience.test_video_guarded_audio import video_bytes
from tests.nana_next_experience.test_video_shared_audio_snapshot import source
from tools.nana_next_experience.experiments.video_guarded_batch import guarded_images
from tools.nana_next_experience.experiments.video_s5_handoff import s5_decode_handoff

pytestmark=pytest.mark.skipif(not all(shutil.which(x) for x in ('ffmpeg','ffprobe','bwrap')),
                              reason='optional FFmpeg and sandbox required')


def make_batch(app,cache,mid):
    def detector(decoded):
        return ({'source_ref':mid,'input_size':decoded.output_size,'input_frames':len(decoded.timestamps),
                 'qualification':'LOCAL_PIPELINE_OUTPUT_ONLY','selected':[],'dropped_sheets':0},
                {'schema_version':1,'source_ref':mid,'input_size':decoded.output_size,
                 'pairs_examined':len(decoded.timestamps)-1,'truncated':False,'proposals':[]})
    return guarded_images(app,cache,mid,scope='world',windows=((0,4),),detector=detector,
                          budget=3,max_gap=2,width=32,height=32,shared_snapshot=True)


def supersede(runtime,mid):
    records=RecordService(runtime.store)
    old=runtime.store.db.execute("SELECT record_id FROM continuity_records WHERE record_kind='MEDIA_OBSERVATION' AND target_id=? AND lifecycle='ACTIVE'",(mid,)).fetchone()[0]
    payload=records.read(old)['payload']
    with runtime.store.transaction('SYNTHETIC_MEDIA_SUPERSESSION') as tx:
        records.create(tx,kind='MEDIA_OBSERVATION',scope='world',payload=payload,
                       memories=(mid,),supersedes=old,target_id=mid)


def test_original_s5_receives_images_and_rejects_tampering(tmp_path):
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4')
            batch=make_batch(app,cache,mid);result=s5_decode_handoff(app,cache,batch,scope='world')
            assert result.source_ref==mid and result.source_sha256==batch.source_sha256
            assert result.source_bytes_rechecked==len(data)
            assert result.state=='TECHNICAL_IMAGE_DECODE_ONLY_NOT_INGESTED'
            assert result.frame_attestation=='TRUSTED_PIPELINE_NOT_INDEPENDENTLY_REDECODED'
            verified=s5_decode_handoff(app,cache,batch,scope='world',verify_source_frames=True)
            assert verified.frame_attestation=='SOURCE_WINDOW_REDECODED_NO_PLATFORM_ATTESTATION'
            assert [f.decoded for f in verified.frames]==[f.decoded for f in result.frames]
            empty=s5_decode_handoff(app,cache,replace(batch,images=()),scope='world',verify_source_frames=True)
            assert empty.frames==() and empty.frame_attestation=='NO_FRAMES_TO_VERIFY'
            assert result.unrequested_intervals==batch.unrequested_intervals and result.sampling_gaps==batch.sampling_gaps
            assert len(result.frames)==len(batch.images)>0
            for original,frame in zip(batch.images,result.frames):
                assert frame.decoded['pixel_digest']==original.pixel_sha256
                assert frame.decoded['semantic_interpretation']=='UNKNOWN'
                assert (frame.source_seconds,frame.pts_tick,frame.time_base)==(original.source_seconds,original.pts_tick,original.time_base)
            assert not runtime.store.all('actions')
            image=batch.images[0]
            pixels=bytes([255,0,0])*(image.output_size[0]*image.output_size[1]);stream=io.BytesIO()
            Image.frombytes('RGB',image.output_size,pixels).save(stream,format='PNG')
            forged=replace(image,png=stream.getvalue(),pixel_sha256=hashlib.sha256(pixels).hexdigest())
            altered=replace(batch,images=(forged,))
            # The legacy path checks PNG consistency but must trust its producer.
            assert s5_decode_handoff(app,cache,altered,scope='world').frames[0].decoded['pixel_digest']==forged.pixel_sha256
            with pytest.raises(ValueError,match='does not match source frame'):
                s5_decode_handoff(app,cache,altered,scope='world',verify_source_frames=True)
            for corrupt in [replace(image,pixel_sha256='0'*64),replace(image,pts_tick=image.pts_tick+1),
                            replace(image,source_ref='wrong-source')]:
                with pytest.raises(ValueError):
                    s5_decode_handoff(app,cache,replace(batch,images=(corrupt,)),scope='world')
            path,_=cache.items[batch.source_sha256]
            path.write_bytes(bytes([data[0]^1])+data[1:])
            with pytest.raises(CoreError,match='MEDIA_CACHE_CONTENT_MISMATCH'):
                s5_decode_handoff(app,cache,batch,scope='world')
        finally:cache.close()


def test_s5_handoff_never_returns_after_original_source_withdrawal(tmp_path,monkeypatch):
    from tools.nana_next_experience.experiments import video_s5_handoff as module
    original=module.MediaDecoder
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4');batch=make_batch(app,cache,mid)
            class RevokingDecoder(original):
                def decode(self,*args,**kwargs):
                    value=super().decode(*args,**kwargs)
                    MemoryService(runtime.store,runtime.authority).forget(mid,runtime.authority)
                    return value
            monkeypatch.setattr(module,'MediaDecoder',RevokingDecoder)
            with pytest.raises(CoreError):s5_decode_handoff(app,cache,batch,scope='world')
        finally:cache.close()


def test_s5_handoff_rechecks_withdrawal_during_source_frame_verification(tmp_path,monkeypatch):
    from tools.nana_next_experience.experiments import video_s5_handoff as module
    original=module.decode_source_window
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4');batch=make_batch(app,cache,mid)
            def revoke(*args,**kwargs):
                result=original(*args,**kwargs)
                MemoryService(runtime.store,runtime.authority).forget(mid,runtime.authority)
                return result
            monkeypatch.setattr(module,'decode_source_window',revoke)
            with pytest.raises(CoreError):
                s5_decode_handoff(app,cache,batch,scope='world',verify_source_frames=True)
        finally:cache.close()


def test_s5_handoff_refuses_superseded_original_observation_between_batches(tmp_path):
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4');batch=make_batch(app,cache,mid)
            supersede(runtime,mid)
            with pytest.raises(CoreError,match='NANALINK_VIDEO_OBSERVATION_AMBIGUOUS'):
                s5_decode_handoff(app,cache,batch,scope='world',verify_source_frames=True)
            now=runtime.clock.utc_now_us()
            descriptor=PublicMediaSource(source_id='synthetic-independent-video',modality='VIDEO',origin='SYNTHETIC',event_time_us=now,observed_time_us=now)
            other,_=PerceptionService(runtime.store,providers(),app.policy).ingest(data,descriptor,entity_id='observer',scope='world')
            cache.put([data],source_ref=other,media_type='video/mp4')
            current=make_batch(app,cache,other)
            assert s5_decode_handoff(app,cache,current,scope='world',verify_source_frames=True).frames
        finally:cache.close()


def test_s5_handoff_refuses_original_observation_superseded_during_decode(tmp_path,monkeypatch):
    from tools.nana_next_experience.experiments import video_s5_handoff as module
    original=module.decode_source_window
    data=video_bytes(tmp_path)
    with fresh(tmp_path/'subject.db',Clock()) as runtime:
        app,mid=source(runtime,data);cache=MediaCache(tmp_path/'cache',source_current=lambda _:True)
        try:
            cache.put([data],source_ref=mid,media_type='video/mp4');batch=make_batch(app,cache,mid)
            def replace_observation(*args,**kwargs):
                result=original(*args,**kwargs);supersede(runtime,mid);return result
            monkeypatch.setattr(module,'decode_source_window',replace_observation)
            with pytest.raises(CoreError,match='NANALINK_VIDEO_OBSERVATION_AMBIGUOUS'):
                s5_decode_handoff(app,cache,batch,scope='world',verify_source_frames=True)
        finally:cache.close()
