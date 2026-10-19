"""Explicit future host wiring; no ambient credentials, discovery or live default."""
import os
from ..contracts import CoreError
from ..continuity.provider_config import ProviderConfigService,ProviderConfigurationAuthority,ResolvedSecret
from ..continuity.provider_routing import CapabilityRouter,RuntimeProviderFactory,RoutingPolicy
from ..continuity.providers import ProviderRegistry

class ExplicitFDResolver:
    """Host explicitly passes one credential FD/ref, only after separate consent."""
    def __init__(self,fd,reference):
        raw=os.read(fd,4097)
        if len(raw)>4096:raise CoreError('SECRET_UNAVAILABLE')
        self._value=ResolvedSecret(raw.decode().strip());self._reference=reference
    def available(self,reference):return reference==self._reference and self._value is not None
    def resolve(self,reference):
        if not self.available(reference):raise CoreError('SECRET_UNAVAILABLE')
        return ResolvedSecret(self._value.reveal_for_header())
    def clear(self):
        if self._value:self._value.clear()
        self._value=None
    def __repr__(self):return '<ExplicitFDResolver REDACTED>'


def configured_router(home,config,*,resolver,authorized=False):
    if not authorized or not config.provider_hosts or not config.remote_privacy or config.provider_cost_ceiling_micro<=0 or config.provider_calls_per_day<=0:raise CoreError('LIVE_PROVIDER_NOT_AUTHORIZED_OR_BUDGETED')
    authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'providers.json',authority)
    service.load()
    factory=RuntimeProviderFactory(ProviderRegistry(),resolver,RoutingPolicy(allow_remote=True,allowed_remote_hosts=config.provider_hosts,timeout_ceiling_ms=config.provider_timeout_ms,cost_ceiling=config.provider_cost_ceiling_micro,context_limit=8192,output_limit=1024))
    return CapabilityRouter(service,factory)
