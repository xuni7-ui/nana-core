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


def test_willing_deference_can_change_choice_without_erasing_desire(subject):
    from nana_core.continuity.subject import PreferenceSignal
    from nana_core.continuity.relational.contracts import RelationalRequest,DAY
    store,_=subject;controller=SubjectBootstrapAuthority();boot=SubjectBootstrapService(store,controller)
    boot.install(SubjectPersonalitySeed(identity_id=store.identity['identity_id'],scope='lab',revision=1,relational_accommodation='HIGH',conviction_persistence='HIGH'),controller)
    loop=SubjectLoop(store,scopes=('lab',))
    def evt(key,entity='person-a',**kw):
        return SubjectInput(source_key='synthetic.tradeoff.'+key,kind='INTERACTION',origin='USER',entity_id=entity,scope='lab',text='Fictional sourced interaction',significance='RELEVANT',observed_at_us=store.clock.utc_now_us(),**kw)
    for i in range(2):
        loop.run(evt(str(i)).model_copy(update={'origin':'ENVIRONMENT','kind':'OUTCOME','preference_signal':PreferenceSignal(topic='social_exploration',direction='SUPPORT',interpretation='A fictional social experience was interesting')}))
    request=RelationalRequest(request_id='ordinary',requesting_entity='person-a',operation='REFRAIN',behavior_domain='SOCIAL_NEW_CONTACTS',duration_us=DAY)
    ordinary=loop.run(evt('ordinary',relational_request=request))
    boot.install(RelationalAnchorSpec(identity_id=store.identity['identity_id'],anchor_id='primary',entity_id='person-a',role_kind='PRIMARY_USER',role_label='companion',scope='lab',revision=1,effective_from_us=store.clock.utc_now_us()),controller)
    primary=loop.run(evt('primary',relational_request=request.model_copy(update={'request_id':'primary'})))
    assert ordinary.relational_decision.response.decision=='DECLINE'
    assert primary.relational_decision.response.decision=='ACCEPT'
    assert primary.relational_decision.response.retained_preference=='SOCIALIZE'
    indefinite=loop.run(evt('indefinite',relational_request=request.model_copy(update={'request_id':'indefinite','duration_us':None,'scope':'GLOBAL'})))
    assert indefinite.relational_decision.response.decision in {'NEGOTIATE','DECLINE'}
    assert not store.all('grants') and not store.all('actions')


def test_instance_bootstrap_is_data_not_default_persona(tmp_path):
    from nana_core.storage.bootstrap import IdentityBootstrap
    from nana_core.continuity import ContinuityStore
    from nana_core.actions import OperatorAuthority
    from nana_core.continuity.identity import IdentityService
    from nana_core.presence.authority import VirtualClock
    path=tmp_path/'instance'/'self.db'
    bootstrap=IdentityBootstrap(name='Synthetic Example',source_reference='synthetic.instance.bootstrap')
    with ContinuityStore(path,VirtualClock(),identity_bootstrap=bootstrap) as store:
        identity=IdentityService(store,OperatorAuthority()).current()
        assert identity.name=='Synthetic Example'
    with ContinuityStore(path,VirtualClock()) as reopened:
        assert reopened.identity['identity_id']==identity.identity_id
    with pytest.raises(CoreError,match='ALREADY_BOOTSTRAPPED'):
        ContinuityStore(path,VirtualClock(),identity_bootstrap=bootstrap)
