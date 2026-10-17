"""Bounded interpretation DTOs. Confidence is reported belief, never verification."""
import base64, hashlib, math
from typing import Literal
from pydantic import Field, model_validator
from ...contracts import DTO

class SemanticDescriptor(DTO):
    provider_id: str = Field(min_length=1,max_length=96)
    model_id: str = Field(min_length=1,max_length=96)
    modalities: tuple[Literal['IMAGE','AUDIO','VIDEO'],...] = Field(min_length=1,max_length=3)
    asr: bool = False
    max_input_bytes: int = Field(default=65536,ge=1,le=98304)

class MediaPart(DTO):
    kind: Literal['IMAGE','AUDIO']
    mime: Literal['image/png','audio/wav']
    data_b64: str|None = Field(min_length=1,max_length=131072)
    digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    start_s: float = Field(default=0,ge=0,le=30,allow_inf_nan=False)
    end_s: float = Field(default=0,ge=0,le=30,allow_inf_nan=False)
    @model_validator(mode='after')
    def exact(self):
        data=base64.b64decode(self.data_b64,validate=True) if self.data_b64 is not None else None
        if (data is not None and (not data or hashlib.sha256(data).hexdigest()!=self.digest)) or self.end_s<self.start_s:raise ValueError('media part integrity')
        if (self.kind,self.mime) not in {('IMAGE','image/png'),('AUDIO','audio/wav')}:raise ValueError('media type')
        return self

class MediaSemanticInput(DTO):
    source_memory_id: str
    source_byte_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    modality: Literal['IMAGE','AUDIO','VIDEO']
    duration_s: float = Field(ge=0,le=30,allow_inf_nan=False)
    parts: tuple[MediaPart,...] = Field(min_length=1,max_length=9)
    asr_supported: bool
    @model_validator(mode='after')
    def bounded(self):
        if sum((len(base64.b64decode(p.data_b64)) if p.data_b64 is not None else 0) for p in self.parts)>98304:raise ValueError('media input bound')
        if self.modality=='IMAGE' and (len(self.parts)!=1 or self.parts[0].kind!='IMAGE' or self.duration_s!=0):raise ValueError('image envelope')
        if self.modality=='AUDIO' and (len(self.parts)!=1 or self.parts[0].kind!='AUDIO'):raise ValueError('audio envelope')
        if self.modality!='IMAGE' and self.duration_s<=0:raise ValueError('duration')
        if any(p.end_s>self.duration_s for p in self.parts):raise ValueError('media span')
        images=[p.start_s for p in self.parts if p.kind=='IMAGE']
        if images!=sorted(set(images)):raise ValueError('frame ordering')
        return self

class SemanticObservation(DTO):
    kind: Literal['OBJECT','ATTRIBUTE','SPATIAL_RELATION','TEXT_REGION','ACTIVITY','ACOUSTIC_EVENT','ASR_TRANSCRIPT','SCENE','SUMMARY']
    part_indices: tuple[int,...] = Field(min_length=1,max_length=9)
    label: str = Field(min_length=1,max_length=512)
    uncertainty: Literal['LOW','RELEVANT','HIGH','UNKNOWN']='UNKNOWN'
    confidence: float = Field(ge=0,le=1,allow_inf_nan=False)
    start_s: float = Field(default=0,ge=0,le=30,allow_inf_nan=False)
    end_s: float = Field(default=0,ge=0,le=30,allow_inf_nan=False)
    region: tuple[float,float,float,float]|None=None
    derived_from: tuple[int,...]=Field(default=(),max_length=16)
    @model_validator(mode='after')
    def region_and_span(self):
        if self.end_s<self.start_s:raise ValueError('semantic span')
        if self.region and (not all(math.isfinite(v) and 0<=v<=1 for v in self.region) or self.region[0]>=self.region[2] or self.region[1]>=self.region[3]):raise ValueError('normalized region')
        if len(set(self.part_indices))!=len(self.part_indices):raise ValueError('duplicate part')
        return self

class MediaSemantics(DTO):
    source_memory_id: str
    source_byte_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    observations: tuple[SemanticObservation,...] = Field(min_length=1,max_length=16)
    coverage: Literal['WHOLE_IMAGE','EXPLICIT_SEGMENTS','PARTIAL']
    asr_status: Literal['NOT_SUPPORTED','NO_SPEECH_REPORTED','TRANSCRIPT_PROPOSED','UNKNOWN']='UNKNOWN'
    confidence_semantics: Literal['PROVIDER_ESTIMATE_NOT_VERIFICATION']='PROVIDER_ESTIMATE_NOT_VERIFICATION'
