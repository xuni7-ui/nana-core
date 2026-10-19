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


def provider_command(home,path):
    """One explicit typed host-local CAS command; never model/Subject authority."""
    from pathlib import Path
    from ..continuity.provider_config import ProviderCommand
    from ..continuity.privacy import _json_object
    import json,stat
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise CoreError('PROVIDER_COMMAND_FILE_INVALID')
        raw=stream.read(65537)
    if len(raw)>65536:raise CoreError('PROVIDER_COMMAND_BOUND')
    try:command=ProviderCommand.model_validate_json(json.dumps(json.loads(raw,object_pairs_hook=_json_object)))
    except (TypeError,ValueError):raise CoreError('PROVIDER_COMMAND_INVALID') from None
    authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'providers.json',authority)
    result=service.update(command,authority)
    return {'host_configuration_revision':result.revision,'operation':command.operation,'network_calls':0,'subject_history_changed':False,'live_permission_granted':False}


def provider_status(home):
    authority=ProviderConfigurationAuthority();service=ProviderConfigService(home/'providers.json',authority)
    factory=RuntimeProviderFactory(ProviderRegistry(),None,RoutingPolicy())
    from ..continuity.provider_routing import ProviderSettingsService
    return {'provider_settings':ProviderSettingsService(service,authority,factory).projection(),'real_provider_qualified':'NOT_RUN','network_calls':0}
