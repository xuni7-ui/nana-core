from nana_core.continuity.provider_config import *
from nana_core.continuity.providers import ProviderRegistry,FixtureMediaPort

def provider(name='fixture.a',**kw):
    return ProviderProfile(provider_profile_id=name,display_name=name,protocol='LOCAL',locality='LOCAL_FIXTURE',**kw)
def model(name='fixture.text',provider_id='fixture.a',ops=('COGNITION',),**kw):
    return ModelProfile(model_profile_id=name,provider_profile_id=provider_id,remote_model_id='qwen.same',model_version='1',operations=ops,input_modalities=('TEXT','IMAGE','AUDIO','VIDEO'),output_modalities=('TEXT','EMBEDDING','IMAGE','AUDIO'),context_limit=64000,output_limit=4096,**kw)
def config_service(path):
    authority=ProviderConfigurationAuthority();service=ProviderConfigService(path,authority);service.initialize(authority);return service,authority

def update(s,a,op,**kwargs):return s.update(ProviderCommand(operation=op,expected_revision=s.load().revision,**kwargs),a)
class Resolver:
    def __init__(self,refs=()):self.refs=set(refs);self.resolved=0
    def available(self,ref):return ref in self.refs
    def resolve(self,ref):
        self.resolved+=1
        if ref not in self.refs:raise ValueError('TEST_ONLY_NOT_SECRET')
        return ResolvedSecret('TEST_ONLY_NOT_SECRET')

class FixtureCognitionTransport:
    remote=False
    def __init__(self,descriptor,mode='ok'):
        self.provider_id=descriptor.provider_id;self.model_id=descriptor.model_id;self.calls=0;self.mode=mode
    def propose(self,*args):
        from nana_core.continuity.cognition import AnalyticalFixturePort
        return AnalyticalFixturePort().propose(*args)
    def exchange(self,request):
        from nana_core.continuity.world_loop.cognition import CognitionReply,StructuredProposal,TransportFailure
        from nana_core.storage import digest
        self.calls+=1
        if self.mode in {'unknown','timeout'}:raise TimeoutError('SYNTHETIC_TIMEOUT')
        if self.mode=='malformed':raise TransportFailure('PROVIDER_MALFORMED')
        return CognitionReply(request_id=request.request_id,request_digest=digest(request.model_dump(mode='json')),provider_id=self.provider_id,model_id=self.model_id,origin='SYNTHETIC',proposal=StructuredProposal(interpretation='Fixture sourced proposal, no authority',source_refs=request.primary_source_refs),cost_micro=0,billing='FIXTURE_ZERO')

def fixture_router(tmp_path,*,ops=('COGNITION',),modes=('ok','ok')):
    from nana_core.continuity.provider_routing import RuntimeProviderFactory,CapabilityRouter,RoutingPolicy
    s,a=config_service(tmp_path/'host/providers.json');registry=ProviderRegistry();ports=[]
    for suffix,mode in zip(('a','b'),modes):
        p=provider('fixture.'+suffix);m=model('model.'+suffix,p.provider_profile_id,ops)
        update(s,a,'UPSERT_PROVIDER',provider=p);update(s,a,'UPSERT_MODEL',model=m)
        port=FixtureCognitionTransport(m.descriptor(p),mode) if ops==('COGNITION',) else FixtureMediaPort()
        registry.register(m.descriptor(p),port);ports.append(port)
    update(s,a,'SET_CAPABILITY_ROUTE',route=CapabilityRoute(operation=ops[0],primary_model_profile_id='model.a',fallback_model_profile_ids=('model.b',)))
    router=CapabilityRouter(s,RuntimeProviderFactory(registry,Resolver(),RoutingPolicy()))
    return router,s,a,registry,ports
