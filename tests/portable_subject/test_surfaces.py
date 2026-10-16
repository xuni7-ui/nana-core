import pytest
from pydantic import ValidationError
from nana_core.contracts import CoreError
from nana_core.continuity.extensions import SurfaceEnvelope, ExtensionDescriptor
from nana_core.continuity.context import ContextPolicy
from nana_core.continuity.subject import SubjectLoop, SubjectInput
from nana_core.continuity.surfaces import SurfaceIngress, ContinuityViews


def envelope(store,platform,key):
    return SurfaceEnvelope(subject_id=store.identity['identity_id'],platform=platform,surface=platform+'.chat',adapter='fixture.messages',entity_id='person-a',conversation_id='conversation-a',session_id='session-a',event_kind='message.input',observed_at_us=store.clock.utc_now_us(),correlation_id=key,privacy_class='PERSONAL',source_reference='synthetic.surface.source',source_event_key=key)

def event(store):
    return SubjectInput(source_key='synthetic.placeholder',kind='INTERACTION',origin='USER',entity_id='person-a',scope='lab',text='A fictional cross-surface shared experience',significance='RELEVANT',observed_at_us=store.clock.utc_now_us())


def test_cross_surface_dedup_and_three_privacy_filtered_views(subject):
    store,_=subject; ingress=SurfaceIngress(SubjectLoop(store,scopes=('lab',)))
    results=[ingress.submit(envelope(store,p,str(n)),event(store)) for n,p in enumerate(('fixture.desktop','fixture.mobile','fixture.social'))]
    assert ingress.submit(envelope(store,'fixture.desktop','0'),event(store)).replayed
    assert len(store.all('subject_events'))==3
    policy=ContextPolicy(policy_id='local',allowed_scopes=('lab',),readable_privacy=('PERSONAL',),remote_privacy=())
    views=ContinuityViews(store,policy)
    for tier in ('L0_LIVE','L1_RECENT','L2_DURABLE'):
        view=views.project(tier,entity_id='person-a',scopes=('lab',))
        assert view.subject_id==store.identity['identity_id'] and len(view.surfaces)==3
        assert len(view.source_event_ids)==3 and len(view.recorded_at_us)==3
    assert not views.project('L0_LIVE',entity_id='person-a',scopes=('lab',),destination='DEVELOPMENT_REMOTE').surfaces
    with pytest.raises(CoreError,match='SCOPE_DENIED'):
        views.project('L1_RECENT',entity_id='person-a',scopes=('other',))
    with pytest.raises(CoreError,match='SUBJECT_MISMATCH'):
        ingress.submit(envelope(store,'fixture.mobile','bad').model_copy(update={'subject_id':'other'}),event(store))
    assert len({r.revision for r in results})==3


def test_open_descriptors_never_open_authority_or_real_ingress(subject):
    ExtensionDescriptor(key='custom.platform',kind='PLATFORM',version='1.0',source_reference='synthetic.registration')
    with pytest.raises(ValidationError):
        ExtensionDescriptor(key='custom.platform',kind='GRANT',version='1.0',source_reference='synthetic.registration')
    store,_=subject
    with pytest.raises(ValidationError):
        SurfaceEnvelope(**{**envelope(store,'custom.platform','real').model_dump(),'domain':'REAL'})
    with pytest.raises(ValidationError):
        SurfaceEnvelope(**{**envelope(store,'custom.platform','real').model_dump(),'platform':'../escape'})
