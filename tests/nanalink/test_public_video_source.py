"""Original public media source must bind any cache handle offered to a decoder."""
import pytest
from types import SimpleNamespace
from nana_core.contracts import CoreError
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.world_loop.perception import PerceptionService, PublicMediaSource
from nana_core.nanalink.media import MediaCache
from tests.world_loop.helpers import fresh, policy, providers, capture


class SyntheticDecoder:
    def decode(self, data, modality):
        assert modality == 'VIDEO'
        return {'modality':'VIDEO','decoded':True,'duration_s':1.0,'width':2,'height':2,
                'frames':[{'sample_s':0.0,'source_frame_index':0,'source_interval_s':[0.0,1.0],
                           'mean_rgb':[0.0,0.0,0.0],'pixel_digest':'0'*64}],
                'source_frame_count':1,'changes':[],
                'coverage':'TEMPORAL_SAMPLES_NOT_FULL_SEMANTIC_COVERAGE',
                'unobserved_between_samples':True,'audio_linkage':'ABSENT','semantic_interpretation':'UNKNOWN'}


@pytest.mark.parametrize('origin', ['SYNTHETIC', 'RECORDED'])
def test_video_handle_requires_current_original_public_observation(tmp_path, monkeypatch, origin):
    from nana_core.nanalink.video_handoff import public_video_cache_handle, with_current_public_video
    with fresh(tmp_path/'subject.db') as runtime:
        app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us();data=b'synthetic-video-bytes'
        service=PerceptionService(runtime.store,providers(),app.policy,decoder=SyntheticDecoder())
        def observe(name):
            src=PublicMediaSource(source_id=name,modality='VIDEO',origin=origin,event_time_us=now,observed_time_us=now)
            return service.ingest(data,src,entity_id='observer',scope='world')[0]
        one,two=observe('video-one'),observe('video-two')
        other_src=PublicMediaSource(source_id='video-other',modality='VIDEO',origin='SYNTHETIC',event_time_us=now,observed_time_us=now)
        other,_=service.ingest(data,other_src,entity_id='device',scope='world')
        cache=MediaCache(tmp_path/'cache',source_current=lambda _:True,max_bytes=128,item_bytes=64,max_items=4)
        cache.put((data,),source_ref=one);cache.put((data,),source_ref=two)
        handle=public_video_cache_handle(app,cache,one,scope='world')
        assert handle.source_ref==one and handle.sha256==public_video_cache_handle(app,cache,two,scope='world').sha256
        result=with_current_public_video(app,cache,one,scope='world',
            operation=lambda h: SimpleNamespace(source_ref=h.source_ref,source_sha256=h.sha256))
        assert result.source_ref==one
        with pytest.raises(CoreError,match='NANALINK_VIDEO_OUTPUT_SOURCE_MISMATCH'):
            with_current_public_video(app,cache,one,scope='world',
                operation=lambda h: SimpleNamespace(source_ref='other',source_sha256=h.sha256))
        with pytest.raises(CoreError,match='NANALINK_VIDEO_MATERIALIZED_RESULT_REQUIRED'):
            with_current_public_video(app,cache,one,scope='world',operation=lambda h: iter((h,)))
        async def deferred(handle):
            return handle
        with pytest.raises(CoreError,match='NANALINK_VIDEO_MATERIALIZED_RESULT_REQUIRED'):
            with_current_public_video(app,cache,one,scope='world',operation=deferred)
        with pytest.raises(CoreError):public_video_cache_handle(app,cache,one,scope='other')
        with pytest.raises(CoreError,match='NANALINK_VIDEO_SOURCE_DENIED'):
            public_video_cache_handle(app,cache,other,scope='world')
        private=capture(runtime,'private-video',{'synthetic':'private'},privacy='PERSONAL')
        with pytest.raises(CoreError):public_video_cache_handle(app,cache,private,scope='world')
        wrong=MediaCache(tmp_path/'wrong-cache',source_current=lambda _:True,max_bytes=128,item_bytes=64,max_items=4)
        wrong.put((b'different bytes',),source_ref=one)
        with pytest.raises(CoreError,match='MEDIA_CACHE_MISS'):
            public_video_cache_handle(app,wrong,one,scope='world')
        wrong.close()
        def revoke_during_operation(handle):
            MemoryService(runtime.store,runtime.authority).forget(one,runtime.authority)
            return 'MUST_NOT_RETURN'
        with pytest.raises(CoreError):
            with_current_public_video(app,cache,one,scope='world',operation=revoke_during_operation)
        assert public_video_cache_handle(app,cache,two,scope='world').source_ref==two
        original_resolve=cache.resolve
        def withdraw_after_resolve(*,source_ref,sha256):
            resolved=original_resolve(source_ref=source_ref,sha256=sha256)
            MemoryService(runtime.store,runtime.authority).forget(two,runtime.authority)
            return resolved
        monkeypatch.setattr(cache,'resolve',withdraw_after_resolve)
        with pytest.raises(CoreError):public_video_cache_handle(app,cache,two,scope='world')
        cache.close()


def test_public_video_handle_rejects_evidence_without_original_observation_record(tmp_path):
    import hashlib
    from nana_core.continuity.contracts import EvidenceInput, MemoryCandidate, MemoryType, Provenance
    from nana_core.nanalink.video_handoff import public_video_cache_handle, with_current_public_video
    from nana_core.storage import canonical
    with fresh(tmp_path/'subject.db') as runtime:
        app=SimpleNamespace(runtime=runtime,policy=policy());now=runtime.clock.utc_now_us();data=b'fixture-not-observed'
        source=PublicMediaSource(source_id='unobserved-video',modality='VIDEO',origin='SYNTHETIC',
                                 event_time_us=now,observed_time_us=now)
        text=canonical({'source':source.model_dump(mode='json'),'decoded':{'modality':'VIDEO','decoded':True},
                        'source_byte_digest':hashlib.sha256(data).hexdigest()})
        memory=MemoryService(runtime.store)
        evidence=memory.capture(EvidenceInput(provenance=Provenance(domain='SYNTHETIC_ONLY',
            source_namespace='synthetic.public-media',source_reference=source.source_id,source_kind='DIRECT_OBSERVATION'),
            text=text,privacy_class='PUBLIC',event_time_us=now,observed_time_us=now))
        mid=memory.add(MemoryCandidate(entity_id='observer',scope='world',memory_type=MemoryType.EPISODIC,
                                       epistemic_kind='OBSERVATION',source_evidence_id=evidence,text=text))
        cache=MediaCache(tmp_path/'cache',source_current=lambda _:True,max_bytes=128,item_bytes=64,max_items=4)
        try:
            cache.put([data],source_ref=mid)
            with pytest.raises(CoreError,match='NANALINK_VIDEO_OBSERVATION_NOT_CURRENT'):
                public_video_cache_handle(app,cache,mid,scope='world')
            called=[]
            with pytest.raises(CoreError,match='NANALINK_VIDEO_OBSERVATION_NOT_CURRENT'):
                with_current_public_video(app,cache,mid,scope='world',operation=lambda handle: called.append(handle))
            assert called == []
        finally:
            cache.close()
