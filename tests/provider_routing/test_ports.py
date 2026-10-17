import json
import pytest
from nana_core.contracts import CoreError
from nana_core.storage import digest,canonical
from nana_core.continuity.providers import EmbeddingCache
from nana_core.continuity.provider_routing import *
from nana_core.continuity.world_loop.cognition import CognitionBudget
from nana_core.continuity.world_loop.harness import provider_harness
from nana_core.continuity.world_loop.semantic_harness import semantic_proposer
from nana_core.continuity.world_loop.semantics import MediaSemanticService
from nana_core.continuity.world_loop.samples import media_samples
from tests.world_loop.helpers import fresh,policy,capture
from tests.h1_semantics.test_grounding import ingest
from .helpers import *

@pytest.mark.parametrize('operation,modality',[('COGNITION','TEXT'),('VISION','IMAGE'),('VIDEO_UNDERSTAND','VIDEO')])
def test_original_openai_transport_native_loopback_config_to_h1(tmp_path,operation,modality):
    with provider_harness(semantic_proposer) as (wire,metrics):
        s,a=config_service(tmp_path/'host/providers.json')
        p=ProviderProfile(provider_profile_id='synthetic.http',display_name='SYNTHETIC_LOOPBACK',protocol='SYNTHETIC_LOOPBACK',base_url=wire.endpoint.removesuffix('/chat/completions'),locality='LOCAL_FIXTURE')
        m=model('model.wire',p.provider_profile_id,(operation,)).model_copy(update={'remote_model_id':'harness-v1'})
        update(s,a,'UPSERT_PROVIDER',provider=p);update(s,a,'UPSERT_MODEL',model=m);update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation=operation,primary_model_profile_id=m.model_profile_id))
        router=CapabilityRouter(s,RuntimeProviderFactory(ProviderRegistry(),Resolver(),RoutingPolicy(allow_synthetic_loopback=True)))
        with fresh(tmp_path/'subject/self.db') as r:
            identity=r.identity_id;t=router.resolve(RouteRequest(operation=operation,input_modalities=(modality,),output_limit=4096),policy());session=t.cognition_session(r)
            if modality=='TEXT':
                mid=capture(r,'text',{'fact':'synthetic context'});cid=session.prepare('text','INTERPRET',(mid,));assert session.execute(cid)['state']=='PROPOSED'
            else:
                raw=media_samples()[modality];mid=ingest(r,modality,raw);service=MediaSemanticService(session)
                cid=service.prepare('native-wire',mid,raw);assert service.execute(cid)['state']=='PROPOSED'
                result=service.ground(cid,entity_id='device');assert result['origin']=='SYNTHETIC'
                assert all(session.records.memory.read(m)['source_provenance']['source_kind']=='MODEL_DERIVATION' for m in result['semantic_memory_ids'])
            assert metrics['calls']==1 and r.identity_id==identity and not r.store.all('subject_cycles') and not r.store.all('actions')
            request=session.records.read(r.store.one('cognitive_requests',cid)['record_id'])['payload']['request']
            assert request['route_snapshot']['protocol']=='SYNTHETIC_LOOPBACK'
            before=metrics['calls'];assert session.execute(cid)['replayed'] and metrics['calls']==before


def test_all_existing_media_ports_and_embedding_route_rebuild(tmp_path):
    ops=('EMBED','VISION','IMAGE_GENERATE','STT','TTS','AUDIO_UNDERSTAND','AUDIO_GENERATE','VIDEO_UNDERSTAND')
    s,a=config_service(tmp_path/'host/providers.json');registry=ProviderRegistry()
    p=provider('fixture.media');m=model('model.media',p.provider_profile_id,ops)
    update(s,a,'UPSERT_PROVIDER',provider=p);update(s,a,'UPSERT_MODEL',model=m);registry.register(m.descriptor(p),FixtureMediaPort())
    for op in ops:update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation=op,primary_model_profile_id=m.model_profile_id))
    router=CapabilityRouter(s,RuntimeProviderFactory(registry,Resolver(),RoutingPolicy()))
    with fresh(tmp_path/'subject/self.db') as r:
        mid=capture(r,'source',{'public':'fictional source'});before=r.store.snapshot();cache=EmbeddingCache()
        for op in ops:
            target=router.resolve(RouteRequest(operation=op),policy())
            if op=='EMBED':
                meta=target.embedding_rebuild(cache,r.store,(mid,),scopes=('world',));assert target.embedding_lookup(cache,r.store,dimension=3)
            else:assert target.media(r.store,(mid,),scopes=('world',))['proposal'].operation==op
        assert before==r.store.snapshot()
        retained=target.media_session(r.store)
        new=model('model.other',p.provider_profile_id,ops)
        update(s,a,'UPSERT_MODEL',model=new);registry.register(new.descriptor(p),FixtureMediaPort())
        update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='EMBED',primary_model_profile_id=new.model_profile_id))
        with pytest.raises(CoreError,match='ROUTE_CHANGED_BEFORE_DISPATCH'):retained._invoke('model.media','VISION',(mid,),scopes=('world',))
        target=router.resolve(RouteRequest(operation='EMBED'),policy())
        with pytest.raises(CoreError,match='REBUILD_REQUIRED'):target.embedding_lookup(cache,r.store,dimension=3)
        target.embedding_rebuild(cache,r.store,(mid,),scopes=('world',))
        # Same remote name and provider, changed version must still rebuild.
        revised=m.model_copy(update={'model_version':'2'})
        update(s,a,'UPSERT_MODEL',model=revised);registry.unregister(m.model_profile_id);registry.register(revised.descriptor(p),FixtureMediaPort())
        update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation='EMBED',primary_model_profile_id=m.model_profile_id))
        changed=router.resolve(RouteRequest(operation='EMBED'),policy())
        with pytest.raises(CoreError,match='REBUILD_REQUIRED'):changed.embedding_lookup(cache,r.store,dimension=3)
        assert r.store.snapshot()==before
