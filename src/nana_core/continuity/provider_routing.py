"""Capability selection before dispatch. No judgment, retries or Subject writes.

Factory/Router are trusted application wiring; existing sessions still own all
privacy/source/usage/recovery validation and dispatch. Config is never memory.
"""
from dataclasses import dataclass,field
from typing import Literal
from urllib.parse import urlsplit
from pydantic import Field
from ..contracts import DTO,CoreError
from ..storage import digest
from .provider_config import ProviderConfigService,ResolvedSecret,Privacy
from .providers import Operation,Modality,ProviderRegistry,MediaSession

class RoutingPolicy(DTO):
    """Application/runtime maxima. Frontend config cannot mutate this policy."""
    allow_remote:bool=False
    allowed_remote_hosts:tuple[str,...]=()
    allow_synthetic_loopback:bool=False
    timeout_ceiling_ms:int=Field(default=30000,ge=50,le=30000)
    cost_ceiling:int=Field(default=100000,ge=0,le=1000000)
    context_limit:int=Field(default=65536,ge=256,le=2000000)
    output_limit:int=Field(default=8192,ge=1,le=131072)

class RouteRequest(DTO):
    operation:Operation
    input_modalities:tuple[Modality,...]=('TEXT',)
    privacy_class:Privacy='PUBLIC'
    timeout_ms:int=Field(default=3000,ge=50,le=30000)
    cost_ceiling:int=Field(default=1000,ge=0,le=1000000)
    context_limit:int=Field(default=16384,ge=256,le=2000000)
    output_limit:int=Field(default=2048,ge=1,le=131072)
    exact_provider_profile_id:str|None=None
    exact_model_profile_id:str|None=None

class EffectiveLimits(DTO):
    timeout_ms:int=Field(ge=50,le=30000)
    cost_ceiling:int=Field(ge=0,le=1000000)
    context_limit:int=Field(ge=256,le=2000000)
    output_limit:int=Field(ge=1,le=131072)
    permitted_privacy:tuple[Privacy,...]

class PreDispatchReason(DTO):
    model_profile_id:str
    code:str
    dispatched:Literal[False]=False

class RouteSnapshot(DTO):
    """Historical call provenance, not portable active config or a secret handle."""
    operation:Operation
    config_revision:int
    route_revision:int|None
    provider_profile_id:str
    provider_revision:int
    model_profile_id:str
    model_revision:int
    remote_model_id:str
    model_version:str
    provider_id:str
    protocol:str
    selection:Literal['PRIMARY','FALLBACK','EXACT_MODEL']
    reasons:tuple[PreDispatchReason,...]=()
    effective:EffectiveLimits

class RuntimeProviderFactory:
    def __init__(self,registry:ProviderRegistry,secret_resolver,policy:RoutingPolicy):
        self.registry=registry;self.__resolver=secret_resolver;self.policy=policy
    def secret_state(self,provider):
        if provider.secret_ref is None:return 'UNCONFIGURED'
        try:return 'AVAILABLE' if self.__resolver is not None and self.__resolver.available(provider.secret_ref) else 'MISSING'
        except Exception:return 'MISSING'
    def create(self,provider,model,operation):
        if provider.protocol=='LOCAL':
            try:d,port=self.registry._resolve(model.model_profile_id,operation)
            except CoreError:raise CoreError('PRE_DISPATCH_UNAVAILABLE') from None
            if d!=model.descriptor(provider):raise CoreError('PRE_DISPATCH_UNAVAILABLE')
            return port
        if provider.protocol not in {'OPENAI_COMPATIBLE_CHAT','SYNTHETIC_LOOPBACK'}:raise CoreError('PROVIDER_PROTOCOL_UNAVAILABLE')
        if operation not in {'COGNITION','VISION','AUDIO_UNDERSTAND','VIDEO_UNDERSTAND'}:raise CoreError('OPERATION_UNSUPPORTED')
        harness=provider.protocol=='SYNTHETIC_LOOPBACK'
        if harness and not self.policy.allow_synthetic_loopback:raise CoreError('PRE_DISPATCH_UNAVAILABLE')
        if not harness and (not self.policy.allow_remote or urlsplit(provider.base_url).hostname not in self.policy.allowed_remote_hosts):raise CoreError('PRE_DISPATCH_UNAVAILABLE')
        credential=None;secret=None
        if not harness:
            if self.secret_state(provider)!='AVAILABLE':raise CoreError('SECRET_UNAVAILABLE')
            try:
                secret=self.__resolver.resolve(provider.secret_ref)
                if type(secret) is not ResolvedSecret:raise ValueError()
                credential=secret.reveal_for_header()
                if credential is None:raise ValueError()
            except Exception:raise CoreError('SECRET_UNAVAILABLE') from None
        try:
            from .world_loop.cognition import OpenAIJSONTransport
            from .world_loop.semantics import OpenAIMediaTransport
            from .world_loop.semantic_contracts import SemanticDescriptor
            endpoint=provider.base_url+'/chat/completions'
            kw=dict(provider_id=provider.provider_profile_id,credential=credential,harness=harness)
            if operation=='COGNITION':return OpenAIJSONTransport(endpoint,model.remote_model_id,**kw)
            modality={'VISION':'IMAGE','AUDIO_UNDERSTAND':'AUDIO','VIDEO_UNDERSTAND':'VIDEO'}[operation]
            # ASR is a separate configured port; no implicit ASR claim here.
            descriptor=SemanticDescriptor(provider_id=provider.provider_profile_id,model_id=model.remote_model_id,modalities=(modality,),asr=False,max_input_bytes=98304)
            return OpenAIMediaTransport(endpoint,model.remote_model_id,descriptor=descriptor,**kw)
        finally:
            if secret:secret.clear()
            credential=None

@dataclass(repr=False)
class RoutedTarget:
    snapshot:RouteSnapshot
    port:object=field(repr=False)
    context_policy:object=field(repr=False)
    _router:object=field(repr=False)
    def __repr__(self):return '<RoutedTarget sanitized='+self.snapshot.model_profile_id+'>'
    def _current(self):return self._router.current(self.snapshot)
    def cognition_session(self,runtime):
        if not callable(getattr(self.port,'exchange',None)):raise CoreError('COGNITION_TRANSPORT_REQUIRED')
        from .world_loop.cognition import CognitionSession
        return CognitionSession(runtime,self.port,self.context_policy,route_snapshot=self.snapshot,route_guard=self._current)
    def media_session(self,store):
        if not self._current():raise CoreError('ROUTE_CHANGED_BEFORE_DISPATCH')
        return MediaSession(store,self._router.factory.registry,self.context_policy,limits=self.snapshot.effective,route_guard=self._current,route_binding=(self.snapshot.model_profile_id,self.snapshot.operation))
    def media(self,store,memory_ids,*,scopes):
        if not self._current():raise CoreError('ROUTE_CHANGED_BEFORE_DISPATCH')
        session=self.media_session(store)
        result=session._invoke(self.snapshot.model_profile_id,self.snapshot.operation,memory_ids,scopes=scopes)
        return {'route':self.snapshot,'proposal':result}
    def embedding_rebuild(self,cache,store,memory_ids,*,scopes):
        if self.snapshot.operation!='EMBED':raise CoreError('OPERATION_UNSUPPORTED')
        return cache.rebuild(self.media_session(store),self.snapshot.model_profile_id,memory_ids,scopes=scopes,route_token=digest(self.snapshot.model_dump(mode='json')))
    def embedding_lookup(self,cache,store,*,dimension):
        if not self._current():raise CoreError('EMBEDDING_REBUILD_REQUIRED')
        return cache.lookup(store,provider_id=self.snapshot.provider_id,model_id=self.snapshot.remote_model_id,model_version=self.snapshot.model_version,dimension=dimension,route_token=digest(self.snapshot.model_dump(mode='json')))

class CapabilityRouter:
    def __init__(self,configuration:ProviderConfigService,factory:RuntimeProviderFactory):
        self.config,self.factory=configuration,factory
    def current(self,snapshot):
        try:return self.config.load().revision==snapshot.config_revision
        except CoreError:return False
    def resolve(self,request:RouteRequest,context_policy):
        if type(request) is not RouteRequest:raise CoreError('ROUTING_TYPED_REQUEST_REQUIRED')
        request=RouteRequest.model_validate_json(request.model_dump_json())
        c=self.config.load();ps={p.provider_profile_id:p for p in c.providers};ms={m.model_profile_id:m for m in c.models};route=next((r for r in c.routes if r.operation==request.operation),None)
        exact=request.exact_model_profile_id is not None or request.exact_provider_profile_id is not None
        if exact and (request.exact_model_profile_id is None or request.exact_provider_profile_id is None):raise CoreError('EXACT_MODEL_BINDING_REQUIRED')
        if route and not route.enabled:raise CoreError('PROFILE_DISABLED')
        if not route and not exact:raise CoreError('CAPABILITY_ROUTE_UNAVAILABLE')
        ids=(request.exact_model_profile_id,) if exact else (route.primary_model_profile_id,*route.fallback_model_profile_ids)
        reasons=[];last='PRE_DISPATCH_UNAVAILABLE'
        for i,mid in enumerate(ids):
            try:
                m=ms.get(mid)
                if not m or (exact and m.provider_profile_id!=request.exact_provider_profile_id):raise CoreError('PRE_DISPATCH_UNAVAILABLE')
                p=ps[m.provider_profile_id]
                if not p.enabled or not m.enabled:raise CoreError('PROFILE_DISABLED')
                if request.operation not in m.operations:raise CoreError('OPERATION_UNSUPPORTED')
                if not set(request.input_modalities)<=set(m.input_modalities):raise CoreError('MODALITY_UNSUPPORTED')
                allowed=context_policy.remote_privacy if p.locality=='REMOTE' else context_policy.readable_privacy
                privacy=tuple(x for x in allowed if x in p.permitted_privacy and (not route or x in route.permitted_privacy) and (p.locality!='REMOTE' or x!='SECRET'))
                if request.privacy_class not in privacy:raise CoreError('PRIVACY_DENIED')
                limits=EffectiveLimits(timeout_ms=min(request.timeout_ms,p.default_timeout_ms,route.timeout_ceiling_ms if route else 30000,self.factory.policy.timeout_ceiling_ms),cost_ceiling=min(request.cost_ceiling,p.default_cost_ceiling,route.cost_ceiling if route else 1000000,self.factory.policy.cost_ceiling),context_limit=min(request.context_limit,m.context_limit,self.factory.policy.context_limit,route.context_ceiling if route else 2000000),output_limit=min(request.output_limit,m.output_limit,self.factory.policy.output_limit,route.output_ceiling if route else 131072),permitted_privacy=privacy)
                if p.locality=='REMOTE' and limits.cost_ceiling==0:raise CoreError('BUDGET_DENIED')
                port=self.factory.create(p,m,request.operation)
                policy=context_policy.model_copy(update={'readable_privacy':tuple(x for x in context_policy.readable_privacy if x in privacy),'remote_privacy':tuple(x for x in context_policy.remote_privacy if x in privacy)})
                snap=RouteSnapshot(operation=request.operation,config_revision=c.revision,route_revision=route.revision if route else None,provider_profile_id=p.provider_profile_id,provider_revision=p.revision,model_profile_id=m.model_profile_id,model_revision=m.revision,remote_model_id=m.remote_model_id,model_version=m.model_version,provider_id=p.provider_profile_id,protocol=p.protocol,selection='EXACT_MODEL' if exact else 'FALLBACK' if i else 'PRIMARY',reasons=tuple(reasons),effective=limits)
                return RoutedTarget(snap,port,policy,self)
            except CoreError as exc:
                last=exc.code;reasons.append(PreDispatchReason(model_profile_id=mid,code=last))
                if exact:raise CoreError(last) from None
        raise CoreError(last)


class ProviderSettingsService:
    """Application-owned configuration controller, never handed to ModelPorts."""
    def __init__(self,configuration,authority,factory):
        self._configuration,self.__authority,self._factory=configuration,authority,factory
        configuration._check(authority)
    def projection(self):
        c=self._configuration.load();profiles=[]
        for p in c.providers:
            data=p.model_dump(mode='json',exclude={'secret_ref'})
            data['secret_state']=self._factory.secret_state(p);profiles.append(data)
        return {'schema_version':c.schema_version,'revision':c.revision,'providers':profiles,'models':[m.model_dump(mode='json') for m in c.models],'routes':[r.model_dump(mode='json') for r in c.routes],'storage_class':'HOST_LOCAL_NOT_SUBJECT_MEMORY','execution_authority':False}
    def command(self,command):
        self._configuration.update(command,self.__authority)
        return self.projection()
