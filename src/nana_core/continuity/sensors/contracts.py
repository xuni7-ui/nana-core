"""Typed, bounded source contracts. Resource references are host-local only."""
import hashlib
from typing import Literal,Protocol
from pydantic import Field,model_validator
from ...contracts import DTO,CoreError
from ...storage import digest
from ..provider_config import ConfigDTO,Privacy
Kind=Literal['SYNTHETIC','FILE_IMPORT','SCREEN','CAMERA','MICROPHONE','APPLICATION_MEDIA','PLATFORM_MEDIA']
Modality=Literal['IMAGE','AUDIO','VIDEO']
class PerceptionSourceProfile(ConfigDTO):
    source_profile_id:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    display_name:str=Field(min_length=1,max_length=64)
    source_kind:Kind
    modality:Modality
    adapter_ref:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    resource_ref:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    scope:str=Field(min_length=1,max_length=64)
    entity_id:str=Field(min_length=1,max_length=128)
    privacy_class:Privacy='PUBLIC'
    enabled:bool=True
    capture_mode:Literal['ON_DEMAND','PERIODIC','EVENT_DRIVEN']='ON_DEMAND'
    base_interval_ms:int=Field(default=30000,ge=100,le=86400000)
    min_interval_ms:int=Field(default=1000,ge=100,le=86400000)
    max_interval_ms:int=Field(default=3600000,ge=100,le=86400000)
    max_capture_bytes:int=Field(default=1048576,ge=1,le=16777216)
    semantic_operations:tuple[Literal['VISION','AUDIO_UNDERSTAND','STT','VIDEO_UNDERSTAND'],...]=()
    retention_policy:Literal['MEMORY_ONLY_EPHEMERAL']='MEMORY_ONLY_EPHEMERAL'
    priority_class:Literal['BACKGROUND','FOREGROUND']='BACKGROUND'
    revision:int=Field(default=1,ge=1)
    @model_validator(mode='after')
    def valid(self):
        if not self.min_interval_ms<=self.base_interval_ms<=self.max_interval_ms:raise ValueError('interval order')
        ops={'IMAGE':{'VISION'},'AUDIO':{'AUDIO_UNDERSTAND','STT'},'VIDEO':{'VIDEO_UNDERSTAND'}}[self.modality]
        if not set(self.semantic_operations)<=ops or len(set(self.semantic_operations))!=len(self.semantic_operations):raise ValueError('operation modality')
        if self.source_kind=='SCREEN' and self.modality!='IMAGE' or self.source_kind=='MICROPHONE' and self.modality!='AUDIO':raise ValueError('kind modality')
        return self
class CapturePolicy(ConfigDTO):
    max_captures_per_minute:int=Field(default=30,ge=1,le=120)
    max_bytes_per_minute:int=Field(default=16777216,ge=1,le=67108864)
    max_semantic_calls_per_minute:int=Field(default=8,ge=0,le=32)
    background_percent:int=Field(default=50,ge=0,le=90)
    pending_capacity:int=Field(default=16,ge=1,le=64)
    debounce_us:int=Field(default=2000000,ge=0,le=5000000)
class PerceptionConfiguration(ConfigDTO):
    schema_version:Literal[1]=1
    revision:int=Field(default=0,ge=0)
    sources:tuple[PerceptionSourceProfile,...]=Field(default=(),max_length=32)
    policy:CapturePolicy=Field(default_factory=CapturePolicy)
    @model_validator(mode='after')
    def valid(self):
        if len({p.source_profile_id for p in self.sources})!=len(self.sources):raise ValueError('duplicate source')
        return self
class SourceCommand(ConfigDTO):
    operation:Literal['UPSERT_PERCEPTION_SOURCE','REMOVE_PERCEPTION_SOURCE','ENABLE_PERCEPTION_SOURCE','DISABLE_PERCEPTION_SOURCE','SET_CAPTURE_POLICY']
    expected_revision:int=Field(ge=0)
    profile:PerceptionSourceProfile|None=None
    target_id:str|None=None
    policy:CapturePolicy|None=None
    @model_validator(mode='after')
    def valid(self):
        expected='profile' if self.operation=='UPSERT_PERCEPTION_SOURCE' else 'policy' if self.operation=='SET_CAPTURE_POLICY' else 'target_id'
        if getattr(self,expected) is None or any(getattr(self,k) is not None for k in ['profile','policy','target_id'] if k!=expected):raise ValueError('command shape')
        return self
class ObservationRequest(ConfigDTO):
    request_id:str=Field(pattern=r'^[a-zA-Z0-9._:-]{1,128}$')
    source_profile_id:str
    source_revision:int=Field(ge=1)
    requested_modality:Modality
    reason_kind:Literal['USER_REQUEST','SCHEDULED','SUBJECT_WATCH','SYSTEM_RECOVERY','SOURCE_EVENT']
    requested_at_us:int=Field(ge=0)
    deadline_us:int=Field(ge=0)
    foreground:bool=False
    source_record_ids:tuple[str,...]=Field(default=(),max_length=16)
    privacy_class:Privacy='PUBLIC'
    max_capture_bytes:int=Field(default=1048576,ge=1,le=16777216)
    semantic_requested:bool=True
    requested_operations:tuple[Literal['VISION','AUDIO_UNDERSTAND','STT','VIDEO_UNDERSTAND'],...]=()
    sample_key:str|None=Field(default=None,max_length=128)
    @model_validator(mode='after')
    def valid(self):
        if not self.requested_at_us<self.deadline_us:raise ValueError('deadline')
        return self
class CapturedMedia(DTO):
    capture_id:str
    source_profile_id:str
    source_revision:int
    source_event_id:str=Field(min_length=1,max_length=128)
    modality:Modality
    event_time_us:int=Field(ge=0)
    observed_time_us:int=Field(ge=0)
    byte_digest:str
    byte_length:int=Field(ge=1,le=16777216)
    coverage:str=Field(min_length=1,max_length=64)
    sequence:int=Field(ge=0)
    privacy_class:Privacy
    data:bytes=Field(exclude=True,repr=False)
    def verify(self,profile,now):
        if (self.source_profile_id,self.source_revision,self.modality,self.privacy_class)!=(profile.source_profile_id,profile.revision,profile.modality,profile.privacy_class):raise CoreError('CAPTURE_SOURCE_MISMATCH')
        if type(self.data)!=bytes or not 1<=len(self.data)<=profile.max_capture_bytes or self.byte_length!=len(self.data) or hashlib.sha256(self.data).hexdigest()!=self.byte_digest:raise CoreError('CAPTURE_INTEGRITY')
        if not self.event_time_us<=self.observed_time_us<=now:raise CoreError('CAPTURE_TIME_INVALID')
        if self.capture_id!=capture_identity(self.source_profile_id,self.source_revision,self.source_event_id,self.event_time_us,self.sequence,self.byte_digest):raise CoreError('CAPTURE_ID_INVALID')
        return self

def capture_identity(profile,revision,event,event_time,sequence,sha):return digest([profile,revision,event,event_time,sequence,sha])
class SourceDescription(DTO):
    adapter_identity:str=Field(pattern=r'^[a-z][a-z0-9._-]{0,63}$')
    source_kind:Kind
    modalities:tuple[Modality,...]
    max_bytes:int=Field(ge=1,le=16777216)
    privacy_floor:Privacy='PUBLIC'
class PerceptionSourcePort(Protocol):
    def describe(self)->SourceDescription:...
    def capture(self,request:ObservationRequest)->CapturedMedia:...
    def health(self)->str:...
ScreenPerceptionPort=PerceptionSourcePort
CameraPerceptionPort=PerceptionSourcePort
MicrophonePerceptionPort=PerceptionSourcePort
class HostPerceptionResolver:
    def __init__(self):self.__ports={}
    def bind(self,adapter_ref,resource_ref,port):
        if (adapter_ref,resource_ref) in self.__ports:raise CoreError('SOURCE_ALREADY_BOUND')
        if not all(callable(getattr(port,x,None)) for x in ['describe','capture','health']):raise CoreError('SOURCE_CONTRACT_INVALID')
        self.__ports[adapter_ref,resource_ref]=port
    def resolve(self,profile):
        port=self.__ports.get((profile.adapter_ref,profile.resource_ref))
        if port is None:raise CoreError('SOURCE_UNAVAILABLE')
        try:d=port.describe()
        except Exception:raise CoreError('SOURCE_UNAVAILABLE') from None
        if type(d) is not SourceDescription or d.source_kind!=profile.source_kind or profile.modality not in d.modalities or profile.max_capture_bytes>d.max_bytes:raise CoreError('SOURCE_DESCRIPTOR_MISMATCH')
        from ..memory import PRIVACY_RANK
        if PRIVACY_RANK[profile.privacy_class]<PRIVACY_RANK[d.privacy_floor]:raise CoreError('SOURCE_PRIVACY_FLOOR_DENIED')
        return port
