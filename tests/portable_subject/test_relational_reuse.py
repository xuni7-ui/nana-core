import pytest
from nana_core.contracts import CoreError
from nana_core.continuity.relational.bootstrap import SubjectBootstrapService, SubjectBootstrapAuthority, primary_user_view
from nana_core.continuity.relational.contracts import RelationalAnchorSpec, SubjectPersonalitySeed
from nana_core.continuity.relational.projections import social_appetite, personality_tendencies, self_narrative
from nana_core.continuity.subject import SubjectInput, SubjectLoop


def test_explicit_primary_anchor_revision_not_appetite_or_authority(subject):
    store, operator = subject
    controller=SubjectBootstrapAuthority()
    service=SubjectBootstrapService(store,controller)
    before=social_appetite(store,scope='lab',privacy_classes=('PERSONAL',))
    spec=RelationalAnchorSpec(identity_id=store.identity['identity_id'],anchor_id='primary',entity_id='person-a',role_kind='PRIMARY_USER',role_label='trusted companion',scope='lab',revision=1,effective_from_us=store.clock.utc_now_us())
    rid=service.install(spec,controller)
    assert service.install(spec,controller)==rid
    assert primary_user_view(store,scope='lab',privacy_classes=('PERSONAL',)).spec.entity_id=='person-a'
    assert social_appetite(store,scope='lab',privacy_classes=('PERSONAL',)).state==before.state
    assert not primary_user_view(store,scope='lab',privacy_classes=('PUBLIC',))
    with pytest.raises(CoreError,match='UNAUTHENTICATED'):
        service.install(spec,operator)
    service.install(spec.model_copy(update={'revision':2,'entity_id':'person-b'}),controller)
    assert primary_user_view(store,scope='lab',privacy_classes=('PERSONAL',)).spec.entity_id=='person-b'
    assert store.all('grants')==[]


def test_reused_same_subject_loop_and_sourced_tendencies(subject):
    store,_=subject
    controller=SubjectBootstrapAuthority()
    SubjectBootstrapService(store,controller).install(SubjectPersonalitySeed(identity_id=store.identity['identity_id'],scope='lab',revision=1),controller)
    loop=SubjectLoop(store,scopes=('lab',))
    result=loop.run(SubjectInput(source_key='synthetic.portable.first',kind='INTERACTION',origin='USER',entity_id='person-a',scope='lab',text='A fictional shared interaction',significance='RELEVANT',observed_at_us=store.clock.utc_now_us()))
    assert result.barrier in {'SHADOW_BLOCKED','NO_ACTION'}
    assert all(f.basis=='BOOTSTRAP' for f in personality_tendencies(store,scope='lab',privacy_classes=('PERSONAL',)).facets)
    assert not self_narrative(store,scope='lab',privacy_classes=('PERSONAL',)).is_policy
    assert store.identity['identity_id']
