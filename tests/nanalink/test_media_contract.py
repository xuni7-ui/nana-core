from nana_core.continuity.autonomy.contracts import MediaSelection, RealizationTarget


def test_optional_media_choice_preserves_old_target_wire():
    target=RealizationTarget(capability='world.contact',operation='CONTACT',resource='project://qq/test',resource_class='ORDINARY')
    assert 'media' not in target.model_dump()
    media=MediaSelection(kind='image',source_memory_id='source.fixture',content_sha256='a'*64,reference='image.fixture')
    selected=target.model_copy(update={'media':media})
    assert RealizationTarget.model_validate_json(selected.model_dump_json()).media==media
