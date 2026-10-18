"""Finite controlled-display wiring into existing H2/Router/H1/C services."""
from contextlib import contextmanager
from nana_core.continuity.sensors.contracts import *
from nana_core.continuity.sensors.config import PerceptionConfigService,PerceptionConfigurationAuthority
from nana_core.continuity.sensors.screen import RealScreenPerceptionPort,ScreenBackendDescriptor
from nana_core.continuity.sensors.coordinator import PerceptionCoordinator
from nana_core.continuity.provider_config import *
from nana_core.continuity.provider_routing import *
from nana_core.continuity.world_loop.reference import codec_providers,context_policy,configure
from nana_core.continuity.world_loop.semantic_harness import semantic_harness,semantic_proposer
from .x11_surface import ControlledX11Surface

def interpretation(request):
    p=semantic_proposer(request)
    if request.cognitive_role=='GOALS':
        p=p.model_copy(update={'interests':tuple(i.model_copy(update={'expected_value':'HIGH','possible_behaviors':('WATCH',)}) for i in p.interests)})
    return p

@contextmanager
def laboratory(runtime,root,*,live_screen=False,interval_ms=10000,periodic=False):
    # The opt-in is checked before any OS display or HTTP harness starts.
    if live_screen is not True:raise CoreError('EXPLICIT_LIVE_SCREEN_FLAG_REQUIRED')
    with ControlledX11Surface(live_screen=True) as surface,semantic_harness(proposer=interpretation) as (transport,metrics):
        configure(runtime,root,transport,('synthetic://public',),grant=False,planner=False)
        resolver=HostPerceptionResolver();authority=PerceptionConfigurationAuthority()
        config=PerceptionConfigService(root/'host/sensors.json',authority,resolver);config.initialize(authority)
        # A new OS session always receives a fresh profile revision before it can
        # be resolved. Old queued requests can never target this new window.
        profile=PerceptionSourceProfile(source_profile_id='screen.controlled',display_name='Owned public test window',source_kind='SCREEN',modality='IMAGE',adapter_ref='owned.x11',resource_ref='controlled.window',scope='world',entity_id=runtime.config.entity_id,max_capture_bytes=131072,semantic_operations=('VISION',),capture_mode='PERIODIC' if periodic else 'ON_DEMAND',min_interval_ms=1000,base_interval_ms=interval_ms)
        profile=profile.model_copy(update={'revision':config._load().revision+1})
        port=RealScreenPerceptionPort(surface,ScreenBackendDescriptor(backend_id='x11.owned-window'),profile,runtime.clock,host_enabled=True)
        resolver.bind(profile.adapter_ref,profile.resource_ref,port)
        config.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=config.load().revision,profile=profile),authority)
        ps_auth=ProviderConfigurationAuthority();ps=ProviderConfigService(root/'host/providers.json',ps_auth);ps.initialize(ps_auth)
        pp=ProviderProfile(provider_profile_id='synthetic.loopback',display_name='Synthetic loopback only',protocol='SYNTHETIC_LOOPBACK',base_url=transport.endpoint.rsplit('/chat/completions',1)[0],locality='LOCAL_FIXTURE',permitted_privacy=('PUBLIC',))
        mp=ModelProfile(model_profile_id='synthetic.vision',provider_profile_id=pp.provider_profile_id,remote_model_id=transport.model_id,model_version='1',operations=('VISION',),input_modalities=('IMAGE',),output_modalities=('TEXT',),context_limit=64000,output_limit=4096)
        for op,kw in [('UPSERT_PROVIDER',{'provider':pp}),('UPSERT_MODEL',{'model':mp}),('SET_CAPABILITY_ROUTE',{'route':CapabilityRoute(operation='VISION',primary_model_profile_id=mp.model_profile_id)})]:
            ps.update(ProviderCommand(operation=op,expected_revision=ps.load().revision,**kw),ps_auth)
        router=CapabilityRouter(ps,RuntimeProviderFactory(codec_providers(),None,RoutingPolicy(allow_synthetic_loopback=True)))
        c=PerceptionCoordinator(runtime,config,resolver,codec_providers(),context_policy(),router=router,host_allow=lambda p:p.source_profile_id==profile.source_profile_id and p.revision==profile.revision,concern_callback=lambda result,cid:[runtime.work.world.observe(mid) for mid in result['semantic_memory_ids']])
        c.attach()
        yield c,surface,metrics,authority

def capture(runtime,coordinator,key,*,semantic=True):
    request=coordinator.request('screen.controlled',request_id=key,foreground=True,semantic=semantic)
    coordinator.enqueue(request)
    for _ in range(32):
        value=runtime.step()
        if value and value.get('perception',{}).get('request_id')==key:return value['perception']
    raise AssertionError('capture queue did not complete')

def rebind(coordinator,surface,authority,*,changes=None):
    """Trusted host renewal; never callable by a model/frontend without host binding."""
    config=coordinator.configuration;old=config.load();p=old.sources[0]
    p=p.model_copy(update={**(changes or {}),'revision':old.revision+1})
    port=RealScreenPerceptionPort(surface,ScreenBackendDescriptor(backend_id='x11.owned-window'),p,coordinator.runtime.clock,host_enabled=True)
    resolver=HostPerceptionResolver();resolver.bind(p.adapter_ref,p.resource_ref,port)
    updated=PerceptionConfigService(config._path,authority,resolver)
    updated.update(SourceCommand(operation='UPSERT_PERCEPTION_SOURCE',expected_revision=old.revision,profile=p),authority)
    coordinator.configuration,coordinator.resolver=updated,resolver
    coordinator.host_allow=lambda candidate:candidate.source_profile_id==p.source_profile_id and candidate.revision==p.revision
    return p
