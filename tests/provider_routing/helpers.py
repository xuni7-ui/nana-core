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
