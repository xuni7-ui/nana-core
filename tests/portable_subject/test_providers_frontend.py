import json
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import canonical,digest
from nana_core.continuity.application import SubjectApplication, FrontendPolicy, CapabilityReviewProposal
from nana_core.continuity.context import ContextPolicy,ContextAssembler,ContextRequest
from nana_core.continuity.cognition import AnalyticalFixturePort,CautiousFixturePort
from nana_core.continuity.contracts import EvidenceInput,Provenance,MemoryCandidate,MemoryType
from nana_core.continuity.memory import MemoryService
from nana_core.continuity.providers import ProviderDescriptor,ProviderRegistry,MediaSession,FixtureMediaPort,EmbeddingCache
from nana_core.continuity.subject import SubjectLoop
from nana_core.continuity.relational.bootstrap import SubjectBootstrapAuthority
from nana_core.continuity.relational.contracts import RelationalAnchorSpec
from .test_surfaces import envelope,event


def policy():
    return ContextPolicy(policy_id='fixture',allowed_scopes=('lab',),readable_privacy=('PERSONAL',),remote_privacy=())

def memory(store,key,privacy='PERSONAL'):
    m=MemoryService(store)
    e=m.capture(EvidenceInput(provenance=Provenance(source_namespace='synthetic.provider',source_reference=key,source_kind='DIRECT_OBSERVATION'),text='fictional portable media source',observed_time_us=store.clock.utc_now_us(),privacy_class=privacy))
    return m.add(MemoryCandidate(entity_id='person-a',scope='lab',memory_type=MemoryType.EPISODIC,epistemic_kind='OBSERVATION',source_evidence_id=e,text='fictional portable media source'))

def descriptor(name,operations=('COGNITION',),version='1',**kwargs):
    return ProviderDescriptor(provider_id='fixture.provider',model_id='fixture.'+name,model_version=version,operations=operations,input_modalities=('TEXT',),output_modalities=('TEXT',),context_limit=64000,output_limit=4096,locality='LOCAL_FIXTURE',permitted_privacy=('PERSONAL',),**kwargs)


def test_model_swap_does_not_change_authoritative_subject(subject):
    store,operator=subject
    registry=ProviderRegistry()
    registry.register(descriptor('analytic'),AnalyticalFixturePort())
    registry.register(descriptor('cautious'),CautiousFixturePort())
    assembler=ContextAssembler(store,operator)
    request=ContextRequest(entity_id='person-a',scopes=('lab',),task_class='fixture.test',task='Consider the fictional record',max_input_tokens=32000)
    before=store.snapshot()
    a=registry.deliberate('fixture.analytic',assembler,request,policy())
    b=registry.deliberate('fixture.cautious',assembler,request,policy())
    assert a.proposal.identity_id==b.proposal.identity_id==store.identity['identity_id']
    assert store.snapshot()==before
    with pytest.raises(CoreError,match='PROVIDER_UNAVAILABLE'):registry.cognition('fixture.missing')


def test_media_ports_and_embedding_swap_rebuild_not_memory_mutation(subject):
    store,operator=subject;mid=memory(store,'media');secret=memory(store,'secret','SECRET')
    registry=ProviderRegistry()
    ops=('EMBED','VISION','IMAGE_GENERATE','STT','TTS','AUDIO_UNDERSTAND','AUDIO_GENERATE','VIDEO_UNDERSTAND')
    registry.register(descriptor('media_a',ops),FixtureMediaPort(3))
    registry.register(descriptor('media_b',ops,version='2'),FixtureMediaPort(5))
    session=MediaSession(store,registry,policy());before=store.snapshot()
    for method in ('understand_image','generate_image','transcribe','synthesize_speech','understand_audio','generate_audio','understand_video'):
        result=getattr(session,method)('fixture.media_a',(mid,),scopes=('lab',))
        assert result.provenance=='MODEL_PROPOSAL_NOT_TRUTH' and result.source_memory_ids==(mid,)
    with pytest.raises(CoreError,match='PRIVACY_DENIED'):
        session.understand_image('fixture.media_a',(secret,),scopes=('lab',))
    cache=EmbeddingCache();assert cache.rebuild(session,'fixture.media_a',(mid,),scopes=('lab',)).dimension==3
    with pytest.raises(CoreError,match='REBUILD_REQUIRED'):cache.lookup(store,provider_id='fixture.provider',model_id='fixture.media_b',model_version='2',dimension=5)
    assert cache.rebuild(session,'fixture.media_b',(mid,),scopes=('lab',)).dimension==5
    assert store.snapshot()==before
    MemoryService(store,operator).forget(mid,operator)
    with pytest.raises(CoreError,match='REBUILD_REQUIRED'):cache.lookup(store,provider_id='fixture.provider',model_id='fixture.media_b',model_version='2',dimension=5)


def test_frontend_commands_through_application_not_direct_state_write(subject):
    store,operator=subject;registry=ProviderRegistry();bootstrap=SubjectBootstrapAuthority()
    app=SubjectApplication(store,SubjectLoop(store,scopes=('lab',)),operator,providers=registry,bootstrap_authority=bootstrap)
    client=app.session(FrontendPolicy(context=policy(),entity_id='person-a',commands=('SEND_INPUT','PROPOSE_GOAL','FORGET','CHANGE_SETTING','CAPABILITY_REVIEW'),deletable_scopes=('lab',)))
    client.send_input(envelope(store,'fixture.frontend','first'),event(store))
    assert not hasattr(client,'store') and not hasattr(client,'authority')
    for kind in ('SELF','LIVING_SELF','RELATIONSHIP','PERSONALITY','MEMORY_SUMMARY','GOALS_COMMITMENTS_PROJECTS','RUNTIME','PROVIDERS'):
        assert client.view(kind,scope='lab').derived
    assert client.view('CONTINUITY',scope='lab').subject_id==store.identity['identity_id']
    before=store.identity
    client.propose_goal(envelope(store,'fixture.frontend','goal'),event(store).model_copy(update={'kind':'PROJECT'}))
    assert store.identity==before and store.all('goals')==[]
    proposal=client.request_capability_review(CapabilityReviewProposal(operation='REQUEST_APPROVAL',capability_id='device.inspect',resource_reference='synthetic.resource',scope='lab'))
    assert not proposal.execution_authority and not store.all('grants')
    with pytest.raises(CoreError,match='SETTING_DENIED'):client.change_setting('authority','all')
    with pytest.raises(CoreError,match='COMMAND_DENIED'):
        client.configure_primary_user(RelationalAnchorSpec(identity_id=store.identity['identity_id'],anchor_id='primary',entity_id='person-a',role_kind='PRIMARY_USER',role_label='companion',scope='lab',revision=1,effective_from_us=store.clock.utc_now_us()))
    mid=store.all('subject_events')[0]['memory_id']
    client.forget(mid)
    assert client.forget(mid)['state']=='ALREADY_DELETED'
    assert mid not in client.view('MEMORY_SUMMARY',scope='lab').data_json
