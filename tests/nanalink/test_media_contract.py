import pytest
from nana_core.continuity.autonomy.contracts import MediaSelection, RealizationTarget


def test_optional_media_choice_preserves_old_target_wire():
    target=RealizationTarget(capability='world.contact',operation='CONTACT',resource='project://qq/test',resource_class='ORDINARY')
    assert 'media' not in target.model_dump()
    media=MediaSelection(kind='image',source_memory_id='source.fixture',content_sha256='a'*64,reference='image.fixture')
    selected=target.model_copy(update={'media':media})
    assert RealizationTarget.model_validate_json(selected.model_dump_json()).media==media


@pytest.mark.parametrize('when',['before-read','during-read'])
def test_image_action_rejects_superseded_original_observation(tmp_path, monkeypatch, when):
    from nana_core.contracts import CoreError
    from nana_core.continuity.memory import MemoryService
    from nana_core.continuity.records import RecordService
    from nana_core.continuity.world_loop.perception import PerceptionService, PublicMediaSource
    from nana_core.nanalink.media import MediaCache
    from nana_core.nanalink.media_candidates import candidate, resolve_image
    from tests.person_self.test_nanalink_media_choice import picture
    from tests.world_loop.helpers import fresh, policy, providers

    with fresh(tmp_path/'subject.db') as runtime:
        now=runtime.clock.utc_now_us();data=picture()
        source=PublicMediaSource(source_id='image-observation-revision',modality='IMAGE',origin='SYNTHETIC',
                                 event_time_us=now,observed_time_us=now)
        mid,rid=PerceptionService(runtime.store,providers(),policy()).ingest(data,source,entity_id='observer',scope='world')
        records=RecordService(runtime.store);original=records.read(rid);support=records.support(rid)
        cache=MediaCache(tmp_path/'cache',source_current=lambda _:True,max_bytes=1024,item_bytes=1024,max_items=4)
        try:
            selection=candidate(MemoryService(runtime.store).read(mid));assert selection is not None
            cache.put([data],source_ref=mid)
            original_read=cache.read
            reads=[]
            def supersede(*,keep_target):
                with runtime.store.transaction('synthetic.image_observation_revised') as tx:
                    records.create(tx,kind='MEDIA_OBSERVATION',scope='world',payload=original['payload'],
                                   memories=support,supersedes=rid,target_id=mid if keep_target else None)
                assert records.current_support(rid)
                assert runtime.store.one('continuity_records',rid)['lifecycle']=='SUPERSEDED'
            if when=='before-read':supersede(keep_target=False)
            def supersede_during_read(*args,**kwargs):
                reads.append(True)
                result=original_read(*args,**kwargs)
                if when=='during-read':supersede(keep_target=True)
                return result
            monkeypatch.setattr(cache,'read',supersede_during_read)
            with pytest.raises(CoreError,match='MEDIA_OBSERVATION_NOT_CURRENT|MEDIA_SELECTION_SOURCE_MISMATCH'):
                resolve_image(runtime.store,cache,selection)
            assert reads==([] if when=='before-read' else [True])
            monkeypatch.setattr(cache,'read',original_read)
            fresh_source=source.model_copy(update={'source_id':'independent-image-observation'})
            fresh_mid,_=PerceptionService(runtime.store,providers(),policy()).ingest(
                data,fresh_source,entity_id='observer',scope='world')
            fresh_selection=candidate(MemoryService(runtime.store).read(fresh_mid))
            assert fresh_mid!=mid and fresh_selection is not None
            cache.put([data],source_ref=fresh_mid)
            assert resolve_image(runtime.store,cache,fresh_selection)==data
        finally:
            cache.close()
