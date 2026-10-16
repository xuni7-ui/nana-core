"""Replaceable cognition/media resources, never subject identity or authority.

V1 implementations are deterministic fixtures. Registration is application wiring;
no credentials, SDK imports, network transport or archived provider instances.
"""
from typing import Annotated, Literal, Protocol
from pydantic import Field, model_validator
from ..contracts import DTO, CoreError
from ..storage import canonical, digest
from .cognition import ContinuityModelPort
from .context import ContextPolicy
from .memory import MemoryService
from .revision import state_token
from .extensions import NAME_PATTERN

Modality = Literal['TEXT','EMBEDDING','IMAGE','AUDIO','VIDEO']

class ProviderDescriptor(DTO):
    provider_id: str = Field(pattern=NAME_PATTERN)
    model_id: str = Field(pattern=NAME_PATTERN)
    model_version: str = Field(min_length=1, max_length=96)
    operations: tuple[Literal['COGNITION','EMBED','VISION','IMAGE_GENERATE','STT','TTS','AUDIO_UNDERSTAND','AUDIO_GENERATE','VIDEO_UNDERSTAND'], ...] = Field(min_length=1, max_length=9)
    input_modalities: tuple[Modality,...] = Field(min_length=1,max_length=5)
    output_modalities: tuple[Modality,...] = Field(min_length=1,max_length=5)
    context_limit: int = Field(ge=256, le=2000000)
    output_limit: int = Field(ge=1, le=131072)
    tool_proposals: bool = False
    locality: Literal['LOCAL_FIXTURE','LOCAL','REMOTE']
    permitted_privacy: tuple[Literal['PUBLIC','PROJECT','PERSONAL','SECRET'], ...]
    latency_class: Literal['LOW','MEDIUM','HIGH','UNKNOWN'] = 'UNKNOWN'
    cost_class: Literal['FIXTURE','LOW','MEDIUM','HIGH','UNKNOWN'] = 'UNKNOWN'
    tags: tuple[str,...] = Field(default=(), max_length=32)
    @model_validator(mode='after')
    def remote_secret(self):
        if self.locality=='REMOTE' and 'SECRET' in self.permitted_privacy:
            raise ValueError('remote secret routing forbidden')
        return self

class FrozenMediaInput(DTO):
    """Already policy-filtered, canonical fixture input. No Store/controller handle."""
    source_memory_ids: tuple[str,...]
    state_token: str
    content_json: str = Field(max_length=65536)
    content_digest: str

class MediaProposal(DTO):
    provenance: Literal['MODEL_PROPOSAL_NOT_TRUTH'] = 'MODEL_PROPOSAL_NOT_TRUTH'
    operation: str
    source_memory_ids: tuple[str,...]
    result_json: str = Field(max_length=65536)

class EmbeddingResult(DTO):
    vectors: tuple[Annotated[tuple[float,...],Field(min_length=1,max_length=4096)],...] = Field(min_length=1,max_length=32)
    source_memory_ids: tuple[str,...] = Field(min_length=1,max_length=32)

class CognitionModelPort(ContinuityModelPort, Protocol): pass
class EmbeddingPort(Protocol):
    def embed(self, request: FrozenMediaInput) -> EmbeddingResult: ...
class VisionUnderstandingPort(Protocol):
    def understand_image(self, request: FrozenMediaInput) -> MediaProposal: ...
class ImageGenerationPort(Protocol):
    def generate_image(self, request: FrozenMediaInput) -> MediaProposal: ...
class STTPort(Protocol):
    def transcribe(self, request: FrozenMediaInput) -> MediaProposal: ...
class TTSPort(Protocol):
    def synthesize_speech(self, request: FrozenMediaInput) -> MediaProposal: ...
class AudioUnderstandingPort(Protocol):
    def understand_audio(self, request: FrozenMediaInput) -> MediaProposal: ...
class AudioGenerationPort(Protocol):
    def generate_audio(self, request: FrozenMediaInput) -> MediaProposal: ...
class VideoUnderstandingPort(Protocol):
    def understand_video(self, request: FrozenMediaInput) -> MediaProposal: ...

_METHODS={'COGNITION':'propose','EMBED':'embed','VISION':'understand_image','IMAGE_GENERATE':'generate_image',
    'STT':'transcribe','TTS':'synthesize_speech','AUDIO_UNDERSTAND':'understand_audio',
    'AUDIO_GENERATE':'generate_audio','VIDEO_UNDERSTAND':'understand_video'}

class ProviderRegistry:
    """Ephemeral capability descriptors, not a second registry of subject facts."""
    def __init__(self): self._ports={}
    def register(self, descriptor: ProviderDescriptor, port):
        descriptor=ProviderDescriptor.model_validate_json(descriptor.model_dump_json())
        if descriptor.model_id in self._ports:raise CoreError('PROVIDER_ALREADY_REGISTERED')
        if any(not callable(getattr(port,_METHODS[op],None)) for op in descriptor.operations):
            raise CoreError('PROVIDER_CONTRACT_MISMATCH')
        self._ports[descriptor.model_id]=(descriptor,port)
    def descriptors(self): return tuple(d for d,p in self._ports.values())
    def _resolve(self, model_id, operation):
        if model_id not in self._ports:raise CoreError('PROVIDER_UNAVAILABLE')
        d,p=self._ports[model_id]
        if operation not in d.operations:raise CoreError('PROVIDER_OPERATION_UNAVAILABLE')
        # Descriptors do not turn a cloud/local SDK into authorized live execution.
        if d.locality!='LOCAL_FIXTURE':raise CoreError('REAL_MODEL_EXECUTION_NOT_AUTHORIZED')
        return d,p
    def cognition(self, model_id):
        return self._resolve(model_id,'COGNITION')[1]

    def deliberate(self, model_id, assembler, request, policy):
        """Use the existing assembler/session, with descriptor limits intersected."""
        from .cognition import DeliberationSession
        d,p=self._resolve(model_id,'COGNITION')
        filtered=policy.model_copy(update={
            'readable_privacy':tuple(x for x in policy.readable_privacy if x in d.permitted_privacy),
            'remote_privacy':tuple(x for x in policy.remote_privacy if x in d.permitted_privacy)})
        request=request.model_copy(update={'max_input_tokens':min(request.max_input_tokens,d.context_limit),
            'output_reserve_tokens':min(request.output_reserve_tokens,d.output_limit)})
        request=type(request).model_validate_json(request.model_dump_json())
        package=assembler.assemble(request,filtered)
        result=DeliberationSession(assembler).run(p,package,request,filtered)
        if len(result.raw_proposal_json.encode())>d.output_limit:raise CoreError('PROVIDER_OUTPUT_LIMIT')
        return result

class MediaSession:
    def __init__(self,store,registry,policy: ContextPolicy):
        self._store,self._registry,self._policy=store,registry,policy
    def _invoke(self,model_id,operation,memory_ids,*,scopes):
        d,p=self._registry._resolve(model_id,operation)
        if not scopes or not set(scopes)<=set(self._policy.allowed_scopes):raise CoreError('MEDIA_SCOPE_DENIED')
        if not 1<=len(memory_ids)<=32 or len(set(memory_ids))!=len(memory_ids):raise CoreError('MEDIA_INPUT_BOUND_INVALID')
        privacy=set(self._policy.readable_privacy)&set(d.permitted_privacy)
        memory=MemoryService(self._store);items=[];token=state_token(self._store)
        for mid in memory_ids:
            head=self._store.one('memories',mid)
            if not head or head['scope'] not in scopes or head['privacy_class'] not in privacy:
                raise CoreError('MEDIA_PRIVACY_DENIED')
            items.append({'memory_id':mid,'content':memory.read(mid)['text']})
        raw=canonical(items)
        if len(raw.encode())>min(d.context_limit,65536):raise CoreError('MEDIA_INPUT_TOO_LARGE')
        inp=FrozenMediaInput(source_memory_ids=tuple(memory_ids),state_token=token,content_json=raw,content_digest=digest(raw.encode()))
        result=getattr(p,_METHODS[operation])(inp)
        if token!=state_token(self._store):raise CoreError('MEDIA_SOURCE_STALE')
        expected=EmbeddingResult if operation=='EMBED' else MediaProposal
        if not isinstance(result,expected):raise CoreError('MEDIA_PROPOSAL_INVALID')
        result=expected.model_validate_json(result.model_dump_json())
        if result.source_memory_ids!=tuple(memory_ids):raise CoreError('MEDIA_SOURCE_MISMATCH')
        if isinstance(result,MediaProposal) and (result.operation!=operation or len(result.result_json.encode())>d.output_limit):
            raise CoreError('MEDIA_PROPOSAL_INVALID')
        if isinstance(result,MediaProposal):
            import json
            from .privacy import _json_object
            try:
                if canonical(json.loads(result.result_json,object_pairs_hook=_json_object))!=result.result_json:
                    raise ValueError()
            except (ValueError,TypeError):raise CoreError('MEDIA_PROPOSAL_INVALID') from None
        return result
    def embed(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'EMBED',memory_ids,scopes=scopes)
    def understand_image(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'VISION',memory_ids,scopes=scopes)
    def generate_image(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'IMAGE_GENERATE',memory_ids,scopes=scopes)
    def transcribe(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'STT',memory_ids,scopes=scopes)
    def synthesize_speech(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'TTS',memory_ids,scopes=scopes)
    def understand_audio(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'AUDIO_UNDERSTAND',memory_ids,scopes=scopes)
    def generate_audio(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'AUDIO_GENERATE',memory_ids,scopes=scopes)
    def understand_video(self,model_id,memory_ids,*,scopes): return self._invoke(model_id,'VIDEO_UNDERSTAND',memory_ids,scopes=scopes)

class EmbeddingIndexMetadata(DTO):
    provider_id: str
    model_id: str
    model_version: str
    dimension: int = Field(ge=1,le=4096)
    index_format: Literal['FIXTURE_FLAT_V1'] = 'FIXTURE_FLAT_V1'
    source_revision: str
    rebuild_token: str

class EmbeddingCache:
    """Disposable process-local cache. Never portable authority or exported data."""
    def __init__(self): self.metadata=None;self._vectors={}
    def rebuild(self,session: MediaSession,model_id,memory_ids,*,scopes):
        d,_=session._registry._resolve(model_id,'EMBED')
        result=session.embed(model_id,memory_ids,scopes=scopes)
        lengths={len(v) for v in result.vectors}
        import math
        if len(result.vectors)!=len(memory_ids) or len(lengths)!=1 or not 1<=next(iter(lengths))<=4096 or any(not math.isfinite(x) for v in result.vectors for x in v):
            raise CoreError('EMBEDDING_SHAPE_INVALID')
        token=state_token(session._store)
        self.metadata=EmbeddingIndexMetadata(provider_id=d.provider_id,model_id=d.model_id,model_version=d.model_version,
            dimension=next(iter(lengths)),source_revision=token,rebuild_token=digest([d.model_dump(mode='json'),token,tuple(memory_ids)]))
        self._vectors=dict(zip(memory_ids,result.vectors))
        return self.metadata
    def lookup(self,store,*,provider_id,model_id,model_version,dimension,index_format='FIXTURE_FLAT_V1'):
        if not self.metadata or (self.metadata.provider_id,self.metadata.model_id,self.metadata.model_version,self.metadata.dimension,self.metadata.index_format,self.metadata.source_revision)!=(provider_id,model_id,model_version,dimension,index_format,state_token(store)):
            self.metadata=None;self._vectors={}
            raise CoreError('EMBEDDING_REBUILD_REQUIRED')
        return dict(self._vectors)

class FixtureMediaPort:
    def __init__(self,dimension=3):self.dimension=dimension
    def embed(self,request):
        # A deterministic fixture, not a semantic-quality assertion.
        return EmbeddingResult(source_memory_ids=request.source_memory_ids,vectors=tuple(
            tuple(int(digest([mid,request.content_digest,i])[:8],16)/0xffffffff for i in range(self.dimension)) for mid in request.source_memory_ids))
    def _proposal(self,request,operation):
        return MediaProposal(operation=operation,source_memory_ids=request.source_memory_ids,
            result_json=canonical({'fixture':True,'operation':operation,'source_digest':request.content_digest}))
    def understand_image(self,r):return self._proposal(r,'VISION')
    def generate_image(self,r):return self._proposal(r,'IMAGE_GENERATE')
    def transcribe(self,r):return self._proposal(r,'STT')
    def synthesize_speech(self,r):return self._proposal(r,'TTS')
    def understand_audio(self,r):return self._proposal(r,'AUDIO_UNDERSTAND')
    def generate_audio(self,r):return self._proposal(r,'AUDIO_GENERATE')
    def understand_video(self,r):return self._proposal(r,'VIDEO_UNDERSTAND')
